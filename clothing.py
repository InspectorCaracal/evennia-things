"""
Updated Clothing module, based on the Clothing contrib by Tim Ashley Jenkins

## How To Use

1. Inherit from `ClothedCharacter` on your main character class, or reference the code
below to add the functionality yourself.
    Note: `ClothedCharacter` adds the clothing handler attribute for managing worn
        items, and modifies two of the hooks involved in returning character appearance
        to display worn vs carried items.
2. Add the `ClothingCmdSet` to your default CharacterCmdSet
3. Update your settings as needed. (An overview of options is further down.)

To make an item wearable, add any tag to it with the "clothing" category. The tag you set
will define what type of clothing it is, for sorting and other limitations. You can also
inherit from the `ContribClothing` class below for additional functionality, which is recommended
for actual clothing items and anything which should have visible detail when worn.
    Note: The tag category for wearable items is configurable in settings.


## Example

Let's say you've set up the module for your `Character` class with all the default settings,
and you're starting off with a simple object.

> create wrist watch = A simple clock face on a leather band.

The new `wrist watch` is your default object class (probably Object) and has no tags. If
you try to wear it, it won't let you.

To make it a simple wearable watch, add a clothing tag to it.

> tag wrist watch = accessory:clothing
> wear wrist watch

Looking at your character (e.g. Monty), you'll see the following in your description:
    `Monty is wearing a wrist watch.`

Now change the type of your wrist watch to the `ContribClothing` typeclass. Assuming the module
is in your `world` dir:

> type wrist watch = world.clothing.ContribClothing

Looking at your character will now show more detail on the worn watch:
    `Monty is wearing a simple clock face on a leather band.`


## Options

Several options can be defined in `settings.py` to modify how the module works.

CLOTHING_TAG_CATEGORY (str)
    - Change the tag category for tagging objects as wearable.
CLOTHING_WORNSTRING_MAX_LENGTH (int)
    - Players can optionally set a string describing how or where they are wearing an item.
      Set the maximum number of characters for these descriptions here, or None to disable.
CLOTHING_TYPE_ORDER (list)
    - Defines which clothing types are displayed in what order when worn. Any types not in
      the list will be left unsorted at the end. Set to None to disable
CLOTHING_TOTAL_LIMIT (int)
    - The maximum number of items that a character can wear. Set to None for unlimited.
CLOTHING_TYPE_LIMITS (dict)
    - Sets the maximum number of a particular type of clothing that a character can wear.
      Any types not present as keys will only be limited by the total item limit.
CLOTHING_AUTOCOVER_TYPES (dict of lists)
    - Sets  which types of clothing will automatically cover which other, already-worn types
      of clothing. See the default for how to structure.
CLOTHING_NO_COVER_TYPES (list)
    - Sets which types of clothing can't be used to cover things. 


The default values are viewable at the beginning of the module.
"""

from collections import defaultdict
from django.conf import settings

from evennia import DefaultCharacter, DefaultObject
from evennia.commands.cmdset import CmdSet
from evennia.commands.default.muxcommand import MuxCommand
from evennia.utils.evtable import EvTable, EvColumn
from evennia.utils import list_to_string, lazy_property

import inflect
_INFLECT = inflect.engine()


########### Default settings ###########

_CLOTHING_TAG_CATEGORY = "clothing"

# Maximum character length of 'wear style' strings, or None to disable.
_WORNSTRING_MAX_LENGTH = 50

# Display order for different clothing types, or None to disable.
# Any types not in the list will be unsorted at the end, but still visible.
_CLOTHING_TYPE_ORDER = [
    "hat",
    "jewelry",
    "top",
    "undershirt",
    "gloves",
    "fullbody",
    "bottom",
    "underpants",
    "socks",
    "shoes",
    "accessory",
]

# The maximum number of each type of clothes that can be worn.
# Any types not specified are not limited.
_CLOTHING_TYPE_LIMITS = {"hat": 1, "gloves": 1, "socks": 1, "shoes": 1}

# The maximum number of clothing items that can be worn, or None for unlimited.
_CLOTHING_TOTAL_LIMIT = 20

