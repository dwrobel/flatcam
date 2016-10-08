from ObjectCollection import *
import TclCommand


class TclCommandMillHoles(TclCommand.TclCommandSignaled):
    """
    Tcl shell command to Create Geometry Object for milling holes from Excellon.

    example:
        millholes my_drill -tools 1,2,3 -tooldia 0.1 -outname mill_holes_geo
    """

    # List of all command aliases, to be able use old names for backward compatibility (add_poly, add_polygon)
    aliases = ['millholes']

    # Dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
        ('name', str),
        ('tools', str),
        ('tooldia', float),
        ('outname', str)
    ])

    # Dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([

    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Create Geometry Object for milling holes from Excellon.",
        'args': collections.OrderedDict([
            ('name', 'Name of the Excellon Object.'),
            ('tools', 'Comma separated indexes of tools (example: 1,3 or 2).'),
            ('tooldia', 'Diameter of the milling tool (example: 0.1).'),
            ('outname', 'Name of object to create.')
        ]),
        'examples': ['scale my_geometry 4.2']
    }

    def execute(self, args, unnamed_args):
        """

        :param args:
        :param unnamed_args:
        :return:
        """

        name = args['name']

        try:
            if 'tools' in args:
                # Split and put back. We are passing the whole dictionary later.
                args['tools'] = [x.strip() for x in args['tools'].split(",")]
        except Exception as e:
            self.raise_tcl_error("Bad tools: %s" % str(e))

        try:
            obj = self.app.collection.get_by_name(str(name))
        except:
            self.raise_tcl_error("Could not retrieve object: %s" % name)

        if not isinstance(obj, FlatCAMExcellon):
            self.raise_tcl_error('Only Excellon objects can be mill-drilled, got %s %s.' % (name, type(obj)))

        try:
            # This runs in the background... Is blocking handled?
            success, msg = obj.generate_milling(**args)

        except Exception as e:
            self.raise_tcl_error("Operation failed: %s" % str(e))

        if not success:
            self.raise_tcl_error(msg)
