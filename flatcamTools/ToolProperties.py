# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 3/10/2019                                          #
# MIT Licence                                              #
# ##########################################################

from PyQt5 import QtGui, QtCore, QtWidgets
from FlatCAMTool import FlatCAMTool

from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import cascaded_union

from copy import deepcopy
import math

import logging
import gettext
import FlatCAMTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class Properties(FlatCAMTool):
    toolName = _("Properties")

    calculations_finished = QtCore.pyqtSignal(float, float, float, float, float, object)

    def __init__(self, app):
        FlatCAMTool.__init__(self, app)

        self.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)

        self.decimals = self.app.decimals

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

        self.calculations_finished.connect(self.show_area_chull)

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
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("Properties Tool was not displayed. No object selected."))
            self.app.ui.notebook.setTabText(2, _("Tools"))
            self.properties_frame.hide()
            self.app.ui.notebook.setCurrentWidget(self.app.ui.project_tab)
            return

        # delete the selection shape, if any
        try:
            self.app.delete_selection_shape()
        except Exception as e:
            log.debug("ToolProperties.Properties.properties() --> %s" % str(e))

        # populate the properties items
        for obj in obj_list:
            self.addItems(obj)
            self.app.inform.emit('[success] %s' % _("Object Properties are displayed."))
        self.app.ui.notebook.setTabText(2, _("Properties Tool"))

    def addItems(self, obj):
        parent = self.treeWidget.invisibleRootItem()
        apertures = ''
        tools = ''
        drills = ''
        slots = ''
        others = ''

        font = QtGui.QFont()
        font.setBold(True)

        # main Items categories
        obj_type = self.addParent(parent, _('TYPE'), expanded=True, color=QtGui.QColor("#000000"), font=font)
        obj_name = self.addParent(parent, _('NAME'), expanded=True, color=QtGui.QColor("#000000"), font=font)
        dims = self.addParent(parent, _('Dimensions'), expanded=True, color=QtGui.QColor("#000000"), font=font)
        units = self.addParent(parent, _('Units'), expanded=True, color=QtGui.QColor("#000000"), font=font)
        options = self.addParent(parent, _('Options'), color=QtGui.QColor("#000000"), font=font)

        if obj.kind.lower() == 'gerber':
            apertures = self.addParent(parent, _('Apertures'), expanded=True, color=QtGui.QColor("#000000"), font=font)
        else:
            tools = self.addParent(parent, _('Tools'), expanded=True, color=QtGui.QColor("#000000"), font=font)

        if obj.kind.lower() == 'excellon':
            drills = self.addParent(parent, _('Drills'), expanded=True, color=QtGui.QColor("#000000"), font=font)
            slots = self.addParent(parent, _('Slots'), expanded=True, color=QtGui.QColor("#000000"), font=font)

        if obj.kind.lower() == 'cncjob':
            others = self.addParent(parent, _('Others'), expanded=True, color=QtGui.QColor("#000000"), font=font)

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

        def job_thread(obj_prop):
            proc = self.app.proc_container.new(_("Calculating dimensions ... Please wait."))

            length = 0.0
            width = 0.0
            area = 0.0
            copper_area = 0.0

            geo = obj_prop.solid_geometry
            if geo:
                # calculate physical dimensions
                try:
                    xmin, ymin, xmax, ymax = obj_prop.bounds()

                    length = abs(xmax - xmin)
                    width = abs(ymax - ymin)
                except Exception as e:
                    log.debug("PropertiesTool.addItems() -> calculate dimensions --> %s" % str(e))

                # calculate box area
                if self.app.defaults['units'].lower() == 'mm':
                    area = (length * width) / 100
                else:
                    area = length * width

                if obj_prop.kind.lower() == 'gerber':
                    # calculate copper area
                    try:
                        for geo_el in geo:
                            copper_area += geo_el.area
                    except TypeError:
                        copper_area += geo.area
                    copper_area /= 100
            else:
                xmin = []
                ymin = []
                xmax = []
                ymax = []

                if obj_prop.kind.lower() == 'cncjob':
                    try:
                        for tool_k in obj_prop.exc_cnc_tools:
                            x0, y0, x1, y1 = cascaded_union(obj_prop.exc_cnc_tools[tool_k]['solid_geometry']).bounds
                            xmin.append(x0)
                            ymin.append(y0)
                            xmax.append(x1)
                            ymax.append(y1)
                    except Exception as ee:
                        log.debug("PropertiesTool.addItems() --> %s" % str(ee))

                    try:
                        for tool_k in obj_prop.cnc_tools:
                            x0, y0, x1, y1 = cascaded_union(obj_prop.cnc_tools[tool_k]['solid_geometry']).bounds
                            xmin.append(x0)
                            ymin.append(y0)
                            xmax.append(x1)
                            ymax.append(y1)
                    except Exception as ee:
                        log.debug("PropertiesTool.addItems() --> %s" % str(ee))
                else:
                    try:
                        for tool_k in obj_prop.tools:
                            x0, y0, x1, y1 = cascaded_union(obj_prop.tools[tool_k]['solid_geometry']).bounds
                            xmin.append(x0)
                            ymin.append(y0)
                            xmax.append(x1)
                            ymax.append(y1)
                    except Exception as ee:
                        log.debug("PropertiesTool.addItems() --> %s" % str(ee))

                try:
                    xmin = min(xmin)
                    ymin = min(ymin)
                    xmax = max(xmax)
                    ymax = max(ymax)

                    length = abs(xmax - xmin)
                    width = abs(ymax - ymin)

                    # calculate box area
                    if self.app.defaults['units'].lower() == 'mm':
                        area = (length * width) / 100
                    else:
                        area = length * width

                    if obj_prop.kind.lower() == 'gerber':
                        # calculate copper area

                        # create a complete solid_geometry from the tools
                        geo_tools = list()
                        for tool_k in obj_prop.tools:
                            if 'solid_geometry' in obj_prop.tools[tool_k]:
                                for geo_el in obj_prop.tools[tool_k]['solid_geometry']:
                                    geo_tools.append(geo_el)

                        try:
                            for geo_el in geo_tools:
                                copper_area += geo_el.area
                        except TypeError:
                            copper_area += geo_tools.area
                        copper_area /= 100
                except Exception as e:
                    log.debug("Properties.addItems() --> %s" % str(e))

            area_chull = 0.0
            if obj_prop.kind.lower() != 'cncjob':
                # calculate and add convex hull area
                if geo:
                    if isinstance(geo, MultiPolygon):
                        env_obj = geo.convex_hull
                    elif (isinstance(geo, MultiPolygon) and len(geo) == 1) or \
                            (isinstance(geo, list) and len(geo) == 1) and isinstance(geo[0], Polygon):
                        env_obj = cascaded_union(obj_prop.solid_geometry)
                        env_obj = env_obj.convex_hull
                    else:
                        env_obj = cascaded_union(obj_prop.solid_geometry)
                        env_obj = env_obj.convex_hull

                    area_chull = env_obj.area
                else:
                    try:
                        area_chull = []
                        for tool_k in obj_prop.tools:
                            area_el = cascaded_union(obj_prop.tools[tool_k]['solid_geometry']).convex_hull
                            area_chull.append(area_el.area)
                        area_chull = max(area_chull)
                    except Exception as e:
                        area_chull = None
                        log.debug("Properties.addItems() --> %s" % str(e))

            if self.app.defaults['units'].lower() == 'mm':
                area_chull = area_chull / 100

            self.calculations_finished.emit(area, length, width, area_chull, copper_area, dims)

        self.app.worker_task.emit({'fcn': job_thread, 'params': [obj]})

        # Units items
        f_unit = {'in': _('Inch'), 'mm': _('MM')}[str(self.app.defaults['units'].lower())]
        self.addChild(units, ['FlatCAM units:', f_unit], True)

        o_unit = {
            'in': _('Inch'),
            'mm': _('Metric'),
            'inch': _('Inch'),
            'metric': _('Metric')
        }[str(obj.units_found.lower())]
        self.addChild(units, ['Object units:', o_unit], True)

        # Options items
        for option in obj.options:
            if option is 'name':
                continue
            self.addChild(options, [str(option), str(obj.options[option])], True)

        # Items that depend on the object type
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
            tot_drill_cnt = 0
            tot_slot_cnt = 0

            for tool, value in obj.tools.items():
                toolid = self.addParent(tools, str(tool), expanded=False, color=QtGui.QColor("#000000"), font=font)

                drill_cnt = 0  # variable to store the nr of drills per tool
                slot_cnt = 0  # variable to store the nr of slots per tool

                # Find no of drills for the current tool
                for drill in obj.drills:
                    if drill['tool'] == tool:
                        drill_cnt += 1

                tot_drill_cnt += drill_cnt

                # Find no of slots for the current tool
                for slot in obj.slots:
                    if slot['tool'] == tool:
                        slot_cnt += 1

                tot_slot_cnt += slot_cnt

                self.addChild(toolid, [_('Diameter'), str(value['C'])], True)
                self.addChild(toolid, [_('Drills number'), str(drill_cnt)], True)
                self.addChild(toolid, [_('Slots number'), str(slot_cnt)], True)

            self.addChild(drills, [_('Drills total number:'), str(tot_drill_cnt)], True)
            self.addChild(slots, [_('Slots total number:'), str(tot_slot_cnt)], True)
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
            # for cncjob objects made from gerber or geometry
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

            # for cncjob objects made from excellon
            for tool, value in obj.exc_cnc_tools.items():
                exc_tool = self.addParent(
                    tools, str(value['tool']), expanded=False, color=QtGui.QColor("#000000"), font=font
                )
                self.addChild(exc_tool, [_('Diameter'), str(tool)], True)
                for k, v in value.items():
                    if k == 'solid_geometry':
                        printed_value = _('Present') if v else _('None')
                        self.addChild(exc_tool, [str(k), printed_value], True)
                    elif k == 'nr_drills':
                        self.addChild(exc_tool, [_("Drills number"), str(v)], True)
                    elif k == 'nr_slots':
                        self.addChild(exc_tool, [_("Slots number"), str(v)], True)
                    else:
                        pass

            r_time = obj.routing_time
            if r_time > 1:
                units_lbl = 'min'
            else:
                r_time *= 60
                units_lbl = 'sec'
            r_time = math.ceil(float(r_time))
            self.addChild(others, ['%s (%s):' % (_('Routing time'), units_lbl), str(r_time)], True)
            self.addChild(others, ['%s (%s):' % (_('Travelled distance'), f_unit), str(obj.travel_distance)], True)

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

    def show_area_chull(self, area, length, width, chull_area, copper_area, location):

        # add dimensions
        self.addChild(
            location,
            ['%s:' % _('Length'), '%.*f %s' % (self.decimals, length, self.app.defaults['units'].lower())],
            True
        )
        self.addChild(
            location,
            ['%s:' % _('Width'), '%.*f %s' % (self.decimals, width, self.app.defaults['units'].lower())],
            True
        )

        # add box area
        if self.app.defaults['units'].lower() == 'mm':
            self.addChild(location, ['%s:' % _('Box Area'), '%.*f %s' % (self.decimals, area, 'cm2')], True)
            self.addChild(
                location,
                ['%s:' % _('Convex_Hull Area'), '%.*f %s' % (self.decimals, chull_area, 'cm2')],
                True
            )

        else:
            self.addChild(location, ['%s:' % _('Box Area'), '%.*f %s' % (self.decimals, area, 'in2')], True)
            self.addChild(
                location,
                ['%s:' % _('Convex_Hull Area'), '%.*f %s' % (self.decimals, chull_area, 'in2')],
                True
            )

        # add copper area
        if self.app.defaults['units'].lower() == 'mm':
            self.addChild(location, ['%s:' % _('Copper Area'), '%.*f %s' % (self.decimals, copper_area, 'cm2')], True)
        else:
            self.addChild(location, ['%s:' % _('Copper Area'), '%.*f %s' % (self.decimals, copper_area, 'in2')], True)

# end of file
