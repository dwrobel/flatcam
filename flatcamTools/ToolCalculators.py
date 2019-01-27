from PyQt5 import QtGui
from GUIElements import FCEntry
from FlatCAMTool import FlatCAMTool
from FlatCAMObj import *
import math


class ToolCalculator(FlatCAMTool):

    toolName = "Calculators"
    v_shapeName = "V-Shape Tool Calculator"
    unitsName = "Units Calculator"

    def __init__(self, app):
        FlatCAMTool.__init__(self, app)

        self.app = app

        ## Title
        title_label = QtWidgets.QLabel("<font size=4><b>%s</b></font>" % self.toolName)
        self.layout.addWidget(title_label)

        ## V-shape Tool Calculator

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
        self.tipDia_entry.setFixedWidth(70)
        self.tipDia_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.tipDia_entry.setToolTip('This is the diameter of the tool tip.\n'
                                     'The manufacturer specifies it.')

        self.tipAngle_label = QtWidgets.QLabel("Tip Angle:")
        self.tipAngle_entry = FCEntry()
        self.tipAngle_entry.setFixedWidth(70)
        self.tipAngle_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.tipAngle_entry.setToolTip("This is the angle of the tip of the tool.\n"
                                       "It is specified by manufacturer.")

        self.cutDepth_label = QtWidgets.QLabel("Cut Z:")
        self.cutDepth_entry = FCEntry()
        self.cutDepth_entry.setFixedWidth(70)
        self.cutDepth_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.cutDepth_entry.setToolTip("This is the depth to cut into the material.\n"
                                       "In the CNCJob is the CutZ parameter.")

        self.effectiveToolDia_label = QtWidgets.QLabel("Tool Diameter:")
        self.effectiveToolDia_entry = FCEntry()
        self.effectiveToolDia_entry.setFixedWidth(70)
        self.effectiveToolDia_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.effectiveToolDia_entry.setToolTip("This is the tool diameter to be entered into\n"
                                               "FlatCAM Gerber section.\n"
                                               "In the CNCJob section it is called >Tool dia<.")
        # self.effectiveToolDia_entry.setEnabled(False)


        form_layout.addRow(self.tipDia_label, self.tipDia_entry)
        form_layout.addRow(self.tipAngle_label, self.tipAngle_entry)
        form_layout.addRow(self.cutDepth_label, self.cutDepth_entry)
        form_layout.addRow(self.effectiveToolDia_label, self.effectiveToolDia_entry)


        ## Buttons
        self.calculate_button = QtWidgets.QPushButton("Calculate")
        self.calculate_button.setFixedWidth(70)
        self.calculate_button.setToolTip(
            "Calculate either the Cut Z or the effective tool diameter,\n  "
            "depending on which is desired and which is known. "
        )
        self.empty_label = QtWidgets.QLabel(" ")

        form_layout.addRow(self.empty_label, self.calculate_button)

        ## Units Calculator
        self.unists_spacer_label = QtWidgets.QLabel(" ")
        self.layout.addWidget(self.unists_spacer_label)

        ## Title of the Units Calculator
        units_label = QtWidgets.QLabel("<font size=3><b>%s</b></font>" % self.unitsName)
        self.layout.addWidget(units_label)

        #Form Layout
        form_units_layout = QtWidgets.QFormLayout()
        self.layout.addLayout(form_units_layout)

        inch_label = QtWidgets.QLabel("INCH")
        mm_label = QtWidgets.QLabel("MM")

        self.inch_entry = FCEntry()
        self.inch_entry.setFixedWidth(70)
        self.inch_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.inch_entry.setToolTip("Here you enter the value to be converted from INCH to MM")

        self.mm_entry = FCEntry()
        self.mm_entry.setFixedWidth(70)
        self.mm_entry.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.mm_entry.setToolTip("Here you enter the value to be converted from MM to INCH")

        form_units_layout.addRow(mm_label, inch_label)
        form_units_layout.addRow(self.mm_entry, self.inch_entry)

        self.layout.addStretch()

        ## Signals
        self.cutDepth_entry.textChanged.connect(self.on_calculate_tool_dia)
        self.cutDepth_entry.editingFinished.connect(self.on_calculate_tool_dia)
        self.tipDia_entry.editingFinished.connect(self.on_calculate_tool_dia)
        self.tipAngle_entry.editingFinished.connect(self.on_calculate_tool_dia)
        self.calculate_button.clicked.connect(self.on_calculate_tool_dia)

        self.mm_entry.editingFinished.connect(self.on_calculate_inch_units)
        self.inch_entry.editingFinished.connect(self.on_calculate_mm_units)


        ## Initialize form
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

        self.mm_entry.set_value('0')
        self.inch_entry.set_value('0')

    def run(self):
        FlatCAMTool.run(self)
        self.app.ui.notebook.setTabText(2, "Calc. Tool")

    def install(self, icon=None, separator=None, **kwargs):
        FlatCAMTool.install(self, icon, separator, shortcut='ALT+C', **kwargs)

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
        except TypeError:
            return

        tool_diameter = tip_diameter + (2 * cut_depth * math.tan(math.radians(half_tip_angle)))
        self.effectiveToolDia_entry.set_value("%.4f" % tool_diameter)

    def on_calculate_inch_units(self):
        self.inch_entry.set_value('%.6f' % (float(self.mm_entry.get_value()) / 25.4))

    def on_calculate_mm_units(self):
        self.mm_entry.set_value('%.6f' % (float(self.inch_entry.get_value()) * 25.4))

# end of file