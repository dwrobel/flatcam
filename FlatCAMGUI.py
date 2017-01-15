############################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# Author: Juan Pablo Caram (c)                             #
# Date: 2/5/2014                                           #
# MIT Licence                                              #
############################################################

from PyQt4 import QtGui, QtCore, Qt
from GUIElements import *

# For the translation by Daniel Sallin Debut
# Use translate_("txt") for translate the "txt" string
# Using gettext for translate 
# Using os for def a locale path
# Using unidecode for accents compatibility
# coding: utf8
import gettext
import os
import sys
from unidecode import unidecode
pathname = os.path.dirname(sys.argv[0])
localdir = os.path.abspath(pathname) + "/locale"
gettext.install("messages", localdir)
def translate_(txt):
    return unicode(_(txt),'utf-8')
# For the translation by Daniel Sallin fin

class FlatCAMGUI(QtGui.QMainWindow):

    # Emitted when persistent window geometry needs to be retained
    geom_update = QtCore.pyqtSignal(int, int, int, int, name='geomUpdate')

    def __init__(self, version, name=None):
        super(FlatCAMGUI, self).__init__()

        # Divine icon pack by Ipapun @ finicons.com

        ############
        ### Menu ###
        ############
        self.menu = self.menuBar()

        ### File ###
        self.menufile = self.menu.addMenu(translate_('&File'))

        # New
        self.menufilenew = QtGui.QAction(QtGui.QIcon('share/file16.png'), translate_('&New'), self)
        self.menufile.addAction(self.menufilenew)
        # Open recent

        # Recent
        self.recent = self.menufile.addMenu(QtGui.QIcon('share/folder16.png'), translate_("Open recent ..."))

        # Open gerber ...
        self.menufileopengerber = QtGui.QAction(QtGui.QIcon('share/folder16.png'), translate_('Open &Gerber ...'), self)
        self.menufile.addAction(self.menufileopengerber)

        # Open Excellon ...
        self.menufileopenexcellon = QtGui.QAction(QtGui.QIcon('share/folder16.png'), translate_('Open &Excellon ...'), self)
        self.menufile.addAction(self.menufileopenexcellon)

        # Open G-Code ...
        self.menufileopengcode = QtGui.QAction(QtGui.QIcon('share/folder16.png'), translate_('Open G-&Code ...'), self)
        self.menufile.addAction(self.menufileopengcode)

        # Open Project ...
        self.menufileopenproject = QtGui.QAction(QtGui.QIcon('share/folder16.png'), translate_('Open &Project ...'), self)
        self.menufile.addAction(self.menufileopenproject)

        # Import SVG ...
        self.menufileimportsvg = QtGui.QAction(QtGui.QIcon('share/folder16.png'), translate_('Import &SVG ...'), self)
        self.menufile.addAction(self.menufileimportsvg)

        # Export SVG ...
        self.menufileexportsvg = QtGui.QAction(QtGui.QIcon('share/folder16.png'), translate_('Export &SVG ...'), self)
        self.menufile.addAction(self.menufileexportsvg)

        # Save Project
        self.menufilesaveproject = QtGui.QAction(QtGui.QIcon('share/floppy16.png'), translate_('&Save Project'), self)
        self.menufile.addAction(self.menufilesaveproject)

        # Save Project As ...
        self.menufilesaveprojectas = QtGui.QAction(QtGui.QIcon('share/floppy16.png'), translate_('Save Project &As ...'), self)
        self.menufile.addAction(self.menufilesaveprojectas)

        # Save Project Copy ...
        self.menufilesaveprojectcopy = QtGui.QAction(QtGui.QIcon('share/floppy16.png'), translate_('Save Project C&opy ...'), self)
        self.menufile.addAction(self.menufilesaveprojectcopy)

        # Save Defaults
        self.menufilesavedefaults = QtGui.QAction(QtGui.QIcon('share/floppy16.png'), translate_('Save &Defaults'), self)
        self.menufile.addAction(self.menufilesavedefaults)

        # Quit
        self.exit_action = QtGui.QAction(QtGui.QIcon('share/power16.png'), translate_('&Exit'), self)
        # exitAction.setShortcut('Ctrl+Q')
        # exitAction.setStatusTip('Exit application')
        #self.exit_action.triggered.connect(QtGui.qApp.quit)

        self.menufile.addAction(self.exit_action)

        ### Edit ###
        self.menuedit = self.menu.addMenu(translate_('&Edit'))
        self.menueditnew = self.menuedit.addAction(QtGui.QIcon('share/new_geo16.png'), translate_('New Geometry'))
        self.menueditedit = self.menuedit.addAction(QtGui.QIcon('share/edit16.png'), translate_('Edit Geometry'))
        self.menueditok = self.menuedit.addAction(QtGui.QIcon('share/edit_ok16.png'), translate_('Update Geometry'))
        #self.menueditok.
        #self.menueditcancel = self.menuedit.addAction(QtGui.QIcon('share/cancel_edit16.png'), "Cancel Edit")
        self.menueditjoin = self.menuedit.addAction(QtGui.QIcon('share/join16.png'), translate_('Join Geometry'))
        self.menueditdelete = self.menuedit.addAction(QtGui.QIcon('share/trash16.png'), translate_('Delete'))

        ### Options ###
        self.menuoptions = self.menu.addMenu(translate_('&Options'))
        self.menuoptions_transfer = self.menuoptions.addMenu(translate_('Transfer options'))
        self.menuoptions_transfer_a2p = self.menuoptions_transfer.addAction(translate_("Application to Project"))
        self.menuoptions_transfer_p2a = self.menuoptions_transfer.addAction(translate_("Project to Application"))
        self.menuoptions_transfer_p2o = self.menuoptions_transfer.addAction(translate_("Project to Object"))
        self.menuoptions_transfer_o2p = self.menuoptions_transfer.addAction(translate_("Object to Project"))
        self.menuoptions_transfer_a2o = self.menuoptions_transfer.addAction(translate_("Application to Object"))
        self.menuoptions_transfer_o2a = self.menuoptions_transfer.addAction(translate_("Object to Application"))
        self.menuoptions_language = self.menuoptions.addMenu(translate_('Language'))
        self.menuoptions_language_en = self.menuoptions_language.addAction(translate_("English"))
        self.menuoptions_language_fr = self.menuoptions_language.addAction(translate_("Francais"))
        self.menuoptions_language_ru = self.menuoptions_language.addAction(translate_("Russian"))

        ### View ###
        self.menuview = self.menu.addMenu(translate_('&View'))
        self.menuviewdisableall = self.menuview.addAction(QtGui.QIcon('share/clear_plot16.png'), translate_('Disable all plots'))
        self.menuviewdisableother = self.menuview.addAction(QtGui.QIcon('share/clear_plot16.png'),
                                                            translate_('Disable all plots but this one'))
        self.menuviewenable = self.menuview.addAction(QtGui.QIcon('share/replot16.png'), translate_('Enable all plots'))

        ### Tool ###
        #self.menutool = self.menu.addMenu('&Tool')
        self.menutool = QtGui.QMenu(translate_('&Tool'))
        self.menutoolaction = self.menu.addMenu(self.menutool)
        self.menutoolshell = self.menutool.addAction(QtGui.QIcon('share/shell16.png'), translate_('&Command Line'))

        ### Help ###
        self.menuhelp = self.menu.addMenu(translate_('&Help'))
        self.menuhelp_about = self.menuhelp.addAction(QtGui.QIcon('share/tv16.png'), translate_('About FlatCAM'))
        self.menuhelp_home = self.menuhelp.addAction(QtGui.QIcon('share/home16.png'), translate_('Home'))
        self.menuhelp_manual = self.menuhelp.addAction(QtGui.QIcon('share/globe16.png'), translate_('Manual'))

        ###############
        ### Toolbar ###
        ###############
        self.toolbar = QtGui.QToolBar()
        self.addToolBar(self.toolbar)

        self.zoom_fit_btn = self.toolbar.addAction(QtGui.QIcon('share/zoom_fit32.png'), translate_("&Zoom Fit"))
        self.zoom_out_btn = self.toolbar.addAction(QtGui.QIcon('share/zoom_out32.png'), translate_("&Zoom Out"))
        self.zoom_in_btn = self.toolbar.addAction(QtGui.QIcon('share/zoom_in32.png'), translate_("&Zoom In"))
        self.clear_plot_btn = self.toolbar.addAction(QtGui.QIcon('share/clear_plot32.png'), translate_("&Clear Plot"))
        self.replot_btn = self.toolbar.addAction(QtGui.QIcon('share/replot32.png'), translate_("&Replot"))
        self.newgeo_btn = self.toolbar.addAction(QtGui.QIcon('share/new_geo32.png'), translate_("New Blank Geometry"))
        self.editgeo_btn = self.toolbar.addAction(QtGui.QIcon('share/edit32.png'), translate_("Edit Geometry"))
        self.updategeo_btn = self.toolbar.addAction(QtGui.QIcon('share/edit_ok32.png'), translate_("Update Geometry"))
        self.updategeo_btn.setEnabled(False)
        #self.canceledit_btn = self.toolbar.addAction(QtGui.QIcon('share/cancel_edit32.png'), "Cancel Edit")
        self.delete_btn = self.toolbar.addAction(QtGui.QIcon('share/delete32.png'), translate_("&Delete"))
        self.shell_btn = self.toolbar.addAction(QtGui.QIcon('share/shell32.png'), translate_("&Command Line"))

        ################
        ### Splitter ###
        ################
        self.splitter = QtGui.QSplitter()
        self.setCentralWidget(self.splitter)

        ################
        ### Notebook ###
        ################
        self.notebook = QtGui.QTabWidget()
        # self.notebook.setMinimumWidth(250)

        ### Projet ###
        project_tab = QtGui.QWidget()
        project_tab.setMinimumWidth(250)  # Hack
        self.project_tab_layout = QtGui.QVBoxLayout(project_tab)
        self.project_tab_layout.setContentsMargins(2, 2, 2, 2)
        self.notebook.addTab(project_tab, translate_("Project"))

        ### Selected ###
        self.selected_tab = QtGui.QWidget()
        self.selected_tab_layout = QtGui.QVBoxLayout(self.selected_tab)
        self.selected_tab_layout.setContentsMargins(2, 2, 2, 2)
        self.selected_scroll_area = VerticalScrollArea()
        self.selected_tab_layout.addWidget(self.selected_scroll_area)
        self.notebook.addTab(self.selected_tab, translate_("Selected"))

        ### Options ###
        self.options_tab = QtGui.QWidget()
        self.options_tab.setContentsMargins(0, 0, 0, 0)
        self.options_tab_layout = QtGui.QVBoxLayout(self.options_tab)
        self.options_tab_layout.setContentsMargins(2, 2, 2, 2)

        hlay1 = QtGui.QHBoxLayout()
        self.options_tab_layout.addLayout(hlay1)

        self.icon = QtGui.QLabel()
        self.icon.setPixmap(QtGui.QPixmap('share/gear48.png'))
        hlay1.addWidget(self.icon)

        self.options_combo = QtGui.QComboBox()
        self.options_combo.addItem(translate_("APPLICATION DEFAULTS"))
        self.options_combo.addItem(translate_("PROJECT OPTIONS"))
        hlay1.addWidget(self.options_combo)
        hlay1.addStretch()

        self.options_scroll_area = VerticalScrollArea()
        self.options_tab_layout.addWidget(self.options_scroll_area)

        self.notebook.addTab(self.options_tab, translate_("Options"))

        ### Tool ###
        self.tool_tab = QtGui.QWidget()
        self.tool_tab_layout = QtGui.QVBoxLayout(self.tool_tab)
        self.tool_tab_layout.setContentsMargins(2, 2, 2, 2)
        self.notebook.addTab(self.tool_tab, translate_("Tool"))
        self.tool_scroll_area = VerticalScrollArea()
        self.tool_tab_layout.addWidget(self.tool_scroll_area)

        self.splitter.addWidget(self.notebook)

        ######################
        ### Plot and other ###
        ######################
        right_widget = QtGui.QWidget()
        # right_widget.setContentsMargins(0, 0, 0, 0)
        self.splitter.addWidget(right_widget)
        self.right_layout = QtGui.QVBoxLayout()
        self.right_layout.setMargin(0)
        # self.right_layout.setContentsMargins(0, 0, 0, 0)
        right_widget.setLayout(self.right_layout)

        ################
        ### Info bar ###
        ################
        infobar = self.statusBar()

        #self.info_label = QtGui.QLabel("Welcome to FlatCAM.")
        #self.info_label.setFrameStyle(QtGui.QFrame.StyledPanel | QtGui.QFrame.Plain)
        #infobar.addWidget(self.info_label, stretch=1)
        self.fcinfo = FlatCAMInfoBar()
        infobar.addWidget(self.fcinfo, stretch=1)

        self.position_label = QtGui.QLabel("")
        #self.position_label.setFrameStyle(QtGui.QFrame.StyledPanel | QtGui.QFrame.Plain)
        self.position_label.setMinimumWidth(110)
        infobar.addWidget(self.position_label)

        self.units_label = QtGui.QLabel("[in]")
        # self.units_label.setFrameStyle(QtGui.QFrame.StyledPanel | QtGui.QFrame.Plain)
        self.units_label.setMargin(2)
        infobar.addWidget(self.units_label)

        self.progress_bar = QtGui.QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        #infobar.addWidget(self.progress_bar)

        self.activity_view = FlatCAMActivityView()
        infobar.addWidget(self.activity_view)

        #############
        ### Icons ###
        #############
        self.app_icon = QtGui.QIcon()
        self.app_icon.addFile('share/flatcam_icon16.png', QtCore.QSize(16, 16))
        self.app_icon.addFile('share/flatcam_icon24.png', QtCore.QSize(24, 24))
        self.app_icon.addFile('share/flatcam_icon32.png', QtCore.QSize(32, 32))
        self.app_icon.addFile('share/flatcam_icon48.png', QtCore.QSize(48, 48))
        self.app_icon.addFile('share/flatcam_icon128.png', QtCore.QSize(128, 128))
        self.app_icon.addFile('share/flatcam_icon256.png', QtCore.QSize(256, 256))
        self.setWindowIcon(self.app_icon)

        self.setGeometry(100, 100, 1024, 650)
        title = 'FlatCAM {}'.format(version)
        if name is not None:
            title += ' - {}'.format(name)
        self.setWindowTitle(title)
        self.show()

    def closeEvent(self, event):
        grect = self.geometry()
        self.geom_update.emit(grect.x(), grect.y(), grect.width(), grect.height())
        QtGui.qApp.quit()

