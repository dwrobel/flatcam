
# from matplotlib.colors import LinearSegmentedColormap
from tclCommands.TclCommand import TclCommand

import collections
from copy import deepcopy

from shapely import box
from shapely.ops import linemerge
from camlib import flatten_shapely_geometry


class TclCommandCutout(TclCommand):
    """
    Tcl shell command to create a board cutout geometry.

    example:
        cutout cut_object -dia 1.2 -margin 0.1 -gapsize 1 -gaps "tb" -outname cutout_geo -type rect

    """

    # List of all command aliases, to be able to use old
    # names for backward compatibility (add_poly, add_polygon)
    aliases = ['cutout', 'geocutout']

    description = '%s %s' % ("--", "Creates board cutout from an outline object (Gerber or Geometry).")

    # Dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
        ('name', str),
    ])

    # Dictionary of types from Tcl command, needs to be ordered,
    # this  is  for options  like -optionname value
    option_types = collections.OrderedDict([
        ('type', str),
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
        'main': 'Creates board cutout from an object (Gerber or Geometry).',
        'args': collections.OrderedDict([
            ('name', 'Name of the object.'),
            ('type', "Type of cutout. Can be: 'rect' or 'any'. default: any"),
            ('dia', 'Tool diameter.'),
            ('margin', 'Margin over bounds.'),
            ('gapsize', 'Size of gap.'),
            ('gaps', "Type of gaps. Can be (case-insensitive): 'None' = no-tabs, 'TB' = top-bottom, 'LR' = left-right, "
                     "'2TB' = 2-top-bottom, '2LR' = 2-left-right, '4' = one each side, and '8' = two each side."),
            ('outname', 'Name of the object to create.')
        ]),
        'examples': ['cutout cut_object -dia 1.2 -margin 0.1 -gapsize 1 -gaps "tb" -outname cutout_geo -type rect']
    }

    def execute(self, args, unnamed_args):
        """

        :param args:
        :param unnamed_args:
        :return:
        """

        if 'name' in args:
            name = args['name']
        else:
            self.app.log.warning(
                "[WARNING] The name of the object for which cutout is done is missing. Add it and retry.")
            return "fail"

        if 'margin' in args:
            margin_par = float(args['margin'])
        else:
            margin_par = float(self.app.options["tools_cutout_margin"])

        if 'dia' in args:
            dia_par = float(args['dia'])
        else:
            dia_par = float(self.app.options["tools_cutout_tooldia"])

        if 'gaps' in args:
            if str(args['gaps']).lower() not in ["none", "tb", "lr", "2tb", "2lr", "4", "8"]:
                error_msg = "Incorrect -gaps values. " \
                            "Can be only a string from: 'none', 'tb', 'lr', '2tb', '2lr', '4', and '8'."
                self.raise_tcl_error(error_msg)
                return "fail"
            gaps_par = str(args['gaps'])
        else:
            gaps_par = str(self.app.options["tools_cutout_gaps_ff"])

        if 'gapsize' in args:
            gapsize_par = float(args['gapsize'])
        else:
            gapsize_par = float(self.app.options["tools_cutout_gapsize"])

        if 'outname' in args:
            outname = args['outname']
        else:
            outname = name + "_cutout"

        if 'type' in args:
            if args['type'] not in ['rect', 'any']:
                self.raise_tcl_error("Incorrect -type value. Can only an be: 'rect', 'any'. default: any")
                return 'fail'
            type_par = args['type']
        else:
            self.app.log.info("No type value specified. Using default: any.")
            type_par = 'any'

        try:
            cutout_obj = self.app.collection.get_by_name(str(name))
        except Exception as e:
            self.app.log.error("TclCommandCutout.execute(). Missing object: --> %s" % str(e))
            self.app.log.debug("Could not retrieve object: %s" % name)
            return "fail"

        def geo_init_me(geo_obj, app_obj):
            geo_obj.multigeo = True
            solid_geo = []

            gapsize = gapsize_par + dia_par

            xmin, ymin, xmax, ymax = cutout_obj.bounds()
            if type_par == 'rect':
                cutout_geom = flatten_shapely_geometry(box(xmin, ymin, xmax, ymax))
            else:
                cutout_geom = flatten_shapely_geometry(cutout_obj.solid_geometry)

            for geom_struct in cutout_geom:
                if cutout_obj.kind == 'gerber':
                    if margin_par >= 0:
                        geom_struct = (geom_struct.buffer(margin_par + abs(dia_par / 2))).exterior
                    else:
                        geom_struct_buff = geom_struct.buffer(-margin_par + abs(dia_par / 2))
                        geom_struct = geom_struct_buff.interiors

                if type_par == 'rect':
                    solid_geo = self.app.cutout_tool.rect_cutout_handler(
                        geom_struct, dia_par, gaps_par, gapsize, margin_par, xmin, ymin, xmax, ymax)
                else:
                    solid_geo, r_geo = self.app.cutout_tool.any_cutout_handler(
                        geom_struct, dia_par, gaps_par, gapsize, margin_par)

            if not solid_geo:
                self.app.log.debug("TclCommandCutout.geo_init_me() -> Empty solid geometry.")
                self.app.log.error('[ERROR] %s' % "Failed.")
                return "fail"

            try:
                solid_geo = linemerge(solid_geo)
            except Exception:
                # there are not lines but polygon
                pass

            geo_obj.solid_geometry = solid_geo

            if not geo_obj.solid_geometry:
                app_obj.log("TclCommandCutout.execute(). No geometry after cutout.")
                return "fail"

            default_tool_data = self.app.options.copy()

            geo_obj.tools = {
                1: {
                    'tooldia': dia_par,
                    'data': default_tool_data,
                    'solid_geometry': deepcopy(geo_obj.solid_geometry)
                }
            }
            geo_obj.tools[1]['data']['tools_cutout_tooldia'] = dia_par
            geo_obj.tools[1]['data']['tools_cutout_gaps_ff'] = gaps_par
            geo_obj.tools[1]['data']['tools_cutout_margin'] = margin_par
            geo_obj.tools[1]['data']['tools_cutout_gapsize'] = gapsize_par

        try:
            ret = self.app.app_obj.new_object("geometry", outname, geo_init_me, plot=False)
            if ret == 'fail':
                self.app.log.error("Could not create a cutout Geometry object.")
                return "fail"
            self.app.log.info("[success] Cutout operation finished.")
        except Exception as e:
            self.app.log.error("Cutout operation failed: %s" % str(e))
            return "fail"
