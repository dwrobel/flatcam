from tclCommands.TclCommand import TclCommand

import collections


class TclCommandDelete(TclCommand):
    """
    Tcl shell command to delete an object.

    example:

    """

    # List of all command aliases, to be able use old names for backward compatibility (add_poly, add_polygon)
    aliases = ['delete', 'del']

    description = '%s %s' % ("--", "Deletes the given object. If no name is given will delete all objects.")

    # Dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
        ('name', str),
    ])

    # Dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([
        ('f', str)
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = []

    # structured help for current command, args needs to be ordered
    help = {
        'main': 'Deletes the given object. If no name is given will delete all objects.',
        'args': collections.OrderedDict([
            ('name', 'Name of the Object.'),
            ('f', 'Use this parameter to force deletion.\n'
                  'Can be used without value which will be auto assumed to be True.\n'
                  'Or it can have a value: True (1) or False (0).')
        ]),
        'examples': ['del new_geo -f True\n'
                     'delete new_geo -f 1\n'
                     'del new_geo -f\n'
                     'del new_geo']
    }

    def execute(self, args, unnamed_args):
        """

        :param args:
        :param unnamed_args:
        :return:
        """
        obj_name = None

        try:
            obj_name = args['name']
            delete_all = False
        except KeyError:
            delete_all = True

        is_forced = False
        if 'f' in args:
            try:
                if args['f'] is None:
                    is_forced = True
                else:
                    try:
                        par = args['f'].capitalize()
                    except AttributeError:
                        par = args['f']
                    is_forced = bool(eval(par))
            except KeyError:
                is_forced = True

        if delete_all is False:
            try:
                # deselect all  to avoid delete selected object when run  delete  from  shell
                self.app.collection.set_all_inactive()
                self.app.collection.set_active(str(obj_name))
                self.app.on_delete(force_deletion=is_forced)
            except Exception as e:
                return "Command failed: %s" % str(e)
        else:
            try:
                self.app.collection.set_all_active()
                self.app.on_delete(force_deletion=is_forced)
            except Exception as e:
                return "Command failed: %s" % str(e)
