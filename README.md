# Evennia Things
Modules and code snippets I've written, for [Evennia](https://evennia.com) v1.0

Anything here could most likely be backported to v0.9.5 but I wouldn't guarantee it.

### How to use
I try to set things up in here so they can either be used as-is or plugged into your existing game code. Check out the different modules for specifics.

I'm also going to add unit tests for everything in here eventually, but don't hold your breath.

### List of Things
* `basic_commands.py` - Extends the functionality of basic IC commands like `look` and `get`, mostly by adding inter-object functionality. e.g. "get A from B" to get an object from a container object.
* `clothing.py` - Initially based on the current clothing contrib, but rewritten for v1.0 updates and ease of customization. (Don't try backporting this one, just use the current contrib instead.) Like the contrib, it lets you wear objects and displays those objects as part of your character description, with support for covering up worn objects so they can't be seen and optional "worn as" strings appended to the clothing description.
* `growables.py` - Lets your objects change over time. Designed as a flexible handler, it should let you implement anything from growing crops, to aging animals, and even decaying corpses, by changing an object's attributes based on its age.
* `multimatch.py` - Provides an alternative multimatch system to the default of re-entering commands, by allowing commands to ask the player directly which of the matches they intended.
* `roomdecor.py` - Adds a mechanism for decorating rooms with objects. Decor items can be placed in different positions within the room and are displayed as part of room's `desc` section instead of as contents. They also retain any other functionality - usable items are usable, sittable items are sittable, etc.
