from tclCommands.TclCommand import TclCommand

import collections
import logging

import gettext
import AppTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class TclCommandCopperClear(TclCommand):
    """
    Clear the non-copper areas.
    """

    # Array of all command aliases, to be able use old names for backward compatibility (add_poly, add_polygon)
    aliases = ['ncc_clear', 'ncc']

    description = '%s %s' % ("--", "Clear excess copper.")

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
        ('connect', str),
        ('contour', str),
        ('offset', float),
        ('rest', str),
        ('all', int),
        ('ref', str),
        ('box', str),
        ('outname', str),
    ])

    # array of mandatory options for current Tcl command: required = {'name','outname'}
    required = ['name']

    # structured help for current command, args needs to be ordered
    help = {
        'main': "Clear excess copper in polygons. Basically it's a negative Paint.",
        'args': collections.OrderedDict([
            ('name', 'Name of the source Geometry object. String.'),
            ('tooldia', 'Diameter of the tool to be used. Can be a comma separated list of diameters.\n'
                        'WARNING: No space is allowed between tool diameters. E.g: correct: 0.5,1 / incorrect: 0.5, 1'),
            ('overlap', 'Percentage of tool diameter to overlap current pass over previous pass. Float [0, 99.9999]\n'
                        'E.g: for a 25% from tool diameter overlap use -overlap 25'),
            ('margin', 'Bounding box margin. Float number.'),
            ('order', 'Can have the values: "no", "fwd" and "rev". String.'
                      'It is useful when there are multiple tools in tooldia parameter.'
                      '"no" -> the order used is the one provided.'
                      '"fwd" -> tools are ordered from smallest to biggest.'
                      '"rev" -> tools are ordered from biggest to smallest.'),
            ('method', 'Algorithm for copper clearing. Can be: "standard", "seed" or "lines".'),
            ('connect', 'Draw lines to minimize tool lifts. True (1) or False (0)'),
            ('contour', 'Cut around the perimeter of the painting. True (1) or False (0)'),
            ('rest', 'Use rest-machining. True (1) or False (0)'),
            ('offset', 'If used, the copper clearing will finish to a distance from copper features. Float number.'),
            ('all', 'If used will copper clear the whole object. Either "-all" or "-box <value>" has to be used.'),
            ('box', 'Name of the object to be used as reference. Either "-all" or "-box <value>" has to be used. '
                    'String.'),
            ('outname', 'Name of the resulting Geometry object. String. No spaces.'),
        ]),
        'examples': ["ncc obj_name -tooldia 0.3,1 -overlap 10 -margin 1.0 -method 'lines' -all"]
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
            log.debug("TclCommandCopperClear.execute() --> %s" % str(e))
            self.raise_tcl_error("%s: %s" % (_("Could not retrieve object"), name))
            return "Could not retrieve object: %s" % name

        if obj is None:
            return "Object not found: %s" % name

        if 'tooldia' in args:
            tooldia = str(args['tooldia'])
        else:
            tooldia = self.app.defaults["tools_ncctools"]

        if 'overlap' in args:
            overlap = float(args['overlap']) / 100.0
        else:
            overlap = float(self.app.defaults["tools_nccoverlap"]) / 100.0

        if 'order' in args:
            order = args['order']
        else:
            order = str(self.app.defaults["tools_nccorder"])

        if 'margin' in args:
            margin = float(args['margin'])
        else:
            margin = float(self.app.defaults["tools_nccmargin"])

        if 'method' in args:
            method = args['method']
            if method == "standard":
                method_data = _("Standard")
            elif method == "seed":
                method_data = _("Seed")
            else:
                method_data = _("Lines")
        else:
            method = str(self.app.defaults["tools_nccmethod"])
            method_data = method
            if method == _("Standard"):
                method = "standard"
            elif method == _("Seed"):
                method = "seed"
            else:
                method = "lines"

        if 'connect' in args:
            try:
                par = args['connect'].capitalize()
            except AttributeError:
                par = args['connect']
            connect = bool(eval(par))
        else:
            connect = bool(eval(str(self.app.defaults["tools_nccconnect"])))

        if 'contour' in args:
            try:
                par = args['contour'].capitalize()
            except AttributeError:
                par = args['contour']
            contour = bool(eval(par))
        else:
            contour = bool(eval(str(self.app.defaults["tools_ncccontour"])))

        offset = 0.0
        if 'offset' in args:
            offset = float(args['offset'])
            has_offset = True
        else:
            has_offset = False

        try:
            tools = [float(eval(dia)) for dia in tooldia.split(",") if dia != '']
        except AttributeError:
            tools = [float(tooldia)]

        if 'rest' in args:
            try:
                par = args['rest'].capitalize()
            except AttributeError:
                par = args['rest']
            rest = bool(eval(par))
        else:
            rest = bool(eval(str(self.app.defaults["tools_nccrest"])))

        if 'outname' in args:
            outname = args['outname']
        else:
            if rest is True:
                outname = name + "_ncc"
            else:
                outname = name + "_ncc_rm"

        # used only to have correct information's in the obj.tools[tool]['data'] dict
        if "all" in args:
            select = _("Itself")
        else:
            select = _("Reference Object")

        # store here the default data for Geometry Data
        default_data = {}
        default_data.update({
            "name": outname,
            "plot": False,
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
            "extracut_length": self.app.defaults["geometry_extracut_length"],
            "toolchange": self.app.defaults["geometry_toolchange"],
            "toolchangez": self.app.defaults["geometry_toolchangez"],
            "endz": self.app.defaults["geometry_endz"],
            "endxy": self.app.defaults["geometry_endxy"],
            "spindlespeed": self.app.defaults["geometry_spindlespeed"],
            "toolchangexy": self.app.defaults["geometry_toolchangexy"],
            "startz": self.app.defaults["geometry_startz"],

            "area_exclusion": self.app.defaults["geometry_area_exclusion"],
            "area_shape": self.app.defaults["geometry_area_shape"],
            "area_strategy": self.app.defaults["geometry_area_strategy"],
            "area_overz": float(self.app.defaults["geometry_area_overz"]),

            "tooldia": self.app.defaults["tools_painttooldia"],
            "tools_nccmargin": margin,
            "tools_nccmethod": method_data,
            "tools_nccref": select,
            "tools_nccconnect": connect,
            "tools_ncccontour": contour,
            "tools_nccoverlap": overlap
        })
        ncc_tools = {}

        tooluid = 0
        for tool in tools:
            tooluid += 1
            ncc_tools.update({
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
            ncc_tools[int(tooluid)]['data']['tooldia'] = float('%.*f' % (obj.decimals, tool))

        # Non-Copper clear all polygons in the non-copper clear object
        if 'all' in args:
            self.app.ncclear_tool.clear_copper_tcl(ncc_obj=obj,
                                                   select_method='itself',
                                                   ncctooldia=tooldia,
                                                   overlap=overlap,
                                                   order=order,
                                                   margin=margin,
                                                   has_offset=has_offset,
                                                   offset=offset,
                                                   method=method,
                                                   outname=outname,
                                                   connect=connect,
                                                   contour=contour,
                                                   rest=rest,
                                                   tools_storage=ncc_tools,
                                                   plot=False,
                                                   run_threaded=False)
            return

        # Non-Copper clear all polygons found within the box object from the the non_copper cleared object
        if 'box' in args:
            box_name = args['box']

            # Get box source object.
            try:
                box_obj = self.app.collection.get_by_name(str(box_name))
            except Exception as e:
                log.debug("TclCommandCopperClear.execute() --> %s" % str(e))
                self.raise_tcl_error("%s: %s" % (_("Could not retrieve box object"), name))
                return "Could not retrieve object: %s" % name

            self.app.ncclear_tool.clear_copper_tcl(ncc_obj=obj,
                                                   sel_obj=box_obj,
                                                   select_method='box',
                                                   ncctooldia=tooldia,
                                                   overlap=overlap,
                                                   order=order,
                                                   margin=margin,
                                                   has_offset=has_offset,
                                                   offset=offset,
                                                   method=method,
                                                   outname=outname,
                                                   connect=connect,
                                                   contour=contour,
                                                   rest=rest,
                                                   tools_storage=ncc_tools,
                                                   plot=False,
                                                   run_threaded=False)
            return

        # if the program reached this then it's an error because neither -all or -box <value> was used.
        self.raise_tcl_error('%s' % _("Expected either -box <value> or -all."))
        return "Expected either -box <value> or -all. Copper clearing failed."
