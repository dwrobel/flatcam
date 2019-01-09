############################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# Author: Juan Pablo Caram (c)                             #
# Date: 2/5/2014                                           #
# MIT Licence                                              #
############################################################

from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtCore import Qt
from GUIElements import *
import platform

class FlatCAMGUI(QtWidgets.QMainWindow):
    # Emitted when persistent window geometry needs to be retained
    geom_update = QtCore.pyqtSignal(int, int, int, int, int, name='geomUpdate')
    final_save = QtCore.pyqtSignal(name='saveBeforeExit')

    def __init__(self, version, beta, app):
        super(FlatCAMGUI, self).__init__()

        self.app = app
        # Divine icon pack by Ipapun @ finicons.com

        #####################################
        ### BUILDING THE GUI IS DONE HERE ###
        #####################################

        ############
        ### Menu ###
        ############
        self.menu = self.menuBar()

        ### File ###
        self.menufile = self.menu.addMenu('&File')

        # New
        self.menufilenew = QtWidgets.QAction(QtGui.QIcon('share/file16.png'), '&New Project', self)
        self.menufile.addAction(self.menufilenew)

        self.menufile_open = self.menufile.addMenu(QtGui.QIcon('share/folder32_bis.png'), 'Open')
        # Open gerber ...
        self.menufileopengerber = QtWidgets.QAction(QtGui.QIcon('share/flatcam_icon24.png'), 'Open &Gerber ...', self)
        self.menufile_open.addAction(self.menufileopengerber)

        # Open gerber with follow...
        self.menufileopengerber_follow = QtWidgets.QAction(QtGui.QIcon('share/flatcam_icon24.png'),
                                                       'Open &Gerber (w/ Follow)', self)
        self.menufile_open.addAction(self.menufileopengerber_follow)
        self.menufile_open.addSeparator()

        # Open Excellon ...
        self.menufileopenexcellon = QtWidgets.QAction(QtGui.QIcon('share/open_excellon32.png'), 'Open &Excellon ...',
                                                  self)
        self.menufile_open.addAction(self.menufileopenexcellon)

        # Open G-Code ...
        self.menufileopengcode = QtWidgets.QAction(QtGui.QIcon('share/code.png'), 'Open G-&Code ...', self)
        self.menufile_open.addAction(self.menufileopengcode)

        # Open Project ...
        self.menufileopenproject = QtWidgets.QAction(QtGui.QIcon('share/folder16.png'), 'Open &Project ...', self)
        self.menufile_open.addAction(self.menufileopenproject)

        # Recent
        self.recent = self.menufile.addMenu(QtGui.QIcon('share/recent_files.png'), "Recent files")

        # Separator
        self.menufile.addSeparator()

        # Run Scripts
        self.menufilerunscript = QtWidgets.QAction(QtGui.QIcon('share/script16.png'), 'Run Script', self)
        self.menufile.addAction(self.menufilerunscript)

        # Separator
        self.menufile.addSeparator()

        # Import ...
        self.menufileimport = self.menufile.addMenu(QtGui.QIcon('share/import.png'), 'Import')
        self.menufileimportsvg = QtWidgets.QAction(QtGui.QIcon('share/svg16.png'),
                                               '&SVG as Geometry Object', self)
        self.menufileimport.addAction(self.menufileimportsvg)
        self.menufileimportsvg_as_gerber = QtWidgets.QAction(QtGui.QIcon('share/svg16.png'),
                                                         '&SVG as Gerber Object', self)
        self.menufileimport.addAction(self.menufileimportsvg_as_gerber)
        self.menufileimport.addSeparator()

        self.menufileimportdxf = QtWidgets.QAction(QtGui.QIcon('share/dxf16.png'),
                                               '&DXF as Geometry Object', self)
        self.menufileimport.addAction(self.menufileimportdxf)
        self.menufileimportdxf_as_gerber = QtWidgets.QAction(QtGui.QIcon('share/dxf16.png'),
                                                         '&DXF as Gerber Object', self)
        self.menufileimport.addAction(self.menufileimportdxf_as_gerber)
        self.menufileimport.addSeparator()

        # Export ...
        self.menufileexport = self.menufile.addMenu(QtGui.QIcon('share/export.png'), 'Export')
        self.menufileexportsvg = QtWidgets.QAction(QtGui.QIcon('share/export.png'), 'Export &SVG ...', self)
        self.menufileexport.addAction(self.menufileexportsvg)

        self.menufileexportdxf = QtWidgets.QAction(QtGui.QIcon('share/export.png'), 'Export DXF ...', self)
        self.menufileexport.addAction(self.menufileexportdxf)

        self.menufileexport.addSeparator()

        self.menufileexportpng = QtWidgets.QAction(QtGui.QIcon('share/export_png32.png'), 'Export &PNG ...', self)
        self.menufileexport.addAction(self.menufileexportpng)

        self.menufileexport.addSeparator()

        self.menufileexportexcellon = QtWidgets.QAction(QtGui.QIcon('share/drill32.png'), 'Export &Excellon ...', self)
        self.menufileexport.addAction(self.menufileexportexcellon)

        self.menufileexportexcellon_altium = QtWidgets.QAction(QtGui.QIcon('share/drill32.png'),
                                                           'Export Excellon 2:4 LZ INCH ...', self)
        self.menufileexport.addAction(self.menufileexportexcellon_altium)

        # Separator
        self.menufile.addSeparator()

        # Save Defaults
        self.menufilesavedefaults = QtWidgets.QAction(QtGui.QIcon('share/defaults.png'), 'Save &Defaults', self)
        self.menufile.addAction(self.menufilesavedefaults)

        # Separator
        self.menufile.addSeparator()

        self.menufile_save = self.menufile.addMenu(QtGui.QIcon('share/save_as.png'), 'Save')
        # Save Project
        self.menufilesaveproject = QtWidgets.QAction(QtGui.QIcon('share/floppy16.png'), '&Save Project', self)
        self.menufile_save.addAction(self.menufilesaveproject)

        # Save Project As ...
        self.menufilesaveprojectas = QtWidgets.QAction(QtGui.QIcon('share/save_as.png'), 'Save Project &As ...', self)
        self.menufile_save.addAction(self.menufilesaveprojectas)

        # Save Project Copy ...
        self.menufilesaveprojectcopy = QtWidgets.QAction(QtGui.QIcon('share/floppy16.png'), 'Save Project C&opy ...',
                                                     self)
        self.menufile_save.addAction(self.menufilesaveprojectcopy)

        # Separator
        self.menufile.addSeparator()

        # Quit
        self.menufile_exit = QtWidgets.QAction(QtGui.QIcon('share/power16.png'), 'E&xit', self)
        # exitAction.setShortcut('Ctrl+Q')
        # exitAction.setStatusTip('Exit application')
        self.menufile.addAction(self.menufile_exit)

        ### Edit ###
        self.menuedit = self.menu.addMenu('&Edit')
        self.menueditnew = self.menuedit.addAction(QtGui.QIcon('share/new_geo16.png'), '&New Geometry')
        self.menueditnewexc = self.menuedit.addAction(QtGui.QIcon('share/new_geo16.png'), 'New Excellon')
        # Separator
        self.menuedit.addSeparator()
        self.menueditedit = self.menuedit.addAction(QtGui.QIcon('share/edit16.png'), 'Edit Object')
        self.menueditok = self.menuedit.addAction(QtGui.QIcon('share/edit_ok16.png'), '&Update Object')
        # Separator
        self.menuedit.addSeparator()
        self.menuedit_convert = self.menuedit.addMenu(QtGui.QIcon('share/convert24.png'), 'Conversion')
        self.menuedit_convertjoin = self.menuedit_convert.addAction(
            QtGui.QIcon('share/join16.png'), '&Join Geo/Gerber/Exc -> Geo')
        self.menuedit_convertjoin.setToolTip(
            "Merge a selection of objects, which can be of type:\n"
            "- Gerber\n"
            "- Excellon\n"
            "- Geometry\n"
            "into a new combo Geometry object.")
        self.menuedit_convertjoinexc = self.menuedit_convert.addAction(
            QtGui.QIcon('share/join16.png'), 'Join Excellon(s) -> Excellon')
        self.menuedit_convertjoinexc.setToolTip(
            "Merge a selection of Excellon objects into a new combo Excellon object.")
        # Separator
        self.menuedit_convert.addSeparator()
        self.menuedit_convert_sg2mg = self.menuedit_convert.addAction(
            QtGui.QIcon('share/convert24.png'), 'Convert Single to MultiGeo')
        self.menuedit_convert_sg2mg.setToolTip(
            "Will convert a Geometry object from single_geometry type\n"
            "to a multi_geometry type.")
        self.menuedit_convert_mg2sg = self.menuedit_convert.addAction(
            QtGui.QIcon('share/convert24.png'), 'Convert Multi to SingleGeo')
        self.menuedit_convert_mg2sg.setToolTip(
            "Will convert a Geometry object from multi_geometry type\n"
            "to a single_geometry type.")
        self.menuedit_convert.setToolTipsVisible(True)
        # Separator
        self.menuedit.addSeparator()
        self.menueditdelete = self.menuedit.addAction(QtGui.QIcon('share/trash16.png'), '&Delete')

        # Separator
        self.menuedit.addSeparator()
        self.menueditcopyobject = self.menuedit.addAction(QtGui.QIcon('share/copy.png'), '&Copy Object')
        self.menueditcopyobjectasgeom = self.menuedit.addAction(QtGui.QIcon('share/copy_geo.png'),
                                                                'Copy as &Geom')

        # Separator
        self.menuedit.addSeparator()
        self.menueditorigin = self.menuedit.addAction(QtGui.QIcon('share/origin.png'), 'Se&t Origin')
        self.menueditjump = self.menuedit.addAction(QtGui.QIcon('share/jump_to16.png'), 'Jump to Location')

        # Separator
        self.menuedit.addSeparator()
        self.menueditselectall = self.menuedit.addAction(QtGui.QIcon('share/select_all.png'),
                                                         '&Select All')

        # Separator
        self.menuedit.addSeparator()
        self.menueditpreferences = self.menuedit.addAction(QtGui.QIcon('share/pref.png'), '&Preferences')

        ### Options ###
        self.menuoptions = self.menu.addMenu('&Options')
        # self.menuoptions_transfer = self.menuoptions.addMenu(QtGui.QIcon('share/transfer.png'), 'Transfer options')
        # self.menuoptions_transfer_a2p = self.menuoptions_transfer.addAction("Application to Project")
        # self.menuoptions_transfer_p2a = self.menuoptions_transfer.addAction("Project to Application")
        # self.menuoptions_transfer_p2o = self.menuoptions_transfer.addAction("Project to Object")
        # self.menuoptions_transfer_o2p = self.menuoptions_transfer.addAction("Object to Project")
        # self.menuoptions_transfer_a2o = self.menuoptions_transfer.addAction("Application to Object")
        # self.menuoptions_transfer_o2a = self.menuoptions_transfer.addAction("Object to Application")

        # Separator
        # self.menuoptions.addSeparator()

        # self.menuoptions_transform = self.menuoptions.addMenu(QtGui.QIcon('share/transform.png'),
        #                                                       '&Transform Object')
        self.menuoptions_transform_rotate = self.menuoptions.addAction(QtGui.QIcon('share/rotate.png'),
                                                                                 "&Rotate Selection")
        # Separator
        self.menuoptions.addSeparator()

        self.menuoptions_transform_skewx = self.menuoptions.addAction(QtGui.QIcon('share/skewX.png'),
                                                                                "&Skew on X axis")
        self.menuoptions_transform_skewy = self.menuoptions.addAction(QtGui.QIcon('share/skewY.png'),
                                                                                "S&kew on Y axis")

        # Separator
        self.menuoptions.addSeparator()
        self.menuoptions_transform_flipx = self.menuoptions.addAction(QtGui.QIcon('share/flipx.png'),
                                                                                "Flip on &X axis")
        self.menuoptions_transform_flipy = self.menuoptions.addAction(QtGui.QIcon('share/flipy.png'),
                                                                                "Flip on &Y axis")
        # Separator
        self.menuoptions.addSeparator()

        ### View ###
        self.menuview = self.menu.addMenu('&View')
        self.menuviewenable = self.menuview.addAction(QtGui.QIcon('share/replot16.png'), 'Enable all plots')
        self.menuviewdisableall = self.menuview.addAction(QtGui.QIcon('share/clear_plot16.png'),
                                                          'Disable all plots')
        self.menuviewdisableother = self.menuview.addAction(QtGui.QIcon('share/clear_plot16.png'),
                                                            'Disable non-selected')
        # Separator
        self.menuview.addSeparator()
        self.menuview_zoom_fit = self.menuview.addAction(QtGui.QIcon('share/zoom_fit32.png'), "&Zoom Fit")
        self.menuview_zoom_in = self.menuview.addAction(QtGui.QIcon('share/zoom_in32.png'), "&Zoom In")
        self.menuview_zoom_out = self.menuview.addAction(QtGui.QIcon('share/zoom_out32.png'), "&Zoom Out")

        self.menuview.addSeparator()
        self.menuview_toggle_axis = self.menuview.addAction(QtGui.QIcon('share/axis32.png'), "&Toggle Axis")
        self.menuview_toggle_workspace = self.menuview.addAction(QtGui.QIcon('share/workspace24.png'),
                                                                 "Toggle Workspace")


        ### FlatCAM Editor menu ###
        # self.editor_menu = QtWidgets.QMenu("Editor")
        # self.menu.addMenu(self.editor_menu)
        self.geo_editor_menu = QtWidgets.QMenu("Geo Editor")
        self.menu.addMenu(self.geo_editor_menu)

        # self.select_menuitem = self.menu.addAction(QtGui.QIcon('share/pointer16.png'), "Select 'Esc'")
        self.geo_add_circle_menuitem = self.geo_editor_menu.addAction(QtGui.QIcon('share/circle32.png'), 'Add Circle')
        self.geo_add_arc_menuitem = self.geo_editor_menu.addAction(QtGui.QIcon('share/arc16.png'), 'Add Arc')
        self.geo_editor_menu.addSeparator()
        self.geo_add_rectangle_menuitem = self.geo_editor_menu.addAction(QtGui.QIcon('share/rectangle32.png'), 'Add Rectangle')
        self.geo_add_polygon_menuitem = self.geo_editor_menu.addAction(QtGui.QIcon('share/polygon32.png'), 'Add Polygon')
        self.geo_add_path_menuitem = self.geo_editor_menu.addAction(QtGui.QIcon('share/path32.png'), 'Add Path')
        self.geo_editor_menu.addSeparator()
        self.geo_add_text_menuitem = self.geo_editor_menu.addAction(QtGui.QIcon('share/text32.png'), 'Add Text')
        self.geo_editor_menu.addSeparator()
        self.geo_union_menuitem = self.geo_editor_menu.addAction(QtGui.QIcon('share/union16.png'), 'Polygon Union')
        self.geo_intersection_menuitem = self.geo_editor_menu.addAction(QtGui.QIcon('share/intersection16.png'),
                                                         'Polygon Intersection')
        self.geo_subtract_menuitem = self.geo_editor_menu.addAction(QtGui.QIcon('share/subtract16.png'), 'Polygon Subtraction')
        self.geo_editor_menu.addSeparator()
        self.geo_cutpath_menuitem = self.geo_editor_menu.addAction(QtGui.QIcon('share/cutpath16.png'), 'Cut Path')
        # self.move_menuitem = self.menu.addAction(QtGui.QIcon('share/move16.png'), "Move Objects 'm'")
        self.geo_copy_menuitem = self.geo_editor_menu.addAction(QtGui.QIcon('share/copy16.png'), "Copy Geom")
        self.geo_delete_menuitem = self.geo_editor_menu.addAction(QtGui.QIcon('share/deleteshape16.png'), "Delete Shape")
        self.geo_editor_menu.addSeparator()
        self.geo_buffer_menuitem = self.geo_editor_menu.addAction(QtGui.QIcon('share/buffer16.png'), "Buffer Selection")
        self.geo_paint_menuitem = self.geo_editor_menu.addAction(QtGui.QIcon('share/paint16.png'), "Paint Selection")
        self.geo_editor_menu.addSeparator()

        # self.exc_editor_menu = QtWidgets.QMenu("Excellon Editor")
        # self.menu.addMenu(self.exc_editor_menu)

        self.geo_editor_menu.setDisabled(True)
        # self.exc_editor_menu.setDisabled(True)

        ### Tool ###
        # self.menutool = self.menu.addMenu('&Tool')
        self.menutool = QtWidgets.QMenu('&Tool')
        self.menutoolaction = self.menu.addMenu(self.menutool)
        self.menutoolshell = self.menutool.addAction(QtGui.QIcon('share/shell16.png'), '&Command Line')

        ### Help ###
        self.menuhelp = self.menu.addMenu('&Help')
        self.menuhelp_about = self.menuhelp.addAction(QtGui.QIcon('share/tv16.png'), 'About FlatCAM')
        self.menuhelp_home = self.menuhelp.addAction(QtGui.QIcon('share/home16.png'), 'Home')
        self.menuhelp_manual = self.menuhelp.addAction(QtGui.QIcon('share/globe16.png'), 'Manual')
        self.menuhelp.addSeparator()
        self.menuhelp_shortcut_list = self.menuhelp.addAction(QtGui.QIcon('share/shortcuts24.png'), 'Shortcuts List')
        self.menuhelp_videohelp = self.menuhelp.addAction(QtGui.QIcon('share/videohelp24.png'), 'See on YouTube')

        ####################
        ### Context menu ###
        ####################

        self.menuproject = QtWidgets.QMenu()
        self.menuprojectenable = self.menuproject.addAction('Enable')
        self.menuprojectdisable = self.menuproject.addAction('Disable')
        self.menuproject.addSeparator()
        self.menuprojectgeneratecnc = self.menuproject.addAction('Generate CNC')
        self.menuproject.addSeparator()
        self.menuprojectdelete = self.menuproject.addAction('Delete')

        ###############
        ### Toolbar ###
        ###############
        self.toolbarfile = QtWidgets.QToolBar('File Toolbar')
        self.addToolBar(self.toolbarfile)
        self.file_open_gerber_btn = self.toolbarfile.addAction(QtGui.QIcon('share/flatcam_icon32.png'),
                                                               "Open GERBER")
        self.file_open_excellon_btn = self.toolbarfile.addAction(QtGui.QIcon('share/drill32.png'), "Open EXCELLON")
        self.toolbarfile.addSeparator()
        self.file_open_btn = self.toolbarfile.addAction(QtGui.QIcon('share/folder32.png'), "Open project")
        self.file_save_btn = self.toolbarfile.addAction(QtGui.QIcon('share/floppy32.png'), "Save project")

        self.toolbargeo = QtWidgets.QToolBar('Edit Toolbar')
        self.addToolBar(self.toolbargeo)

        self.newgeo_btn = self.toolbargeo.addAction(QtGui.QIcon('share/new_geo32_bis.png'), "New Blank Geometry")
        self.newexc_btn = self.toolbargeo.addAction(QtGui.QIcon('share/new_exc32.png'), "New Blank Excellon")
        self.toolbargeo.addSeparator()
        self.editgeo_btn = self.toolbargeo.addAction(QtGui.QIcon('share/edit32.png'), "Editor")
        self.update_obj_btn = self.toolbargeo.addAction(QtGui.QIcon('share/edit_ok32_bis.png'), "Save Object")
        self.update_obj_btn.setEnabled(False)
        self.toolbargeo.addSeparator()
        self.delete_btn = self.toolbargeo.addAction(QtGui.QIcon('share/cancel_edit32.png'), "&Delete")

        self.toolbarview = QtWidgets.QToolBar('View Toolbar')
        self.addToolBar(self.toolbarview)
        self.replot_btn = self.toolbarview.addAction(QtGui.QIcon('share/replot32.png'), "&Replot")
        self.clear_plot_btn = self.toolbarview.addAction(QtGui.QIcon('share/clear_plot32.png'), "&Clear plot")
        self.zoom_in_btn = self.toolbarview.addAction(QtGui.QIcon('share/zoom_in32.png'), "Zoom In")
        self.zoom_out_btn = self.toolbarview.addAction(QtGui.QIcon('share/zoom_out32.png'), "Zoom Out")
        self.zoom_fit_btn = self.toolbarview.addAction(QtGui.QIcon('share/zoom_fit32.png'), "Zoom Fit")

        # self.toolbarview.setVisible(False)

        self.toolbartools = QtWidgets.QToolBar('Tools Toolbar')
        self.addToolBar(self.toolbartools)
        self.shell_btn = self.toolbartools.addAction(QtGui.QIcon('share/shell32.png'), "&Command Line")

        ### Drill Editor Toolbar ###
        self.exc_edit_toolbar = QtWidgets.QToolBar('Excellon Editor Toolbar')
        self.addToolBar(self.exc_edit_toolbar)

        self.select_drill_btn = self.exc_edit_toolbar.addAction(QtGui.QIcon('share/pointer32.png'), "Select 'Esc'")
        self.add_drill_btn = self.exc_edit_toolbar.addAction(QtGui.QIcon('share/plus16.png'), 'Add Drill Hole')
        self.add_drill_array_btn = self.exc_edit_toolbar.addAction(
            QtGui.QIcon('share/addarray16.png'), 'Add Drill Hole Array')
        self.resize_drill_btn = self.exc_edit_toolbar.addAction(QtGui.QIcon('share/resize16.png'), 'Resize Drill')
        self.exc_edit_toolbar.addSeparator()

        self.copy_drill_btn = self.exc_edit_toolbar.addAction(QtGui.QIcon('share/copy32.png'), 'Copy Drill')
        self.delete_drill_btn = self.exc_edit_toolbar.addAction(QtGui.QIcon('share/deleteshape32.png'), "Delete Drill")

        self.exc_edit_toolbar.addSeparator()
        self.move_drill_btn = self.exc_edit_toolbar.addAction(QtGui.QIcon('share/move32.png'), "Move Drill")

        self.exc_edit_toolbar.setDisabled(True)
        self.exc_edit_toolbar.setVisible(False)

        ### Geometry Editor Toolbar ###
        self.geo_edit_toolbar = QtWidgets.QToolBar('Geometry Editor Toolbar')
        self.geo_edit_toolbar.setVisible(False)
        self.addToolBar(self.geo_edit_toolbar)

        self.geo_select_btn = self.geo_edit_toolbar.addAction(QtGui.QIcon('share/pointer32.png'), "Select 'Esc'")
        self.geo_add_circle_btn = self.geo_edit_toolbar.addAction(QtGui.QIcon('share/circle32.png'), 'Add Circle')
        self.geo_add_arc_btn = self.geo_edit_toolbar.addAction(QtGui.QIcon('share/arc32.png'), 'Add Arc')
        self.geo_add_rectangle_btn = self.geo_edit_toolbar.addAction(QtGui.QIcon('share/rectangle32.png'), 'Add Rectangle')

        self.geo_edit_toolbar.addSeparator()
        self.geo_add_path_btn = self.geo_edit_toolbar.addAction(QtGui.QIcon('share/path32.png'), 'Add Path')
        self.geo_add_polygon_btn = self.geo_edit_toolbar.addAction(QtGui.QIcon('share/polygon32.png'), 'Add Polygon')
        self.geo_edit_toolbar.addSeparator()
        self.geo_add_text_btn = self.geo_edit_toolbar.addAction(QtGui.QIcon('share/text32.png'), 'Add Text')
        self.geo_add_buffer_btn = self.geo_edit_toolbar.addAction(QtGui.QIcon('share/buffer16-2.png'), 'Add Buffer')
        self.geo_add_paint_btn = self.geo_edit_toolbar.addAction(QtGui.QIcon('share/paint20_1.png'), 'Paint Shape')

        self.geo_edit_toolbar.addSeparator()
        self.geo_union_btn = self.geo_edit_toolbar.addAction(QtGui.QIcon('share/union32.png'), 'Polygon Union')
        self.geo_intersection_btn = self.geo_edit_toolbar.addAction(QtGui.QIcon('share/intersection32.png'),
                                                               'Polygon Intersection')
        self.geo_subtract_btn = self.geo_edit_toolbar.addAction(QtGui.QIcon('share/subtract32.png'), 'Polygon Subtraction')

        self.geo_edit_toolbar.addSeparator()
        self.geo_cutpath_btn = self.geo_edit_toolbar.addAction(QtGui.QIcon('share/cutpath32.png'), 'Cut Path')
        self.geo_copy_btn = self.geo_edit_toolbar.addAction(QtGui.QIcon('share/copy32.png'), "Copy Objects 'c'")
        self.geo_rotate_btn = self.geo_edit_toolbar.addAction(QtGui.QIcon('share/rotate.png'), "Rotate Objects 'Space'")
        self.geo_delete_btn = self.geo_edit_toolbar.addAction(QtGui.QIcon('share/deleteshape32.png'), "Delete Shape '-'")

        self.geo_edit_toolbar.addSeparator()
        self.geo_move_btn = self.geo_edit_toolbar.addAction(QtGui.QIcon('share/move32.png'), "Move Objects 'm'")

        ### Snap Toolbar ###
        self.snap_toolbar = QtWidgets.QToolBar('Grid Toolbar')
        # Snap GRID toolbar is always active to facilitate usage of measurements done on GRID
        self.addToolBar(self.snap_toolbar)

        self.grid_snap_btn = self.snap_toolbar.addAction(QtGui.QIcon('share/grid32.png'), 'Snap to grid')
        self.grid_gap_x_entry = FCEntry2()
        self.grid_gap_x_entry.setMaximumWidth(70)
        self.grid_gap_x_entry.setToolTip("Grid X distance")
        self.snap_toolbar.addWidget(self.grid_gap_x_entry)

        self.grid_gap_y_entry = FCEntry2()
        self.grid_gap_y_entry.setMaximumWidth(70)
        self.grid_gap_y_entry.setToolTip("Grid Y distance")
        self.snap_toolbar.addWidget(self.grid_gap_y_entry)

        self.grid_space_label = QtWidgets.QLabel("  ")
        self.snap_toolbar.addWidget(self.grid_space_label)
        self.grid_gap_link_cb = FCCheckBox()
        self.grid_gap_link_cb.setToolTip("When active, value on Grid_X\n"
                                         "is copied to the Grid_Y value.")
        self.snap_toolbar.addWidget(self.grid_gap_link_cb)

        self.ois_grid = OptionalInputSection(self.grid_gap_link_cb, [self.grid_gap_y_entry], logic=False)

        self.corner_snap_btn = self.snap_toolbar.addAction(QtGui.QIcon('share/corner32.png'), 'Snap to corner')

        self.snap_max_dist_entry = QtWidgets.QLineEdit()
        self.snap_max_dist_entry.setMaximumWidth(70)
        self.snap_max_dist_entry.setToolTip("Max. magnet distance")
        self.snap_toolbar.addWidget(self.snap_max_dist_entry)

        self.grid_snap_btn.setCheckable(True)
        self.corner_snap_btn.setCheckable(True)

        ################
        ### Splitter ###
        ################
        self.splitter = QtWidgets.QSplitter()
        self.setCentralWidget(self.splitter)

        ################
        ### Notebook ###
        ################
        self.notebook = QtWidgets.QTabWidget()
        self.splitter.addWidget(self.notebook)

        ### Project ###
        self.project_tab = QtWidgets.QWidget()
        # project_tab.setMinimumWidth(250)  # Hack
        self.project_tab_layout = QtWidgets.QVBoxLayout(self.project_tab)
        self.project_tab_layout.setContentsMargins(2, 2, 2, 2)
        self.notebook.addTab(self.project_tab, "Project")

        ### Selected ###
        self.selected_tab = QtWidgets.QWidget()
        self.selected_tab_layout = QtWidgets.QVBoxLayout(self.selected_tab)
        self.selected_tab_layout.setContentsMargins(2, 2, 2, 2)
        self.selected_scroll_area = VerticalScrollArea()
        self.selected_tab_layout.addWidget(self.selected_scroll_area)
        self.notebook.addTab(self.selected_tab, "Selected")

        ### Tool ###
        self.tool_tab = QtWidgets.QWidget()
        self.tool_tab_layout = QtWidgets.QVBoxLayout(self.tool_tab)
        self.tool_tab_layout.setContentsMargins(2, 2, 2, 2)
        self.notebook.addTab(self.tool_tab, "Tool")
        self.tool_scroll_area = VerticalScrollArea()
        self.tool_tab_layout.addWidget(self.tool_scroll_area)

        self.right_widget = QtWidgets.QWidget()
        self.right_widget.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
        self.splitter.addWidget(self.right_widget)

        self.right_lay = QtWidgets.QVBoxLayout()
        self.right_lay.setContentsMargins(0, 0, 0, 0)
        self.right_widget.setLayout(self.right_lay)
        self.plot_tab_area = FCTab()
        self.right_lay.addWidget(self.plot_tab_area)
        self.plot_tab_area.setTabsClosable(True)

        plot_tab = QtWidgets.QWidget()
        self.plot_tab_area.addTab(plot_tab, "Plot Area")

        self.right_layout = QtWidgets.QVBoxLayout()
        self.right_layout.setContentsMargins(2, 2, 2, 2)
        plot_tab.setLayout(self.right_layout)

        # remove the close button from the Plot Area tab (first tab index = 0) as this one will always be ON
        self.plot_tab_area.protectTab(0)

        ########################################
        ### HERE WE BUILD THE PREF. TAB AREA ###
        ########################################
        self.preferences_tab = QtWidgets.QWidget()
        self.pref_tab_layout = QtWidgets.QVBoxLayout(self.preferences_tab)
        self.pref_tab_layout.setContentsMargins(2, 2, 2, 2)

        self.pref_tab_area = FCTab()
        self.pref_tab_area.setTabsClosable(False)
        self.pref_tab_area_tabBar = self.pref_tab_area.tabBar()
        self.pref_tab_area_tabBar.setStyleSheet("QTabBar::tab{width:80px;}")
        self.pref_tab_area_tabBar.setExpanding(True)
        self.pref_tab_layout.addWidget(self.pref_tab_area)

        self.general_tab = QtWidgets.QWidget()
        self.pref_tab_area.addTab(self.general_tab, "General")
        self.general_tab_lay = QtWidgets.QVBoxLayout()
        self.general_tab_lay.setContentsMargins(2, 2, 2, 2)
        self.general_tab.setLayout(self.general_tab_lay)

        self.hlay1 = QtWidgets.QHBoxLayout()
        self.general_tab_lay.addLayout(self.hlay1)

        self.options_combo = QtWidgets.QComboBox()
        self.options_combo.addItem("APP.  DEFAULTS")
        self.options_combo.addItem("PROJ. OPTIONS ")
        self.hlay1.addWidget(self.options_combo)

        self.hlay1.addStretch()

        self.general_scroll_area = VerticalScrollArea()
        self.general_tab_lay.addWidget(self.general_scroll_area)

        self.gerber_tab = QtWidgets.QWidget()
        self.pref_tab_area.addTab(self.gerber_tab, "GERBER")
        self.gerber_tab_lay = QtWidgets.QVBoxLayout()
        self.gerber_tab_lay.setContentsMargins(2, 2, 2, 2)
        self.gerber_tab.setLayout(self.gerber_tab_lay)

        self.gerber_scroll_area = VerticalScrollArea()
        self.gerber_tab_lay.addWidget(self.gerber_scroll_area)

        self.excellon_tab = QtWidgets.QWidget()
        self.pref_tab_area.addTab(self.excellon_tab, "EXCELLON")
        self.excellon_tab_lay = QtWidgets.QVBoxLayout()
        self.excellon_tab_lay.setContentsMargins(2, 2, 2, 2)
        self.excellon_tab.setLayout(self.excellon_tab_lay)

        self.excellon_scroll_area = VerticalScrollArea()
        self.excellon_tab_lay.addWidget(self.excellon_scroll_area)

        self.geometry_tab = QtWidgets.QWidget()
        self.pref_tab_area.addTab(self.geometry_tab, "GEOMETRY")
        self.geometry_tab_lay = QtWidgets.QVBoxLayout()
        self.geometry_tab_lay.setContentsMargins(2, 2, 2, 2)
        self.geometry_tab.setLayout(self.geometry_tab_lay)

        self.geometry_scroll_area = VerticalScrollArea()
        self.geometry_tab_lay.addWidget(self.geometry_scroll_area)

        self.cncjob_tab = QtWidgets.QWidget()
        self.pref_tab_area.addTab(self.cncjob_tab, "CNC-JOB")
        self.cncjob_tab_lay = QtWidgets.QVBoxLayout()
        self.cncjob_tab_lay.setContentsMargins(2, 2, 2, 2)
        self.cncjob_tab.setLayout(self.cncjob_tab_lay)

        self.cncjob_scroll_area = VerticalScrollArea()
        self.cncjob_tab_lay.addWidget(self.cncjob_scroll_area)

        self.pref_tab_bottom_layout = QtWidgets.QHBoxLayout()
        self.pref_tab_bottom_layout.setAlignment(QtCore.Qt.AlignVCenter)
        self.pref_tab_layout.addLayout(self.pref_tab_bottom_layout)

        self.pref_tab_bottom_layout_1 = QtWidgets.QHBoxLayout()
        self.pref_tab_bottom_layout_1.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.pref_tab_bottom_layout.addLayout(self.pref_tab_bottom_layout_1)

        self.pref_factory_button = QtWidgets.QPushButton()
        self.pref_factory_button.setText("Import Factory Def.")
        self.pref_factory_button.setFixedWidth(110)
        self.pref_tab_bottom_layout_1.addWidget(self.pref_factory_button)

        self.pref_load_button = QtWidgets.QPushButton()
        self.pref_load_button.setText("Load User Defaults")
        self.pref_load_button.setFixedWidth(110)
        self.pref_tab_bottom_layout_1.addWidget(self.pref_load_button)

        self.pref_tab_bottom_layout_2 = QtWidgets.QHBoxLayout()
        self.pref_tab_bottom_layout_2.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.pref_tab_bottom_layout.addLayout(self.pref_tab_bottom_layout_2)

        self.pref_save_button = QtWidgets.QPushButton()
        self.pref_save_button.setText("Save")
        self.pref_save_button.setFixedWidth(100)
        self.pref_tab_bottom_layout_2.addWidget(self.pref_save_button)

        ########################################
        ### HERE WE BUILD THE CONTEXT MENU FOR RMB CLICK ON CANVAS ###
        ########################################
        self.popMenu = QtWidgets.QMenu()

        self.cmenu_gridmenu = self.popMenu.addMenu(QtGui.QIcon('share/grid32_menu.png'), "Grids")
        self.gridmenu_1 = self.cmenu_gridmenu.addAction(QtGui.QIcon('share/grid32_menu.png'), "0.05")
        self.gridmenu_2 = self.cmenu_gridmenu.addAction(QtGui.QIcon('share/grid32_menu.png'), "0.10")
        self.gridmenu_3 = self.cmenu_gridmenu.addAction(QtGui.QIcon('share/grid32_menu.png'), "0.20")
        self.gridmenu_4 = self.cmenu_gridmenu.addAction(QtGui.QIcon('share/grid32_menu.png'), "0.50")
        self.gridmenu_5 = self.cmenu_gridmenu.addAction(QtGui.QIcon('share/grid32_menu.png'), "1.00")

        self.g_editor_cmenu = self.popMenu.addMenu(QtGui.QIcon('share/draw32.png'), "Geo Editor")
        self.draw_line = self.g_editor_cmenu.addAction(QtGui.QIcon('share/path32.png'), "Line")
        self.draw_rect = self.g_editor_cmenu.addAction(QtGui.QIcon('share/rectangle32.png'), "Rectangle")
        self.draw_cut = self.g_editor_cmenu.addAction(QtGui.QIcon('share/cutpath32.png'), "Cut")

        self.e_editor_cmenu = self.popMenu.addMenu(QtGui.QIcon('share/drill32.png'), "Exc Editor")
        self.drill = self.e_editor_cmenu.addAction(QtGui.QIcon('share/drill32.png'), "Add Drill")
        self.drill_array = self.e_editor_cmenu.addAction(QtGui.QIcon('share/addarray32.png'), "Add Drill Array")
        self.drill_copy = self.e_editor_cmenu.addAction(QtGui.QIcon('share/copy32.png'), "Copy Drill(s)")

        self.cmenu_viewmenu = self.popMenu.addMenu(QtGui.QIcon('share/view64.png'), "View")
        self.zoomfit = self.cmenu_viewmenu.addAction(QtGui.QIcon('share/zoom_fit32.png'), "Zoom Fit")
        self.clearplot = self.cmenu_viewmenu.addAction(QtGui.QIcon('share/clear_plot32.png'), "Clear Plot")
        self.replot = self.cmenu_viewmenu.addAction(QtGui.QIcon('share/replot32.png'), "Replot")

        self.popmenu_properties = self.popMenu.addAction(QtGui.QIcon('share/properties32.png'), "Properties")


        ####################################
        ### Here we build the CNCJob Tab ###
        ####################################
        self.cncjob_tab = QtWidgets.QWidget()
        self.cncjob_tab_layout = QtWidgets.QGridLayout(self.cncjob_tab)
        self.cncjob_tab_layout.setContentsMargins(2, 2, 2, 2)
        self.cncjob_tab.setLayout(self.cncjob_tab_layout)

        self.code_editor = QtWidgets.QTextEdit()
        stylesheet = """
                        QTextEdit { selection-background-color:yellow;
                                    selection-color:black;
                        }
                     """

        self.code_editor.setStyleSheet(stylesheet)

        self.buttonPreview = QtWidgets.QPushButton('Print Preview')
        self.buttonPrint = QtWidgets.QPushButton('Print CNC Code')
        self.buttonFind = QtWidgets.QPushButton('Find in CNC Code')
        self.buttonFind.setFixedWidth(100)
        self.buttonPreview.setFixedWidth(100)
        self.entryFind = FCEntry()
        self.entryFind.setMaximumWidth(200)
        self.buttonReplace = QtWidgets.QPushButton('Replace With')
        self.buttonReplace.setFixedWidth(100)
        self.entryReplace = FCEntry()
        self.entryReplace.setMaximumWidth(200)
        self.sel_all_cb = QtWidgets.QCheckBox('All')
        self.sel_all_cb.setToolTip(
            "When checked it will replace all instances in the 'Find' box\n"
            "with the text in the 'Replace' box.."
        )
        self.buttonOpen = QtWidgets.QPushButton('Open CNC Code')
        self.buttonSave = QtWidgets.QPushButton('Save CNC Code')

        self.cncjob_tab_layout.addWidget(self.code_editor, 0, 0, 1, 5)

        cnc_tab_lay_1 = QtWidgets.QHBoxLayout()
        cnc_tab_lay_1.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        cnc_tab_lay_1.addWidget(self.buttonFind)
        cnc_tab_lay_1.addWidget(self.entryFind)
        cnc_tab_lay_1.addWidget(self.buttonReplace)
        cnc_tab_lay_1.addWidget(self.entryReplace)
        cnc_tab_lay_1.addWidget(self.sel_all_cb)
        self.cncjob_tab_layout.addLayout(cnc_tab_lay_1, 1, 0, 1, 1, QtCore.Qt.AlignLeft)

        cnc_tab_lay_3 = QtWidgets.QHBoxLayout()
        cnc_tab_lay_3.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        cnc_tab_lay_3.addWidget(self.buttonPreview)
        cnc_tab_lay_3.addWidget(self.buttonPrint)
        self.cncjob_tab_layout.addLayout(cnc_tab_lay_3, 2, 0, 1, 1, QtCore.Qt.AlignLeft)

        cnc_tab_lay_4 = QtWidgets.QHBoxLayout()
        cnc_tab_lay_4.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        cnc_tab_lay_4.addWidget(self.buttonOpen)
        cnc_tab_lay_4.addWidget(self.buttonSave)
        self.cncjob_tab_layout.addLayout(cnc_tab_lay_4, 2, 4, 1, 1)

        ##################################
        ### Build InfoBar is done here ###
        ##################################
        self.infobar = self.statusBar()
        self.fcinfo = FlatCAMInfoBar()
        self.infobar.addWidget(self.fcinfo, stretch=1)

        self.rel_position_label = QtWidgets.QLabel(
            "<b>Dx</b>: 0.0000&nbsp;&nbsp;   <b>Dy</b>: 0.0000&nbsp;&nbsp;&nbsp;&nbsp;")
        self.rel_position_label.setMinimumWidth(110)
        self.rel_position_label.setToolTip("Relative neasurement.\nReference is last click position")
        self.infobar.addWidget(self.rel_position_label)

        self.position_label = QtWidgets.QLabel(
            "&nbsp;&nbsp;&nbsp;&nbsp;<b>X</b>: 0.0000&nbsp;&nbsp;   <b>Y</b>: 0.0000")
        self.position_label.setMinimumWidth(110)
        self.position_label.setToolTip("Absolute neasurement.\nReference is (X=0, Y= 0) position")
        self.infobar.addWidget(self.position_label)

        self.units_label = QtWidgets.QLabel("[in]")
        self.units_label.setMargin(2)
        self.infobar.addWidget(self.units_label)

        # disabled
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        # infobar.addWidget(self.progress_bar)

        self.activity_view = FlatCAMActivityView()
        self.infobar.addWidget(self.activity_view)

        self.app_icon = QtGui.QIcon()
        self.app_icon.addFile('share/flatcam_icon16.png', QtCore.QSize(16, 16))
        self.app_icon.addFile('share/flatcam_icon24.png', QtCore.QSize(24, 24))
        self.app_icon.addFile('share/flatcam_icon32.png', QtCore.QSize(32, 32))
        self.app_icon.addFile('share/flatcam_icon48.png', QtCore.QSize(48, 48))
        self.app_icon.addFile('share/flatcam_icon128.png', QtCore.QSize(128, 128))
        self.app_icon.addFile('share/flatcam_icon256.png', QtCore.QSize(256, 256))
        self.setWindowIcon(self.app_icon)

        self.setGeometry(100, 100, 1024, 650)
        self.setWindowTitle('FlatCAM %s %s - %s' % (version, ('BETA' if beta else ''), platform.architecture()[0]))
        self.show()

        self.filename = ""
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls:
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls:
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls:
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
            for url in event.mimeData().urls():
                self.filename = str(url.toLocalFile())

                if self.filename == "":
                    self.app.inform.emit("Open cancelled.")
                else:
                    if self.filename.lower().rpartition('.')[-1] in self.app.grb_list:
                        self.app.worker_task.emit({'fcn': self.app.open_gerber,
                                                   'params': [self.filename]})
                    else:
                        event.ignore()

                    if self.filename.lower().rpartition('.')[-1] in self.app.exc_list:
                        self.app.worker_task.emit({'fcn': self.app.open_excellon,
                                                   'params': [self.filename]})
                    else:
                        event.ignore()

                    if self.filename.lower().rpartition('.')[-1] in self.app.gcode_list:
                        self.app.worker_task.emit({'fcn': self.app.open_gcode,
                                                   'params': [self.filename]})
                    else:
                        event.ignore()

                    if self.filename.lower().rpartition('.')[-1] in self.app.svg_list:
                        object_type = 'geometry'
                        self.app.worker_task.emit({'fcn': self.app.import_svg,
                                                   'params': [self.filename, object_type, None]})

                    if self.filename.lower().rpartition('.')[-1] in self.app.dxf_list:
                        object_type = 'geometry'
                        self.app.worker_task.emit({'fcn': self.app.import_dxf,
                                                   'params': [self.filename, object_type, None]})

                    if self.filename.lower().rpartition('.')[-1] in self.app.prj_list:
                        # self.app.open_project() is not Thread Safe
                        self.app.open_project(self.filename)
                    else:
                        event.ignore()
        else:
            event.ignore()

    def closeEvent(self, event):
        grect = self.geometry()

        # self.splitter.sizes()[0] is actually the size of the "notebook"
        self.geom_update.emit(grect.x(), grect.y(), grect.width(), grect.height(), self.splitter.sizes()[0])
        self.final_save.emit()
        QtWidgets.qApp.quit()