# What types will automatically cover what other types of clothes when worn.
# Note: clothing can only auto-cover other clothing that is already being worn.
_CLOTHING_AUTOCOVER_TYPES = {
    "top": ["undershirt"],
    "bottom": ["underpants"],
    "fullbody": ["undershirt", "underpants"],
    "shoes": ["socks"],
}
# Types that can't be used to cover other clothes.
_CLOTHING_NO_COVER_TYPES = ["jewelry"]


# Override defaults if defined in settings
if hasattr(settings, "CLOTHING_TAG_CATEGORY"):
    _CLOTHING_TAG_CATEGORY = settings.CLOTHING_TAG_CATEGORY
if hasattr(settings, "CLOTHING_WORNSTRING_MAX_LENGTH"):
    _WORNSTRING_MAX_LENGTH = settings.CLOTHING_WORNSTRING_MAX_LENGTH
if hasattr(settings, "CLOTHING_TYPE_ORDER"):
    _CLOTHING_TYPE_ORDER = settings.CLOTHING_TYPE_ORDER
if hasattr(settings, "CLOTHING_TOTAL_LIMIT"):
    _CLOTHING_TOTAL_LIMIT = settings.CLOTHING_TOTAL_LIMIT
if hasattr(settings, "CLOTHING_TYPE_LIMITS"):
    _CLOTHING_TYPE_LIMITS = settings.CLOTHING_TYPE_LIMITS
if hasattr(settings, "CLOTHING_AUTOCOVER_TYPES"):
    _CLOTHING_AUTOCOVER_TYPES = settings.CLOTHING_AUTOCOVER_TYPES
if hasattr(settings, "CLOTHING_NO_COVER_TYPES"):
    _CLOTHING_NO_COVER_TYPES = settings.CLOTHING_NO_COVER_TYPES



class ClothingHandler():
    """
    Tracks a character's worn objects and visible outfit.
    """

    def __init__(self, obj, db_attr_key="clothing", db_attr_cat="clothing"):
        """
        Initialize the handler.
        """
        self.clothing_list = obj.attributes.get(db_attr_key, category=db_attr_cat)
        self.wearer = obj
        if not self.clothing_list:
            obj.attributes.add(db_attr_key, [], category=db_attr_cat)
            self.clothing_list = obj.attributes.get(db_attr_key, category=db_attr_cat)
    
    @property
    def all(self):
        return list(self.clothing_list)

    @property
    def visible(self):
        return [obj for obj in self.clothing_list if not obj.db.covered_by ]
    
    def add(self, obj, style=None, quiet=False):
        """Wears an object on the character, optionally in a particular style."""
        # check if new or adjusting
        if obj in self.clothing_list:
            adjust = True
        else:
            adjust = False
            self.clothing_list.append(obj)

        # Set clothing pose
        obj.db.worn = style

        # Auto-cover appropirate clothing types, as specified above
        to_cover = []
        if not adjust and True in obj.tags.has(_CLOTHING_AUTOCOVER_TYPES.keys(), category=_CLOTHING_TAG_CATEGORY, return_list=True):
            tags = []
            for key in obj.tags.get(category=_CLOTHING_TAG_CATEGORY, return_list="true"):
                tags += _CLOTHING_AUTOCOVER_TYPES[key]
            outfit_list = [obj for obj in self.clothing_list if not obj.db.covered_by]
            for garment in outfit_list:
                if True in garment.tags.has(tags, category=_CLOTHING_TAG_CATEGORY, return_list=True):
                    to_cover.append(_INFLECT.an(garment.name))
                    garment.db.covered_by = obj
        # Return nothing if quiet
        if quiet:
            message = None
        # Return a message to echo if otherwise
        else:
            # Echo a message to the room
            if adjust:
                message = "adjusts %s" % _INFLECT.an(obj.name)
            else:
                message = "puts on %s" % _INFLECT.an(obj.name)
            if to_cover:
                message += ", covering %s" % list_to_string(to_cover)
            message = f"{self.wearer.name} {message}."
        
        return message
    
    def remove(self, obj, quiet=False):
        """Removes worn clothes and optionally echoes to the room."""
        obj.db.worn = None
        obj.db.covered_by = None
        clothing = self.clothing_list
        self.clothing_list.remove(obj)
