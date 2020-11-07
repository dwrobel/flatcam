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

    description = '%s %s' % ("--", "Plots all objects on appGUI.")

    # Dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([

    ])

    # Dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([
        ('plot_status', str),
        ('use_thread', str)
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = []

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Plots all objects on appGUI.",
        'args': collections.OrderedDict([
            ('plot_status', 'If to display or not the objects: True (1) or False (0).'),
            ('use_thread', 'If to use multithreading: True (1) or False (0).')
        ]),
        'examples': ['plot_all', 'plot_all -plot_status False']
    }

    def execute(self, args, unnamed_args):
        """

        :param args:
        :param unnamed_args:
        :return:
        """

        if 'use_thread' in args:
            try:
                par = args['use_thread'].capitalize()
            except AttributeError:
                par = args['use_thread']
            threaded = bool(eval(par))
        else:
            threaded = False

        plot_status = True
        if 'plot_status' in args:
            try:
                if args['plot_status'] is None:
                    plot_status = True
                else:
                    try:
                        par = args['plot_status'].capitalize()
                    except AttributeError:
                        par = args['plot_status']
                    plot_status = bool(eval(par))
            except KeyError:
                plot_status = True

        for obj in self.app.collection.get_list():
            obj.options["plot"] = True if plot_status is True else False

        if self.app.cmd_line_headless != 1:
            self.app.plot_all(use_thread=threaded)
