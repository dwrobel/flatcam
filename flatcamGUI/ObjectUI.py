# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# Author: Juan Pablo Caram (c)                             #
# Date: 2/5/2014                                           #
# MIT Licence                                              #
# ##########################################################

# ##########################################################
# File Modified (major mod): Marius Adrian Stanciu         #
# Date: 3/10/2019                                          #
# ##########################################################

from flatcamGUI.GUIElements import *
import sys

import gettext
import FlatCAMTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

settings = QtCore.QSettings("Open Source", "FlatCAM")
if settings.contains("machinist"):
    machinist_setting = settings.value('machinist', type=int)
else:
    machinist_setting = 0


class ObjectUI(QtWidgets.QWidget):
    """
    Base class for the UI of FlatCAM objects. Deriving classes should
    put UI elements in ObjectUI.custom_box (QtWidgets.QLayout).
    """

    def __init__(self, icon_file='share/flatcam_icon32.png', title=_('FlatCAM Object'), parent=None, common=True, 
                 decimals=4):
        QtWidgets.QWidget.__init__(self, parent=parent)

        self.decimals = decimals

        theme_settings = QtCore.QSettings("Open Source", "FlatCAM")
        if theme_settings.contains("theme"):
            theme = theme_settings.value('theme', type=str)
        else:
            theme = 'white'

        if theme == 'white':
            self.resource_loc = 'share'
        else:
            self.resource_loc = 'share'

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        # ## Page Title box (spacing between children)
        self.title_box = QtWidgets.QHBoxLayout()
        layout.addLayout(self.title_box)

        # ## Page Title icon
        pixmap = QtGui.QPixmap(icon_file.replace('share', self.resource_loc))
        self.icon = QtWidgets.QLabel()
        self.icon.setPixmap(pixmap)
        self.title_box.addWidget(self.icon, stretch=0)

        # ## Title label
        self.title_label = QtWidgets.QLabel("<font size=5><b>%s</b></font>" % title)
        self.title_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.title_box.addWidget(self.title_label, stretch=1)

        # ## App Level label
        self.level = QtWidgets.QLabel("")
        self.level.setToolTip(
            _(
                "BASIC is suitable for a beginner. Many parameters\n"
                "are hidden from the user in this mode.\n"
                "ADVANCED mode will make available all parameters.\n\n"
                "To change the application LEVEL, go to:\n"
                "Edit -> Preferences -> General and check:\n"
                "'APP. LEVEL' radio button."
            )
        )
        self.level.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.title_box.addWidget(self.level)

        # ## Box box for custom widgets
        # This gets populated in offspring implementations.
        self.custom_box = QtWidgets.QVBoxLayout()
        layout.addLayout(self.custom_box)

        # ###########################
        # ## Common to all objects ##
        # ###########################
        if common is True:
            self.common_grid = QtWidgets.QGridLayout()
            self.common_grid.setColumnStretch(0, 1)
            self.common_grid.setColumnStretch(1, 0)
            layout.addLayout(self.common_grid)

            # self.common_grid.addWidget(QtWidgets.QLabel(''), 1, 0, 1, 2)
            separator_line = QtWidgets.QFrame()
            separator_line.setFrameShape(QtWidgets.QFrame.HLine)
            separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
            self.common_grid.addWidget(separator_line, 1, 0, 1, 2)

            self.transform_label = QtWidgets.QLabel('<b>%s</b>' % _('Transformations'))
            self.transform_label.setToolTip(
                _("Geometrical transformations of the current object.")
            )

            self.common_grid.addWidget(self.transform_label, 2, 0, 1, 2)

            # ### Scale ####
            self.scale_entry = FCEntry()
            self.scale_entry.set_value(1.0)
            self.scale_entry.setToolTip(
                _("Factor by which to multiply\n"
                  "geometric features of this object.\n"
                  "Expressions are allowed. E.g: 1/25.4")
            )
            # GO Button
            self.scale_button = QtWidgets.QPushButton(_('Scale'))
            self.scale_button.setToolTip(
                _("Perform scaling operation.")
            )
            self.scale_button.setMinimumWidth(70)

            self.common_grid.addWidget(self.scale_entry, 3, 0)
            self.common_grid.addWidget(self.scale_button, 3, 1)

            # ### Offset ####
            self.offsetvector_entry = EvalEntry2()
            self.offsetvector_entry.setText("(0.0, 0.0)")
            self.offsetvector_entry.setToolTip(
                _("Amount by which to move the object\n"
                  "in the x and y axes in (x, y) format.\n"
                  "Expressions are allowed. E.g: (1/3.2, 0.5*3)")
            )

            self.offset_button = QtWidgets.QPushButton(_('Offset'))
            self.offset_button.setToolTip(
                _("Perform the offset operation.")
            )
            self.offset_button.setMinimumWidth(70)

            self.common_grid.addWidget(self.offsetvector_entry, 4, 0)
            self.common_grid.addWidget(self.offset_button, 4, 1)

        layout.addStretch()


