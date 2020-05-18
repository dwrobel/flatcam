# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 2/14/2020                                          #
# MIT Licence                                              #
# ##########################################################

from PyQt5 import QtWidgets, QtCore

from AppTool import AppTool
from AppGUI.GUIElements import FCButton, FCDoubleSpinner, RadioSet, FCComboBox

from shapely.geometry import box

from copy import deepcopy

import logging
import gettext
import AppTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class ToolEtchCompensation(AppTool):

    toolName = _("Etch Compensation Tool")

    def __init__(self, app):
        self.app = app
        self.decimals = self.app.decimals

        AppTool.__init__(self, app)

        self.tools_frame = QtWidgets.QFrame()
        self.tools_frame.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.tools_frame)
        self.tools_box = QtWidgets.QVBoxLayout()
        self.tools_box.setContentsMargins(0, 0, 0, 0)
        self.tools_frame.setLayout(self.tools_box)

        # Title
        title_label = QtWidgets.QLabel("%s" % self.toolName)
        title_label.setStyleSheet("""
                        QLabel
                        {
                            font-size: 16px;
                            font-weight: bold;
                        }
                        """)
        self.tools_box.addWidget(title_label)

        # Grid Layout
        grid0 = QtWidgets.QGridLayout()
        grid0.setColumnStretch(0, 0)
        grid0.setColumnStretch(1, 1)
        self.tools_box.addLayout(grid0)

        grid0.addWidget(QtWidgets.QLabel(''), 0, 0, 1, 2)

        # Target Gerber Object
        self.gerber_combo = FCComboBox()
        self.gerber_combo.setModel(self.app.collection)
        self.gerber_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.gerber_combo.is_last = True
        self.gerber_combo.obj_type = "Gerber"

        self.gerber_label = QtWidgets.QLabel('<b>%s:</b>' % _("GERBER"))
        self.gerber_label.setToolTip(
            _("Gerber object that will be inverted.")
        )

        grid0.addWidget(self.gerber_label, 1, 0, 1, 2)
        grid0.addWidget(self.gerber_combo, 2, 0, 1, 2)

        grid0.addWidget(QtWidgets.QLabel(""), 3, 0, 1, 2)

        self.param_label = QtWidgets.QLabel("<b>%s:</b>" % _("Parameters"))
        self.param_label.setToolTip('%s.' % _("Parameters for this tool"))

        grid0.addWidget(self.param_label, 4, 0, 1, 2)

        # Thickness
        self.thick_label = QtWidgets.QLabel('%s:' % _('Copper Thickness'))
        self.thick_label.setToolTip(
            _("The thickness of the copper foil.\n"
              "In microns [um].")
        )
        self.thick_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.thick_entry.set_precision(self.decimals)
        self.thick_entry.set_range(0.0000, 9999.9999)
        self.thick_entry.setObjectName(_("Thickness"))

        grid0.addWidget(self.thick_label, 5, 0, 1, 2)
        grid0.addWidget(self.thick_entry, 6, 0, 1, 2)

        self.ratio_label = QtWidgets.QLabel('%s:' % _("Ratio"))
        self.ratio_label.setToolTip(
            _("The ratio of lateral etch versus depth etch.\n"
              "Can be:\n"
              "- custom -> the user will enter a custom value\n"
              "- preselection -> value which depends on a selection of etchants")
        )
        self.ratio_radio = RadioSet([
            {'label': _('PreSelection'), 'value': 'p'},
            {'label': _('Custom'), 'value': 'c'}
        ])

        grid0.addWidget(self.ratio_label, 7, 0, 1, 2)
        grid0.addWidget(self.ratio_radio, 8, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 9, 0, 1, 2)

        self.compensate_btn = FCButton(_('Compensate'))
        self.compensate_btn.setToolTip(
            _("Will increase the copper features thickness to compensate the lateral etch.")
        )
        self.compensate_btn.setStyleSheet("""
                        QPushButton
                        {
                            font-weight: bold;
                        }
                        """)
        grid0.addWidget(self.compensate_btn, 10, 0, 1, 2)

        self.tools_box.addStretch()

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
        self.tools_box.addWidget(self.reset_button)

        self.compensate_btn.clicked.connect(self.on_grb_invert)
        self.reset_button.clicked.connect(self.set_tool_ui)
        self.ratio_radio.activated_custom.connect(self.on_ratio_change)

    def install(self, icon=None, separator=None, **kwargs):
        AppTool.install(self, icon, separator, shortcut='', **kwargs)

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
        self.thick_entry.set_value(18)
        self.ratio_radio.set_value('p')

    def on_ratio_change(self, val):
        pass

    def on_grb_invert(self):
        margin = self.margin_entry.get_value()
        if round(margin, self.decimals) == 0.0:
            margin = 1E-10

        join_style = {'r': 1, 'b': 3, 's': 2}[self.join_radio.get_value()]
        if join_style is None:
            join_style = 'r'

        grb_circle_steps = int(self.app.defaults["gerber_circle_steps"])
        obj_name = self.gerber_combo.currentText()

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

        new_options = {}
        for opt in grb_obj.options:
            new_options[opt] = deepcopy(grb_obj.options[opt])

        new_apertures = {}

        # for apid, val in grb_obj.apertures.items():
        #     new_apertures[apid] = {}
        #     for key in val:
        #         if key == 'geometry':
        #             new_apertures[apid]['geometry'] = []
        #             for elem in val['geometry']:
        #                 geo_elem = {}
        #                 if 'follow' in elem:
        #                     try:
        #                         geo_elem['clear'] = elem['follow'].buffer(val['size'] / 2.0).exterior
        #                     except AttributeError:
        #                         # TODO should test if width or height is bigger
        #                         geo_elem['clear'] = elem['follow'].buffer(val['width'] / 2.0).exterior
        #                 if 'clear' in elem:
        #                     if isinstance(elem['clear'], Polygon):
        #                         try:
        #                             geo_elem['solid'] = elem['clear'].buffer(val['size'] / 2.0, grb_circle_steps)
        #                         except AttributeError:
        #                             # TODO should test if width or height is bigger
        #                             geo_elem['solid'] = elem['clear'].buffer(val['width'] / 2.0, grb_circle_steps)
        #                     else:
        #                         geo_elem['follow'] = elem['clear']
        #                 new_apertures[apid]['geometry'].append(deepcopy(geo_elem))
        #         else:
        #             new_apertures[apid][key] = deepcopy(val[key])

        if '0' not in new_apertures:
            new_apertures['0'] = {}
            new_apertures['0']['type'] = 'C'
            new_apertures['0']['size'] = 0.0
            new_apertures['0']['geometry'] = []

        try:
            for poly in new_solid_geometry:
                new_el = {}
                new_el['solid'] = poly
                new_el['follow'] = poly.exterior
                new_apertures['0']['geometry'].append(new_el)
        except TypeError:
            new_el = {}
            new_el['solid'] = new_solid_geometry
            new_el['follow'] = new_solid_geometry.exterior
            new_apertures['0']['geometry'].append(new_el)

        for td in new_apertures:
            print(td, new_apertures[td])

        def init_func(new_obj, app_obj):
            new_obj.options.update(new_options)
            new_obj.options['name'] = outname
            new_obj.fill_color = deepcopy(grb_obj.fill_color)
            new_obj.outline_color = deepcopy(grb_obj.outline_color)

            new_obj.apertures = deepcopy(new_apertures)

            new_obj.solid_geometry = deepcopy(new_solid_geometry)
            new_obj.source_file = self.app.export_gerber(obj_name=outname, filename=None,
                                                         local_use=new_obj, use_thread=False)

        self.app.app_obj.new_object('gerber', outname, init_func)

    def reset_fields(self):
        self.gerber_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))

    @staticmethod
    def poly2rings(poly):
        return [poly.exterior] + [interior for interior in poly.interiors]
# end of file
