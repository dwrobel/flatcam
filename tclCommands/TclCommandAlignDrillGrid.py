from ObjectCollection import *
import TclCommand


class TclCommandAlignDrillGrid(TclCommand.TclCommandSignaled):
    """
    Tcl shell command to create an Excellon object
    with drills for aligment grid.

    Todo: What is an alignment grid?
    """

    # array of all command aliases, to be able use  old names for
    # backward compatibility (add_poly, add_polygon)
    aliases = ['aligndrillgrid']

    # Dictionary of types from Tcl command, needs to be ordered.
    # For positional arguments
    arg_names = collections.OrderedDict([
        ('outname', str)
    ])

    # Dictionary of types from Tcl command, needs to be ordered.
    # For options like -optionname value
    option_types = collections.OrderedDict([
        ('dia', float),
        ('gridx', float),
        ('gridxoffset', float),
        ('gridy', float),
        ('gridyoffset', float),
        ('columns', int),
        ('rows', int)
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['outname', 'gridx', 'gridy', 'columns', 'rows']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Create excellon with drills for aligment grid.",
        'args': collections.OrderedDict([
            ('outname', 'Name of the object to create.'),
            ('dia', 'Tool diameter.'),
            ('gridx', 'Grid size in X axis.'),
            ('gridoffsetx', 'Move grid  from origin.'),
            ('gridy', 'Grid size in Y axis.'),
            ('gridoffsety', 'Move grid  from origin.'),
            ('colums', 'Number of grid holes on X axis.'),
            ('rows', 'Number of grid holes on Y axis.'),
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

        if 'gridoffsetx' not in args:
            gridoffsetx = 0
        else:
            gridoffsetx = args['gridoffsetx']

        if 'gridoffsety' not in args:
            gridoffsety = 0
        else:
            gridoffsety = args['gridoffsety']

        # Tools
        tools = {"1": {"C": args['dia']}}

        def aligndrillgrid_init_me(init_obj, app_obj):
            """
            This function is used to initialize the new
            object once it's created.

            :param init_obj: The new object.
            :param app_obj: The application (FlatCAMApp)
            :return: None
            """

            drills = []
            currenty = 0

            for row in range(args['rows']):
                currentx = 0

                for col in range(args['columns']):
                    point = Point(currentx + gridoffsetx, currenty + gridoffsety)
                    drills.append({"point": point, "tool": "1"})
                    currentx = currentx + args['gridx']

                currenty = currenty + args['gridy']

            init_obj.tools = tools
            init_obj.drills = drills
            init_obj.create_geometry()

        # Create the new object
        self.new_object("excellon", args['outname'], aligndrillgrid_init_me)
