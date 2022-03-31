# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 3/10/2019                                          #
# MIT Licence                                              #
# ##########################################################

from appTool import *

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class ToolCalculator(AppTool):

    def __init__(self, app):
        AppTool.__init__(self, app)

        self.app = app
        self.decimals = self.app.decimals

        # #############################################################################
        # ######################### Tool GUI ##########################################
        # #############################################################################
        self.ui = CalcUI(layout=self.layout, app=self.app)
        self.pluginName = self.ui.pluginName

        self.units = ''

    def run(self, toggle=True):
        self.app.defaults.report_usage("ToolCalculators()")

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

        self.app.ui.notebook.setTabText(2, _("Calculators"))

    def connect_signals_at_init(self):
        # ## Signals
        self.ui.mm_entry.editingFinished.connect(self.on_calculate_inch_units)
        self.ui.inch_entry.editingFinished.connect(self.on_calculate_mm_units)
        self.ui.g_entry.editingFinished.connect(self.on_calculate_oz_units)
        self.ui.oz_entry.editingFinished.connect(self.on_calculate_gram_units)
        self.ui.ml_entry.editingFinished.connect(self.on_calculate_floz_units)
        self.ui.fl_oz_entry.editingFinished.connect(self.on_calculate_ml_units)

        self.ui.reset_button.clicked.connect(self.set_tool_ui)
        self.ui.area_sel_radio.activated_custom.connect(self.on_area_calculation_radio)
        self.ui.calculate_tin_button.clicked.connect(lambda: self.on_tin_solution_calculation())
        self.ui.sol_radio.activated_custom.connect(self.on_tin_solution_type)

    def install(self, icon=None, separator=None, **kwargs):
        AppTool.install(self, icon, separator, shortcut='Alt+C', **kwargs)

    def set_tool_ui(self):
        self.units = self.app.app_units.lower()

        self.clear_ui(self.layout)
        self.ui = CalcUI(layout=self.layout, app=self.app)
        self.pluginName = self.ui.pluginName

        self.connect_signals_at_init()

        # ## Initialize form
        # Units Calculator
        self.ui.mm_entry.set_value('%.*f' % (self.decimals, 0))
        self.ui.inch_entry.set_value('%.*f' % (self.decimals, 0))
        self.ui.g_entry.set_value('%.*f' % (self.decimals, 0))
        self.ui.oz_entry.set_value('%.*f' % (self.decimals, 0))
        self.ui.ml_entry.set_value('%.*f' % (self.decimals, 0))
        self.ui.fl_oz_entry.set_value('%.*f' % (self.decimals, 0))

        # Electroplating Calculator
        length = self.app.options["tools_calc_electro_length"]
        width = self.app.options["tools_calc_electro_width"]
        density = self.app.options["tools_calc_electro_cdensity"]
        growth = self.app.options["tools_calc_electro_growth"]

        self.ui.pcblength_entry.set_value(length)
        self.ui.pcbwidth_entry.set_value(width)
        self.ui.area_entry.set_value(self.app.options["tools_calc_electro_area"])
        self.ui.cdensity_entry.set_value(density)
        self.ui.growth_entry.set_value(growth)
        self.ui.cvalue_entry.set_value(0.00)
        self.ui.time_entry.set_value(0.0)

        # V-Shape tool Calculator
        tip_dia = self.app.options["tools_calc_vshape_tip_dia"]
        tip_angle = self.app.options["tools_calc_vshape_tip_angle"]
        cut_z = self.app.options["tools_calc_vshape_cut_z"]

        self.ui.tipDia_entry.set_value(tip_dia)
        self.ui.tipAngle_entry.set_value(tip_angle)
        self.ui.cutDepth_entry.set_value(cut_z)
        self.on_calculate_tool_dia()

        self.ui.area_sel_radio.set_value('d')
        self.on_area_calculation_radio(val='d')

        self.on_calculate_eplate()

        # Tinning Calculator
        self.ui.sol_radio.set_value("sol1")

        self.ui_disconnect()
        self.ui_connect()

    def on_area_calculation_radio(self, val):
        if val == 'a':
            self.ui.pcbwidthlabel.hide()
            self.ui.pcbwidth_entry.hide()
            self.ui.width_unit.hide()

            self.ui.pcblengthlabel.hide()
            self.ui.pcblength_entry.hide()
            self.ui.length_unit.hide()

            self.ui.area_label.show()
            self.ui.area_entry.show()
            self.ui.area_unit.show()
        else:
            self.ui.pcbwidthlabel.show()
            self.ui.pcbwidth_entry.show()
            self.ui.width_unit.show()

            self.ui.pcblengthlabel.show()
            self.ui.pcblength_entry.show()
            self.ui.length_unit.show()

            self.ui.area_label.hide()
            self.ui.area_entry.hide()
            self.ui.area_unit.hide()

    def on_calculate_tool_dia(self):
        self.ui_disconnect()
        # Calculation:
        # Manufacturer gives total angle of the the tip but we need only half of it
        # tangent(half_tip_angle) = opposite side / adjacent = part_of _real_dia / depth_of_cut
        # effective_diameter = tip_diameter + part_of_real_dia_left_side + part_of_real_dia_right_side
        # tool is symmetrical therefore: part_of_real_dia_left_side = part_of_real_dia_right_side
        # effective_diameter = tip_diameter + (2 * part_of_real_dia_left_side)
        # effective diameter = tip_diameter + (2 * depth_of_cut * tangent(half_tip_angle))

        tip_diameter = float(self.ui.tipDia_entry.get_value())

        half_tip_angle = float(self.ui.tipAngle_entry.get_value()) / 2.0

        cut_depth = float(self.ui.cutDepth_entry.get_value())
        cut_depth = -cut_depth if cut_depth < 0 else cut_depth

        tool_diameter = tip_diameter + (2 * cut_depth * math.tan(math.radians(half_tip_angle)))
        self.ui.effectiveToolDia_entry.set_value(self.app.dec_format(tool_diameter, self.decimals))
        self.app.inform.emit('[success] %s' % _("Cut width (tool diameter) calculated."))

        self.ui_connect()

    def on_calculate_cutz(self):
        self.ui_disconnect()
        # Calculation:
        # Manufacturer gives total angle of the the tip but we need only half of it
        # tangent(half_tip_angle) = opposite side / adjacent = part_of _real_dia / depth_of_cut
        # effective_diameter = tip_diameter + part_of_real_dia_left_side + part_of_real_dia_right_side
        # tool is symmetrical therefore: part_of_real_dia_left_side = part_of_real_dia_right_side
        # effective_diameter = tip_diameter + (2 * part_of_real_dia_left_side)
        # effective diameter = tip_diameter + (2 * depth_of_cut * tangent(half_tip_angle))

        tip_diameter = float(self.ui.tipDia_entry.get_value())
        half_tip_angle = float(self.ui.tipAngle_entry.get_value()) / 2.0

        tooldia = self.ui.effectiveToolDia_entry.get_value()

        if tip_diameter > tooldia:
            self.ui.cutDepth_entry.set_value(self.app.dec_format(0.0, self.decimals))
            self.app.inform.emit('[ERROR_NOTCL] %s' %
                                 _("Tool diameter (cut width) cannot be smaller than the tip diameter."))
            self.ui_connect()
            return

        cut_depth = (tooldia - tip_diameter) / (2 * math.tan(math.radians(half_tip_angle))) * -1
        self.ui.cutDepth_entry.set_value(self.app.dec_format(cut_depth, self.decimals))
        self.app.inform.emit('[success] %s' % _("Cut depth (Cut Z) calculated."))

        self.ui_connect()

    def on_calculate_inch_units(self):
        # Length units
        mm_val = float(self.ui.mm_entry.get_value())
        self.ui.inch_entry.set_value('%.*f' % (self.decimals, (mm_val / 25.4)))

    def on_calculate_mm_units(self):
        # Length units
        inch_val = float(self.ui.inch_entry.get_value())
        self.ui.mm_entry.set_value('%.*f' % (self.decimals, (inch_val * 25.4)))

    def on_calculate_oz_units(self):
        # Weight units
        gram_val = float(self.ui.g_entry.get_value())
        self.ui.oz_entry.set_value('%.*f' % (self.decimals, (gram_val / 28.3495)))

    def on_calculate_gram_units(self):
        # Weight units
        oz_val = float(self.ui.oz_entry.get_value())
        self.ui.g_entry.set_value('%.*f' % (self.decimals, (oz_val * 28.3495)))

    def on_calculate_floz_units(self):
        # Liquid weight units
        ml_val = float(self.ui.ml_entry.get_value())
        self.ui.fl_oz_entry.set_value('%.*f' % (self.decimals, (ml_val / 29.5735296875)))

    def on_calculate_ml_units(self):
        # Liquid weight units
        floz_val = float(self.ui.fl_oz_entry.get_value())
        self.ui.ml_entry.set_value('%.*f' % (self.decimals, (floz_val * 29.5735296875)))

    def on_calculate_current(self):
        """

        :return:
        """

        '''
        Example: If you are plating a 12" by 9", double-sided board, with a current density of 20 ASF, you will need:
        [(12" x 9" x 2 sides)/144] x 20 = 30 Amps = C
        In Metric, for a 10cm by 10cm, double sided board, with a current density of 20 ASF, you will need:
        [(10cm x 10cm x 2 sides]/929.0304359661127] x 20 =~ 4.3 Amps = C
        or written differently:
        [(10cm x 10cm x 2 sides] * 0.001076391] x 20 =~ 4.3 Amps = C
        or:
        (10cm x 10cm) * 0.0021527820833419] x 20 =~ 4.3 Amps = C
        '''
        self.ui_disconnect()
        area_calc_sel = self.ui.area_sel_radio.get_value()
        length = self.ui.pcblength_entry.get_value()
        width = self.ui.pcbwidth_entry.get_value()
        area = self.ui.area_entry.get_value()

        density = self.ui.cdensity_entry.get_value()

        if area_calc_sel == 'd':
            calculated_current = (length * width * density) * 0.0021527820833419
        else:
            calculated_current = (area * density) * 0.0021527820833419

        self.ui.cvalue_entry.set_value('%.2f' % calculated_current)
        self.ui_connect()

    def on_calculate_time(self):
        """

        :return:
        """

        '''
        Calculated time for a copper growth of 10 microns is:
        [10um / (28um/hr)] x 60 min/hr = 21.42 minutes = TC (at 20ASF)
        or:
        10 um * 2.142857142857143 min/um = 21.42 minutes = TC (at 20ASF)
        or:
        10 * 2.142857142857143 min * (20/new_density) = 21.42 minutes = TC 
        (with new_density = 20ASF amd copper groth of 10 um)
        '''
        self.ui_disconnect()

        density = self.ui.cdensity_entry.get_value()
        growth = self.ui.growth_entry.get_value()

        try:
            calculated_time = growth * 2.142857142857143 * float(20 / density)
        except ZeroDivisionError:
            calculated_time = 0.0

        self.ui.time_entry.set_value('%.1f' % calculated_time)
        self.ui_connect()

    def on_calculate_eplate(self):
        self.on_calculate_time()
        self.on_calculate_current()
        self.app.inform.emit('[success] %s' % _("Done."))

    def on_calculate_growth(self):
        self.ui_disconnect()
        density = self.ui.cdensity_entry.get_value()
        g_time = self.ui.time_entry.get_value()

        growth = g_time / (2.142857142857143 * float(20 / density))

        self.ui.growth_entry.set_value(self.app.dec_format(growth, self.decimals))
        self.app.inform.emit('[success] %s' % _("Done."))

        self.ui_connect()

    def on_tin_solution_type(self, val):
        if val == 'sol1':
            sncl2_val = 0.5
            thiourea_val = 2.0
            sulfamic_acid_val = 3.0
            water_val = 100.0
            soap_val = 0.1
            hypo_val = 1.5
        else:
            sncl2_val = 2.0
            thiourea_val = 7.5
            sulfamic_acid_val = 9.0
            water_val = 100.0
            soap_val = 0.1
            hypo_val = 1.5

        desired_vol = 100

        self.ui.sn_cl_entry.set_value(sncl2_val)
        self.ui.th_entry.set_value(thiourea_val)
        self.ui.sa_entry.set_value(sulfamic_acid_val)
        self.ui.h2o_entry.set_value(water_val)
        self.ui.soap_entry.set_value(soap_val)
        self.ui.hypo_entry.set_value(hypo_val)
        self.ui.vol_entry.set_value(desired_vol)

    def on_tin_solution_calculation(self):
        solution_type = self.ui.sol_radio.get_value()
        desired_volume = self.ui.vol_entry.get_value()  # milliliters

        if solution_type == 'sol1':
            sncl2_val = 0.005
            thiourea_val = 0.02
            sulfamic_acid_val = 0.03
            water_val = 1
            soap_val = 0.001
            hypo_val = 0.015
        else:
            sncl2_val = 0.02
            thiourea_val = 0.075
            sulfamic_acid_val = 0.09
            water_val = 1
            soap_val = 0.001
            hypo_val = 0.015

        self.ui.sn_cl_entry.set_value(sncl2_val * desired_volume)
        self.ui.th_entry.set_value(thiourea_val * desired_volume)
        self.ui.sa_entry.set_value(sulfamic_acid_val * desired_volume)
        self.ui.h2o_entry.set_value(water_val * desired_volume)
        self.ui.soap_entry.set_value(soap_val * desired_volume)
        self.ui.hypo_entry.set_value(hypo_val * desired_volume)

    def ui_connect(self):
        # V-Shape Calculator
        self.ui.cutDepth_entry.valueChanged.connect(self.on_calculate_tool_dia)
        self.ui.cutDepth_entry.returnPressed.connect(self.on_calculate_tool_dia)

        self.ui.effectiveToolDia_entry.valueChanged.connect(self.on_calculate_cutz)
        self.ui.effectiveToolDia_entry.returnPressed.connect(self.on_calculate_cutz)

        self.ui.tipDia_entry.returnPressed.connect(self.on_calculate_tool_dia)
        self.ui.tipAngle_entry.returnPressed.connect(self.on_calculate_tool_dia)

        self.ui.calculate_vshape_button.clicked.connect(self.on_calculate_tool_dia)

        # Electroplating Calculator
        self.ui.cdensity_entry.valueChanged.connect(self.on_calculate_eplate)
        self.ui.cdensity_entry.returnPressed.connect(self.on_calculate_eplate)

        self.ui.growth_entry.valueChanged.connect(self.on_calculate_time)
        self.ui.growth_entry.returnPressed.connect(self.on_calculate_time)

        self.ui.area_entry.valueChanged.connect(self.on_calculate_current)
        self.ui.area_entry.returnPressed.connect(self.on_calculate_current)

        self.ui.time_entry.valueChanged.connect(self.on_calculate_growth)
        self.ui.time_entry.returnPressed.connect(self.on_calculate_growth)

        self.ui.calculate_plate_button.clicked.connect(self.on_calculate_eplate)

    def ui_disconnect(self):
        # V-Shape Calculator
        try:
            self.ui.cutDepth_entry.valueChanged.disconnect()
        except (AttributeError, TypeError):
            pass
        try:
            self.ui.cutDepth_entry.returnPressed.disconnect()
        except (AttributeError, TypeError):
            pass
        # ##
        try:
            self.ui.effectiveToolDia_entry.valueChanged.disconnect()
        except (AttributeError, TypeError):
            pass
        try:
            self.ui.effectiveToolDia_entry.returnPressed.disconnect()
        except (AttributeError, TypeError):
            pass
        # ###

        try:
            self.ui.tipDia_entry.returnPressed.disconnect()
        except (AttributeError, TypeError):
            pass
        try:
            self.ui.tipAngle_entry.returnPressed.disconnect()
        except (AttributeError, TypeError):
            pass
        try:
            self.ui.calculate_vshape_button.clicked.disconnect()
        except (AttributeError, TypeError):
            pass

        # Electroplating Calculator
        # Density
        try:
            self.ui.cdensity_entry.valueChanged.disconnect()
        except (AttributeError, TypeError):
            pass
        try:
            self.ui.cdensity_entry.returnPressed.disconnect()
        except (AttributeError, TypeError):
            pass
        # Growth
        try:
            self.ui.growth_entry.valueChanged.disconnect()
        except (AttributeError, TypeError):
            pass
        try:
            self.ui.growth_entry.returnPressed.disconnect()
        except (AttributeError, TypeError):
            pass
        # Area
        try:
            self.ui.area_entry.valueChanged.disconnect()
        except (AttributeError, TypeError):
            pass
        try:
            self.ui.area_entry.returnPressed.disconnect()
        except (AttributeError, TypeError):
            pass
        # Time
        try:
            self.ui.time_entry.valueChanged.disconnect()
        except (AttributeError, TypeError):
            pass
        try:
            self.ui.time_entry.returnPressed.disconnect()
        except (AttributeError, TypeError):
            pass
        # Calculate
        try:
            self.ui.calculate_plate_button.clicked.disconnect()
        except (AttributeError, TypeError):
            pass


