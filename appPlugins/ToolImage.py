# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 3/10/2019                                          #
# MIT Licence                                              #
# ##########################################################

from appTool import *
from rasterio import open as rasterio_open
from rasterio.features import shapes

from svgtrace import trace
from pyppeteer.chromium_downloader import check_chromium
from lxml import etree as ET

from appParsers.ParseSVG import svgparselength, svgparse_viewbox, getsvggeo, getsvgtext

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
        self.ui.import_button.clicked.connect(lambda: self.on_file_importimage())
        self.ui.image_type.activated_custom.connect(self.ui.on_image_type)

    def set_tool_ui(self):
        self.clear_ui(self.layout)
        self.ui = ImageUI(layout=self.layout, app=self.app)
        self.pluginName = self.ui.pluginName
        self.connect_signals_at_init()

        # ## Initialize form
        self.ui.dpi_entry.set_value(96)
        self.ui.image_type.set_value('black')
        self.ui.on_image_type(val=self.ui.image_type.get_value())

        self.ui.min_area_entry.set_value(0.3)

        self.ui.import_mode_radio.set_value('raster')
        self.ui.on_import_image_mode(val=self.ui.import_mode_radio.get_value())

        self.ui.control_radio.set_value('presets')
        self.ui.on_tracing_control_radio(val=self.ui.control_radio.get_value())

        self.ui.mask_bw_entry.set_value(250)
        self.ui.mask_r_entry.set_value(250)
        self.ui.mask_g_entry.set_value(250)
        self.ui.mask_b_entry.set_value(250)

        self.ui.error_lines_entry.set_value(1)
        self.ui.error_splines_entry.set_value(0)
        self.ui.path_omit_entry.set_value(8)
        self.ui.enhance_rangle_cb.set_value(True)
        self.ui.sampling_combo.set_value(0)
        self.ui.nr_colors_entry.set_value(16)
        self.ui.ratio_entry.set_value(0)
        self.ui.cycles_entry.set_value(3)
        self.ui.stroke_width_entry.set_value(1.0)
        self.ui.line_filter_cb.set_value(False)
        self.ui.rounding_entry.set_value(1)
        self.ui.blur_radius_entry.set_value(1)
        self.ui.blur_delta_entry.set_value(20)

    def on_file_importimage(self, threaded=True):
        """
        Callback for menu item File->Import IMAGE.

        :return: None
        """

        self.app.log.debug("on_file_importimage()")

        import_mode = self.ui.import_mode_radio.get_value()
        trace_options = self.ui.presets_combo.get_value() if self.ui.control_radio.get_value() == 'presets' else \
            self.get_tracing_options()
        type_obj = self.ui.tf_type_obj_combo.get_value()
        dpi = self.ui.dpi_entry.get_value()
        mode = self.ui.image_type.get_value()
        min_area = self.ui.min_area_entry.get_value()

        if import_mode == 'trace':
            # check if Chromium is present, if not issue a warning
            res = check_chromium()
            if res is False:
                msgbox = FCMessageBox(parent=self.app.ui)
                title = _("Import warning")
                txt = _("The tracing require Chromium,\n"
                        "but it was not detected.\n"
                        "\n"
                        "Do you want to download it (about 300MB)?")
                msgbox.setWindowTitle(title)  # taskbar still shows it
                msgbox.setWindowIcon(QtGui.QIcon(self.app.resource_location + '/app128.png'))
                msgbox.setText('<b>%s</b>' % title)
                msgbox.setInformativeText(txt)
                msgbox.setIcon(QtWidgets.QMessageBox.Icon.Warning)

                bt_yes = msgbox.addButton(_('Yes'), QtWidgets.QMessageBox.ButtonRole.YesRole)
                bt_no = msgbox.addButton(_('No'), QtWidgets.QMessageBox.ButtonRole.NoRole)

                msgbox.setDefaultButton(bt_yes)
                msgbox.exec()
                response = msgbox.clickedButton()

                if response == bt_no:
                    self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled."))
                    return
                self.app.inform.emit(_("Please be patient. Chromium is being downloaded in the background.\n"
                                       "The app will resume after it is installed."))

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

        mask = [
            self.ui.mask_bw_entry.get_value(),
            self.ui.mask_r_entry.get_value(),
            self.ui.mask_g_entry.get_value(),
            self.ui.mask_b_entry.get_value()
        ]

        if filename == "":
            self.app.inform.emit(_("Cancelled."))
        else:
            if import_mode == 'trace':
                # there are thread issues so I process this outside
                svg_text = trace(filename, blackAndWhite=True if mode == 'black' else False, mode=trace_options)
            else:
                svg_text = None
            if threaded is True:
                self.app.worker_task.emit({'fcn': self.import_image,
                                           'params': [
                                               filename, import_mode, type_obj, dpi, mode, mask, svg_text, min_area]
                                           })
            else:
                self.import_image(filename, import_mode, type_obj, dpi, mode, mask, svg_text, min_area)

    def import_image(self, filename, import_mode='raster', o_type=_("Geometry"), dpi=96, mode='black',
                     mask=None, svg_text=None, min_area=0.0, outname=None, silent=False):
        """
        Adds a new Geometry Object to the projects and populates
        it with shapes extracted from the SVG file.

        :param filename:        Path to the SVG file.
        :param import_mode:     The kind of image import to be done: 'raster' or 'trace'
        :param o_type:          type of FlatCAM object
        :param dpi:             dot per inch
        :param mode:            black or color
        :param mask:            dictate the level of detail
        :param svg_text:        a SVG string only for when tracing
        :param outname:         name for the resulting file
        :param min_area:        the minimum area for the imported polygons for them to be kept
        :param silent:          bool: if False then there are no messages issued to GUI
        :return:
        """

        self.app.defaults.report_usage("import_image()")
        if not os.path.exists(filename):
            if silent:
                self.app.log.debug("File no longer available.")
            else:
                self.app.inform.emit('[ERROR_NOTCL] %s' % _("File no longer available."))
            return

        if mask is None:
            mask = [250, 250, 250, 250]

        if o_type is None or o_type == _("Geometry"):
            obj_type = "geometry"
        elif o_type == _("Gerber"):
            obj_type = "gerber"
        else:
            if silent is False:
                self.app.inform.emit('[ERROR_NOTCL] %s' % _("Only Geometry and Gerber objects are supported"))
            return

        def obj_init(geo_obj, app_obj):
            app_obj.log.debug("ToolImage.import_image() -> importing image as: %s" % obj_type.capitalize())
            if import_mode == 'raster':
                image_geo = self.import_image_handler(filename, units=units, dpi=dpi, mode=mode, mask=mask)
            else:   # 'trace'
                image_geo = self.import_image_as_trace_handler(svg_text=svg_text, obj_type=obj_type, units=units,
                                                               dpi=dpi)

            if not image_geo:
                app_obj.log.debug("ToolImage.import_image() -> empty geometry.")
                return 'fail'

            if image_geo == 'fail':
                if silent is False:
                    app_obj.inform.emit("[ERROR_NOTCL] %s" % _("Failed."))
                return "fail"

            geo_obj.multigeo = False
            geo_obj.multitool = False

            # flatten the geo_obj.solid_geometry list
            geo_obj.solid_geometry = list(self.flatten_list(image_geo))
            geo_obj.solid_geometry = [p for p in geo_obj.solid_geometry if p and p.is_valid and p.area >= min_area]

            if obj_type == 'geometry':
                tooldia = float(self.app.options["tools_mill_tooldia"])
                tooldia = float('%.*f' % (self.decimals, tooldia))

                new_data = {k: v for k, v in self.app.options.items()}

                geo_obj.tools.update({
                    1: {
                        'tooldia': tooldia,
                        'data': deepcopy(new_data),
                        'solid_geometry': deepcopy(geo_obj.solid_geometry)
                    }
                })

                geo_obj.tools[1]['data']['name'] = name
                if svg_text is not None:
                    geo_obj.source_file = svg_text
                else:
                    geo_obj.source_file = app_obj.f_handlers.export_dxf(
                        obj_name=None, filename=None, local_use=geo_obj, use_thread=False)
            else:   # 'gerber'
                if 0 not in geo_obj.tools:
                    geo_obj.tools[0] = {
                        'type': 'REG',
                        'size': 0.0,
                        'geometry': []
                    }

                try:
                    w_geo = geo_obj.solid_geometry.geoms if \
                        isinstance(geo_obj.solid_geometry, (MultiLineString, MultiPolygon)) else geo_obj.solid_geometry
                    for pol in w_geo:
                        new_el = {'solid': pol, 'follow': LineString(pol.exterior.coords)}
                        geo_obj.tools[0]['geometry'].append(new_el)
                except TypeError:
                    new_el = {
                        'solid': geo_obj.solid_geometry,
                        'follow': LineString(geo_obj.solid_geometry.exterior.coords) if
                        isinstance(geo_obj.solid_geometry, Polygon) else geo_obj.solid_geometry
                    }
                    geo_obj.tools[0]['geometry'].append(new_el)
                geo_obj.source_file = app_obj.f_handlers.export_gerber(
                    obj_name=None, filename=None, local_use=geo_obj, use_thread=False)

        with self.app.proc_container.new('%s ...' % _("Importing")):

            # Object name
            name = outname or filename.split('/')[-1].split('\\')[-1]
            units = self.app.app_units

            res = self.app.app_obj.new_object(obj_type, name, obj_init)
            if res == 'fail':
                self.app.inform.emit("[ERROR_NOTCL] %s" % _("Failed."))
                return
            # Register recent file
            self.app.file_opened.emit("image", filename)

            # GUI feedback
            if silent is False:
                self.app.inform.emit('[success] %s: %s' % (_("Opened"), filename))

    def import_image_handler(self, filename, flip=True, units='MM', dpi=96, mode='black', mask=None):
        """
        Imports shapes from an IMAGE file into the object's geometry.

        :param filename:    Path to the IMAGE file.
        :type filename:     str
        :param flip:        Flip the object vertically.
        :type flip:         bool
        :param units:       App units
        :type units:        str
        :param dpi:         dots per inch on the imported image
        :param mode:        how to import the image: as 'black' or 'color'
        :type mode:         str
        :param mask:        level of detail for the import
        :return:            None
        """
        if mask is None:
            mask = [128, 128, 128, 128]

        scale_factor = 25.4 / dpi if units.lower() == 'mm' else 1 / dpi

        geos = []
        unscaled_geos = []

        with rasterio_open(filename) as src:
            # if filename.lower().rpartition('.')[-1] == 'bmp':
            #     red = green = blue = src.read(1)
            #     print("BMP")
            # elif filename.lower().rpartition('.')[-1] == 'png':
            #     red, green, blue, alpha = src.read()
            # elif filename.lower().rpartition('.')[-1] == 'jpg':
            #     red, green, blue = src.read()

            red = green = blue = src.read(1)

            try:
                green = src.read(2)
            except Exception:
                pass

            try:
                blue = src.read(3)
            except Exception:
                pass

        if mode == 'black':
            mask_setting = red <= mask[0]
            total = red
            self.app.log.debug("Image import as monochrome.")
        else:
            mask_setting = (red <= mask[1]) + (green <= mask[2]) + (blue <= mask[3])
            total = np.zeros(red.shape, dtype=np.float32)
            for band in red, green, blue:
                total += band
            total /= 3
            self.app.log.debug("Image import as colored. Thresholds are: R = %s , G = %s, B = %s" %
                               (str(mask[1]), str(mask[2]), str(mask[3])))

        for geom, val in shapes(total, mask=mask_setting):
            unscaled_geos.append(shape(geom))

        for g in unscaled_geos:
            geos.append(scale(g, scale_factor, scale_factor, origin=(0, 0)))

        if flip:
            geos = [translate(scale(g, 1.0, -1.0, origin=(0, 0))) for g in geos]

        return geos

    def import_image_as_trace_handler(self, svg_text, obj_type, flip=True, units='MM', dpi=96):
        """
        Imports shapes from an IMAGE file into the object's geometry.

        :param svg_text:    A SVG text object
        :type svg_text:     str
        :param obj_type:    the way the image is imported. As: 'gerber' or 'geometry' objects
        :type obj_type:     str
        :param flip:        Flip the object vertically.
        :type flip:         bool
        :param units:       App units
        :type units:        str
        :param dpi:         dots per inch on the imported image
        :return:            None
        """

        # Parse into list of shapely objects
        # svg_tree = ET.parse(filename)
        # svg_root = svg_tree.getroot()
        svg_root = ET.fromstring(svg_text)

        # Change origin to bottom left
        # h = float(svg_root.get('height'))
        # w = float(svg_root.get('width'))
        svg_parsed_dims = svgparselength(svg_root.get('height'))
        h = svg_parsed_dims[0]
        svg_units = svg_parsed_dims[1]
        if svg_units in ['em', 'ex', 'pt', 'px']:
            self.app.log.error("ToolImage.import_image_as_trace_handler(). SVG units not supported: %s" % svg_units)
            return "fail"

        res = self.app.options['geometry_circle_steps']
        factor = svgparse_viewbox(svg_root)

        if svg_units == 'cm':
            factor *= 10

        geos = getsvggeo(svg_root, obj_type, units=units, res=res, factor=factor, app=self.app)
        if geos is None:
            return 'fail'
        self.app.log.debug("ToolImage.import_image_as_trace_handler(). Finished parsing the SVG geometry.")

        geos_text = getsvgtext(svg_root, obj_type, app=self.app, units=units)
        if geos_text is not None:
            self.app.log.debug("ToolImage.import_image_as_trace_handler(). Processing SVG text.")
            geos_text_f = []
            if flip:
                # Change origin to bottom left
                for i in geos_text:
                    __, minimy, __, maximy = i.bounds
                    h2 = (maximy - minimy) * 0.5
                    geos_text_f.append(translate(scale(i, 1.0, -1.0, origin=(0, 0)), yoff=(h + h2)))
            if geos_text_f:
                geos += geos_text_f

        if flip:
            geos = [translate(scale(g, 1.0, -1.0, origin=(0, 0))) for g in geos]
            self.app.log.debug("ToolImage.import_image_as_trace_handler(). SVG geometry was flipped.")

        scale_factor = 25.4 / dpi if units.lower() == 'mm' else 1 / dpi
        geos = [translate(scale(g, scale_factor, scale_factor, origin=(0, 0))) for g in geos]

        return geos

    def get_tracing_options(self):
        opt_dict = {
            'ltres': self.ui.error_lines_entry.get_value(),
            'qtres': self.ui.error_splines_entry.get_value(),
            'pathomit': self.ui.path_omit_entry.get_value(),
            'rightangleenhance': self.ui.enhance_rangle_cb.get_value(),
            'colorsampling': self.ui.sampling_combo.get_value(),
            'numberofcolors': self.ui.nr_colors_entry.get_value(),
            'mincolorratio': self.ui.ratio_entry.get_value(),
            'colorquantcycles': self.ui.cycles_entry.get_value(),
            'strokewidth': self.ui.stroke_width_entry.get_value(),
            'linefilter': self.ui.line_filter_cb.get_value(),
            'roundcoords': self.ui.rounding_entry.get_value(),
            'blurradius': self.ui.blur_radius_entry.get_value(),
            'blurdelta': self.ui.blur_delta_entry.get_value()
        }
        dict_as_string = '{ '
        for k, v in opt_dict.items():
            dict_as_string += "%s:%s, " % (str(k), str(v))
            # remove last comma and space and add the terminator
        dict_as_string = dict_as_string[:-2] + ' }'
        return dict_as_string

    def flatten_list(self, obj_list):
        for item in obj_list:
            if hasattr(item, '__iter__') and not isinstance(item, (str, bytes)):
                yield from self.flatten_list(item)
            else:
                yield item


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

        self.param_lbl = FCLabel('%s' % _("Parameters"), color='blue', bold=True)
        self.layout.addWidget(self.param_lbl)
        # #############################################################################################################
        # ######################################## Parameters #########################################################
        # #############################################################################################################
        # add a frame and inside add a grid box layout.
        par_frame = FCFrame()
        self.layout.addWidget(par_frame)

        par_grid = GLay(v_spacing=5, h_spacing=3)
        par_frame.setLayout(par_grid)

        # Type of object to create for the image
        self.tf_type_obj_combo_label = FCLabel('%s:' % _("Object Type"))
        self.tf_type_obj_combo_label.setToolTip(
            _("Specify the type of object to create from the image.\n"
              "It can be of type: Gerber or Geometry.")

        )

        self.tf_type_obj_combo = FCComboBox()
        self.tf_type_obj_combo.addItems([_("Gerber"), _("Geometry")])
        self.tf_type_obj_combo.setItemIcon(0, QtGui.QIcon(self.app.resource_location + "/flatcam_icon16.png"))
        self.tf_type_obj_combo.setItemIcon(1, QtGui.QIcon(self.app.resource_location + "/geometry16.png"))

        par_grid.addWidget(self.tf_type_obj_combo_label, 0, 0)
        par_grid.addWidget(self.tf_type_obj_combo, 0, 1, 1, 2)

        # DPI value of the imported image
        self.dpi_entry = FCSpinner()
        self.dpi_entry.set_range(0, 99999)
        self.dpi_label = FCLabel('%s:' % _("DPI value"))
        self.dpi_label.setToolTip(_("Specify a DPI value for the image."))
        par_grid.addWidget(self.dpi_label, 2, 0)
        par_grid.addWidget(self.dpi_entry, 2, 1, 1, 2)

        # Area
        area_lbl = FCLabel('%s' % _("Area:"), bold=True)
        area_lbl.setToolTip(
            _("Polygons inside the image with less area are discarded.")
        )
        self.min_area_entry = FCDoubleSpinner()
        self.min_area_entry.set_range(0.0000, 10000.0000)
        self.min_area_entry.setSingleStep(0.1)
        self.min_area_entry.set_value(0.0)
        a_units = _("mm") if self.app.app_units == 'MM' else _("in")
        area_units_lbl = FCLabel('%s<sup>2</sup>' % a_units)

        par_grid.addWidget(area_lbl, 4, 0)
        par_grid.addWidget(self.min_area_entry, 4, 1)
        par_grid.addWidget(area_units_lbl, 4, 2)

        # The import Mode
        self.import_mode_lbl = FCLabel('%s:' % _('Mode'), color='red', bold=True)
        self.import_mode_lbl.setToolTip(
            _("Choose a method for the image interpretation.\n"
              "B/W means a black & white image. Color means a colored image.")
        )

        self.import_mode_radio = RadioSet([
            {'label': 'Raster', 'value': 'raster'},
            {'label': 'Tracing', 'value': 'trace'}
        ])

        mod_grid = GLay(v_spacing=5, h_spacing=3)
        self.layout.addLayout(mod_grid)

        mod_grid.addWidget(self.import_mode_lbl, 0, 0)
        mod_grid.addWidget(self.import_mode_radio, 0, 1)

        # Type of image interpretation
        self.image_type_label = FCLabel('%s:' % _('Type'), bold=True)
        self.image_type_label.setToolTip(
            _("Choose a method for the image interpretation.\n"
              "B/W means a black & white image. Color means a colored image.")
        )

        self.image_type = RadioSet([{'label': 'B/W', 'value': 'black'},
                                    {'label': 'Color', 'value': 'color'}])

        mod_grid.addWidget(self.image_type_label, 6, 0)
        mod_grid.addWidget(self.image_type, 6, 1, 1, 2)

        # #############################################################################################################
        # ######################################## Raster Mode ########################################################
        # #############################################################################################################
        # add a frame and inside add a grid box layout.
        self.raster_frame = FCFrame()
        self.layout.addWidget(self.raster_frame)

        raster_grid = GLay(v_spacing=5, h_spacing=3)
        self.raster_frame.setLayout(raster_grid)

        self.detail_label = FCLabel("%s:" % _('Level of detail'), bold=True)
        raster_grid.addWidget(self.detail_label, 0, 0, 1, 2)

        # Mask value of the imported image when image monochrome
        self.mask_bw_entry = FCSpinner()
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
        raster_grid.addWidget(self.mask_bw_label, 2, 0)
        raster_grid.addWidget(self.mask_bw_entry, 2, 1)

        # Mask value of the imported image for RED color when image color
        self.mask_r_entry = FCSpinner()
        self.mask_r_entry.set_range(0, 255)

        self.mask_r_label = FCLabel("%s <b>R:</b>" % _('Mask value'))
        self.mask_r_label.setToolTip(
            _("Mask for RED color.\n"
              "Takes values between [0 ... 255].\n"
              "Decides the level of details to include\n"
              "in the resulting geometry.")
        )
        raster_grid.addWidget(self.mask_r_label, 4, 0)
        raster_grid.addWidget(self.mask_r_entry, 4, 1)

        # Mask value of the imported image for GREEN color when image color
        self.mask_g_entry = FCSpinner()
        self.mask_g_entry.set_range(0, 255)

        self.mask_g_label = FCLabel("%s <b>G:</b>" % _('Mask value'))
        self.mask_g_label.setToolTip(
            _("Mask for GREEN color.\n"
              "Takes values between [0 ... 255].\n"
              "Decides the level of details to include\n"
              "in the resulting geometry.")
        )
        raster_grid.addWidget(self.mask_g_label, 6, 0)
        raster_grid.addWidget(self.mask_g_entry, 6, 1)

        # Mask value of the imported image for BLUE color when image color
        self.mask_b_entry = FCSpinner()
        self.mask_b_entry.set_range(0, 255)

        self.mask_b_label = FCLabel("%s <b>B:</b>" % _('Mask value'))
        self.mask_b_label.setToolTip(
            _("Mask for BLUE color.\n"
              "Takes values between [0 ... 255].\n"
              "Decides the level of details to include\n"
              "in the resulting geometry.")
        )
        raster_grid.addWidget(self.mask_b_label, 8, 0)
        raster_grid.addWidget(self.mask_b_entry, 8, 1)

        # #############################################################################################################
        # ######################################## Raster Mode ########################################################
        # #############################################################################################################
        # add a frame and inside add a grid box layout.
        self.trace_frame = FCFrame()
        self.layout.addWidget(self.trace_frame)

        trace_grid = GLay(v_spacing=5, h_spacing=3)
        self.trace_frame.setLayout(trace_grid)

        # Options Control Mode
        self.control_lbl = FCLabel('%s:' % _('Control'), color='indigo', bold=True)
        self.control_lbl.setToolTip(
            _("Tracing control.")
        )

        self.control_radio = RadioSet([
            {'label': _("Presets"), 'value': 'presets'},
            {'label': _("Options"), 'value': 'options'}
        ])

        trace_grid.addWidget(self.control_lbl, 0, 0)
        trace_grid.addWidget(self.control_radio, 0, 1)

        # --------------------------------------------------
        # Presets Frame
        # --------------------------------------------------
        self.preset_frame = QtWidgets.QFrame()
        self.preset_frame.setContentsMargins(0, 0, 0, 0)
        trace_grid.addWidget(self.preset_frame, 2, 0, 1, 2)

        preset_grid = GLay(v_spacing=5, h_spacing=3)
        preset_grid.setContentsMargins(0, 0, 0, 0)
        self.preset_frame.setLayout(preset_grid)

        # Presets
        self.presets_lbl = FCLabel('%s:' % _('Presets'))
        self.presets_lbl.setToolTip(
            _("Options presets to control the tracing.")
        )

        self.presets_combo = FCComboBox()
        self.presets_combo.addItems([
            'default', 'posterized1', 'posterized2', 'posterized3', 'curvy', 'sharp', 'detailed', 'smoothed',
            'grayscale', 'fixedpalette', 'randomsampling1', 'randomsampling2', 'artistic1', 'artistic2', 'artistic3',
            'artistic4'
        ])
        preset_grid.addWidget(self.presets_lbl, 0, 0)
        preset_grid.addWidget(self.presets_combo, 0, 1)

        # --------------------------------------------------
        # Options Frame
        # --------------------------------------------------
        self.options_frame = QtWidgets.QFrame()
        self.options_frame.setContentsMargins(0, 0, 0, 0)
        trace_grid.addWidget(self.options_frame, 4, 0, 1, 2)

        options_grid = GLay(v_spacing=5, h_spacing=3)
        options_grid.setContentsMargins(0, 0, 0, 0)
        self.options_frame.setLayout(options_grid)

        # Error Threshold
        self.error_lbl = FCLabel('%s' % _("Error Threshold"), bold=True)
        self.error_lbl.setToolTip(
            _("Error threshold for straight lines and quadratic splines.")
        )
        options_grid.addWidget(self.error_lbl, 0, 0, 1, 2)

        # Error Threshold for Lines
        self.error_lines_lbl = FCLabel('%s:' % _("Lines"))
        self.error_lines_entry = FCDoubleSpinner()
        self.error_lines_entry.set_precision(self.decimals)
        self.error_lines_entry.set_range(0, 10)
        self.error_lines_entry.setSingleStep(0.1)

        options_grid.addWidget(self.error_lines_lbl, 2, 0)
        options_grid.addWidget(self.error_lines_entry, 2, 1)

        # Error Threshold for Splines
        self.error_splines_lbl = FCLabel('%s:' % _("Splines"))
        self.error_splines_entry = FCDoubleSpinner()
        self.error_splines_entry.set_precision(self.decimals)
        self.error_splines_entry.set_range(0, 10)
        self.error_splines_entry.setSingleStep(0.1)

        options_grid.addWidget(self.error_splines_lbl, 4, 0)
        options_grid.addWidget(self.error_splines_entry, 4, 1)

        # Enhance Right Angle
        self.enhance_rangle_cb = FCCheckBox(_("Enhance R Angle"))
        self.enhance_rangle_cb.setToolTip(
            _("Enhance right angle corners.")
        )
        options_grid.addWidget(self.enhance_rangle_cb, 6, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        options_grid.addWidget(separator_line, 8, 0, 1, 2)

        # Noise Reduction
        self.noise_lbl = FCLabel('%s' % _("Noise Reduction"), bold=True)
        options_grid.addWidget(self.noise_lbl, 10, 0, 1, 2)

        # Path Omit
        self.path_omit_lbl = FCLabel('%s' % _("Path Omit"))
        self.path_omit_lbl.setToolTip(
            _("Edge node paths shorter than this will be discarded for noise reduction.")
        )
        self.path_omit_entry = FCSpinner()
        self.path_omit_entry.set_range(0, 9999)
        self.path_omit_entry.setSingleStep(1)

        options_grid.addWidget(self.path_omit_lbl, 12, 0)
        options_grid.addWidget(self.path_omit_entry, 12, 1)

        # Line Filter
        self.line_filter_cb = FCCheckBox(_("Line Filter"))
        options_grid.addWidget(self.line_filter_cb, 14, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        options_grid.addWidget(separator_line, 16, 0, 1, 2)

        # Colors Section
        self.colors_lbl = FCLabel('%s' % _("Colors"), bold=True)
        options_grid.addWidget(self.colors_lbl, 18, 0, 1, 2)

        # Sampling
        self.samp_lbl = FCLabel('%s:' % _('Sampling'))
        self.sampling_combo = FCComboBox2()
        self.sampling_combo.addItems([_("Palette"), _("Random"), _("Deterministic")])
        options_grid.addWidget(self.samp_lbl, 20, 0)
        options_grid.addWidget(self.sampling_combo, 20, 1)

        # Number of colors
        self.nr_colors_lbl = FCLabel('%s' % _("Colors"))
        self.nr_colors_lbl.setToolTip(
            _("Number of colors to use on palette.")
        )
        self.nr_colors_entry = FCSpinner()
        self.nr_colors_entry.set_range(0, 9999)
        self.nr_colors_entry.setSingleStep(1)

        options_grid.addWidget(self.nr_colors_lbl, 22, 0)
        options_grid.addWidget(self.nr_colors_entry, 22, 1)

        # Randomization Ratio
        self.ratio_lbl = FCLabel('%s' % _("Ratio"))
        self.ratio_lbl.setToolTip(
            _("Color quantization will randomize a color if fewer pixels than (total pixels * ratio) has it.")
        )
        self.ratio_entry = FCSpinner()
        self.ratio_entry.set_range(0, 10)
        self.ratio_entry.setSingleStep(1)

        options_grid.addWidget(self.ratio_lbl, 24, 0)
        options_grid.addWidget(self.ratio_entry, 24, 1)

        # Cycles of quantization
        self.cycles_lbl = FCLabel('%s' % _("Cycles"))
        self.cycles_lbl.setToolTip(
            _("Color quantization will be repeated this many times.")
        )
        self.cycles_entry = FCSpinner()
        self.cycles_entry.set_range(0, 20)
        self.cycles_entry.setSingleStep(1)

        options_grid.addWidget(self.cycles_lbl, 26, 0)
        options_grid.addWidget(self.cycles_entry, 26, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        options_grid.addWidget(separator_line, 28, 0, 1, 2)

        # Parameters
        self.par_lbl = FCLabel('%s' % _("Parameters"), bold=True)
        options_grid.addWidget(self.par_lbl, 30, 0, 1, 2)

        # Stroke width
        self.stroke_width_lbl = FCLabel('%s' % _("Stroke"))
        self.stroke_width_lbl.setToolTip(
            _("Width of the stroke to be applied to the shape.")
        )
        self.stroke_width_entry = FCDoubleSpinner()
        self.stroke_width_entry.set_precision(self.decimals)
        self.stroke_width_entry.set_range(0.0000, 9999.0000)
        self.stroke_width_entry.setSingleStep(0.1)

        options_grid.addWidget(self.stroke_width_lbl, 32, 0)
        options_grid.addWidget(self.stroke_width_entry, 32, 1)

        # Rounding
        self.rounding_lbl = FCLabel('%s' % _("Rounding"))
        self.rounding_lbl.setToolTip(
            _("Rounding coordinates to a given decimal place.")
        )
        self.rounding_entry = FCSpinner()
        self.rounding_entry.set_range(0, 10)
        self.rounding_entry.setSingleStep(1)

        options_grid.addWidget(self.rounding_lbl, 34, 0)
        options_grid.addWidget(self.rounding_entry, 34, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        options_grid.addWidget(separator_line, 36, 0, 1, 2)

        # Blur
        self.blur_lbl = FCLabel('%s' % _("Blur"), bold=True)
        options_grid.addWidget(self.blur_lbl, 38, 0, 1, 2)

        # Radius
        self.blur_radius_lbl = FCLabel('%s' % _("Radius"))
        self.blur_radius_lbl.setToolTip(
            _("Selective Gaussian blur preprocessing.")
        )
        self.blur_radius_entry = FCSpinner()
        self.blur_radius_entry.set_range(0, 5)
        self.blur_radius_entry.setSingleStep(1)

        options_grid.addWidget(self.blur_radius_lbl, 40, 0)
        options_grid.addWidget(self.blur_radius_entry, 40, 1)

        # Delta
        self.blur_delta_lbl = FCLabel('%s' % _("Delta"))
        self.blur_delta_lbl.setToolTip(
            _("RGBA delta threshold for selective Gaussian blur preprocessing.")
        )
        self.blur_delta_entry = FCDoubleSpinner()
        self.blur_delta_entry.set_precision(self.decimals)
        self.blur_delta_entry.set_range(0.0000, 9999.0000)
        self.blur_delta_entry.setSingleStep(0.1)

        options_grid.addWidget(self.blur_delta_lbl, 42, 0)
        options_grid.addWidget(self.blur_delta_entry, 42, 1)

        GLay.set_common_column_size([par_grid, mod_grid, raster_grid, trace_grid, preset_grid, options_grid], 0)

        # Buttons
        self.import_button = FCButton(_("Import image"))
        self.import_button.setIcon(QtGui.QIcon(self.app.resource_location + '/image32.png'))
        self.import_button.setToolTip(
            _("Open a image of raster type and then import it in FlatCAM.")
        )
        self.layout.addWidget(self.import_button)

        self.layout.addStretch(1)

        # #################################### FINSIHED GUI ###########################
        # #############################################################################

        # Signals
        self.import_mode_radio.activated_custom.connect(self.on_import_image_mode)
        self.control_radio.activated_custom.connect(self.on_tracing_control_radio)

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

    def on_import_image_mode(self, val):
        if val == 'raster':
            self.raster_frame.show()
            self.trace_frame.hide()
        else:
            self.raster_frame.hide()
            self.trace_frame.show()

    def on_tracing_control_radio(self, val):
        if val == 'presets':
            self.preset_frame.show()
            self.options_frame.hide()
        else:
            self.preset_frame.hide()
            self.options_frame.show()
