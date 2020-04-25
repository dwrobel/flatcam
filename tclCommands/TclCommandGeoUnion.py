from tclCommands.TclCommand import TclCommand

import collections


class TclCommandGeoUnion(TclCommand):
    """
    Tcl shell command to run a union (addition) operation on the
    components of a geometry object.

    example:

    """

    # List of all command aliases, to be able use old names for backward compatibility (add_poly, add_polygon)
    aliases = ['geo_union']

    description = '%s %s' % ("--", "Run the Union (join) geometry operation on the elements of a Geometry object.")

    # Dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
        ('name', str),
    ])

    # Dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([

    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name']

    # structured help for current command, args needs to be ordered
    help = {
        'main': ('Runs a union operation (addition) on the components '
                 'of the geometry object. For example, if it contains '
                 '2 intersecting polygons, this operation adds them into'
                 'a single larger polygon.'),
        'args': collections.OrderedDict([
            ('name', 'Name of the Geometry Object that contain the components to be joined. Required.'),
        ]),
        'examples': ['geo_union target_geo']
    }

    def execute(self, args, unnamed_args):
        """

        :param args:
        :param unnamed_args:
        :return:
        """

        obj_name = args['name']

        try:
            obj = self.app.collection.get_by_name(str(obj_name))
        except Exception:
            return "Could not retrieve object: %s" % obj_name
        if obj is None:
            return "Object not found: %s" % obj_name

        obj.union()
