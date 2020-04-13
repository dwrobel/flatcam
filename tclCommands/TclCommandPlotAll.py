from tclCommands.TclCommand import TclCommandSignaled

import collections


class TclCommandPlotAll(TclCommandSignaled):
    """
    Tcl shell command to update the plot on the user interface.

    example:
        plot
    """

    # List of all command aliases, to be able use old names for backward compatibility (add_poly, add_polygon)
    aliases = ['plot_all']

    description = '%s %s' % ("--", "Plots all objects on GUI.")

    # Dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([

    ])

    # Dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([
        ('use_thread', str)
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = []

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Plots all objects on GUI.",
        'args': collections.OrderedDict([
            ('use_thread', 'If to use multithreading: True (1) or False (0).')
        ]),
        'examples': ['plot_all']
    }

    def execute(self, args, unnamed_args):
        """

        :param args:
        :param unnamed_args:
        :return:
        """

        if 'use_thread' in args:
            threaded = bool(eval(args['use_thread']))
        else:
            threaded = False

        if self.app.cmd_line_headless != 1:
            self.app.plot_all(use_thread=threaded)