class GeneralPreferencesUI(QtWidgets.QWidget):
    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)
        self.layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.layout)

        self.general_group = GeneralPrefGroupUI()
        self.general_group.setFixedWidth(260)
        self.layout.addWidget(self.general_group)


class GerberPreferencesUI(QtWidgets.QWidget):

    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)
        self.layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.layout)

        self.gerber_group = GerberPrefGroupUI()
        self.gerber_group.setFixedWidth(260)
        self.layout.addWidget(self.gerber_group)


class ExcellonPreferencesUI(QtWidgets.QWidget):

    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)
        self.layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.layout)

        self.excellon_group = ExcellonPrefGroupUI()
        self.excellon_group.setFixedWidth(260)
        self.layout.addWidget(self.excellon_group)


class GeometryPreferencesUI(QtWidgets.QWidget):

    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)
        self.layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.layout)

        self.geometry_group = GeometryPrefGroupUI()
        self.geometry_group.setFixedWidth(260)
        self.layout.addWidget(self.geometry_group)


class CNCJobPreferencesUI(QtWidgets.QWidget):

    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)
        self.layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.layout)

        self.cncjob_group = CNCJobPrefGroupUI()
        self.cncjob_group.setFixedWidth(260)
        self.layout.addWidget(self.cncjob_group)


