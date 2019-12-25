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

from flatcamGUI.PreferencesUI import *
from flatcamEditors.FlatCAMGeoEditor import FCShapeTool
from matplotlib.backend_bases import KeyEvent as mpl_key_event

import webbrowser
from copy import deepcopy
from datetime import datetime
import gettext
import FlatCAMTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class FlatCAMGUI(QtWidgets.QMainWindow):
    # Emitted when persistent window geometry needs to be retained
    geom_update = QtCore.pyqtSignal(int, int, int, int, int, name='geomUpdate')
    final_save = QtCore.pyqtSignal(name='saveBeforeExit')

    def __init__(self, app):
        super(FlatCAMGUI, self).__init__()

        self.app = app
        self.decimals = self.app.decimals

        # Divine icon pack by Ipapun @ finicons.com

        # ################################## ##
        # ## BUILDING THE GUI IS DONE HERE # ##
        # ################################## ##

        # ######### ##
        # ## Menu # ##
        # ######### ##
        self.menu = self.menuBar()

        self.menu_toggle_nb = QtWidgets.QAction(QtGui.QIcon(self.app.resource_location + '/notebook32.png'), _("Toggle Panel"))
        self.menu_toggle_nb.setToolTip(
            _("Toggle Panel")
        )
        # self.menu_toggle_nb = QtWidgets.QAction("NB")

        self.menu_toggle_nb.setCheckable(True)
        self.menu.addAction(self.menu_toggle_nb)

        # ########################################################################
        # ########################## File # ######################################
        # ########################################################################
        self.menufile = self.menu.addMenu(_('File'))
        self.menufile.setToolTipsVisible(True)

        # New Project
        self.menufilenewproject = QtWidgets.QAction(QtGui.QIcon(self.app.resource_location + '/file16.png'),
                                                    _('&New Project ...\tCTRL+N'), self)
        self.menufilenewproject.setToolTip(
            _("Will create a new, blank project")
        )
        self.menufile.addAction(self.menufilenewproject)

        # New Category (Excellon, Geometry)
        self.menufilenew = self.menufile.addMenu(QtGui.QIcon(self.app.resource_location + '/file16.png'), _('&New'))
        self.menufilenew.setToolTipsVisible(True)

        self.menufilenewgeo = self.menufilenew.addAction(
            QtGui.QIcon(self.app.resource_location + '/new_file_geo16.png'), _('Geometry\tN'))
        self.menufilenewgeo.setToolTip(
            _("Will create a new, empty Geometry Object.")
        )
        self.menufilenewgrb = self.menufilenew.addAction(QtGui.QIcon(self.app.resource_location + '/new_file_grb16.png'), _('Gerber\tB'))
        self.menufilenewgrb.setToolTip(
            _("Will create a new, empty Gerber Object.")
        )
        self.menufilenewexc = self.menufilenew.addAction(QtGui.QIcon(self.app.resource_location + '/new_file_exc16.png'), _('Excellon\tL'))
        self.menufilenewexc.setToolTip(
            _("Will create a new, empty Excellon Object.")
        )
        self.menufilenew.addSeparator()

        self.menufilenewdoc = self.menufilenew.addAction(QtGui.QIcon(self.app.resource_location + '/notes16_1.png'), _('Document\tD'))
        self.menufilenewdoc.setToolTip(
            _("Will create a new, empty Document Object.")
        )

        self.menufile_open = self.menufile.addMenu(QtGui.QIcon(self.app.resource_location + '/folder32_bis.png'), _('Open'))
        self.menufile_open.setToolTipsVisible(True)

        # Open Project ...
        self.menufileopenproject = QtWidgets.QAction(QtGui.QIcon(self.app.resource_location + '/folder16.png'), _('Open &Project ...'), self)
        self.menufile_open.addAction(self.menufileopenproject)
        self.menufile_open.addSeparator()

        # Open Gerber ...
        self.menufileopengerber = QtWidgets.QAction(QtGui.QIcon(self.app.resource_location + '/flatcam_icon24.png'),
                                                    _('Open &Gerber ...\tCTRL+G'), self)
        self.menufile_open.addAction(self.menufileopengerber)

        # Open Excellon ...
        self.menufileopenexcellon = QtWidgets.QAction(QtGui.QIcon(self.app.resource_location + '/open_excellon32.png'),
                                                      _('Open &Excellon ...\tCTRL+E'), self)
        self.menufile_open.addAction(self.menufileopenexcellon)

        # Open G-Code ...
        self.menufileopengcode = QtWidgets.QAction(QtGui.QIcon(self.app.resource_location + '/code.png'), _('Open G-&Code ...'), self)
        self.menufile_open.addAction(self.menufileopengcode)

        self.menufile_open.addSeparator()

        # Open Config File...
        self.menufileopenconfig = QtWidgets.QAction(QtGui.QIcon(self.app.resource_location + '/folder16.png'), _('Open Config ...'), self)
        self.menufile_open.addAction(self.menufileopenconfig)

        # Recent
        self.recent_projects = self.menufile.addMenu(QtGui.QIcon(self.app.resource_location + '/recent_files.png'), _("Recent projects"))
        self.recent = self.menufile.addMenu(QtGui.QIcon(self.app.resource_location + '/recent_files.png'), _("Recent files"))

        # Separator
        self.menufile.addSeparator()

        # Scripting
        self.menufile_scripting = self.menufile.addMenu(QtGui.QIcon(self.app.resource_location + '/script16.png'), _('Scripting'))
        self.menufile_scripting.setToolTipsVisible(True)

        self.menufilenewscript = QtWidgets.QAction(QtGui.QIcon(self.app.resource_location + '/script_new16.png'), _('New Script ...'), self)
        self.menufileopenscript = QtWidgets.QAction(QtGui.QIcon(self.app.resource_location + '/open_script32.png'), _('Open Script ...'), self)
        self.menufilerunscript = QtWidgets.QAction(QtGui.QIcon(self.app.resource_location + '/script16.png'),
                                                   '%s\tSHIFT+S' % _('Run Script ...'), self)
        self.menufilerunscript.setToolTip(
           _("Will run the opened Tcl Script thus\n"
             "enabling the automation of certain\n"
             "functions of FlatCAM.")
        )
        self.menufile_scripting.addAction(self.menufilenewscript)
        self.menufile_scripting.addAction(self.menufileopenscript)
        self.menufile_scripting.addSeparator()
        self.menufile_scripting.addAction(self.menufilerunscript)

        # Separator
        self.menufile.addSeparator()

        # Import ...
        self.menufileimport = self.menufile.addMenu(QtGui.QIcon(self.app.resource_location + '/import.png'), _('Import'))
        self.menufileimportsvg = QtWidgets.QAction(QtGui.QIcon(self.app.resource_location + '/svg16.png'),
                                                   _('&SVG as Geometry Object ...'), self)
        self.menufileimport.addAction(self.menufileimportsvg)
        self.menufileimportsvg_as_gerber = QtWidgets.QAction(QtGui.QIcon(self.app.resource_location + '/svg16.png'),
                                                             _('&SVG as Gerber Object ...'), self)
        self.menufileimport.addAction(self.menufileimportsvg_as_gerber)
        self.menufileimport.addSeparator()

        self.menufileimportdxf = QtWidgets.QAction(QtGui.QIcon(self.app.resource_location + '/dxf16.png'),
                                                   _('&DXF as Geometry Object ...'), self)
        self.menufileimport.addAction(self.menufileimportdxf)
        self.menufileimportdxf_as_gerber = QtWidgets.QAction(QtGui.QIcon(self.app.resource_location + '/dxf16.png'),
                                                             _('&DXF as Gerber Object ...'), self)
        self.menufileimport.addAction(self.menufileimportdxf_as_gerber)
        self.menufileimport.addSeparator()
        self.menufileimport_hpgl2_as_geo = QtWidgets.QAction(QtGui.QIcon(self.app.resource_location + '/dxf16.png'),
                                                             _('HPGL2 as Geometry Object ...'), self)
        self.menufileimport.addAction(self.menufileimport_hpgl2_as_geo)
        self.menufileimport.addSeparator()

        # Export ...
        self.menufileexport = self.menufile.addMenu(QtGui.QIcon(self.app.resource_location + '/export.png'), _('Export'))
        self.menufileexport.setToolTipsVisible(True)

        self.menufileexportsvg = QtWidgets.QAction(QtGui.QIcon(self.app.resource_location + '/export.png'), _('Export &SVG ...'), self)
        self.menufileexport.addAction(self.menufileexportsvg)

        self.menufileexportdxf = QtWidgets.QAction(QtGui.QIcon(self.app.resource_location + '/export.png'), _('Export DXF ...'), self)
        self.menufileexport.addAction(self.menufileexportdxf)

        self.menufileexport.addSeparator()

        self.menufileexportpng = QtWidgets.QAction(QtGui.QIcon(self.app.resource_location + '/export_png32.png'), _('Export &PNG ...'), self)
        self.menufileexportpng.setToolTip(
            _("Will export an image in PNG format,\n"
              "the saved image will contain the visual \n"
              "information currently in FlatCAM Plot Area.")
        )
        self.menufileexport.addAction(self.menufileexportpng)

        self.menufileexport.addSeparator()

        self.menufileexportexcellon = QtWidgets.QAction(QtGui.QIcon(self.app.resource_location + '/drill32.png'),
                                                        _('Export &Excellon ...'), self)
        self.menufileexportexcellon.setToolTip(
           _("Will export an Excellon Object as Excellon file,\n"
             "the coordinates format, the file units and zeros\n"
             "are set in Preferences -> Excellon Export.")
        )
        self.menufileexport.addAction(self.menufileexportexcellon)

        self.menufileexportgerber = QtWidgets.QAction(QtGui.QIcon(self.app.resource_location + '/flatcam_icon32.png'),
                                                      _('Export &Gerber ...'), self)
        self.menufileexportgerber.setToolTip(
            _("Will export an Gerber Object as Gerber file,\n"
              "the coordinates format, the file units and zeros\n"
              "are set in Preferences -> Gerber Export.")
        )
        self.menufileexport.addAction(self.menufileexportgerber)

        # Separator
        self.menufile.addSeparator()

        # Save Defaults
        self.menufilesavedefaults = QtWidgets.QAction(QtGui.QIcon(self.app.resource_location + '/defaults.png'),
                                                      _('Save Preferences'), self)
        self.menufile.addAction(self.menufilesavedefaults)

        # Separator
        self.menufile.addSeparator()

        self.menufile_backup = self.menufile.addMenu(QtGui.QIcon(self.app.resource_location + '/backup24.png'),
                                                     _('Backup'))

        # Import Preferences
        self.menufileimportpref = QtWidgets.QAction(QtGui.QIcon(self.app.resource_location + '/backup_import24.png'),
                                                    _('Import Preferences from file ...'), self)
        self.menufile_backup.addAction(self.menufileimportpref)

        # Export Preferences
        self.menufileexportpref = QtWidgets.QAction(QtGui.QIcon(self.app.resource_location + '/backup_export24.png'),
                                                    _('Export Preferences to file ...'), self)
        self.menufile_backup.addAction(self.menufileexportpref)

        # Separator
        self.menufile.addSeparator()
        self.menufile_print = QtWidgets.QAction(
            QtGui.QIcon(self.app.resource_location + '/printer32.png'), '%s\tCTRL+P' % _('Print (PDF)'))
        self.menufile.addAction(self.menufile_print)

        self.menufile_save = self.menufile.addMenu(QtGui.QIcon(self.app.resource_location + '/save_as.png'), _('Save'))

        # Save Project
        self.menufilesaveproject = QtWidgets.QAction(QtGui.QIcon(self.app.resource_location + '/floppy16.png'),
                                                     _('&Save Project ...'), self)
        self.menufile_save.addAction(self.menufilesaveproject)

        # Save Project As ...
        self.menufilesaveprojectas = QtWidgets.QAction(QtGui.QIcon(self.app.resource_location + '/save_as.png'),
                                                       _('Save Project &As ...\tCTRL+S'), self)
        self.menufile_save.addAction(self.menufilesaveprojectas)

        # Save Project Copy ...
        self.menufilesaveprojectcopy = QtWidgets.QAction(QtGui.QIcon(self.app.resource_location + '/floppy16.png'),
                                                         _('Save Project C&opy ...'), self)
        self.menufile_save.addAction(self.menufilesaveprojectcopy)

        self.menufile_save.addSeparator()

        # Separator
        self.menufile.addSeparator()

        # Quit
        self.menufile_exit = QtWidgets.QAction(QtGui.QIcon(self.app.resource_location + '/power16.png'),
                                               _('E&xit'), self)
        # exitAction.setShortcut('Ctrl+Q')
        # exitAction.setStatusTip('Exit application')
        self.menufile.addAction(self.menufile_exit)

        # ########################################################################
        # ########################## Edit # ######################################
        # ########################################################################
        self.menuedit = self.menu.addMenu(_('Edit'))
        # Separator
        self.menuedit.addSeparator()
        self.menueditedit = self.menuedit.addAction(QtGui.QIcon(self.app.resource_location + '/edit16.png'),
                                                    _('Edit Object\tE'))
        self.menueditok = self.menuedit.addAction(QtGui.QIcon(self.app.resource_location + '/edit_ok16.png'),
                                                  _('Close Editor\tCTRL+S'))

        # adjust the initial state of the menu entries related to the editor
        self.menueditedit.setDisabled(False)
        self.menueditok.setDisabled(True)

        # Separator
        self.menuedit.addSeparator()
        self.menuedit_convert = self.menuedit.addMenu(QtGui.QIcon(self.app.resource_location + '/convert24.png'),
                                                      _('Conversion'))
        self.menuedit_convertjoin = self.menuedit_convert.addAction(
            QtGui.QIcon(self.app.resource_location + '/join16.png'), _('&Join Geo/Gerber/Exc -> Geo'))
        self.menuedit_convertjoin.setToolTip(
           _("Merge a selection of objects, which can be of type:\n"
             "- Gerber\n"
             "- Excellon\n"
             "- Geometry\n"
             "into a new combo Geometry object.")
        )
        self.menuedit_convertjoinexc = self.menuedit_convert.addAction(
            QtGui.QIcon(self.app.resource_location + '/join16.png'), _('Join Excellon(s) -> Excellon'))
        self.menuedit_convertjoinexc.setToolTip(
           _("Merge a selection of Excellon objects into a new combo Excellon object.")
        )
        self.menuedit_convertjoingrb = self.menuedit_convert.addAction(
            QtGui.QIcon(self.app.resource_location + '/join16.png'), _('Join Gerber(s) -> Gerber'))
        self.menuedit_convertjoingrb.setToolTip(
            _("Merge a selection of Gerber objects into a new combo Gerber object.")
        )
        # Separator
        self.menuedit_convert.addSeparator()
        self.menuedit_convert_sg2mg = self.menuedit_convert.addAction(
            QtGui.QIcon(self.app.resource_location + '/convert24.png'), _('Convert Single to MultiGeo'))
        self.menuedit_convert_sg2mg.setToolTip(
           _("Will convert a Geometry object from single_geometry type\n"
             "to a multi_geometry type.")
        )
        self.menuedit_convert_mg2sg = self.menuedit_convert.addAction(
            QtGui.QIcon(self.app.resource_location + '/convert24.png'), _('Convert Multi to SingleGeo'))
        self.menuedit_convert_mg2sg.setToolTip(
           _("Will convert a Geometry object from multi_geometry type\n"
             "to a single_geometry type.")
        )
        # Separator
        self.menuedit_convert.addSeparator()
        self.menueditconvert_any2geo = self.menuedit_convert.addAction(
            QtGui.QIcon(self.app.resource_location + '/copy_geo.png'),
            _('Convert Any to Geo'))
        self.menueditconvert_any2gerber = self.menuedit_convert.addAction(
            QtGui.QIcon(self.app.resource_location + '/copy_geo.png'),
            _('Convert Any to Gerber'))
        self.menuedit_convert.setToolTipsVisible(True)

        # Separator
        self.menuedit.addSeparator()
        self.menueditcopyobject = self.menuedit.addAction(
            QtGui.QIcon(self.app.resource_location + '/copy.png'), _('&Copy\tCTRL+C'))

        # Separator
        self.menuedit.addSeparator()
        self.menueditdelete = self.menuedit.addAction(
            QtGui.QIcon(self.app.resource_location + '/trash16.png'), _('&Delete\tDEL'))

        # Separator
        self.menuedit.addSeparator()
        self.menueditorigin = self.menuedit.addAction(
            QtGui.QIcon(self.app.resource_location + '/origin16.png'), _('Se&t Origin\tO'))
        self.menueditjump = self.menuedit.addAction(
            QtGui.QIcon(self.app.resource_location + '/jump_to16.png'), _('Jump to Location\tJ'))

        # Separator
        self.menuedit.addSeparator()
        self.menuedittoggleunits = self.menuedit.addAction(
            QtGui.QIcon(self.app.resource_location + '/toggle_units16.png'), _('Toggle Units\tQ'))
        self.menueditselectall = self.menuedit.addAction(
            QtGui.QIcon(self.app.resource_location + '/select_all.png'), _('&Select All\tCTRL+A'))

        # Separator
        self.menuedit.addSeparator()
        self.menueditpreferences = self.menuedit.addAction(
            QtGui.QIcon(self.app.resource_location + '/pref.png'), _('&Preferences\tSHIFT+P'))

        # ########################################################################
        # ########################## OPTIONS # ###################################
        # ########################################################################

        self.menuoptions = self.menu.addMenu(_('Options'))
        self.menuoptions_transform_rotate = self.menuoptions.addAction(
            QtGui.QIcon(self.app.resource_location + '/rotate.png'), _("&Rotate Selection\tSHIFT+(R)"))
        # Separator
        self.menuoptions.addSeparator()

        self.menuoptions_transform_skewx = self.menuoptions.addAction(
            QtGui.QIcon(self.app.resource_location + '/skewX.png'), _("&Skew on X axis\tSHIFT+X"))
        self.menuoptions_transform_skewy = self.menuoptions.addAction(
            QtGui.QIcon(self.app.resource_location + '/skewY.png'), _("S&kew on Y axis\tSHIFT+Y"))

        # Separator
        self.menuoptions.addSeparator()
        self.menuoptions_transform_flipx = self.menuoptions.addAction(
            QtGui.QIcon(self.app.resource_location + '/flipx.png'), _("Flip on &X axis\tX"))
        self.menuoptions_transform_flipy = self.menuoptions.addAction(
            QtGui.QIcon(self.app.resource_location + '/flipy.png'), _("Flip on &Y axis\tY"))
        # Separator
        self.menuoptions.addSeparator()

        self.menuoptions_view_source = self.menuoptions.addAction(
            QtGui.QIcon(self.app.resource_location + '/source32.png'), _("View source\tALT+S"))
        self.menuoptions_tools_db = self.menuoptions.addAction(
            QtGui.QIcon(self.app.resource_location + '/database32.png'), _("Tools DataBase\tCTRL+D"))
        # Separator
        self.menuoptions.addSeparator()

        # ########################################################################
        # ########################## View # ######################################
        # ########################################################################
        self.menuview = self.menu.addMenu(_('View'))
        self.menuviewenable = self.menuview.addAction(
            QtGui.QIcon(self.app.resource_location + '/replot16.png'), _('Enable all plots\tALT+1'))
        self.menuviewdisableall = self.menuview.addAction(
            QtGui.QIcon(self.app.resource_location + '/clear_plot16.png'), _('Disable all plots\tALT+2'))
        self.menuviewdisableother = self.menuview.addAction(
            QtGui.QIcon(self.app.resource_location + '/clear_plot16.png'), _('Disable non-selected\tALT+3'))
        # Separator
        self.menuview.addSeparator()
        self.menuview_zoom_fit = self.menuview.addAction(
            QtGui.QIcon(self.app.resource_location + '/zoom_fit32.png'), _("&Zoom Fit\tV"))
        self.menuview_zoom_in = self.menuview.addAction(
            QtGui.QIcon(self.app.resource_location + '/zoom_in32.png'), _("&Zoom In\t="))
        self.menuview_zoom_out = self.menuview.addAction(
            QtGui.QIcon(self.app.resource_location + '/zoom_out32.png'), _("&Zoom Out\t-"))
        self.menuview.addSeparator()

        # Replot all
        self.menuview_replot = self.menuview.addAction(
            QtGui.QIcon(self.app.resource_location + '/replot32.png'), _("Redraw All\tF5"))
        self.menuview.addSeparator()

        self.menuview_toggle_code_editor = self.menuview.addAction(
            QtGui.QIcon(self.app.resource_location + '/code_editor32.png'), _('Toggle Code Editor\tSHIFT+E'))
        self.menuview.addSeparator()
        self.menuview_toggle_fscreen = self.menuview.addAction(
            QtGui.QIcon(self.app.resource_location + '/fscreen32.png'), _("&Toggle FullScreen\tALT+F10"))
        self.menuview_toggle_parea = self.menuview.addAction(
            QtGui.QIcon(self.app.resource_location + '/plot32.png'), _("&Toggle Plot Area\tCTRL+F10"))
        self.menuview_toggle_notebook = self.menuview.addAction(
            QtGui.QIcon(self.app.resource_location + '/notebook32.png'), _("&Toggle Project/Sel/Tool\t`"))

        self.menuview.addSeparator()
        self.menuview_toggle_grid = self.menuview.addAction(
            QtGui.QIcon(self.app.resource_location + '/grid32.png'), _("&Toggle Grid Snap\tG"))
        self.menuview_toggle_grid_lines = self.menuview.addAction(
            QtGui.QIcon(self.app.resource_location + '/grid32.png'), _("&Toggle Grid Lines\tALT+G"))
        self.menuview_toggle_axis = self.menuview.addAction(
            QtGui.QIcon(self.app.resource_location + '/axis32.png'), _("&Toggle Axis\tSHIFT+G"))
        self.menuview_toggle_workspace = self.menuview.addAction(
            QtGui.QIcon(self.app.resource_location + '/workspace24.png'), _("Toggle Workspace\tSHIFT+W"))

        # ########################################################################
        # ########################## Objects # ###################################
        # ########################################################################
        self.menuobjects = self.menu.addMenu(_('Objects'))
        self.menuobjects.addSeparator()
        self.menuobjects_selall = self.menuobjects.addAction(
            QtGui.QIcon(self.app.resource_location + '/select_all.png'), _('Select All'))
        self.menuobjects_unselall = self.menuobjects.addAction(
            QtGui.QIcon(self.app.resource_location + '/deselect_all32.png'), _('Deselect All')
        )

        # ########################################################################
        # ########################## Tool # ######################################
        # ########################################################################
        self.menutool = QtWidgets.QMenu(_('Tool'))
        self.menutoolaction = self.menu.addMenu(self.menutool)
        self.menutoolshell = self.menutool.addAction(
            QtGui.QIcon(self.app.resource_location + '/shell16.png'), _('&Command Line\tS'))

        # ########################################################################
        # ########################## Help # ######################################
        # ########################################################################
        self.menuhelp = self.menu.addMenu(_('Help'))
        self.menuhelp_manual = self.menuhelp.addAction(
            QtGui.QIcon(self.app.resource_location + '/globe16.png'), _('Online Help\tF1'))

        self.menuhelp_bookmarks = self.menuhelp.addMenu(
            QtGui.QIcon(self.app.resource_location + '/bookmarks16.png'), _('Bookmarks'))
        self.menuhelp_bookmarks.addSeparator()
        self.menuhelp_bookmarks_manager = self.menuhelp_bookmarks.addAction(
            QtGui.QIcon(self.app.resource_location + '/bookmarks16.png'), _('Bookmarks Manager'))

        self.menuhelp.addSeparator()
        self.menuhelp_report_bug = self.menuhelp.addAction(
            QtGui.QIcon(self.app.resource_location + '/bug16.png'), _('Report a bug'))
        self.menuhelp.addSeparator()
        self.menuhelp_exc_spec = self.menuhelp.addAction(
            QtGui.QIcon(self.app.resource_location + '/pdf_link16.png'), _('Excellon Specification'))
        self.menuhelp_gerber_spec = self.menuhelp.addAction(
            QtGui.QIcon(self.app.resource_location + '/pdf_link16.png'), _('Gerber Specification'))

        self.menuhelp.addSeparator()

        self.menuhelp_shortcut_list = self.menuhelp.addAction(
            QtGui.QIcon(self.app.resource_location + '/shortcuts24.png'), _('Shortcuts List\tF3'))
        self.menuhelp_videohelp = self.menuhelp.addAction(
            QtGui.QIcon(self.app.resource_location + '/youtube32.png'), _('YouTube Channel\tF4'))
        self.menuhelp_about = self.menuhelp.addAction(
            QtGui.QIcon(self.app.resource_location + '/about32.png'), _('About FlatCAM'))

        # ########################################################################
        # ########################## GEOMETRY EDITOR # ###########################
        # ########################################################################
        self.geo_editor_menu = QtWidgets.QMenu(">Geo Editor<")
        self.menu.addMenu(self.geo_editor_menu)

        self.geo_add_circle_menuitem = self.geo_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/circle32.png'), _('Add Circle\tO')
        )
        self.geo_add_arc_menuitem = self.geo_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/arc16.png'), _('Add Arc\tA'))
        self.geo_editor_menu.addSeparator()
        self.geo_add_rectangle_menuitem = self.geo_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/rectangle32.png'), _('Add Rectangle\tR')
        )
        self.geo_add_polygon_menuitem = self.geo_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/polygon32.png'), _('Add Polygon\tN')
        )
        self.geo_add_path_menuitem = self.geo_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/path32.png'), _('Add Path\tP'))
        self.geo_editor_menu.addSeparator()
        self.geo_add_text_menuitem = self.geo_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/text32.png'), _('Add Text\tT'))
        self.geo_editor_menu.addSeparator()
        self.geo_union_menuitem = self.geo_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/union16.png'),_('Polygon Union\tU'))
        self.geo_intersection_menuitem = self.geo_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/intersection16.png'), _('Polygon Intersection\tE'))
        self.geo_subtract_menuitem = self.geo_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/subtract16.png'), _('Polygon Subtraction\tS')
        )
        self.geo_editor_menu.addSeparator()
        self.geo_cutpath_menuitem = self.geo_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/cutpath16.png'), _('Cut Path\tX'))
        # self.move_menuitem = self.menu.addAction(QtGui.QIcon(self.app.resource_location + '/move16.png'), "Move Objects 'm'")
        self.geo_copy_menuitem = self.geo_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/copy16.png'), _("Copy Geom\tC"))
        self.geo_delete_menuitem = self.geo_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/deleteshape16.png'), _("Delete Shape\tDEL")
        )
        self.geo_editor_menu.addSeparator()
        self.geo_move_menuitem = self.geo_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/move32.png'), _("Move\tM"))
        self.geo_buffer_menuitem = self.geo_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/buffer16.png'), _("Buffer Tool\tB")
        )
        self.geo_paint_menuitem = self.geo_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/paint16.png'), _("Paint Tool\tI")
        )
        self.geo_transform_menuitem = self.geo_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/transform.png'), _("Transform Tool\tALT+R")
        )
        self.geo_editor_menu.addSeparator()
        self.geo_cornersnap_menuitem = self.geo_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/corner32.png'), _("Toggle Corner Snap\tK")
        )

        # ########################################################################
        # ########################## EXCELLON Editor # ###########################
        # ########################################################################
        self.exc_editor_menu = QtWidgets.QMenu(_(">Excellon Editor<"))
        self.menu.addMenu(self.exc_editor_menu)

        self.exc_add_array_drill_menuitem = self.exc_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/rectangle32.png'), _('Add Drill Array\tA'))
        self.exc_add_drill_menuitem = self.exc_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/plus16.png'), _('Add Drill\tD'))
        self.exc_editor_menu.addSeparator()

        self.exc_add_array_slot_menuitem = self.exc_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/slot_array26.png'), _('Add Slot Array\tQ'))
        self.exc_add_slot_menuitem = self.exc_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/slot26.png'), _('Add Slot\tW'))
        self.exc_editor_menu.addSeparator()

        self.exc_resize_drill_menuitem = self.exc_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/resize16.png'), _('Resize Drill(S)\tR')
        )
        self.exc_copy_drill_menuitem = self.exc_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/copy32.png'), _('Copy\tC'))
        self.exc_delete_drill_menuitem = self.exc_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/deleteshape32.png'), _('Delete\tDEL')
        )
        self.exc_editor_menu.addSeparator()

        self.exc_move_drill_menuitem = self.exc_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/move32.png'), _('Move Drill(s)\tM'))

        # ########################################################################
        # ########################## GERBER Editor # #############################
        # ########################################################################
        self.grb_editor_menu = QtWidgets.QMenu(_(">Gerber Editor<"))
        self.menu.addMenu(self.grb_editor_menu)

        self.grb_add_pad_menuitem = self.grb_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/aperture16.png'), _('Add Pad\tP'))
        self.grb_add_pad_array_menuitem = self.grb_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/padarray32.png'), _('Add Pad Array\tA'))
        self.grb_add_track_menuitem = self.grb_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/track32.png'), _('Add Track\tT'))
        self.grb_add_region_menuitem = self.grb_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/rectangle32.png'), _('Add Region\tN'))
        self.grb_editor_menu.addSeparator()

        self.grb_convert_poly_menuitem = self.grb_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/poligonize32.png'), _("Poligonize\tALT+N"))
        self.grb_add_semidisc_menuitem = self.grb_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/semidisc32.png'), _("Add SemiDisc\tE"))
        self.grb_add_disc_menuitem = self.grb_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/disc32.png'), _("Add Disc\tD"))
        self.grb_add_buffer_menuitem = self.grb_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/buffer16-2.png'), _('Buffer\tB'))
        self.grb_add_scale_menuitem = self.grb_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/scale32.png'), _('Scale\tS'))
        self.grb_add_markarea_menuitem = self.grb_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/markarea32.png'), _('Mark Area\tALT+A'))
        self.grb_add_eraser_menuitem = self.grb_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/eraser26.png'), _('Eraser\tCTRL+E'))
        self.grb_transform_menuitem = self.grb_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/transform.png'), _("Transform\tALT+R"))
        self.grb_editor_menu.addSeparator()

        self.grb_copy_menuitem = self.grb_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/copy32.png'), _('Copy\tC'))
        self.grb_delete_menuitem = self.grb_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/deleteshape32.png'), _('Delete\tDEL'))
        self.grb_editor_menu.addSeparator()

        self.grb_move_menuitem = self.grb_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/move32.png'), _('Move\tM'))

        self.grb_editor_menu.menuAction().setVisible(False)
        self.grb_editor_menu.setDisabled(True)

        self.geo_editor_menu.menuAction().setVisible(False)
        self.geo_editor_menu.setDisabled(True)

        self.exc_editor_menu.menuAction().setVisible(False)
        self.exc_editor_menu.setDisabled(True)

        # ########################################################################
        # ########################## Project Tab Context Menu # ##################
        # ########################################################################
        self.menuproject = QtWidgets.QMenu()

        self.menuprojectenable = self.menuproject.addAction(
            QtGui.QIcon(self.app.resource_location + '/replot32.png'), _('Enable Plot'))
        self.menuprojectdisable = self.menuproject.addAction(
            QtGui.QIcon(self.app.resource_location + '/clear_plot32.png'), _('Disable Plot'))
        self.menuproject.addSeparator()

        self.menuprojectcolor = self.menuproject.addMenu(
            QtGui.QIcon(self.app.resource_location + '/set_color32.png'), _('Set Color'))

        self.menuproject_red = self.menuprojectcolor.addAction(
            QtGui.QIcon(self.app.resource_location + '/red32.png'), _('Red'))

        self.menuproject_blue = self.menuprojectcolor.addAction(
            QtGui.QIcon(self.app.resource_location + '/blue32.png'), _('Blue'))

        self.menuproject_yellow = self.menuprojectcolor.addAction(
            QtGui.QIcon(self.app.resource_location + '/yellow32.png'), _('Yellow'))

        self.menuproject_green = self.menuprojectcolor.addAction(
            QtGui.QIcon(self.app.resource_location + '/green32.png'), _('Green'))

        self.menuproject_purple = self.menuprojectcolor.addAction(
            QtGui.QIcon(self.app.resource_location + '/violet32.png'), _('Purple'))

        self.menuproject_brown = self.menuprojectcolor.addAction(
            QtGui.QIcon(self.app.resource_location + '/brown32.png'), _('Brown'))

        self.menuproject_custom = self.menuprojectcolor.addAction(
            QtGui.QIcon(self.app.resource_location + '/set_color32.png'), _('Custom'))

        self.menuproject.addSeparator()

        self.menuprojectgeneratecnc = self.menuproject.addAction(
            QtGui.QIcon(self.app.resource_location + '/cnc32.png'), _('Generate CNC'))
        self.menuprojectviewsource = self.menuproject.addAction(
            QtGui.QIcon(self.app.resource_location + '/source32.png'), _('View Source'))

        self.menuprojectedit = self.menuproject.addAction(
            QtGui.QIcon(self.app.resource_location + '/edit_ok32.png'), _('Edit'))
        self.menuprojectcopy = self.menuproject.addAction(
            QtGui.QIcon(self.app.resource_location + '/copy32.png'), _('Copy'))
        self.menuprojectdelete = self.menuproject.addAction(
            QtGui.QIcon(self.app.resource_location + '/delete32.png'), _('Delete'))
        self.menuprojectsave = self.menuproject.addAction(
            QtGui.QIcon(self.app.resource_location + '/save_as.png'), _('Save'))
        self.menuproject.addSeparator()

        self.menuprojectproperties = self.menuproject.addAction(
            QtGui.QIcon(self.app.resource_location + '/properties32.png'), _('Properties'))

        # ########################################################################
        # ####################### Central Widget -> Splitter # ##################
        # ########################################################################

        # IMPORTANT #
        # The order: SPITTER -> NOTEBOOK -> SNAP TOOLBAR is important and without it the GUI will not be initialized as
        # desired.
        self.splitter = QtWidgets.QSplitter()
        self.setCentralWidget(self.splitter)

        # self.notebook = QtWidgets.QTabWidget()
        self.notebook = FCDetachableTab(protect=True)
        self.notebook.setTabsClosable(False)
        self.notebook.useOldIndex(True)

        self.splitter.addWidget(self.notebook)

        self.splitter_left = QtWidgets.QSplitter(Qt.Vertical)
        self.splitter.addWidget(self.splitter_left)
        self.splitter_left.addWidget(self.notebook)
        self.splitter_left.setHandleWidth(0)

        # ########################################################################
        # ########################## ToolBAR # ###################################
        # ########################################################################

        # ## TOOLBAR INSTALLATION ###
        self.toolbarfile = QtWidgets.QToolBar(_('File Toolbar'))
        self.toolbarfile.setObjectName('File_TB')
        self.addToolBar(self.toolbarfile)

        self.toolbargeo = QtWidgets.QToolBar(_('Edit Toolbar'))
        self.toolbargeo.setObjectName('Edit_TB')
        self.addToolBar(self.toolbargeo)

        self.toolbarview = QtWidgets.QToolBar(_('View Toolbar'))
        self.toolbarview.setObjectName('View_TB')
        self.addToolBar(self.toolbarview)

        self.toolbarshell = QtWidgets.QToolBar(_('Shell Toolbar'))
        self.toolbarshell.setObjectName('Shell_TB')
        self.addToolBar(self.toolbarshell)

        self.toolbartools = QtWidgets.QToolBar(_('Tools Toolbar'))
        self.toolbartools.setObjectName('Tools_TB')
        self.addToolBar(self.toolbartools)

        self.exc_edit_toolbar = QtWidgets.QToolBar(_('Excellon Editor Toolbar'))
        self.exc_edit_toolbar.setObjectName('ExcEditor_TB')
        self.addToolBar(self.exc_edit_toolbar)

        self.addToolBarBreak()

        self.geo_edit_toolbar = QtWidgets.QToolBar(_('Geometry Editor Toolbar'))
        self.geo_edit_toolbar.setObjectName('GeoEditor_TB')
        self.addToolBar(self.geo_edit_toolbar)

        self.grb_edit_toolbar = QtWidgets.QToolBar(_('Gerber Editor Toolbar'))
        self.grb_edit_toolbar.setObjectName('GrbEditor_TB')
        self.addToolBar(self.grb_edit_toolbar)

        self.snap_toolbar = QtWidgets.QToolBar(_('Grid Toolbar'))
        self.snap_toolbar.setObjectName('Snap_TB')
        self.addToolBar(self.snap_toolbar)

        settings = QSettings("Open Source", "FlatCAM")
        if settings.contains("layout"):
            layout = settings.value('layout', type=str)
            if layout == 'standard':
                pass
            elif layout == 'compact':
                self.removeToolBar(self.snap_toolbar)
                self.snap_toolbar.setMaximumHeight(30)
                self.splitter_left.addWidget(self.snap_toolbar)

        # ########################################################################
        # ########################## File Toolbar# ###############################
        # ########################################################################
        self.file_open_gerber_btn = self.toolbarfile.addAction(
            QtGui.QIcon(self.app.resource_location + '/flatcam_icon32.png'), _("Open Gerber"))
        self.file_open_excellon_btn = self.toolbarfile.addAction(
            QtGui.QIcon(self.app.resource_location + '/drill32.png'), _("Open Excellon"))
        self.toolbarfile.addSeparator()
        self.file_open_btn = self.toolbarfile.addAction(
            QtGui.QIcon(self.app.resource_location + '/folder32.png'), _("Open project"))
        self.file_save_btn = self.toolbarfile.addAction(
            QtGui.QIcon(self.app.resource_location + '/project_save32.png'), _("Save project"))

        # ########################################################################
        # ########################## Edit Toolbar# ###############################
        # ########################################################################
        self.newgeo_btn = self.toolbargeo.addAction(
            QtGui.QIcon(self.app.resource_location + '/new_file_geo32.png'), _("New Blank Geometry"))
        self.newgrb_btn = self.toolbargeo.addAction(
            QtGui.QIcon(self.app.resource_location + '/new_file_grb32.png'), _("New Blank Gerber"))
        self.newexc_btn = self.toolbargeo.addAction(
            QtGui.QIcon(self.app.resource_location + '/new_file_exc32.png'), _("New Blank Excellon"))
        self.toolbargeo.addSeparator()
        self.editgeo_btn = self.toolbargeo.addAction(
            QtGui.QIcon(self.app.resource_location + '/edit_file32.png'), _("Editor"))
        self.update_obj_btn = self.toolbargeo.addAction(
            QtGui.QIcon(self.app.resource_location + '/close_edit_file32.png'), _("Save Object and close the Editor")
        )

        self.toolbargeo.addSeparator()
        self.copy_btn = self.toolbargeo.addAction(
            QtGui.QIcon(self.app.resource_location + '/copy_file32.png'), _("Copy"))
        self.delete_btn = self.toolbargeo.addAction(
            QtGui.QIcon(self.app.resource_location + '/delete_file32.png'), _("&Delete"))
        self.toolbargeo.addSeparator()
        self.distance_btn = self.toolbargeo.addAction(
            QtGui.QIcon(self.app.resource_location + '/distance32.png'), _("Distance Tool"))
        self.distance_min_btn = self.toolbargeo.addAction(
            QtGui.QIcon(self.app.resource_location + '/distance_min32.png'), _("Distance Min Tool"))
        self.origin_btn = self.toolbargeo.addAction(
            QtGui.QIcon(self.app.resource_location + '/origin32.png'), _('Set Origin'))
        self.jmp_btn = self.toolbargeo.addAction(
            QtGui.QIcon(self.app.resource_location + '/jump_to16.png'), _('Jump to Location'))

        # ########################################################################
        # ########################## View Toolbar# ###############################
        # ########################################################################
        self.replot_btn = self.toolbarview.addAction(
            QtGui.QIcon(self.app.resource_location + '/replot32.png'), _("&Replot"))
        self.clear_plot_btn = self.toolbarview.addAction(
            QtGui.QIcon(self.app.resource_location + '/clear_plot32.png'), _("&Clear plot"))
        self.zoom_in_btn = self.toolbarview.addAction(
            QtGui.QIcon(self.app.resource_location + '/zoom_in32.png'), _("Zoom In"))
        self.zoom_out_btn = self.toolbarview.addAction(
            QtGui.QIcon(self.app.resource_location + '/zoom_out32.png'), _("Zoom Out"))
        self.zoom_fit_btn = self.toolbarview.addAction(
            QtGui.QIcon(self.app.resource_location + '/zoom_fit32.png'), _("Zoom Fit"))

        # self.toolbarview.setVisible(False)

        # ########################################################################
        # ########################## Shell Toolbar# ##############################
        # ########################################################################
        self.shell_btn = self.toolbarshell.addAction(
            QtGui.QIcon(self.app.resource_location + '/shell32.png'), _("&Command Line"))
        self.new_script_btn = self.toolbarshell.addAction(
            QtGui.QIcon(self.app.resource_location + '/script_new24.png'), _('New Script ...'))
        self.open_script_btn = self.toolbarshell.addAction(
            QtGui.QIcon(self.app.resource_location + '/open_script32.png'), _('Open Script ...'))
        self.run_script_btn = self.toolbarshell.addAction(
            QtGui.QIcon(self.app.resource_location + '/script16.png'), _('Run Script ...'))

        # ########################################################################
        # ########################## Tools Toolbar# ##############################
        # ########################################################################
        self.dblsided_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/doubleside32.png'), _("2Sided Tool"))
        self.cutout_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/cut16_bis.png'), _("Cutout Tool"))
        self.ncc_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/ncc16.png'), _("NCC Tool"))
        self.paint_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/paint20_1.png'), _("Paint Tool"))
        self.toolbartools.addSeparator()

        self.panelize_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/panelize32.png'), _("Panel Tool"))
        self.film_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/film16.png'), _("Film Tool"))
        self.solder_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/solderpastebis32.png'), _("SolderPaste Tool"))
        self.sub_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/sub32.png'), _("Subtract Tool"))
        self.rules_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/rules32.png'), _("Rules Tool"))
        self.optimal_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/open_excellon32.png'), _("Optimal Tool"))

        self.toolbartools.addSeparator()

        self.calculators_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/calculator24.png'), _("Calculators Tool"))
        self.transform_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/transform.png'), _("Transform Tool"))
        self.qrcode_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/qrcode32.png'), _("QRCode Tool"))
        self.copperfill_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/copperfill32.png'), _("Copper Thieving Tool"))

        self.fiducials_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/fiducials_32.png'), _("Fiducials Tool"))
        self.cal_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/calibrate_32.png'), _("Calibration Tool"))

        # ########################################################################
        # ########################## Excellon Editor Toolbar# ####################
        # ########################################################################
        self.select_drill_btn = self.exc_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/pointer32.png'), _("Select"))
        self.add_drill_btn = self.exc_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/plus16.png'), _('Add Drill Hole'))
        self.add_drill_array_btn = self.exc_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/addarray16.png'), _('Add Drill Hole Array'))
        self.add_slot_btn = self.exc_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/slot26.png'), _('Add Slot'))
        self.add_slot_array_btn = self.exc_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/slot_array26.png'), _('Add Slot Array'))
        self.resize_drill_btn = self.exc_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/resize16.png'), _('Resize Drill'))
        self.exc_edit_toolbar.addSeparator()

        self.copy_drill_btn = self.exc_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/copy32.png'), _('Copy Drill'))
        self.delete_drill_btn = self.exc_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/trash32.png'), _("Delete Drill"))

        self.exc_edit_toolbar.addSeparator()
        self.move_drill_btn = self.exc_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/move32.png'), _("Move Drill"))

        # ########################################################################
        # ########################## Geometry Editor Toolbar# ####################
        # ########################################################################
        self.geo_select_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/pointer32.png'), _("Select"))
        self.geo_add_circle_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/circle32.png'), _('Add Circle'))
        self.geo_add_arc_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/arc32.png'), _('Add Arc'))
        self.geo_add_rectangle_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/rectangle32.png'), _('Add Rectangle'))

        self.geo_edit_toolbar.addSeparator()
        self.geo_add_path_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/path32.png'), _('Add Path'))
        self.geo_add_polygon_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/polygon32.png'), _('Add Polygon'))
        self.geo_edit_toolbar.addSeparator()
        self.geo_add_text_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/text32.png'), _('Add Text'))
        self.geo_add_buffer_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/buffer16-2.png'), _('Add Buffer'))
        self.geo_add_paint_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/paint20_1.png'), _('Paint Shape'))
        self.geo_eraser_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/eraser26.png'), _('Eraser'))

        self.geo_edit_toolbar.addSeparator()
        self.geo_union_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/union32.png'), _('Polygon Union'))
        self.geo_explode_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/explode32.png'), _('Polygon Explode'))

        self.geo_intersection_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/intersection32.png'), _('Polygon Intersection'))
        self.geo_subtract_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/subtract32.png'), _('Polygon Subtraction'))

        self.geo_edit_toolbar.addSeparator()
        self.geo_cutpath_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/cutpath32.png'), _('Cut Path'))
        self.geo_copy_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/copy32.png'), _("Copy Shape(s)"))

        self.geo_delete_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/trash32.png'), _("Delete Shape '-'"))
        self.geo_transform_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/transform.png'), _("Transformations"))
        self.geo_edit_toolbar.addSeparator()
        self.geo_move_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/move32.png'), _("Move Objects "))

        # ########################################################################
        # ########################## Gerber Editor Toolbar# ######################
        # ########################################################################
        self.grb_select_btn = self.grb_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/pointer32.png'), _("Select"))
        self.grb_add_pad_btn = self.grb_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/aperture32.png'), _("Add Pad"))
        self.add_pad_ar_btn = self.grb_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/padarray32.png'), _('Add Pad Array'))
        self.grb_add_track_btn = self.grb_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/track32.png'), _("Add Track"))
        self.grb_add_region_btn = self.grb_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/polygon32.png'), _("Add Region"))
        self.grb_convert_poly_btn = self.grb_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/poligonize32.png'), _("Poligonize"))

        self.grb_add_semidisc_btn = self.grb_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/semidisc32.png'), _("SemiDisc"))
        self.grb_add_disc_btn = self.grb_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/disc32.png'), _("Disc"))
        self.grb_edit_toolbar.addSeparator()

        self.aperture_buffer_btn = self.grb_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/buffer16-2.png'), _('Buffer'))
        self.aperture_scale_btn = self.grb_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/scale32.png'), _('Scale'))
        self.aperture_markarea_btn = self.grb_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/markarea32.png'), _('Mark Area'))

        self.aperture_eraser_btn = self.grb_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/eraser26.png'), _('Eraser'))

        self.grb_edit_toolbar.addSeparator()
        self.aperture_copy_btn = self.grb_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/copy32.png'), _("Copy"))
        self.aperture_delete_btn = self.grb_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/trash32.png'), _("Delete"))
        self.grb_transform_btn = self.grb_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/transform.png'), _("Transformations"))
        self.grb_edit_toolbar.addSeparator()
        self.aperture_move_btn = self.grb_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/move32.png'), _("Move"))

        # ########################################################################
        # ########################## Snap Toolbar# ###############################
        # ########################################################################

        # Snap GRID toolbar is always active to facilitate usage of measurements done on GRID
        self.grid_snap_btn = self.snap_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/grid32.png'), _('Snap to grid'))
        self.grid_gap_x_entry = FCEntry2()
        self.grid_gap_x_entry.setMaximumWidth(70)
        self.grid_gap_x_entry.setToolTip(_("Grid X snapping distance"))
        self.snap_toolbar.addWidget(self.grid_gap_x_entry)

        self.grid_gap_y_entry = FCEntry2()
        self.grid_gap_y_entry.setMaximumWidth(70)
        self.grid_gap_y_entry.setToolTip(_("Grid Y snapping distance"))
        self.snap_toolbar.addWidget(self.grid_gap_y_entry)

        self.grid_space_label = QtWidgets.QLabel("  ")
        self.snap_toolbar.addWidget(self.grid_space_label)
        self.grid_gap_link_cb = FCCheckBox()
        self.grid_gap_link_cb.setToolTip(_("When active, value on Grid_X\n"
                                         "is copied to the Grid_Y value."))
        self.snap_toolbar.addWidget(self.grid_gap_link_cb)

        self.ois_grid = OptionalInputSection(self.grid_gap_link_cb, [self.grid_gap_y_entry], logic=False)

        self.corner_snap_btn = self.snap_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/corner32.png'), _('Snap to corner'))

        self.snap_max_dist_entry = FCEntry()
        self.snap_max_dist_entry.setMaximumWidth(70)
        self.snap_max_dist_entry.setToolTip(_("Max. magnet distance"))
        self.snap_magnet = self.snap_toolbar.addWidget(self.snap_max_dist_entry)

        # ########################################################################
        # ########################## Notebook # ##################################
        # ########################################################################

        # ########################################################################
        # ########################## PROJECT Tab # ###############################
        # ########################################################################
        self.project_tab = QtWidgets.QWidget()
        self.project_tab.setObjectName("project_tab")

        self.project_frame_lay = QtWidgets.QVBoxLayout(self.project_tab)
        self.project_frame_lay.setContentsMargins(0, 0, 0, 0)

        self.project_frame = QtWidgets.QFrame()
        self.project_frame.setContentsMargins(0, 0, 0, 0)
        self.project_frame_lay.addWidget(self.project_frame)

        self.project_tab_layout = QtWidgets.QVBoxLayout(self.project_frame)
        self.project_tab_layout.setContentsMargins(2, 2, 2, 2)
        self.notebook.addTab(self.project_tab, _("Project"))
        self.project_frame.setDisabled(False)

        # ########################################################################
        # ########################## SELECTED Tab # ##############################
        # ########################################################################
        self.selected_tab = QtWidgets.QWidget()
        self.selected_tab.setObjectName("selected_tab")
        self.selected_tab_layout = QtWidgets.QVBoxLayout(self.selected_tab)
        self.selected_tab_layout.setContentsMargins(2, 2, 2, 2)
        self.selected_scroll_area = VerticalScrollArea()
        self.selected_tab_layout.addWidget(self.selected_scroll_area)
        self.notebook.addTab(self.selected_tab, _("Selected"))

        # ########################################################################
        # ########################## TOOL Tab # ##################################
        # ########################################################################
        self.tool_tab = QtWidgets.QWidget()
        self.tool_tab.setObjectName("tool_tab")
        self.tool_tab_layout = QtWidgets.QVBoxLayout(self.tool_tab)
        self.tool_tab_layout.setContentsMargins(2, 2, 2, 2)
        self.notebook.addTab(self.tool_tab, _("Tool"))
        self.tool_scroll_area = VerticalScrollArea()
        self.tool_tab_layout.addWidget(self.tool_scroll_area)

        # ########################################################################
        # ########################## RIGHT Widget # ##############################
        # ########################################################################
        self.right_widget = QtWidgets.QWidget()
        self.right_widget.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
        self.splitter.addWidget(self.right_widget)

        self.right_lay = QtWidgets.QVBoxLayout()
        self.right_lay.setContentsMargins(0, 0, 0, 0)
        self.right_widget.setLayout(self.right_lay)

        # ########################################################################
        # ########################## PLOT AREA Tab # #############################
        # ########################################################################
        self.plot_tab_area = FCDetachableTab2(protect=False, protect_by_name=[_('Plot Area')])
        self.plot_tab_area.useOldIndex(True)

        self.right_lay.addWidget(self.plot_tab_area)
        self.plot_tab_area.setTabsClosable(True)

        self.plot_tab = QtWidgets.QWidget()
        self.plot_tab.setObjectName("plotarea")
        self.plot_tab_area.addTab(self.plot_tab, _("Plot Area"))

        self.right_layout = QtWidgets.QVBoxLayout()
        self.right_layout.setObjectName("right_layout")
        self.right_layout.setContentsMargins(2, 2, 2, 2)
        self.plot_tab.setLayout(self.right_layout)

        # remove the close button from the Plot Area tab (first tab index = 0) as this one will always be ON
        self.plot_tab_area.protectTab(0)

        # ########################################################################
        # ########################## PREFERENCES AREA Tab # ######################
        # ########################################################################
        self.preferences_tab = QtWidgets.QWidget()
        self.preferences_tab.setObjectName("preferences_tab")
        self.pref_tab_layout = QtWidgets.QVBoxLayout(self.preferences_tab)
        self.pref_tab_layout.setContentsMargins(2, 2, 2, 2)

        self.pref_tab_area = FCTab()
        self.pref_tab_area.setTabsClosable(False)
        self.pref_tab_area_tabBar = self.pref_tab_area.tabBar()
        self.pref_tab_area_tabBar.setStyleSheet("QTabBar::tab{min-width:90px;}")
        self.pref_tab_area_tabBar.setExpanding(True)
        self.pref_tab_layout.addWidget(self.pref_tab_area)

        self.general_tab = QtWidgets.QWidget()
        self.general_tab.setObjectName("general_tab")
        self.pref_tab_area.addTab(self.general_tab, _("General"))
        self.general_tab_lay = QtWidgets.QVBoxLayout()
        self.general_tab_lay.setContentsMargins(2, 2, 2, 2)
        self.general_tab.setLayout(self.general_tab_lay)

        self.hlay1 = QtWidgets.QHBoxLayout()
        self.general_tab_lay.addLayout(self.hlay1)

        self.hlay1.addStretch()

        self.general_scroll_area = QtWidgets.QScrollArea()
        self.general_tab_lay.addWidget(self.general_scroll_area)

        self.gerber_tab = QtWidgets.QWidget()
        self.gerber_tab.setObjectName("gerber_tab")
        self.pref_tab_area.addTab(self.gerber_tab, _("GERBER"))
        self.gerber_tab_lay = QtWidgets.QVBoxLayout()
        self.gerber_tab_lay.setContentsMargins(2, 2, 2, 2)
        self.gerber_tab.setLayout(self.gerber_tab_lay)

        self.gerber_scroll_area = QtWidgets.QScrollArea()
        self.gerber_tab_lay.addWidget(self.gerber_scroll_area)

        self.excellon_tab = QtWidgets.QWidget()
        self.excellon_tab.setObjectName("excellon_tab")
        self.pref_tab_area.addTab(self.excellon_tab, _("EXCELLON"))
        self.excellon_tab_lay = QtWidgets.QVBoxLayout()
        self.excellon_tab_lay.setContentsMargins(2, 2, 2, 2)
        self.excellon_tab.setLayout(self.excellon_tab_lay)

        self.excellon_scroll_area = QtWidgets.QScrollArea()
        self.excellon_tab_lay.addWidget(self.excellon_scroll_area)

        self.geometry_tab = QtWidgets.QWidget()
        self.geometry_tab.setObjectName("geometry_tab")
        self.pref_tab_area.addTab(self.geometry_tab, _("GEOMETRY"))
        self.geometry_tab_lay = QtWidgets.QVBoxLayout()
        self.geometry_tab_lay.setContentsMargins(2, 2, 2, 2)
        self.geometry_tab.setLayout(self.geometry_tab_lay)

        self.geometry_scroll_area = QtWidgets.QScrollArea()
        self.geometry_tab_lay.addWidget(self.geometry_scroll_area)

        self.text_editor_tab = QtWidgets.QWidget()
        self.text_editor_tab.setObjectName("text_editor_tab")
        self.pref_tab_area.addTab(self.text_editor_tab, _("CNC-JOB"))
        self.cncjob_tab_lay = QtWidgets.QVBoxLayout()
        self.cncjob_tab_lay.setContentsMargins(2, 2, 2, 2)
        self.text_editor_tab.setLayout(self.cncjob_tab_lay)

        self.cncjob_scroll_area = QtWidgets.QScrollArea()
        self.cncjob_tab_lay.addWidget(self.cncjob_scroll_area)

        self.tools_tab = QtWidgets.QWidget()
        self.pref_tab_area.addTab(self.tools_tab, _("TOOLS"))
        self.tools_tab_lay = QtWidgets.QVBoxLayout()
        self.tools_tab_lay.setContentsMargins(2, 2, 2, 2)
        self.tools_tab.setLayout(self.tools_tab_lay)

        self.tools_scroll_area = QtWidgets.QScrollArea()
        self.tools_tab_lay.addWidget(self.tools_scroll_area)

        self.tools2_tab = QtWidgets.QWidget()
        self.pref_tab_area.addTab(self.tools2_tab, _("TOOLS 2"))
        self.tools2_tab_lay = QtWidgets.QVBoxLayout()
        self.tools2_tab_lay.setContentsMargins(2, 2, 2, 2)
        self.tools2_tab.setLayout(self.tools2_tab_lay)

        self.tools2_scroll_area = QtWidgets.QScrollArea()
        self.tools2_tab_lay.addWidget(self.tools2_scroll_area)

        self.fa_tab = QtWidgets.QWidget()
        self.fa_tab.setObjectName("fa_tab")
        self.pref_tab_area.addTab(self.fa_tab, _("UTILITIES"))
        self.fa_tab_lay = QtWidgets.QVBoxLayout()
        self.fa_tab_lay.setContentsMargins(2, 2, 2, 2)
        self.fa_tab.setLayout(self.fa_tab_lay)

        self.fa_scroll_area = QtWidgets.QScrollArea()
        self.fa_tab_lay.addWidget(self.fa_scroll_area)

        self.pref_tab_bottom_layout = QtWidgets.QHBoxLayout()
        self.pref_tab_bottom_layout.setAlignment(QtCore.Qt.AlignVCenter)
        self.pref_tab_layout.addLayout(self.pref_tab_bottom_layout)

        self.pref_tab_bottom_layout_1 = QtWidgets.QHBoxLayout()
        self.pref_tab_bottom_layout_1.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.pref_tab_bottom_layout.addLayout(self.pref_tab_bottom_layout_1)

        self.pref_defaults_button = QtWidgets.QPushButton()
        self.pref_defaults_button.setText(_("Restore Defaults"))
        self.pref_defaults_button.setMinimumWidth(130)
        self.pref_defaults_button.setToolTip(
            _("Restore the entire set of default valaues\n"
              "to the initial values loaded after first launch."))
        self.pref_tab_bottom_layout_1.addWidget(self.pref_defaults_button)

        self.pref_open_button = QtWidgets.QPushButton()
        self.pref_open_button.setText(_("Open Pref Folder"))
        self.pref_open_button.setMinimumWidth(130)
        self.pref_open_button.setToolTip(
            _("Open the folder where FlatCAM save the preferences files."))
        self.pref_tab_bottom_layout_1.addWidget(self.pref_open_button)

        self.pref_tab_bottom_layout_2 = QtWidgets.QHBoxLayout()
        self.pref_tab_bottom_layout_2.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.pref_tab_bottom_layout.addLayout(self.pref_tab_bottom_layout_2)

        self.pref_apply_button = FCButton()
        self.pref_apply_button.setText(_("Apply"))
        self.pref_apply_button.setMinimumWidth(130)
        self.pref_apply_button.setToolTip(
            _("Apply the current preferences without saving to a file."))
        self.pref_tab_bottom_layout_2.addWidget(self.pref_apply_button)

        self.pref_save_button = QtWidgets.QPushButton()
        self.pref_save_button.setText(_("Save"))
        self.pref_save_button.setMinimumWidth(130)
        self.pref_save_button.setToolTip(
            _("Save the current settings in the 'current_defaults' file\n"
              "which is the file storing the working default preferences."))
        self.pref_tab_bottom_layout_2.addWidget(self.pref_save_button)

        self.pref_close_button = QtWidgets.QPushButton()
        self.pref_close_button.setText(_("Cancel"))
        self.pref_close_button.setMinimumWidth(130)
        self.pref_close_button.setToolTip(
            _("Will not save the changes and will close the preferences window."))
        self.pref_tab_bottom_layout_2.addWidget(self.pref_close_button)

        # ########################################################################
        # #################### SHORTCUT LIST AREA Tab # ##########################
        # ########################################################################
        self.shortcuts_tab = QtWidgets.QWidget()
        self.sh_tab_layout = QtWidgets.QVBoxLayout()
        self.sh_tab_layout.setContentsMargins(2, 2, 2, 2)
        self.shortcuts_tab.setLayout(self.sh_tab_layout)

        self.sh_hlay = QtWidgets.QHBoxLayout()
        self.sh_title = QtWidgets.QTextEdit(
            _('<b>Shortcut Key List</b>'))
        self.sh_title.setTextInteractionFlags(QtCore.Qt.NoTextInteraction)
        self.sh_title.setFrameStyle(QtWidgets.QFrame.NoFrame)
        self.sh_title.setMaximumHeight(30)
        font = self.sh_title.font()
        font.setPointSize(12)
        self.sh_title.setFont(font)

        self.sh_tab_layout.addWidget(self.sh_title)
        self.sh_tab_layout.addLayout(self.sh_hlay)

        self.app_sh_msg = (
            '''<b>General Shortcut list</b><br>
            <table border="0" cellpadding="0" cellspacing="0" style="width:283px">
                <tbody>
                    <tr height="20">
                        <td height="20" width="89"><strong>F3</strong></td>
                        <td width="194"><span style="color:#006400"><strong>&nbsp;%s</strong></span></td>
                    </tr>
                    <tr height="20">
                        <td height="20">&nbsp;</td>
                        <td>&nbsp;</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>1</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>2</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>3</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20">&nbsp;</td>
                        <td>&nbsp;</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>B</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>E</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>G</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>J</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>L</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>M</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>N</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>O</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>Q</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>P</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>R</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>S</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>T</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>V</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>X</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>Y</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>&#39;-&#39;</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>&#39;=&#39;</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20">&nbsp;</td>
                        <td>&nbsp;</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>CTRL+A</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>CTRL+C</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>CTRL+D</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>CTRL+E</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>CTRL+G</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>CTRL+M</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>CTRL+N</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>                   
                    <tr height="20">
                        <td height="20"><strong>CTRL+O</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>CTRL+P</strong></td>
                        <td>&nbsp;%s</td>
                    </tr> 
                    <tr height="20">
                        <td height="20"><strong>CTRL+Q</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>CTRL+S</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>CTRL+F10</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20">&nbsp;</td>
                        <td>&nbsp;</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>SHIFT+C</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>SHIFT+E</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>SHIFT+G</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>SHIFT+M</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>SHIFT+P</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>SHIFT+R</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>SHIFT+S</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>SHIFT+W</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>SHIFT+X</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>SHIFT+Y</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20">&nbsp;</td>
                        <td>&nbsp;</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>ALT+C</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>ALT+D</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>ALT+E</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>ALT+J</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>ALT+K</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>ALT+L</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>ALT+N</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>ALT+O</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>ALT+P</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>ALT+Q</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>ALT+R</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>ALT+S</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>ALT+U</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>ALT+1</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>ALT+2</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>ALT+3</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>ALT+F10</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20">&nbsp;</td>
                        <td>&nbsp;</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>CTRL+ALT+X</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20">&nbsp;</td>
                        <td>&nbsp;</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>F1</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>F4</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>F5</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>Del</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>Del</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>'`'</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>SPACE</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>Escape</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                </tbody>
            </table>
            ''' %
            (
                _("SHOW SHORTCUT LIST"), _("Switch to Project Tab"), _("Switch to Selected Tab"),
                _("Switch to Tool Tab"),
                _("New Gerber"), _("Edit Object (if selected)"), _("Grid On/Off"), _("Jump to Coordinates"),
                _("New Excellon"), _("Move Obj"), _("New Geometry"), _("Set Origin"), _("Change Units"),
                _("Open Properties Tool"), _("Rotate by 90 degree CW"), _("Shell Toggle"),
                _("Add a Tool (when in Geometry Selected Tab or in Tools NCC or Tools Paint)"), _("Zoom Fit"),
                _("Flip on X_axis"), _("Flip on Y_axis"), _("Zoom Out"), _("Zoom In"),

                # CTRL section
                _("Select All"), _("Copy Obj"), _("Open Tools Database"),
                _("Open Excellon File"), _("Open Gerber File"), _("Distance Tool"), _("New Project"),
                _("Open Project"), _("Print (PDF)"), _("PDF Import Tool"), _("Save Project As"), _("Toggle Plot Area"),

                # SHIFT section
                _("Copy Obj_Name"),
                _("Toggle Code Editor"), _("Toggle the axis"), _("Distance Minimum Tool"), _("Open Preferences Window"),
                _("Rotate by 90 degree CCW"), _("Run a Script"), _("Toggle the workspace"), _("Skew on X axis"),
                _("Skew on Y axis"),
                # ALT section
                _("Calculators Tool"), _("2-Sided PCB Tool"), _("Transformations Tool"), _("Fiducials Tool"),
                _("Solder Paste Dispensing Tool"),
                _("Film PCB Tool"), _("Non-Copper Clearing Tool"), _("Optimal Tool"),
                _("Paint Area Tool"), _("QRCode Tool"), _("Rules Check Tool"),
                _("View File Source"),
                _("Cutout PCB Tool"), _("Enable all Plots"), _("Disable all Plots"), _("Disable Non-selected Plots"),
                _("Toggle Full Screen"),

                # CTRL + ALT section
                _("Abort current task (gracefully)"),

                # F keys section
                _("Open Online Manual"),
                _("Open Online Tutorials"), _("Refresh Plots"), _("Delete Object"), _("Alternate: Delete Tool"),
                _("(left to Key_1)Toogle Notebook Area (Left Side)"), _("En(Dis)able Obj Plot"),
                _("Deselects all objects")
            )
        )

        self.sh_app = QtWidgets.QTextEdit()
        self.sh_app.setTextInteractionFlags(QtCore.Qt.NoTextInteraction)

        self.sh_app.setText(self.app_sh_msg)
        self.sh_app.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.sh_hlay.addWidget(self.sh_app)

        editor_title = """
        <b>%s</b><br>
        <br>
        """ % _("Editor Shortcut list")

        geo_sh_messages = """
        <strong><span style="color:#0000ff">%s</span></strong><br>
        <table border="0" cellpadding="0" cellspacing="0" style="width:283px">
                <tbody>
                    <tr height="20">
                        <td height="20" width="89"><strong>A</strong></td>
                        <td width="194">&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>B</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>C</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>D</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>E</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>I</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>J</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>K</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>M</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>M</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>N</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>O</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>P</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>R</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>S</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>T</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>U</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>X</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>Y</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20">&nbsp;</td>
                        <td>&nbsp;</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>SHIFT+M</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>SHIFT+X</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>SHIFT+Y</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20">&nbsp;</td>
                        <td>&nbsp;</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>ALT+R</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>ALT+X</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>ALT+Y</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20">&nbsp;</td>
                        <td>&nbsp;</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>CTRL+M</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>CTRL+S</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>CTRL+X</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20">&nbsp;</td>
                        <td>&nbsp;</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>Space</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>ENTER</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>ESC</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>Del</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                </tbody>
            </table>
            <br>
        """ % (
            _("GEOMETRY EDITOR"), _("Draw an Arc"), _("Buffer Tool"), _("Copy Geo Item"),
            _("Within Add Arc will toogle the ARC direction: CW or CCW"), _("Polygon Intersection Tool"),
            _("Geo Paint Tool"), _("Jump to Location (x, y)"), _("Toggle Corner Snap"), _("Move Geo Item"),
            _("Within Add Arc will cycle through the ARC modes"), _("Draw a Polygon"), _("Draw a Circle"),
            _("Draw a Path"), _("Draw Rectangle"), _("Polygon Subtraction Tool"), _("Add Text Tool"),
            _("Polygon Union Tool"), _("Flip shape on X axis"), _("Flip shape on Y axis"), _("Distance Minimum Tool"),
            _("Skew shape on X axis"), _("Skew shape on Y axis"), _("Editor Transformation Tool"),
            _("Offset shape on X axis"), _("Offset shape on Y axis"), _("Distance Tool"),
            _("Save Object and Exit Editor"), _("Polygon Cut Tool"),
            _("Rotate Geometry"), _("Finish drawing for certain tools"), _("Abort and return to Select"),
            _("Delete Shape")
        )

        exc_sh_messages = """
        <br>
        <strong><span style="color:#ff0000">%s</span></strong><br>
        <table border="0" cellpadding="0" cellspacing="0" style="width:283px">
            <tbody>
                <tr height="20">
                    <td height="20" width="89"><strong>A</strong></td>
                    <td width="194">&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>C</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>D</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>J</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>M</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20" width="89"><strong>Q</strong></td>
                    <td width="194">&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>R</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>T</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20" width="89"><strong>W</strong></td>
                    <td width="194">&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20">&nbsp;</td>
                    <td>&nbsp;</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>SHIFT+M</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20">&nbsp;</td>
                    <td>&nbsp;</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>Del</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>Del</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20">&nbsp;</td>
                    <td>&nbsp;</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>ESC</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>CTRL+S</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
            </tbody>
        </table>
        <br>
        """ % (
            _("EXCELLON EDITOR"), _("Add Drill Array"), _("Copy Drill(s)"), _("Add Drill"),
            _("Jump to Location (x, y)"), _("Move Drill(s)"), _("Add Slot Array"), _("Resize Drill(s)"),
            _("Add a new Tool"), _("Add Slot"), _("Distance Minimum Tool"),
            _("Delete Drill(s)"), _("Alternate: Delete Tool(s)"),
            _("Abort and return to Select"), _("Save Object and Exit Editor")
        )

        grb_sh_messages = """
        <br>
        <strong><span style="color:#00ff00">%s</span></strong><br>
        <table border="0" cellpadding="0" cellspacing="0" style="width:283px">
            <tbody>
                <tr height="20">
                    <td height="20" width="89"><strong>A</strong></td>
                    <td width="194">&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>B</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>C</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>D</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>E</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>J</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>M</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>N</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>P</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>R</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>S</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>T</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>T</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20">&nbsp;</td>
                    <td>&nbsp;</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>Del</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>Del</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>ESC</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20">&nbsp;</td>
                    <td>&nbsp;</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>SHIFT+M</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20">&nbsp;</td>
                    <td>&nbsp;</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>CTRL+E</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>CTRL+S</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20">&nbsp;</td>
                    <td>&nbsp;</td>
                </tr>
                 <tr height="20">
                    <td height="20"><strong>ALT+A</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>ALT+N</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>ALT+R</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
            </tbody>
        </table>
        <br>
        """ % (
            _("GERBER EDITOR"), _("Add Pad Array"), _("Buffer"), _("Copy"), _("Add Disc"), _("Add SemiDisc"),
            _("Jump to Location (x, y)"), _("Move"), _("Add Region"), _("Add Pad"),
            _("Within Track & Region Tools will cycle in REVERSE the bend modes"), _("Scale"), _("Add Track"),
            _("Within Track & Region Tools will cycle FORWARD the bend modes"), _("Delete"),
            _("Alternate: Delete Apertures"), _("Abort and return to Select"), _("Distance Minimum Tool"),
            _("Eraser Tool"),
            _("Save Object and Exit Editor"), _("Mark Area Tool"), _("Poligonize Tool"), _("Transformation Tool")
        )

        self.editor_sh_msg = editor_title + geo_sh_messages + grb_sh_messages + exc_sh_messages

        self.sh_editor = QtWidgets.QTextEdit()
        self.sh_editor.setTextInteractionFlags(QtCore.Qt.NoTextInteraction)
        self.sh_editor.setText(self.editor_sh_msg)
        self.sh_editor.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.sh_hlay.addWidget(self.sh_editor)

        # ########################################################################
        # ########################## PLOT AREA CONTEXT MENU  # ###################
        # ########################################################################
        self.popMenu = FCMenu()

        self.popmenu_disable = self.popMenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/disable32.png'), _("Toggle Visibility"))
        self.popmenu_panel_toggle = self.popMenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/notebook16.png'), _("Toggle Panel"))

        self.popMenu.addSeparator()
        self.cmenu_newmenu = self.popMenu.addMenu(
            QtGui.QIcon(self.app.resource_location + '/file32.png'), _("New"))
        self.popmenu_new_geo = self.cmenu_newmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/new_geo32_bis.png'), _("Geometry"))
        self.popmenu_new_grb = self.cmenu_newmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/flatcam_icon32.png'), "Gerber")
        self.popmenu_new_exc = self.cmenu_newmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/new_exc32.png'), _("Excellon"))
        self.cmenu_newmenu.addSeparator()
        self.popmenu_new_prj = self.cmenu_newmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/file16.png'), _("Project"))
        self.popMenu.addSeparator()

        self.cmenu_gridmenu = self.popMenu.addMenu(
            QtGui.QIcon(self.app.resource_location + '/grid32_menu.png'), _("Grids"))

        self.cmenu_viewmenu = self.popMenu.addMenu(
            QtGui.QIcon(self.app.resource_location + '/view64.png'), _("View"))
        self.zoomfit = self.cmenu_viewmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/zoom_fit32.png'), _("Zoom Fit"))
        self.clearplot = self.cmenu_viewmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/clear_plot32.png'), _("Clear Plot"))
        self.replot = self.cmenu_viewmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/replot32.png'), _("Replot"))
        self.popMenu.addSeparator()

        self.g_editor_cmenu = self.popMenu.addMenu(
            QtGui.QIcon(self.app.resource_location + '/draw32.png'), _("Geo Editor"))
        self.draw_line = self.g_editor_cmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/path32.png'), _("Path"))
        self.draw_rect = self.g_editor_cmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/rectangle32.png'), _("Rectangle"))
        self.g_editor_cmenu.addSeparator()
        self.draw_circle = self.g_editor_cmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/circle32.png'), _("Circle"))
        self.draw_poly = self.g_editor_cmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/polygon32.png'), _("Polygon"))
        self.draw_arc = self.g_editor_cmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/arc32.png'), _("Arc"))
        self.g_editor_cmenu.addSeparator()

        self.draw_text = self.g_editor_cmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/text32.png'), _("Text"))
        self.draw_buffer = self.g_editor_cmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/buffer16-2.png'), _("Buffer"))
        self.draw_paint = self.g_editor_cmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/paint20_1.png'), _("Paint"))
        self.draw_eraser = self.g_editor_cmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/eraser26.png'), _("Eraser"))
        self.g_editor_cmenu.addSeparator()

        self.draw_union = self.g_editor_cmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/union32.png'), _("Union"))
        self.draw_intersect = self.g_editor_cmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/intersection32.png'), _("Intersection"))
        self.draw_substract = self.g_editor_cmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/subtract32.png'), _("Subtraction"))
        self.draw_cut = self.g_editor_cmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/cutpath32.png'), _("Cut"))
        self.draw_transform = self.g_editor_cmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/transform.png'), _("Transformations"))

        self.g_editor_cmenu.addSeparator()
        self.draw_move = self.g_editor_cmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/move32.png'), _("Move"))

        self.grb_editor_cmenu = self.popMenu.addMenu(
            QtGui.QIcon(self.app.resource_location + '/draw32.png'), _("Gerber Editor"))
        self.grb_draw_pad = self.grb_editor_cmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/aperture32.png'), _("Pad"))
        self.grb_draw_pad_array = self.grb_editor_cmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/padarray32.png'), _("Pad Array"))
        self.grb_editor_cmenu.addSeparator()

        self.grb_draw_track = self.grb_editor_cmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/track32.png'), _("Track"))
        self.grb_draw_region = self.grb_editor_cmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/polygon32.png'), _("Region"))
        self.grb_draw_poligonize = self.grb_editor_cmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/poligonize32.png'), _("Poligonize"))
        self.grb_draw_semidisc = self.grb_editor_cmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/semidisc32.png'), _("SemiDisc"))
        self.grb_draw_disc = self.grb_editor_cmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/disc32.png'), _("Disc"))
        self.grb_editor_cmenu.addSeparator()

        self.grb_draw_buffer = self.grb_editor_cmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/buffer16-2.png'), _("Buffer"))
        self.grb_draw_scale = self.grb_editor_cmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/scale32.png'), _("Scale"))
        self.grb_draw_markarea = self.grb_editor_cmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/markarea32.png'), _("Mark Area"))
        self.grb_draw_eraser = self.grb_editor_cmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/eraser26.png'), _("Eraser"))
        self.grb_editor_cmenu.addSeparator()

        self.grb_draw_transformations = self.grb_editor_cmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/transform.png'), _("Transformations"))

        self.e_editor_cmenu = self.popMenu.addMenu(
            QtGui.QIcon(self.app.resource_location + '/drill32.png'), _("Exc Editor"))
        self.drill = self.e_editor_cmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/drill32.png'), _("Add Drill"))
        self.drill_array = self.e_editor_cmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/addarray32.png'), _("Add Drill Array"))
        self.e_editor_cmenu.addSeparator()
        self.slot = self.e_editor_cmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/slot26.png'), _("Add Slot"))
        self.slot_array = self.e_editor_cmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/slot_array26.png'), _("Add Slot Array"))
        self.e_editor_cmenu.addSeparator()
        self.drill_resize = self.e_editor_cmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/resize16.png'), _("Resize Drill"))

        self.popMenu.addSeparator()
        self.popmenu_copy = self.popMenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/copy32.png'), _("Copy"))
        self.popmenu_delete = self.popMenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/delete32.png'), _("Delete"))
        self.popmenu_edit = self.popMenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/edit32.png'), _("Edit"))
        self.popmenu_save = self.popMenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/floppy32.png'), _("Close Editor"))
        self.popmenu_save.setVisible(False)
        self.popMenu.addSeparator()

        self.popmenu_move = self.popMenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/move32.png'), _("Move"))
        self.popmenu_properties = self.popMenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/properties32.png'), _("Properties"))

        # ########################################################################
        # ########################## INFO BAR # ##################################
        # ########################################################################
        self.infobar = self.statusBar()
        self.fcinfo = FlatCAMInfoBar(app=self.app)
        self.infobar.addWidget(self.fcinfo, stretch=1)

        self.snap_infobar_label = QtWidgets.QLabel()
        self.snap_infobar_label.setPixmap(QtGui.QPixmap(self.app.resource_location + '/snap_16.png'))
        self.infobar.addWidget(self.snap_infobar_label)

        self.rel_position_label = QtWidgets.QLabel(
            "<b>Dx</b>: 0.0000&nbsp;&nbsp;   <b>Dy</b>: 0.0000&nbsp;&nbsp;&nbsp;&nbsp;")
        self.rel_position_label.setMinimumWidth(110)
        self.rel_position_label.setToolTip(_("Relative neasurement.\nReference is last click position"))
        self.infobar.addWidget(self.rel_position_label)

        self.position_label = QtWidgets.QLabel(
            "&nbsp;&nbsp;&nbsp;&nbsp;<b>X</b>: 0.0000&nbsp;&nbsp;   <b>Y</b>: 0.0000")
        self.position_label.setMinimumWidth(110)
        self.position_label.setToolTip(_("Absolute neasurement.\nReference is (X=0, Y= 0) position"))
        self.infobar.addWidget(self.position_label)

        self.units_label = QtWidgets.QLabel("[in]")
        self.units_label.setMargin(2)
        self.infobar.addWidget(self.units_label)

        # disabled
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        # infobar.addWidget(self.progress_bar)

        # ########################################################################
        # ########################## SET GUI Elements # ##########################
        # ########################################################################
        self.app_icon = QtGui.QIcon()
        self.app_icon.addFile(self.app.resource_location + '/flatcam_icon16.png', QtCore.QSize(16, 16))
        self.app_icon.addFile(self.app.resource_location + '/flatcam_icon24.png', QtCore.QSize(24, 24))
        self.app_icon.addFile(self.app.resource_location + '/flatcam_icon32.png', QtCore.QSize(32, 32))
        self.app_icon.addFile(self.app.resource_location + '/flatcam_icon48.png', QtCore.QSize(48, 48))
        self.app_icon.addFile(self.app.resource_location + '/flatcam_icon128.png', QtCore.QSize(128, 128))
        self.app_icon.addFile(self.app.resource_location + '/flatcam_icon256.png', QtCore.QSize(256, 256))
        self.setWindowIcon(self.app_icon)

        self.setGeometry(100, 100, 1024, 650)
        self.setWindowTitle('FlatCAM %s %s - %s' %
                            (self.app.version,
                             ('BETA' if self.app.beta else ''),
                             platform.architecture()[0])
                            )

        self.filename = ""
        self.units = ""
        self.setAcceptDrops(True)

        # ########################################################################
        # ########################## Build GUI # #################################
        # ########################################################################
        self.grid_snap_btn.setCheckable(True)
        self.corner_snap_btn.setCheckable(True)
        self.update_obj_btn.setEnabled(False)
        # start with GRID activated
        self.grid_snap_btn.trigger()

        self.g_editor_cmenu.menuAction().setVisible(False)
        self.grb_editor_cmenu.menuAction().setVisible(False)
        self.e_editor_cmenu.menuAction().setVisible(False)

        self.general_defaults_form = GeneralPreferencesUI(decimals=self.decimals)
        self.gerber_defaults_form = GerberPreferencesUI(decimals=self.decimals)
        self.excellon_defaults_form = ExcellonPreferencesUI(decimals=self.decimals)
        self.geometry_defaults_form = GeometryPreferencesUI(decimals=self.decimals)
        self.cncjob_defaults_form = CNCJobPreferencesUI(decimals=self.decimals)
        self.tools_defaults_form = ToolsPreferencesUI(decimals=self.decimals)
        self.tools2_defaults_form = Tools2PreferencesUI(decimals=self.decimals)
        self.util_defaults_form = UtilPreferencesUI(decimals=self.decimals)

        QtWidgets.qApp.installEventFilter(self)

        # restore the Toolbar State from file
        settings = QSettings("Open Source", "FlatCAM")
        if settings.contains("saved_gui_state"):
            saved_gui_state = settings.value('saved_gui_state')
            self.restoreState(saved_gui_state)
            log.debug("FlatCAMGUI.__init__() --> UI state restored.")

        if settings.contains("layout"):
            layout = settings.value('layout', type=str)
            if layout == 'standard':
                # self.exc_edit_toolbar.setVisible(False)
                self.exc_edit_toolbar.setDisabled(True)
                # self.geo_edit_toolbar.setVisible(False)
                self.geo_edit_toolbar.setDisabled(True)
                # self.grb_edit_toolbar.setVisible(False)
                self.grb_edit_toolbar.setDisabled(True)

                self.corner_snap_btn.setVisible(False)
                self.snap_magnet.setVisible(False)
            elif layout == 'compact':
                self.exc_edit_toolbar.setDisabled(True)
                self.geo_edit_toolbar.setDisabled(True)
                self.grb_edit_toolbar.setDisabled(True)

                self.snap_magnet.setVisible(True)
                self.corner_snap_btn.setVisible(True)
                self.snap_magnet.setDisabled(True)
                self.corner_snap_btn.setDisabled(True)
            log.debug("FlatCAMGUI.__init__() --> UI layout restored from QSettings.")
        else:
            # self.exc_edit_toolbar.setVisible(False)
            self.exc_edit_toolbar.setDisabled(True)
            # self.geo_edit_toolbar.setVisible(False)
            self.geo_edit_toolbar.setDisabled(True)
            # self.grb_edit_toolbar.setVisible(False)
            self.grb_edit_toolbar.setDisabled(True)

            self.corner_snap_btn.setVisible(False)
            self.snap_magnet.setVisible(False)

            settings.setValue('layout', "standard")
            # This will write the setting to the platform specific storage.
            del settings
            log.debug("FlatCAMGUI.__init__() --> UI layout restored from defaults. QSettings set to 'standard'")

        # construct the Toolbar Lock menu entry to the context menu of the QMainWindow
        self.lock_action = QtWidgets.QAction()
        self.lock_action.setText(_("Lock Toolbars"))
        self.lock_action.setCheckable(True)

        settings = QSettings("Open Source", "FlatCAM")
        if settings.contains("toolbar_lock"):
            lock_val = settings.value('toolbar_lock')
            if lock_val == 'true':
                lock_state = True
                self.lock_action.setChecked(True)
            else:

                lock_state = False
                self.lock_action.setChecked(False)
        else:
            lock_state = False
            settings.setValue('toolbar_lock', lock_state)

            # This will write the setting to the platform specific storage.
            del settings

        self.lock_toolbar(lock=lock_state)
        self.lock_action.triggered[bool].connect(self.lock_toolbar)

        # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
        # %%%%%%%%%%%%%%%%% GUI Building FINISHED %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
        # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

    def eventFilter(self, obj, event):
        """
        Filter the ToolTips display based on a Preferences setting

        :param obj:
        :param event: QT event to filter
        :return:
        """
        if self.general_defaults_form.general_gui_set_group.toggle_tooltips_cb.get_value() is False:
            if event.type() == QtCore.QEvent.ToolTip:
                return True
            else:
                return False

        return False

    def populate_toolbars(self):
        """
        Will populate the App Toolbars with theie actions
        :return: None
        """

        # ## File Toolbar # ##
        self.file_open_gerber_btn = self.toolbarfile.addAction(
            QtGui.QIcon(self.app.resource_location + '/flatcam_icon32.png'), _("Open Gerber"))
        self.file_open_excellon_btn = self.toolbarfile.addAction(
            QtGui.QIcon(self.app.resource_location + '/drill32.png'), _("Open Excellon"))
        self.toolbarfile.addSeparator()
        self.file_open_btn = self.toolbarfile.addAction(
            QtGui.QIcon(self.app.resource_location + '/folder32.png'), _("Open project"))
        self.file_save_btn = self.toolbarfile.addAction(
            QtGui.QIcon(self.app.resource_location + '/project_save32.png'), _("Save project"))

        # ## Edit Toolbar # ##
        self.newgeo_btn = self.toolbargeo.addAction(
            QtGui.QIcon(self.app.resource_location + '/new_file_geo32.png'), _("New Blank Geometry"))
        self.newgrb_btn = self.toolbargeo.addAction(
            QtGui.QIcon(self.app.resource_location + '/new_file_grb32.png'), _("New Blank Gerber"))
        self.newexc_btn = self.toolbargeo.addAction(
            QtGui.QIcon(self.app.resource_location + '/new_file_exc32.png'), _("New Blank Excellon"))
        self.toolbargeo.addSeparator()
        self.editgeo_btn = self.toolbargeo.addAction(
            QtGui.QIcon(self.app.resource_location + '/edit32.png'), _("Editor"))
        self.update_obj_btn = self.toolbargeo.addAction(
            QtGui.QIcon(self.app.resource_location + '/close_edit_file32.png'),
            _("Save Object and close the Editor")
        )

        self.toolbargeo.addSeparator()
        self.copy_btn = self.toolbargeo.addAction(
            QtGui.QIcon(self.app.resource_location + '/copy_file32.png'), _("Copy"))
        self.delete_btn = self.toolbargeo.addAction(
            QtGui.QIcon(self.app.resource_location + '/delete_file32.png'), _("&Delete"))
        self.toolbargeo.addSeparator()
        self.distance_btn = self.toolbargeo.addAction(
            QtGui.QIcon(self.app.resource_location + '/distance32.png'), _("Distance Tool"))
        self.distance_min_btn = self.toolbargeo.addAction(
            QtGui.QIcon(self.app.resource_location + '/distance_min32.png'), _("Distance Min Tool"))
        self.origin_btn = self.toolbargeo.addAction(
            QtGui.QIcon(self.app.resource_location + '/origin32.png'), _('Set Origin'))
        self.jmp_btn = self.toolbargeo.addAction(
            QtGui.QIcon(self.app.resource_location + '/jump_to16.png'), _('Jump to Location'))

        # ## View Toolbar # ##
        self.replot_btn = self.toolbarview.addAction(
            QtGui.QIcon(self.app.resource_location + '/replot32.png'), _("&Replot"))
        self.clear_plot_btn = self.toolbarview.addAction(
            QtGui.QIcon(self.app.resource_location + '/clear_plot32.png'), _("&Clear plot"))
        self.zoom_in_btn = self.toolbarview.addAction(
            QtGui.QIcon(self.app.resource_location + '/zoom_in32.png'), _("Zoom In"))
        self.zoom_out_btn = self.toolbarview.addAction(
            QtGui.QIcon(self.app.resource_location + '/zoom_out32.png'), _("Zoom Out"))
        self.zoom_fit_btn = self.toolbarview.addAction(
            QtGui.QIcon(self.app.resource_location + '/zoom_fit32.png'), _("Zoom Fit"))

        # self.toolbarview.setVisible(False)

        # ## Shell Toolbar # ##
        self.shell_btn = self.toolbarshell.addAction(
            QtGui.QIcon(self.app.resource_location + '/shell32.png'), _("&Command Line"))
        self.new_script_btn = self.toolbarshell.addAction(
            QtGui.QIcon(self.app.resource_location + '/script_new24.png'), _('New Script ...'))
        self.open_script_btn = self.toolbarshell.addAction(
            QtGui.QIcon(self.app.resource_location + '/open_script32.png'), _('Open Script ...'))
        self.run_script_btn = self.toolbarshell.addAction(
            QtGui.QIcon(self.app.resource_location + '/script16.png'), _('Run Script ...'))

        # ## Tools Toolbar # ##
        self.dblsided_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/doubleside32.png'), _("2Sided Tool"))
        self.cutout_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/cut16_bis.png'), _("&Cutout Tool"))
        self.ncc_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/ncc16.png'), _("NCC Tool"))
        self.paint_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/paint20_1.png'), _("Paint Tool"))
        self.toolbartools.addSeparator()

        self.panelize_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/panelize32.png'), _("Panel Tool"))
        self.film_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/film16.png'), _("Film Tool"))
        self.solder_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/solderpastebis32.png'),
                                                      _("SolderPaste Tool"))
        self.sub_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/sub32.png'), _("Subtract Tool"))

        self.toolbartools.addSeparator()

        self.calculators_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/calculator24.png'), _("Calculators Tool"))
        self.transform_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/transform.png'), _("Transform Tool"))
        self.qrcode_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/qrcode32.png'), _("QRCode Tool"))
        self.copperfill_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/copperfill32.png'), _("Copper Thieving Tool"))

        self.fiducials_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/fiducials_32.png'), _("Fiducials Tool"))
        self.cal_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/calibrate_32.png'), _("Calibration Tool"))

        # ## Excellon Editor Toolbar # ##
        self.select_drill_btn = self.exc_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/pointer32.png'), _("Select"))
        self.add_drill_btn = self.exc_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/plus16.png'), _('Add Drill Hole'))
        self.add_drill_array_btn = self.exc_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/addarray16.png'), _('Add Drill Hole Array'))
        self.resize_drill_btn = self.exc_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/resize16.png'), _('Resize Drill'))
        self.add_slot_btn = self.exc_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/slot26.png'), _('Add Slot'))
        self.add_slot_array_btn = self.exc_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/slot_array26.png'), _('Add Slot Array'))
        self.exc_edit_toolbar.addSeparator()

        self.copy_drill_btn = self.exc_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/copy32.png'), _('Copy Drill'))
        self.delete_drill_btn = self.exc_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/trash32.png'), _("Delete Drill"))

        self.exc_edit_toolbar.addSeparator()
        self.move_drill_btn = self.exc_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/move32.png'), _("Move Drill"))

        # ## Geometry Editor Toolbar # ##
        self.geo_select_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/pointer32.png'), _("Select 'Esc'"))
        self.geo_add_circle_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/circle32.png'), _('Add Circle'))
        self.geo_add_arc_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/arc32.png'), _('Add Arc'))
        self.geo_add_rectangle_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/rectangle32.png'), _('Add Rectangle'))

        self.geo_edit_toolbar.addSeparator()
        self.geo_add_path_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/path32.png'), _('Add Path'))
        self.geo_add_polygon_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/polygon32.png'), _('Add Polygon'))
        self.geo_edit_toolbar.addSeparator()
        self.geo_add_text_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/text32.png'), _('Add Text'))
        self.geo_add_buffer_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/buffer16-2.png'), _('Add Buffer'))
        self.geo_add_paint_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/paint20_1.png'), _('Paint Shape'))
        self.geo_eraser_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/eraser26.png'), _('Eraser'))

        self.geo_edit_toolbar.addSeparator()
        self.geo_union_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/union32.png'), _('Polygon Union'))
        self.geo_explode_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/explode32.png'), _('Polygon Explode'))

        self.geo_intersection_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/intersection32.png'), _('Polygon Intersection'))
        self.geo_subtract_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/subtract32.png'), _('Polygon Subtraction'))

        self.geo_edit_toolbar.addSeparator()
        self.geo_cutpath_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/cutpath32.png'), _('Cut Path'))
        self.geo_copy_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/copy32.png'), _("Copy Objects"))
        self.geo_delete_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/trash32.png'), _("Delete Shape"))
        self.geo_transform_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/transform.png'), _("Transformations"))

        self.geo_edit_toolbar.addSeparator()
        self.geo_move_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/move32.png'), _("Move Objects"))

        # ## Gerber Editor Toolbar # ##
        self.grb_select_btn = self.grb_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/pointer32.png'), _("Select"))
        self.grb_add_pad_btn = self.grb_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/aperture32.png'), _("Add Pad"))
        self.add_pad_ar_btn = self.grb_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/padarray32.png'), _('Add Pad Array'))
        self.grb_add_track_btn = self.grb_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/track32.png'), _("Add Track"))
        self.grb_add_region_btn = self.grb_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/polygon32.png'), _("Add Region"))
        self.grb_convert_poly_btn = self.grb_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/poligonize32.png'), _("Poligonize"))

        self.grb_add_semidisc_btn = self.grb_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/semidisc32.png'), _("SemiDisc"))
        self.grb_add_disc_btn = self.grb_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/disc32.png'), _("Disc"))
        self.grb_edit_toolbar.addSeparator()

        self.aperture_buffer_btn = self.grb_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/buffer16-2.png'), _('Buffer'))
        self.aperture_scale_btn = self.grb_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/scale32.png'), _('Scale'))
        self.aperture_markarea_btn = self.grb_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/markarea32.png'), _('Mark Area'))
        self.aperture_eraser_btn = self.grb_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/eraser26.png'), _('Eraser'))

        self.grb_edit_toolbar.addSeparator()
        self.aperture_copy_btn = self.grb_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/copy32.png'), _("Copy"))
        self.aperture_delete_btn = self.grb_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/trash32.png'), _("Delete"))
        self.grb_transform_btn = self.grb_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/transform.png'), _("Transformations"))
        self.grb_edit_toolbar.addSeparator()
        self.aperture_move_btn = self.grb_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/move32.png'), _("Move"))

        # ## Snap Toolbar # ##
        # Snap GRID toolbar is always active to facilitate usage of measurements done on GRID
        # self.addToolBar(self.snap_toolbar)

        self.grid_snap_btn = self.snap_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/grid32.png'), _('Snap to grid'))
        self.grid_gap_x_entry = FCEntry2()
        self.grid_gap_x_entry.setMaximumWidth(70)
        self.grid_gap_x_entry.setToolTip(_("Grid X snapping distance"))
        self.snap_toolbar.addWidget(self.grid_gap_x_entry)

        self.grid_gap_y_entry = FCEntry2()
        self.grid_gap_y_entry.setMaximumWidth(70)
        self.grid_gap_y_entry.setToolTip(_("Grid Y snapping distance"))
        self.snap_toolbar.addWidget(self.grid_gap_y_entry)

        self.grid_space_label = QtWidgets.QLabel("  ")
        self.snap_toolbar.addWidget(self.grid_space_label)
        self.grid_gap_link_cb = FCCheckBox()
        self.grid_gap_link_cb.setToolTip(_("When active, value on Grid_X\n" 
                                           "is copied to the Grid_Y value."))
        self.snap_toolbar.addWidget(self.grid_gap_link_cb)

        self.ois_grid = OptionalInputSection(self.grid_gap_link_cb, [self.grid_gap_y_entry], logic=False)

        self.corner_snap_btn = self.snap_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/corner32.png'), _('Snap to corner'))

        self.snap_max_dist_entry = FCEntry()
        self.snap_max_dist_entry.setMaximumWidth(70)
        self.snap_max_dist_entry.setToolTip(_("Max. magnet distance"))
        self.snap_magnet = self.snap_toolbar.addWidget(self.snap_max_dist_entry)

        self.grid_snap_btn.setCheckable(True)
        self.corner_snap_btn.setCheckable(True)
        self.update_obj_btn.setEnabled(False)
        # start with GRID activated
        self.grid_snap_btn.trigger()

        settings = QSettings("Open Source", "FlatCAM")
        if settings.contains("layout"):
            layout = settings.value('layout', type=str)
            if layout == 'standard':
                self.exc_edit_toolbar.setVisible(True)
                self.exc_edit_toolbar.setDisabled(True)
                self.geo_edit_toolbar.setVisible(True)
                self.geo_edit_toolbar.setDisabled(True)
                self.grb_edit_toolbar.setVisible(True)
                self.grb_edit_toolbar.setDisabled(True)

                self.corner_snap_btn.setVisible(False)
                self.snap_magnet.setVisible(False)
            elif layout == 'compact':
                self.exc_edit_toolbar.setVisible(True)
                self.exc_edit_toolbar.setDisabled(True)
                self.geo_edit_toolbar.setVisible(True)
                self.geo_edit_toolbar.setDisabled(True)
                self.grb_edit_toolbar.setVisible(True)
                self.grb_edit_toolbar.setDisabled(True)

                self.corner_snap_btn.setVisible(True)
                self.snap_magnet.setVisible(True)
                self.corner_snap_btn.setDisabled(True)
                self.snap_magnet.setDisabled(True)

    def keyPressEvent(self, event):
        """
        Key event handler for the entire app.
        Some of the key events are also treated locally in the FlatCAM editors

        :param event: QT event
        :return:
        """
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        active = self.app.collection.get_active()
        selected = self.app.collection.get_selected()

        matplotlib_key_flag = False

        # events out of the self.app.collection view (it's about Project Tab) are of type int
        if type(event) is int:
            key = event
        # events from the GUI are of type QKeyEvent
        elif type(event) == QtGui.QKeyEvent:
            key = event.key()
        elif isinstance(event, mpl_key_event):  # MatPlotLib key events are trickier to interpret than the rest
            matplotlib_key_flag = True

            key = event.key
            key = QtGui.QKeySequence(key)

            # check for modifiers
            key_string = key.toString().lower()
            if '+' in key_string:
                mod, __, key_text = key_string.rpartition('+')
                if mod.lower() == 'ctrl':
                    modifiers = QtCore.Qt.ControlModifier
                elif mod.lower() == 'alt':
                    modifiers = QtCore.Qt.AltModifier
                elif mod.lower() == 'shift':
                    modifiers = QtCore.Qt.ShiftModifier
                else:
                    modifiers = QtCore.Qt.NoModifier
                key = QtGui.QKeySequence(key_text)

        # events from Vispy are of type KeyEvent
        else:
            key = event.key

        if self.app.call_source == 'app':
            if modifiers == QtCore.Qt.ControlModifier | QtCore.Qt.AltModifier:
                if key == QtCore.Qt.Key_X:
                    self.app.abort_all_tasks()
                    return

            elif modifiers == QtCore.Qt.ControlModifier:
                # Select All
                if key == QtCore.Qt.Key_A:
                    self.app.on_selectall()

                # Copy an FlatCAM object
                if key == QtCore.Qt.Key_C:
                    widget_name = self.plot_tab_area.currentWidget().objectName()
                    if widget_name == 'database_tab':
                        # Tools DB saved, update flag
                        self.app.tools_db_changed_flag = True
                        self.app.tools_db_tab.on_tool_copy()
                        return

                    self.app.on_copy_object()

                # Copy an FlatCAM object
                if key == QtCore.Qt.Key_D:
                    self.app.on_tools_database()

                # Open Excellon file
                if key == QtCore.Qt.Key_E:
                    self.app.on_fileopenexcellon()

                # Open Gerber file
                if key == QtCore.Qt.Key_G:
                    self.app.on_fileopengerber()

                # Distance Tool
                if key == QtCore.Qt.Key_M:
                    self.app.distance_tool.run()

                # Create New Project
                if key == QtCore.Qt.Key_N:
                    self.app.on_file_new_click()

                # Open Project
                if key == QtCore.Qt.Key_O:
                    self.app.on_file_openproject()

                # Open Project
                if key == QtCore.Qt.Key_P:
                    self.app.on_file_save_objects_pdf(use_thread=True)

                # PDF Import
                if key == QtCore.Qt.Key_Q:
                    self.app.pdf_tool.run()

                # Save Project
                if key == QtCore.Qt.Key_S:
                    widget_name = self.plot_tab_area.currentWidget().objectName()
                    if widget_name == 'preferences_tab':
                        self.app.on_save_button(save_to_file=False)
                        return

                    if widget_name == 'database_tab':
                        # Tools DB saved, update flag
                        self.app.tools_db_changed_flag = False
                        self.app.tools_db_tab.on_save_tools_db()
                        return

                    self.app.on_file_saveproject()

                # Toggle Plot Area
                if key == QtCore.Qt.Key_F10 or key == 'F10':
                    self.app.on_toggle_plotarea()

                return
            elif modifiers == QtCore.Qt.ShiftModifier:

                # Copy Object Name
                if key == QtCore.Qt.Key_C:
                    self.app.on_copy_name()

                # Toggle Code Editor
                if key == QtCore.Qt.Key_E:
                    self.app.on_toggle_code_editor()

                # Toggle axis
                if key == QtCore.Qt.Key_G:
                    self.app.on_toggle_axis()

                # Run Distance Minimum Tool
                if key == QtCore.Qt.Key_M:
                    self.app.distance_min_tool.run()
                    return

                # Open Preferences Window
                if key == QtCore.Qt.Key_P:
                    self.app.on_preferences()
                    return

                # Rotate Object by 90 degree CCW
                if key == QtCore.Qt.Key_R:
                    self.app.on_rotate(silent=True, preset=-float(self.app.defaults['tools_transform_rotate']))
                    return

                # Run a Script
                if key == QtCore.Qt.Key_S:
                    self.app.on_filerunscript()
                    return

                # Toggle Workspace
                if key == QtCore.Qt.Key_W:
                    self.app.on_workspace_toggle()
                    return

                # Skew on X axis
                if key == QtCore.Qt.Key_X:
                    self.app.on_skewx()
                    return

                # Skew on Y axis
                if key == QtCore.Qt.Key_Y:
                    self.app.on_skewy()
                    return
            elif modifiers == QtCore.Qt.AltModifier:

                # Eanble all plots
                if key == Qt.Key_1:
                    self.app.enable_all_plots()

                # Disable all plots
                if key == Qt.Key_2:
                    self.app.disable_all_plots()

                # Disable all other plots
                if key == Qt.Key_3:
                    self.app.disable_other_plots()

                # Calculator Tool
                if key == QtCore.Qt.Key_C:
                    self.app.calculator_tool.run(toggle=True)

                # 2-Sided PCB Tool
                if key == QtCore.Qt.Key_D:
                    self.app.dblsidedtool.run(toggle=True)
                    return

                # Calibration  Tool
                if key == QtCore.Qt.Key_E:
                    self.app.cal_exc_tool.run(toggle=True)
                    return

                # Copper Thieving Tool
                if key == QtCore.Qt.Key_F:
                    self.app.copper_thieving_tool.run(toggle=True)
                    return

                # Toggle Grid lines
                if key == QtCore.Qt.Key_G:
                    self.app.on_toggle_grid_lines()
                    return

                # Fiducials Tool
                if key == QtCore.Qt.Key_J:
                    self.app.fiducial_tool.run(toggle=True)
                    return

                # Solder Paste Dispensing Tool
                if key == QtCore.Qt.Key_K:
                    self.app.paste_tool.run(toggle=True)
                    return

                # Film Tool
                if key == QtCore.Qt.Key_L:
                    self.app.film_tool.run(toggle=True)
                    return

                # Non-Copper Clear Tool
                if key == QtCore.Qt.Key_N:
                    self.app.ncclear_tool.run(toggle=True)
                    return

                # Optimal Tool
                if key == QtCore.Qt.Key_O:
                    self.app.optimal_tool.run(toggle=True)
                    return

                # Paint Tool
                if key == QtCore.Qt.Key_P:
                    self.app.paint_tool.run(toggle=True)
                    return

                # QRCode Tool
                if key == QtCore.Qt.Key_Q:
                    self.app.qrcode_tool.run()
                    return

                # Rules Tool
                if key == QtCore.Qt.Key_R:
                    self.app.rules_tool.run(toggle=True)
                    return

                # View Source Object Content
                if key == QtCore.Qt.Key_S:
                    self.app.on_view_source()
                    return

                # Transformation Tool
                if key == QtCore.Qt.Key_T:
                    self.app.transform_tool.run(toggle=True)
                    return

                # Substract Tool
                if key == QtCore.Qt.Key_W:
                    self.app.sub_tool.run(toggle=True)
                    return

                # Cutout Tool
                if key == QtCore.Qt.Key_X:
                    self.app.cutout_tool.run(toggle=True)
                    return

                # Panelize Tool
                if key == QtCore.Qt.Key_Z:
                    self.app.panelize_tool.run(toggle=True)
                    return

                # Toggle Fullscreen
                if key == QtCore.Qt.Key_F10 or key == 'F10':
                    self.app.on_fullscreen()
                    return
            elif modifiers == QtCore.Qt.NoModifier:
                # Open Manual
                if key == QtCore.Qt.Key_F1 or key == 'F1':
                    webbrowser.open(self.app.manual_url)

                # Show shortcut list
                if key == QtCore.Qt.Key_F3 or key == 'F3':
                    self.app.on_shortcut_list()

                # Open Video Help
                if key == QtCore.Qt.Key_F4 or key == 'F4':
                    webbrowser.open(self.app.video_url)

                # Open Video Help
                if key == QtCore.Qt.Key_F5 or key == 'F5':
                    self.app.plot_all()

                # Switch to Project Tab
                if key == QtCore.Qt.Key_1:
                    self.app.on_select_tab('project')

                # Switch to Selected Tab
                if key == QtCore.Qt.Key_2:
                    self.app.on_select_tab('selected')

                # Switch to Tool Tab
                if key == QtCore.Qt.Key_3:
                    self.app.on_select_tab('tool')

                # Delete from PyQt
                # It's meant to make a difference between delete objects and delete tools in
                # Geometry Selected tool table
                if key == QtCore.Qt.Key_Delete and matplotlib_key_flag is False:
                    widget_name = self.plot_tab_area.currentWidget().objectName()
                    if widget_name == 'database_tab':
                        # Tools DB saved, update flag
                        self.app.tools_db_changed_flag = True
                        self.app.tools_db_tab.on_tool_delete()
                        return

                    self.app.on_delete_keypress()

                # Delete from canvas
                if key == 'Delete':
                    # Delete via the application to
                    # ensure cleanup of the GUI
                    if active:
                        active.app.on_delete()

                # Escape = Deselect All
                if key == QtCore.Qt.Key_Escape or key == 'Escape':
                    self.app.on_deselect_all()

                    # if in full screen, exit to normal view
                    if self.app.toggle_fscreen is True:
                        self.app.on_fullscreen(disable=True)

                    # try to disconnect the slot from Set Origin
                    try:
                        self.app.plotcanvas.graph_event_disconnect('mouse_press', self.app.on_set_zero_click)
                    except TypeError:
                        pass
                    self.app.inform.emit("")

                # Space = Toggle Active/Inactive
                if key == QtCore.Qt.Key_Space:
                    for select in selected:
                        select.ui.plot_cb.toggle()
                    self.app.collection.update_view()
                    self.app.delete_selection_shape()

                # New Geometry
                if key == QtCore.Qt.Key_B:
                    self.app.new_gerber_object()

                # New Geometry
                if key == QtCore.Qt.Key_D:
                    self.app.new_document_object()

                # Copy Object Name
                if key == QtCore.Qt.Key_E:
                    self.app.object2editor()

                # Grid toggle
                if key == QtCore.Qt.Key_G:
                    self.app.ui.grid_snap_btn.trigger()

                # Jump to coords
                if key == QtCore.Qt.Key_J:
                    self.app.on_jump_to()

                # New Excellon
                if key == QtCore.Qt.Key_L:
                    self.app.new_excellon_object()

                # Move tool toggle
                if key == QtCore.Qt.Key_M:
                    self.app.move_tool.toggle()

                # New Geometry
                if key == QtCore.Qt.Key_N:
                    self.app.new_geometry_object()

                # Set Origin
                if key == QtCore.Qt.Key_O:
                    self.app.on_set_origin()
                    return

                # Properties Tool
                if key == QtCore.Qt.Key_P:
                    self.app.properties_tool.run()
                    return

                # Change Units
                if key == QtCore.Qt.Key_Q:
                    # if self.app.defaults["units"] == 'MM':
                    #     self.app.ui.general_defaults_form.general_app_group.units_radio.set_value("IN")
                    # else:
                    #     self.app.ui.general_defaults_form.general_app_group.units_radio.set_value("MM")
                    # self.app.on_toggle_units(no_pref=True)
                    self.app.on_toggle_units_click()

                # Rotate Object by 90 degree CW
                if key == QtCore.Qt.Key_R:
                    self.app.on_rotate(silent=True, preset=self.app.defaults['tools_transform_rotate'])

                # Shell toggle
                if key == QtCore.Qt.Key_S:
                    self.app.on_toggle_shell()

                # Add a Tool from shortcut
                if key == QtCore.Qt.Key_T:
                    widget_name = self.plot_tab_area.currentWidget().objectName()
                    if widget_name == 'database_tab':
                        # Tools DB saved, update flag
                        self.app.tools_db_changed_flag = True
                        self.app.tools_db_tab.on_tool_add()
                        return

                    self.app.on_tool_add_keypress()

                # Zoom Fit
                if key == QtCore.Qt.Key_V:
                    self.app.on_zoom_fit(None)

                # Mirror on X the selected object(s)
                if key == QtCore.Qt.Key_X:
                    self.app.on_flipx()

                # Mirror on Y the selected object(s)
                if key == QtCore.Qt.Key_Y:
                    self.app.on_flipy()

                # Zoom In
                if key == QtCore.Qt.Key_Equal:
                    self.app.plotcanvas.zoom(1 / self.app.defaults['global_zoom_ratio'], self.app.mouse)

                # Zoom Out
                if key == QtCore.Qt.Key_Minus:
                    self.app.plotcanvas.zoom(self.app.defaults['global_zoom_ratio'], self.app.mouse)

                # toggle display of Notebook area
                if key == QtCore.Qt.Key_QuoteLeft:
                    self.app.on_toggle_notebook()

                return
        elif self.app.call_source == 'geo_editor':
            if modifiers == QtCore.Qt.ControlModifier:
                # save (update) the current geometry and return to the App
                if key == QtCore.Qt.Key_S or key == 'S':
                    self.app.editor2object()
                    return

                # toggle the measurement tool
                if key == QtCore.Qt.Key_M or key == 'M':
                    self.app.distance_tool.run()
                    return

                # Cut Action Tool
                if key == QtCore.Qt.Key_X or key == 'X':
                    if self.app.geo_editor.get_selected() is not None:
                        self.app.geo_editor.cutpath()
                    else:
                        msg = _('Please first select a geometry item to be cutted\n'
                                'then select the geometry item that will be cutted\n'
                                'out of the first item. In the end press ~X~ key or\n'
                                'the toolbar button.')

                        messagebox = QtWidgets.QMessageBox()
                        messagebox.setText(msg)
                        messagebox.setWindowTitle(_("Warning"))
                        messagebox.setWindowIcon(QtGui.QIcon(self.app.resource_location + '/warning.png'))
                        messagebox.setStandardButtons(QtWidgets.QMessageBox.Ok)
                        messagebox.setDefaultButton(QtWidgets.QMessageBox.Ok)
                        messagebox.exec_()
                    return
            elif modifiers == QtCore.Qt.ShiftModifier:
                # Run Distance Minimum Tool
                if key == QtCore.Qt.Key_M or key == 'M':
                    self.app.distance_min_tool.run()
                    return

                # Skew on X axis
                if key == QtCore.Qt.Key_X or key == 'X':
                    self.app.geo_editor.transform_tool.on_skewx_key()
                    return

                # Skew on Y axis
                if key == QtCore.Qt.Key_Y or key == 'Y':
                    self.app.geo_editor.transform_tool.on_skewy_key()
                    return
            elif modifiers == QtCore.Qt.AltModifier:

                # Transformation Tool
                if key == QtCore.Qt.Key_R or key == 'R':
                    self.app.geo_editor.select_tool('transform')
                    return

                # Offset on X axis
                if key == QtCore.Qt.Key_X or key == 'X':
                    self.app.geo_editor.transform_tool.on_offx_key()
                    return

                # Offset on Y axis
                if key == QtCore.Qt.Key_Y or key == 'Y':
                    self.app.geo_editor.transform_tool.on_offy_key()
                    return
            elif modifiers == QtCore.Qt.NoModifier:
                # toggle display of Notebook area
                if key == QtCore.Qt.Key_QuoteLeft or key == '`':
                    self.app.on_toggle_notebook()

                # Finish the current action. Use with tools that do not
                # complete automatically, like a polygon or path.
                if key == QtCore.Qt.Key_Enter or key == 'Enter':
                    if isinstance(self.app.geo_editor.active_tool, FCShapeTool):
                        if self.app.geo_editor.active_tool.name == 'rotate':
                            self.app.geo_editor.active_tool.make()

                            if self.app.geo_editor.active_tool.complete:
                                self.app.geo_editor.on_shape_complete()
                                self.app.inform.emit('[success] %s' % _("Done."))
                            # automatically make the selection tool active after completing current action
                            self.app.geo_editor.select_tool('select')
                            return
                        else:
                            self.app.geo_editor.active_tool.click(
                                self.app.geo_editor.snap(self.app.geo_editor.x, self.app.geo_editor.y))

                            self.app.geo_editor.active_tool.make()

                            if self.app.geo_editor.active_tool.complete:
                                self.app.geo_editor.on_shape_complete()
                                self.app.inform.emit('[success] %s' % _("Done."))
                            # automatically make the selection tool active after completing current action
                            self.app.geo_editor.select_tool('select')

                # Abort the current action
                if key == QtCore.Qt.Key_Escape or key == 'Escape':
                    # TODO: ...?
                    # self.on_tool_select("select")
                    self.app.inform.emit('[WARNING_NOTCL] %s' %
                                         _("Cancelled."))

                    self.app.geo_editor.delete_utility_geometry()

                    # deselect any shape that might be selected
                    self.app.geo_editor.selected = []

                    self.app.geo_editor.replot()
                    self.app.geo_editor.select_tool('select')

                    # hide the notebook
                    self.app.ui.splitter.setSizes([0, 1])
                    return

                # Delete selected object
                if key == QtCore.Qt.Key_Delete or key == 'Delete':
                    self.app.geo_editor.delete_selected()
                    self.app.geo_editor.replot()

                # Rotate
                if key == QtCore.Qt.Key_Space or key == 'Space':
                    self.app.geo_editor.transform_tool.on_rotate_key()

                # Zoom Out
                if key == QtCore.Qt.Key_Minus or key == '-':
                    self.app.plotcanvas.zoom(1 / self.app.defaults['global_zoom_ratio'],
                                             [self.app.geo_editor.snap_x, self.app.geo_editor.snap_y])

                # Zoom In
                if key == QtCore.Qt.Key_Equal or key == '=':
                    self.app.plotcanvas.zoom(self.app.defaults['global_zoom_ratio'],
                                             [self.app.geo_editor.snap_x, self.app.geo_editor.snap_y])

                # Switch to Project Tab
                if key == QtCore.Qt.Key_1 or key == '1':
                    self.app.on_select_tab('project')

                # Switch to Selected Tab
                if key == QtCore.Qt.Key_2 or key == '2':
                    self.app.on_select_tab('selected')

                # Switch to Tool Tab
                if key == QtCore.Qt.Key_3 or key == '3':
                    self.app.on_select_tab('tool')

                if self.app.geo_editor.active_tool is not None and self.geo_select_btn.isChecked() is False:
                    response = self.app.geo_editor.active_tool.on_key(key=key)
                    if response is not None:
                        self.app.inform.emit(response)
                else:
                    # Arc Tool
                    if key == QtCore.Qt.Key_A or key == 'A':
                        self.app.geo_editor.select_tool('arc')

                    # Buffer
                    if key == QtCore.Qt.Key_B or key == 'B':
                        self.app.geo_editor.select_tool('buffer')

                    # Copy
                    if key == QtCore.Qt.Key_C or key == 'C':
                        self.app.geo_editor.on_copy_click()

                    # Substract Tool
                    if key == QtCore.Qt.Key_E or key == 'E':
                        if self.app.geo_editor.get_selected() is not None:
                            self.app.geo_editor.intersection()
                        else:
                            msg = _("Please select geometry items \n"
                                    "on which to perform Intersection Tool.")

                            messagebox = QtWidgets.QMessageBox()
                            messagebox.setText(msg)
                            messagebox.setWindowTitle(_("Warning"))
                            messagebox.setWindowIcon(QtGui.QIcon(self.app.resource_location + '/warning.png'))
                            messagebox.setStandardButtons(QtWidgets.QMessageBox.Ok)
                            messagebox.setDefaultButton(QtWidgets.QMessageBox.Ok)
                            messagebox.exec_()

                    # Grid Snap
                    if key == QtCore.Qt.Key_G or key == 'G':
                        self.app.ui.grid_snap_btn.trigger()

                        # make sure that the cursor shape is enabled/disabled, too
                        if self.app.geo_editor.options['grid_snap'] is True:
                            self.app.app_cursor.enabled = True
                        else:
                            self.app.app_cursor.enabled = False

                    # Paint
                    if key == QtCore.Qt.Key_I or key == 'I':
                        self.app.geo_editor.select_tool('paint')

                    # Jump to coords
                    if key == QtCore.Qt.Key_J or key == 'J':
                        self.app.on_jump_to()

                    # Corner Snap
                    if key == QtCore.Qt.Key_K or key == 'K':
                        self.app.geo_editor.on_corner_snap()

                    # Move
                    if key == QtCore.Qt.Key_M or key == 'M':
                        self.app.geo_editor.on_move_click()

                    # Polygon Tool
                    if key == QtCore.Qt.Key_N or key == 'N':
                        self.app.geo_editor.select_tool('polygon')

                    # Circle Tool
                    if key == QtCore.Qt.Key_O or key == 'O':
                        self.app.geo_editor.select_tool('circle')

                    # Path Tool
                    if key == QtCore.Qt.Key_P or key == 'P':
                        self.app.geo_editor.select_tool('path')

                    # Rectangle Tool
                    if key == QtCore.Qt.Key_R or key == 'R':
                        self.app.geo_editor.select_tool('rectangle')

                    # Substract Tool
                    if key == QtCore.Qt.Key_S or key == 'S':
                        if self.app.geo_editor.get_selected() is not None:
                            self.app.geo_editor.subtract()
                        else:
                            msg = _(
                                "Please select geometry items \n"
                                "on which to perform Substraction Tool.")

                            messagebox = QtWidgets.QMessageBox()
                            messagebox.setText(msg)
                            messagebox.setWindowTitle(_("Warning"))
                            messagebox.setWindowIcon(QtGui.QIcon(self.app.resource_location + '/warning.png'))
                            messagebox.setStandardButtons(QtWidgets.QMessageBox.Ok)
                            messagebox.setDefaultButton(QtWidgets.QMessageBox.Ok)
                            messagebox.exec_()

                    # Add Text Tool
                    if key == QtCore.Qt.Key_T or key == 'T':
                        self.app.geo_editor.select_tool('text')

                    # Substract Tool
                    if key == QtCore.Qt.Key_U or key == 'U':
                        if self.app.geo_editor.get_selected() is not None:
                            self.app.geo_editor.union()
                        else:
                            msg = _("Please select geometry items \n"
                                    "on which to perform union.")

                            messagebox = QtWidgets.QMessageBox()
                            messagebox.setText(msg)
                            messagebox.setWindowTitle(_("Warning"))
                            messagebox.setWindowIcon(QtGui.QIcon(self.app.resource_location + '/warning.png'))
                            messagebox.setStandardButtons(QtWidgets.QMessageBox.Ok)
                            messagebox.setDefaultButton(QtWidgets.QMessageBox.Ok)
                            messagebox.exec_()

                    if key == QtCore.Qt.Key_V or key == 'V':
                        self.app.on_zoom_fit(None)

                    # Flip on X axis
                    if key == QtCore.Qt.Key_X or key == 'X':
                        self.app.geo_editor.transform_tool.on_flipx()
                        return

                    # Flip on Y axis
                    if key == QtCore.Qt.Key_Y or key == 'Y':
                        self.app.geo_editor.transform_tool.on_flipy()
                        return

                # Show Shortcut list
                if key == 'F3':
                    self.app.on_shortcut_list()
        elif self.app.call_source == 'grb_editor':
            if modifiers == QtCore.Qt.ControlModifier:
                # Eraser Tool
                if key == QtCore.Qt.Key_E or key == 'E':
                    self.app.grb_editor.on_eraser()
                    return

                # save (update) the current geometry and return to the App
                if key == QtCore.Qt.Key_S or key == 'S':
                    self.app.editor2object()
                    return

                # toggle the measurement tool
                if key == QtCore.Qt.Key_M or key == 'M':
                    self.app.distance_tool.run()
                    return

            elif modifiers == QtCore.Qt.ShiftModifier:
                # Run Distance Minimum Tool
                if key == QtCore.Qt.Key_M or key == 'M':
                    self.app.distance_min_tool.run()
                    return
            elif modifiers == QtCore.Qt.AltModifier:
                # Mark Area Tool
                if key == QtCore.Qt.Key_A or key == 'A':
                    self.app.grb_editor.on_markarea()
                    return

                # Poligonize Tool
                if key == QtCore.Qt.Key_N or key == 'N':
                    self.app.grb_editor.on_poligonize()
                    return
                # Transformation Tool
                if key == QtCore.Qt.Key_R or key == 'R':
                    self.app.grb_editor.on_transform()
                    return
            elif modifiers == QtCore.Qt.NoModifier:
                # Abort the current action
                if key == QtCore.Qt.Key_Escape or key == 'Escape':
                    # self.on_tool_select("select")
                    self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled."))

                    self.app.grb_editor.delete_utility_geometry()

                    # self.app.grb_editor.plot_all()
                    self.app.grb_editor.active_tool.clean_up()
                    self.app.grb_editor.select_tool('select')
                    return

                # Delete selected object if delete key event comes out of canvas
                if key == 'Delete':
                    self.app.grb_editor.launched_from_shortcuts = True
                    if self.app.grb_editor.selected:
                        self.app.grb_editor.delete_selected()
                        self.app.grb_editor.plot_all()
                    else:
                        self.app.inform.emit('[WARNING_NOTCL] %s' %
                                             _("Cancelled. Nothing selected to delete."))
                    return

                # Delete aperture in apertures table if delete key event comes from the Selected Tab
                if key == QtCore.Qt.Key_Delete:
                    self.app.grb_editor.launched_from_shortcuts = True
                    self.app.grb_editor.on_aperture_delete()
                    return

                if key == QtCore.Qt.Key_Minus or key == '-':
                    self.app.grb_editor.launched_from_shortcuts = True
                    self.app.plotcanvas.zoom(1 / self.app.defaults['global_zoom_ratio'],
                                             [self.app.grb_editor.snap_x, self.app.grb_editor.snap_y])
                    return

                if key == QtCore.Qt.Key_Equal or key == '=':
                    self.app.grb_editor.launched_from_shortcuts = True
                    self.app.plotcanvas.zoom(self.app.defaults['global_zoom_ratio'],
                                             [self.app.grb_editor.snap_x, self.app.grb_editor.snap_y])
                    return

                # toggle display of Notebook area
                if key == QtCore.Qt.Key_QuoteLeft or key == '`':
                    self.app.grb_editor.launched_from_shortcuts = True
                    self.app.on_toggle_notebook()
                    return

                # Rotate
                if key == QtCore.Qt.Key_Space or key == 'Space':
                    self.app.grb_editor.transform_tool.on_rotate_key()

                # Switch to Project Tab
                if key == QtCore.Qt.Key_1 or key == '1':
                    self.app.grb_editor.launched_from_shortcuts = True
                    self.app.on_select_tab('project')
                    return

                # Switch to Selected Tab
                if key == QtCore.Qt.Key_2 or key == '2':
                    self.app.grb_editor.launched_from_shortcuts = True
                    self.app.on_select_tab('selected')
                    return

                # Switch to Tool Tab
                if key == QtCore.Qt.Key_3 or key == '3':
                    self.app.grb_editor.launched_from_shortcuts = True
                    self.app.on_select_tab('tool')
                    return

                # we do this so we can reuse the following keys while inside a Tool
                # the above keys are general enough so were left outside
                if self.app.grb_editor.active_tool is not None and self.grb_select_btn.isChecked() is False:
                    response = self.app.grb_editor.active_tool.on_key(key=key)
                    if response is not None:
                        self.app.inform.emit(response)
                else:
                    # Add Array of pads
                    if key == QtCore.Qt.Key_A or key == 'A':
                        self.app.grb_editor.launched_from_shortcuts = True
                        self.app.inform.emit("Click on target point.")
                        self.app.ui.add_pad_ar_btn.setChecked(True)

                        self.app.grb_editor.x = self.app.mouse[0]
                        self.app.grb_editor.y = self.app.mouse[1]

                        self.app.grb_editor.select_tool('array')
                        return

                    # Scale Tool
                    if key == QtCore.Qt.Key_B or key == 'B':
                        self.app.grb_editor.launched_from_shortcuts = True
                        self.app.grb_editor.select_tool('buffer')
                        return

                    # Copy
                    if key == QtCore.Qt.Key_C or key == 'C':
                        self.app.grb_editor.launched_from_shortcuts = True
                        if self.app.grb_editor.selected:
                            self.app.inform.emit(_("Click on target point."))
                            self.app.ui.aperture_copy_btn.setChecked(True)
                            self.app.grb_editor.on_tool_select('copy')
                            self.app.grb_editor.active_tool.set_origin(
                                (self.app.grb_editor.snap_x, self.app.grb_editor.snap_y))
                        else:
                            self.app.inform.emit('[WARNING_NOTCL] %s' %
                                                 _("Cancelled. Nothing selected to copy."))
                        return

                    # Add Disc Tool
                    if key == QtCore.Qt.Key_D or key == 'D':
                        self.app.grb_editor.launched_from_shortcuts = True
                        self.app.grb_editor.select_tool('disc')
                        return

                    # Add SemiDisc Tool
                    if key == QtCore.Qt.Key_E or key == 'E':
                        self.app.grb_editor.launched_from_shortcuts = True
                        self.app.grb_editor.select_tool('semidisc')
                        return

                    # Grid Snap
                    if key == QtCore.Qt.Key_G or key == 'G':
                        self.app.grb_editor.launched_from_shortcuts = True
                        # make sure that the cursor shape is enabled/disabled, too
                        if self.app.grb_editor.options['grid_snap'] is True:
                            self.app.app_cursor.enabled = False
                        else:
                            self.app.app_cursor.enabled = True
                        self.app.ui.grid_snap_btn.trigger()
                        return

                    # Jump to coords
                    if key == QtCore.Qt.Key_J or key == 'J':
                        self.app.on_jump_to()

                    # Corner Snap
                    if key == QtCore.Qt.Key_K or key == 'K':
                        self.app.grb_editor.launched_from_shortcuts = True
                        self.app.ui.corner_snap_btn.trigger()
                        return

                    # Move
                    if key == QtCore.Qt.Key_M or key == 'M':
                        self.app.grb_editor.launched_from_shortcuts = True
                        if self.app.grb_editor.selected:
                            self.app.inform.emit(_("Click on target point."))
                            self.app.ui.aperture_move_btn.setChecked(True)
                            self.app.grb_editor.on_tool_select('move')
                            self.app.grb_editor.active_tool.set_origin(
                                (self.app.grb_editor.snap_x, self.app.grb_editor.snap_y))
                        else:
                            self.app.inform.emit('[WARNING_NOTCL] %s' %
                                                 _("Cancelled. Nothing selected to move."))
                        return

                    # Add Region Tool
                    if key == QtCore.Qt.Key_N or key == 'N':
                        self.app.grb_editor.launched_from_shortcuts = True
                        self.app.grb_editor.select_tool('region')
                        return

                    # Add Pad Tool
                    if key == QtCore.Qt.Key_P or key == 'P':
                        self.app.grb_editor.launched_from_shortcuts = True
                        self.app.inform.emit(_("Click on target point."))
                        self.app.ui.add_pad_ar_btn.setChecked(True)

                        self.app.grb_editor.x = self.app.mouse[0]
                        self.app.grb_editor.y = self.app.mouse[1]

                        self.app.grb_editor.select_tool('pad')
                        return

                    # Scale Tool
                    if key == QtCore.Qt.Key_S or key == 'S':
                        self.app.grb_editor.launched_from_shortcuts = True
                        self.app.grb_editor.select_tool('scale')
                        return

                    # Add Track
                    if key == QtCore.Qt.Key_T or key == 'T':
                        self.app.grb_editor.launched_from_shortcuts = True
                        # ## Current application units in Upper Case
                        self.app.grb_editor.select_tool('track')
                        return

                    # Zoom Fit
                    if key == QtCore.Qt.Key_V or key == 'V':
                        self.app.grb_editor.launched_from_shortcuts = True
                        self.app.on_zoom_fit(None)
                        return

                # Show Shortcut list
                if key == QtCore.Qt.Key_F3 or key == 'F3':
                    self.app.on_shortcut_list()
                    return
        elif self.app.call_source == 'exc_editor':
            if modifiers == QtCore.Qt.ControlModifier:
                # save (update) the current geometry and return to the App
                if key == QtCore.Qt.Key_S or key == 'S':
                    self.app.editor2object()
                    return

                # toggle the measurement tool
                if key == QtCore.Qt.Key_M or key == 'M':
                    self.app.distance_tool.run()
                    return

            elif modifiers == QtCore.Qt.ShiftModifier:
                # Run Distance Minimum Tool
                if key == QtCore.Qt.Key_M or key == 'M':
                    self.app.distance_min_tool.run()
                    return
            elif modifiers == QtCore.Qt.AltModifier:
                pass
            elif modifiers == QtCore.Qt.NoModifier:
                # Abort the current action
                if key == QtCore.Qt.Key_Escape or key == 'Escape':
                    # TODO: ...?
                    # self.on_tool_select("select")
                    self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled."))

                    self.app.exc_editor.delete_utility_geometry()

                    self.app.exc_editor.replot()
                    # self.select_btn.setChecked(True)
                    # self.on_tool_select('select')
                    self.app.exc_editor.select_tool('drill_select')
                    return

                # Delete selected object if delete key event comes out of canvas
                if key == 'Delete':
                    self.app.exc_editor.launched_from_shortcuts = True
                    if self.app.exc_editor.selected:
                        self.app.exc_editor.delete_selected()
                        self.app.exc_editor.replot()
                    else:
                        self.app.inform.emit('[WARNING_NOTCL] %s' %
                                             _("Cancelled. Nothing selected to delete."))
                    return

                # Delete tools in tools table if delete key event comes from the Selected Tab
                if key == QtCore.Qt.Key_Delete:
                    self.app.exc_editor.launched_from_shortcuts = True
                    self.app.exc_editor.on_tool_delete()
                    return

                if key == QtCore.Qt.Key_Minus or key == '-':
                    self.app.exc_editor.launched_from_shortcuts = True
                    self.app.plotcanvas.zoom(1 / self.app.defaults['global_zoom_ratio'],
                                             [self.app.exc_editor.snap_x, self.app.exc_editor.snap_y])
                    return

                if key == QtCore.Qt.Key_Equal or key == '=':
                    self.app.exc_editor.launched_from_shortcuts = True
                    self.app.plotcanvas.zoom(self.app.defaults['global_zoom_ratio'],
                                             [self.app.exc_editor.snap_x, self.app.exc_editor.snap_y])
                    return

                # toggle display of Notebook area
                if key == QtCore.Qt.Key_QuoteLeft or key == '`':
                    self.app.exc_editor.launched_from_shortcuts = True
                    self.app.on_toggle_notebook()
                    return

                # Switch to Project Tab
                if key == QtCore.Qt.Key_1 or key == '1':
                    self.app.exc_editor.launched_from_shortcuts = True
                    self.app.on_select_tab('project')
                    return

                # Switch to Selected Tab
                if key == QtCore.Qt.Key_2 or key == '2':
                    self.app.exc_editor.launched_from_shortcuts = True
                    self.app.on_select_tab('selected')
                    return

                # Switch to Tool Tab
                if key == QtCore.Qt.Key_3 or key == '3':
                    self.app.exc_editor.launched_from_shortcuts = True
                    self.app.on_select_tab('tool')
                    return

                # Add Array of Drill Hole Tool
                if key == QtCore.Qt.Key_A or key == 'A':
                    self.app.exc_editor.launched_from_shortcuts = True
                    self.app.inform.emit("Click on target point.")
                    self.app.ui.add_drill_array_btn.setChecked(True)

                    self.app.exc_editor.x = self.app.mouse[0]
                    self.app.exc_editor.y = self.app.mouse[1]

                    self.app.exc_editor.select_tool('drill_array')
                    return

                # Copy
                if key == QtCore.Qt.Key_C or key == 'C':
                    self.app.exc_editor.launched_from_shortcuts = True
                    if self.app.exc_editor.selected:
                        self.app.inform.emit(_("Click on target point."))
                        self.app.ui.copy_drill_btn.setChecked(True)
                        self.app.exc_editor.on_tool_select('drill_copy')
                        self.app.exc_editor.active_tool.set_origin(
                            (self.app.exc_editor.snap_x, self.app.exc_editor.snap_y))
                    else:
                        self.app.inform.emit('[WARNING_NOTCL] %s' %
                                             _("Cancelled. Nothing selected to copy."))
                    return

                # Add Drill Hole Tool
                if key == QtCore.Qt.Key_D or key == 'D':
                    self.app.exc_editor.launched_from_shortcuts = True
                    self.app.inform.emit(_("Click on target point."))
                    self.app.ui.add_drill_btn.setChecked(True)

                    self.app.exc_editor.x = self.app.mouse[0]
                    self.app.exc_editor.y = self.app.mouse[1]

                    self.app.exc_editor.select_tool('drill_add')
                    return

                # Grid Snap
                if key == QtCore.Qt.Key_G or key == 'G':
                    self.app.exc_editor.launched_from_shortcuts = True
                    # make sure that the cursor shape is enabled/disabled, too
                    if self.app.exc_editor.options['grid_snap'] is True:
                        self.app.app_cursor.enabled = False
                    else:
                        self.app.app_cursor.enabled = True
                    self.app.ui.grid_snap_btn.trigger()
                    return

                # Jump to coords
                if key == QtCore.Qt.Key_J or key == 'J':
                    self.app.on_jump_to()

                # Corner Snap
                if key == QtCore.Qt.Key_K or key == 'K':
                    self.app.exc_editor.launched_from_shortcuts = True
                    self.app.ui.corner_snap_btn.trigger()
                    return

                # Move
                if key == QtCore.Qt.Key_M or key == 'M':
                    self.app.exc_editor.launched_from_shortcuts = True
                    if self.app.exc_editor.selected:
                        self.app.inform.emit(_("Click on target point."))
                        self.app.ui.move_drill_btn.setChecked(True)
                        self.app.exc_editor.on_tool_select('drill_move')
                        self.app.exc_editor.active_tool.set_origin(
                            (self.app.exc_editor.snap_x, self.app.exc_editor.snap_y))
                    else:
                        self.app.inform.emit('[WARNING_NOTCL] %s' %
                                             _("Cancelled. Nothing selected to move."))
                    return

                # Add Array of Slote Hole Tool
                if key == QtCore.Qt.Key_Q or key == 'Q':
                    self.app.exc_editor.launched_from_shortcuts = True
                    self.app.inform.emit("Click on target point.")
                    self.app.ui.add_slot_array_btn.setChecked(True)

                    self.app.exc_editor.x = self.app.mouse[0]
                    self.app.exc_editor.y = self.app.mouse[1]

                    self.app.exc_editor.select_tool('slot_array')
                    return

                # Resize Tool
                if key == QtCore.Qt.Key_R or key == 'R':
                    self.app.exc_editor.launched_from_shortcuts = True
                    self.app.exc_editor.select_tool('drill_resize')
                    return

                # Add Tool
                if key == QtCore.Qt.Key_T or key == 'T':
                    self.app.exc_editor.launched_from_shortcuts = True
                    # ## Current application units in Upper Case
                    self.units = self.general_defaults_form.general_app_group.units_radio.get_value().upper()
                    tool_add_popup = FCInputDialog(title=_("New Tool ..."),
                                                   text='%s:' % _('Enter a Tool Diameter'),
                                                   min=0.0000, max=99.9999, decimals=4)
                    tool_add_popup.setWindowIcon(QtGui.QIcon(self.app.resource_location + '/letter_t_32.png'))

                    val, ok = tool_add_popup.get_value()
                    if ok:
                        self.app.exc_editor.on_tool_add(tooldia=val)
                        formated_val = '%.*f' % (self.decimals, float(val))
                        self.app.inform.emit(
                            '[success] %s: %s %s' % (_("Added new tool with dia"), formated_val, str(self.units))
                        )
                    else:
                        self.app.inform.emit('[WARNING_NOTCL] %s' % _("Adding Tool cancelled ..."))
                    return

                # Zoom Fit
                if key == QtCore.Qt.Key_V or key == 'V':
                    self.app.exc_editor.launched_from_shortcuts = True
                    self.app.on_zoom_fit(None)
                    return

                # Add Slot Hole Tool
                if key == QtCore.Qt.Key_W or key == 'W':
                    self.app.exc_editor.launched_from_shortcuts = True
                    self.app.inform.emit(_("Click on target point."))
                    self.app.ui.add_slot_btn.setChecked(True)

                    self.app.exc_editor.x = self.app.mouse[0]
                    self.app.exc_editor.y = self.app.mouse[1]

                    self.app.exc_editor.select_tool('slot_add')
                    return

                # Propagate to tool
                response = None
                if self.app.exc_editor.active_tool is not None:
                    response = self.app.exc_editor.active_tool.on_key(key=key)
                if response is not None:
                    self.app.inform.emit(response)

                # Show Shortcut list
                if key == QtCore.Qt.Key_F3 or key == 'F3':
                    self.app.on_shortcut_list()
                    return
        elif self.app.call_source == 'measurement':
            if modifiers == QtCore.Qt.ControlModifier:
                pass
            elif modifiers == QtCore.Qt.AltModifier:
                pass
            elif modifiers == QtCore.Qt.ShiftModifier:
                pass
            elif modifiers == QtCore.Qt.NoModifier:
                if key == QtCore.Qt.Key_Escape or key == 'Escape':
                    # abort the measurement action
                    self.app.distance_tool.deactivate_measure_tool()
                    self.app.inform.emit(_("Distance Tool exit..."))
                    return

                if key == QtCore.Qt.Key_G or key == 'G':
                    self.app.ui.grid_snap_btn.trigger()
                    return

                # Jump to coords
                if key == QtCore.Qt.Key_J or key == 'J':
                    self.app.on_jump_to()
        elif self.app.call_source == 'qrcode_tool':
            if modifiers == QtCore.Qt.ControlModifier | QtCore.Qt.AltModifier:
                if key == QtCore.Qt.Key_X:
                    self.app.abort_all_tasks()
                    return

            elif modifiers == QtCore.Qt.ControlModifier:
                pass
            elif modifiers == QtCore.Qt.ShiftModifier:
                pass
            elif modifiers == QtCore.Qt.AltModifier:
                pass
            elif modifiers == QtCore.Qt.NoModifier:
                # Escape = Deselect All
                if key == QtCore.Qt.Key_Escape or key == 'Escape':
                    self.app.qrcode_tool.on_exit()

                # Grid toggle
                if key == QtCore.Qt.Key_G:
                    self.app.ui.grid_snap_btn.trigger()

                # Jump to coords
                if key == QtCore.Qt.Key_J:
                    self.app.on_jump_to()
        elif self.app.call_source == 'copper_thieving_tool':
            if modifiers == QtCore.Qt.ControlModifier | QtCore.Qt.AltModifier:
                if key == QtCore.Qt.Key_X:
                    self.app.abort_all_tasks()
                    return

            elif modifiers == QtCore.Qt.ControlModifier:
                pass
            elif modifiers == QtCore.Qt.ShiftModifier:
                pass
            elif modifiers == QtCore.Qt.AltModifier:
                pass
            elif modifiers == QtCore.Qt.NoModifier:
                # Escape = Deselect All
                if key == QtCore.Qt.Key_Escape or key == 'Escape':
                    self.app.copperfill_tool.on_exit()

                # Grid toggle
                if key == QtCore.Qt.Key_G:
                    self.app.ui.grid_snap_btn.trigger()

                # Jump to coords
                if key == QtCore.Qt.Key_J:
                    self.app.on_jump_to()

    def createPopupMenu(self):
        menu = super().createPopupMenu()

        menu.addSeparator()
        menu.addAction(self.lock_action)
        return menu

    def lock_toolbar(self, lock=False):
        """
        Used to (un)lock the toolbars of the app.

        :param lock: boolean, will lock all toolbars in place when set True
        :return: None
        """

        if lock:
            for widget in self.children():
                if isinstance(widget, QtWidgets.QToolBar):
                    widget.setMovable(False)
        else:
            for widget in self.children():
                if isinstance(widget, QtWidgets.QToolBar):
                    widget.setMovable(True)

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
                    extension = self.filename.lower().rpartition('.')[-1]

                    if extension in self.app.grb_list:
                        self.app.worker_task.emit({'fcn': self.app.open_gerber,
                                                   'params': [self.filename]})
                    else:
                        event.ignore()

                    if extension in self.app.exc_list:
                        self.app.worker_task.emit({'fcn': self.app.open_excellon,
                                                   'params': [self.filename]})
                    else:
                        event.ignore()

                    if extension in self.app.gcode_list:
                        self.app.worker_task.emit({'fcn': self.app.open_gcode,
                                                   'params': [self.filename]})
                    else:
                        event.ignore()

                    if extension in self.app.svg_list:
                        object_type = 'geometry'
                        self.app.worker_task.emit({'fcn': self.app.import_svg,
                                                   'params': [self.filename, object_type, None]})

                    if extension in self.app.dxf_list:
                        object_type = 'geometry'
                        self.app.worker_task.emit({'fcn': self.app.import_dxf,
                                                   'params': [self.filename, object_type, None]})

                    if extension in self.app.pdf_list:
                        self.app.pdf_tool.periodic_check(1000)
                        self.app.worker_task.emit({'fcn': self.app.pdf_tool.open_pdf,
                                                   'params': [self.filename]})

                    if extension in self.app.prj_list:
                        # self.app.open_project() is not Thread Safe
                        self.app.open_project(self.filename)

                    if extension in self.app.conf_list:
                        self.app.open_config_file(self.filename)
                    else:
                        event.ignore()
        else:
            event.ignore()

    def closeEvent(self, event):
        if self.app.save_in_progress:
            self.app.inform.emit('[WARNING_NOTCL] %s' %
                                 _("Application is saving the project. Please wait ..."))
        else:
            grect = self.geometry()

            # self.splitter.sizes()[0] is actually the size of the "notebook"
            if not self.isMaximized():
                self.geom_update.emit(grect.x(), grect.y(), grect.width(), grect.height(), self.splitter.sizes()[0])

            self.final_save.emit()
        event.ignore()