#        self._set(clothing)

        uncovered_list = []
        # Check to see if any other clothes are covered by this object.
        for thing in self.clothing_list:
            # If anything is covered by
            if thing.db.covered_by == obj:
                thing.db.covered_by = None
                uncovered_list.append(_INFLECT.an(thing.name))
        
        if quiet:
            message = None
        
        else:
            message = "removes %s" % _INFLECT.an(obj.name)
            if uncovered_list:
                message += ", revealing %s" % list_to_string(uncovered_list)
            message = f"{self.wearer.name} {message}."
            
        return message
        
    def clear(self):
        for obj in list(self.clothing_list):
            obj.db.worn = None
            obj.db.covered_by = None
            self.clothing_list.remove(obj)

    def can_add(self, obj):
        """
        Checks whether the object can be worn.
        """
        clothing_type = obj.tags.get(category=_CLOTHING_TAG_CATEGORY)
        if not clothing_type:
            self.wearer.msg("You can't wear that.")
            return False

        # Enforce overall clothing limit.
        if _CLOTHING_TOTAL_LIMIT and len(self.clothing_list) >= _CLOTHING_TOTAL_LIMIT:
            self.wearer.msg("You can't wear anything else.")
            return False
        
        if clothing_type in _CLOTHING_TYPE_LIMITS:
            if self.count_type(clothing_type) >= _CLOTHING_TYPE_LIMITS[clothing_type]:
                self.wearer.msg("You can't wear any more of those.")
                return False

        return True

    def can_remove(self, obj):
        if obj not in self.clothing_list:
            self.wearer.msg("You're not wearing that.")
            return False
        if obj.db.covered_by:
            self.wearer.msg("You can't remove that, it's covered by your %s." % obj.db.covered_by.get_display_name(self.wearer))
            return False
        
        return True

    def can_cover(self, to_cover, cover_with):
        # check if clothing already covered
        if to_cover.db.covered_by:
            caller.msg("Your %s is already covered by %s." % (to_cover.name, _INFLECT.an(to_cover.db.covered_by.name)))
            return False

        # check if the covering item can cover things
        if not cover_with.tags.has(category=_CLOTHING_TAG_CATEGORY):
            self.wearer.msg("Your %s isn't clothes." % cover_with.get_display_name(caller))
            return False
        if True in cover_with.tags.has(_CLOTHING_NO_COVER_TYPES, category=_CLOTHING_TAG_CATEGORY, return_list=True):
            self.wearer.msg("You can't cover anything with %s." % _INFLECT.an(cover_with.name))
            return False
        if to_cover == cover_with:
            self.wearer.msg("You can't cover an item with itself.")
            return False
        if cover_with.db.covered_by:
            self.caller.msg("Your %s is covered by %s." % (cover_with.name, _INFLECT.an(cover_with.db.covered_by.name)))
            return False

        return True

    def count_type(self, type):
        count = 0
        for obj in self.clothing_list:
            if obj.tags.has(type, category=_CLOTHING_TAG_CATEGORY):
                count += 1
        
        return count
    
    def get_outfit(self, sorted=True):
        """
        Returns the appearance of all worn and visible clothing items.
        
        Args:
            sorted (bool): Whether or not the resulting list is sorted by _LAYERS_ORDER
        
        Returns:
            list of strings
        """
        # sort the worn objects by the order options
        if sorted and _CLOTHING_TYPE_ORDER:
            obj_dict = {}
            extra = []
            for obj in self.visible:
                # separate visible clothing by type, for sorting
                type = obj.tags.get(category=_CLOTHING_TAG_CATEGORY)
                if type in _CLOTHING_TYPE_ORDER:
                    if type in obj_dict:
                        obj_dict[type].append(obj)
                    else:
                        obj_dict[type] = [obj]
                else:
                    extra.append(obj)
            obj_list = []
            # add the clothing objects in the type order
            for type in _CLOTHING_TYPE_ORDER:
                if type in obj_dict:
                    obj_list += obj_dict[type]
            # anything not specified in the order list goes at the end
            obj_list += extra
        else:
            obj_list = self.visible
        # get the actual appearances
        appearance_list = []
        for obj in obj_list:
            try:
                appearance = obj.get_worn_desc()
            except:
                # fallback to allow other classes of objects to be worn
                appearance = _INFLECT.an(obj.key)
            appearance_list.append(appearance)
        
        return appearance_list
        
        