class OptionsGroupUI(QtWidgets.QGroupBox):
    def __init__(self, title, parent=None):
        # QtGui.QGroupBox.__init__(self, title, parent=parent)
        super(OptionsGroupUI, self).__init__()
        self.setStyleSheet("""
        QGroupBox
        {
            font-size: 16px;
            font-weight: bold;
        }
        """)

        self.layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.layout)


class GeneralPrefGroupUI(OptionsGroupUI):
    def __init__(self, parent=None):
        super(GeneralPrefGroupUI, self).__init__(self)

        self.setTitle(str("Global Preferences"))

        # Create a form layout for the Application general settings
        self.form_box = QtWidgets.QFormLayout()

        # Units for FlatCAM
        self.unitslabel = QtWidgets.QLabel('<b>Units:</b>')
        self.unitslabel.setToolTip("Those are units in which FlatCAM works.")
        self.units_radio = RadioSet([{'label': 'IN', 'value': 'IN'},
                                     {'label': 'MM', 'value': 'MM'}])

        # Shell StartUp CB
        self.shell_startup_label = QtWidgets.QLabel('Shell at StartUp:')
        self.shell_startup_label.setToolTip(
            "Check this box if you want the shell to\n"
            "start automatically at startup."
        )
        self.shell_startup_cb = FCCheckBox(label='')
        self.shell_startup_cb.setToolTip(
            "Check this box if you want the shell to\n"
            "start automatically at startup."
        )

        # Version Check CB
        self.version_check_label = QtWidgets.QLabel('Version Check:')
        self.version_check_label.setToolTip(
            "Check this box if you want to check\n"
            "for a new version automatically at startup."
        )
        self.version_check_cb = FCCheckBox(label='')
        self.version_check_cb.setToolTip(
            "Check this box if you want to check\n"
            "for a new version automatically at startup."
        )

        # Send Stats CB
        self.send_stats_label = QtWidgets.QLabel('Send Stats:')
        self.send_stats_label.setToolTip(
            "Check this box if you agree to send anonymous\n"
            "stats automatically at startup, to help improve FlatCAM."
        )
        self.send_stats_cb= FCCheckBox(label='')
        self.send_stats_cb.setToolTip(
            "Check this box if you agree to send anonymous\n"
            "stats automatically at startup, to help improve FlatCAM."
        )

        self.ois_version_check = OptionalInputSection(self.version_check_cb, [self.send_stats_cb])

        # Grid X Entry
        self.gridx_label = QtWidgets.QLabel('Grid X value:')
        self.gridx_label.setToolTip(
            "This is the Grid value on X axis\n"
        )
        self.gridx_entry = LengthEntry()

        # Grid Y Entry
        self.gridy_label = QtWidgets.QLabel('Grid Y value:')
        self.gridy_label.setToolTip(
            "This is the Grid value on Y axis\n"
        )
        self.gridy_entry = LengthEntry()

        # Select mouse pan button
        self.panbuttonlabel = QtWidgets.QLabel('<b>Pan Button:</b>')
        self.panbuttonlabel.setToolTip("Select the mouse button to use for panning.")
        self.pan_button_radio = RadioSet([{'label': 'Middle But.', 'value': '3'},
                                     {'label': 'Right But.', 'value': '2'}])

        # Multiple Selection Modifier Key
        self.mselectlabel = QtWidgets.QLabel('<b>Multiple Sel:</b>')
        self.mselectlabel.setToolTip("Select the key used for multiple selection.")
        self.mselect_radio = RadioSet([{'label': 'CTRL', 'value': 'Control'},
                                     {'label': 'SHIFT', 'value': 'Shift'}])

        # # Mouse panning with "Space" key, CB
        # self.pan_with_space_label = QtWidgets.QLabel('Pan w/ Space:')
        # self.pan_with_space_label.setToolTip(
        #     "Check this box if you want to pan when mouse is moved,\n"
        #     "and key 'Space' is pressed."
        # )
        # self.pan_with_space_cb = FCCheckBox(label='')
        # self.pan_with_space_cb.setToolTip(
        #     "Check this box if you want to pan when mouse is moved,\n"
        #     "and key 'Space' is pressed."
        # )

        # Workspace
        self.workspace_lbl = QtWidgets.QLabel('Workspace:')
        self.workspace_lbl.setToolTip(
            "Draw a delimiting rectangle on canvas.\n"
            "The purpose is to illustrate the limits for our work."
        )
        self.workspace_type_lbl = QtWidgets.QLabel('Wk. format:')
        self.workspace_type_lbl.setToolTip(
            "Select the type of rectangle to be used on canvas,\n"
            "as valid workspace."
        )
        self.workspace_cb = FCCheckBox()
        self.wk_cb = FCComboBox()
        self.wk_cb.addItem('A4P')
        self.wk_cb.addItem('A4L')
        self.wk_cb.addItem('A3P')
        self.wk_cb.addItem('A3L')

        self.wks = OptionalInputSection(self.workspace_cb, [self.workspace_type_lbl, self.wk_cb])

        # Plot Fill Color
        self.pf_color_label = QtWidgets.QLabel('Plot Fill:')
        self.pf_color_label.setToolTip(
            "Set the fill color for plotted objects.\n"
            "First 6 digits are the color and the last 2\n"
            "digits are for alpha (transparency) level."
        )
        self.pf_color_entry = FCEntry()
        self.pf_color_button = QtWidgets.QPushButton()
        self.pf_color_button.setFixedSize(15, 15)

        self.form_box_child_1 = QtWidgets.QHBoxLayout()
        self.form_box_child_1.addWidget(self.pf_color_entry)
        self.form_box_child_1.addWidget(self.pf_color_button)
        self.form_box_child_1.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        # Plot Fill Transparency Level
        self.pf_alpha_label = QtWidgets.QLabel('Alpha Level:')
        self.pf_alpha_label.setToolTip(
            "Set the fill transparency for plotted objects."
        )
        self.pf_color_alpha_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.pf_color_alpha_slider.setMinimum(0)
        self.pf_color_alpha_slider.setMaximum(255)
        self.pf_color_alpha_slider.setSingleStep(1)

        self.pf_color_alpha_spinner = FCSpinner()
        self.pf_color_alpha_spinner.setFixedWidth(70)
        self.pf_color_alpha_spinner.setMinimum(0)
        self.pf_color_alpha_spinner.setMaximum(255)

        self.form_box_child_2 = QtWidgets.QHBoxLayout()
        self.form_box_child_2.addWidget(self.pf_color_alpha_slider)
        self.form_box_child_2.addWidget(self.pf_color_alpha_spinner)

        # Plot Line Color
        self.pl_color_label = QtWidgets.QLabel('Plot Line:')
        self.pl_color_label.setToolTip(
            "Set the line color for plotted objects."
        )
        self.pl_color_entry = FCEntry()
        self.pl_color_button = QtWidgets.QPushButton()
        self.pl_color_button.setFixedSize(15, 15)

        self.form_box_child_3 = QtWidgets.QHBoxLayout()
        self.form_box_child_3.addWidget(self.pl_color_entry)
        self.form_box_child_3.addWidget(self.pl_color_button)
        self.form_box_child_3.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        # Plot Selection (left - right) Fill Color
        self.sf_color_label = QtWidgets.QLabel('Sel. Fill:')
        self.sf_color_label.setToolTip(
            "Set the fill color for the selection box\n"
            "in case that the selection is done from left to right.\n"
            "First 6 digits are the color and the last 2\n"
            "digits are for alpha (transparency) level."
        )
        self.sf_color_entry = FCEntry()
        self.sf_color_button = QtWidgets.QPushButton()
        self.sf_color_button.setFixedSize(15, 15)

        self.form_box_child_4 = QtWidgets.QHBoxLayout()
        self.form_box_child_4.addWidget(self.sf_color_entry)
        self.form_box_child_4.addWidget(self.sf_color_button)
        self.form_box_child_4.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        # Plot Selection (left - right) Fill Transparency Level
        self.sf_alpha_label = QtWidgets.QLabel('Alpha Level:')
        self.sf_alpha_label.setToolTip(
            "Set the fill transparency for the 'left to right' selection box."
        )
        self.sf_color_alpha_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.sf_color_alpha_slider.setMinimum(0)
        self.sf_color_alpha_slider.setMaximum(255)
        self.sf_color_alpha_slider.setSingleStep(1)

        self.sf_color_alpha_spinner = FCSpinner()
        self.sf_color_alpha_spinner.setFixedWidth(70)
        self.sf_color_alpha_spinner.setMinimum(0)
        self.sf_color_alpha_spinner.setMaximum(255)

        self.form_box_child_5 = QtWidgets.QHBoxLayout()
        self.form_box_child_5.addWidget(self.sf_color_alpha_slider)
        self.form_box_child_5.addWidget(self.sf_color_alpha_spinner)

        # Plot Selection (left - right) Line Color
        self.sl_color_label = QtWidgets.QLabel('Sel. Line:')
        self.sl_color_label.setToolTip(
            "Set the line color for the 'left to right' selection box."
        )
        self.sl_color_entry = FCEntry()
        self.sl_color_button = QtWidgets.QPushButton()
        self.sl_color_button.setFixedSize(15, 15)

        self.form_box_child_6 = QtWidgets.QHBoxLayout()
        self.form_box_child_6.addWidget(self.sl_color_entry)
        self.form_box_child_6.addWidget(self.sl_color_button)
        self.form_box_child_6.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        # Plot Selection (right - left) Fill Color
        self.alt_sf_color_label = QtWidgets.QLabel('Sel2. Fill:')
        self.alt_sf_color_label.setToolTip(
            "Set the fill color for the selection box\n"
            "in case that the selection is done from right to left.\n"
            "First 6 digits are the color and the last 2\n"
            "digits are for alpha (transparency) level."
        )
        self.alt_sf_color_entry = FCEntry()
        self.alt_sf_color_button = QtWidgets.QPushButton()
        self.alt_sf_color_button.setFixedSize(15, 15)

        self.form_box_child_7 = QtWidgets.QHBoxLayout()
        self.form_box_child_7.addWidget(self.alt_sf_color_entry)
        self.form_box_child_7.addWidget(self.alt_sf_color_button)
        self.form_box_child_7.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        # Plot Selection (right - left) Fill Transparency Level
        self.alt_sf_alpha_label = QtWidgets.QLabel('Alpha Level:')
        self.alt_sf_alpha_label.setToolTip(
            "Set the fill transparency for selection 'right to left' box."
        )
        self.alt_sf_color_alpha_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.alt_sf_color_alpha_slider.setMinimum(0)
        self.alt_sf_color_alpha_slider.setMaximum(255)
        self.alt_sf_color_alpha_slider.setSingleStep(1)

        self.alt_sf_color_alpha_spinner = FCSpinner()
        self.alt_sf_color_alpha_spinner.setFixedWidth(70)
        self.alt_sf_color_alpha_spinner.setMinimum(0)
        self.alt_sf_color_alpha_spinner.setMaximum(255)

        self.form_box_child_8 = QtWidgets.QHBoxLayout()
        self.form_box_child_8.addWidget(self.alt_sf_color_alpha_slider)
        self.form_box_child_8.addWidget(self.alt_sf_color_alpha_spinner)

        # Plot Selection (right - left) Line Color
        self.alt_sl_color_label = QtWidgets.QLabel('Sel2. Line:')
        self.alt_sl_color_label.setToolTip(
            "Set the line color for the 'right to left' selection box."
        )
        self.alt_sl_color_entry = FCEntry()
        self.alt_sl_color_button = QtWidgets.QPushButton()
        self.alt_sl_color_button.setFixedSize(15, 15)

        self.form_box_child_9 = QtWidgets.QHBoxLayout()
        self.form_box_child_9.addWidget(self.alt_sl_color_entry)
        self.form_box_child_9.addWidget(self.alt_sl_color_button)
        self.form_box_child_9.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        # Editor Draw Color
        self.draw_color_label = QtWidgets.QLabel('Editor Draw:')
        self.alt_sf_color_label.setToolTip(
            "Set the color for the shape."
        )
        self.draw_color_entry = FCEntry()
        self.draw_color_button = QtWidgets.QPushButton()
        self.draw_color_button.setFixedSize(15, 15)

        self.form_box_child_10 = QtWidgets.QHBoxLayout()
        self.form_box_child_10.addWidget(self.draw_color_entry)
        self.form_box_child_10.addWidget(self.draw_color_button)
        self.form_box_child_10.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        # Editor Draw Selection Color
        self.sel_draw_color_label = QtWidgets.QLabel('Editor Draw Sel.:')
        self.sel_draw_color_label.setToolTip(
            "Set the color of the shape when selected."
        )
        self.sel_draw_color_entry = FCEntry()
        self.sel_draw_color_button = QtWidgets.QPushButton()
        self.sel_draw_color_button.setFixedSize(15, 15)

        self.form_box_child_11 = QtWidgets.QHBoxLayout()
        self.form_box_child_11.addWidget(self.sel_draw_color_entry)
        self.form_box_child_11.addWidget(self.sel_draw_color_button)
        self.form_box_child_11.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        # Just to add empty rows
        self.spacelabel = QtWidgets.QLabel('')

        # Add (label - input field) pair to the QFormLayout
        self.form_box.addRow(self.unitslabel, self.units_radio)
        self.form_box.addRow(self.spacelabel, self.spacelabel)
        self.form_box.addRow(self.shell_startup_label, self.shell_startup_cb)
        self.form_box.addRow(self.version_check_label, self.version_check_cb)
        self.form_box.addRow(self.send_stats_label, self.send_stats_cb)

        self.form_box.addRow(self.gridx_label, self.gridx_entry)
        self.form_box.addRow(self.gridy_label, self.gridy_entry)
        self.form_box.addRow(self.panbuttonlabel, self.pan_button_radio)
        self.form_box.addRow(self.mselectlabel, self.mselect_radio)
        # self.form_box.addRow(self.pan_with_space_label, self.pan_with_space_cb)
        self.form_box.addRow(self.workspace_lbl, self.workspace_cb)
        self.form_box.addRow(self.workspace_type_lbl, self.wk_cb)
        self.form_box.addRow(self.spacelabel, self.spacelabel)
        self.form_box.addRow(self.pf_color_label, self.form_box_child_1)
        self.form_box.addRow(self.pf_alpha_label, self.form_box_child_2)
        self.form_box.addRow(self.pl_color_label, self.form_box_child_3)
        self.form_box.addRow(self.sf_color_label, self.form_box_child_4)
        self.form_box.addRow(self.sf_alpha_label, self.form_box_child_5)
        self.form_box.addRow(self.sl_color_label, self.form_box_child_6)
        self.form_box.addRow(self.alt_sf_color_label, self.form_box_child_7)
        self.form_box.addRow(self.alt_sf_alpha_label, self.form_box_child_8)
        self.form_box.addRow(self.alt_sl_color_label, self.form_box_child_9)
        self.form_box.addRow(self.draw_color_label, self.form_box_child_10)
        self.form_box.addRow(self.sel_draw_color_label, self.form_box_child_11)

        # Add the QFormLayout that holds the Application general defaults
        # to the main layout of this TAB
        self.layout.addLayout(self.form_box)


