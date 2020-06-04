# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 3/10/2019                                          #
# MIT Licence                                              #
# ##########################################################

from PyQt5 import QtWidgets
from appTool import AppTool
from appGUI.GUIElements import FCSpinner, FCDoubleSpinner, FCEntry
import math

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class ToolCalculator(AppTool):

    toolName = _("Calculators")
    v_shapeName = _("V-Shape Tool Calculator")
    unitsName = _("Units Calculator")
    eplateName = _("ElectroPlating Calculator")

    def __init__(self, app):
        AppTool.__init__(self, app)

        self.app = app
        self.decimals = self.app.decimals

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

        # #####################
        # ## Units Calculator #
        # #####################

        self.unists_spacer_label = QtWidgets.QLabel(" ")
        self.layout.addWidget(self.unists_spacer_label)

        # ## Title of the Units Calculator
        units_label = QtWidgets.QLabel("<font size=3><b>%s</b></font>" % self.unitsName)
        self.layout.addWidget(units_label)

        # Grid Layout
        grid_units_layout = QtWidgets.QGridLayout()
        self.layout.addLayout(grid_units_layout)

        inch_label = QtWidgets.QLabel(_("INCH"))
        mm_label = QtWidgets.QLabel(_("MM"))
        grid_units_layout.addWidget(mm_label, 0, 0)
        grid_units_layout.addWidget(inch_label, 0, 1)

        self.inch_entry = FCEntry()

        # self.inch_entry.setFixedWidth(70)
        # self.inch_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.inch_entry.setToolTip(_("Here you enter the value to be converted from INCH to MM"))

        self.mm_entry = FCEntry()
        # self.mm_entry.setFixedWidth(130)
        # self.mm_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.mm_entry.setToolTip(_("Here you enter the value to be converted from MM to INCH"))

        grid_units_layout.addWidget(self.mm_entry, 1, 0)
        grid_units_layout.addWidget(self.inch_entry, 1, 1)

        # ##############################
        # ## V-shape Tool Calculator ###
        # ##############################
        self.v_shape_spacer_label = QtWidgets.QLabel(" ")
        self.layout.addWidget(self.v_shape_spacer_label)

        # ## Title of the V-shape Tools Calculator
        v_shape_title_label = QtWidgets.QLabel("<font size=3><b>%s</b></font>" % self.v_shapeName)
        self.layout.addWidget(v_shape_title_label)

        # ## Form Layout
        form_layout = QtWidgets.QFormLayout()
        self.layout.addLayout(form_layout)

        self.tipDia_label = QtWidgets.QLabel('%s:' % _("Tip Diameter"))
        self.tipDia_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.tipDia_entry.set_precision(self.decimals)
        self.tipDia_entry.set_range(0.0, 9999.9999)
        self.tipDia_entry.setSingleStep(0.1)

        # self.tipDia_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.tipDia_label.setToolTip(
            _("This is the tool tip diameter.\n"
              "It is specified by manufacturer.")
        )
        self.tipAngle_label = QtWidgets.QLabel('%s:' % _("Tip Angle"))
        self.tipAngle_entry = FCSpinner(callback=self.confirmation_message_int)
        self.tipAngle_entry.set_range(0,180)
        self.tipAngle_entry.set_step(5)

        # self.tipAngle_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.tipAngle_label.setToolTip(_("This is the angle of the tip of the tool.\n"
                                         "It is specified by manufacturer."))

        self.cutDepth_label = QtWidgets.QLabel('%s:' % _("Cut Z"))
        self.cutDepth_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.cutDepth_entry.set_range(-9999.9999, 9999.9999)
        self.cutDepth_entry.set_precision(self.decimals)

        # self.cutDepth_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.cutDepth_label.setToolTip(_("This is the depth to cut into the material.\n"
                                         "In the CNCJob is the CutZ parameter."))

        self.effectiveToolDia_label = QtWidgets.QLabel('%s:' % _("Tool Diameter"))
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
        self.calculate_vshape_button = QtWidgets.QPushButton(_("Calculate"))
        # self.calculate_button.setFixedWidth(70)
        self.calculate_vshape_button.setToolTip(
            _("Calculate either the Cut Z or the effective tool diameter,\n  "
              "depending on which is desired and which is known. ")
        )

        self.layout.addWidget(self.calculate_vshape_button)

        # ####################################
        # ## ElectroPlating Tool Calculator ##
        # ####################################

        self.plate_spacer_label = QtWidgets.QLabel(" ")
        self.layout.addWidget(self.plate_spacer_label)

        # ## Title of the ElectroPlating Tools Calculator
        plate_title_label = QtWidgets.QLabel("<font size=3><b>%s</b></font>" % self.eplateName)
        plate_title_label.setToolTip(
            _("This calculator is useful for those who plate the via/pad/drill holes,\n"
              "using a method like graphite ink or calcium hypophosphite ink or palladium chloride.")
        )
        self.layout.addWidget(plate_title_label)

        # ## Plate Form Layout
        plate_form_layout = QtWidgets.QFormLayout()
        self.layout.addLayout(plate_form_layout)

        self.pcblengthlabel = QtWidgets.QLabel('%s:' % _("Board Length"))
        self.pcblength_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.pcblength_entry.set_precision(self.decimals)
        self.pcblength_entry.set_range(0.0, 9999.9999)

        # self.pcblength_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.pcblengthlabel.setToolTip(_('This is the board length. In centimeters.'))

        self.pcbwidthlabel = QtWidgets.QLabel('%s:' % _("Board Width"))
        self.pcbwidth_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.pcbwidth_entry.set_precision(self.decimals)
        self.pcbwidth_entry.set_range(0.0, 9999.9999)

        # self.pcbwidth_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.pcbwidthlabel.setToolTip(_('This is the board width.In centimeters.'))

        self.cdensity_label = QtWidgets.QLabel('%s:' % _("Current Density"))
        self.cdensity_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.cdensity_entry.set_precision(self.decimals)
        self.cdensity_entry.set_range(0.0, 9999.9999)
        self.cdensity_entry.setSingleStep(0.1)

        # self.cdensity_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.cdensity_label.setToolTip(_("Current density to pass through the board. \n"
                                         "In Amps per Square Feet ASF."))

        self.growth_label = QtWidgets.QLabel('%s:' % _("Copper Growth"))
        self.growth_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.growth_entry.set_precision(self.decimals)
        self.growth_entry.set_range(0.0, 9999.9999)
        self.growth_entry.setSingleStep(0.01)

        # self.growth_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.growth_label.setToolTip(_("How thick the copper growth is intended to be.\n"
                                       "In microns."))

        # self.growth_entry.setEnabled(False)

        self.cvaluelabel = QtWidgets.QLabel('%s:' % _("Current Value"))
        self.cvalue_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.cvalue_entry.set_precision(self.decimals)
        self.cvalue_entry.set_range(0.0, 9999.9999)
        self.cvalue_entry.setSingleStep(0.1)

        # self.cvalue_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.cvaluelabel.setToolTip(_('This is the current intensity value\n'
                                      'to be set on the Power Supply. In Amps.'))
        self.cvalue_entry.setReadOnly(True)

        self.timelabel = QtWidgets.QLabel('%s:' % _("Time"))
        self.time_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.time_entry.set_precision(self.decimals)
        self.time_entry.set_range(0.0, 9999.9999)
        self.time_entry.setSingleStep(0.1)

        # self.time_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.timelabel.setToolTip(_('This is the calculated time required for the procedure.\n'
                                    'In minutes.'))
        self.time_entry.setReadOnly(True)

        plate_form_layout.addRow(self.pcblengthlabel, self.pcblength_entry)
        plate_form_layout.addRow(self.pcbwidthlabel, self.pcbwidth_entry)
        plate_form_layout.addRow(self.cdensity_label, self.cdensity_entry)
        plate_form_layout.addRow(self.growth_label, self.growth_entry)
        plate_form_layout.addRow(self.cvaluelabel, self.cvalue_entry)
        plate_form_layout.addRow(self.timelabel, self.time_entry)

        # ## Buttons
        self.calculate_plate_button = QtWidgets.QPushButton(_("Calculate"))
        # self.calculate_button.setFixedWidth(70)
        self.calculate_plate_button.setToolTip(
            _("Calculate the current intensity value and the procedure time,\n"
              "depending on the parameters above")
        )
        self.layout.addWidget(self.calculate_plate_button)

        self.layout.addStretch()

        # ## Reset Tool
        self.reset_button = QtWidgets.QPushButton(_("Reset Tool"))
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

        self.units = ''

        # ## Signals
        self.cutDepth_entry.valueChanged.connect(self.on_calculate_tool_dia)
        self.cutDepth_entry.returnPressed.connect(self.on_calculate_tool_dia)
        self.tipDia_entry.returnPressed.connect(self.on_calculate_tool_dia)
        self.tipAngle_entry.returnPressed.connect(self.on_calculate_tool_dia)
        self.calculate_vshape_button.clicked.connect(self.on_calculate_tool_dia)

        self.mm_entry.editingFinished.connect(self.on_calculate_inch_units)
        self.inch_entry.editingFinished.connect(self.on_calculate_mm_units)

        self.calculate_plate_button.clicked.connect(self.on_calculate_eplate)
        self.reset_button.clicked.connect(self.set_tool_ui)

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
        self.units = self.app.defaults['units'].upper()

        # ## Initialize form
        self.mm_entry.set_value('%.*f' % (self.decimals, 0))
        self.inch_entry.set_value('%.*f' % (self.decimals, 0))

        length = self.app.defaults["tools_calc_electro_length"]
        width = self.app.defaults["tools_calc_electro_width"]
        density = self.app.defaults["tools_calc_electro_cdensity"]
        growth = self.app.defaults["tools_calc_electro_growth"]
        self.pcblength_entry.set_value(length)
        self.pcbwidth_entry.set_value(width)
        self.cdensity_entry.set_value(density)
        self.growth_entry.set_value(growth)
        self.cvalue_entry.set_value(0.00)
        self.time_entry.set_value(0.0)

        tip_dia = self.app.defaults["tools_calc_vshape_tip_dia"]
        tip_angle = self.app.defaults["tools_calc_vshape_tip_angle"]
        cut_z = self.app.defaults["tools_calc_vshape_cut_z"]

        self.tipDia_entry.set_value(tip_dia)
        self.tipAngle_entry.set_value(tip_angle)
        self.cutDepth_entry.set_value(cut_z)
        self.effectiveToolDia_entry.set_value('0.0000')

    def on_calculate_tool_dia(self):
        # Calculation:
        # Manufacturer gives total angle of the the tip but we need only half of it
        # tangent(half_tip_angle) = opposite side / adjacent = part_of _real_dia / depth_of_cut
        # effective_diameter = tip_diameter + part_of_real_dia_left_side + part_of_real_dia_right_side
        # tool is symmetrical therefore: part_of_real_dia_left_side = part_of_real_dia_right_side
        # effective_diameter = tip_diameter + (2 * part_of_real_dia_left_side)
        # effective diameter = tip_diameter + (2 * depth_of_cut * tangent(half_tip_angle))

        tip_diameter = float(self.tipDia_entry.get_value())

        half_tip_angle = float(self.tipAngle_entry.get_value()) / 2.0

        cut_depth = float(self.cutDepth_entry.get_value())
        cut_depth = -cut_depth if cut_depth < 0 else cut_depth

        tool_diameter = tip_diameter + (2 * cut_depth * math.tan(math.radians(half_tip_angle)))
        self.effectiveToolDia_entry.set_value("%.*f" % (self.decimals, tool_diameter))

    def on_calculate_inch_units(self):
        mm_val = float(self.mm_entry.get_value())
        self.inch_entry.set_value('%.*f' % (self.decimals, (mm_val / 25.4)))

    def on_calculate_mm_units(self):
        inch_val = float(self.inch_entry.get_value())
        self.mm_entry.set_value('%.*f' % (self.decimals, (inch_val * 25.4)))

    def on_calculate_eplate(self):
        length = float(self.pcblength_entry.get_value())
        width = float(self.pcbwidth_entry.get_value())
        density = float(self.cdensity_entry.get_value())
        copper = float(self.growth_entry.get_value())

        calculated_current = (length * width * density) * 0.0021527820833419
        calculated_time = copper * 2.142857142857143 * float(20 / density)

        self.cvalue_entry.set_value('%.2f' % calculated_current)
        self.time_entry.set_value('%.1f' % calculated_time)

# end of file
