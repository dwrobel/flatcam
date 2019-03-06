from FlatCAMTool import FlatCAMTool

from GUIElements import RadioSet, FloatEntry, FCComboBox, IntEntry
from PyQt5 import QtGui, QtCore, QtWidgets


class ToolImage(FlatCAMTool):

    toolName = "Image as Object"

    def __init__(self, app):
        FlatCAMTool.__init__(self, app)

        # Title
        title_label = QtWidgets.QLabel("%s" % 'Image to PCB')
        title_label.setStyleSheet("""
                        QLabel
                        {
                            font-size: 16px;
                            font-weight: bold;
                        }
                        """)
        self.layout.addWidget(title_label)

        # Form Layout
        ti_form_layout = QtWidgets.QFormLayout()
        self.layout.addLayout(ti_form_layout)

        # Type of object to create for the image
        self.tf_type_obj_combo = FCComboBox()
        self.tf_type_obj_combo.addItem("Gerber")
        self.tf_type_obj_combo.addItem("Geometry")

        self.tf_type_obj_combo.setItemIcon(0, QtGui.QIcon("share/flatcam_icon16.png"))
        self.tf_type_obj_combo.setItemIcon(1, QtGui.QIcon("share/geometry16.png"))

        self.tf_type_obj_combo_label = QtWidgets.QLabel("Object Type:")
        self.tf_type_obj_combo_label.setToolTip(
            "Specify the type of object to create from the image.\n"
            "It can be of type: Gerber or Geometry."

        )
        ti_form_layout.addRow(self.tf_type_obj_combo_label, self.tf_type_obj_combo)

        # DPI value of the imported image
        self.dpi_entry = IntEntry()
        self.dpi_label = QtWidgets.QLabel("DPI value:")
        self.dpi_label.setToolTip(
            "Specify a DPI value for the image."
        )
        ti_form_layout.addRow(self.dpi_label, self.dpi_entry)

        self.emty_lbl = QtWidgets.QLabel("")
        self.layout.addWidget(self.emty_lbl)

        self.detail_label = QtWidgets.QLabel("<font size=4><b>Level of detail:</b>")
        self.layout.addWidget(self.detail_label)

        ti2_form_layout = QtWidgets.QFormLayout()
        self.layout.addLayout(ti2_form_layout)

        # Type of image interpretation
        self.image_type = RadioSet([{'label': 'B/W', 'value': 'black'},
                                     {'label': 'Color', 'value': 'color'}])
        self.image_type_label = QtWidgets.QLabel("<b>Image type:</b>")
        self.image_type_label.setToolTip(
            "Choose a method for the image interpretation.\n"
            "B/W means a black & white image. Color means a colored image."
        )
        ti2_form_layout.addRow(self.image_type_label, self.image_type)

        # Mask value of the imported image when image monochrome
        self.mask_bw_entry = IntEntry()
        self.mask_bw_label = QtWidgets.QLabel("Mask value <b>B/W</b>:")
        self.mask_bw_label.setToolTip(
            "Mask for monochrome image.\n"
            "Takes values between [0 ... 255].\n"
            "Decides the level of details to include\n"
            "in the resulting geometry.\n"
            "0 means no detail and 255 means everything \n"
            "(which is totally black)."
        )
        ti2_form_layout.addRow(self.mask_bw_label, self.mask_bw_entry)

        # Mask value of the imported image for RED color when image color
        self.mask_r_entry = IntEntry()
        self.mask_r_label = QtWidgets.QLabel("Mask value <b>R:</b>")
        self.mask_r_label.setToolTip(
            "Mask for RED color.\n"
            "Takes values between [0 ... 255].\n"
            "Decides the level of details to include\n"
            "in the resulting geometry."
        )
        ti2_form_layout.addRow(self.mask_r_label, self.mask_r_entry)

        # Mask value of the imported image for GREEN color when image color
        self.mask_g_entry = IntEntry()
        self.mask_g_label = QtWidgets.QLabel("Mask value <b>G:</b>")
        self.mask_g_label.setToolTip(
            "Mask for GREEN color.\n"
            "Takes values between [0 ... 255].\n"
            "Decides the level of details to include\n"
            "in the resulting geometry."
        )
        ti2_form_layout.addRow(self.mask_g_label, self.mask_g_entry)

        # Mask value of the imported image for BLUE color when image color
        self.mask_b_entry = IntEntry()
        self.mask_b_label = QtWidgets.QLabel("Mask value <b>B:</b>")
        self.mask_b_label.setToolTip(
            "Mask for BLUE color.\n"
            "Takes values between [0 ... 255].\n"
            "Decides the level of details to include\n"
            "in the resulting geometry."
        )
        ti2_form_layout.addRow(self.mask_b_label, self.mask_b_entry)

        # Buttons
        hlay = QtWidgets.QHBoxLayout()
        self.layout.addLayout(hlay)
        hlay.addStretch()

        self.import_button = QtWidgets.QPushButton("Import image")
        self.import_button.setToolTip(
            "Open a image of raster type and then import it in FlatCAM."
        )
        hlay.addWidget(self.import_button)

        self.layout.addStretch()

        ## Signals
        self.import_button.clicked.connect(self.on_file_importimage)

    def run(self, toggle=False):
        self.app.report_usage("ToolImage()")

        if toggle:
            # if the splitter is hidden, display it, else hide it but only if the current widget is the same
            if self.app.ui.splitter.sizes()[0] == 0:
                self.app.ui.splitter.setSizes([1, 1])
            else:
                try:
                    if self.app.ui.tool_scroll_area.widget().objectName() == self.toolName:
                        self.app.ui.splitter.setSizes([0, 1])
                except AttributeError:
                    pass

        FlatCAMTool.run(self)
        self.set_tool_ui()

        self.app.ui.notebook.setTabText(2, "Image Tool")

    def install(self, icon=None, separator=None, **kwargs):
        FlatCAMTool.install(self, icon, separator, **kwargs)

    def set_tool_ui(self):
        ## Initialize form
        self.dpi_entry.set_value(96)
        self.image_type.set_value('black')
        self.mask_bw_entry.set_value(250)
        self.mask_r_entry.set_value(250)
        self.mask_g_entry.set_value(250)
        self.mask_b_entry.set_value(250)

    def on_file_importimage(self):
        """
        Callback for menu item File->Import IMAGE.
        :param type_of_obj: to import the IMAGE as Geometry or as Gerber
        :type type_of_obj: str
        :return: None
        """
        mask = []
        self.app.log.debug("on_file_importimage()")

        filter = "Image Files(*.BMP *.PNG *.JPG *.JPEG);;" \
                 "Bitmap File (*.BMP);;" \
                 "PNG File (*.PNG);;" \
                 "Jpeg File (*.JPG);;" \
                 "All Files (*.*)"
        try:
            filename, _ = QtWidgets.QFileDialog.getOpenFileName(caption="Import IMAGE",
                                                         directory=self.app.get_last_folder(), filter=filter)
        except TypeError:
            filename, _ = QtWidgets.QFileDialog.getOpenFileName(caption="Import IMAGE", filter=filter)

        filename = str(filename)
        type = self.tf_type_obj_combo.get_value().lower()
        dpi = self.dpi_entry.get_value()
        mode = self.image_type.get_value()
        mask = [self.mask_bw_entry.get_value(), self.mask_r_entry.get_value(),self.mask_g_entry.get_value(),
                self.mask_b_entry.get_value()]

        if filename == "":
            self.app.inform.emit("Open cancelled.")
        else:
            self.app.worker_task.emit({'fcn': self.app.import_image,
                                       'params': [filename, type, dpi, mode, mask]})
            #  self.import_svg(filename, "geometry")
