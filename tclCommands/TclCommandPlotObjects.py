from ObjectCollection import *
from tclCommands.TclCommand import TclCommand


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
    required = []

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Plot a list of objects.",
        'args': collections.OrderedDict([
            ('names', "UA list of object names to be plotted.")
        ]),
        'examples': ["plot_objects"]
    }

    def execute(self, args, unnamed_args):
        """

        :param args:
        :param unnamed_args:
        :return:
        """
        names = [x.strip() for x in args['names'].split(",")]
        objs = []
        for name in names:
            objs.append(self.app.collection.get_by_name(name))

        for obj in objs:
            obj.plot()
