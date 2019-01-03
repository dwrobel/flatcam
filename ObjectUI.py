import sys
from PyQt5 import QtGui, QtCore, QtWidgets, QtWidgets
from GUIElements import FCEntry, FloatEntry, EvalEntry, FCCheckBox, FCTable, \
    LengthEntry, FCTextArea, IntEntry, RadioSet, OptionalInputSection, FCComboBox, FloatEntry2, EvalEntry2
from camlib import Excellon

class ObjectUI(QtWidgets.QWidget):
    """
    Base class for the UI of FlatCAM objects. Deriving classes should
    put UI elements in ObjectUI.custom_box (QtWidgets.QLayout).
    """

    def __init__(self, icon_file='share/flatcam_icon32.png', title='FlatCAM Object', parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        ## Page Title box (spacing between children)
        self.title_box = QtWidgets.QHBoxLayout()
        layout.addLayout(self.title_box)

        ## Page Title icon
        pixmap = QtGui.QPixmap(icon_file)
        self.icon = QtWidgets.QLabel()
        self.icon.setPixmap(pixmap)
        self.title_box.addWidget(self.icon, stretch=0)

        ## Title label
        self.title_label = QtWidgets.QLabel("<font size=5><b>" + title + "</b></font>")
        self.title_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.title_box.addWidget(self.title_label, stretch=1)

        ## Object name
        self.name_box = QtWidgets.QHBoxLayout()
        layout.addLayout(self.name_box)
        name_label = QtWidgets.QLabel("Name:")
        self.name_box.addWidget(name_label)
        self.name_entry = FCEntry()
        self.name_box.addWidget(self.name_entry)

        ## Box box for custom widgets
        # This gets populated in offspring implementations.
        self.custom_box = QtWidgets.QVBoxLayout()
        layout.addLayout(self.custom_box)

        ###########################
        ## Common to all objects ##
        ###########################

        #### Scale ####
        self.scale_label = QtWidgets.QLabel('<b>Scale:</b>')
        self.scale_label.setToolTip(
            "Change the size of the object."
        )
        layout.addWidget(self.scale_label)

        self.scale_grid = QtWidgets.QGridLayout()
        layout.addLayout(self.scale_grid)

        # Factor
        faclabel = QtWidgets.QLabel('Factor:')
        faclabel.setToolTip(
            "Factor by which to multiply\n"
            "geometric features of this object."
        )
        self.scale_grid.addWidget(faclabel, 0, 0)
        self.scale_entry = FloatEntry2()
        self.scale_entry.set_value(1.0)
        self.scale_grid.addWidget(self.scale_entry, 0, 1)

        # GO Button
        self.scale_button = QtWidgets.QPushButton('Scale')
        self.scale_button.setToolTip(
            "Perform scaling operation."
        )
        self.scale_button.setFixedWidth(40)
        self.scale_grid.addWidget(self.scale_button, 0, 2)

        #### Offset ####
        self.offset_label = QtWidgets.QLabel('<b>Offset:</b>')
        self.offset_label.setToolTip(
            "Change the position of this object."
        )
        layout.addWidget(self.offset_label)

        self.offset_grid = QtWidgets.QGridLayout()
        layout.addLayout(self.offset_grid)

        self.offset_vectorlabel = QtWidgets.QLabel('Vector:')
        self.offset_vectorlabel.setToolTip(
            "Amount by which to move the object\n"
            "in the x and y axes in (x, y) format."
        )
        self.offset_grid.addWidget(self.offset_vectorlabel, 0, 0)
        self.offsetvector_entry = EvalEntry2()
        self.offsetvector_entry.setText("(0.0, 0.0)")
        self.offset_grid.addWidget(self.offsetvector_entry, 0, 1)

        self.offset_button = QtWidgets.QPushButton('Offset')
        self.offset_button.setToolTip(
            "Perform the offset operation."
        )
        self.offset_button.setFixedWidth(40)
        self.offset_grid.addWidget(self.offset_button, 0, 2)

        layout.addStretch()


class GerberObjectUI(ObjectUI):
    """
    User interface for Gerber objects.
    """

    def __init__(self, parent=None):
        ObjectUI.__init__(self, title='Gerber Object', parent=parent)

        # Plot options
        self.plot_options_label = QtWidgets.QLabel("<b>Plot Options:</b>")
        self.custom_box.addWidget(self.plot_options_label)

        grid0 = QtWidgets.QGridLayout()
        grid0.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.custom_box.addLayout(grid0)

        # Plot CB
        self.plot_cb = FCCheckBox(label='Plot   ')
        self.plot_options_label.setToolTip(
            "Plot (show) this object."
        )
        self.plot_cb.setFixedWidth(50)
        grid0.addWidget(self.plot_cb, 0, 0)

        # Solid CB
        self.solid_cb = FCCheckBox(label='Solid   ')
        self.solid_cb.setToolTip(
            "Solid color polygons."
        )
        self.solid_cb.setFixedWidth(50)
        grid0.addWidget(self.solid_cb, 0, 1)

        # Multicolored CB
        self.multicolored_cb = FCCheckBox(label='M-Color   ')
        self.multicolored_cb.setToolTip(
            "Draw polygons in different colors."
        )
        self.multicolored_cb.setFixedWidth(55)
        grid0.addWidget(self.multicolored_cb, 0, 2)

        # Isolation Routing
        self.isolation_routing_label = QtWidgets.QLabel("<b>Isolation Routing:</b>")
        self.isolation_routing_label.setToolTip(
            "Create a Geometry object with\n"
            "toolpaths to cut outside polygons."
        )
        self.custom_box.addWidget(self.isolation_routing_label)

        grid1 = QtWidgets.QGridLayout()
        self.custom_box.addLayout(grid1)
        tdlabel = QtWidgets.QLabel('Tool dia:')
        tdlabel.setToolTip(
            "Diameter of the cutting tool.\n"
            "If you want to have an isolation path\n"
            "inside the actual shape of the Gerber\n"
            "feature, use a negative value for\n"
            "this parameter."
        )
        grid1.addWidget(tdlabel, 0, 0)
        self.iso_tool_dia_entry = LengthEntry()
        grid1.addWidget(self.iso_tool_dia_entry, 0, 1)

        passlabel = QtWidgets.QLabel('Passes:')
        passlabel.setToolTip(
            "Width of the isolation gap in\n"
            "number (integer) of tool widths."
        )
        grid1.addWidget(passlabel, 1, 0)
        self.iso_width_entry = IntEntry()
        grid1.addWidget(self.iso_width_entry, 1, 1)

        overlabel = QtWidgets.QLabel('Pass overlap:')
        overlabel.setToolTip(
            "How much (fraction) of the tool width to overlap each tool pass.\n"
            "Example:\n"
            "A value here of 0.25 means an overlap of 25% from the tool diameter found above."
        )
        grid1.addWidget(overlabel, 2, 0)
        self.iso_overlap_entry = FloatEntry()
        grid1.addWidget(self.iso_overlap_entry, 2, 1)

        # Milling Type Radio Button
        milling_type_label = QtWidgets.QLabel('Milling Type:')
        milling_type_label.setToolTip(
            "Milling type:\n"
            "- climb / best for precision milling and to reduce tool usage\n"
            "- conventional / useful when there is no backlash compensation"
        )
        grid1.addWidget(milling_type_label, 3, 0)
        self.milling_type_radio = RadioSet([{'label': 'Climb', 'value': 'cl'},
                                    {'label': 'Conv.', 'value': 'cv'}])
        grid1.addWidget(self.milling_type_radio, 3, 1)

        # combine all passes CB
        self.combine_passes_cb = FCCheckBox(label='Combine')
        self.combine_passes_cb.setToolTip(
            "Combine all passes into one object"
        )
        grid1.addWidget(self.combine_passes_cb, 4, 0)

        # generate follow
        self.follow_cb = FCCheckBox(label='"Follow" Geo')
        self.follow_cb.setToolTip(
            "Generate a 'Follow' geometry.\n"
            "This means that it will cut through\n"
            "the middle of the trace.\n"
            "Requires that the Gerber file to be\n"
            "loaded with 'follow' parameter."
        )
        grid1.addWidget(self.follow_cb, 4, 1)

        self.gen_iso_label = QtWidgets.QLabel("<b>Generate Isolation Geometry:</b>")
        self.gen_iso_label.setToolTip(
            "Create a Geometry object with toolpaths to cut \n"
            "isolation outside, inside or on both sides of the\n"
            "object. For a Gerber object outside means outside\n"
            "of the Gerber feature and inside means inside of\n"
            "the Gerber feature, if possible at all. This means\n"
            "that only if the Gerber feature has openings inside, they\n"
            "will be isolated. If what is wanted is to cut isolation\n"
            "inside the actual Gerber feature, use a negative tool\n"
            "diameter above."
        )
        self.custom_box.addWidget(self.gen_iso_label)

        hlay_1 = QtWidgets.QHBoxLayout()
        self.custom_box.addLayout(hlay_1)

        hlay_1.addStretch()

        self.generate_ext_iso_button = QtWidgets.QPushButton('Ext Geo')
        self.generate_ext_iso_button.setToolTip(
            "Create the Geometry Object\n"
            "for isolation routing containing\n"
            "only the exteriors geometry."
        )
        self.generate_ext_iso_button.setFixedWidth(60)
        hlay_1.addWidget(self.generate_ext_iso_button)

        self.generate_int_iso_button = QtWidgets.QPushButton('Int Geo')
        self.generate_int_iso_button.setToolTip(
            "Create the Geometry Object\n"
            "for isolation routing containing\n"
            "only the interiors geometry."
        )
        self.generate_int_iso_button.setFixedWidth(60)
        hlay_1.addWidget(self.generate_int_iso_button)

        self.generate_iso_button = QtWidgets.QPushButton('FULL Geo')
        self.generate_iso_button.setToolTip(
            "Create the Geometry Object\n"
            "for isolation routing. It contains both\n"
            "the interiors and exteriors geometry."
        )
        self.generate_iso_button.setFixedWidth(80)
        hlay_1.addWidget(self.generate_iso_button)

        # when the follow checkbox is checked then the exteriors and interiors isolation generation buttons
        # are disabled as is doesn't make sense to have them enabled due of the nature of "follow"
        self.ois_iso = OptionalInputSection(self.follow_cb,
                                            [self.generate_int_iso_button, self.generate_ext_iso_button], logic=False)

        ## Clear non-copper regions
        self.clearcopper_label = QtWidgets.QLabel("<b>Clear non-copper:</b>")
        self.clearcopper_label.setToolTip(
            "Create a Geometry object with\n"
            "toolpaths to cut all non-copper regions."
        )
        self.custom_box.addWidget(self.clearcopper_label)

        self.generate_ncc_button = QtWidgets.QPushButton('Non-Copper Clear Tool')
        self.generate_ncc_button.setToolTip(
            "Create the Geometry Object\n"
            "for non-copper routing."
        )
        self.custom_box.addWidget(self.generate_ncc_button)

        ## Board cutout
        self.board_cutout_label = QtWidgets.QLabel("<b>Board cutout:</b>")
        self.board_cutout_label.setToolTip(
            "Create toolpaths to cut around\n"
            "the PCB and separate it from\n"
            "the original board."
        )
        self.custom_box.addWidget(self.board_cutout_label)

        self.generate_cutout_button = QtWidgets.QPushButton('Cutout Tool')
        self.generate_cutout_button.setToolTip(
            "Generate the geometry for\n"
            "the board cutout."
        )
        self.custom_box.addWidget(self.generate_cutout_button)

        ## Non-copper regions
        self.noncopper_label = QtWidgets.QLabel("<b>Non-copper regions:</b>")
        self.noncopper_label.setToolTip(
            "Create polygons covering the\n"
            "areas without copper on the PCB.\n"
            "Equivalent to the inverse of this\n"
            "object. Can be used to remove all\n"
            "copper from a specified region."
        )
        self.custom_box.addWidget(self.noncopper_label)

        grid4 = QtWidgets.QGridLayout()
        self.custom_box.addLayout(grid4)

        # Margin
        bmlabel = QtWidgets.QLabel('Boundary Margin:')
        bmlabel.setToolTip(
            "Specify the edge of the PCB\n"
            "by drawing a box around all\n"
            "objects with this minimum\n"
            "distance."
        )
        grid4.addWidget(bmlabel, 0, 0)
        self.noncopper_margin_entry = LengthEntry()
        grid4.addWidget(self.noncopper_margin_entry, 0, 1)

        # Rounded corners
        self.noncopper_rounded_cb = FCCheckBox(label="Rounded corners")
        self.noncopper_rounded_cb.setToolTip(
            "Creates a Geometry objects with polygons\n"
            "covering the copper-free areas of the PCB."
        )
        grid4.addWidget(self.noncopper_rounded_cb, 1, 0, 1, 2)

        self.generate_noncopper_button = QtWidgets.QPushButton('Generate Geometry')
        self.custom_box.addWidget(self.generate_noncopper_button)

        ## Bounding box
        self.boundingbox_label = QtWidgets.QLabel('<b>Bounding Box:</b>')
        self.custom_box.addWidget(self.boundingbox_label)

        grid5 = QtWidgets.QGridLayout()
        self.custom_box.addLayout(grid5)

        bbmargin = QtWidgets.QLabel('Boundary Margin:')
        bbmargin.setToolTip(
            "Distance of the edges of the box\n"
            "to the nearest polygon."
        )
        grid5.addWidget(bbmargin, 0, 0)
        self.bbmargin_entry = LengthEntry()
        grid5.addWidget(self.bbmargin_entry, 0, 1)

        self.bbrounded_cb = FCCheckBox(label="Rounded corners")
        self.bbrounded_cb.setToolTip(
            "If the bounding box is \n"
            "to have rounded corners\n"
            "their radius is equal to\n"
            "the margin."
        )
        grid5.addWidget(self.bbrounded_cb, 1, 0, 1, 2)

        self.generate_bb_button = QtWidgets.QPushButton('Generate Geometry')
        self.generate_bb_button.setToolTip(
            "Genrate the Geometry object."
        )
        self.custom_box.addWidget(self.generate_bb_button)


class ExcellonObjectUI(ObjectUI):
    """
    User interface for Excellon objects.
    """

    def __init__(self, parent=None):
        ObjectUI.__init__(self, title='Excellon Object',
                          icon_file='share/drill32.png',
                          parent=parent)

        #### Plot options ####

        self.plot_options_label = QtWidgets.QLabel("<b>Plot Options:</b>")
        self.custom_box.addWidget(self.plot_options_label)

        grid0 = QtWidgets.QGridLayout()
        self.custom_box.addLayout(grid0)
        self.plot_cb = FCCheckBox(label='Plot')
        self.plot_cb.setToolTip(
            "Plot (show) this object."
        )
        grid0.addWidget(self.plot_cb, 0, 0)
        self.solid_cb = FCCheckBox(label='Solid')
        self.solid_cb.setToolTip(
            "Solid circles."
        )
        grid0.addWidget(self.solid_cb, 0, 1)

        # add a frame and inside add a vertical box layout. Inside this vbox layout I add all the Drills widgets
        # this way I can hide/show the frame
        self.drills_frame = QtWidgets.QFrame()
        self.drills_frame.setContentsMargins(0, 0, 0, 0)
        self.custom_box.addWidget(self.drills_frame)
        self.tools_box = QtWidgets.QVBoxLayout()
        self.tools_box.setContentsMargins(0, 0, 0, 0)
        self.drills_frame.setLayout(self.tools_box)

        #### Tools Drills ####
        self.tools_table_label = QtWidgets.QLabel('<b>Tools Table</b>')
        self.tools_table_label.setToolTip(
            "Tools in this Excellon object\n"
            "when are used for drilling."
        )
        self.tools_box.addWidget(self.tools_table_label)

        self.tools_table = FCTable()
        self.tools_box.addWidget(self.tools_table)

        self.tools_table.setColumnCount(4)
        self.tools_table.setHorizontalHeaderLabels(['#', 'Diameter', 'D', 'S'])
        self.tools_table.setSortingEnabled(False)

        self.empty_label = QtWidgets.QLabel('')
        self.tools_box.addWidget(self.empty_label)

        #### Create CNC Job ####
        self.cncjob_label = QtWidgets.QLabel('<b>Create CNC Job</b>')
        self.cncjob_label.setToolTip(
            "Create a CNC Job object\n"
            "for this drill object."
        )
        self.tools_box.addWidget(self.cncjob_label)

        grid1 = QtWidgets.QGridLayout()
        self.tools_box.addLayout(grid1)

        # Cut Z
        cutzlabel = QtWidgets.QLabel('Cut Z:')
        cutzlabel.setToolTip(
            "Drill depth (negative)\n"
            "below the copper surface."
        )
        grid1.addWidget(cutzlabel, 0, 0)
        self.cutz_entry = LengthEntry()
        grid1.addWidget(self.cutz_entry, 0, 1)

        # Travel Z (z_move)
        travelzlabel = QtWidgets.QLabel('Travel Z:')
        travelzlabel.setToolTip(
            "Tool height when travelling\n"
            "across the XY plane."
        )
        grid1.addWidget(travelzlabel, 1, 0)
        self.travelz_entry = LengthEntry()
        grid1.addWidget(self.travelz_entry, 1, 1)

        # Tool change:
        self.toolchange_cb = FCCheckBox("Tool change")
        self.toolchange_cb.setToolTip(
            "Include tool-change sequence\n"
            "in G-Code (Pause for tool change)."
        )
        grid1.addWidget(self.toolchange_cb, 2, 0)

        # Tool change Z:
        toolchzlabel = QtWidgets.QLabel("Tool change Z:")
        toolchzlabel.setToolTip(
            "Z-axis position (height) for\n"
            "tool change."
        )
        grid1.addWidget(toolchzlabel, 3, 0)
        self.toolchangez_entry = LengthEntry()
        grid1.addWidget(self.toolchangez_entry, 3, 1)
        self.ois_tcz_e = OptionalInputSection(self.toolchange_cb, [self.toolchangez_entry])

        # Start move Z:
        startzlabel = QtWidgets.QLabel("Start move Z:")
        startzlabel.setToolTip(
            "Tool height just before starting the work.\n"
            "Delete the value if you don't need this feature."
        )
        grid1.addWidget(startzlabel, 4, 0)
        self.estartz_entry = FloatEntry()
        grid1.addWidget(self.estartz_entry, 4, 1)

        # End move Z:
        endzlabel = QtWidgets.QLabel("End move Z:")
        endzlabel.setToolTip(
            "Z-axis position (height) for\n"
            "the last move."
        )
        grid1.addWidget(endzlabel, 5, 0)
        self.eendz_entry = LengthEntry()
        grid1.addWidget(self.eendz_entry, 5, 1)

        # Excellon Feedrate
        frlabel = QtWidgets.QLabel('Feedrate (Plunge):')
        frlabel.setToolTip(
            "Tool speed while drilling\n"
            "(in units per minute).\n"
            "This is for linear move G01."
        )
        grid1.addWidget(frlabel, 6, 0)
        self.feedrate_entry = LengthEntry()
        grid1.addWidget(self.feedrate_entry, 6, 1)

        # Excellon Rapid Feedrate
        fr_rapid_label = QtWidgets.QLabel('Feedrate Rapids:')
        fr_rapid_label.setToolTip(
            "Tool speed while drilling\n"
            "(in units per minute).\n"
            "This is for the rapid move G00."
        )
        grid1.addWidget(fr_rapid_label, 7, 0)
        self.feedrate_rapid_entry = LengthEntry()
        grid1.addWidget(self.feedrate_rapid_entry, 7, 1)

        # Spindlespeed
        spdlabel = QtWidgets.QLabel('Spindle speed:')
        spdlabel.setToolTip(
            "Speed of the spindle\n"
            "in RPM (optional)"
        )
        grid1.addWidget(spdlabel, 8, 0)
        self.spindlespeed_entry = IntEntry(allow_empty=True)
        grid1.addWidget(self.spindlespeed_entry, 8, 1)

        # Dwell
        self.dwell_cb = FCCheckBox('Dwell:')
        self.dwell_cb.setToolTip(
            "Pause to allow the spindle to reach its\n"
            "speed before cutting."
        )
        self.dwelltime_entry = FCEntry()
        self.dwelltime_entry.setToolTip(
            "Number of milliseconds for spindle to dwell."
        )
        grid1.addWidget(self.dwell_cb, 9, 0)
        grid1.addWidget(self.dwelltime_entry, 9, 1)

        self.ois_dwell = OptionalInputSection(self.dwell_cb, [self.dwelltime_entry])

        # postprocessor selection
        pp_excellon_label = QtWidgets.QLabel("Postprocessor")
        pp_excellon_label.setToolTip(
            "The json file that dictates\n"
            "gcode output."
        )
        self.tools_box.addWidget(pp_excellon_label)
        self.pp_excellon_name_cb = FCComboBox()
        self.pp_excellon_name_cb.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.tools_box.addWidget(self.pp_excellon_name_cb)

        choose_tools_label = QtWidgets.QLabel(
            "Select from the Tools Table above\n"
            "the tools you want to include."
        )
        self.tools_box.addWidget(choose_tools_label)

        #### Choose what to use for Gcode creation: Drills, Slots or Both
        gcode_box = QtWidgets.QFormLayout()
        gcode_type_label = QtWidgets.QLabel('<b>Type:    </b>')
        gcode_type_label.setToolTip(
            "Choose what to use for GCode generation:\n"
            "'Drills', 'Slots' or 'Both'.\n"
            "When choosing 'Slots' or 'Both', slots will be\n"
            "converted to a series of drills."
        )
        self.excellon_gcode_type_radio = RadioSet([{'label': 'Drills', 'value': 'drills'},
                                    {'label': 'Slots', 'value': 'slots'},
                                    {'label': 'Both', 'value': 'both'}])
        gcode_box.addRow(gcode_type_label, self.excellon_gcode_type_radio)
        self.tools_box.addLayout(gcode_box)

        # temporary action until I finish the feature
        self.excellon_gcode_type_radio.setEnabled(False)

        self.generate_cnc_button = QtWidgets.QPushButton('Create GCode')
        self.generate_cnc_button.setToolTip(
            "Generate the CNC Job."
        )
        self.tools_box.addWidget(self.generate_cnc_button)

        #### Milling Holes Drills####
        self.mill_hole_label = QtWidgets.QLabel('<b>Mill Holes</b>')
        self.mill_hole_label.setToolTip(
            "Create Geometry for milling holes."
        )
        self.tools_box.addWidget(self.mill_hole_label)

        self.choose_tools_label2 = QtWidgets.QLabel(
            "Select from the Tools Table above\n"
            " the hole dias that are to be milled."
        )
        self.tools_box.addWidget(self.choose_tools_label2)

        grid2 = QtWidgets.QGridLayout()
        self.tools_box.addLayout(grid2)
        self.tdlabel = QtWidgets.QLabel('Drills Tool dia:')
        self.tdlabel.setToolTip(
            "Diameter of the cutting tool."
        )
        grid2.addWidget(self.tdlabel, 0, 0)
        self.tooldia_entry = LengthEntry()
        grid2.addWidget(self.tooldia_entry, 0, 1)
        self.generate_milling_button = QtWidgets.QPushButton('Mill Drills Geo')
        self.generate_milling_button.setToolTip(
            "Create the Geometry Object\n"
            "for milling DRILLS toolpaths."
        )
        grid2.addWidget(self.generate_milling_button, 0, 2)

        grid3 = QtWidgets.QGridLayout()
        self.custom_box.addLayout(grid3)
        self.stdlabel = QtWidgets.QLabel('Slots Tool dia:')
        self.stdlabel.setToolTip(
            "Diameter of the cutting tool."
        )
        grid3.addWidget(self.stdlabel, 0, 0)
        self.slot_tooldia_entry = LengthEntry()
        grid3.addWidget(self.slot_tooldia_entry, 0, 1)
        self.generate_milling_slots_button = QtWidgets.QPushButton('Mill Slots Geo')
        self.generate_milling_slots_button.setToolTip(
            "Create the Geometry Object\n"
            "for milling SLOTS toolpaths."
        )
        grid3.addWidget(self.generate_milling_slots_button, 0, 2)

    def hide_drills(self, state=True):
        if state is True:
            self.drills_frame.hide()
        else:
            self.drills_frame.show()


class GeometryObjectUI(ObjectUI):
    """
    User interface for Geometry objects.
    """

    def __init__(self, parent=None):
        super(GeometryObjectUI, self).__init__(title='Geometry Object', icon_file='share/geometry32.png', parent=parent)

        # Plot options
        # self.plot_options_label = QtWidgets.QLabel("<b>Plot Options:</b>")
        # self.custom_box.addWidget(self.plot_options_label)

        # add a frame and inside add a vertical box layout. Inside this vbox layout I add all the Tools widgets
        # this way I can hide/show the frame
        self.geo_tools_frame = QtWidgets.QFrame()
        self.geo_tools_frame.setContentsMargins(0, 0, 0, 0)
        self.custom_box.addWidget(self.geo_tools_frame)
        self.geo_tools_box = QtWidgets.QVBoxLayout()
        self.geo_tools_box.setContentsMargins(0, 0, 0, 0)
        self.geo_tools_frame.setLayout(self.geo_tools_box)

        hlay_plot = QtWidgets.QHBoxLayout()
        self.geo_tools_box.addLayout(hlay_plot)

        #### Tools ####
        self.tools_table_label = QtWidgets.QLabel('<b>Tools Table</b>')
        self.tools_table_label.setToolTip(
            "Tools in this Geometry object used for cutting.\n"
            "The 'Offset' entry will set an offset for the cut.\n"
            "'Offset' can be inside, outside, on path (none) and custom.\n"
            "'Type' entry is only informative and it allow to know the \n"
            "intent of using the current tool. \n"
            "It can be Rough(ing), Finish(ing) or Iso(lation).\n"
            "The 'Tool type'(TT) can be circular with 1 to 4 teeths(C1..C4),\n"
            "ball(B), or V-Shaped(V). \n"
            "When V-shaped is selected the 'Type' entry is automatically \n"
            "set to Isolation, the CutZ parameter in the UI form is\n"
            "grayed out and Cut Z is automatically calculated from the newly \n"
            "showed UI form entries named V-Tip Dia and V-Tip Angle."
        )
        hlay_plot.addWidget(self.tools_table_label)

        # Plot CB
        # self.plot_cb = QtWidgets.QCheckBox('Plot')
        self.plot_cb = FCCheckBox('Plot Object')
        self.plot_cb.setToolTip(
            "Plot (show) this object."
        )
        self.plot_cb.setLayoutDirection(QtCore.Qt.RightToLeft)
        hlay_plot.addStretch()
        hlay_plot.addWidget(self.plot_cb)

        self.geo_tools_table = FCTable()
        self.geo_tools_box.addWidget(self.geo_tools_table)
        self.geo_tools_table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)

        self.geo_tools_table.setColumnCount(7)
        self.geo_tools_table.setColumnWidth(0, 20)
        self.geo_tools_table.setHorizontalHeaderLabels(['#', 'Dia', 'Offset', 'Type', 'TT', '', 'P'])
        self.geo_tools_table.setColumnHidden(5, True)

        self.geo_tools_table.horizontalHeaderItem(0).setToolTip(
            "This is the Tool Number.\n"
            "When ToolChange is checked, on toolchange event this value\n"
            "will be showed as a T1, T2 ... Tn")
        self.geo_tools_table.horizontalHeaderItem(1).setToolTip(
            "Tool Diameter. It's value (in current FlatCAM units) \n"
            "is the cut width into the material.")
        self.geo_tools_table.horizontalHeaderItem(2).setToolTip(
            "The value for the Offset can be:\n"
            "- Path -> There is no offset, the tool cut will be done through the geometry line.\n"
            "- In(side) -> The tool cut will follow the geometry inside. It will create a 'pocket'.\n"
            "- Out(side) -> The tool cut will follow the geometry line on the outside.")
        self.geo_tools_table.horizontalHeaderItem(3).setToolTip(
            "The (Operation) Type has only informative value. Usually the UI form values \n"
            "are choosed based on the operation type and this will serve as a reminder.\n"
            "Can be 'Roughing', 'Finishing' or 'Isolation'.\n"
            "For Roughing we may choose a lower Feedrate and multiDepth cut.\n"
            "For Finishing we may choose a higher Feedrate, without multiDepth.\n"
            "For Isolation we need a lower Feedrate as it use a milling bit with a fine tip.")
        self.geo_tools_table.horizontalHeaderItem(4).setToolTip(
            "The Tool Type (TT) can be:\n"
            "- Circular with 1 ... 4 teeth -> it is informative only. Being circular the cut width in material\n"
            "is exactly the tool diameter.\n"
            "- Ball -> informative only and make reference to the Ball type endmill.\n"
            "- V-Shape -> it will disable de Z-Cut parameter in the UI form and enable two additional UI form\n"
            "fields: V-Tip Dia and V-Tip Angle. Adjusting those two values will adjust the Z-Cut parameter such\n"
            "as the cut width into material will be equal with the value in the Tool Diameter column of this table.\n"
            "Choosing the V-Shape Tool Type automatically will select the Operation Type as Isolation.")
        self.geo_tools_table.horizontalHeaderItem(6).setToolTip(
            "Plot column. It is visible only for MultiGeo geometries, meaning geometries that holds the geometry\n"
            "data into the tools. For those geometries, deleting the tool will delete the geometry data also,\n"
            "so be WARNED. From the checkboxes on each row it can be enabled/disabled the plot on canvas\n"
            "for the corresponding tool.")

        # self.geo_tools_table.setSortingEnabled(False)
        # self.geo_tools_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

        # Tool Offset
        self.grid1 = QtWidgets.QGridLayout()
        self.geo_tools_box.addLayout(self.grid1)

        self.tool_offset_lbl = QtWidgets.QLabel('Tool Offset:')
        self.tool_offset_lbl.setToolTip(
            "The value to offset the cut when \n"
            "the Offset type selected is 'Offset'.\n"
            "The value can be positive for 'outside'\n"
            "cut and negative for 'inside' cut."
        )
        self.grid1.addWidget(self.tool_offset_lbl, 0, 0)
        self.tool_offset_entry = FloatEntry()
        spacer_lbl = QtWidgets.QLabel(" ")
        spacer_lbl.setFixedWidth(80)

        self.grid1.addWidget(self.tool_offset_entry, 0, 1)
        self.grid1.addWidget(spacer_lbl, 0, 2)

        #### Add a new Tool ####
        hlay = QtWidgets.QHBoxLayout()
        self.geo_tools_box.addLayout(hlay)

        # self.addtool_label = QtWidgets.QLabel('<b>Tool</b>')
        # self.addtool_label.setToolTip(
        #     "Add/Copy/Delete a tool to the tool list."
        # )
        self.addtool_entry_lbl = QtWidgets.QLabel('<b>Tool Dia:</b>')
        self.addtool_entry_lbl.setToolTip(
            "Diameter for the new tool"
        )
        self.addtool_entry = FloatEntry()

        # hlay.addWidget(self.addtool_label)
        # hlay.addStretch()
        hlay.addWidget(self.addtool_entry_lbl)
        hlay.addWidget(self.addtool_entry)

        grid2 = QtWidgets.QGridLayout()
        self.geo_tools_box.addLayout(grid2)

        self.addtool_btn = QtWidgets.QPushButton('Add')
        self.addtool_btn.setToolTip(
            "Add a new tool to the Tool Table\n"
            "with the diameter specified above."
        )

        self.copytool_btn = QtWidgets.QPushButton('Copy')
        self.copytool_btn.setToolTip(
            "Copy a selection of tools in the Tool Table\n"
            "by first selecting a row in the Tool Table."
        )

        self.deltool_btn = QtWidgets.QPushButton('Delete')
        self.deltool_btn.setToolTip(
            "Delete a selection of tools in the Tool Table\n"
            "by first selecting a row in the Tool Table."
        )

        grid2.addWidget(self.addtool_btn, 0, 0)
        grid2.addWidget(self.copytool_btn, 0, 1)
        grid2.addWidget(self.deltool_btn, 0,2)

        self.empty_label = QtWidgets.QLabel('')
        self.geo_tools_box.addWidget(self.empty_label)

        #-----------------------------------
        # Create CNC Job
        #-----------------------------------
        #### Tools Data ####
        self.tool_data_label = QtWidgets.QLabel('<b>Tool Data</b>')
        self.tool_data_label.setToolTip(
            "The data used for creating GCode.\n"
            "Each tool store it's own set of such data."
        )
        self.geo_tools_box.addWidget(self.tool_data_label)

        self.grid3 = QtWidgets.QGridLayout()
        self.geo_tools_box.addLayout(self.grid3)

        # Tip Dia
        self.tipdialabel = QtWidgets.QLabel('V-Tip Dia:')
        self.tipdialabel.setToolTip(
            "The tip diameter for V-Shape Tool"
        )
        self.grid3.addWidget(self.tipdialabel, 1, 0)
        self.tipdia_entry = LengthEntry()
        self.grid3.addWidget(self.tipdia_entry, 1, 1)

        # Tip Angle
        self.tipanglelabel = QtWidgets.QLabel('V-Tip Angle:')
        self.tipanglelabel.setToolTip(
            "The tip angle for V-Shape Tool.\n"
            "In degree."
        )
        self.grid3.addWidget(self.tipanglelabel, 2, 0)
        self.tipangle_entry = LengthEntry()
        self.grid3.addWidget(self.tipangle_entry, 2, 1)

        # Cut Z
        cutzlabel = QtWidgets.QLabel('Cut Z:')
        cutzlabel.setToolTip(
            "Cutting depth (negative)\n"
            "below the copper surface."
        )
        self.grid3.addWidget(cutzlabel, 3, 0)
        self.cutz_entry = LengthEntry()
        self.grid3.addWidget(self.cutz_entry, 3, 1)

        # Multi-pass
        self.mpass_cb = FCCheckBox("Multi-Depth:")
        self.mpass_cb.setToolTip(
            "Use multiple passes to limit\n"
            "the cut depth in each pass. Will\n"
            "cut multiple times until Cut Z is\n"
            "reached.\n"
            "To the right, input the depth of \n"
            "each pass (positive value)."
        )
        self.grid3.addWidget(self.mpass_cb, 4, 0)


        self.maxdepth_entry = LengthEntry()
        self.maxdepth_entry.setToolTip(
            "Depth of each pass (positive)."
        )
        self.grid3.addWidget(self.maxdepth_entry, 4, 1)

        self.ois_mpass_geo = OptionalInputSection(self.mpass_cb, [self.maxdepth_entry])

        # Travel Z
        travelzlabel = QtWidgets.QLabel('Travel Z:')
        travelzlabel.setToolTip(
            "Height of the tool when\n"
            "moving without cutting."
        )
        self.grid3.addWidget(travelzlabel, 5, 0)
        self.travelz_entry = LengthEntry()
        self.grid3.addWidget(self.travelz_entry, 5, 1)

        # Tool change:

        self.toolchzlabel = QtWidgets.QLabel("Tool change Z:")
        self.toolchzlabel.setToolTip(
            "Z-axis position (height) for\n"
            "tool change."
        )
        self.toolchangeg_cb = FCCheckBox("Tool change")
        self.toolchangeg_cb.setToolTip(
            "Include tool-change sequence\n"
            "in G-Code (Pause for tool change)."
        )
        self.toolchangez_entry = LengthEntry()

        self.grid3.addWidget(self.toolchangeg_cb, 6, 0)
        self.grid3.addWidget(self.toolchzlabel, 7, 0)
        self.grid3.addWidget(self.toolchangez_entry, 7, 1)
        self.ois_tcz_geo = OptionalInputSection(self.toolchangeg_cb, [self.toolchangez_entry])

        # The Z value for the start move
        # startzlabel = QtWidgets.QLabel('Start move Z:')
        # startzlabel.setToolTip(
        #     "Tool height just before starting the work.\n"
        #     "Delete the value if you don't need this feature."
        #
        # )
        # self.grid3.addWidget(startzlabel, 8, 0)
        # self.gstartz_entry = FloatEntry()
        # self.grid3.addWidget(self.gstartz_entry, 8, 1)

        # The Z value for the end move
        endzlabel = QtWidgets.QLabel('End move Z:')
        endzlabel.setToolTip(
            "This is the height (Z) at which the CNC\n"
            "will go as the last move."
        )
        self.grid3.addWidget(endzlabel, 9, 0)
        self.gendz_entry = LengthEntry()
        self.grid3.addWidget(self.gendz_entry, 9, 1)

        # Feedrate X-Y
        frlabel = QtWidgets.QLabel('Feed Rate X-Y:')
        frlabel.setToolTip(
            "Cutting speed in the XY\n"
            "plane in units per minute"
        )
        self.grid3.addWidget(frlabel, 10, 0)
        self.cncfeedrate_entry = LengthEntry()
        self.grid3.addWidget(self.cncfeedrate_entry, 10, 1)

        # Feedrate Z (Plunge)
        frzlabel = QtWidgets.QLabel('Feed Rate Z (Plunge):')
        frzlabel.setToolTip(
            "Cutting speed in the Z\n"
            "plane in units per minute"
        )
        self.grid3.addWidget(frzlabel, 11, 0)
        self.cncplunge_entry = LengthEntry()
        self.grid3.addWidget(self.cncplunge_entry, 11, 1)

        # Feedrate rapids
        fr_rapidlabel = QtWidgets.QLabel('Feed Rate Rapids:')
        fr_rapidlabel.setToolTip(
            "Cutting speed in the XY\n"
            "plane in units per minute\n"
            "for the rapid movements"
        )
        self.grid3.addWidget(fr_rapidlabel, 12, 0)
        self.cncfeedrate_rapid_entry = LengthEntry()
        self.grid3.addWidget(self.cncfeedrate_rapid_entry, 12, 1)

        # Cut over 1st point in path
        self.extracut_cb = FCCheckBox('Cut over 1st pt')
        self.extracut_cb.setToolTip(
            "In order to remove possible\n"
            "copper leftovers where first cut\n"
            "meet with last cut, we generate an\n"
            "extended cut over the first cut section."
        )
        self.grid3.addWidget(self.extracut_cb, 13, 0)

        # Spindlespeed
        spdlabel = QtWidgets.QLabel('Spindle speed:')
        spdlabel.setToolTip(
            "Speed of the spindle\n"
            "in RPM (optional)"
        )
        self.grid3.addWidget(spdlabel, 14, 0)
        self.cncspindlespeed_entry = IntEntry(allow_empty=True)
        self.grid3.addWidget(self.cncspindlespeed_entry, 14, 1)

        # Dwell
        self.dwell_cb = FCCheckBox('Dwell:')
        self.dwell_cb.setToolTip(
            "Pause to allow the spindle to reach its\n"
            "speed before cutting."
        )
        self.dwelltime_entry = FCEntry()
        self.dwelltime_entry.setToolTip(
            "Number of milliseconds for spindle to dwell."
        )
        self.grid3.addWidget(self.dwell_cb, 15, 0)
        self.grid3.addWidget(self.dwelltime_entry, 15, 1)

        self.ois_dwell_geo = OptionalInputSection(self.dwell_cb, [self.dwelltime_entry])

        # postprocessor selection
        pp_label = QtWidgets.QLabel("PostProcessor:")
        pp_label.setToolTip(
            "The Postprocessor file that dictates\n"
            "Gcode output."
        )
        self.grid3.addWidget(pp_label, 16, 0)
        self.pp_geometry_name_cb = FCComboBox()
        self.pp_geometry_name_cb.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.grid3.addWidget(self.pp_geometry_name_cb, 16, 1)

        warning_lbl = QtWidgets.QLabel(
            "Add at least one tool in the tool-table.\n"
            "Click the header to select all, or Ctrl + LMB\n"
            "for custom selection of tools.")
        self.grid3.addWidget(warning_lbl, 17, 0, 1, 2)

        # Button
        self.generate_cnc_button = QtWidgets.QPushButton('Generate')
        self.generate_cnc_button.setToolTip(
            "Generate the CNC Job object."
        )
        self.geo_tools_box.addWidget(self.generate_cnc_button)

        #------------------------------
        # Paint area
        #------------------------------
        self.paint_label = QtWidgets.QLabel('<b>Paint Area:</b>')
        self.paint_label.setToolTip(
            "Creates tool paths to cover the\n"
            "whole area of a polygon (remove\n"
            "all copper). You will be asked\n"
            "to click on the desired polygon."
        )
        self.geo_tools_box.addWidget(self.paint_label)

        # GO Button
        self.paint_tool_button = QtWidgets.QPushButton('Paint Tool')
        self.paint_tool_button.setToolTip(
            "Launch Paint Tool in Tools Tab."
        )
        self.geo_tools_box.addWidget(self.paint_tool_button)


