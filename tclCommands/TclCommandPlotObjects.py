# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 8/17/2019                                          #
# MIT Licence                                              #
# ##########################################################

from tclCommands.TclCommand import TclCommand

import collections


class TclCommandPlotObjects(TclCommand):
    """
    Tcl shell command to update the plot on the user interface.

    example:
        plot
    """

    # List of all command aliases, to be able use old names for backward compatibility (add_poly, add_polygon)
    aliases = ['plot_objects']

    description = '%s %s' % ("--", "Plot a specified list of objects in appGUI.")

    # Dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
        ('names', str)
    ])

    # Dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([
        ('plot_status', str)
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['names']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Plot a specified list of objects in appGUI.",
        'args': collections.OrderedDict([
            ('names', "A list of object names to be plotted separated by comma. Required.\n"
                      "WARNING: no spaces are allowed. If unsure enclose the entire list with quotes."),
            ('plot_status', 'If to display or not the objects: True (1) or False (0).')
        ]),
        'examples': ["plot_objects gerber_obj.GRB,excellon_obj.DRL"]
    }

    def execute(self, args, unnamed_args):
        """

        :param args:
        :param unnamed_args:
        :return:
        """

        if 'plot_status' in args:
            if args['plot_status'] is None:
                plot_status = True
            else:
                plot_status = bool(eval(args['plot_status']))
        else:
            plot_status = True

        if self.app.cmd_line_headless != 1:
            names = [x.strip() for x in args['names'].split(",") if x != '']
            objs = []
            for name in names:
                obj = self.app.collection.get_by_name(name)
                obj.options["plot"] = True if plot_status is True else False
                objs.append(obj)

            for obj in objs:
                obj.plot()
