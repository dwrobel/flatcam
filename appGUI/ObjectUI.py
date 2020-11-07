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

from appGUI.GUIElements import *
import sys

import gettext
import appTranslation as fcTranslate
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

    def __init__(self, app, icon_file='assets/resources/flatcam_icon32.png', title=_('App Object'),
                 parent=None, common=True):
        QtWidgets.QWidget.__init__(self, parent=parent)

        self.app = app
        self.decimals = app.decimals

        theme_settings = QtCore.QSettings("Open Source", "FlatCAM")
        if theme_settings.contains("theme"):
            theme = theme_settings.value('theme', type=str)
        else:
            theme = 'white'

        if theme == 'white':
            self.resource_loc = 'assets/resources'
        else:
            self.resource_loc = 'assets/resources'

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        # ## Page Title box (spacing between children)
        self.title_box = QtWidgets.QHBoxLayout()
        layout.addLayout(self.title_box)

        # ## Page Title icon
        pixmap = QtGui.QPixmap(icon_file.replace('assets/resources', self.resource_loc))
        self.icon = FCLabel()
        self.icon.setPixmap(pixmap)
        self.title_box.addWidget(self.icon, stretch=0)

        # ## Title label
        self.title_label = FCLabel("<font size=5><b>%s</b></font>" % title)
        self.title_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.title_box.addWidget(self.title_label, stretch=1)

        # ## App Level label
        self.level = FCLabel("")
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

            # self.common_grid.addWidget(FCLabel(''), 1, 0, 1, 2)
            separator_line = QtWidgets.QFrame()
            separator_line.setFrameShape(QtWidgets.QFrame.HLine)
            separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
            self.common_grid.addWidget(separator_line, 1, 0, 1, 2)

            self.transform_label = FCLabel('<b>%s</b>' % _('Transformations'))
            self.transform_label.setToolTip(
                _("Geometrical transformations of the current object.")
            )

            self.common_grid.addWidget(self.transform_label, 2, 0, 1, 2)

            # ### Scale ####
            self.scale_entry = NumericalEvalEntry(border_color='#0069A9')
            self.scale_entry.set_value(1.0)
            self.scale_entry.setToolTip(
                _("Factor by which to multiply\n"
                  "geometric features of this object.\n"
                  "Expressions are allowed. E.g: 1/25.4")
            )
            # GO Button
            self.scale_button = FCButton(_('Scale'))
            self.scale_button.setToolTip(
                _("Perform scaling operation.")
            )
            self.scale_button.setMinimumWidth(70)

            self.common_grid.addWidget(self.scale_entry, 3, 0)
            self.common_grid.addWidget(self.scale_button, 3, 1)

            # ### Offset ####
            self.offsetvector_entry = NumericalEvalTupleEntry(border_color='#0069A9')
            self.offsetvector_entry.setText("(0.0, 0.0)")
            self.offsetvector_entry.setToolTip(
                _("Amount by which to move the object\n"
                  "in the x and y axes in (x, y) format.\n"
                  "Expressions are allowed. E.g: (1/3.2, 0.5*3)")
            )

            self.offset_button = FCButton(_('Offset'))
            self.offset_button.setToolTip(
                _("Perform the offset operation.")
            )
            self.offset_button.setMinimumWidth(70)

            self.common_grid.addWidget(self.offsetvector_entry, 4, 0)
            self.common_grid.addWidget(self.offset_button, 4, 1)

            self.transformations_button = FCButton(_('Transformations'))
            self.transformations_button.setIcon(QtGui.QIcon(self.app.resource_location + '/transform.png'))
            self.transformations_button.setToolTip(
                _("Geometrical transformations of the current object.")
            )
            self.common_grid.addWidget(self.transformations_button, 5, 0, 1, 2)

        layout.addStretch()
    
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
            self.app.inform[str, bool].emit(
                '[WARNING_NOTCL] %s: [%d, %d]' % (_("Edited value is out of range"), minval, maxval), False)
        else:
            self.app.inform[str, bool].emit('[success] %s' % _("Edited value is within limits."), False)


class GerberObjectUI(ObjectUI):
    """
    User interface for Gerber objects.
    """

    def __init__(self, app, parent=None):
        self.decimals = app.decimals
        self.app = app

        ObjectUI.__init__(self, title=_('Gerber Object'), parent=parent, app=self.app)

        # Plot options
        grid0 = QtWidgets.QGridLayout()
        grid0.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.custom_box.addLayout(grid0)
        grid0.setColumnStretch(0, 0)
        grid0.setColumnStretch(1, 1)

        self.plot_options_label = FCLabel("<b>%s:</b>" % _("Plot Options"))

        grid0.addWidget(self.plot_options_label, 0, 0)

        # Solid CB
        self.solid_cb = FCCheckBox(label=_('Solid'))
        self.solid_cb.setToolTip(
            _("Solid color polygons.")
        )
        grid0.addWidget(self.solid_cb, 0, 1)

        # Multicolored CB
        self.multicolored_cb = FCCheckBox(label=_('Multi-Color'))
        self.multicolored_cb.setToolTip(
            _("Draw polygons in different colors.")
        )
        grid0.addWidget(self.multicolored_cb, 0, 2)

        # ## Object name
        self.name_hlay = QtWidgets.QHBoxLayout()
        grid0.addLayout(self.name_hlay, 1, 0, 1, 3)

        name_label = FCLabel("<b>%s:</b>" % _("Name"))
        self.name_entry = FCEntry()
        self.name_entry.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.name_hlay.addWidget(name_label)
        self.name_hlay.addWidget(self.name_entry)

        # Plot CB
        self.plot_lbl = FCLabel('%s:' % _("Plot"))
        self.plot_lbl.setToolTip(_("Plot (show) this object."))
        self.plot_cb = FCCheckBox()

        grid0.addWidget(self.plot_lbl, 2, 0)
        grid0.addWidget(self.plot_cb, 2, 1)

        # Generate 'Follow'
        self.follow_cb = FCCheckBox('%s' % _("Follow"))
        self.follow_cb.setToolTip(_("Generate a 'Follow' geometry.\n"
                                    "This means that it will cut through\n"
                                    "the middle of the trace."))
        grid0.addWidget(self.follow_cb, 2, 2)

        # Editor
        self.editor_button = FCButton(_('Gerber Editor'))
        self.editor_button.setIcon(QtGui.QIcon(self.app.resource_location + '/edit_file32.png'))
        self.editor_button.setToolTip(
            _("Start the Object Editor")
        )
        self.editor_button.setStyleSheet("""
                                      QPushButton
                                      {
                                          font-weight: bold;
                                      }
                                      """)
        grid0.addWidget(self.editor_button, 4, 0, 1, 3)

        # PROPERTIES CB
        self.properties_button = FCButton('%s' % _("PROPERTIES"), checkable=True)
        self.properties_button.setIcon(QtGui.QIcon(self.app.resource_location + '/properties32.png'))
        self.properties_button.setToolTip(_("Show the Properties."))
        self.properties_button.setStyleSheet("""
                                      QPushButton
                                      {
                                          font-weight: bold;
                                      }
                                      """)
        grid0.addWidget(self.properties_button, 6, 0, 1, 3)

        # PROPERTIES Frame
        self.properties_frame = QtWidgets.QFrame()
        self.properties_frame.setContentsMargins(0, 0, 0, 0)
        grid0.addWidget(self.properties_frame, 7, 0, 1, 3)
        self.properties_box = QtWidgets.QVBoxLayout()
        self.properties_box.setContentsMargins(0, 0, 0, 0)
        self.properties_frame.setLayout(self.properties_box)
        self.properties_frame.hide()

        self.treeWidget = FCTree(columns=2)

        self.properties_box.addWidget(self.treeWidget)
        self.properties_box.setStretch(0, 0)

        # ### Gerber Apertures ####
        self.apertures_table_label = FCLabel('%s:' % _('Apertures'))
        self.apertures_table_label.setToolTip(
            _("Apertures Table for the Gerber Object.")
        )

        grid0.addWidget(self.apertures_table_label, 8, 0)

        # Aperture Table Visibility CB
        self.aperture_table_visibility_cb = FCCheckBox()
        self.aperture_table_visibility_cb.setToolTip(
            _("Toggle the display of the Tools Table.")
        )
        # self.aperture_table_visibility_cb.setLayoutDirection(QtCore.Qt.RightToLeft)
        grid0.addWidget(self.aperture_table_visibility_cb, 8, 1)

        hlay_plot = QtWidgets.QHBoxLayout()
        grid0.addLayout(hlay_plot, 8, 2)

        # Aperture Mark all CB
        self.mark_all_cb = FCCheckBox(_('Mark All'))
        self.mark_all_cb.setToolTip(
            _("When checked it will display all the apertures.\n"
              "When unchecked, it will delete all mark shapes\n"
              "that are drawn on canvas.")

        )
        self.mark_all_cb.setLayoutDirection(QtCore.Qt.RightToLeft)
        hlay_plot.addStretch()
        hlay_plot.addWidget(self.mark_all_cb)

        # Apertures Table
        self.apertures_table = FCTable()
        grid0.addWidget(self.apertures_table, 10, 0, 1, 3)

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

        # Buffer Geometry
        self.create_buffer_button = FCButton(_('Buffer Solid Geometry'))
        self.create_buffer_button.setToolTip(
            _("This button is shown only when the Gerber file\n"
              "is loaded without buffering.\n"
              "Clicking this will create the buffered geometry\n"
              "required for isolation.")
        )
        grid0.addWidget(self.create_buffer_button, 12, 0, 1, 3)

        separator_line1 = QtWidgets.QFrame()
        separator_line1.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line1.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line1, 13, 0, 1, 3)

        self.tool_lbl = FCLabel('<b>%s</b>' % _("TOOLS"))
        grid0.addWidget(self.tool_lbl, 14, 0, 1, 3)

        # Isolation Tool - will create isolation paths around the copper features
        self.iso_button = FCButton(_('Isolation Routing'))
        # self.iso_button.setIcon(QtGui.QIcon(self.app.resource_location + '/iso_16.png'))
        self.iso_button.setToolTip(
            _("Create a Geometry object with\n"
              "toolpaths to cut around polygons.")
        )
        self.iso_button.setStyleSheet("""
                                      QPushButton
                                      {
                                          font-weight: bold;
                                      }
                                      """)
        grid0.addWidget(self.iso_button, 16, 0, 1, 3)

        # ## Clear non-copper regions
        self.generate_ncc_button = FCButton(_('NCC Tool'))
        self.generate_ncc_button.setIcon(QtGui.QIcon(self.app.resource_location + '/eraser26.png'))
        self.generate_ncc_button.setToolTip(
            _("Create the Geometry Object\n"
              "for non-copper routing.")
        )
        # self.generate_ncc_button.setStyleSheet("""
        #                 QPushButton
        #                 {
        #                     font-weight: bold;
        #                 }
        #                 """)
        grid0.addWidget(self.generate_ncc_button, 18, 0, 1, 3)

        # ## Board cutout
        self.generate_cutout_button = FCButton(_('Cutout Tool'))
        self.generate_cutout_button.setIcon(QtGui.QIcon(self.app.resource_location + '/cut32_bis.png'))
        self.generate_cutout_button.setToolTip(
            _("Generate the geometry for\n"
              "the board cutout.")
        )
        # self.generate_cutout_button.setStyleSheet("""
        #                 QPushButton
        #                 {
        #                     font-weight: bold;
        #                 }
        #                 """)
        grid0.addWidget(self.generate_cutout_button, 20, 0, 1, 3)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 22, 0, 1, 3)

        # UTILITIES BUTTON
        self.util_button = FCButton('%s' % _("UTILTIES"), checkable=True)
        self.util_button.setIcon(QtGui.QIcon(self.app.resource_location + '/settings18.png'))
        self.util_button.setToolTip(_("Show the Utilties."))
        self.util_button.setStyleSheet("""
                                      QPushButton
                                      {
                                          font-weight: bold;
                                      }
                                      """)
        grid0.addWidget(self.util_button, 24, 0, 1, 3)

        # UTILITIES Frame
        self.util_frame = QtWidgets.QFrame()
        self.util_frame.setContentsMargins(0, 0, 0, 0)
        grid0.addWidget(self.util_frame, 25, 0, 1, 3)
        self.util_box = QtWidgets.QVBoxLayout()
        self.util_box.setContentsMargins(0, 0, 0, 0)
        self.util_frame.setLayout(self.util_box)
        self.util_frame.hide()

        util_grid = QtWidgets.QGridLayout()
        util_grid.setColumnStretch(0, 0)
        util_grid.setColumnStretch(1, 1)
        self.util_box.addLayout(util_grid)

        # ## Non-copper regions
        self.noncopper_label = FCLabel("<b>%s</b>" % _("Non-copper regions"))
        self.noncopper_label.setToolTip(
            _("Create polygons covering the\n"
              "areas without copper on the PCB.\n"
              "Equivalent to the inverse of this\n"
              "object. Can be used to remove all\n"
              "copper from a specified region.")
        )

        util_grid.addWidget(self.noncopper_label, 0, 0, 1, 3)

        # Margin
        bmlabel = FCLabel('%s:' % _('Boundary Margin'))
        bmlabel.setToolTip(
            _("Specify the edge of the PCB\n"
              "by drawing a box around all\n"
              "objects with this minimum\n"
              "distance.")
        )

        self.noncopper_margin_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.noncopper_margin_entry.set_range(-10000.0000, 10000.0000)
        self.noncopper_margin_entry.set_precision(self.decimals)
        self.noncopper_margin_entry.setSingleStep(0.1)

        util_grid.addWidget(bmlabel, 2, 0)
        util_grid.addWidget(self.noncopper_margin_entry, 2, 1, 1, 2)

        # Rounded corners
        self.noncopper_rounded_cb = FCCheckBox(label=_("Rounded"))
        self.noncopper_rounded_cb.setToolTip(
            _("Resulting geometry will have rounded corners.")
        )

        self.generate_noncopper_button = FCButton(_('Generate Geometry'))
        self.generate_noncopper_button.setIcon(QtGui.QIcon(self.app.resource_location + '/geometry32.png'))
        util_grid.addWidget(self.noncopper_rounded_cb, 4, 0)
        util_grid.addWidget(self.generate_noncopper_button, 4, 1, 1, 2)

        separator_line1 = QtWidgets.QFrame()
        separator_line1.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line1.setFrameShadow(QtWidgets.QFrame.Sunken)
        util_grid.addWidget(separator_line1, 6, 0, 1, 3)

        # ## Bounding box
        self.boundingbox_label = FCLabel('<b>%s</b>' % _('Bounding Box'))
        self.boundingbox_label.setToolTip(
            _("Create a geometry surrounding the Gerber object.\n"
              "Square shape.")
        )

        util_grid.addWidget(self.boundingbox_label, 8, 0, 1, 3)

        bbmargin = FCLabel('%s:' % _('Boundary Margin'))
        bbmargin.setToolTip(
            _("Distance of the edges of the box\n"
              "to the nearest polygon.")
        )
        self.bbmargin_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.bbmargin_entry.set_range(-10000.0000, 10000.0000)
        self.bbmargin_entry.set_precision(self.decimals)
        self.bbmargin_entry.setSingleStep(0.1)

        util_grid.addWidget(bbmargin, 10, 0)
        util_grid.addWidget(self.bbmargin_entry, 10, 1, 1, 2)

        self.bbrounded_cb = FCCheckBox(label=_("Rounded"))
        self.bbrounded_cb.setToolTip(
            _("If the bounding box is \n"
              "to have rounded corners\n"
              "their radius is equal to\n"
              "the margin.")
        )

        self.generate_bb_button = FCButton(_('Generate Geometry'))
        self.generate_bb_button.setIcon(QtGui.QIcon(self.app.resource_location + '/geometry32.png'))
        self.generate_bb_button.setToolTip(
            _("Generate the Geometry object.")
        )
        util_grid.addWidget(self.bbrounded_cb, 12, 0)
        util_grid.addWidget(self.generate_bb_button, 12, 1, 1, 2)


