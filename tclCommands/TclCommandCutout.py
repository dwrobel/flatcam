from ObjectCollection import *
from tclCommands.TclCommand import TclCommand


class TclCommandCutout(TclCommand):
    """
    Tcl shell command to create a board cutout geometry. Rectangular shape only.

    example:

    """

    # List of all command aliases, to be able use old
    # names for backward compatibility (add_poly, add_polygon)
    aliases = ['cutout']

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
        'main': 'Creates board cutout from an object (Gerber or Geometry) with a rectangular shape',
        'args': collections.OrderedDict([
            ('name', 'Name of the object.'),
            ('dia', 'Tool diameter. Default = 0.1'),
            ('margin', 'Margin over bounds. Default = 0.001'),
            ('gapsize', 'Size of gap. Default = 0.1'),
            ('gaps', "Type of gaps. Can be: 'tb' = top-bottom, 'lr' = left-right and '4' = one each side. Default = 4"),
        ]),
        'examples': []
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
            margin_par = args['margin']
        else:
            margin_par = 0.001

        if 'dia' in args:
            dia_par = args['dia']
        else:
            dia_par = 0.1

        if 'gaps' in args:
            gaps_par = args['gaps']
        else:
            gaps_par = 4

        if 'gapsize' in args:
            gapsize_par = args['gapsize']
        else:
            gapsize_par = 0.1

        try:
            obj = self.app.collection.get_by_name(str(name))
        except:
            return "Could not retrieve object: %s" % name

        def geo_init_me(geo_obj, app_obj):
            margin =  margin_par + dia_par / 2
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
            geo_obj.solid_geometry = cascaded_union([LineString(segment) for segment in cuts])

        try:
            self.app.new_object("geometry", name + "_cutout", geo_init_me)
            self.app.inform.emit("[success] Rectangular-form Cutout operation finished.")
        except Exception as e:
            return "Operation failed: %s" % str(e)
