from ObjectCollection import *
from copy import copy,deepcopy

from tclCommands.TclCommand import TclCommand


class TclCommandPanelize(TclCommand):
    """
    Tcl shell command to panelize an object.

    example:

    """

    # List of all command aliases, to be able use old names for backward compatibility (add_poly, add_polygon)
    aliases = ['panelize','pan', 'panel']

    # Dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
        ('name', str),
    ])

    # Dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([
        ('rows', int),
        ('columns', int),
        ('spacing_columns', float),
        ('spacing_rows', float),
        ('box', str),
        ('outname', str)
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name', 'rows', 'columns']

    # structured help for current command, args needs to be ordered
    help = {
        'main': 'Rectangular panelizing.',
        'args': collections.OrderedDict([
            ('name', 'Name of the object to panelize.'),
            ('box', 'Name of object which acts as box (cutout for example.)'
                    'for cutout boundary. Object from name is used if not specified.'),
            ('spacing_columns', 'Spacing between columns.'),
            ('spacing_rows', 'Spacing between rows.'),
            ('columns', 'Number of columns.'),
            ('rows', 'Number of rows;'),
            ('outname', 'Name of the new geometry object.')
        ]),
        'examples': []
    }

    def execute(self, args, unnamed_args):
        """

        :param args:
        :param unnamed_args:
        :return:
        """

        name = args['name']

        # Get source object.
        try:
            obj = self.app.collection.get_by_name(str(name))
        except:
            return "Could not retrieve object: %s" % name

        if obj is None:
            return "Object not found: %s" % name

        if 'box' in args:
            boxname = args['box']
            try:
                box = self.app.collection.get_by_name(boxname)
            except:
                return "Could not retrieve object: %s" % name
        else:
            box = obj

        if 'columns' not in args or 'rows' not in args:
            return "ERROR: Specify -columns and -rows"

        if 'outname' in args:
            outname = args['outname']
        else:
            outname = name + '_panelized'

        if 'spacing_columns' in args:
            spacing_columns = args['spacing_columns']
        else:
            spacing_columns = 5

        if 'spacing_rows' in args:
            spacing_rows = args['spacing_rows']
        else:
            spacing_rows = 5

        xmin, ymin, xmax, ymax = box.bounds()
        lenghtx = xmax - xmin + spacing_columns
        lenghty = ymax - ymin + spacing_rows

        currenty = 0

        def initialize_local(obj_init, app):
            obj_init.solid_geometry = obj.solid_geometry
            obj_init.offset([float(currentx), float(currenty)])
            objs.append(obj_init)

        def initialize_local_excellon(obj_init, app):
            obj_init.tools = obj.tools
            # drills are offset, so they need to be deep copied
            obj_init.drills = deepcopy(obj.drills) 
            obj_init.offset([float(currentx), float(currenty)])
            obj_init.create_geometry()
            objs.append(obj_init)

        def initialize_geometry(obj_init, app):
            FlatCAMGeometry.merge(objs, obj_init)

        def initialize_excellon(obj_init, app):
            # merge expects tools to exist in the target object
            obj_init.tools = obj.tools.copy()
            FlatCAMExcellon.merge(objs, obj_init)

        objs = []
        if obj is not None:           

            for row in range(args['rows']):
                currentx = 0
                for col in range(args['columns']):
                    local_outname = outname + ".tmp." + str(col) + "." + str(row)
                    if isinstance(obj, FlatCAMExcellon):
                        self.app.new_object("excellon", local_outname, initialize_local_excellon, plot=False,
                                            autoselected=False)
                    else:
                        self.app.new_object("geometry", local_outname, initialize_local, plot=False, autoselected=False)

                    currentx += lenghtx
                currenty += lenghty

            if isinstance(obj, FlatCAMExcellon):
                self.app.new_object("excellon", outname, initialize_excellon)
            else:
                self.app.new_object("geometry", outname, initialize_geometry)

            # deselect all  to avoid  delete selected object when run  delete  from  shell
            self.app.collection.set_all_inactive()
            for delobj in objs:
                self.app.collection.set_active(delobj.options['name'])
                self.app.on_delete()
        else:
            return "ERROR: obj is None"

        return "Ok"
