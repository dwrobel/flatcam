from tclCommands.TclCommand import TclCommand
from appObjects.FlatCAMGeometry import GeometryObject

import collections
from copy import deepcopy


class TclCommandSplitGeometry(TclCommand):
    """
    Tcl shell command to split a geometry by tools.

    example:

    """

    # List of all command aliases, to be able use old names for backward compatibility (add_poly, add_polygon)
    aliases = ['split_geometries', 'split_geometry']

    description = '%s %s' % (
        "--", "Split one Geometry object into separate ones for each tool.")

    # Dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
        ('source_name', str),
    ])

    # Dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([

    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['source_name']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Runs a merge operation (join) on the Geometry objects.\n"
                "The names of the Geometry objects to be merged will be entered after the outname,\n"
                "separated by spaces. See the example below.\n"
                "WARNING: if the name of an Geometry objects has spaces, enclose the name with quotes.",
        'args': collections.OrderedDict([
            ('source_name', 'Name of the new Geometry Object made by joining of other Geometry objects. Required'),
        ]),
        'examples': ['join_geometry merged_new_geo geo_name_1 "geo name_2"']
    }

    def execute(self, args, unnamed_args):
        """

        :param args:
        :param unnamed_args:
        :return:
        """

        obj: GeometryObject = self.app.collection.get_by_name(
            str(args['source_name']))
        if obj is None:
            return "Object not found: %s" % args['source_name']

        for uid in list(obj.tools.keys()):
            def initialize(new_obj, app):
                new_obj.multigeo = True
                new_obj.tools[uid] = deepcopy(obj.tools[uid])
            name = "{0}_tool_{1}".format(args['source_name'], uid)
            self.app.app_obj.new_object(
                "geometry", name, initialize, plot=False)