class GerberObjectUI(ObjectUI):
    """
    User interface for Gerber objects.
    """

    def __init__(self, decimals, parent=None):
        ObjectUI.__init__(self, title=_('Gerber Object'), parent=parent, decimals=decimals)
        self.decimals = decimals

        self.custom_box.addWidget(QtWidgets.QLabel(''))

        # Plot options
        grid0 = QtWidgets.QGridLayout()
        grid0.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.custom_box.addLayout(grid0)
        grid0.setColumnStretch(0, 0)
        grid0.setColumnStretch(1, 1)

        # Plot CB
        self.plot_cb = FCCheckBox()
        self.plot_cb.setToolTip(
            _("Plot (show) this object.")
        )
        plot_label = QtWidgets.QLabel('<b>%s:</b>' % _("Plot"))

        grid0.addWidget(plot_label, 0, 0)
        grid0.addWidget(self.plot_cb, 0, 1)

        self.plot_options_label = QtWidgets.QLabel("<b>%s:</b>" % _("Plot Options"))
        self.plot_options_label.setMinimumWidth(90)

        grid0.addWidget(self.plot_options_label, 1, 0)

        # Solid CB
        self.solid_cb = FCCheckBox(label=_('Solid'))
        self.solid_cb.setToolTip(
            _("Solid color polygons.")
        )
        self.solid_cb.setMinimumWidth(50)
        grid0.addWidget(self.solid_cb, 1, 1)

        # Multicolored CB
        self.multicolored_cb = FCCheckBox(label=_('Multi-Color'))
        self.multicolored_cb.setToolTip(
            _("Draw polygons in different colors.")
        )
        self.multicolored_cb.setMinimumWidth(55)
        grid0.addWidget(self.multicolored_cb, 1, 2)

        # ## Object name
        self.name_hlay = QtWidgets.QHBoxLayout()
        self.custom_box.addLayout(self.name_hlay)
        name_label = QtWidgets.QLabel("<b>%s:</b>" % _("Name"))
        self.name_entry = FCEntry()
        self.name_entry.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.name_hlay.addWidget(name_label)
        self.name_hlay.addWidget(self.name_entry)

        hlay_plot = QtWidgets.QHBoxLayout()
        self.custom_box.addLayout(hlay_plot)

        # ### Gerber Apertures ####
        self.apertures_table_label = QtWidgets.QLabel('<b>%s:</b>' % _('Apertures'))
        self.apertures_table_label.setToolTip(
            _("Apertures Table for the Gerber Object.")
        )
        self.apertures_table_label.setMinimumWidth(90)

        hlay_plot.addWidget(self.apertures_table_label)

        # Aperture Table Visibility CB
        self.aperture_table_visibility_cb = FCCheckBox()
        self.aperture_table_visibility_cb.setToolTip(
            _("Toggle the display of the Gerber Apertures Table.\n"
              "When unchecked, it will delete all mark shapes\n"
              "that are drawn on canvas.")
        )
        # self.aperture_table_visibility_cb.setLayoutDirection(QtCore.Qt.RightToLeft)
        hlay_plot.addWidget(self.aperture_table_visibility_cb)

        hlay_plot.addStretch()

        # Aperture Mark all CB
        self.mark_all_cb = FCCheckBox(_('Mark All'))
        self.mark_all_cb.setToolTip(
            _("When checked it will display all the apertures.\n"
              "When unchecked, it will delete all mark shapes\n"
              "that are drawn on canvas.")

        )
        self.mark_all_cb.setLayoutDirection(QtCore.Qt.RightToLeft)
        hlay_plot.addWidget(self.mark_all_cb)

        self.apertures_table = FCTable()
        self.custom_box.addWidget(self.apertures_table)

        self.apertures_table.setColumnCount(6)
        self.apertures_table.setHorizontalHeaderLabels(['#', _('Code'), _('Type'), _('Size'), _('Dim'), 'M'])
        self.apertures_table.setSortingEnabled(False)

        self.apertures_table.horizontalHeaderItem(0).setToolTip(
            _("Index"))
        self.apertures_table.horizontalHeaderItem(1).setToolTip(
            _("Aperture Code"))
        self.apertures_table.horizontalHeaderItem(2).setToolTip(
            _("Type of aperture: circular, rectangle, macros etc"))
        self.apertures_table.horizontalHeaderItem(4).setToolTip(
            _("Aperture Size:"))
        self.apertures_table.horizontalHeaderItem(4).setToolTip(
            _("Aperture Dimensions:\n"
              " - (width, height) for R, O type.\n"
              " - (dia, nVertices) for P type"))
        self.apertures_table.horizontalHeaderItem(5).setToolTip(
            _("Mark the aperture instances on canvas."))
        # self.apertures_table.setColumnHidden(5, True)

        # start with apertures table hidden
        self.apertures_table.setVisible(False)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.custom_box.addWidget(separator_line)

        # Isolation Routing
        self.isolation_routing_label = QtWidgets.QLabel("<b>%s</b>" % _("Isolation Routing"))
        self.isolation_routing_label.setToolTip(
            _("Create a Geometry object with\n"
              "toolpaths to cut outside polygons.")
        )
        self.custom_box.addWidget(self.isolation_routing_label)

        # ###########################################
        # ########## NEW GRID #######################
        # ###########################################

        grid1 = QtWidgets.QGridLayout()
        self.custom_box.addLayout(grid1)
        grid1.setColumnStretch(0, 0)
        grid1.setColumnStretch(1, 1)
        grid1.setColumnStretch(2, 1)

        # Tool Type
        self.tool_type_label = QtWidgets.QLabel('%s:' % _('Tool Type'))
        self.tool_type_label.setToolTip(
            _("Choose what tool to use for Gerber isolation:\n"
              "'Circular' or 'V-shape'.\n"
              "When the 'V-shape' is selected then the tool\n"
              "diameter will depend on the chosen cut depth.")
        )
        self.tool_type_radio = RadioSet([{'label': _('Circular'), 'value': 'circular'},
                                         {'label': _('V-Shape'), 'value': 'v'}])

        grid1.addWidget(self.tool_type_label, 0, 0)
        grid1.addWidget(self.tool_type_radio, 0, 1, 1, 2)

        # Tip Dia
        self.tipdialabel = QtWidgets.QLabel('%s:' % _('V-Tip Dia'))
        self.tipdialabel.setToolTip(
            _("The tip diameter for V-Shape Tool")
        )
        self.tipdia_spinner = FCDoubleSpinner()
        self.tipdia_spinner.set_range(-99.9999, 99.9999)
        self.tipdia_spinner.set_precision(self.decimals)
        self.tipdia_spinner.setSingleStep(0.1)
        self.tipdia_spinner.setWrapping(True)
        grid1.addWidget(self.tipdialabel, 1, 0)
        grid1.addWidget(self.tipdia_spinner, 1, 1, 1, 2)

        # Tip Angle
        self.tipanglelabel = QtWidgets.QLabel('%s:' % _('V-Tip Angle'))
        self.tipanglelabel.setToolTip(
            _("The tip angle for V-Shape Tool.\n"
              "In degree.")
        )
        self.tipangle_spinner = FCDoubleSpinner()
        self.tipangle_spinner.set_range(0, 180)
        self.tipangle_spinner.set_precision(self.decimals)
        self.tipangle_spinner.setSingleStep(5)
        self.tipangle_spinner.setWrapping(True)
        grid1.addWidget(self.tipanglelabel, 2, 0)
        grid1.addWidget(self.tipangle_spinner, 2, 1, 1, 2)

        # Cut Z
        self.cutzlabel = QtWidgets.QLabel('%s:' % _('Cut Z'))
        self.cutzlabel.setToolTip(
            _("Cutting depth (negative)\n"
              "below the copper surface.")
        )
        self.cutz_spinner = FCDoubleSpinner()
        self.cutz_spinner.set_range(-9999.9999, 0.0000)
        self.cutz_spinner.set_precision(self.decimals)
        self.cutz_spinner.setSingleStep(0.1)
        self.cutz_spinner.setWrapping(True)
        grid1.addWidget(self.cutzlabel, 3, 0)
        grid1.addWidget(self.cutz_spinner, 3, 1, 1, 2)

        # Tool diameter
        tdlabel = QtWidgets.QLabel('%s:' % _('Tool dia'))
        tdlabel.setToolTip(
            _("Diameter of the cutting tool.\n"
              "If you want to have an isolation path\n"
              "inside the actual shape of the Gerber\n"
              "feature, use a negative value for\n"
              "this parameter.")
        )
        tdlabel.setMinimumWidth(90)
        self.iso_tool_dia_entry = FCDoubleSpinner()
        self.iso_tool_dia_entry.set_range(-9999.9999, 9999.9999)
        self.iso_tool_dia_entry.set_precision(self.decimals)
        self.iso_tool_dia_entry.setSingleStep(0.1)

        grid1.addWidget(tdlabel, 4, 0)
        grid1.addWidget(self.iso_tool_dia_entry, 4, 1, 1, 2)

        # Number of Passes
        passlabel = QtWidgets.QLabel('%s:' % _('# Passes'))
        passlabel.setToolTip(
            _("Width of the isolation gap in\n"
              "number (integer) of tool widths.")
        )
        passlabel.setMinimumWidth(90)
        self.iso_width_entry = FCSpinner()
        self.iso_width_entry.set_range(1, 999)
        grid1.addWidget(passlabel, 5, 0)
        grid1.addWidget(self.iso_width_entry, 5, 1, 1, 2)

        # Pass overlap
        overlabel = QtWidgets.QLabel('%s:' % _('Pass overlap'))
        overlabel.setToolTip(
            _("How much (percentage) of the tool width to overlap each tool pass.")
        )
        overlabel.setMinimumWidth(90)
        self.iso_overlap_entry = FCDoubleSpinner(suffix='%')
        self.iso_overlap_entry.set_precision(self.decimals)
        self.iso_overlap_entry.setWrapping(True)
        self.iso_overlap_entry.set_range(0.0000, 99.9999)
        self.iso_overlap_entry.setSingleStep(0.1)
        grid1.addWidget(overlabel, 6, 0)
        grid1.addWidget(self.iso_overlap_entry, 6, 1, 1, 2)

        # Milling Type Radio Button
        self.milling_type_label = QtWidgets.QLabel('%s:' % _('Milling Type'))
        self.milling_type_label.setToolTip(
            _("Milling type:\n"
              "- climb / best for precision milling and to reduce tool usage\n"
              "- conventional / useful when there is no backlash compensation")
        )
        self.milling_type_radio = RadioSet([{'label': _('Climb'), 'value': 'cl'},
                                            {'label': _('Conventional'), 'value': 'cv'}])
        grid1.addWidget(self.milling_type_label, 7, 0)
        grid1.addWidget(self.milling_type_radio, 7, 1, 1, 2)

        # combine all passes CB
        self.combine_passes_cb = FCCheckBox(label=_('Combine'))
        self.combine_passes_cb.setToolTip(
            _("Combine all passes into one object")
        )

        # generate follow
        self.follow_cb = FCCheckBox(label=_('"Follow"'))
        self.follow_cb.setToolTip(_("Generate a 'Follow' geometry.\n"
                                    "This means that it will cut through\n"
                                    "the middle of the trace."))
        grid1.addWidget(self.combine_passes_cb, 8, 0)

        # avoid an area from isolation
        self.except_cb = FCCheckBox(label=_('Except'))
        grid1.addWidget(self.follow_cb, 8, 1)

        self.except_cb.setToolTip(_("When the isolation geometry is generated,\n"
                                    "by checking this, the area of the object bellow\n"
                                    "will be subtracted from the isolation geometry."))
        grid1.addWidget(self.except_cb, 8, 2)

        # ## Form Layout
        form_layout = QtWidgets.QFormLayout()
        grid1.addLayout(form_layout, 9, 0, 1, 3)

        # ################################################
        # ##### Type of object to be excepted ############
        # ################################################
        self.type_obj_combo = QtWidgets.QComboBox()
        self.type_obj_combo.addItem("Gerber")
        self.type_obj_combo.addItem("Excellon")
        self.type_obj_combo.addItem("Geometry")

        # we get rid of item1 ("Excellon") as it is not suitable
        self.type_obj_combo.view().setRowHidden(1, True)
        self.type_obj_combo.setItemIcon(0, QtGui.QIcon(self.resource_loc + "/flatcam_icon16.png"))
        self.type_obj_combo.setItemIcon(2, QtGui.QIcon(self.resource_loc + "/geometry16.png"))

        self.type_obj_combo_label = QtWidgets.QLabel('%s:' % _("Obj Type"))
        self.type_obj_combo_label.setToolTip(
            _("Specify the type of object to be excepted from isolation.\n"
              "It can be of type: Gerber or Geometry.\n"
              "What is selected here will dictate the kind\n"
              "of objects that will populate the 'Object' combobox.")
        )
        # self.type_obj_combo_label.setMinimumWidth(60)
        form_layout.addRow(self.type_obj_combo_label, self.type_obj_combo)

        # ################################################
        # ##### The object to be excepted ################
        # ################################################
        self.obj_combo = QtWidgets.QComboBox()

        self.obj_label = QtWidgets.QLabel('%s:' % _("Object"))
        self.obj_label.setToolTip(_("Object whose area will be removed from isolation geometry."))

        form_layout.addRow(self.obj_label, self.obj_combo)

        # ---------------------------------------------- #
        # --------- Isolation scope -------------------- #
        # ---------------------------------------------- #
        self.iso_scope_label = QtWidgets.QLabel('<b>%s:</b>' % _('Scope'))
        self.iso_scope_label.setToolTip(
            _("Isolation scope. Choose what to isolate:\n"
              "- 'All' -> Isolate all the polygons in the object\n"
              "- 'Selection' -> Isolate a selection of polygons.")
        )
        self.iso_scope_radio = RadioSet([{'label': _('All'), 'value': 'all'},
                                         {'label': _('Selection'), 'value': 'single'}])

        grid1.addWidget(self.iso_scope_label, 10, 0)
        grid1.addWidget(self.iso_scope_radio, 10, 1, 1, 2)

        # ---------------------------------------------- #
        # --------- Isolation type  -------------------- #
        # ---------------------------------------------- #
        self.iso_type_label = QtWidgets.QLabel('<b>%s:</b>' % _('Isolation Type'))
        self.iso_type_label.setToolTip(
            _("Choose how the isolation will be executed:\n"
              "- 'Full' -> complete isolation of polygons\n"
              "- 'Ext' -> will isolate only on the outside\n"
              "- 'Int' -> will isolate only on the inside\n"
              "'Exterior' isolation is almost always possible\n"
              "(with the right tool) but 'Interior'\n"
              "isolation can be done only when there is an opening\n"
              "inside of the polygon (e.g polygon is a 'doughnut' shape).")
        )
        self.iso_type_radio = RadioSet([{'label': _('Full'), 'value': 'full'},
                                        {'label': _('Ext'), 'value': 'ext'},
                                        {'label': _('Int'), 'value': 'int'}])

        grid1.addWidget(self.iso_type_label, 11, 0)
        grid1.addWidget(self.iso_type_radio, 11, 1, 1, 2)

        self.generate_iso_button = QtWidgets.QPushButton("%s" % _("Generate Isolation Geometry"))
        self.generate_iso_button.setStyleSheet("""
                        QPushButton
                        {
                            font-weight: bold;
                        }
                        """)
        self.generate_iso_button.setToolTip(
            _("Create a Geometry object with toolpaths to cut \n"
              "isolation outside, inside or on both sides of the\n"
              "object. For a Gerber object outside means outside\n"
              "of the Gerber feature and inside means inside of\n"
              "the Gerber feature, if possible at all. This means\n"
              "that only if the Gerber feature has openings inside, they\n"
              "will be isolated. If what is wanted is to cut isolation\n"
              "inside the actual Gerber feature, use a negative tool\n"
              "diameter above.")
        )
        grid1.addWidget(self.generate_iso_button, 12, 0, 1, 3)

        self.create_buffer_button = QtWidgets.QPushButton(_('Buffer Solid Geometry'))
        self.create_buffer_button.setToolTip(
            _("This button is shown only when the Gerber file\n"
              "is loaded without buffering.\n"
              "Clicking this will create the buffered geometry\n"
              "required for isolation.")
        )
        grid1.addWidget(self.create_buffer_button, 13, 0, 1, 2)

        self.ohis_iso = OptionalHideInputSection(
            self.except_cb,
            [self.type_obj_combo, self.type_obj_combo_label, self.obj_combo, self.obj_label],
            logic=True
        )

        grid1.addWidget(QtWidgets.QLabel(''), 14, 0)

        # ###########################################
        # ########## NEW GRID #######################
        # ###########################################

        grid2 = QtWidgets.QGridLayout()
        self.custom_box.addLayout(grid2)
        grid2.setColumnStretch(0, 0)
        grid2.setColumnStretch(1, 1)

        self.tool_lbl = QtWidgets.QLabel('<b>%s</b>' % _("TOOLS"))
        grid2.addWidget(self.tool_lbl, 0, 0, 1, 2)

        # ## Clear non-copper regions
        self.clearcopper_label = QtWidgets.QLabel("%s" % _("Clear N-copper"))
        self.clearcopper_label.setToolTip(
            _("Create a Geometry object with\n"
              "toolpaths to cut all non-copper regions.")
        )
        self.clearcopper_label.setMinimumWidth(90)

        self.generate_ncc_button = QtWidgets.QPushButton(_('NCC Tool'))
        self.generate_ncc_button.setToolTip(
            _("Create the Geometry Object\n"
              "for non-copper routing.")
        )
        self.generate_ncc_button.setStyleSheet("""
                        QPushButton
                        {
                            font-weight: bold;
                        }
                        """)
        grid2.addWidget(self.clearcopper_label, 1, 0)
        grid2.addWidget(self.generate_ncc_button, 1, 1)

        # ## Board cutout
        self.board_cutout_label = QtWidgets.QLabel("%s" % _("Board cutout"))
        self.board_cutout_label.setToolTip(
            _("Create toolpaths to cut around\n"
              "the PCB and separate it from\n"
              "the original board.")
        )

        self.generate_cutout_button = QtWidgets.QPushButton(_('Cutout Tool'))
        self.generate_cutout_button.setToolTip(
            _("Generate the geometry for\n"
              "the board cutout.")
        )
        self.generate_cutout_button.setStyleSheet("""
                        QPushButton
                        {
                            font-weight: bold;
                        }
                        """)
        grid2.addWidget(self.board_cutout_label, 2, 0)
        grid2.addWidget(self.generate_cutout_button, 2, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid2.addWidget(separator_line, 3, 0, 1, 2)

        # ## Non-copper regions
        self.noncopper_label = QtWidgets.QLabel("<b>%s</b>" % _("Non-copper regions"))
        self.noncopper_label.setToolTip(
            _("Create polygons covering the\n"
              "areas without copper on the PCB.\n"
              "Equivalent to the inverse of this\n"
              "object. Can be used to remove all\n"
              "copper from a specified region.")
        )

        grid2.addWidget(self.noncopper_label, 4, 0, 1, 2)

        # Margin
        bmlabel = QtWidgets.QLabel('%s:' % _('Boundary Margin'))
        bmlabel.setToolTip(
            _("Specify the edge of the PCB\n"
              "by drawing a box around all\n"
              "objects with this minimum\n"
              "distance.")
        )
        bmlabel.setMinimumWidth(90)
        self.noncopper_margin_entry = FCDoubleSpinner()
        self.noncopper_margin_entry.set_range(-9999.9999, 9999.9999)
        self.noncopper_margin_entry.set_precision(self.decimals)
        self.noncopper_margin_entry.setSingleStep(0.1)

        grid2.addWidget(bmlabel, 5, 0)
        grid2.addWidget(self.noncopper_margin_entry, 5, 1)

        # Rounded corners
        self.noncopper_rounded_cb = FCCheckBox(label=_("Rounded Geo"))
        self.noncopper_rounded_cb.setToolTip(
            _("Resulting geometry will have rounded corners.")
        )
        self.noncopper_rounded_cb.setMinimumWidth(90)

        self.generate_noncopper_button = QtWidgets.QPushButton(_('Generate Geo'))
        grid2.addWidget(self.noncopper_rounded_cb, 6, 0)
        grid2.addWidget(self.generate_noncopper_button, 6, 1)

        separator_line1 = QtWidgets.QFrame()
        separator_line1.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line1.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid2.addWidget(separator_line1, 7, 0, 1, 2)

        # ## Bounding box
        self.boundingbox_label = QtWidgets.QLabel('<b>%s</b>' % _('Bounding Box'))
        self.boundingbox_label.setToolTip(
            _("Create a geometry surrounding the Gerber object.\n"
              "Square shape.")
        )

        grid2.addWidget(self.boundingbox_label, 8, 0, 1, 2)

        bbmargin = QtWidgets.QLabel('%s:' % _('Boundary Margin'))
        bbmargin.setToolTip(
            _("Distance of the edges of the box\n"
              "to the nearest polygon.")
        )
        bbmargin.setMinimumWidth(90)
        self.bbmargin_entry = FCDoubleSpinner()
        self.bbmargin_entry.set_range(-9999.9999, 9999.9999)
        self.bbmargin_entry.set_precision(self.decimals)
        self.bbmargin_entry.setSingleStep(0.1)

        grid2.addWidget(bbmargin, 9, 0)
        grid2.addWidget(self.bbmargin_entry, 9, 1)

        self.bbrounded_cb = FCCheckBox(label=_("Rounded Geo"))
        self.bbrounded_cb.setToolTip(
            _("If the bounding box is \n"
              "to have rounded corners\n"
              "their radius is equal to\n"
              "the margin.")
        )
        self.bbrounded_cb.setMinimumWidth(90)

        self.generate_bb_button = QtWidgets.QPushButton(_('Generate Geo'))
        self.generate_bb_button.setToolTip(
            _("Generate the Geometry object.")
        )
        grid2.addWidget(self.bbrounded_cb, 10, 0)
        grid2.addWidget(self.generate_bb_button, 10, 1)

        separator_line2 = QtWidgets.QFrame()
        separator_line2.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line2.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid2.addWidget(separator_line2, 11, 0, 1, 2)


class ExcellonObjectUI(ObjectUI):
    """
    User interface for Excellon objects.
    """

    def __init__(self, decimals, parent=None):

        theme_settings = QtCore.QSettings("Open Source", "FlatCAM")
        if theme_settings.contains("theme"):
            theme = theme_settings.value('theme', type=str)
        else:
            theme = 'white'

        if theme == 'white':
            self.resource_loc = 'share'
        else:
            self.resource_loc = 'share'

        ObjectUI.__init__(self, title=_('Excellon Object'),
                          icon_file=self.resource_loc + '/drill32.png',
                          parent=parent,
                          decimals=decimals)

        self.decimals = decimals

        # ### Plot options ####
        hlay_plot = QtWidgets.QHBoxLayout()
        self.custom_box.addLayout(hlay_plot)

        self.plot_options_label = QtWidgets.QLabel("<b>%s:</b>" % _("Plot Options"))
        self.solid_cb = FCCheckBox(label=_('Solid'))
        self.solid_cb.setToolTip(
            _("Solid circles.")
        )
        hlay_plot.addWidget(self.plot_options_label)
        hlay_plot.addStretch()
        hlay_plot.addWidget(self.solid_cb)

        # ## Object name
        self.name_hlay = QtWidgets.QHBoxLayout()
        self.custom_box.addLayout(self.name_hlay)
        name_label = QtWidgets.QLabel("<b>%s:</b>" % _("Name"))
        self.name_entry = FCEntry()
        self.name_entry.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.name_hlay.addWidget(name_label)
        self.name_hlay.addWidget(self.name_entry)

        # add a frame and inside add a vertical box layout. Inside this vbox layout I add all the Drills widgets
        # this way I can hide/show the frame
        self.drills_frame = QtWidgets.QFrame()
        self.drills_frame.setContentsMargins(0, 0, 0, 0)
        self.custom_box.addWidget(self.drills_frame)
        self.tools_box = QtWidgets.QVBoxLayout()
        self.tools_box.setContentsMargins(0, 0, 0, 0)
        self.drills_frame.setLayout(self.tools_box)

        hlay_plot = QtWidgets.QHBoxLayout()
        self.tools_box.addLayout(hlay_plot)

        # ### Tools Drills ####
        self.tools_table_label = QtWidgets.QLabel('<b>%s:</b>' % _('Tools Table'))
        self.tools_table_label.setToolTip(
            _("Tools in this Excellon object\n"
              "when are used for drilling.")
        )
        hlay_plot.addWidget(self.tools_table_label)

        # Plot CB
        self.plot_cb = FCCheckBox(_('Plot'))
        self.plot_cb.setToolTip(
            _("Plot (show) this object.")
        )
        self.plot_cb.setLayoutDirection(QtCore.Qt.RightToLeft)
        hlay_plot.addStretch()
        hlay_plot.addWidget(self.plot_cb)

        self.tools_table = FCTable()
        self.tools_box.addWidget(self.tools_table)

        self.tools_table.setColumnCount(6)
        self.tools_table.setHorizontalHeaderLabels(['#', _('Diameter'), _('Drills'), _('Slots'),
                                                    _('Offset Z'), 'P'])
        self.tools_table.setSortingEnabled(False)

        self.tools_table.horizontalHeaderItem(0).setToolTip(
            _("This is the Tool Number.\n"
              "When ToolChange is checked, on toolchange event this value\n"
              "will be showed as a T1, T2 ... Tn in the Machine Code.\n\n"
              "Here the tools are selected for G-code generation."))
        self.tools_table.horizontalHeaderItem(1).setToolTip(
            _("Tool Diameter. It's value (in current FlatCAM units) \n"
              "is the cut width into the material."))
        self.tools_table.horizontalHeaderItem(2).setToolTip(
            _("The number of Drill holes. Holes that are drilled with\n"
              "a drill bit."))
        self.tools_table.horizontalHeaderItem(3).setToolTip(
            _("The number of Slot holes. Holes that are created by\n"
              "milling them with an endmill bit."))
        self.tools_table.horizontalHeaderItem(4).setToolTip(
            _("Some drill bits (the larger ones) need to drill deeper\n"
              "to create the desired exit hole diameter due of the tip shape.\n"
              "The value here can compensate the Cut Z parameter."))
        self.tools_table.horizontalHeaderItem(5).setToolTip(
            _("Toggle display of the drills for the current tool.\n"
              "This does not select the tools for G-code generation."))

        self.tools_box.addWidget(QtWidgets.QLabel(''))

        # ###########################################################
        # ############# Create CNC Job ##############################
        # ###########################################################

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.tools_box.addWidget(separator_line)

        self.tool_data_label = QtWidgets.QLabel(
            "<b>%s: <font color='#0000FF'>%s %d</font></b>" % (_('Parameters for'), _("Tool"), int(1)))
        self.tool_data_label.setToolTip(
            _(
                "The data used for creating GCode.\n"
                "Each tool store it's own set of such data."
            )
        )
        self.tools_box.addWidget(self.tool_data_label)

        self.exc_param_frame = QtWidgets.QFrame()
        self.exc_param_frame.setContentsMargins(0, 0, 0, 0)
        self.tools_box.addWidget(self.exc_param_frame)

        self.exc_tools_box = QtWidgets.QVBoxLayout()
        self.exc_tools_box.setContentsMargins(0, 0, 0, 0)
        self.exc_param_frame.setLayout(self.exc_tools_box)

        # #################################################################
        # ################# GRID LAYOUT 3   ###############################
        # #################################################################

        self.grid3 = QtWidgets.QGridLayout()
        self.grid3.setColumnStretch(0, 0)
        self.grid3.setColumnStretch(1, 1)
        self.exc_tools_box.addLayout(self.grid3)

        # Operation Type
        self.operation_label = QtWidgets.QLabel('<b>%s:</b>' % _('Operation'))
        self.operation_label.setToolTip(
            _("Operation type:\n"
              "- Drilling -> will drill the drills/slots associated with this tool\n"
              "- Milling -> will mill the drills/slots")
        )
        self.operation_radio = RadioSet(
            [
                {'label': _('Drilling'), 'value': 'drill'},
                {'label': _("Milling"), 'value': 'mill'}
            ]
        )

        self.grid3.addWidget(self.operation_label, 0, 0)
        self.grid3.addWidget(self.operation_radio, 0, 1)

        # separator_line = QtWidgets.QFrame()
        # separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        # separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        # self.grid3.addWidget(separator_line, 1, 0, 1, 2)

        self.mill_type_label = QtWidgets.QLabel('%s:' % _('Milling Type'))
        self.mill_type_label.setToolTip(
            _("Milling type:\n"
              "- Drills -> will mill the drills associated with this tool\n"
              "- Slots -> will mill the slots associated with this tool\n"
              "- Both -> will mill both drills and mills or whatever is available")
        )
        self.mill_type_radio = RadioSet(
            [
                {'label': _('Drills'), 'value': 'drills'},
                {'label': _("Slots"), 'value': 'slots'},
                {'label': _("Both"), 'value': 'both'},
            ]
        )

        self.grid3.addWidget(self.mill_type_label, 2, 0)
        self.grid3.addWidget(self.mill_type_radio, 2, 1)

        self.mill_dia_label = QtWidgets.QLabel('%s:' % _('Milling Diameter'))
        self.mill_dia_label.setToolTip(
            _("The diameter of the tool who will do the milling")
        )

        self.mill_dia_entry = FCDoubleSpinner()
        self.mill_dia_entry.set_precision(self.decimals)
        self.mill_dia_entry.set_range(0.0000, 9999.9999)

        self.grid3.addWidget(self.mill_dia_label, 3, 0)
        self.grid3.addWidget(self.mill_dia_entry, 3, 1)

        # Cut Z
        cutzlabel = QtWidgets.QLabel('%s:' % _('Cut Z'))
        cutzlabel.setToolTip(
            _("Drill depth (negative)\n"
              "below the copper surface.")
        )

        self.cutz_entry = FCDoubleSpinner()
        self.cutz_entry.set_precision(self.decimals)

        if machinist_setting == 0:
            self.cutz_entry.set_range(-9999.9999, 0.0000)
        else:
            self.cutz_entry.set_range(-9999.9999, 9999.9999)

        self.cutz_entry.setSingleStep(0.1)

        self.grid3.addWidget(cutzlabel, 4, 0)
        self.grid3.addWidget(self.cutz_entry, 4, 1)

        # Multi-Depth
        self.mpass_cb = FCCheckBox('%s:' % _("Multi-Depth"))
        self.mpass_cb.setToolTip(
            _(
                "Use multiple passes to limit\n"
                "the cut depth in each pass. Will\n"
                "cut multiple times until Cut Z is\n"
                "reached."
            )
        )

        self.maxdepth_entry = FCDoubleSpinner()
        self.maxdepth_entry.set_precision(self.decimals)
        self.maxdepth_entry.set_range(0, 9999.9999)
        self.maxdepth_entry.setSingleStep(0.1)

        self.maxdepth_entry.setToolTip(
            _(
                "Depth of each pass (positive)."
            )
        )
        self.mis_mpass_geo = OptionalInputSection(self.mpass_cb, [self.maxdepth_entry])

        self.grid3.addWidget(self.mpass_cb, 5, 0)
        self.grid3.addWidget(self.maxdepth_entry, 5, 1)

        # Travel Z (z_move)
        travelzlabel = QtWidgets.QLabel('%s:' % _('Travel Z'))
        travelzlabel.setToolTip(
            _("Tool height when travelling\n"
              "across the XY plane.")
        )

        self.travelz_entry = FCDoubleSpinner()
        self.travelz_entry.set_precision(self.decimals)

        if machinist_setting == 0:
            self.travelz_entry.set_range(0.00001, 9999.9999)
        else:
            self.travelz_entry.set_range(-9999.9999, 9999.9999)

        self.travelz_entry.setSingleStep(0.1)

        self.grid3.addWidget(travelzlabel, 6, 0)
        self.grid3.addWidget(self.travelz_entry, 6, 1)

        # Tool change:
        self.toolchange_cb = FCCheckBox('%s:' % _("Tool change Z"))
        self.toolchange_cb.setToolTip(
            _("Include tool-change sequence\n"
              "in G-Code (Pause for tool change).")
        )

        self.toolchangez_entry = FCDoubleSpinner()
        self.toolchangez_entry.set_precision(self.decimals)
        self.toolchangez_entry.setToolTip(
            _("Z-axis position (height) for\n"
              "tool change.")
        )
        if machinist_setting == 0:
            self.toolchangez_entry.set_range(0.0, 9999.9999)
        else:
            self.toolchangez_entry.set_range(-9999.9999, 9999.9999)

        self.toolchangez_entry.setSingleStep(0.1)
        self.ois_tcz_e = OptionalInputSection(self.toolchange_cb, [self.toolchangez_entry])

        self.grid3.addWidget(self.toolchange_cb, 8, 0)
        self.grid3.addWidget(self.toolchangez_entry, 8, 1)

        # Start move Z:
        self.estartz_label = QtWidgets.QLabel('%s:' % _("Start Z"))
        self.estartz_label.setToolTip(
            _("Height of the tool just after start.\n"
              "Delete the value if you don't need this feature.")
        )
        self.estartz_entry = FloatEntry()

        self.grid3.addWidget(self.estartz_label, 9, 0)
        self.grid3.addWidget(self.estartz_entry, 9, 1)

        # End move Z:
        self.eendz_label = QtWidgets.QLabel('%s:' % _("End move Z"))
        self.eendz_label.setToolTip(
            _("Height of the tool after\n"
              "the last move at the end of the job.")
        )
        self.eendz_entry = FCDoubleSpinner()
        self.eendz_entry.set_precision(self.decimals)

        if machinist_setting == 0:
            self.eendz_entry.set_range(0.0, 9999.9999)
        else:
            self.eendz_entry.set_range(-9999.9999, 9999.9999)

        self.eendz_entry.setSingleStep(0.1)

        self.grid3.addWidget(self.eendz_label, 11, 0)
        self.grid3.addWidget(self.eendz_entry, 11, 1)

        # Feedrate X-Y
        self.frxylabel = QtWidgets.QLabel('%s:' % _('Feedrate X-Y'))
        self.frxylabel.setToolTip(
            _("Cutting speed in the XY\n"
              "plane in units per minute")
        )
        self.xyfeedrate_entry = FCDoubleSpinner()
        self.xyfeedrate_entry.set_precision(self.decimals)
        self.xyfeedrate_entry.set_range(0, 9999.9999)
        self.xyfeedrate_entry.setSingleStep(0.1)

        self.grid3.addWidget(self.frxylabel, 12, 0)
        self.grid3.addWidget(self.xyfeedrate_entry, 12, 1)

        # Excellon Feedrate Z
        frlabel = QtWidgets.QLabel('%s:' % _('Feedrate Z'))
        frlabel.setToolTip(
            _("Tool speed while drilling\n"
              "(in units per minute).\n"
              "So called 'Plunge' feedrate.\n"
              "This is for linear move G01.")
        )
        self.feedrate_entry = FCDoubleSpinner()
        self.feedrate_entry.set_precision(self.decimals)
        self.feedrate_entry.set_range(0.0, 9999.9999)
        self.feedrate_entry.setSingleStep(0.1)

        self.grid3.addWidget(frlabel, 14, 0)
        self.grid3.addWidget(self.feedrate_entry, 14, 1)

        # Excellon Rapid Feedrate
        self.feedrate_rapid_label = QtWidgets.QLabel('%s:' % _('Feedrate Rapids'))
        self.feedrate_rapid_label.setToolTip(
            _("Tool speed while drilling\n"
              "(in units per minute).\n"
              "This is for the rapid move G00.\n"
              "It is useful only for Marlin,\n"
              "ignore for any other cases.")
        )
        self.feedrate_rapid_entry = FCDoubleSpinner()
        self.feedrate_rapid_entry.set_precision(self.decimals)
        self.feedrate_rapid_entry.set_range(0.0, 9999.9999)
        self.feedrate_rapid_entry.setSingleStep(0.1)

        self.grid3.addWidget(self.feedrate_rapid_label, 16, 0)
        self.grid3.addWidget(self.feedrate_rapid_entry, 16, 1)

        # default values is to hide
        self.feedrate_rapid_label.hide()
        self.feedrate_rapid_entry.hide()

        # Cut over 1st point in path
        self.extracut_cb = FCCheckBox('%s:' % _('Re-cut'))
        self.extracut_cb.setToolTip(
            _("In order to remove possible\n"
              "copper leftovers where first cut\n"
              "meet with last cut, we generate an\n"
              "extended cut over the first cut section.")
        )

        self.e_cut_entry = FCDoubleSpinner()
        self.e_cut_entry.set_range(0, 99999)
        self.e_cut_entry.set_precision(self.decimals)
        self.e_cut_entry.setSingleStep(0.1)
        self.e_cut_entry.setWrapping(True)
        self.e_cut_entry.setToolTip(
            _("In order to remove possible\n"
              "copper leftovers where first cut\n"
              "meet with last cut, we generate an\n"
              "extended cut over the first cut section.")
        )

        self.ois_recut = OptionalInputSection(self.extracut_cb, [self.e_cut_entry])

        self.grid3.addWidget(self.extracut_cb, 17, 0)
        self.grid3.addWidget(self.e_cut_entry, 17, 1)

        # Spindlespeed
        spdlabel = QtWidgets.QLabel('%s:' % _('Spindle speed'))
        spdlabel.setToolTip(
            _("Speed of the spindle\n"
              "in RPM (optional)")
        )

        self.spindlespeed_entry = FCSpinner()
        self.spindlespeed_entry.set_range(0, 1000000)
        self.spindlespeed_entry.setSingleStep(100)

        self.grid3.addWidget(spdlabel, 19, 0)
        self.grid3.addWidget(self.spindlespeed_entry, 19, 1)

        # Dwell
        self.dwell_cb = FCCheckBox('%s:' % _('Dwell'))
        self.dwell_cb.setToolTip(
            _("Pause to allow the spindle to reach its\n"
              "speed before cutting.")
        )
        self.dwelltime_entry = FCDoubleSpinner()
        self.dwelltime_entry.set_precision(self.decimals)
        self.dwelltime_entry.set_range(0.0, 9999.9999)
        self.dwelltime_entry.setSingleStep(0.1)

        self.dwelltime_entry.setToolTip(
            _("Number of time units for spindle to dwell.")
        )

        self.grid3.addWidget(self.dwell_cb, 20, 0)
        self.grid3.addWidget(self.dwelltime_entry, 20, 1)

        self.ois_dwell = OptionalInputSection(self.dwell_cb, [self.dwelltime_entry])

        # Probe depth
        self.pdepth_label = QtWidgets.QLabel('%s:' % _("Probe Z depth"))
        self.pdepth_label.setToolTip(
            _("The maximum depth that the probe is allowed\n"
              "to probe. Negative value, in current units.")
        )

        self.pdepth_entry = FCDoubleSpinner()
        self.pdepth_entry.set_precision(self.decimals)
        self.pdepth_entry.set_range(-9999.9999, 9999.9999)
        self.pdepth_entry.setSingleStep(0.1)

        self.grid3.addWidget(self.pdepth_label, 22, 0)
        self.grid3.addWidget(self.pdepth_entry, 22, 1)

        self.pdepth_label.hide()
        self.pdepth_entry.setVisible(False)

        # Probe feedrate
        self.feedrate_probe_label = QtWidgets.QLabel('%s:' % _("Feedrate Probe"))
        self.feedrate_probe_label.setToolTip(
            _("The feedrate used while the probe is probing.")
        )

        self.feedrate_probe_entry = FCDoubleSpinner()
        self.feedrate_probe_entry.set_precision(self.decimals)
        self.feedrate_probe_entry.set_range(0.0, 9999.9999)
        self.feedrate_probe_entry.setSingleStep(0.1)

        self.grid3.addWidget(self.feedrate_probe_label, 24, 0)
        self.grid3.addWidget(self.feedrate_probe_entry, 24, 1)

        self.feedrate_probe_label.hide()
        self.feedrate_probe_entry.setVisible(False)

        # Tool Offset
        self.tool_offset_label = QtWidgets.QLabel('%s:' % _('Offset Z'))
        self.tool_offset_label.setToolTip(
            _("Some drill bits (the larger ones) need to drill deeper\n"
              "to create the desired exit hole diameter due of the tip shape.\n"
              "The value here can compensate the Cut Z parameter.")
        )

        self.offset_entry = FCDoubleSpinner()
        self.offset_entry.set_precision(self.decimals)
        self.offset_entry.set_range(-9999.9999, 9999.9999)

        self.grid3.addWidget(self.tool_offset_label, 25, 0)
        self.grid3.addWidget(self.offset_entry, 25, 1)

        # #################################################################
        # ################# GRID LAYOUT 4   ###############################
        # #################################################################

        self.grid4 = QtWidgets.QGridLayout()
        self.exc_tools_box.addLayout(self.grid4)
        self.grid4.setColumnStretch(0, 0)
        self.grid4.setColumnStretch(1, 1)

        # choose_tools_label = QtWidgets.QLabel(
        #     _("Select from the Tools Table above the hole dias to be\n"
        #       "drilled. Use the # column to make the selection.")
        # )
        # grid2.addWidget(choose_tools_label, 0, 0, 1, 3)

        # ### Choose what to use for Gcode creation: Drills, Slots or Both
        gcode_type_label = QtWidgets.QLabel('<b>%s</b>' % _('Gcode'))
        gcode_type_label.setToolTip(
            _("Choose what to use for GCode generation:\n"
              "'Drills', 'Slots' or 'Both'.\n"
              "When choosing 'Slots' or 'Both', slots will be\n"
              "converted to a series of drills.")
        )
        self.excellon_gcode_type_radio = RadioSet([{'label': 'Drills', 'value': 'drills'},
                                                   {'label': 'Slots', 'value': 'slots'},
                                                   {'label': 'Both', 'value': 'both'}])
        self.grid4.addWidget(gcode_type_label, 1, 0)
        self.grid4.addWidget(self.excellon_gcode_type_radio, 1, 1)
        # temporary action until I finish the feature
        self.excellon_gcode_type_radio.setVisible(False)
        gcode_type_label.hide()

        # #################################################################
        # ################# GRID LAYOUT 5   ###############################
        # #################################################################

        self.grid5 = QtWidgets.QGridLayout()
        self.grid5.setColumnStretch(0, 0)
        self.grid5.setColumnStretch(1, 1)
        self.exc_tools_box.addLayout(self.grid5)

        separator_line2 = QtWidgets.QFrame()
        separator_line2.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line2.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.grid5.addWidget(separator_line2, 0, 0, 1, 2)

        self.apply_param_to_all = FCButton(_("Apply parameters to all tools"))
        self.apply_param_to_all.setToolTip(
            _("The parameters in the current form will be applied\n"
              "on all the tools from the Tool Table.")
        )
        self.grid5.addWidget(self.apply_param_to_all, 1, 0, 1, 2)

        separator_line2 = QtWidgets.QFrame()
        separator_line2.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line2.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.grid5.addWidget(separator_line2, 2, 0, 1, 2)

        # General Parameters
        self.gen_param_label = QtWidgets.QLabel('<b>%s</b>' % _("Common Parameters"))
        self.gen_param_label.setToolTip(
            _("Parameters that are common for all tools.")
        )
        self.grid5.addWidget(self.gen_param_label, 3, 0, 1, 2)

        # preprocessor selection
        pp_excellon_label = QtWidgets.QLabel('%s:' % _("Preprocessor"))
        pp_excellon_label.setToolTip(
            _("The preprocessor JSON file that dictates\n"
              "Gcode output.")
        )
        self.pp_excellon_name_cb = FCComboBox()
        self.pp_excellon_name_cb.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.grid5.addWidget(pp_excellon_label, 4, 0)
        self.grid5.addWidget(self.pp_excellon_name_cb, 4, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.grid5.addWidget(separator_line, 5, 0, 1, 2)

        # #################################################################
        # ################# GRID LAYOUT 6   ###############################
        # #################################################################
        self.grid6 = QtWidgets.QGridLayout()
        self.grid6.setColumnStretch(0, 0)
        self.grid6.setColumnStretch(1, 1)
        self.tools_box.addLayout(self.grid6)

        warning_lbl = QtWidgets.QLabel(
            _(
                "Add / Select at least one tool in the tool-table.\n"
                "Click the # header to select all, or Ctrl + LMB\n"
                "for custom selection of tools."
            ))

        self.grid6.addWidget(QtWidgets.QLabel(''), 1, 0, 1, 3)
        self.grid6.addWidget(warning_lbl, 2, 0, 1, 3)

        self.generate_cnc_button = QtWidgets.QPushButton(_('Generate CNCJob object'))
        self.generate_cnc_button.setToolTip(
            _("Generate the CNC Job.\n"
              "If milling then an additional Geometry object will be created")
        )
        self.generate_cnc_button.setStyleSheet("""
                        QPushButton
                        {
                            font-weight: bold;
                        }
                        """)
        self.grid6.addWidget(self.generate_cnc_button, 3, 0, 1, 3)

        separator_line2 = QtWidgets.QFrame()
        separator_line2.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line2.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.grid6.addWidget(separator_line2, 4, 0, 1, 3)

        # ### Milling Holes Drills ####
        self.mill_hole_label = QtWidgets.QLabel('<b>%s</b>' % _('Milling Geometry'))
        self.mill_hole_label.setToolTip(
            _("Create Geometry for milling holes.\n"
              "Select from the Tools Table above the hole dias to be\n"
              "milled. Use the # column to make the selection.")
        )
        self.grid6.addWidget(self.mill_hole_label, 5, 0, 1, 3)

        self.tdlabel = QtWidgets.QLabel('%s:' % _('Tool Dia'))
        self.tdlabel.setToolTip(
            _("Diameter of the cutting tool.")
        )

        self.grid6.addWidget(self.tdlabel, 6, 0, 1, 3)

        self.tooldia_entry = FCDoubleSpinner()
        self.tooldia_entry.set_precision(self.decimals)
        self.tooldia_entry.set_range(0.0, 9999.9999)
        self.tooldia_entry.setSingleStep(0.1)

        self.generate_milling_button = QtWidgets.QPushButton(_('Mill Drills'))
        self.generate_milling_button.setToolTip(
            _("Create the Geometry Object\n"
              "for milling DRILLS toolpaths.")
        )
        self.generate_milling_button.setStyleSheet("""
                        QPushButton
                        {
                            font-weight: bold;
                        }
                        """)

        self.grid6.addWidget(self.tooldia_entry, 7, 0, 1, 2)
        self.grid6.addWidget(self.generate_milling_button, 7, 2)

        self.slot_tooldia_entry = FCDoubleSpinner()
        self.slot_tooldia_entry.set_precision(self.decimals)
        self.slot_tooldia_entry.set_range(0.0, 9999.9999)
        self.slot_tooldia_entry.setSingleStep(0.1)

        self.generate_milling_slots_button = QtWidgets.QPushButton(_('Mill Slots'))
        self.generate_milling_slots_button.setToolTip(
            _("Create the Geometry Object\n"
              "for milling SLOTS toolpaths.")
        )
        self.generate_milling_slots_button.setStyleSheet("""
                        QPushButton
                        {
                            font-weight: bold;
                        }
                        """)

        self.grid6.addWidget(self.slot_tooldia_entry, 8, 0, 1, 2)
        self.grid6.addWidget(self.generate_milling_slots_button, 8, 2)

    def hide_drills(self, state=True):
        if state is True:
            self.drills_frame.hide()
        else:
            self.drills_frame.show()


class GeometryObjectUI(ObjectUI):
    """
    User interface for Geometry objects.
    """

    def __init__(self, decimals, parent=None):

        theme_settings = QtCore.QSettings("Open Source", "FlatCAM")
        if theme_settings.contains("theme"):
            theme = theme_settings.value('theme', type=str)
        else:
            theme = 'white'

        if theme == 'white':
            self.resource_loc = 'share'
        else:
            self.resource_loc = 'share'

        super(GeometryObjectUI, self).__init__(
            title=_('Geometry Object'),
            icon_file=self.resource_loc + '/geometry32.png', parent=parent, decimals=decimals
        )

        self.decimals = decimals

        # Plot options
        self.plot_options_label = QtWidgets.QLabel("<b>%s:</b>" % _("Plot Options"))
        self.custom_box.addWidget(self.plot_options_label)

        # ## Object name
        self.name_hlay = QtWidgets.QHBoxLayout()
        self.custom_box.addLayout(self.name_hlay)
        name_label = QtWidgets.QLabel("<b>%s:</b>" % _("Name"))
        self.name_entry = FCEntry()
        self.name_entry.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.name_hlay.addWidget(name_label)
        self.name_hlay.addWidget(self.name_entry)

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

        # ### Tools ####
        self.tools_table_label = QtWidgets.QLabel('<b>%s:</b>' % _('Tools Table'))
        self.tools_table_label.setToolTip(
            _("Tools in this Geometry object used for cutting.\n"
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
              "showed UI form entries named V-Tip Dia and V-Tip Angle.")
        )
        hlay_plot.addWidget(self.tools_table_label)

        # Plot CB
        # self.plot_cb = QtWidgets.QCheckBox('Plot')
        self.plot_cb = FCCheckBox(_('Plot Object'))
        self.plot_cb.setToolTip(
            _("Plot (show) this object.")
        )
        self.plot_cb.setLayoutDirection(QtCore.Qt.RightToLeft)
        hlay_plot.addStretch()
        hlay_plot.addWidget(self.plot_cb)

        self.geo_tools_table = FCTable()
        self.geo_tools_box.addWidget(self.geo_tools_table)
        self.geo_tools_table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)

        self.geo_tools_table.setColumnCount(7)
        self.geo_tools_table.setColumnWidth(0, 20)
        self.geo_tools_table.setHorizontalHeaderLabels(['#', _('Dia'), _('Offset'), _('Type'), _('TT'), '', 'P'])
        self.geo_tools_table.setColumnHidden(5, True)
        # stylesheet = "::section{Background-color:rgb(239,239,245)}"
        # self.geo_tools_table.horizontalHeader().setStyleSheet(stylesheet)

        self.geo_tools_table.horizontalHeaderItem(0).setToolTip(
            _(
                "This is the Tool Number.\n"
                "When ToolChange is checked, on toolchange event this value\n"
                "will be showed as a T1, T2 ... Tn")
            )
        self.geo_tools_table.horizontalHeaderItem(1).setToolTip(
            _(
                "Tool Diameter. It's value (in current FlatCAM units) \n"
                "is the cut width into the material."
            ))
        self.geo_tools_table.horizontalHeaderItem(2).setToolTip(
            _(
                "The value for the Offset can be:\n"
                "- Path -> There is no offset, the tool cut will be done through the geometry line.\n"
                "- In(side) -> The tool cut will follow the geometry inside. It will create a 'pocket'.\n"
                "- Out(side) -> The tool cut will follow the geometry line on the outside."
            ))
        self.geo_tools_table.horizontalHeaderItem(3).setToolTip(
            _(
                "The (Operation) Type has only informative value. Usually the UI form values \n"
                "are choose based on the operation type and this will serve as a reminder.\n"
                "Can be 'Roughing', 'Finishing' or 'Isolation'.\n"
                "For Roughing we may choose a lower Feedrate and multiDepth cut.\n"
                "For Finishing we may choose a higher Feedrate, without multiDepth.\n"
                "For Isolation we need a lower Feedrate as it use a milling bit with a fine tip."
            ))
        self.geo_tools_table.horizontalHeaderItem(4).setToolTip(
            _(
                "The Tool Type (TT) can be:\n"
                "- Circular with 1 ... 4 teeth -> it is informative only. Being circular the cut width in material\n"
                "is exactly the tool diameter.\n"
                "- Ball -> informative only and make reference to the Ball type endmill.\n"
                "- V-Shape -> it will disable de Z-Cut parameter in the UI form and enable two additional UI form\n"
                "fields: V-Tip Dia and V-Tip Angle. Adjusting those two values will adjust the Z-Cut parameter such\n"
                "as the cut width into material will be equal with the value in the Tool "
                "Diameter column of this table.\n"
                "Choosing the V-Shape Tool Type automatically will select the Operation Type as Isolation."
            ))
        self.geo_tools_table.horizontalHeaderItem(6).setToolTip(
            _(
                "Plot column. It is visible only for MultiGeo geometries, meaning geometries that holds the geometry\n"
                "data into the tools. For those geometries, deleting the tool will delete the geometry data also,\n"
                "so be WARNED. From the checkboxes on each row it can be enabled/disabled the plot on canvas\n"
                "for the corresponding tool."
            ))

        # self.geo_tools_table.setSortingEnabled(False)
        # self.geo_tools_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

        # Tool Offset
        self.grid1 = QtWidgets.QGridLayout()
        self.geo_tools_box.addLayout(self.grid1)
        self.grid1.setColumnStretch(0, 0)
        self.grid1.setColumnStretch(1, 1)

        self.tool_offset_lbl = QtWidgets.QLabel('%s:' % _('Tool Offset'))
        self.tool_offset_lbl.setToolTip(
            _(
                "The value to offset the cut when \n"
                "the Offset type selected is 'Offset'.\n"
                "The value can be positive for 'outside'\n"
                "cut and negative for 'inside' cut."
            )
        )
        self.tool_offset_entry = FCDoubleSpinner()
        self.tool_offset_entry.set_precision(self.decimals)
        self.tool_offset_entry.set_range(-9999.9999, 9999.9999)
        self.tool_offset_entry.setSingleStep(0.1)

        self.grid1.addWidget(self.tool_offset_lbl, 0, 0)
        self.grid1.addWidget(self.tool_offset_entry, 0, 1, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.grid1.addWidget(separator_line, 1, 0, 1, 3)

        self.tool_sel_label = QtWidgets.QLabel('<b>%s</b>' % _("New Tool"))
        self.grid1.addWidget(self.tool_sel_label, 2, 0, 1, 3)

        self.addtool_entry_lbl = QtWidgets.QLabel('<b>%s:</b>' % _('Tool Dia'))
        self.addtool_entry_lbl.setToolTip(
            _("Diameter for the new tool")
        )
        self.addtool_entry = FCDoubleSpinner()
        self.addtool_entry.set_precision(self.decimals)
        self.addtool_entry.set_range(0.00001, 9999.9999)
        self.addtool_entry.setSingleStep(0.1)

        self.addtool_btn = QtWidgets.QPushButton(_('Add'))
        self.addtool_btn.setToolTip(
            _("Add a new tool to the Tool Table\n"
              "with the specified diameter.")
        )

        self.grid1.addWidget(self.addtool_entry_lbl, 3, 0)
        self.grid1.addWidget(self.addtool_entry, 3, 1)
        self.grid1.addWidget(self.addtool_btn, 3, 2)

        self.addtool_from_db_btn = QtWidgets.QPushButton(_('Add from DB'))
        self.addtool_from_db_btn.setToolTip(
            _("Add a new tool to the Tool Table\n"
              "from the Tool DataBase.")
        )
        self.grid1.addWidget(self.addtool_from_db_btn, 4, 0, 1, 3)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.grid1.addWidget(separator_line, 5, 0, 1, 3)

        grid2 = QtWidgets.QGridLayout()
        self.geo_tools_box.addLayout(grid2)

        self.copytool_btn = QtWidgets.QPushButton(_('Copy'))
        self.copytool_btn.setToolTip(
            _("Copy a selection of tools in the Tool Table\n"
              "by first selecting a row in the Tool Table.")
        )

        self.deltool_btn = QtWidgets.QPushButton(_('Delete'))
        self.deltool_btn.setToolTip(
            _("Delete a selection of tools in the Tool Table\n"
              "by first selecting a row in the Tool Table.")
        )

        grid2.addWidget(self.copytool_btn, 0, 0)
        grid2.addWidget(self.deltool_btn, 0, 1)

        self.empty_label = QtWidgets.QLabel('')
        self.geo_tools_box.addWidget(self.empty_label)

        # ###########################################################
        # ############# Create CNC Job ##############################
        # ###########################################################

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.geo_tools_box.addWidget(separator_line)

        # ### Tools Data ## ##
        self.tool_data_label = QtWidgets.QLabel(
            "<b>%s: <font color='#0000FF'>%s %d</font></b>" % (_('Parameters for'), _("Tool"), int(1)))
        self.tool_data_label.setToolTip(
            _(
                "The data used for creating GCode.\n"
                "Each tool store it's own set of such data."
            )
        )
        self.geo_tools_box.addWidget(self.tool_data_label)

        self.geo_param_frame = QtWidgets.QFrame()
        self.geo_param_frame.setContentsMargins(0, 0, 0, 0)
        self.geo_tools_box.addWidget(self.geo_param_frame)

        self.geo_param_box = QtWidgets.QVBoxLayout()
        self.geo_param_box.setContentsMargins(0, 0, 0, 0)
        self.geo_param_frame.setLayout(self.geo_param_box)

        # #################################################################
        # ################# GRID LAYOUT 3   ###############################
        # #################################################################

        self.grid3 = QtWidgets.QGridLayout()
        self.grid3.setColumnStretch(0, 0)
        self.grid3.setColumnStretch(1, 1)
        self.geo_param_box.addLayout(self.grid3)

        # Tip Dia
        self.tipdialabel = QtWidgets.QLabel('%s:' % _('V-Tip Dia'))
        self.tipdialabel.setToolTip(
            _(
                "The tip diameter for V-Shape Tool"
            )
        )
        self.tipdia_entry = FCDoubleSpinner()
        self.tipdia_entry.set_precision(self.decimals)
        self.tipdia_entry.set_range(0.00001, 9999.9999)
        self.tipdia_entry.setSingleStep(0.1)

        self.grid3.addWidget(self.tipdialabel, 1, 0)
        self.grid3.addWidget(self.tipdia_entry, 1, 1)

        # Tip Angle
        self.tipanglelabel = QtWidgets.QLabel('%s:' % _('V-Tip Angle'))
        self.tipanglelabel.setToolTip(
            _(
                "The tip angle for V-Shape Tool.\n"
                "In degree."
            )
        )
        self.tipangle_entry = FCDoubleSpinner()
        self.tipangle_entry.set_precision(self.decimals)
        self.tipangle_entry.set_range(0.0, 180.0)
        self.tipangle_entry.setSingleStep(1)

        self.grid3.addWidget(self.tipanglelabel, 2, 0)
        self.grid3.addWidget(self.tipangle_entry, 2, 1)

        # Cut Z
        cutzlabel = QtWidgets.QLabel('%s:' % _('Cut Z'))
        cutzlabel.setToolTip(
            _(
                "Cutting depth (negative)\n"
                "below the copper surface."
            )
        )
        self.cutz_entry = FCDoubleSpinner()
        self.cutz_entry.set_precision(self.decimals)

        if machinist_setting == 0:
            self.cutz_entry.set_range(-9999.9999, 0.0000)
        else:
            self.cutz_entry.set_range(-9999.9999, 9999.9999)

        self.cutz_entry.setSingleStep(0.1)

        self.grid3.addWidget(cutzlabel, 3, 0)
        self.grid3.addWidget(self.cutz_entry, 3, 1)

        # Multi-pass
        self.mpass_cb = FCCheckBox('%s:' % _("Multi-Depth"))
        self.mpass_cb.setToolTip(
            _(
                "Use multiple passes to limit\n"
                "the cut depth in each pass. Will\n"
                "cut multiple times until Cut Z is\n"
                "reached."
            )
        )

        self.maxdepth_entry = FCDoubleSpinner()
        self.maxdepth_entry.set_precision(self.decimals)
        self.maxdepth_entry.set_range(0, 9999.9999)
        self.maxdepth_entry.setSingleStep(0.1)

        self.maxdepth_entry.setToolTip(
            _(
                "Depth of each pass (positive)."
            )
        )
        self.ois_mpass_geo = OptionalInputSection(self.mpass_cb, [self.maxdepth_entry])

        self.grid3.addWidget(self.mpass_cb, 4, 0)
        self.grid3.addWidget(self.maxdepth_entry, 4, 1)

        # Travel Z
        travelzlabel = QtWidgets.QLabel('%s:' % _('Travel Z'))
        travelzlabel.setToolTip(
            _("Height of the tool when\n"
              "moving without cutting.")
        )
        self.travelz_entry = FCDoubleSpinner()
        self.travelz_entry.set_precision(self.decimals)

        if machinist_setting == 0:
            self.travelz_entry.set_range(0.00001, 9999.9999)
        else:
            self.travelz_entry.set_range(-9999.9999, 9999.9999)

        self.travelz_entry.setSingleStep(0.1)

        self.grid3.addWidget(travelzlabel, 5, 0)
        self.grid3.addWidget(self.travelz_entry, 5, 1)

        # Tool change
        self.toolchangeg_cb = FCCheckBox('%s:' % _("Tool change Z"))
        self.toolchangeg_cb.setToolTip(
            _(
                "Include tool-change sequence\n"
                "in the Machine Code (Pause for tool change)."
            )
        )
        self.toolchangez_entry = FCDoubleSpinner()
        self.toolchangez_entry.set_precision(self.decimals)
        self.toolchangez_entry.setToolTip(
            _(
                "Z-axis position (height) for\n"
                "tool change."
            )
        )

        if machinist_setting == 0:
            self.toolchangez_entry.set_range(0, 9999.9999)
        else:
            self.toolchangez_entry.set_range(-9999.9999, 9999.9999)

        self.toolchangez_entry.setSingleStep(0.1)
        self.ois_tcz_geo = OptionalInputSection(self.toolchangeg_cb, [self.toolchangez_entry])

        self.grid3.addWidget(self.toolchangeg_cb, 6, 0)
        self.grid3.addWidget(self.toolchangez_entry, 6, 1)

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
        self.endzlabel = QtWidgets.QLabel('%s:' % _('End move Z'))
        self.endzlabel.setToolTip(
            _("Height of the tool after\n"
              "the last move at the end of the job.")
        )
        self.gendz_entry = FCDoubleSpinner()
        self.gendz_entry.set_precision(self.decimals)

        if machinist_setting == 0:
            self.gendz_entry.set_range(0, 9999.9999)
        else:
            self.gendz_entry.set_range(-9999.9999, 9999.9999)

        self.gendz_entry.setSingleStep(0.1)

        self.grid3.addWidget(self.endzlabel, 9, 0)
        self.grid3.addWidget(self.gendz_entry, 9, 1)

        # Feedrate X-Y
        frlabel = QtWidgets.QLabel('%s:' % _('Feedrate X-Y'))
        frlabel.setToolTip(
            _("Cutting speed in the XY\n"
              "plane in units per minute")
        )
        self.cncfeedrate_entry = FCDoubleSpinner()
        self.cncfeedrate_entry.set_precision(self.decimals)
        self.cncfeedrate_entry.set_range(0, 9999.9999)
        self.cncfeedrate_entry.setSingleStep(0.1)

        self.grid3.addWidget(frlabel, 10, 0)
        self.grid3.addWidget(self.cncfeedrate_entry, 10, 1)

        # Feedrate Z (Plunge)
        frzlabel = QtWidgets.QLabel('%s:' % _('Feedrate Z'))
        frzlabel.setToolTip(
            _("Cutting speed in the XY\n"
              "plane in units per minute.\n"
              "It is called also Plunge.")
        )
        self.cncplunge_entry = FCDoubleSpinner()
        self.cncplunge_entry.set_precision(self.decimals)
        self.cncplunge_entry.set_range(0, 9999.9999)
        self.cncplunge_entry.setSingleStep(0.1)

        self.grid3.addWidget(frzlabel, 11, 0)
        self.grid3.addWidget(self.cncplunge_entry, 11, 1)

        # Feedrate rapids
        self.fr_rapidlabel = QtWidgets.QLabel('%s:' % _('Feedrate Rapids'))
        self.fr_rapidlabel.setToolTip(
            _("Cutting speed in the XY plane\n"
              "(in units per minute).\n"
              "This is for the rapid move G00.\n"
              "It is useful only for Marlin,\n"
              "ignore for any other cases.")
        )
        self.cncfeedrate_rapid_entry = FCDoubleSpinner()
        self.cncfeedrate_rapid_entry.set_precision(self.decimals)
        self.cncfeedrate_rapid_entry.set_range(0, 9999.9999)
        self.cncfeedrate_rapid_entry.setSingleStep(0.1)

        self.grid3.addWidget(self.fr_rapidlabel, 12, 0)
        self.grid3.addWidget(self.cncfeedrate_rapid_entry, 12, 1)
        # default values is to hide
        self.fr_rapidlabel.hide()
        self.cncfeedrate_rapid_entry.hide()

        # Cut over 1st point in path
        self.extracut_cb = FCCheckBox('%s:' % _('Re-cut'))
        self.extracut_cb.setToolTip(
            _("In order to remove possible\n"
              "copper leftovers where first cut\n"
              "meet with last cut, we generate an\n"
              "extended cut over the first cut section.")
        )

        self.e_cut_entry = FCDoubleSpinner()
        self.e_cut_entry.set_range(0, 99999)
        self.e_cut_entry.set_precision(self.decimals)
        self.e_cut_entry.setSingleStep(0.1)
        self.e_cut_entry.setWrapping(True)
        self.e_cut_entry.setToolTip(
            _("In order to remove possible\n"
              "copper leftovers where first cut\n"
              "meet with last cut, we generate an\n"
              "extended cut over the first cut section.")
        )
        self.grid3.addWidget(self.extracut_cb, 13, 0)
        self.grid3.addWidget(self.e_cut_entry, 13, 1)

        # Spindlespeed
        spdlabel = QtWidgets.QLabel('%s:' % _('Spindle speed'))
        spdlabel.setToolTip(
            _(
                "Speed of the spindle in RPM (optional).\n"
                "If LASER preprocessor is used,\n"
                "this value is the power of laser."
            )
        )
        self.cncspindlespeed_entry = FCSpinner()
        self.cncspindlespeed_entry.set_range(0, 1000000)
        self.cncspindlespeed_entry.setSingleStep(100)

        self.grid3.addWidget(spdlabel, 14, 0)
        self.grid3.addWidget(self.cncspindlespeed_entry, 14, 1)

        # Dwell
        self.dwell_cb = FCCheckBox('%s:' % _('Dwell'))
        self.dwell_cb.setToolTip(
            _(
                "Pause to allow the spindle to reach its\n"
                "speed before cutting."
            )
        )
        self.dwelltime_entry = FCDoubleSpinner()
        self.dwelltime_entry.set_precision(self.decimals)
        self.dwelltime_entry.set_range(0, 9999.9999)
        self.dwelltime_entry.setSingleStep(0.1)

        self.dwelltime_entry.setToolTip(
            _("Number of time units for spindle to dwell.")
        )
        self.ois_dwell_geo = OptionalInputSection(self.dwell_cb, [self.dwelltime_entry])

        self.grid3.addWidget(self.dwell_cb, 15, 0)
        self.grid3.addWidget(self.dwelltime_entry, 15, 1)

        # Probe depth
        self.pdepth_label = QtWidgets.QLabel('%s:' % _("Probe Z depth"))
        self.pdepth_label.setToolTip(
            _("The maximum depth that the probe is allowed\n"
              "to probe. Negative value, in current units.")
        )
        self.pdepth_entry = FCDoubleSpinner()
        self.pdepth_entry.set_precision(self.decimals)
        self.pdepth_entry.set_range(-9999.9999, 9999.9999)
        self.pdepth_entry.setSingleStep(0.1)

        self.grid3.addWidget(self.pdepth_label, 17, 0)
        self.grid3.addWidget(self.pdepth_entry, 17, 1)

        self.pdepth_label.hide()
        self.pdepth_entry.setVisible(False)

        # Probe feedrate
        self.feedrate_probe_label = QtWidgets.QLabel('%s:' % _("Feedrate Probe"))
        self.feedrate_probe_label.setToolTip(
            _("The feedrate used while the probe is probing.")
        )
        self.feedrate_probe_entry = FCDoubleSpinner()
        self.feedrate_probe_entry.set_precision(self.decimals)
        self.feedrate_probe_entry.set_range(0.0, 9999.9999)
        self.feedrate_probe_entry.setSingleStep(0.1)

        self.grid3.addWidget(self.feedrate_probe_label, 18, 0)
        self.grid3.addWidget(self.feedrate_probe_entry, 18, 1)

        self.feedrate_probe_label.hide()
        self.feedrate_probe_entry.setVisible(False)

        # #################################################################
        # ################# GRID LAYOUT 4   ###############################
        # #################################################################

        self.grid4 = QtWidgets.QGridLayout()
        self.grid4.setColumnStretch(0, 0)
        self.grid4.setColumnStretch(1, 1)
        self.geo_param_box.addLayout(self.grid4)

        separator_line2 = QtWidgets.QFrame()
        separator_line2.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line2.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.grid4.addWidget(separator_line2, 0, 0, 1, 2)

        self.apply_param_to_all = FCButton(_("Apply parameters to all tools"))
        self.apply_param_to_all.setToolTip(
            _("The parameters in the current form will be applied\n"
              "on all the tools from the Tool Table.")
        )
        self.grid4.addWidget(self.apply_param_to_all, 1, 0, 1, 2)

        separator_line2 = QtWidgets.QFrame()
        separator_line2.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line2.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.grid4.addWidget(separator_line2, 2, 0, 1, 2)

        # General Parameters
        self.gen_param_label = QtWidgets.QLabel('<b>%s</b>' % _("Common Parameters"))
        self.gen_param_label.setToolTip(
            _("Parameters that are common for all tools.")
        )
        self.grid4.addWidget(self.gen_param_label, 3, 0, 1, 2)

        # preprocessor selection
        pp_label = QtWidgets.QLabel('%s:' % _("Preprocessor"))
        pp_label.setToolTip(
            _("The Preprocessor file that dictates\n"
              "the Machine Code (like GCode, RML, HPGL) output.")
        )
        self.pp_geometry_name_cb = FCComboBox()
        self.pp_geometry_name_cb.setFocusPolicy(QtCore.Qt.StrongFocus)

        self.grid4.addWidget(pp_label, 4, 0)
        self.grid4.addWidget(self.pp_geometry_name_cb, 4, 1)

        self.grid4.addWidget(QtWidgets.QLabel(''), 5, 0, 1, 2)
        warning_lbl = QtWidgets.QLabel(
            _(
                "Add / Select at least one tool in the tool-table.\n"
                "Click the # header to select all, or Ctrl + LMB\n"
                "for custom selection of tools."
            ))
        self.grid4.addWidget(warning_lbl, 6, 0, 1, 2)

        # Button
        self.generate_cnc_button = QtWidgets.QPushButton(_('Generate CNCJob object'))
        self.generate_cnc_button.setToolTip(
            _("Generate the CNC Job object.")
        )
        self.generate_cnc_button.setStyleSheet("""
                        QPushButton
                        {
                            font-weight: bold;
                        }
                        """)
        self.grid4.addWidget(self.generate_cnc_button, 7, 0, 1, 2)

        self.grid4.addWidget(QtWidgets.QLabel(''), 8, 0, 1, 2)

        # ##############
        # Paint area ##
        # ##############
        self.tools_label = QtWidgets.QLabel('<b>%s</b>' % _('TOOLS'))
        self.tools_label.setToolTip(
            _("Launch Paint Tool in Tools Tab.")
        )
        self.grid4.addWidget(self.tools_label, 10, 0, 1, 2)

        # Paint Button
        self.paint_tool_button = QtWidgets.QPushButton(_('Paint Tool'))
        self.paint_tool_button.setToolTip(
            _(
                "Creates tool paths to cover the\n"
                "whole area of a polygon (remove\n"
                "all copper). You will be asked\n"
                "to click on the desired polygon."
            )
        )
        self.paint_tool_button.setStyleSheet("""
                        QPushButton
                        {
                            font-weight: bold;
                        }
                        """)
        self.grid4.addWidget(self.paint_tool_button, 12, 0, 1, 2)

        # NCC Tool
        self.generate_ncc_button = QtWidgets.QPushButton(_('NCC Tool'))
        self.generate_ncc_button.setToolTip(
            _("Create the Geometry Object\n"
              "for non-copper routing.")
        )
        self.generate_ncc_button.setStyleSheet("""
                        QPushButton
                        {
                            font-weight: bold;
                        }
                        """)
        self.grid4.addWidget(self.generate_ncc_button, 13, 0, 1, 2)


class CNCObjectUI(ObjectUI):
    """
    User interface for CNCJob objects.
    """

    def __init__(self, decimals, parent=None):
        """
        Creates the user interface for CNCJob objects. GUI elements should
        be placed in ``self.custom_box`` to preserve the layout.
        """

        theme_settings = QtCore.QSettings("Open Source", "FlatCAM")
        if theme_settings.contains("theme"):
            theme = theme_settings.value('theme', type=str)
        else:
            theme = 'white'

        if theme == 'white':
            self.resource_loc = 'share'
        else:
            self.resource_loc = 'share'

        ObjectUI.__init__(
            self, title=_('CNC Job Object'),
            icon_file=self.resource_loc + '/cnc32.png', parent=parent,
            decimals=decimals)
        self.decimals = decimals

        for i in range(0, self.common_grid.count()):
            self.common_grid.itemAt(i).widget().hide()

        # ## Plot options
        self.plot_options_label = QtWidgets.QLabel("<b>%s:</b>" % _("Plot Options"))
        self.custom_box.addWidget(self.plot_options_label)

        self.cncplot_method_label = QtWidgets.QLabel("<b>%s:</b>" % _("Plot kind"))
        self.cncplot_method_label.setToolTip(
            _(
                "This selects the kind of geometries on the canvas to plot.\n"
                "Those can be either of type 'Travel' which means the moves\n"
                "above the work piece or it can be of type 'Cut',\n"
                "which means the moves that cut into the material."
            )
        )

        self.cncplot_method_combo = RadioSet([
            {"label": _("All"), "value": "all"},
            {"label": _("Travel"), "value": "travel"},
            {"label": _("Cut"), "value": "cut"}
        ], stretch=False)

        self.annotation_label = QtWidgets.QLabel("<b>%s:</b>" % _("Display Annotation"))
        self.annotation_label.setToolTip(
            _("This selects if to display text annotation on the plot.\n"
              "When checked it will display numbers in order for each end\n"
              "of a travel line.")
        )
        self.annotation_cb = FCCheckBox()

        # ## Object name
        self.name_hlay = QtWidgets.QHBoxLayout()
        self.custom_box.addLayout(self.name_hlay)
        name_label = QtWidgets.QLabel("<b>%s:</b>" % _("Name"))
        self.name_entry = FCEntry()
        self.name_entry.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.name_hlay.addWidget(name_label)
        self.name_hlay.addWidget(self.name_entry)

        self.t_distance_label = QtWidgets.QLabel("<b>%s:</b>" % _("Travelled dist."))
        self.t_distance_label.setToolTip(
            _("This is the total travelled distance on X-Y plane.\n"
              "In current units.")
        )
        self.t_distance_entry = FCEntry()
        self.t_distance_entry.setToolTip(
            _("This is the total travelled distance on X-Y plane.\n"
              "In current units.")
        )
        self.units_label = QtWidgets.QLabel()

        self.t_time_label = QtWidgets.QLabel("<b>%s:</b>" % _("Estimated time"))
        self.t_time_label.setToolTip(
            _("This is the estimated time to do the routing/drilling,\n"
              "without the time spent in ToolChange events.")
        )
        self.t_time_entry = FCEntry()
        self.t_time_entry.setToolTip(
            _("This is the estimated time to do the routing/drilling,\n"
              "without the time spent in ToolChange events.")
        )
        self.units_time_label = QtWidgets.QLabel()

        f_lay = QtWidgets.QGridLayout()
        f_lay.setColumnStretch(1, 1)
        f_lay.setColumnStretch(2, 1)

        self.custom_box.addLayout(f_lay)
        f_lay.addWidget(self.cncplot_method_label, 0, 0)
        f_lay.addWidget(self.cncplot_method_combo, 0, 1)
        f_lay.addWidget(QtWidgets.QLabel(''), 0, 2)
        f_lay.addWidget(self.annotation_label, 1, 0)
        f_lay.addWidget(self.annotation_cb, 1, 1)
        f_lay.addWidget(QtWidgets.QLabel(''), 1, 2)
        f_lay.addWidget(self.t_distance_label, 2, 0)
        f_lay.addWidget(self.t_distance_entry, 2, 1)
        f_lay.addWidget(self.units_label, 2, 2)
        f_lay.addWidget(self.t_time_label, 3, 0)
        f_lay.addWidget(self.t_time_entry, 3, 1)
        f_lay.addWidget(self.units_time_label, 3, 2)

        self.t_distance_label.hide()
        self.t_distance_entry.setVisible(False)
        self.t_time_label.hide()
        self.t_time_entry.setVisible(False)

        e1_lbl = QtWidgets.QLabel('')
        self.custom_box.addWidget(e1_lbl)

        hlay = QtWidgets.QHBoxLayout()
        self.custom_box.addLayout(hlay)

        # CNC Tools Table for plot
        self.cnc_tools_table_label = QtWidgets.QLabel('<b>%s</b>' % _('CNC Tools Table'))
        self.cnc_tools_table_label.setToolTip(
            _(
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
        )
        hlay.addWidget(self.cnc_tools_table_label)

        # Plot CB
        # self.plot_cb = QtWidgets.QCheckBox('Plot')
        self.plot_cb = FCCheckBox(_('Plot Object'))
        self.plot_cb.setToolTip(
            _("Plot (show) this object.")
        )
        self.plot_cb.setLayoutDirection(QtCore.Qt.RightToLeft)
        hlay.addStretch()
        hlay.addWidget(self.plot_cb)

        self.cnc_tools_table = FCTable()
        self.custom_box.addWidget(self.cnc_tools_table)

        self.cnc_tools_table.setColumnCount(7)
        self.cnc_tools_table.setColumnWidth(0, 20)
        self.cnc_tools_table.setHorizontalHeaderLabels(['#', _('Dia'), _('Offset'), _('Type'), _('TT'), '', _('P')])
        self.cnc_tools_table.setColumnHidden(5, True)
        # stylesheet = "::section{Background-color:rgb(239,239,245)}"
        # self.cnc_tools_table.horizontalHeader().setStyleSheet(stylesheet)

        self.exc_cnc_tools_table = FCTable()
        self.custom_box.addWidget(self.exc_cnc_tools_table)

        self.exc_cnc_tools_table.setColumnCount(7)
        self.exc_cnc_tools_table.setColumnWidth(0, 20)
        self.exc_cnc_tools_table.setHorizontalHeaderLabels(['#', _('Dia'), _('Drills'), _('Slots'), '', _("Cut Z"),
                                                            _('P')])
        self.exc_cnc_tools_table.setColumnHidden(4, True)

        self.tooldia_entry = FCDoubleSpinner()
        self.tooldia_entry.set_range(0, 9999.9999)
        self.tooldia_entry.set_precision(self.decimals)
        self.tooldia_entry.setSingleStep(0.1)
        self.custom_box.addWidget(self.tooldia_entry)

        # Update plot button
        self.updateplot_button = QtWidgets.QPushButton(_('Update Plot'))
        self.updateplot_button.setToolTip(
            _("Update the plot.")
        )
        self.custom_box.addWidget(self.updateplot_button)

        # ####################
        # ## Export G-Code ##
        # ####################
        self.export_gcode_label = QtWidgets.QLabel("<b>%s:</b>" % _("Export CNC Code"))
        self.export_gcode_label.setToolTip(
            _("Export and save G-Code to\n"
              "make this object to a file.")
        )
        self.custom_box.addWidget(self.export_gcode_label)

        # Prepend text to GCode
        prependlabel = QtWidgets.QLabel('%s:' % _('Prepend to CNC Code'))
        prependlabel.setToolTip(
            _("Type here any G-Code commands you would\n"
              "like to add at the beginning of the G-Code file.")
        )
        self.custom_box.addWidget(prependlabel)

        self.prepend_text = FCTextArea()
        self.prepend_text.setPlaceholderText(
            _("Type here any G-Code commands you would\n"
              "like to add at the beginning of the G-Code file.")
        )
        self.custom_box.addWidget(self.prepend_text)

        # Append text to GCode
        appendlabel = QtWidgets.QLabel('%s:' % _('Append to CNC Code'))
        appendlabel.setToolTip(
            _("Type here any G-Code commands you would\n"
              "like to append to the generated file.\n"
              "I.e.: M2 (End of program)")
        )
        self.custom_box.addWidget(appendlabel)

        self.append_text = FCTextArea()
        self.append_text.setPlaceholderText(
            _("Type here any G-Code commands you would\n"
              "like to append to the generated file.\n"
              "I.e.: M2 (End of program)")
        )
        self.custom_box.addWidget(self.append_text)

        self.cnc_frame = QtWidgets.QFrame()
        self.cnc_frame.setContentsMargins(0, 0, 0, 0)
        self.custom_box.addWidget(self.cnc_frame)
        self.cnc_box = QtWidgets.QVBoxLayout()
        self.cnc_box.setContentsMargins(0, 0, 0, 0)
        self.cnc_frame.setLayout(self.cnc_box)

        # Toolchange Custom G-Code
        self.toolchangelabel = QtWidgets.QLabel('%s:' % _('Toolchange G-Code'))
        self.toolchangelabel.setToolTip(
            _(
                "Type here any G-Code commands you would\n"
                "like to be executed when Toolchange event is encountered.\n"
                "This will constitute a Custom Toolchange GCode,\n"
                "or a Toolchange Macro.\n"
                "The FlatCAM variables are surrounded by '%' symbol.\n\n"
                "WARNING: it can be used only with a preprocessor file\n"
                "that has 'toolchange_custom' in it's name and this is built\n"
                "having as template the 'Toolchange Custom' posprocessor file."
            )
        )
        self.cnc_box.addWidget(self.toolchangelabel)

        self.toolchange_text = FCTextArea()
        self.toolchange_text.setPlaceholderText(
            _(
                "Type here any G-Code commands you would\n"
                "like to be executed when Toolchange event is encountered.\n"
                "This will constitute a Custom Toolchange GCode,\n"
                "or a Toolchange Macro.\n"
                "The FlatCAM variables are surrounded by '%' symbol.\n"
                "WARNING: it can be used only with a preprocessor file\n"
                "that has 'toolchange_custom' in it's name."
            )
        )
        self.cnc_box.addWidget(self.toolchange_text)

        cnclay = QtWidgets.QHBoxLayout()
        self.cnc_box.addLayout(cnclay)

        # Toolchange Replacement Enable
        self.toolchange_cb = FCCheckBox(label='%s' % _('Use Toolchange Macro'))
        self.toolchange_cb.setToolTip(
            _("Check this box if you want to use\n"
              "a Custom Toolchange GCode (macro).")
        )

        # Variable list
        self.tc_variable_combo = FCComboBox()
        self.tc_variable_combo.setToolTip(
            _(
                "A list of the FlatCAM variables that can be used\n"
                "in the Toolchange event.\n"
                "They have to be surrounded by the '%' symbol"
            )
        )

        # Populate the Combo Box
        variables = [_('Parameters'), 'tool', 'tooldia', 't_drills', 'x_toolchange', 'y_toolchange', 'z_toolchange',
                     'z_cut', 'z_move', 'z_depthpercut', 'spindlespeed', 'dwelltime']
        self.tc_variable_combo.addItems(variables)
        self.tc_variable_combo.setItemData(0, _("FlatCAM CNC parameters"), Qt.ToolTipRole)
        self.tc_variable_combo.setItemData(1, "tool = " + _("tool number"), Qt.ToolTipRole)
        self.tc_variable_combo.setItemData(2, "tooldia = " + _("tool diameter"), Qt.ToolTipRole)
        self.tc_variable_combo.setItemData(3, "t_drills = " + _("for Excellon, total number of drills"),
                                           Qt.ToolTipRole)
        self.tc_variable_combo.setItemData(4, "x_toolchange = " + _("X coord for Toolchange"), Qt.ToolTipRole)
        self.tc_variable_combo.setItemData(5, "y_toolchange = " + _("Y coord for Toolchange"), Qt.ToolTipRole)
        self.tc_variable_combo.setItemData(6, "z_toolchange = " + _("Z coord for Toolchange"), Qt.ToolTipRole)
        self.tc_variable_combo.setItemData(7, "z_cut = " + _("depth where to cut"), Qt.ToolTipRole)
        self.tc_variable_combo.setItemData(8, "z_move = " + _("height where to travel"), Qt.ToolTipRole)
        self.tc_variable_combo.setItemData(9, "z_depthpercut = " + _("the step value for multidepth cut"),
                                           Qt.ToolTipRole)
        self.tc_variable_combo.setItemData(10, "spindlesspeed = " + _("the value for the spindle speed"),
                                           Qt.ToolTipRole)
        self.tc_variable_combo.setItemData(11, "dwelltime = " + _("time to dwell to allow the "
                                                                  "spindle to reach it's set RPM"),
                                           Qt.ToolTipRole)

        cnclay.addWidget(self.toolchange_cb)
        cnclay.addStretch()
        cnclay.addWidget(self.tc_variable_combo)

        self.toolch_ois = OptionalInputSection(self.toolchange_cb,
                                               [self.toolchangelabel, self.toolchange_text, self.tc_variable_combo])

        h_lay = QtWidgets.QHBoxLayout()
        h_lay.setAlignment(QtCore.Qt.AlignVCenter)
        self.custom_box.addLayout(h_lay)

        # Edit GCode Button
        self.modify_gcode_button = QtWidgets.QPushButton(_('View CNC Code'))
        self.modify_gcode_button.setToolTip(
            _("Opens TAB to view/modify/print G-Code\n"
              "file.")
        )

        # GO Button
        self.export_gcode_button = QtWidgets.QPushButton(_('Save CNC Code'))
        self.export_gcode_button.setToolTip(
            _("Opens dialog to save G-Code\n"
              "file.")
        )

        h_lay.addWidget(self.modify_gcode_button)
        h_lay.addWidget(self.export_gcode_button)
        # self.custom_box.addWidget(self.export_gcode_button)


class ScriptObjectUI(ObjectUI):
    """
    User interface for Script  objects.
    """

    def __init__(self, decimals, parent=None):
        """
        Creates the user interface for Script objects. GUI elements should
        be placed in ``self.custom_box`` to preserve the layout.
        """

        theme_settings = QtCore.QSettings("Open Source", "FlatCAM")
        if theme_settings.contains("theme"):
            theme = theme_settings.value('theme', type=str)
        else:
            theme = 'white'

        if theme == 'white':
            self.resource_loc = 'share'
        else:
            self.resource_loc = 'share'

        ObjectUI.__init__(self, title=_('Script Object'),
                          icon_file=self.resource_loc + '/script_new24.png',
                          parent=parent,
                          common=False,
                          decimals=decimals)

        self.decimals = decimals

        # ## Object name
        self.name_hlay = QtWidgets.QHBoxLayout()
        self.custom_box.addLayout(self.name_hlay)

        name_label = QtWidgets.QLabel("<b>%s:</b>" % _("Name"))
        self.name_entry = FCEntry()
        self.name_entry.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.name_hlay.addWidget(name_label)
        self.name_hlay.addWidget(self.name_entry)

        h_lay = QtWidgets.QHBoxLayout()
        h_lay.setAlignment(QtCore.Qt.AlignVCenter)
        self.custom_box.addLayout(h_lay)

        self.autocomplete_cb = FCCheckBox("%s" % _("Auto Completer"))
        self.autocomplete_cb.setToolTip(
            _("This selects if the auto completer is enabled in the Script Editor.")
        )
        self.autocomplete_cb.setStyleSheet(
            """
            QCheckBox {font-weight: bold; color: black}
            """
        )
        h_lay.addWidget(self.autocomplete_cb)
        h_lay.addStretch()

        # Plot CB - this is added only for compatibility; other FlatCAM objects expect it and the mechanism is already
        # established and I don't want to changed it right now
        self.plot_cb = FCCheckBox()
        self.plot_cb.setLayoutDirection(QtCore.Qt.RightToLeft)
        self.custom_box.addWidget(self.plot_cb)
        self.plot_cb.hide()

        self.custom_box.addStretch()


class DocumentObjectUI(ObjectUI):
    """
    User interface for Notes objects.
    """

    def __init__(self, decimals, parent=None):
        """
        Creates the user interface for Notes objects. GUI elements should
        be placed in ``self.custom_box`` to preserve the layout.
        """

        theme_settings = QtCore.QSettings("Open Source", "FlatCAM")
        if theme_settings.contains("theme"):
            theme = theme_settings.value('theme', type=str)
        else:
            theme = 'white'

        if theme == 'white':
            self.resource_loc = 'share'
        else:
            self.resource_loc = 'share'

        ObjectUI.__init__(self, title=_('Document Object'),
                          icon_file=self.resource_loc + '/notes16_1.png',
                          parent=parent,
                          common=False,
                          decimals=decimals)

        self.decimals = decimals

        # ## Object name
        self.name_hlay = QtWidgets.QHBoxLayout()
        self.custom_box.addLayout(self.name_hlay)

        name_label = QtWidgets.QLabel("<b>%s:</b>" % _("Name"))
        self.name_entry = FCEntry()
        self.name_entry.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.name_hlay.addWidget(name_label)
        self.name_hlay.addWidget(self.name_entry)

        # Plot CB - this is added only for compatibility; other FlatCAM objects expect it and the mechanism is already
        # established and I don't want to changed it right now
        self.plot_cb = FCCheckBox()
        self.plot_cb.setLayoutDirection(QtCore.Qt.RightToLeft)
        self.custom_box.addWidget(self.plot_cb)
        self.plot_cb.hide()

        h_lay = QtWidgets.QHBoxLayout()
        h_lay.setAlignment(QtCore.Qt.AlignVCenter)
        self.custom_box.addLayout(h_lay)

        self.autocomplete_cb = FCCheckBox("%s" % _("Auto Completer"))
        self.autocomplete_cb.setToolTip(
            _("This selects if the auto completer is enabled in the Document Editor.")
        )
        self.autocomplete_cb.setStyleSheet(
            """
            QCheckBox {font-weight: bold; color: black}
            """
        )
        h_lay.addWidget(self.autocomplete_cb)
        h_lay.addStretch()

        # ##############################################################
        # ############ FORM LAYOUT #####################################
        # ##############################################################

        self.form_box = QtWidgets.QFormLayout()
        self.custom_box.addLayout(self.form_box)

        # Font
        self.font_type_label = QtWidgets.QLabel('%s:' % _("Font Type"))

        if sys.platform == "win32":
            f_current = QtGui.QFont("Arial")
        elif sys.platform == "linux":
            f_current = QtGui.QFont("FreeMono")
        else:
            f_current = QtGui.QFont("Helvetica Neue")

        self.font_name = f_current.family()

        self.font_type_cb = QtWidgets.QFontComboBox(self)
        self.font_type_cb.setCurrentFont(f_current)

        self.form_box.addRow(self.font_type_label, self.font_type_cb)

        # Font Size
        self.font_size_label = QtWidgets.QLabel('%s:' % _("Font Size"))

        self.font_size_cb = FCComboBox()
        self.font_size_cb.setEditable(True)
        self.font_size_cb.setMinimumContentsLength(3)
        self.font_size_cb.setMaximumWidth(70)

        font_sizes = ['6', '7', '8', '9', '10', '11', '12', '13', '14',
                      '15', '16', '18', '20', '22', '24', '26', '28',
                      '32', '36', '40', '44', '48', '54', '60', '66',
                      '72', '80', '88', '96']

        for i in font_sizes:
            self.font_size_cb.addItem(i)

        size_hlay = QtWidgets.QHBoxLayout()
        size_hlay.addWidget(self.font_size_cb)
        size_hlay.addStretch()

        self.font_bold_tb = QtWidgets.QToolButton()
        self.font_bold_tb.setCheckable(True)
        self.font_bold_tb.setIcon(QtGui.QIcon(self.resource_loc + '/bold32.png'))
        size_hlay.addWidget(self.font_bold_tb)

        self.font_italic_tb = QtWidgets.QToolButton()
        self.font_italic_tb.setCheckable(True)
        self.font_italic_tb.setIcon(QtGui.QIcon(self.resource_loc + '/italic32.png'))
        size_hlay.addWidget(self.font_italic_tb)
        self.font_under_tb = QtWidgets.QToolButton()
        self.font_under_tb.setCheckable(True)
        self.font_under_tb.setIcon(QtGui.QIcon(self.resource_loc + '/underline32.png'))
        size_hlay.addWidget(self.font_under_tb)

        self.form_box.addRow(self.font_size_label, size_hlay)

        # Alignment Choices
        self.alignment_label = QtWidgets.QLabel('%s:' % _("Alignment"))

        al_hlay = QtWidgets.QHBoxLayout()

        self.al_left_tb = QtWidgets.QToolButton()
        self.al_left_tb.setToolTip(_("Align Left"))
        self.al_left_tb.setIcon(QtGui.QIcon(self.resource_loc + '/align_left32.png'))
        al_hlay.addWidget(self.al_left_tb)

        self.al_center_tb = QtWidgets.QToolButton()
        self.al_center_tb.setToolTip(_("Center"))
        self.al_center_tb.setIcon(QtGui.QIcon(self.resource_loc + '/align_center32.png'))
        al_hlay.addWidget(self.al_center_tb)

        self.al_right_tb = QtWidgets.QToolButton()
        self.al_right_tb.setToolTip(_("Align Right"))
        self.al_right_tb.setIcon(QtGui.QIcon(self.resource_loc + '/align_right32.png'))
        al_hlay.addWidget(self.al_right_tb)

        self.al_justify_tb = QtWidgets.QToolButton()
        self.al_justify_tb.setToolTip(_("Justify"))
        self.al_justify_tb.setIcon(QtGui.QIcon(self.resource_loc + '/align_justify32.png'))
        al_hlay.addWidget(self.al_justify_tb)

        self.form_box.addRow(self.alignment_label, al_hlay)

        # Font Color
        self.font_color_label = QtWidgets.QLabel('%s:' % _('Font Color'))
        self.font_color_label.setToolTip(
           _("Set the font color for the selected text")
        )
        self.font_color_entry = FCEntry()
        self.font_color_button = QtWidgets.QPushButton()
        self.font_color_button.setFixedSize(15, 15)

        self.form_box_child_1 = QtWidgets.QHBoxLayout()
        self.form_box_child_1.addWidget(self.font_color_entry)
        self.form_box_child_1.addWidget(self.font_color_button)
        self.form_box_child_1.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        self.form_box.addRow(self.font_color_label, self.form_box_child_1)

        # Selection Color
        self.sel_color_label = QtWidgets.QLabel('%s:' % _('Selection Color'))
        self.sel_color_label.setToolTip(
           _("Set the selection color when doing text selection.")
        )
        self.sel_color_entry = FCEntry()
        self.sel_color_button = QtWidgets.QPushButton()
        self.sel_color_button.setFixedSize(15, 15)

        self.form_box_child_2 = QtWidgets.QHBoxLayout()
        self.form_box_child_2.addWidget(self.sel_color_entry)
        self.form_box_child_2.addWidget(self.sel_color_button)
        self.form_box_child_2.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        self.form_box.addRow(self.sel_color_label, self.form_box_child_2)

        # Tab size
        self.tab_size_label = QtWidgets.QLabel('%s:' % _('Tab Size'))
        self.tab_size_label.setToolTip(
            _("Set the tab size. In pixels. Default value is 80 pixels.")
        )
        self.tab_size_spinner = FCSpinner()
        self.tab_size_spinner.set_range(0, 1000)

        self.form_box.addRow(self.tab_size_label, self.tab_size_spinner)

        self.custom_box.addStretch()

# end of file
