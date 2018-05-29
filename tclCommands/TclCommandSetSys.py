from tclCommands.TclCommand import *


class TclCommandSetSys(TclCommand):
    """
    Tcl shell command to set the value of a system variable

    example:

    """

    # List of all command aliases, to be able use old names for backward compatibility (add_poly, add_polygon)
    aliases = ['set_sys', 'setsys']

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
        'main': "Sets the value of the system variable.",
        'args': collections.OrderedDict([
            ('name', 'Name of the system variable.'),
            ('value', 'Value to set.')
        ]),
        'examples': []
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
            "mm": "MM",
            "in": "IN"
        }

        if param in self.app.defaults:

            try:
                value = tcl2py[value]
            except KeyError:
                pass

            self.app.defaults[param] = value
            self.app.propagate_defaults()
        else:
            self.raise_tcl_error("No such system parameter \"{}\".".format(param))

