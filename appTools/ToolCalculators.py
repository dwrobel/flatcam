# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 3/10/2019                                          #
# MIT Licence                                              #
# ##########################################################

from PyQt5 import QtWidgets, QtGui
from appTool import AppTool
from appGUI.GUIElements import FCSpinner, FCDoubleSpinner, NumericalEvalEntry, FCLabel, RadioSet, FCButton
import math

import gettext
import appTranslation as fcTranslate
import builtins

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
        self.toolName = self.ui.toolName

        self.units = ''

        # ## Signals
        self.ui.mm_entry.editingFinished.connect(self.on_calculate_inch_units)
        self.ui.inch_entry.editingFinished.connect(self.on_calculate_mm_units)

        self.ui.reset_button.clicked.connect(self.set_tool_ui)

        self.ui.area_sel_radio.activated_custom.connect(self.on_area_calculation_radio)

    def run(self, toggle=True):
        self.app.defaults.report_usage("ToolCalculators()")

        if toggle:
            # if the splitter is hidden, display it
            if self.app.ui.splitter.sizes()[0] == 0:
                self.app.ui.splitter.setSizes([1, 1])

            # if the Tool Tab is hidden display it, else hide it but only if the objectName is the same
            found_idx = None
            for idx in range(self.app.ui.notebook.count()):
                if self.app.ui.notebook.widget(idx).objectName() == "tool_tab":
                    found_idx = idx
                    break
            # show the Tab
            if not found_idx:
                self.app.ui.notebook.addTab(self.app.ui.tool_tab, _("Tool"))
                # focus on Tool Tab
                self.app.ui.notebook.setCurrentWidget(self.app.ui.tool_tab)

            try:
                if self.app.ui.tool_scroll_area.widget().objectName() == self.toolName and found_idx:
                    # if the Tool Tab is not focused, focus on it
                    if not self.app.ui.notebook.currentWidget() is self.app.ui.tool_tab:
                        # focus on Tool Tab
                        self.app.ui.notebook.setCurrentWidget(self.app.ui.tool_tab)
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

        self.app.ui.notebook.setTabText(2, _("Calc. Tool"))

    def install(self, icon=None, separator=None, **kwargs):
        AppTool.install(self, icon, separator, shortcut='Alt+C', **kwargs)

    def set_tool_ui(self):
        self.units = self.app.defaults['units'].lower()

        # ## Initialize form
        self.ui.mm_entry.set_value('%.*f' % (self.decimals, 0))
        self.ui.inch_entry.set_value('%.*f' % (self.decimals, 0))

        length = self.app.defaults["tools_calc_electro_length"]
        width = self.app.defaults["tools_calc_electro_width"]
        density = self.app.defaults["tools_calc_electro_cdensity"]
        growth = self.app.defaults["tools_calc_electro_growth"]

        self.ui.pcblength_entry.set_value(length)
        self.ui.pcbwidth_entry.set_value(width)
        self.ui.area_entry.set_value(self.app.defaults["tools_calc_electro_area"])
        self.ui.cdensity_entry.set_value(density)
        self.ui.growth_entry.set_value(growth)
        self.ui.cvalue_entry.set_value(0.00)
        self.ui.time_entry.set_value(0.0)

        tip_dia = self.app.defaults["tools_calc_vshape_tip_dia"]
        tip_angle = self.app.defaults["tools_calc_vshape_tip_angle"]
        cut_z = self.app.defaults["tools_calc_vshape_cut_z"]

        self.ui.tipDia_entry.set_value(tip_dia)
        self.ui.tipAngle_entry.set_value(tip_angle)
        self.ui.cutDepth_entry.set_value(cut_z)
        self.on_calculate_tool_dia()

        self.ui.area_sel_radio.set_value('d')
        self.on_area_calculation_radio(val='d')

        self.on_calculate_eplate()

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
        mm_val = float(self.ui.mm_entry.get_value())
        self.ui.inch_entry.set_value('%.*f' % (self.decimals, (mm_val / 25.4)))

    def on_calculate_mm_units(self):
        inch_val = float(self.ui.inch_entry.get_value())
        self.ui.mm_entry.set_value('%.*f' % (self.decimals, (inch_val * 25.4)))

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

        calculated_time = growth * 2.142857142857143 * float(20 / density)

        self.ui.time_entry.set_value('%.1f' % calculated_time)
        self.ui_connect()

    def on_calculate_eplate(self):
        self.on_calculate_time()
        self.on_calculate_current()
        self.app.inform.emit('[success] %s' % _("Done."))

    def on_calculate_growth(self):
        self.ui_disconnect()
        density = self.ui.cdensity_entry.get_value()
        time = self.ui.time_entry.get_value()

        growth = time / (2.142857142857143 * float(20 / density))

        self.ui.growth_entry.set_value(self.app.dec_format(growth, self.decimals))
        self.app.inform.emit('[success] %s' % _("Done."))

        self.ui_connect()

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

    toolName = _("Calculators")
    v_shapeName = _("V-Shape Tool Calculator")
    unitsName = _("Units Calculator")
    eplateName = _("ElectroPlating Calculator")

    def __init__(self, layout, app):
        self.app = app
        self.decimals = self.app.decimals
        self.layout = layout
        self.units = self.app.defaults['units'].lower()

        # ## Title
        title_label = FCLabel("%s" % self.toolName)
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

        self.unists_spacer_label = FCLabel(" ")
        self.layout.addWidget(self.unists_spacer_label)

        # ## Title of the Units Calculator
        units_label = FCLabel("<font size=3><b>%s</b></font>" % self.unitsName)
        self.layout.addWidget(units_label)

        # Grid Layout
        grid_units_layout = QtWidgets.QGridLayout()
        self.layout.addLayout(grid_units_layout)

        inch_label = FCLabel(_("INCH"))
        mm_label = FCLabel(_("MM"))
        grid_units_layout.addWidget(mm_label, 0, 0)
        grid_units_layout.addWidget(inch_label, 0, 1)

        self.inch_entry = NumericalEvalEntry(border_color='#0069A9')

        # self.inch_entry.setFixedWidth(70)
        # self.inch_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.inch_entry.setToolTip(_("Here you enter the value to be converted from INCH to MM"))

        self.mm_entry = NumericalEvalEntry(border_color='#0069A9')
        # self.mm_entry.setFixedWidth(130)
        # self.mm_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.mm_entry.setToolTip(_("Here you enter the value to be converted from MM to INCH"))

        grid_units_layout.addWidget(self.mm_entry, 1, 0)
        grid_units_layout.addWidget(self.inch_entry, 1, 1)

        # #############################################################################################################
        # ################################ V-shape Tool Calculator ####################################################
        # #############################################################################################################
        grid_vshape = QtWidgets.QGridLayout()
        grid_vshape.setColumnStretch(0, 0)
        grid_vshape.setColumnStretch(1, 1)
        self.layout.addLayout(grid_vshape)

        self.v_shape_spacer_label = FCLabel(" ")
        grid_vshape.addWidget(self.v_shape_spacer_label, 0, 0, 1, 2)

        # ## Title of the V-shape Tools Calculator
        v_shape_title_label = FCLabel("<font size=3><b>%s</b></font>" % self.v_shapeName)
        grid_vshape.addWidget(v_shape_title_label, 2, 0, 1, 2)

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
        self.cutDepth_label.setToolTip(_("This is the depth to cut into the material.\n"
                                         "In the CNCJob is the CutZ parameter."))

        self.cutDepth_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.cutDepth_entry.set_range(-10000.0000, 10000.0000)
        self.cutDepth_entry.set_precision(self.decimals)

        grid_vshape.addWidget(self.cutDepth_label, 8, 0)
        grid_vshape.addWidget(self.cutDepth_entry, 8, 1)

        # Tool Diameter
        self.effectiveToolDia_label = FCLabel('%s:' % _("Tool Diameter"))
        self.effectiveToolDia_label.setToolTip(_("This is the tool diameter to be entered into\n"
                                                 "FlatCAM Gerber section.\n"
                                                 "In the CNCJob section it is called >Tool dia<."))
        self.effectiveToolDia_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.effectiveToolDia_entry.set_precision(self.decimals)

        grid_vshape.addWidget(self.effectiveToolDia_label, 10, 0)
        grid_vshape.addWidget(self.effectiveToolDia_entry, 10, 1)

        # ## Buttons
        self.calculate_vshape_button = FCButton(_("Calculate"))
        self.calculate_vshape_button.setIcon(QtGui.QIcon(self.app.resource_location + '/calculator16.png'))

        self.calculate_vshape_button.setToolTip(
            _("Calculate either the Cut Z or the effective tool diameter,\n  "
              "depending on which is desired and which is known. ")
        )

        grid_vshape.addWidget(self.calculate_vshape_button, 12, 0, 1, 2)

        # #############################################################################################################
        # ############################## ElectroPlating Tool Calculator ###############################################
        # #############################################################################################################
        grid_electro = QtWidgets.QGridLayout()
        grid_electro.setColumnStretch(0, 0)
        grid_electro.setColumnStretch(1, 1)
        self.layout.addLayout(grid_electro)

        grid_electro.addWidget(FCLabel(""), 0, 0, 1, 2)

        # ## Title of the ElectroPlating Tools Calculator
        plate_title_label = FCLabel("<font size=3><b>%s</b></font>" % self.eplateName)
        plate_title_label.setToolTip(
            _("This calculator is useful for those who plate the via/pad/drill holes,\n"
              "using a method like graphite ink or calcium hypophosphite ink or palladium chloride.")
        )
        grid_electro.addWidget(plate_title_label, 2, 0, 1, 2)

        # Area Calculation
        self.area_sel_label = FCLabel('%s:' % _("Area Calculation"))
        self.area_sel_label.setToolTip(
            _("Choose how to calculate the board area.")
        )
        self.area_sel_radio = RadioSet([
            {'label': _('Dimensions'), 'value': 'd'},
            {"label": _("Area"), "value": "a"}
        ], stretch=False)

        grid_electro.addWidget(self.area_sel_label, 4, 0)
        grid_electro.addWidget(self.area_sel_radio, 6, 0, 1, 2)

        # BOARD LENGTH
        self.pcblengthlabel = FCLabel('%s:' % _("Board Length"))
        self.pcblengthlabel.setToolTip(_('This is the board length. In centimeters.'))
        self.pcblength_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.pcblength_entry.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Preferred)
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
        self.pcbwidthlabel.setToolTip(_('This is the board width.In centimeters.'))
        self.pcbwidth_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.pcbwidth_entry.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Preferred)
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
        self.area_label.setToolTip(_('This is the board area.'))
        self.area_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.area_entry.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Preferred)
        self.area_entry.set_precision(self.decimals)
        self.area_entry.set_range(0.0, 10000.0000)

        self.area_unit = FCLabel('%s<sup>2</sup>' % _("cm"))
        self.area_unit.setMinimumWidth(25)

        a_hlay = QtWidgets.QHBoxLayout()
        a_hlay.addWidget(self.area_entry)
        a_hlay.addWidget(self.area_unit)

        grid_electro.addWidget(self.area_label, 12, 0)
        grid_electro.addLayout(a_hlay, 12, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid_electro.addWidget(separator_line, 14, 0, 1, 2)

        # DENSITY
        self.cdensity_label = FCLabel('%s:' % _("Current Density"))
        self.cdensity_label.setToolTip(_("Current density to pass through the board. \n"
                                         "In Amps per Square Feet ASF."))
        self.cdensity_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.cdensity_entry.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Preferred)
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
        self.growth_label.setToolTip(_("How thick the copper growth is intended to be.\n"
                                       "In microns."))
        self.growth_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.growth_entry.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Preferred)
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
                                      'to be set on the Power Supply. In Amps.'))
        self.cvalue_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.cvalue_entry.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Preferred)
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
        self.timelabel.setToolTip(_('This is the calculated time required for the procedure.\n'
                                    'In minutes.'))
        self.time_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.time_entry.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Preferred)
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
            _("Calculate the current intensity value and the procedure time,\n"
              "depending on the parameters above")
        )
        grid_electro.addWidget(self.calculate_plate_button, 24, 0, 1, 2)

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
