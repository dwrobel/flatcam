from tclCommands.TclCommand import TclCommand

import collections
import logging

import gettext
import FlatCAMTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class TclCommandPaint(TclCommand):
    """
    Paint the interior of polygons
    """

    # Array of all command aliases, to be able use old names for backward compatibility (add_poly, add_polygon)
    aliases = ['paint']

    # dictionary of types from Tcl command, needs to be ordered
    arg_names = collections.OrderedDict([
        ('name', str),
    ])

    # dictionary of types from Tcl command, needs to be ordered , this  is  for options  like -optionname value
    option_types = collections.OrderedDict([
        ('tooldia', str),
        ('overlap', float),
        ('order', str),
        ('margin', float),
        ('method', str),
        ('connect', bool),
        ('contour', bool),

        ('all', bool),
        ('single', bool),
        ('ref', bool),
        ('box', str),
        ('x', float),
        ('y', float),
        ('outname', str),
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Paint polygons",
        'args': collections.OrderedDict([
            ('name', 'Name of the source Geometry object. String.'),
            ('tooldia', 'Diameter of the tool to be used. Can be a comma separated list of diameters. No space is '
                        'allowed between tool diameters. E.g: correct: 0.5,1 / incorrect: 0.5, 1'),
            ('overlap', 'Fraction of the tool diameter to overlap cuts. Float number.'),
            ('margin', 'Bounding box margin. Float number.'),
            ('order', 'Can have the values: "no", "fwd" and "rev". String.'
                      'It is useful when there are multiple tools in tooldia parameter.'
                      '"no" -> the order used is the one provided.'
                      '"fwd" -> tools are ordered from smallest to biggest.'
                      '"rev" -> tools are ordered from biggest to smallest.'),
            ('method', 'Algorithm for painting. Can be: "standard", "seed" or "lines".'),
            ('connect', 'Draw lines to minimize tool lifts. True or False'),
            ('contour', 'Cut around the perimeter of the painting. True or False'),
            ('all', 'Paint all polygons in the object. True or False'),
            ('single', 'Paint a single polygon specified by "x" and "y" parameters. True or False'),
            ('ref', 'Paint all polygons within a specified object with the name in "box" parameter. True or False'),
            ('box', 'name of the object to be used as paint reference when selecting "ref"" True. String.'),
            ('x', 'X value of coordinate for the selection of a single polygon. Float number.'),
            ('y', 'Y value of coordinate for the selection of a single polygon. Float number.'),
            ('outname', 'Name of the resulting Geometry object. String.'),
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

        name = args['name']

        # Get source object.
        try:
            obj = self.app.collection.get_by_name(str(name))
        except Exception as e:
            log.debug("TclCommandPaint.execute() --> %s" % str(e))
            self.raise_tcl_error("%s: %s" % (_("Could not retrieve object"), name))
            return "Could not retrieve object: %s" % name

        if 'tooldia' in args:
            tooldia = str(args['tooldia'])
        else:
            tooldia = float(self.app.defaults["tools_paintoverlap"])

        if 'overlap' in args:
            overlap = float(args['overlap'])
        else:
            overlap = float(self.app.defaults["tools_paintoverlap"])

        if 'order' in args:
            order = args['order']
        else:
            order = str(self.app.defaults["tools_paintorder"])

        if 'margin' in args:
            margin = float(args['margin'])
        else:
            margin = float(self.app.defaults["tools_paintmargin"])

        if 'method' in args:
            method = args['method']
        else:
            method = str(self.app.defaults["tools_paintmethod"])

        if 'connect' in args:
            connect = bool(args['connect'])
        else:
            connect = eval(str(self.app.defaults["tools_pathconnect"]))

        if 'contour' in args:
            contour = bool(args['contour'])
        else:
            contour = eval(str(self.app.defaults["tools_paintcontour"]))

        if 'outname' in args:
            outname = args['outname']
        else:
            outname = name + "_paint"

        try:
            tools = [float(eval(dia)) for dia in tooldia.split(",") if dia != '']
        except AttributeError:
            tools = [float(tooldia)]
        # store here the default data for Geometry Data
        default_data = {}
        default_data.update({
            "name": '_paint',
            "plot": self.app.defaults["geometry_plot"],
            "cutz": self.app.defaults["geometry_cutz"],
            "vtipdia": 0.1,
            "vtipangle": 30,
            "travelz": self.app.defaults["geometry_travelz"],
            "feedrate": self.app.defaults["geometry_feedrate"],
            "feedrate_z": self.app.defaults["geometry_feedrate_z"],
            "feedrate_rapid": self.app.defaults["geometry_feedrate_rapid"],
            "dwell": self.app.defaults["geometry_dwell"],
            "dwelltime": self.app.defaults["geometry_dwelltime"],
            "multidepth": self.app.defaults["geometry_multidepth"],
            "ppname_g": self.app.defaults["geometry_ppname_g"],
            "depthperpass": self.app.defaults["geometry_depthperpass"],
            "extracut": self.app.defaults["geometry_extracut"],
            "toolchange": self.app.defaults["geometry_toolchange"],
            "toolchangez": self.app.defaults["geometry_toolchangez"],
            "endz": self.app.defaults["geometry_endz"],
            "spindlespeed": self.app.defaults["geometry_spindlespeed"],
            "toolchangexy": self.app.defaults["geometry_toolchangexy"],
            "startz": self.app.defaults["geometry_startz"],

            "tooldia": self.app.defaults["tools_painttooldia"],
            "paintmargin": self.app.defaults["tools_paintmargin"],
            "paintmethod": self.app.defaults["tools_paintmethod"],
            "selectmethod": self.app.defaults["tools_selectmethod"],
            "pathconnect": self.app.defaults["tools_pathconnect"],
            "paintcontour": self.app.defaults["tools_paintcontour"],
            "paintoverlap": self.app.defaults["tools_paintoverlap"]
        })
        paint_tools = dict()

        tooluid = 0
        for tool in tools:
            tooluid += 1
            paint_tools.update({
                int(tooluid): {
                    'tooldia': float('%.*f' % (obj.decimals, tool)),
                    'offset': 'Path',
                    'offset_value': 0.0,
                    'type': 'Iso',
                    'tool_type': 'C1',
                    'data': dict(default_data),
                    'solid_geometry': []
                }
            })

        if obj is None:
            return "Object not found: %s" % name

        # Paint all polygons in the painted object
        if 'all' in args and bool(args['all']) is True:
            self.app.paint_tool.paint_poly_all(obj=obj,
                                               tooldia=tooldia,
                                               overlap=overlap,
                                               order=order,
                                               margin=margin,
                                               method=method,
                                               outname=outname,
                                               connect=connect,
                                               contour=contour,
                                               tools_storage=paint_tools,
                                               plot=False,
                                               run_threaded=False)
            return

        # Paint single polygon in the painted object
        elif 'single' in args and bool(args['single']) is True:
            if 'x' not in args or 'y' not in args:
                self.raise_tcl_error('%s' % _("Expected -x <value> and -y <value>."))
            else:
                x = args['x']
                y = args['y']

                self.app.paint_tool.paint_poly(obj=obj,
                                               inside_pt=[x, y],
                                               tooldia=tooldia,
                                               overlap=overlap,
                                               order=order,
                                               margin=margin,
                                               method=method,
                                               outname=outname,
                                               connect=connect,
                                               contour=contour,
                                               tools_storage=paint_tools,
                                               plot=False,
                                               run_threaded=False)
            return

        # Paint all polygons found within the box object from the the painted object
        elif 'ref' in args and bool(args['ref']) is True:
            if 'box' not in args:
                self.raise_tcl_error('%s' % _("Expected -box <value>."))
            else:
                box_name = args['box']

                # Get box source object.
                try:
                    box_obj = self.app.collection.get_by_name(str(box_name))
                except Exception as e:
                    log.debug("TclCommandPaint.execute() --> %s" % str(e))
                    self.raise_tcl_error("%s: %s" % (_("Could not retrieve box object"), name))
                    return "Could not retrieve object: %s" % name

                self.app.paint_tool.paint_poly_ref(obj=obj,
                                                   sel_obj=box_obj,
                                                   tooldia=tooldia,
                                                   overlap=overlap,
                                                   order=order,
                                                   margin=margin,
                                                   method=method,
                                                   outname=outname,
                                                   connect=connect,
                                                   contour=contour,
                                                   tools_storage=paint_tools,
                                                   plot=False,
                                                   run_threaded=False)
            return

        else:
            self.raise_tcl_error("%s:" % _("There was none of the following args: 'ref', 'single', 'all'.\n"
                                           "Paint failed."))
            return "There was none of the following args: 'ref', 'single', 'all'.\n" \
                   "Paint failed."
