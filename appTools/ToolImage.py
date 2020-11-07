# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 3/10/2019                                          #
# MIT Licence                                              #
# ##########################################################

from PyQt5 import QtGui, QtWidgets

from appTool import AppTool
from appGUI.GUIElements import RadioSet, FCComboBox, FCSpinner

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class ToolImage(AppTool):

    def __init__(self, app):
        AppTool.__init__(self, app)

        self.app = app
        self.decimals = self.app.decimals

        # #############################################################################
        # ######################### Tool GUI ##########################################
        # #############################################################################
        self.ui = ImageUI(layout=self.layout, app=self.app)
        self.toolName = self.ui.toolName

        # ## Signals
        self.ui.import_button.clicked.connect(self.on_file_importimage)
        self.ui.image_type.activated_custom.connect(self.ui.on_image_type)

    def run(self, toggle=True):
        self.app.defaults.report_usage("ToolImage()")

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

        self.app.ui.notebook.setTabText(2, _("Image Tool"))

    def install(self, icon=None, separator=None, **kwargs):
        AppTool.install(self, icon, separator, **kwargs)

    def set_tool_ui(self):
        # ## Initialize form
        self.ui.dpi_entry.set_value(96)
        self.ui.image_type.set_value('black')
        self.ui.mask_bw_entry.set_value(250)
        self.ui.mask_r_entry.set_value(250)
        self.ui.mask_g_entry.set_value(250)
        self.ui.mask_b_entry.set_value(250)

    def on_file_importimage(self):
        """
        Callback for menu item File->Import IMAGE.

        :return: None
        """

        self.app.log.debug("on_file_importimage()")

        _filter = "Image Files(*.BMP *.PNG *.JPG *.JPEG);;" \
                  "Bitmap File (*.BMP);;" \
                  "PNG File (*.PNG);;" \
                  "Jpeg File (*.JPG);;" \
                  "All Files (*.*)"
        try:
            filename, _f = QtWidgets.QFileDialog.getOpenFileName(caption=_("Import IMAGE"),
                                                                 directory=self.app.get_last_folder(), filter=_filter)
        except TypeError:
            filename, _f = QtWidgets.QFileDialog.getOpenFileName(caption=_("Import IMAGE"), filter=filter)

        filename = str(filename)
        type_obj = self.ui.tf_type_obj_combo.get_value()
        dpi = self.ui.dpi_entry.get_value()
        mode = self.ui.image_type.get_value()
        mask = [
            self.ui.mask_bw_entry.get_value(),
            self.ui.mask_r_entry.get_value(),
            self.ui.mask_g_entry.get_value(),
            self.ui.mask_b_entry.get_value()
        ]

        if filename == "":
            self.app.inform.emit(_("Cancelled."))
        else:
            self.app.worker_task.emit({'fcn': self.import_image,
                                       'params': [filename, type_obj, dpi, mode, mask]})

    def import_image(self, filename, o_type=_("Gerber"), dpi=96, mode='black', mask=None, outname=None):
        """
        Adds a new Geometry Object to the projects and populates
        it with shapes extracted from the SVG file.

        :param filename: Path to the SVG file.
        :param o_type: type of FlatCAM objeect
        :param dpi: dot per inch
        :param mode: black or color
        :param mask: dictate the level of detail
        :param outname: name for the resulting file
        :return:
        """

        self.app.defaults.report_usage("import_image()")

        if mask is None:
            mask = [250, 250, 250, 250]

        if o_type is None or o_type == _("Geometry"):
            obj_type = "geometry"
        elif o_type == _("Gerber"):
            obj_type = "gerber"
        else:
            self.app.inform.emit('[ERROR_NOTCL] %s' %
                                 _("Not supported type is picked as parameter. "
                                   "Only Geometry and Gerber are supported"))
            return

        def obj_init(geo_obj, app_obj):
            geo_obj.import_image(filename, units=units, dpi=dpi, mode=mode, mask=mask)
            geo_obj.multigeo = False

        with self.app.proc_container.new('%s ...' % _("Importing")):

            # Object name
            name = outname or filename.split('/')[-1].split('\\')[-1]
            units = self.app.defaults['units']

            self.app.app_obj.new_object(obj_type, name, obj_init)

            # Register recent file
            self.app.file_opened.emit("image", filename)

            # GUI feedback
            self.app.inform.emit('[success] %s: %s' % (_("Opened"), filename))


