from tclCommands.TclCommand import TclCommandSignaled

import collections


class TclCommandIsolate(TclCommandSignaled):
    """
    Tcl shell command to Creates isolation routing geometry for the given Gerber.

    example:
        set_sys units MM
        new
        open_gerber tests/gerber_files/simple1.gbr -outname margin
        isolate margin -dia 3
        cncjob margin_iso
    """

    # array of all command aliases, to be able use  old names for backward compatibility (add_poly, add_polygon)
    aliases = ['isolate']

    description = '%s %s' % ("--", "Creates isolation routing Geometry for the specified Gerber object.")

    # dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
        ('name', str)
    ])

    # dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([
        ('dia', float),
        ('passes', int),
        ('overlap', float),
        ('combine', str),
        ('outname', str),
        ('follow', str),
        ('iso_type', int)

    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Creates isolation routing Geometry for the specified Gerber object.",
        'args': collections.OrderedDict([
            ('name', 'Name of the Gerber source object to be isolated. Required.'),
            ('dia', 'Tool diameter.'),
            ('passes', 'Passes of tool width.'),
            ('overlap', 'Percentage of tool diameter to overlap current pass over previous pass. Float [0, 99.9999]\n'
                        'E.g: for a 25% from tool diameter overlap use -overlap 25'),
            ('combine', 'Combine all passes into one geometry. Can be True (1) or False (0)'),
            ('outname', 'Name of the resulting Geometry object.'),
            ('follow', 'Create a Geometry that follows the Gerber path. Can be True (1) or False (0).'),
            ('iso_type', 'A value of 0 will isolate exteriors, a value of 1 will isolate interiors '
                         'and a value of 2 will do full isolation.')
        ]),
        'examples': ['isolate my_gerber -dia 0.1 -passes 2 -overlap 10 -combine True -iso_type 2 -outname out_geo']
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
            args['outname'] = name + "_iso"

        # if 'timeout' in args:
        #     timeout = args['timeout']
        # else:
        #     timeout = 10000

        if 'follow' not in args:
            args['follow'] = None

        # evaluate this parameter so True, False, 0 and 1 works
        if 'combine' in args:
            try:
                par = args['combine'].capitalize()
            except AttributeError:
                par = args['combine']
            args['combine'] = bool(eval(par))
        else:
            args['combine'] = bool(eval(self.app.defaults["tools_iso_combine_passes"]))

        obj = self.app.collection.get_by_name(name)
        if obj is None:
            self.raise_tcl_error("Object not found: %s" % name)

        if obj.kind != 'gerber':
            self.raise_tcl_error('Expected GerberObject, got %s %s.' % (name, type(obj)))

        del args['name']
        obj.isolate(plot=False, **args)
