# ########################################################## ##
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 3/10/2019                                          #
# MIT Licence                                              #
# ########################################################## ##

from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtCore import Qt
from FlatCAMTool import FlatCAMTool
from FlatCAMObj import *

import gettext
import FlatCAMTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class Properties(FlatCAMTool):

    toolName = _("Properties")

    def __init__(self, app):
        FlatCAMTool.__init__(self, app)

        self.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)

        # this way I can hide/show the frame
        self.properties_frame = QtWidgets.QFrame()
        self.properties_frame.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.properties_frame)
        self.properties_box = QtWidgets.QVBoxLayout()
        self.properties_box.setContentsMargins(0, 0, 0, 0)
        self.properties_frame.setLayout(self.properties_box)

        # ## Title
        title_label = QtWidgets.QLabel("%s" % self.toolName)
        title_label.setStyleSheet("""
                        QLabel
                        {
                            font-size: 16px;
                            font-weight: bold;
                        }
                        """)
        self.properties_box.addWidget(title_label)

        # self.layout.setMargin(0)  # PyQt4
        self.properties_box.setContentsMargins(0, 0, 0, 0)  # PyQt5

        self.vlay = QtWidgets.QVBoxLayout()

        self.properties_box.addLayout(self.vlay)

        self.treeWidget = QtWidgets.QTreeWidget()
        self.treeWidget.setColumnCount(2)
        self.treeWidget.setHeaderHidden(True)
        self.treeWidget.header().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.treeWidget.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Expanding)

        self.vlay.addWidget(self.treeWidget)
        self.vlay.setStretch(0, 0)

    def run(self, toggle=True):
        self.app.report_usage("ToolProperties()")

        if self.app.tool_tab_locked is True:
            return

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

        self.properties()

    def install(self, icon=None, separator=None, **kwargs):
        FlatCAMTool.install(self, icon, separator, shortcut='P', **kwargs)

    def set_tool_ui(self):
        # this reset the TreeWidget
        self.treeWidget.clear()
        self.properties_frame.show()

    def properties(self):
        obj_list = self.app.collection.get_selected()
        if not obj_list:
            self.app.inform.emit(_("[ERROR_NOTCL] Properties Tool was not displayed. No object selected."))
            self.app.ui.notebook.setTabText(2, _("Tools"))
            self.properties_frame.hide()
            self.app.ui.notebook.setCurrentWidget(self.app.ui.project_tab)
            return
        for obj in obj_list:
            self.addItems(obj)
            self.app.inform.emit(_("[success] Object Properties are displayed."))
        self.app.ui.notebook.setTabText(2, _("Properties Tool"))

    def addItems(self, obj):
        parent = self.treeWidget.invisibleRootItem()
        apertures = ''
        tools = ''

        font = QtGui.QFont()
        font.setBold(True)
        obj_type = self.addParent(parent, _('TYPE'), expanded=True, color=QtGui.QColor("#000000"), font=font)
        obj_name = self.addParent(parent, _('NAME'), expanded=True, color=QtGui.QColor("#000000"), font=font)
        dims = self.addParent(parent, _('Dimensions'), expanded=True, color=QtGui.QColor("#000000"), font=font)
        units = self.addParent(parent, _('Units'), expanded=True, color=QtGui.QColor("#000000"), font=font)

        options = self.addParent(parent, _('Options'), color=QtGui.QColor("#000000"), font=font)
        if obj.kind.lower() == 'gerber':
            apertures = self.addParent(parent, _('Apertures'), expanded=True, color=QtGui.QColor("#000000"), font=font)
        else:
            tools = self.addParent(parent, _('Tools'), expanded=True, color=QtGui.QColor("#000000"), font=font)

        separator = self.addParent(parent, '')

        self.addChild(obj_type, ['%s:' % _('Object Type'), ('%s' % (obj.kind.capitalize()))], True)
        try:
            self.addChild(obj_type,
                          ['%s:' % _('Geo Type'),
                           ('%s' % ({False: _("Single-Geo"), True: _("Multi-Geo")}[obj.multigeo]))],
                          True)
        except Exception as e:
            log.debug("Properties.addItems() --> %s" % str(e))

        self.addChild(obj_name, [obj.options['name']])

        # calculate physical dimensions
        try:
            xmin, ymin, xmax, ymax = obj.bounds()
        except Exception as e:
            log.debug("PropertiesTool.addItems() --> %s" % str(e))
            return

        length = abs(xmax - xmin)
        width = abs(ymax - ymin)

        self.addChild(dims, ['%s:' % _('Length'), '%.4f %s' % (
            length, self.app.ui.general_defaults_form.general_app_group.units_radio.get_value().lower())], True)
        self.addChild(dims, ['%s:' % _('Width'), '%.4f %s' % (
            width, self.app.ui.general_defaults_form.general_app_group.units_radio.get_value().lower())], True)

        # calculate and add box area
        if self.app.ui.general_defaults_form.general_app_group.units_radio.get_value().lower() == 'mm':
            area = (length * width) / 100
            self.addChild(dims, ['%s:' % _('Box Area'), '%.4f %s' % (area, 'cm2')], True)
        else:
            area = length * width
            self.addChild(dims, ['%s:' % _('Box Area'), '%.4f %s' % (area, 'in2')], True)

        # calculate and add convex hull area
        geo = obj.solid_geometry
        if isinstance(geo, MultiPolygon):
            env_obj = geo.convex_hull
        elif (isinstance(geo, MultiPolygon) and len(geo) == 1) or \
                (isinstance(geo, list) and len(geo) == 1) and isinstance(geo[0], Polygon):
            env_obj = cascaded_union(self.bound_obj.solid_geometry)
            env_obj = env_obj.convex_hull
        else:
            env_obj = cascaded_union(self.bound_obj.solid_geometry)
            env_obj = env_obj.convex_hull

        area_chull = env_obj.area
        if self.app.ui.general_defaults_form.general_app_group.units_radio.get_value().lower() == 'mm':
            area_chull = area_chull / 100
            self.addChild(dims, ['%s:' % _('Convex_Hull Area'), '%.4f %s' % (area_chull, 'cm2')], True)
        else:
            area_chull = area_chull
            self.addChild(dims, ['%s:' % _('Convex_Hull Area'), '%.4f %s' % (area_chull, 'in2')], True)

        self.addChild(units,
                      ['FlatCAM units:',
                       {
                           'in': _('Inch'),
                           'mm': _('Metric')
                       }
                       [str(self.app.ui.general_defaults_form.general_app_group.units_radio.get_value().lower())]
                       ],
                      True
                      )

        for option in obj.options:
            if option is 'name':
                continue
            self.addChild(options, [str(option), str(obj.options[option])], True)

        if obj.kind.lower() == 'gerber':
            temp_ap = dict()
            for ap in obj.apertures:
                temp_ap.clear()
                temp_ap = deepcopy(obj.apertures[ap])
                temp_ap.pop('geometry', None)

                solid_nr = 0
                follow_nr = 0
                clear_nr = 0

                if 'geometry' in obj.apertures[ap]:
                    if obj.apertures[ap]['geometry']:
                        font.setBold(True)
                        for el in obj.apertures[ap]['geometry']:
                            if 'solid' in el:
                                solid_nr += 1
                            if 'follow' in el:
                                follow_nr += 1
                            if 'clear' in el:
                                clear_nr += 1
                else:
                    font.setBold(False)
                temp_ap['Solid_Geo'] = '%s Polygons' % str(solid_nr)
                temp_ap['Follow_Geo'] = '%s LineStrings' % str(follow_nr)
                temp_ap['Clear_Geo'] = '%s Polygons' % str(clear_nr)

                apid = self.addParent(apertures, str(ap), expanded=False, color=QtGui.QColor("#000000"), font=font)
                for key in temp_ap:
                    self.addChild(apid, [str(key), str(temp_ap[key])], True)

        elif obj.kind.lower() == 'excellon':
            for tool, value in obj.tools.items():
                self.addChild(tools, [str(tool), str(value['C'])], True)
        elif obj.kind.lower() == 'geometry':
            for tool, value in obj.tools.items():
                geo_tool = self.addParent(tools, str(tool), expanded=True, color=QtGui.QColor("#000000"), font=font)
                for k, v in value.items():
                    if k == 'solid_geometry':
                        printed_value = _('Present') if v else _('None')
                        self.addChild(geo_tool, [str(k), printed_value], True)
                    elif k == 'data':
                        tool_data = self.addParent(geo_tool, str(k).capitalize(),
                                                   color=QtGui.QColor("#000000"), font=font)
                        for data_k, data_v in v.items():
                            self.addChild(tool_data, [str(data_k), str(data_v)], True)
                    else:
                        self.addChild(geo_tool, [str(k), str(v)], True)
        elif obj.kind.lower() == 'cncjob':
            for tool, value in obj.cnc_tools.items():
                geo_tool = self.addParent(tools, str(tool), expanded=True, color=QtGui.QColor("#000000"), font=font)
                for k, v in value.items():
                    if k == 'solid_geometry':
                        printed_value = _('Present') if v else _('None')
                        self.addChild(geo_tool, [str(k), printed_value], True)
                    elif k == 'gcode':
                        printed_value = _('Present') if v != '' else _('None')
                        self.addChild(geo_tool, [str(k), printed_value], True)
                    elif k == 'gcode_parsed':
                        printed_value = _('Present') if v else _('None')
                        self.addChild(geo_tool, [str(k), printed_value], True)
                    elif k == 'data':
                        tool_data = self.addParent(geo_tool, str(k).capitalize(),
                                                   color=QtGui.QColor("#000000"), font=font)
                        for data_k, data_v in v.items():
                            self.addChild(tool_data, [str(data_k), str(data_v)], True)
                    else:
                        self.addChild(geo_tool, [str(k), str(v)], True)

        self.addChild(separator, [''])

    def addParent(self, parent, title, expanded=False, color=None, font=None):
        item = QtWidgets.QTreeWidgetItem(parent, [title])
        item.setChildIndicatorPolicy(QtWidgets.QTreeWidgetItem.ShowIndicator)
        item.setExpanded(expanded)
        if color is not None:
            # item.setTextColor(0, color) # PyQt4
            item.setForeground(0, QtGui.QBrush(color))
        if font is not None:
            item.setFont(0, font)
        return item

    def addChild(self, parent, title, column1=None):
        item = QtWidgets.QTreeWidgetItem(parent)
        item.setText(0, str(title[0]))
        if column1 is not None:
            item.setText(1, str(title[1]))

# end of file