class CNCObjectUI(ObjectUI):
    """
    User interface for CNCJob objects.
    """

    def __init__(self, parent=None):
        """
        Creates the user interface for CNCJob objects. GUI elements should
        be placed in ``self.custom_box`` to preserve the layout.
        """

        ObjectUI.__init__(self, title='CNC Job Object', icon_file='share/cnc32.png', parent=parent)

        # Scale and offset ans skew are not available for CNCJob objects.
        # Hiding from the GUI.
        for i in range(0, self.scale_grid.count()):
            self.scale_grid.itemAt(i).widget().hide()
        self.scale_label.hide()
        self.scale_button.hide()


        for i in range(0, self.offset_grid.count()):
            self.offset_grid.itemAt(i).widget().hide()
        self.offset_label.hide()
        self.offset_button.hide()

        ## Plot options
        self.plot_options_label = QtWidgets.QLabel("<b>Plot Options:</b>")
        self.custom_box.addWidget(self.plot_options_label)

        # # Tool dia for plot
        # tdlabel = QtWidgets.QLabel('Tool dia:')
        # tdlabel.setToolTip(
        #     "Diameter of the tool to be\n"
        #     "rendered in the plot."
        # )
        # grid0.addWidget(tdlabel, 1, 0)
        # self.tooldia_entry = LengthEntry()
        # grid0.addWidget(self.tooldia_entry, 1, 1)

        hlay = QtWidgets.QHBoxLayout()
        self.custom_box.addLayout(hlay)

        # CNC Tools Table for plot
        self.cnc_tools_table_label = QtWidgets.QLabel('<b>CNC Tools Table</b>')
        self.cnc_tools_table_label.setToolTip(
            "Tools in this CNCJob object used for cutting.\n"
            "The tool diameter is used for plotting on canvas.\n"
            "The 'Offset' entry will set an offset for the cut.\n"
            "'Offset' can be inside, outside, on path (none) and custom.\n"
            "'Type' entry is only informative and it allow to know the \n"
            "intent of using the current tool. \n"
            "It can be Rough(ing), Finish(ing) or Iso(lation).\n"
            "The 'Tool type'(TT) can be circular with 1 to 4 teeths(C1..C4),\n"
            "ball(B), or V-Shaped(V)."
        )
        hlay.addWidget(self.cnc_tools_table_label)

        # Plot CB
        # self.plot_cb = QtWidgets.QCheckBox('Plot')
        self.plot_cb = FCCheckBox('Plot Object')
        self.plot_cb.setToolTip(
            "Plot (show) this object."
        )
        self.plot_cb.setLayoutDirection(QtCore.Qt.RightToLeft)
        hlay.addStretch()
        hlay.addWidget(self.plot_cb)

        self.cnc_tools_table = FCTable()
        self.custom_box.addWidget(self.cnc_tools_table)

        # self.cnc_tools_table.setColumnCount(4)
        # self.cnc_tools_table.setHorizontalHeaderLabels(['#', 'Dia', 'Plot', ''])
        # self.cnc_tools_table.setColumnHidden(3, True)
        self.cnc_tools_table.setColumnCount(7)
        self.cnc_tools_table.setColumnWidth(0, 20)
        self.cnc_tools_table.setHorizontalHeaderLabels(['#', 'Dia', 'Offset', 'Type', 'TT', '', 'P'])
        self.cnc_tools_table.setColumnHidden(5, True)

        # Update plot button
        self.updateplot_button = QtWidgets.QPushButton('Update Plot')
        self.updateplot_button.setToolTip(
            "Update the plot."
        )
        self.custom_box.addWidget(self.updateplot_button)

        ##################
        ## Export G-Code
        ##################
        self.export_gcode_label = QtWidgets.QLabel("<b>Export CNC Code:</b>")
        self.export_gcode_label.setToolTip(
            "Export and save G-Code to\n"
            "make this object to a file."
        )
        self.custom_box.addWidget(self.export_gcode_label)

        # Prepend text to Gerber
        prependlabel = QtWidgets.QLabel('Prepend to CNC Code:')
        prependlabel.setToolTip(
            "Type here any G-Code commands you would\n"
            "like to add to the beginning of the generated file."
        )
        self.custom_box.addWidget(prependlabel)

        self.prepend_text = FCTextArea()
        self.custom_box.addWidget(self.prepend_text)

        # Append text to Gerber
        appendlabel = QtWidgets.QLabel('Append to CNC Code')
        appendlabel.setToolTip(
            "Type here any G-Code commands you would\n"
            "like to append to the generated file.\n"
            "I.e.: M2 (End of program)"
        )
        self.custom_box.addWidget(appendlabel)

        self.append_text = FCTextArea()
        self.custom_box.addWidget(self.append_text)

        h_lay = QtWidgets.QHBoxLayout()
        h_lay.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.custom_box.addLayout(h_lay)

        # Edit GCode Button
        self.modify_gcode_button = QtWidgets.QPushButton('Edit CNC Code')
        self.modify_gcode_button.setToolTip(
            "Opens TAB to modify/print G-Code\n"
            "file."
        )

        # GO Button
        self.export_gcode_button = QtWidgets.QPushButton('Save CNC Code')
        self.export_gcode_button.setToolTip(
            "Opens dialog to save G-Code\n"
            "file."
        )

        h_lay.addWidget(self.modify_gcode_button)
        h_lay.addWidget(self.export_gcode_button)
        # self.custom_box.addWidget(self.export_gcode_button)

# end of file