class FlatCAMActivityView(QtGui.QWidget):

    def __init__(self, parent=None):
        super(FlatCAMActivityView, self).__init__(parent=parent)

        self.setMinimumWidth(200)

        self.icon = QtGui.QLabel(self)
        self.icon.setGeometry(0, 0, 12, 12)
        self.movie = QtGui.QMovie("share/active.gif")
        self.icon.setMovie(self.movie)
        #self.movie.start()

        layout = QtGui.QHBoxLayout()
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setAlignment(QtCore.Qt.AlignLeft)
        self.setLayout(layout)

        layout.addWidget(self.icon)
        self.text = QtGui.QLabel(self)
        self.text.setText(translate_("Idle."))

        layout.addWidget(self.text)

    def set_idle(self):
        self.movie.stop()
        self.text.setText(translate_("Idle."))

    def set_busy(self, msg):
        self.movie.start()
        self.text.setText(msg)


class FlatCAMInfoBar(QtGui.QWidget):

    def __init__(self, parent=None):
        super(FlatCAMInfoBar, self).__init__(parent=parent)

        self.icon = QtGui.QLabel(self)
        self.icon.setGeometry(0, 0, 12, 12)
        self.pmap = QtGui.QPixmap('share/graylight12.png')
        self.icon.setPixmap(self.pmap)

        layout = QtGui.QHBoxLayout()
        layout.setContentsMargins(5, 0, 5, 0)
        self.setLayout(layout)

        layout.addWidget(self.icon)

        self.text = QtGui.QLabel(self)
        self.text.setText(translate_("Hello!"))
        self.text.setToolTip(translate_("Hello!"))

        layout.addWidget(self.text)

        layout.addStretch()

    def set_text_(self, text):
        self.text.setText(text)
        self.text.setToolTip(text)

    def set_status(self, text, level="info"):
        level = str(level)
        self.pmap.fill()
        if level == "error":
            self.pmap = QtGui.QPixmap('share/redlight12.png')
        elif level == "success":
            self.pmap = QtGui.QPixmap('share/greenlight12.png')
        elif level == "warning":
            self.pmap = QtGui.QPixmap('share/yellowlight12.png')
        else:
            self.pmap = QtGui.QPixmap('share/graylight12.png')

        self.icon.setPixmap(self.pmap)
        self.set_text_(text)


