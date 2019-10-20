# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 3/10/2019                                          #
# MIT Licence                                              #
# ##########################################################

from PyQt5 import QtGui, QtCore, QtWidgets

from FlatCAMTool import FlatCAMTool
from flatcamGUI.GUIElements import RadioSet, FCDoubleSpinner, FCCheckBox, \
    OptionalHideInputSection, OptionalInputSection

from copy import deepcopy
import logging
from shapely.geometry import Polygon, MultiPolygon, Point

import gettext
import FlatCAMTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class Film(FlatCAMTool):

    toolName = _("Film PCB")

    def __init__(self, app):
        FlatCAMTool.__init__(self, app)

        self.decimals = 4

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

        # Form Layout
        grid0 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid0)

        grid0.setColumnStretch(0, 0)
        grid0.setColumnStretch(1, 1)

        # Type of object for which to create the film
        self.tf_type_obj_combo = QtWidgets.QComboBox()
        self.tf_type_obj_combo.addItem("Gerber")
        self.tf_type_obj_combo.addItem("Excellon")
        self.tf_type_obj_combo.addItem("Geometry")

        # we get rid of item1 ("Excellon") as it is not suitable for creating film
        self.tf_type_obj_combo.view().setRowHidden(1, True)
        self.tf_type_obj_combo.setItemIcon(0, QtGui.QIcon("share/flatcam_icon16.png"))
        self.tf_type_obj_combo.setItemIcon(2, QtGui.QIcon("share/geometry16.png"))

        self.tf_type_obj_combo_label = QtWidgets.QLabel('%s:' % _("Object Type"))
        self.tf_type_obj_combo_label.setToolTip(
            _("Specify the type of object for which to create the film.\n"
              "The object can be of type: Gerber or Geometry.\n"
              "The selection here decide the type of objects that will be\n"
              "in the Film Object combobox.")
        )
        grid0.addWidget(self.tf_type_obj_combo_label, 0, 0)
        grid0.addWidget(self.tf_type_obj_combo, 0, 1)

        # List of objects for which we can create the film
        self.tf_object_combo = QtWidgets.QComboBox()
        self.tf_object_combo.setModel(self.app.collection)
        self.tf_object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.tf_object_combo.setCurrentIndex(1)

        self.tf_object_label = QtWidgets.QLabel('%s:' % _("Film Object"))
        self.tf_object_label.setToolTip(
            _("Object for which to create the film.")
        )
        grid0.addWidget(self.tf_object_label, 1, 0)
        grid0.addWidget(self.tf_object_combo, 1, 1)

        # Type of Box Object to be used as an envelope for film creation
        # Within this we can create negative
        self.tf_type_box_combo = QtWidgets.QComboBox()
        self.tf_type_box_combo.addItem("Gerber")
        self.tf_type_box_combo.addItem("Excellon")
        self.tf_type_box_combo.addItem("Geometry")

        # we get rid of item1 ("Excellon") as it is not suitable for box when creating film
        self.tf_type_box_combo.view().setRowHidden(1, True)
        self.tf_type_box_combo.setItemIcon(0, QtGui.QIcon("share/flatcam_icon16.png"))
        self.tf_type_box_combo.setItemIcon(2, QtGui.QIcon("share/geometry16.png"))

        self.tf_type_box_combo_label = QtWidgets.QLabel(_("Box Type:"))
        self.tf_type_box_combo_label.setToolTip(
            _("Specify the type of object to be used as an container for\n"
              "film creation. It can be: Gerber or Geometry type."
              "The selection here decide the type of objects that will be\n"
              "in the Box Object combobox.")
        )
        grid0.addWidget(self.tf_type_box_combo_label, 2, 0)
        grid0.addWidget(self.tf_type_box_combo, 2, 1)

        # Box
        self.tf_box_combo = QtWidgets.QComboBox()
        self.tf_box_combo.setModel(self.app.collection)
        self.tf_box_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.tf_box_combo.setCurrentIndex(1)

        self.tf_box_combo_label = QtWidgets.QLabel('%s:' % _("Box Object"))
        self.tf_box_combo_label.setToolTip(
            _("The actual object that is used a container for the\n "
              "selected object for which we create the film.\n"
              "Usually it is the PCB outline but it can be also the\n"
              "same object for which the film is created.")
        )
        grid0.addWidget(self.tf_box_combo_label, 3, 0)
        grid0.addWidget(self.tf_box_combo, 3, 1)

        grid0.addWidget(QtWidgets.QLabel(''), 4, 0)

        self.film_adj_label = QtWidgets.QLabel('<b>%s</b>' % _("Film Adjustments"))
        self.film_adj_label.setToolTip(
            _("Sometime the printers will distort the print shape, especially the Laser types.\n"
              "This section provide the tools to compensate for the print distortions.")
        )

        grid0.addWidget(self.film_adj_label, 5, 0, 1, 2)

        # Scale Geometry
        self.film_scale_cb = FCCheckBox('%s' % _("Scale Film geometry"))
        self.film_scale_cb.setToolTip(
            _("A value greater than 1 will stretch the film\n"
              "while a value less than 1 will jolt it.")
        )
        self.film_scale_cb.setStyleSheet(
            """
            QCheckBox {font-weight: bold; color: black}
            """
        )
        grid0.addWidget(self.film_scale_cb, 6, 0, 1, 2)

        self.film_scalex_label = QtWidgets.QLabel('%s:' % _("X factor"))
        self.film_scalex_entry = FCDoubleSpinner()
        self.film_scalex_entry.set_range(-999.9999, 999.9999)
        self.film_scalex_entry.set_precision(self.decimals)
        self.film_scalex_entry.setSingleStep(0.01)

        grid0.addWidget(self.film_scalex_label, 7, 0)
        grid0.addWidget(self.film_scalex_entry, 7, 1)

        self.film_scaley_label = QtWidgets.QLabel('%s:' % _("Y factor"))
        self.film_scaley_entry = FCDoubleSpinner()
        self.film_scaley_entry.set_range(-999.9999, 999.9999)
        self.film_scaley_entry.set_precision(self.decimals)
        self.film_scaley_entry.setSingleStep(0.01)

        grid0.addWidget(self.film_scaley_label, 8, 0)
        grid0.addWidget(self.film_scaley_entry, 8, 1)

        self.ois_scale = OptionalInputSection(self.film_scale_cb, [self.film_scalex_label, self.film_scalex_entry,
                                                                   self.film_scaley_label,  self.film_scaley_entry])
        # Skew Geometry
        self.film_skew_cb = FCCheckBox('%s' % _("Skew Film geometry"))
        self.film_skew_cb.setToolTip(
            _("Positive values will skew to the right\n"
              "while negative values will skew to the left.")
        )
        self.film_skew_cb.setStyleSheet(
            """
            QCheckBox {font-weight: bold; color: black}
            """
        )
        grid0.addWidget(self.film_skew_cb, 9, 0, 1, 2)

        self.film_skewx_label = QtWidgets.QLabel('%s:' % _("X angle"))
        self.film_skewx_entry = FCDoubleSpinner()
        self.film_skewx_entry.set_range(-999.9999, 999.9999)
        self.film_skewx_entry.set_precision(self.decimals)
        self.film_skewx_entry.setSingleStep(0.01)

        grid0.addWidget(self.film_skewx_label, 10, 0)
        grid0.addWidget(self.film_skewx_entry, 10, 1)

        self.film_skewy_label = QtWidgets.QLabel('%s:' % _("Y angle"))
        self.film_skewy_entry = FCDoubleSpinner()
        self.film_skewy_entry.set_range(-999.9999, 999.9999)
        self.film_skewy_entry.set_precision(self.decimals)
        self.film_skewy_entry.setSingleStep(0.01)

        grid0.addWidget(self.film_skewy_label, 11, 0)
        grid0.addWidget(self.film_skewy_entry, 11, 1)

        self.film_skew_ref_label = QtWidgets.QLabel('%s:' % _("Reference"))
        self.film_skew_ref_label.setToolTip(
            _("The reference point to be used as origin for the skew.\n"
              "It can be one of the four points of the geometry bounding box.")
        )
        self.film_skew_reference = RadioSet([{'label': _('Bottom Left'), 'value': 'bottomleft'},
                                             {'label': _('Top Left'), 'value': 'topleft'},
                                             {'label': _('Bottom Right'), 'value': 'bottomright'},
                                             {'label': _('Top right'), 'value': 'topright'}],
                                            orientation='vertical',
                                            stretch=False)

        grid0.addWidget(self.film_skew_ref_label, 12, 0)
        grid0.addWidget(self.film_skew_reference, 12, 1)

        self.ois_skew = OptionalInputSection(self.film_skew_cb, [self.film_skewx_label, self.film_skewx_entry,
                                                                 self.film_skewy_label,  self.film_skewy_entry,
                                                                 self.film_skew_reference])
        # Mirror Geometry
        self.film_mirror_cb = FCCheckBox('%s' % _("Mirror Film geometry"))
        self.film_mirror_cb.setToolTip(
            _("Mirror the film geometry on the selected axis or on both.")
        )
        self.film_mirror_cb.setStyleSheet(
            """
            QCheckBox {font-weight: bold; color: black}
            """
        )
        grid0.addWidget(self.film_mirror_cb, 13, 0, 1, 2)

        self.film_mirror_axis = RadioSet([{'label': _('None'), 'value': 'none'},
                                          {'label': _('X'), 'value': 'x'},
                                          {'label': _('Y'), 'value': 'y'},
                                          {'label': _('Both'), 'value': 'both'}],
                                         stretch=False)
        self.film_mirror_axis_label = QtWidgets.QLabel('%s:' % _("Mirror axis"))

        grid0.addWidget(self.film_mirror_axis_label, 14, 0)
        grid0.addWidget(self.film_mirror_axis, 14, 1)

        self.ois_mirror = OptionalInputSection(self.film_mirror_cb,
                                               [self.film_mirror_axis_label, self.film_mirror_axis])

        grid0.addWidget(QtWidgets.QLabel(''), 15, 0)

        # Scale Stroke size
        self.film_scale_stroke_entry = FCDoubleSpinner()
        self.film_scale_stroke_entry.set_range(-999.9999, 999.9999)
        self.film_scale_stroke_entry.setSingleStep(0.01)
        self.film_scale_stroke_entry.set_precision(self.decimals)

        self.film_scale_stroke_label = QtWidgets.QLabel('%s:' % _("Scale Stroke"))
        self.film_scale_stroke_label.setToolTip(
            _("Scale the line stroke thickness of each feature in the SVG file.\n"
              "It means that the line that envelope each SVG feature will be thicker or thinner,\n"
              "therefore the fine features may be more affected by this parameter.")
        )
        grid0.addWidget(self.film_scale_stroke_label, 16, 0)
        grid0.addWidget(self.film_scale_stroke_entry, 16, 1)

        grid0.addWidget(QtWidgets.QLabel(''), 17, 0)

        # Film Type
        self.film_type = RadioSet([{'label': _('Positive'), 'value': 'pos'},
                                   {'label': _('Negative'), 'value': 'neg'}],
                                  stretch=False)
        self.film_type_label = QtWidgets.QLabel(_("Film Type:"))
        self.film_type_label.setToolTip(
            _("Generate a Positive black film or a Negative film.\n"
              "Positive means that it will print the features\n"
              "with black on a white canvas.\n"
              "Negative means that it will print the features\n"
              "with white on a black canvas.\n"
              "The Film format is SVG.")
        )
        grid0.addWidget(self.film_type_label, 18, 0)
        grid0.addWidget(self.film_type, 18, 1)

        # Boundary for negative film generation
        self.boundary_entry = FCDoubleSpinner()
        self.boundary_entry.set_range(-999.9999, 999.9999)
        self.boundary_entry.setSingleStep(0.01)
        self.boundary_entry.set_precision(self.decimals)

        self.boundary_label = QtWidgets.QLabel('%s:' % _("Border"))
        self.boundary_label.setToolTip(
            _("Specify a border around the object.\n"
              "Only for negative film.\n"
              "It helps if we use as a Box Object the same \n"
              "object as in Film Object. It will create a thick\n"
              "black bar around the actual print allowing for a\n"
              "better delimitation of the outline features which are of\n"
              "white color like the rest and which may confound with the\n"
              "surroundings if not for this border.")
        )
        grid0.addWidget(self.boundary_label, 19, 0)
        grid0.addWidget(self.boundary_entry, 19, 1)

        self.boundary_label.hide()
        self.boundary_entry.hide()

        # Punch Drill holes
        self.punch_cb = FCCheckBox(_("Punch drill holes"))
        self.punch_cb.setToolTip(_("When checked the generated film will have holes in pads when\n"
                                   "the generated film is positive. This is done to help drilling,\n"
                                   "when done manually."))
        grid0.addWidget(self.punch_cb, 20, 0, 1, 2)

        # this way I can hide/show the frame
        self.punch_frame = QtWidgets.QFrame()
        self.punch_frame.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.punch_frame)
        punch_grid = QtWidgets.QGridLayout()
        punch_grid.setContentsMargins(0, 0, 0, 0)
        self.punch_frame.setLayout(punch_grid)

        punch_grid.setColumnStretch(0, 0)
        punch_grid.setColumnStretch(1, 1)

        self.ois_p = OptionalHideInputSection(self.punch_cb, [self.punch_frame])

        self.source_label = QtWidgets.QLabel('%s:' % _("Source"))
        self.source_label.setToolTip(
            _("The punch hole source can be:\n"
              "- Excellon -> an Excellon holes center will serve as reference.\n"
              "- Pad Center -> will try to use the pads center as reference.")
        )
        self.source_punch = RadioSet([{'label': _('Excellon'), 'value': 'exc'},
                                      {'label': _('Pad center'), 'value': 'pad'}],
                                     stretch=False)
        punch_grid.addWidget(self.source_label, 0, 0)
        punch_grid.addWidget(self.source_punch, 0, 1)

        self.exc_label = QtWidgets.QLabel('%s:' % _("Excellon Obj"))
        self.exc_label.setToolTip(
            _("Remove the geometry of Excellon from the Film to create the holes in pads.")
        )
        self.exc_combo = QtWidgets.QComboBox()
        self.exc_combo.setModel(self.app.collection)
        self.exc_combo.setRootModelIndex(self.app.collection.index(1, 0, QtCore.QModelIndex()))
        self.exc_combo.setCurrentIndex(1)
        punch_grid.addWidget(self.exc_label, 1, 0)
        punch_grid.addWidget(self.exc_combo, 1, 1)

        self.exc_label.hide()
        self.exc_combo.hide()

        self.punch_size_label = QtWidgets.QLabel('%s:' % _("Punch Size"))
        self.punch_size_label.setToolTip(_("The value here will control how big is the punch hole in the pads."))
        self.punch_size_spinner = FCDoubleSpinner()
        self.punch_size_spinner.set_range(0, 999.9999)
        self.punch_size_spinner.setSingleStep(0.1)
        self.punch_size_spinner.set_precision(self.decimals)

        punch_grid.addWidget(self.punch_size_label, 2, 0)
        punch_grid.addWidget(self.punch_size_spinner, 2, 1)

        self.punch_size_label.hide()
        self.punch_size_spinner.hide()

        # Buttons
        hlay = QtWidgets.QHBoxLayout()
        self.layout.addLayout(hlay)

        self.film_object_button = QtWidgets.QPushButton(_("Save Film"))
        self.film_object_button.setToolTip(
            _("Create a Film for the selected object, within\n"
              "the specified box. Does not create a new \n "
              "FlatCAM object, but directly save it in SVG format\n"
              "which can be opened with Inkscape.")
        )
        hlay.addWidget(self.film_object_button)

        self.layout.addStretch()

        # ## Signals
        self.film_object_button.clicked.connect(self.on_film_creation)
        self.tf_type_obj_combo.currentIndexChanged.connect(self.on_type_obj_index_changed)
        self.tf_type_box_combo.currentIndexChanged.connect(self.on_type_box_index_changed)

        self.film_type.activated_custom.connect(self.on_film_type)
        self.source_punch.activated_custom.connect(self.on_punch_source)

    def on_type_obj_index_changed(self, index):
        obj_type = self.tf_type_obj_combo.currentIndex()
        self.tf_object_combo.setRootModelIndex(self.app.collection.index(obj_type, 0, QtCore.QModelIndex()))
        self.tf_object_combo.setCurrentIndex(0)

    def on_type_box_index_changed(self, index):
        obj_type = self.tf_type_box_combo.currentIndex()
        self.tf_box_combo.setRootModelIndex(self.app.collection.index(obj_type, 0, QtCore.QModelIndex()))
        self.tf_box_combo.setCurrentIndex(0)

    def run(self, toggle=True):
        self.app.report_usage("ToolFilm()")

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

        self.app.ui.notebook.setTabText(2, _("Film Tool"))

    def install(self, icon=None, separator=None, **kwargs):
        FlatCAMTool.install(self, icon, separator, shortcut='ALT+L', **kwargs)

    def set_tool_ui(self):
        self.reset_fields()

        f_type = self.app.defaults["tools_film_type"] if self.app.defaults["tools_film_type"] else 'neg'
        self.film_type.set_value(str(f_type))
        self.on_film_type(val=f_type)

        b_entry = self.app.defaults["tools_film_boundary"] if self.app.defaults["tools_film_boundary"] else 0.0
        self.boundary_entry.set_value(float(b_entry))

        scale_stroke_width = self.app.defaults["tools_film_scale_stroke"] if \
            self.app.defaults["tools_film_scale_stroke"] else 0.0
        self.film_scale_stroke_entry.set_value(int(scale_stroke_width))

        self.punch_cb.set_value(False)
        self.source_punch.set_value('exc')

        self.film_scale_cb.set_value(self.app.defaults["tools_film_scale_cb"])
        self.film_scalex_entry.set_value(float(self.app.defaults["tools_film_scale_x_entry"]))
        self.film_scaley_entry.set_value(float(self.app.defaults["tools_film_scale_y_entry"]))
        self.film_skew_cb.set_value(self.app.defaults["tools_film_skew_cb"])
        self.film_skewx_entry.set_value(float(self.app.defaults["tools_film_skew_x_entry"]))
        self.film_skewy_entry.set_value(float(self.app.defaults["tools_film_skew_y_entry"]))
        self.film_skew_reference.set_value(self.app.defaults["tools_film_skew_ref_radio"])
        self.film_mirror_cb.set_value(self.app.defaults["tools_film_mirror_cb"])
        self.film_mirror_axis.set_value(self.app.defaults["tools_film_mirror_axis_radio"])

    def on_film_type(self, val):
        type_of_film = val

        if type_of_film == 'neg':
            self.boundary_label.show()
            self.boundary_entry.show()
            self.punch_cb.set_value(False)  # required so the self.punch_frame it's hidden also by the signal emitted
            self.punch_cb.hide()
        else:
            self.boundary_label.hide()
            self.boundary_entry.hide()
            self.punch_cb.show()

    def on_punch_source(self, val):
        if val == 'pad' and self.punch_cb.get_value():
            self.punch_size_label.show()
            self.punch_size_spinner.show()
            self.exc_label.hide()
            self.exc_combo.hide()
        else:
            self.punch_size_label.hide()
            self.punch_size_spinner.hide()
            self.exc_label.show()
            self.exc_combo.show()

        if val == 'pad' and self.tf_type_obj_combo.currentText() == 'Geometry':
            self.source_punch.set_value('exc')
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Using the Pad center does not work on Geometry objects. "
                                                          "Only a Gerber object has pads."))

    def on_film_creation(self):
        log.debug("ToolFilm.Film.on_film_creation() started ...")

        try:
            name = self.tf_object_combo.currentText()
        except Exception as e:
            self.app.inform.emit('[ERROR_NOTCL] %s' %
                                 _("No FlatCAM object selected. Load an object for Film and retry."))
            return

        try:
            boxname = self.tf_box_combo.currentText()
        except Exception as e:
            self.app.inform.emit('[ERROR_NOTCL] %s' %
                                 _("No FlatCAM object selected. Load an object for Box and retry."))
            return

        scale_stroke_width = float(self.film_scale_stroke_entry.get_value())

        source = self.source_punch.get_value()

        # #################################################################
        # ################ STARTING THE JOB ###############################
        # #################################################################

        self.app.inform.emit(_("Generating Film ..."))

        if self.film_type.get_value() == "pos":

            if self.punch_cb.get_value() is False:
                self.generate_positive_normal_film(name, boxname, factor=scale_stroke_width)
            else:
                self.generate_positive_punched_film(name, boxname, source, factor=scale_stroke_width)
        else:
            self.generate_negative_film(name, boxname, factor=scale_stroke_width)

    def generate_positive_normal_film(self, name, boxname, factor):
        log.debug("ToolFilm.Film.generate_positive_normal_film() started ...")

        scale_factor_x = None
        scale_factor_y = None
        skew_factor_x = None
        skew_factor_y = None
        mirror = None
        skew_reference = 'center'

        if self.film_scale_cb.get_value():
            if self.film_scalex_entry.get_value() != 1.0:
                scale_factor_x = self.film_scalex_entry.get_value()
            if self.film_scaley_entry.get_value() != 1.0:
                scale_factor_y = self.film_scaley_entry.get_value()
        if self.film_skew_cb.get_value():
            if self.film_skewx_entry.get_value() != 0.0:
                skew_factor_x = self.film_skewx_entry.get_value()
            if self.film_skewy_entry.get_value() != 0.0:
                skew_factor_y = self.film_skewy_entry.get_value()

            skew_reference = self.film_skew_reference.get_value()
        if self.film_mirror_cb.get_value():
            if self.film_mirror_axis.get_value() != 'none':
                mirror = self.film_mirror_axis.get_value()
        try:
            filename, _f = QtWidgets.QFileDialog.getSaveFileName(
                caption=_("Export SVG positive"),
                directory=self.app.get_last_save_folder() + '/' + name,
                filter="*.svg")
        except TypeError:
            filename, _f = QtWidgets.QFileDialog.getSaveFileName(caption=_("Export SVG positive"))

        filename = str(filename)

        if str(filename) == "":
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Export SVG positive cancelled."))
            return
        else:
            self.app.export_svg_positive(name, boxname, filename,
                                         scale_stroke_factor=factor,
                                         scale_factor_x=scale_factor_x, scale_factor_y=scale_factor_y,
                                         skew_factor_x=skew_factor_x, skew_factor_y=skew_factor_y,
                                         skew_reference=skew_reference,
                                         mirror=mirror
                                         )

    def generate_positive_punched_film(self, name, boxname, source, factor):

        film_obj = self.app.collection.get_by_name(name)

        if source == 'exc':
            log.debug("ToolFilm.Film.generate_positive_punched_film() with Excellon source started ...")

            try:
                exc_name = self.exc_combo.currentText()
            except Exception as e:
                self.app.inform.emit('[ERROR_NOTCL] %s' %
                                     _("No Excellon object selected. Load an object for punching reference and retry."))
                return

            exc_obj = self.app.collection.get_by_name(exc_name)
            exc_solid_geometry = MultiPolygon(exc_obj.solid_geometry)
            punched_solid_geometry = MultiPolygon(film_obj.solid_geometry).difference(exc_solid_geometry)

            def init_func(new_obj, app_obj):
                new_obj.solid_geometry = deepcopy(punched_solid_geometry)

            outname = name + "_punched"
            self.app.new_object('gerber', outname, init_func)

            self.generate_positive_normal_film(outname, boxname, factor=factor)
        else:
            log.debug("ToolFilm.Film.generate_positive_punched_film() with Pad center source started ...")

            punch_size = float(self.punch_size_spinner.get_value())

            punching_geo = list()
            for apid in film_obj.apertures:
                if film_obj.apertures[apid]['type'] == 'C':
                    if punch_size >= float(film_obj.apertures[apid]['size']):
                        self.app.inform.emit('[ERROR_NOTCL] %s' %
                                             _(" Could not generate punched hole film because the punch hole size"
                                               "is bigger than some of the apertures in the Gerber object."))
                        return 'fail'
                    else:
                        for elem in film_obj.apertures[apid]['geometry']:
                            if 'follow' in elem:
                                if isinstance(elem['follow'], Point):
                                    punching_geo.append(elem['follow'].buffer(punch_size / 2))
                else:
                    if punch_size >= float(film_obj.apertures[apid]['width']) or \
                            punch_size >= float(film_obj.apertures[apid]['height']):
                        self.app.inform.emit('[ERROR_NOTCL] %s' %
                                             _("Could not generate punched hole film because the punch hole size"
                                               "is bigger than some of the apertures in the Gerber object."))
                        return 'fail'
                    else:
                        for elem in film_obj.apertures[apid]['geometry']:
                            if 'follow' in elem:
                                if isinstance(elem['follow'], Point):
                                    punching_geo.append(elem['follow'].buffer(punch_size / 2))

            punching_geo = MultiPolygon(punching_geo)
            if not isinstance(film_obj.solid_geometry, Polygon):
                temp_solid_geometry = MultiPolygon(film_obj.solid_geometry)
            else:
                temp_solid_geometry = film_obj.solid_geometry
            punched_solid_geometry = temp_solid_geometry.difference(punching_geo)

            if punched_solid_geometry == temp_solid_geometry:
                self.app.inform.emit('[WARNING_NOTCL] %s' %
                                     _("Could not generate punched hole film because the newly created object geometry "
                                       "is the same as the one in the source object geometry..."))
                return 'fail'

            def init_func(new_obj, app_obj):
                new_obj.solid_geometry = deepcopy(punched_solid_geometry)

            outname = name + "_punched"
            self.app.new_object('gerber', outname, init_func)

            self.generate_positive_normal_film(outname, boxname, factor=factor)

    def generate_negative_film(self, name, boxname, factor):
        log.debug("ToolFilm.Film.generate_negative_film() started ...")

        scale_factor_x = None
        scale_factor_y = None
        skew_factor_x = None
        skew_factor_y = None
        mirror = None
        skew_reference = 'center'

        if self.film_scale_cb.get_value():
            if self.film_scalex_entry.get_value() != 1.0:
                scale_factor_x = self.film_scalex_entry.get_value()
            if self.film_scaley_entry.get_value() != 1.0:
                scale_factor_y = self.film_scaley_entry.get_value()
        if self.film_skew_cb.get_value():
            if self.film_skewx_entry.get_value() != 0.0:
                skew_factor_x = self.film_skewx_entry.get_value()
            if self.film_skewy_entry.get_value() != 0.0:
                skew_factor_y = self.film_skewy_entry.get_value()

            skew_reference = self.film_skew_reference.get_value()
        if self.film_mirror_cb.get_value():
            if self.film_mirror_axis.get_value() != 'none':
                mirror = self.film_mirror_axis.get_value()

        border = float(self.boundary_entry.get_value())

        if border is None:
            border = 0

        try:
            filename, _f = QtWidgets.QFileDialog.getSaveFileName(
                caption=_("Export SVG negative"),
                directory=self.app.get_last_save_folder() + '/' + name,
                filter="*.svg")
        except TypeError:
            filename, _f = QtWidgets.QFileDialog.getSaveFileName(caption=_("Export SVG negative"))

        filename = str(filename)

        if str(filename) == "":
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Export SVG negative cancelled."))
            return
        else:
            self.app.export_svg_negative(name, boxname, filename, border,
                                         scale_stroke_factor=factor,
                                         scale_factor_x=scale_factor_x, scale_factor_y=scale_factor_y,
                                         skew_factor_x=skew_factor_x, skew_factor_y=skew_factor_y,
                                         skew_reference=skew_reference,
                                         mirror=mirror
                                         )

    def reset_fields(self):
        self.tf_object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.tf_box_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
