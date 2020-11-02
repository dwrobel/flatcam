from tclCommands.TclCommand import TclCommand

import collections


class TclCommandSetSys(TclCommand):
    """
    Tcl shell command to set the value of a system variable

    example:

    """

    # List of all command aliases, to be able use old names for backward compatibility (add_poly, add_polygon)
    aliases = ['set_sys', 'setsys']

    description = '%s %s' % ("--", "Sets the value of the specified system variable.")

    # Dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
        ('name', str),
        ('value', str)
    ])

    # Dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([

    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name', 'value']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Sets the value of the specified system variable.",
        'args': collections.OrderedDict([
            ('name', 'Name of the system variable. Required.'),
            ('value', 'Value to set.')
        ]),
        'examples': ['set_sys global_gridx 1.0']
    }

    def execute(self, args, unnamed_args):
        """

        :param args:
        :param unnamed_args:
        :return:
        """

        param = args['name']
        value = args['value']

        # TCL string to python keywords:
        tcl2py = {
            "None": None,
            "none": None,
            "false": False,
            "False": False,
            "true": True,
            "True": True,
            "l": "L",
            "L": "L",
            "T": "T",
            "t": "T",
            "0": "0",
            "1": "1",
            "2": "2",
            "3": "3",
            "4": "4",
            "5": "5",
            "in": "IN",
            "IN": "IN",
            "mm": "MM",
            "MM": "MM"
        }

        if param in self.app.defaults:

            try:
                value = tcl2py[value]
            except KeyError:
                pass

            self.app.defaults[param] = value
            self.app.defaults.propagate_defaults()

        else:
            self.raise_tcl_error("No such system parameter \"{}\".".format(param))