class ExcellonObjectUI(ObjectUI):
    """
    User interface for Excellon objects.
    """

    def __init__(self, app, parent=None):

        self.decimals = app.decimals
        self.app = app

        theme_settings = QtCore.QSettings("Open Source", "FlatCAM")
        if theme_settings.contains("theme"):
            theme = theme_settings.value('theme', type=str)
        else:
            theme = 'white'

        if theme == 'white':
            self.resource_loc = 'assets/resources'
        else:
            self.resource_loc = 'assets/resources'

        ObjectUI.__init__(self, title=_('Excellon Object'),
                          icon_file=self.resource_loc + '/drill32.png',
                          parent=parent,
                          app=self.app)

        grid0 = QtWidgets.QGridLayout()
        grid0.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        grid0.setColumnStretch(0, 0)
        grid0.setColumnStretch(1, 1)
        self.custom_box.addLayout(grid0)

        # Plot options
        self.plot_options_label = FCLabel("<b>%s:</b>" % _("Plot Options"))

        # Solid CB
        self.solid_cb = FCCheckBox(label=_('Solid'))
        self.solid_cb.setToolTip(
            _("Solid circles.")
        )

        # Multicolored CB
        self.multicolored_cb = FCCheckBox(label=_('Multi-Color'))
        self.multicolored_cb.setToolTip(
            _("Draw polygons in different colors.")
        )

        grid0.addWidget(self.plot_options_label, 0, 0)
        grid0.addWidget(self.solid_cb, 0, 1)
        grid0.addWidget(self.multicolored_cb, 0, 2)

        # ## Object name
        self.name_hlay = QtWidgets.QHBoxLayout()

        name_label = FCLabel("<b>%s:</b>" % _("Name"))
        self.name_entry = FCEntry()
        self.name_entry.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.name_hlay.addWidget(name_label)
        self.name_hlay.addWidget(self.name_entry)

        grid0.addLayout(self.name_hlay, 2, 0, 1, 3)

        # Editor
        self.editor_button = FCButton(_('Excellon Editor'))
        self.editor_button.setIcon(QtGui.QIcon(self.app.resource_location + '/edit_file32.png'))

        self.editor_button.setToolTip(
            _("Start the Object Editor")
        )
        self.editor_button.setStyleSheet("""
                                      QPushButton
                                      {
                                          font-weight: bold;
                                      }
                                      """)
        grid0.addWidget(self.editor_button, 4, 0, 1, 3)

        # PROPERTIES CB
        self.properties_button = FCButton('%s' % _("PROPERTIES"), checkable=True)
        self.properties_button.setIcon(QtGui.QIcon(self.app.resource_location + '/properties32.png'))
        self.properties_button.setToolTip(_("Show the Properties."))
        self.properties_button.setStyleSheet("""
                                      QPushButton
                                      {
                                          font-weight: bold;
                                      }
                                      """)
        grid0.addWidget(self.properties_button, 6, 0, 1, 3)

        # PROPERTIES Frame
        self.properties_frame = QtWidgets.QFrame()
        self.properties_frame.setContentsMargins(0, 0, 0, 0)
        grid0.addWidget(self.properties_frame, 7, 0, 1, 3)
        self.properties_box = QtWidgets.QVBoxLayout()
        self.properties_box.setContentsMargins(0, 0, 0, 0)
        self.properties_frame.setLayout(self.properties_box)
        self.properties_frame.hide()

        self.treeWidget = FCTree(columns=2)

        self.properties_box.addWidget(self.treeWidget)
        self.properties_box.setStretch(0, 0)

        # ### Tools Drills ####
        self.tools_table_label = FCLabel('<b>%s</b>' % _('Tools Table'))
        self.tools_table_label.setToolTip(
            _("Tools in this Excellon object\n"
              "when are used for drilling.")
        )

        # Table Visibility CB
        self.table_visibility_cb = FCCheckBox()
        self.table_visibility_cb.setToolTip(
            _("Toggle the display of the Tools Table.")
        )

        # Plot CB
        hlay_plot = QtWidgets.QHBoxLayout()
        self.plot_cb = FCCheckBox(_('Plot'))
        self.plot_cb.setToolTip(
            _("Plot (show) this object.")
        )
        self.plot_cb.setLayoutDirection(QtCore.Qt.RightToLeft)
        hlay_plot.addStretch()
        hlay_plot.addWidget(self.plot_cb)

        grid0.addWidget(self.tools_table_label, 8, 0)
        grid0.addWidget(self.table_visibility_cb, 8, 1)
        grid0.addLayout(hlay_plot, 8, 2)

        # #############################################################################################################
        # #############################################################################################################
        # add a frame and inside add a vertical box layout. Inside this vbox layout I add all the Drills widgets
        # this way I can hide/show the frame
        # #############################################################################################################
        # #############################################################################################################

        self.drills_frame = QtWidgets.QFrame()
        self.drills_frame.setContentsMargins(0, 0, 0, 0)
        self.custom_box.addWidget(self.drills_frame)
        self.tools_box = QtWidgets.QVBoxLayout()
        self.tools_box.setContentsMargins(0, 0, 0, 0)
        self.drills_frame.setLayout(self.tools_box)

        self.tools_table = FCTable()
        self.tools_table.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.tools_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tools_box.addWidget(self.tools_table)

        self.tools_table.setColumnCount(6)
        self.tools_table.setHorizontalHeaderLabels(['#', _('Diameter'), _('Drills'), _('Slots'),
                                                    "C", 'P'])
        self.tools_table.setSortingEnabled(False)

        self.tools_table.horizontalHeaderItem(0).setToolTip(
            _("This is the Tool Number.\n"
              "When ToolChange is checked, on toolchange event this value\n"
              "will be showed as a T1, T2 ... Tn in the Machine Code.\n\n"
              "Here the tools are selected for G-code generation."))
        self.tools_table.horizontalHeaderItem(1).setToolTip(
            _("Tool Diameter. Its value\n"
              "is the cut width into the material."))
        self.tools_table.horizontalHeaderItem(2).setToolTip(
            _("The number of Drill holes. Holes that are drilled with\n"
              "a drill bit."))
        self.tools_table.horizontalHeaderItem(3).setToolTip(
            _("The number of Slot holes. Holes that are created by\n"
              "milling them with an endmill bit."))
        self.tools_table.horizontalHeaderItem(4).setToolTip(
            _("Show the color of the drill holes when using multi-color."))
        self.tools_table.horizontalHeaderItem(5).setToolTip(
            _("Toggle display of the drills for the current tool.\n"
              "This does not select the tools for G-code generation."))

        # this column is not used; reserved for future usage
        # self.tools_table.setColumnHidden(4, True)

        # Excellon Tools autoload from DB

        # Auto Load Tools from DB
        self.autoload_db_cb = FCCheckBox('%s' % _("Auto load from DB"))
        self.autoload_db_cb.setToolTip(
            _("Automatic replacement of the tools from related application tools\n"
              "with tools from DB that have a close diameter value.")
        )
        self.tools_box.addWidget(self.autoload_db_cb)

        # #################################################################
        # ########## TOOLS GRID ###########################################
        # #################################################################

        grid2 = QtWidgets.QGridLayout()
        self.tools_box.addLayout(grid2)
        grid2.setColumnStretch(0, 0)
        grid2.setColumnStretch(1, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid2.addWidget(separator_line, 0, 0, 1, 2)

        self.tool_lbl = FCLabel('<b>%s</b>' % _("TOOLS"))
        grid2.addWidget(self.tool_lbl, 2, 0, 1, 2)

        # Drilling Tool - will create GCode for drill holes
        self.drill_button = FCButton(_('Drilling Tool'))
        self.drill_button.setIcon(QtGui.QIcon(self.app.resource_location + '/drilling_tool32.png'))
        self.drill_button.setToolTip(
            _("Generate GCode from the drill holes in an Excellon object.")
        )
        self.drill_button.setStyleSheet("""
                                      QPushButton
                                      {
                                          font-weight: bold;
                                      }
                                      """)
        grid2.addWidget(self.drill_button, 4, 0, 1, 2)

        # Milling Tool - will create GCode for slot holes
        self.milling_button = FCButton(_('Milling Tool'))
        self.milling_button.setIcon(QtGui.QIcon(self.app.resource_location + '/milling_tool32.png'))
        self.milling_button.setToolTip(
            _("Generate a Geometry for milling drills or slots in an Excellon object.")
        )
        # self.milling_button.setStyleSheet("""
        #                 QPushButton
        #                 {
        #                     font-weight: bold;
        #                 }
        #                 """)
        grid2.addWidget(self.milling_button, 6, 0, 1, 2)
        # TODO until the Milling Tool is finished this stays disabled
        self.milling_button.setDisabled(True)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid2.addWidget(separator_line, 8, 0, 1, 2)

        # UTILITIES BUTTON
        self.util_button = FCButton('%s' % _("UTILTIES"), checkable=True)
        self.util_button.setIcon(QtGui.QIcon(self.app.resource_location + '/settings18.png'))
        self.util_button.setToolTip(_("Show the Utilties."))
        self.util_button.setStyleSheet("""
                                      QPushButton
                                      {
                                          font-weight: bold;
                                      }
                                      """)
        grid2.addWidget(self.util_button, 10, 0, 1, 2)

        # UTILITIES Frame
        self.util_frame = QtWidgets.QFrame()
        self.util_frame.setContentsMargins(0, 0, 0, 0)
        grid2.addWidget(self.util_frame, 12, 0, 1, 2)
        self.util_box = QtWidgets.QVBoxLayout()
        self.util_box.setContentsMargins(0, 0, 0, 0)
        self.util_frame.setLayout(self.util_box)
        self.util_frame.hide()

        util_grid = QtWidgets.QGridLayout()
        util_grid.setColumnStretch(0, 0)
        util_grid.setColumnStretch(1, 1)
        self.util_box.addLayout(util_grid)

        # ### Milling Holes Drills ####
        self.mill_hole_label = FCLabel('<b>%s</b>' % _('Milling Geometry'))
        self.mill_hole_label.setToolTip(
            _("Create Geometry for milling holes.\n"
              "Select from the Tools Table above the hole dias to be\n"
              "milled. Use the # column to make the selection.")
        )
        util_grid.addWidget(self.mill_hole_label, 0, 0, 1, 3)

        self.tdlabel = FCLabel('%s:' % _('Milling Diameter'))
        self.tdlabel.setToolTip(
            _("Diameter of the cutting tool.")
        )

        util_grid.addWidget(self.tdlabel, 2, 0, 1, 3)

        self.tooldia_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.tooldia_entry.set_precision(self.decimals)
        self.tooldia_entry.set_range(0.0, 10000.0000)
        self.tooldia_entry.setSingleStep(0.1)

        self.generate_milling_button = FCButton(_('Mill Drills'))
        self.generate_milling_button.setToolTip(
            _("Create the Geometry Object\n"
              "for milling drills.")
        )
        self.generate_milling_button.setStyleSheet("""
                        QPushButton
                        {
                            font-weight: bold;
                        }
                        """)

        util_grid.addWidget(self.tooldia_entry, 4, 0, 1, 2)
        util_grid.addWidget(self.generate_milling_button, 4, 2)

        self.slot_tooldia_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.slot_tooldia_entry.set_precision(self.decimals)
        self.slot_tooldia_entry.set_range(0.0, 10000.0000)
        self.slot_tooldia_entry.setSingleStep(0.1)

        self.generate_milling_slots_button = FCButton(_('Mill Slots'))
        self.generate_milling_slots_button.setToolTip(
            _("Create the Geometry Object\n"
              "for milling slots.")
        )
        self.generate_milling_slots_button.setStyleSheet("""
                        QPushButton
                        {
                            font-weight: bold;
                        }
                        """)

        util_grid.addWidget(self.slot_tooldia_entry, 6, 0, 1, 2)
        util_grid.addWidget(self.generate_milling_slots_button, 6, 2)

    def hide_drills(self, state=True):
        if state is True:
            self.drills_frame.hide()
        else:
            self.drills_frame.show()


class GeometryObjectUI(ObjectUI):
    """
    User interface for Geometry objects.
    """

    def __init__(self, app, parent=None):

        self.decimals = app.decimals
        self.app = app

        theme_settings = QtCore.QSettings("Open Source", "FlatCAM")
        if theme_settings.contains("theme"):
            theme = theme_settings.value('theme', type=str)
        else:
            theme = 'white'

        if theme == 'white':
            self.resource_loc = 'assets/resources'
        else:
            self.resource_loc = 'assets/resources'

        super(GeometryObjectUI, self).__init__(
            title=_('Geometry Object'),
            icon_file=self.resource_loc + '/geometry32.png', parent=parent,  app=self.app
        )

        # Plot options
        grid_header = QtWidgets.QGridLayout()
        grid_header.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.custom_box.addLayout(grid_header)
        grid_header.setColumnStretch(0, 0)
        grid_header.setColumnStretch(1, 1)

        self.plot_options_label = FCLabel("<b>%s:</b>" % _("Plot Options"))
        self.plot_options_label.setMinimumWidth(90)

        grid_header.addWidget(self.plot_options_label, 0, 0)

        # Multicolored CB
        self.multicolored_cb = FCCheckBox(label=_('Multi-Color'))
        self.multicolored_cb.setToolTip(
            _("Draw polygons in different colors.")
        )
        self.multicolored_cb.setMinimumWidth(55)
        grid_header.addWidget(self.multicolored_cb, 0, 2)

        # ## Object name
        self.name_hlay = QtWidgets.QHBoxLayout()
        grid_header.addLayout(self.name_hlay, 2, 0, 1, 3)

        name_label = FCLabel("<b>%s:</b>" % _("Name"))
        self.name_entry = FCEntry()
        self.name_entry.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.name_hlay.addWidget(name_label)
        self.name_hlay.addWidget(self.name_entry)

        # Editor
        self.editor_button = FCButton(_('Geometry Editor'))
        self.editor_button.setIcon(QtGui.QIcon(self.app.resource_location + '/edit_file32.png'))

        self.editor_button.setToolTip(
            _("Start the Object Editor")
        )
        self.editor_button.setStyleSheet("""
                                      QPushButton
                                      {
                                          font-weight: bold;
                                      }
                                      """)
        grid_header.addWidget(self.editor_button, 4, 0, 1, 3)

        # PROPERTIES CB
        self.properties_button = FCButton('%s' % _("PROPERTIES"), checkable=True)
        self.properties_button.setIcon(QtGui.QIcon(self.app.resource_location + '/properties32.png'))
        self.properties_button.setToolTip(_("Show the Properties."))
        self.properties_button.setStyleSheet("""
                                      QPushButton
                                      {
                                          font-weight: bold;
                                      }
                                      """)
        grid_header.addWidget(self.properties_button, 6, 0, 1, 3)

        # PROPERTIES Frame
        self.properties_frame = QtWidgets.QFrame()
        self.properties_frame.setContentsMargins(0, 0, 0, 0)
        grid_header.addWidget(self.properties_frame, 7, 0, 1, 3)
        self.properties_box = QtWidgets.QVBoxLayout()
        self.properties_box.setContentsMargins(0, 0, 0, 0)
        self.properties_frame.setLayout(self.properties_box)
        self.properties_frame.hide()

        self.treeWidget = FCTree(columns=2)

        self.properties_box.addWidget(self.treeWidget)
        self.properties_box.setStretch(0, 0)

        # add a frame and inside add a vertical box layout. Inside this vbox layout I add all the Tools widgets
        # this way I can hide/show the frame
        self.geo_tools_frame = QtWidgets.QFrame()
        self.geo_tools_frame.setContentsMargins(0, 0, 0, 0)
        self.custom_box.addWidget(self.geo_tools_frame)

        self.geo_tools_box = QtWidgets.QVBoxLayout()
        self.geo_tools_box.setContentsMargins(0, 0, 0, 0)
        self.geo_tools_frame.setLayout(self.geo_tools_box)

        # ************************************************************************
        # ************** TABLE BOX FRAME *****************************************
        # ************************************************************************
        self.geo_table_frame = QtWidgets.QFrame()
        self.geo_table_frame.setContentsMargins(0, 0, 0, 0)
        self.geo_tools_box.addWidget(self.geo_table_frame)
        self.geo_table_box = QtWidgets.QVBoxLayout()
        self.geo_table_box.setContentsMargins(0, 0, 0, 0)
        self.geo_table_frame.setLayout(self.geo_table_box)

        grid0 = QtWidgets.QGridLayout()
        self.geo_table_box.addLayout(grid0)
        grid0.setColumnStretch(0, 0)
        grid0.setColumnStretch(1, 1)

        # ### Tools ####
        self.tools_table_label = FCLabel('<b>%s:</b>' % _('Tools Table'))
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
        grid0.addWidget(self.tools_table_label, 0, 0)

        # Plot CB
        # self.plot_cb = QtWidgets.QCheckBox('Plot')
        self.plot_cb = FCCheckBox(_('Plot Object'))
        self.plot_cb.setToolTip(
            _("Plot (show) this object.")
        )
        self.plot_cb.setLayoutDirection(QtCore.Qt.RightToLeft)
        grid0.addWidget(self.plot_cb, 0, 1)

        self.geo_tools_table = FCTable(drag_drop=True)
        grid0.addWidget(self.geo_tools_table, 1, 0, 1, 2)
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
            _("Tool Diameter. Its value\n"
              "is the cut width into the material."))
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
                "- V-Shape -> it will disable Z-Cut parameter in the UI form and enable two additional UI form\n"
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

        # Tool Offset
        grid1 = QtWidgets.QGridLayout()
        self.geo_table_box.addLayout(grid1)
        grid1.setColumnStretch(0, 0)
        grid1.setColumnStretch(1, 1)

        self.tool_offset_lbl = FCLabel('%s:' % _('Tool Offset'))
        self.tool_offset_lbl.setToolTip(
            _(
                "The value to offset the cut when \n"
                "the Offset type selected is 'Offset'.\n"
                "The value can be positive for 'outside'\n"
                "cut and negative for 'inside' cut."
            )
        )
        self.tool_offset_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.tool_offset_entry.set_precision(self.decimals)
        self.tool_offset_entry.set_range(-10000.0000, 10000.0000)
        self.tool_offset_entry.setSingleStep(0.1)

        grid1.addWidget(self.tool_offset_lbl, 0, 0)
        grid1.addWidget(self.tool_offset_entry, 0, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid1.addWidget(separator_line, 1, 0, 1, 2)

        self.tool_sel_label = FCLabel('<b>%s</b>' % _("Add from DB"))
        grid1.addWidget(self.tool_sel_label, 2, 0, 1, 2)

        self.addtool_entry_lbl = FCLabel('%s:' % _('Tool Dia'))
        self.addtool_entry_lbl.setToolTip(
            _("Diameter for the new tool")
        )
        self.addtool_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.addtool_entry.set_precision(self.decimals)
        self.addtool_entry.set_range(0.00001, 10000.0000)
        self.addtool_entry.setSingleStep(0.1)

        grid1.addWidget(self.addtool_entry_lbl, 3, 0)
        grid1.addWidget(self.addtool_entry, 3, 1)

        bhlay = QtWidgets.QHBoxLayout()

        self.search_and_add_btn = FCButton(_('Search and Add'))
        self.search_and_add_btn.setIcon(QtGui.QIcon(self.app.resource_location + '/plus16.png'))
        self.search_and_add_btn.setToolTip(
            _("Add a new tool to the Tool Table\n"
              "with the diameter specified above.")
        )

        self.addtool_from_db_btn = FCButton(_('Pick from DB'))
        self.addtool_from_db_btn.setIcon(QtGui.QIcon(self.app.resource_location + '/search_db32.png'))
        self.addtool_from_db_btn.setToolTip(
            _("Add a new tool to the Tool Table\n"
              "from the Tools Database.\n"
              "Tools database administration in in:\n"
              "Menu: Options -> Tools Database")
        )

        bhlay.addWidget(self.search_and_add_btn)
        bhlay.addWidget(self.addtool_from_db_btn)

        grid1.addLayout(bhlay, 5, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid1.addWidget(separator_line, 9, 0, 1, 2)

        grid2 = QtWidgets.QGridLayout()
        self.geo_table_box.addLayout(grid2)

        self.deltool_btn = FCButton(_('Delete'))
        self.deltool_btn.setIcon(QtGui.QIcon(self.app.resource_location + '/trash16.png'))
        self.deltool_btn.setToolTip(
            _("Delete a selection of tools in the Tool Table\n"
              "by first selecting a row in the Tool Table.")
        )

        grid2.addWidget(self.deltool_btn, 0, 0, 1, 2)

        # ###########################################################
        # ############# Create CNC Job ##############################
        # ###########################################################
        self.geo_param_frame = QtWidgets.QFrame()
        self.geo_param_frame.setContentsMargins(0, 0, 0, 0)
        self.geo_tools_box.addWidget(self.geo_param_frame)

        self.geo_param_box = QtWidgets.QVBoxLayout()
        self.geo_param_box.setContentsMargins(0, 0, 0, 0)
        self.geo_param_frame.setLayout(self.geo_param_box)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.geo_param_box.addWidget(separator_line)

        # #################################################################
        # ################# GRID LAYOUT 3   ###############################
        # #################################################################

        self.grid3 = QtWidgets.QGridLayout()
        self.grid3.setColumnStretch(0, 0)
        self.grid3.setColumnStretch(1, 1)
        self.geo_param_box.addLayout(self.grid3)

        # ### Tools Data ## ##
        self.tool_data_label = FCLabel(
            "<b>%s: <font color='#0000FF'>%s %d</font></b>" % (_('Parameters for'), _("Tool"), int(1)))
        self.tool_data_label.setToolTip(
            _(
                "The data used for creating GCode.\n"
                "Each tool store it's own set of such data."
            )
        )
        self.grid3.addWidget(self.tool_data_label, 0, 0, 1, 2)

        # Tip Dia
        self.tipdialabel = FCLabel('%s:' % _('V-Tip Dia'))
        self.tipdialabel.setToolTip(
            _(
                "The tip diameter for V-Shape Tool"
            )
        )
        self.tipdia_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.tipdia_entry.set_precision(self.decimals)
        self.tipdia_entry.set_range(0.00001, 10000.0000)
        self.tipdia_entry.setSingleStep(0.1)

        self.grid3.addWidget(self.tipdialabel, 1, 0)
        self.grid3.addWidget(self.tipdia_entry, 1, 1)

        # Tip Angle
        self.tipanglelabel = FCLabel('%s:' % _('V-Tip Angle'))
        self.tipanglelabel.setToolTip(
            _(
                "The tip angle for V-Shape Tool.\n"
                "In degree."
            )
        )
        self.tipangle_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.tipangle_entry.set_precision(self.decimals)
        self.tipangle_entry.set_range(1.0, 180.0)
        self.tipangle_entry.setSingleStep(1)

        self.grid3.addWidget(self.tipanglelabel, 2, 0)
        self.grid3.addWidget(self.tipangle_entry, 2, 1)

        # Cut Z
        self.cutzlabel = FCLabel('%s:' % _('Cut Z'))
        self.cutzlabel.setToolTip(
            _(
                "Cutting depth (negative)\n"
                "below the copper surface."
            )
        )
        self.cutz_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.cutz_entry.set_precision(self.decimals)

        if machinist_setting == 0:
            self.cutz_entry.set_range(-10000.0000, 0.0000)
        else:
            self.cutz_entry.set_range(-10000.0000, 10000.0000)

        self.cutz_entry.setSingleStep(0.1)

        self.grid3.addWidget(self.cutzlabel, 3, 0)
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

        self.maxdepth_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.maxdepth_entry.set_precision(self.decimals)
        self.maxdepth_entry.set_range(0, 10000.0000)
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
        self.travelzlabel = FCLabel('%s:' % _('Travel Z'))
        self.travelzlabel.setToolTip(
            _("Height of the tool when\n"
              "moving without cutting.")
        )
        self.travelz_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.travelz_entry.set_precision(self.decimals)

        if machinist_setting == 0:
            self.travelz_entry.set_range(0.00001, 10000.0000)
        else:
            self.travelz_entry.set_range(-10000.0000, 10000.0000)

        self.travelz_entry.setSingleStep(0.1)

        self.grid3.addWidget(self.travelzlabel, 5, 0)
        self.grid3.addWidget(self.travelz_entry, 5, 1)

        # Feedrate X-Y
        self.frlabel = FCLabel('%s:' % _('Feedrate X-Y'))
        self.frlabel.setToolTip(
            _("Cutting speed in the XY\n"
              "plane in units per minute")
        )
        self.cncfeedrate_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.cncfeedrate_entry.set_precision(self.decimals)
        self.cncfeedrate_entry.set_range(0, 910000.0000)
        self.cncfeedrate_entry.setSingleStep(0.1)

        self.grid3.addWidget(self.frlabel, 10, 0)
        self.grid3.addWidget(self.cncfeedrate_entry, 10, 1)

        # Feedrate Z (Plunge)
        self.frzlabel = FCLabel('%s:' % _('Feedrate Z'))
        self.frzlabel.setToolTip(
            _("Cutting speed in the XY\n"
              "plane in units per minute.\n"
              "It is called also Plunge.")
        )
        self.feedrate_z_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.feedrate_z_entry.set_precision(self.decimals)
        self.feedrate_z_entry.set_range(0, 910000.0000)
        self.feedrate_z_entry.setSingleStep(0.1)

        self.grid3.addWidget(self.frzlabel, 11, 0)
        self.grid3.addWidget(self.feedrate_z_entry, 11, 1)

        # Feedrate rapids
        self.fr_rapidlabel = FCLabel('%s:' % _('Feedrate Rapids'))
        self.fr_rapidlabel.setToolTip(
            _("Cutting speed in the XY plane\n"
              "(in units per minute).\n"
              "This is for the rapid move G00.\n"
              "It is useful only for Marlin,\n"
              "ignore for any other cases.")
        )
        self.feedrate_rapid_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.feedrate_rapid_entry.set_precision(self.decimals)
        self.feedrate_rapid_entry.set_range(0, 910000.0000)
        self.feedrate_rapid_entry.setSingleStep(0.1)

        self.grid3.addWidget(self.fr_rapidlabel, 12, 0)
        self.grid3.addWidget(self.feedrate_rapid_entry, 12, 1)
        # default values is to hide
        self.fr_rapidlabel.hide()
        self.feedrate_rapid_entry.hide()

        # Cut over 1st point in path
        self.extracut_cb = FCCheckBox('%s:' % _('Re-cut'))
        self.extracut_cb.setToolTip(
            _("In order to remove possible\n"
              "copper leftovers where first cut\n"
              "meet with last cut, we generate an\n"
              "extended cut over the first cut section.")
        )

        self.e_cut_entry = FCDoubleSpinner(callback=self.confirmation_message)
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
        self.spindle_label = FCLabel('%s:' % _('Spindle speed'))
        self.spindle_label.setToolTip(
            _(
                "Speed of the spindle in RPM (optional).\n"
                "If LASER preprocessor is used,\n"
                "this value is the power of laser."
            )
        )
        self.cncspindlespeed_entry = FCSpinner(callback=self.confirmation_message_int)
        self.cncspindlespeed_entry.set_range(0, 1000000)
        self.cncspindlespeed_entry.set_step(100)

        self.grid3.addWidget(self.spindle_label, 14, 0)
        self.grid3.addWidget(self.cncspindlespeed_entry, 14, 1)

        # Dwell
        self.dwell_cb = FCCheckBox('%s:' % _('Dwell'))
        self.dwell_cb.setToolTip(
            _(
                "Pause to allow the spindle to reach its\n"
                "speed before cutting."
            )
        )
        self.dwelltime_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.dwelltime_entry.set_precision(self.decimals)
        self.dwelltime_entry.set_range(0, 10000.0000)
        self.dwelltime_entry.setSingleStep(0.1)

        self.dwelltime_entry.setToolTip(
            _("Number of time units for spindle to dwell.")
        )
        self.ois_dwell_geo = OptionalInputSection(self.dwell_cb, [self.dwelltime_entry])

        self.grid3.addWidget(self.dwell_cb, 15, 0)
        self.grid3.addWidget(self.dwelltime_entry, 15, 1)

        # Probe depth
        self.pdepth_label = FCLabel('%s:' % _("Probe Z depth"))
        self.pdepth_label.setToolTip(
            _("The maximum depth that the probe is allowed\n"
              "to probe. Negative value, in current units.")
        )
        self.pdepth_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.pdepth_entry.set_precision(self.decimals)
        self.pdepth_entry.set_range(-10000.0000, 10000.0000)
        self.pdepth_entry.setSingleStep(0.1)

        self.grid3.addWidget(self.pdepth_label, 17, 0)
        self.grid3.addWidget(self.pdepth_entry, 17, 1)

        self.pdepth_label.hide()
        self.pdepth_entry.setVisible(False)

        # Probe feedrate
        self.feedrate_probe_label = FCLabel('%s:' % _("Feedrate Probe"))
        self.feedrate_probe_label.setToolTip(
            _("The feedrate used while the probe is probing.")
        )
        self.feedrate_probe_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.feedrate_probe_entry.set_precision(self.decimals)
        self.feedrate_probe_entry.set_range(0.0, 10000.0000)
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
        self.apply_param_to_all.setIcon(QtGui.QIcon(self.app.resource_location + '/param_all32.png'))
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
        self.gen_param_label = FCLabel('<b>%s</b>' % _("Common Parameters"))
        self.gen_param_label.setToolTip(
            _("Parameters that are common for all tools.")
        )
        self.grid4.addWidget(self.gen_param_label, 3, 0, 1, 2)

        # Tool change Z
        self.toolchangeg_cb = FCCheckBox('%s:' % _("Tool change Z"))
        self.toolchangeg_cb.setToolTip(
            _(
                "Include tool-change sequence\n"
                "in the Machine Code (Pause for tool change)."
            )
        )
        self.toolchangez_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.toolchangez_entry.set_precision(self.decimals)
        self.toolchangez_entry.setToolTip(
            _(
                "Z-axis position (height) for\n"
                "tool change."
            )
        )

        if machinist_setting == 0:
            self.toolchangez_entry.set_range(0, 10000.0000)
        else:
            self.toolchangez_entry.set_range(-10000.0000, 10000.0000)

        self.toolchangez_entry.setSingleStep(0.1)
        self.ois_tcz_geo = OptionalInputSection(self.toolchangeg_cb, [self.toolchangez_entry])

        self.grid4.addWidget(self.toolchangeg_cb, 6, 0)
        self.grid4.addWidget(self.toolchangez_entry, 6, 1)

        # The Z value for the start move
        # startzlabel = FCLabel('Start move Z:')
        # startzlabel.setToolTip(
        #     "Tool height just before starting the work.\n"
        #     "Delete the value if you don't need this feature."
        #
        # )
        # grid3.addWidget(startzlabel, 8, 0)
        # self.gstartz_entry = FloatEntry()
        # grid3.addWidget(self.gstartz_entry, 8, 1)

        # The Z value for the end move
        self.endz_label = FCLabel('%s:' % _('End move Z'))
        self.endz_label.setToolTip(
            _("Height of the tool after\n"
              "the last move at the end of the job.")
        )
        self.endz_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.endz_entry.set_precision(self.decimals)

        if machinist_setting == 0:
            self.endz_entry.set_range(0, 10000.0000)
        else:
            self.endz_entry.set_range(-10000.0000, 10000.0000)

        self.endz_entry.setSingleStep(0.1)

        self.grid4.addWidget(self.endz_label, 9, 0)
        self.grid4.addWidget(self.endz_entry, 9, 1)

        # End Move X,Y
        endmove_xy_label = FCLabel('%s:' % _('End move X,Y'))
        endmove_xy_label.setToolTip(
            _("End move X,Y position. In format (x,y).\n"
              "If no value is entered then there is no move\n"
              "on X,Y plane at the end of the job.")
        )
        self.endxy_entry = NumericalEvalTupleEntry(border_color='#0069A9')
        self.endxy_entry.setPlaceholderText(_("X,Y coordinates"))

        self.grid4.addWidget(endmove_xy_label, 10, 0)
        self.grid4.addWidget(self.endxy_entry, 10, 1)

        # preprocessor selection
        pp_label = FCLabel('%s:' % _("Preprocessor"))
        pp_label.setToolTip(
            _("The Preprocessor file that dictates\n"
              "the Machine Code (like GCode, RML, HPGL) output.")
        )
        self.pp_geometry_name_cb = FCComboBox()
        self.pp_geometry_name_cb.setFocusPolicy(QtCore.Qt.StrongFocus)

        self.grid4.addWidget(pp_label, 11, 0)
        self.grid4.addWidget(self.pp_geometry_name_cb, 11, 1)

        # self.grid4.addWidget(FCLabel(''), 12, 0, 1, 2)

        # ------------------------------------------------------------------------------------------------------------
        # ------------------------- EXCLUSION AREAS ------------------------------------------------------------------
        # ------------------------------------------------------------------------------------------------------------

        # Exclusion Areas
        self.exclusion_cb = FCCheckBox('%s' % _("Add exclusion areas"))
        self.exclusion_cb.setToolTip(
            _(
                "Include exclusion areas.\n"
                "In those areas the travel of the tools\n"
                "is forbidden."
            )
        )
        self.grid4.addWidget(self.exclusion_cb, 12, 0, 1, 2)

        self.exclusion_frame = QtWidgets.QFrame()
        self.exclusion_frame.setContentsMargins(0, 0, 0, 0)
        self.grid4.addWidget(self.exclusion_frame, 14, 0, 1, 2)

        self.exclusion_box = QtWidgets.QVBoxLayout()
        self.exclusion_box.setContentsMargins(0, 0, 0, 0)
        self.exclusion_frame.setLayout(self.exclusion_box)

        self.exclusion_table = FCTable()
        self.exclusion_box.addWidget(self.exclusion_table)
        self.exclusion_table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)

        self.exclusion_table.setColumnCount(4)
        self.exclusion_table.setColumnWidth(0, 20)
        self.exclusion_table.setHorizontalHeaderLabels(['#', _('Object'), _('Strategy'), _('Over Z')])

        self.exclusion_table.horizontalHeaderItem(0).setToolTip(_("This is the Area ID."))
        self.exclusion_table.horizontalHeaderItem(1).setToolTip(
            _("Type of the object where the exclusion area was added."))
        self.exclusion_table.horizontalHeaderItem(2).setToolTip(
            _("The strategy used for exclusion area. Go around the exclusion areas or over it."))
        self.exclusion_table.horizontalHeaderItem(3).setToolTip(
            _("If the strategy is to go over the area then this is the height at which the tool will go to avoid the "
              "exclusion area."))

        self.exclusion_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

        grid_a1 = QtWidgets.QGridLayout()
        grid_a1.setColumnStretch(0, 0)
        grid_a1.setColumnStretch(1, 1)
        self.exclusion_box.addLayout(grid_a1)

        # Chose Strategy
        self.strategy_label = FCLabel('%s:' % _("Strategy"))
        self.strategy_label.setToolTip(_("The strategy followed when encountering an exclusion area.\n"
                                         "Can be:\n"
                                         "- Over -> when encountering the area, the tool will go to a set height\n"
                                         "- Around -> will avoid the exclusion area by going around the area"))
        self.strategy_radio = RadioSet([{'label': _('Over'), 'value': 'over'},
                                        {'label': _('Around'), 'value': 'around'}])

        grid_a1.addWidget(self.strategy_label, 1, 0)
        grid_a1.addWidget(self.strategy_radio, 1, 1)

        # Over Z
        self.over_z_label = FCLabel('%s:' % _("Over Z"))
        self.over_z_label.setToolTip(_("The height Z to which the tool will rise in order to avoid\n"
                                       "an interdiction area."))
        self.over_z_entry = FCDoubleSpinner()
        self.over_z_entry.set_range(0.000, 10000.0000)
        self.over_z_entry.set_precision(self.decimals)

        grid_a1.addWidget(self.over_z_label, 2, 0)
        grid_a1.addWidget(self.over_z_entry, 2, 1)

        # Button Add Area
        self.add_area_button = FCButton(_('Add Area:'))
        self.add_area_button.setToolTip(_("Add an Exclusion Area."))

        # Area Selection shape
        self.area_shape_radio = RadioSet([{'label': _("Square"), 'value': 'square'},
                                          {'label': _("Polygon"), 'value': 'polygon'}])
        self.area_shape_radio.setToolTip(
            _("The kind of selection shape used for area selection.")
        )

        grid_a1.addWidget(self.add_area_button, 4, 0)
        grid_a1.addWidget(self.area_shape_radio, 4, 1)

        h_lay_1 = QtWidgets.QHBoxLayout()
        self.exclusion_box.addLayout(h_lay_1)

        # Button Delete All Areas
        self.delete_area_button = FCButton(_('Delete All'))
        self.delete_area_button.setToolTip(_("Delete all exclusion areas."))

        # Button Delete Selected Areas
        self.delete_sel_area_button = FCButton(_('Delete Selected'))
        self.delete_sel_area_button.setToolTip(_("Delete all exclusion areas that are selected in the table."))

        h_lay_1.addWidget(self.delete_area_button)
        h_lay_1.addWidget(self.delete_sel_area_button)

        self.ois_exclusion_geo = OptionalHideInputSection(self.exclusion_cb, [self.exclusion_frame])
        # -------------------------- EXCLUSION AREAS END -------------------------------------------------------------
        # ------------------------------------------------------------------------------------------------------------

        # Add Polish
        self.polish_cb = FCCheckBox(label=_('Add Polish'))
        self.polish_cb.setToolTip(_(
            "Will add a Paint section at the end of the GCode.\n"
            "A metallic brush will clean the material after milling."))
        self.polish_cb.setObjectName("g_polish")
        self.grid4.addWidget(self.polish_cb, 15, 0, 1, 2)

        # Polish Tool Diameter
        self.polish_dia_lbl = FCLabel('%s:' % _('Tool Dia'))
        self.polish_dia_lbl.setToolTip(
            _("Diameter for the polishing tool.")
        )
        self.polish_dia_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.polish_dia_entry.set_precision(self.decimals)
        self.polish_dia_entry.set_range(0.000, 10000.0000)
        self.polish_dia_entry.setObjectName("g_polish_dia")

        self.grid4.addWidget(self.polish_dia_lbl, 16, 0)
        self.grid4.addWidget(self.polish_dia_entry, 16, 1)

        # Polish Travel Z
        self.polish_travelz_lbl = FCLabel('%s:' % _('Travel Z'))
        self.polish_travelz_lbl.setToolTip(
            _("Height of the tool when\n"
              "moving without cutting.")
        )
        self.polish_travelz_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.polish_travelz_entry.set_precision(self.decimals)
        self.polish_travelz_entry.set_range(0.00000, 10000.00000)
        self.polish_travelz_entry.setSingleStep(0.1)
        self.polish_travelz_entry.setObjectName("g_polish_travelz")

        self.grid4.addWidget(self.polish_travelz_lbl, 17, 0)
        self.grid4.addWidget(self.polish_travelz_entry, 17, 1)

        # Polish Pressure
        self.polish_pressure_lbl = FCLabel('%s:' % _('Pressure'))
        self.polish_pressure_lbl.setToolTip(
            _("Negative value. The higher the absolute value\n"
              "the stronger the pressure of the brush on the material.")
        )
        self.polish_pressure_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.polish_pressure_entry.set_precision(self.decimals)
        self.polish_pressure_entry.set_range(-10000.0000, 10000.0000)
        self.polish_pressure_entry.setObjectName("g_polish_pressure")

        self.grid4.addWidget(self.polish_pressure_lbl, 18, 0)
        self.grid4.addWidget(self.polish_pressure_entry, 18, 1)

        # Polish Margin
        self.polish_margin_lbl = FCLabel('%s:' % _('Margin'))
        self.polish_margin_lbl.setToolTip(
            _("Bounding box margin.")
        )
        self.polish_margin_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.polish_margin_entry.set_precision(self.decimals)
        self.polish_margin_entry.set_range(-10000.0000, 10000.0000)
        self.polish_margin_entry.setObjectName("g_polish_margin")

        self.grid4.addWidget(self.polish_margin_lbl, 20, 0)
        self.grid4.addWidget(self.polish_margin_entry, 20, 1)

        # Polish Overlap
        self.polish_over_lbl = FCLabel('%s:' % _('Overlap'))
        self.polish_over_lbl.setToolTip(
            _("How much (percentage) of the tool width to overlap each tool pass.")
        )
        self.polish_over_entry = FCDoubleSpinner(suffix='%', callback=self.confirmation_message)
        self.polish_over_entry.set_precision(self.decimals)
        self.polish_over_entry.setWrapping(True)
        self.polish_over_entry.set_range(0.0000, 99.9999)
        self.polish_over_entry.setSingleStep(0.1)
        self.polish_over_entry.setObjectName("g_polish_overlap")

        self.grid4.addWidget(self.polish_over_lbl, 22, 0)
        self.grid4.addWidget(self.polish_over_entry, 22, 1)

        # Polish Method
        self.polish_method_lbl = FCLabel('%s:' % _('Method'))
        self.polish_method_lbl.setToolTip(
            _("Algorithm for polishing:\n"
              "- Standard: Fixed step inwards.\n"
              "- Seed-based: Outwards from seed.\n"
              "- Line-based: Parallel lines.")
        )

        self.polish_method_combo = FCComboBox2()
        self.polish_method_combo.addItems(
            [_("Standard"), _("Seed"), _("Lines")]
        )
        self.polish_method_combo.setObjectName('g_polish_method')

        self.grid4.addWidget(self.polish_method_lbl, 24, 0)
        self.grid4.addWidget(self.polish_method_combo, 24, 1)

        self.polish_dia_lbl.hide()
        self.polish_dia_entry.hide()
        self.polish_pressure_lbl.hide()
        self.polish_pressure_entry.hide()
        self.polish_travelz_lbl.hide()
        self.polish_travelz_entry.hide()
        self.polish_margin_lbl.hide()
        self.polish_margin_entry.hide()
        self.polish_over_lbl.hide()
        self.polish_over_entry.hide()
        self.polish_method_lbl.hide()
        self.polish_method_combo.hide()

        self.ois_polish = OptionalHideInputSection(
            self.polish_cb,
            [
                self.polish_dia_lbl,
                self.polish_dia_entry,
                self.polish_pressure_lbl,
                self.polish_pressure_entry,
                self.polish_travelz_lbl,
                self.polish_travelz_entry,
                self.polish_margin_lbl,
                self.polish_margin_entry,
                self.polish_over_lbl,
                self.polish_over_entry,
                self.polish_method_lbl,
                self.polish_method_combo
            ]
        )

        separator_line2 = QtWidgets.QFrame()
        separator_line2.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line2.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.grid4.addWidget(separator_line2, 26, 0, 1, 2)

        # Button
        self.generate_cnc_button = FCButton(_('Generate CNCJob object'))
        self.generate_cnc_button.setIcon(QtGui.QIcon(self.app.resource_location + '/cnc16.png'))
        self.generate_cnc_button.setToolTip('%s.\n%s' % (
            _("Generate CNCJob object"),
            _(
                "Add / Select at least one tool in the tool-table.\n"
                "Click the # header to select all, or Ctrl + LMB\n"
                "for custom selection of tools.")))

        self.generate_cnc_button.setStyleSheet("""
                        QPushButton
                        {
                            font-weight: bold;
                        }
                        """)
        self.grid4.addWidget(self.generate_cnc_button, 28, 0, 1, 2)

        self.grid4.addWidget(FCLabel(''), 30, 0, 1, 2)

        # ##############
        # Paint area ##
        # ##############
        self.tools_label = FCLabel('<b>%s</b>' % _('TOOLS'))
        self.tools_label.setToolTip(
            _("Launch Paint Tool in Tools Tab.")
        )
        self.grid4.addWidget(self.tools_label, 32, 0, 1, 2)

        # Milling Tool - will create GCode for slot holes
        self.milling_button = FCButton(_('Milling Tool'))
        self.milling_button.setIcon(QtGui.QIcon(self.app.resource_location + '/milling_tool32.png'))
        self.milling_button.setToolTip(
            _("Generate a CNCJob by milling a Geometry.")
        )
        self.milling_button.setStyleSheet("""
                        QPushButton
                        {
                            font-weight: bold;
                        }
                        """)
        self.grid4.addWidget(self.milling_button, 34, 0, 1, 2)
        # FIXME: until the Milling Tool is ready, this get disabled
        self.milling_button.setDisabled(True)

        # Paint Button
        self.paint_tool_button = FCButton(_('Paint Tool'))
        self.paint_tool_button.setIcon(QtGui.QIcon(self.app.resource_location + '/paint20_1.png'))
        self.paint_tool_button.setToolTip(
            _("Creates tool paths to cover the\n"
              "whole area of a polygon.")
        )

        # self.paint_tool_button.setStyleSheet("""
        #                 QPushButton
        #                 {
        #                     font-weight: bold;
        #                 }
        #                 """)
        self.grid4.addWidget(self.paint_tool_button, 36, 0, 1, 2)

        # NCC Tool
        self.generate_ncc_button = FCButton(_('NCC Tool'))
        self.generate_ncc_button.setIcon(QtGui.QIcon(self.app.resource_location + '/eraser26.png'))
        self.generate_ncc_button.setToolTip(
            _("Create the Geometry Object\n"
              "for non-copper routing.")
        )
        # self.generate_ncc_button.setStyleSheet("""
        #                 QPushButton
        #                 {
        #                     font-weight: bold;
        #                 }
        #                 """)
        self.grid4.addWidget(self.generate_ncc_button, 38, 0, 1, 2)


class CNCObjectUI(ObjectUI):
    """
    User interface for CNCJob objects.
    """

    def __init__(self, app, parent=None):
        """
        Creates the user interface for CNCJob objects. GUI elements should
        be placed in ``self.custom_box`` to preserve the layout.
        """

        self.decimals = app.decimals
        self.app = app

        theme_settings = QtCore.QSettings("Open Source", "FlatCAM")
        if theme_settings.contains("theme"):
            theme = theme_settings.value('theme', type=str)
        else:
            theme = 'white'

        if theme == 'white':
            self.resource_loc = 'assets/resources'
        else:
            self.resource_loc = 'assets/resources'

        ObjectUI.__init__(
            self, title=_('CNC Job Object'),
            icon_file=self.resource_loc + '/cnc32.png', parent=parent,
            app=self.app)

        for i in range(0, self.common_grid.count()):
            self.common_grid.itemAt(i).widget().hide()

        f_lay = QtWidgets.QGridLayout()
        f_lay.setColumnStretch(0, 0)
        f_lay.setColumnStretch(1, 1)
        self.custom_box.addLayout(f_lay)

        # Plot Options
        self.cncplot_method_label = FCLabel("<b>%s:</b>" % _("Plot Options"))
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

        f_lay.addWidget(self.cncplot_method_label, 0, 0)
        f_lay.addWidget(self.cncplot_method_combo, 0, 1, 1, 2)

        self.name_hlay = QtWidgets.QHBoxLayout()
        f_lay.addLayout(self.name_hlay, 2, 0, 1, 3)

        # ## Object name
        name_label = FCLabel("<b>%s:</b>" % _("Name"))
        self.name_entry = FCEntry()
        self.name_entry.setFocusPolicy(QtCore.Qt.StrongFocus)

        self.name_hlay.addWidget(name_label)
        self.name_hlay.addWidget(self.name_entry)

        # Editor
        self.editor_button = FCButton(_('GCode Editor'))
        self.editor_button.setIcon(QtGui.QIcon(self.app.resource_location + '/edit_file32.png'))

        self.editor_button.setToolTip(
            _("Start the Object Editor")
        )
        self.editor_button.setStyleSheet("""
                                       QPushButton
                                       {
                                           font-weight: bold;
                                       }
                                       """)
        f_lay.addWidget(self.editor_button, 4, 0, 1, 3)

        # PROPERTIES CB
        self.properties_button = FCButton('%s' % _("PROPERTIES"), checkable=True)
        self.properties_button.setIcon(QtGui.QIcon(self.app.resource_location + '/properties32.png'))
        self.properties_button.setToolTip(_("Show the Properties."))
        self.properties_button.setStyleSheet("""
                                      QPushButton
                                      {
                                          font-weight: bold;
                                      }
                                      """)
        f_lay.addWidget(self.properties_button, 6, 0, 1, 3)

        # PROPERTIES Frame
        self.properties_frame = QtWidgets.QFrame()
        self.properties_frame.setContentsMargins(0, 0, 0, 0)
        f_lay.addWidget(self.properties_frame, 7, 0, 1, 3)
        self.properties_box = QtWidgets.QVBoxLayout()
        self.properties_box.setContentsMargins(0, 0, 0, 0)
        self.properties_frame.setLayout(self.properties_box)
        self.properties_frame.hide()

        self.treeWidget = FCTree(columns=2)

        self.properties_box.addWidget(self.treeWidget)
        self.properties_box.setStretch(0, 0)

        # Annotation
        self.annotation_cb = FCCheckBox(_("Display Annotation"))
        self.annotation_cb.setToolTip(
            _("This selects if to display text annotation on the plot.\n"
              "When checked it will display numbers in order for each end\n"
              "of a travel line.")
        )
        f_lay.addWidget(self.annotation_cb, 8, 0, 1, 3)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        f_lay.addWidget(separator_line, 10, 0, 1, 3)

        # Travelled Distance
        self.t_distance_label = FCLabel("<b>%s:</b>" % _("Travelled distance"))
        self.t_distance_label.setToolTip(
            _("This is the total travelled distance on X-Y plane.\n"
              "In current units.")
        )
        self.t_distance_entry = FCEntry()
        self.units_label = FCLabel()

        f_lay.addWidget(self.t_distance_label, 12, 0)
        f_lay.addWidget(self.t_distance_entry, 12, 1)
        f_lay.addWidget(self.units_label, 12, 2)

        # Estimated Time
        self.t_time_label = FCLabel("<b>%s:</b>" % _("Estimated time"))
        self.t_time_label.setToolTip(
            _("This is the estimated time to do the routing/drilling,\n"
              "without the time spent in ToolChange events.")
        )
        self.t_time_entry = FCEntry()
        self.units_time_label = FCLabel()

        f_lay.addWidget(self.t_time_label, 14, 0)
        f_lay.addWidget(self.t_time_entry, 14, 1)
        f_lay.addWidget(self.units_time_label, 14, 2)

        self.t_distance_label.hide()
        self.t_distance_entry.setVisible(False)
        self.t_time_label.hide()
        self.t_time_entry.setVisible(False)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        f_lay.addWidget(separator_line, 16, 0, 1, 3)

        hlay = QtWidgets.QHBoxLayout()
        self.custom_box.addLayout(hlay)

        # CNC Tools Table for plot
        self.cnc_tools_table_label = FCLabel('<b>%s</b>' % _('CNC Tools Table'))
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

        self.tooldia_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.tooldia_entry.set_range(0, 10000.0000)
        self.tooldia_entry.set_precision(self.decimals)
        self.tooldia_entry.setSingleStep(0.1)
        self.custom_box.addWidget(self.tooldia_entry)

        # Update plot button
        self.updateplot_button = FCButton(_('Update Plot'))
        self.updateplot_button.setToolTip(
            _("Update the plot.")
        )
        self.custom_box.addWidget(self.updateplot_button)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.custom_box.addWidget(separator_line)

        # CNC Code snippets
        self.snippets_cb = FCCheckBox(_("Use CNC Code Snippets"))
        self.snippets_cb.setToolTip(
            _("When selected, it will include CNC Code snippets (append and prepend)\n"
              "defined in the Preferences.")
        )
        self.custom_box.addWidget(self.snippets_cb)

        # Autolevelling
        self.sal_btn = FCButton('%s' % _("Autolevelling"), checkable=True)
        # self.sal_btn.setIcon(QtGui.QIcon(self.app.resource_location + '/properties32.png'))
        self.sal_btn.setToolTip(
            _("Enable the autolevelling feature.")
        )
        self.sal_btn.setStyleSheet("""
                                  QPushButton
                                  {
                                      font-weight: bold;
                                  }
                                  """)
        self.custom_box.addWidget(self.sal_btn)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.custom_box.addWidget(separator_line)

        self.al_frame = QtWidgets.QFrame()
        self.al_frame.setContentsMargins(0, 0, 0, 0)
        self.custom_box.addWidget(self.al_frame)

        self.al_box = QtWidgets.QVBoxLayout()
        self.al_box.setContentsMargins(0, 0, 0, 0)
        self.al_frame.setLayout(self.al_box)

        grid0 = QtWidgets.QGridLayout()
        grid0.setColumnStretch(0, 0)
        grid0.setColumnStretch(1, 1)
        self.al_box.addLayout(grid0)

        al_title = FCLabel('<b>%s</b>' % _("Probe Points Table"))
        al_title.setToolTip(_("Generate GCode that will obtain the height map"))

        self.show_al_table = FCCheckBox(_("Show"))
        self.show_al_table.setToolTip(_("Toggle the display of the Probe Points table."))
        self.show_al_table.setChecked(True)

        hor_lay = QtWidgets.QHBoxLayout()
        hor_lay.addWidget(al_title)
        hor_lay.addStretch()
        hor_lay.addWidget(self.show_al_table, alignment=QtCore.Qt.AlignRight)

        grid0.addLayout(hor_lay, 0, 0, 1, 2)

        self.al_probe_points_table = FCTable()
        self.al_probe_points_table.setColumnCount(3)
        self.al_probe_points_table.setColumnWidth(0, 20)
        self.al_probe_points_table.setHorizontalHeaderLabels(['#', _('X-Y Coordinates'), _('Height')])

        grid0.addWidget(self.al_probe_points_table, 1, 0, 1, 2)

        self.plot_probing_pts_cb = FCCheckBox(_("Plot probing points"))
        self.plot_probing_pts_cb.setToolTip(
            _("Plot the probing points in the table.\n"
              "If a Voronoi method is used then\n"
              "the Voronoi areas are also plotted.")
        )
        grid0.addWidget(self.plot_probing_pts_cb, 3, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 5, 0, 1, 2)

        # #############################################################################################################
        # ############### Probe GCode Generation ######################################################################
        # #############################################################################################################

        self.probe_gc_label = FCLabel('<b>%s</b>:' % _("Probe GCode Generation"))
        self.probe_gc_label.setToolTip(
            _("Will create a GCode which will be sent to the controller,\n"
              "either through a file or directly, with the intent to get the height map\n"
              "that is to modify the original GCode to level the cutting height.")
        )
        grid0.addWidget(self.probe_gc_label, 7, 0, 1, 2)

        # Travel Z Probe
        self.ptravelz_label = FCLabel('%s:' % _("Probe Z travel"))
        self.ptravelz_label.setToolTip(
            _("The safe Z for probe travelling between probe points.")
        )
        self.ptravelz_entry = FCDoubleSpinner()
        self.ptravelz_entry.set_precision(self.decimals)
        self.ptravelz_entry.set_range(0.0000, 10000.0000)

        grid0.addWidget(self.ptravelz_label, 9, 0)
        grid0.addWidget(self.ptravelz_entry, 9, 1)

        # Probe depth
        self.pdepth_label = FCLabel('%s:' % _("Probe Z depth"))
        self.pdepth_label.setToolTip(
            _("The maximum depth that the probe is allowed\n"
              "to probe. Negative value, in current units.")
        )
        self.pdepth_entry = FCDoubleSpinner()
        self.pdepth_entry.set_precision(self.decimals)
        self.pdepth_entry.set_range(-910000.0000, 0.0000)

        grid0.addWidget(self.pdepth_label, 11, 0)
        grid0.addWidget(self.pdepth_entry, 11, 1)

        # Probe feedrate
        self.feedrate_probe_label = FCLabel('%s:' % _("Probe Feedrate"))
        self.feedrate_probe_label.setToolTip(
           _("The feedrate used while the probe is probing.")
        )
        self.feedrate_probe_entry = FCDoubleSpinner()
        self.feedrate_probe_entry.set_precision(self.decimals)
        self.feedrate_probe_entry.set_range(0, 910000.0000)

        grid0.addWidget(self.feedrate_probe_label, 13, 0)
        grid0.addWidget(self.feedrate_probe_entry, 13, 1)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 15, 0, 1, 2)

        # AUTOLEVELL MODE
        al_mode_lbl = FCLabel('<b>%s</b>:' % _("Mode"))
        al_mode_lbl.setToolTip(_("Choose a mode for height map generation.\n"
                                 "- Manual: will pick a selection of probe points by clicking on canvas\n"
                                 "- Grid: will automatically generate a grid of probe points"))

        self.al_mode_radio = RadioSet(
            [
                {'label': _('Manual'), 'value': 'manual'},
                {'label': _('Grid'), 'value': 'grid'}
            ])
        grid0.addWidget(al_mode_lbl, 16, 0)
        grid0.addWidget(self.al_mode_radio, 16, 1)

        # AUTOLEVELL METHOD
        self.al_method_lbl = FCLabel('%s:' % _("Method"))
        self.al_method_lbl.setToolTip(_("Choose a method for approximation of heights from autolevelling data.\n"
                                        "- Voronoi: will generate a Voronoi diagram\n"
                                        "- Bilinear: will use bilinear interpolation. Usable only for grid mode."))

        self.al_method_radio = RadioSet(
            [
                {'label': _('Voronoi'), 'value': 'v'},
                {'label': _('Bilinear'), 'value': 'b'}
            ])
        self.al_method_lbl.setDisabled(True)
        self.al_method_radio.setDisabled(True)
        self.al_method_radio.set_value('v')

        grid0.addWidget(self.al_method_lbl, 17, 0)
        grid0.addWidget(self.al_method_radio, 17, 1)

        # ## Columns
        self.al_columns_entry = FCSpinner()
        self.al_columns_entry.setMinimum(2)

        self.al_columns_label = FCLabel('%s:' % _("Columns"))
        self.al_columns_label.setToolTip(
            _("The number of grid columns.")
        )
        grid0.addWidget(self.al_columns_label, 19, 0)
        grid0.addWidget(self.al_columns_entry, 19, 1)

        # ## Rows
        self.al_rows_entry = FCSpinner()
        self.al_rows_entry.setMinimum(2)

        self.al_rows_label = FCLabel('%s:' % _("Rows"))
        self.al_rows_label.setToolTip(
            _("The number of grid rows.")
        )
        grid0.addWidget(self.al_rows_label, 21, 0)
        grid0.addWidget(self.al_rows_entry, 21, 1)

        self.al_add_button = FCButton(_("Add Probe Points"))
        grid0.addWidget(self.al_add_button, 23, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 25, 0, 1, 2)

        self.al_controller_label = FCLabel('<b>%s</b>:' % _("Controller"))
        self.al_controller_label.setToolTip(
            _("The kind of controller for which to generate\n"
              "height map gcode.")
        )

        self.al_controller_combo = FCComboBox()
        self.al_controller_combo.addItems(["MACH3", "MACH4", "LinuxCNC", "GRBL"])
        grid0.addWidget(self.al_controller_label, 27, 0)
        grid0.addWidget(self.al_controller_combo, 27, 1)

        # #############################################################################################################
        # ########################## GRBL frame #######################################################################
        # #############################################################################################################
        self.grbl_frame = QtWidgets.QFrame()
        self.grbl_frame.setContentsMargins(0, 0, 0, 0)
        grid0.addWidget(self.grbl_frame, 29, 0, 1, 2)

        self.grbl_box = QtWidgets.QVBoxLayout()
        self.grbl_box.setContentsMargins(0, 0, 0, 0)
        self.grbl_frame.setLayout(self.grbl_box)

        # #############################################################################################################
        # ########################## GRBL TOOLBAR #####################################################################
        # #############################################################################################################
        self.al_toolbar = FCDetachableTab(protect=True, parent=self)
        self.al_toolbar.setTabsClosable(False)
        self.al_toolbar.useOldIndex(True)
        self.al_toolbar.set_detachable(val=False)
        self.grbl_box.addWidget(self.al_toolbar)

        # GRBL Connect TAB
        self.gr_conn_tab = QtWidgets.QWidget()
        self.gr_conn_tab.setObjectName("connect_tab")
        self.gr_conn_tab_layout = QtWidgets.QVBoxLayout(self.gr_conn_tab)
        self.gr_conn_tab_layout.setContentsMargins(2, 2, 2, 2)
        # self.gr_conn_scroll_area = VerticalScrollArea()
        # self.gr_conn_tab_layout.addWidget(self.gr_conn_scroll_area)
        self.al_toolbar.addTab(self.gr_conn_tab, _("Connect"))

        # GRBL Control TAB
        self.gr_ctrl_tab = QtWidgets.QWidget()
        self.gr_ctrl_tab.setObjectName("connect_tab")
        self.gr_ctrl_tab_layout = QtWidgets.QVBoxLayout(self.gr_ctrl_tab)
        self.gr_ctrl_tab_layout.setContentsMargins(2, 2, 2, 2)

        # self.gr_ctrl_scroll_area = VerticalScrollArea()
        # self.gr_ctrl_tab_layout.addWidget(self.gr_ctrl_scroll_area)
        self.al_toolbar.addTab(self.gr_ctrl_tab, _("Control"))

        # GRBL Sender TAB
        self.gr_send_tab = QtWidgets.QWidget()
        self.gr_send_tab.setObjectName("connect_tab")
        self.gr_send_tab_layout = QtWidgets.QVBoxLayout(self.gr_send_tab)
        self.gr_send_tab_layout.setContentsMargins(2, 2, 2, 2)

        # self.gr_send_scroll_area = VerticalScrollArea()
        # self.gr_send_tab_layout.addWidget(self.gr_send_scroll_area)
        self.al_toolbar.addTab(self.gr_send_tab, _("Sender"))

        for idx in range(self.al_toolbar.count()):
            if self.al_toolbar.tabText(idx) == _("Connect"):
                self.al_toolbar.tabBar.setTabTextColor(idx, QtGui.QColor('red'))
            if self.al_toolbar.tabText(idx) == _("Control"):
                self.al_toolbar.tabBar.setTabEnabled(idx, False)
            if self.al_toolbar.tabText(idx) == _("Sender"):
                self.al_toolbar.tabBar.setTabEnabled(idx, False)
        # #############################################################################################################

        # #############################################################################################################
        # GRBL CONNECT
        # #############################################################################################################
        grbl_conn_grid = QtWidgets.QGridLayout()
        grbl_conn_grid.setColumnStretch(0, 0)
        grbl_conn_grid.setColumnStretch(1, 1)
        grbl_conn_grid.setColumnStretch(2, 0)
        self.gr_conn_tab_layout.addLayout(grbl_conn_grid)

        # COM list
        self.com_list_label = FCLabel('%s:' % _("COM list"))
        self.com_list_label.setToolTip(
            _("Lists the available serial ports.")
        )

        self.com_list_combo = FCComboBox()
        self.com_search_button = FCButton(_("Search"))
        self.com_search_button.setToolTip(
            _("Search for the available serial ports.")
        )
        grbl_conn_grid.addWidget(self.com_list_label, 2, 0)
        grbl_conn_grid.addWidget(self.com_list_combo, 2, 1)
        grbl_conn_grid.addWidget(self.com_search_button, 2, 2)

        # BAUDRATES list
        self.baudrates_list_label = FCLabel('%s:' % _("Baud rates"))
        self.baudrates_list_label.setToolTip(
            _("Lists the available serial ports.")
        )

        self.baudrates_list_combo = FCComboBox()
        cbmodel = QtCore.QStringListModel()
        self.baudrates_list_combo.setModel(cbmodel)
        self.baudrates_list_combo.addItems(
            ['9600', '19200', '38400', '57600', '115200', '230400', '460800', '500000', '576000', '921600', '1000000',
             '1152000', '1500000', '2000000'])
        self.baudrates_list_combo.setCurrentText('115200')

        grbl_conn_grid.addWidget(self.baudrates_list_label, 4, 0)
        grbl_conn_grid.addWidget(self.baudrates_list_combo, 4, 1)

        # New baudrate
        self.new_bd_label = FCLabel('%s:' % _("New"))
        self.new_bd_label.setToolTip(
            _("New, custom baudrate.")
        )

        self.new_baudrate_entry = FCSpinner()
        self.new_baudrate_entry.set_range(40, 9999999)

        self.add_bd_button = FCButton(_("Add"))
        self.add_bd_button.setToolTip(
            _("Add the specified custom baudrate to the list.")
        )
        grbl_conn_grid.addWidget(self.new_bd_label, 6, 0)
        grbl_conn_grid.addWidget(self.new_baudrate_entry, 6, 1)
        grbl_conn_grid.addWidget(self.add_bd_button, 6, 2)

        self.del_bd_button = FCButton(_("Delete selected baudrate"))
        grbl_conn_grid.addWidget(self.del_bd_button, 8, 0, 1, 3)

        ctrl_hlay = QtWidgets.QHBoxLayout()
        self.controller_reset_button = FCButton(_("Reset"))
        self.controller_reset_button.setToolTip(
            _("Software reset of the controller.")
        )
        self.controller_reset_button.setDisabled(True)
        ctrl_hlay.addWidget(self.controller_reset_button)

        self.com_connect_button = FCButton()
        self.com_connect_button.setText(_("Disconnected"))
        self.com_connect_button.setToolTip(
            _("Connect to the selected port with the selected baud rate.")
        )
        self.com_connect_button.setStyleSheet("QPushButton {background-color: red;}")
        ctrl_hlay.addWidget(self.com_connect_button)

        grbl_conn_grid.addWidget(FCLabel(""), 9, 0, 1, 3)
        grbl_conn_grid.setRowStretch(9, 1)
        grbl_conn_grid.addLayout(ctrl_hlay, 10, 0, 1, 3)

        # #############################################################################################################
        # GRBL CONTROL
        # #############################################################################################################
        grbl_ctrl_grid = QtWidgets.QGridLayout()
        grbl_ctrl_grid.setColumnStretch(0, 0)
        grbl_ctrl_grid.setColumnStretch(1, 1)
        grbl_ctrl_grid.setColumnStretch(2, 0)
        self.gr_ctrl_tab_layout.addLayout(grbl_ctrl_grid)

        grbl_ctrl2_grid = QtWidgets.QGridLayout()
        grbl_ctrl2_grid.setColumnStretch(0, 0)
        grbl_ctrl2_grid.setColumnStretch(1, 1)
        self.gr_ctrl_tab_layout.addLayout(grbl_ctrl2_grid)

        self.gr_ctrl_tab_layout.addStretch(1)

        jog_title_label = FCLabel(_("Jog"))
        jog_title_label.setStyleSheet("""
                                FCLabel
                                {
                                    font-weight: bold;
                                }
                                """)

        zero_title_label = FCLabel(_("Zero Axes"))
        zero_title_label.setStyleSheet("""
                                FCLabel
                                {
                                    font-weight: bold;
                                }
                                """)

        grbl_ctrl_grid.addWidget(jog_title_label, 0, 0)
        grbl_ctrl_grid.addWidget(zero_title_label, 0, 2)

        self.jog_wdg = FCJog(self.app)
        self.jog_wdg.setStyleSheet("""
                            FCJog
                            {
                                border: 1px solid lightgray;
                                border-radius: 5px;
                            }
                            """)

        self.zero_axs_wdg = FCZeroAxes(self.app)
        self.zero_axs_wdg.setStyleSheet("""
                            FCZeroAxes
                            {
                                border: 1px solid lightgray;
                                border-radius: 5px
                            }
                            """)
        grbl_ctrl_grid.addWidget(self.jog_wdg, 2, 0)
        grbl_ctrl_grid.addWidget(self.zero_axs_wdg, 2, 2)

        self.pause_resume_button = RotatedToolButton()
        self.pause_resume_button.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.pause_resume_button.setText(_("Pause/Resume"))
        self.pause_resume_button.setCheckable(True)
        self.pause_resume_button.setStyleSheet("""
                            RotatedToolButton:checked
                            {
                                background-color: red;
                                color: white;
                                border: none;
                            }
                            """)

        pause_frame = QtWidgets.QFrame()
        pause_frame.setContentsMargins(0, 0, 0, 0)
        pause_frame.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Expanding)
        pause_hlay = QtWidgets.QHBoxLayout()
        pause_hlay.setContentsMargins(0, 0, 0, 0)

        pause_hlay.addWidget(self.pause_resume_button)
        pause_frame.setLayout(pause_hlay)
        grbl_ctrl_grid.addWidget(pause_frame, 2, 1)

        # JOG Step
        self.jog_step_label = FCLabel('%s:' % _("Step"))
        self.jog_step_label.setToolTip(
            _("Each jog action will move the axes with this value.")
        )

        self.jog_step_entry = FCSliderWithDoubleSpinner()
        self.jog_step_entry.set_precision(self.decimals)
        self.jog_step_entry.setSingleStep(0.1)
        self.jog_step_entry.set_range(0, 500)

        grbl_ctrl2_grid.addWidget(self.jog_step_label, 0, 0)
        grbl_ctrl2_grid.addWidget(self.jog_step_entry, 0, 1)

        # JOG Feedrate
        self.jog_fr_label = FCLabel('%s:' % _("Feedrate"))
        self.jog_fr_label.setToolTip(
            _("Feedrate when jogging.")
        )

        self.jog_fr_entry = FCSliderWithDoubleSpinner()
        self.jog_fr_entry.set_precision(self.decimals)
        self.jog_fr_entry.setSingleStep(10)
        self.jog_fr_entry.set_range(0, 10000)

        grbl_ctrl2_grid.addWidget(self.jog_fr_label, 1, 0)
        grbl_ctrl2_grid.addWidget(self.jog_fr_entry, 1, 1)

        # #############################################################################################################
        # GRBL SENDER
        # #############################################################################################################
        grbl_send_grid = QtWidgets.QGridLayout()
        grbl_send_grid.setColumnStretch(0, 1)
        grbl_send_grid.setColumnStretch(1, 0)
        self.gr_send_tab_layout.addLayout(grbl_send_grid)

        # Send CUSTOM COMMAND
        self.grbl_command_label = FCLabel('%s:' % _("Send Command"))
        self.grbl_command_label.setToolTip(
            _("Send a custom command to GRBL.")
        )
        grbl_send_grid.addWidget(self.grbl_command_label, 2, 0, 1, 2)

        self.grbl_command_entry = FCEntry()
        self.grbl_command_entry.setPlaceholderText(_("Type GRBL command ..."))

        self.grbl_send_button = QtWidgets.QToolButton()
        self.grbl_send_button.setText(_("Send"))
        self.grbl_send_button.setToolTip(
            _("Send a custom command to GRBL.")
        )
        grbl_send_grid.addWidget(self.grbl_command_entry, 4, 0)
        grbl_send_grid.addWidget(self.grbl_send_button, 4, 1)

        # Get Parameter
        self.grbl_get_param_label = FCLabel('%s:' % _("Get Config parameter"))
        self.grbl_get_param_label.setToolTip(
            _("A GRBL configuration parameter.")
        )
        grbl_send_grid.addWidget(self.grbl_get_param_label, 6, 0, 1, 2)

        self.grbl_parameter_entry = FCEntry()
        self.grbl_parameter_entry.setPlaceholderText(_("Type GRBL parameter ..."))

        self.grbl_get_param_button = QtWidgets.QToolButton()
        self.grbl_get_param_button.setText(_("Get"))
        self.grbl_get_param_button.setToolTip(
            _("Get the value of a specified GRBL parameter.")
        )
        grbl_send_grid.addWidget(self.grbl_parameter_entry, 8, 0)
        grbl_send_grid.addWidget(self.grbl_get_param_button, 8, 1)

        grbl_send_grid.setRowStretch(9, 1)

        # GET Report
        self.grbl_report_button = FCButton(_("Get Report"))
        self.grbl_report_button.setToolTip(
            _("Print in shell the GRBL report.")
        )
        grbl_send_grid.addWidget(self.grbl_report_button, 10, 0, 1, 2)

        hm_lay = QtWidgets.QHBoxLayout()
        # GET HEIGHT MAP
        self.grbl_get_heightmap_button = FCButton(_("Apply AutoLevelling"))
        self.grbl_get_heightmap_button.setToolTip(
            _("Will send the probing GCode to the GRBL controller,\n"
              "wait for the Z probing data and then apply this data\n"
              "over the original GCode therefore doing autolevelling.")
        )
        hm_lay.addWidget(self.grbl_get_heightmap_button, stretch=1)

        self.grbl_save_height_map_button = QtWidgets.QToolButton()
        self.grbl_save_height_map_button.setIcon(QtGui.QIcon(self.app.resource_location + '/save_as.png'))
        self.grbl_save_height_map_button.setToolTip(
            _("Will save the GRBL height map.")
        )
        hm_lay.addWidget(self.grbl_save_height_map_button, stretch=0, alignment=Qt.AlignRight)

        grbl_send_grid.addLayout(hm_lay, 12, 0, 1, 2)

        self.grbl_frame.hide()
        # #############################################################################################################

        height_lay = QtWidgets.QHBoxLayout()
        self.h_gcode_button = FCButton(_("Save Probing GCode"))
        self.h_gcode_button.setToolTip(
            _("Will save the probing GCode.")
        )
        self.h_gcode_button.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.MinimumExpanding)

        height_lay.addWidget(self.h_gcode_button)
        self.view_h_gcode_button = QtWidgets.QToolButton()
        self.view_h_gcode_button.setIcon(QtGui.QIcon(self.app.resource_location + '/edit_file32.png'))
        # self.view_h_gcode_button.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
        self.view_h_gcode_button.setToolTip(
            _("View/Edit the probing GCode.")
        )
        # height_lay.addStretch()
        height_lay.addWidget(self.view_h_gcode_button)

        grid0.addLayout(height_lay, 31, 0, 1, 2)

        self.import_heights_button = FCButton(_("Import Height Map"))
        self.import_heights_button.setToolTip(
            _("Import the file that has the Z heights\n"
              "obtained through probing and then apply this data\n"
              "over the original GCode therefore\n"
              "doing autolevelling.")
        )
        grid0.addWidget(self.import_heights_button, 33, 0, 1, 2)

        self.h_gcode_button.hide()
        self.import_heights_button.hide()

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 35, 0, 1, 2)

        # #############################################################################################################
        # ## Export G-Code ##
        # #############################################################################################################
        self.export_gcode_label = FCLabel("<b>%s:</b>" % _("Export CNC Code"))
        self.export_gcode_label.setToolTip(
            _("Export and save G-Code to\n"
              "make this object to a file.")
        )
        self.custom_box.addWidget(self.export_gcode_label)

        g_export_lay = QtWidgets.QHBoxLayout()
        self.custom_box.addLayout(g_export_lay)

        # Save Button
        self.export_gcode_button = FCButton(_('Save CNC Code'))
        self.export_gcode_button.setIcon(QtGui.QIcon(self.app.resource_location + '/save_as.png'))
        self.export_gcode_button.setToolTip(
            _("Opens dialog to save G-Code\n"
              "file.")
        )
        self.export_gcode_button.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        g_export_lay.addWidget(self.export_gcode_button)

        self.review_gcode_button = QtWidgets.QToolButton()
        self.review_gcode_button.setToolTip(_("Review CNC Code."))
        self.review_gcode_button.setIcon(QtGui.QIcon(self.app.resource_location + '/find32.png'))
        g_export_lay.addWidget(self.review_gcode_button)

        self.custom_box.addStretch()

        self.al_probe_points_table.setRowCount(0)
        self.al_probe_points_table.resizeColumnsToContents()
        self.al_probe_points_table.resizeRowsToContents()
        v_header = self.al_probe_points_table.verticalHeader()
        v_header.hide()
        self.al_probe_points_table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        h_header = self.al_probe_points_table.horizontalHeader()
        h_header.setMinimumSectionSize(10)
        h_header.setDefaultSectionSize(70)
        h_header.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        h_header.resizeSection(0, 20)
        h_header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        h_header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)

        self.al_probe_points_table.setMinimumHeight(self.al_probe_points_table.getHeight())
        self.al_probe_points_table.setMaximumHeight(self.al_probe_points_table.getHeight())

        # Set initial UI
        self.al_frame.hide()
        self.al_rows_entry.setDisabled(True)
        self.al_rows_label.setDisabled(True)
        self.al_columns_entry.setDisabled(True)
        self.al_columns_label.setDisabled(True)
        self.al_method_lbl.setDisabled(True)
        self.al_method_radio.setDisabled(True)
        self.al_method_radio.set_value('v')
        # self.on_mode_radio(val='grid')


