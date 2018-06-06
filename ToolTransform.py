from PyQt4 import QtGui, QtCore
from PyQt4 import Qt
from GUIElements import FCEntry, FCButton
from FlatCAMTool import FlatCAMTool
from camlib import *


class ToolTransform(FlatCAMTool):

    toolName = "Object Transformation"
    rotateName = "Rotate Transformation"
    skewName = "Skew/Shear Transformation"
    flipName = "Flip Transformation"

    def __init__(self, app):
        FlatCAMTool.__init__(self, app)

        self.transform_lay = QtGui.QVBoxLayout()
        self.layout.addLayout(self.transform_lay)
        ## Title
        title_label = QtGui.QLabel("<font size=4><b>%s</b></font><br>" % self.toolName)
        self.transform_lay.addWidget(title_label)

        self.empty_label = QtGui.QLabel("")
        self.empty_label.setFixedWidth(80)
        self.empty_label1 = QtGui.QLabel("")
        self.empty_label1.setFixedWidth(80)
        self.empty_label2 = QtGui.QLabel("")
        self.empty_label2.setFixedWidth(80)
        self.transform_lay.addWidget(self.empty_label)

        ## Rotate Title
        rotate_title_label = QtGui.QLabel("<font size=3><b>%s</b></font>" % self.rotateName)
        self.transform_lay.addWidget(rotate_title_label)

        ## Form Layout
        form_layout = QtGui.QFormLayout()
        self.transform_lay.addLayout(form_layout)

        self.rotate_entry = FCEntry()
        self.rotate_entry.setFixedWidth(70)
        self.rotate_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.rotate_label = QtGui.QLabel("Angle Rotation:")
        self.rotate_label.setToolTip(
            "Angle for Rotation action, in degrees.\n"
            "Float number between -360 and 359.\n"
            "Positive numbers for CW motion.\n"
            "Negative numbers for CCW motion."
        )
        self.rotate_label.setFixedWidth(80)

        self.rotate_button = FCButton()
        self.rotate_button.set_value("Rotate")
        self.rotate_button.setToolTip(
            "Rotate the selected object(s).\n"
            "The point of reference is the middle of\n"
            "the bounding box for all selected objects.\n"
        )
        self.rotate_button.setFixedWidth(70)

        form_layout.addRow(self.rotate_label, self.rotate_entry)
        form_layout.addRow(self.empty_label, self.rotate_button)

        self.transform_lay.addWidget(self.empty_label1)

        ## Skew Title
        skew_title_label = QtGui.QLabel("<font size=3><b>%s</b></font>" % self.skewName)
        self.transform_lay.addWidget(skew_title_label)

        ## Form Layout
        form1_layout = QtGui.QFormLayout()
        self.transform_lay.addLayout(form1_layout)

        self.skewx_entry = FCEntry()
        self.skewx_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.skewx_entry.setFixedWidth(70)
        self.skewx_label = QtGui.QLabel("Angle SkewX:")
        self.skewx_label.setToolTip(
            "Angle for Skew action, in degrees.\n"
            "Float number between -360 and 359."
        )
        self.skewx_label.setFixedWidth(80)

        self.skewx_button = FCButton()
        self.skewx_button.set_value("Skew_X")
        self.skewx_button.setToolTip(
            "Skew/shear the selected object(s).\n"
            "The point of reference is the middle of\n"
            "the bounding box for all selected objects.\n")
        self.skewx_button.setFixedWidth(70)

        self.skewy_entry = FCEntry()
        self.skewy_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.skewy_entry.setFixedWidth(70)
        self.skewy_label = QtGui.QLabel("Angle SkewY:")
        self.skewy_label.setToolTip(
            "Angle for Skew action, in degrees.\n"
            "Float number between -360 and 359."
        )
        self.skewy_label.setFixedWidth(80)

        self.skewy_button = FCButton()
        self.skewy_button.set_value("Skew_Y")
        self.skewy_button.setToolTip(
            "Skew/shear the selected object(s).\n"
            "The point of reference is the middle of\n"
            "the bounding box for all selected objects.\n")
        self.skewy_button.setFixedWidth(70)

        form1_layout.addRow(self.skewx_label, self.skewx_entry)
        form1_layout.addRow(self.empty_label, self.skewx_button)
        form1_layout.addRow(self.skewy_label, self.skewy_entry)
        form1_layout.addRow(self.empty_label, self.skewy_button)

        self.transform_lay.addWidget(self.empty_label2)

        ## Flip Title
        flip_title_label = QtGui.QLabel("<font size=3><b>%s</b></font>" % self.flipName)
        self.transform_lay.addWidget(flip_title_label)

        ## Form Layout
        form2_layout = QtGui.QFormLayout()
        self.transform_lay.addLayout(form2_layout)

        self.flipx_button = FCButton()
        self.flipx_button.set_value("Flip_X")
        self.flipx_button.setToolTip(
            "Flip the selected object(s) over the X axis.\n"
            "Does not create a new object.\n "
        )
        self.flipx_button.setFixedWidth(70)

        self.flipy_button = FCButton()
        self.flipy_button.set_value("Flip_Y")
        self.flipy_button.setToolTip(
            "Flip the selected object(s) over the X axis.\n"
            "Does not create a new object.\n "
        )
        self.flipy_button.setFixedWidth(70)

        form2_layout.setSpacing(16)
        form2_layout.addRow(self.flipx_button, self.flipy_button)

        self.transform_lay.addStretch()

        ## Signals
        self.rotate_button.clicked.connect(self.on_rotate)
        self.skewx_button.clicked.connect(self.on_skewx)
        self.skewy_button.clicked.connect(self.on_skewy)
        self.flipx_button.clicked.connect(self.on_flipx)
        self.flipy_button.clicked.connect(self.on_flipy)

        self.rotate_entry.returnPressed.connect(self.on_rotate)
        self.skewx_entry.returnPressed.connect(self.on_skewx)
        self.skewy_entry.returnPressed.connect(self.on_skewy)

        ## Initialize form
        self.rotate_entry.set_value('0')
        self.skewx_entry.set_value('0')
        self.skewy_entry.set_value('0')

    def on_rotate(self):
        value = float(self.rotate_entry.get_value())
        self.on_rotate_action(value)
        return

    def on_flipx(self):
        self.on_flip("Y")
        return

    def on_flipy(self):
        self.on_flip("X")
        return

    def on_skewx(self):
        value = float(self.skewx_entry.get_value())
        self.on_skew("X", value)
        return

    def on_skewy(self):
        value = float(self.skewy_entry.get_value())
        self.on_skew("Y", value)
        return

    def on_rotate_action(self, num):
        obj_list = self.app.collection.get_selected()
        xminlist = []
        yminlist = []
        xmaxlist = []
        ymaxlist = []

        if not obj_list:
            self.app.inform.emit("WARNING: No object selected.")
            msg = "Please Select an object to rotate!"
            warningbox = QtGui.QMessageBox()
            warningbox.setText(msg)
            warningbox.setWindowTitle("Warning ...")
            warningbox.setWindowIcon(QtGui.QIcon('share/warning.png'))
            warningbox.setStandardButtons(QtGui.QMessageBox.Ok)
            warningbox.setDefaultButton(QtGui.QMessageBox.Ok)
            warningbox.exec_()
        else:
            try:
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

                for sel_obj in obj_list:
                    px = 0.5 * (xminimal + xmaximal)
                    py = 0.5 * (yminimal + ymaximal)

                    sel_obj.rotate(-num, point=(px, py))
                    sel_obj.plot()
                self.app.inform.emit('Object was rotated ...')
            except Exception as e:
                self.app.inform.emit("[ERROR] Due of %s, rotation movement was not executed." % str(e))
                raise

    def on_flip(self, axis):
        obj_list = self.app.collection.get_selected()
        xminlist = []
        yminlist = []
        xmaxlist = []
        ymaxlist = []

        if not obj_list:
            self.app.inform.emit("WARNING: No object selected.")
            msg = "Please Select an object to flip!"
            warningbox = QtGui.QMessageBox()
            warningbox.setText(msg)
            warningbox.setWindowTitle("Warning ...")
            warningbox.setWindowIcon(QtGui.QIcon('share/warning.png'))
            warningbox.setStandardButtons(QtGui.QMessageBox.Ok)
            warningbox.setDefaultButton(QtGui.QMessageBox.Ok)
            warningbox.exec_()
            return
        else:
            try:
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

                px = 0.5 * (xminimal + xmaximal)
                py = 0.5 * (yminimal + ymaximal)

                # execute mirroring
                for obj in obj_list:
                    if axis is 'X':
                        obj.mirror('X', [px, py])
                        obj.plot()
                        self.app.inform.emit('Flipped on the Y axis ...')
                    elif axis is 'Y':
                        obj.mirror('Y', [px, py])
                        obj.plot()
                        self.app.inform.emit('Flipped on the X axis ...')

            except Exception as e:
                self.app.inform.emit("[ERROR] Due of %s, Flip action was not executed.")
                raise

    def on_skew(self, axis, num):
        obj_list = self.app.collection.get_selected()
        xminlist = []
        yminlist = []

        if not obj_list:
            self.app.inform.emit("WARNING: No object selected.")
            msg = "Please Select an object to skew/shear!"
            warningbox = QtGui.QMessageBox()
            warningbox.setText(msg)
            warningbox.setWindowTitle("Warning ...")
            warningbox.setWindowIcon(QtGui.QIcon('share/warning.png'))
            warningbox.setStandardButtons(QtGui.QMessageBox.Ok)
            warningbox.setDefaultButton(QtGui.QMessageBox.Ok)
            warningbox.exec_()
        else:
            try:
                # first get a bounding box to fit all
                for obj in obj_list:
                    xmin, ymin, xmax, ymax = obj.bounds()
                    xminlist.append(xmin)
                    yminlist.append(ymin)

                # get the minimum x,y and maximum x,y for all objects selected
                xminimal = min(xminlist)
                yminimal = min(yminlist)

                for obj in obj_list:
                    if axis is 'X':
                        obj.skew(num, 0, point=(xminimal, yminimal))
                    elif axis is 'Y':
                        obj.skew(0, num, point=(xminimal, yminimal))
                    obj.plot()
                self.app.inform.emit('Object was skewed on %s axis ...' % str(axis))
            except Exception as e:
                self.app.inform.emit("[ERROR] Due of %s, Skew action was not executed." % str(e))
                raise

# end of file