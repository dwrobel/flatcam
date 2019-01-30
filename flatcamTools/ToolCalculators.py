from PyQt5 import QtGui
from GUIElements import FCEntry
from FlatCAMTool import FlatCAMTool
from FlatCAMObj import *
import math


class ToolCalculator(FlatCAMTool):

    toolName = "Calculators"
    v_shapeName = "V-Shape Tool Calculator"
    unitsName = "Units Calculator"
    eplateName = "ElectroPlating Calculator"

    def __init__(self, app):
        FlatCAMTool.__init__(self, app)

        self.app = app

        ## Title
        title_label = QtWidgets.QLabel("<font size=4><b>%s</b></font>" % self.toolName)
        self.layout.addWidget(title_label)

        ############################
        ## V-shape Tool Calculator ##
        ############################

        self.v_shape_spacer_label = QtWidgets.QLabel(" ")
        self.layout.addWidget(self.v_shape_spacer_label)

        ## Title of the V-shape Tools Calculator
        v_shape_title_label = QtWidgets.QLabel("<font size=3><b>%s</b></font>" % self.v_shapeName)
        self.layout.addWidget(v_shape_title_label)

        ## Form Layout
        form_layout = QtWidgets.QFormLayout()
        self.layout.addLayout(form_layout)

        self.tipDia_label = QtWidgets.QLabel("Tip Diameter:")
        self.tipDia_entry = FCEntry()
        # self.tipDia_entry.setFixedWidth(70)
        self.tipDia_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.tipDia_label.setToolTip('This is the diameter of the tool tip.\n'
                                     'The manufacturer specifies it.')

        self.tipAngle_label = QtWidgets.QLabel("Tip Angle:")
        self.tipAngle_entry = FCEntry()
        # self.tipAngle_entry.setFixedWidth(70)
        self.tipAngle_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.tipAngle_label.setToolTip("This is the angle of the tip of the tool.\n"
                                       "It is specified by manufacturer.")

        self.cutDepth_label = QtWidgets.QLabel("Cut Z:")
        self.cutDepth_entry = FCEntry()
        # self.cutDepth_entry.setFixedWidth(70)
        self.cutDepth_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.cutDepth_label.setToolTip("This is the depth to cut into the material.\n"
                                       "In the CNCJob is the CutZ parameter.")

        self.effectiveToolDia_label = QtWidgets.QLabel("Tool Diameter:")
        self.effectiveToolDia_entry = FCEntry()
        # self.effectiveToolDia_entry.setFixedWidth(70)
        self.effectiveToolDia_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.effectiveToolDia_label.setToolTip("This is the tool diameter to be entered into\n"
                                               "FlatCAM Gerber section.\n"
                                               "In the CNCJob section it is called >Tool dia<.")
        # self.effectiveToolDia_entry.setEnabled(False)


        form_layout.addRow(self.tipDia_label, self.tipDia_entry)
        form_layout.addRow(self.tipAngle_label, self.tipAngle_entry)
        form_layout.addRow(self.cutDepth_label, self.cutDepth_entry)
        form_layout.addRow(self.effectiveToolDia_label, self.effectiveToolDia_entry)

        ## Buttons
        self.calculate_vshape_button = QtWidgets.QPushButton("Calculate")
        # self.calculate_button.setFixedWidth(70)
        self.calculate_vshape_button.setToolTip(
            "Calculate either the Cut Z or the effective tool diameter,\n  "
            "depending on which is desired and which is known. "
        )
        self.empty_label = QtWidgets.QLabel(" ")

        form_layout.addRow(self.empty_label, self.calculate_vshape_button)

        ######################
        ## Units Calculator ##
        ######################

        self.unists_spacer_label = QtWidgets.QLabel(" ")
        self.layout.addWidget(self.unists_spacer_label)

        ## Title of the Units Calculator
        units_label = QtWidgets.QLabel("<font size=3><b>%s</b></font>" % self.unitsName)
        self.layout.addWidget(units_label)

        #Grid Layout
        grid_units_layout = QtWidgets.QGridLayout()
        self.layout.addLayout(grid_units_layout)

        inch_label = QtWidgets.QLabel("INCH")
        mm_label = QtWidgets.QLabel("MM")
        grid_units_layout.addWidget(mm_label, 0, 0)
        grid_units_layout.addWidget( inch_label, 0, 1)

        self.inch_entry = FCEntry()
        # self.inch_entry.setFixedWidth(70)
        self.inch_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.inch_entry.setToolTip("Here you enter the value to be converted from INCH to MM")

        self.mm_entry = FCEntry()
        # self.mm_entry.setFixedWidth(130)
        self.mm_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.mm_entry.setToolTip("Here you enter the value to be converted from MM to INCH")

        grid_units_layout.addWidget(self.mm_entry, 1, 0)
        grid_units_layout.addWidget(self.inch_entry, 1, 1)

        ####################################
        ## ElectroPlating Tool Calculator ##
        ####################################

        self.plate_spacer_label = QtWidgets.QLabel(" ")
        self.layout.addWidget(self.plate_spacer_label)

        ## Title of the ElectroPlating Tools Calculator
        plate_title_label = QtWidgets.QLabel("<font size=3><b>%s</b></font>" % self.eplateName)
        plate_title_label.setToolTip(
            "This calculator is useful for those who plate the via/pad/drill holes,\n"
            "using a method like grahite ink or calcium hypophosphite ink or palladium chloride."
        )
        self.layout.addWidget(plate_title_label)

        ## Plate Form Layout
        plate_form_layout = QtWidgets.QFormLayout()
        self.layout.addLayout(plate_form_layout)

        self.pcblengthlabel = QtWidgets.QLabel("Board Length:")
        self.pcblength_entry = FCEntry()
        # self.pcblengthlabel.setFixedWidth(70)
        self.pcblength_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.pcblengthlabel.setToolTip('This is the board length. In centimeters.')

        self.pcbwidthlabel = QtWidgets.QLabel("Board Width:")
        self.pcbwidth_entry = FCEntry()
        # self.pcbwidthlabel.setFixedWidth(70)
        self.pcbwidth_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.pcbwidthlabel.setToolTip('This is the board width.In centimeters.')

        self.cdensity_label = QtWidgets.QLabel("Current Density:")
        self.cdensity_entry = FCEntry()
        # self.cdensity_entry.setFixedWidth(70)
        self.cdensity_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.cdensity_label.setToolTip("Current density to pass through the board. \n"
                                       "In Amps per Square Feet ASF.")


        self.growth_label = QtWidgets.QLabel("Copper Growth:")
        self.growth_entry = FCEntry()
        # self.growth_entry.setFixedWidth(70)
        self.growth_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.growth_label.setToolTip("How thick the copper growth is intended to be.\n"
                                     "In microns.")

        # self.growth_entry.setEnabled(False)

        self.cvaluelabel = QtWidgets.QLabel("Current Value:")
        self.cvalue_entry = FCEntry()
        # self.cvaluelabel.setFixedWidth(70)
        self.cvalue_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.cvaluelabel.setToolTip('This is the current intensity value\n'
                                     'to be set on the Power Supply. In Amps.')
        self.cvalue_entry.setDisabled(True)

        self.timelabel = QtWidgets.QLabel("Time:")
        self.time_entry = FCEntry()
        # self.timelabel.setFixedWidth(70)
        self.time_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.timelabel.setToolTip('This is the calculated time required for the procedure.\n'
                                  'In minutes.')
        self.time_entry.setDisabled(True)

        plate_form_layout.addRow(self.pcblengthlabel, self.pcblength_entry)
        plate_form_layout.addRow(self.pcbwidthlabel, self.pcbwidth_entry)
        plate_form_layout.addRow(self.cdensity_label, self.cdensity_entry)
        plate_form_layout.addRow(self.growth_label, self.growth_entry)
        plate_form_layout.addRow(self.cvaluelabel, self.cvalue_entry)
        plate_form_layout.addRow(self.timelabel, self.time_entry)

        ## Buttons
        self.calculate_plate_button = QtWidgets.QPushButton("Calculate")
        # self.calculate_button.setFixedWidth(70)
        self.calculate_plate_button.setToolTip(
            "Calculate the current intensity value and the procedure time,\n  "
            "depending on the parameters above"
        )
        self.empty_label_2 = QtWidgets.QLabel(" ")

        plate_form_layout.addRow(self.empty_label_2, self.calculate_plate_button)

        self.layout.addStretch()

        ## Signals
        self.cutDepth_entry.textChanged.connect(self.on_calculate_tool_dia)
        self.cutDepth_entry.editingFinished.connect(self.on_calculate_tool_dia)
        self.tipDia_entry.editingFinished.connect(self.on_calculate_tool_dia)
        self.tipAngle_entry.editingFinished.connect(self.on_calculate_tool_dia)
        self.calculate_vshape_button.clicked.connect(self.on_calculate_tool_dia)

        self.mm_entry.editingFinished.connect(self.on_calculate_inch_units)
        self.inch_entry.editingFinished.connect(self.on_calculate_mm_units)

        self.calculate_plate_button.clicked.connect(self.on_calculate_eplate)

        self.set_ui()

    def run(self):
        FlatCAMTool.run(self)
        self.set_ui()
        self.app.ui.notebook.setTabText(2, "Calc. Tool")

    def install(self, icon=None, separator=None, **kwargs):
        FlatCAMTool.install(self, icon, separator, shortcut='ALT+C', **kwargs)

    def set_ui(self):
        ## Initialize form
        self.mm_entry.set_value('0')
        self.inch_entry.set_value('0')

        self.pcblength_entry.set_value('10')
        self.pcbwidth_entry.set_value('10')
        self.cdensity_entry.set_value('13')
        self.growth_entry.set_value('10')
        self.cvalue_entry.set_value(2.80)
        self.time_entry.set_value(33.0)

        if self.app.defaults["units"] == 'MM':
            self.tipDia_entry.set_value('0.2')
            self.tipAngle_entry.set_value('45')
            self.cutDepth_entry.set_value('0.25')
            self.effectiveToolDia_entry.set_value('0.39')
        else:
            self.tipDia_entry.set_value('7.87402')
            self.tipAngle_entry.set_value('45')
            self.cutDepth_entry.set_value('9.84252')
            self.effectiveToolDia_entry.set_value('15.35433')

    def on_calculate_tool_dia(self):
        # Calculation:
        # Manufacturer gives total angle of the the tip but we need only half of it
        # tangent(half_tip_angle) = opposite side / adjacent = part_of _real_dia / depth_of_cut
        # effective_diameter = tip_diameter + part_of_real_dia_left_side + part_of_real_dia_right_side
        # tool is symmetrical therefore: part_of_real_dia_left_side = part_of_real_dia_right_side
        # effective_diameter = tip_diameter + (2 * part_of_real_dia_left_side)
        # effective diameter = tip_diameter + (2 * depth_of_cut * tangent(half_tip_angle))

        try:
            tip_diameter = float(self.tipDia_entry.get_value())
            half_tip_angle = float(self.tipAngle_entry.get_value()) / 2
            cut_depth = float(self.cutDepth_entry.get_value())
        except:
            return

        tool_diameter = tip_diameter + (2 * cut_depth * math.tan(math.radians(half_tip_angle)))
        self.effectiveToolDia_entry.set_value("%.4f" % tool_diameter)

    def on_calculate_inch_units(self):
        self.inch_entry.set_value('%.6f' % (float(self.mm_entry.get_value()) / 25.4))

    def on_calculate_mm_units(self):
        self.mm_entry.set_value('%.6f' % (float(self.inch_entry.get_value()) * 25.4))

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