class ScriptObjectUI(ObjectUI):
    """
    User interface for Script  objects.
    """

    def __init__(self, app, parent=None):
        """
        Creates the user interface for Script objects. GUI elements should
        be placed in ``self.custom_box`` to preserve the layout.
        """

        self.decimals = app.decimals
        self.app = app

        theme_settings = QtCore.QSettings("Open Source", "FlatCAM")
        if theme_settings.contains("theme"):
            theme = theme_settings.value('theme', type=str)
        else:
            theme = 'white'

        if theme == 'white':
            self.resource_loc = 'assets/resources'
        else:
            self.resource_loc = 'assets/resources'

        ObjectUI.__init__(self, title=_('Script Object'),
                          icon_file=self.resource_loc + '/script_new24.png',
                          parent=parent,
                          common=False,
                          app=self.app)

        # ## Object name
        self.name_hlay = QtWidgets.QHBoxLayout()
        self.custom_box.addLayout(self.name_hlay)

        name_label = FCLabel("<b>%s:</b>" % _("Name"))
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

    def __init__(self, app, parent=None):
        """
        Creates the user interface for Notes objects. GUI elements should
        be placed in ``self.custom_box`` to preserve the layout.
        """

        self.decimals = app.decimals
        self.app = app

        theme_settings = QtCore.QSettings("Open Source", "FlatCAM")
        if theme_settings.contains("theme"):
            theme = theme_settings.value('theme', type=str)
        else:
            theme = 'white'

        if theme == 'white':
            self.resource_loc = 'assets/resources'
        else:
            self.resource_loc = 'assets/resources'

        ObjectUI.__init__(self, title=_('Document Object'),
                          icon_file=self.resource_loc + '/notes16_1.png',
                          parent=parent,
                          common=False,
                          app=self.app)

        # ## Object name
        self.name_hlay = QtWidgets.QHBoxLayout()
        self.custom_box.addLayout(self.name_hlay)

        name_label = FCLabel("<b>%s:</b>" % _("Name"))
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
        self.font_type_label = FCLabel('%s:' % _("Font Type"))

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
        self.font_size_label = FCLabel('%s:' % _("Font Size"))

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
        self.alignment_label = FCLabel('%s:' % _("Alignment"))

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
        self.font_color_label = FCLabel('%s:' % _('Font Color'))
        self.font_color_label.setToolTip(
           _("Set the font color for the selected text")
        )
        self.font_color_entry = FCEntry()
        self.font_color_button = FCButton()
        self.font_color_button.setFixedSize(15, 15)

        self.form_box_child_1 = QtWidgets.QHBoxLayout()
        self.form_box_child_1.addWidget(self.font_color_entry)
        self.form_box_child_1.addWidget(self.font_color_button)
        self.form_box_child_1.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        self.form_box.addRow(self.font_color_label, self.form_box_child_1)

        # Selection Color
        self.sel_color_label = FCLabel('%s:' % _('Selection Color'))
        self.sel_color_label.setToolTip(
           _("Set the selection color when doing text selection.")
        )
        self.sel_color_entry = FCEntry()
        self.sel_color_button = FCButton()
        self.sel_color_button.setFixedSize(15, 15)

        self.form_box_child_2 = QtWidgets.QHBoxLayout()
        self.form_box_child_2.addWidget(self.sel_color_entry)
        self.form_box_child_2.addWidget(self.sel_color_button)
        self.form_box_child_2.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        self.form_box.addRow(self.sel_color_label, self.form_box_child_2)

        # Tab size
        self.tab_size_label = FCLabel('%s:' % _('Tab Size'))
        self.tab_size_label.setToolTip(
            _("Set the tab size. In pixels. Default value is 80 pixels.")
        )
        self.tab_size_spinner = FCSpinner(callback=self.confirmation_message_int)
        self.tab_size_spinner.set_range(0, 1000)

        self.form_box.addRow(self.tab_size_label, self.tab_size_spinner)

        self.custom_box.addStretch()

# end of file
