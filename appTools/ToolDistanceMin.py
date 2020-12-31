# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 09/29/2019                                         #
# MIT Licence                                              #
# ##########################################################

from PyQt5 import QtWidgets, QtCore
from appTool import AppTool
from appGUI.GUIElements import FCEntry, FCLabel, FCButton

from shapely.ops import nearest_points
from shapely.geometry import Point, MultiPolygon
from shapely.ops import unary_union

import math
import logging
import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class DistanceMin(AppTool):

    def __init__(self, app):
        AppTool.__init__(self, app)

        self.app = app
        self.canvas = self.app.plotcanvas
        self.units = self.app.defaults['units'].lower()
        self.decimals = self.app.decimals

        # #############################################################################
        # ######################### Tool GUI ##########################################
        # #############################################################################
        self.ui = DistMinUI(layout=self.layout, app=self.app)
        self.toolName = self.ui.toolName

        self.h_point = (0, 0)

        self.ui.measure_btn.clicked.connect(self.activate_measure_tool)
        self.ui.jump_hp_btn.clicked.connect(self.on_jump_to_half_point)

    def run(self, toggle=False):
        self.app.defaults.report_usage("ToolDistanceMin()")

        if self.app.tool_tab_locked is True:
            return

        # if the splitter is hidden, display it
        if self.app.ui.splitter.sizes()[0] == 0:
            self.app.ui.splitter.setSizes([1, 1])

        if toggle:
            pass

        self.set_tool_ui()
        self.app.inform.emit('MEASURING: %s' %
                             _("Select two objects and no more, to measure the distance between them ..."))

    def install(self, icon=None, separator=None, **kwargs):
        AppTool.install(self, icon, separator, shortcut='Shift+M', **kwargs)

    def set_tool_ui(self):
        # if the Tool Tab is hidden display it, else hide it but only if the objectName is the same
        found_idx = None
        for idx in range(self.app.ui.notebook.count()):
            if self.app.ui.notebook.widget(idx).objectName() == "tool_tab":
                found_idx = idx
                break
        # show the Tab
        if not found_idx:
            self.app.ui.notebook.addTab(self.app.ui.tool_tab, _("Tool"))
            # focus on Tool Tab
            self.app.ui.notebook.setCurrentWidget(self.app.ui.tool_tab)

        self.app.ui.notebook.setTabText(2, _("Minimum Distance Tool"))

        # Remove anything else in the appGUI
        self.app.ui.tool_scroll_area.takeWidget()

        # Put oneself in the appGUI
        self.app.ui.tool_scroll_area.setWidget(self)

        # Switch notebook to tool page
        self.app.ui.notebook.setCurrentWidget(self.app.ui.tool_tab)

        self.units = self.app.defaults['units'].lower()

        # initial view of the layout
        self.ui.start_entry.set_value('(0, 0)')
        self.ui.stop_entry.set_value('(0, 0)')

        self.ui.distance_x_entry.set_value('0.0')
        self.ui.distance_y_entry.set_value('0.0')
        self.ui.angle_entry.set_value('0.0')
        self.ui.total_distance_entry.set_value('0.0')
        self.ui.half_point_entry.set_value('(0, 0)')

        self.ui.jump_hp_btn.setDisabled(True)

        log.debug("Minimum Distance Tool --> tool initialized")

    def activate_measure_tool(self):
        # ENABLE the Measuring TOOL
        self.ui.jump_hp_btn.setDisabled(False)

        self.units = self.app.defaults['units'].lower()

        if self.app.call_source == 'app':
            selected_objs = self.app.collection.get_selected()
            if len(selected_objs) != 2:
                self.app.inform.emit('[WARNING_NOTCL] %s %s' %
                                     (_("Select two objects and no more. Currently the selection has objects: "),
                                      str(len(selected_objs))))
                return
            else:
                if isinstance(selected_objs[0].solid_geometry, list):
                    try:
                        selected_objs[0].solid_geometry = MultiPolygon(selected_objs[0].solid_geometry)
                    except Exception:
                        selected_objs[0].solid_geometry = unary_union(selected_objs[0].solid_geometry)

                    try:
                        selected_objs[1].solid_geometry = MultiPolygon(selected_objs[1].solid_geometry)
                    except Exception:
                        selected_objs[1].solid_geometry = unary_union(selected_objs[1].solid_geometry)

                first_pos, last_pos = nearest_points(selected_objs[0].solid_geometry, selected_objs[1].solid_geometry)

        elif self.app.call_source == 'geo_editor':
            selected_objs = self.app.geo_editor.selected
            if len(selected_objs) != 2:
                self.app.inform.emit('[WARNING_NOTCL] %s %s' %
                                     (_("Select two objects and no more. Currently the selection has objects: "),
                                      str(len(selected_objs))))
                return
            else:
                first_pos, last_pos = nearest_points(selected_objs[0].geo, selected_objs[1].geo)
        elif self.app.call_source == 'exc_editor':
            selected_objs = self.app.exc_editor.selected
            if len(selected_objs) != 2:
                self.app.inform.emit('[WARNING_NOTCL] %s %s' %
                                     (_("Select two objects and no more. Currently the selection has objects: "),
                                      str(len(selected_objs))))
                return
            else:
                # the objects are really MultiLinesStrings made out of 2 lines in cross shape
                xmin, ymin, xmax, ymax = selected_objs[0].geo.bounds
                first_geo_radius = (xmax - xmin) / 2
                first_geo_center = Point(xmin + first_geo_radius, ymin + first_geo_radius)
                first_geo = first_geo_center.buffer(first_geo_radius)

                # the objects are really MultiLinesStrings made out of 2 lines in cross shape
                xmin, ymin, xmax, ymax = selected_objs[1].geo.bounds
                last_geo_radius = (xmax - xmin) / 2
                last_geo_center = Point(xmin + last_geo_radius, ymin + last_geo_radius)
                last_geo = last_geo_center.buffer(last_geo_radius)

                first_pos, last_pos = nearest_points(first_geo, last_geo)
        elif self.app.call_source == 'grb_editor':
            selected_objs = self.app.grb_editor.selected
            if len(selected_objs) != 2:
                self.app.inform.emit('[WARNING_NOTCL] %s %s' %
                                     (_("Select two objects and no more. Currently the selection has objects: "),
                                      str(len(selected_objs))))
                return
            else:
                first_pos, last_pos = nearest_points(selected_objs[0].geo['solid'], selected_objs[1].geo['solid'])
        else:
            first_pos, last_pos = 0, 0

        self.ui.start_entry.set_value("(%.*f, %.*f)" % (self.decimals, first_pos.x, self.decimals, first_pos.y))
        self.ui.stop_entry.set_value("(%.*f, %.*f)" % (self.decimals, last_pos.x, self.decimals, last_pos.y))

        dx = first_pos.x - last_pos.x
        dy = first_pos.y - last_pos.y

        self.ui.distance_x_entry.set_value('%.*f' % (self.decimals, abs(dx)))
        self.ui.distance_y_entry.set_value('%.*f' % (self.decimals, abs(dy)))

        try:
            angle = math.degrees(math.atan(dy / dx))
            self.ui.angle_entry.set_value('%.*f' % (self.decimals, angle))
        except Exception:
            pass

        d = math.sqrt(dx ** 2 + dy ** 2)
        self.ui.total_distance_entry.set_value('%.*f' % (self.decimals, abs(d)))

        self.h_point = (min(first_pos.x, last_pos.x) + (abs(dx) / 2), min(first_pos.y, last_pos.y) + (abs(dy) / 2))
        if d != 0:
            self.ui.half_point_entry.set_value(
                "(%.*f, %.*f)" % (self.decimals, self.h_point[0], self.decimals, self.h_point[1])
            )
        else:
            self.ui.half_point_entry.set_value(
                "(%.*f, %.*f)" % (self.decimals, 0.0, self.decimals, 0.0)
            )

        if d != 0:
            self.app.inform.emit("{tx1}: {tx2} D(x) = {d_x} | D(y) = {d_y} | {tx3} = {d_z}".format(
                tx1=_("MEASURING"),
                tx2=_("Result"),
                tx3=_("Distance"),
                d_x='%*f' % (self.decimals, abs(dx)),
                d_y='%*f' % (self.decimals, abs(dy)),
                d_z='%*f' % (self.decimals, abs(d)))
            )
        else:
            self.app.inform.emit('[WARNING_NOTCL] %s: %s' %
                                 (_("Objects intersects or touch at"),
                                  "(%.*f, %.*f)" % (self.decimals, self.h_point[0], self.decimals, self.h_point[1])))

    def on_jump_to_half_point(self):
        self.app.on_jump_to(custom_location=self.h_point)
        self.app.inform.emit('[success] %s: %s' %
                             (_("Jumped to the half point between the two selected objects"),
                              "(%.*f, %.*f)" % (self.decimals, self.h_point[0], self.decimals, self.h_point[1])))

    # def set_meas_units(self, units):
    #     self.meas.units_label.setText("[" + self.app.options["units"].lower() + "]")


