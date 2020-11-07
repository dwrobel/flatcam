# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 1/10/2020                                          #
# MIT Licence                                              #
# ##########################################################

from PyQt5 import QtWidgets, QtCore, QtGui

from appTool import AppTool
from appGUI.GUIElements import RadioSet, FCDoubleSpinner, FCCheckBox, FCComboBox

from shapely.geometry import Point

import logging
import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class ToolExtractDrills(AppTool):

    def __init__(self, app):
        AppTool.__init__(self, app)
        self.decimals = self.app.decimals

        # #############################################################################
        # ######################### Tool GUI ##########################################
        # #############################################################################
        self.ui = ExtractDrillsUI(layout=self.layout, app=self.app)
        self.toolName = self.ui.toolName

        # ## Signals
        self.ui.hole_size_radio.activated_custom.connect(self.on_hole_size_toggle)
        self.ui.e_drills_button.clicked.connect(self.on_extract_drills_click)
        self.ui.reset_button.clicked.connect(self.set_tool_ui)

        self.ui.circular_cb.stateChanged.connect(
            lambda state:
            self.ui.circular_ring_entry.setDisabled(False) if state else self.ui.circular_ring_entry.setDisabled(True)
        )

        self.ui.oblong_cb.stateChanged.connect(
            lambda state:
            self.ui.oblong_ring_entry.setDisabled(False) if state else self.ui.oblong_ring_entry.setDisabled(True)
        )

        self.ui.square_cb.stateChanged.connect(
            lambda state:
            self.ui.square_ring_entry.setDisabled(False) if state else self.ui.square_ring_entry.setDisabled(True)
        )

        self.ui.rectangular_cb.stateChanged.connect(
            lambda state:
            self.ui.rectangular_ring_entry.setDisabled(False) if state else
            self.ui.rectangular_ring_entry.setDisabled(True)
        )

        self.ui.other_cb.stateChanged.connect(
            lambda state:
            self.ui.other_ring_entry.setDisabled(False) if state else self.ui.other_ring_entry.setDisabled(True)
        )

    def install(self, icon=None, separator=None, **kwargs):
        AppTool.install(self, icon, separator, shortcut='Alt+I', **kwargs)

    def run(self, toggle=True):
        self.app.defaults.report_usage("Extract Drills()")

        if toggle:
            # if the splitter is hidden, display it, else hide it but only if the current widget is the same
            if self.app.ui.splitter.sizes()[0] == 0:
                self.app.ui.splitter.setSizes([1, 1])
            else:
                try:
                    if self.app.ui.tool_scroll_area.widget().objectName() == self.toolName:
                        # if tab is populated with the tool but it does not have the focus, focus on it
                        if not self.app.ui.notebook.currentWidget() is self.app.ui.tool_tab:
                            # focus on Tool Tab
                            self.app.ui.notebook.setCurrentWidget(self.app.ui.tool_tab)
                        else:
                            self.app.ui.splitter.setSizes([0, 1])
                except AttributeError:
                    pass
        else:
            if self.app.ui.splitter.sizes()[0] == 0:
                self.app.ui.splitter.setSizes([1, 1])

        AppTool.run(self)
        self.set_tool_ui()

        self.app.ui.notebook.setTabText(2, _("Extract Drills Tool"))

    def set_tool_ui(self):
        self.reset_fields()

        self.ui.hole_size_radio.set_value(self.app.defaults["tools_edrills_hole_type"])

        self.ui.dia_entry.set_value(float(self.app.defaults["tools_edrills_hole_fixed_dia"]))

        self.ui.circular_ring_entry.set_value(float(self.app.defaults["tools_edrills_circular_ring"]))
        self.ui.oblong_ring_entry.set_value(float(self.app.defaults["tools_edrills_oblong_ring"]))
        self.ui.square_ring_entry.set_value(float(self.app.defaults["tools_edrills_square_ring"]))
        self.ui.rectangular_ring_entry.set_value(float(self.app.defaults["tools_edrills_rectangular_ring"]))
        self.ui.other_ring_entry.set_value(float(self.app.defaults["tools_edrills_others_ring"]))

        self.ui.circular_cb.set_value(self.app.defaults["tools_edrills_circular"])
        self.ui.oblong_cb.set_value(self.app.defaults["tools_edrills_oblong"])
        self.ui.square_cb.set_value(self.app.defaults["tools_edrills_square"])
        self.ui.rectangular_cb.set_value(self.app.defaults["tools_edrills_rectangular"])
        self.ui.other_cb.set_value(self.app.defaults["tools_edrills_others"])

        self.ui.factor_entry.set_value(float(self.app.defaults["tools_edrills_hole_prop_factor"]))

    def on_extract_drills_click(self):

        drill_dia = self.ui.dia_entry.get_value()
        circ_r_val = self.ui.circular_ring_entry.get_value()
        oblong_r_val = self.ui.oblong_ring_entry.get_value()
        square_r_val = self.ui.square_ring_entry.get_value()
        rect_r_val = self.ui.rectangular_ring_entry.get_value()
        other_r_val = self.ui.other_ring_entry.get_value()

        prop_factor = self.ui.factor_entry.get_value() / 100.0

        drills = []
        tools = {}

        selection_index = self.ui.gerber_object_combo.currentIndex()
        model_index = self.app.collection.index(selection_index, 0, self.ui.gerber_object_combo.rootModelIndex())

        try:
            fcobj = model_index.internalPointer().obj
        except Exception:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("There is no Gerber object loaded ..."))
            return

        outname = fcobj.options['name'].rpartition('.')[0]

        mode = self.ui.hole_size_radio.get_value()

        if mode == 'fixed':
            tools = {
                1: {
                    "tooldia": drill_dia,
                    "drills": [],
                    "slots": []
                }
            }
            for apid, apid_value in fcobj.apertures.items():
                ap_type = apid_value['type']

                if ap_type == 'C':
                    if self.ui.circular_cb.get_value() is False:
                        continue
                elif ap_type == 'O':
                    if self.ui.oblong_cb.get_value() is False:
                        continue
                elif ap_type == 'R':
                    width = float(apid_value['width'])
                    height = float(apid_value['height'])

                    # if the height == width (float numbers so the reason for the following)
                    if round(width, self.decimals) == round(height, self.decimals):
                        if self.ui.square_cb.get_value() is False:
                            continue
                    else:
                        if self.ui.rectangular_cb.get_value() is False:
                            continue
                else:
                    if self.ui.other_cb.get_value() is False:
                        continue

                for geo_el in apid_value['geometry']:
                    if 'follow' in geo_el and isinstance(geo_el['follow'], Point):
                        tools[1]["drills"].append(geo_el['follow'])
                        if 'solid_geometry' not in tools[1]:
                            tools[1]['solid_geometry'] = []
                        else:
                            tools[1]['solid_geometry'].append(geo_el['follow'])

            if 'solid_geometry' not in tools[1] or not tools[1]['solid_geometry']:
                self.app.inform.emit('[WARNING_NOTCL] %s' % _("No drills extracted. Try different parameters."))
                return
        elif mode == 'ring':
            drills_found = set()
            for apid, apid_value in fcobj.apertures.items():
                ap_type = apid_value['type']

                dia = None
                if ap_type == 'C':
                    if self.ui.circular_cb.get_value():
                        dia = float(apid_value['size']) - (2 * circ_r_val)
                elif ap_type == 'O':
                    width = float(apid_value['width'])
                    height = float(apid_value['height'])
                    if self.ui.oblong_cb.get_value():
                        if width > height:
                            dia = float(apid_value['height']) - (2 * oblong_r_val)
                        else:
                            dia = float(apid_value['width']) - (2 * oblong_r_val)
                elif ap_type == 'R':
                    width = float(apid_value['width'])
                    height = float(apid_value['height'])

                    # if the height == width (float numbers so the reason for the following)
                    if abs(float('%.*f' % (self.decimals, width)) - float('%.*f' % (self.decimals, height))) < \
                            (10 ** -self.decimals):
                        if self.ui.square_cb.get_value():
                            dia = float(apid_value['height']) - (2 * square_r_val)
                    else:
                        if self.ui.rectangular_cb.get_value():
                            if width > height:
                                dia = float(apid_value['height']) - (2 * rect_r_val)
                            else:
                                dia = float(apid_value['width']) - (2 * rect_r_val)
                else:
                    if self.ui.other_cb.get_value():
                        try:
                            dia = float(apid_value['size']) - (2 * other_r_val)
                        except KeyError:
                            if ap_type == 'AM':
                                pol = apid_value['geometry'][0]['solid']
                                x0, y0, x1, y1 = pol.bounds
                                dx = x1 - x0
                                dy = y1 - y0
                                if dx <= dy:
                                    dia = dx - (2 * other_r_val)
                                else:
                                    dia = dy - (2 * other_r_val)

                # if dia is None then none of the above applied so we skip the following
                if dia is None:
                    continue

                tool_in_drills = False
                for tool, tool_val in tools.items():
                    if abs(float('%.*f' % (
                            self.decimals,
                            tool_val["tooldia"])) - float('%.*f' % (self.decimals, dia))) < (10 ** -self.decimals):
                        tool_in_drills = tool

                if tool_in_drills is False:
                    if tools:
                        new_tool = max([int(t) for t in tools]) + 1
                        tool_in_drills = new_tool
                    else:
                        tool_in_drills = 1

                for geo_el in apid_value['geometry']:
                    if 'follow' in geo_el and isinstance(geo_el['follow'], Point):
                        if tool_in_drills not in tools:
                            tools[tool_in_drills] = {
                                "tooldia": dia,
                                "drills": [],
                                "slots": []
                            }

                        tools[tool_in_drills]['drills'].append(geo_el['follow'])

                        if 'solid_geometry' not in tools[tool_in_drills]:
                            tools[tool_in_drills]['solid_geometry'] = []
                        else:
                            tools[tool_in_drills]['solid_geometry'].append(geo_el['follow'])

                if tool_in_drills in tools:
                    if 'solid_geometry' not in tools[tool_in_drills] or not tools[tool_in_drills]['solid_geometry']:
                        drills_found.add(False)
                    else:
                        drills_found.add(True)

            if True not in drills_found:
                self.app.inform.emit('[WARNING_NOTCL] %s' % _("No drills extracted. Try different parameters."))
                return
        else:
            drills_found = set()
            for apid, apid_value in fcobj.apertures.items():
                ap_type = apid_value['type']

                dia = None
                if ap_type == 'C':
                    if self.ui.circular_cb.get_value():
                        dia = float(apid_value['size']) * prop_factor
                elif ap_type == 'O':
                    width = float(apid_value['width'])
                    height = float(apid_value['height'])
                    if self.ui.oblong_cb.get_value():
                        if width > height:
                            dia = float(apid_value['height']) * prop_factor
                        else:
                            dia = float(apid_value['width']) * prop_factor
                elif ap_type == 'R':
                    width = float(apid_value['width'])
                    height = float(apid_value['height'])

                    # if the height == width (float numbers so the reason for the following)
                    if abs(float('%.*f' % (self.decimals, width)) - float('%.*f' % (self.decimals, height))) < \
                            (10 ** -self.decimals):
                        if self.ui.square_cb.get_value():
                            dia = float(apid_value['height']) * prop_factor
                    else:
                        if self.ui.rectangular_cb.get_value():
                            if width > height:
                                dia = float(apid_value['height']) * prop_factor
                            else:
                                dia = float(apid_value['width']) * prop_factor
                else:
                    if self.ui.other_cb.get_value():
                        try:
                            dia = float(apid_value['size']) * prop_factor
                        except KeyError:
                            if ap_type == 'AM':
                                pol = apid_value['geometry'][0]['solid']
                                x0, y0, x1, y1 = pol.bounds
                                dx = x1 - x0
                                dy = y1 - y0
                                if dx <= dy:
                                    dia = dx * prop_factor
                                else:
                                    dia = dy * prop_factor

                # if dia is None then none of the above applied so we skip the following
                if dia is None:
                    continue

                tool_in_drills = False
                for tool, tool_val in tools.items():
                    if abs(float('%.*f' % (
                            self.decimals,
                            tool_val["tooldia"])) - float('%.*f' % (self.decimals, dia))) < (10 ** -self.decimals):
                        tool_in_drills = tool

                if tool_in_drills is False:
                    if tools:
                        new_tool = max([int(t) for t in tools]) + 1
                        tool_in_drills = new_tool
                    else:
                        tool_in_drills = 1

                for geo_el in apid_value['geometry']:
                    if 'follow' in geo_el and isinstance(geo_el['follow'], Point):
                        if tool_in_drills not in tools:
                            tools[tool_in_drills] = {
                                "tooldia": dia,
                                "drills": [],
                                "slots": []
                            }

                        tools[tool_in_drills]['drills'].append(geo_el['follow'])

                        if 'solid_geometry' not in tools[tool_in_drills]:
                            tools[tool_in_drills]['solid_geometry'] = []
                        else:
                            tools[tool_in_drills]['solid_geometry'].append(geo_el['follow'])

                if tool_in_drills in tools:
                    if 'solid_geometry' not in tools[tool_in_drills] or not tools[tool_in_drills]['solid_geometry']:
                        drills_found.add(False)
                    else:
                        drills_found.add(True)

            if True not in drills_found:
                self.app.inform.emit('[WARNING_NOTCL] %s' % _("No drills extracted. Try different parameters."))
                return

        def obj_init(obj_inst, app_inst):
            obj_inst.tools = tools
            obj_inst.drills = drills
            obj_inst.create_geometry()
            obj_inst.source_file = app_inst.f_handlers.export_excellon(obj_name=outname, local_use=obj_inst,
                                                                       filename=None,
                                                                       use_thread=False)

        self.app.app_obj.new_object("excellon", outname, obj_init)

    def on_hole_size_toggle(self, val):
        if val == "fixed":
            self.ui.fixed_label.setVisible(True)
            self.ui.dia_entry.setVisible(True)
            self.ui.dia_label.setVisible(True)

            self.ui.ring_frame.setVisible(False)

            self.ui.prop_label.setVisible(False)
            self.ui.factor_label.setVisible(False)
            self.ui.factor_entry.setVisible(False)
        elif val == "ring":
            self.ui.fixed_label.setVisible(False)
            self.ui.dia_entry.setVisible(False)
            self.ui.dia_label.setVisible(False)

            self.ui.ring_frame.setVisible(True)

            self.ui.prop_label.setVisible(False)
            self.ui.factor_label.setVisible(False)
            self.ui.factor_entry.setVisible(False)
        elif val == "prop":
            self.ui.fixed_label.setVisible(False)
            self.ui.dia_entry.setVisible(False)
            self.ui.dia_label.setVisible(False)

            self.ui.ring_frame.setVisible(False)

            self.ui.prop_label.setVisible(True)
            self.ui.factor_label.setVisible(True)
            self.ui.factor_entry.setVisible(True)

    def reset_fields(self):
        self.ui.gerber_object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.ui.gerber_object_combo.setCurrentIndex(0)


