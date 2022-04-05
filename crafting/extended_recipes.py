"""
Crafting Contrib extensions

This module adds multiple CraftingRecipe classes that allow for more
input-aware crafting systems.

The `QuantityCraftingRecipe` class extends the base `CraftingRecipe`
to allow for using "part" of an object as a crafting ingredient,
instead of the entire object.

The `VariableCraftingRecipe` class extends the base `CraftingRecipe`
to adjust the output object to match input materials.

If you want to inherit from both, you can - just make sure that
`QuantityCraftingRecipe` comes first, since its `post_craft` method
needs to take preceence.
"""

from evennia import DefaultObject
from evennia.utils import list_to_string, inherits_from
from evennia.prototypes.spawner import spawn
from evennia.contrib.game_systems.crafting.crafting import CraftingRecipe,CraftingValidationError

class QuantityCraftingRecipe(CraftingRecipe):
    """
    Rather than either consuming or not-consuming an entire object, this
    type of crafting recipe can use "part" of an object by reducing its
    size attribute by the amount defined.
    
    Example:
        ```python
        # Use one "fabric" ingredient and one "thread" ingredient
        consumable_tags = ["fabric", "thread"]
        # Use two units of the fabric and one unit of the thread
        consumable_sizes = [2, 1]
        ```
    
    NOTE:
        This recipe expects your material objects to have a `size` attribute
        for identifying the quantity, and a `resize` attributes for changing
        the size.

    This is most useful for materials which it doesn't make sense to use
    all of on one project, e.g. spools of thread.
        
    """
    def pre_craft(self, **kwargs):
        """
        Do pre-craft checks, including input validation.
        Make sure the given inputs are what is needed.
        Validated data is stored as lists on `.validated_tools`,
        `.validated_consumables` and `.validated_quantities`

        Args:
            **kwargs: Any optional extra kwargs passed during initialization of
                the recipe class.

        Raises:
            CraftingValidationError: If validation fails. At this point the crafter
                is expected to have been informed of the problem already.
        """

        def _check_tools(
            tagmap,
            taglist,
            namelist,
            exact_match,
            exact_order,
            error_missing_message,
            error_order_message,
            error_excess_message,
        ):
            """Compare tagmap (inputs) to taglist (required)"""
            valids = []
            for itag, tagkey in enumerate(taglist):
                found_obj = None
                for obj, objtags in tagmap.items():
                    if tagkey in objtags:
                        found_obj = obj
                        break
                    if exact_order:
                        # if we get here order is wrong
                        err = self._format_message(
                            error_order_message, missing=obj.get_display_name(looker=self.crafter)
                        )
                        self.crafter.msg(err)
                        raise CraftingValidationError(err)

                # since we pop from the mapping, it gets ever shorter
                match = tagmap.pop(found_obj, None)
                if match:
                    valids.append(found_obj)
                elif exact_match:
                    err = self._format_message(
                        error_missing_message,
                        missing=namelist[itag] if namelist else tagkey.capitalize(),
                    )
                    self.crafter.msg(err)
                    raise CraftingValidationError(err)

            if exact_match and tagmap:
                # something is left in tagmap, that means it was never popped and
                # thus this is not an exact match
                err = self._format_message(
                    error_excess_message,
                    excess=[obj.get_display_name(looker=self.crafter) for obj in tagmap],
                )
                self.crafter.msg(err)
                raise CraftingValidationError(err)

            return valids

        def _check_ingredients(
            tagmap,
            taglist,
            namelist,
            quantities,
            exact_match,
            exact_order,
            error_missing_message,
            error_order_message,
            error_excess_message,
        ):
            """Compare tagmap (inputs) to taglist (required)"""
            valids = []
            quants = []
            quantity_list = quantities
            for itag, tagkey in enumerate(taglist):
                found_objs = []
                for obj, objtags in tagmap.items():
                    if tagkey in objtags:
                        if obj.size >= quantity_list[itag]:
                            found_objs.append((obj,quantity_list[itag]))
                            quantity_list[itag] = 0
                            break
                        else:
                            found_objs.append((obj,obj.size))
                            quantity_list[itag] -= obj.size
                            continue
                    if exact_order:
                        # if we get here order is wrong
                        err = self._format_message(
                            error_order_message, missing=obj.get_display_name(looker=self.crafter)
                        )
                        self.crafter.msg(err)
                        raise CraftingValidationError(err)

                # since we pop from the mapping, it gets ever shorter
                
                # objects matching tags were found
                if found_objs:
                    # if the quantity is still above zero, inputs weren't enough
                    if quantity_list[itag] > 0:
                        err = self._format_message(
                            error_missing_message,
                            missing=namelist[itag] if namelist else tagkey.capitalize(),
                        )
                        self.crafter.msg(err)
                        raise CraftingValidationError(err)
                    for obj,quantity in found_objs:
                        tagmap.pop(obj)
                        valids.append(obj)
                        quants.append(quantity)

                # no objects with required tags were found
                elif exact_match:
                    err = self._format_message(
                        error_missing_message,
                        missing=namelist[itag] if namelist else tagkey.capitalize(),
                    )
                    self.crafter.msg(err)
                    raise CraftingValidationError(err)

            if exact_match and tagmap:
                # something is left in tagmap, that means it was never popped and
                # thus this is not an exact match
                err = self._format_message(
                    error_excess_message,
                    excess=[obj.get_display_name(looker=self.crafter) for obj in tagmap],
                )
                self.crafter.msg(err)
                raise CraftingValidationError(err)

            return valids, quants

        # get tools and consumables from self.inputs
        tool_map = {
            obj: obj.tags.get(category=self.tool_tag_category, return_list=True)
            for obj in self.inputs
            if obj
            and hasattr(obj, "tags")
            and inherits_from(obj, "evennia.objects.models.ObjectDB")
        }
        tool_map = {obj: tags for obj, tags in tool_map.items() if tags}
        consumable_map = {
            obj: obj.tags.get(category=self.consumable_tag_category, return_list=True)
            for obj in self.inputs
            if obj
            and hasattr(obj, "tags")
            and obj not in tool_map
            and inherits_from(obj, "evennia.objects.models.ObjectDB")
        }
        consumable_map = {obj: tags for obj, tags in consumable_map.items() if tags}

        # we set these so they are available for error management at all times,
        # they will be updated with the actual values at the end
        self.validated_tools = [obj for obj in tool_map]
        self.validated_consumables = [obj for obj in consumable_map]
        self.validated_quantities = [1 for obj in consumable_map]

        tools = _check_tools(
            tool_map,
            self.tool_tags,
            self.tool_names,
            self.exact_tools,
            self.exact_tool_order,
            self.error_tool_missing_message,
            self.error_tool_order_message,
            self.error_tool_excess_message,
        )
        consumables, quantities = _check_ingredients(
            consumable_map,
            self.consumable_tags,
            self.consumable_names,
            self.consumable_quantities,
            self.exact_consumables,
            self.exact_consumable_order,
            self.error_consumable_missing_message,
            self.error_consumable_order_message,
            self.error_consumable_excess_message,
        )

        # regardless of flags, the tools/consumable lists much contain exactly
        # all the recipe needs now.
        if len(tools) != len(self.tool_tags):
            raise CraftingValidationError(
                f"Tools {tools}'s tags do not match expected tags {self.tool_tags}"
            )
        # since multiple ingredients can count towards the total quantity, list lengths may not match
        # instead we check total quantities
        if sum(quantities) != sum(self.validated_quantities):
            raise CraftingValidationError(
                "The amount of ingredients do not match the recipe."
            )
        
        self.validated_tools = tools
        self.validated_consumables = consumables
        self.validated_quantities = quantities
        
    def post_craft(self, craft_result, **kwargs):
        """
        Hook to override.
        This is called just after crafting has finished. A common use of
        this method is to delete the inputs.

        Args:
            craft_result (list): The crafted result, provided by `self.do_craft`.
            **kwargs (any): Passed from `self.craft`.

        Returns:
            list: The return(s) of the craft, possibly modified in this method.

        Notes:
            This is _always_ called, also if validation in `pre_craft` fails
            (`craft_result` will then be `None`).

        """
        if craft_result:
            self.output_names = craft_result
            self.crafter.msg(self._format_message(self.success_message))
        elif self.failure_message:
            self.crafter.msg(self._format_message(self.failure_message))

        if craft_result or self.consume_on_fail:
            # consume the inputs
            used_up = zip(self.validated_consumables, self.validated_quantities)
            for obj, quantity in used_up:
                if obj.size == quantity:
                    obj.delete()
                elif obj.size > quantity:
                    obj.resize(quantity * -1)
                else:
                    self.crafter.msg(f"Recipe resulted in invalid quantity for {obj.key}.")
                    obj.delete()

        return craft_result