class FlatCAMActivityView(QtWidgets.QWidget):
    """
    This class create and control the activity icon displayed in the App status bar
    """

    def __init__(self, app, parent=None):
        super().__init__(parent=parent)

        self.app = app

        if self.app.defaults["global_activity_icon"] == "Ball green":
            icon = self.app.resource_location + '/active_2_static.png'
            movie = self.app.resource_location + "/active_2.gif"
        elif self.app.defaults["global_activity_icon"] == "Ball black":
            icon = self.app.resource_location + '/active_static.png'
            movie = self.app.resource_location + "/active.gif"
        elif self.app.defaults["global_activity_icon"] == "Arrow green":
            icon = self.app.resource_location + '/active_3_static.png'
            movie = self.app.resource_location + "/active_3.gif"
        elif self.app.defaults["global_activity_icon"] == "Eclipse green":
            icon = self.app.resource_location + '/active_4_static.png'
            movie = self.app.resource_location + "/active_4.gif"
        else:
            icon = self.app.resource_location + '/active_static.png'
            movie = self.app.resource_location + "/active.gif"

        self.setMinimumWidth(200)
        self.movie_path = movie
        self.icon_path = icon

        self.icon = QtWidgets.QLabel(self)
        self.icon.setGeometry(0, 0, 16, 12)
        self.movie = QtGui.QMovie(self.movie_path)

        self.icon.setMovie(self.movie)
        # self.movie.start()

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setAlignment(QtCore.Qt.AlignLeft)
        self.setLayout(layout)

        layout.addWidget(self.icon)
        self.text = QtWidgets.QLabel(self)
        self.text.setText(_("Idle."))
        self.icon.setPixmap(QtGui.QPixmap(self.icon_path))

        layout.addWidget(self.text)

    def set_idle(self):
        self.movie.stop()
        self.text.setText(_("Idle."))

    def set_busy(self, msg, no_movie=None):
        if no_movie is not True:
            self.icon.setMovie(self.movie)
            self.movie.start()
        self.text.setText(msg)


