from tclCommands.TclCommand import *
from copy import deepcopy
from shapely import Point


class TclCommandAddDrill(TclCommandSignaled):
    """
    Tcl shell command to add a rectange to the given Geometry object.
    """

    # array of all command aliases, to be able use  old names for backward compatibility (add_poly, add_polygon)
    aliases = ['add_drill']

    description = '%s %s' % ("--", "Adds a drill in the given Excellon object, if it does not exist already.")

    # Dictionary of types from Tcl command, needs to be ordered.
    # For positional arguments
    arg_names = collections.OrderedDict([
        ('name', str)
    ])

    # Dictionary of types from Tcl command, needs to be ordered.
    # For options like -optionname value
    option_types = collections.OrderedDict([
        ('dia', float),
        ('x', float),
        ('y', float),
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Adds a drill hole in the given Excellon object.",
        'args': collections.OrderedDict([
            ('name', 'Name of the Excellon object in which to add the drill hole.'),
            ('dia', 'The tool diameter.'),
            ('x', "X coordinate for the drill hole. If not used then the assumed X value is 0.0."),
            ('y', "Y coordinate for the drill hole. If not used then the assumed Y value is 0.0."),
        ]),
        'examples': ["add_drill excellon_name -dia 0.8 -x 13.3 -y 6.2"]
    }

    def execute(self, args, unnamed_args):
        """
        execute current TCL shell command

        :param args:            array of known named arguments and options
        :param unnamed_args:    array of other values which were passed into command
                                without -somename and  we do not have them in known arg_names
        :return:                None or exception
        """

        if unnamed_args:
            self.raise_tcl_error(
                "Too many arguments. Correct format: %s" %
                '["add_drill excellon_name -dia -x -y"]')

        name = args['name']
        try:
            obj = self.app.collection.get_by_name(str(name))
        except Exception:
            return "Could not retrieve object: %s" % name
        if obj is None:
            return "Object not found: %s" % name
        if obj.kind != 'excellon':
            return 'Expected Excellon, got %s %s.' % (name, type(obj))

        if 'dia' not in args:
            return "Failed. The -dia parameter is missing and it is required."

        new_dia = args['dia']
        drill_x = 0.0 if 'x' not in args else args['x']
        drill_y = 0.0 if 'y' not in args else args['y']

        # create a dict with the keys the tool dimater value truncated to the nr of decimals use by the app and the
        # value is the tool number
        dia_tool_dict = {
            self.app.dec_format(diam['tooldia'], self.app.decimals): tool for tool, diam in list(obj.tools.items())
        }

        new_data = {}
        kind = 'excellon'
        for option in self.app.options:
            if option.find(kind + "_") == 0:
                oname = option[len(kind) + 1:]
                new_data[oname] = self.app.options[option]

            if option.find('tools_drill_') == 0:
                new_data[option] = self.app.options[option]

        drill_point = Point((drill_x, drill_y))

        if not dia_tool_dict:
            obj.tools[1] = {
                'tooldia': new_dia,
                'drills': [drill_point],
                'slots': [],
                'data': deepcopy(new_data)
            }
        elif new_dia not in list(dia_tool_dict.keys()):
            new_tool = max(list(obj.tools.keys())) + 1
            obj.tools[new_tool] = {
                'tooldia': new_dia,
                'drills': [drill_point],
                'slots': [],
                'data': deepcopy(new_data)
            }

            # sort the updated tools dict
            new_tools = {}
            tools_sorted = sorted(obj.tools.items(), key=lambda x: x[1]['tooldia'])
            for idx, tool in enumerate(tools_sorted, start=1):
                new_tools[idx] = tool[1]
            obj.tools = deepcopy(new_tools)
        elif new_dia in list(dia_tool_dict.keys()):
            if drill_point not in obj.tools[dia_tool_dict[new_dia]]['drills']:
                obj.tools[dia_tool_dict[new_dia]]['drills'].append(drill_point)
            else:
                return "Drill with the given coordinates is already in the object."

        obj.create_geometry()