class DistMinUI:

    toolName = _("Minimum Distance Tool")

    def __init__(self, layout, app):
        self.app = app
        self.decimals = self.app.decimals
        self.layout = layout
        self.units = self.app.defaults['units'].lower()

        # ## Title
        title_label = FCLabel("<font size=4><b>%s</b></font><br>" % self.toolName)
        self.layout.addWidget(title_label)

        # ## Grid Layout
        grid0 = QtWidgets.QGridLayout()
        grid0.setColumnStretch(0, 0)
        grid0.setColumnStretch(1, 1)
        self.layout.addLayout(grid0)
        
        # Units
        self.units_label = FCLabel('%s:' % _("Units"))
        self.units_label.setToolTip(_("Those are the units in which the distance is measured."))
        self.units_value = FCLabel("%s" % str({'mm': _("METRIC (mm)"), 'in': _("INCH (in)")}[self.units]))
        self.units_value.setDisabled(True)

        grid0.addWidget(self.units_label, 0, 0)
        grid0.addWidget(self.units_value, 0, 1)
        
        # Start
        self.start_label = FCLabel("%s:" % _('First object point'))
        self.start_label.setToolTip(_("This is first object point coordinates.\n"
                                      "This is the start point for measuring distance."))

        self.start_entry = FCEntry()
        self.start_entry.setReadOnly(True)
        self.start_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.start_entry.setToolTip(_("This is first object point coordinates.\n"
                                      "This is the start point for measuring distance."))

        grid0.addWidget(self.start_label, 2, 0)
        grid0.addWidget(self.start_entry, 2, 1)
        
        # Stop
        self.stop_label = FCLabel("%s:" % _('Second object point'))
        self.stop_label.setToolTip(_("This is second object point coordinates.\n"
                                     "This is the end point for measuring distance."))
        
        self.stop_entry = FCEntry()
        self.stop_entry.setReadOnly(True)
        self.stop_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.stop_entry.setToolTip(_("This is second object point coordinates.\n"
                                     "This is the end point for measuring distance."))

        grid0.addWidget(self.stop_label, 4, 0)
        grid0.addWidget(self.stop_entry, 4, 1)
        
        # DX
        self.distance_x_label = FCLabel('%s:' % _("Dx"))
        self.distance_x_label.setToolTip(_("This is the distance measured over the X axis."))

        self.distance_x_entry = FCEntry()
        self.distance_x_entry.setReadOnly(True)
        self.distance_x_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.distance_x_entry.setToolTip(_("This is the distance measured over the X axis."))

        grid0.addWidget(self.distance_x_label, 6, 0)
        grid0.addWidget(self.distance_x_entry, 6, 1)
        
        # DY
        self.distance_y_label = FCLabel('%s:' % _("Dy"))
        self.distance_y_label.setToolTip(_("This is the distance measured over the Y axis."))

        self.distance_y_entry = FCEntry()
        self.distance_y_entry.setReadOnly(True)
        self.distance_y_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.distance_y_entry.setToolTip(_("This is the distance measured over the Y axis."))

        grid0.addWidget(self.distance_y_label, 8, 0)
        grid0.addWidget(self.distance_y_entry, 8, 1)
        
        # Angle
        self.angle_label = FCLabel('%s:' % _("Angle"))
        self.angle_label.setToolTip(_("This is orientation angle of the measuring line."))

        self.angle_entry = FCEntry()
        self.angle_entry.setReadOnly(True)
        self.angle_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.angle_entry.setToolTip(_("This is orientation angle of the measuring line."))

        grid0.addWidget(self.angle_label, 10, 0)
        grid0.addWidget(self.angle_entry, 10, 1)
        
        # Total Distance
        self.total_distance_label = FCLabel("<b>%s:</b>" % _('DISTANCE'))
        self.total_distance_label.setToolTip(_("This is the point to point Euclidean distance."))

        self.total_distance_entry = FCEntry()
        self.total_distance_entry.setReadOnly(True)
        self.total_distance_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.total_distance_entry.setToolTip(_("This is the point to point Euclidean distance."))

        grid0.addWidget(self.total_distance_label, 12, 0)
        grid0.addWidget(self.total_distance_entry, 12, 1)
        
        # Half Point
        self.half_point_label = FCLabel("<b>%s:</b>" % _('Half Point'))
        self.half_point_label.setToolTip(_("This is the middle point of the point to point Euclidean distance."))

        self.half_point_entry = FCEntry()
        self.half_point_entry.setReadOnly(True)
        self.half_point_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.half_point_entry.setToolTip(_("This is the middle point of the point to point Euclidean distance."))

        grid0.addWidget(self.half_point_label, 14, 0)
        grid0.addWidget(self.half_point_entry, 14, 1)
        
        self.measure_btn = FCButton(_("Measure"))
        grid0.addWidget(self.measure_btn, 16, 0, 1, 2)

        self.jump_hp_btn = FCButton(_("Jump to Half Point"))
        self.jump_hp_btn.setDisabled(True)
        
        grid0.addWidget(self.jump_hp_btn, 18, 0, 1, 2)

        self.layout.addStretch(1)
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
