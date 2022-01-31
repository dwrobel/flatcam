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

    ])

    # Dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([
        ('outname', str),
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = []

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Runs a merge operation (join) on the Excellon objects.\n"
                "The names of the Excellon objects to be merged will be entered after the command,\n"
                "separated by spaces. See the example below.\n"
                "WARNING: if the name of an Excellon objects has spaces, enclose the name with quotes.",
        'args': collections.OrderedDict([
            ('outname', 'Name of the new Excellon Object made by joining of other Excellon objects.\n'
                        'If not used then it will be used a generic name: "joined_exc"'),
        ]),
        'examples': ['join_excellons exc_name_1 "exc name_2" -outname merged_new_excellon',
                     'join_excellon exc_name_1 "exc name_2"']
    }

    def execute(self, args, unnamed_args):
        """

        :param args:
        :param unnamed_args:
        :return:
        """
        self.app.log.debug("TclCommandJoinExcellon.execute()")

        outname = args['outname'] if 'outname' in args else "joined_exc"
        obj_names = unnamed_args

        objs = []
        for obj_n in obj_names:
            obj = self.app.collection.get_by_name(str(obj_n))
            if obj is None:
                self.app.log.error("Object not found: %s" % obj_n)
                return "fail"
            else:
                objs.append(obj)

        def initialize(obj_, app):
            ExcellonObject.merge(objs, obj_, decimals=self.app.decimals, log=app.log)

        if objs and len(objs) >= 2:
            self.app.app_obj.new_object("excellon", outname, initialize, plot=False)
        else:
            self.app.log.error(
                "No Excellon objects to be joined or less than two Excellon objects specified for merging.")
            return "fail"
