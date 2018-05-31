from tclCommands.TclCommand import *


class TclCommandDelete(TclCommand):
    """
    Tcl shell command to delete an object.

    example:

    """

    # List of all command aliases, to be able use old names for backward compatibility (add_poly, add_polygon)
    aliases = ['delete']

    # Dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
        ('name', str),
    ])

    # Dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([

    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name']

    # structured help for current command, args needs to be ordered
    help = {
        'main': 'Deletes the given object.',
        'args': collections.OrderedDict([
            ('name', 'Name of the Object.'),
        ]),
        'examples': []
    }

    def execute(self, args, unnamed_args):
        """

        :param args:
        :param unnamed_args:
        :return:
        """

        obj_name = args['name']

        try:
            # deselect all  to avoid delete selected object when run  delete  from  shell
            self.app.collection.set_all_inactive()
            self.app.collection.set_active(str(obj_name))
            self.app.on_delete()  # Todo: This is an event handler for the GUI... bad?
        except Exception as e:
            return "Command failed: %s" % str(e)