class GerberPrefGroupUI(OptionsGroupUI):
    def __init__(self, parent=None):
        # OptionsGroupUI.__init__(self, "Gerber Options", parent=parent)
        super(GerberPrefGroupUI, self).__init__(self)

        self.setTitle(str("Gerber Options"))

        ## Plot options
        self.plot_options_label = QtWidgets.QLabel("<b>Plot Options:</b>")
        self.layout.addWidget(self.plot_options_label)

        grid0 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid0)
        # Plot CB
        self.plot_cb = FCCheckBox(label='Plot')
        self.plot_options_label.setToolTip(
            "Plot (show) this object."
        )
        grid0.addWidget(self.plot_cb, 0, 0)

        # Solid CB
        self.solid_cb = FCCheckBox(label='Solid')
        self.solid_cb.setToolTip(
            "Solid color polygons."
        )
        grid0.addWidget(self.solid_cb, 0, 1)

        # Multicolored CB
        self.multicolored_cb = FCCheckBox(label='Multicolored')
        self.multicolored_cb.setToolTip(
            "Draw polygons in different colors."
        )
        grid0.addWidget(self.multicolored_cb, 0, 2)

        # Number of circle steps for circular aperture linear approximation
        self.circle_steps_label = QtWidgets.QLabel("Circle Steps:")
        self.circle_steps_label.setToolTip(
            "The number of circle steps for Gerber \n"
            "circular aperture linear approximation."
        )
        grid0.addWidget(self.circle_steps_label, 1, 0)
        self.circle_steps_entry = IntEntry()
        grid0.addWidget(self.circle_steps_entry, 1, 1)

        ## Isolation Routing
        self.isolation_routing_label = QtWidgets.QLabel("<b>Isolation Routing:</b>")
        self.isolation_routing_label.setToolTip(
            "Create a Geometry object with\n"
            "toolpaths to cut outside polygons."
        )
        self.layout.addWidget(self.isolation_routing_label)

        # Cutting Tool Diameter
        grid1 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid1)
        tdlabel = QtWidgets.QLabel('Tool dia:')
        tdlabel.setToolTip(
            "Diameter of the cutting tool."
        )
        grid1.addWidget(tdlabel, 0, 0)
        self.iso_tool_dia_entry = LengthEntry()
        grid1.addWidget(self.iso_tool_dia_entry, 0, 1)

        # Nr of passes
        passlabel = QtWidgets.QLabel('Width (# passes):')
        passlabel.setToolTip(
            "Width of the isolation gap in\n"
            "number (integer) of tool widths."
        )
        grid1.addWidget(passlabel, 1, 0)
        self.iso_width_entry = IntEntry()
        grid1.addWidget(self.iso_width_entry, 1, 1)

        # Pass overlap
        overlabel = QtWidgets.QLabel('Pass overlap:')
        overlabel.setToolTip(
            "How much (fraction) of the tool width to overlap each tool pass.\n"
            "Example:\n"
            "A value here of 0.25 means an overlap of 25% from the tool diameter found above."
        )
        grid1.addWidget(overlabel, 2, 0)
        self.iso_overlap_entry = FloatEntry()
        grid1.addWidget(self.iso_overlap_entry, 2, 1)

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

        # Combine passes
        self.combine_passes_cb = FCCheckBox(label='Combine Passes')
        self.combine_passes_cb.setToolTip(
            "Combine all passes into one object"
        )
        grid1.addWidget(self.combine_passes_cb, 4, 0)

        ## Clear non-copper regions
        self.clearcopper_label = QtWidgets.QLabel("<b>Clear non-copper:</b>")
        self.clearcopper_label.setToolTip(
            "Create a Geometry object with\n"
            "toolpaths to cut all non-copper regions."
        )
        self.layout.addWidget(self.clearcopper_label)

        grid5 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid5)
        ncctdlabel = QtWidgets.QLabel('Tools dia:')
        ncctdlabel.setToolTip(
            "Diameters of the cutting tools, separated by ','"
        )
        grid5.addWidget(ncctdlabel, 0, 0)
        self.ncc_tool_dia_entry = FCEntry()
        grid5.addWidget(self.ncc_tool_dia_entry, 0, 1)

        nccoverlabel = QtWidgets.QLabel('Overlap:')
        nccoverlabel.setToolTip(
            "How much (fraction) of the tool width to overlap each tool pass.\n"
            "Example:\n"
            "A value here of 0.25 means 25% from the tool diameter found above.\n\n"
            "Adjust the value starting with lower values\n"
            "and increasing it if areas that should be cleared are still \n"
            "not cleared.\n"
            "Lower values = faster processing, faster execution on PCB.\n"
            "Higher values = slow processing and slow execution on CNC\n"
            "due of too many paths."
        )
        grid5.addWidget(nccoverlabel, 1, 0)
        self.ncc_overlap_entry = FloatEntry()
        grid5.addWidget(self.ncc_overlap_entry, 1, 1)

        nccmarginlabel = QtWidgets.QLabel('Margin:')
        nccmarginlabel.setToolTip(
            "Bounding box margin."
        )
        grid5.addWidget(nccmarginlabel, 2, 0)
        self.ncc_margin_entry = FloatEntry()
        grid5.addWidget(self.ncc_margin_entry, 2, 1)

        # Method
        methodlabel = QtWidgets.QLabel('Method:')
        methodlabel.setToolTip(
            "Algorithm for non-copper clearing:<BR>"
            "<B>Standard</B>: Fixed step inwards.<BR>"
            "<B>Seed-based</B>: Outwards from seed.<BR>"
            "<B>Line-based</B>: Parallel lines."
        )
        grid5.addWidget(methodlabel, 3, 0)
        self.ncc_method_radio = RadioSet([
            {"label": "Standard", "value": "standard"},
            {"label": "Seed-based", "value": "seed"},
            {"label": "Straight lines", "value": "lines"}
        ], orientation='vertical', stretch=False)
        grid5.addWidget(self.ncc_method_radio, 3, 1)

        # Connect lines
        pathconnectlabel = QtWidgets.QLabel("Connect:")
        pathconnectlabel.setToolTip(
            "Draw lines between resulting\n"
            "segments to minimize tool lifts."
        )
        grid5.addWidget(pathconnectlabel, 4, 0)
        self.ncc_connect_cb = FCCheckBox()
        grid5.addWidget(self.ncc_connect_cb, 4, 1)

        contourlabel = QtWidgets.QLabel("Contour:")
        contourlabel.setToolTip(
            "Cut around the perimeter of the polygon\n"
            "to trim rough edges."
        )
        grid5.addWidget(contourlabel, 5, 0)
        self.ncc_contour_cb = FCCheckBox()
        grid5.addWidget(self.ncc_contour_cb, 5, 1)

        restlabel = QtWidgets.QLabel("Rest M.:")
        restlabel.setToolTip(
            "If checked, use 'rest machining'.\n"
            "Basically it will clear copper outside PCB features,\n"
            "using the biggest tool and continue with the next tools,\n"
            "from bigger to smaller, to clear areas of copper that\n"
            "could not be cleared by previous tool.\n"
            "If not checked, use the standard algorithm."
        )
        grid5.addWidget(restlabel, 6, 0)
        self.ncc_rest_cb = FCCheckBox()
        grid5.addWidget(self.ncc_rest_cb, 6, 1)

        ## Board cuttout
        self.board_cutout_label = QtWidgets.QLabel("<b>Board cutout:</b>")
        self.board_cutout_label.setToolTip(
            "Create toolpaths to cut around\n"
            "the PCB and separate it from\n"
            "the original board."
        )
        self.layout.addWidget(self.board_cutout_label)

        grid2 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid2)
        tdclabel = QtWidgets.QLabel('Tool dia:')
        tdclabel.setToolTip(
            "Diameter of the cutting tool."
        )
        grid2.addWidget(tdclabel, 0, 0)
        self.cutout_tooldia_entry = LengthEntry()
        grid2.addWidget(self.cutout_tooldia_entry, 0, 1)

        marginlabel = QtWidgets.QLabel('Margin:')
        marginlabel.setToolTip(
            "Distance from objects at which\n"
            "to draw the cutout."
        )
        grid2.addWidget(marginlabel, 1, 0)
        self.cutout_margin_entry = LengthEntry()
        grid2.addWidget(self.cutout_margin_entry, 1, 1)

        gaplabel = QtWidgets.QLabel('Gap size:')
        gaplabel.setToolTip(
            "Size of the gaps in the toolpath\n"
            "that will remain to hold the\n"
            "board in place."
        )
        grid2.addWidget(gaplabel, 2, 0)
        self.cutout_gap_entry = LengthEntry()
        grid2.addWidget(self.cutout_gap_entry, 2, 1)

        gapslabel = QtWidgets.QLabel('Gaps:')
        gapslabel.setToolTip(
            "Where to place the gaps, Top/Bottom\n"
            "Left/Rigt, or on all 4 sides."
        )
        grid2.addWidget(gapslabel, 3, 0)
        self.gaps_radio = RadioSet([{'label': '2 (T/B)', 'value': 'tb'},
                                    {'label': '2 (L/R)', 'value': 'lr'},
                                    {'label': '4', 'value': '4'}])
        grid2.addWidget(self.gaps_radio, 3, 1)

        ## Non-copper regions
        self.noncopper_label = QtWidgets.QLabel("<b>Non-copper regions:</b>")
        self.noncopper_label.setToolTip(
            "Create polygons covering the\n"
            "areas without copper on the PCB.\n"
            "Equivalent to the inverse of this\n"
            "object. Can be used to remove all\n"
            "copper from a specified region."
        )
        self.layout.addWidget(self.noncopper_label)

        grid3 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid3)

        # Margin
        bmlabel = QtWidgets.QLabel('Boundary Margin:')
        bmlabel.setToolTip(
            "Specify the edge of the PCB\n"
            "by drawing a box around all\n"
            "objects with this minimum\n"
            "distance."
        )
        grid3.addWidget(bmlabel, 0, 0)
        self.noncopper_margin_entry = LengthEntry()
        grid3.addWidget(self.noncopper_margin_entry, 0, 1)

        # Rounded corners
        self.noncopper_rounded_cb = FCCheckBox(label="Rounded corners")
        self.noncopper_rounded_cb.setToolTip(
            "Creates a Geometry objects with polygons\n"
            "covering the copper-free areas of the PCB."
        )
        grid3.addWidget(self.noncopper_rounded_cb, 1, 0, 1, 2)

        ## Bounding box
        self.boundingbox_label = QtWidgets.QLabel('<b>Bounding Box:</b>')
        self.layout.addWidget(self.boundingbox_label)

        grid4 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid4)

        bbmargin = QtWidgets.QLabel('Boundary Margin:')
        bbmargin.setToolTip(
            "Distance of the edges of the box\n"
            "to the nearest polygon."
        )
        grid4.addWidget(bbmargin, 0, 0)
        self.bbmargin_entry = LengthEntry()
        grid4.addWidget(self.bbmargin_entry, 0, 1)

        self.bbrounded_cb = FCCheckBox(label="Rounded corners")
        self.bbrounded_cb.setToolTip(
            "If the bounding box is \n"
            "to have rounded corners\n"
            "their radius is equal to\n"
            "the margin."
        )
        grid4.addWidget(self.bbrounded_cb, 1, 0, 1, 2)
        self.layout.addStretch()


