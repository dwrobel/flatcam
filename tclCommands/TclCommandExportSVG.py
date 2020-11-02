from tclCommands.TclCommand import TclCommand

import collections


class TclCommandExportSVG(TclCommand):
    """
    Tcl shell command to export a Geometry Object as an SVG File.

    example:
        export_svg my_geometry filename
    """

    # List of all command aliases, to be able use old names for backward compatibility (add_poly, add_polygon)
    aliases = ['export_svg']

    description = '%s %s' % ("--", "Export a Geometry object as a SVG File.")

    # Dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
        ('name', str),
        ('filename', str),
        ('scale_stroke_factor', float)
    ])

    # Dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([
        ('scale_stroke_factor', float)
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Export a Geometry object as a SVG File.",
        'args': collections.OrderedDict([
            ('name', 'Name of the object export. Required.'),
            ('filename', 'Absolute path to file to export.\n'
                         'WARNING: no spaces are allowed. If unsure enclose the entire path with quotes.'),
            ('scale_stroke_factor', 'Multiplication factor used for scaling line widths during export.')
        ]),
        'examples': ['export_svg my_geometry my_file.svg']
    }

    def execute(self, args, unnamed_args):
        """

        :param args:
        :param unnamed_args:
        :return:
        """

        self.app.f_handlers.export_svg(**args)
