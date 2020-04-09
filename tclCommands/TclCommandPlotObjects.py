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

    # Dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
        ('names', str)
    ])

    # Dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([

    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['names']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Plot a list of objects.",
        'args': collections.OrderedDict([
            ('names', "A list of object names to be plotted separated by comma. Required.")
        ]),
        'examples': ["plot_objects gerber_obj.GRB, excellon_obj.DRL"]
    }

    def execute(self, args, unnamed_args):
        """

        :param args:
        :param unnamed_args:
        :return:
        """
        if self.app.cmd_line_headless != 1:
            names = [x.strip() for x in args['names'].split(",") if x != '']
            objs = []
            for name in names:
                objs.append(self.app.collection.get_by_name(name))

            for obj in objs:
                obj.plot()
