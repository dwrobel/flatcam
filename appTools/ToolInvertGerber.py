# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 2/14/2020                                          #
# MIT Licence                                              #
# ##########################################################

from PyQt5 import QtWidgets, QtCore, QtGui

from appTool import AppTool
from appGUI.GUIElements import FCButton, FCDoubleSpinner, RadioSet, FCComboBox, FCLabel

from shapely.geometry import box

from copy import deepcopy

import logging
import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class ToolInvertGerber(AppTool):

    def __init__(self, app):
        self.app = app
        self.decimals = self.app.decimals

        AppTool.__init__(self, app)

        # #############################################################################
        # ######################### Tool GUI ##########################################
        # #############################################################################
        self.ui = InvertUI(layout=self.layout, app=self.app)
        self.toolName = self.ui.toolName

        self.ui.invert_btn.clicked.connect(self.on_grb_invert)
        self.ui.reset_button.clicked.connect(self.set_tool_ui)

    def install(self, icon=None, separator=None, **kwargs):
        AppTool.install(self, icon, separator, shortcut='ALT+G', **kwargs)

    def run(self, toggle=True):
        self.app.defaults.report_usage("ToolInvertGerber()")
        log.debug("ToolInvertGerber() is running ...")

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

        self.app.ui.notebook.setTabText(2, _("Invert Tool"))

    def set_tool_ui(self):
        self.ui.margin_entry.set_value(float(self.app.defaults["tools_invert_margin"]))
        self.ui.join_radio.set_value(self.app.defaults["tools_invert_join_style"])

    def on_grb_invert(self):
        margin = self.ui.margin_entry.get_value()
        if round(margin, self.decimals) == 0.0:
            margin = 1E-10

        join_style = {'r': 1, 'b': 3, 's': 2}[self.ui.join_radio.get_value()]
        if join_style is None:
            join_style = 'r'

        grb_circle_steps = int(self.app.defaults["gerber_circle_steps"])
        obj_name = self.ui.gerber_combo.currentText()

        outname = obj_name + "_inverted"

        # Get source object.
        try:
            grb_obj = self.app.collection.get_by_name(obj_name)
        except Exception as e:
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Could not retrieve object"), str(obj_name)))
            return "Could not retrieve object: %s with error: %s" % (obj_name, str(e))

        if grb_obj is None:
            if obj_name == '':
                obj_name = 'None'
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Object not found"), str(obj_name)))
            return

        xmin, ymin, xmax, ymax = grb_obj.bounds()

        grb_box = box(xmin, ymin, xmax, ymax).buffer(margin, resolution=grb_circle_steps, join_style=join_style)

        try:
            __ = iter(grb_obj.solid_geometry)
        except TypeError:
            grb_obj.solid_geometry = list(grb_obj.solid_geometry)

        new_solid_geometry = deepcopy(grb_box)

        for poly in grb_obj.solid_geometry:
            new_solid_geometry = new_solid_geometry.difference(poly)

        try:
            __ = iter(new_solid_geometry)
        except TypeError:
            new_solid_geometry = [new_solid_geometry]

        new_options = {}
        for opt in grb_obj.options:
            new_options[opt] = deepcopy(grb_obj.options[opt])

        new_apertures = {}

        if '0' not in new_apertures:
            new_apertures['0'] = {
                'type': 'C',
                'size': 0.0,
                'geometry': []
            }

        try:
            for poly in new_solid_geometry:
                new_el = {'solid': poly, 'follow': poly.exterior}
                new_apertures['0']['geometry'].append(new_el)
        except TypeError:
            new_el = {'solid': new_solid_geometry, 'follow': new_solid_geometry.exterior}
            new_apertures['0']['geometry'].append(new_el)

        def init_func(new_obj, app_obj):
            new_obj.options.update(new_options)
            new_obj.options['name'] = outname
            new_obj.fill_color = deepcopy(grb_obj.fill_color)
            new_obj.outline_color = deepcopy(grb_obj.outline_color)

            new_obj.apertures = deepcopy(new_apertures)

            new_obj.solid_geometry = deepcopy(new_solid_geometry)
            new_obj.source_file = app_obj.f_handlers.export_gerber(obj_name=outname, filename=None,
                                                                   local_use=new_obj, use_thread=False)

        self.app.app_obj.new_object('gerber', outname, init_func)

    def reset_fields(self):
        self.ui.gerber_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))

    @staticmethod
    def poly2rings(poly):
        return [poly.exterior] + [interior for interior in poly.interiors]