class ExtractDrillsUI:

    toolName = _("Extract Drills")

    def __init__(self, layout, app):
        self.app = app
        self.decimals = self.app.decimals
        self.layout = layout

        # ## Title
        title_label = QtWidgets.QLabel("%s" % self.toolName)
        title_label.setStyleSheet("""
                                QLabel
                                {
                                    font-size: 16px;
                                    font-weight: bold;
                                }
                                """)
        self.layout.addWidget(title_label)

        self.layout.addWidget(QtWidgets.QLabel(""))

        # ## Grid Layout
        grid_lay = QtWidgets.QGridLayout()
        self.layout.addLayout(grid_lay)
        grid_lay.setColumnStretch(0, 1)
        grid_lay.setColumnStretch(1, 0)

        # ## Gerber Object
        self.gerber_object_combo = FCComboBox()
        self.gerber_object_combo.setModel(self.app.collection)
        self.gerber_object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.gerber_object_combo.is_last = True
        self.gerber_object_combo.obj_type = "Gerber"

        self.grb_label = QtWidgets.QLabel("<b>%s:</b>" % _("GERBER"))
        self.grb_label.setToolTip('%s.' % _("Gerber from which to extract drill holes"))

        # grid_lay.addRow("Bottom Layer:", self.object_combo)
        grid_lay.addWidget(self.grb_label, 0, 0, 1, 2)
        grid_lay.addWidget(self.gerber_object_combo, 1, 0, 1, 2)

        self.padt_label = QtWidgets.QLabel("<b>%s</b>" % _("Processed Pads Type"))
        self.padt_label.setToolTip(
            _("The type of pads shape to be processed.\n"
              "If the PCB has many SMD pads with rectangular pads,\n"
              "disable the Rectangular aperture.")
        )

        grid_lay.addWidget(self.padt_label, 2, 0, 1, 2)

        # Circular Aperture Selection
        self.circular_cb = FCCheckBox('%s' % _("Circular"))
        self.circular_cb.setToolTip(
            _("Process Circular Pads.")
        )

        grid_lay.addWidget(self.circular_cb, 3, 0, 1, 2)

        # Oblong Aperture Selection
        self.oblong_cb = FCCheckBox('%s' % _("Oblong"))
        self.oblong_cb.setToolTip(
            _("Process Oblong Pads.")
        )

        grid_lay.addWidget(self.oblong_cb, 4, 0, 1, 2)

        # Square Aperture Selection
        self.square_cb = FCCheckBox('%s' % _("Square"))
        self.square_cb.setToolTip(
            _("Process Square Pads.")
        )

        grid_lay.addWidget(self.square_cb, 5, 0, 1, 2)

        # Rectangular Aperture Selection
        self.rectangular_cb = FCCheckBox('%s' % _("Rectangular"))
        self.rectangular_cb.setToolTip(
            _("Process Rectangular Pads.")
        )

        grid_lay.addWidget(self.rectangular_cb, 6, 0, 1, 2)

        # Others type of Apertures Selection
        self.other_cb = FCCheckBox('%s' % _("Others"))
        self.other_cb.setToolTip(
            _("Process pads not in the categories above.")
        )

        grid_lay.addWidget(self.other_cb, 7, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid_lay.addWidget(separator_line, 8, 0, 1, 2)

        # ## Grid Layout
        grid1 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid1)
        grid1.setColumnStretch(0, 0)
        grid1.setColumnStretch(1, 1)

        self.method_label = QtWidgets.QLabel('<b>%s</b>' % _("Method"))
        self.method_label.setToolTip(
            _("The method for processing pads. Can be:\n"
              "- Fixed Diameter -> all holes will have a set size\n"
              "- Fixed Annular Ring -> all holes will have a set annular ring\n"
              "- Proportional -> each hole size will be a fraction of the pad size"))
        grid1.addWidget(self.method_label, 2, 0, 1, 2)

        # ## Holes Size
        self.hole_size_radio = RadioSet(
            [
                {'label': _("Fixed Diameter"), 'value': 'fixed'},
                {'label': _("Proportional"), 'value': 'prop'},
                {'label': _("Fixed Annular Ring"), 'value': 'ring'}
            ],
            orientation='vertical',
            stretch=False)

        grid1.addWidget(self.hole_size_radio, 3, 0, 1, 2)

        # grid_lay1.addWidget(QtWidgets.QLabel(''))

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid1.addWidget(separator_line, 5, 0, 1, 2)

        # Annular Ring
        self.fixed_label = QtWidgets.QLabel('<b>%s</b>' % _("Fixed Diameter"))
        grid1.addWidget(self.fixed_label, 6, 0, 1, 2)

        # Diameter value
        self.dia_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.dia_entry.set_precision(self.decimals)
        self.dia_entry.set_range(0.0000, 10000.0000)

        self.dia_label = QtWidgets.QLabel('%s:' % _("Value"))
        self.dia_label.setToolTip(
            _("Fixed hole diameter.")
        )

        grid1.addWidget(self.dia_label, 8, 0)
        grid1.addWidget(self.dia_entry, 8, 1)

        self.ring_frame = QtWidgets.QFrame()
        self.ring_frame.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.ring_frame)

        self.ring_box = QtWidgets.QVBoxLayout()
        self.ring_box.setContentsMargins(0, 0, 0, 0)
        self.ring_frame.setLayout(self.ring_box)

        # ## Grid Layout
        grid2 = QtWidgets.QGridLayout()
        grid2.setColumnStretch(0, 0)
        grid2.setColumnStretch(1, 1)
        self.ring_box.addLayout(grid2)

        # Annular Ring value
        self.ring_label = QtWidgets.QLabel('<b>%s</b>' % _("Fixed Annular Ring"))
        self.ring_label.setToolTip(
            _("The size of annular ring.\n"
              "The copper sliver between the hole exterior\n"
              "and the margin of the copper pad.")
        )
        grid2.addWidget(self.ring_label, 0, 0, 1, 2)

        # Circular Annular Ring Value
        self.circular_ring_label = QtWidgets.QLabel('%s:' % _("Circular"))
        self.circular_ring_label.setToolTip(
            _("The size of annular ring for circular pads.")
        )

        self.circular_ring_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.circular_ring_entry.set_precision(self.decimals)
        self.circular_ring_entry.set_range(0.0000, 10000.0000)

        grid2.addWidget(self.circular_ring_label, 1, 0)
        grid2.addWidget(self.circular_ring_entry, 1, 1)

        # Oblong Annular Ring Value
        self.oblong_ring_label = QtWidgets.QLabel('%s:' % _("Oblong"))
        self.oblong_ring_label.setToolTip(
            _("The size of annular ring for oblong pads.")
        )

        self.oblong_ring_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.oblong_ring_entry.set_precision(self.decimals)
        self.oblong_ring_entry.set_range(0.0000, 10000.0000)

        grid2.addWidget(self.oblong_ring_label, 2, 0)
        grid2.addWidget(self.oblong_ring_entry, 2, 1)

        # Square Annular Ring Value
        self.square_ring_label = QtWidgets.QLabel('%s:' % _("Square"))
        self.square_ring_label.setToolTip(
            _("The size of annular ring for square pads.")
        )

        self.square_ring_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.square_ring_entry.set_precision(self.decimals)
        self.square_ring_entry.set_range(0.0000, 10000.0000)

        grid2.addWidget(self.square_ring_label, 3, 0)
        grid2.addWidget(self.square_ring_entry, 3, 1)

        # Rectangular Annular Ring Value
        self.rectangular_ring_label = QtWidgets.QLabel('%s:' % _("Rectangular"))
        self.rectangular_ring_label.setToolTip(
            _("The size of annular ring for rectangular pads.")
        )

        self.rectangular_ring_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.rectangular_ring_entry.set_precision(self.decimals)
        self.rectangular_ring_entry.set_range(0.0000, 10000.0000)

        grid2.addWidget(self.rectangular_ring_label, 4, 0)
        grid2.addWidget(self.rectangular_ring_entry, 4, 1)

        # Others Annular Ring Value
        self.other_ring_label = QtWidgets.QLabel('%s:' % _("Others"))
        self.other_ring_label.setToolTip(
            _("The size of annular ring for other pads.")
        )

        self.other_ring_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.other_ring_entry.set_precision(self.decimals)
        self.other_ring_entry.set_range(0.0000, 10000.0000)

        grid2.addWidget(self.other_ring_label, 5, 0)
        grid2.addWidget(self.other_ring_entry, 5, 1)

        grid3 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid3)
        grid3.setColumnStretch(0, 0)
        grid3.setColumnStretch(1, 1)

        # Annular Ring value
        self.prop_label = QtWidgets.QLabel('<b>%s</b>' % _("Proportional Diameter"))
        grid3.addWidget(self.prop_label, 2, 0, 1, 2)

        # Diameter value
        self.factor_entry = FCDoubleSpinner(callback=self.confirmation_message, suffix='%')
        self.factor_entry.set_precision(self.decimals)
        self.factor_entry.set_range(0.0000, 100.0000)
        self.factor_entry.setSingleStep(0.1)

        self.factor_label = QtWidgets.QLabel('%s:' % _("Value"))
        self.factor_label.setToolTip(
            _("Proportional Diameter.\n"
              "The hole diameter will be a fraction of the pad size.")
        )

        grid3.addWidget(self.factor_label, 3, 0)
        grid3.addWidget(self.factor_entry, 3, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid3.addWidget(separator_line, 5, 0, 1, 2)

        # Extract drills from Gerber apertures flashes (pads)
        self.e_drills_button = QtWidgets.QPushButton(_("Extract Drills"))
        self.e_drills_button.setIcon(QtGui.QIcon(self.app.resource_location + '/drill16.png'))
        self.e_drills_button.setToolTip(
            _("Extract drills from a given Gerber file.")
        )
        self.e_drills_button.setStyleSheet("""
                                        QPushButton
                                        {
                                            font-weight: bold;
                                        }
                                        """)
        self.layout.addWidget(self.e_drills_button)

        self.layout.addStretch()

        # ## Reset Tool
        self.reset_button = QtWidgets.QPushButton(_("Reset Tool"))
        self.reset_button.setIcon(QtGui.QIcon(self.app.resource_location + '/reset32.png'))
        self.reset_button.setToolTip(
            _("Will reset the tool parameters.")
        )
        self.reset_button.setStyleSheet("""
                                QPushButton
                                {
                                    font-weight: bold;
                                }
                                """)
        self.layout.addWidget(self.reset_button)

        self.circular_ring_entry.setEnabled(False)
        self.oblong_ring_entry.setEnabled(False)
        self.square_ring_entry.setEnabled(False)
        self.rectangular_ring_entry.setEnabled(False)
        self.other_ring_entry.setEnabled(False)

        self.dia_entry.setVisible(False)
        self.dia_label.setVisible(False)
        self.factor_label.setVisible(False)
        self.factor_entry.setVisible(False)

        self.ring_frame.setVisible(False)
        # #################################### FINSIHED GUI ###########################
        # #############################################################################

    def confirmation_message(self, accepted, minval, maxval):
        if accepted is False:
            self.app.inform[str, bool].emit('[WARNING_NOTCL] %s: [%.*f, %.*f]' % (_("Edited value is out of range"),
                                                                                  self.decimals,
                                                                                  minval,
                                                                                  self.decimals,
                                                                                  maxval), False)
        else:
            self.app.inform[str, bool].emit('[success] %s' % _("Edited value is within limits."), False)

    def confirmation_message_int(self, accepted, minval, maxval):
        if accepted is False:
            self.app.inform[str, bool].emit('[WARNING_NOTCL] %s: [%d, %d]' %
                                            (_("Edited value is out of range"), minval, maxval), False)
        else:
            self.app.inform[str, bool].emit('[success] %s' % _("Edited value is within limits."), False)