class OptionsGroupUI(QtGui.QGroupBox):
    def __init__(self, title, parent=None):
        QtGui.QGroupBox.__init__(self, title, parent=parent)
        self.setStyleSheet("""
        QGroupBox
        {
            font-size: 16px;
            font-weight: bold;
        }
        """)

        self.layout = QtGui.QVBoxLayout()
        self.setLayout(self.layout)


class GerberOptionsGroupUI(OptionsGroupUI):
    def __init__(self, parent=None):
        OptionsGroupUI.__init__(self, translate_("Gerber Options"), parent=parent)

        ## Plot options
        self.plot_options_label = QtGui.QLabel(translate_("<b>Plot Options:</b>"))
        self.layout.addWidget(self.plot_options_label)

        grid0 = QtGui.QGridLayout()
        self.layout.addLayout(grid0)
        # Plot CB
        self.plot_cb = FCCheckBox(label=translate_('Plot'))
        self.plot_options_label.setToolTip(translate_(
            "Plot (show) this object."
        ))
        grid0.addWidget(self.plot_cb, 0, 0)

        # Solid CB
        self.solid_cb = FCCheckBox(label=translate_('Solid'))
        self.solid_cb.setToolTip(translate_(
            "Solid color polygons."
        ))
        grid0.addWidget(self.solid_cb, 0, 1)

        # Multicolored CB
        self.multicolored_cb = FCCheckBox(label=translate_('Multicolored'))
        self.multicolored_cb.setToolTip(translate_(
            "Draw polygons in different colors."
        ))
        grid0.addWidget(self.multicolored_cb, 0, 2)

        ## Isolation Routing
        self.isolation_routing_label = QtGui.QLabel(translate_("<b>Isolation Routing:</b>"))
        self.isolation_routing_label.setToolTip(translate_(
            "Create a Geometry object with\n"
            "toolpaths to cut outside polygons."
        ))
        self.layout.addWidget(self.isolation_routing_label)

        grid1 = QtGui.QGridLayout()
        self.layout.addLayout(grid1)
        tdlabel = QtGui.QLabel(translate_('Tool dia:'))
        tdlabel.setToolTip(translate_(
            "Diameter of the cutting tool."
        ))
        grid1.addWidget(tdlabel, 0, 0)
        self.iso_tool_dia_entry = LengthEntry()
        grid1.addWidget(self.iso_tool_dia_entry, 0, 1)

        passlabel = QtGui.QLabel(translate_('Width (# passes):'))
        passlabel.setToolTip(translate_(
            "Width of the isolation gap in\n"
            "number (integer) of tool widths."
        ))
        grid1.addWidget(passlabel, 1, 0)
        self.iso_width_entry = IntEntry()
        grid1.addWidget(self.iso_width_entry, 1, 1)

        overlabel = QtGui.QLabel(translate_('Pass overlap:'))
        overlabel.setToolTip(translate_(
            "How much (fraction of tool width)\n"
            "to overlap each pass."
        ))
        grid1.addWidget(overlabel, 2, 0)
        self.iso_overlap_entry = FloatEntry()
        grid1.addWidget(self.iso_overlap_entry, 2, 1)
        
        self.combine_passes_cb = FCCheckBox(label=translate_('Combine Passes'))
        self.combine_passes_cb.setToolTip(translate_(
            "Combine all passes into one object"
        ))
        grid1.addWidget(self.combine_passes_cb, 3, 0)

        ## Board cuttout
        self.board_cutout_label = QtGui.QLabel(translate_("<b>Board cutout:</b>"))
        self.board_cutout_label.setToolTip(translate_(
            "Create toolpaths to cut around\n"
            "the PCB and separate it from\n"
            "the original board."
        ))
        self.layout.addWidget(self.board_cutout_label)

        grid2 = QtGui.QGridLayout()
        self.layout.addLayout(grid2)
        tdclabel = QtGui.QLabel(translate_('Tool dia:'))
        tdclabel.setToolTip(translate_(
            "Diameter of the cutting tool."
        ))
        grid2.addWidget(tdclabel, 0, 0)
        self.cutout_tooldia_entry = LengthEntry()
        grid2.addWidget(self.cutout_tooldia_entry, 0, 1)

        marginlabel = QtGui.QLabel(translate_('Margin:'))
        marginlabel.setToolTip(translate_(
            "Distance from objects at which\n"
            "to draw the cutout."
        ))
        grid2.addWidget(marginlabel, 1, 0)
        self.cutout_margin_entry = LengthEntry()
        grid2.addWidget(self.cutout_margin_entry, 1, 1)

        gaplabel = QtGui.QLabel(translate_('Gap size:'))
        gaplabel.setToolTip(translate_(
            "Size of the gaps in the toolpath\n"
            "that will remain to hold the\n"
            "board in place."
        ))
        grid2.addWidget(gaplabel, 2, 0)
        self.cutout_gap_entry = LengthEntry()
        grid2.addWidget(self.cutout_gap_entry, 2, 1)

        gapslabel = QtGui.QLabel(translate_('Gaps:'))
        gapslabel.setToolTip(translate_(
            "Where to place the gaps, Top/Bottom\n"
            "Left/Rigt, or on all 4 sides."
        ))
        grid2.addWidget(gapslabel, 3, 0)
        self.gaps_radio = RadioSet([{'label': translate_('2 (T/B)'), 'value': 'tb'},
                                    {'label': translate_('2 (L/R)'), 'value': 'lr'},
                                    {'label': '4', 'value': '4'}])
        grid2.addWidget(self.gaps_radio, 3, 1)

        ## Non-copper regions
        self.noncopper_label = QtGui.QLabel(translate_("<b>Non-copper regions:</b>"))
        self.noncopper_label.setToolTip(translate_(
            "Create polygons covering the\n"
            "areas without copper on the PCB.\n"
            "Equivalent to the inverse of this\n"
            "object. Can be used to remove all\n"
            "copper from a specified region."
        ))
        self.layout.addWidget(self.noncopper_label)

        grid3 = QtGui.QGridLayout()
        self.layout.addLayout(grid3)

        # Margin
        bmlabel = QtGui.QLabel(translate_('Boundary Margin:'))
        bmlabel.setToolTip(translate_(
            "Specify the edge of the PCB\n"
            "by drawing a box around all\n"
            "objects with this minimum\n"
            "distance."
        ))
        grid3.addWidget(bmlabel, 0, 0)
        self.noncopper_margin_entry = LengthEntry()
        grid3.addWidget(self.noncopper_margin_entry, 0, 1)

        # Rounded corners
        self.noncopper_rounded_cb = FCCheckBox(label=translate_("Rounded corners"))
        self.noncopper_rounded_cb.setToolTip(translate_(
            "Creates a Geometry objects with polygons\n"
            "covering the copper-free areas of the PCB."
        ))
        grid3.addWidget(self.noncopper_rounded_cb, 1, 0, 1, 2)

        ## Bounding box
        self.boundingbox_label = QtGui.QLabel(translate_('<b>Bounding Box:</b>'))
        self.layout.addWidget(self.boundingbox_label)

        grid4 = QtGui.QGridLayout()
        self.layout.addLayout(grid4)

        bbmargin = QtGui.QLabel(translate_('Boundary Margin:'))
        bbmargin.setToolTip(translate_(
            "Distance of the edges of the box\n"
            "to the nearest polygon."
        ))
        grid4.addWidget(bbmargin, 0, 0)
        self.bbmargin_entry = LengthEntry()
        grid4.addWidget(self.bbmargin_entry, 0, 1)

        self.bbrounded_cb = FCCheckBox(label=translate_("Rounded corners"))
        self.bbrounded_cb.setToolTip(translate_(
            "If the bounding box is \n"
            "to have rounded corners\n"
            "their radius is equal to\n"
            "the margin."
        ))
        grid4.addWidget(self.bbrounded_cb, 1, 0, 1, 2)


