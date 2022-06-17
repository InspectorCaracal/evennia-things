"""
Testing clothing contrib

"""

from evennia.commands.default.tests import BaseEvenniaCommandTest
from evennia.utils.create import create_object
from evennia.objects.objects import DefaultRoom, DefaultObject
from evennia.utils.test_resources import BaseEvenniaTest
from . import clothing


class TestClothingCmd(BaseEvenniaCommandTest):
    def test_clothingcommands(self):
        wearer = create_object(clothing.ClothedCharacter, key="Wearer")
        friend = create_object(clothing.ClothedCharacter, key="Friend")
        room = create_object(DefaultRoom, key="room")
        wearer.location = room
        friend.location = room
        # Make a test hat
        test_hat = create_object(clothing.ContribClothing, key="test hat")
        test_hat.tags.add("hat", category="clothing")
        test_hat.location = wearer
        # Make a test scarf
        test_scarf = create_object(clothing.ContribClothing, key="test scarf")
        test_scarf.tags.add("accessory", category="clothing")
        test_scarf.location = wearer
        # Test wear command
        self.call(clothing.CmdWear(), "", "Usage: wear <obj> [= wear style]", caller=wearer)
        self.call(clothing.CmdWear(), "hat", "Wearer puts on a test hat.", caller=wearer)
        self.call(
            clothing.CmdWear(),
            "scarf = stylishly",
            "Wearer puts on a test scarf.",
            caller=wearer,
        )
        self.assertEqual(test_scarf.db.worn, "stylishly")
        # Test cover command.
        self.call(
            clothing.CmdCover(),
            "",
            "Usage: cover <worn clothing> with <clothing object>",
            caller=wearer,
        )
        self.call(
            clothing.CmdCover(),
            "hat with scarf",
            "Wearer covers a test hat with a test scarf.",
            caller=wearer,
        )
        # Test remove command.
        self.call(clothing.CmdRemove(), "", "Usage: remove <object>", caller=wearer)
        self.call(
            clothing.CmdRemove(), "hat", "You can't remove that, it's covered by your test scarf.", caller=wearer
        )
        self.call(
            clothing.CmdRemove(),
            "scarf",
            "Wearer removes a test scarf, revealing a test hat.",
            caller=wearer,
        )
        # Test uncover command.
        wearer.clothing.add(test_scarf,quiet=True)
        test_hat.db.covered_by = test_scarf
        self.call(clothing.CmdUncover(), "", "Usage: uncover <worn clothing object>", caller=wearer)
        self.call(clothing.CmdUncover(), "hat", "Wearer uncovers a test hat.", caller=wearer)
        # Test drop command.
        test_hat.db.covered_by = test_scarf
        self.call(clothing.CmdDrop(), "", "Drop what?", caller=wearer)
        self.call(
            clothing.CmdDrop(),
            "hat",
            "You can't remove that, it's covered by your test scarf.",
            caller=wearer,
        )
        self.call(clothing.CmdDrop(), "scarf", "Wearer removes a test scarf, revealing a test hat.|You drop a test scarf.", caller=wearer)
        # Test give command.
        self.call(
            clothing.CmdGive(), "", "Usage: give <object> to <target>", caller=wearer
        )
        self.call(
            clothing.CmdGive(),
            "hat to Friend",
            "Wearer removes a test hat.|You give a test hat to Friend.",
            caller=wearer,
        )
        # Test inventory command.
        self.call(
            clothing.CmdInventory(), "", "You are carrying:| Nothing.|You are wearing:| Nothing.", caller=wearer
        )


class TestClothingHandler(BaseEvenniaCommandTest):
    def test_clothinghandler(self):
        wearer = create_object(clothing.ClothedCharacter, key="Wearer")
        room = create_object(DefaultRoom, key="room")
        wearer.location = room

        # Make a test shirt
        test_shirt = create_object(clothing.ContribClothing, key="test shirt", attributes=[("desc", "An ordinary shirt.")])
        test_shirt.tags.add("top", category="clothing")
        test_shirt.location = wearer
        # Make a test pants
        test_pants = create_object(clothing.ContribClothing, key="test pants", attributes=[("desc", "A pair of pants.")])
        test_pants.tags.add("bottom", category="clothing")
        test_pants.location = wearer
        # Make a test accessory
        test_ring = create_object(DefaultObject, key="test ring", attributes=[("desc", "A normal ring.")])
        test_ring.tags.add("jewelry", category="clothing")
        test_ring.location = wearer
        
        # add - adds to list, optionally sets worn style
        self.assertEqual(wearer.clothing.add(test_shirt),"Wearer puts on a test shirt.")
        self.assertEqual(wearer.clothing.add(test_shirt,"hanging loosely"),"Wearer adjusts a test shirt.")
        self.assertEqual(test_shirt.db.worn,"hanging loosely")
        
        # can_add - checks if item is wearable
        self.assertEqual(wearer.clothing.can_add(test_ring), True)

        wearer.clothing.add(test_pants)
        
        # can_cover - checks if item is worn and covering item can cover things
        self.assertEqual(wearer.clothing.can_cover(test_pants, test_shirt), True)
        self.assertEqual(wearer.clothing.can_cover(test_pants, test_ring), False)

        # can_remove - checks if item is worn and not covered
        test_pants.db.covered_by = test_shirt
        self.assertEqual(wearer.clothing.can_remove(test_pants), False)
        self.assertEqual(wearer.clothing.can_remove(test_shirt), True)
        self.assertEqual(wearer.clothing.can_remove(test_ring), False)
        
        wearer.clothing.add(test_ring)
        
        # all - return list of objects
        self.assertEqual(wearer.clothing.all, [test_shirt, test_pants, test_ring])

        # visible - return list of objects not covered
        self.assertEqual(wearer.clothing.visible, [test_shirt, test_ring])

        # get_outfit - returns sorted list of descriptions of visible worn items
        self.assertEqual(wearer.clothing.get_outfit(),["a test ring", "an ordinary shirt hanging loosely"])
        test_pants.db.covered_by = None
        self.assertEqual(wearer.clothing.get_outfit(),["a test ring", "an ordinary shirt hanging loosely", "a pair of pants"])
        
        # remove - removes from list, clears wear style, uncovers things
        wearer.clothing.remove(test_shirt)
        self.assertEqual(test_pants.db.covered_by, None)
        self.assertEqual(test_shirt.db.worn, None)
        self.assertEqual(wearer.clothing.all, [test_pants, test_ring])

        # count_type - returns an int of items worn of that type
        self.assertEqual(wearer.clothing.count_type("jewelry"), 1)

        # clear - silently removes all objects
        wearer.clothing.clear()
        self.assertEqual(wearer.clothing.all, [])


class TestClothingFunc(BaseEvenniaTest):
    def test_clothingfunctions(self):
        wearer = create_object(clothing.ClothedCharacter, key="Wearer")
        room = create_object(DefaultRoom, key="room")
        wearer.location = room
        # Make a test hat
        test_hat = create_object(clothing.ContribClothing, key="test hat", attributes=[("desc", "A normal hat.")])
        test_hat.tags.add("hat", category="clothing")
        test_hat.location = wearer

        self.assertEqual(test_hat.get_worn_desc(), "a normal hat")
        self.assertEqual(test_hat.get_extra_info(wearer), " (carried)")

        wearer.clothing.add(test_hat, "on the head")
        self.assertEqual(test_hat.get_worn_desc(), "a normal hat on the head")
        self.assertEqual(test_hat.get_extra_info(wearer), " (worn)")
