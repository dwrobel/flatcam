from tclCommands.TclCommand import TclCommandSignaled

import logging
import collections
from copy import deepcopy
from shapely.ops import unary_union
from shapely.geometry import Polygon, LineString, LinearRing

import gettext
import appTranslation as fcTranslate
import builtins

log = logging.getLogger('base')

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class TclCommandGeoCutout(TclCommandSignaled):
    """
        Tcl shell command to create a board cutout geometry.
        Allow cutout for any shape.
        Cuts holding gaps from geometry.

        example:

        """

    # List of all command aliases, to be able use old
    # names for backward compatibility (add_poly, add_polygon)
    aliases = ['geocutout', 'geoc']

    description = '%s %s' % ("--", "Creates board cutout from an object (Gerber or Geometry) of any shape.")

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
        ('gaps', str),
        ('outname', str)
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name']

    # structured help for current command, args needs to be ordered
    help = {
        'main': 'Creates board cutout from an object (Gerber or Geometry) of any shape.',
        'args': collections.OrderedDict([
            ('name', 'Name of the object to be cutout. Required'),
            ('dia', 'Tool diameter.'),
            ('margin', 'Margin over bounds.'),
            ('gapsize', 'size of gap.'),
            ('gaps', "type of gaps. Can be: 'tb' = top-bottom, 'lr' = left-right, '2tb' = 2top-2bottom, "
                     "'2lr' = 2left-2right, '4' = 4 cuts, '8' = 8 cuts"),
            ('outname', 'Name of the resulting Geometry object.'),
        ]),
        'examples': ["      #isolate margin for example from Fritzing arduino shield or any svg etc\n" +
                     "      isolate BCu_margin -dia 3 -overlap 1\n" +
                     "\n" +
                     "      #create exteriors from isolated object\n" +
                     "      exteriors BCu_margin_iso -outname BCu_margin_iso_exterior\n" +
                     "\n" +
                     "      #delete isolated object if you dond need id anymore\n" +
                     "      delete BCu_margin_iso\n" +
                     "\n" +
                     "      #finally cut holding gaps\n" +
                     "      geocutout BCu_margin_iso_exterior -dia 3 -gapsize 0.6 -gaps 4 -outname cutout_geo\n"]
    }

    flat_geometry = []

    def execute(self, args, unnamed_args):
        """

        :param args:
        :param unnamed_args:
        :return:
        """

        # def subtract_rectangle(obj_, x0, y0, x1, y1):
        #     pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        #     obj_.subtract_polygon(pts)

        def substract_rectangle_geo(geo, x0, y0, x1, y1):
            pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]

            def flatten(geometry=None, reset=True, pathonly=False):
                """
                Creates a list of non-iterable linear geometry objects.
                Polygons are expanded into its exterior and interiors if specified.

                Results are placed in flat_geometry

                :param geometry: Shapely type or list or list of list of such.
                :param reset: Clears the contents of self.flat_geometry.
                :param pathonly: Expands polygons into linear elements.
                """

                if reset:
                    self.flat_geometry = []

                # If iterable, expand recursively.
                try:
                    for geo_el in geometry:
                        if geo_el is not None:
                            flatten(geometry=geo_el,
                                    reset=False,
                                    pathonly=pathonly)

                # Not iterable, do the actual indexing and add.
                except TypeError:
                    if pathonly and type(geometry) == Polygon:
                        self.flat_geometry.append(geometry.exterior)
                        flatten(geometry=geometry.interiors,
                                reset=False,
                                pathonly=True)
                    else:
                        self.flat_geometry.append(geometry)

                return self.flat_geometry

            flat_geometry = flatten(geo, pathonly=True)

            polygon = Polygon(pts)
            toolgeo = unary_union(polygon)
            diffs = []
            for target in flat_geometry:
                if type(target) == LineString or type(target) == LinearRing:
                    diffs.append(target.difference(toolgeo))
                else:
                    log.warning("Not implemented.")
            return unary_union(diffs)

        if 'name' in args:
            name = args['name']
        else:
            self.app.inform.emit(
                "[WARNING] %s" % _("The name of the object for which cutout is done is missing. Add it and retry."))
            return

        if 'margin' in args:
            margin = float(args['margin'])
        else:
            margin = float(self.app.defaults["tools_cutout_margin"])

        if 'dia' in args:
            dia = float(args['dia'])
        else:
            dia = float(self.app.defaults["tools_cutout_tooldia"])

        if 'gaps' in args:
            gaps = args['gaps']
        else:
            gaps = str(self.app.defaults["tools_cutout_gaps_ff"])

        if 'gapsize' in args:
            gapsize = float(args['gapsize'])
        else:
            gapsize = float(self.app.defaults["tools_cutout_gapsize"])

        if 'outname' in args:
            outname = args['outname']
        else:
            outname = str(name) + "_cutout"

        # Get source object.
        try:
            cutout_obj = self.app.collection.get_by_name(str(name))
        except Exception as e:
            log.debug("TclCommandGeoCutout --> %s" % str(e))
            return "Could not retrieve object: %s" % name

        if 0 in {dia}:
            self.app.inform.emit(
                "[WARNING] %s" % _("Tool Diameter is zero value. Change it to a positive real number."))
            return "Tool Diameter is zero value. Change it to a positive real number."

        if gaps not in ['lr', 'tb', '2lr', '2tb', '4', '8']:
            self.app.inform.emit(
                "[WARNING] %s" % _("Gaps value can be only one of: 'lr', 'tb', '2lr', '2tb', 4 or 8."))
            return

        # Get min and max data for each object as we just cut rectangles across X or Y
        xmin, ymin, xmax, ymax = cutout_obj.bounds()
        cutout_obj.options['xmin'] = xmin
        cutout_obj.options['ymin'] = ymin
        cutout_obj.options['xmax'] = xmax
        cutout_obj.options['ymax'] = ymax

        px = 0.5 * (xmin + xmax) + margin
        py = 0.5 * (ymin + ymax) + margin
        lenghtx = (xmax - xmin) + (margin * 2)
        lenghty = (ymax - ymin) + (margin * 2)

        gapsize = gapsize / 2 + (dia / 2)

        try:
            gaps_u = int(gaps)
        except ValueError:
            gaps_u = gaps

        if cutout_obj.kind == 'geometry':
            # rename the obj name so it can be identified as cutout
            # cutout_obj.options["name"] += "_cutout"

            # if gaps_u == 8 or gaps_u == '2lr':
            #     subtract_rectangle(cutout_obj,
            #                        xmin - gapsize,  # botleft_x
            #                        py - gapsize + lenghty / 4,  # botleft_y
            #                        xmax + gapsize,  # topright_x
            #                        py + gapsize + lenghty / 4)  # topright_y
            #     subtract_rectangle(cutout_obj,
            #                        xmin - gapsize,
            #                        py - gapsize - lenghty / 4,
            #                        xmax + gapsize,
            #                        py + gapsize - lenghty / 4)
            #
            # if gaps_u == 8 or gaps_u == '2tb':
            #     subtract_rectangle(cutout_obj,
            #                        px - gapsize + lenghtx / 4,
            #                        ymin - gapsize,
            #                        px + gapsize + lenghtx / 4,
            #                        ymax + gapsize)
            #     subtract_rectangle(cutout_obj,
            #                        px - gapsize - lenghtx / 4,
            #                        ymin - gapsize,
            #                        px + gapsize - lenghtx / 4,
            #                        ymax + gapsize)
            #
            # if gaps_u == 4 or gaps_u == 'lr':
            #     subtract_rectangle(cutout_obj,
            #                        xmin - gapsize,
            #                        py - gapsize,
            #                        xmax + gapsize,
            #                        py + gapsize)
            #
            # if gaps_u == 4 or gaps_u == 'tb':
            #     subtract_rectangle(cutout_obj,
            #                        px - gapsize,
            #                        ymin - gapsize,
            #                        px + gapsize,
            #                        ymax + gapsize)

            def geo_init(geo_obj, app_obj):
                geo = deepcopy(cutout_obj.solid_geometry)

                if gaps_u == 8 or gaps_u == '2lr':
                    geo = substract_rectangle_geo(geo,
                                                  xmin - gapsize,  # botleft_x
                                                  py - gapsize + lenghty / 4,  # botleft_y
                                                  xmax + gapsize,  # topright_x
                                                  py + gapsize + lenghty / 4)  # topright_y
                    geo = substract_rectangle_geo(geo,
                                                  xmin - gapsize,
                                                  py - gapsize - lenghty / 4,
                                                  xmax + gapsize,
                                                  py + gapsize - lenghty / 4)

                if gaps_u == 8 or gaps_u == '2tb':
                    geo = substract_rectangle_geo(geo,
                                                  px - gapsize + lenghtx / 4,
                                                  ymin - gapsize,
                                                  px + gapsize + lenghtx / 4,
                                                  ymax + gapsize)
                    geo = substract_rectangle_geo(geo,
                                                  px - gapsize - lenghtx / 4,
                                                  ymin - gapsize,
                                                  px + gapsize - lenghtx / 4,
                                                  ymax + gapsize)

                if gaps_u == 4 or gaps_u == 'lr':
                    geo = substract_rectangle_geo(geo,
                                                  xmin - gapsize,
                                                  py - gapsize,
                                                  xmax + gapsize,
                                                  py + gapsize)

                if gaps_u == 4 or gaps_u == 'tb':
                    geo = substract_rectangle_geo(geo,
                                                  px - gapsize,
                                                  ymin - gapsize,
                                                  px + gapsize,
                                                  ymax + gapsize)
                geo_obj.solid_geometry = deepcopy(geo)
                geo_obj.options['xmin'] = cutout_obj.options['xmin']
                geo_obj.options['ymin'] = cutout_obj.options['ymin']
                geo_obj.options['xmax'] = cutout_obj.options['xmax']
                geo_obj.options['ymax'] = cutout_obj.options['ymax']

                app_obj.disable_plots(objects=[cutout_obj])

                app_obj.inform.emit("[success] %s" % _("Any-form Cutout operation finished."))

            self.app.app_obj.new_object('geometry', outname, geo_init, plot=False)

        elif cutout_obj.kind == 'gerber':

            def geo_init(geo_obj, app_obj):
                try:
                    geo = cutout_obj.isolation_geometry((dia / 2), iso_type=0, corner=2, follow=None)
                except Exception as exc:
                    log.debug("TclCommandGeoCutout.execute() --> %s" % str(exc))
                    return 'fail'

                if gaps_u == 8 or gaps_u == '2lr':
                    geo = substract_rectangle_geo(geo,
                                                  xmin - gapsize,  # botleft_x
                                                  py - gapsize + lenghty / 4,  # botleft_y
                                                  xmax + gapsize,  # topright_x
                                                  py + gapsize + lenghty / 4)  # topright_y
                    geo = substract_rectangle_geo(geo,
                                                  xmin - gapsize,
                                                  py - gapsize - lenghty / 4,
                                                  xmax + gapsize,
                                                  py + gapsize - lenghty / 4)

                if gaps_u == 8 or gaps_u == '2tb':
                    geo = substract_rectangle_geo(geo,
                                                  px - gapsize + lenghtx / 4,
                                                  ymin - gapsize,
                                                  px + gapsize + lenghtx / 4,
                                                  ymax + gapsize)
                    geo = substract_rectangle_geo(geo,
                                                  px - gapsize - lenghtx / 4,
                                                  ymin - gapsize,
                                                  px + gapsize - lenghtx / 4,
                                                  ymax + gapsize)

                if gaps_u == 4 or gaps_u == 'lr':
                    geo = substract_rectangle_geo(geo,
                                                  xmin - gapsize,
                                                  py - gapsize,
                                                  xmax + gapsize,
                                                  py + gapsize)

                if gaps_u == 4 or gaps_u == 'tb':
                    geo = substract_rectangle_geo(geo,
                                                  px - gapsize,
                                                  ymin - gapsize,
                                                  px + gapsize,
                                                  ymax + gapsize)
                geo_obj.solid_geometry = deepcopy(geo)
                geo_obj.options['xmin'] = cutout_obj.options['xmin']
                geo_obj.options['ymin'] = cutout_obj.options['ymin']
                geo_obj.options['xmax'] = cutout_obj.options['xmax']
                geo_obj.options['ymax'] = cutout_obj.options['ymax']
                app_obj.inform.emit("[success] %s" % _("Any-form Cutout operation finished."))

            self.app.app_obj.new_object('geometry', outname, geo_init, plot=False)

            cutout_obj = self.app.collection.get_by_name(outname)
        else:
            self.app.inform.emit("[ERROR] %s" % _("Cancelled. Object type is not supported."))
            return
