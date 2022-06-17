from django.conf import settings

from evennia.accounts.models import AccountDB
from evennia.utils import create, search, logger, utils
from evennia.utils.utils import class_from_module

from .evbot import DiscordBot
from .settings import EVBOT_PREFIX

COMMAND_DEFAULT_CLASS = class_from_module(settings.COMMAND_DEFAULT_CLASS)

class CmdDiscord2Chan(COMMAND_DEFAULT_CLASS):
	"""
	Link an evennia channel to an external Discord channel

	Usage:
	  discord2chan[/switches] <evennia channel> = <discord channel ID>,<botname>[:typeclass]
	  discord2chan/delete botname|#dbid

	Switches:
	  /delete	 - this will delete the bot and remove the irc connection
					to the channel. Requires the botname or #dbid as input.
	  /remove	 - alias to /delete
	  /disconnect - alias to /delete
		/list - not yet implemented, but will show all active discord relays

	Example:
	  discord2chan discordchan = 55555555555,discbot
	  discord2chan public = 12345667886 discbot:accounts.mybot.MyBot

	This creates a bot that relays messages from the game channel to a
	Discord channel, and vice versa.

	If a custom typeclass path is given, this will be used instead of
	the default DiscordBot class.

	In order for the bot to function, you will also need to create a
	Discord application and bot, and make sure it has access to the
	Discord server and channel you want to relay to and from. Only one
	Discord application is needed.
	"""

	key = "discord2chan"
	switch_options = ("delete", "remove", "disconnect", "list",)
	locks = "pperm(Developer)"
	help_category = "Comms"

	def func(self):
		"""Setup the discord-channel mapping"""


		if "list" in self.switches:
			# show all connections
			self.msg("Botlist is not yet implemented.")
			return

		if "disconnect" in self.switches or "remove" in self.switches or "delete" in self.switches:
			botname = self.lhs
			if not botname.startswith(EVBOT_PREFIX):
				botname = EVBOT_PREFIX + botname
			matches = AccountDB.objects.filter(db_is_bot=True, username=botname)
			dbref = utils.dbref(self.lhs)
			if not matches and dbref:
				# try dbref match
				matches = AccountDB.objects.filter(db_is_bot=True, id=dbref)
			if matches:
				matches[0].delete()
				self.msg("Discord connection destroyed.")
			else:
				self.msg("Discord connection/bot could not be removed, does it exist?")
			return

		if not self.args or not self.rhs:
			string = (
				"Usage: discord2chan[/switches] <evennia_channel> ="
				" <discord channel ID>"
			)
			self.msg(string)
			return

		channel = self.lhs
		if len(self.rhslist) > 1:
			dc_chan_id = self.rhslist[0]
			dc_botname = ",".join(self.rhslist[1:])
		else:
			dc_chan_id = self.rhs
			dc_botname = channel
		try:
			dc_chan_id = int(dc_chan_id)
		except Exception:
			string = "Discord channel ID '%s' is not valid." % self.rhs
			self.msg(string)
			return

		botclass = None
		if ":" in dc_botname:
			dc_botname, botclass = [part.strip() for part in dc_botname.split(":", 2)]
		botname = dc_botname
		if not botname.startswith(EVBOT_PREFIX):
			botname = EVBOT_PREFIX + botname
		# If path given, use custom bot otherwise use default.
		botclass = botclass if botclass else DiscordBot

		# create a new bot
		bot = AccountDB.objects.filter(username__iexact=botname)
		if bot:
			# re-use an existing bot
			bot = bot[0]
			if not bot.is_bot:
				self.msg("Account '%s' already exists and is not a bot." % botname)
				return
		else:
			try:
				bot = create.create_account(botname, None, None, typeclass=botclass)
			except Exception as err:
				self.msg("|rError, could not create the bot:|n '%s'." % err)
				return
		bot.initialize(
			ev_channel=channel,
			dc_botname=botname,
			dc_chan_id=dc_chan_id
		)
		self.msg("Connection to Discord created.")
