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

    # Dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
        ('obj_name', str),
        ('filename', str)
    ])

    # Dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([
    ])

    # array of mandatory options for current Tcl command: required = ['name','outname']
    required = ['obj_name']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Export a Excellon Object as a Excellon File.",
        'args': collections.OrderedDict([
            ('obj_name', 'Name of the object to export.'),
            ('filename', 'Path to the file to export.')
        ]),
        'examples': ['export_excellon my_excellon path/my_file.drl']
    }

    def execute(self, args, unnamed_args):
        """

        :param args:
        :param unnamed_args:
        :return:
        """
        if  'filename' not in args:
            args['filename'] = self.app.defaults["global_last_save_folder"] + '/' + args['obj_name']
        self.app.export_excellon(use_thread=False,**args)