class ImageUI:

    toolName = _("Image as Object")

    def __init__(self, layout, app):
        self.app = app
        self.decimals = self.app.decimals
        self.layout = layout

        # ## Title
        title_label = QtWidgets.QLabel("%s" % self.toolName)
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
        self.tf_type_obj_combo.addItems([_("Gerber"), _("Geometry")])

        self.tf_type_obj_combo.setItemIcon(0, QtGui.QIcon(self.app.resource_location + "/flatcam_icon16.png"))
        self.tf_type_obj_combo.setItemIcon(1, QtGui.QIcon(self.app.resource_location + "/geometry16.png"))

        self.tf_type_obj_combo_label = QtWidgets.QLabel('%s:' % _("Object Type"))
        self.tf_type_obj_combo_label.setToolTip(
            _("Specify the type of object to create from the image.\n"
              "It can be of type: Gerber or Geometry.")

        )
        ti_form_layout.addRow(self.tf_type_obj_combo_label, self.tf_type_obj_combo)

        # DPI value of the imported image
        self.dpi_entry = FCSpinner(callback=self.confirmation_message_int)
        self.dpi_entry.set_range(0, 99999)
        self.dpi_label = QtWidgets.QLabel('%s:' % _("DPI value"))
        self.dpi_label.setToolTip(_("Specify a DPI value for the image."))
        ti_form_layout.addRow(self.dpi_label, self.dpi_entry)

        self.emty_lbl = QtWidgets.QLabel("")
        self.layout.addWidget(self.emty_lbl)

        self.detail_label = QtWidgets.QLabel("<font size=4><b>%s:</b></font>" % _('Level of detail'))
        self.layout.addWidget(self.detail_label)

        ti2_form_layout = QtWidgets.QFormLayout()
        self.layout.addLayout(ti2_form_layout)

        # Type of image interpretation
        self.image_type = RadioSet([{'label': 'B/W', 'value': 'black'},
                                    {'label': 'Color', 'value': 'color'}])
        self.image_type_label = QtWidgets.QLabel("<b>%s:</b>" % _('Image type'))
        self.image_type_label.setToolTip(
            _("Choose a method for the image interpretation.\n"
              "B/W means a black & white image. Color means a colored image.")
        )
        ti2_form_layout.addRow(self.image_type_label, self.image_type)

        # Mask value of the imported image when image monochrome
        self.mask_bw_entry = FCSpinner(callback=self.confirmation_message_int)
        self.mask_bw_entry.set_range(0, 255)

        self.mask_bw_label = QtWidgets.QLabel("%s <b>B/W</b>:" % _('Mask value'))
        self.mask_bw_label.setToolTip(
            _("Mask for monochrome image.\n"
              "Takes values between [0 ... 255].\n"
              "Decides the level of details to include\n"
              "in the resulting geometry.\n"
              "0 means no detail and 255 means everything \n"
              "(which is totally black).")
        )
        ti2_form_layout.addRow(self.mask_bw_label, self.mask_bw_entry)

        # Mask value of the imported image for RED color when image color
        self.mask_r_entry = FCSpinner(callback=self.confirmation_message_int)
        self.mask_r_entry.set_range(0, 255)

        self.mask_r_label = QtWidgets.QLabel("%s <b>R:</b>" % _('Mask value'))
        self.mask_r_label.setToolTip(
            _("Mask for RED color.\n"
              "Takes values between [0 ... 255].\n"
              "Decides the level of details to include\n"
              "in the resulting geometry.")
        )
        ti2_form_layout.addRow(self.mask_r_label, self.mask_r_entry)

        # Mask value of the imported image for GREEN color when image color
        self.mask_g_entry = FCSpinner(callback=self.confirmation_message_int)
        self.mask_g_entry.set_range(0, 255)

        self.mask_g_label = QtWidgets.QLabel("%s <b>G:</b>" % _('Mask value'))
        self.mask_g_label.setToolTip(
            _("Mask for GREEN color.\n"
              "Takes values between [0 ... 255].\n"
              "Decides the level of details to include\n"
              "in the resulting geometry.")
        )
        ti2_form_layout.addRow(self.mask_g_label, self.mask_g_entry)

        # Mask value of the imported image for BLUE color when image color
        self.mask_b_entry = FCSpinner(callback=self.confirmation_message_int)
        self.mask_b_entry.set_range(0, 255)

        self.mask_b_label = QtWidgets.QLabel("%s <b>B:</b>" % _('Mask value'))
        self.mask_b_label.setToolTip(
            _("Mask for BLUE color.\n"
              "Takes values between [0 ... 255].\n"
              "Decides the level of details to include\n"
              "in the resulting geometry.")
        )
        ti2_form_layout.addRow(self.mask_b_label, self.mask_b_entry)

        # Buttons
        self.import_button = QtWidgets.QPushButton(_("Import image"))
        self.import_button.setToolTip(
            _("Open a image of raster type and then import it in FlatCAM.")
        )
        self.layout.addWidget(self.import_button)

        self.layout.addStretch()

        self.on_image_type(val=False)

        # #################################### FINSIHED GUI ###########################
        # #############################################################################

    def on_image_type(self, val):
        if val == 'color':
            self.mask_r_label.setDisabled(False)
            self.mask_r_entry.setDisabled(False)
            self.mask_g_label.setDisabled(False)
            self.mask_g_entry.setDisabled(False)
            self.mask_b_label.setDisabled(False)
            self.mask_b_entry.setDisabled(False)

            self.mask_bw_label.setDisabled(True)
            self.mask_bw_entry.setDisabled(True)
        else:
            self.mask_r_label.setDisabled(True)
            self.mask_r_entry.setDisabled(True)
            self.mask_g_label.setDisabled(True)
            self.mask_g_entry.setDisabled(True)
            self.mask_b_label.setDisabled(True)
            self.mask_b_entry.setDisabled(True)

            self.mask_bw_label.setDisabled(False)
            self.mask_bw_entry.setDisabled(False)

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