class ExcellonPrefGroupUI(OptionsGroupUI):

    def __init__(self, parent=None):
        # OptionsGroupUI.__init__(self, "Excellon Options", parent=parent)
        super(ExcellonPrefGroupUI, self).__init__(self)

        self.setTitle(str("Excellon Options"))

        # Plot options
        self.plot_options_label = QtWidgets.QLabel("<b>Plot Options:</b>")
        self.layout.addWidget(self.plot_options_label)

        grid1 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid1)
        self.plot_cb = FCCheckBox(label='Plot')
        self.plot_cb.setToolTip(
            "Plot (show) this object."
        )
        grid1.addWidget(self.plot_cb, 0, 0)
        self.solid_cb = FCCheckBox(label='Solid')
        self.solid_cb.setToolTip(
            "Solid circles."
        )
        grid1.addWidget(self.solid_cb, 0, 1)

        # Excellon format
        self.excellon_format_label = QtWidgets.QLabel("<b>Excellon Format:</b>")
        self.excellon_format_label.setToolTip(
            "The NC drill files, usually named Excellon files\n"
            "are files that can be found in different formats.\n"
            "Here we set the format used when the provided\n"
            "coordinates are not using period.\n"
            "\n"
            "Possible presets:\n"
            "\n"
            "PROTEUS 3:3 MM LZ\n"
            "DipTrace 5:2 MM TZ\n"
            "DipTrace 4:3 MM LZ\n"
            "\n"
            "EAGLE 3:3 MM TZ\n"
            "EAGLE 4:3 MM TZ\n"
            "EAGLE 2:5 INCH TZ\n"
            "EAGLE 3:5 INCH TZ\n"
            "\n"
            "ALTIUM 2:4 INCH LZ\n"
            "Sprint Layout 2:4 INCH LZ"
            "\n"
            "KiCAD 3:5 INCH TZ"
        )
        self.layout.addWidget(self.excellon_format_label)

        hlay1 = QtWidgets.QHBoxLayout()
        self.layout.addLayout(hlay1)
        self.excellon_format_in_label = QtWidgets.QLabel("INCH")
        self.excellon_format_in_label.setAlignment(QtCore.Qt.AlignLeft)
        self.excellon_format_in_label.setToolTip(
            "Default values for INCH are 2:4")
        hlay1.addWidget(self.excellon_format_in_label, QtCore.Qt.AlignLeft)

        self.excellon_format_upper_in_entry = IntEntry()
        self.excellon_format_upper_in_entry.setMaxLength(1)
        self.excellon_format_upper_in_entry.setAlignment(QtCore.Qt.AlignRight)
        self.excellon_format_upper_in_entry.setFixedWidth(30)
        self.excellon_format_upper_in_entry.setToolTip(
            "This numbers signify the number of digits in\n"
            "the whole part of Excellon coordinates."
        )
        hlay1.addWidget(self.excellon_format_upper_in_entry, QtCore.Qt.AlignLeft)

        excellon_separator_in_label= QtWidgets.QLabel(':')
        excellon_separator_in_label.setFixedWidth(5)
        hlay1.addWidget(excellon_separator_in_label, QtCore.Qt.AlignLeft)

        self.excellon_format_lower_in_entry = IntEntry()
        self.excellon_format_lower_in_entry.setMaxLength(1)
        self.excellon_format_lower_in_entry.setAlignment(QtCore.Qt.AlignRight)
        self.excellon_format_lower_in_entry.setFixedWidth(30)
        self.excellon_format_lower_in_entry.setToolTip(
            "This numbers signify the number of digits in\n"
            "the decimal part of Excellon coordinates."
        )
        hlay1.addWidget(self.excellon_format_lower_in_entry, QtCore.Qt.AlignLeft)
        hlay1.addStretch()

        hlay2 = QtWidgets.QHBoxLayout()
        self.layout.addLayout(hlay2)
        self.excellon_format_mm_label = QtWidgets.QLabel("METRIC")
        self.excellon_format_mm_label.setAlignment(QtCore.Qt.AlignLeft)
        self.excellon_format_mm_label.setToolTip(
            "Default values for METRIC are 3:3")
        hlay2.addWidget(self.excellon_format_mm_label, QtCore.Qt.AlignLeft)

        self.excellon_format_upper_mm_entry = IntEntry()
        self.excellon_format_upper_mm_entry.setMaxLength(1)
        self.excellon_format_upper_mm_entry.setAlignment(QtCore.Qt.AlignRight)
        self.excellon_format_upper_mm_entry.setFixedWidth(30)
        self.excellon_format_upper_mm_entry.setToolTip(
            "This numbers signify the number of digits in\n"
            "the whole part of Excellon coordinates."
        )
        hlay2.addWidget(self.excellon_format_upper_mm_entry, QtCore.Qt.AlignLeft)

        excellon_separator_mm_label= QtWidgets.QLabel(':')
        excellon_separator_mm_label.setFixedWidth(5)
        hlay2.addWidget(excellon_separator_mm_label, QtCore.Qt.AlignLeft)

        self.excellon_format_lower_mm_entry = IntEntry()
        self.excellon_format_lower_mm_entry.setMaxLength(1)
        self.excellon_format_lower_mm_entry.setAlignment(QtCore.Qt.AlignRight)
        self.excellon_format_lower_mm_entry.setFixedWidth(30)
        self.excellon_format_lower_mm_entry.setToolTip(
            "This numbers signify the number of digits in\n"
            "the decimal part of Excellon coordinates."
        )
        hlay2.addWidget(self.excellon_format_lower_mm_entry, QtCore.Qt.AlignLeft)
        hlay2.addStretch()

        hlay3 = QtWidgets.QHBoxLayout()
        self.layout.addLayout(hlay3)

        self.excellon_zeros_label = QtWidgets.QLabel('Excellon <b>Zeros</b> Type:')
        self.excellon_zeros_label.setAlignment(QtCore.Qt.AlignLeft)
        self.excellon_zeros_label.setToolTip(
            "This sets the type of excellon zeros.\n"
            "If LZ then Leading Zeros are kept and\n"
            "Trailing Zeros are removed.\n"
            "If TZ is checked then Trailing Zeros are kept\n"
            "and Leading Zeros are removed."
        )
        hlay3.addWidget(self.excellon_zeros_label)

        self.excellon_zeros_radio = RadioSet([{'label': 'LZ', 'value': 'L'},
                                     {'label': 'TZ', 'value': 'T'}])
        self.excellon_zeros_radio.setToolTip(
            "This sets the type of excellon zeros.\n"
            "If LZ then Leading Zeros are kept and\n"
            "Trailing Zeros are removed.\n"
            "If TZ is checked then Trailing Zeros are kept\n"
            "and Leading Zeros are removed."
        )
        hlay3.addStretch()
        hlay3.addWidget(self.excellon_zeros_radio, QtCore.Qt.AlignRight)

        hlay4 = QtWidgets.QHBoxLayout()
        self.layout.addLayout(hlay4)

        self.excellon_units_label = QtWidgets.QLabel('Excellon <b>Units</b> Type:')
        self.excellon_units_label.setAlignment(QtCore.Qt.AlignLeft)
        self.excellon_units_label.setToolTip(
            "This sets the units of Excellon files.\n"
            "Some Excellon files don't have an header\n"
            "therefore this parameter will be used.\n"
        )
        hlay4.addWidget(self.excellon_units_label)

        self.excellon_units_radio = RadioSet([{'label': 'INCH', 'value': 'INCH'},
                                              {'label': 'MM', 'value': 'METRIC'}])
        self.excellon_units_radio.setToolTip(
            "This sets the units of Excellon files.\n"
            "Some Excellon files don't have an header\n"
            "therefore this parameter will be used.\n"
        )
        hlay4.addStretch()
        hlay4.addWidget(self.excellon_units_radio, QtCore.Qt.AlignRight)

        hlay5 = QtWidgets.QVBoxLayout()
        self.layout.addLayout(hlay5)

        self.empty_label = QtWidgets.QLabel("")
        hlay5.addWidget(self.empty_label)

        hlay6 = QtWidgets.QVBoxLayout()
        self.layout.addLayout(hlay6)

        self.excellon_general_label = QtWidgets.QLabel("<b>Excellon Optimization:</b>")
        hlay6.addWidget(self.excellon_general_label)

        # Create a form layout for the Excellon general settings
        form_box_excellon = QtWidgets.QFormLayout()
        hlay6.addLayout(form_box_excellon)

        self.excellon_optimization_label = QtWidgets.QLabel('Path Optimization:   ')
        self.excellon_optimization_label.setAlignment(QtCore.Qt.AlignLeft)
        self.excellon_optimization_label.setToolTip(
            "This sets the optimization type for the Excellon drill path.\n"
            "If MH is checked then Google OR-Tools algorithm with MetaHeuristic\n"
            "Guided Local Path is used. Default search time is 3sec.\n"
            "Use set_sys excellon_search_time value Tcl Command to set other values.\n"
            "If Basic is checked then Google OR-Tools Basic algorithm is used.\n"
            "\n"
            "If DISABLED, then FlatCAM works in 32bit mode and it uses \n"
            "Travelling Salesman algorithm for path optimization."
        )

        self.excellon_optimization_radio = RadioSet([{'label': 'MH', 'value': 'M'},
                                     {'label': 'Basic', 'value': 'B'}])
        self.excellon_optimization_radio.setToolTip(
            "This sets the optimization type for the Excellon drill path.\n"
            "If MH is checked then Google OR-Tools algorithm with MetaHeuristic\n"
            "Guided Local Path is used. Default search time is 3sec.\n"
            "Use set_sys excellon_search_time value Tcl Command to set other values.\n"
            "If Basic is checked then Google OR-Tools Basic algorithm is used.\n"
            "\n"
            "If DISABLED, then FlatCAM works in 32bit mode and it uses \n"
            "Travelling Salesman algorithm for path optimization."
        )

        form_box_excellon.addRow(self.excellon_optimization_label, self.excellon_optimization_radio)

        current_platform = platform.architecture()[0]
        if current_platform == '64bit':
            self.excellon_optimization_label.setDisabled(False)
            self.excellon_optimization_radio.setDisabled(False)
        else:
            self.excellon_optimization_label.setDisabled(True)
            self.excellon_optimization_radio.setDisabled(True)

        ## Create CNC Job
        self.cncjob_label = QtWidgets.QLabel('<b>Create CNC Job</b>')
        self.cncjob_label.setToolTip(
            "Create a CNC Job object\n"
            "for this drill object."
        )
        self.layout.addWidget(self.cncjob_label)

        grid2 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid2)

        cutzlabel = QtWidgets.QLabel('Cut Z:')
        cutzlabel.setToolTip(
            "Drill depth (negative)\n"
            "below the copper surface."
        )
        grid2.addWidget(cutzlabel, 0, 0)
        self.cutz_entry = LengthEntry()
        grid2.addWidget(self.cutz_entry, 0, 1)

        travelzlabel = QtWidgets.QLabel('Travel Z:')
        travelzlabel.setToolTip(
            "Tool height when travelling\n"
            "across the XY plane."
        )
        grid2.addWidget(travelzlabel, 1, 0)
        self.travelz_entry = LengthEntry()
        grid2.addWidget(self.travelz_entry, 1, 1)

        # Tool change:
        toolchlabel = QtWidgets.QLabel("Tool change:")
        toolchlabel.setToolTip(
            "Include tool-change sequence\n"
            "in G-Code (Pause for tool change)."
        )
        self.toolchange_cb = FCCheckBox()
        grid2.addWidget(toolchlabel, 2, 0)
        grid2.addWidget(self.toolchange_cb, 2, 1)

        toolchangezlabel = QtWidgets.QLabel('Toolchange Z:')
        toolchangezlabel.setToolTip(
            "Toolchange Z position."
        )
        grid2.addWidget(toolchangezlabel, 3, 0)
        self.toolchangez_entry = LengthEntry()
        grid2.addWidget(self.toolchangez_entry, 3, 1)

        toolchange_xy_label = QtWidgets.QLabel('Toolchange X,Y:')
        toolchange_xy_label.setToolTip(
            "Toolchange X,Y position."
        )
        grid2.addWidget(toolchange_xy_label, 4, 0)
        self.toolchangexy_entry = FCEntry()
        grid2.addWidget(self.toolchangexy_entry, 4, 1)

        startzlabel = QtWidgets.QLabel('Start move Z:')
        startzlabel.setToolTip(
            "Height of the tool just after start.\n"
            "Delete the value if you don't need this feature."
        )
        grid2.addWidget(startzlabel, 5, 0)
        self.estartz_entry = FloatEntry()
        grid2.addWidget(self.estartz_entry, 5, 1)

        endzlabel = QtWidgets.QLabel('End move Z:')
        endzlabel.setToolTip(
            "Tool Z where user can change drill bit."
        )
        grid2.addWidget(endzlabel, 6, 0)
        self.eendz_entry = LengthEntry()
        grid2.addWidget(self.eendz_entry, 6, 1)

        frlabel = QtWidgets.QLabel('Feedrate (Plunge):')
        frlabel.setToolTip(
            "Tool speed while drilling\n"
            "(in units per minute)."
        )
        grid2.addWidget(frlabel, 7, 0)
        self.feedrate_entry = LengthEntry()
        grid2.addWidget(self.feedrate_entry, 7, 1)

        fr_rapid_label = QtWidgets.QLabel('Feedrate Rapids:')
        fr_rapid_label.setToolTip(
            "Tool speed while drilling\n"
            "with rapid move\n"
            "(in units per minute)."
        )
        grid2.addWidget(fr_rapid_label, 8, 0)
        self.feedrate_rapid_entry = LengthEntry()
        grid2.addWidget(self.feedrate_rapid_entry, 8, 1)

        # Spindle speed
        spdlabel = QtWidgets.QLabel('Spindle speed:')
        spdlabel.setToolTip(
            "Speed of the spindle\n"
            "in RPM (optional)"
        )
        grid2.addWidget(spdlabel, 9, 0)
        self.spindlespeed_entry = IntEntry(allow_empty=True)
        grid2.addWidget(self.spindlespeed_entry, 9, 1)

        # Dwell
        dwelllabel = QtWidgets.QLabel('Dwell:')
        dwelllabel.setToolTip(
            "Pause to allow the spindle to reach its\n"
            "speed before cutting."
        )
        dwelltime = QtWidgets.QLabel('Duration [m-sec.]:')
        dwelltime.setToolTip(
            "Number of milliseconds for spindle to dwell."
        )
        self.dwell_cb = FCCheckBox()
        self.dwelltime_entry = FCEntry()
        grid2.addWidget(dwelllabel, 10, 0)
        grid2.addWidget(self.dwell_cb, 10, 1)
        grid2.addWidget(dwelltime, 11, 0)
        grid2.addWidget(self.dwelltime_entry, 11, 1)

        self.ois_dwell_exc = OptionalInputSection(self.dwell_cb, [self.dwelltime_entry])

        # postprocessor selection
        pp_excellon_label = QtWidgets.QLabel("Postprocessor")
        pp_excellon_label.setToolTip(
            "The postprocessor file that dictates\n"
            "gcode output."
        )
        grid2.addWidget(pp_excellon_label, 12, 0)
        self.pp_excellon_name_cb = FCComboBox()
        self.pp_excellon_name_cb.setFocusPolicy(Qt.StrongFocus)
        grid2.addWidget(self.pp_excellon_name_cb, 12, 1)

        #### Choose what to use for Gcode creation: Drills, Slots or Both
        excellon_gcode_type_label = QtWidgets.QLabel('<b>Gcode:    </b>')
        excellon_gcode_type_label.setToolTip(
            "Choose what to use for GCode generation:\n"
            "'Drills', 'Slots' or 'Both'.\n"
            "When choosing 'Slots' or 'Both', slots will be\n"
            "converted to drills."
        )
        self.excellon_gcode_type_radio = RadioSet([{'label': 'Drills', 'value': 'drills'},
                                          {'label': 'Slots', 'value': 'slots'},
                                          {'label': 'Both', 'value': 'both'}])
        grid2.addWidget(excellon_gcode_type_label, 13, 0)
        grid2.addWidget(self.excellon_gcode_type_radio, 13, 1)

        #### Milling Holes ####
        self.mill_hole_label = QtWidgets.QLabel('<b>Mill Holes</b>')
        self.mill_hole_label.setToolTip(
            "Create Geometry for milling holes."
        )
        self.layout.addWidget(self.mill_hole_label)

        grid3 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid3)
        tdlabel = QtWidgets.QLabel('Drill Tool dia:')
        tdlabel.setToolTip(
            "Diameter of the cutting tool."
        )
        grid3.addWidget(tdlabel, 0, 0)
        self.tooldia_entry = LengthEntry()
        grid3.addWidget(self.tooldia_entry, 0, 1)
        stdlabel = QtWidgets.QLabel('Slot Tool dia:')
        stdlabel.setToolTip(
            "Diameter of the cutting tool\n"
            "when milling slots."
        )
        grid3.addWidget(stdlabel, 1, 0)
        self.slot_tooldia_entry = LengthEntry()
        grid3.addWidget(self.slot_tooldia_entry, 1, 1)

        grid4 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid4)

        # Adding the Excellon Format Defaults Button
        self.excellon_defaults_button = QtWidgets.QPushButton()
        self.excellon_defaults_button.setText(str("Defaults"))
        self.excellon_defaults_button.setFixedWidth(80)
        grid4.addWidget(self.excellon_defaults_button, 0, 0, QtCore.Qt.AlignRight)

        self.layout.addStretch()