class FlatCAMInfoBar(QtWidgets.QWidget):
    """
    This class create a place to display the App messages in the Status Bar
    """

    def __init__(self, parent=None, app=None):
        super(FlatCAMInfoBar, self).__init__(parent=parent)

        self.app = app

        self.icon = QtWidgets.QLabel(self)
        self.icon.setGeometry(0, 0, 12, 12)
        self.pmap = QtGui.QPixmap(self.app.resource_location + '/graylight12.png')
        self.icon.setPixmap(self.pmap)

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(5, 0, 5, 0)
        self.setLayout(layout)

        layout.addWidget(self.icon)

        self.text = QtWidgets.QLabel(self)
        self.text.setText(_("Application started ..."))
        self.text.setToolTip(_("Hello!"))

        layout.addWidget(self.text)

        layout.addStretch()

    def set_text_(self, text, color=None):
        self.text.setText(text)
        self.text.setToolTip(text)
        if color:
            self.text.setStyleSheet('color: %s' % str(color))

    def set_status(self, text, level="info"):
        level = str(level)
        self.pmap.fill()
        if level == "ERROR" or level == "ERROR_NOTCL":
            self.pmap = QtGui.QPixmap(self.app.resource_location + '/redlight12.png')
        elif level == "success" or level == "SUCCESS":
            self.pmap = QtGui.QPixmap(self.app.resource_location + '/greenlight12.png')
        elif level == "WARNING" or level == "WARNING_NOTCL":
            self.pmap = QtGui.QPixmap(self.app.resource_location + '/yellowlight12.png')
        elif level == "selected" or level == "SELECTED":
            self.pmap = QtGui.QPixmap(self.app.resource_location + '/bluelight12.png')
        else:
            self.pmap = QtGui.QPixmap(self.app.resource_location + '/graylight12.png')

        self.set_text_(text)
        self.icon.setPixmap(self.pmap)