class ExcellonOptionsGroupUI(OptionsGroupUI):
    def __init__(self, parent=None):
        OptionsGroupUI.__init__(self, translate_("Excellon Options"), parent=parent)

        ## Plot options
        self.plot_options_label = QtGui.QLabel(translate_("<b>Plot Options:</b>"))
        self.layout.addWidget(self.plot_options_label)

        grid0 = QtGui.QGridLayout()
        self.layout.addLayout(grid0)
        self.plot_cb = FCCheckBox(label=translate_('Plot'))
        self.plot_cb.setToolTip(translate_(
            "Plot (show) this object."
        ))
        grid0.addWidget(self.plot_cb, 0, 0)
        self.solid_cb = FCCheckBox(label=translate_('Solid'))
        self.solid_cb.setToolTip(translate_(
            "Solid circles."
        ))
        grid0.addWidget(self.solid_cb, 0, 1)

        ## Create CNC Job
        self.cncjob_label = QtGui.QLabel(translate_('<b>Create CNC Job</b>'))
        self.cncjob_label.setToolTip(translate_(
            "Create a CNC Job object\n"
            "for this drill object."
        ))
        self.layout.addWidget(self.cncjob_label)

        grid1 = QtGui.QGridLayout()
        self.layout.addLayout(grid1)

        cutzlabel = QtGui.QLabel(translate_('Cut Z:'))
        cutzlabel.setToolTip(translate_(
            "Drill depth (negative)\n"
            "below the copper surface."
        ))
        grid1.addWidget(cutzlabel, 0, 0)
        self.cutz_entry = LengthEntry()
        grid1.addWidget(self.cutz_entry, 0, 1)

        travelzlabel = QtGui.QLabel(translate_('Travel Z:'))
        travelzlabel.setToolTip(translate_(
            "Tool height when travelling\n"
            "across the XY plane."
        ))
        grid1.addWidget(travelzlabel, 1, 0)
        self.travelz_entry = LengthEntry()
        grid1.addWidget(self.travelz_entry, 1, 1)

        frlabel = QtGui.QLabel(translate_('Feed rate:'))
        frlabel.setToolTip(translate_(
            "Tool speed while drilling\n"
            "(in units per minute)."
        ))
        grid1.addWidget(frlabel, 2, 0)
        self.feedrate_entry = LengthEntry()
        grid1.addWidget(self.feedrate_entry, 2, 1)

        toolchangezlabel = QtGui.QLabel(translate_('Toolchange Z:'))
        toolchangezlabel.setToolTip(translate_(
            "Tool Z where user can change drill bit\n"
        ))
        grid1.addWidget(toolchangezlabel, 3, 0)
        self.toolchangez_entry = LengthEntry()
        grid1.addWidget(self.toolchangez_entry, 3, 1)

        spdlabel = QtGui.QLabel(translate_('Spindle speed:'))
        spdlabel.setToolTip(translate_(
            "Speed of the spindle\n"
            "in RPM (optional)"
        ))
        grid1.addWidget(spdlabel, 4, 0)
        self.spindlespeed_entry = IntEntry(allow_empty=True)
        grid1.addWidget(self.spindlespeed_entry, 4, 1)

        #### Milling Holes ####
        self.mill_hole_label = QtGui.QLabel(translate_('<b>Mill Holes</b>'))
        self.mill_hole_label.setToolTip(translate_(
            "Create Geometry for milling holes."
        ))
        self.layout.addWidget(self.mill_hole_label)

        grid1 = QtGui.QGridLayout()
        self.layout.addLayout(grid1)
        tdlabel = QtGui.QLabel(translate_('Tool dia:'))
        tdlabel.setToolTip(translate_(
            "Diameter of the cutting tool."
        ))
        grid1.addWidget(tdlabel, 0, 0)
        self.tooldia_entry = LengthEntry()
        grid1.addWidget(self.tooldia_entry, 0, 1)