class ClothedCharacter(DefaultCharacter):
    """
    Typeclass for clothing-aware characters.
    
    Overloads base `return_appearance` hooks to include worn clothing, and adds
    a handler to manage wearables.
    """
    # Define a new appearance template to better display clothing.
    # RECOMMENDATION: Set up the funcparser and use $pron instead of {name}
    appearance_template = """
{header}
|c{name}|n
{desc}

{name} is wearing {clothing}.

{name} is carrying {things}.
{footer}
    """

    @lazy_property
    def clothing(self):
        return ClothingHandler(self)

    def get_visible_contents(self, looker, **kwargs):
        # filter out items that are being worn, since they're handled separately
        def filter_visible(obj_list):
            return [obj for obj in obj_list if obj != looker and obj.access(looker, "view") and not obj in self.clothing.all]

        return {
            "exits": filter_visible(self.contents_get(content_type="exit")),
            "characters": filter_visible(self.contents_get(content_type="character")),
            "things": filter_visible(self.contents_get(content_type="object")),
        }

    def return_appearance(self, looker, **kwargs):
        if not looker:
            return ""

        name = self.get_display_name(looker, **kwargs)
        desc = self.db.desc

        # contents
        content_names_map = self.get_content_names(looker, **kwargs)
        exits = list_to_string(content_names_map["exits"])
        characters = list_to_string(content_names_map["characters"])
        things = list_to_string(content_names_map["things"])
        # adds the worn outfit separately
        clothing = list_to_string(self.clothing.get_outfit())

        return self.appearance_template.format(
            header="",
            name=name,
            desc=desc,
            clothing=clothing if clothing else "nothing",
            characters=characters,
            things=things if things else "nothing",
            footer="",
        ).strip()


class ContribClothing(DefaultObject):
    def get_worn_desc(self):
        description = self.db.desc[0].lower() + self.db.desc[1:] if len(self.db.desc) > 1 else self.db.desc.lower()
        if description[-1] in [".","!","?"]:
            description = description[:-1]
        # append worn style
        description = f"{description} {self.db.worn}" if self.db.worn else description
        return description
    
   
    def get_extra_info(self, looker, **kwargs):
        if self.location == looker:
            if self in looker.clothing.all:
                return " (worn)"
            return " (carried)"
        return ""


# COMMANDS START HERE

class CmdWear(MuxCommand):
    """
    Puts on an item of clothing you are holding.

    Usage:
        wear <obj> [= wear style]

    Examples:
        wear shirt
        wear scarf = wrapped loosely about the shoulders

    All the clothes you are wearing are appended to your description.
    If you provide a 'wear style' after the command, the message you
    provide will be displayed after the clothing's name.
    """

    key = "wear"
    help_category = "Clothing"

    def func(self):
        """
        This performs the actual command.
        """
        caller = self.caller
        
        if not self.args:
            if _WORNSTRING_MAX_LENGTH:
                caller.msg("Usage: wear <obj> [= wear style]")
            else:
                caller.msg("Usage: wear <obj>")
            return

        obj = caller.search(self.lhs, candidates=caller.contents)
        if not obj:
            return

        if obj in caller.clothing.all and not self.rhs:
            caller.msg("You're already wearing that.")
            return

        if self.rhs and _WORNSTRING_MAX_LENGTH:
            # If length of wearstyle exceeds limit
            if len(self.rhs) > _WORNSTRING_MAX_LENGTH:
                caller.msg(
                    "Please keep your wear style message to less than %i characters."
                    % _WORNSTRING_MAX_LENGTH
                )
                return
        elif not _WORNSTRING_MAX_LENGTH:
            self.rhs = None

        if caller.clothing.can_add(obj):
            msg = caller.clothing.add(obj, style=self.rhs)
            if msg:
                caller.location.msg_contents(msg)


