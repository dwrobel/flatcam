from tclCommands.TclCommand import TclCommand
from FlatCAMObj import FlatCAMExcellon

import collections


class TclCommandJoinExcellon(TclCommand):
    """
    Tcl shell command to merge Excellon objects.

    example:

    """

    # List of all command aliases, to be able use old names for backward compatibility (add_poly, add_polygon)
    aliases = ['join_excellon', 'join_excellons']

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
        'main': "Runs a merge operation (join) on the Excellon objects.",
        'args': collections.OrderedDict([
            ('name', 'Name of the new Excellon Object.'),
            ('obj_name_0', 'Name of the first object'),
            ('obj_name_1', 'Name of the second object.'),
            ('obj_name_2...', 'Additional object names')
        ]),
        'examples': []
    }

    def execute(self, args, unnamed_args):
        """

        :param args:
        :param unnamed_args:
        :return:
        """

        outname = args['name']
        obj_names = unnamed_args

        objs = []
        for obj_n in obj_names:
            obj = self.app.collection.get_by_name(str(obj_n))
            if obj is None:
                return "Object not found: %s" % obj_n
            else:
                objs.append(obj)

        def initialize(obj_, app):
            FlatCAMExcellon.merge(objs, obj_)

        if objs is not None:
            self.app.new_object("excellon", outname, initialize, plot=False)