class FlatCAMSystemTray(QtWidgets.QSystemTrayIcon):
    """
    This class create the Sys Tray icon for the app
    """

    def __init__(self, app, icon, headless=None, parent=None):
        # QtWidgets.QSystemTrayIcon.__init__(self, icon, parent)
        super().__init__(icon, parent=parent)
        self.app = app

        menu = QtWidgets.QMenu(parent)

        menu_runscript = QtWidgets.QAction(QtGui.QIcon(self.app.resource_location + '/script14.png'),
                                           '%s' % _('Run Script ...'), self)
        menu_runscript.setToolTip(
            _("Will run the opened Tcl Script thus\n"
              "enabling the automation of certain\n"
              "functions of FlatCAM.")
        )
        menu.addAction(menu_runscript)

        menu.addSeparator()

        if headless is None:
            self.menu_open = menu.addMenu(QtGui.QIcon(self.app.resource_location + '/folder32_bis.png'), _('Open'))

            # Open Project ...
            menu_openproject = QtWidgets.QAction(QtGui.QIcon(self.app.resource_location + '/folder16.png'),
                                                 _('Open Project ...'), self)
            self.menu_open.addAction(menu_openproject)
            self.menu_open.addSeparator()

            # Open Gerber ...
            menu_opengerber = QtWidgets.QAction(QtGui.QIcon(self.app.resource_location + '/flatcam_icon24.png'),
                                                _('Open &Gerber ...\tCTRL+G'), self)
            self.menu_open.addAction(menu_opengerber)

            # Open Excellon ...
            menu_openexcellon = QtWidgets.QAction(QtGui.QIcon(self.app.resource_location + '/open_excellon32.png'),
                                                  _('Open &Excellon ...\tCTRL+E'), self)
            self.menu_open.addAction(menu_openexcellon)

            # Open G-Code ...
            menu_opengcode = QtWidgets.QAction(QtGui.QIcon(self.app.resource_location + '/code.png'),
                                               _('Open G-&Code ...'), self)
            self.menu_open.addAction(menu_opengcode)

            self.menu_open.addSeparator()

            menu_openproject.triggered.connect(self.app.on_file_openproject)
            menu_opengerber.triggered.connect(self.app.on_fileopengerber)
            menu_openexcellon.triggered.connect(self.app.on_fileopenexcellon)
            menu_opengcode.triggered.connect(self.app.on_fileopengcode)

        exitAction = menu.addAction(_("Exit"))
        exitAction.setIcon(QtGui.QIcon(self.app.resource_location + '/power16.png'))
        self.setContextMenu(menu)

        menu_runscript.triggered.connect(lambda: self.app.on_filerunscript(
            silent=True if self.app.cmd_line_headless == 1 else False))

        exitAction.triggered.connect(self.app.final_save)

# end of file
