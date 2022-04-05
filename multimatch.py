"""
Interactive Multi-Matches

How To Use

Due to the nature of commands and interactivity, this is a bit more
complicated to use than just inheriting classes or importing methods.

First, install the multimatch functions on your base `Character` class.
You can do this either by inheriting `MMCharacter` as a mixin, or by
copy/pasting the methods directly into your own class.

Next, reference the dummy command at the end for how to implement this
multimatch into your own commands.

Notes:
- This system is NOT retroactive! It will not apply for any commands
    that you didn't explicitly code it into.
- This is NOT a custom search function. It can be used with your own
    custom search functions without any alterations.
- Using this system in any function besides a command's `func` requires
    the `@interactive` decorator on that function. Be sure you understand
    *exactly* how that works before trying it!
"""

class MMCharacter():
    """
    A mixin class for implementing interactive multimatches.
    """
    def multimatch_msg(self, input, lst):
        """
        Formats the results for display, including option indexes, and sends
        it to the caller.

        Args:
            input (str) - the search string provided by the caller
            lst (list)  - a list containing all objects which matched the search
        """
        result_str = []
        for i, obj in enumerate(lst):
            # build a string with the index in the list, the name, and any disambiguation info
            string = " %i. |w%s|n%s" % (i+1, obj.get_display_name(self), obj.get_extra_info(self))
            result_str.append(string)
        self.msg("Which |c%s|n do you mean?\n%s" % (target, "\n".join(result_str)))
    
    def process_multimatch(self, option, lst):
        """
        Process the caller's input to determine which multimatch was selected.

        Args:
            option (str) - the option string provided by the caller
            lst (list)   - a list containing all objects which matched the search
        """
        # provide an option to explicitly cancel the command
        if option == 'c':
            self.msg("Action cancelled.")
            return None
        # check if the option given is a valid index
        option = int(option)
        if option <= len(lst) and option > 0:
            return lst[option-1]
        else:
            self.msg("Invalid option, cancelling.")
            return None


class DummyCmd():
    """
    Example of how to structure a command for interactive multimatch.

    This is not a real command! Don't try to use it.
    """
    key = "your_key"
    
    def func(self):
        caller = self.caller
    
        # Perform your normal object search here.
        # The `quiet` flag is necessary to skip the build-in multimatch 
        result = caller.search(arg, quiet=True)
        
        # no results means no matches
        if len(result) == 0:
            caller.msg("You don't have any |w%s|n." % arg)
            return
        # more than one match
        elif len(result) > 1:
            # message the caller with the options 
            caller.multimatch_msg(arg, result)
            # prompt the caller for additional input
            index = yield("Enter a number (or |wc|n to cancel):")
            # process the caller's selection
            obj = caller.process_multimatch(index, result)
        # only one match, use it as-is
        else:
            obj = result[0]

        # check if `obj` is None, in case the caller cancelled a multimatch
        if not obj:
            return

        # Do the rest of your command stuff here.
