from PyQt5.QtGui import QPalette
from PyQt5 import QtCore, QtWidgets

import vispy.scene as scene
from vispy.scene.visuals import Rectangle, Text
from vispy.color import Color

import sys


class VisPyCanvas(scene.SceneCanvas):

    def __init__(self, config=None):
        super().__init__(config=config, keys=None)

        self.unfreeze()
        
        # Colors used by the Scene
        theme_color = Color('#FFFFFF')
        tick_color = Color('#000000')
        back_color = str(QPalette().color(QPalette.Window).name())
        
        # Central Widget Colors
        self.central_widget.bgcolor = back_color
        self.central_widget.border_color = back_color

        self.grid_widget = self.central_widget.add_grid(margin=10)
        self.grid_widget.spacing = 0
        
        # TOP Padding
        top_padding = self.grid_widget.add_widget(row=0, col=0, col_span=2)
        top_padding.height_max = 0

        # RIGHT Padding
        right_padding = self.grid_widget.add_widget(row=0, col=2, row_span=2)
        right_padding.width_max = 0

        # X Axis
        self.xaxis = scene.AxisWidget(
            orientation='bottom', axis_color=tick_color, text_color=tick_color,
            font_size=8, axis_width=1,
            anchors=['center', 'bottom']
        )
        self.xaxis.height_max = 30
        self.grid_widget.add_widget(self.xaxis, row=2, col=1)

        # Y Axis
        self.yaxis = scene.AxisWidget(
            orientation='left', axis_color=tick_color, text_color=tick_color, 
            font_size=8, axis_width=1
        )
        self.yaxis.width_max = 55
        self.grid_widget.add_widget(self.yaxis, row=1, col=0)

        # View & Camera
        self.view = self.grid_widget.add_view(row=1, col=1, border_color=tick_color,
                                              bgcolor=theme_color)
        self.view.camera = scene.PanZoomCamera(aspect=1, rect=(-25, -25, 150, 150))

        self.xaxis.link_view(self.view)
        self.yaxis.link_view(self.view)

        self.grid = scene.GridLines(parent=self.view.scene, color='dimgray')
        self.grid.set_gl_state(depth_test=False)

        self.rect = Rectangle(center=(65,30), color=Color('#0000FF10'), border_color=Color('#0000FF10'),
                              width=120, height=50, radius=[5, 5, 5, 5], parent=self.view)
        self.rect.set_gl_state(depth_test=False)

        self.text = Text('', parent=self.view, color='black', pos=(5, 30), method='gpu', anchor_x='left')
        self.text.font_size = 8
        self.text.text = 'Coordinates:\nX: %s\nY: %s' % ('0.0000', '0.0000')

        self.freeze()

        # self.measure_fps()


class PlotCanvas(QtCore.QObject):

    def __init__(self, container, my_app):
        """
        The constructor configures the VisPy figure that
        will contain all plots, creates the base axes and connects
        events to the plotting area.

        :param container: The parent container in which to draw plots.
        :rtype: PlotCanvas
        """

        super().__init__()
        
        # VisPyCanvas instance
        self.vispy_canvas = VisPyCanvas()
        
        self.vispy_canvas.unfreeze()
        
        self.my_app = my_app
        
        # Parent container
        self.container = container
        
        # <VisPyCanvas>
        self.vispy_canvas.create_native()
        self.vispy_canvas.native.setParent(self.my_app.ui)

        # <QtCore.QObject>
        self.container.addWidget(self.vispy_canvas.native)
        
        # add two Infinite Lines to act as markers for the X,Y axis
        self.v_line = scene.visuals.InfiniteLine(
            pos=0, color=(0.0, 0.0, 1.0, 0.3), vertical=True, 
            parent=self.vispy_canvas.view.scene)

        self.h_line = scene.visuals.InfiniteLine(
            pos=0, color=(0.00, 0.0, 1.0, 0.3), vertical=False, 
            parent=self.vispy_canvas.view.scene)
        
        self.vispy_canvas.freeze()
    
    def event_connect(self, event, callback):
        getattr(self.vispy_canvas.events, event).connect(callback)
        
    def event_disconnect(self, event, callback):
        getattr(self.vispy_canvas.events, event).disconnect(callback)
    
    def translate_coords(self, pos):
        """
        Translate pixels to canvas units.
        """
        tr = self.vispy_canvas.grid.get_transform('canvas', 'visual')
        return tr.map(pos)
        

class MyGui(QtWidgets.QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("VisPy Test")

        # add Menubar
        self.menu = self.menuBar()
        self.menufile = self.menu.addMenu("File")
        self.menuedit = self.menu.addMenu("Edit")
        self.menufhelp = self.menu.addMenu("Help")

        # add a Toolbar
        self.file_toolbar = QtWidgets.QToolBar("File Toolbar")
        self.addToolBar(self.file_toolbar)
        self.button = self.file_toolbar.addAction("Open")

        # add Central Widget
        self.c_widget = QtWidgets.QWidget()
        self.central_layout = QtWidgets.QVBoxLayout()
        self.c_widget.setLayout(self.central_layout)
        self.setCentralWidget(self.c_widget)

        # add InfoBar
        # self.infobar = self.statusBar()
        # self.position_label = QtWidgets.QLabel("Position:  X: 0.0000\tY: 0.0000")
        # self.infobar.addWidget(self.position_label)


class MyApp(QtCore.QObject):

    def __init__(self):
        super().__init__()
        
        self.ui = MyGui()
        self.plot = PlotCanvas(container=self.ui.central_layout, my_app=self)
        
        self.ui.show()
        
        self.plot.event_connect(event="mouse_move", callback=self.on_mouse_move)
    
    def on_mouse_move(self, event):
        cursor_pos = event.pos
        
        pos_canvas = self.plot.translate_coords(cursor_pos)
        
        # we don't need all the info in the tuple returned by the translate_coords()
        # only first 2 elements
        pos_canvas = [pos_canvas[0], pos_canvas[1]]
        self.ui.position_label.setText("Position:  X: %.4f\tY: %.4f" % (pos_canvas[0], pos_canvas[1]))
        # pos_text = 'Coordinates:   \nX: {:<7.4f}\nY: {:<7.4f}'.format(pos_canvas[0], pos_canvas[1])
        pos_text = 'Coordinates:   \nX: {:<.4f}\nY: {:<.4f}'.format(pos_canvas[0], pos_canvas[1])
        self.plot.vispy_canvas.text.text = pos_text


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)

    m_app = MyApp()
    sys.exit(app.exec_())
