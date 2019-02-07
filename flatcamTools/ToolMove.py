from FlatCAMTool import FlatCAMTool
from FlatCAMObj import *
from VisPyVisuals import *

from io import StringIO
from copy import copy


class ToolMove(FlatCAMTool):

    toolName = "Move"

    def __init__(self, app):
        FlatCAMTool.__init__(self, app)

        self.layout.setContentsMargins(0, 0, 3, 0)
        self.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Maximum)

        self.clicked_move = 0

        self.point1 = None
        self.point2 = None

        # the default state is disabled for the Move command
        self.setVisible(False)

        self.sel_rect = None
        self.old_coords = []

        # VisPy visuals
        self.sel_shapes = ShapeCollection(parent=self.app.plotcanvas.vispy_canvas.view.scene, layers=1)

    def install(self, icon=None, separator=None, **kwargs):
        FlatCAMTool.install(self, icon, separator, shortcut='M', **kwargs)

    def run(self):
        self.app.report_usage("ToolMove()")

        if self.app.tool_tab_locked is True:
            return
        self.toggle()

    def toggle(self):
        if self.isVisible():
            self.setVisible(False)

            self.app.plotcanvas.vis_disconnect('mouse_move', self.on_move)
            self.app.plotcanvas.vis_disconnect('mouse_press', self.on_left_click)
            self.app.plotcanvas.vis_disconnect('key_release', self.on_key_press)
            self.app.plotcanvas.vis_connect('key_press', self.app.ui.keyPressEvent)

            self.clicked_move = 0

            # signal that there is no command active
            self.app.command_active = None

            # delete the selection box
            self.delete_shape()
            return
        else:
            self.setVisible(True)
            # signal that there is a command active and it is 'Move'
            self.app.command_active = "Move"

            if self.app.collection.get_selected():
                self.app.inform.emit("MOVE: Click on the Start point ...")
                # draw the selection box
                self.draw_sel_bbox()
            else:
                self.setVisible(False)
                # signal that there is no command active
                self.app.command_active = None
                self.app.inform.emit("[WARNING_NOTCL]MOVE action cancelled. No object(s) to move.")

    def on_left_click(self, event):
        # mouse click will be accepted only if the left button is clicked
        # this is necessary because right mouse click and middle mouse click
        # are used for panning on the canvas

        if event.button == 1:
            if self.clicked_move == 0:
                pos_canvas = self.app.plotcanvas.vispy_canvas.translate_coords(event.pos)

                # if GRID is active we need to get the snapped positions
                if self.app.grid_status() == True:
                    pos = self.app.geo_editor.snap(pos_canvas[0], pos_canvas[1])
                else:
                    pos = pos_canvas

                if self.point1 is None:
                    self.point1 = pos
                else:
                    self.point2 = copy(self.point1)
                    self.point1 = pos
                self.app.inform.emit("MOVE: Click on the Destination point ...")

            if self.clicked_move == 1:
                try:
                    pos_canvas = self.app.plotcanvas.vispy_canvas.translate_coords(event.pos)

                    # delete the selection bounding box
                    self.delete_shape()

                    # if GRID is active we need to get the snapped positions
                    if self.app.grid_status() == True:
                        pos = self.app.geo_editor.snap(pos_canvas[0], pos_canvas[1])
                    else:
                        pos = pos_canvas

                    dx = pos[0] - self.point1[0]
                    dy = pos[1] - self.point1[1]

                    proc = self.app.proc_container.new("Moving ...")

                    def job_move(app_obj):
                        obj_list = self.app.collection.get_selected()

                        try:
                            if not obj_list:
                                self.app.inform.emit("[WARNING_NOTCL] No object(s) selected.")
                                return "fail"
                            else:
                                for sel_obj in obj_list:

                                    sel_obj.offset((dx, dy))
                                    sel_obj.plot()
                                    # Update the object bounding box options
                                    a,b,c,d = sel_obj.bounds()
                                    sel_obj.options['xmin'] = a
                                    sel_obj.options['ymin'] = b
                                    sel_obj.options['xmax'] = c
                                    sel_obj.options['ymax'] = d
                                    # self.app.collection.set_active(sel_obj.options['name'])
                        except Exception as e:
                            proc.done()
                            self.app.inform.emit('[ERROR_NOTCL] '
                                                 'ToolMove.on_left_click() --> %s' % str(e))
                            return "fail"
                        proc.done()
                        # delete the selection bounding box
                        self.delete_shape()
                        self.app.inform.emit('[success]%s object was moved ...' %
                                             str(sel_obj.kind).capitalize())

                    self.app.worker_task.emit({'fcn': job_move, 'params': [self]})

                    self.clicked_move = 0
                    self.toggle()
                    return

                except TypeError:
                    self.app.inform.emit('[ERROR_NOTCL] '
                                         'ToolMove.on_left_click() --> Error when mouse left click.')
                    return

            self.clicked_move = 1

    def on_move(self, event):
        pos_canvas = self.app.plotcanvas.vispy_canvas.translate_coords(event.pos)

        # if GRID is active we need to get the snapped positions
        if self.app.grid_status() == True:
            pos = self.app.geo_editor.snap(pos_canvas[0], pos_canvas[1])
        else:
            pos = pos_canvas

        if self.point1 is None:
            dx = pos[0]
            dy = pos[1]
        else:
            dx = pos[0] - self.point1[0]
            dy = pos[1] - self.point1[1]

        if self.clicked_move == 1:
            self.update_sel_bbox((dx, dy))

    def on_key_press(self, event):
        if event.key == 'escape':
            # abort the move action
            self.app.inform.emit("[WARNING_NOTCL]Move action cancelled.")
            self.toggle()
        return

    def draw_sel_bbox(self):
        xminlist = []
        yminlist = []
        xmaxlist = []
        ymaxlist = []

        obj_list = self.app.collection.get_selected()
        if not obj_list:
            self.app.inform.emit("[WARNING_NOTCL]Object(s) not selected")
            self.toggle()
        else:
            # if we have an object selected then we can safely activate the mouse events
            self.app.plotcanvas.vis_connect('mouse_move', self.on_move)
            self.app.plotcanvas.vis_connect('mouse_press', self.on_left_click)
            self.app.plotcanvas.vis_connect('key_release', self.on_key_press)
            # first get a bounding box to fit all
            for obj in obj_list:
                xmin, ymin, xmax, ymax = obj.bounds()
                xminlist.append(xmin)
                yminlist.append(ymin)
                xmaxlist.append(xmax)
                ymaxlist.append(ymax)

            # get the minimum x,y and maximum x,y for all objects selected
            xminimal = min(xminlist)
            yminimal = min(yminlist)
            xmaximal = max(xmaxlist)
            ymaximal = max(ymaxlist)

            p1 = (xminimal, yminimal)
            p2 = (xmaximal, yminimal)
            p3 = (xmaximal, ymaximal)
            p4 = (xminimal, ymaximal)
            self.old_coords = [p1, p2, p3, p4]
            self.draw_shape(self.old_coords)

    def update_sel_bbox(self, pos):
        self.delete_shape()

        pt1 = (self.old_coords[0][0] + pos[0], self.old_coords[0][1] + pos[1])
        pt2 = (self.old_coords[1][0] + pos[0], self.old_coords[1][1] + pos[1])
        pt3 = (self.old_coords[2][0] + pos[0], self.old_coords[2][1] + pos[1])
        pt4 = (self.old_coords[3][0] + pos[0], self.old_coords[3][1] + pos[1])

        self.draw_shape([pt1, pt2, pt3, pt4])

    def delete_shape(self):
        self.sel_shapes.clear()
        self.sel_shapes.redraw()

    def draw_shape(self, coords):
        self.sel_rect = Polygon(coords)

        blue_t = Color('blue')
        blue_t.alpha = 0.2
        self.sel_shapes.add(self.sel_rect, color='blue', face_color=blue_t, update=True, layer=0, tolerance=None)

# end of file