class GeometryPrefGroupUI(OptionsGroupUI):
    def __init__(self, parent=None):
        # OptionsGroupUI.__init__(self, "Geometry Options", parent=parent)
        super(GeometryPrefGroupUI, self).__init__(self)

        self.setTitle(str("Geometry Options"))

        ## Plot options
        self.plot_options_label = QtWidgets.QLabel("<b>Plot Options:</b>")
        self.layout.addWidget(self.plot_options_label)

        # Plot CB
        self.plot_cb = FCCheckBox(label='Plot')
        self.plot_cb.setToolTip(
            "Plot (show) this object."
        )
        self.layout.addWidget(self.plot_cb)

        grid0 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid0)
        # Number of circle steps for circular aperture linear approximation
        self.circle_steps_label = QtWidgets.QLabel("Circle Steps:")
        self.circle_steps_label.setToolTip(
            "The number of circle steps for <b>Geometry</b> \n"
            "circle and arc shapes linear approximation."
        )
        grid0.addWidget(self.circle_steps_label, 1, 0)
        self.circle_steps_entry = IntEntry()
        grid0.addWidget(self.circle_steps_entry, 1, 1)

        # Tools
        self.tools_label = QtWidgets.QLabel("<b>Tools</b>")
        self.layout.addWidget(self.tools_label)

        grid1 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid1)

        # Tooldia
        tdlabel = QtWidgets.QLabel('Tool dia:                   ')
        tdlabel.setToolTip(
            "The diameter of the cutting\n"
            "tool (just for display)."
        )
        grid1.addWidget(tdlabel, 0, 0)
        self.cnctooldia_entry = LengthEntry()
        grid1.addWidget(self.cnctooldia_entry, 0, 1)

        # ------------------------------
        ## Create CNC Job
        # ------------------------------
        self.cncjob_label = QtWidgets.QLabel('<b>Create CNC Job:</b>')
        self.cncjob_label.setToolTip(
            "Create a CNC Job object\n"
            "tracing the contours of this\n"
            "Geometry object."
        )
        self.layout.addWidget(self.cncjob_label)

        grid2 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid2)

        # Cut Z
        cutzlabel = QtWidgets.QLabel('Cut Z:')
        cutzlabel.setToolTip(
            "Cutting depth (negative)\n"
            "below the copper surface."
        )
        grid2.addWidget(cutzlabel, 0, 0)
        self.cutz_entry = LengthEntry()
        grid2.addWidget(self.cutz_entry, 0, 1)

        # Multidepth CheckBox
        self.multidepth_cb = FCCheckBox(label='Multidepth')
        self.multidepth_cb.setToolTip(
            "Multidepth usage: True or False."
        )
        grid2.addWidget(self.multidepth_cb, 1, 0)

        # Depth/pass
        dplabel = QtWidgets.QLabel('Depth/Pass:')
        dplabel.setToolTip(
            "The depth to cut on each pass,\n"
            "when multidepth is enabled."
        )

        grid2.addWidget(dplabel, 2, 0)
        self.depthperpass_entry = LengthEntry()
        grid2.addWidget(self.depthperpass_entry, 2, 1)

        self.ois_multidepth = OptionalInputSection(self.multidepth_cb, [self.depthperpass_entry])

        # Travel Z
        travelzlabel = QtWidgets.QLabel('Travel Z:')
        travelzlabel.setToolTip(
            "Height of the tool when\n"
            "moving without cutting."
        )
        grid2.addWidget(travelzlabel, 3, 0)
        self.travelz_entry = LengthEntry()
        grid2.addWidget(self.travelz_entry, 3, 1)

        # Tool change:
        toolchlabel = QtWidgets.QLabel("Tool change:")
        toolchlabel.setToolTip(
            "Include tool-change sequence\n"
            "in G-Code (Pause for tool change)."
        )
        self.toolchange_cb = FCCheckBox()
        grid2.addWidget(toolchlabel, 4, 0)
        grid2.addWidget(self.toolchange_cb, 4, 1)

        # Toolchange Z
        toolchangezlabel = QtWidgets.QLabel('Toolchange Z:')
        toolchangezlabel.setToolTip(
            "Toolchange Z position."
        )
        grid2.addWidget(toolchangezlabel, 5, 0)
        self.toolchangez_entry = LengthEntry()
        grid2.addWidget(self.toolchangez_entry, 5, 1)

        # Toolchange X,Y
        toolchange_xy_label = QtWidgets.QLabel('Toolchange X,Y:')
        toolchange_xy_label.setToolTip(
            "Toolchange X,Y position."
        )
        grid2.addWidget(toolchange_xy_label, 6, 0)
        self.toolchangexy_entry = FCEntry()
        grid2.addWidget(self.toolchangexy_entry, 6, 1)

        # Start move Z
        startzlabel = QtWidgets.QLabel('Start move Z:')
        startzlabel.setToolTip(
            "Height of the tool just\n"
            "after starting the work.\n"
            "Delete the value if you don't need this feature."
        )
        grid2.addWidget(startzlabel, 7, 0)
        self.gstartz_entry = FloatEntry()
        grid2.addWidget(self.gstartz_entry, 7, 1)

        # End move Z
        endzlabel = QtWidgets.QLabel('End move Z:')
        endzlabel.setToolTip(
            "Height of the tool after\n"
            " the last move."
        )
        grid2.addWidget(endzlabel, 8, 0)
        self.gendz_entry = LengthEntry()
        grid2.addWidget(self.gendz_entry, 8, 1)

        # Feedrate X-Y
        frlabel = QtWidgets.QLabel('Feed Rate X-Y:')
        frlabel.setToolTip(
            "Cutting speed in the XY\n"
            "plane in units per minute"
        )
        grid2.addWidget(frlabel, 9, 0)
        self.cncfeedrate_entry = LengthEntry()
        grid2.addWidget(self.cncfeedrate_entry, 9, 1)

        # Feedrate Z (Plunge)
        frz_label = QtWidgets.QLabel('Feed Rate Z (Plunge):')
        frz_label.setToolTip(
            "Cutting speed in the XY\n"
            "plane in units per minute"
        )
        grid2.addWidget(frz_label, 10, 0)
        self.cncplunge_entry = LengthEntry()
        grid2.addWidget(self.cncplunge_entry, 10, 1)

        # Feedrate rapids
        fr_rapid_label = QtWidgets.QLabel('Feed Rate Rapids:')
        fr_rapid_label.setToolTip(
            "Cutting speed in the XY\n"
            "plane in units per minute"
        )
        grid2.addWidget(fr_rapid_label, 11, 0)
        self.cncfeedrate_rapid_entry = LengthEntry()
        grid2.addWidget(self.cncfeedrate_rapid_entry, 11, 1)

        # End move extra cut
        self.extracut_cb = FCCheckBox(label='Cut over 1st pt.')
        self.extracut_cb.setToolTip(
            "In order to remove possible\n"
            "copper leftovers where first cut\n"
            "meet with last cut, we generate an\n"
            "extended cut over the first cut section."
        )
        grid2.addWidget(self.extracut_cb, 12, 0)

        # Spindle Speed
        spdlabel = QtWidgets.QLabel('Spindle speed:')
        spdlabel.setToolTip(
            "Speed of the spindle\n"
            "in RPM (optional)"
        )
        grid2.addWidget(spdlabel, 13, 0)
        self.cncspindlespeed_entry = IntEntry(allow_empty=True)
        grid2.addWidget(self.cncspindlespeed_entry, 13, 1)

        # Dwell
        self.dwell_cb = FCCheckBox(label='Dwell:')
        self.dwell_cb.setToolTip(
            "Pause to allow the spindle to reach its\n"
            "speed before cutting."
        )
        dwelltime = QtWidgets.QLabel('Duration [m-sec.]:')
        dwelltime.setToolTip(
            "Number of milliseconds for spindle to dwell."
        )
        self.dwelltime_entry = FCEntry()
        grid2.addWidget(self.dwell_cb, 14, 0)
        grid2.addWidget(dwelltime, 15, 0)
        grid2.addWidget(self.dwelltime_entry, 15, 1)

        grid3 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid3)

        self.ois_dwell = OptionalInputSection(self.dwell_cb, [self.dwelltime_entry])

        # postprocessor selection
        pp_label = QtWidgets.QLabel("Postprocessor")
        pp_label.setToolTip(
            "The postprocessor file that dictates\n"
            "gcode output."
        )
        grid3.addWidget(pp_label)
        self.pp_geometry_name_cb = FCComboBox()
        self.pp_geometry_name_cb.setFocusPolicy(Qt.StrongFocus)
        grid3.addWidget(self.pp_geometry_name_cb)

        # ------------------------------
        ## Paint area
        # ------------------------------
        self.paint_label = QtWidgets.QLabel('<b>Paint Area:</b>')
        self.paint_label.setToolTip(
            "Creates tool paths to cover the\n"
            "whole area of a polygon (remove\n"
            "all copper). You will be asked\n"
            "to click on the desired polygon."
        )
        self.layout.addWidget(self.paint_label)

        grid4 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid4)

        # Tool dia
        ptdlabel = QtWidgets.QLabel('Tool dia:')
        ptdlabel.setToolTip(
            "Diameter of the tool to\n"
            "be used in the operation."
        )
        grid4.addWidget(ptdlabel, 0, 0)

        self.painttooldia_entry = LengthEntry()
        grid4.addWidget(self.painttooldia_entry, 0, 1)

        # Overlap
        ovlabel = QtWidgets.QLabel('Overlap:')
        ovlabel.setToolTip(
            "How much (fraction) of the tool\n"
            "width to overlap each tool pass."
        )
        grid4.addWidget(ovlabel, 1, 0)
        self.paintoverlap_entry = LengthEntry()
        grid4.addWidget(self.paintoverlap_entry, 1, 1)

        # Margin
        marginlabel = QtWidgets.QLabel('Margin:')
        marginlabel.setToolTip(
            "Distance by which to avoid\n"
            "the edges of the polygon to\n"
            "be painted."
        )
        grid4.addWidget(marginlabel, 2, 0)
        self.paintmargin_entry = LengthEntry()
        grid4.addWidget(self.paintmargin_entry, 2, 1)

        # Method
        methodlabel = QtWidgets.QLabel('Method:')
        methodlabel.setToolTip(
            "Algorithm to paint the polygon:<BR>"
            "<B>Standard</B>: Fixed step inwards.<BR>"
            "<B>Seed-based</B>: Outwards from seed."
        )
        grid4.addWidget(methodlabel, 3, 0)
        self.paintmethod_combo = RadioSet([
            {"label": "Standard", "value": "standard"},
            {"label": "Seed-based", "value": "seed"},
            {"label": "Straight lines", "value": "lines"}
        ], orientation='vertical', stretch=False)
        grid4.addWidget(self.paintmethod_combo, 3, 1)

        # Connect lines
        pathconnectlabel = QtWidgets.QLabel("Connect:")
        pathconnectlabel.setToolTip(
            "Draw lines between resulting\n"
            "segments to minimize tool lifts."
        )
        grid4.addWidget(pathconnectlabel, 4, 0)
        self.pathconnect_cb = FCCheckBox()
        grid4.addWidget(self.pathconnect_cb, 4, 1)

        # Paint contour
        contourlabel = QtWidgets.QLabel("Contour:")
        contourlabel.setToolTip(
            "Cut around the perimeter of the polygon\n"
            "to trim rough edges."
        )
        grid4.addWidget(contourlabel, 5, 0)
        self.contour_cb = FCCheckBox()
        grid4.addWidget(self.contour_cb, 5, 1)

        # Polygon selection
        selectlabel = QtWidgets.QLabel('Selection:')
        selectlabel.setToolTip(
            "How to select the polygons to paint."
        )
        grid4.addWidget(selectlabel, 6, 0)
        self.selectmethod_combo = RadioSet([
            {"label": "Single", "value": "single"},
            {"label": "All", "value": "all"},
            # {"label": "Rectangle", "value": "rectangle"}
        ])
        grid4.addWidget(self.selectmethod_combo, 6, 1)

        self.layout.addStretch()


