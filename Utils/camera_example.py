# importing required libraries
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtMultimedia import *
from PyQt6.QtMultimediaWidgets import *
from PyQt6.QtCore import Qt
import os
import sys
import time

stylesheet = """
QWidget {
    background-color: rgba(32.000, 33.000, 36.000, 1.000);
    color: rgba(170.000, 170.000, 170.000, 1.000);
    selection-background-color: rgba(138.000, 180.000, 247.000, 1.000);
    selection-color: rgba(32.000, 33.000, 36.000, 1.000);
}
QWidget:disabled {
    color: rgba(105.000, 113.000, 119.000, 1.000);
    selection-background-color: rgba(83.000, 87.000, 91.000, 1.000);
    selection-color: rgba(105.000, 113.000, 119.000, 1.000);
}
QToolTip {
    background-color: rgba(41.000, 42.000, 45.000, 1.000);
    color: rgba(228.000, 231.000, 235.000, 1.000);
    border: 1px solid rgba(63.000, 64.000, 66.000, 1.000);
}
QSizeGrip {
    width: 0;
    height: 0;
    image: none;
}
QStatusBar {
    background-color: rgba(42.000, 43.000, 46.000, 1.000);
}
QStatusBar::item {
    border: none;
}
QStatusBar QWidget {
    background-color: transparent;
    padding: 0px;
    border-radius: 0px;
    margin: 0px;
}
QStatusBar QWidget:pressed {
    background-color: rgba(79.000, 80.000, 84.000, 1.000);
}
QStatusBar QWidget:disabled {
    background-color: rgba(32.000, 33.000, 36.000, 1.000);
}
QStatusBar QWidget:checked {
    background-color: rgba(79.000, 80.000, 84.000, 1.000);
}
QToolBar {
    background-color: rgba(41.000, 42.000, 45.000, 1.000);
    padding: 1x;
    font-weight: bold;
    spacing: 1px;
    margin: 1px;
}
QToolBar::separator {
    background-color: rgba(63.000, 64.000, 66.000, 1.000);
}
QToolBar::separator:horizontal {
    width: 2px;
    margin: 0 6px;
}
QToolBar::separator:vertical {
    height: 2px;
    margin: 6px 0;
}
QPushButton {
    border: 1px solid rgba(63.000, 64.000, 66.000, 1.000);
    padding: 4px 8px;
    border-radius: 4px;
    color: rgba(138.000, 180.000, 247.000, 1.000);
}
QPushButton:hover {
    background-color: rgba(30.000, 43.000, 60.000, 1.000);
}
QPushButton:pressed {
    background-color: rgba(46.000, 70.000, 94.000, 1.000);
}
QPushButton:checked {
    border-color: rgba(138.000, 180.000, 247.000, 1.000);
}
QPushButton:disabled {
    border-color: rgba(63.000, 64.000, 66.000, 1.000);
}
QPushButton[flat=true]:!checked {
    border-color: transparent;
}
QDialogButtonBox QPushButton {
    min-width: 65px;
}
QComboBox {
    border: 1px solid rgba(63.000, 64.000, 66.000, 1.000);
    border-radius: 4px;
    min-height: 1.5em;
    padding: 0 4px;
    background-color: rgba(63.000, 64.000, 66.000, 1.000);
}
QComboBox:focus,
QComboBox:open {
    border: 1px solid rgba(138.000, 180.000, 247.000, 1.000);
}
QComboBox::drop-down {
    subcontrol-position: center right;
    border: none;
    padding-right: 4px;
}
QComboBox::item:selected {
    border: none;
    background-color: rgba(0.000, 72.000, 117.000, 1.000);
    color: rgba(228.000, 231.000, 235.000, 1.000);
}
QComboBox QAbstractItemView {
    margin: 0;
    border: 1px solid rgba(63.000, 64.000, 66.000, 1.000);
    selection-background-color: rgba(0.000, 72.000, 117.000, 1.000);
    selection-color: rgba(228.000, 231.000, 235.000, 1.000);
    padding: 2px;
}
"""


