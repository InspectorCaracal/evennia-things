"""
A handler for managing the development/growth of an object over time.

Use by attaching to your object class as a lazy property, e.g.

```
@lazy_property
def growth(self):
    return GrowthHandler(self)
```

You can optionally add an `at_pre_grow` hook to set limitations on whether or not
the object can increment its age.

To actually allow the object to change, set growth stages via the `add` method.

```
self.add("sprout", 1200, key="seedling", desc="A tiny seedling, just barely sprouted.")
self.add("young", 1200, key="small plant", desc="This plant is small but still growing.", leaves=True)
```

A name for the growth stage and an age (in seconds of game time) are required;
any other keys are optional and will by default be assigned as object attributes.
It does support callable hooks, however: pass the callable name as the keyword
and a single arg or list of args as the value.

e.g. if your object has a method `at_grow(self, stage)` you can have it trigger like so
```
self.add("sprout", 1200, key="seedling", desc="A tiny seedling, just barely sprouted.", at_grow="sprout")
```
Note: I haven't tested the callable functionality, but it should work.
"""

from evennia.utils import gametime, delay


class GrowthHandler():
    """
    Tracks an objects age and change over time.
    """

    def __init__(self, obj, interval=36000):
        """
        Initialize the handler.
        """
        self.obj = obj
        self.delay = interval

        # load existing growth stage dict or initialize
        self.growth_stages = obj.attributes.get("stages", category="growth")
        if not self.growth_stages:
            obj.attributes.add("stages", {}, category="growth")
            self.growth_stages = obj.attributes.get("stages", category="growth")

        # load existing object status or initialize
        self.growth_status = obj.attributes.get("status", category="growth")
        if not self.growth_status:
            init_status = {
                    "last_update": gametime.gametime(),
                    "stage": None,
                    "age": 0,
                    "next_age": 0
                }
            obj.attributes.add("status", init_status, category="growth")
            self.growth_status = obj.attributes.get("status", category="growth")

        # run grow to initialize and schedule next growth
        self.grow()

    def all(self):
        return self.growth_stages.keys()

    @property
    def current(self):
        return self.growth_status['stage']

    def grow(self, force=False):
        """
        Tells the owner object to "grow", i.e. update attributes to match its
        age to the correct growth stage. By default, it does nothing if the
        current stage matches the new stage; however, setting `force=True`
        will tell it to re-apply the attributes.
        """
        current_update = gametime.gametime() 
        last_update = self.growth_status['last_update']
        if current_update - last_update < self.delay and not force:
            return

        if len(self.growth_stages) <= 0:
            # no stages added yet, reschedule
            delay(self.delay, self.grow)
            return

        grower = self.obj
        try:
            if not grower.at_pre_grow():
                # set delayed task for next growth
                delay(self.delay, self.grow)
                return
        except AttributeError:
            # continue with the growth if pre-check isn't implemented
            pass

        current_stage = self.growth_status['stage']
        current_age = (current_update - self.growth_status['last_update']) + self.growth_status['age']
        next_age = self.growth_status['next_age']

        last_stage = list(self.growth_stages)[-1]
        if current_stage == last_stage and not force:
            # done growing! don't reschedule
            return

        if current_age < next_age and not force:
            self.growth_status['age'] = current_age
            # set delayed task for next growth
            delay(self.delay, self.grow)
            return

        # time to age up!
        base_age = 0
        new_stage = None
        # iterate through the growth stages to find the new stage and next age point
        for stage, value in self.growth_stages.items():
            if current_age < value['age']:
                next_age = value['age']
                break
            elif base_age <= value['age']:
                base_age = value['age']
                new_stage = stage

        if not new_stage:
            # it couldn't find a new stage for some reason, try again later
            delay(self.delay, self.grow)
            return

        # update object attributes
        stage_dict = dict(self.growth_stages[new_stage])
        # pop age because it isn't used
        stage_dict.pop('age')
        # pop key to handle None
        new_key = stage_dict.pop('key')
        if new_key:
            grower.key = new_key
        # pop desc to handle None
        new_desc = stage_dict.pop('desc')
        if new_desc:
            grower.attributes.add('desc', new_desc)

        # go through all the rest of the items and set as attributes
        for attr, value in stage_dict.items():
            if hasattr(grower, attr):
                obj_attr = getattr(grower, attr)
                # you can use this to call a hook instead of set an attribute
                # it does not support kwargs because i don't feel like it
                if callable(obj_attr):
                    if type(value) is list:
                        # pass list as separate args
                        obj_attr(*value)
                    else:
                        # pass value as single arg
                        obj_attr(value)
                # not a callable, just set the attribute
                else:
                    setattr(grower, attr, value)
            # not a class attribute, set the db attr
            else:
                grower.attributes.add(attr, value)

        # set delayed task for next growth
        delay(self.delay, self.grow)

        self.growth_status['last_update'] = current_update
        self.growth_status['age'] = current_age
        self.growth_status['next_age'] = next_age
        self.growth_status['stage'] = new_stage


    def add(self, stage, age, key=None, desc=None, force_add=False, **kwargs):
        # check if stage already exists and abort if not set to override
        if stage in self.growth_stages and not force_add:
            return
        stages = self.growth_stages
        stages[stage] = { "age": age, "key": key, "desc": desc }
        # add additional keywords to dict for later attributes
        for key, value in kwargs.items():
            stages[stage][key] = value

        # sort stages by age order
        self.growth_stages = dict(sorted(stages.items(), key=lambda item: item[1]['age']))
        # update growth stage attributes in case the new one should apply
        self.grow(force=True)

    def remove(self, stage):
        popped = self.growth_stages.pop(stage, None)
        # update growth stage attributes, in case the removed stage is current
        if popped:
            self.grow(force=True)

