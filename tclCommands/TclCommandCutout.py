from tclCommands.TclCommand import TclCommand

import collections
import logging

from shapely.ops import unary_union
from shapely.geometry import LineString

log = logging.getLogger('base')


class TclCommandCutout(TclCommand):
    """
    Tcl shell command to create a board cutout geometry. Rectangular shape only.

    example:

    """

    # List of all command aliases, to be able use old
    # names for backward compatibility (add_poly, add_polygon)
    aliases = ['cutout']

    description = '%s %s' % ("--", "Creates board cutout from an object (Gerber or Geometry) with a rectangular shape.")

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
        'main': 'Creates board cutout from an object (Gerber or Geometry) with a rectangular shape.',
        'args': collections.OrderedDict([
            ('name', 'Name of the object.'),
            ('dia', 'Tool diameter.'),
            ('margin', 'Margin over bounds.'),
            ('gapsize', 'Size of gap.'),
            ('gaps', "Type of gaps. Can be: 'tb' = top-bottom, 'lr' = left-right and '4' = one each side."),
            ('outname', 'Name of the object to create.')
        ]),
        'examples': ['cutout new_geo -dia 1.2 -margin 0.1 -gapsize 1 -gaps "tb" -outname cut_geo']
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
            self.app.inform.emit(
                "[WARNING]The name of the object for which cutout is done is missing. Add it and retry.")
            return

        if 'margin' in args:
            margin_par = float(args['margin'])
        else:
            margin_par = float(self.app.defaults["tools_cutout_margin"])

        if 'dia' in args:
            dia_par = float(args['dia'])
        else:
            dia_par = float(self.app.defaults["tools_cutout_tooldia"])

        if 'gaps' in args:
            gaps_par = args['gaps']
        else:
            gaps_par = str(self.app.defaults["tools_cutout_gaps_ff"])

        if 'gapsize' in args:
            gapsize_par = float(args['gapsize'])
        else:
            gapsize_par = float(self.app.defaults["tools_cutout_gapsize"])

        if 'outname' in args:
            outname = args['outname']
        else:
            outname = name + "_cutout"

        try:
            obj = self.app.collection.get_by_name(str(name))
        except Exception as e:
            log.debug("TclCommandCutout.execute() --> %s" % str(e))
            return "Could not retrieve object: %s" % name

        def geo_init_me(geo_obj, app_obj):
            margin = margin_par + dia_par / 2
            gap_size = dia_par + gapsize_par

            minx, miny, maxx, maxy = obj.bounds()
            minx -= margin
            maxx += margin
            miny -= margin
            maxy += margin
            midx = 0.5 * (minx + maxx)
            midy = 0.5 * (miny + maxy)
            hgap = 0.5 * gap_size
            pts = [[midx - hgap, maxy],
                   [minx, maxy],
                   [minx, midy + hgap],
                   [minx, midy - hgap],
                   [minx, miny],
                   [midx - hgap, miny],
                   [midx + hgap, miny],
                   [maxx, miny],
                   [maxx, midy - hgap],
                   [maxx, midy + hgap],
                   [maxx, maxy],
                   [midx + hgap, maxy]]
            cases = {"tb": [[pts[0], pts[1], pts[4], pts[5]],
                            [pts[6], pts[7], pts[10], pts[11]]],
                     "lr": [[pts[9], pts[10], pts[1], pts[2]],
                            [pts[3], pts[4], pts[7], pts[8]]],
                     "4": [[pts[0], pts[1], pts[2]],
                           [pts[3], pts[4], pts[5]],
                           [pts[6], pts[7], pts[8]],
                           [pts[9], pts[10], pts[11]]]}
            cuts = cases[gaps_par]
            geo_obj.solid_geometry = unary_union([LineString(segment) for segment in cuts])

        try:
            self.app.app_obj.new_object("geometry", outname, geo_init_me, plot=False)
            self.app.inform.emit("[success] Rectangular-form Cutout operation finished.")
        except Exception as e:
            return "Operation failed: %s" % str(e)