# Main window class
class MainWindow(QMainWindow):

    # constructor
    def __init__(self):
        super().__init__()

        self.captured_image = None
        self.save_seq = None
        self.capture = None
        self.camera = None
        self.current_camera_name = None
        self.mirror_h = True

        # setting geometry
        self.setGeometry(200, 200, 800, 600)
        self.setStyleSheet("background : darkgrey;")

        # getting available cameras
        self.available_cameras = QMediaDevices.videoInputs()
        # if no camera found
        if not self.available_cameras:
            # exit the code
            sys.exit()

        self.status = QStatusBar()
        self.setStatusBar(self.status)

        # path to save
        self.save_path = ""

        toolbar = QToolBar("Camera Tool Bar")
        self.addToolBar(toolbar)

        # creating a photo action to take photo
        click_action = QAction("Get Photo", self)
        click_action.setStatusTip("This will capture picture")
        click_action.setToolTip("Capture picture")
        click_action.triggered.connect(self.capture_picture)
        toolbar.addAction(click_action)

        # similarly creating action for changing save folder
        change_folder_action = QAction("Save location", self)
        change_folder_action.setStatusTip("Change folder where picture will be saved saved.")
        change_folder_action.setToolTip("Change save location")
        change_folder_action.triggered.connect(self.change_folder)
        toolbar.addAction(change_folder_action)

        # creating a combo box for selecting camera
        camera_selector = QComboBox()
        camera_selector.setStatusTip("Choose camera to take pictures")
        camera_selector.setToolTip("Select Camera")
        camera_selector.setToolTipDuration(2500)
        camera_selector.addItems([camera.description() for camera in self.available_cameras])
        camera_selector.currentIndexChanged.connect(self.select_camera)
        toolbar.addWidget(camera_selector)

        camera_mirror = QCheckBox("Mirror")
        camera_mirror.setChecked(True)
        camera_mirror.setStatusTip("Mirror the captured image horizontally")
        camera_mirror.setToolTip("Mirror Camera")
        camera_mirror.stateChanged.connect(self.on_mirror_changed)
        toolbar.addWidget(camera_mirror)

        # setting window title
        self.setWindowTitle("PyQt6 Cam")

        main_wdg = QWidget()
        layout = QVBoxLayout(main_wdg)

        glay = QGridLayout()
        glay.setRowStretch(0, 1)
        glay.setRowStretch(1, 0)
        self.label = QLabel()
        self.label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        self.save_btn = QPushButton("Save Picture")
        self.save_btn.clicked.connect(self.on_save_picture)
        glay.addWidget(self.label, 0, 0)
        glay.addWidget(self.save_btn, 1, 0)

        self.video_wdg = QVideoWidget()

        hlay = QHBoxLayout()
        hlay.addLayout(glay)
        hlay.addWidget(self.video_wdg)

        layout.addLayout(hlay, stretch=1)

        self.setCentralWidget(main_wdg)
        self.video_wdg.show()

        # showing the main window
        self.show()
        self.select_camera(0)

    # method to select camera
    def select_camera(self, current_camera):
        media_capture_session = QMediaCaptureSession(self)
        self.camera = QCamera(self.available_cameras[current_camera])
        self.camera.start()

        media_capture_session.setCamera(self.camera)
        media_capture_session.setVideoOutput(self.video_wdg)

        self.camera.errorOccurred.connect(lambda err, err_str: self.alert(err_str))

        self.capture = QImageCapture(self.camera)
        media_capture_session.setImageCapture(self.capture)
        self.capture.errorOccurred.connect(lambda error_msg, error, msg: self.alert(msg))

        # when image captured showing message
        self.capture.imageCaptured.connect(self.on_image_captured)

        self.current_camera_name = self.available_cameras[current_camera].description()

        # initial save sequence
        self.save_seq = 0

    def on_image_captured(self, id, image):
        width = self.label.width()
        height = self.label.height()
        self.captured_image = image
        if self.mirror_h is True:
            self.captured_image = image.mirrored(horizontal=True, vertical=False)
        pixmap = QPixmap().fromImage(self.captured_image)

        self.label.setPixmap(pixmap.scaled(width, height, Qt.AspectRatioMode.KeepAspectRatio))
        self.status.showMessage("Image captured.")

    # method to take photo
    def capture_picture(self):
        self.capture.capture()

    def on_save_picture(self):
        # time stamp
        timestamp = time.strftime("%d-%b-%Y-%H_%M_%S")

        file_path = os.path.join(
            self.save_path, "%s-%04d-%s.jpg" % (self.current_camera_name, self.save_seq, timestamp))
        try:
            self.captured_image.save(file_path, format='jpg', quality=-1)
        except Exception as err:
            print(err)

        self.status.showMessage("Image saved to: %s" % str(file_path))
        # increment the sequence
        self.save_seq += 1

    def on_mirror_changed(self, state):
        self.mirror_h = True if int(state) else False

    # change folder method
    def change_folder(self):

        # open the dialog to select path
        path = QFileDialog.getExistingDirectory(self, "Picture Location", "")

        # if path is selected
        if path:
            # update the path
            self.save_path = path

            # update the sequence
            self.save_seq = 0

    # method for alerts
    def alert(self, msg):

        # error message
        error = QErrorMessage(self)

        # setting text to the error message
        error.showMessage(msg)


# Driver code
if __name__ == "__main__":
    # create pyqt5 app
    App = QApplication(sys.argv)

    # create the instance of our Window
    window = MainWindow()
    window.setStyleSheet(stylesheet)

    # start the app
    sys.exit(App.exec())
