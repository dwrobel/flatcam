# ########################################################## ##
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# Author: Juan Pablo Caram (c)                             #
# Date: 2/5/2014                                           #
# MIT Licence                                              #
# ########################################################## ##

from PyQt5 import QtCore, QtWidgets

from shapely.geometry import Polygon, LineString

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class AppTool(QtWidgets.QWidget):

    toolName = "FlatCAM Generic Tool"

    def __init__(self, app, parent=None):
        """

        :param app:         The application this tool will run in.
        :type app:          app_Main.App
        :param parent:      Qt Parent
        :return:            AppTool
        """
        QtWidgets.QWidget.__init__(self, parent)

        self.app = app
        self.decimals = self.app.decimals

        # self.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum)

        self.layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.layout)

        self.menuAction = None

    def install(self, icon=None, separator=None, shortcut=None, **kwargs):
        before = None

        # 'pos' is the menu where the Action has to be installed
        # if no 'pos' kwarg is provided then by default our Action will be installed in the menutool
        # as it previously was
        if 'pos' in kwargs:
            pos = kwargs['pos']
        else:
            pos = self.app.ui.menutool

        # 'before' is the Action in the menu stated by 'pos' kwarg, before which we want our Action to be installed
        # if 'before' kwarg is not provided, by default our Action will be added in the last place.
        if 'before' in kwargs:
            before = (kwargs['before'])

        # create the new Action
        self.menuAction = QtWidgets.QAction(self)
        # if provided, add an icon to this Action
        if icon is not None:
            self.menuAction.setIcon(icon)

        # set the text name of the Action, which will be displayed in the menu
        if shortcut is None:
            self.menuAction.setText(self.toolName)
        else:
            self.menuAction.setText(self.toolName + '\t%s' % shortcut)

        # add a ToolTip to the new Action
        # self.menuAction.setToolTip(self.toolTip) # currently not available

        # insert the action in the position specified by 'before' and 'pos' kwargs
        pos.insertAction(before, self.menuAction)

        # if separator parameter is True add a Separator after the newly created Action
        if separator is True:
            pos.addSeparator()

        self.menuAction.triggered.connect(self.run)

    def run(self):

        if self.app.tool_tab_locked is True:
            return
        # Remove anything else in the appGUI
        self.app.ui.tool_scroll_area.takeWidget()

        # Put ourselves in the appGUI
        self.app.ui.tool_scroll_area.setWidget(self)

        # Switch notebook to tool page
        self.app.ui.notebook.setCurrentWidget(self.app.ui.tool_tab)

        # Set the tool name as the widget object name
        self.app.ui.tool_scroll_area.widget().setObjectName(self.toolName)

        self.show()

    def draw_tool_selection_shape(self, old_coords, coords, **kwargs):
        """

        :param old_coords: old coordinates
        :param coords: new coordinates
        :param kwargs:
        :return:
        """

        if 'shapes_storage' in kwargs:
            s_storage = kwargs['shapes_storage']
        else:
            s_storage = self.app.tool_shapes

        if 'color' in kwargs:
            color = kwargs['color']
        else:
            color = self.app.defaults['global_sel_line']

        if 'face_color' in kwargs:
            face_color = kwargs['face_color']
        else:
            face_color = self.app.defaults['global_sel_fill']

        if 'face_alpha' in kwargs:
            face_alpha = kwargs['face_alpha']
        else:
            face_alpha = 0.3

        x0, y0 = old_coords
        x1, y1 = coords

        pt1 = (x0, y0)
        pt2 = (x1, y0)
        pt3 = (x1, y1)
        pt4 = (x0, y1)
        sel_rect = Polygon([pt1, pt2, pt3, pt4])

        # color_t = Color(face_color)
        # color_t.alpha = face_alpha

        color_t = face_color[:-2] + str(hex(int(face_alpha * 255)))[2:]

        s_storage.add(sel_rect, color=color, face_color=color_t, update=True, layer=0, tolerance=None)
        if self.app.is_legacy is True:
            s_storage.redraw()

    def draw_selection_shape_polygon(self, points, **kwargs):
        """

        :param points: a list of points from which to create a Polygon
        :param kwargs:
        :return:
        """

        if 'shapes_storage' in kwargs:
            s_storage = kwargs['shapes_storage']
        else:
            s_storage = self.app.tool_shapes

        if 'color' in kwargs:
            color = kwargs['color']
        else:
            color = self.app.defaults['global_sel_line']

        if 'face_color' in kwargs:
            face_color = kwargs['face_color']
        else:
            face_color = self.app.defaults['global_sel_fill']

        if 'face_alpha' in kwargs:
            face_alpha = kwargs['face_alpha']
        else:
            face_alpha = 0.3

        if len(points) < 3:
            sel_rect = LineString(points)
        else:
            sel_rect = Polygon(points)

        # color_t = Color(face_color)
        # color_t.alpha = face_alpha

        color_t = face_color[:-2] + str(hex(int(face_alpha * 255)))[2:]

        s_storage.add(sel_rect, color=color, face_color=color_t, update=True, layer=0, tolerance=None)
        if self.app.is_legacy is True:
            s_storage.redraw()

    def delete_tool_selection_shape(self, **kwargs):
        """

        :param kwargs:
        :return:
        """

        if 'shapes_storage' in kwargs:
            s_storage = kwargs['shapes_storage']
        else:
            s_storage = self.app.tool_shapes

        s_storage.clear()
        s_storage.redraw()

    def draw_moving_selection_shape_poly(self, points, data, **kwargs):
        """

        :param points:
        :param data:
        :param kwargs:
        :return:
        """

        if 'shapes_storage' in kwargs:
            s_storage = kwargs['shapes_storage']
        else:
            s_storage = self.app.move_tool.sel_shapes

        if 'color' in kwargs:
            color = kwargs['color']
        else:
            color = self.app.defaults['global_sel_line']

        if 'face_color' in kwargs:
            face_color = kwargs['face_color']
        else:
            face_color = self.app.defaults['global_sel_fill']

        if 'face_alpha' in kwargs:
            face_alpha = kwargs['face_alpha']
        else:
            face_alpha = 0.3

        temp_points = [x for x in points]
        try:
            if data != temp_points[-1]:
                temp_points.append(data)
        except IndexError:
            return

        l_points = len(temp_points)
        if l_points == 2:
            geo = LineString(temp_points)
        elif l_points > 2:
            geo = Polygon(temp_points)
        else:
            return

        color_t = face_color[:-2] + str(hex(int(face_alpha * 255)))[2:]
        color_t_error = "#00000000"

        if geo.is_valid and not geo.is_empty:
            s_storage.add(geo, color=color, face_color=color_t, update=True, layer=0, tolerance=None)
        elif not geo.is_valid:
            s_storage.add(geo, color="red", face_color=color_t_error, update=True, layer=0, tolerance=None)

        if self.app.is_legacy is True:
            s_storage.redraw()

    def delete_moving_selection_shape(self, **kwargs):
        """

        :param kwargs:
        :return:
        """

        if 'shapes_storage' in kwargs:
            s_storage = kwargs['shapes_storage']
        else:
            s_storage = self.app.move_tool.sel_shapes

        s_storage.clear()
        s_storage.redraw()

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

    def sizeHint(self):
        """
        I've overloaded this just in case I will need to make changes in the future to enforce dimensions
        :return:
        """
        default_hint_size = super(AppTool, self).sizeHint()
        return QtCore.QSize(default_hint_size.width(), default_hint_size.height())
