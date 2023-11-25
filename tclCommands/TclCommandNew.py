from tclCommands.TclCommand import TclCommand

import collections


class TclCommandNew(TclCommand):
    """
    Tcl shell command to starts a new project. Clears objects from memory
    """

    # array of all command aliases, to be able use  old names for backward compatibility (add_poly, add_polygon)
    aliases = ['new']

    description = '%s %s' % ("--", "Starts a new project. Clears objects from memory.")

    # dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict()

    # dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([
        ('reset', str),
        ('keep_scripts', str)
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = []

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Starts a new project. Clears objects from memory. Default action: reset the Tcl environment.",
        'args': collections.OrderedDict([
            ('reset', 'If True/1 or missing (default value) or no value provided then the Tcl is re-instantiated '
                      'thus resetting all its variables.'),
            ('keep_scripts', 'If True/1, all script objects are kept in the new project. '
                             'Default: scripts are not kept.')
        ]),
        'examples': ['new', 'new -reset False', 'new -keep_scripts False']
    }

    def execute(self, args, unnamed_args):
        """
        execute current TCL shell command

        :param args: array of known named arguments and options
        :param unnamed_args: array of other values which were passed into command
            without -somename and  we do not have them in known arg_names
        :return: None or exception
        """

        reset_tcl = True
        if 'reset' in args:
            if args['reset']:
                try:
                    reset_tcl = bool(eval(str(args['reset'])))
                except NameError:
                    if args['reset'].lower() == 'false':
                        reset_tcl = False

        keep_scripts = False
        if 'keep_scripts' in args:
            if args['keep_scripts']:
                try:
                    keep_scripts = bool(eval(str(args['keep_scripts'])))
                except NameError:
                    if args['keep_scripts'].lower() == 'true':
                        keep_scripts = True

        self.app.f_handlers.on_file_new_project(cli=True, reset_tcl=reset_tcl, keep_scripts=keep_scripts)