class CNCJobPrefGroupUI(OptionsGroupUI):
    def __init__(self, parent=None):
        # OptionsGroupUI.__init__(self, "CNC Job Options", parent=None)
        super(CNCJobPrefGroupUI, self).__init__(self)

        self.setTitle(str("CNC Job Options"))

        ## Plot options
        self.plot_options_label = QtWidgets.QLabel("<b>Plot Options:</b>")
        self.layout.addWidget(self.plot_options_label)

        grid0 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid0)

        # Plot CB
        # self.plot_cb = QtWidgets.QCheckBox('Plot')
        self.plot_cb = FCCheckBox('Plot')
        self.plot_cb.setToolTip(
            "Plot (show) this object."
        )
        grid0.addWidget(self.plot_cb, 0, 0)

        # Number of circle steps for circular aperture linear approximation
        self.steps_per_circle_label = QtWidgets.QLabel("Circle Steps:")
        self.steps_per_circle_label.setToolTip(
            "The number of circle steps for <b>GCode</b> \n"
            "circle and arc shapes linear approximation."
        )
        grid0.addWidget(self.steps_per_circle_label, 1, 0)
        self.steps_per_circle_entry = IntEntry()
        grid0.addWidget(self.steps_per_circle_entry, 1, 1)

        # Tool dia for plot
        tdlabel = QtWidgets.QLabel('Tool dia:')
        tdlabel.setToolTip(
            "Diameter of the tool to be\n"
            "rendered in the plot."
        )
        grid0.addWidget(tdlabel, 2, 0)
        self.tooldia_entry = LengthEntry()
        grid0.addWidget(self.tooldia_entry, 2, 1)

        # Number of decimals to use in GCODE coordinates
        cdeclabel = QtWidgets.QLabel('Coords decimals:')
        cdeclabel.setToolTip(
            "The number of decimals to be used for \n"
            "the X, Y, Z coordinates in CNC code (GCODE, etc.)"
        )
        grid0.addWidget(cdeclabel, 3, 0)
        self.coords_dec_entry = IntEntry()
        grid0.addWidget(self.coords_dec_entry, 3, 1)

        # Number of decimals to use in GCODE feedrate
        frdeclabel = QtWidgets.QLabel('Feedrate decimals:')
        frdeclabel.setToolTip(
            "The number of decimals to be used for \n"
            "the feedrate in CNC code (GCODE, etc.)"
        )
        grid0.addWidget(frdeclabel, 4, 0)
        self.fr_dec_entry = IntEntry()
        grid0.addWidget(self.fr_dec_entry, 4, 1)

        ## Export G-Code
        self.export_gcode_label = QtWidgets.QLabel("<b>Export G-Code:</b>")
        self.export_gcode_label.setToolTip(
            "Export and save G-Code to\n"
            "make this object to a file."
        )
        self.layout.addWidget(self.export_gcode_label)

        # Prepend to G-Code
        prependlabel = QtWidgets.QLabel('Prepend to G-Code:')
        prependlabel.setToolTip(
            "Type here any G-Code commands you would\n"
            "like to add at the beginning of the G-Code file."
        )
        self.layout.addWidget(prependlabel)

        self.prepend_text = FCTextArea()
        self.layout.addWidget(self.prepend_text)

        # Append text to G-Code
        appendlabel = QtWidgets.QLabel('Append to G-Code:')
        appendlabel.setToolTip(
            "Type here any G-Code commands you would\n"
            "like to append to the generated file.\n"
            "I.e.: M2 (End of program)"
        )
        self.layout.addWidget(appendlabel)

        self.append_text = FCTextArea()
        self.layout.addWidget(self.append_text)

        grid0 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid0)


