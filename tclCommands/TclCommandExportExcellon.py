from tclCommands.TclCommand import TclCommand

import collections


class TclCommandExportExcellon(TclCommand):
    """
    Tcl shell command to export a Excellon Object as an Excellon File.

    example:
        export_exc path/my_excellon filename
    """

    # List of all command aliases, to be able use old names for backward compatibility (add_poly, add_polygon)
    aliases = ['export_exc', 'ee', 'export_excellon']

    description = '%s %s' % ("--", "Export a Excellon object as a Excellon File.")

    # Dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
        ('name', str),
        ('filename', str)
    ])

    # Dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([
    ])

    # array of mandatory options for current Tcl command: required = ['name','outname']
    required = ['name']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Export a Excellon object as a Excellon File.",
        'args': collections.OrderedDict([
            ('name', 'Name of the Excellon object to export.'),
            ('filename', 'Absolute path to file to export.\n'
                         'WARNING: no spaces are allowed. If unsure enclose the entire path with quotes.'),
        ]),
        'examples': ['export_excellon my_excellon path/my_file.drl', 'export_excellon My_Excellon D:/drill_file.DRL']
    }

    def execute(self, args, unnamed_args):
        """

        :param args:
        :param unnamed_args:
        :return:
        """
        if 'filename' not in args:
            args['filename'] = self.app.defaults["global_last_save_folder"] + '/' + args['name']
        self.app.f_handlers.export_excellon(use_thread=False, **args)
