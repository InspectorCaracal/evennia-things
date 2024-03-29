"""
Room Decor Module

Allows you to decorate a room with various objects, which displays
those objects as part of the room's description instead of its
contents on look.

How To Use:
    - Copy this file into your gamedir.
    - Add 'CmdPlace' to your default CharacterCmdSet
    - Create rooms or objects with the classes below to let them
        be decoratable or used for decoration.
    - Or, use them as parents for your own classes.

Once installed, DecorRooms can be decorated with DecorObjects by using
the `place` command. By default this is available to all players and 
decorating permissions are controlled by the `decorate` lockfunc.

Since the decor objects are still in the room, players retain their
ability to look at or otherwise interact with them. Sittable chairs
will still be sittable, and so on.
"""

from evennia import DefaultObject, DefaultRoom
from evennia.utils.utils import iter_to_str
from evennia.commands.cmdset import CmdSet
from evennia.commands.default.muxcommand import MuxCommand

from random import randint
from collections import defaultdict

class DecorObject(DefaultObject):
    """
    Base class for any objects that can be used to decorate rooms.
    """
    def at_pre_place(self, doer, location):
        """
        Access and validity checks before placement
        """
        return location.access(doer, "decorate")

    def place(self, doer, location, position):
        """
        Do the actual placement or replacement.
        """
        if self.location != location:
            drop = self.move_to(location, quiet=True)
            if not drop:
                doer.msg("You can't put things there.")
                return
        # fallback position if none was set
        position = "here" if position == True
        # set the placement status
        if position[-1] in ('.','!','?',',',';',':'):
            position = position[:-1]
        self.db.placed = position
        try:
            location.update_decor()
        except AttributeError:
            self.db.placed = False
            doer.msg("This location can't be decorated.")
            return

        doer.msg(f"You place the {self.get_display_name(doer)} {position}.")

    def at_pre_get(self, getter, **kwargs):
        # if already placed in the room, check decor access
        if self.db.placed:
            # does getter have decor access for the room
            if not self.location.access(getter, "decorate"):
                return False
        return True

    def move_to(self, destination, **kwargs):
        """
        Make sure that being moved unsets placement.
        """
        location = self.location
        success = super().move_to(destination, **kwargs)
        if success or self.location == destination:
            self.db.placed = False
            try:
                location.update_decor()
            except AttributeError:
                pass
        return success


class DecorRoom(DefaultRoom):
    """
    Rooms that can be decorated with decor objects.
    """
    def get_display_things(self, looker, **kwargs):
        """
        Get the 'things' component of the object description. Called by `return_appearance`.

        Args:
            looker (Object): Object doing the looking.
            **kwargs: Arbitrary data for use when overriding.
        Returns:
            str: The things display data.

        """

        def _filter_visible(obj_list):
            # we use a modified filter that ignores objects that have been placed as decor
            return (obj for obj in obj_list if not obj.db.placed and obj != looker and obj.access(looker, "view"))

        # sort and handle same-named things
        things = _filter_visible(self.contents_get(content_type="object"))

        grouped_things = defaultdict(list)
        for thing in things:
            grouped_things[thing.get_display_name(looker, **kwargs)].append(thing)

        thing_names = []
        for thingname, thinglist in sorted(grouped_things.items()):
            nthings = len(thinglist)
            thing = thinglist[0]
            singular, plural = thing.get_numbered_name(nthings, looker, key=thingname)
            thing_names.append(singular if nthings == 1 else plural)
        thing_names = iter_to_str(thing_names)
        return f"\n|wYou see:|n {thing_names}" if thing_names else ""

    def get_display_desc(self, looker, **kwargs):
        """
        Appends the current decor description to the room's description.
        """
        desc = super().get_display_desc(looker, **kwargs)
        
        if self.db.decor_desc:
            desc = f"{desc} {decor_desc}" if desc else decor_desc

        return desc

    def update_decor(self):
        """
        Re-processes all placed decor objects to generate their description.
        """
        decor_descs = []
        placements = defaultdict(list)
        # get a list of all objects that have been placed as decor
        decor_list = [obj for obj in self.contents_get(content_type="object") if obj.db.placed]

        # group decor by position
        for decor in decor_list:
            placements[decor.db.placed].append(decor.get_numbered_name(1,self)[0])

        for position, names_list in placements.items():
            verb = "is" if len(names_list) == 1 else "are"
            names = iter_to_str(names_list)
            # liven up the decor desc a bit by occasionally swapping the name/position order
            if randint(1,4) == 1:
                desc = f"{position} {verb} {names}."
            else:
                desc = f"{names} {verb} {position}."
            # capitalize sentences
            desc = desc[0].upper() + desc[1:]
            decor_descs.append(desc)

        # set the decor description
        self.db.decor_desc = " ".join(decor_descs)


class CmdPlace(MuxCommand):
    """
    Decorate a room with an object

    Usage:
        place <obj> [= position]

    Examples:
        place painting
        place painting = hanging from the south wall
    
    Placed objects will appear as part of the room's description instead of
    its contents.
    """

    key = "place"
    aliases = ("arrange",)
    help_category = "General"

    def func(self):
        """
        This performs the actual command.
        """
        caller = self.caller
        
        if not self.args:
            caller.msg("Usage: place <obj> [= position]")
            return

        obj = caller.search(self.lhs.strip())
        if not obj:
            return

        try:
            allow = obj.at_pre_place(caller, caller.location)
        except AttributeError:
            caller.msg("You can't decorate with that.")
            return
        
        if not allow:
            caller.msg("You can't decorate here.")
            return

        # set a positional string, or just put in the room
        if self.rhs:
            position = self.rhs.strip()
        else:
            position = True

        # This is where you can validate positional descriptions
        if len(self.rhs) > 50:
            caller.msg("Please keep your positional description below 50 characters.")

        # do the actual placement
        obj.place(caller, caller.location, position)


class DecorCmdSet(CmdSet):
    """
    Groups the extended basic commands.
    """

    def at_cmdset_creation(self):
        self.add(CmdPlace)
