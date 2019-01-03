from ObjectCollection import *
from tclCommands.TclCommand import TclCommandSignaled


class TclCommandCncjob(TclCommandSignaled):
    """
    Tcl shell command to Generates a CNC Job from a Geometry Object.

    example:
        set_sys units MM
        new
        open_gerber tests/gerber_files/simple1.gbr -outname margin
        isolate margin -dia 3
        cncjob margin_iso
    """

    # array of all command aliases, to be able use  old names for backward compatibility (add_poly, add_polygon)
    aliases = ['cncjob']

    # dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
        ('name', str)
    ])

    # dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([
        ('z_cut', float),
        ('z_move', float),
        ('feedrate', float),
        ('feedrate_rapid', float),
        ('tooldia', float),
        ('spindlespeed', int),
        ('multidepth', bool),
        ('extracut', bool),
        ('depthperpass', float),
        ('endz', float),
        ('ppname_g', str),
        ('outname', str)
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Generates a CNC Job from a Geometry Object.",
        'args': collections.OrderedDict([
            ('name', 'Name of the source object.'),
            ('tooldia', 'Tool diameter to show on screen.'),
            ('z_cut', 'Z-axis cutting position.'),
            ('z_move', 'Z-axis moving position.'),
            ('feedrate', 'Moving speed when cutting.'),
            ('feedrate_rapid', 'Rapid moving at speed when cutting.'),
            ('spindlespeed', 'Speed of the spindle in rpm (example: 4000).'),
            ('multidepth', 'Use or not multidepth cnccut. (True or False)'),
            ('depthperpass', 'Height of one layer for multidepth.'),
            ('extracut', 'Use or not an extra cnccut over the first point in path,in the job end (example: True)'),
            ('endz', 'Height where the last move will park.'),
            ('outname', 'Name of the resulting Geometry object.'),
            ('ppname_g', 'Name of the Geometry postprocessor. No quotes, case sensitive')
        ]),
        'examples': []
    }

    def execute(self, args, unnamed_args):
        """
        execute current TCL shell command

        :param args: array of known named arguments and options
        :param unnamed_args: array of other values which were passed into command
            without -somename and  we do not have them in known arg_names
        :return: None or exception
        """

        name = args['name']

        if 'outname' not in args:
            args['outname'] = str(name) + "_cnc"

        obj = self.app.collection.get_by_name(str(name), isCaseSensitive=False)
        if obj is None:
            self.raise_tcl_error("Object not found: %s" % str(name))

        if not isinstance(obj, FlatCAMGeometry):
            self.raise_tcl_error('Expected FlatCAMGeometry, got %s %s.' % (str(name), type(obj)))

        args["z_cut"] = args["z_cut"] if "z_cut" in args else obj.options["cutz"]
        args["z_move"] = args["z_move"] if "z_move" in args else obj.options["travelz"]
        args["feedrate"] = args["feedrate"] if "feedrate" in args else obj.options["feedrate"]
        args["feedrate_rapid"] = args["feedrate_rapid"] if "feedrate_rapid" in args else obj.options["feedrate_rapid"]
        args["spindlespeed"] = args["spindlespeed"] if "spindlespeed" in args else None
        args["tooldia"] = args["tooldia"] if "tooldia" in args else obj.options["cnctooldia"]
        args["multidepth"] = args["multidepth"] if "multidepth" in args else obj.options["multidepth"]
        args["depthperpass"] = args["depthperpass"] if "depthperpass" in args else obj.options["depthperpass"]
        args["extracut"] = args["extracut"] if "extracut" in args else obj.options["extracut"]
        args["endz"]= args["endz"] if "endz" in args else obj.options["endz"]
        args["ppname_g"] = args["ppname_g"] if "ppname_g" in args else obj.options["ppname_g"]

        del args['name']

        # HACK !!! Should be solved elsewhere!!!
        # default option for multidepth is False
        obj.options['multidepth'] = False

        obj.generatecncjob(use_thread=False, **args)
