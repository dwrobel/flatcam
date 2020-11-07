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
from PyQt5.QtCore import QSettings

import platform

from appGUI.GUIElements import *
from appGUI.preferences import settings
from appGUI.preferences.cncjob.CNCJobPreferencesUI import CNCJobPreferencesUI
from appGUI.preferences.excellon.ExcellonPreferencesUI import ExcellonPreferencesUI
from appGUI.preferences.general.GeneralPreferencesUI import GeneralPreferencesUI
from appGUI.preferences.geometry.GeometryPreferencesUI import GeometryPreferencesUI
from appGUI.preferences.gerber.GerberPreferencesUI import GerberPreferencesUI
from appEditors.AppGeoEditor import FCShapeTool

from matplotlib.backend_bases import KeyEvent as mpl_key_event

import webbrowser

from appGUI.preferences.tools.Tools2PreferencesUI import Tools2PreferencesUI
from appGUI.preferences.tools.ToolsPreferencesUI import ToolsPreferencesUI
from appGUI.preferences.utilities.UtilPreferencesUI import UtilPreferencesUI
from appObjects.ObjectCollection import KeySensitiveListView

import subprocess
import os
import sys
import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class MainGUI(QtWidgets.QMainWindow):
    # Emitted when persistent window geometry needs to be retained
    geom_update = QtCore.pyqtSignal(int, int, int, int, int, name='geomUpdate')
    final_save = QtCore.pyqtSignal(name='saveBeforeExit')

    def __init__(self, app):
        super(MainGUI, self).__init__()

        self.app = app
        self.decimals = self.app.decimals

        # Divine icon pack by Ipapun @ finicons.com

        # #######################################################################
        # ############ BUILDING THE GUI IS EXECUTED HERE ########################
        # #######################################################################

        # #######################################################################
        # ###################### Menu BUILDING ##################################
        # #######################################################################
        self.menu = self.menuBar()

        self.menu_toggle_nb = QtWidgets.QAction(
            QtGui.QIcon(self.app.resource_location + '/notebook32.png'), _("Toggle Panel"))
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
                                                    '%s...\t%s' % (_('New Project'), _("Ctrl+N")), self)
        self.menufilenewproject.setToolTip(
            _("Will create a new, blank project")
        )
        self.menufile.addAction(self.menufilenewproject)

        # New Category (Excellon, Geometry)
        self.menufilenew = self.menufile.addMenu(QtGui.QIcon(self.app.resource_location + '/file16.png'), _('New'))
        self.menufilenew.setToolTipsVisible(True)

        self.menufilenewgeo = self.menufilenew.addAction(
            QtGui.QIcon(self.app.resource_location + '/new_file_geo16.png'), '%s\t%s' % (_('Geometry'), _('N')))
        self.menufilenewgeo.setToolTip(
            _("Will create a new, empty Geometry Object.")
        )
        self.menufilenewgrb = self.menufilenew.addAction(
            QtGui.QIcon(self.app.resource_location + '/new_file_grb16.png'), '%s\t%s' % (_('Gerber'), _('B')))
        self.menufilenewgrb.setToolTip(
            _("Will create a new, empty Gerber Object.")
        )
        self.menufilenewexc = self.menufilenew.addAction(
            QtGui.QIcon(self.app.resource_location + '/new_file_exc16.png'), '%s\t%s' % (_('Excellon'), _('L')))
        self.menufilenewexc.setToolTip(
            _("Will create a new, empty Excellon Object.")
        )
        self.menufilenew.addSeparator()

        self.menufilenewdoc = self.menufilenew.addAction(
            QtGui.QIcon(self.app.resource_location + '/notes16_1.png'), '%s\t%s' % (_('Document'), _('D')))
        self.menufilenewdoc.setToolTip(
            _("Will create a new, empty Document Object.")
        )

        self.menufile_open = self.menufile.addMenu(
            QtGui.QIcon(self.app.resource_location + '/folder32_bis.png'), '%s' % _('Open'))
        self.menufile_open.setToolTipsVisible(True)

        # Open Project ...
        self.menufileopenproject = QtWidgets.QAction(
            QtGui.QIcon(self.app.resource_location + '/folder16.png'), '%s...\t%s' % (_('Open Project'), _('Ctrl+O')),
            self)
        self.menufile_open.addAction(self.menufileopenproject)
        self.menufile_open.addSeparator()

        # Open Gerber ...
        self.menufileopengerber = QtWidgets.QAction(QtGui.QIcon(self.app.resource_location + '/flatcam_icon24.png'),
                                                    '%s...\t%s' % (_('Open Gerber'), _('Ctrl+G')), self)
        self.menufile_open.addAction(self.menufileopengerber)

        # Open Excellon ...
        self.menufileopenexcellon = QtWidgets.QAction(QtGui.QIcon(self.app.resource_location + '/open_excellon32.png'),
                                                      '%s...\t%s' % (_('Open Excellon'), _('Ctrl+E')), self)
        self.menufile_open.addAction(self.menufileopenexcellon)

        # Open G-Code ...
        self.menufileopengcode = QtWidgets.QAction(
            QtGui.QIcon(self.app.resource_location + '/code.png'), '%s...\t%s' % (_('Open G-Code'), ''), self)
        self.menufile_open.addAction(self.menufileopengcode)

        self.menufile_open.addSeparator()

        # Open Config File...
        self.menufileopenconfig = QtWidgets.QAction(
            QtGui.QIcon(self.app.resource_location + '/folder16.png'), '%s...\t%s' % (_('Open Config'), ''), self)
        self.menufile_open.addAction(self.menufileopenconfig)

        # Recent
        self.recent_projects = self.menufile.addMenu(
            QtGui.QIcon(self.app.resource_location + '/recent_files.png'), _("Recent projects"))
        self.recent = self.menufile.addMenu(
            QtGui.QIcon(self.app.resource_location + '/recent_files.png'), _("Recent files"))

        # SAVE category
        self.menufile_save = self.menufile.addMenu(QtGui.QIcon(self.app.resource_location + '/save_as.png'), _('Save'))

        # Save Project
        self.menufilesaveproject = QtWidgets.QAction(
            QtGui.QIcon(self.app.resource_location + '/floppy16.png'), '%s...\t%s' % (_('Save Project'), _('Ctrl+S')),
            self)
        self.menufile_save.addAction(self.menufilesaveproject)

        # Save Project As ...
        self.menufilesaveprojectas = QtWidgets.QAction(QtGui.QIcon(self.app.resource_location + '/floppy16.png'),
                                                       '%s...\t%s' % (_('Save Project As'), _('Ctrl+Shift+S')), self)
        self.menufile_save.addAction(self.menufilesaveprojectas)

        # Save Project Copy ...
        # self.menufilesaveprojectcopy = QtWidgets.QAction(
        #     QtGui.QIcon(self.app.resource_location + '/floppy16.png'), _('Save Project Copy ...'), self)
        # self.menufile_save.addAction(self.menufilesaveprojectcopy)

        self.menufile_save.addSeparator()

        # Separator
        self.menufile.addSeparator()

        # Scripting
        self.menufile_scripting = self.menufile.addMenu(
            QtGui.QIcon(self.app.resource_location + '/script16.png'), _('Scripting'))
        self.menufile_scripting.setToolTipsVisible(True)

        self.menufilenewscript = QtWidgets.QAction(QtGui.QIcon(self.app.resource_location + '/script_new16.png'),
                                                   '%s...\t%s' % (_('New Script'), ''), self)
        self.menufileopenscript = QtWidgets.QAction(QtGui.QIcon(self.app.resource_location + '/open_script32.png'),
                                                    '%s...\t%s' % (_('Open Script'), ''), self)
        self.menufileopenscriptexample = QtWidgets.QAction(
            QtGui.QIcon(self.app.resource_location + '/open_script32.png'),
            '%s...\t%s' % (_('Open Example'), ''), self)
        self.menufilerunscript = QtWidgets.QAction(
            QtGui.QIcon(self.app.resource_location + '/script16.png'),
            '%s...\t%s' % (_('Run Script'), _('Shift+S')), self)
        self.menufilerunscript.setToolTip(
            _("Will run the opened Tcl Script thus\n"
              "enabling the automation of certain\n"
              "functions of FlatCAM.")
        )
        self.menufile_scripting.addAction(self.menufilenewscript)
        self.menufile_scripting.addAction(self.menufileopenscript)
        self.menufile_scripting.addAction(self.menufileopenscriptexample)
        self.menufile_scripting.addSeparator()
        self.menufile_scripting.addAction(self.menufilerunscript)

        # Separator
        self.menufile.addSeparator()

        # Import ...
        self.menufileimport = self.menufile.addMenu(
            QtGui.QIcon(self.app.resource_location + '/import.png'), _('Import'))
        self.menufileimportsvg = QtWidgets.QAction(
            QtGui.QIcon(self.app.resource_location + '/svg16.png'),
            '%s...\t%s' % (_('SVG as Geometry Object'), ''), self)
        self.menufileimport.addAction(self.menufileimportsvg)
        self.menufileimportsvg_as_gerber = QtWidgets.QAction(
            QtGui.QIcon(self.app.resource_location + '/svg16.png'),
            '%s...\t%s' % (_('SVG as Gerber Object'), ''), self)
        self.menufileimport.addAction(self.menufileimportsvg_as_gerber)
        self.menufileimport.addSeparator()

        self.menufileimportdxf = QtWidgets.QAction(
            QtGui.QIcon(self.app.resource_location + '/dxf16.png'),
            '%s...\t%s' % (_('DXF as Geometry Object'), ''), self)
        self.menufileimport.addAction(self.menufileimportdxf)
        self.menufileimportdxf_as_gerber = QtWidgets.QAction(
            QtGui.QIcon(self.app.resource_location + '/dxf16.png'),
            '%s...\t%s' % (_('DXF as Gerber Object'), ''), self)
        self.menufileimport.addAction(self.menufileimportdxf_as_gerber)
        self.menufileimport.addSeparator()
        self.menufileimport_hpgl2_as_geo = QtWidgets.QAction(
            QtGui.QIcon(self.app.resource_location + '/dxf16.png'),
            '%s...\t%s' % (_('HPGL2 as Geometry Object'), ''), self)
        self.menufileimport.addAction(self.menufileimport_hpgl2_as_geo)
        self.menufileimport.addSeparator()

        # Export ...
        self.menufileexport = self.menufile.addMenu(
            QtGui.QIcon(self.app.resource_location + '/export.png'), _('Export'))
        self.menufileexport.setToolTipsVisible(True)

        self.menufileexportsvg = QtWidgets.QAction(
            QtGui.QIcon(self.app.resource_location + '/export.png'),
            '%s...\t%s' % (_('Export SVG'), ''), self)
        self.menufileexport.addAction(self.menufileexportsvg)

        self.menufileexportdxf = QtWidgets.QAction(
            QtGui.QIcon(self.app.resource_location + '/export.png'),
            '%s...\t%s' % (_('Export DXF'), ''), self)
        self.menufileexport.addAction(self.menufileexportdxf)

        self.menufileexport.addSeparator()

        self.menufileexportpng = QtWidgets.QAction(
            QtGui.QIcon(self.app.resource_location + '/export_png32.png'),
            '%s...\t%s' % (_('Export PNG'), ''), self)
        self.menufileexportpng.setToolTip(
            _("Will export an image in PNG format,\n"
              "the saved image will contain the visual \n"
              "information currently in FlatCAM Plot Area.")
        )
        self.menufileexport.addAction(self.menufileexportpng)

        self.menufileexport.addSeparator()

        self.menufileexportexcellon = QtWidgets.QAction(
            QtGui.QIcon(self.app.resource_location + '/drill32.png'),
            '%s...\t%s' % (_('Export Excellon'), ''), self)
        self.menufileexportexcellon.setToolTip(
            _("Will export an Excellon Object as Excellon file,\n"
              "the coordinates format, the file units and zeros\n"
              "are set in Preferences -> Excellon Export.")
        )
        self.menufileexport.addAction(self.menufileexportexcellon)

        self.menufileexportgerber = QtWidgets.QAction(
            QtGui.QIcon(self.app.resource_location + '/flatcam_icon32.png'),
            '%s...\t%s' % (_('Export Gerber'), ''), self)
        self.menufileexportgerber.setToolTip(
            _("Will export an Gerber Object as Gerber file,\n"
              "the coordinates format, the file units and zeros\n"
              "are set in Preferences -> Gerber Export.")
        )
        self.menufileexport.addAction(self.menufileexportgerber)

        # Separator
        self.menufile.addSeparator()

        self.menufile_backup = self.menufile.addMenu(
            QtGui.QIcon(self.app.resource_location + '/backup24.png'), _('Backup'))

        # Import Preferences
        self.menufileimportpref = QtWidgets.QAction(
            QtGui.QIcon(self.app.resource_location + '/backup_import24.png'),
            '%s...\t%s' % (_('Import Preferences from file'), ''), self
        )
        self.menufile_backup.addAction(self.menufileimportpref)

        # Export Preferences
        self.menufileexportpref = QtWidgets.QAction(
            QtGui.QIcon(self.app.resource_location + '/backup_export24.png'),
            '%s...\t%s' % (_('Export Preferences to file'), ''), self)
        self.menufile_backup.addAction(self.menufileexportpref)

        # Separator
        self.menufile_backup.addSeparator()

        # Save Defaults
        self.menufilesavedefaults = QtWidgets.QAction(
            QtGui.QIcon(self.app.resource_location + '/defaults.png'),
            '%s\t%s' % (_('Save Preferences'), ''), self)
        self.menufile_backup.addAction(self.menufilesavedefaults)

        # Separator
        self.menufile.addSeparator()
        self.menufile_print = QtWidgets.QAction(
            QtGui.QIcon(self.app.resource_location + '/printer32.png'),
            '%s\t%s' % (_('Print (PDF)'), _('Ctrl+P')))
        self.menufile.addAction(self.menufile_print)

        # Separator
        self.menufile.addSeparator()

        # Quit
        self.menufile_exit = QtWidgets.QAction(
            QtGui.QIcon(self.app.resource_location + '/power16.png'),
            '%s\t%s' % (_('Exit'), ''), self)
        # exitAction.setShortcut('Ctrl+Q')
        # exitAction.setStatusTip('Exit application')
        self.menufile.addAction(self.menufile_exit)

        # ########################################################################
        # ########################## Edit # ######################################
        # ########################################################################
        self.menuedit = self.menu.addMenu(_('Edit'))
        # Separator
        self.menuedit.addSeparator()
        self.menueditedit = self.menuedit.addAction(
            QtGui.QIcon(self.app.resource_location + '/edit16.png'),
            '%s\t%s' % (_('Edit Object'), _('E')))
        self.menueditok = self.menuedit.addAction(
            QtGui.QIcon(self.app.resource_location + '/power16.png'),
            '%s\t%s' % (_('Exit Editor'), _('Ctrl+S')))

        # adjust the initial state of the menu entries related to the editor
        self.menueditedit.setDisabled(False)
        self.menueditok.setDisabled(True)

        # ############################ EDIT -> CONVERSION ######################################################
        # Separator
        self.menuedit.addSeparator()
        self.menuedit_convert = self.menuedit.addMenu(
            QtGui.QIcon(self.app.resource_location + '/convert24.png'), _('Conversion'))

        self.menuedit_convert_sg2mg = self.menuedit_convert.addAction(
            QtGui.QIcon(self.app.resource_location + '/convert24.png'),
            '%s\t%s' % (_('Convert Single to MultiGeo'), ''))
        self.menuedit_convert_sg2mg.setToolTip(
            _("Will convert a Geometry object from single_geometry type\n"
              "to a multi_geometry type.")
        )
        self.menuedit_convert_mg2sg = self.menuedit_convert.addAction(
            QtGui.QIcon(self.app.resource_location + '/convert24.png'),
            '%s\t%s' % (_('Convert Multi to SingleGeo'), ''))
        self.menuedit_convert_mg2sg.setToolTip(
            _("Will convert a Geometry object from multi_geometry type\n"
              "to a single_geometry type.")
        )
        # Separator
        self.menuedit_convert.addSeparator()
        self.menueditconvert_any2geo = self.menuedit_convert.addAction(
            QtGui.QIcon(self.app.resource_location + '/copy_geo.png'),
            '%s\t%s' % (_('Convert Any to Geo'), ''))
        self.menueditconvert_any2gerber = self.menuedit_convert.addAction(
            QtGui.QIcon(self.app.resource_location + '/copy_geo.png'),
            '%s\t%s' % (_('Convert Any to Gerber'), ''))
        self.menueditconvert_any2excellon = self.menuedit_convert.addAction(
            QtGui.QIcon(self.app.resource_location + '/copy_geo.png'),
            '%s\t%s' % (_('Convert Any to Excellon'), ''))
        self.menuedit_convert.setToolTipsVisible(True)

        # ############################ EDIT -> JOIN        ######################################################
        self.menuedit_join = self.menuedit.addMenu(
            QtGui.QIcon(self.app.resource_location + '/join16.png'), _('Join Objects'))
        self.menuedit_join2geo = self.menuedit_join.addAction(
            QtGui.QIcon(self.app.resource_location + '/join16.png'),
            '%s\t%s' % (_('Join Geo/Gerber/Exc -> Geo'), ''))
        self.menuedit_join2geo.setToolTip(
            _("Merge a selection of objects, which can be of type:\n"
              "- Gerber\n"
              "- Excellon\n"
              "- Geometry\n"
              "into a new combo Geometry object.")
        )
        self.menuedit_join_exc2exc = self.menuedit_join.addAction(
            QtGui.QIcon(self.app.resource_location + '/join16.png'),
            '%s\t%s' % (_('Join Excellon(s) -> Excellon'), ''))
        self.menuedit_join_exc2exc.setToolTip(
            _("Merge a selection of Excellon objects into a new combo Excellon object.")
        )
        self.menuedit_join_grb2grb = self.menuedit_join.addAction(
            QtGui.QIcon(self.app.resource_location + '/join16.png'),
            '%s\t%s' % (_('Join Gerber(s) -> Gerber'), ''))
        self.menuedit_join_grb2grb.setToolTip(
            _("Merge a selection of Gerber objects into a new combo Gerber object.")
        )
        self.menuedit_join.setToolTipsVisible(True)

        # ############################ EDIT -> COPY        ######################################################
        # Separator
        self.menuedit.addSeparator()
        self.menueditcopyobject = self.menuedit.addAction(
            QtGui.QIcon(self.app.resource_location + '/copy.png'),
            '%s\t%s' % (_('Copy'), _('Ctrl+C')))

        # Separator
        self.menuedit.addSeparator()
        self.menueditdelete = self.menuedit.addAction(
            QtGui.QIcon(self.app.resource_location + '/trash16.png'),
            '%s\t%s' % (_('Delete'), _('DEL')))

        # Separator
        self.menuedit.addSeparator()
        self.menueditorigin = self.menuedit.addAction(
            QtGui.QIcon(self.app.resource_location + '/origin16.png'),
            '%s\t%s' % (_('Set Origin'), _('O')))
        self.menuedit_move2origin = self.menuedit.addAction(
            QtGui.QIcon(self.app.resource_location + '/origin2_16.png'),
            '%s\t%s' % (_('Move to Origin'), _('Shift+O')))

        self.menueditjump = self.menuedit.addAction(
            QtGui.QIcon(self.app.resource_location + '/jump_to16.png'),
            '%s\t%s' % (_('Jump to Location'), _('J')))
        self.menueditlocate = self.menuedit.addAction(
            QtGui.QIcon(self.app.resource_location + '/locate16.png'),
            '%s\t%s' % (_('Locate in Object'), _('Shift+J')))

        # Separator
        self.menuedit.addSeparator()
        self.menuedittoggleunits = self.menuedit.addAction(
            QtGui.QIcon(self.app.resource_location + '/toggle_units16.png'),
            '%s\t%s' % (_('Toggle Units'), _('Q')))
        self.menueditselectall = self.menuedit.addAction(
            QtGui.QIcon(self.app.resource_location + '/select_all.png'),
            '%s\t%s' % (_('Select All'), _('Ctrl+A')))

        # Separator
        self.menuedit.addSeparator()
        self.menueditpreferences = self.menuedit.addAction(
            QtGui.QIcon(self.app.resource_location + '/pref.png'),
            '%s\t%s' % (_('Preferences'), _('Shift+P')))

        # ########################################################################
        # ########################## OPTIONS # ###################################
        # ########################################################################

        self.menuoptions = self.menu.addMenu(_('Options'))
        self.menuoptions_transform_rotate = self.menuoptions.addAction(
            QtGui.QIcon(self.app.resource_location + '/rotate.png'),
            '%s\t%s' % (_("Rotate Selection"), _('Shift+(R)')))
        # Separator
        self.menuoptions.addSeparator()

        self.menuoptions_transform_skewx = self.menuoptions.addAction(
            QtGui.QIcon(self.app.resource_location + '/skewX.png'),
            '%s\t%s' % (_("Skew on X axis"), _('Shift+X')))
        self.menuoptions_transform_skewy = self.menuoptions.addAction(
            QtGui.QIcon(self.app.resource_location + '/skewY.png'),
            '%s\t%s' % (_("Skew on Y axis"), _('Shift+Y')))

        # Separator
        self.menuoptions.addSeparator()
        self.menuoptions_transform_flipx = self.menuoptions.addAction(
            QtGui.QIcon(self.app.resource_location + '/flipx.png'),
            '%s\t%s' % (_("Flip on X axis"), _('X')))
        self.menuoptions_transform_flipy = self.menuoptions.addAction(
            QtGui.QIcon(self.app.resource_location + '/flipy.png'),
            '%s\t%s' % (_("Flip on Y axis"), _('Y')))
        # Separator
        self.menuoptions.addSeparator()

        self.menuoptions_view_source = self.menuoptions.addAction(
            QtGui.QIcon(self.app.resource_location + '/source32.png'),
            '%s\t%s' % (_("View source"), _('Alt+S')))
        self.menuoptions_tools_db = self.menuoptions.addAction(
            QtGui.QIcon(self.app.resource_location + '/database32.png'),
            '%s\t%s' % (_("Tools Database"), _('Ctrl+D')))
        # Separator
        self.menuoptions.addSeparator()

        # ########################################################################
        # ########################## View # ######################################
        # ########################################################################
        self.menuview = self.menu.addMenu(_('View'))
        self.menuviewenable = self.menuview.addAction(
            QtGui.QIcon(self.app.resource_location + '/replot16.png'),
            '%s\t%s' % (_('Enable all'), _('Alt+1')))
        self.menuviewdisableall = self.menuview.addAction(
            QtGui.QIcon(self.app.resource_location + '/clear_plot16.png'),
            '%s\t%s' % (_('Disable all'), _('Alt+2')))
        self.menuviewenableother = self.menuview.addAction(
            QtGui.QIcon(self.app.resource_location + '/replot16.png'),
            '%s\t%s' % (_('Enable non-selected'), _('Alt+3')))
        self.menuviewdisableother = self.menuview.addAction(
            QtGui.QIcon(self.app.resource_location + '/clear_plot16.png'),
            '%s\t%s' % (_('Disable non-selected'), _('Alt+4')))

        # Separator
        self.menuview.addSeparator()
        self.menuview_zoom_fit = self.menuview.addAction(
            QtGui.QIcon(self.app.resource_location + '/zoom_fit32.png'),
            '%s\t%s' % (_("Zoom Fit"), _('V')))
        self.menuview_zoom_in = self.menuview.addAction(
            QtGui.QIcon(self.app.resource_location + '/zoom_in32.png'),
            '%s\t%s' % (_("Zoom In"), _('=')))
        self.menuview_zoom_out = self.menuview.addAction(
            QtGui.QIcon(self.app.resource_location + '/zoom_out32.png'),
            '%s\t%s' % (_("Zoom Out"), _('-')))
        self.menuview.addSeparator()

        # Replot all
        self.menuview_replot = self.menuview.addAction(
            QtGui.QIcon(self.app.resource_location + '/replot32.png'),
            '%s\t%s' % (_("Redraw All"), _('F5')))
        self.menuview.addSeparator()

        self.menuview_toggle_code_editor = self.menuview.addAction(
            QtGui.QIcon(self.app.resource_location + '/code_editor32.png'),
            '%s\t%s' % (_('Toggle Code Editor'), _('Shift+E')))
        self.menuview.addSeparator()
        self.menuview_toggle_fscreen = self.menuview.addAction(
            QtGui.QIcon(self.app.resource_location + '/fscreen32.png'),
            '%s\t%s' % (_("Toggle FullScreen"), _('Alt+F10')))
        self.menuview_toggle_parea = self.menuview.addAction(
            QtGui.QIcon(self.app.resource_location + '/plot32.png'),
            '%s\t%s' % (_("Toggle Plot Area"), _('Ctrl+F10')))
        self.menuview_toggle_notebook = self.menuview.addAction(
            QtGui.QIcon(self.app.resource_location + '/notebook32.png'),
            '%s\t%s' % (_("Toggle Project/Properties/Tool"), _('`')))

        self.menuview.addSeparator()
        self.menuview_toggle_grid = self.menuview.addAction(
            QtGui.QIcon(self.app.resource_location + '/grid32.png'),
            '%s\t%s' % (_("Toggle Grid Snap"), _('G')))
        self.menuview_toggle_grid_lines = self.menuview.addAction(
            QtGui.QIcon(self.app.resource_location + '/grid_lines32.png'),
            '%s\t%s' % (_("Toggle Grid Lines"), _('Shift+G')))
        self.menuview_toggle_axis = self.menuview.addAction(
            QtGui.QIcon(self.app.resource_location + '/axis32.png'),
            '%s\t%s' % (_("Toggle Axis"), _('Shift+A')))
        self.menuview_toggle_workspace = self.menuview.addAction(
            QtGui.QIcon(self.app.resource_location + '/workspace24.png'),
            '%s\t%s' % (_("Toggle Workspace"), _('Shift+W')))
        self.menuview_toggle_hud = self.menuview.addAction(
            QtGui.QIcon(self.app.resource_location + '/hud_32.png'),
            '%s\t%s' % (_("Toggle HUD"), _('Shift+H')))

        # ########################################################################
        # ########################## Objects # ###################################
        # ########################################################################
        self.menuobjects = self.menu.addMenu(_('Objects'))
        self.menuobjects.addSeparator()
        self.menuobjects_selall = self.menuobjects.addAction(
            QtGui.QIcon(self.app.resource_location + '/select_all.png'),
            '%s\t%s' % (_('Select All'), ''))
        self.menuobjects_unselall = self.menuobjects.addAction(
            QtGui.QIcon(self.app.resource_location + '/deselect_all32.png'),
            '%s\t%s' % (_('Deselect All'), ''))

        # ########################################################################
        # ########################## Tool # ######################################
        # ########################################################################
        self.menutool = QtWidgets.QMenu(_('Tool'))
        self.menutoolaction = self.menu.addMenu(self.menutool)
        self.menutoolshell = self.menutool.addAction(
            QtGui.QIcon(self.app.resource_location + '/shell16.png'),
            '%s\t%s' % (_('Command Line'), _('S')))

        # ########################################################################
        # ########################## Help # ######################################
        # ########################################################################
        self.menuhelp = self.menu.addMenu(_('Help'))
        self.menuhelp_manual = self.menuhelp.addAction(
            QtGui.QIcon(self.app.resource_location + '/globe16.png'),
            '%s\t%s' % (_('Online Help'), _('F1')))

        self.menuhelp_bookmarks = self.menuhelp.addMenu(
            QtGui.QIcon(self.app.resource_location + '/bookmarks16.png'), _('Bookmarks'))
        self.menuhelp_bookmarks.addSeparator()
        self.menuhelp_bookmarks_manager = self.menuhelp_bookmarks.addAction(
            QtGui.QIcon(self.app.resource_location + '/bookmarks16.png'),
            '%s\t%s' % (_('Bookmarks Manager'), ''))

        self.menuhelp.addSeparator()
        self.menuhelp_report_bug = self.menuhelp.addAction(
            QtGui.QIcon(self.app.resource_location + '/bug16.png'),
            '%s\t%s' % (_('Report a bug'), ''))
        self.menuhelp.addSeparator()
        self.menuhelp_exc_spec = self.menuhelp.addAction(
            QtGui.QIcon(self.app.resource_location + '/pdf_link16.png'),
            '%s\t%s' % (_('Excellon Specification'), ''))
        self.menuhelp_gerber_spec = self.menuhelp.addAction(
            QtGui.QIcon(self.app.resource_location + '/pdf_link16.png'),
            '%s\t%s' % (_('Gerber Specification'), ''))

        self.menuhelp.addSeparator()

        self.menuhelp_shortcut_list = self.menuhelp.addAction(
            QtGui.QIcon(self.app.resource_location + '/shortcuts24.png'),
            '%s\t%s' % (_('Shortcuts List'), _('F3')))
        self.menuhelp_videohelp = self.menuhelp.addAction(
            QtGui.QIcon(self.app.resource_location + '/youtube32.png'),
            '%s\t%s' % (_('YouTube Channel'), _('F4')))

        self.menuhelp.addSeparator()

        self.menuhelp_readme = self.menuhelp.addAction(
            QtGui.QIcon(self.app.resource_location + '/warning.png'),
            '%s\t%s' % (_("How To"), ''))

        self.menuhelp_about = self.menuhelp.addAction(
            QtGui.QIcon(self.app.resource_location + '/about32.png'),
            '%s\t%s' % (_('About'), ''))

        # ########################################################################
        # ########################## GEOMETRY EDITOR # ###########################
        # ########################################################################
        self.geo_editor_menu = QtWidgets.QMenu('>%s<' % _('Geo Editor'))
        self.menu.addMenu(self.geo_editor_menu)

        self.geo_add_circle_menuitem = self.geo_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/circle32.png'),
            '%s\t%s' % (_('Add Circle'), _('O'))
        )
        self.geo_add_arc_menuitem = self.geo_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/arc16.png'),
            '%s\t%s' % (_('Add Arc'), _('A')))
        self.geo_editor_menu.addSeparator()
        self.geo_add_rectangle_menuitem = self.geo_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/rectangle32.png'),
            '%s\t%s' % (_('Add Rectangle'), _('R'))
        )
        self.geo_add_polygon_menuitem = self.geo_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/polygon32.png'),
            '%s\t%s' % (_('Add Polygon'), _('N'))
        )
        self.geo_add_path_menuitem = self.geo_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/path32.png'),
            '%s\t%s' % (_('Add Path'), _('P')))
        self.geo_editor_menu.addSeparator()
        self.geo_add_text_menuitem = self.geo_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/text32.png'),
            '%s\t%s' % (_('Add Text'), _('T')))
        self.geo_editor_menu.addSeparator()
        self.geo_union_menuitem = self.geo_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/union16.png'),
            '%s\t%s' % (_('Polygon Union'), _('U')))
        self.geo_intersection_menuitem = self.geo_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/intersection16.png'),
            '%s\t%s' % (_('Polygon Intersection'), _('E')))
        self.geo_subtract_menuitem = self.geo_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/subtract16.png'),
            '%s\t%s' % (_('Polygon Subtraction'), _('S'))
        )
        self.geo_editor_menu.addSeparator()
        self.geo_cutpath_menuitem = self.geo_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/cutpath16.png'),
            '%s\t%s' % (_('Cut Path'), _('X')))
        # self.move_menuitem = self.menu.addAction(
        #   QtGui.QIcon(self.app.resource_location + '/move16.png'), "Move Objects 'm'")
        self.geo_copy_menuitem = self.geo_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/copy16.png'),
            '%s\t%s' % (_("Copy Geom"), _('C')))
        self.geo_delete_menuitem = self.geo_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/deleteshape16.png'),
            '%s\t%s' % (_("Delete Shape"), _('DEL'))
        )
        self.geo_editor_menu.addSeparator()
        self.geo_move_menuitem = self.geo_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/move32.png'),
            '%s\t%s' % (_("Move"), _('M')))
        self.geo_buffer_menuitem = self.geo_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/buffer16.png'),
            '%s\t%s' % (_("Buffer Tool"), _('B'))
        )
        self.geo_paint_menuitem = self.geo_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/paint16.png'),
            '%s\t%s' % (_("Paint Tool"), _('I'))
        )
        self.geo_transform_menuitem = self.geo_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/transform.png'),
            '%s\t%s' % (_("Transform Tool"), _('Alt+R'))
        )
        self.geo_editor_menu.addSeparator()
        self.geo_cornersnap_menuitem = self.geo_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/corner32.png'),
            '%s\t%s' % (_("Toggle Corner Snap"), _('K'))
        )

        # ########################################################################
        # ########################## EXCELLON Editor # ###########################
        # ########################################################################
        self.exc_editor_menu = QtWidgets.QMenu('>%s<' % _('Excellon Editor'))
        self.menu.addMenu(self.exc_editor_menu)

        self.exc_add_array_drill_menuitem = self.exc_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/rectangle32.png'),
            '%s\t%s' % (_('Add Drill Array'), _('A')))
        self.exc_add_drill_menuitem = self.exc_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/plus16.png'),
            '%s\t%s' % (_('Add Drill'), _('D')))
        self.exc_editor_menu.addSeparator()

        self.exc_add_array_slot_menuitem = self.exc_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/slot_array26.png'),
            '%s\t%s' % (_('Add Slot Array'), _('Q')))
        self.exc_add_slot_menuitem = self.exc_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/slot26.png'),
            '%s\t%s' % (_('Add Slot'), _('W')))
        self.exc_editor_menu.addSeparator()

        self.exc_resize_drill_menuitem = self.exc_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/resize16.png'),
            '%s\t%s' % (_('Resize Drill(S)'), _('R'))
        )
        self.exc_copy_drill_menuitem = self.exc_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/copy32.png'),
            '%s\t%s' % (_('Copy'), _('C')))
        self.exc_delete_drill_menuitem = self.exc_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/deleteshape32.png'),
            '%s\t%s' % (_('Delete'), _('DEL'))
        )
        self.exc_editor_menu.addSeparator()

        self.exc_move_drill_menuitem = self.exc_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/move32.png'),
            '%s\t%s' % (_('Move Drill'), _('M')))

        # ########################################################################
        # ########################## GERBER Editor # #############################
        # ########################################################################
        self.grb_editor_menu = QtWidgets.QMenu('>%s<' % _('Gerber Editor'))
        self.menu.addMenu(self.grb_editor_menu)

        self.grb_add_pad_menuitem = self.grb_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/aperture16.png'),
            '%s\t%s' % (_('Add Pad'), _('P')))
        self.grb_add_pad_array_menuitem = self.grb_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/padarray32.png'),
            '%s\t%s' % (_('Add Pad Array'), _('A')))
        self.grb_add_track_menuitem = self.grb_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/track32.png'),
            '%s\t%s' % (_('Add Track'), _('T')))
        self.grb_add_region_menuitem = self.grb_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/rectangle32.png'),
            '%s\t%s' % (_('Add Region'), _('N')))
        self.grb_editor_menu.addSeparator()

        self.grb_convert_poly_menuitem = self.grb_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/poligonize32.png'),
            '%s\t%s' % (_("Poligonize"), _('Alt+N')))
        self.grb_add_semidisc_menuitem = self.grb_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/semidisc32.png'),
            '%s\t%s' % (_("Add SemiDisc"), _('E')))
        self.grb_add_disc_menuitem = self.grb_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/disc32.png'),
            '%s\t%s' % (_("Add Disc"), _('D')))
        self.grb_add_buffer_menuitem = self.grb_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/buffer16-2.png'),
            '%s\t%s' % (_('Buffer'), _('B')))
        self.grb_add_scale_menuitem = self.grb_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/scale32.png'),
            '%s\t%s' % (_('Scale'), _('S')))
        self.grb_add_markarea_menuitem = self.grb_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/markarea32.png'),
            '%s\t%s' % (_('Mark Area'), _('Alt+A')))
        self.grb_add_eraser_menuitem = self.grb_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/eraser26.png'),
            '%s\t%s' % (_('Eraser'), _('Ctrl+E')))
        self.grb_transform_menuitem = self.grb_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/transform.png'),
            '%s\t%s' % (_("Transform"), _('Alt+R')))
        self.grb_editor_menu.addSeparator()

        self.grb_copy_menuitem = self.grb_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/copy32.png'),
            '%s\t%s' % (_('Copy'), _('C')))
        self.grb_delete_menuitem = self.grb_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/deleteshape32.png'),
            '%s\t%s' % (_('Delete'), _('DEL')))
        self.grb_editor_menu.addSeparator()

        self.grb_move_menuitem = self.grb_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/move32.png'),
            '%s\t%s' % (_('Move'), _('M')))

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

        self.menuproject_brown = self.menuprojectcolor.addAction(
            QtGui.QIcon(self.app.resource_location + '/white32.png'), _('White'))

        self.menuproject_brown = self.menuprojectcolor.addAction(
            QtGui.QIcon(self.app.resource_location + '/black32.png'), _('Black'))

        self.menuprojectcolor.addSeparator()

        self.menuproject_custom = self.menuprojectcolor.addAction(
            QtGui.QIcon(self.app.resource_location + '/set_color32.png'), _('Custom'))

        self.menuprojectcolor.addSeparator()

        self.menuproject_custom = self.menuprojectcolor.addAction(
            QtGui.QIcon(self.app.resource_location + '/set_color32.png'), _('Opacity'))

        self.menuproject_custom = self.menuprojectcolor.addAction(
            QtGui.QIcon(self.app.resource_location + '/set_color32.png'), _('Default'))

        self.menuproject.addSeparator()

        self.menuprojectgeneratecnc = self.menuproject.addAction(
            QtGui.QIcon(self.app.resource_location + '/cnc32.png'), _('Create CNCJob'))
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
        # The order: SPLITTER -> NOTEBOOK -> SNAP TOOLBAR is important and without it the GUI will not be initialized as
        # desired.
        self.splitter = QtWidgets.QSplitter()
        self.setCentralWidget(self.splitter)

        # self.notebook = QtWidgets.QTabWidget()
        self.notebook = FCDetachableTab(protect=True, parent=self)
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

        self.toolbaredit = QtWidgets.QToolBar(_('Edit Toolbar'))
        self.toolbaredit.setObjectName('Edit_TB')
        self.addToolBar(self.toolbaredit)

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

        # ### INFOBAR TOOLBARS ###################################################
        self.delta_coords_toolbar = QtWidgets.QToolBar(_('Delta Coordinates Toolbar'))
        self.delta_coords_toolbar.setObjectName('Delta_Coords_TB')

        self.coords_toolbar = QtWidgets.QToolBar(_('Coordinates Toolbar'))
        self.coords_toolbar.setObjectName('Coords_TB')

        self.grid_toolbar = QtWidgets.QToolBar(_('Grid Toolbar'))
        self.grid_toolbar.setObjectName('Snap_TB')
        self.grid_toolbar.setStyleSheet(
            """
            QToolBar { padding: 0; }
            QToolBar QToolButton { padding: -2; margin: -2; }
            """
        )

        self.status_toolbar = QtWidgets.QToolBar(_('Status Toolbar'))
        self.status_toolbar.setStyleSheet(
            """
            QToolBar { padding: 0; }
            QToolBar QToolButton { padding: -2; margin: -2; }
            """
        )

        # ########################################################################
        # ########################## File Toolbar# ###############################
        # ########################################################################
        self.file_open_gerber_btn = self.toolbarfile.addAction(
            QtGui.QIcon(self.app.resource_location + '/flatcam_icon32.png'), _("Open Gerber"))
        self.file_open_excellon_btn = self.toolbarfile.addAction(
            QtGui.QIcon(self.app.resource_location + '/drill32.png'), _("Open Excellon"))
        self.toolbarfile.addSeparator()
        self.file_open_btn = self.toolbarfile.addAction(
            QtGui.QIcon(self.app.resource_location + '/folder32.png'), _("Open Project"))
        self.file_save_btn = self.toolbarfile.addAction(
            QtGui.QIcon(self.app.resource_location + '/project_save32.png'), _("Save project"))

        # ########################################################################
        # ########################## Edit Toolbar# ###############################
        # ########################################################################
        self.editgeo_btn = self.toolbaredit.addAction(
            QtGui.QIcon(self.app.resource_location + '/edit_file32.png'), _("Editor"))
        self.update_obj_btn = self.toolbaredit.addAction(
            QtGui.QIcon(self.app.resource_location + '/close_edit_file32.png'), _("Save Object and close the Editor")
        )

        self.toolbaredit.addSeparator()
        self.copy_btn = self.toolbaredit.addAction(
            QtGui.QIcon(self.app.resource_location + '/copy_file32.png'), _("Copy"))
        self.delete_btn = self.toolbaredit.addAction(
            QtGui.QIcon(self.app.resource_location + '/trash32.png'), _("Delete"))
        self.toolbaredit.addSeparator()
        self.distance_btn = self.toolbaredit.addAction(
            QtGui.QIcon(self.app.resource_location + '/distance32.png'), _("Distance Tool"))
        self.distance_min_btn = self.toolbaredit.addAction(
            QtGui.QIcon(self.app.resource_location + '/distance_min32.png'), _("Distance Min Tool"))
        self.origin_btn = self.toolbaredit.addAction(
            QtGui.QIcon(self.app.resource_location + '/origin32.png'), _('Set Origin'))
        self.move2origin_btn = self.toolbaredit.addAction(
            QtGui.QIcon(self.app.resource_location + '/origin2_32.png'), _('Move to Origin'))

        self.jmp_btn = self.toolbaredit.addAction(
            QtGui.QIcon(self.app.resource_location + '/jump_to16.png'), _('Jump to Location'))
        self.locate_btn = self.toolbaredit.addAction(
            QtGui.QIcon(self.app.resource_location + '/locate32.png'), _('Locate in Object'))

        # ########################################################################
        # ########################## View Toolbar# ###############################
        # ########################################################################
        self.replot_btn = self.toolbarview.addAction(
            QtGui.QIcon(self.app.resource_location + '/replot32.png'), _("Replot"))
        self.clear_plot_btn = self.toolbarview.addAction(
            QtGui.QIcon(self.app.resource_location + '/clear_plot32.png'), _("Clear Plot"))
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
            QtGui.QIcon(self.app.resource_location + '/shell32.png'), _("Command Line"))
        self.new_script_btn = self.toolbarshell.addAction(
            QtGui.QIcon(self.app.resource_location + '/script_new24.png'), '%s ...' % _('New Script'))
        self.open_script_btn = self.toolbarshell.addAction(
            QtGui.QIcon(self.app.resource_location + '/open_script32.png'), '%s ...' % _('Open Script'))
        self.run_script_btn = self.toolbarshell.addAction(
            QtGui.QIcon(self.app.resource_location + '/script16.png'), '%s ...' % _('Run Script'))

        # ########################################################################
        # ########################## Tools Toolbar# ##############################
        # ########################################################################
        self.dblsided_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/doubleside32.png'), _("2-Sided Tool"))
        self.align_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/align32.png'), _("Align Objects Tool"))
        self.extract_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/extract_drill32.png'), _("Extract Drills Tool"))

        self.cutout_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/cut16_bis.png'), _("Cutout Tool"))
        self.ncc_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/ncc16.png'), _("NCC Tool"))
        self.paint_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/paint20_1.png'), _("Paint Tool"))
        self.isolation_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/iso_16.png'), _("Isolation Tool"))
        self.drill_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/drilling_tool32.png'), _("Drilling Tool"))
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
        self.punch_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/punch32.png'), _("Punch Gerber Tool"))
        self.invert_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/invert32.png'), _("Invert Gerber Tool"))
        self.corners_tool_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/corners_32.png'), _("Corner Markers Tool"))
        self.etch_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/etch_32.png'), _("Etch Compensation Tool"))

        # ########################################################################
        # ########################## Excellon Editor Toolbar# ####################
        # ########################################################################
        self.select_drill_btn = self.exc_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/pointer32.png'), _("Select"))
        self.add_drill_btn = self.exc_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/plus16.png'), _('Add Drill'))
        self.add_drill_array_btn = self.exc_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/addarray16.png'), _('Add Drill Array'))
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
            QtGui.QIcon(self.app.resource_location + '/trash32.png'), _("Delete Shape"))
        self.geo_transform_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/transform.png'), _("Transformations"))
        self.geo_edit_toolbar.addSeparator()
        self.geo_move_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/move32.png'), _("Move Objects"))

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
        # ########################## GRID Toolbar# ###############################
        # ########################################################################

        # Snap GRID toolbar is always active to facilitate usage of measurements done on GRID
        self.grid_snap_btn = self.grid_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/grid32.png'), _('Snap to grid'))
        self.grid_gap_x_entry = FCEntry2()
        self.grid_gap_x_entry.setMaximumWidth(70)
        self.grid_gap_x_entry.setToolTip(_("Grid X snapping distance"))
        self.grid_toolbar.addWidget(self.grid_gap_x_entry)

        self.grid_toolbar.addWidget(FCLabel(" "))
        self.grid_gap_link_cb = FCCheckBox()
        self.grid_gap_link_cb.setToolTip(_("When active, value on Grid_X\n"
                                           "is copied to the Grid_Y value."))
        self.grid_toolbar.addWidget(self.grid_gap_link_cb)
        self.grid_toolbar.addWidget(FCLabel(" "))

        self.grid_gap_y_entry = FCEntry2()
        self.grid_gap_y_entry.setMaximumWidth(70)
        self.grid_gap_y_entry.setToolTip(_("Grid Y snapping distance"))
        self.grid_toolbar.addWidget(self.grid_gap_y_entry)
        self.grid_toolbar.addWidget(FCLabel(" "))

        self.ois_grid = OptionalInputSection(self.grid_gap_link_cb, [self.grid_gap_y_entry], logic=False)

        self.corner_snap_btn = self.grid_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/corner32.png'), _('Snap to corner'))

        self.snap_max_dist_entry = FCEntry()
        self.snap_max_dist_entry.setMaximumWidth(70)
        self.snap_max_dist_entry.setToolTip(_("Max. magnet distance"))
        self.snap_magnet = self.grid_toolbar.addWidget(self.snap_max_dist_entry)

        self.corner_snap_btn.setVisible(False)
        self.snap_magnet.setVisible(False)

        # ########################################################################
        # ########################## Status Toolbar ##############################
        # ########################################################################
        self.axis_status_label = FCLabel()
        self.axis_status_label.setToolTip(_("Toggle the display of axis on canvas"))
        self.axis_status_label.setPixmap(QtGui.QPixmap(self.app.resource_location + '/axis16.png'))
        self.status_toolbar.addWidget(self.axis_status_label)
        self.status_toolbar.addWidget(FCLabel(" "))

        self.pref_status_label = FCLabel()
        self.pref_status_label.setToolTip(_("Preferences"))
        self.pref_status_label.setPixmap(QtGui.QPixmap(self.app.resource_location + '/settings18.png'))
        self.status_toolbar.addWidget(self.pref_status_label)
        self.status_toolbar.addWidget(FCLabel(" "))

        self.shell_status_label = FCLabel()
        self.shell_status_label.setToolTip(_("Command Line"))
        self.shell_status_label.setPixmap(QtGui.QPixmap(self.app.resource_location + '/shell20.png'))
        self.status_toolbar.addWidget(self.shell_status_label)
        self.status_toolbar.addWidget(FCLabel(" "))

        self.hud_label = FCLabel()
        self.hud_label.setToolTip(_("HUD (Heads up display)"))
        self.hud_label.setPixmap(QtGui.QPixmap(self.app.resource_location + '/hud16.png'))
        self.status_toolbar.addWidget(self.hud_label)
        self.status_toolbar.addWidget(FCLabel(" "))

        self.wplace_label = FCLabel("A4")
        self.wplace_label.setToolTip(_("Draw a delimiting rectangle on canvas.\n"
                                       "The purpose is to illustrate the limits for our work.")
                                     )
        self.wplace_label.setMargin(2)
        self.status_toolbar.addWidget(self.wplace_label)
        self.status_toolbar.addWidget(FCLabel(" "))

        # #######################################################################
        # ####################### Delta Coordinates TOOLBAR #####################
        # #######################################################################
        self.rel_position_label = FCLabel(
            "<b>Dx</b>: 0.0000&nbsp;&nbsp;   <b>Dy</b>: 0.0000&nbsp;&nbsp;&nbsp;&nbsp;")
        self.rel_position_label.setMinimumWidth(110)
        self.rel_position_label.setToolTip(_("Relative measurement.\nReference is last click position"))
        self.delta_coords_toolbar.addWidget(self.rel_position_label)

        # #######################################################################
        # ####################### Coordinates TOOLBAR ###########################
        # #######################################################################
        self.position_label = FCLabel("&nbsp;<b>X</b>: 0.0000&nbsp;&nbsp;   <b>Y</b>: 0.0000&nbsp;")
        self.position_label.setMinimumWidth(110)
        self.position_label.setToolTip(_("Absolute measurement.\n"
                                         "Reference is (X=0, Y= 0) position"))
        self.coords_toolbar.addWidget(self.position_label)

        # #######################################################################
        # ####################### TCL Shell DOCK ################################
        # #######################################################################
        self.shell_dock = FCDock(_("TCL Shell"), close_callback=self.toggle_shell_ui)
        self.shell_dock.setObjectName('Shell_DockWidget')
        self.shell_dock.setAllowedAreas(QtCore.Qt.AllDockWidgetAreas)
        self.shell_dock.setFeatures(QtWidgets.QDockWidget.DockWidgetMovable |
                                    QtWidgets.QDockWidget.DockWidgetFloatable |
                                    QtWidgets.QDockWidget.DockWidgetClosable)
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.shell_dock)

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
        self.properties_tab = QtWidgets.QWidget()
        # self.properties_tab.setMinimumWidth(270)
        self.properties_tab.setObjectName("properties_tab")
        self.properties_tab_layout = QtWidgets.QVBoxLayout(self.properties_tab)
        self.properties_tab_layout.setContentsMargins(2, 2, 2, 2)

        self.properties_scroll_area = VerticalScrollArea()
        # self.properties_scroll_area.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.properties_tab_layout.addWidget(self.properties_scroll_area)
        self.notebook.addTab(self.properties_tab, _("Properties"))

        # ########################################################################
        # ########################## TOOL Tab # ##################################
        # ########################################################################
        self.tool_tab = QtWidgets.QWidget()
        self.tool_tab.setObjectName("tool_tab")
        self.tool_tab_layout = QtWidgets.QVBoxLayout(self.tool_tab)
        self.tool_tab_layout.setContentsMargins(2, 2, 2, 2)
        self.notebook.addTab(self.tool_tab, _("Tool"))
        self.tool_scroll_area = VerticalScrollArea()
        # self.tool_scroll_area.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
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
        self.plot_tab_area = FCDetachableTab2(protect=False, protect_by_name=[_('Plot Area')], parent=self)
        self.plot_tab_area.useOldIndex(True)

        self.right_lay.addWidget(self.plot_tab_area)
        self.plot_tab_area.setTabsClosable(True)

        self.plot_tab = QtWidgets.QWidget()
        self.plot_tab.setObjectName("plotarea_tab")
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

        self.pref_defaults_button = FCButton(_("Restore Defaults"))
        self.pref_defaults_button.setIcon(QtGui.QIcon(self.app.resource_location + '/restore32.png'))
        self.pref_defaults_button.setMinimumWidth(130)
        self.pref_defaults_button.setToolTip(
            _("Restore the entire set of default values\n"
              "to the initial values loaded after first launch."))
        self.pref_tab_bottom_layout_1.addWidget(self.pref_defaults_button)

        self.pref_open_button = FCButton()
        self.pref_open_button.setText(_("Open Pref Folder"))
        self.pref_open_button.setIcon(QtGui.QIcon(self.app.resource_location + '/pref.png'))
        self.pref_open_button.setMinimumWidth(130)
        self.pref_open_button.setToolTip(
            _("Open the folder where FlatCAM save the preferences files."))
        self.pref_tab_bottom_layout_1.addWidget(self.pref_open_button)

        # Clear Settings
        self.clear_btn = FCButton('%s' % _('Clear GUI Settings'))
        self.clear_btn.setIcon(QtGui.QIcon(self.app.resource_location + '/trash32.png'))
        self.clear_btn.setMinimumWidth(130)

        self.clear_btn.setToolTip(
            _("Clear the GUI settings for FlatCAM,\n"
              "such as: layout, gui state, style, hdpi support etc.")
        )

        self.pref_tab_bottom_layout_1.addWidget(self.clear_btn)

        self.pref_tab_bottom_layout_2 = QtWidgets.QHBoxLayout()
        self.pref_tab_bottom_layout_2.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.pref_tab_bottom_layout.addLayout(self.pref_tab_bottom_layout_2)

        self.pref_apply_button = FCButton()
        self.pref_apply_button.setIcon(QtGui.QIcon(self.app.resource_location + '/apply32.png'))
        self.pref_apply_button.setText(_("Apply"))
        self.pref_apply_button.setMinimumWidth(130)
        self.pref_apply_button.setToolTip(
            _("Apply the current preferences without saving to a file."))
        self.pref_tab_bottom_layout_2.addWidget(self.pref_apply_button)

        self.pref_save_button = FCButton()
        self.pref_save_button.setIcon(QtGui.QIcon(self.app.resource_location + '/save_as.png'))
        self.pref_save_button.setText(_("Save"))
        self.pref_save_button.setMinimumWidth(130)
        self.pref_save_button.setToolTip(
            _("Save the current settings in the 'current_defaults' file\n"
              "which is the file storing the working default preferences."))
        self.pref_tab_bottom_layout_2.addWidget(self.pref_save_button)

        self.pref_close_button = FCButton()
        self.pref_close_button.setText(_("Cancel"))
        self.pref_close_button.setMinimumWidth(130)
        self.pref_close_button.setToolTip(
            _("Will not save the changes and will close the preferences window."))
        self.pref_tab_bottom_layout_2.addWidget(self.pref_close_button)

        # ########################################################################
        # #################### SHORTCUT LIST AREA Tab # ##########################
        # ########################################################################
        self.shortcuts_tab = ShortcutsTab()

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
            QtGui.QIcon(self.app.resource_location + '/new_file_geo16.png'), _("Geometry"))
        self.popmenu_new_grb = self.cmenu_newmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/new_file_grb16.png'), "Gerber")
        self.popmenu_new_exc = self.cmenu_newmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/new_file_exc16.png'), _("Excellon"))
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
        self.popmenu_copy = self.popMenu.addAction(QtGui.QIcon(self.app.resource_location + '/copy32.png'), _("Copy"))
        self.popmenu_delete = self.popMenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/delete32.png'), _("Delete"))
        self.popmenu_edit = self.popMenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/edit32.png'), _("Edit"))
        self.popmenu_save = self.popMenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/power16.png'), _("Exit Editor"))
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

        self.infobar.addWidget(self.delta_coords_toolbar)
        self.delta_coords_toolbar.setVisible(self.app.defaults["global_delta_coordsbar_show"])

        self.infobar.addWidget(self.coords_toolbar)
        self.coords_toolbar.setVisible(self.app.defaults["global_coordsbar_show"])

        self.grid_toolbar.setMaximumHeight(24)
        self.infobar.addWidget(self.grid_toolbar)
        self.grid_toolbar.setVisible(self.app.defaults["global_gridbar_show"])

        self.status_toolbar.setMaximumHeight(24)
        self.infobar.addWidget(self.status_toolbar)
        self.status_toolbar.setVisible(self.app.defaults["global_statusbar_show"])

        self.units_label = FCLabel("[mm]")
        self.units_label.setToolTip(_("Application units"))
        self.units_label.setMargin(2)
        self.infobar.addWidget(self.units_label)

        # this used to be done in the APP.__init__()
        self.activity_view = FlatCAMActivityView(app=self.app)
        self.infobar.addWidget(self.activity_view)

        # disabled
        # self.progress_bar = QtWidgets.QProgressBar()
        # self.progress_bar.setMinimum(0)
        # self.progress_bar.setMaximum(100)
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

        # ########################################################################
        # ######################## BUILD PREFERENCES #############################
        # ########################################################################
        self.general_defaults_form = GeneralPreferencesUI(decimals=self.decimals)
        self.gerber_defaults_form = GerberPreferencesUI(decimals=self.decimals)
        self.excellon_defaults_form = ExcellonPreferencesUI(decimals=self.decimals)
        self.geometry_defaults_form = GeometryPreferencesUI(decimals=self.decimals)
        self.cncjob_defaults_form = CNCJobPreferencesUI(decimals=self.decimals)
        self.tools_defaults_form = ToolsPreferencesUI(decimals=self.decimals)
        self.tools2_defaults_form = Tools2PreferencesUI(decimals=self.decimals)
        self.util_defaults_form = UtilPreferencesUI(decimals=self.decimals)

        QtWidgets.qApp.installEventFilter(self)

        # ########################################################################
        # ################## RESTORE THE TOOLBAR STATE from file #################
        # ########################################################################
        flat_settings = QSettings("Open Source", "FlatCAM")
        if flat_settings.contains("saved_gui_state"):
            saved_gui_state = flat_settings.value('saved_gui_state')
            self.restoreState(saved_gui_state)
            log.debug("MainGUI.__init__() --> UI state restored from QSettings.")

        self.corner_snap_btn.setVisible(False)
        self.snap_magnet.setVisible(False)

        if flat_settings.contains("layout"):
            layout = flat_settings.value('layout', type=str)
            self.exc_edit_toolbar.setDisabled(True)
            self.geo_edit_toolbar.setDisabled(True)
            self.grb_edit_toolbar.setDisabled(True)

            log.debug("MainGUI.__init__() --> UI layout restored from QSettings. Layout = %s" % str(layout))
        else:
            self.exc_edit_toolbar.setDisabled(True)
            self.geo_edit_toolbar.setDisabled(True)
            self.grb_edit_toolbar.setDisabled(True)

            flat_settings.setValue('layout', "standard")
            # This will write the setting to the platform specific storage.
            del flat_settings
            log.debug("MainGUI.__init__() --> UI layout restored from defaults. QSettings set to 'standard'")

        # construct the Toolbar Lock menu entry to the context menu of the QMainWindow
        self.lock_action = QtWidgets.QAction()
        self.lock_action.setText(_("Lock Toolbars"))
        self.lock_action.setCheckable(True)

        qsettings = QSettings("Open Source", "FlatCAM")
        if qsettings.contains("toolbar_lock"):
            lock_val = settings.value('toolbar_lock')
            if lock_val == 'true':
                lock_state = True
                self.lock_action.setChecked(True)
            else:

                lock_state = False
                self.lock_action.setChecked(False)
        else:
            lock_state = False
            qsettings.setValue('toolbar_lock', lock_state)

            # This will write the setting to the platform specific storage.
            del qsettings

        self.lock_toolbar(lock=lock_state)

        self.lock_action.triggered[bool].connect(self.lock_toolbar)

        self.pref_open_button.clicked.connect(self.on_preferences_open_folder)
        self.clear_btn.clicked.connect(self.on_gui_clear)

        self.wplace_label.clicked.connect(self.app.on_workspace_toggle)
        self.shell_status_label.clicked.connect(self.toggle_shell_ui)

        # to be used in the future
        # self.plot_tab_area.tab_attached.connect(lambda x: print(x))
        # self.plot_tab_area.tab_detached.connect(lambda x: print(x))

        # restore the toolbar view
        self.restore_toolbar_view()

        # restore the GUI geometry
        self.restore_main_win_geom()

        # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
        # %%%%%%%%%%%%%%%%% GUI Building FINISHED %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
        # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

        # Variable to store the status of the fullscreen event
        self.toggle_fscreen = False
        self.x_pos = None
        self.y_pos = None
        self.width = None
        self.height = None
        self.titlebar_height = None

        self.geom_update[int, int, int, int, int].connect(self.save_geometry)
        self.final_save.connect(self.app.final_save)

        self.shell_dock.visibilityChanged.connect(self.on_shelldock_toggled)

        # Notebook and Plot Tab Area signals
        # make the right click on the notebook tab and plot tab area tab raise a menu
        self.notebook.tabBar.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.plot_tab_area.tabBar.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.on_tab_setup_context_menu()
        # activate initial state
        self.on_detachable_tab_rmb_click(self.app.defaults["global_tabs_detachable"])

        # status bar activation/deactivation
        self.infobar.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.build_infobar_context_menu()

    def set_ui_title(self, name):
        """
        Sets the title of the main window.

        :param name: String that store the project path and project name
        :return: None
        """
        title = 'FlatCAM %s %s - %s - [%s]    %s' % (
            self.app.version, ('BETA' if self.app.beta else ''), platform.architecture()[0], self.app.engine, name)
        self.setWindowTitle(title)

    def save_geometry(self, x, y, width, height, notebook_width):
        """
        Will save the application geometry and positions in the defaults dicitionary to be restored at the next
        launch of the application.

        :param x:               X position of the main window
        :param y:               Y position of the main window
        :param width:           width of the main window
        :param height:          height of the main window
        :param notebook_width:  the notebook width is adjustable so it get saved here, too.

        :return: None
        """
        self.app.defaults["global_def_win_x"] = x
        self.app.defaults["global_def_win_y"] = y
        self.app.defaults["global_def_win_w"] = width
        self.app.defaults["global_def_win_h"] = height
        self.app.defaults["global_def_notebook_width"] = notebook_width
        self.app.preferencesUiManager.save_defaults()

    def restore_main_win_geom(self):
        try:
            self.setGeometry(self.app.defaults["global_def_win_x"],
                             self.app.defaults["global_def_win_y"],
                             self.app.defaults["global_def_win_w"],
                             self.app.defaults["global_def_win_h"])
            self.splitter.setSizes([self.app.defaults["global_def_notebook_width"], 0])
        except KeyError as e:
            log.debug("appGUI.MainGUI.restore_main_win_geom() --> %s" % str(e))

    def restore_toolbar_view(self):
        """
        Some toolbars may be hidden by user and here we restore the state of the toolbars visibility that
        was saved in the defaults dictionary.

        :return: None
        """
        tb = self.app.defaults["global_toolbar_view"]

        if tb & 1:
            self.toolbarfile.setVisible(True)
        else:
            self.toolbarfile.setVisible(False)

        if tb & 2:
            self.toolbaredit.setVisible(True)
        else:
            self.toolbaredit.setVisible(False)

        if tb & 4:
            self.toolbarview.setVisible(True)
        else:
            self.toolbarview.setVisible(False)

        if tb & 8:
            self.toolbartools.setVisible(True)
        else:
            self.toolbartools.setVisible(False)

        if tb & 16:
            self.exc_edit_toolbar.setVisible(True)
        else:
            self.exc_edit_toolbar.setVisible(False)

        if tb & 32:
            self.geo_edit_toolbar.setVisible(True)
        else:
            self.geo_edit_toolbar.setVisible(False)

        if tb & 64:
            self.grb_edit_toolbar.setVisible(True)
        else:
            self.grb_edit_toolbar.setVisible(False)

        # if tb & 128:
        #     self.ui.grid_toolbar.setVisible(True)
        # else:
        #     self.ui.grid_toolbar.setVisible(False)

        # Grid Toolbar is controlled by its own setting

        if tb & 256:
            self.toolbarshell.setVisible(True)
        else:
            self.toolbarshell.setVisible(False)

    def on_tab_setup_context_menu(self):
        initial_checked = self.app.defaults["global_tabs_detachable"]
        action_name = str(_("Detachable Tabs"))
        action = QtWidgets.QAction(self)
        action.setCheckable(True)
        action.setText(action_name)
        action.setChecked(initial_checked)

        self.notebook.tabBar.addAction(action)
        self.plot_tab_area.tabBar.addAction(action)

        try:
            action.triggered.disconnect()
        except TypeError:
            pass
        action.triggered.connect(self.on_detachable_tab_rmb_click)

    def on_detachable_tab_rmb_click(self, checked):
        self.notebook.set_detachable(val=checked)
        self.app.defaults["global_tabs_detachable"] = checked

        self.plot_tab_area.set_detachable(val=checked)
        self.app.defaults["global_tabs_detachable"] = checked

    def build_infobar_context_menu(self):
        delta_coords_action_name = str(_("Delta Coordinates Toolbar"))
        delta_coords_action = QtWidgets.QAction(self)
        delta_coords_action.setCheckable(True)
        delta_coords_action.setText(delta_coords_action_name)
        delta_coords_action.setChecked(self.app.defaults["global_delta_coordsbar_show"])
        self.infobar.addAction(delta_coords_action)
        delta_coords_action.triggered.connect(self.toggle_delta_coords)

        coords_action_name = str(_("Coordinates Toolbar"))
        coords_action = QtWidgets.QAction(self)
        coords_action.setCheckable(True)
        coords_action.setText(coords_action_name)
        coords_action.setChecked(self.app.defaults["global_coordsbar_show"])
        self.infobar.addAction(coords_action)
        coords_action.triggered.connect(self.toggle_coords)

        grid_action_name = str(_("Grid Toolbar"))
        grid_action = QtWidgets.QAction(self)
        grid_action.setCheckable(True)
        grid_action.setText(grid_action_name)
        grid_action.setChecked(self.app.defaults["global_gridbar_show"])
        self.infobar.addAction(grid_action)
        grid_action.triggered.connect(self.toggle_gridbar)

        status_action_name = str(_("Status Toolbar"))
        status_action = QtWidgets.QAction(self)
        status_action.setCheckable(True)
        status_action.setText(status_action_name)
        status_action.setChecked(self.app.defaults["global_statusbar_show"])
        self.infobar.addAction(status_action)
        status_action.triggered.connect(self.toggle_statusbar)

    def toggle_coords(self, checked):
        self.app.defaults["global_coordsbar_show"] = checked
        self.coords_toolbar.setVisible(checked)

    def toggle_delta_coords(self, checked):
        self.app.defaults["global_delta_coordsbar_show"] = checked
        self.delta_coords_toolbar.setVisible(checked)

    def toggle_gridbar(self, checked):
        self.app.defaults["global_gridbar_show"] = checked
        self.grid_toolbar.setVisible(checked)

    def toggle_statusbar(self, checked):
        self.app.defaults["global_statusbar_show"] = checked
        self.status_toolbar.setVisible(checked)

    def eventFilter(self, obj, event):
        """
        Filter the ToolTips display based on a Preferences setting

        :param obj:
        :param event: QT event to filter
        :return:
        """
        if self.app.defaults["global_toggle_tooltips"] is False:
            if event.type() == QtCore.QEvent.ToolTip:
                return True
            else:
                return False

        return False

    def on_preferences_open_folder(self):
        """
        Will open an Explorer window set to the folder path where the FlatCAM preferences files are usually saved.

        :return: None
        """

        if sys.platform == 'win32':
            subprocess.Popen('explorer %s' % self.app.data_path)
        elif sys.platform == 'darwin':
            os.system('open "%s"' % self.app.data_path)
        else:
            subprocess.Popen(['xdg-open', self.app.data_path])
        self.app.inform.emit('[success] %s' % _("FlatCAM Preferences Folder opened."))

    def on_gui_clear(self, signal=None, forced_clear=False):
        """
        Will clear the settings that are stored in QSettings.
        """
        log.debug("Clearing the settings in QSettings. GUI settings cleared.")

        theme_settings = QtCore.QSettings("Open Source", "FlatCAM")
        theme_settings.setValue('theme', 'white')

        del theme_settings

        resource_loc = self.app.resource_location

        response = None
        bt_yes = None
        if forced_clear is False:
            msgbox = QtWidgets.QMessageBox()
            msgbox.setText(_("Are you sure you want to delete the GUI Settings? \n"))
            msgbox.setWindowTitle(_("Clear GUI Settings"))
            msgbox.setWindowIcon(QtGui.QIcon(resource_loc + '/trash32.png'))
            msgbox.setIcon(QtWidgets.QMessageBox.Question)

            bt_yes = msgbox.addButton(_('Yes'), QtWidgets.QMessageBox.YesRole)
            bt_no = msgbox.addButton(_('No'), QtWidgets.QMessageBox.NoRole)

            msgbox.setDefaultButton(bt_no)
            msgbox.exec_()
            response = msgbox.clickedButton()

        if forced_clear is True or response == bt_yes:
            qsettings = QSettings("Open Source", "FlatCAM")
            for key in qsettings.allKeys():
                qsettings.remove(key)
            # This will write the setting to the platform specific storage.
            del qsettings

    def populate_toolbars(self):
        """
        Will populate the App Toolbars with their actions

        :return: None
        """
        self.app.log.debug(" -> Add actions to new Toolbars")

        # ########################################################################
        # ##################### File Toolbar #####################################
        # ########################################################################
        self.file_open_gerber_btn = self.toolbarfile.addAction(
            QtGui.QIcon(self.app.resource_location + '/flatcam_icon32.png'), _("Open Gerber"))
        self.file_open_excellon_btn = self.toolbarfile.addAction(
            QtGui.QIcon(self.app.resource_location + '/drill32.png'), _("Open Excellon"))
        self.toolbarfile.addSeparator()
        self.file_open_btn = self.toolbarfile.addAction(
            QtGui.QIcon(self.app.resource_location + '/folder32.png'), _("Open Project"))
        self.file_save_btn = self.toolbarfile.addAction(
            QtGui.QIcon(self.app.resource_location + '/project_save32.png'), _("Save Project"))

        # ########################################################################
        # ######################### Edit Toolbar #################################
        # ########################################################################
        self.editgeo_btn = self.toolbaredit.addAction(
            QtGui.QIcon(self.app.resource_location + '/edit32.png'), _("Editor"))
        self.update_obj_btn = self.toolbaredit.addAction(
            QtGui.QIcon(self.app.resource_location + '/close_edit_file32.png'),
            _("Save Object and close the Editor")
        )

        self.toolbaredit.addSeparator()
        self.copy_btn = self.toolbaredit.addAction(
            QtGui.QIcon(self.app.resource_location + '/copy_file32.png'), _("Copy"))
        self.delete_btn = self.toolbaredit.addAction(
            QtGui.QIcon(self.app.resource_location + '/trash32.png'), _("Delete"))
        self.toolbaredit.addSeparator()
        self.distance_btn = self.toolbaredit.addAction(
            QtGui.QIcon(self.app.resource_location + '/distance32.png'), _("Distance Tool"))
        self.distance_min_btn = self.toolbaredit.addAction(
            QtGui.QIcon(self.app.resource_location + '/distance_min32.png'), _("Distance Min Tool"))
        self.origin_btn = self.toolbaredit.addAction(
            QtGui.QIcon(self.app.resource_location + '/origin32.png'), _('Set Origin'))
        self.move2origin_btn = self.toolbaredit.addAction(
            QtGui.QIcon(self.app.resource_location + '/origin2_32.png'), _('Move to Origin'))
        self.jmp_btn = self.toolbaredit.addAction(
            QtGui.QIcon(self.app.resource_location + '/jump_to16.png'), _('Jump to Location'))
        self.locate_btn = self.toolbaredit.addAction(
            QtGui.QIcon(self.app.resource_location + '/locate32.png'), _('Locate in Object'))

        # ########################################################################
        # ########################## View Toolbar# ###############################
        # ########################################################################
        self.replot_btn = self.toolbarview.addAction(
            QtGui.QIcon(self.app.resource_location + '/replot32.png'), _("Replot"))
        self.clear_plot_btn = self.toolbarview.addAction(
            QtGui.QIcon(self.app.resource_location + '/clear_plot32.png'), _("Clear Plot"))
        self.zoom_in_btn = self.toolbarview.addAction(
            QtGui.QIcon(self.app.resource_location + '/zoom_in32.png'), _("Zoom In"))
        self.zoom_out_btn = self.toolbarview.addAction(
            QtGui.QIcon(self.app.resource_location + '/zoom_out32.png'), _("Zoom Out"))
        self.zoom_fit_btn = self.toolbarview.addAction(
            QtGui.QIcon(self.app.resource_location + '/zoom_fit32.png'), _("Zoom Fit"))

        # ########################################################################
        # ########################## Shell Toolbar# ##############################
        # ########################################################################
        self.shell_btn = self.toolbarshell.addAction(
            QtGui.QIcon(self.app.resource_location + '/shell32.png'), _("Command Line"))
        self.new_script_btn = self.toolbarshell.addAction(
            QtGui.QIcon(self.app.resource_location + '/script_new24.png'), '%s ...' % _('New Script'))
        self.open_script_btn = self.toolbarshell.addAction(
            QtGui.QIcon(self.app.resource_location + '/open_script32.png'), '%s ...' % _('Open Script'))
        self.run_script_btn = self.toolbarshell.addAction(
            QtGui.QIcon(self.app.resource_location + '/script16.png'), '%s ...' % _('Run Script'))

        # #########################################################################
        # ######################### Tools Toolbar #################################
        # #########################################################################
        self.dblsided_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/doubleside32.png'), _("2-Sided Tool"))
        self.align_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/align32.png'), _("Align Objects Tool"))
        self.extract_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/extract_drill32.png'), _("Extract Drills Tool"))

        self.cutout_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/cut16_bis.png'), _("Cutout Tool"))
        self.ncc_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/ncc16.png'), _("NCC Tool"))
        self.paint_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/paint20_1.png'), _("Paint Tool"))
        self.isolation_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/iso_16.png'), _("Isolation Tool"))
        self.drill_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/drilling_tool32.png'), _("Drilling Tool"))
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
        self.punch_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/punch32.png'), _("Punch Gerber Tool"))
        self.invert_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/invert32.png'), _("Invert Gerber Tool"))
        self.corners_tool_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/corners_32.png'), _("Corner Markers Tool"))
        self.etch_btn = self.toolbartools.addAction(
            QtGui.QIcon(self.app.resource_location + '/etch_32.png'), _("Etch Compensation Tool"))

        # ########################################################################
        # ################### Excellon Editor Toolbar ############################
        # ########################################################################
        self.select_drill_btn = self.exc_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/pointer32.png'), _("Select"))
        self.add_drill_btn = self.exc_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/plus16.png'), _('Add Drill'))
        self.add_drill_array_btn = self.exc_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/addarray16.png'), _('Add Drill Array'))
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

        # ########################################################################
        # ################### Geometry Editor Toolbar ############################
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
            QtGui.QIcon(self.app.resource_location + '/copy32.png'), _("Copy Objects"))
        self.geo_delete_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/trash32.png'), _("Delete Shape"))
        self.geo_transform_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/transform.png'), _("Transformations"))

        self.geo_edit_toolbar.addSeparator()
        self.geo_move_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/move32.png'), _("Move Objects"))

        # ########################################################################
        # ################### Gerber Editor Toolbar ##############################
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

        self.corner_snap_btn.setVisible(False)
        self.snap_magnet.setVisible(False)

        qsettings = QSettings("Open Source", "FlatCAM")
        if qsettings.contains("layout"):
            layout = qsettings.value('layout', type=str)

            # on 'minimal' layout only some toolbars are active
            if layout != 'minimal':
                self.exc_edit_toolbar.setVisible(True)
                self.exc_edit_toolbar.setDisabled(True)
                self.geo_edit_toolbar.setVisible(True)
                self.geo_edit_toolbar.setDisabled(True)
                self.grb_edit_toolbar.setVisible(True)
                self.grb_edit_toolbar.setDisabled(True)

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
        names_list = self.app.collection.get_names()

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
            # CTRL + ALT
            if modifiers == QtCore.Qt.ControlModifier | QtCore.Qt.AltModifier:
                if key == QtCore.Qt.Key_X:
                    self.app.abort_all_tasks()
                    return
            # CTRL + SHIFT
            if modifiers == QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier:
                if key == QtCore.Qt.Key_S:
                    self.app.f_handlers.on_file_saveprojectas()
                    return
            # CTRL
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

                    self.app.on_copy_command()

                # Copy an FlatCAM object
                if key == QtCore.Qt.Key_D:
                    self.app.on_tools_database()

                # Open Excellon file
                if key == QtCore.Qt.Key_E:
                    self.app.f_handlers.on_fileopenexcellon(signal=None)

                # Open Gerber file
                if key == QtCore.Qt.Key_G:
                    widget_name = self.plot_tab_area.currentWidget().objectName()
                    if 'editor' in widget_name.lower():
                        self.app.goto_text_line()
                    else:
                        self.app.f_handlers.on_fileopengerber(signal=None)

                # Distance Tool
                if key == QtCore.Qt.Key_M:
                    self.app.distance_tool.run()

                # Create New Project
                if key == QtCore.Qt.Key_N:
                    self.app.f_handlers.on_file_new_click()

                # Open Project
                if key == QtCore.Qt.Key_O:
                    self.app.f_handlers.on_file_openproject(signal=None)

                # Open Project
                if key == QtCore.Qt.Key_P:
                    self.app.f_handlers.on_file_save_objects_pdf(use_thread=True)

                # PDF Import
                if key == QtCore.Qt.Key_Q:
                    self.app.pdf_tool.run()

                # Save Project
                if key == QtCore.Qt.Key_S:
                    widget_name = self.plot_tab_area.currentWidget().objectName()
                    if widget_name == 'preferences_tab':
                        self.app.preferencesUiManager.on_save_button(save_to_file=False)
                        return

                    if widget_name == 'database_tab':
                        # Tools DB saved, update flag
                        self.app.tools_db_changed_flag = False
                        self.app.tools_db_tab.on_save_tools_db()
                        return

                    self.app.f_handlers.on_file_saveproject()

                # Toggle Plot Area
                if key == QtCore.Qt.Key_F10 or key == 'F10':
                    self.on_toggle_plotarea()

                return
            # SHIFT
            elif modifiers == QtCore.Qt.ShiftModifier:

                # Toggle axis
                if key == QtCore.Qt.Key_A:
                    self.app.plotcanvas.on_toggle_axis()

                # Copy Object Name
                if key == QtCore.Qt.Key_C:
                    self.app.on_copy_name()

                # Toggle Code Editor
                if key == QtCore.Qt.Key_E:
                    self.app.on_toggle_code_editor()

                # Toggle Grid lines
                if key == QtCore.Qt.Key_G:
                    self.app.plotcanvas.on_toggle_grid_lines()
                    return

                # Toggle HUD (Heads-Up Display)
                if key == QtCore.Qt.Key_H:
                    self.app.plotcanvas.on_toggle_hud()
                # Locate in Object
                if key == QtCore.Qt.Key_J:
                    self.app.on_locate(obj=self.app.collection.get_active())

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
                    self.app.f_handlers.on_filerunscript()
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
            # ALT
            elif modifiers == QtCore.Qt.AltModifier:
                # Eanble all plots
                if key == Qt.Key_1:
                    self.app.enable_all_plots()

                # Disable all plots
                if key == Qt.Key_2:
                    self.app.disable_all_plots()

                # Disable all other plots
                if key == Qt.Key_3:
                    self.app.enable_other_plots()

                # Disable all other plots
                if key == Qt.Key_4:
                    self.app.disable_other_plots()

                # Align in Object Tool
                if key == QtCore.Qt.Key_A:
                    self.app.align_objects_tool.run(toggle=True)

                # Calculator Tool
                if key == QtCore.Qt.Key_C:
                    self.app.calculator_tool.run(toggle=True)

                # 2-Sided PCB Tool
                if key == QtCore.Qt.Key_D:
                    self.app.dblsidedtool.run(toggle=True)
                    return

                # Extract Drills  Tool
                if key == QtCore.Qt.Key_E:
                    # self.app.cal_exc_tool.run(toggle=True)
                    self.app.edrills_tool.run(toggle=True)
                    return

                # Fiducials Tool
                if key == QtCore.Qt.Key_F:
                    self.app.fiducial_tool.run(toggle=True)
                    return

                # Punch Gerber Tool
                if key == QtCore.Qt.Key_G:
                    self.app.invert_tool.run(toggle=True)

                # Punch Gerber Tool
                if key == QtCore.Qt.Key_H:
                    self.app.punch_tool.run(toggle=True)

                # Isolation Tool
                if key == QtCore.Qt.Key_I:
                    self.app.isolation_tool.run(toggle=True)

                # Copper Thieving Tool
                if key == QtCore.Qt.Key_J:
                    self.app.copper_thieving_tool.run(toggle=True)
                    return

                # Solder Paste Dispensing Tool
                if key == QtCore.Qt.Key_K:
                    self.app.paste_tool.run(toggle=True)
                    return

                # Film Tool
                if key == QtCore.Qt.Key_L:
                    self.app.film_tool.run(toggle=True)
                    return

                # Corner Markers Tool
                if key == QtCore.Qt.Key_M:
                    self.app.corners_tool.run(toggle=True)
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
                    self.on_fullscreen()
                    return
            # NO MODIFIER
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
                    self.app.on_select_tab('properties')

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
                    # ensure cleanup of the appGUI
                    if active:
                        active.app.on_delete()

                # Escape = Deselect All
                if key == QtCore.Qt.Key_Escape or key == 'Escape':
                    self.app.on_deselect_all()

                    # if in full screen, exit to normal view
                    if self.toggle_fscreen is True:
                        self.on_fullscreen(disable=True)

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
                        QtWidgets.QApplication.processEvents()
                    self.app.collection.update_view()
                    self.app.delete_selection_shape()

                # Select the object in the Tree above the current one
                if key == QtCore.Qt.Key_Up:
                    # make sure it works only for the Project Tab who is an instance of KeySensitiveListView
                    focused_wdg = QtWidgets.QApplication.focusWidget()
                    if isinstance(focused_wdg, KeySensitiveListView):
                        self.app.collection.set_all_inactive()
                        if active is None:
                            return
                        active_name = active.options['name']
                        active_index = names_list.index(active_name)
                        if active_index == 0:
                            self.app.collection.set_active(names_list[-1])
                        else:
                            self.app.collection.set_active(names_list[active_index - 1])

                # Select the object in the Tree below the current one
                if key == QtCore.Qt.Key_Down:
                    # make sure it works only for the Project Tab who is an instance of KeySensitiveListView
                    focused_wdg = QtWidgets.QApplication.focusWidget()
                    if isinstance(focused_wdg, KeySensitiveListView):
                        self.app.collection.set_all_inactive()
                        if active is None:
                            return
                        active_name = active.options['name']
                        active_index = names_list.index(active_name)
                        if active_index == len(names_list) - 1:
                            self.app.collection.set_active(names_list[0])
                        else:
                            self.app.collection.set_active(names_list[active_index + 1])

                # New Geometry
                if key == QtCore.Qt.Key_B:
                    self.app.app_obj.new_gerber_object()

                # New Document Object
                if key == QtCore.Qt.Key_D:
                    self.app.app_obj.new_document_object()

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
                    self.app.app_obj.new_excellon_object()

                # Move tool toggle
                if key == QtCore.Qt.Key_M:
                    self.app.move_tool.toggle()

                # New Geometry
                if key == QtCore.Qt.Key_N:
                    self.app.app_obj.new_geometry_object()

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
                    self.toggle_shell_ui()

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
                    self.app.on_zoom_fit()

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
                    self.on_toggle_notebook()

                return
        elif self.app.call_source == 'geo_editor':
            # CTRL
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
                        messagebox.setIcon(QtWidgets.QMessageBox.Question)

                        messagebox.setStandardButtons(QtWidgets.QMessageBox.Ok)
                        messagebox.setDefaultButton(QtWidgets.QMessageBox.Ok)
                        messagebox.exec_()
                    return
            # SHIFT
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
            # ALT
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
            # NO MODIFIER
            elif modifiers == QtCore.Qt.NoModifier:
                # toggle display of Notebook area
                if key == QtCore.Qt.Key_QuoteLeft or key == '`':
                    self.on_toggle_notebook()

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
                    # self.on_tool_select("select")
                    self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled."))

                    self.app.geo_editor.delete_utility_geometry()

                    self.app.geo_editor.active_tool.clean_up()

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

                # Grid Snap
                if key == QtCore.Qt.Key_G or key == 'G':
                    self.app.ui.grid_snap_btn.trigger()

                    # make sure that the cursor shape is enabled/disabled, too
                    if self.app.geo_editor.options['grid_snap'] is True:
                        self.app.app_cursor.enabled = True
                    else:
                        self.app.app_cursor.enabled = False

                # Corner Snap
                if key == QtCore.Qt.Key_K or key == 'K':
                    self.app.geo_editor.on_corner_snap()

                if key == QtCore.Qt.Key_V or key == 'V':
                    self.app.on_zoom_fit()

                # we do this so we can reuse the following keys while inside a Tool
                # the above keys are general enough so were left outside
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
                            messagebox.setIcon(QtWidgets.QMessageBox.Warning)

                            messagebox.setStandardButtons(QtWidgets.QMessageBox.Ok)
                            messagebox.setDefaultButton(QtWidgets.QMessageBox.Ok)
                            messagebox.exec_()

                    # Paint
                    if key == QtCore.Qt.Key_I or key == 'I':
                        self.app.geo_editor.select_tool('paint')

                    # Jump to coords
                    if key == QtCore.Qt.Key_J or key == 'J':
                        self.app.on_jump_to()

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
                            messagebox.setIcon(QtWidgets.QMessageBox.Warning)

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
                            messagebox.setIcon(QtWidgets.QMessageBox.Warning)

                            messagebox.setStandardButtons(QtWidgets.QMessageBox.Ok)
                            messagebox.setDefaultButton(QtWidgets.QMessageBox.Ok)
                            messagebox.exec_()

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
            # CTRL
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
            # SHIFT
            elif modifiers == QtCore.Qt.ShiftModifier:
                # Run Distance Minimum Tool
                if key == QtCore.Qt.Key_M or key == 'M':
                    self.app.distance_min_tool.run()
                    return
            # ALT
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
            # NO MODIFIER
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
                        self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled. Nothing selected."))
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
                    self.on_toggle_notebook()
                    return

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

                    # Rotate
                    if key == QtCore.Qt.Key_Space or key == 'Space':
                        self.app.grb_editor.transform_tool.on_rotate_key()

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
                            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled. Nothing selected."))
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
                            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled. Nothing selected."))
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

                    # Zoom fit
                    if key == QtCore.Qt.Key_V or key == 'V':
                        self.app.grb_editor.launched_from_shortcuts = True
                        self.app.grb_editor.on_zoom_fit()
                        return

                # Show Shortcut list
                if key == QtCore.Qt.Key_F3 or key == 'F3':
                    self.app.on_shortcut_list()
                    return
        elif self.app.call_source == 'exc_editor':
            # CTRL
            if modifiers == QtCore.Qt.ControlModifier:
                # save (update) the current geometry and return to the App
                if key == QtCore.Qt.Key_S or key == 'S':
                    self.app.editor2object()
                    return

                # toggle the measurement tool
                if key == QtCore.Qt.Key_M or key == 'M':
                    self.app.distance_tool.run()
                    return

                # we do this so we can reuse the following keys while inside a Tool
                # the above keys are general enough so were left outside
                if self.app.exc_editor.active_tool is not None and self.select_drill_btn.isChecked() is False:
                    response = self.app.exc_editor.active_tool.on_key(key=key)
                    if response is not None:
                        self.app.inform.emit(response)
                else:
                    pass

            # SHIFT
            elif modifiers == QtCore.Qt.ShiftModifier:
                # Run Distance Minimum Tool
                if key == QtCore.Qt.Key_M or key == 'M':
                    self.app.distance_min_tool.run()
                    return
            # ALT
            elif modifiers == QtCore.Qt.AltModifier:
                pass
            # NO MODIFIER
            elif modifiers == QtCore.Qt.NoModifier:
                # Abort the current action
                if key == QtCore.Qt.Key_Escape or key == 'Escape':
                    self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled."))

                    self.app.exc_editor.delete_utility_geometry()

                    self.app.exc_editor.active_tool.clean_up()

                    self.app.exc_editor.select_tool('drill_select')
                    return

                # Delete selected object if delete key event comes out of canvas
                if key == 'Delete':
                    self.app.exc_editor.launched_from_shortcuts = True
                    if self.app.exc_editor.selected:
                        self.app.exc_editor.delete_selected()
                        self.app.exc_editor.replot()
                    else:
                        self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled. Nothing selected."))
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
                    self.on_toggle_notebook()
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

                # Corner Snap
                if key == QtCore.Qt.Key_K or key == 'K':
                    self.app.exc_editor.launched_from_shortcuts = True
                    self.app.ui.corner_snap_btn.trigger()
                    return

                # Zoom Fit
                if key == QtCore.Qt.Key_V or key == 'V':
                    self.app.exc_editor.launched_from_shortcuts = True
                    self.app.on_zoom_fit()
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

                # Show Shortcut list
                if key == QtCore.Qt.Key_F3 or key == 'F3':
                    self.app.on_shortcut_list()
                    return

                # Propagate to tool
                # we do this so we can reuse the following keys while inside a Tool
                # the above keys are general enough so were left outside
                if self.app.exc_editor.active_tool is not None and self.select_drill_btn.isChecked() is False:
                    response = self.app.exc_editor.active_tool.on_key(key=key)
                    if response is not None:
                        self.app.inform.emit(response)
                else:
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
                            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled. Nothing selected."))
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

                    # Jump to coords
                    if key == QtCore.Qt.Key_J or key == 'J':
                        self.app.on_jump_to()

                    # Move
                    if key == QtCore.Qt.Key_M or key == 'M':
                        self.app.exc_editor.launched_from_shortcuts = True
                        if self.app.exc_editor.selected:
                            self.app.inform.emit(_("Click on target location ..."))
                            self.app.ui.move_drill_btn.setChecked(True)
                            self.app.exc_editor.on_tool_select('drill_move')
                            self.app.exc_editor.active_tool.set_origin(
                                (self.app.exc_editor.snap_x, self.app.exc_editor.snap_y))
                        else:
                            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled. Nothing selected."))
                        return

                    # Add Array of Slots Hole Tool
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
                        tool_add_popup = FCInputDoubleSpinner(title='%s ...' % _("New Tool"),
                                                              text='%s:' % _('Enter a Tool Diameter'),
                                                              min=0.0000, max=99.9999, decimals=self.decimals)
                        tool_add_popup.set_icon(QtGui.QIcon(self.app.resource_location + '/letter_t_32.png'))

                        val, ok = tool_add_popup.get_value()
                        if ok:
                            self.app.exc_editor.on_tool_add(tooldia=val)
                            formated_val = '%.*f' % (self.decimals, float(val))
                            self.app.inform.emit(
                                '[success] %s: %s %s' % (_("Added new tool with dia"), formated_val, str(self.units))
                            )
                        else:
                            self.app.inform.emit('[WARNING_NOTCL] %s...' % _("Adding Tool cancelled"))
                        return
        elif self.app.call_source == 'gcode_editor':
            # CTRL
            if modifiers == QtCore.Qt.ControlModifier:
                # save (update) the current geometry and return to the App
                if key == QtCore.Qt.Key_S or key == 'S':
                    self.app.editor2object()
                    return
            # SHIFT
            elif modifiers == QtCore.Qt.ShiftModifier:
                pass
            # ALT
            elif modifiers == QtCore.Qt.AltModifier:
                pass
            # NO MODIFIER
            elif modifiers == QtCore.Qt.NoModifier:
                pass
        elif self.app.call_source == 'measurement':
            if modifiers == QtCore.Qt.ControlModifier:
                pass
            elif modifiers == QtCore.Qt.AltModifier:
                pass
            elif modifiers == QtCore.Qt.ShiftModifier:
                pass
            # NO MODIFIER
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
            # CTRL + ALT
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
            # NO MODIFIER
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
            # CTRL + ALT
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
            # NO MODIFIER
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
        elif self.app.call_source == 'geometry':
            if modifiers == QtCore.Qt.ControlModifier:
                pass
            elif modifiers == QtCore.Qt.AltModifier:
                pass
            elif modifiers == QtCore.Qt.ShiftModifier:
                pass
            # NO MODIFIER
            elif modifiers == QtCore.Qt.NoModifier:
                if key == QtCore.Qt.Key_Escape or key == 'Escape':
                    sel_obj = self.app.collection.get_active()
                    assert sel_obj.kind == 'geometry' or sel_obj.kind == 'excellon', \
                        "Expected a Geometry or Excellon Object, got %s" % type(sel_obj)

                    sel_obj.area_disconnect()
                    return

                if key == QtCore.Qt.Key_G or key == 'G':
                    self.app.ui.grid_snap_btn.trigger()
                    return

                # Jump to coords
                if key == QtCore.Qt.Key_J or key == 'J':
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
                    self.app.inform.emit("Cancelled.")
                else:
                    extension = self.filename.lower().rpartition('.')[-1]

                    if extension in self.app.grb_list:
                        self.app.worker_task.emit({'fcn': self.app.f_handlers.open_gerber,
                                                   'params': [self.filename]})
                    else:
                        event.ignore()

                    if extension in self.app.exc_list:
                        self.app.worker_task.emit({'fcn': self.app.f_handlers.open_excellon,
                                                   'params': [self.filename]})
                    else:
                        event.ignore()

                    if extension in self.app.gcode_list:
                        self.app.worker_task.emit({'fcn': self.app.f_handlers.open_gcode,
                                                   'params': [self.filename]})
                    else:
                        event.ignore()

                    if extension in self.app.svg_list:
                        object_type = 'geometry'
                        self.app.worker_task.emit({'fcn': self.app.f_handlers.import_svg,
                                                   'params': [self.filename, object_type, None]})

                    if extension in self.app.dxf_list:
                        object_type = 'geometry'
                        self.app.worker_task.emit({'fcn': self.app.f_handlers.import_dxf,
                                                   'params': [self.filename, object_type, None]})

                    if extension in self.app.pdf_list:
                        self.app.pdf_tool.periodic_check(1000)
                        self.app.worker_task.emit({'fcn': self.app.pdf_tool.open_pdf,
                                                   'params': [self.filename]})

                    if extension in self.app.prj_list:
                        # self.app.open_project() is not Thread Safe
                        self.app.f_handlers.open_project(self.filename)

                    if extension in self.app.conf_list:
                        self.app.f_handlers.open_config_file(self.filename)
                    else:
                        event.ignore()
        else:
            event.ignore()

    def closeEvent(self, event):
        if self.app.save_in_progress:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Application is saving the project. Please wait ..."))
        else:
            grect = self.geometry()

            # self.splitter.sizes()[0] is actually the size of the "notebook"
            if not self.isMaximized():
                self.geom_update.emit(grect.x(), grect.y(), grect.width(), grect.height(), self.splitter.sizes()[0])

            self.final_save.emit()
        event.ignore()

    def on_fullscreen(self, disable=False):
        """

        :param disable:
        :return:
        """
        flags = self.windowFlags()
        if self.toggle_fscreen is False and disable is False:
            # self.ui.showFullScreen()
            self.setWindowFlags(flags | Qt.FramelessWindowHint)
            a = self.geometry()
            self.x_pos = a.x()
            self.y_pos = a.y()
            self.width = a.width()
            self.height = a.height()
            self.titlebar_height = self.app.qapp.style().pixelMetric(QtWidgets.QStyle.PM_TitleBarHeight)

            # set new geometry to full desktop rect
            # Subtracting and adding the pixels below it's hack to bypass a bug in Qt5 and OpenGL that made that a
            # window drawn with OpenGL in fullscreen will not show any other windows on top which means that menus and
            # everything else will not work without this hack. This happen in Windows.
            # https://bugreports.qt.io/browse/QTBUG-41309
            desktop = self.app.qapp.desktop()
            screen = desktop.screenNumber(QtGui.QCursor.pos())

            rec = desktop.screenGeometry(screen)
            x = rec.x() - 1
            y = rec.y() - 1
            h = rec.height() + 2
            w = rec.width() + 2

            self.setGeometry(x, y, w, h)
            self.show()

            # hide all Toolbars
            for tb in self.findChildren(QtWidgets.QToolBar):
                tb.setVisible(False)

            self.coords_toolbar.setVisible(self.app.defaults["global_coordsbar_show"])
            self.delta_coords_toolbar.setVisible(self.app.defaults["global_delta_coordsbar_show"])
            self.grid_toolbar.setVisible(self.app.defaults["global_gridbar_show"])
            self.status_toolbar.setVisible(self.app.defaults["global_statusbar_show"])

            self.splitter.setSizes([0, 1])
            self.toggle_fscreen = True
        elif self.toggle_fscreen is True or disable is True:
            self.setWindowFlags(flags & ~Qt.FramelessWindowHint)
            # the additions are made to account for the pixels we subtracted/added above in the (x, y, h, w)
            self.setGeometry(self.x_pos+1, self.y_pos+self.titlebar_height+4, self.width, self.height)
            self.showNormal()
            self.restore_toolbar_view()
            self.toggle_fscreen = False

    def on_toggle_plotarea(self):
        """

        :return:
        """
        try:
            name = self.plot_tab_area.widget(0).objectName()
        except AttributeError:
            self.plot_tab_area.addTab(self.plot_tab, _("Plot Area"))
            # remove the close button from the Plot Area tab (first tab index = 0) as this one will always be ON
            self.plot_tab_area.protectTab(0)
            return

        if name != 'plotarea_tab':
            self.plot_tab_area.insertTab(0, self.plot_tab, _("Plot Area"))
            # remove the close button from the Plot Area tab (first tab index = 0) as this one will always be ON
            self.plot_tab_area.protectTab(0)
        else:
            self.plot_tab_area.closeTab(0)

    def on_toggle_notebook(self):
        """

        :return:
        """
        if self.splitter.sizes()[0] == 0:
            self.splitter.setSizes([1, 1])
            self.menu_toggle_nb.setChecked(True)
        else:
            self.splitter.setSizes([0, 1])
            self.menu_toggle_nb.setChecked(False)

    def on_toggle_grid(self):
        """

        :return:
        """
        self.grid_snap_btn.trigger()

    def toggle_shell_ui(self):
        """
        Toggle shell dock: if is visible close it, if it is closed then open it

        :return: None
        """

        if self.shell_dock.isVisible():
            self.shell_dock.hide()
            self.app.plotcanvas.native.setFocus()
        else:
            self.shell_dock.show()

            # I want to take the focus and give it to the Tcl Shell when the Tcl Shell is run
            # self.shell._edit.setFocus()
            QtCore.QTimer.singleShot(0, lambda: self.shell_dock.widget()._edit.setFocus())

            # HACK - simulate a mouse click - alternative
            # no_km = QtCore.Qt.KeyboardModifier(QtCore.Qt.NoModifier)    # no KB modifier
            # pos = QtCore.QPoint((self.shell._edit.width() - 40), (self.shell._edit.height() - 2))
            # e = QtGui.QMouseEvent(QtCore.QEvent.MouseButtonPress, pos, QtCore.Qt.LeftButton, QtCore.Qt.LeftButton,
            #                       no_km)
            # QtWidgets.qApp.sendEvent(self.shell._edit, e)
            # f = QtGui.QMouseEvent(QtCore.QEvent.MouseButtonRelease, pos, QtCore.Qt.LeftButton, QtCore.Qt.LeftButton,
            #                       no_km)
            # QtWidgets.qApp.sendEvent(self.shell._edit, f)

    def on_shelldock_toggled(self, visibility):
        if visibility is True:
            self.shell_status_label.setStyleSheet("""
                                                  QLabel
                                                  {
                                                      color: black;
                                                      background-color: lightcoral;
                                                  }
                                                  """)
            self.app.inform[str, bool].emit(_("Shell enabled."), False)
        else:
            self.shell_status_label.setStyleSheet("")
            self.app.inform[str, bool].emit(_("Shell disabled."), False)


