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


class ObjectUI(QtWidgets.QWidget):
    """
    Base class for the UI of FlatCAM objects. Deriving classes should
    put UI elements in ObjectUI.custom_box (QtWidgets.QLayout).
    """

    def __init__(self, app, icon_file='assets/resources/app32.png', title=_('App Object'),
                 parent=None, common=True):
        QtWidgets.QWidget.__init__(self, parent=parent)

        self.app = app
        self.decimals = app.decimals

        theme_settings = QtCore.QSettings("Open Source", "FlatCAM")
        if theme_settings.contains("theme"):
            theme = theme_settings.value('theme', type=str)
        else:
            theme = 'light'

        if theme == 'light':
            self.resource_loc = 'assets/resources'
        else:
            self.resource_loc = 'assets/resources/dark_resources'

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
        self.title_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.title_box.addWidget(self.title_label, stretch=1)

        # App Level label
        self.level = QtWidgets.QToolButton()
        self.level.setToolTip(
            _(
                "Beginner Mode - many parameters are hidden.\n"
                "Advanced Mode - full control.\n"
                "Permanent change is done in 'Preferences' menu."
            )
        )
        self.level.setCheckable(True)
        self.title_box.addWidget(self.level)

        # ## Box box for custom widgets
        # This gets populated in offspring implementations.
        self.custom_box = QtWidgets.QVBoxLayout()
        layout.addLayout(self.custom_box)

        # ###########################
        # ## Common to all objects ##
        # ###########################
        if common is True:
            # #############################################################################################################
            # Transformations Frame
            # #############################################################################################################
            self.transform_label = FCLabel(_("Transformations"), color='blue', bold=True)
            self.transform_label.setToolTip(
                _("Geometrical transformations of the current object.")
            )

            layout.addWidget(self.transform_label)

            trans_frame = FCFrame()
            layout.addWidget(trans_frame)

            self.common_grid = GLay(v_spacing=5, h_spacing=3)
            self.common_grid.setColumnStretch(0, 1)
            self.common_grid.setColumnStretch(1, 0)
            trans_frame.setLayout(self.common_grid)

            # separator_line = QtWidgets.QFrame()
            # separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
            # separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
            # self.common_grid.addWidget(separator_line, 0, 0, 1, 2)

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

            self.common_grid.addWidget(self.scale_entry, 2, 0)
            self.common_grid.addWidget(self.scale_button, 2, 1)

            # ### Offset ####
            self.offsetvector_entry = NumericalEvalTupleEntry(border_color='#0069A9')
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
            self.common_grid.addWidget(self.transformations_button, 6, 0, 1, 2)

        layout.addStretch(1)
    
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

        self.general_label = FCLabel(_("General Information"), color='darkorange', bold=True)
        self.general_label.setToolTip(_("General data about the object."))
        self.custom_box.addWidget(self.general_label)

        # #############################################################################################################
        # General Frame
        # #############################################################################################################
        gen_frame = FCFrame()
        self.custom_box.addWidget(gen_frame)

        # Plot options
        plot_grid = GLay(v_spacing=5, h_spacing=3)
        plot_grid.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
        gen_frame.setLayout(plot_grid)

        self.plot_options_label = FCLabel('%s:' % _("Plot Options"), bold=True)

        plot_grid.addWidget(self.plot_options_label, 0, 0)

        # Solid CB
        self.solid_cb = FCCheckBox(label=_('Solid'))
        self.solid_cb.setToolTip(
            _("Solid color polygons.")
        )
        plot_grid.addWidget(self.solid_cb, 0, 1)

        # Multicolored CB
        self.multicolored_cb = FCCheckBox(label=_('Multi-Color'))
        self.multicolored_cb.setToolTip(
            _("Draw polygons in different colors.")
        )
        plot_grid.addWidget(self.multicolored_cb, 0, 2)

        # ## Object name
        self.name_hlay = QtWidgets.QHBoxLayout()
        plot_grid.addLayout(self.name_hlay, 1, 0, 1, 3)

        name_label = FCLabel('%s:' % _("Name"), bold=True)
        self.name_entry = FCEntry()
        self.name_entry.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.name_hlay.addWidget(name_label)
        self.name_hlay.addWidget(self.name_entry)

        # Plot CB
        self.plot_lbl = FCLabel('%s:' % _("Plot"))
        self.plot_lbl.setToolTip(_("Plot (show) this object."))
        self.plot_cb = FCCheckBox()

        plot_grid.addWidget(self.plot_lbl, 2, 0)
        plot_grid.addWidget(self.plot_cb, 2, 1)

        # Generate 'Follow'
        self.follow_cb = FCCheckBox('%s' % _("Follow"))
        self.follow_cb.setToolTip(_("Generate a 'Follow' geometry.\n"
                                    "This means that it will cut through\n"
                                    "the middle of the trace."))
        plot_grid.addWidget(self.follow_cb, 2, 2)

        # Editor
        self.editor_button = FCButton(_('Gerber Editor'), bold=True)
        self.editor_button.setIcon(QtGui.QIcon(self.app.resource_location + '/edit_file32.png'))
        self.editor_button.setToolTip(
            _("Start the Object Editor")
        )
        self.custom_box.addWidget(self.editor_button)

        # INFO CB
        self.info_button = FCButton('%s' % _("INFO"), checkable=True, bold=True)
        self.info_button.setIcon(QtGui.QIcon(self.app.resource_location + '/properties32.png'))
        self.info_button.setToolTip(_("Show the Object Attributes."))
        self.custom_box.addWidget(self.info_button)

        # INFO Frame
        self.info_frame = QtWidgets.QFrame()
        self.info_frame.setContentsMargins(0, 0, 0, 0)
        self.custom_box.addWidget(self.info_frame)

        self.info_box = QtWidgets.QVBoxLayout()
        self.info_box.setContentsMargins(0, 0, 0, 0)
        self.info_frame.setLayout(self.info_box)
        self.info_frame.hide()

        self.treeWidget = FCTree(columns=2)

        self.info_box.addWidget(self.treeWidget)
        self.info_box.setStretch(0, 0)

        # #############################################################################################################
        # Gerber Tool Table Frame
        # #############################################################################################################
        self.tools_table_label = FCLabel(_("Tools Table"), color='green', bold=True)
        self.tools_table_label.setToolTip(_("Tools/apertures in the loaded object."))
        self.custom_box.addWidget(self.tools_table_label)

        self.tt_frame = FCFrame()
        self.custom_box.addWidget(self.tt_frame)

        # Grid Layout
        tt_grid = GLay(v_spacing=5, h_spacing=3)
        self.tt_frame.setLayout(tt_grid)

        # ### Gerber Apertures ####
        self.apertures_table_label = FCLabel('%s' % _('Apertures'))
        self.apertures_table_label.setToolTip(
            _("Apertures Table for the Gerber Object.")
        )

        tt_grid.addWidget(self.apertures_table_label, 0, 0)

        # Aperture Table Visibility CB
        self.aperture_table_visibility_cb = FCCheckBox()
        self.aperture_table_visibility_cb.setToolTip(
            _("Toggle the display of the Tools Table.")
        )
        # self.aperture_table_visibility_cb.setLayoutDirection(QtCore.Qt.LayoutDirection.RightToLeft)
        tt_grid.addWidget(self.aperture_table_visibility_cb, 0, 1)

        hlay_plot = QtWidgets.QHBoxLayout()
        tt_grid.addLayout(hlay_plot, 0, 2)

        # Aperture Mark all CB
        self.mark_all_cb = FCCheckBox(_('Mark All'))
        self.mark_all_cb.setToolTip(
            _("When checked it will display all the apertures.\n"
              "When unchecked, it will delete all mark shapes\n"
              "that are drawn on canvas.")

        )
        self.mark_all_cb.setLayoutDirection(QtCore.Qt.LayoutDirection.RightToLeft)
        hlay_plot.addStretch()
        hlay_plot.addWidget(self.mark_all_cb)

        # Apertures Table
        self.apertures_table = FCTable()
        tt_grid.addWidget(self.apertures_table, 2, 0, 1, 3)

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
        tt_grid.addWidget(self.create_buffer_button, 4, 0, 1, 3)

        # separator_line1 = QtWidgets.QFrame()
        # separator_line1.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        # separator_line1.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        # plot_grid.addWidget(separator_line1, 13, 0, 1, 3)

        # #############################################################################################################
        # PLUGINS Frame
        # #############################################################################################################
        self.tool_lbl = FCLabel(_("Plugins"), color='indigo', bold=True)
        self.custom_box.addWidget(self.tool_lbl)

        plugins_frame = FCFrame()
        self.custom_box.addWidget(plugins_frame)

        # Grid Layout
        plugins_grid = GLay(v_spacing=5, h_spacing=3, c_stretch=[0, 0])
        plugins_frame.setLayout(plugins_grid)

        # Isolation Tool - will create isolation paths around the copper features
        self.iso_button = FCButton(_('Isolation Routing'), bold=True)
        # self.iso_button.setIcon(QtGui.QIcon(self.app.resource_location + '/iso_16.png'))
        self.iso_button.setToolTip(
            _("Create a Geometry object with\n"
              "toolpaths to cut around polygons.")
        )
        plugins_grid.addWidget(self.iso_button, 0, 0)

        # ## Board cutout
        self.generate_cutout_button = FCButton(_('Cutout'))
        self.generate_cutout_button.setIcon(QtGui.QIcon(self.app.resource_location + '/cut32.png'))
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
        plugins_grid.addWidget(self.generate_cutout_button, 2, 0)

        # ## Film Plugin
        self.generate_film_button = FCButton(_("Film"))
        self.generate_film_button.setIcon(QtGui.QIcon(self.app.resource_location + '/film32.png'))
        self.generate_film_button.setToolTip(
            _("Create a positive/negative film for UV exposure.")
        )
        # self.generate_film_button.setStyleSheet("""
        #                 QPushButton
        #                 {
        #                     font-weight: bold;
        #                 }
        #                 """)
        plugins_grid.addWidget(self.generate_film_button, 4, 0)

        # ## Clear non-copper regions
        self.generate_ncc_button = FCButton(_('NCC'))
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
        plugins_grid.addWidget(self.generate_ncc_button, 6, 0)

        # Follow Plugin
        self.generate_follow_button = FCButton(_('Follow'))
        self.generate_follow_button.setIcon(QtGui.QIcon(self.app.resource_location + '/follow32.png'))
        self.generate_follow_button.setToolTip(
            _("Generate a 'Follow' geometry.\n"
              "This means that it will cut through\n"
              "the middle of the trace."))
        # self.generate_cutout_button.setStyleSheet("""

        plugins_grid.addWidget(self.generate_follow_button, 8, 0)

        # separator_line = QtWidgets.QFrame()
        # separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        # separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        # self.custom_box.addWidget(separator_line)

        # UTILITIES BUTTON
        self.util_button = FCButton('%s' % _("Utilities").upper(), checkable=True, bold=True)
        self.util_button.setIcon(QtGui.QIcon(self.app.resource_location + '/settings18.png'))
        self.util_button.setToolTip(_("Show the Utilities."))
        self.custom_box.addWidget(self.util_button)

        # UTILITIES Frame
        self.util_frame = QtWidgets.QFrame()
        self.util_frame.setContentsMargins(0, 0, 0, 0)
        self.custom_box.addWidget(self.util_frame)

        self.util_box = QtWidgets.QVBoxLayout()
        self.util_box.setContentsMargins(0, 0, 0, 0)
        self.util_frame.setLayout(self.util_box)
        self.util_frame.hide()

        # #############################################################################################################
        # Non-Copper Regions Frame
        # #############################################################################################################
        # ## Non-copper regions
        self.noncopper_label = FCLabel('%s' % _("Non-copper regions"), bold=True)
        self.noncopper_label.setToolTip(
            _("Create polygons covering the\n"
              "areas without copper on the PCB.\n"
              "Equivalent to the inverse of this\n"
              "object. Can be used to remove all\n"
              "copper from a specified region.")
        )
        self.util_box.addWidget(self.noncopper_label)

        ncc_frame = FCFrame()
        self.util_box.addWidget(ncc_frame)

        grid_ncc = GLay(v_spacing=5, h_spacing=3)
        ncc_frame.setLayout(grid_ncc)

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

        grid_ncc.addWidget(bmlabel, 2, 0)
        grid_ncc.addWidget(self.noncopper_margin_entry, 2, 1, 1, 2)

        # Rounded corners
        self.noncopper_rounded_cb = FCCheckBox(label=_("Rounded"))
        self.noncopper_rounded_cb.setToolTip(
            _("Resulting geometry will have rounded corners.")
        )

        self.generate_noncopper_button = FCButton(_('Generate Geometry'))
        self.generate_noncopper_button.setIcon(QtGui.QIcon(self.app.resource_location + '/geometry32.png'))
        grid_ncc.addWidget(self.noncopper_rounded_cb, 4, 0)
        grid_ncc.addWidget(self.generate_noncopper_button, 4, 1, 1, 2)

        # #############################################################################################################
        # Bounding Box Frame
        # #############################################################################################################
        # ## Bounding box
        self.boundingbox_label = FCLabel('%s' % _('Bounding Box'), bold=True)
        self.boundingbox_label.setToolTip(
            _("Create a geometry surrounding the Gerber object.\n"
              "Square shape.")
        )

        self.util_box.addWidget(self.boundingbox_label)

        bb_frame = FCFrame()
        self.util_box.addWidget(bb_frame)

        # Grid Layout
        grid_bb = GLay(v_spacing=5, h_spacing=3)
        bb_frame.setLayout(grid_bb)

        bbmargin = FCLabel('%s:' % _('Boundary Margin'))
        bbmargin.setToolTip(
            _("Distance of the edges of the box\n"
              "to the nearest polygon.")
        )
        self.bbmargin_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.bbmargin_entry.set_range(-10000.0000, 10000.0000)
        self.bbmargin_entry.set_precision(self.decimals)
        self.bbmargin_entry.setSingleStep(0.1)

        grid_bb.addWidget(bbmargin, 0, 0)
        grid_bb.addWidget(self.bbmargin_entry, 0, 1, 1, 2)

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
        grid_bb.addWidget(self.bbrounded_cb, 2, 0)
        grid_bb.addWidget(self.generate_bb_button, 2, 1, 1, 2)


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
            theme = 'light'

        if theme == 'light':
            self.resource_loc = 'assets/resources'
        else:
            self.resource_loc = 'assets/resources/dark_resources'

        ObjectUI.__init__(self, title=_('Excellon Object'),
                          icon_file=self.resource_loc + '/drill32.png',
                          parent=parent,
                          app=self.app)

        self.general_label = FCLabel(_("General Information"), color='darkorange', bold=True)
        self.general_label.setToolTip(_("General data about the object."))
        self.custom_box.addWidget(self.general_label)

        # #############################################################################################################
        # General Frame
        # #############################################################################################################
        gen_frame = FCFrame()
        self.custom_box.addWidget(gen_frame)

        # Plot options
        plot_grid = GLay(v_spacing=5, h_spacing=3)
        plot_grid.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
        gen_frame.setLayout(plot_grid)

        # Plot options
        self.plot_options_label = FCLabel('%s: ' % _("Plot Options"), bold=True)

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

        plot_grid.addWidget(self.plot_options_label, 0, 0)
        plot_grid.addWidget(self.solid_cb, 0, 1)
        plot_grid.addWidget(self.multicolored_cb, 0, 2)

        # ## Object name
        self.name_hlay = QtWidgets.QHBoxLayout()

        name_label = FCLabel('%s: ' % _("Name"), bold=True)
        self.name_entry = FCEntry()
        self.name_entry.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.name_hlay.addWidget(name_label)
        self.name_hlay.addWidget(self.name_entry)

        plot_grid.addLayout(self.name_hlay, 2, 0, 1, 3)

        # Editor
        self.editor_button = FCButton(_('Excellon Editor'), bold=True)
        self.editor_button.setIcon(QtGui.QIcon(self.app.resource_location + '/edit_file32.png'))

        self.editor_button.setToolTip(
            _("Start the Object Editor")
        )
        self.custom_box.addWidget(self.editor_button)

        # INFO CB
        self.info_button = FCButton('%s' % _("INFO"), checkable=True, bold=True)
        self.info_button.setIcon(QtGui.QIcon(self.app.resource_location + '/properties32.png'))
        self.info_button.setToolTip(_("Show the Object Attributes."))
        self.custom_box.addWidget(self.info_button)

        # INFO Frame
        self.info_frame = QtWidgets.QFrame()
        self.info_frame.setContentsMargins(0, 0, 0, 0)
        self.custom_box.addWidget(self.info_frame)

        self.info_box = QtWidgets.QVBoxLayout()
        self.info_box.setContentsMargins(0, 0, 0, 0)
        self.info_frame.setLayout(self.info_box)
        self.info_frame.hide()

        self.treeWidget = FCTree(columns=2)

        self.info_box.addWidget(self.treeWidget)
        self.info_box.setStretch(0, 0)

        # #############################################################################################################
        # Excellon Tool Table Frame
        # #############################################################################################################
        self.tools_table_label = FCLabel('%s: ' % _("Tools Table"), color='green', bold=True)
        self.tools_table_label.setToolTip(_("Tools/apertures in the loaded object."))
        self.custom_box.addWidget(self.tools_table_label)

        tt_grid = GLay(v_spacing=5, h_spacing=3)
        tt_grid.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.custom_box.addLayout(tt_grid)

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
        self.plot_cb.setLayoutDirection(QtCore.Qt.LayoutDirection.RightToLeft)
        hlay_plot.addStretch()
        hlay_plot.addWidget(self.plot_cb)

        tt_grid.addWidget(self.tools_table_label, 0, 0)
        tt_grid.addWidget(self.table_visibility_cb, 0, 1)
        tt_grid.addLayout(hlay_plot, 0, 2)

        # #############################################################################################################
        # #############################################################################################################
        # add a frame and inside add a vertical box layout. Inside this vbox layout I add all the Drills widgets
        # this way I can hide/show the frame
        # #############################################################################################################
        # #############################################################################################################

        self.drills_frame = FCFrame()
        self.custom_box.addWidget(self.drills_frame)

        self.tools_box = QtWidgets.QVBoxLayout()
        self.drills_frame.setLayout(self.tools_box)

        self.tools_table = FCTable()
        self.tools_table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tools_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.tools_box.addWidget(self.tools_table)

        self.tools_table.setColumnCount(6)
        self.tools_table.setHorizontalHeaderLabels(['#', _('Diameter'), _('Drills'), _('Slots'), "C", 'P'])
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

        # #############################################################################################################
        # Plugins Frame
        # #############################################################################################################
        self.tool_lbl = FCLabel('%s' % _("Plugins"), color='indigo', bold=True)
        self.custom_box.addWidget(self.tool_lbl)

        plugins_frame = FCFrame()
        self.custom_box.addWidget(plugins_frame)

        plugins_grid = GLay(v_spacing=5, h_spacing=3, c_stretch=[0, 0])
        plugins_frame.setLayout(plugins_grid)

        # Drilling Tool - will create GCode for drill holes
        self.drill_button = FCButton(_('Drilling'), bold=True)
        self.drill_button.setIcon(QtGui.QIcon(self.app.resource_location + '/drilling_tool32.png'))
        self.drill_button.setToolTip(
            _("Generate GCode from the drill holes in an Excellon object.")
        )
        plugins_grid.addWidget(self.drill_button, 0, 0)

        # Milling Tool - will create GCode for slot holes
        self.milling_button = FCButton(_('Milling'))
        self.milling_button.setIcon(QtGui.QIcon(self.app.resource_location + '/milling_tool32.png'))
        self.milling_button.setToolTip(
            _("Generate a Geometry for milling drills or slots in an Excellon object.")
        )
        plugins_grid.addWidget(self.milling_button, 2, 0)

        # separator_line = QtWidgets.QFrame()
        # separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        # separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        # self.custom_box.addWidget(separator_line)

        # UTILITIES BUTTON
        self.util_button = FCButton('%s' % _("Utilities").upper(), checkable=True, bold=True)
        self.util_button.setIcon(QtGui.QIcon(self.app.resource_location + '/settings18.png'))
        self.util_button.setToolTip(_("Show the Utilities."))
        self.custom_box.addWidget(self.util_button)

        # UTILITIES Frame
        self.util_frame = QtWidgets.QFrame()
        self.util_frame.setContentsMargins(0, 0, 0, 0)
        self.custom_box.addWidget(self.util_frame)

        self.util_box = QtWidgets.QVBoxLayout()
        self.util_box.setContentsMargins(0, 0, 0, 0)
        self.util_frame.setLayout(self.util_box)
        self.util_frame.hide()

        # #############################################################################################################
        # Milling Drill Holes Frame
        # #############################################################################################################
        self.mill_hole_label = FCLabel('%s' % _('Milling Geometry'), bold=True)
        self.mill_hole_label.setToolTip(
            _("Create Geometry for milling holes.\n"
              "Select from the Tools Table above the hole dias to be\n"
              "milled. Use the # column to make the selection.")
        )
        self.util_box.addWidget(self.mill_hole_label)

        mill_frame = FCFrame()
        self.util_box.addWidget(mill_frame)

        grid_mill = GLay(v_spacing=5, h_spacing=3)
        mill_frame.setLayout(grid_mill)

        self.tdlabel = FCLabel('%s:' % _('Milling Diameter'))
        self.tdlabel.setToolTip(
            _("Diameter of the cutting tool.")
        )

        grid_mill.addWidget(self.tdlabel, 0, 0, 1, 3)

        self.tooldia_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.tooldia_entry.set_precision(self.decimals)
        self.tooldia_entry.set_range(0.0, 10000.0000)
        self.tooldia_entry.setSingleStep(0.1)

        self.generate_milling_button = FCButton(_('Mill Drills'), bold=True)
        self.generate_milling_button.setToolTip(
            _("Create the Geometry Object\n"
              "for milling drills.")
        )

        grid_mill.addWidget(self.tooldia_entry, 2, 0, 1, 2)
        grid_mill.addWidget(self.generate_milling_button, 2, 2)

        self.slot_tooldia_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.slot_tooldia_entry.set_precision(self.decimals)
        self.slot_tooldia_entry.set_range(0.0, 10000.0000)
        self.slot_tooldia_entry.setSingleStep(0.1)

        self.generate_milling_slots_button = FCButton(_('Mill Slots'), bold=True)
        self.generate_milling_slots_button.setToolTip(
            _("Create the Geometry Object\n"
              "for milling slots.")
        )

        grid_mill.addWidget(self.slot_tooldia_entry, 4, 0, 1, 2)
        grid_mill.addWidget(self.generate_milling_slots_button, 4, 2)

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
            theme = 'light'

        if theme == 'light':
            self.resource_loc = 'assets/resources'
        else:
            self.resource_loc = 'assets/resources/dark_resources'

        super(GeometryObjectUI, self).__init__(
            title=_('Geometry Object'),
            icon_file=self.resource_loc + '/geometry32.png', parent=parent,  app=self.app
        )

        self.general_label = FCLabel('%s' % _("General Information"), color='darkorange', bold=True)
        self.general_label.setToolTip(_("General data about the object."))
        self.custom_box.addWidget(self.general_label)

        # #############################################################################################################
        # General Frame
        # #############################################################################################################
        gen_frame = FCFrame()
        self.custom_box.addWidget(gen_frame)

        # Plot options
        plot_grid = GLay(v_spacing=5, h_spacing=3)
        plot_grid.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
        gen_frame.setLayout(plot_grid)

        self.plot_options_label = FCLabel('%s:' % _("Plot Options"), bold=True)
        self.plot_options_label.setMinimumWidth(90)

        plot_grid.addWidget(self.plot_options_label, 0, 0)

        # Multicolored CB
        self.multicolored_cb = FCCheckBox(label=_('Multi-Color'))
        self.multicolored_cb.setToolTip(
            _("Draw polygons in different colors.")
        )
        self.multicolored_cb.setMinimumWidth(55)
        plot_grid.addWidget(self.multicolored_cb, 0, 2)

        # ## Object name
        self.name_hlay = QtWidgets.QHBoxLayout()
        plot_grid.addLayout(self.name_hlay, 2, 0, 1, 3)

        name_label = FCLabel('%s:' % _("Name"), bold=True)
        self.name_entry = FCEntry()
        self.name_entry.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.name_hlay.addWidget(name_label)
        self.name_hlay.addWidget(self.name_entry)

        # Editor
        self.editor_button = FCButton(_('Geometry Editor'), bold=True)
        self.editor_button.setIcon(QtGui.QIcon(self.app.resource_location + '/edit_file32.png'))

        self.editor_button.setToolTip(
            _("Start the Object Editor")
        )
        self.custom_box.addWidget(self.editor_button)

        # INFO CB
        self.info_button = FCButton('%s' % _("INFO"), checkable=True, bold=True)
        self.info_button.setIcon(QtGui.QIcon(self.app.resource_location + '/properties32.png'))
        self.info_button.setToolTip(_("Show the Object Attributes."))
        self.custom_box.addWidget(self.info_button)

        # INFO Frame
        self.info_frame = QtWidgets.QFrame()
        self.info_frame.setContentsMargins(0, 0, 0, 0)
        self.custom_box.addWidget(self.info_frame)

        self.info_box = QtWidgets.QVBoxLayout()
        self.info_box.setContentsMargins(0, 0, 0, 0)
        self.info_frame.setLayout(self.info_box)
        self.info_frame.hide()

        self.treeWidget = FCTree(columns=2)

        self.info_box.addWidget(self.treeWidget)
        self.info_box.setStretch(0, 0)

        # #############################################################################################################
        # Gerber Tool Table Frame
        # #############################################################################################################
        self.tools_table_label = FCLabel('%s' % _("Tools Table"), color='green', bold=True)
        self.tools_table_label.setToolTip(_("Tools/apertures in the loaded object."))
        self.custom_box.addWidget(self.tools_table_label)

        self.tt_frame = FCFrame()
        self.custom_box.addWidget(self.tt_frame)

        # Grid Layout
        tt_grid = GLay(v_spacing=5, h_spacing=3)
        self.tt_frame.setLayout(tt_grid)

        # ### Tools ####
        self.tools_table_label = FCLabel('%s:' % _('Tools Table'), bold=True)
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
        tt_grid.addWidget(self.tools_table_label, 0, 0)

        # Plot CB
        # self.plot_cb = QtWidgets.QCheckBox('Plot')
        self.plot_cb = FCCheckBox(_('Plot Object'))
        self.plot_cb.setToolTip(
            _("Plot (show) this object.")
        )
        self.plot_cb.setLayoutDirection(QtCore.Qt.LayoutDirection.RightToLeft)
        tt_grid.addWidget(self.plot_cb, 0, 1)

        self.geo_tools_table = FCTable(drag_drop=True)
        tt_grid.addWidget(self.geo_tools_table, 1, 0, 1, 2)
        self.geo_tools_table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)

        self.geo_tools_table.setColumnCount(7)
        self.geo_tools_table.setColumnWidth(0, 20)
        self.geo_tools_table.setHorizontalHeaderLabels(['#', _('Dia'), _('Offset'), _('Job'), _('Shape'), '', 'P'])
        self.geo_tools_table.setColumnHidden(5, True)
        # stylesheet = "::section{Background-color:rgb(239,239,245)}"
        # self.geo_tools_table.horizontalHeader().setStyleSheet(stylesheet)

        self.geo_tools_table.horizontalHeaderItem(0).setToolTip(
            _(
                "Tool Number.\n"
                "When ToolChange is checked, on toolchange event this value\n"
                "will be showed as a T1, T2 ... Tn")
            )
        self.geo_tools_table.horizontalHeaderItem(1).setToolTip(
            _("Tool Diameter. Its value\n"
              "is the cut width into the material."))
        self.geo_tools_table.horizontalHeaderItem(2).setToolTip(
            _(
                "Offset Type. The kind of cut offset to be used."
            ))
        self.geo_tools_table.horizontalHeaderItem(3).setToolTip(
            _(
                "Job Type. Usually the UI form values \n"
                "are choose based on the operation type and this will serve as a reminder."
            ))
        self.geo_tools_table.horizontalHeaderItem(4).setToolTip(
            _("Tool Shape. \n"
              "Can be:\n"
              "C1 ... C4 = circular tool with x flutes\n"
              "B = ball tip milling tool\n"
              "V = v-shape milling tool\n"
              "L = laser")
        )
        self.geo_tools_table.horizontalHeaderItem(6).setToolTip(
            _("Plot column. It is visible only for MultiGeo Geometry objects.\n"
              "Enable plot for the selected tool geometry."))

        # #############################################################################################################
        # PLUGINS Frame
        # #############################################################################################################
        self.tools_label = FCLabel('%s' % _("Plugins"), color='indigo', bold=True)
        self.custom_box.addWidget(self.tools_label)

        plugins_frame = FCFrame()
        self.custom_box.addWidget(plugins_frame)

        plugins_grid = GLay(v_spacing=5, h_spacing=3, c_stretch=[0, 0])
        plugins_frame.setLayout(plugins_grid)

        # Milling Tool - will create GCode for slot holes
        self.milling_button = FCButton(_('Milling'), bold=True)
        self.milling_button.setIcon(QtGui.QIcon(self.app.resource_location + '/milling_tool32.png'))
        self.milling_button.setToolTip(
            _("Generate a CNCJob by milling a Geometry.")
        )
        plugins_grid.addWidget(self.milling_button, 0, 0)

        # Paint Button
        self.paint_tool_button = FCButton(_('Paint'))
        self.paint_tool_button.setIcon(QtGui.QIcon(self.app.resource_location + '/paint32.png'))
        self.paint_tool_button.setToolTip(
            _("Creates tool paths to cover the\n"
              "whole area of a polygon.")
        )

        plugins_grid.addWidget(self.paint_tool_button, 2, 0)

        # NCC Tool
        self.generate_ncc_button = FCButton(_('NCC'))
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
        plugins_grid.addWidget(self.generate_ncc_button, 4, 0)

        # separator_line = QtWidgets.QFrame()
        # separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        # separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        # self.custom_box.addWidget(separator_line)

        # UTILITIES BUTTON
        self.util_button = FCButton('%s' % _("Utilities").upper(), checkable=True, bold=True)
        self.util_button.setIcon(QtGui.QIcon(self.app.resource_location + '/settings18.png'))
        self.util_button.setToolTip(_("Show the Utilities."))
        self.custom_box.addWidget(self.util_button)

        # UTILITIES Frame
        self.util_frame = QtWidgets.QFrame()
        self.util_frame.setContentsMargins(0, 0, 0, 0)
        self.custom_box.addWidget(self.util_frame)

        self.util_box = QtWidgets.QVBoxLayout()
        self.util_box.setContentsMargins(0, 0, 0, 0)
        self.util_frame.setLayout(self.util_box)
        self.util_frame.hide()

        # #############################################################################################################
        # Simplification Frame
        # #############################################################################################################
        # Simplification Title
        simplif_lbl = FCLabel('%s' % _("Simplification"), bold=True)
        simplif_lbl.setToolTip(
            _("Simplify a geometry by reducing its vertex points number.")
        )
        self.util_box.addWidget(simplif_lbl)

        sim_frame = FCFrame()
        self.util_box.addWidget(sim_frame)

        grid_sim = GLay(v_spacing=5, h_spacing=3)
        sim_frame.setLayout(grid_sim)

        # Vertex Points
        vertexes_lbl = FCLabel('%s:' % _("Points"))
        vertexes_lbl.setToolTip(
            _("Total of vertex points in the geometry.")
        )
        self.vertex_points_entry = FCEntry()

        grid_sim.addWidget(vertexes_lbl, 2, 0)
        grid_sim.addWidget(self.vertex_points_entry, 2, 1)

        # Calculate vertexes button
        self.vertex_points_btn = FCButton(_("Calculate"))
        # self.vertex_points_btn.setIcon(QtGui.QIcon(self.app.resource_location + '/simplify32.png'))
        self.vertex_points_btn.setToolTip(
            _("Calculate the number of vertex points in the geometry.")
        )
        # self.vertex_points_btn.setStyleSheet("""
        #                                       QPushButton
        #                                       {
        #                                           font-weight: bold;
        #                                       }
        #                                       """)

        grid_sim.addWidget(self.vertex_points_btn, 2, 2)

        # Simplification Tolerance
        simplification_tol_lbl = FCLabel('%s:' % _("Tolerance"))
        simplification_tol_lbl.setToolTip(
            _("All points in the simplified object will be\n"
              "within the tolerance distance of the original geometry.")
        )
        self.geo_tol_entry = FCDoubleSpinner()
        self.geo_tol_entry.set_precision(self.decimals)
        self.geo_tol_entry.setSingleStep(10 ** -self.decimals)
        self.geo_tol_entry.set_range(0.0000, 10000.0000)

        grid_sim.addWidget(simplification_tol_lbl, 4, 0)
        grid_sim.addWidget(self.geo_tol_entry, 4, 1)

        # Simplification button
        self.simplification_btn = FCButton(_("Simplify"))
        # self.simplification_btn.setIcon(QtGui.QIcon(self.app.resource_location + '/simplify32.png'))
        self.simplification_btn.setToolTip(
            _("Simplify a geometry element by reducing its vertex points number.")
        )
        # self.simplification_btn.setStyleSheet("""
        #                                       QPushButton
        #                                       {
        #                                           font-weight: bold;
        #                                       }
        #                                       """)

        grid_sim.addWidget(self.simplification_btn, 4, 2)


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
            theme = 'light'

        if theme == 'light':
            self.resource_loc = 'assets/resources'
        else:
            self.resource_loc = 'assets/resources/dark_resources'

        ObjectUI.__init__(self, title=_('CNC Job Object'),
                          icon_file=self.resource_loc + '/cnc32.png', parent=parent,
                          app=self.app, common=False)

        # for i in range(0, self.common_grid.count()):
        #     self.common_grid.itemAt(i).widget().hide()
        self.general_label = FCLabel('%s' % _("General Information"), color='darkorange', bold=True)
        self.general_label.setToolTip(_("General data about the object."))
        self.custom_box.addWidget(self.general_label)

        # #############################################################################################################
        # General Frame
        # #############################################################################################################
        gen_frame = FCFrame()
        self.custom_box.addWidget(gen_frame)

        # Plot options
        grid0 = GLay(v_spacing=5, h_spacing=3)
        grid0.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
        gen_frame.setLayout(grid0)

        # Plot Options
        self.cncplot_method_label = FCLabel('%s: ' % _("Plot Options"), bold=True)
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
        ], compact=True)

        grid0.addWidget(self.cncplot_method_label, 0, 0)
        grid0.addWidget(self.cncplot_method_combo, 0, 1, 1, 2)

        self.name_hlay = QtWidgets.QHBoxLayout()
        grid0.addLayout(self.name_hlay, 2, 0, 1, 3)

        # ## Object name
        name_label = FCLabel('%s: ' % _("Name"), bold=True)
        self.name_entry = FCEntry()
        self.name_entry.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)

        self.name_hlay.addWidget(name_label)
        self.name_hlay.addWidget(self.name_entry)

        # Editor
        self.editor_button = FCButton(_('GCode Editor'), bold=True)
        self.editor_button.setIcon(QtGui.QIcon(self.app.resource_location + '/edit_file32.png'))

        self.editor_button.setToolTip(_("Start the Object Editor"))
        self.custom_box.addWidget(self.editor_button)

        # INFO CB
        self.info_button = FCButton('%s' % _("INFO"), checkable=True, bold=True)
        self.info_button.setIcon(QtGui.QIcon(self.app.resource_location + '/properties32.png'))
        self.info_button.setToolTip(_("Show the Object Attributes."))
        self.custom_box.addWidget(self.info_button)

        # INFO Frame
        self.info_frame = QtWidgets.QFrame()
        self.info_frame.setContentsMargins(0, 0, 0, 0)
        self.custom_box.addWidget(self.info_frame)

        self.info_box = QtWidgets.QVBoxLayout()
        self.info_box.setContentsMargins(0, 0, 0, 0)
        self.info_frame.setLayout(self.info_box)
        self.info_frame.hide()

        self.treeWidget = FCTree(columns=2)

        self.info_box.addWidget(self.treeWidget)
        self.info_box.setStretch(0, 0)

        # #############################################################################################################
        # COMMON PARAMETERS Frame
        # #############################################################################################################
        self.param_label = FCLabel('%s' % _("Parameters"), color='blue', bold=True)
        self.custom_box.addWidget(self.param_label)

        self.gp_frame = FCFrame()
        self.gp_frame.setSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Minimum)
        self.custom_box.addWidget(self.gp_frame)

        grid_par = GLay(v_spacing=5, h_spacing=3)
        self.gp_frame.setLayout(grid_par)

        self.estimated_frame = QtWidgets.QFrame()
        self.estimated_frame.setContentsMargins(0, 0, 0, 0)
        estimated_grid = GLay(v_spacing=5, h_spacing=3)
        estimated_grid.setContentsMargins(0, 0, 0, 0)
        self.estimated_frame.setLayout(estimated_grid)
        grid_par.addWidget(self.estimated_frame, 4, 0, 1, 3)

        # Travelled Distance
        self.t_distance_label = FCLabel('%s:' % _("Travelled distance"), bold=True)
        self.t_distance_label.setToolTip(
            _("This is the total travelled distance on X-Y plane.\n"
              "In current units.")
        )
        self.t_distance_entry = FCEntry()
        self.units_label = FCLabel()

        estimated_grid.addWidget(self.t_distance_label, 0, 0)
        estimated_grid.addWidget(self.t_distance_entry, 0, 1)
        estimated_grid.addWidget(self.units_label, 0, 2)

        # Estimated Time
        self.t_time_label = FCLabel('%s:' % _("Estimated time"), bold=True)
        self.t_time_label.setToolTip(
            _("This is the estimated time to do the routing/drilling,\n"
              "without the time spent in ToolChange events.")
        )
        self.t_time_entry = FCEntry()
        self.units_time_label = FCLabel()

        estimated_grid.addWidget(self.t_time_label, 2, 0)
        estimated_grid.addWidget(self.t_time_entry, 2, 1)
        estimated_grid.addWidget(self.units_time_label, 2, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        estimated_grid.addWidget(separator_line, 4, 0, 1, 3)

        self.estimated_frame.hide()
        self.gp_frame.resize(self.gp_frame.minimumSizeHint())
        self.gp_frame.adjustSize()

        # CNC Code snippets
        self.snippets_cb = FCCheckBox(_("Use CNC Code Snippets"))
        self.snippets_cb.setToolTip(
            _("When selected, it will include CNC Code snippets (append and prepend)\n"
              "defined in the Preferences.")
        )
        grid_par.addWidget(self.snippets_cb, 12, 0, 1, 3)

        # Annotation
        self.annotation_cb = FCCheckBox(_("Display Annotation"))
        self.annotation_cb.setToolTip(
            _("This selects if to display text annotation on the plot.\n"
              "When checked it will display numbers in order for each end\n"
              "of a travel line.")
        )
        grid_par.addWidget(self.annotation_cb, 14, 0, 1, 3)

        # #############################################################################################################
        # CNC Tool Table Frame
        # #############################################################################################################
        self.tools_table_label = FCLabel('%s' % _("Tools Table"), color='green', bold=True)
        self.tools_table_label.setToolTip(_("Tools/apertures in the loaded object."))
        self.custom_box.addWidget(self.tools_table_label)

        self.tt_frame = FCFrame()
        self.custom_box.addWidget(self.tt_frame)

        # Grid Layout
        grid1 = GLay(v_spacing=5, h_spacing=3)
        self.tt_frame.setLayout(grid1)

        hlay = QtWidgets.QHBoxLayout()
        grid1.addLayout(hlay, 0, 0, 1, 2)

        # CNC Tools Table for plot
        self.cnc_tools_table_label = FCLabel('%s' % _('CNC Tools Table'), bold=True)
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
        self.plot_cb.setLayoutDirection(QtCore.Qt.LayoutDirection.RightToLeft)
        hlay.addStretch()
        hlay.addWidget(self.plot_cb)

        self.cnc_tools_table = FCTable()
        grid1.addWidget(self.cnc_tools_table, 2, 0, 1, 2)

        self.cnc_tools_table.setColumnCount(7)
        self.cnc_tools_table.setColumnWidth(0, 20)
        self.cnc_tools_table.setHorizontalHeaderLabels(['#', _('Dia'), _('Offset'), _('Job'), _('Shape'), '', _('P')])
        self.cnc_tools_table.setColumnHidden(5, True)
        # stylesheet = "::section{Background-color:rgb(239,239,245)}"
        # self.cnc_tools_table.horizontalHeader().setStyleSheet(stylesheet)

        self.exc_cnc_tools_table = FCTable()
        grid1.addWidget(self.exc_cnc_tools_table, 4, 0, 1, 2)

        self.exc_cnc_tools_table.setColumnCount(7)
        self.exc_cnc_tools_table.setColumnWidth(0, 20)
        self.exc_cnc_tools_table.setHorizontalHeaderLabels(['#', _('Dia'), _('Drills'), _('Slots'), '', _("Cut Z"),
                                                            _('P')])
        self.exc_cnc_tools_table.setColumnHidden(4, True)

        self.tooldia_entry = FCDoubleSpinner(callback=self.confirmation_message)
        self.tooldia_entry.set_range(0, 10000.0000)
        self.tooldia_entry.set_precision(self.decimals)
        self.tooldia_entry.setSingleStep(0.1)
        grid1.addWidget(self.tooldia_entry, 6, 0, 1, 2)

        # Update plot button
        self.updateplot_button = FCButton(_('Update Plot'))
        self.updateplot_button.setToolTip(
            _("Update the plot.")
        )
        grid1.addWidget(self.updateplot_button, 8, 0, 1, 2)

        # #############################################################################################################
        # ######################   PLUGINS   ##########################################################################
        # #############################################################################################################
        self.tool_lbl = FCLabel('%s' % _("Plugins"), color='indigo', bold=True)
        self.custom_box.addWidget(self.tool_lbl)

        # Levelling Tool - will process the generated GCode using a Height Map generating levelled GCode
        self.autolevel_button = FCButton(_('Levelling'), bold=True)
        self.autolevel_button.setIcon(QtGui.QIcon(self.app.resource_location + '/level32.png'))
        self.autolevel_button.setToolTip(
            _("Generate CNC Code with auto-levelled paths.")
        )
        self.custom_box.addWidget(self.autolevel_button)
        # self.autolevel_button.setDisabled(True)
        # self.autolevel_button.setToolTip("DISABLED. Work in progress!")

        # #############################################################################################################
        # ## Export G-Code ##
        # #############################################################################################################
        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.custom_box.addWidget(separator_line)

        g_export_lay = QtWidgets.QHBoxLayout()
        self.custom_box.addLayout(g_export_lay)

        # Save Button
        self.export_gcode_button = FCButton(_('Save'))
        self.export_gcode_button.setIcon(QtGui.QIcon(self.app.resource_location + '/save_as.png'))
        self.export_gcode_button.setToolTip(
            _("Opens dialog to save CNC Code file.")
        )
        self.export_gcode_button.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding,
                                               QtWidgets.QSizePolicy.Policy.Minimum)
        g_export_lay.addWidget(self.export_gcode_button)

        self.review_gcode_button = QtWidgets.QToolButton()
        self.review_gcode_button.setToolTip(_("Review CNC Code."))
        self.review_gcode_button.setIcon(QtGui.QIcon(self.app.resource_location + '/find32.png'))
        g_export_lay.addWidget(self.review_gcode_button)

        self.custom_box.addStretch(1)

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
            theme = 'light'

        if theme == 'light':
            self.resource_loc = 'assets/resources'
        else:
            self.resource_loc = 'assets/resources/dark_resources'

        ObjectUI.__init__(self, title=_('Script Object'),
                          icon_file=self.resource_loc + '/script_new24.png',
                          parent=parent,
                          common=False,
                          app=self.app)

        # ## Object name
        self.name_hlay = QtWidgets.QHBoxLayout()
        self.custom_box.addLayout(self.name_hlay)

        name_label = FCLabel('%s:' % _("Name"), bold=True)
        self.name_entry = FCEntry()
        self.name_entry.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.name_hlay.addWidget(name_label)
        self.name_hlay.addWidget(self.name_entry)

        h_lay = QtWidgets.QHBoxLayout()
        h_lay.setAlignment(QtCore.Qt.AlignmentFlag.AlignVCenter)
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
        self.plot_cb.setLayoutDirection(QtCore.Qt.LayoutDirection.RightToLeft)
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
            theme = 'light'

        if theme == 'light':
            self.resource_loc = 'assets/resources'
        else:
            self.resource_loc = 'assets/resources/dark_resources'

        ObjectUI.__init__(self, title=_('Document Object'),
                          icon_file=self.resource_loc + '/notes16_1.png',
                          parent=parent,
                          common=False,
                          app=self.app)

        # ## Object name
        self.name_hlay = QtWidgets.QHBoxLayout()
        self.custom_box.addLayout(self.name_hlay)

        name_label = FCLabel('%s:' % _("Name"), bold=True)
        self.name_entry = FCEntry()
        self.name_entry.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.name_hlay.addWidget(name_label)
        self.name_hlay.addWidget(self.name_entry)

        # Plot CB - this is added only for compatibility; other FlatCAM objects expect it and the mechanism is already
        # established and I don't want to changed it right now
        self.plot_cb = FCCheckBox()
        self.plot_cb.setLayoutDirection(QtCore.Qt.LayoutDirection.RightToLeft)
        self.custom_box.addWidget(self.plot_cb)
        self.plot_cb.hide()

        h_lay = QtWidgets.QHBoxLayout()
        h_lay.setAlignment(QtCore.Qt.AlignmentFlag.AlignVCenter)
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
        # ############ Grid LAYOUT #####################################
        # ##############################################################

        self.grid0 = GLay(v_spacing=5, h_spacing=3, c_stretch=[0, 1, 0])
        self.custom_box.addLayout(self.grid0)

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

        self.grid0.addWidget(self.font_type_label, 0, 0)
        self.grid0.addWidget(self.font_type_cb, 0, 1)

        # Font Size
        self.font_size_label = FCLabel('%s:' % _("Font Size"))

        size_hlay = QtWidgets.QHBoxLayout()

        self.font_size_cb = FCComboBox()
        self.font_size_cb.setEditable(True)
        self.font_size_cb.setMinimumContentsLength(3)
        # self.font_size_cb.setMaximumWidth(70)

        font_sizes = ['6', '7', '8', '9', '10', '11', '12', '13', '14',
                      '15', '16', '18', '20', '22', '24', '26', '28',
                      '32', '36', '40', '44', '48', '54', '60', '66',
                      '72', '80', '88', '96']

        self.font_size_cb.addItems(font_sizes)

        size_hlay.addWidget(self.font_size_cb)

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

        self.grid0.addWidget(self.font_size_label, 2, 0)
        self.grid0.addLayout(size_hlay, 2, 1)

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

        al_hlay.addStretch()

        self.grid0.addWidget(self.alignment_label, 4, 0)
        self.grid0.addLayout(al_hlay, 4, 1)

        # Font Color
        self.font_color_label = FCLabel('%s:' % _('Font Color'))
        self.font_color_label.setToolTip(
           _("Set the font color for the selected text")
        )

        self.grid0_child_1 = QtWidgets.QHBoxLayout()

        self.font_color_entry = FCEntry()
        self.font_color_button = FCButton()
        self.font_color_button.setFixedSize(15, 15)

        self.grid0_child_1.addWidget(self.font_color_entry)
        self.grid0_child_1.addWidget(self.font_color_button)
        self.grid0_child_1.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)

        self.grid0.addWidget(self.font_color_label, 6, 0)
        self.grid0.addLayout(self.grid0_child_1, 6, 1)

        # Selection Color
        self.sel_color_label = FCLabel('%s:' % _('Selection Color'))
        self.sel_color_label.setToolTip(
           _("Set the selection color when doing text selection.")
        )

        self.grid0_child_2 = QtWidgets.QHBoxLayout()

        self.sel_color_entry = FCEntry()
        self.sel_color_button = FCButton()
        self.sel_color_button.setFixedSize(15, 15)

        self.grid0_child_2.addWidget(self.sel_color_entry)
        self.grid0_child_2.addWidget(self.sel_color_button)
        self.grid0_child_2.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)

        self.grid0.addWidget(self.sel_color_label, 8, 0)
        self.grid0.addLayout(self.grid0_child_2, 8, 1)

        # Tab size
        self.tab_size_label = FCLabel('%s:' % _('Tab Size'))
        self.tab_size_label.setToolTip(
            _("Set the tab size. In pixels. Default value is 80 pixels.")
        )
        self.tab_size_spinner = FCSpinner(callback=self.confirmation_message_int)
        self.tab_size_spinner.set_range(0, 1000)

        self.grid0.addWidget(self.tab_size_label, 10, 0)
        self.grid0.addWidget(self.tab_size_spinner, 10, 1)

        self.custom_box.addStretch(1)

# end of file