class GeometryOptionsGroupUI(OptionsGroupUI):
    def __init__(self, parent=None):
        OptionsGroupUI.__init__(self, translate_("Geometry Options"), parent=parent)

        ## Plot options
        self.plot_options_label = QtGui.QLabel(translate_("<b>Plot Options:</b>"))
        self.layout.addWidget(self.plot_options_label)

        # Plot CB
        self.plot_cb = FCCheckBox(label=translate_('Plot'))
        self.plot_cb.setToolTip(translate_(
            "Plot (show) this object."
        ))
        self.layout.addWidget(self.plot_cb)

        # ------------------------------
        ## Create CNC Job
        # ------------------------------
        self.cncjob_label = QtGui.QLabel(translate_('<b>Create CNC Job:</b>'))
        self.cncjob_label.setToolTip(translate_(
            "Create a CNC Job object\n"
            "tracing the contours of this\n"
            "Geometry object."
        ))
        self.layout.addWidget(self.cncjob_label)

        grid1 = QtGui.QGridLayout()
        self.layout.addLayout(grid1)

        cutzlabel = QtGui.QLabel(translate_('Cut Z:'))
        cutzlabel.setToolTip(translate_(
            "Cutting depth (negative)\n"
            "below the copper surface."
        ))
        grid1.addWidget(cutzlabel, 0, 0)
        self.cutz_entry = LengthEntry()
        grid1.addWidget(self.cutz_entry, 0, 1)

        # Travel Z
        travelzlabel = QtGui.QLabel(translate_('Travel Z:'))
        travelzlabel.setToolTip(translate_(
            "Height of the tool when\n"
            "moving without cutting."
        ))
        grid1.addWidget(travelzlabel, 1, 0)
        self.travelz_entry = LengthEntry()
        grid1.addWidget(self.travelz_entry, 1, 1)

        # Feedrate
        frlabel = QtGui.QLabel(translate_('Feed Rate:'))
        frlabel.setToolTip(translate_(
            "Cutting speed in the XY\n"
            "plane in units per minute"
        ))
        grid1.addWidget(frlabel, 2, 0)
        self.cncfeedrate_entry = LengthEntry()
        grid1.addWidget(self.cncfeedrate_entry, 2, 1)

        # Tooldia
        tdlabel = QtGui.QLabel(translate_('Tool dia:'))
        tdlabel.setToolTip(translate_(
            "The diameter of the cutting\n"
            "tool (just for display)."
        ))
        grid1.addWidget(tdlabel, 3, 0)
        self.cnctooldia_entry = LengthEntry()
        grid1.addWidget(self.cnctooldia_entry, 3, 1)

        spdlabel = QtGui.QLabel(translate_('Spindle speed:'))
        spdlabel.setToolTip(translate_(
            "Speed of the spindle\n"
            "in RPM (optional)"
        ))
        grid1.addWidget(spdlabel, 4, 0)
        self.cncspindlespeed_entry = IntEntry(allow_empty=True)
        grid1.addWidget(self.cncspindlespeed_entry, 4, 1)

        # ------------------------------
        ## Paint area
        # ------------------------------
        self.paint_label = QtGui.QLabel(translate_('<b>Paint Area:</b>'))
        self.paint_label.setToolTip(translate_(
            "Creates tool paths to cover the\n"
            "whole area of a polygon (remove\n"
            "all copper). You will be asked\n"
            "to click on the desired polygon."
        ))
        self.layout.addWidget(self.paint_label)

        grid2 = QtGui.QGridLayout()
        self.layout.addLayout(grid2)

        # Tool dia
        ptdlabel = QtGui.QLabel(translate_('Tool dia:'))
        ptdlabel.setToolTip(translate_(
            "Diameter of the tool to\n"
            "be used in the operation."
        ))
        grid2.addWidget(ptdlabel, 0, 0)

        self.painttooldia_entry = LengthEntry()
        grid2.addWidget(self.painttooldia_entry, 0, 1)

        # Overlap
        ovlabel = QtGui.QLabel(translate_('Overlap:'))
        ovlabel.setToolTip(translate_(
            "How much (fraction) of the tool\n"
            "width to overlap each tool pass."
        ))
        grid2.addWidget(ovlabel, 1, 0)
        self.paintoverlap_entry = LengthEntry()
        grid2.addWidget(self.paintoverlap_entry, 1, 1)

        # Margin
        marginlabel = QtGui.QLabel(translate_('Margin:'))
        marginlabel.setToolTip(translate_(
            "Distance by which to avoid\n"
            "the edges of the polygon to\n"
            "be painted."
        ))
        grid2.addWidget(marginlabel, 2, 0)
        self.paintmargin_entry = LengthEntry()
        grid2.addWidget(self.paintmargin_entry, 2, 1)

        # Method
        methodlabel = QtGui.QLabel(translate_('Method:'))
        methodlabel.setToolTip(translate_(
            "Algorithm to paint the polygon:<BR>"
            "<B>Standard</B>: Fixed step inwards.<BR>"
            "<B>Seed-based</B>: Outwards from seed."
        ))
        grid2.addWidget(methodlabel, 3, 0)
        self.paintmethod_combo = RadioSet([
            {"label": translate_("Standard"), "value": "standard"},
            {"label": translate_("Seed-based"), "value": "seed"},
            {"label": translate_("Straight lines"), "value": "lines"}
        ], orientation='vertical')
        grid2.addWidget(self.paintmethod_combo, 3, 1)

        # Connect lines
        pathconnectlabel = QtGui.QLabel(translate_("Connect:"))
        pathconnectlabel.setToolTip(translate_(
            "Draw lines between resulting\n"
            "segments to minimize tool lifts."
        ))
        grid2.addWidget(pathconnectlabel, 4, 0)
        self.pathconnect_cb = FCCheckBox()
        grid2.addWidget(self.pathconnect_cb, 4, 1)

        # Paint contour
        contourlabel = QtGui.QLabel(translate_("Contour:"))
        contourlabel.setToolTip(translate_(
            "Cut around the perimeter of the polygon\n"
            "to trim rough edges."
        ))
        grid2.addWidget(contourlabel, 5, 0)
        self.contour_cb = FCCheckBox()
        grid2.addWidget(self.contour_cb, 5, 1)

        # Polygon selection
        selectlabel = QtGui.QLabel(translate_('Selection:'))
        selectlabel.setToolTip(translate_(
            "How to select the polygons to paint."
        ))
        grid2.addWidget(selectlabel, 6, 0)
        # grid3 = QtGui.QGridLayout()
        self.selectmethod_combo = RadioSet([
            {"label": translate_("Single"), "value": "single"},
            {"label": translate_("All"), "value": "all"},
            # {"label": "Rectangle", "value": "rectangle"}
        ])
        grid2.addWidget(self.selectmethod_combo, 6, 1)


