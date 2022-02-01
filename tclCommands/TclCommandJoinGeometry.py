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
    ])

    # Dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([
        ('outname', str)
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = []

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Runs a merge operation (join) on the Geometry objects.\n"
                "The names of the Geometry objects to be merged will be entered after the command,\n"
                "separated by spaces. See the example below.\n"
                "WARNING: if the name of an Geometry objects has spaces, enclose the name with quotes.",
        'args': collections.OrderedDict([
            ('outname', 'Name of the new Geometry Object made by joining of other Geometry objects.\n'
                        'If no outname is provided then will be used a generic "joined_geo" name.'),
        ]),
        'examples': ['join_geometry geo_name_1 "geo name_2" -outname merged_new_geo']
    }

    def execute(self, args, unnamed_args):
        """

        :param args:
        :param unnamed_args:
        :return:
        """
        self.app.log.debug("TclCommandJoinGeometry.execute()")

        outname = args['outname'] if 'outname' in args else "joined_geo"
        obj_names = unnamed_args
        if not obj_names:
            self.app.log.error("Missing objects to be joined. Exiting.")
            return "fail"

        objs = []
        for obj_n in obj_names:
            obj = self.app.collection.get_by_name(str(obj_n))
            if obj is None or obj == '':
                self.app.log.error("Object not found: %s" % obj_n)
                return "fail"
            objs.append(obj)

        def initialize(obj_, app):
            GeometryObject.merge(objs, obj_, log=app.log)

        if objs and len(objs) >= 2:
            self.app.app_obj.new_object("geometry", outname, initialize, plot=False)
        else:
            self.app.log.error(
                "No Geometry objects to be joined or less than two Geometry objects specified for merging.")
            return "fail"