class InvertUI:
    
    toolName = _("Invert Gerber Tool")

    def __init__(self, layout, app):
        self.app = app
        self.decimals = self.app.decimals
        self.layout = layout

        # ## Title
        title_label = FCLabel("%s" % self.toolName)
        title_label.setStyleSheet("""
                                QLabel
                                {
                                    font-size: 16px;
                                    font-weight: bold;
                                }
                                """)
        self.layout.addWidget(title_label)
        self.layout.addWidget(FCLabel(""))

        self.tools_frame = QtWidgets.QFrame()
        self.tools_frame.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.tools_frame)

        self.tools_box = QtWidgets.QVBoxLayout()
        self.tools_box.setContentsMargins(0, 0, 0, 0)
        self.tools_frame.setLayout(self.tools_box)

        # Grid Layout
        grid0 = QtWidgets.QGridLayout()
        grid0.setColumnStretch(0, 0)
        grid0.setColumnStretch(1, 1)
        self.tools_box.addLayout(grid0)

        # Target Gerber Object
        self.gerber_combo = FCComboBox()
        self.gerber_combo.setModel(self.app.collection)
        self.gerber_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.gerber_combo.is_last = True
        self.gerber_combo.obj_type = "Gerber"

        self.gerber_label = FCLabel('<b>%s:</b>' % _("GERBER"))
        self.gerber_label.setToolTip(
            _("Gerber object that will be inverted.")
        )

        grid0.addWidget(self.gerber_label, 1, 0, 1, 2)
        grid0.addWidget(self.gerber_combo, 2, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 3, 0, 1, 2)

        self.param_label = FCLabel("<b>%s:</b>" % _("Parameters"))
        self.param_label.setToolTip('%s.' % _("Parameters for this tool"))

        grid0.addWidget(self.param_label, 4, 0, 1, 2)

        # Margin
        self.margin_label = FCLabel('%s:' % _('Margin'))
        self.margin_label.setToolTip(
            _("Distance by which to avoid\n"
              "the edges of the Gerber object.")
        )
        self.margin_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.margin_entry.set_precision(self.decimals)
        self.margin_entry.set_range(0.0000, 10000.0000)
        self.margin_entry.setObjectName(_("Margin"))

        grid0.addWidget(self.margin_label, 5, 0, 1, 2)
        grid0.addWidget(self.margin_entry, 6, 0, 1, 2)

        self.join_label = FCLabel('%s:' % _("Lines Join Style"))
        self.join_label.setToolTip(
            _("The way that the lines in the object outline will be joined.\n"
              "Can be:\n"
              "- rounded -> an arc is added between two joining lines\n"
              "- square -> the lines meet in 90 degrees angle\n"
              "- bevel -> the lines are joined by a third line")
        )
        self.join_radio = RadioSet([
            {'label': _('Rounded'), 'value': 'r'},
            {'label': _('Square'), 'value': 's'},
            {'label': _('Bevel'), 'value': 'b'}
        ], orientation='vertical', stretch=False)

        grid0.addWidget(self.join_label, 7, 0, 1, 2)
        grid0.addWidget(self.join_radio, 8, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 9, 0, 1, 2)

        self.invert_btn = FCButton(_('Invert Gerber'))
        self.invert_btn.setIcon(QtGui.QIcon(self.app.resource_location + '/invert32.png'))
        self.invert_btn.setToolTip(
            _("Will invert the Gerber object: areas that have copper\n"
              "will be empty of copper and previous empty area will be\n"
              "filled with copper.")
        )
        self.invert_btn.setStyleSheet("""
                                QPushButton
                                {
                                    font-weight: bold;
                                }
                                """)
        grid0.addWidget(self.invert_btn, 10, 0, 1, 2)

        self.tools_box.addStretch()

        # ## Reset Tool
        self.reset_button = FCButton(_("Reset Tool"))
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
        self.tools_box.addWidget(self.reset_button)

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
