from tclCommands.TclCommand import *


class TclCommandFollow(TclCommandSignaled):
    """
    Tcl shell command to follow a Gerber file
    """

    # array of all command aliases, to be able use  old names for backward compatibility (add_poly, add_polygon)
    aliases = ['follow']

    # dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
        ('name', str)
    ])

    # dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([
        ('outname', str)
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Creates a geometry object following gerber paths.",
        'args': collections.OrderedDict([
            ('name', 'Object name to follow.'),
            ('outname', 'Name of the resulting Geometry object.')
        ]),
        'examples': ['follow name -outname name_follow']
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
            follow_name = name + "_follow"

        obj = self.app.collection.get_by_name(name)

        if obj is None:
            self.raise_tcl_error("Object not found: %s" % name)

        if not isinstance(obj, FlatCAMGerber):
            self.raise_tcl_error('Expected FlatCAMGerber, got %s %s.' % (name, type(obj)))

        del args['name']
        obj.follow(**args)


