from evennia import CmdSet
from evennia.utils import list_to_string
from evennia.commands.default.muxcommand import MuxCommand

import inflect
_INFLECT = inflect.engine()

# Custom Look command expanding the look syntax to view objects contained
# within other objects, with natural language syntax.
class CmdLook(MuxCommand):
	"""
	look

	Usage:
	  look
	  look <obj>
		look in <obj>
		look <container>'s <obj>
		look <obj> in <container>

	Observes your location or objects in your vicinity.
	"""
	key = "look"
	aliases = ["l", "look at"]
	locks = "cmd:all()"
	arg_regex = r"\s|$"
	rhs_split = (" in ", " on ") 

	def func(self):
		"""
		Handle the looking
		"""
		caller = self.caller
		location = caller.location

		if not self.args:
			target = location
			if not target:
				caller.msg("You have no location to look at.")
				return
			self.msg((caller.at_look(target), {"type": "look"}), options=None)
			return

		# parse for possessive 's
		if not self.rhs and ("'s " in self.args):
			# split at the first possessive and swap
			self.rhs, self.lhs = self.args.strip().split("'s ", maxsplit=1)

		# at this point, `lhs` is the target and `rhs` is the container
		holder = None
		target = None
		look_in = False

		# if there's a rhs, get the container and its access
		if self.rhs:
			holder = caller.search(self.rhs)
			if not holder:
				return
			if not holder.access(caller, "viewcon") and not holder.access(caller, "getfrom"):
				self.msg("You can't look there.")
				return

		# if there's a lhs, get the target
		if self.lhs:
			candidates = holder.contents if holder else caller.contents + location.contents
			target = caller.search(self.lhs, candidates=candidates)
			if not target:
				return

		# at this point, all needed objects have been found
		# if "target" isn't specified, the container IS the target
		if holder and not target:
			look_in = True
			target = holder
		
		self.msg((caller.at_look(target, look_in=look_in), {"type": "look"}), options=None)

# Custom Get command allowing you to get objects from within other objects.
class CmdGet(MuxCommand):
	"""
	pick up something

	Usage:
	    get <obj>
	    get <obj> from <obj>

	Picks up an object from your location or another object you have permission
	to get (or get from) and puts it in your inventory.
	"""

	key = "get"
	aliases = "grab"
	locks = "cmd:all()"
	arg_regex = r"\s|$"
	rhs_split = (" from ",) 

	def func(self):
		"""implements the command."""

		caller = self.caller

		if not self.args:
			caller.msg("Get what?")
			return

		if self.rhs:
			holder = caller.search(self.rhs)
			if not holder:
				return
			if not holder.access(caller, "getfrom"):
				self.msg("You can't get things from there.")
				return
		else:
			holder = None

		# add support for a csl here
		if holder:
			obj = caller.search(self.lhs, holder.contents)
		else:
			obj = caller.search(self.lhs)

		if not obj:
			return

		if caller == obj:
			caller.msg("You can't get yourself.")
			return
		if not obj.access(caller, "get"):
			if obj.db.get_err_msg:
				caller.msg(obj.db.get_err_msg)
			else:
				caller.msg("You can't get that.")
			return

		# calling at_before_get hook method
		if not obj.at_before_get(caller):
			return

		success = obj.move_to(caller, quiet=True)
		if not success:
			if obj.db.get_err_msg:
				caller.msg(obj.db.get_err_msg)
			else:
				caller.msg("This can't be picked up.")
			return
		if holder:
			caller.location.msg_contents("gets %s from %s." % (_INFLECT.an(obj.name), _INFLECT.an(holder.name)))
		else:
			caller.location.msg_contents("picks up %s." % _INFLECT.an(obj.name))
		# calling at_get hook method
		obj.at_get(caller)


class CmdPut(MuxCommand):
	"""
	put something on something else

	Usage:
	    put <obj> on <obj>
	    put <obj> in <obj>

	Lets you place an object in your inventory into (or onto)
	another object.
	"""

	key = "put"
#	aliases = "place"
	locks = "cmd:all()"
	arg_regex = r"\s|$"

	def func(self):
		"""Implement command"""

		caller = self.caller
		if not self.args:
			caller.msg("Put down what?")
			return

		target = None

		# remember command split syntax
		if " on " in self.args:
			self.lhs, self.rhs = self.args.strip().split(" on ", maxsplit=1)
			syntax = "on"
		elif " in " in self.args:
			self.lhs, self.rhs = self.args.strip().split(" in ", maxsplit=1)
			syntax = "in"
		else:
			# "put" requires two arguments
			caller.msg("Put it where?")
			return

		# add support for a csl here
		obj = caller.search(self.lhs, location=caller)
		if not obj:
			return

		# Call the object script's at_before_drop() method.
		if not obj.at_before_drop(caller):
			return

		target = caller.search(self.rhs)
		if not target:
			return
		if not target.access(caller, 'getfrom'):
			caller.msg("You can't put things there.")
			return
		success = obj.move_to(target, quiet=True)

		if not success:
			caller.msg("This couldn't be put down.")
			return

		 caller.location.msg_contents("puts %s %s %s." % (_INFLECT.an(obj.name), syntax, _INFLECT.an(target.name)))
		# Call the object script's at_drop() method.
		obj.at_drop(caller)


class CmdUse(MuxCommand):
	"""
	use something

	Usage:
		use <obj>
		use <obj> on <target>

	Lets you use a particular item, for whatever its intended purpose is.
	"""

	key = "use"
	locks = "cmd:all()"
	rhs_split = (" on ", "=")
	arg_regex = r"\s|$"

	def func(self):
		caller = self.caller

    if not self.args:
			caller.msg("Use what?")
			return

		obj = caller.search(self.lhs)
		if not obj:
			return

		if self.rhs:
			target = caller.search(self.rhs)
			if not target:
				return
		else:
			target = None

		# Call the object script's at_before_use() method.
		try:
			if not obj.at_before_use(caller, target=target):
				return
		except AttributeError:
			caller.msg("That is not usable.")
			return

		obj.at_use(caller, target=target)


# CmdSet for extended basic commands
class BasicsCmdSet(CmdSet):
	"""
	Groups the extended basic commands.
	"""

	def at_cmdset_creation(self):
		self.add(CmdLook)
		self.add(CmdGet)
		self.add(CmdPut)
		self.add(CmdUse)