class CNCJobOptionsGroupUI(OptionsGroupUI):
    def __init__(self, parent=None):
        OptionsGroupUI.__init__(self, translate_("CNC Job Options"), parent=None)

        ## Plot options
        self.plot_options_label = QtGui.QLabel(translate_("<b>Plot Options:</b>"))
        self.layout.addWidget(self.plot_options_label)

        grid0 = QtGui.QGridLayout()
        self.layout.addLayout(grid0)

        # Plot CB
        # self.plot_cb = QtGui.QCheckBox('Plot')
        self.plot_cb = FCCheckBox(translate_('Plot'))
        self.plot_cb.setToolTip(translate_(
            "Plot (show) this object."
        ))
        grid0.addWidget(self.plot_cb, 0, 0)

        # Tool dia for plot
        tdlabel = QtGui.QLabel(translate_('Tool dia:'))
        tdlabel.setToolTip(translate_(
            "Diameter of the tool to be\n"
            "rendered in the plot."
        ))
        grid0.addWidget(tdlabel, 1, 0)
        self.tooldia_entry = LengthEntry()
        grid0.addWidget(self.tooldia_entry, 1, 1)

        ## Export G-Code
        self.export_gcode_label = QtGui.QLabel(translate_("<b>Export G-Code:</b>"))
        self.export_gcode_label.setToolTip(translate_(
            "Export and save G-Code to\n"
            "make this object to a file."
        ))
        self.layout.addWidget(self.export_gcode_label)

        # Prepend to G-Code
        prependlabel = QtGui.QLabel(translate_('Prepend to G-Code:'))
        prependlabel.setToolTip(translate_(
            "Type here any G-Code commands you would\n"
            "like to add at the beginning of the G-Code file."
        ))
        self.layout.addWidget(prependlabel)

        self.prepend_text = FCTextArea()
        self.layout.addWidget(self.prepend_text)

        # Append text to G-Code
        appendlabel = QtGui.QLabel(translate_('Append to G-Code:'))
        appendlabel.setToolTip(translate_(
            "Type here any G-Code commands you would\n"
            "like to append to the generated file.\n"
            "I.e.: M2 (End of program)"
        ))
        self.layout.addWidget(appendlabel)

        self.append_text = FCTextArea()
        self.layout.addWidget(self.append_text)

        # Dwell
        grid1 = QtGui.QGridLayout()
        self.layout.addLayout(grid1)

        dwelllabel = QtGui.QLabel(translate_('Dwell:'))
        dwelllabel.setToolTip(translate_(
            "Pause to allow the spindle to reach its\n"
            "speed before cutting."
        ))
        dwelltime = QtGui.QLabel(translate_('Duration [sec.]:'))
        dwelltime.setToolTip(translate_(
            "Number of second to dwell."
        ))
        self.dwell_cb = FCCheckBox()
        self.dwelltime_cb = FCEntry()
        grid1.addWidget(dwelllabel, 0, 0)
        grid1.addWidget(self.dwell_cb, 0, 1)
        grid1.addWidget(dwelltime, 1, 0)
        grid1.addWidget(self.dwelltime_cb, 1, 1)