class FlatCAMActivityView(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.setMinimumWidth(200)

        self.icon = QtWidgets.QLabel(self)
        self.icon.setGeometry(0, 0, 16, 12)
        self.movie = QtGui.QMovie("share/active.gif")
        self.icon.setMovie(self.movie)
        # self.movie.start()

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setAlignment(QtCore.Qt.AlignLeft)
        self.setLayout(layout)

        layout.addWidget(self.icon)
        self.text = QtWidgets.QLabel(self)
        self.text.setText("Idle.")

        layout.addWidget(self.text)

    def set_idle(self):
        self.movie.stop()
        self.text.setText("Idle.")

    def set_busy(self, msg):
        self.movie.start()
        self.text.setText(msg)


class FlatCAMInfoBar(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super(FlatCAMInfoBar, self).__init__(parent=parent)

        self.icon = QtWidgets.QLabel(self)
        self.icon.setGeometry(0, 0, 12, 12)
        self.pmap = QtGui.QPixmap('share/graylight12.png')
        self.icon.setPixmap(self.pmap)

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(5, 0, 5, 0)
        self.setLayout(layout)

        layout.addWidget(self.icon)

        self.text = QtWidgets.QLabel(self)
        self.text.setText("Hello!")
        self.text.setToolTip("Hello!")

        layout.addWidget(self.text)

        layout.addStretch()

    def set_text_(self, text):
        self.text.setText(text)
        self.text.setToolTip(text)

    def set_status(self, text, level="info"):
        level = str(level)
        self.pmap.fill()
        if level == "error" or level == "error_notcl":
            self.pmap = QtGui.QPixmap('share/redlight12.png')
        elif level == "success":
            self.pmap = QtGui.QPixmap('share/greenlight12.png')
        elif level == "warning" or level == "warning_notcl":
            self.pmap = QtGui.QPixmap('share/yellowlight12.png')
        else:
            self.pmap = QtGui.QPixmap('share/graylight12.png')

        self.icon.setPixmap(self.pmap)
        self.set_text_(text)
# end of file
