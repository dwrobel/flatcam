# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Content was borrowed from FlatCAM proper                 #
# Date: 4/22/2020                                          #
# MIT Licence                                              #
# ##########################################################

from tclCommands.TclCommand import TclCommand

import collections

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class TclCommandHelp(TclCommand):
    """
    Tcl shell command to show Help

    example:
        help add_circle
    """

    # List of all command aliases, to be able use old names for backward compatibility (add_poly, add_polygon)
    aliases = ['help']

    description = '%s %s' % ("--", "PRINTS to TCL the HELP.")

    # Dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
        ('name', str)
    ])

    # Dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([

    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = []

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Returns to TCL the value for the entered system variable.",
        'args': collections.OrderedDict([
            ('name', 'Name of a Tcl Command for which to display the Help.'),
        ]),
        'examples': ['help add_circle']
    }

    def execute(self, args, unnamed_args):
        """

        :param args:            Without any argument will display the list of commands. Can have as a argument
        a tcl command name to display the help for that command.
        :param unnamed_args:
        :return:
        """

        if 'name' in args:
            name = args['name']
            if name not in self.app.shell.tcl_commands_storage:
                return "Unknown command: %s" % name

            help_for_command = self.app.shell.tcl_commands_storage[name]["help"] + '\n\n'
            self.app.shell.append_output(help_for_command)
        else:
            if not args:
                cmd_enum = '%s\n' % _("Available commands:")

                displayed_text = []
                try:
                    # find the maximum length of a command name
                    max_len = 0
                    for cmd_name in self.app.shell.tcl_commands_storage:
                        curr_len = len(cmd_name)
                        if curr_len > max_len:
                            max_len = curr_len

                    h_space = "&nbsp;"
                    cnt = 0
                    for cmd_name in sorted(self.app.shell.tcl_commands_storage):
                        cmd_description = "<span>%s</span>" % \
                                          self.app.shell.tcl_commands_storage[cmd_name]['description']

                        curr_len = len(cmd_name)

                        cmd_name_colored = "> <span style=\" font-weight: bold; color: red;\" >%s</span>" % \
                                           str(cmd_name)

                        nr_chars = max_len - curr_len

                        cmd_line_txt = '%s%s&nbsp;&nbsp;%s' % (cmd_name_colored, nr_chars * h_space, cmd_description)

                        displayed_text.append(cmd_line_txt)

                        # group commands by 4 adding a line break after 4 commands
                        if cnt == 3:
                            cnt = 0
                            displayed_text.append(' ')
                        else:
                            cnt += 1
                except Exception as err:
                    self.app.log.debug("tclCommands.TclCommandHelp() when run as 'help' --> %s" % str(err))
                    displayed_text = ['> %s' % cmd for cmd in sorted(self.app.shell.tcl_commands_storage)]

                cmd_enum += '<br>'.join(displayed_text)
                cmd_enum += '<br><br>%s<br>%s<br><br>' % (
                    _("Type help <command_name> for usage."), _("Example: help open_gerber"))

                self.app.shell.append_raw(cmd_enum)
