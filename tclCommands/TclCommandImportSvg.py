from tclCommands.TclCommand import TclCommandSignaled

import collections
from camlib import Geometry


class TclCommandImportSvg(TclCommandSignaled):
    """
    Tcl shell command to import an SVG file as a Geometry Object.
    """

    # array of all command aliases, to be able use  old names for backward compatibility (add_poly, add_polygon)
    aliases = ['import_svg']

    description = '%s %s' % ("--", "Import a SVG file as a Geometry (or Gerber) Object.")

    # dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
        ('filename', str)
    ])

    # dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([
        ('type', str),
        ('outname', str)
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['filename']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Import a SVG file as a Geometry (or Gerber) Object.",
        'args':  collections.OrderedDict([
            ('filename', 'Absolute path to file to open. Required.\n'
                         'WARNING: no spaces are allowed. If unsure enclose the entire path with quotes.'),
            ('type', 'Import as a Gerber or Geometry (default) object. Values can be: "geometry" or "gerber"'),
            ('outname', 'Name of the resulting Geometry object.')
        ]),
        'examples': ['import_svg D:\\my_beautiful_svg_file.SVG']
    }

    def execute(self, args, unnamed_args):
        """
        execute current TCL shell command

        :param args: array of known named arguments and options
        :param unnamed_args: array of other values which were passed into command
            without -somename and  we do not have them in known arg_names
        :return: None or exception
        """

        # How the object should be initialized
        def obj_init(geo_obj, app_obj):

            if not isinstance(geo_obj, Geometry):
                self.raise_tcl_error('Expected Geometry or Gerber, got %s %s.' % (outname, type(geo_obj)))

            geo_obj.import_svg(filename)

        filename = args['filename']

        if 'outname' in args:
            outname = args['outname']
        else:
            outname = filename.split('/')[-1].split('\\')[-1]

        if 'type' in args:
            obj_type = args['type'].lower()
        else:
            obj_type = 'geometry'

        if obj_type != "geometry" and obj_type != "gerber":
            self.raise_tcl_error("Option type can be 'geometry' or 'gerber' only, got '%s'." % obj_type)

        with self.app.proc_container.new('%s ...' % _("Importing")):

            # Object creation
            self.app.app_obj.new_object(obj_type, outname, obj_init, plot=False)

            # Register recent file
            self.app.file_opened.emit("svg", filename)

            # GUI feedback
            self.app.inform.emit("Opened: " + filename)