class VariableCraftingRecipe(CraftingRecipe):
    """
    Crafting recipes where the name and description of the output items
    are affected by the materials or ingredients used.
    
    Placeholders within the key or description of the recipe prototypes
    that are to be replaced with the material keys or descriptions
    should be in the format of [tag]
    
    Inputs are expected to have an attribute `material` which contains
    a tuple, of two strings. The first string is the "short" material name
    and is put into the result's key. The second is the "long" material
    name and is put into the result's desc.
    
    This mechanism can easily be changed.
    
    Example:
        ```python
            output_prototypes = [
                {
                    "key": "[fabric] tunic",
                    "desc": "A simple tunic made of [fabric].",
                }
            ]
        ```
        
        The resulting item made with a piece of blue linen as the fabric
        material would then be:
        
        blue linen tunic
            A simple tunic made of blue linen.
    """
    def do_craft(self, **kwargs):
        """
        Returns:
          list: A list of spawned objects created from the inputs, or None
          on a failure.
        """
        for ingr in self.consumable_tags:
            mats = []
            full_mats = []
            rep_key = "[%s]" % ingr
            for obj in self.validated_consumables:
                if obj.tags.has(ingr,category=self.consumable_tag_category):
                    # get the material desc strings from the ingredient
                    mat, full_mat = obj.attributes.get("material",(None,None))
                    # don't duplicate matching materials
                    if mat not in mats:
                        mats.append(mat)
                    # check long mat desc separately since it has more detail
                    if full_mat not in full_mats:
                        full_mats.append(full_mat)
            mat_str = list_to_string(mats)
            desc_str = list_to_string(full_mats)

            # modify the prototypes before spawning
            for prot in self.output_prototypes:
                prot["key"] = prot["key"].replace(rep_key,mat_str)
                prot["desc"] = prot["desc"].replace(rep_key,desc_str)

        #return spawn(*self.output_prototypes)
        return super().do_craft(**kwargs)

    def post_craft(self, craft_result, **kwargs):
        """
        Overrides the output names to make sure the output message matches
        the actual result objects, rather than printing the recipe's key with
        its tag placeholders.
        """
        if craft_result:
            self.output_names = craft_result

        return super().post_craft(craft_result, **kwargs)