class ShortcutsTab(QtWidgets.QWidget):

    def __init__(self):
        super(ShortcutsTab, self).__init__()

        self.sh_tab_layout = QtWidgets.QVBoxLayout()
        self.sh_tab_layout.setContentsMargins(2, 2, 2, 2)
        self.setLayout(self.sh_tab_layout)

        self.sh_hlay = QtWidgets.QHBoxLayout()

        self.sh_title = QtWidgets.QTextEdit('<b>%s</b>' % _('Shortcut Key List'))
        self.sh_title.setTextInteractionFlags(QtCore.Qt.NoTextInteraction)
        self.sh_title.setFrameStyle(QtWidgets.QFrame.NoFrame)
        self.sh_title.setMaximumHeight(30)

        font = self.sh_title.font()
        font.setPointSize(12)
        self.sh_title.setFont(font)

        self.sh_tab_layout.addWidget(self.sh_title)
        self.sh_tab_layout.addLayout(self.sh_hlay)

        self.app_sh_msg = (
                '''<b>%s</b><br>
            <table border="0" cellpadding="0" cellspacing="0" style="width:283px">
                <tbody>
                    <tr height="20">
                        <td height="20" width="89"><strong>%s</strong></td>
                        <td width="194"><span style="color:#006400"><strong>&nbsp;%s</strong></span></td>
                    </tr>
                    <tr height="20">
                        <td height="20">&nbsp;</td>
                        <td>&nbsp;</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20">&nbsp;</td>
                        <td>&nbsp;</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong%s>T</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>&#39;%s&#39;</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>&#39;%s&#39;</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20">&nbsp;</td>
                        <td>&nbsp;</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>                   
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr> 
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20">&nbsp;</td>
                        <td>&nbsp;</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20">&nbsp;</td>
                        <td>&nbsp;</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20">&nbsp;</td>
                        <td>&nbsp;</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20">&nbsp;</td>
                        <td>&nbsp;</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20">&nbsp;</td>
                        <td>&nbsp;</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>'%s'</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                </tbody>
            </table>
            ''' %
                (
                    _("General Shortcut list"),
                    _('F3'), _("SHOW SHORTCUT LIST"),
                    _('1'), _("Switch to Project Tab"),
                    _('2'), _("Switch to Selected Tab"),
                    _('3'), _("Switch to Tool Tab"),
                    _('B'), _("New Gerber"),
                    _('E'), _("Edit Object (if selected)"),
                    _('G'), _("Grid On/Off"),
                    _('J'), _("Jump to Coordinates"),
                    _('L'), _("New Excellon"),
                    _('M'), _("Move Obj"),
                    _('N'), _("New Geometry"),
                    _('O'), _("Set Origin"),
                    _('Q'), _("Change Units"),
                    _('P'), _("Open Properties Tool"),
                    _('R'), _("Rotate by 90 degree CW"),
                    _('S'), _("Shell Toggle"),
                    _('T'), _("Add a Tool (when in Geometry Selected Tab or in Tools NCC or Tools Paint)"),
                    _('V'), _("Zoom Fit"),
                    _('X'), _("Flip on X_axis"),
                    _('Y'), _("Flip on Y_axis"),
                    _('-'), _("Zoom Out"),
                    _('='), _("Zoom In"),

                    # CTRL section
                    _('Ctrl+A'), _("Select All"),
                    _('Ctrl+C'), _("Copy Obj"),
                    _('Ctrl+D'), _("Open Tools Database"),
                    _('Ctrl+E'), _("Open Excellon File"),
                    _('Ctrl+G'), _("Open Gerber File"),
                    _('Ctrl+M'), _("Distance Tool"),
                    _('Ctrl+N'), _("New Project"),
                    _('Ctrl+O'), _("Open Project"),
                    _('Ctrl+P'), _("Print (PDF)"),
                    _('Ctrl+Q'), _("PDF Import Tool"),
                    _('Ctrl+S'), _("Save Project"),
                    _('Ctrl+F10'), _("Toggle Plot Area"),

                    # SHIFT section
                    _('Shift+A'), _("Toggle the axis"),
                    _('Shift+C'), _("Copy Obj_Name"),
                    _('Shift+E'), _("Toggle Code Editor"),
                    _('Shift+G'), _("Toggle Grid Lines"),
                    _('Shift+H'), _("Toggle HUD"),
                    _('Shift+J'), _("Locate in Object"),
                    _('Shift+M'), _("Distance Minimum Tool"),
                    _('Shift+P'), _("Open Preferences Window"),
                    _('Shift+R'), _("Rotate by 90 degree CCW"),
                    _('Shift+S'), _("Run a Script"),
                    _('Shift+W'), _("Toggle the workspace"),
                    _('Shift+X'), _("Skew on X axis"),
                    _('Shift+Y'), _("Skew on Y axis"),

                    # ALT section
                    _('Alt+A'), _("Align Objects Tool"),
                    _('Alt+C'), _("Calculators Tool"),
                    _('Alt+D'), _("2-Sided PCB Tool"),
                    _('Alt+E'), _("Extract Drills Tool"),
                    _('Alt+F'), _("Fiducials Tool"),
                    _('Alt+G'), _("Invert Gerber Tool"),
                    _('Alt+H'), _("Punch Gerber Tool"),
                    _('Alt+I'), _("Isolation Tool"),
                    _('Alt+J'), _("Copper Thieving Tool"),
                    _('Alt+K'), _("Solder Paste Dispensing Tool"),
                    _('Alt+L'), _("Film PCB Tool"),
                    _('Alt+M'), _("Corner Markers Tool"),
                    _('Alt+N'), _("Non-Copper Clearing Tool"),
                    _('Alt+O'), _("Optimal Tool"),
                    _('Alt+P'), _("Paint Area Tool"),
                    _('Alt+Q'), _("QRCode Tool"),
                    _('Alt+R'), _("Rules Check Tool"),
                    _('Alt+S'), _("View File Source"),
                    _('Alt+T'), _("Transformations Tool"),
                    _('Alt+W'), _("Subtract Tool"),
                    _('Alt+X'), _("Cutout PCB Tool"),
                    _('Alt+Z'), _("Panelize PCB"),
                    _('Alt+1'), _("Enable all"),
                    _('Alt+2'), _("Disable all"),
                    _('Alt+3'), _("Enable Non-selected Objects"),
                    _('Alt+4'), _("Disable Non-selected Objects"),
                    _('Alt+F10'), _("Toggle Full Screen"),

                    # CTRL + ALT section
                    _('Ctrl+Alt+X'), _("Abort current task (gracefully)"),

                    # CTRL + SHIFT section
                    _('Ctrl+Shift+S'), _("Save Project As"),
                    _('Ctrl+Shift+V'), _("Paste Special. "
                                         "Will convert a Windows path style to the one required in Tcl Shell"),

                    # F keys section
                    _('F1'), _("Open Online Manual"),
                    _('F4'), _("Open Online Tutorials"),
                    _('F5'), _("Refresh Plots"),
                    _('Del'), _("Delete Object"),
                    _('Del'), _("Alternate: Delete Tool"),
                    _('`'), _("(left to Key_1)Toggle Notebook Area (Left Side)"),
                    _('Space'), _("En(Dis)able Obj Plot"),
                    _('Esc'), _("Deselects all objects")
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

        # GEOMETRY EDITOR SHORTCUT LIST
        geo_sh_messages = """
        <strong><span style="color:#0000ff">%s</span></strong><br>
        <table border="0" cellpadding="0" cellspacing="0" style="width:283px">
                <tbody>
                    <tr height="20">
                        <td height="20" width="89"><strong>%s</strong></td>
                        <td width="194">&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20">&nbsp;</td>
                        <td>&nbsp;</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20">&nbsp;</td>
                        <td>&nbsp;</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20">&nbsp;</td>
                        <td>&nbsp;</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20">&nbsp;</td>
                        <td>&nbsp;</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                    <tr height="20">
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                </tbody>
            </table>
            <br>
        """ % (
            _("GEOMETRY EDITOR"),
            _('A'), _("Draw an Arc"),
            _('B'), _("Buffer Tool"),
            _('C'), _("Copy Geo Item"),
            _('D'), _("Within Add Arc will toogle the ARC direction: CW or CCW"),
            _('E'), _("Polygon Intersection Tool"),
            _('I'), _("Geo Paint Tool"),
            _('J'), _("Jump to Location (x, y)"),
            _('K'), _("Toggle Corner Snap"),
            _('M'), _("Move Geo Item"),
            _('M'), _("Within Add Arc will cycle through the ARC modes"),
            _('N'), _("Draw a Polygon"),
            _('O'), _("Draw a Circle"),
            _('P'), _("Draw a Path"),
            _('R'), _("Draw Rectangle"),
            _('S'), _("Polygon Subtraction Tool"),
            _('T'), _("Add Text Tool"),
            _('U'), _("Polygon Union Tool"),
            _('X'), _("Flip shape on X axis"),
            _('Y'), _("Flip shape on Y axis"),
            _('Shift+M'), _("Distance Minimum Tool"),
            _('Shift+X'), _("Skew shape on X axis"),
            _('Shift+Y'), _("Skew shape on Y axis"),
            _('Alt+R'), _("Editor Transformation Tool"),
            _('Alt+X'), _("Offset shape on X axis"),
            _('Alt+Y'), _("Offset shape on Y axis"),
            _('Ctrl+M'), _("Distance Tool"),
            _('Ctrl+S'), _("Save Object and Exit Editor"),
            _('Ctrl+X'), _("Polygon Cut Tool"),
            _('Space'), _("Rotate Geometry"),
            _('ENTER'), _("Finish drawing for certain tools"),
            _('Esc'), _("Abort and return to Select"),
            _('Del'), _("Delete Shape")
        )

        # EXCELLON EDITOR SHORTCUT LIST
        exc_sh_messages = """
        <br>
        <strong><span style="color:#ff0000">%s</span></strong><br>
        <table border="0" cellpadding="0" cellspacing="0" style="width:283px">
            <tbody>
                <tr height="20">
                    <td height="20" width="89"><strong>%s</strong></td>
                    <td width="194">&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>%s</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>%s</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>%s</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>%s</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20" width="89"><strong>%s</strong></td>
                    <td width="194">&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>%s</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>%s</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20" width="89"><strong>%s</strong></td>
                    <td width="194">&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20">&nbsp;</td>
                    <td>&nbsp;</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>%s</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20">&nbsp;</td>
                    <td>&nbsp;</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>%s</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>%s</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>%s</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>%s</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20">&nbsp;</td>
                    <td>&nbsp;</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>%s</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>%s</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
            </tbody>
        </table>
        <br>
        """ % (
            _("EXCELLON EDITOR"),
            _('A'), _("Add Drill Array"),
            _('C'), _("Copy Drill"),
            _('D'), _("Add Drill"),
            _('J'), _("Jump to Location (x, y)"),
            _('M'), _("Move Drill"),
            _('Q'), _("Add Slot Array"),
            _('R'), _("Resize Drill"),
            _('T'), _("Add a new Tool"),
            _('W'), _("Add Slot"),
            _('Shift+M'), _("Distance Minimum Tool"),
            _('Del'), _("Delete Drill"),
            _('Del'), _("Alternate: Delete Tool"),
            _('Esc'), _("Abort and return to Select"),
            _('Space'), _("Toggle Slot direction"),
            _('Ctrl+S'), _("Save Object and Exit Editor"),
            _('Ctrl+Space'), _("Toggle array direction")
        )

        # GERBER EDITOR SHORTCUT LIST
        grb_sh_messages = """
        <br>
        <strong><span style="color:#00ff00">%s</span></strong><br>
        <table border="0" cellpadding="0" cellspacing="0" style="width:283px">
            <tbody>
                <tr height="20">
                    <td height="20" width="89"><strong>%s</strong></td>
                    <td width="194">&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>%s</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>%s</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>%s</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>%s</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>%s</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>%s</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>%s</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>%s</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>%s</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>%s</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>%s</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>%s</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20">&nbsp;</td>
                    <td>&nbsp;</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>%s</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>%s</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>%s</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                </tr>
                <tr height="20">
                    <td height="20"><strong>%s</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20">&nbsp;</td>
                    <td>&nbsp;</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>%s</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20">&nbsp;</td>
                    <td>&nbsp;</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>%s</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>%s</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20">&nbsp;</td>
                    <td>&nbsp;</td>
                </tr>
                 <tr height="20">
                    <td height="20"><strong>%s</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>%s</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
                <tr height="20">
                    <td height="20"><strong>%s</strong></td>
                    <td>&nbsp;%s</td>
                </tr>
            </tbody>
        </table>
        <br>
        """ % (
            _("GERBER EDITOR"),
            _('A'), _("Add Pad Array"),
            _('B'), _("Buffer"),
            _('C'), _("Copy"),
            _('D'), _("Add Disc"),
            _('E'), _("Add SemiDisc"),
            _('J'), _("Jump to Location (x, y)"),
            _('M'), _("Move"),
            _('N'), _("Add Region"),
            _('P'), _("Add Pad"),
            _('R'), _("Within Track & Region Tools will cycle in REVERSE the bend modes"),
            _('S'), _("Scale"),
            _('T'), _("Add Track"),
            _('T'), _("Within Track & Region Tools will cycle FORWARD the bend modes"),
            _('Del'), _("Delete"),
            _('Del'), _("Alternate: Delete Apertures"),
            _('Esc'), _("Abort and return to Select"),
            _('Space'), _("Toggle array direction"),
            _('Shift+M'), _("Distance Minimum Tool"),
            _('Ctrl+E'), _("Eraser Tool"),
            _('Ctrl+S'), _("Save Object and Exit Editor"),
            _('Alt+A'), _("Mark Area Tool"),
            _('Alt+N'), _("Poligonize Tool"),
            _('Alt+R'), _("Transformation Tool")
        )

        self.editor_sh_msg = editor_title + geo_sh_messages + grb_sh_messages + exc_sh_messages

        self.sh_editor = QtWidgets.QTextEdit()
        self.sh_editor.setTextInteractionFlags(QtCore.Qt.NoTextInteraction)
        self.sh_editor.setText(self.editor_sh_msg)
        self.sh_editor.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.sh_hlay.addWidget(self.sh_editor)

# end of file
