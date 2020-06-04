from tclCommands.TclCommand import TclCommand
import collections
import logging

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class TclCommandBounds(TclCommand):
    """
    Tcl shell command to return the bounds values for a supplied list of objects (identified by their names).
    example:

    """

    # List of all command aliases, to be able use old names for backward compatibility (add_poly, add_polygon)
    aliases = ['get_bounds', 'bounds']

    description = '%s %s' % ("--", "Return in the console a list of bounds values for a list of objects.")

    # Dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
        ('objects', str)
    ])

    # Dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = []

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Will return a list of bounds values, each set of bound values is "
                "a list itself: [xmin, ymin, xmax, ymax] corresponding to each of the provided objects.",
        'args': collections.OrderedDict([
            ('objects', 'A list of object names separated by comma without spaces.'),
        ]),
        'examples': ['bounds a_obj.GTL,b_obj.DRL']
    }

    def execute(self, args, unnamed_args):
        """

        :param args:
        :param unnamed_args:
        :return:
        """

        obj_list = []
        if 'objects' in args:
            try:
                obj_list = [str(obj_name) for obj_name in str(args['objects']).split(",") if obj_name != '']
            except AttributeError as e:
                log.debug("TclCommandBounds.execute --> %s" % str(e))

            if not obj_list:
                self.raise_tcl_error('%s: %s:' % (
                    _("Expected a list of objects names separated by comma. Got"), str(args['objects'])))
                return 'fail'
        else:
            self.raise_tcl_error('%s: %s:' % (
                _("Expected a list of objects names separated by comma. Got"), str(args['objects'])))
            return 'fail'

        result_list = []
        for name in obj_list:
            obj = self.app.collection.get_by_name(name)

            xmin, ymin, xmax, ymax = obj.bounds()
            result_list.append([xmin, ymin, xmax, ymax])

        self.app.inform.emit('[success] %s ...' % _('TclCommand Bounds done.'))

        return result_list