class CmdRemove(MuxCommand):
    """
    Takes off an item of clothing.

    Usage:
         remove <obj>

    Removes an item of clothing you are wearing. You can't remove clothes
    that are being covered by something else.
    """

    key = "remove"
    help_category = "Clothing"

    def func(self):
        """
        This performs the actual command.
        """
        caller = self.caller

        if not self.args:
            caller.msg("Usage: remove <object>")
            return
        
        obj = caller.search(self.args.strip(), candidates=caller.contents)
        if not obj:
            return

        if caller.clothing.can_remove(obj):
            msg = caller.clothing.remove(obj)
            if msg:
                caller.location.msg_contents(msg)


class CmdCover(MuxCommand):
    """
    Covers a worn item of clothing with another you're holding or wearing.

    Usage:
        cover <obj> with <obj>

    When you cover a clothing item, it is hidden and no longer appears in
    your description until it's uncovered or the item covering it is removed.
    You can't remove an item of clothing if it's covered.
    """

    key = "cover"
    help_category = "clothing"
    rhs_split = (" with ",)

    def func(self):
        """
        This performs the actual command.
        """

        caller = self.caller
        if not self.rhs or not self.lhs:
            self.caller.msg("Usage: cover <worn clothing> with <clothing object>")
            return

        argslist = [ self.lhs, self.rhs ]
        objs = []
        
        for arg in argslist:
            obj = caller.search(arg, candidates=caller.contents)
            if not obj:
                return
            else:
                objs.append(obj)

        to_cover = objs[0]
        cover_with = objs[1]

        if to_cover not in caller.clothing.all:
            caller.msg("You're not wearing %s." % _INFLECT.an(to_cover.name))
            return
        
        if caller.clothing.can_cover(to_cover, cover_with):
            to_cover.db.covered_by = cover_with
            message = f"{caller.name} covers {_INFLECT.an(to_cover.name)} with {_INFLECT.an(cover_with.name)}."
            if cover_with not in caller.clothing.all:
                caller.clothing.add(cover_with, quiet=True )  # Put on the item to cover with if it's not on already

            caller.location.msg_contents(message)


class CmdUncover(MuxCommand):
    """
    Reveals a worn item of clothing that's currently covered up.

    Usage:
        uncover <obj>

    When you uncover an item of clothing, you allow it to appear in your
    description without having to take off the garment that's currently
    covering it. You can't uncover an item of clothing if the item covering
    it is also covered by something else.
    """

    key = "uncover"
    help_category = "clothing"

    def func(self):
        """
        This performs the actual command.
        """
        caller = self.caller
        if not self.args:
            caller.msg("Usage: uncover <worn clothing object>")
            return
        target = self.args.strip()
        obj = caller.search(target, candidates=caller.contents)
        if not obj:
            return

        if obj not in caller.clothing.all:
            caller.msg("You're not wearing %s." % _INFLECT.an(obj.name))
            return
        covered_by = obj.db.covered_by
        if not covered_by:
            caller.msg("Your %s isn't covered by anything." % obj.name)
            return
        if covered_by.db.covered_by:
            caller.msg("Your %s is under too many layers to uncover." % (obj.name))
            return
        message = "{name} uncovers {clothing}.".format(name=caller.name, clothing=_INFLECT.an(obj.name))
        caller.location.msg_contents(message)
        obj.db.covered_by = None


