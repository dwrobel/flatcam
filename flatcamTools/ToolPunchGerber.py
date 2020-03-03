# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 1/24/2020                                          #
# MIT Licence                                              #
# ##########################################################

from PyQt5 import QtCore, QtWidgets

from FlatCAMTool import FlatCAMTool
from flatcamGUI.GUIElements import RadioSet, FCDoubleSpinner, FCCheckBox, FCComboBox

from copy import deepcopy
import logging
from shapely.geometry import MultiPolygon, Point

import gettext
import FlatCAMTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class ToolPunchGerber(FlatCAMTool):

    toolName = _("Punch Gerber")

    def __init__(self, app):
        FlatCAMTool.__init__(self, app)

        self.decimals = self.app.decimals

        # Title
        title_label = QtWidgets.QLabel("%s" % self.toolName)
        title_label.setStyleSheet("""
                        QLabel
                        {
                            font-size: 16px;
                            font-weight: bold;
                        }
                        """)
        self.layout.addWidget(title_label)

        # Punch Drill holes
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
        self.grb_label.setToolTip('%s.' % _("Gerber into which to punch holes"))

        grid_lay.addWidget(self.grb_label, 0, 0, 1, 2)
        grid_lay.addWidget(self.gerber_object_combo, 1, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid_lay.addWidget(separator_line, 2, 0, 1, 2)

        self.padt_label = QtWidgets.QLabel("<b>%s</b>" % _("Processed Pads Type"))
        self.padt_label.setToolTip(
            _("The type of pads shape to be processed.\n"
              "If the PCB has many SMD pads with rectangular pads,\n"
              "disable the Rectangular aperture.")
        )

        grid_lay.addWidget(self.padt_label, 3, 0, 1, 2)

        # Select all
        self.select_all_cb = FCCheckBox('%s' % _("ALL"))
        grid_lay.addWidget(self.select_all_cb)

        # Circular Aperture Selection
        self.circular_cb = FCCheckBox('%s' % _("Circular"))
        self.circular_cb.setToolTip(
            _("Process Circular Pads.")
        )

        grid_lay.addWidget(self.circular_cb, 5, 0, 1, 2)

        # Oblong Aperture Selection
        self.oblong_cb = FCCheckBox('%s' % _("Oblong"))
        self.oblong_cb.setToolTip(
            _("Process Oblong Pads.")
        )

        grid_lay.addWidget(self.oblong_cb, 6, 0, 1, 2)

        # Square Aperture Selection
        self.square_cb = FCCheckBox('%s' % _("Square"))
        self.square_cb.setToolTip(
            _("Process Square Pads.")
        )

        grid_lay.addWidget(self.square_cb, 7, 0, 1, 2)

        # Rectangular Aperture Selection
        self.rectangular_cb = FCCheckBox('%s' % _("Rectangular"))
        self.rectangular_cb.setToolTip(
            _("Process Rectangular Pads.")
        )

        grid_lay.addWidget(self.rectangular_cb, 8, 0, 1, 2)

        # Others type of Apertures Selection
        self.other_cb = FCCheckBox('%s' % _("Others"))
        self.other_cb.setToolTip(
            _("Process pads not in the categories above.")
        )

        grid_lay.addWidget(self.other_cb, 9, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid_lay.addWidget(separator_line, 10, 0, 1, 2)

        # Grid Layout
        grid0 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid0)
        grid0.setColumnStretch(0, 0)
        grid0.setColumnStretch(1, 1)

        self.method_label = QtWidgets.QLabel('<b>%s:</b>' % _("Method"))
        self.method_label.setToolTip(
            _("The punch hole source can be:\n"
              "- Excellon Object-> the Excellon object drills center will serve as reference.\n"
              "- Fixed Diameter -> will try to use the pads center as reference adding fixed diameter holes.\n"
              "- Fixed Annular Ring -> will try to keep a set annular ring.\n"
              "- Proportional -> will make a Gerber punch hole having the diameter a percentage of the pad diameter.\n")
        )
        self.method_punch = RadioSet(
            [
                {'label': _('Excellon'), 'value': 'exc'},
                {'label': _("Fixed Diameter"), 'value': 'fixed'},
                {'label': _("Fixed Annular Ring"), 'value': 'ring'},
                {'label': _("Proportional"), 'value': 'prop'}
            ],
            orientation='vertical',
            stretch=False)
        grid0.addWidget(self.method_label, 0, 0, 1, 2)
        grid0.addWidget(self.method_punch, 1, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 2, 0, 1, 2)

        self.exc_label = QtWidgets.QLabel('<b>%s</b>' % _("Excellon"))
        self.exc_label.setToolTip(
            _("Remove the geometry of Excellon from the Gerber to create the holes in pads.")
        )

        self.exc_combo = FCComboBox()
        self.exc_combo.setModel(self.app.collection)
        self.exc_combo.setRootModelIndex(self.app.collection.index(1, 0, QtCore.QModelIndex()))
        self.exc_combo.is_last = True
        self.exc_combo.obj_type = "Excellon"

        grid0.addWidget(self.exc_label, 3, 0, 1, 2)
        grid0.addWidget(self.exc_combo, 4, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 5, 0, 1, 2)

        # Fixed Dia
        self.fixed_label = QtWidgets.QLabel('<b>%s</b>' % _("Fixed Diameter"))
        grid0.addWidget(self.fixed_label, 6, 0, 1, 2)

        # Diameter value
        self.dia_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.dia_entry.set_precision(self.decimals)
        self.dia_entry.set_range(0.0000, 9999.9999)

        self.dia_label = QtWidgets.QLabel('%s:' % _("Value"))
        self.dia_label.setToolTip(
            _("Fixed hole diameter.")
        )

        grid0.addWidget(self.dia_label, 8, 0)
        grid0.addWidget(self.dia_entry, 8, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 9, 0, 1, 2)

        self.ring_frame = QtWidgets.QFrame()
        self.ring_frame.setContentsMargins(0, 0, 0, 0)
        grid0.addWidget(self.ring_frame, 10, 0, 1, 2)

        self.ring_box = QtWidgets.QVBoxLayout()
        self.ring_box.setContentsMargins(0, 0, 0, 0)
        self.ring_frame.setLayout(self.ring_box)

        # Annular Ring value
        self.ring_label = QtWidgets.QLabel('<b>%s</b>' % _("Fixed Annular Ring"))
        self.ring_label.setToolTip(
            _("The size of annular ring.\n"
              "The copper sliver between the hole exterior\n"
              "and the margin of the copper pad.")
        )
        self.ring_box.addWidget(self.ring_label)

        # ## Grid Layout
        self.grid1 = QtWidgets.QGridLayout()
        self.grid1.setColumnStretch(0, 0)
        self.grid1.setColumnStretch(1, 1)
        self.ring_box.addLayout(self.grid1)

        # Circular Annular Ring Value
        self.circular_ring_label = QtWidgets.QLabel('%s:' % _("Circular"))
        self.circular_ring_label.setToolTip(
            _("The size of annular ring for circular pads.")
        )

        self.circular_ring_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.circular_ring_entry.set_precision(self.decimals)
        self.circular_ring_entry.set_range(0.0000, 9999.9999)

        self.grid1.addWidget(self.circular_ring_label, 3, 0)
        self.grid1.addWidget(self.circular_ring_entry, 3, 1)

        # Oblong Annular Ring Value
        self.oblong_ring_label = QtWidgets.QLabel('%s:' % _("Oblong"))
        self.oblong_ring_label.setToolTip(
            _("The size of annular ring for oblong pads.")
        )

        self.oblong_ring_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.oblong_ring_entry.set_precision(self.decimals)
        self.oblong_ring_entry.set_range(0.0000, 9999.9999)

        self.grid1.addWidget(self.oblong_ring_label, 4, 0)
        self.grid1.addWidget(self.oblong_ring_entry, 4, 1)

        # Square Annular Ring Value
        self.square_ring_label = QtWidgets.QLabel('%s:' % _("Square"))
        self.square_ring_label.setToolTip(
            _("The size of annular ring for square pads.")
        )

        self.square_ring_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.square_ring_entry.set_precision(self.decimals)
        self.square_ring_entry.set_range(0.0000, 9999.9999)

        self.grid1.addWidget(self.square_ring_label, 5, 0)
        self.grid1.addWidget(self.square_ring_entry, 5, 1)

        # Rectangular Annular Ring Value
        self.rectangular_ring_label = QtWidgets.QLabel('%s:' % _("Rectangular"))
        self.rectangular_ring_label.setToolTip(
            _("The size of annular ring for rectangular pads.")
        )

        self.rectangular_ring_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.rectangular_ring_entry.set_precision(self.decimals)
        self.rectangular_ring_entry.set_range(0.0000, 9999.9999)

        self.grid1.addWidget(self.rectangular_ring_label, 6, 0)
        self.grid1.addWidget(self.rectangular_ring_entry, 6, 1)

        # Others Annular Ring Value
        self.other_ring_label = QtWidgets.QLabel('%s:' % _("Others"))
        self.other_ring_label.setToolTip(
            _("The size of annular ring for other pads.")
        )

        self.other_ring_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.other_ring_entry.set_precision(self.decimals)
        self.other_ring_entry.set_range(0.0000, 9999.9999)

        self.grid1.addWidget(self.other_ring_label, 7, 0)
        self.grid1.addWidget(self.other_ring_entry, 7, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 11, 0, 1, 2)

        # Proportional value
        self.prop_label = QtWidgets.QLabel('<b>%s</b>' % _("Proportional Diameter"))
        grid0.addWidget(self.prop_label, 12, 0, 1, 2)

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

        grid0.addWidget(self.factor_label, 13, 0)
        grid0.addWidget(self.factor_entry, 13, 1)

        separator_line3 = QtWidgets.QFrame()
        separator_line3.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line3.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line3, 14, 0, 1, 2)

        # Buttons
        self.punch_object_button = QtWidgets.QPushButton(_("Punch Gerber"))
        self.punch_object_button.setToolTip(
            _("Create a Gerber object from the selected object, within\n"
              "the specified box.")
        )
        self.punch_object_button.setStyleSheet("""
                        QPushButton
                        {
                            font-weight: bold;
                        }
                        """)
        self.layout.addWidget(self.punch_object_button)

        self.layout.addStretch()

        # ## Reset Tool
        self.reset_button = QtWidgets.QPushButton(_("Reset Tool"))
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

        self.units = self.app.defaults['units']

        # self.cb_items = [
        #     self.grid1.itemAt(w).widget() for w in range(self.grid1.count())
        #     if isinstance(self.grid1.itemAt(w).widget(), FCCheckBox)
        # ]

        self.circular_ring_entry.setEnabled(False)
        self.oblong_ring_entry.setEnabled(False)
        self.square_ring_entry.setEnabled(False)
        self.rectangular_ring_entry.setEnabled(False)
        self.other_ring_entry.setEnabled(False)

        self.dia_entry.setDisabled(True)
        self.dia_label.setDisabled(True)
        self.factor_label.setDisabled(True)
        self.factor_entry.setDisabled(True)

        # ## Signals
        self.method_punch.activated_custom.connect(self.on_method)
        self.reset_button.clicked.connect(self.set_tool_ui)
        self.punch_object_button.clicked.connect(self.on_generate_object)

        self.circular_cb.stateChanged.connect(
            lambda state:
                self.circular_ring_entry.setDisabled(False) if state else self.circular_ring_entry.setDisabled(True)
        )

        self.oblong_cb.stateChanged.connect(
            lambda state:
            self.oblong_ring_entry.setDisabled(False) if state else self.oblong_ring_entry.setDisabled(True)
        )

        self.square_cb.stateChanged.connect(
            lambda state:
            self.square_ring_entry.setDisabled(False) if state else self.square_ring_entry.setDisabled(True)
        )

        self.rectangular_cb.stateChanged.connect(
            lambda state:
            self.rectangular_ring_entry.setDisabled(False) if state else self.rectangular_ring_entry.setDisabled(True)
        )

        self.other_cb.stateChanged.connect(
            lambda state:
            self.other_ring_entry.setDisabled(False) if state else self.other_ring_entry.setDisabled(True)
        )

    def run(self, toggle=True):
        self.app.report_usage("ToolPunchGerber()")

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

        FlatCAMTool.run(self)

        self.set_tool_ui()

        self.app.ui.notebook.setTabText(2, _("Punch Tool"))

    def install(self, icon=None, separator=None, **kwargs):
        FlatCAMTool.install(self, icon, separator, shortcut='ALT+H', **kwargs)

    def set_tool_ui(self):
        self.reset_fields()

        self.ui_connect()
        self.method_punch.set_value(self.app.defaults["tools_punch_hole_type"])
        self.select_all_cb.set_value(False)

        self.dia_entry.set_value(float(self.app.defaults["tools_punch_hole_fixed_dia"]))

        self.circular_ring_entry.set_value(float(self.app.defaults["tools_punch_circular_ring"]))
        self.oblong_ring_entry.set_value(float(self.app.defaults["tools_punch_oblong_ring"]))
        self.square_ring_entry.set_value(float(self.app.defaults["tools_punch_square_ring"]))
        self.rectangular_ring_entry.set_value(float(self.app.defaults["tools_punch_rectangular_ring"]))
        self.other_ring_entry.set_value(float(self.app.defaults["tools_punch_others_ring"]))

        self.circular_cb.set_value(self.app.defaults["tools_punch_circular"])
        self.oblong_cb.set_value(self.app.defaults["tools_punch_oblong"])
        self.square_cb.set_value(self.app.defaults["tools_punch_square"])
        self.rectangular_cb.set_value(self.app.defaults["tools_punch_rectangular"])
        self.other_cb.set_value(self.app.defaults["tools_punch_others"])

        self.factor_entry.set_value(float(self.app.defaults["tools_punch_hole_prop_factor"]))

    def on_select_all(self, state):
        self.ui_disconnect()
        if state:
            self.circular_cb.setChecked(True)
            self.oblong_cb.setChecked(True)
            self.square_cb.setChecked(True)
            self.rectangular_cb.setChecked(True)
            self.other_cb.setChecked(True)
        else:
            self.circular_cb.setChecked(False)
            self.oblong_cb.setChecked(False)
            self.square_cb.setChecked(False)
            self.rectangular_cb.setChecked(False)
            self.other_cb.setChecked(False)
        self.ui_connect()

    def on_method(self, val):
        self.exc_label.setEnabled(False)
        self.exc_combo.setEnabled(False)
        self.fixed_label.setEnabled(False)
        self.dia_label.setEnabled(False)
        self.dia_entry.setEnabled(False)
        self.ring_frame.setEnabled(False)
        self.prop_label.setEnabled(False)
        self.factor_label.setEnabled(False)
        self.factor_entry.setEnabled(False)

        if val == 'exc':
            self.exc_label.setEnabled(True)
            self.exc_combo.setEnabled(True)
        elif val == 'fixed':
            self.fixed_label.setEnabled(True)
            self.dia_label.setEnabled(True)
            self.dia_entry.setEnabled(True)
        elif val == 'ring':
            self.ring_frame.setEnabled(True)
        elif val == 'prop':
            self.prop_label.setEnabled(True)
            self.factor_label.setEnabled(True)
            self.factor_entry.setEnabled(True)

    def ui_connect(self):
        self.select_all_cb.stateChanged.connect(self.on_select_all)

    def ui_disconnect(self):
        try:
            self.select_all_cb.stateChanged.disconnect()
        except (AttributeError, TypeError):
            pass

    def on_generate_object(self):

        # get the Gerber file who is the source of the punched Gerber
        selection_index = self.gerber_object_combo.currentIndex()
        model_index = self.app.collection.index(selection_index, 0, self.gerber_object_combo.rootModelIndex())

        try:
            grb_obj = model_index.internalPointer().obj
        except Exception:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("There is no Gerber object loaded ..."))
            return

        name = grb_obj.options['name'].rpartition('.')[0]
        outname = name + "_punched"

        punch_method = self.method_punch.get_value()

        new_options = {}
        for opt in grb_obj.options:
            new_options[opt] = deepcopy(grb_obj.options[opt])

        if punch_method == 'exc':

            # get the Excellon file whose geometry will create the punch holes
            selection_index = self.exc_combo.currentIndex()
            model_index = self.app.collection.index(selection_index, 0, self.exc_combo.rootModelIndex())

            try:
                exc_obj = model_index.internalPointer().obj
            except Exception:
                self.app.inform.emit('[WARNING_NOTCL] %s' % _("There is no Excellon object loaded ..."))
                return

            # this is the punching geometry
            exc_solid_geometry = MultiPolygon(exc_obj.solid_geometry)
            if isinstance(grb_obj.solid_geometry, list):
                grb_solid_geometry = MultiPolygon(grb_obj.solid_geometry)
            else:
                grb_solid_geometry = grb_obj.solid_geometry

                # create the punched Gerber solid_geometry
            punched_solid_geometry = grb_solid_geometry.difference(exc_solid_geometry)

            # update the gerber apertures to include the clear geometry so it can be exported successfully
            new_apertures = deepcopy(grb_obj.apertures)
            new_apertures_items = new_apertures.items()

            # find maximum aperture id
            new_apid = max([int(x) for x, __ in new_apertures_items])

            # store here the clear geometry, the key is the drill size
            holes_apertures = {}

            for apid, val in new_apertures_items:
                for elem in val['geometry']:
                    # make it work only for Gerber Flashes who are Points in 'follow'
                    if 'solid' in elem and isinstance(elem['follow'], Point):
                        for drill in exc_obj.drills:
                            clear_apid_size = exc_obj.tools[drill['tool']]['C']

                            # since there may be drills that do not drill into a pad we test only for drills in a pad
                            if drill['point'].within(elem['solid']):
                                geo_elem = {}
                                geo_elem['clear'] = drill['point']

                                if clear_apid_size not in holes_apertures:
                                    holes_apertures[clear_apid_size] = {}
                                    holes_apertures[clear_apid_size]['type'] = 'C'
                                    holes_apertures[clear_apid_size]['size'] = clear_apid_size
                                    holes_apertures[clear_apid_size]['geometry'] = []

                                holes_apertures[clear_apid_size]['geometry'].append(deepcopy(geo_elem))

            # add the clear geometry to new apertures; it's easier than to test if there are apertures with the same
            # size and add there the clear geometry
            for hole_size, ap_val in holes_apertures.items():
                new_apid += 1
                new_apertures[str(new_apid)] = deepcopy(ap_val)

            def init_func(new_obj, app_obj):
                new_obj.options.update(new_options)
                new_obj.options['name'] = outname
                new_obj.fill_color = deepcopy(grb_obj.fill_color)
                new_obj.outline_color = deepcopy(grb_obj.outline_color)

                new_obj.apertures = deepcopy(new_apertures)

                new_obj.solid_geometry = deepcopy(punched_solid_geometry)
                new_obj.source_file = self.app.export_gerber(obj_name=outname, filename=None,
                                                             local_use=new_obj, use_thread=False)

            self.app.new_object('gerber', outname, init_func)
        elif punch_method == 'fixed':
            punch_size = float(self.dia_entry.get_value())

            if punch_size == 0.0:
                self.app.inform.emit('[WARNING_NOTCL] %s' % _("The value of the fixed diameter is 0.0. Aborting."))
                return 'fail'

            punching_geo = []
            for apid in grb_obj.apertures:
                if grb_obj.apertures[apid]['type'] == 'C' and self.circular_cb.get_value():
                    if punch_size >= float(grb_obj.apertures[apid]['size']):
                        self.app.inform.emit('[ERROR_NOTCL] %s' %
                                             _(" Could not generate punched hole Gerber because the punch hole size"
                                               "is bigger than some of the apertures in the Gerber object."))
                        return 'fail'
                    else:
                        for elem in grb_obj.apertures[apid]['geometry']:
                            if 'follow' in elem:
                                if isinstance(elem['follow'], Point):
                                    punching_geo.append(elem['follow'].buffer(punch_size / 2))
                elif grb_obj.apertures[apid]['type'] == 'R':
                    if punch_size >= float(grb_obj.apertures[apid]['width']) or \
                            punch_size >= float(grb_obj.apertures[apid]['height']):
                        self.app.inform.emit('[ERROR_NOTCL] %s' %
                                             _("Could not generate punched hole Gerber because the punch hole size"
                                               "is bigger than some of the apertures in the Gerber object."))
                        return 'fail'
                    elif round(float(grb_obj.apertures[apid]['width']), self.decimals) == \
                            round(float(grb_obj.apertures[apid]['height']), self.decimals) and \
                            self.square_cb.get_value():
                        for elem in grb_obj.apertures[apid]['geometry']:
                            if 'follow' in elem:
                                if isinstance(elem['follow'], Point):
                                    punching_geo.append(elem['follow'].buffer(punch_size / 2))
                    elif round(float(grb_obj.apertures[apid]['width']), self.decimals) != \
                            round(float(grb_obj.apertures[apid]['height']), self.decimals) and \
                            self.rectangular_cb.get_value():
                        for elem in grb_obj.apertures[apid]['geometry']:
                            if 'follow' in elem:
                                if isinstance(elem['follow'], Point):
                                    punching_geo.append(elem['follow'].buffer(punch_size / 2))
                elif grb_obj.apertures[apid]['type'] == 'O' and self.oblong_cb.get_value():
                    for elem in grb_obj.apertures[apid]['geometry']:
                        if 'follow' in elem:
                            if isinstance(elem['follow'], Point):
                                punching_geo.append(elem['follow'].buffer(punch_size / 2))
                elif grb_obj.apertures[apid]['type'] not in ['C', 'R', 'O'] and self.other_cb.get_value():
                    for elem in grb_obj.apertures[apid]['geometry']:
                        if 'follow' in elem:
                            if isinstance(elem['follow'], Point):
                                punching_geo.append(elem['follow'].buffer(punch_size / 2))

            punching_geo = MultiPolygon(punching_geo)
            if isinstance(grb_obj.solid_geometry, list):
                temp_solid_geometry = MultiPolygon(grb_obj.solid_geometry)
            else:
                temp_solid_geometry = grb_obj.solid_geometry
            punched_solid_geometry = temp_solid_geometry.difference(punching_geo)

            if punched_solid_geometry == temp_solid_geometry:
                self.app.inform.emit('[WARNING_NOTCL] %s' %
                                     _("Could not generate punched hole Gerber because the newly created object "
                                       "geometry is the same as the one in the source object geometry..."))
                return 'fail'

            # update the gerber apertures to include the clear geometry so it can be exported successfully
            new_apertures = deepcopy(grb_obj.apertures)
            new_apertures_items = new_apertures.items()

            # find maximum aperture id
            new_apid = max([int(x) for x, __ in new_apertures_items])

            # store here the clear geometry, the key is the drill size
            holes_apertures = {}

            for apid, val in new_apertures_items:
                for elem in val['geometry']:
                    # make it work only for Gerber Flashes who are Points in 'follow'
                    if 'solid' in elem and isinstance(elem['follow'], Point):
                        for geo in punching_geo:
                            clear_apid_size = punch_size

                            # since there may be drills that do not drill into a pad we test only for drills in a pad
                            if geo.within(elem['solid']):
                                geo_elem = {}
                                geo_elem['clear'] = geo.centroid

                                if clear_apid_size not in holes_apertures:
                                    holes_apertures[clear_apid_size] = {}
                                    holes_apertures[clear_apid_size]['type'] = 'C'
                                    holes_apertures[clear_apid_size]['size'] = clear_apid_size
                                    holes_apertures[clear_apid_size]['geometry'] = []

                                holes_apertures[clear_apid_size]['geometry'].append(deepcopy(geo_elem))

            # add the clear geometry to new apertures; it's easier than to test if there are apertures with the same
            # size and add there the clear geometry
            for hole_size, ap_val in holes_apertures.items():
                new_apid += 1
                new_apertures[str(new_apid)] = deepcopy(ap_val)

            def init_func(new_obj, app_obj):
                new_obj.options.update(new_options)
                new_obj.options['name'] = outname
                new_obj.fill_color = deepcopy(grb_obj.fill_color)
                new_obj.outline_color = deepcopy(grb_obj.outline_color)

                new_obj.apertures = deepcopy(new_apertures)

                new_obj.solid_geometry = deepcopy(punched_solid_geometry)
                new_obj.source_file = self.app.export_gerber(obj_name=outname, filename=None,
                                                             local_use=new_obj, use_thread=False)

            self.app.new_object('gerber', outname, init_func)
        elif punch_method == 'ring':
            circ_r_val = self.circular_ring_entry.get_value()
            oblong_r_val = self.oblong_ring_entry.get_value()
            square_r_val = self.square_ring_entry.get_value()
            rect_r_val = self.rectangular_ring_entry.get_value()
            other_r_val = self.other_ring_entry.get_value()

            dia = None

            if isinstance(grb_obj.solid_geometry, list):
                temp_solid_geometry = MultiPolygon(grb_obj.solid_geometry)
            else:
                temp_solid_geometry = grb_obj.solid_geometry

            punched_solid_geometry = temp_solid_geometry

            new_apertures = deepcopy(grb_obj.apertures)
            new_apertures_items = new_apertures.items()

            # find maximum aperture id
            new_apid = max([int(x) for x, __ in new_apertures_items])

            # store here the clear geometry, the key is the new aperture size
            holes_apertures = {}

            for apid, apid_value in grb_obj.apertures.items():
                ap_type = apid_value['type']
                punching_geo = []

                if ap_type == 'C' and self.circular_cb.get_value():
                    dia = float(apid_value['size']) - (2 * circ_r_val)
                    for elem in apid_value['geometry']:
                        if 'follow' in elem and isinstance(elem['follow'], Point):
                            punching_geo.append(elem['follow'].buffer(dia / 2))

                elif ap_type == 'O' and self.oblong_cb.get_value():
                    width = float(apid_value['width'])
                    height = float(apid_value['height'])

                    if width > height:
                        dia = float(apid_value['height']) - (2 * oblong_r_val)
                    else:
                        dia = float(apid_value['width']) - (2 * oblong_r_val)

                    for elem in grb_obj.apertures[apid]['geometry']:
                        if 'follow' in elem:
                            if isinstance(elem['follow'], Point):
                                punching_geo.append(elem['follow'].buffer(dia / 2))

                elif ap_type == 'R':
                    width = float(apid_value['width'])
                    height = float(apid_value['height'])

                    # if the height == width (float numbers so the reason for the following)
                    if round(width, self.decimals) == round(height, self.decimals):
                        if self.square_cb.get_value():
                            dia = float(apid_value['height']) - (2 * square_r_val)

                            for elem in grb_obj.apertures[apid]['geometry']:
                                if 'follow' in elem:
                                    if isinstance(elem['follow'], Point):
                                        punching_geo.append(elem['follow'].buffer(dia / 2))
                    elif self.rectangular_cb.get_value():
                        if width > height:
                            dia = float(apid_value['height']) - (2 * rect_r_val)
                        else:
                            dia = float(apid_value['width']) - (2 * rect_r_val)

                        for elem in grb_obj.apertures[apid]['geometry']:
                            if 'follow' in elem:
                                if isinstance(elem['follow'], Point):
                                    punching_geo.append(elem['follow'].buffer(dia / 2))

                elif self.other_cb.get_value():
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

                    for elem in grb_obj.apertures[apid]['geometry']:
                        if 'follow' in elem:
                            if isinstance(elem['follow'], Point):
                                punching_geo.append(elem['follow'].buffer(dia / 2))

                # if dia is None then none of the above applied so we skip the following
                if dia is None:
                    continue

                punching_geo = MultiPolygon(punching_geo)

                if punching_geo is None or punching_geo.is_empty:
                    continue

                punched_solid_geometry = punched_solid_geometry.difference(punching_geo)

                # update the gerber apertures to include the clear geometry so it can be exported successfully
                for elem in apid_value['geometry']:
                    # make it work only for Gerber Flashes who are Points in 'follow'
                    if 'solid' in elem and isinstance(elem['follow'], Point):
                        clear_apid_size = dia
                        for geo in punching_geo:

                            # since there may be drills that do not drill into a pad we test only for geos in a pad
                            if geo.within(elem['solid']):
                                geo_elem = {}
                                geo_elem['clear'] = geo.centroid

                                if clear_apid_size not in holes_apertures:
                                    holes_apertures[clear_apid_size] = {}
                                    holes_apertures[clear_apid_size]['type'] = 'C'
                                    holes_apertures[clear_apid_size]['size'] = clear_apid_size
                                    holes_apertures[clear_apid_size]['geometry'] = []

                                holes_apertures[clear_apid_size]['geometry'].append(deepcopy(geo_elem))

            # add the clear geometry to new apertures; it's easier than to test if there are apertures with the same
            # size and add there the clear geometry
            for hole_size, ap_val in holes_apertures.items():
                new_apid += 1
                new_apertures[str(new_apid)] = deepcopy(ap_val)

            def init_func(new_obj, app_obj):
                new_obj.options.update(new_options)
                new_obj.options['name'] = outname
                new_obj.fill_color = deepcopy(grb_obj.fill_color)
                new_obj.outline_color = deepcopy(grb_obj.outline_color)

                new_obj.apertures = deepcopy(new_apertures)

                new_obj.solid_geometry = deepcopy(punched_solid_geometry)
                new_obj.source_file = self.app.export_gerber(obj_name=outname, filename=None,
                                                             local_use=new_obj, use_thread=False)

            self.app.new_object('gerber', outname, init_func)

        elif punch_method == 'prop':
            prop_factor = self.factor_entry.get_value() / 100.0

            dia = None

            if isinstance(grb_obj.solid_geometry, list):
                temp_solid_geometry = MultiPolygon(grb_obj.solid_geometry)
            else:
                temp_solid_geometry = grb_obj.solid_geometry

            punched_solid_geometry = temp_solid_geometry

            new_apertures = deepcopy(grb_obj.apertures)
            new_apertures_items = new_apertures.items()

            # find maximum aperture id
            new_apid = max([int(x) for x, __ in new_apertures_items])

            # store here the clear geometry, the key is the new aperture size
            holes_apertures = {}

            for apid, apid_value in grb_obj.apertures.items():
                ap_type = apid_value['type']
                punching_geo = []

                if ap_type == 'C' and self.circular_cb.get_value():
                    dia = float(apid_value['size']) * prop_factor
                    for elem in apid_value['geometry']:
                        if 'follow' in elem and isinstance(elem['follow'], Point):
                            punching_geo.append(elem['follow'].buffer(dia / 2))

                elif ap_type == 'O' and self.oblong_cb.get_value():
                    width = float(apid_value['width'])
                    height = float(apid_value['height'])

                    if width > height:
                        dia = float(apid_value['height']) * prop_factor
                    else:
                        dia = float(apid_value['width']) * prop_factor

                    for elem in grb_obj.apertures[apid]['geometry']:
                        if 'follow' in elem:
                            if isinstance(elem['follow'], Point):
                                punching_geo.append(elem['follow'].buffer(dia / 2))

                elif ap_type == 'R':
                    width = float(apid_value['width'])
                    height = float(apid_value['height'])

                    # if the height == width (float numbers so the reason for the following)
                    if round(width, self.decimals) == round(height, self.decimals):
                        if self.square_cb.get_value():
                            dia = float(apid_value['height']) * prop_factor

                            for elem in grb_obj.apertures[apid]['geometry']:
                                if 'follow' in elem:
                                    if isinstance(elem['follow'], Point):
                                        punching_geo.append(elem['follow'].buffer(dia / 2))
                    elif self.rectangular_cb.get_value():
                        if width > height:
                            dia = float(apid_value['height']) * prop_factor
                        else:
                            dia = float(apid_value['width']) * prop_factor

                        for elem in grb_obj.apertures[apid]['geometry']:
                            if 'follow' in elem:
                                if isinstance(elem['follow'], Point):
                                    punching_geo.append(elem['follow'].buffer(dia / 2))

                elif self.other_cb.get_value():
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

                    for elem in grb_obj.apertures[apid]['geometry']:
                        if 'follow' in elem:
                            if isinstance(elem['follow'], Point):
                                punching_geo.append(elem['follow'].buffer(dia / 2))

                # if dia is None then none of the above applied so we skip the following
                if dia is None:
                    continue

                punching_geo = MultiPolygon(punching_geo)

                if punching_geo is None or punching_geo.is_empty:
                    continue

                punched_solid_geometry = punched_solid_geometry.difference(punching_geo)

                # update the gerber apertures to include the clear geometry so it can be exported successfully
                for elem in apid_value['geometry']:
                    # make it work only for Gerber Flashes who are Points in 'follow'
                    if 'solid' in elem and isinstance(elem['follow'], Point):
                        clear_apid_size = dia
                        for geo in punching_geo:

                            # since there may be drills that do not drill into a pad we test only for geos in a pad
                            if geo.within(elem['solid']):
                                geo_elem = {}
                                geo_elem['clear'] = geo.centroid

                                if clear_apid_size not in holes_apertures:
                                    holes_apertures[clear_apid_size] = {}
                                    holes_apertures[clear_apid_size]['type'] = 'C'
                                    holes_apertures[clear_apid_size]['size'] = clear_apid_size
                                    holes_apertures[clear_apid_size]['geometry'] = []

                                holes_apertures[clear_apid_size]['geometry'].append(deepcopy(geo_elem))

            # add the clear geometry to new apertures; it's easier than to test if there are apertures with the same
            # size and add there the clear geometry
            for hole_size, ap_val in holes_apertures.items():
                new_apid += 1
                new_apertures[str(new_apid)] = deepcopy(ap_val)

            def init_func(new_obj, app_obj):
                new_obj.options.update(new_options)
                new_obj.options['name'] = outname
                new_obj.fill_color = deepcopy(grb_obj.fill_color)
                new_obj.outline_color = deepcopy(grb_obj.outline_color)

                new_obj.apertures = deepcopy(new_apertures)

                new_obj.solid_geometry = deepcopy(punched_solid_geometry)
                new_obj.source_file = self.app.export_gerber(obj_name=outname, filename=None,
                                                             local_use=new_obj, use_thread=False)

            self.app.new_object('gerber', outname, init_func)

    def reset_fields(self):
        self.gerber_object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.exc_combo.setRootModelIndex(self.app.collection.index(1, 0, QtCore.QModelIndex()))
        self.ui_disconnect()
