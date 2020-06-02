from tclCommands.TclCommand import TclCommandSignaled

import collections


class TclCommandWriteGCode(TclCommandSignaled):
    """
    Tcl shell command to save the G-code of a CNC Job object to file.
    """

    # array of all command aliases, to be able use
    # old names for backward compatibility (add_poly, add_polygon)
    aliases = ['write_gcode']

    description = '%s %s' % ("--", "Saves G-code of a CNC Job object to file.")

    # Dictionary of types from Tcl command, needs to be ordered.
    # For positional arguments
    arg_names = collections.OrderedDict([
        ('name', str),
        ('filename', str)
    ])

    # Dictionary of types from Tcl command, needs to be ordered.
    # For options like -optionname value
    option_types = collections.OrderedDict([
        ('preamble', str),
        ('postamble', str),
        ('muted', str)
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name', 'filename']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Saves G-code of a CNC Job object to file.",
        'args': collections.OrderedDict([
            ('name', 'Source CNC Job object. Required.'),
            ('filename', 'Output filename. Required.'),
            ('preamble', 'Text to append at the beginning.'),
            ('postamble', 'Text to append at the end.'),
            ('muted', 'It will not put errors in the Shell or status bar. True (1) or False (0)')

        ]),
        'examples': ["write_gcode name c:\\\\gcode_repo"]
    }

    def execute(self, args, unnamed_args):
        """
        execute current TCL shell command

        :param args: array of known named arguments and options
        :param unnamed_args: array of other values which were passed into command
            without -somename and  we do not have them in known arg_names
        :return: None or exception
        """

        """
        Requires obj_name to be available. It might still be in the
        making at the time this function is called, so check for
        promises and send to background if there are promises.
        """

        obj_name = args['name']
        filename = args['filename']

        preamble = args['preamble'] if 'preamble' in args else ''
        postamble = args['postamble'] if 'postamble' in args else ''

        if 'muted' in args:
            try:
                par = args['muted'].capitalize()
            except AttributeError:
                par = args['muted']
            muted = bool(eval(par))
        else:
            muted = False

        # This is not needed any more? All targets should be present.
        # If there are promised objects, wait until all promises have been fulfilled.
        # if self.collection.has_promises():
        #     def write_gcode_on_object(app_obj.new_object):
        #         self.log.debug("write_gcode_on_object(): Disconnecting %s" % write_gcode_on_object)
        #         self.app_obj.new_object_available.disconnect(write_gcode_on_object)
        #         write_gcode(obj_name, filename, preamble, postamble)
        #
        #     # Try again when a new object becomes available.
        #     self.log.debug("write_gcode(): Collection has promises. Queued for %s." % obj_name)
        #     self.log.debug("write_gcode(): Queued function: %s" % write_gcode_on_object)
        #     self.app_obj.new_object_available.connect(write_gcode_on_object)
        #
        #     return

        # self.log.debug("write_gcode(): No promises. Continuing for %s." % obj_name)

        try:
            obj = self.app.collection.get_by_name(str(obj_name))
        except Exception:
            if muted is False:
                return "Could not retrieve object: %s" % obj_name
            else:
                return "fail"

        try:
            obj.export_gcode(str(filename), str(preamble), str(postamble), from_tcl=True)
        except Exception as e:
            if muted is False:
                return "Operation failed: %s" % str(e)
            else:
                return