class CalcUI:

    pluginName = _("Calculators")
    v_shapeName = _("V-Shape Tool")
    unitsName = _("Units Conversion")
    eplateName = _("ElectroPlating")
    tinningName = _("Tinning")

    def __init__(self, layout, app):
        self.app = app
        self.decimals = self.app.decimals
        self.layout = layout
        self.units = self.app.app_units.lower()

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

        # #####################
        # ## Units Calculator #
        # #####################

        # ## Title of the Units Calculator
        units_label = FCLabel('<span style="color:blue;"><b>%s</b></span>' % self.unitsName)
        self.layout.addWidget(units_label)

        units_frame = FCFrame()
        self.layout.addWidget(units_frame)

        # #############################################################################################################
        # Units Calculators
        # #############################################################################################################
        # Grid Layout
        grid_units_layout = FCGridLayout(v_spacing=5, h_spacing=3)
        units_frame.setLayout(grid_units_layout)

        # Length conversion
        inch_label = FCLabel(_("inch"))
        mm_label = FCLabel(_("mm"))
        grid_units_layout.addWidget(mm_label, 0, 0)
        grid_units_layout.addWidget(inch_label, 0, 1)

        self.inch_entry = NumericalEvalEntry(border_color='#0069A9')
        self.inch_entry.setToolTip(_("Here you enter the value to be converted from imperial to metric"))

        self.mm_entry = NumericalEvalEntry(border_color='#0069A9')
        self.mm_entry.setToolTip(_("Here you enter the value to be converted from metric to imperial"))

        grid_units_layout.addWidget(self.mm_entry, 2, 0)
        grid_units_layout.addWidget(self.inch_entry, 2, 1)

        # Weight conversion
        oz_label = FCLabel(_("oz"))
        gram_label = FCLabel(_("gram"))
        grid_units_layout.addWidget(gram_label, 4, 0)
        grid_units_layout.addWidget(oz_label, 4, 1)

        self.oz_entry = NumericalEvalEntry(border_color='#0069A9')
        self.oz_entry.setToolTip(_("Here you enter the value to be converted from imperial to metric"))

        self.g_entry = NumericalEvalEntry(border_color='#0069A9')
        self.g_entry.setToolTip(_("Here you enter the value to be converted from metric to imperial"))

        grid_units_layout.addWidget(self.g_entry, 6, 0)
        grid_units_layout.addWidget(self.oz_entry, 6, 1)

        # Liquid weight conversion
        fl_oz_label = FCLabel(_("fl oz"))
        ml_label = FCLabel(_("mL"))
        grid_units_layout.addWidget(ml_label, 8, 0)
        grid_units_layout.addWidget(fl_oz_label, 8, 1)

        self.fl_oz_entry = NumericalEvalEntry(border_color='#0069A9')
        self.fl_oz_entry.setToolTip(_("Here you enter the value to be converted from imperial to metric"))

        self.ml_entry = NumericalEvalEntry(border_color='#0069A9')
        self.ml_entry.setToolTip(_("Here you enter the value to be converted from metric to imperial"))

        grid_units_layout.addWidget(self.ml_entry, 10, 0)
        grid_units_layout.addWidget(self.fl_oz_entry, 10, 1)

        # #############################################################################################################
        # ################################ V-shape Tool Calculator ####################################################
        # #############################################################################################################
        # ## Title of the V-shape Tools Calculator
        v_shape_title_label = FCLabel('<span style="color:green;"><b>%s</b></span>' % self.v_shapeName)
        self.layout.addWidget(v_shape_title_label)

        v_frame = FCFrame()
        self.layout.addWidget(v_frame)

        grid_vshape = FCGridLayout(v_spacing=5, h_spacing=3)
        v_frame.setLayout(grid_vshape)

        # self.v_shape_spacer_label = FCLabel(" ")
        # grid_vshape.addWidget(self.v_shape_spacer_label, 0, 0, 1, 2)

        # Tip Diameter
        self.tipDia_label = FCLabel('%s:' % _("Tip Diameter"))
        self.tipDia_label.setToolTip(
            _("This is the tool tip diameter.\n"
              "It is specified by manufacturer.")
        )

        self.tipDia_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.tipDia_entry.set_precision(self.decimals)
        self.tipDia_entry.set_range(0.0, 10000.0000)
        self.tipDia_entry.setSingleStep(0.1)

        grid_vshape.addWidget(self.tipDia_label, 4, 0)
        grid_vshape.addWidget(self.tipDia_entry, 4, 1)

        # Tip Angle
        self.tipAngle_label = FCLabel('%s:' % _("Tip Angle"))
        self.tipAngle_label.setToolTip(_("This is the angle of the tip of the tool.\n"
                                         "It is specified by manufacturer."))

        self.tipAngle_entry = FCSpinner(callback=self.confirmation_message_int)
        self.tipAngle_entry.set_range(0, 180)
        self.tipAngle_entry.set_step(5)

        grid_vshape.addWidget(self.tipAngle_label, 6, 0)
        grid_vshape.addWidget(self.tipAngle_entry, 6, 1)

        # Cut Z
        self.cutDepth_label = FCLabel('%s:' % _("Cut Z"))
        self.cutDepth_label.setToolTip(_("This is the depth to cut into the material."))

        self.cutDepth_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.cutDepth_entry.set_range(-10000.0000, 10000.0000)
        self.cutDepth_entry.set_precision(self.decimals)

        grid_vshape.addWidget(self.cutDepth_label, 8, 0)
        grid_vshape.addWidget(self.cutDepth_entry, 8, 1)

        # Tool Diameter
        self.effectiveToolDia_label = FCLabel('%s:' % _("Tool Diameter"))
        self.effectiveToolDia_label.setToolTip(_("This is the actual tool diameter\n"
                                                 "at the desired depth of cut."))
        self.effectiveToolDia_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.effectiveToolDia_entry.set_precision(self.decimals)

        grid_vshape.addWidget(self.effectiveToolDia_label, 10, 0)
        grid_vshape.addWidget(self.effectiveToolDia_entry, 10, 1)

        # ## Buttons
        self.calculate_vshape_button = FCButton(_("Calculate"))
        self.calculate_vshape_button.setIcon(QtGui.QIcon(self.app.resource_location + '/calculator16.png'))

        self.calculate_vshape_button.setToolTip(
            _("Calculate either the depth of cut or the effective tool diameter.")
        )

        grid_vshape.addWidget(self.calculate_vshape_button, 12, 0, 1, 2)

        # #############################################################################################################
        # ############################## ElectroPlating Tool Calculator ###############################################
        # #############################################################################################################
        # ## Title of the ElectroPlating Tools Calculator
        tin_title_label = FCLabel('<span style="color:purple;"><b>%s</b></span>' % self.eplateName)
        tin_title_label.setToolTip(
            _("This calculator is useful for those who plate the via/pad/drill holes,\n"
              "using a method like graphite ink or calcium hypophosphite ink or palladium chloride.")
        )
        self.layout.addWidget(tin_title_label)

        ep_frame = FCFrame()
        self.layout.addWidget(ep_frame)

        grid_electro = FCGridLayout(v_spacing=5, h_spacing=3)
        ep_frame.setLayout(grid_electro)

        # grid_electro.addWidget(FCLabel(""), 0, 0, 1, 2)

        # Area Calculation
        self.area_sel_label = FCLabel('%s:' % _("Area Calculation"))
        self.area_sel_label.setToolTip(
            _("Determine the board area.")
        )
        self.area_sel_radio = RadioSet([
            {'label': _('Dimensions'), 'value': 'd'},
            {"label": _("Area"), "value": "a"}
        ], compact=True)

        grid_electro.addWidget(self.area_sel_label, 4, 0)
        grid_electro.addWidget(self.area_sel_radio, 6, 0, 1, 2)

        # BOARD LENGTH
        self.pcblengthlabel = FCLabel('%s:' % _("Board Length"))
        self.pcblengthlabel.setToolTip(_('Board Length.'))
        self.pcblength_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.pcblength_entry.setSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding,
                                           QtWidgets.QSizePolicy.Policy.Preferred)
        self.pcblength_entry.set_precision(self.decimals)
        self.pcblength_entry.set_range(0.0, 10000.0000)

        self.length_unit = FCLabel('%s' % _("cm"))
        self.length_unit.setMinimumWidth(25)

        l_hlay = QtWidgets.QHBoxLayout()
        l_hlay.addWidget(self.pcblength_entry)
        l_hlay.addWidget(self.length_unit)

        grid_electro.addWidget(self.pcblengthlabel, 8, 0)
        grid_electro.addLayout(l_hlay, 8, 1)

        # BOARD WIDTH
        self.pcbwidthlabel = FCLabel('%s:' % _("Board Width"))
        self.pcbwidthlabel.setToolTip(_('Board Width'))
        self.pcbwidth_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.pcbwidth_entry.setSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding,
                                          QtWidgets.QSizePolicy.Policy.Preferred)
        self.pcbwidth_entry.set_precision(self.decimals)
        self.pcbwidth_entry.set_range(0.0, 10000.0000)

        self.width_unit = FCLabel('%s' % _("cm"))
        self.width_unit.setMinimumWidth(25)

        w_hlay = QtWidgets.QHBoxLayout()
        w_hlay.addWidget(self.pcbwidth_entry)
        w_hlay.addWidget(self.width_unit)

        grid_electro.addWidget(self.pcbwidthlabel, 10, 0)
        grid_electro.addLayout(w_hlay, 10, 1)

        # AREA
        self.area_label = FCLabel('%s:' % _("Area"))
        self.area_label.setToolTip(_('Board area.'))
        self.area_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.area_entry.setSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding,
                                      QtWidgets.QSizePolicy.Policy.Preferred)
        self.area_entry.set_precision(self.decimals)
        self.area_entry.set_range(0.0, 10000.0000)

        self.area_unit = FCLabel('%s<sup>2</sup>' % _("cm"))
        self.area_unit.setMinimumWidth(25)

        a_hlay = QtWidgets.QHBoxLayout()
        a_hlay.addWidget(self.area_entry)
        a_hlay.addWidget(self.area_unit)

        grid_electro.addWidget(self.area_label, 12, 0)
        grid_electro.addLayout(a_hlay, 12, 1)

        self.separator_line = QtWidgets.QFrame()
        self.separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        grid_electro.addWidget(self.separator_line, 14, 0, 1, 2)

        # DENSITY
        self.cdensity_label = FCLabel('%s:' % _("Current Density"))
        self.cdensity_label.setToolTip(_("Current density applied to the board. \n"
                                         "In Amperes per Square Feet ASF."))
        self.cdensity_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.cdensity_entry.setSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding,
                                          QtWidgets.QSizePolicy.Policy.Preferred)
        self.cdensity_entry.set_precision(self.decimals)
        self.cdensity_entry.set_range(0.0, 10000.0000)
        self.cdensity_entry.setSingleStep(0.1)

        density_unit = FCLabel('%s' % "ASF")
        density_unit.setMinimumWidth(25)

        d_hlay = QtWidgets.QHBoxLayout()
        d_hlay.addWidget(self.cdensity_entry)
        d_hlay.addWidget(density_unit)

        grid_electro.addWidget(self.cdensity_label, 16, 0)
        grid_electro.addLayout(d_hlay, 16, 1)

        # COPPER GROWTH
        self.growth_label = FCLabel('%s:' % _("Copper Growth"))
        self.growth_label.setToolTip(_("Thickness of the deposited copper."))
        self.growth_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.growth_entry.setSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding,
                                        QtWidgets.QSizePolicy.Policy.Preferred)
        self.growth_entry.set_precision(self.decimals)
        self.growth_entry.set_range(0.0, 10000.0000)
        self.growth_entry.setSingleStep(0.01)

        growth_unit = FCLabel('%s' % _("um"))
        growth_unit.setMinimumWidth(25)

        g_hlay = QtWidgets.QHBoxLayout()
        g_hlay.addWidget(self.growth_entry)
        g_hlay.addWidget(growth_unit)

        grid_electro.addWidget(self.growth_label, 18, 0)
        grid_electro.addLayout(g_hlay, 18, 1)

        # CURRENT
        self.cvaluelabel = FCLabel('%s:' % _("Current Value"))
        self.cvaluelabel.setToolTip(_('This is the current intensity value\n'
                                      'to be set on the Power Supply.'))
        self.cvalue_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.cvalue_entry.setSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding,
                                        QtWidgets.QSizePolicy.Policy.Preferred)
        self.cvalue_entry.set_precision(self.decimals)
        self.cvalue_entry.set_range(0.0, 10000.0000)
        self.cvalue_entry.setSingleStep(0.1)

        current_unit = FCLabel('%s' % "A")
        current_unit.setMinimumWidth(25)
        self.cvalue_entry.setReadOnly(True)

        c_hlay = QtWidgets.QHBoxLayout()
        c_hlay.addWidget(self.cvalue_entry)
        c_hlay.addWidget(current_unit)

        grid_electro.addWidget(self.cvaluelabel, 20, 0)
        grid_electro.addLayout(c_hlay, 20, 1)

        # TIME
        self.timelabel = FCLabel('%s:' % _("Time"))
        self.timelabel.setToolTip(_('The time calculated to deposit copper.'))
        self.time_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.time_entry.setSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding,
                                      QtWidgets.QSizePolicy.Policy.Preferred)
        self.time_entry.set_precision(self.decimals)
        self.time_entry.set_range(0.0, 10000.0000)
        self.time_entry.setSingleStep(0.1)

        time_unit = FCLabel('%s' % "min")
        time_unit.setMinimumWidth(25)
        # self.time_entry.setReadOnly(True)

        t_hlay = QtWidgets.QHBoxLayout()
        t_hlay.addWidget(self.time_entry)
        t_hlay.addWidget(time_unit)

        grid_electro.addWidget(self.timelabel, 22, 0)
        grid_electro.addLayout(t_hlay, 22, 1)

        # ## Buttons
        self.calculate_plate_button = FCButton(_("Calculate"))
        self.calculate_plate_button.setIcon(QtGui.QIcon(self.app.resource_location + '/calculator16.png'))
        self.calculate_plate_button.setToolTip(
            _("Calculate the current intensity value and the procedure time.")
        )
        grid_electro.addWidget(self.calculate_plate_button, 24, 0, 1, 2)

        # #############################################################################################################
        # ############################## Tinning Calculator ###############################################
        # #############################################################################################################
        # ## Title of the Tinning Calculator
        tin_title_label = FCLabel('<span style="color:orange;"><b>%s</b></span>' % self.tinningName)
        tin_title_label.setToolTip(
            _("Calculator for chemical quantities\n"
              "required for tinning PCB's.")
        )
        self.layout.addWidget(tin_title_label)

        tin_frame = FCFrame()
        self.layout.addWidget(tin_frame)

        grid_tin = FCGridLayout(v_spacing=5, h_spacing=3)
        tin_frame.setLayout(grid_tin)

        # Solution
        self.solution_lbl = FCLabel('%s:' % _("Solution"))
        self.solution_lbl.setToolTip(
            _("Choose one solution for tinning.")
        )
        self.sol_radio = RadioSet([
            {'label': '1', 'value': 'sol1'},
            {"label": '2', "value": "sol2"}
        ], compact=True)

        grid_tin.addWidget(self.solution_lbl, 4, 0)
        grid_tin.addWidget(self.sol_radio, 4, 1)

        # Stannous Chloride
        self.sn_cl_lbl = FCLabel('%s :' % "SnCl<sub>2</sub>")
        self.sn_cl_lbl.setToolTip(_('Stannous Chloride.'))
        self.sn_cl_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.sn_cl_entry.setSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding,
                                       QtWidgets.QSizePolicy.Policy.Preferred)
        self.sn_cl_entry.lineEdit().setReadOnly(True)
        self.sn_cl_entry.set_precision(self.decimals)
        self.sn_cl_entry.set_range(0.0, 10000.0000)

        self.sncl_unit = FCLabel('%s' % _("g"))
        self.sncl_unit.setMinimumWidth(25)

        sncl_hlay = QtWidgets.QHBoxLayout()
        sncl_hlay.addWidget(self.sn_cl_entry)
        sncl_hlay.addWidget(self.sncl_unit)

        grid_tin.addWidget(self.sn_cl_lbl, 8, 0)
        grid_tin.addLayout(sncl_hlay, 8, 1)

        # Thiourea
        self.th_label = FCLabel('%s:' % _("Thiourea"))
        self.th_label.setToolTip('%s.' % _('Thiourea'))
        self.th_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.th_entry.setSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding,
                                    QtWidgets.QSizePolicy.Policy.Preferred)
        self.th_entry.lineEdit().setReadOnly(True)
        self.th_entry.set_precision(self.decimals)
        self.th_entry.set_range(0.0, 10000.0000)

        self.th_unit = FCLabel('%s' % _("g"))
        self.th_unit.setMinimumWidth(25)

        th_hlay = QtWidgets.QHBoxLayout()
        th_hlay.addWidget(self.th_entry)
        th_hlay.addWidget(self.th_unit)

        grid_tin.addWidget(self.th_label, 12, 0)
        grid_tin.addLayout(th_hlay, 12, 1)

        # Sulfamic Acid
        self.sa_label = FCLabel('%s :' % "H<sub>3</sub>NSO<sub>3</sub>")
        self.sa_label.setToolTip(_('Sulfamic Acid.'))
        self.sa_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.sa_entry.setSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding,
                                    QtWidgets.QSizePolicy.Policy.Preferred)
        self.sa_entry.lineEdit().setReadOnly(True)
        self.sa_entry.set_precision(self.decimals)
        self.sa_entry.set_range(0.0, 10000.0000)

        self.sa_unit = FCLabel('%s' % _("g"))
        self.sa_unit.setMinimumWidth(25)

        sa_hlay = QtWidgets.QHBoxLayout()
        sa_hlay.addWidget(self.sa_entry)
        sa_hlay.addWidget(self.sa_unit)

        grid_tin.addWidget(self.sa_label, 14, 0)
        grid_tin.addLayout(sa_hlay, 14, 1)

        # Water
        self.h2o_label = FCLabel("H<sub>2</sub>O :")
        self.h2o_label.setToolTip(_('Distilled Water.'))
        self.h2o_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.h2o_entry.setSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding,
                                     QtWidgets.QSizePolicy.Policy.Preferred)
        self.h2o_entry.lineEdit().setReadOnly(True)
        self.h2o_entry.set_precision(self.decimals)
        self.h2o_entry.set_range(0.0, 10000.0000)

        self.h20_unit = FCLabel('%s' % _("mL"))
        self.h20_unit.setMinimumWidth(25)

        h2o_hlay = QtWidgets.QHBoxLayout()
        h2o_hlay.addWidget(self.h2o_entry)
        h2o_hlay.addWidget(self.h20_unit)

        grid_tin.addWidget(self.h2o_label, 16, 0)
        grid_tin.addLayout(h2o_hlay, 16, 1)

        # Soap
        self.soap_label = FCLabel('%s:' % _("Soap"))
        self.soap_label.setToolTip(_('Liquid soap.'))
        self.soap_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.soap_entry.setSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding,
                                      QtWidgets.QSizePolicy.Policy.Preferred)
        self.soap_entry.lineEdit().setReadOnly(True)
        self.soap_entry.set_precision(self.decimals)
        self.soap_entry.set_range(0.0, 10000.0000)

        self.soap_unit = FCLabel('%s' % _("mL"))
        self.soap_unit.setMinimumWidth(25)

        soap_hlay = QtWidgets.QHBoxLayout()
        soap_hlay.addWidget(self.soap_entry)
        soap_hlay.addWidget(self.soap_unit)

        grid_tin.addWidget(self.soap_label, 18, 0)
        grid_tin.addLayout(soap_hlay, 18, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        grid_tin.addWidget(separator_line, 20, 0, 1, 2)

        self.tin_opt_label = FCLabel('%s:' % _("Optional"))
        grid_tin.addWidget(self.tin_opt_label, 22, 0)

        # Sodium hypophosphite
        self.hypo_label = FCLabel("NaPO<sub>2</sub>H<sub>2</sub> :")
        self.hypo_label.setToolTip(
            _('Sodium hypophosphite.\n'
              'Optional, for solution stability.\n'
              'Warning: List 1 chemical in USA.'))
        self.hypo_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.hypo_entry.setSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding,
                                      QtWidgets.QSizePolicy.Policy.Preferred)
        self.hypo_entry.lineEdit().setReadOnly(True)
        self.hypo_entry.set_precision(self.decimals)
        self.hypo_entry.set_range(0.0, 10000.0000)

        self.hypo_unit = FCLabel('%s' % _("g"))
        self.hypo_unit.setMinimumWidth(25)

        hypo_hlay = QtWidgets.QHBoxLayout()
        hypo_hlay.addWidget(self.hypo_entry)
        hypo_hlay.addWidget(self.hypo_unit)

        grid_tin.addWidget(self.hypo_label, 24, 0)
        grid_tin.addLayout(hypo_hlay, 24, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        grid_tin.addWidget(separator_line, 26, 0, 1, 2)

        # Volume
        self.vol_lbl = FCLabel('<span style="color:red;">%s:</span>' % _("Volume"))
        self.vol_lbl.setToolTip(_('Desired volume of tinning solution.'))
        self.vol_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.vol_entry.setSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding,
                                     QtWidgets.QSizePolicy.Policy.Preferred)
        self.vol_entry.set_precision(self.decimals)
        self.vol_entry.set_range(0.0, 10000.0000)

        self.vol_unit = FCLabel('%s' % _("mL"))
        self.vol_unit.setMinimumWidth(25)

        vol_hlay = QtWidgets.QHBoxLayout()
        vol_hlay.addWidget(self.vol_entry)
        vol_hlay.addWidget(self.vol_unit)

        grid_tin.addWidget(self.vol_lbl, 28, 0)
        grid_tin.addLayout(vol_hlay, 28, 1)

        # ## Buttons
        self.calculate_tin_button = FCButton(_("Calculate"))
        self.calculate_tin_button.setIcon(QtGui.QIcon(self.app.resource_location + '/calculator16.png'))
        self.calculate_tin_button.setToolTip(
            _("Calculate the chemical quantities for the desired volume of tinning solution.")
        )
        grid_tin.addWidget(self.calculate_tin_button, 30, 0, 1, 2)

        FCGridLayout.set_common_column_size([grid_units_layout, grid_electro, grid_vshape, grid_tin], 0)

        self.layout.addStretch(1)

        # ## Reset Tool
        self.reset_button = FCButton(_("Reset Tool"))
        self.reset_button.setIcon(QtGui.QIcon(self.app.resource_location + '/reset32.png'))
        self.reset_button.setToolTip(
            _("Will reset the tool parameters.")
        )
        self.reset_button.setStyleSheet("""
                                QPushButton
                                {
                                    font-weight: bold;
                                }
                                """)
        self.layout.addWidget(self.reset_button)

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