class GlobalOptionsUI(QtGui.QWidget):
    """
    This is the app and project options editor.
    """
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent=parent)

        layout = QtGui.QVBoxLayout()
        self.setLayout(layout)

        hlay1 = QtGui.QHBoxLayout()
        layout.addLayout(hlay1)
        unitslabel = QtGui.QLabel(translate_('Units:'))
        hlay1.addWidget(unitslabel)
        self.units_radio = RadioSet([{'label': translate_('inch'), 'value': 'IN'},
                                     {'label': translate_('mm'), 'value': 'MM'}])
        hlay1.addWidget(self.units_radio)

        ####### Gerber #######
        # gerberlabel = QtGui.QLabel('<b>Gerber Options</b>')
        # layout.addWidget(gerberlabel)
        self.gerber_group = GerberOptionsGroupUI()
        # self.gerber_group.setFrameStyle(QtGui.QFrame.StyledPanel)
        layout.addWidget(self.gerber_group)

        ####### Excellon #######
        # excellonlabel = QtGui.QLabel('<b>Excellon Options</b>')
        # layout.addWidget(excellonlabel)
        self.excellon_group = ExcellonOptionsGroupUI()
        # self.excellon_group.setFrameStyle(QtGui.QFrame.StyledPanel)
        layout.addWidget(self.excellon_group)

        ####### Geometry #######
        # geometrylabel = QtGui.QLabel('<b>Geometry Options</b>')
        # layout.addWidget(geometrylabel)
        self.geometry_group = GeometryOptionsGroupUI()
        # self.geometry_group.setStyle(QtGui.QFrame.StyledPanel)
        layout.addWidget(self.geometry_group)

        ####### CNC #######
        # cnclabel = QtGui.QLabel('<b>CNC Job Options</b>')
        # layout.addWidget(cnclabel)
        self.cncjob_group = CNCJobOptionsGroupUI()
        # self.cncjob_group.setStyle(QtGui.QFrame.StyledPanel)
        layout.addWidget(self.cncjob_group)

# def main():
#
#     app = QtGui.QApplication(sys.argv)
#     fc = FlatCAMGUI()
#     sys.exit(app.exec_())
#
#
# if __name__ == '__main__':
#     main()
