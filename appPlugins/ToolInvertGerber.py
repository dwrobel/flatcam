# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 2/14/2020                                          #
# MIT Licence                                              #
# ##########################################################

from PyQt6 import QtWidgets, QtCore, QtGui

from appTool import AppTool
from appGUI.GUIElements import FCButton, FCDoubleSpinner, RadioSet, FCComboBox, FCLabel, \
    VerticalScrollArea, FCGridLayout, FCFrame
from camlib import flatten_shapely_geometry

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
        self.pluginName = self.ui.pluginName
        self.connect_signals_at_init()

    def install(self, icon=None, separator=None, **kwargs):
        AppTool.install(self, icon, separator, shortcut='ALT+G', **kwargs)

    def run(self, toggle=True):
        self.app.defaults.report_usage("ToolInvertGerber()")
        log.debug("ToolInvertGerber() is running ...")

        if toggle:
            # if the splitter is hidden, display it
            if self.app.ui.splitter.sizes()[0] == 0:
                self.app.ui.splitter.setSizes([1, 1])

            # if the Tool Tab is hidden display it, else hide it but only if the objectName is the same
            found_idx = None
            for idx in range(self.app.ui.notebook.count()):
                if self.app.ui.notebook.widget(idx).objectName() == "plugin_tab":
                    found_idx = idx
                    break
            # show the Tab
            if not found_idx:
                try:
                    self.app.ui.notebook.addTab(self.app.ui.plugin_tab, _("Plugin"))
                except RuntimeError:
                    self.app.ui.plugin_tab = QtWidgets.QWidget()
                    self.app.ui.plugin_tab.setObjectName("plugin_tab")
                    self.app.ui.plugin_tab_layout = QtWidgets.QVBoxLayout(self.app.ui.plugin_tab)
                    self.app.ui.plugin_tab_layout.setContentsMargins(2, 2, 2, 2)

                    self.app.ui.plugin_scroll_area = VerticalScrollArea()
                    self.app.ui.plugin_tab_layout.addWidget(self.app.ui.plugin_scroll_area)
                    self.app.ui.notebook.addTab(self.app.ui.plugin_tab, _("Plugin"))

                # focus on Tool Tab
                self.app.ui.notebook.setCurrentWidget(self.app.ui.plugin_tab)

            try:
                if self.app.ui.plugin_scroll_area.widget().objectName() == self.pluginName and found_idx:
                    # if the Tool Tab is not focused, focus on it
                    if not self.app.ui.notebook.currentWidget() is self.app.ui.plugin_tab:
                        # focus on Tool Tab
                        self.app.ui.notebook.setCurrentWidget(self.app.ui.plugin_tab)
                    else:
                        # else remove the Tool Tab
                        self.app.ui.notebook.setCurrentWidget(self.app.ui.properties_tab)
                        self.app.ui.notebook.removeTab(2)

                        # if there are no objects loaded in the app then hide the Notebook widget
                        if not self.app.collection.get_list():
                            self.app.ui.splitter.setSizes([0, 1])
            except AttributeError:
                pass
        else:
            if self.app.ui.splitter.sizes()[0] == 0:
                self.app.ui.splitter.setSizes([1, 1])

        AppTool.run(self)
        self.set_tool_ui()

        self.app.ui.notebook.setTabText(2, _("Invert Gerber"))

    def connect_signals_at_init(self):
        self.ui.invert_btn.clicked.connect(self.on_grb_invert)
        self.ui.reset_button.clicked.connect(self.set_tool_ui)

    def set_tool_ui(self):
        self.clear_ui(self.layout)
        self.ui = InvertUI(layout=self.layout, app=self.app)
        self.pluginName = self.ui.pluginName
        self.connect_signals_at_init()

        self.ui.margin_entry.set_value(float(self.app.defaults["tools_invert_margin"]))
        self.ui.join_radio.set_value(self.app.defaults["tools_invert_join_style"])

        # SELECT THE CURRENT OBJECT
        obj = self.app.collection.get_active()
        if obj and obj.kind == 'gerber':
            obj_name = obj.options['name']
            self.ui.gerber_combo.set_value(obj_name)

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
        new_solid_geometry = deepcopy(grb_box)

        grb_obj.solid_geometry = flatten_shapely_geometry(grb_obj.solid_geometry)
        for poly in grb_obj.solid_geometry:
            new_solid_geometry = new_solid_geometry.difference(poly)
        new_solid_geometry = flatten_shapely_geometry(new_solid_geometry)

        new_options = {}
        for opt in grb_obj.options:
            new_options[opt] = deepcopy(grb_obj.options[opt])

        new_apertures = {}

        if 0 not in new_apertures:
            new_apertures[0] = {
                'type':     'REG',
                'size':     0.0,
                'geometry': []
            }

        try:
            for poly in new_solid_geometry:
                new_el = {'solid': poly, 'follow': poly.exterior}
                new_apertures[0]['geometry'].append(new_el)
        except TypeError:
            new_el = {'solid': new_solid_geometry, 'follow': new_solid_geometry.exterior}
            new_apertures[0]['geometry'].append(new_el)

        def init_func(new_obj, app_obj):
            new_obj.options.update(new_options)
            new_obj.options['name'] = outname
            new_obj.fill_color = deepcopy(grb_obj.fill_color)
            new_obj.outline_color = deepcopy(grb_obj.outline_color)

            new_obj.tools = deepcopy(new_apertures)

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
    
    pluginName = _("Invert Gerber")

    def __init__(self, layout, app):
        self.app = app
        self.decimals = self.app.decimals
        self.layout = layout

        # ## Title
        title_label = FCLabel("%s" % self.pluginName)
        title_label.setStyleSheet("""
                                QLabel
                                {
                                    font-size: 16px;
                                    font-weight: bold;
                                }
                                """)
        self.layout.addWidget(title_label)

        self.tools_frame = QtWidgets.QFrame()
        self.tools_frame.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.tools_frame)

        self.tools_box = QtWidgets.QVBoxLayout()
        self.tools_box.setContentsMargins(0, 0, 0, 0)
        self.tools_frame.setLayout(self.tools_box)

        # #############################################################################################################
        # Source Object Frame
        # #############################################################################################################
        self.gerber_label = FCLabel('<span style="color:darkorange;"><b>%s</b></span>' % _("Source Object"))
        self.gerber_label.setToolTip(_("Gerber object that will be inverted."))
        self.tools_box.addWidget(self.gerber_label)

        # Target Gerber Object
        self.gerber_combo = FCComboBox()
        self.gerber_combo.setModel(self.app.collection)
        self.gerber_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.gerber_combo.is_last = True
        self.gerber_combo.obj_type = "Gerber"

        self.tools_box.addWidget(self.gerber_combo)

        # separator_line = QtWidgets.QFrame()
        # separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        # separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        # grid0.addWidget(separator_line, 3, 0, 1, 2)

        # #############################################################################################################
        # COMMON PARAMETERS Frame
        # #############################################################################################################
        self.param_label = FCLabel('<span style="color:blue;"><b>%s</b></span>' % _("Parameters"))
        self.param_label.setToolTip('%s.' % _("Parameters for this tool"))
        self.tools_box.addWidget(self.param_label)

        self.gp_frame = FCFrame()
        self.tools_box.addWidget(self.gp_frame)

        # Grid Layout
        grid0 = FCGridLayout(v_spacing=5, h_spacing=3)
        self.gp_frame.setLayout(grid0)

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

        grid0.addWidget(self.margin_label, 0, 0)
        grid0.addWidget(self.margin_entry, 0, 1)

        self.join_label = FCLabel('%s:  ' % _("Lines Join Style"))
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
        ], orientation='vertical', compact=True)

        grid0.addWidget(self.join_label, 2, 0)
        grid0.addWidget(self.join_radio, 2, 1)

        # #############################################################################################################
        # Generate Inverted Gerber Button
        # #############################################################################################################
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
        self.tools_box.addWidget(self.invert_btn)

        self.tools_box.addStretch(1)

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