class CmdInventory(MuxCommand):
    """
    view inventory

    Usage:
        inventory
        inv

    Shows your inventory.
    """

    # Alternate version of the inventory command which separates
    # worn and carried items.

    key = "inventory"
    aliases = ["inv", "i"]
    locks = "cmd:all()"
    arg_regex = r"$"

    def func(self):
        """check inventory"""
        caller = self.caller

        clothing = caller.clothing.all
        carried = [obj for obj in caller.contents if obj not in clothing]
        
        def _fill_columns(obj_list):
            cols_list = []
            if len(obj_list) > 10:
                if len(obj_list) < 20:
                    cols_list.append(EvColumn(*obj_list[:10]))
                    cols_list.append(EvColumn(*obj_list[10:]))

                else:
                    split = int(len(obj_list)/2)
                    cols_list.append(EvColumn(*obj_list[:split]))
                    cols_list.append(EvColumn(*obj_list[split:]))

            else:
                cols_list.append(EvColumn(*obj_list))
            
            return cols_list

        # build carried inventory
        if len(carried) > 0:
            # group all same-named things under one name
            carried_dict = defaultdict(list)
            for thing in carried:
                carried_dict[thing.get_display_name(caller)].append(thing)

            # pluralize same-named things
            carried_names = []
            for thingname, thinglist in sorted(carried_dict.items()):
                nthings = len(thinglist)
                thing = thinglist[0]
                singular, plural = thing.get_numbered_name(nthings, caller, key=thingname)
                carried_names.append(singular if nthings == 1 else plural)
            carried_names = ["%s" % name for name in carried_names]

            carry_col_list = _fill_columns(carried_names)
            carry_table = EvTable(table = carry_col_list, border="none")
        else:
            carry_table = " Nothing."

        # build worn inventory
        if len(clothing) > 0:
            clothing_names = ["|C%s|n%s" % (_INFLECT.an(item.get_display_name(caller)), " (hidden)" if item.db.covered_by else "") for item in clothing]
            clothing_col_list = _fill_columns(clothing_names)
            clothing_table = EvTable(table = clothing_col_list, border="none")
        else:
            clothing_table = " Nothing."

        # output to caller
        caller.msg("|cYou are carrying:|n")
        caller.msg(carry_table)
        caller.msg("|cYou are wearing:|n")
        caller.msg(clothing_table)

class CmdDrop(MuxCommand):
    """
    drop something

    Usage:
      drop <obj>

    Lets you drop an object from your inventory into the
    location you are currently in.
    """

    key = "drop"
    locks = "cmd:all()"
    arg_regex = r"\s|$"

    def func(self):
        """Implement command"""

        caller = self.caller
        if not self.args:
            caller.msg("Drop what?")
            return

        obj = caller.search(
            self.args,
            location=caller,
            nofound_string="You aren't carrying any %s." % self.args,
            multimatch_string="You carry more than one %s:" % self.args,
        )
        if not obj:
            return

        if obj in caller.clothing.all:
            if not caller.clothing.can_remove(obj):
                return
            remove_msg = caller.clothing.remove(obj)
            caller.location.msg_contents(remove_msg)

        obj.move_to(caller.location, quiet=True)
        caller.msg("You drop %s." % _INFLECT.an(obj.name) )
        caller.location.msg_contents("%s drops %s." % (caller.name, _INFLECT.an(obj.name)), exclude=caller)
        obj.at_drop(caller)


class CmdGive(MuxCommand):
    """
    give away something to someone
    Usage:
      give <inventory obj> = <target>
    Gives an items from your inventory to another character,
    placing it in their inventory.
    """

    key = "give"
    locks = "cmd:all()"
    rhs_split = (" to ","=")
    arg_regex = r"\s|$"

    def func(self):
        """Implement give"""

        caller = self.caller
        if not self.args or not self.rhs:
            caller.msg("Usage: give <object> to <target>")
            return

        obj = caller.search(
            self.lhs,
            location=caller,
            nofound_string="You aren't carrying %s." % self.lhs,
            multimatch_string="You carry more than one %s:" % self.lhs,
        )
        if not obj:
            return
        target = caller.search(self.rhs)
        if not target:
            return
        if target == caller:
            caller.msg("You keep %s to yourself." % obj.key)
            return
        if not obj.location == caller:
            caller.msg("You are not holding %s." % obj.key)
            return

        if obj in caller.clothing.all:
            if not caller.clothing.can_remove(obj):
                return
            remove_msg = caller.clothing.remove(obj)
            caller.location.msg_contents(remove_msg)

        caller.msg("You give %s to %s." % (_INFLECT.an(obj.key), target.key))
        obj.move_to(target, quiet=True)
        target.msg("%s gives you %s." % (caller.key, _INFLECT.an(obj.key)))
        # Call the object's at_give() method.
        obj.at_give(caller, target)


class ClothedCharacterCmdSet(CmdSet):
    """
    Command set for managing worn clothing, including an adapted version of
    `inventory` that separates carried vs worn items.
    """

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #
        self.add(CmdWear())
        self.add(CmdRemove())
        self.add(CmdCover())
        self.add(CmdUncover())
        self.add(CmdInventory())
        self.add(CmdDrop())
        self.add(CmdGive())
