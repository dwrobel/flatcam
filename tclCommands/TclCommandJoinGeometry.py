from tclCommands.TclCommand import TclCommand
from appObjects.FlatCAMGeometry import GeometryObject

import collections


class TclCommandJoinGeometry(TclCommand):
    """
    Tcl shell command to merge Excellon objects.

    example:

    """

    # List of all command aliases, to be able use old names for backward compatibility (add_poly, add_polygon)
    aliases = ['join_geometries', 'join_geometry']

    description = '%s %s' % ("--", "Merge two or more Geometry objects and create a new Geometry object.")

    # Dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
        ('outname', str),
    ])

    # Dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([

    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['outname']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Runs a merge operation (join) on the Geometry objects.\n"
                "The names of the Geometry objects to be merged will be entered after the outname,\n"
                "separated by spaces. See the example below.\n"
                "WARNING: if the name of an Geometry objects has spaces, enclose the name with quotes.",
        'args': collections.OrderedDict([
            ('outname', 'Name of the new Geometry Object made by joining of other Geometry objects. Required'),
        ]),
        'examples': ['join_geometry merged_new_geo geo_name_1 "geo name_2"']
    }

    def execute(self, args, unnamed_args):
        """

        :param args:
        :param unnamed_args:
        :return:
        """

        outname = args['outname']
        obj_names = unnamed_args

        objs = []
        for obj_n in obj_names:
            obj = self.app.collection.get_by_name(str(obj_n))
            if obj is None:
                return "Object not found: %s" % obj_n
            else:
                objs.append(obj)

        def initialize(obj_, app):
            GeometryObject.merge(objs, obj_)

        if objs and len(objs) >= 2:
            self.app.app_obj.new_object("geometry", outname, initialize, plot=False)
        else:
            return "No Geometry objects to be joined or less than two Geometry objects specified for merging."
