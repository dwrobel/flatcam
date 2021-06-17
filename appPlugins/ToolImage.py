# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 3/10/2019                                          #
# MIT Licence                                              #
# ##########################################################

from PyQt5 import QtGui, QtWidgets

from appTool import AppTool
from appGUI.GUIElements import RadioSet, FCComboBox, FCSpinner, FCLabel, VerticalScrollArea

import os

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
        self.pluginName = self.ui.pluginName
        self.connect_signals_at_init()

    def run(self, toggle=True):
        self.app.defaults.report_usage("ToolImage()")

        if toggle:
            # if the splitter is hidden, display it
            if self.app.ui.splitter.sizes()[0] == 0:
                self.app.ui.splitter.setSizes([1, 1])

            # if the Tool Tab is hidden display it, else hide it but only if the objectName is the same
            found_idx = None
            for idx in range(self.app.ui.notebook.count()):
                if self.app.ui.notebook.widget(idx).objectName() == "plugin_tab":
                    found_idx = idx
                    break
            # show the Tab
            if not found_idx:
                try:
                    self.app.ui.notebook.addTab(self.app.ui.plugin_tab, _("Plugin"))
                except RuntimeError:
                    self.app.ui.plugin_tab = QtWidgets.QWidget()
                    self.app.ui.plugin_tab.setObjectName("plugin_tab")
                    self.app.ui.plugin_tab_layout = QtWidgets.QVBoxLayout(self.app.ui.plugin_tab)
                    self.app.ui.plugin_tab_layout.setContentsMargins(2, 2, 2, 2)

                    self.app.ui.plugin_scroll_area = VerticalScrollArea()
                    self.app.ui.plugin_tab_layout.addWidget(self.app.ui.plugin_scroll_area)
                    self.app.ui.notebook.addTab(self.app.ui.plugin_tab, _("Plugin"))
                # focus on Tool Tab
                self.app.ui.notebook.setCurrentWidget(self.app.ui.plugin_tab)

            try:
                if self.app.ui.plugin_scroll_area.widget().objectName() == self.pluginName and found_idx:
                    # if the Tool Tab is not focused, focus on it
                    if not self.app.ui.notebook.currentWidget() is self.app.ui.plugin_tab:
                        # focus on Tool Tab
                        self.app.ui.notebook.setCurrentWidget(self.app.ui.plugin_tab)
                    else:
                        # else remove the Tool Tab
                        self.app.ui.notebook.setCurrentWidget(self.app.ui.properties_tab)
                        self.app.ui.notebook.removeTab(2)

                        # if there are no objects loaded in the app then hide the Notebook widget
                        if not self.app.collection.get_list():
                            self.app.ui.splitter.setSizes([0, 1])
            except AttributeError:
                pass
        else:
            if self.app.ui.splitter.sizes()[0] == 0:
                self.app.ui.splitter.setSizes([1, 1])

        AppTool.run(self)
        self.set_tool_ui()

        self.app.ui.notebook.setTabText(2, _("Image Import"))

    def install(self, icon=None, separator=None, **kwargs):
        AppTool.install(self, icon, separator, **kwargs)

    def connect_signals_at_init(self):
        # ## Signals
        self.ui.import_button.clicked.connect(self.on_file_importimage)
        self.ui.image_type.activated_custom.connect(self.ui.on_image_type)

    def set_tool_ui(self):
        self.clear_ui(self.layout)
        self.ui = ImageUI(layout=self.layout, app=self.app)
        self.pluginName = self.ui.pluginName
        self.connect_signals_at_init()

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
            filename, _f = QtWidgets.QFileDialog.getOpenFileName(caption=_("Import IMAGE"), filter=_filter)

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
        if not os.path.exists(filename):
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("File no longer available."))
            return

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
            app_obj.log.debug("ToolIamge.import_image() -> importing image as geometry")
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

    pluginName = _("Image Import")

    def __init__(self, layout, app):
        self.app = app
        self.decimals = self.app.decimals
        self.layout = layout

        # ## Title
        title_label = FCLabel("%s" % self.pluginName)
        title_label.setStyleSheet("""
                                QLabel
                                {
                                    font-size: 16px;
                                    font-weight: bold;
                                }
                                """)
        self.layout.addWidget(title_label)

        # Grid Layout
        grid0 = QtWidgets.QGridLayout()
        grid0.setColumnStretch(0, 0)
        grid0.setColumnStretch(1, 1)
        self.layout.addLayout(grid0)

        # Type of object to create for the image
        self.tf_type_obj_combo = FCComboBox()
        self.tf_type_obj_combo.addItems([_("Gerber"), _("Geometry")])

        self.tf_type_obj_combo.setItemIcon(0, QtGui.QIcon(self.app.resource_location + "/flatcam_icon16.png"))
        self.tf_type_obj_combo.setItemIcon(1, QtGui.QIcon(self.app.resource_location + "/geometry16.png"))

        self.tf_type_obj_combo_label = FCLabel('%s:' % _("Object Type"))
        self.tf_type_obj_combo_label.setToolTip(
            _("Specify the type of object to create from the image.\n"
              "It can be of type: Gerber or Geometry.")

        )
        grid0.addWidget(self.tf_type_obj_combo_label, 0, 0)
        grid0.addWidget(self.tf_type_obj_combo, 0, 1)

        # DPI value of the imported image
        self.dpi_entry = FCSpinner(callback=self.confirmation_message_int)
        self.dpi_entry.set_range(0, 99999)
        self.dpi_label = FCLabel('%s:' % _("DPI value"))
        self.dpi_label.setToolTip(_("Specify a DPI value for the image."))
        grid0.addWidget(self.dpi_label, 2, 0)
        grid0.addWidget(self.dpi_entry, 2, 1)

        grid0.addWidget(FCLabel(''), 4, 0, 1, 2)

        self.detail_label = FCLabel("<font size=4><b>%s:</b></font>" % _('Level of detail'))
        grid0.addWidget(self.detail_label, 6, 0, 1, 2)

        # Type of image interpretation
        self.image_type = RadioSet([{'label': 'B/W', 'value': 'black'},
                                    {'label': 'Color', 'value': 'color'}])
        self.image_type_label = FCLabel("<b>%s:</b>" % _('Image type'))
        self.image_type_label.setToolTip(
            _("Choose a method for the image interpretation.\n"
              "B/W means a black & white image. Color means a colored image.")
        )
        grid0.addWidget(self.image_type_label, 8, 0)
        grid0.addWidget(self.image_type, 8, 1)

        # Mask value of the imported image when image monochrome
        self.mask_bw_entry = FCSpinner(callback=self.confirmation_message_int)
        self.mask_bw_entry.set_range(0, 255)

        self.mask_bw_label = FCLabel("%s <b>B/W</b>:" % _('Mask value'))
        self.mask_bw_label.setToolTip(
            _("Mask for monochrome image.\n"
              "Takes values between [0 ... 255].\n"
              "Decides the level of details to include\n"
              "in the resulting geometry.\n"
              "0 means no detail and 255 means everything \n"
              "(which is totally black).")
        )
        grid0.addWidget(self.mask_bw_label, 10, 0)
        grid0.addWidget(self.mask_bw_entry, 10, 1)

        # Mask value of the imported image for RED color when image color
        self.mask_r_entry = FCSpinner(callback=self.confirmation_message_int)
        self.mask_r_entry.set_range(0, 255)

        self.mask_r_label = FCLabel("%s <b>R:</b>" % _('Mask value'))
        self.mask_r_label.setToolTip(
            _("Mask for RED color.\n"
              "Takes values between [0 ... 255].\n"
              "Decides the level of details to include\n"
              "in the resulting geometry.")
        )
        grid0.addWidget(self.mask_r_label, 12, 0)
        grid0.addWidget(self.mask_r_entry, 12, 1)

        # Mask value of the imported image for GREEN color when image color
        self.mask_g_entry = FCSpinner(callback=self.confirmation_message_int)
        self.mask_g_entry.set_range(0, 255)

        self.mask_g_label = FCLabel("%s <b>G:</b>" % _('Mask value'))
        self.mask_g_label.setToolTip(
            _("Mask for GREEN color.\n"
              "Takes values between [0 ... 255].\n"
              "Decides the level of details to include\n"
              "in the resulting geometry.")
        )
        grid0.addWidget(self.mask_g_label, 14, 0)
        grid0.addWidget(self.mask_g_entry, 14, 1)

        # Mask value of the imported image for BLUE color when image color
        self.mask_b_entry = FCSpinner(callback=self.confirmation_message_int)
        self.mask_b_entry.set_range(0, 255)

        self.mask_b_label = FCLabel("%s <b>B:</b>" % _('Mask value'))
        self.mask_b_label.setToolTip(
            _("Mask for BLUE color.\n"
              "Takes values between [0 ... 255].\n"
              "Decides the level of details to include\n"
              "in the resulting geometry.")
        )
        grid0.addWidget(self.mask_b_label, 16, 0)
        grid0.addWidget(self.mask_b_entry, 16, 1)

        # Buttons
        self.import_button = QtWidgets.QPushButton(_("Import image"))
        self.import_button.setToolTip(
            _("Open a image of raster type and then import it in FlatCAM.")
        )
        grid0.addWidget(self.import_button, 18, 0, 1, 2)

        self.layout.addStretch(1)

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
