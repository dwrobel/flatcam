from tclCommands.TclCommand import TclCommand
from appObjects.FlatCAMExcellon import ExcellonObject

import collections


class TclCommandJoinExcellon(TclCommand):
    """
    Tcl shell command to merge Excellon objects.

    example:

    """

    # List of all command aliases, to be able use old names for backward compatibility (add_poly, add_polygon)
    aliases = ['join_excellon', 'join_excellons']

    description = '%s %s' % ("--", "Merge two or more Excellon objects drills and create "
                                   "a new Excellon object with them.")

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
        'main': "Runs a merge operation (join) on the Excellon objects.\n"
                "The names of the Excellon objects to be merged will be entered after the outname,\n"
                "separated by spaces. See the example below.\n"
                "WARNING: if the name of an Excellon objects has spaces, enclose the name with quotes.",
        'args': collections.OrderedDict([
            ('outname', 'Name of the new Excellon Object made by joining of other Excellon objects. Required'),
        ]),
        'examples': ['join_excellons merged_new_excellon exc_name_1 "exc name_2"']
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
            ExcellonObject.merge(objs, obj_, decimals=self.app.decimals)

        if objs and len(objs) >= 2:
            self.app.app_obj.new_object("excellon", outname, initialize, plot=False)
        else:
            return "No Excellon objects to be joined or less than two Excellon objects specified for merging."
