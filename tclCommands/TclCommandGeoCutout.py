from ObjectCollection import *
from tclCommands.TclCommand import TclCommandSignaled


class TclCommandGeoCutout(TclCommandSignaled):
    """
        Tcl shell command to create a board cutout geometry. Allow cutout for any shape. Cuts holding gaps from geometry.

        example:

        """

    # List of all command aliases, to be able use old
    # names for backward compatibility (add_poly, add_polygon)
    aliases = ['geocutout', 'geoc']

    # Dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
        ('name', str),
    ])

    # Dictionary of types from Tcl command, needs to be ordered,
    # this  is  for options  like -optionname value
    option_types = collections.OrderedDict([
        ('dia', float),
        ('margin', float),
        ('gapsize', float),
        ('gaps', str)
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name']

    # structured help for current command, args needs to be ordered
    help = {
        'main': 'Creates board cutout from an object (Gerber or Geometry) of any shape',
        'args': collections.OrderedDict([
            ('name', 'Name of the object.'),
            ('dia', 'Tool diameter.'),
            ('margin', 'Margin over bounds.'),
            ('gapsize', 'size of gap.'),
            ('gaps', "type of gaps. Can be: 'tb' = top-bottom, 'lr' = left-right, '2tb' = 2top-2bottom, "
                     "'2lr' = 2left-2right, '4' = 4 cuts, '8' = 8 cuts")
        ]),
        'examples': ["      #isolate margin for example from fritzing arduino shield or any svg etc\n" +
                     "      isolate BCu_margin -dia 3 -overlap 1\n" +
                     "\n" +
                     "      #create exteriors from isolated object\n" +
                     "      exteriors BCu_margin_iso -outname BCu_margin_iso_exterior\n" +
                     "\n" +
                     "      #delete isolated object if you dond need id anymore\n" +
                     "      delete BCu_margin_iso\n" +
                     "\n" +
                     "      #finally cut holding gaps\n" +
                     "      geocutout BCu_margin_iso_exterior -dia 3 -gapsize 0.6 -gaps 4\n"]
    }

    def execute(self, args, unnamed_args):
        """

        :param args:
        :param unnamed_args:
        :return:
        """

        def subtract_rectangle(obj_, x0, y0, x1, y1):
            pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
            obj_.subtract_polygon(pts)

        if 'name' in args:
            name = args['name']
        else:
            self.app.inform.emit(
                "[WARNING]The name of the object for which cutout is done is missing. Add it and retry.")
            return

        if 'margin' in args:
            margin = args['margin']
        else:
            margin = 0.001

        if 'dia' in args:
            dia = args['dia']
        else:
            dia = 0.1

        if 'gaps' in args:
            gaps = args['gaps']
        else:
            gaps = 4

        if 'gapsize' in args:
            gapsize = args['gapsize']
        else:
            gapsize = 0.1

        # Get source object.
        try:
            cutout_obj = self.app.collection.get_by_name(str(name))
        except:
            return "Could not retrieve object: %s" % name

        if 0 in {dia}:
            self.app.inform.emit("[WARNING]Tool Diameter is zero value. Change it to a positive integer.")
            return "Tool Diameter is zero value. Change it to a positive integer."

        if gaps not in ['lr', 'tb', '2lr', '2tb', 4, 8]:
            self.app.inform.emit("[WARNING]Gaps value can be only one of: 'lr', 'tb', '2lr', '2tb', 4 or 8. "
                                 "Fill in a correct value and retry. ")
            return

        # Get min and max data for each object as we just cut rectangles across X or Y
        xmin, ymin, xmax, ymax = cutout_obj.bounds()
        px = 0.5 * (xmin + xmax) + margin
        py = 0.5 * (ymin + ymax) + margin
        lenghtx = (xmax - xmin) + (margin * 2)
        lenghty = (ymax - ymin) + (margin * 2)

        gapsize = gapsize + (dia / 2)

        if isinstance(cutout_obj, FlatCAMGeometry):
            # rename the obj name so it can be identified as cutout
            cutout_obj.options["name"] += "_cutout"
        elif isinstance(cutout_obj, FlatCAMGerber):

            def geo_init(geo_obj, app_obj):
                geo_obj.solid_geometry = obj_exteriors

            outname = cutout_obj.options["name"] + "_cutout"
            cutout_obj.isolate(dia=dia, passes=1, overlap=1, combine=False, outname="_temp")
            ext_obj = self.app.collection.get_by_name("_temp")

            try:
                obj_exteriors = ext_obj.get_exteriors()
            except:
                obj_exteriors = ext_obj.solid_geometry

            self.app.new_object('geometry', outname, geo_init)
            self.app.collection.set_all_inactive()
            self.app.collection.set_active("_temp")
            self.app.on_delete()

            cutout_obj = self.app.collection.get_by_name(outname)
        else:
            self.app.inform.emit("[ERROR]Cancelled. Object type is not supported.")
            return

        try:
            gaps_u = int(gaps)
        except ValueError:
            gaps_u = gaps

        if gaps_u == 8 or gaps_u == '2lr':
            subtract_rectangle(cutout_obj,
                               xmin - gapsize,  # botleft_x
                               py - gapsize + lenghty / 4,  # botleft_y
                               xmax + gapsize,  # topright_x
                               py + gapsize + lenghty / 4)  # topright_y
            subtract_rectangle(cutout_obj,
                               xmin - gapsize,
                               py - gapsize - lenghty / 4,
                               xmax + gapsize,
                               py + gapsize - lenghty / 4)

        if gaps_u == 8 or gaps_u == '2tb':
            subtract_rectangle(cutout_obj,
                               px - gapsize + lenghtx / 4,
                               ymin - gapsize,
                               px + gapsize + lenghtx / 4,
                               ymax + gapsize)
            subtract_rectangle(cutout_obj,
                               px - gapsize - lenghtx / 4,
                               ymin - gapsize,
                               px + gapsize - lenghtx / 4,
                               ymax + gapsize)

        if gaps_u == 4 or gaps_u == 'lr':
            subtract_rectangle(cutout_obj,
                               xmin - gapsize,
                               py - gapsize,
                               xmax + gapsize,
                               py + gapsize)

        if gaps_u == 4 or gaps_u == 'tb':
            subtract_rectangle(cutout_obj,
                               px - gapsize,
                               ymin - gapsize,
                               px + gapsize,
                               ymax + gapsize)

        cutout_obj.plot()
        self.app.inform.emit("[success]Any-form Cutout operation finished.")
