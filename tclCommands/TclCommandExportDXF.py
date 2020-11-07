from tclCommands.TclCommand import TclCommand

import collections


class TclCommandExportDXF(TclCommand):
    """
    Tcl shell command to export a Geometry Object as an DXF File.

    example:
        export_dxf path/my_geometry filename
    """

    # List of all command aliases, to be able use old names for backward compatibility (add_poly, add_polygon)
    aliases = ['export_dxf', 'edxf']

    description = '%s %s' % ("--", "Export a Geometry object as a DXF File.")

    # Dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
        ('name', str),
        ('filename', str)
    ])

    # Dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([
    ])

    # array of mandatory options for current Tcl command: required = ['name','outname']
    required = ['obj_name']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Export a Geometry object as a DXF File.",
        'args': collections.OrderedDict([
            ('name', 'Name of the Geometry object to export.'),
            ('filename', 'Absolute path to file to export.\n'
                         'WARNING: no spaces are allowed. If unsure enclose the entire path with quotes.'),
        ]),
        'examples': ['export_dxf my_geo path/my_file.dxf', 'export_dxf my_geo D:/my_file.dxf']
    }

    def execute(self, args, unnamed_args):
        """

        :param args:
        :param unnamed_args:
        :return:
        """
        if 'filename' not in args:
            args['filename'] = self.app.defaults["global_last_save_folder"] + '/' + args['name']
        self.app.f_handlers.export_dxf(use_thread=False, local_use=None, **args)
