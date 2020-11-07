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
        self.ui.cutDepth_entry.valueChanged.connect(self.on_calculate_tool_dia)
        self.ui.cutDepth_entry.returnPressed.connect(self.on_calculate_tool_dia)
        self.ui.tipDia_entry.returnPressed.connect(self.on_calculate_tool_dia)
        self.ui.tipAngle_entry.returnPressed.connect(self.on_calculate_tool_dia)
        self.ui.calculate_vshape_button.clicked.connect(self.on_calculate_tool_dia)

        self.ui.mm_entry.editingFinished.connect(self.on_calculate_inch_units)
        self.ui.inch_entry.editingFinished.connect(self.on_calculate_mm_units)

        self.ui.calculate_plate_button.clicked.connect(self.on_calculate_eplate)
        self.ui.reset_button.clicked.connect(self.set_tool_ui)

        self.ui.area_sel_radio.activated_custom.connect(self.on_area_calculation_radio)

    def run(self, toggle=True):
        self.app.defaults.report_usage("ToolCalculators()")

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
        self.ui.effectiveToolDia_entry.set_value('0.0000')

        self.ui.area_sel_radio.set_value('d')
        self.on_area_calculation_radio(val='d')

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

    def on_calculate_inch_units(self):
        mm_val = float(self.ui.mm_entry.get_value())
        self.ui.inch_entry.set_value('%.*f' % (self.decimals, (mm_val / 25.4)))

    def on_calculate_mm_units(self):
        inch_val = float(self.ui.inch_entry.get_value())
        self.ui.mm_entry.set_value('%.*f' % (self.decimals, (inch_val * 25.4)))

    def on_calculate_eplate(self):
        area_calc_sel = self.ui.area_sel_radio.get_value()
        length = self.ui.pcblength_entry.get_value()
        width = self.ui.pcbwidth_entry.get_value()
        area = self.ui.area_entry.get_value()

        density = self.ui.cdensity_entry.get_value()
        copper = self.ui.growth_entry.get_value()

        if area_calc_sel == 'd':
            calculated_current = (length * width * density) * 0.0021527820833419
        else:
            calculated_current = (area * density) * 0.0021527820833419
        calculated_time = copper * 2.142857142857143 * float(20 / density)

        self.ui.cvalue_entry.set_value('%.2f' % calculated_current)
        self.ui.time_entry.set_value('%.1f' % calculated_time)


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

        # ##############################
        # ## V-shape Tool Calculator ###
        # ##############################
        self.v_shape_spacer_label = FCLabel(" ")
        self.layout.addWidget(self.v_shape_spacer_label)

        # ## Title of the V-shape Tools Calculator
        v_shape_title_label = FCLabel("<font size=3><b>%s</b></font>" % self.v_shapeName)
        self.layout.addWidget(v_shape_title_label)

        # ## Form Layout
        form_layout = QtWidgets.QFormLayout()
        self.layout.addLayout(form_layout)

        self.tipDia_label = FCLabel('%s:' % _("Tip Diameter"))
        self.tipDia_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.tipDia_entry.set_precision(self.decimals)
        self.tipDia_entry.set_range(0.0, 10000.0000)
        self.tipDia_entry.setSingleStep(0.1)

        # self.tipDia_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.tipDia_label.setToolTip(
            _("This is the tool tip diameter.\n"
              "It is specified by manufacturer.")
        )
        self.tipAngle_label = FCLabel('%s:' % _("Tip Angle"))
        self.tipAngle_entry = FCSpinner(callback=self.confirmation_message_int)
        self.tipAngle_entry.set_range(0, 180)
        self.tipAngle_entry.set_step(5)

        # self.tipAngle_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.tipAngle_label.setToolTip(_("This is the angle of the tip of the tool.\n"
                                         "It is specified by manufacturer."))

        self.cutDepth_label = FCLabel('%s:' % _("Cut Z"))
        self.cutDepth_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.cutDepth_entry.set_range(-10000.0000, 10000.0000)
        self.cutDepth_entry.set_precision(self.decimals)

        # self.cutDepth_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.cutDepth_label.setToolTip(_("This is the depth to cut into the material.\n"
                                         "In the CNCJob is the CutZ parameter."))

        self.effectiveToolDia_label = FCLabel('%s:' % _("Tool Diameter"))
        self.effectiveToolDia_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.effectiveToolDia_entry.set_precision(self.decimals)

        # self.effectiveToolDia_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.effectiveToolDia_label.setToolTip(_("This is the tool diameter to be entered into\n"
                                                 "FlatCAM Gerber section.\n"
                                                 "In the CNCJob section it is called >Tool dia<."))
        # self.effectiveToolDia_entry.setEnabled(False)

        form_layout.addRow(self.tipDia_label, self.tipDia_entry)
        form_layout.addRow(self.tipAngle_label, self.tipAngle_entry)
        form_layout.addRow(self.cutDepth_label, self.cutDepth_entry)
        form_layout.addRow(self.effectiveToolDia_label, self.effectiveToolDia_entry)

        # ## Buttons
        self.calculate_vshape_button = FCButton(_("Calculate"))
        self.calculate_vshape_button.setIcon(QtGui.QIcon(self.app.resource_location + '/calculator16.png'))

        self.calculate_vshape_button.setToolTip(
            _("Calculate either the Cut Z or the effective tool diameter,\n  "
              "depending on which is desired and which is known. ")
        )

        self.layout.addWidget(self.calculate_vshape_button)

        # ####################################
        # ## ElectroPlating Tool Calculator ##
        # ####################################

        self.layout.addWidget(FCLabel(""))

        # ## Title of the ElectroPlating Tools Calculator
        plate_title_label = FCLabel("<font size=3><b>%s</b></font>" % self.eplateName)
        plate_title_label.setToolTip(
            _("This calculator is useful for those who plate the via/pad/drill holes,\n"
              "using a method like graphite ink or calcium hypophosphite ink or palladium chloride.")
        )
        self.layout.addWidget(plate_title_label)

        # ## Plate Form Layout
        grid2 = QtWidgets.QGridLayout()
        grid2.setColumnStretch(0, 0)
        grid2.setColumnStretch(1, 1)
        self.layout.addLayout(grid2)

        # Area Calculation
        self.area_sel_label = FCLabel('%s:' % _("Area Calculation"))
        self.area_sel_label.setToolTip(
            _("Choose how to calculate the board area.")
        )
        self.area_sel_radio = RadioSet([
            {'label': _('Dimensions'), 'value': 'd'},
            {"label": _("Area"), "value": "a"}
        ], stretch=False)

        grid2.addWidget(self.area_sel_label, 0, 0)
        grid2.addWidget(self.area_sel_radio, 1, 0, 1, 2)

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

        grid2.addWidget(self.pcblengthlabel, 2, 0)
        grid2.addLayout(l_hlay, 2, 1)

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

        grid2.addWidget(self.pcbwidthlabel, 4, 0)
        grid2.addLayout(w_hlay, 4, 1)

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

        grid2.addWidget(self.area_label, 6, 0)
        grid2.addLayout(a_hlay, 6, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid2.addWidget(separator_line, 7, 0, 1, 2)

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

        grid2.addWidget(self.cdensity_label, 8, 0)
        grid2.addLayout(d_hlay, 8, 1)

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

        grid2.addWidget(self.growth_label, 10, 0)
        grid2.addLayout(g_hlay, 10, 1)

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

        grid2.addWidget(self.cvaluelabel, 12, 0)
        grid2.addLayout(c_hlay, 12, 1)

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
        self.time_entry.setReadOnly(True)

        t_hlay = QtWidgets.QHBoxLayout()
        t_hlay.addWidget(self.time_entry)
        t_hlay.addWidget(time_unit)

        grid2.addWidget(self.timelabel, 14, 0)
        grid2.addLayout(t_hlay, 14, 1)

        # ## Buttons
        self.calculate_plate_button = FCButton(_("Calculate"))
        self.calculate_plate_button.setIcon(QtGui.QIcon(self.app.resource_location + '/calculator16.png'))
        self.calculate_plate_button.setToolTip(
            _("Calculate the current intensity value and the procedure time,\n"
              "depending on the parameters above")
        )
        self.layout.addWidget(self.calculate_plate_button)

        self.layout.addStretch()

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
