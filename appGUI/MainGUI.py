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
from PyQt6.QtCore import QSettings

import platform

from appGUI.GUIElements import *

from appGUI.preferences.cncjob.CNCJobPreferencesUI import CNCJobPreferencesUI
from appGUI.preferences.excellon.ExcellonPreferencesUI import ExcellonPreferencesUI
from appGUI.preferences.general.GeneralPreferencesUI import GeneralPreferencesUI
from appGUI.preferences.geometry.GeometryPreferencesUI import GeometryPreferencesUI
from appGUI.preferences.gerber.GerberPreferencesUI import GerberPreferencesUI
from appEditors.AppGeoEditor import FCShapeTool

from matplotlib.backend_bases import KeyEvent as mpl_key_event

import webbrowser

from appGUI.preferences.tools.PluginsPreferencesUI import PluginsPreferencesUI
from appGUI.preferences.tools.Plugins2PreferencesUI import Plugins2PreferencesUI
from appGUI.preferences.tools.PluginsEngravingPreferencesUI import PluginsEngravingPreferencesUI

from appGUI.preferences.utilities.UtilPreferencesUI import UtilPreferencesUI
from appObjects.ObjectCollection import EventSensitiveListView

import subprocess
import os
import sys
import gettext
import appTranslation as fcTranslate
import builtins

import darkdetect

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class MainGUI(QtWidgets.QMainWindow):
    final_save = QtCore.pyqtSignal(name='saveBeforeExit')
    # screenChanged = QtCore.pyqtSignal(QtGui.QScreen, QtGui.QScreen)

    # Mapping of colors used for text on Light theme to
    # similar colors safe for use on Dark theme
    # 'input_color': (light_color, dark_color),
    theme_safe_colors = {
        "blue": "#1F80FF",
        "brown": "#CC9966",
        "darkgreen": "#008015",
        "darkorange": "darkorange",
        "green": "#00CC22",
        "indigo": "#9457EB",
        "magenta": "magenta",
        "orange": "orange",
        "purple": "#B284BE",
        "red": "salmon",
        "teal": "teal",
        "tomato": "tomato",
    }

    def theme_safe_color(self, color):
        """
        Some colors do not work well with light or dark backgrounds making them unreadable in the wrong
        theme. For an approved color value this will return a similar color better suited for the current theme.

        :param color: color to be replaced
        :return: similar color better suited for dark or light theme
        """

        if color in self.theme_safe_colors:
            if self.app.options['global_theme'] in ['default', 'light']:
                return color
            else:
                return self.theme_safe_colors[color]
        else:
            return color

    # https://www.w3.org/TR/SVG11/types.html#ColorKeywords
    def __init__(self, app):
        super(MainGUI, self).__init__()
        # self.setWindowFlags(Qt.WindowType.FramelessWindowHint)

        self.app = app
        self.decimals = self.app.decimals

        FCLabel.patching_text_color = self.theme_safe_color
        FCButton.patching_text_color = self.theme_safe_color

        # self.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint)

        # Divine icon pack by Ipapun @ finicons.com

        # #######################################################################
        # ############ BUILDING THE GUI IS EXECUTED HERE ########################
        # #######################################################################

        # #######################################################################
        # ###################### Menu BUILDING ##################################
        # #######################################################################
        self.menu = self.menuBar()

        self.menu_toggle_nb = QtGui.QAction(
            QtGui.QIcon(self.app.resource_location + '/notebook32.png'), _("Toggle Panel"))
        self.menu_toggle_nb.setToolTip(
            _("Toggle Panel")
        )
        # self.menu_toggle_nb = QtGui.QAction("NB")

        self.menu_toggle_nb.setCheckable(True)
        self.menu.addAction(self.menu_toggle_nb)

        # ########################################################################
        # ########################## File # ######################################
        # ########################################################################
        self.menufile = self.menu.addMenu(_('File'))
        self.menufile.setToolTipsVisible(True)

        # New Project
        self.menufilenewproject = QtGui.QAction(QtGui.QIcon(self.app.resource_location + '/file16.png'),
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
            QtGui.QIcon(self.app.resource_location + '/folder32.png'), '%s' % _('Open'))
        self.menufile_open.setToolTipsVisible(True)

        # Open Project ...
        self.menufileopenproject = QtGui.QAction(
            QtGui.QIcon(self.app.resource_location + '/folder16.png'), '%s...\t%s' % (_('Open Project'), _('Ctrl+O')),
            self)
        self.menufile_open.addAction(self.menufileopenproject)
        self.menufile_open.addSeparator()

        # Open Gerber ...
        self.menufileopengerber = QtGui.QAction(QtGui.QIcon(self.app.resource_location + '/open_gerber32.png'),
                                                '%s...\t%s' % (_('Open Gerber'), _('Ctrl+G')), self)
        self.menufile_open.addAction(self.menufileopengerber)

        # Open Excellon ...
        self.menufileopenexcellon = QtGui.QAction(QtGui.QIcon(self.app.resource_location + '/open_excellon32.png'),
                                                  '%s...\t%s' % (_('Open Excellon'), _('Ctrl+E')), self)
        self.menufile_open.addAction(self.menufileopenexcellon)

        # Open G-Code ...
        self.menufileopengcode = QtGui.QAction(
            QtGui.QIcon(self.app.resource_location + '/code.png'), '%s...\t%s' % (_('Open G-Code'), ''), self)
        self.menufile_open.addAction(self.menufileopengcode)

        self.menufile_open.addSeparator()

        # Open Config File...
        self.menufileopenconfig = QtGui.QAction(
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
        self.menufilesaveproject = QtGui.QAction(
            QtGui.QIcon(self.app.resource_location + '/floppy16.png'), '%s...\t%s' % (_('Save Project'), _('Ctrl+S')),
            self)
        self.menufile_save.addAction(self.menufilesaveproject)

        # Save Project As ...
        self.menufilesaveprojectas = QtGui.QAction(QtGui.QIcon(self.app.resource_location + '/floppy16.png'),
                                                   '%s...\t%s' % (_('Save Project As'), _('Ctrl+Shift+S')), self)
        self.menufile_save.addAction(self.menufilesaveprojectas)

        # Save Project Copy ...
        # self.menufilesaveprojectcopy = QtGui.QAction(
        #     QtGui.QIcon(self.app.resource_location + '/floppy16.png'), _('Save Project Copy ...'), self)
        # self.menufile_save.addAction(self.menufilesaveprojectcopy)

        self.menufile_save.addSeparator()

        # Separator
        self.menufile.addSeparator()

        # Scripting
        self.menufile_scripting = self.menufile.addMenu(
            QtGui.QIcon(self.app.resource_location + '/script16.png'), _('Scripting'))
        self.menufile_scripting.setToolTipsVisible(True)

        self.menufilenewscript = QtGui.QAction(QtGui.QIcon(self.app.resource_location + '/script_new16.png'),
                                               '%s...\t%s' % (_('New Script'), ''), self)
        self.menufileopenscript = QtGui.QAction(QtGui.QIcon(self.app.resource_location + '/open_script32.png'),
                                                '%s...\t%s' % (_('Open Script'), ''), self)
        self.menufileopenscriptexample = QtGui.QAction(
            QtGui.QIcon(self.app.resource_location + '/open_script32.png'),
            '%s...\t%s' % (_('Open Example'), ''), self)
        self.menufilerunscript = QtGui.QAction(
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
        self.menufileimportsvg = QtGui.QAction(
            QtGui.QIcon(self.app.resource_location + '/svg16.png'),
            '%s...\t%s' % (_('SVG as Geometry Object'), ''), self)
        self.menufileimport.addAction(self.menufileimportsvg)
        self.menufileimportsvg_as_gerber = QtGui.QAction(
            QtGui.QIcon(self.app.resource_location + '/svg16.png'),
            '%s...\t%s' % (_('SVG as Gerber Object'), ''), self)
        self.menufileimport.addAction(self.menufileimportsvg_as_gerber)
        self.menufileimport.addSeparator()

        self.menufileimportdxf = QtGui.QAction(
            QtGui.QIcon(self.app.resource_location + '/dxf16.png'),
            '%s...\t%s' % (_('DXF as Geometry Object'), ''), self)
        self.menufileimport.addAction(self.menufileimportdxf)
        self.menufileimportdxf_as_gerber = QtGui.QAction(
            QtGui.QIcon(self.app.resource_location + '/dxf16.png'),
            '%s...\t%s' % (_('DXF as Gerber Object'), ''), self)
        self.menufileimport.addAction(self.menufileimportdxf_as_gerber)
        self.menufileimport.addSeparator()
        self.menufileimport_hpgl2_as_geo = QtGui.QAction(
            QtGui.QIcon(self.app.resource_location + '/dxf16.png'),
            '%s...\t%s' % (_('HPGL2 as Geometry Object'), ''), self)
        self.menufileimport.addAction(self.menufileimport_hpgl2_as_geo)
        self.menufileimport.addSeparator()

        # Export ...
        self.menufileexport = self.menufile.addMenu(
            QtGui.QIcon(self.app.resource_location + '/export.png'), _('Export'))
        self.menufileexport.setToolTipsVisible(True)

        self.menufileexportsvg = QtGui.QAction(
            QtGui.QIcon(self.app.resource_location + '/export.png'),
            '%s...\t%s' % (_('Export SVG'), ''), self)
        self.menufileexport.addAction(self.menufileexportsvg)

        self.menufileexportdxf = QtGui.QAction(
            QtGui.QIcon(self.app.resource_location + '/export.png'),
            '%s...\t%s' % (_('Export DXF'), ''), self)
        self.menufileexport.addAction(self.menufileexportdxf)

        self.menufileexport.addSeparator()

        self.menufileexportpng = QtGui.QAction(
            QtGui.QIcon(self.app.resource_location + '/export_png32.png'),
            '%s...\t%s' % (_('Export PNG'), ''), self)
        self.menufileexportpng.setToolTip(
            _("Will export an image in PNG format,\n"
              "the saved image will contain the visual \n"
              "information currently in FlatCAM Plot Area.")
        )
        self.menufileexport.addAction(self.menufileexportpng)

        self.menufileexport.addSeparator()

        self.menufileexportexcellon = QtGui.QAction(
            QtGui.QIcon(self.app.resource_location + '/drill32.png'),
            '%s...\t%s' % (_('Export Excellon'), ''), self)
        self.menufileexportexcellon.setToolTip(
            _("Will export an Excellon Object as Excellon file,\n"
              "the coordinates format, the file units and zeros\n"
              "are set in Preferences -> Excellon Export.")
        )
        self.menufileexport.addAction(self.menufileexportexcellon)

        self.menufileexportgerber = QtGui.QAction(
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
        self.menufileimportpref = QtGui.QAction(
            QtGui.QIcon(self.app.resource_location + '/backup_import24.png'),
            '%s...\t%s' % (_('Import Preferences from file'), ''), self
        )
        self.menufile_backup.addAction(self.menufileimportpref)

        # Export Preferences
        self.menufileexportpref = QtGui.QAction(
            QtGui.QIcon(self.app.resource_location + '/backup_export24.png'),
            '%s...\t%s' % (_('Export Preferences to file'), ''), self)
        self.menufile_backup.addAction(self.menufileexportpref)

        # Separator
        self.menufile_backup.addSeparator()

        # Save Defaults
        self.menufilesavedefaults = QtGui.QAction(
            QtGui.QIcon(self.app.resource_location + '/defaults.png'),
            '%s\t%s' % (_('Save Preferences'), ''), self)
        self.menufile_backup.addAction(self.menufilesavedefaults)

        # Separator
        self.menufile.addSeparator()
        self.menufile_print = QtGui.QAction(
            QtGui.QIcon(self.app.resource_location + '/printer32.png'),
            '%s\t%s' % (_('Print (PDF)'), _('Ctrl+P')))
        self.menufile.addAction(self.menufile_print)

        # Separator
        self.menufile.addSeparator()

        # Quit
        self.menufile_exit = QtGui.QAction(
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
        self.menuedit_numeric_move = self.menuedit.addAction(
            QtGui.QIcon(self.app.resource_location + '/move32_bis.png'),
            '%s\t%s' % (_('Num Move'), ''))
        self.menueditorigin = self.menuedit.addAction(
            QtGui.QIcon(self.app.resource_location + '/origin16.png'),
            '%s\t%s' % (_('Set Origin'), _('O')))
        self.menuedit_move2origin = self.menuedit.addAction(
            QtGui.QIcon(self.app.resource_location + '/move2origin32.png'),
            '%s\t%s' % (_('Move to Origin'), _('Shift+O')))
        self.menuedit_center_in_origin = self.menuedit.addAction(
            QtGui.QIcon(self.app.resource_location + '/custom_origin32.png'),
            '%s\t%s' % (_('Custom Origin'), ''))

        self.menueditjump = self.menuedit.addAction(
            QtGui.QIcon(self.app.resource_location + '/jump_to32.png'),
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

        # #############################################################################################################
        # ########################################### OPTIONS # ######################################################
        # #############################################################################################################

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

        # ########################### Options ->Experimental ##########################################################
        self.menuoptions_experimental = self.menuoptions.addMenu(
            QtGui.QIcon(self.app.resource_location + '/experiment32.png'), _('Experimental'))

        self.menuoptions_experimental_3D_area = self.menuoptions_experimental.addAction(
            QtGui.QIcon(self.app.resource_location + '/3D_area32.png'),
            '%s\t%s' % (_('3D Area'), ''))
        # Separator
        self.menuoptions.addSeparator()

        # #############################################################################################################
        # ################################## View # ###################################################################
        # #############################################################################################################
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

        self.menuview.addSeparator()
        self.menuview_show_log = self.menuview.addAction(
            QtGui.QIcon(self.app.resource_location + '/log32.png'),
            '%s\t%s' % (_("Error Log"), ''))

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
        # ########################## Plugins # ######################################
        # ########################################################################
        self.menu_plugins = QtWidgets.QMenu(_('Plugins'))
        self.menu_plugins_action = self.menu.addMenu(self.menu_plugins)
        self.menu_plugins_shell = self.menu_plugins.addAction(
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

        self.menuhelp_donate = self.menuhelp.addAction(
            QtGui.QIcon(self.app.resource_location + '/paypal32.png'),
            '%s\t%s' % (_('Donate'), ''))

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
        self.geo_subtract_alt_menuitem = self.geo_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/subtract16.png'),
            '%s\t%s' % (_('Alt Subtraction'), '')
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
            '%s\t%s' % (_("Delete"), _('DEL'))
        )
        self.geo_editor_menu.addSeparator()
        self.geo_move_menuitem = self.geo_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/move32.png'),
            '%s\t%s' % (_("Move"), _('M')))
        self.geo_buffer_menuitem = self.geo_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/buffer16.png'),
            '%s\t%s' % (_("Buffer"), _('B'))
        )
        self.geo_simplification_menuitem = self.geo_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/simplify32.png'),
            '%s\t%s' % (_("Simplification"), '')
        )
        self.geo_paint_menuitem = self.geo_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/paint32.png'),
            '%s\t%s' % (_("Paint"), _('I'))
        )
        self.geo_transform_menuitem = self.geo_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/transform.png'),
            '%s\t%s' % (_("Transformation"), _('Alt+R'))
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
            '%s\t%s' % (_('Resize Drill'), _('R'))
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
            '%s\t%s' % (_('Move'), _('M')))

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
        self.grb_simplification_menuitem = self.geo_editor_menu.addAction(
            QtGui.QIcon(self.app.resource_location + '/simplify32.png'),
            '%s\t%s' % (_("Simplification"), '')
        )
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
            QtGui.QIcon(self.app.resource_location + '/indigo32.png'), _('Indigo'))

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
        self.notebook = FCDetachableTab2(protect=True, protect_by_name=[_("Project"), _("Properties")], parent=self)
        # self.notebook.setTabsClosable(False)
        self.notebook.useOldIndex(True)
        self.notebook.auto_remove_closed_tab = False

        self.splitter.addWidget(self.notebook)

        self.splitter_left = QtWidgets.QSplitter(Qt.Orientation.Vertical)
        self.splitter.addWidget(self.splitter_left)
        self.splitter_left.addWidget(self.notebook)
        self.splitter_left.setHandleWidth(0)

        # ########################################################################
        # ########################## ToolBAR # ###################################
        # ########################################################################

        # ## TOOLBAR INSTALLATION ###
        self.toolbarfile = QtWidgets.QToolBar(_('File Toolbar'))
        self.toolbarfile.setObjectName('File_TB')
        self.toolbarfile.setStyleSheet("QToolBar{spacing:0px;}")
        self.addToolBar(self.toolbarfile)

        self.toolbaredit = QtWidgets.QToolBar(_('Edit Toolbar'))
        self.toolbaredit.setObjectName('Edit_TB')
        self.toolbaredit.setStyleSheet("QToolBar{spacing:0px;}")
        self.addToolBar(self.toolbaredit)

        self.toolbarview = QtWidgets.QToolBar(_('View Toolbar'))
        self.toolbarview.setObjectName('View_TB')
        self.toolbarview.setStyleSheet("QToolBar{spacing:0px;}")
        self.addToolBar(self.toolbarview)

        self.toolbarshell = QtWidgets.QToolBar(_('Shell Toolbar'))
        self.toolbarshell.setObjectName('Shell_TB')
        self.toolbarshell.setStyleSheet("QToolBar{spacing:0px;}")
        self.addToolBar(self.toolbarshell)

        self.toolbarplugins = QtWidgets.QToolBar(_('Plugin Toolbar'))
        self.toolbarplugins.setObjectName('Plugins_TB')
        self.toolbarplugins.setStyleSheet("QToolBar{spacing:0px;}")
        self.addToolBar(self.toolbarplugins)

        self.exc_edit_toolbar = QtWidgets.QToolBar(_('Excellon Editor Toolbar'))
        self.exc_edit_toolbar.setObjectName('ExcEditor_TB')
        self.exc_edit_toolbar.setStyleSheet("QToolBar{spacing:0px;}")
        self.addToolBar(self.exc_edit_toolbar)

        self.addToolBarBreak()

        self.geo_edit_toolbar = QtWidgets.QToolBar(_('Geometry Editor Toolbar'))
        self.geo_edit_toolbar.setObjectName('GeoEditor_TB')
        self.geo_edit_toolbar.setStyleSheet("QToolBar{spacing:0px;}")
        self.addToolBar(self.geo_edit_toolbar)

        self.grb_edit_toolbar = QtWidgets.QToolBar(_('Gerber Editor Toolbar'))
        self.grb_edit_toolbar.setObjectName('GrbEditor_TB')
        self.grb_edit_toolbar.setStyleSheet("QToolBar{spacing:0px;}")
        self.addToolBar(self.grb_edit_toolbar)

        # ### INFOBAR TOOLBARS ###################################################
        self.delta_coords_toolbar = CoordsToolbar(_('Delta Coordinates Toolbar'))
        self.delta_coords_toolbar.setObjectName('Delta_Coords_TB')
        self.delta_coords_toolbar.setStyleSheet("QToolBar{spacing:0px;}")

        self.coords_toolbar = CoordsToolbar(_('Coordinates Toolbar'))
        self.coords_toolbar.setObjectName('Coords_TB')
        self.coords_toolbar.setStyleSheet("QToolBar{spacing:0px;}")

        self.grid_toolbar = QtWidgets.QToolBar(_('Grid Toolbar'))
        self.grid_toolbar.setObjectName('Snap_TB')
        self.grid_toolbar.setStyleSheet(
            """
            QToolBar { padding: 0; }
            QToolBar QToolButton { padding: -2; margin: -2; }
            """
        )
        self.grid_toolbar.setStyleSheet("QToolBar{spacing:0px;}")

        self.status_toolbar = QtWidgets.QToolBar(_('Status Toolbar'))
        self.status_toolbar.setStyleSheet(
            """
            QToolBar { padding: 0; }
            QToolBar QToolButton { padding: -2; margin: -2; }
            """
        )
        self.status_toolbar.setStyleSheet("QToolBar{spacing:0px;}")

        # ########################################################################
        # ########################## File Toolbar# ###############################
        # ########################################################################
        self.file_open_gerber_btn = self.toolbarfile.addAction(
            QtGui.QIcon(self.app.resource_location + '/open_gerber32.png'), _("Gerber"))
        self.file_open_gerber_btn.setToolTip(_("Open a Gerber file."))
        self.file_open_excellon_btn = self.toolbarfile.addAction(
            QtGui.QIcon(self.app.resource_location + '/open_excellon32.png'), _("Excellon"))
        self.file_open_excellon_btn.setToolTip(_("Open a Excellon file."))
        self.toolbarfile.addSeparator()
        self.file_open_btn = self.toolbarfile.addAction(
            QtGui.QIcon(self.app.resource_location + '/folder32.png'), _("Open"))
        self.file_open_btn.setToolTip(_("Open a project."))
        self.file_save_btn = self.toolbarfile.addAction(
            QtGui.QIcon(self.app.resource_location + '/save_as.png'), _("Save"))
        self.file_save_btn.setToolTip(_("Save the current project."))

        # ########################################################################
        # ########################## Edit Toolbar# ###############################
        # ########################################################################
        self.editor_start_btn = self.toolbaredit.addAction(
            QtGui.QIcon(self.app.resource_location + '/edit_file32.png'), _("Editor"))
        self.editor_exit_btn = QtWidgets.QToolButton()

        # https://www.w3.org/TR/SVG11/types.html#ColorKeywords
        self.editor_exit_btn.setStyleSheet("""
                                          QToolButton
                                          {
                                              color: black;
                                              background-color: blue;
                                          }
                                          """)
        self.editor_exit_btn.setIcon(QtGui.QIcon(self.app.resource_location + '/power16.png'))
        self.editor_exit_btn.setToolTip(_("Exit from Editor."))
        # in order to hide it we hide the returned action
        self.editor_exit_btn_ret_action = self.toolbaredit.addWidget(self.editor_exit_btn)

        self.toolbaredit.addSeparator()
        self.copy_btn = self.toolbaredit.addAction(
            QtGui.QIcon(self.app.resource_location + '/copy_file32.png'), _("Copy"))
        self.copy_btn.setToolTip(_("Copy a selection of objects."))
        self.delete_btn = self.toolbaredit.addAction(
            QtGui.QIcon(self.app.resource_location + '/trash32.png'), _("Delete"))
        self.delete_btn.setToolTip(_("Delete a selection of objects."))
        self.toolbaredit.addSeparator()
        self.distance_btn = self.toolbaredit.addAction(
            QtGui.QIcon(self.app.resource_location + '/distance32.png'), _("Distance"))
        self.distance_btn.setToolTip(_("Measure a distance between two or more points."))
        # self.distance_min_btn = self.toolbaredit.addAction(
        #     QtGui.QIcon(self.app.resource_location + '/distance_min32.png'), _("Min Distance"))
        # self.distance_min_btn.setToolTip(_("Measure the minimum distance between two objects."))
        self.origin_btn = self.toolbaredit.addAction(
            QtGui.QIcon(self.app.resource_location + '/origin32.png'), _('Set Origin'))
        self.origin_btn.setToolTip(_("Set an origin to a custom location."))
        # self.move2origin_btn = self.toolbaredit.addAction(
        #     QtGui.QIcon(self.app.resource_location + '/move2origin32.png'), _('To Orig.'))
        # self.move2origin_btn.setToolTip(_("Move selected objects to the origin."))
        # self.center_in_origin_btn = self.toolbaredit.addAction(
        #     QtGui.QIcon(self.app.resource_location + '/custom_origin32.png'), _('C Origin'))
        # self.center_in_origin_btn.setToolTip(_("Move the selected objects to custom positions."))

        self.jmp_btn = self.toolbaredit.addAction(
            QtGui.QIcon(self.app.resource_location + '/jump_to32.png'), _('Jump to'))
        self.jmp_btn.setToolTip(_("Move the mouse cursor to a defined position and center into view."))
        self.locate_btn = self.toolbaredit.addAction(
            QtGui.QIcon(self.app.resource_location + '/locate32.png'), _('Locate'))
        self.locate_btn.setToolTip(_("Locate a predefined position on a selected object."))

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
        self.drill_btn = self.toolbarplugins.addAction(
            QtGui.QIcon(self.app.resource_location + '/drill32.png'), _("Drilling"))
        self.mill_btn = self.toolbarplugins.addAction(
            QtGui.QIcon(self.app.resource_location + '/milling_tool32.png'), _("Milling"))
        self.level_btn = self.toolbarplugins.addAction(
            QtGui.QIcon(self.app.resource_location + '/level32.png'), _("Levelling"))
        self.level_btn.setDisabled(True)
        self.level_btn.setToolTip("DISABLED. Work in progress!")

        self.toolbarplugins.addSeparator()

        self.isolation_btn = self.toolbarplugins.addAction(
            QtGui.QIcon(self.app.resource_location + '/iso32.png'), _("Isolation"))
        self.follow_btn = self.toolbarplugins.addAction(
            QtGui.QIcon(self.app.resource_location + '/follow32.png'), _("Follow"))
        self.ncc_btn = self.toolbarplugins.addAction(
            QtGui.QIcon(self.app.resource_location + '/ncc32.png'), _("NCC"))
        self.paint_btn = self.toolbarplugins.addAction(
            QtGui.QIcon(self.app.resource_location + '/paint32.png'), _("Paint"))

        self.toolbarplugins.addSeparator()

        self.cutout_btn = self.toolbarplugins.addAction(
            QtGui.QIcon(self.app.resource_location + '/cut32.png'), _("Cutout"))
        self.panelize_btn = self.toolbarplugins.addAction(
            QtGui.QIcon(self.app.resource_location + '/panelize32.png'), _("Panel"))
        self.film_btn = self.toolbarplugins.addAction(
            QtGui.QIcon(self.app.resource_location + '/film32.png'), _("Film"))
        self.dblsided_btn = self.toolbarplugins.addAction(
            QtGui.QIcon(self.app.resource_location + '/doubleside32.png'), _("2-Sided"))

        self.toolbarplugins.addSeparator()

        self.align_btn = self.toolbarplugins.addAction(
            QtGui.QIcon(self.app.resource_location + '/align32.png'), _("Align"))
        # self.sub_btn = self.toolbarplugins.addAction(
        #     QtGui.QIcon(self.app.resource_location + '/sub32.png'), _("Subtract Tool"))

        self.toolbarplugins.addSeparator()

        # self.extract_btn = self.toolbarplugins.addAction(
        #     QtGui.QIcon(self.app.resource_location + '/extract32.png'), _("Extract"))
        self.copperfill_btn = self.toolbarplugins.addAction(
            QtGui.QIcon(self.app.resource_location + '/copperfill32.png'), _("Thieving"))
        self.markers_tool_btn = self.toolbarplugins.addAction(
            QtGui.QIcon(self.app.resource_location + '/corners_32.png'), _("Markers"))
        self.punch_btn = self.toolbarplugins.addAction(
            QtGui.QIcon(self.app.resource_location + '/punch32.png'), _("Punch"))
        self.calculators_btn = self.toolbarplugins.addAction(
            QtGui.QIcon(self.app.resource_location + '/calculator32.png'), _("Calculators"))

        self.toolbarplugins.addSeparator()

        # self.solder_btn = self.toolbarplugins.addAction(
        #     QtGui.QIcon(self.app.resource_location + '/solderpastebis32.png'), _("SolderPaste"))
        # self.sub_btn = self.toolbarplugins.addAction(
        #     QtGui.QIcon(self.app.resource_location + '/sub32.png'), _("Subtract"))
        # self.rules_btn = self.toolbarplugins.addAction(
        #     QtGui.QIcon(self.app.resource_location + '/rules32.png'), _("Rules"))
        # self.optimal_btn = self.toolbarplugins.addAction(
        #     QtGui.QIcon(self.app.resource_location + '/open_excellon32.png'), _("Optimal"))
        # self.transform_btn = self.toolbarplugins.addAction(
        #     QtGui.QIcon(self.app.resource_location + '/transform.png'), _("Transform"))
        # self.qrcode_btn = self.toolbarplugins.addAction(
        #     QtGui.QIcon(self.app.resource_location + '/qrcode32.png'), _("QRCode"))
        # self.align_btn = self.toolbarplugins.addAction(
        #     QtGui.QIcon(self.app.resource_location + '/align32.png'), _("Align Objects"))
        # self.fiducials_btn = self.toolbarplugins.addAction(
        #     QtGui.QIcon(self.app.resource_location + '/fiducials_32.png'), _("Fiducials"))
        # self.cal_btn = self.toolbarplugins.addAction(
        #     QtGui.QIcon(self.app.resource_location + '/calibrate_32.png'), _("Calibration"))

        # self.invert_btn = self.toolbarplugins.addAction(
        #     QtGui.QIcon(self.app.resource_location + '/invert32.png'), _("Invert Gerber"))
        # self.etch_btn = self.toolbarplugins.addAction(
        #     QtGui.QIcon(self.app.resource_location + '/etch_32.png'), _("Etch Compensation"))

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
            QtGui.QIcon(self.app.resource_location + '/copy32.png'), _('Copy'))
        self.delete_drill_btn = self.exc_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/trash32.png'), _("Delete"))

        self.exc_edit_toolbar.addSeparator()
        self.move_drill_btn = self.exc_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/move32.png'), _("Move"))

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
        self.geo_add_simplification_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/simplify32.png'), _('Simplify'))
        self.geo_add_buffer_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/buffer16-2.png'), _('Add Buffer'))
        self.geo_add_paint_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/paint32.png'), _('Paint Shape'))
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
            QtGui.QIcon(self.app.resource_location + '/subtract32.png'),
            _('Polygon Subtraction. First selected is the target.\n'
              'The rest of the selected is subtracted from the first.\n'
              'First selected is replaced by the result.'))
        self.geo_alt_subtract_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/subtract_alt32.png'),
            _('Alt Subtraction. First selected is the target.\n'
              'The rest of the selected is subtracted from the first.\n'
              'First selected is kept besides the result.'))

        self.geo_edit_toolbar.addSeparator()
        self.geo_cutpath_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/cutpath32.png'), _('Cut Path'))
        self.geo_copy_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/copy32.png'), _("Copy Shape(s)"))

        self.geo_delete_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/trash32.png'), _("Delete"))
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
        self.aperture_simplify_btn = self.grb_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/simplify32.png'), _('Simplification'))
        self.aperture_scale_btn = self.grb_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/scale32.png'), _('Scale'))
        self.aperture_markarea_btn = self.grb_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/markarea32.png'), _('Mark Area'))
        self.grb_import_btn = self.grb_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/import.png'), _('Import Shape'))

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
            QtGui.QIcon(self.app.resource_location + '/grid18.png'), _('Snap to grid'))
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

        self.grid_gap_y_entry.setVisible(False)

        self.gridy_entry_action = self.grid_toolbar.addWidget(self.grid_gap_y_entry)
        self.grid_toolbar.addWidget(FCLabel(" "))

        # self.ois_grid = OptionalInputSection(self.grid_gap_link_cb, [self.grid_gap_y_entry], logic=False)
        self.grid_gap_link_cb.clicked.connect(
            lambda x: self.gridy_entry_action.setVisible(False) if x else self.gridy_entry_action.setVisible(True))
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
        self.axis_status_label.setPixmap(QtGui.QPixmap(self.app.resource_location + '/axis18.png'))
        self.status_toolbar.addWidget(self.axis_status_label)
        self.status_toolbar.addWidget(FCLabel(" "))

        self.pref_status_label = FCLabel()
        self.pref_status_label.setToolTip(_("Preferences"))
        self.pref_status_label.setPixmap(QtGui.QPixmap(self.app.resource_location + '/settings18.png'))
        self.status_toolbar.addWidget(self.pref_status_label)
        self.status_toolbar.addWidget(FCLabel(" "))

        self.hud_label = FCLabel()
        self.hud_label.setToolTip(_("HUD (Heads up display)"))
        self.hud_label.setPixmap(QtGui.QPixmap(self.app.resource_location + '/hud18.png'))
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
            "<b>Dx</b>: 0.0&nbsp;&nbsp;   <b>Dy</b>: 0.0&nbsp;&nbsp;&nbsp;&nbsp;")
        self.rel_position_label.setMinimumWidth(110)
        self.rel_position_label.setToolTip(_("Relative measurement.\nReference is last click position"))
        self.delta_coords_toolbar.addWidget(self.rel_position_label)

        # #######################################################################
        # ####################### Coordinates TOOLBAR ###########################
        # #######################################################################
        self.position_label = FCLabel("&nbsp;<b>X</b>: 0.0&nbsp;&nbsp;   <b>Y</b>: 0.0&nbsp;")
        self.position_label.setMinimumWidth(110)
        self.position_label.setToolTip(_("Absolute measurement.\n"
                                         "Reference is (X=0, Y= 0) position"))
        self.coords_toolbar.addWidget(self.position_label)

        # #######################################################################
        # ####################### TCL Shell DOCK ################################
        # #######################################################################
        self.shell_dock = FCDock(_("TCL Shell"), close_callback=self.toggle_shell_ui)
        self.shell_dock.setWindowIcon(QtGui.QIcon(self.app.resource_location + '/app24.png'))
        self.shell_dock.setObjectName('Shell_DockWidget')
        self.shell_dock.setAllowedAreas(QtCore.Qt.DockWidgetArea.AllDockWidgetAreas)
        self.shell_dock.setFeatures(QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetMovable |
                                    QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetFloatable |
                                    QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetClosable)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.BottomDockWidgetArea, self.shell_dock)

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
        self.notebook.protectTab(0)
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
        self.notebook.protectTab(1)

        # ########################################################################
        # ########################## TOOL Tab # ##################################
        # ########################################################################
        self.plugin_tab = QtWidgets.QWidget()
        self.plugin_tab.setObjectName("plugin_tab")
        self.plugin_tab_layout = QtWidgets.QVBoxLayout(self.plugin_tab)
        self.plugin_tab_layout.setContentsMargins(2, 2, 2, 2)
        # self.notebook.addTab(self.plugin_tab, _("Tool"))

        self.plugin_scroll_area = VerticalScrollArea()
        # self.plugin_scroll_area.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.plugin_tab_layout.addWidget(self.plugin_scroll_area)

        # ########################################################################
        # ########################## RIGHT Widget # ##############################
        # ########################################################################
        self.right_widget = QtWidgets.QWidget()
        self.right_widget.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Ignored)
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

        if self.app.options["global_theme"] not in ['default', 'light']:
            self.plot_tab_area.setStyleSheet(
                """
                QTabWidget::pane {
                border: 0px solid rgba(255.000, 00.000, 00.000, 1.000);
                }
                """
            )

        # ########################################################################
        # ########################## PREFERENCES AREA Tab # ######################
        # ########################################################################
        self.preferences_tab = QtWidgets.QWidget()
        self.preferences_tab.setObjectName("preferences_tab")
        self.pref_tab_layout = QtWidgets.QVBoxLayout(self.preferences_tab)
        self.pref_tab_layout.setContentsMargins(2, 2, 2, 2)

        self.pref_tab_area = FCTab()
        if self.app.options["global_theme"] not in ['default', 'light']:
            self.pref_tab_area.setStyleSheet(
                """
                QTabWidget::pane {
                border: 0px solid rgba(63.000, 64.000, 66.000, 1.000);
                }
                """
            )
        self.pref_tab_area.setTabsClosable(False)
        self.pref_tab_area_tabBar = self.pref_tab_area.tabBar()
        self.pref_tab_area_tabBar.setStyleSheet("QTabBar::tab{min-width:90px;}")
        self.pref_tab_area_tabBar.setExpanding(True)
        self.pref_tab_layout.addWidget(self.pref_tab_area)
        self.default_pref_tab_area_tab_text_color = self.pref_tab_area.tabBar().tabTextColor(0)

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
        self.general_scroll_area.setWidgetResizable(True)
        self.general_tab_lay.addWidget(self.general_scroll_area)

        self.gerber_tab = QtWidgets.QWidget()
        self.gerber_tab.setObjectName("gerber_tab")
        self.pref_tab_area.addTab(self.gerber_tab, _("Gerber").upper())
        self.gerber_tab_lay = QtWidgets.QVBoxLayout()
        self.gerber_tab_lay.setContentsMargins(2, 2, 2, 2)
        self.gerber_tab.setLayout(self.gerber_tab_lay)

        self.gerber_scroll_area = QtWidgets.QScrollArea()
        self.gerber_scroll_area.setWidgetResizable(True)
        self.gerber_tab_lay.addWidget(self.gerber_scroll_area)

        self.excellon_tab = QtWidgets.QWidget()
        self.excellon_tab.setObjectName("excellon_tab")
        self.pref_tab_area.addTab(self.excellon_tab, _("Excellon").upper())
        self.excellon_tab_lay = QtWidgets.QVBoxLayout()
        self.excellon_tab_lay.setContentsMargins(2, 2, 2, 2)
        self.excellon_tab.setLayout(self.excellon_tab_lay)

        self.excellon_scroll_area = QtWidgets.QScrollArea()
        self.excellon_scroll_area.setWidgetResizable(True)
        self.excellon_tab_lay.addWidget(self.excellon_scroll_area)

        self.geometry_tab = QtWidgets.QWidget()
        self.geometry_tab.setObjectName("geometry_tab")
        self.pref_tab_area.addTab(self.geometry_tab, _("Geometry").upper())
        self.geometry_tab_lay = QtWidgets.QVBoxLayout()
        self.geometry_tab_lay.setContentsMargins(2, 2, 2, 2)
        self.geometry_tab.setLayout(self.geometry_tab_lay)

        self.geometry_scroll_area = QtWidgets.QScrollArea()
        self.geometry_scroll_area.setWidgetResizable(True)
        self.geometry_tab_lay.addWidget(self.geometry_scroll_area)

        self.text_editor_tab = QtWidgets.QWidget()
        self.text_editor_tab.setObjectName("text_editor_tab")
        self.pref_tab_area.addTab(self.text_editor_tab, _("CNC-JOB"))
        self.cncjob_tab_lay = QtWidgets.QVBoxLayout()
        self.cncjob_tab_lay.setContentsMargins(2, 2, 2, 2)
        self.text_editor_tab.setLayout(self.cncjob_tab_lay)

        self.cncjob_scroll_area = QtWidgets.QScrollArea()
        self.cncjob_scroll_area.setWidgetResizable(True)
        self.cncjob_tab_lay.addWidget(self.cncjob_scroll_area)

        self.plugins_eng_tab = QtWidgets.QWidget()
        self.pref_tab_area.addTab(self.plugins_eng_tab, '%s' % _("Engraving").upper())
        self.plugins_eng_tab_lay = QtWidgets.QVBoxLayout()
        self.plugins_eng_tab_lay.setContentsMargins(2, 2, 2, 2)
        self.plugins_eng_tab.setLayout(self.plugins_eng_tab_lay)

        self.plugins_engraving_scroll_area = QtWidgets.QScrollArea()
        self.plugins_engraving_scroll_area.setWidgetResizable(True)
        self.plugins_eng_tab_lay.addWidget(self.plugins_engraving_scroll_area)

        self.tools_tab = QtWidgets.QWidget()
        self.pref_tab_area.addTab(self.tools_tab, '%s' % _("Processing").upper())
        self.tools_tab_lay = QtWidgets.QVBoxLayout()
        self.tools_tab_lay.setContentsMargins(2, 2, 2, 2)
        self.tools_tab.setLayout(self.tools_tab_lay)

        self.tools_scroll_area = QtWidgets.QScrollArea()
        self.tools_scroll_area.setWidgetResizable(True)
        self.tools_tab_lay.addWidget(self.tools_scroll_area)

        self.tools2_tab = QtWidgets.QWidget()
        self.pref_tab_area.addTab(self.tools2_tab, '%s' % _("Extra Plugins").upper())
        self.tools2_tab_lay = QtWidgets.QVBoxLayout()
        self.tools2_tab_lay.setContentsMargins(2, 2, 2, 2)
        self.tools2_tab.setLayout(self.tools2_tab_lay)

        self.tools2_scroll_area = QtWidgets.QScrollArea()
        self.tools2_scroll_area.setWidgetResizable(True)
        self.tools2_tab_lay.addWidget(self.tools2_scroll_area)

        self.fa_tab = QtWidgets.QWidget()
        self.fa_tab.setObjectName("fa_tab")
        self.pref_tab_area.addTab(self.fa_tab, _("UTILITIES"))
        self.fa_tab_lay = QtWidgets.QVBoxLayout()
        self.fa_tab_lay.setContentsMargins(2, 2, 2, 2)
        self.fa_tab.setLayout(self.fa_tab_lay)

        self.fa_scroll_area = QtWidgets.QScrollArea()
        self.fa_scroll_area.setWidgetResizable(True)
        self.fa_tab_lay.addWidget(self.fa_scroll_area)

        self.pref_tab_bottom_layout = QtWidgets.QHBoxLayout()
        self.pref_tab_bottom_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.pref_tab_layout.addLayout(self.pref_tab_bottom_layout)

        self.pref_tab_bottom_layout_1 = QtWidgets.QHBoxLayout()
        self.pref_tab_bottom_layout_1.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
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
              "such as: layout, gui state, style etc.")
        )

        self.pref_tab_bottom_layout_1.addWidget(self.clear_btn)

        self.pref_tab_bottom_layout_2 = QtWidgets.QHBoxLayout()
        self.pref_tab_bottom_layout_2.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight |
                                                   QtCore.Qt.AlignmentFlag.AlignVCenter)
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

        # View
        self.cmenu_viewmenu = self.popMenu.addMenu(
            QtGui.QIcon(self.app.resource_location + '/view64.png'), _("View"))
        self.popmenu_disable = self.cmenu_viewmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/disable32.png'), _("Toggle Visibility"))
        self.popmenu_panel_toggle = self.cmenu_viewmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/notebook16.png'), _("Toggle Panel"))
        self.cmenu_viewmenu.addSeparator()
        self.zoomfit = self.cmenu_viewmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/zoom_fit32.png'), _("Zoom Fit"))
        self.clearplot = self.cmenu_viewmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/clear_plot32.png'), _("Clear Plot"))
        self.replot = self.cmenu_viewmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/replot32.png'), _("Replot"))

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

        # Grids
        self.cmenu_gridmenu = self.popMenu.addMenu(
            QtGui.QIcon(self.app.resource_location + '/grid32_menu.png'), _("Grids"))

        self.popMenu.addSeparator()

        # Set colors
        self.pop_menucolor = self.popMenu.addMenu(
            QtGui.QIcon(self.app.resource_location + '/set_color32.png'), _('Set Color'))

        self.pop_menu_red = self.pop_menucolor.addAction(
            QtGui.QIcon(self.app.resource_location + '/red32.png'), _('Red'))

        self.pop_menu_blue = self.pop_menucolor.addAction(
            QtGui.QIcon(self.app.resource_location + '/blue32.png'), _('Blue'))

        self.pop_menu_yellow = self.pop_menucolor.addAction(
            QtGui.QIcon(self.app.resource_location + '/yellow32.png'), _('Yellow'))

        self.pop_menu_green = self.pop_menucolor.addAction(
            QtGui.QIcon(self.app.resource_location + '/green32.png'), _('Green'))

        self.pop_menu_purple = self.pop_menucolor.addAction(
            QtGui.QIcon(self.app.resource_location + '/violet32.png'), _('Purple'))

        self.pop_menu_brown = self.pop_menucolor.addAction(
            QtGui.QIcon(self.app.resource_location + '/brown32.png'), _('Brown'))

        self.pop_menu_brown = self.pop_menucolor.addAction(
            QtGui.QIcon(self.app.resource_location + '/indigo32.png'), _('Indigo'))

        self.pop_menu_brown = self.pop_menucolor.addAction(
            QtGui.QIcon(self.app.resource_location + '/white32.png'), _('White'))

        self.pop_menu_brown = self.pop_menucolor.addAction(
            QtGui.QIcon(self.app.resource_location + '/black32.png'), _('Black'))

        self.pop_menucolor.addSeparator()

        self.pop_menu_custom = self.pop_menucolor.addAction(
            QtGui.QIcon(self.app.resource_location + '/set_color32.png'), _('Custom'))

        self.pop_menucolor.addSeparator()

        self.pop_menu_custom = self.pop_menucolor.addAction(
            QtGui.QIcon(self.app.resource_location + '/set_color32.png'), _('Opacity'))

        self.pop_menu_custom = self.pop_menucolor.addAction(
            QtGui.QIcon(self.app.resource_location + '/set_color32.png'), _('Default'))

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
        self.draw_simplification = self.g_editor_cmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/simplify32.png'), _("Simplification"))
        self.draw_buffer = self.g_editor_cmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/buffer16-2.png'), _("Buffer"))
        self.draw_paint = self.g_editor_cmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/paint32.png'), _("Paint"))
        self.draw_eraser = self.g_editor_cmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/eraser26.png'), _("Eraser"))
        self.g_editor_cmenu.addSeparator()

        self.draw_union = self.g_editor_cmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/union32.png'), _("Union"))
        self.draw_intersect = self.g_editor_cmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/intersection32.png'), _("Intersection"))
        self.draw_substract = self.g_editor_cmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/subtract32.png'), _("Subtraction"))
        self.draw_substract_alt = self.g_editor_cmenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/subtract_alt32.png'), _("Alt Subtraction"))
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
            QtGui.QIcon(self.app.resource_location + '/open_excellon32.png'), _("Add Drill"))
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

        self.popmenu_numeric_move = self.popMenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/move32_bis.png'), _("Num Move"))
        self.popmenu_move2origin = self.popMenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/move2origin32.png'), _("Move2Origin"))
        self.popmenu_move = self.popMenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/move32.png'), _("Move"))
        self.popmenu_properties = self.popMenu.addAction(
            QtGui.QIcon(self.app.resource_location + '/properties32.png'), _("Properties"))

        # ########################################################################
        # ########################## INFO BAR # ##################################
        # ########################################################################
        self.infobar = self.statusBar()
        self.fcinfo = AppInfoBar(app=self.app)

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
        self.activity_view = FlatCAMActivityView(icon_location=self.app.resource_location,
                                                 icon_kind=self.app.defaults["global_activity_icon"],
                                                 replot_callback=self.app.on_toolbar_replot)
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
        self.app_icon.addFile(self.app.resource_location + '/app16.png', QtCore.QSize(16, 16))
        self.app_icon.addFile(self.app.resource_location + '/app24.png', QtCore.QSize(24, 24))
        self.app_icon.addFile(self.app.resource_location + '/app32.png', QtCore.QSize(32, 32))
        self.app_icon.addFile(self.app.resource_location + '/app48.png', QtCore.QSize(48, 48))
        self.app_icon.addFile(self.app.resource_location + '/app64.png', QtCore.QSize(64, 64))
        self.app_icon.addFile(self.app.resource_location + '/app128.png', QtCore.QSize(128, 128))
        self.app_icon.addFile(self.app.resource_location + '/app256.png', QtCore.QSize(256, 256))
        self.setWindowIcon(self.app_icon)

        self.setWindowTitle('FlatCAM Evo %s %s - %s' %
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
        self.editor_exit_btn_ret_action.setVisible(False)

        # start with GRID activated
        self.grid_snap_btn.trigger()

        self.g_editor_cmenu.menuAction().setVisible(False)
        self.grb_editor_cmenu.menuAction().setVisible(False)
        self.e_editor_cmenu.menuAction().setVisible(False)

        # ########################################################################
        # construct the Toolbar Lock menu entry to the context menu of the QMainWindow
        # ########################################################################
        self.lock_action = QtGui.QAction()
        self.lock_action.setText(_("Lock Toolbars"))
        self.lock_action.setCheckable(True)

        # ########################################################################
        # construct the Show Text menu entry to the context menu of the QMainWindow
        # ########################################################################
        self.show_text_action = QtGui.QAction()
        self.show_text_action.setText(_("Show Text"))
        self.show_text_action.setCheckable(True)

        # ########################################################################
        # ######################## BUILD PREFERENCES #############################
        # ########################################################################
        self.general_pref_form = GeneralPreferencesUI(app=self.app)
        self.gerber_pref_form = GerberPreferencesUI(app=self.app)
        self.excellon_pref_form = ExcellonPreferencesUI(app=self.app)
        self.geo_pref_form = GeometryPreferencesUI(app=self.app)
        self.cncjob_pref_form = CNCJobPreferencesUI(app=self.app)
        self.plugin_pref_form = PluginsPreferencesUI(app=self.app)
        self.plugin2_pref_form = Plugins2PreferencesUI(app=self.app)
        self.plugin_eng_pref_form = PluginsEngravingPreferencesUI(app=self.app)

        self.util_pref_form = UtilPreferencesUI(app=self.app)

        QtCore.QCoreApplication.instance().installEventFilter(self)

        # ########################################################################
        # ################## RESTORE UI from QSettings #################
        # ########################################################################
        qsettings = QSettings("Open Source", "FlatCAM")
        if qsettings.contains("saved_gui_state"):
            self.restoreState(qsettings.value('saved_gui_state'), 0)
        tb_lock_state = qsettings.value('toolbar_lock', "true")
        show_text_state = qsettings.value('menu_show_text', "true")
        win_geo = qsettings.value('window_geometry', (100, 100, 800, 400))
        splitter_left = qsettings.value('splitter_left', 1)

        if qsettings.contains("layout"):
            layout = qsettings.value('layout', type=str)
            self.exc_edit_toolbar.setDisabled(True)
            self.geo_edit_toolbar.setDisabled(True)
            self.grb_edit_toolbar.setDisabled(True)

            self.app.log.debug("MainGUI.__init__() --> UI layout restored from QSettings. Layout = %s" % str(layout))
        else:
            self.exc_edit_toolbar.setDisabled(True)
            self.geo_edit_toolbar.setDisabled(True)
            self.grb_edit_toolbar.setDisabled(True)

            qsettings.setValue('layout', "standard")
            # This will write the setting to the platform specific storage.
            del qsettings
            self.app.log.debug("MainGUI.__init__() --> UI layout restored from options. QSettings set to 'standard'")

        self.lock_action.setChecked(True if tb_lock_state == 'true' else False)
        self.show_text_action.setChecked(True if show_text_state == 'true' else False)

        self.setGeometry(win_geo[0], win_geo[1], win_geo[2], win_geo[3])
        self.app.log.debug("MainGUI.__init__() --> UI state restored from QSettings.")

        self.splitter.setSizes([splitter_left, 0])

        self.lock_toolbar(lock=True if tb_lock_state == 'true' else False)
        self.show_text_under_action(show_text=True if show_text_state == 'true' else False)

        self.corner_snap_btn.setVisible(False)
        self.snap_magnet.setVisible(False)

        self.lock_action.triggered[bool].connect(self.lock_toolbar)
        self.show_text_action.triggered.connect(self.show_text_under_action)

        self.pref_open_button.clicked.connect(self.on_preferences_open_folder)
        self.clear_btn.clicked.connect(lambda: self.on_gui_clear())

        self.wplace_label.clicked.connect(self.app.on_workspace_toggle)
        self.fcinfo.clicked.connect(self.toggle_shell_ui)
        self.coords_toolbar.clicked.connect(self.app.on_gui_coords_clicked)
        self.delta_coords_toolbar.clicked.connect(self.app.on_gui_coords_clicked)

        # to be used in the future
        # self.plot_tab_area.tab_attached.connect(lambda x: print(x))
        # self.plot_tab_area.tab_detached.connect(lambda x: print(x))

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

        self.final_save.connect(self.app.final_save)

        # Notebook and Plot Tab Area signals
        # make the right click on the notebook tab and plot tab area tab raise a menu
        self.notebook.tabBar.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.ActionsContextMenu)
        self.plot_tab_area.tabBar.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.ActionsContextMenu)
        self.on_tab_setup_context_menu()
        # activate initial state
        self.on_detachable_tab_rmb_click(self.app.defaults["global_tabs_detachable"])

        # status bar activation/deactivation
        self.infobar.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.ActionsContextMenu)
        self.build_infobar_context_menu()

        self.plot_tab_area.tab_detached.connect(self.on_tab_detached)

        self.pref_tab_area.tabBar().tabBarClicked.connect(self.on_pref_tabbar_clicked)

        # self.screenChanged.connect(self.on_screen_change)

    # def on_screen_change(self, old_screen, new_screen):
    #     """
    #     Handler of a signal that emits when screens are changed in a multi-monitor setup
    #
    #     :param old_screen:  QtGui.QScreen where the app windows was located before move
    #     :param new_screen:  QtGui.QScreen where the app windows is located after move
    #     :return:
    #     """
    #     old_pixel_ratio = old_screen.devicePixelRatio()
    #     new_pixel_ratio = new_screen.devicePixelRatio()
    #
    #     if old_pixel_ratio != 1.0 or new_pixel_ratio != 1.0:
    #         # update canvas dpi
    #         ratio = new_pixel_ratio / old_pixel_ratio
    #         self.app.plotcanvas.dpi = self.app.plotcanvas.Pdpi * ratio

    def on_pref_tabbar_clicked(self, idx, color=None):
        self.set_pref_tab_area_tab_default_text_color()
        if color is None:
            self.pref_tab_area.tabBar().setTabTextColor(idx, QtGui.QColor('green'))
        else:
            self.pref_tab_area.tabBar().setTabTextColor(idx, color)

    def set_pref_tab_area_tab_default_text_color(self):
        for idx in range(self.pref_tab_area.count()):
            self.pref_tab_area.tabBar().setTabTextColor(idx, self.default_pref_tab_area_tab_text_color)

    def update_location_labels(self, dx, dy, x, y):
        """
        Update the text of the location labels from InfoBar

        :param x:   X location
        :type x:    float
        :param y:   Y location
        :type y:    float
        :param dx:  Delta X location
        :type dx:   float
        :param dy:  Delta Y location
        :type dy:   float
        :return:
        :rtype:     None
        """

        # Set the position label
        if x is None or y is None:
            self.position_label.setText("")
        else:
            x_dec = str(self.app.dec_format(x, self.app.decimals)) if x else '0.0'
            y_dec = str(self.app.dec_format(y, self.app.decimals)) if y else '0.0'
            self.position_label.setText("&nbsp;<b>X</b>: %s&nbsp;&nbsp;   "
                                        "<b>Y</b>: %s&nbsp;" % (x_dec, y_dec))

        # Set the Delta position label
        if dx is None or dy is None or (dx is None and dy is None):
            self.rel_position_label.setText("")
        else:
            dx_dec = str(self.app.dec_format(dx, self.app.decimals)) if dx else '0.0'
            dy_dec = str(self.app.dec_format(dy, self.app.decimals)) if dy else '0.0'

            self.rel_position_label.setText("<b>Dx</b>: %s&nbsp;&nbsp;  <b>Dy</b>: "
                                            "%s&nbsp;&nbsp;&nbsp;&nbsp;" % (dx_dec, dy_dec))

    def on_tab_detached(self, tab_detached, tab_detached_name):
        if tab_detached_name == 'FlatCAM Plot Area':
            pass
            # print(tab_detached_name)
            # self.app.plotcanvas.unfreeze()
            # self.app.plotcanvas.native.setParent(tab_detached)
            # self.app.plotcanvas.freeze()

    def set_ui_title(self, name):
        """
        Sets the title of the main window.

        :param name: String that store the project path and project name
        :return: None
        """
        title = 'FlatCAM Evo %s %s - %s - [%s]    %s' % (
            self.app.version, ('BETA' if self.app.beta else ''), platform.architecture()[0], self.app.engine, name)
        self.setWindowTitle(title)

    def on_toggle_gui(self):
        if self.isHidden():
            mgui_settings = QSettings("Open Source", "FlatCAM")
            if mgui_settings.contains("maximized_gui"):
                maximized_ui = mgui_settings.value('maximized_gui', type=bool)
                if maximized_ui is True:
                    self.showMaximized()
                else:
                    self.show()
            else:
                self.show()
        else:
            self.hide()

    def on_tab_setup_context_menu(self):
        initial_checked = self.app.defaults["global_tabs_detachable"]
        action_name = str(_("Detachable Tabs"))
        action = QtGui.QAction(self)
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
        delta_coords_action = QtGui.QAction(self)
        delta_coords_action.setCheckable(True)
        delta_coords_action.setText(delta_coords_action_name)
        delta_coords_action.setChecked(self.app.defaults["global_delta_coordsbar_show"])
        self.infobar.addAction(delta_coords_action)
        delta_coords_action.triggered.connect(self.toggle_delta_coords)

        coords_action_name = str(_("Coordinates Toolbar"))
        coords_action = QtGui.QAction(self)
        coords_action.setCheckable(True)
        coords_action.setText(coords_action_name)
        coords_action.setChecked(self.app.defaults["global_coordsbar_show"])
        self.infobar.addAction(coords_action)
        coords_action.triggered.connect(self.toggle_coords)

        grid_action_name = str(_("Grid Toolbar"))
        grid_action = QtGui.QAction(self)
        grid_action.setCheckable(True)
        grid_action.setText(grid_action_name)
        grid_action.setChecked(self.app.defaults["global_gridbar_show"])
        self.infobar.addAction(grid_action)
        grid_action.triggered.connect(self.toggle_gridbar)

        status_action_name = str(_("Status Toolbar"))
        status_action = QtGui.QAction(self)
        status_action.setCheckable(True)
        status_action.setText(status_action_name)
        status_action.setChecked(self.app.defaults["global_statusbar_show"])
        self.infobar.addAction(status_action)
        status_action.triggered.connect(self.toggle_statusbar)

    def toggle_coords(self, checked):
        self.app.options["global_coordsbar_show"] = checked
        self.coords_toolbar.setVisible(checked)

    def toggle_delta_coords(self, checked):
        self.app.options["global_delta_coordsbar_show"] = checked
        self.delta_coords_toolbar.setVisible(checked)

    def toggle_gridbar(self, checked):
        self.app.options["global_gridbar_show"] = checked
        self.grid_toolbar.setVisible(checked)

    def toggle_statusbar(self, checked):
        self.app.options["global_statusbar_show"] = checked
        self.status_toolbar.setVisible(checked)

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

    def on_gui_clear(self, forced_clear=False):
        """
        Will clear the settings that are stored in QSettings.
        """
        self.app.log.debug("Clearing the settings in QSettings. GUI settings cleared.")

        theme_settings = QtCore.QSettings("Open Source", "FlatCAM")
        theme_settings.setValue('theme', 'light')

        del theme_settings

        response = None
        bt_yes = None
        if forced_clear is False:
            msgbox = FCMessageBox(parent=self)
            title = _("Clear GUI Settings")
            txt = _("Are you sure you want to delete the GUI Settings? \n")
            msgbox.setWindowTitle(title)  # taskbar still shows it
            msgbox.setWindowIcon(QtGui.QIcon(self.app.resource_location + '/app128.png'))
            msgbox.setText('<b>%s</b>' % title)
            msgbox.setInformativeText(txt)
            msgbox.setIconPixmap(QtGui.QPixmap(self.app.resource_location + '/trash32.png'))

            bt_yes = msgbox.addButton(_('Yes'), QtWidgets.QMessageBox.ButtonRole.YesRole)
            bt_no = msgbox.addButton(_('No'), QtWidgets.QMessageBox.ButtonRole.NoRole)

            msgbox.setDefaultButton(bt_no)
            msgbox.exec()
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
            QtGui.QIcon(self.app.resource_location + '/open_gerber32.png'), _("Gerber"))
        self.file_open_gerber_btn.setToolTip(_("Open a Gerber file."))
        self.file_open_excellon_btn = self.toolbarfile.addAction(
            QtGui.QIcon(self.app.resource_location + '/open_excellon32.png'), _("Excellon"))
        self.file_open_excellon_btn.setToolTip(_("Open a Excellon file."))
        self.toolbarfile.addSeparator()
        self.file_open_btn = self.toolbarfile.addAction(
            QtGui.QIcon(self.app.resource_location + '/folder32.png'), _("Open"))
        self.file_open_btn.setToolTip(_("Open a project."))
        self.file_save_btn = self.toolbarfile.addAction(
            QtGui.QIcon(self.app.resource_location + '/save_as.png'), _("Save"))
        self.file_save_btn.setToolTip(_("Save the current project."))

        # ########################################################################
        # ######################### Edit Toolbar #################################
        # ########################################################################
        self.editor_start_btn = self.toolbaredit.addAction(
            QtGui.QIcon(self.app.resource_location + '/edit_file32.png'), _("Editor"))
        self.editor_exit_btn = QtWidgets.QToolButton()

        # https://www.w3.org/TR/SVG11/types.html#ColorKeywords
        self.editor_exit_btn.setStyleSheet("""
                                          QToolButton
                                          {
                                              color: black;
                                              background-color: blue;
                                          }
                                          """)
        self.editor_exit_btn.setIcon(QtGui.QIcon(self.app.resource_location + '/power16.png'))
        self.editor_exit_btn.setToolTip(_("Exit from Editor."))
        # in order to hide it we hide the returned action
        self.editor_exit_btn_ret_action = self.toolbaredit.addWidget(self.editor_exit_btn)

        self.copy_btn = self.toolbaredit.addAction(
            QtGui.QIcon(self.app.resource_location + '/copy_file32.png'), _("Copy"))
        self.copy_btn.setToolTip(_("Copy a selection of objects."))
        self.delete_btn = self.toolbaredit.addAction(
            QtGui.QIcon(self.app.resource_location + '/trash32.png'), _("Delete"))
        self.delete_btn.setToolTip(_("Delete a selection of objects."))
        self.toolbaredit.addSeparator()
        self.distance_btn = self.toolbaredit.addAction(
            QtGui.QIcon(self.app.resource_location + '/distance32.png'), _("Distance"))
        self.distance_btn.setToolTip(_("Measure a distance between two or more points."))
        # self.distance_min_btn = self.toolbaredit.addAction(
        #     QtGui.QIcon(self.app.resource_location + '/distance_min32.png'), _("Min Distance"))
        # self.distance_min_btn.setToolTip(_("Measure the minimum distance between two objects."))
        self.origin_btn = self.toolbaredit.addAction(
            QtGui.QIcon(self.app.resource_location + '/origin32.png'), _('Set Origin'))
        self.origin_btn.setToolTip(_("Set an origin to a custom location."))
        # self.move2origin_btn = self.toolbaredit.addAction(
        #     QtGui.QIcon(self.app.resource_location + '/move2origin32.png'), _('To Orig.'))
        # self.move2origin_btn.setToolTip(_("Move selected objects to the origin."))
        # self.center_in_origin_btn = self.toolbaredit.addAction(
        #     QtGui.QIcon(self.app.resource_location + '/custom_origin32.png'), _('C Origin'))
        # self.center_in_origin_btn.setToolTip(_("Move the selected objects to custom positions."))

        self.jmp_btn = self.toolbaredit.addAction(
            QtGui.QIcon(self.app.resource_location + '/jump_to32.png'), _('Jump to'))
        self.jmp_btn.setToolTip(_("Move the mouse cursor to a defined position and center into view."))
        self.locate_btn = self.toolbaredit.addAction(
            QtGui.QIcon(self.app.resource_location + '/locate32.png'), _('Locate'))
        self.locate_btn.setToolTip(_("Locate a predefined position on a selected object."))

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
        self.drill_btn = self.toolbarplugins.addAction(
            QtGui.QIcon(self.app.resource_location + '/drill32.png'), _("Drilling"))
        self.mill_btn = self.toolbarplugins.addAction(
            QtGui.QIcon(self.app.resource_location + '/milling_tool32.png'), _("Milling"))
        self.level_btn = self.toolbarplugins.addAction(
            QtGui.QIcon(self.app.resource_location + '/level32.png'), _("Levelling"))
        self.level_btn.setDisabled(True)
        self.level_btn.setToolTip("DISABLED. Work in progress!")

        self.toolbarplugins.addSeparator()

        self.isolation_btn = self.toolbarplugins.addAction(
            QtGui.QIcon(self.app.resource_location + '/iso32.png'), _("Isolation"))
        self.follow_btn = self.toolbarplugins.addAction(
            QtGui.QIcon(self.app.resource_location + '/follow32.png'), _("Follow"))
        self.ncc_btn = self.toolbarplugins.addAction(
            QtGui.QIcon(self.app.resource_location + '/ncc32.png'), _("NCC"))
        self.paint_btn = self.toolbarplugins.addAction(
            QtGui.QIcon(self.app.resource_location + '/paint32.png'), _("Paint"))

        self.toolbarplugins.addSeparator()

        self.cutout_btn = self.toolbarplugins.addAction(
            QtGui.QIcon(self.app.resource_location + '/cut32.png'), _("Cutout"))
        self.panelize_btn = self.toolbarplugins.addAction(
            QtGui.QIcon(self.app.resource_location + '/panelize32.png'), _("Panel"))
        self.film_btn = self.toolbarplugins.addAction(
            QtGui.QIcon(self.app.resource_location + '/film32.png'), _("Film"))
        self.dblsided_btn = self.toolbarplugins.addAction(
            QtGui.QIcon(self.app.resource_location + '/doubleside32.png'), _("2-Sided"))

        self.toolbarplugins.addSeparator()

        self.align_btn = self.toolbarplugins.addAction(
            QtGui.QIcon(self.app.resource_location + '/align32.png'), _("Align"))
        # self.sub_btn = self.toolbarplugins.addAction(
        #     QtGui.QIcon(self.app.resource_location + '/sub32.png'), _("Subtract"))

        self.toolbarplugins.addSeparator()

        # self.extract_btn = self.toolbarplugins.addAction(
        #     QtGui.QIcon(self.app.resource_location + '/extract32.png'), _("Extract"))
        self.copperfill_btn = self.toolbarplugins.addAction(
            QtGui.QIcon(self.app.resource_location + '/copperfill32.png'), _("Thieving"))
        self.markers_tool_btn = self.toolbarplugins.addAction(
            QtGui.QIcon(self.app.resource_location + '/corners_32.png'), _("Markers"))
        self.punch_btn = self.toolbarplugins.addAction(
            QtGui.QIcon(self.app.resource_location + '/punch32.png'), _("Punch Gerber"))
        self.calculators_btn = self.toolbarplugins.addAction(
            QtGui.QIcon(self.app.resource_location + '/calculator32.png'), _("Calculators"))

        self.toolbarplugins.addSeparator()

        # self.solder_btn = self.toolbarplugins.addAction(
        #     QtGui.QIcon(self.app.resource_location + '/solderpastebis32.png'), _("SolderPaste"))
        # self.sub_btn = self.toolbarplugins.addAction(
        #     QtGui.QIcon(self.app.resource_location + '/sub32.png'), _("Subtract"))
        # self.rules_btn = self.toolbarplugins.addAction(
        #     QtGui.QIcon(self.app.resource_location + '/rules32.png'), _("Rules"))
        # self.optimal_btn = self.toolbarplugins.addAction(
        #     QtGui.QIcon(self.app.resource_location + '/open_excellon32.png'), _("Optimal"))
        # self.transform_btn = self.toolbarplugins.addAction(
        #     QtGui.QIcon(self.app.resource_location + '/transform.png'), _("Transform"))
        # self.qrcode_btn = self.toolbarplugins.addAction(
        #     QtGui.QIcon(self.app.resource_location + '/qrcode32.png'), _("QRCode"))
        # self.align_btn = self.toolbarplugins.addAction(
        #     QtGui.QIcon(self.app.resource_location + '/align32.png'), _("Align Objects"))
        # self.fiducials_btn = self.toolbarplugins.addAction(
        #     QtGui.QIcon(self.app.resource_location + '/fiducials_32.png'), _("Fiducials"))
        # self.cal_btn = self.toolbarplugins.addAction(
        #     QtGui.QIcon(self.app.resource_location + '/calibrate_32.png'), _("Calibration"))

        # self.invert_btn = self.toolbarplugins.addAction(
        #     QtGui.QIcon(self.app.resource_location + '/invert32.png'), _("Invert Gerber"))
        # self.etch_btn = self.toolbarplugins.addAction(
        #     QtGui.QIcon(self.app.resource_location + '/etch_32.png'), _("Etch Compensation"))

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
            QtGui.QIcon(self.app.resource_location + '/copy32.png'), _('Copy'))
        self.delete_drill_btn = self.exc_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/trash32.png'), _("Delete"))

        self.exc_edit_toolbar.addSeparator()
        self.move_drill_btn = self.exc_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/move32.png'), _("Move"))

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
            QtGui.QIcon(self.app.resource_location + '/paint32.png'), _('Paint Shape'))
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
        self.geo_alt_subtract_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/subtract_alt32.png'), _('Alt Subtraction'))

        self.geo_edit_toolbar.addSeparator()
        self.geo_cutpath_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/cutpath32.png'), _('Cut Path'))
        self.geo_copy_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/copy32.png'), _("Copy Objects"))
        self.geo_delete_btn = self.geo_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/trash32.png'), _("Delete"))
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
        self.aperture_simplify_btn = self.grb_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/simplify32.png'), _('Simplification'))
        self.aperture_scale_btn = self.grb_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/scale32.png'), _('Scale'))
        self.aperture_markarea_btn = self.grb_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/markarea32.png'), _('Mark Area'))
        self.grb_import_btn = self.grb_edit_toolbar.addAction(
            QtGui.QIcon(self.app.resource_location + '/import.png'), _('Import Shape'))

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
        self.editor_exit_btn_ret_action.setVisible(False)

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

    def on_shortcut_list(self):
        # add the tab if it was closed
        self.plot_tab_area.addTab(self.shortcuts_tab, _("Key Shortcut List"))

        # delete the absolute and relative position and messages in the infobar
        # self.ui.position_label.setText("")
        # self.ui.rel_position_label.setText("")
        # hide coordinates toolbars in the infobar while in DB
        self.coords_toolbar.hide()
        self.delta_coords_toolbar.hide()

        # Switch plot_area to preferences page
        self.plot_tab_area.setCurrentWidget(self.shortcuts_tab)
        # self.show()

    def on_select_tab(self, name):
        # if the splitter is hidden, display it, else hide it but only if the current widget is the same
        if self.splitter.sizes()[0] == 0:
            self.splitter.setSizes([1, 1])
        else:
            if self.notebook.currentWidget().objectName() == name + '_tab':
                self.splitter.setSizes([0, 1])

        if name == 'project':
            self.notebook.setCurrentWidget(self.project_tab)
        elif name == 'properties':
            self.notebook.setCurrentWidget(self.properties_tab)
        elif name == 'tool':
            self.notebook.setCurrentWidget(self.plugin_tab)

    def createPopupMenu(self):
        menu = super().createPopupMenu()

        menu.addSeparator()
        menu.addAction(self.lock_action)
        menu.addAction(self.show_text_action)
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

        qsettings = QSettings("Open Source", "FlatCAM")
        qsettings.setValue('toolbar_lock', lock)
        # This will write the setting to the platform specific storage.
        del qsettings

    def show_text_under_action(self, show_text=True):
        if show_text:
            for widget in self.children():
                if isinstance(widget, QtWidgets.QToolBar):
                    widget.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        else:
            for widget in self.children():
                if isinstance(widget, QtWidgets.QToolBar):
                    widget.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)

        qsettings = QSettings("Open Source", "FlatCAM")
        qsettings.setValue('menu_show_text', show_text)
        # This will write the setting to the platform specific storage.
        del qsettings

    def on_fullscreen(self, disable=False):
        """

        :param disable:
        :return:
        """
        flags = self.windowFlags()
        if self.toggle_fscreen is False and disable is False:
            # self.ui.showFullScreen()
            self.setWindowFlags(flags | Qt.WindowType.FramelessWindowHint)
            a = self.geometry()
            self.x_pos = a.x()
            self.y_pos = a.y()
            self.width = a.width()
            self.height = a.height()
            self.titlebar_height = self.app.qapp.style().pixelMetric(QtWidgets.QStyle.PixelMetric.PM_TitleBarHeight)

            # set new geometry to full desktop rect
            # Subtracting and adding the pixels below it's hack to bypass a bug in Qt5 and OpenGL that made that a
            # window drawn with OpenGL in fullscreen will not show any other windows on top which means that menus and
            # everything else will not work without this hack. This happen in Windows.
            # https://bugreports.qt.io/browse/QTBUG-41309
            # desktop = self.app.qapp.desktop()
            # screen = desktop.screenNumber(QtGui.QCursor.pos())

            # rec = desktop.screenGeometry(screen)

            # x = rec.x() - 1
            # y = rec.y() - 1
            # h = rec.height() + 2
            # w = rec.width() + 2
            #
            # self.setGeometry(x, y, w, h)
            # self.show()

            self.app.ui.showFullScreen()

            # hide all Toolbars
            for tb in self.findChildren(QtWidgets.QToolBar):
                if isinstance(tb, QtWidgets.QToolBar):
                    tb.setVisible(False)

            self.coords_toolbar.setVisible(self.app.defaults["global_coordsbar_show"])
            self.delta_coords_toolbar.setVisible(self.app.defaults["global_delta_coordsbar_show"])
            self.grid_toolbar.setVisible(self.app.defaults["global_gridbar_show"])
            self.status_toolbar.setVisible(self.app.defaults["global_statusbar_show"])

            self.splitter.setSizes([0, 1])
            self.toggle_fscreen = True
        elif self.toggle_fscreen is True or disable is True:
            self.setWindowFlags(flags & ~Qt.WindowType.FramelessWindowHint)
            # the additions are made to account for the pixels we subtracted/added above in the (x, y, h, w)
            # self.setGeometry(self.x_pos+1, self.y_pos+self.titlebar_height+4, self.width, self.height)
            self.setGeometry(self.x_pos+1, self.y_pos+self.titlebar_height+13, self.width, self.height)

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
            # no_km = QtCore.Qt.KeyboardModifier(QtCore.Qt.KeyboardModifier.NoModifier)    # no KB modifier
            # pos = QtCore.QPoint((self.shell._edit.width() - 40), (self.shell._edit.height() - 2))
            # e = QtGui.QMouseEvent(QtCore.QEvent.MouseButtonPress, pos, QtCore.Qt.LeftButton, QtCore.Qt.LeftButton,
            #                       no_km)
            # QtCore.QCoreApplication.instance().sendEvent(self.shell._edit, e)
            # f = QtGui.QMouseEvent(QtCore.QEvent.MouseButtonRelease, pos, QtCore.Qt.LeftButton, QtCore.Qt.LeftButton,
            #                       no_km)
            # QtCore.QCoreApplication.instance().sendEvent(self.shell._edit, f)

    def keyPressEvent(self, event):
        """
        Key event handler for the entire app.
        Some key events are also treated locally in the FlatCAM editors

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
                    modifiers = QtCore.Qt.KeyboardModifier.ControlModifier
                elif mod.lower() == 'alt':
                    modifiers = QtCore.Qt.KeyboardModifier.AltModifier
                elif mod.lower() == 'shift':
                    modifiers = QtCore.Qt.KeyboardModifier.ShiftModifier
                else:
                    modifiers = QtCore.Qt.KeyboardModifier.NoModifier
                key = QtGui.QKeySequence(key_text)

        # events from Vispy are of type KeyEvent
        else:
            key = event.key

        if self.app.call_source == 'app':
            # CTRL + ALT
            if modifiers == QtCore.Qt.KeyboardModifier.ControlModifier | QtCore.Qt.KeyboardModifier.AltModifier:
                if key == QtCore.Qt.Key.Key_X:
                    self.app.abort_all_tasks()
                    return
            # CTRL + SHIFT
            if modifiers == QtCore.Qt.KeyboardModifier.ControlModifier | QtCore.Qt.KeyboardModifier.ShiftModifier:
                if key == QtCore.Qt.Key.Key_S:
                    self.app.f_handlers.on_file_saveprojectas()
                    return
            # CTRL
            elif modifiers == QtCore.Qt.KeyboardModifier.ControlModifier:
                # Select All
                if key == QtCore.Qt.Key.Key_A:
                    self.app.on_selectall()

                # Copy an FlatCAM object
                if key == QtCore.Qt.Key.Key_C:
                    widget_name = self.plot_tab_area.currentWidget().objectName()
                    if widget_name == 'database_tab':
                        # Tools DB saved, update flag
                        self.app.tools_db_changed_flag = True
                        self.app.tools_db_tab.on_tool_copy()
                        return

                    self.app.on_copy_command()

                # Copy an FlatCAM object
                if key == QtCore.Qt.Key.Key_D:
                    self.app.on_tools_database()

                # Open Excellon file
                if key == QtCore.Qt.Key.Key_E:
                    self.app.f_handlers.on_fileopenexcellon()

                # Open Gerber file
                if key == QtCore.Qt.Key.Key_G:
                    widget_name = self.plot_tab_area.currentWidget().objectName()
                    if 'editor' in widget_name.lower():
                        self.app.goto_text_line()
                    else:
                        self.app.f_handlers.on_fileopengerber()

                # Distance Tool
                if key == QtCore.Qt.Key.Key_M:
                    self.app.distance_tool.run()

                # Create New Project
                if key == QtCore.Qt.Key.Key_N:
                    self.app.f_handlers.on_file_new_click()

                # Open Project
                if key == QtCore.Qt.Key.Key_O:
                    self.app.f_handlers.on_file_openproject()

                # Open Project
                if key == QtCore.Qt.Key.Key_P:
                    self.app.f_handlers.on_file_save_objects_pdf(use_thread=True)

                # PDF Import
                if key == QtCore.Qt.Key.Key_Q:
                    # self.app.pdf_tool.run()
                    pass

                # Save Project
                if key == QtCore.Qt.Key.Key_S:
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
                if key == QtCore.Qt.Key.Key_F10 or key == 'F10':
                    self.on_toggle_plotarea()

                return
            # SHIFT
            elif modifiers == QtCore.Qt.KeyboardModifier.ShiftModifier:

                # Toggle axis
                if key == QtCore.Qt.Key.Key_A:
                    self.app.plotcanvas.on_toggle_axis()

                # Copy Object Name
                if key == QtCore.Qt.Key.Key_C:
                    self.app.on_copy_name()

                # Toggle Code Editor
                if key == QtCore.Qt.Key.Key_E:
                    self.app.on_toggle_code_editor()

                # Toggle Grid lines
                if key == QtCore.Qt.Key.Key_G:
                    self.app.plotcanvas.on_toggle_grid_lines()
                    return

                # Toggle HUD (Heads-Up Display)
                if key == QtCore.Qt.Key.Key_H:
                    self.app.plotcanvas.on_toggle_hud()
                # Locate in Object
                if key == QtCore.Qt.Key.Key_J:
                    self.app.on_locate(obj=self.app.collection.get_active())

                # Run Distance Minimum Tool
                if key == QtCore.Qt.Key.Key_M:
                    self.app.distance_min_tool.run()
                    return

                # Open Preferences Window
                if key == QtCore.Qt.Key.Key_P:
                    self.app.on_preferences()
                    return

                # Rotate Object by 90 degree CCW
                if key == QtCore.Qt.Key.Key_R:
                    self.app.on_rotate(silent=True, preset=-float(self.app.options['tools_transform_rotate']))
                    return

                # Run a Script
                if key == QtCore.Qt.Key.Key_S:
                    self.app.f_handlers.on_filerunscript()
                    return

                # Toggle Workspace
                if key == QtCore.Qt.Key.Key_W:
                    self.app.on_workspace_toggle()
                    return

                # Skew on X axis
                if key == QtCore.Qt.Key.Key_X:
                    self.app.on_skewx()
                    return

                # Skew on Y axis
                if key == QtCore.Qt.Key.Key_Y:
                    self.app.on_skewy()
                    return
            # ALT
            elif modifiers == QtCore.Qt.KeyboardModifier.AltModifier:
                # Eanble all plots
                if key == Qt.Key.Key_1:
                    self.app.enable_all_plots()

                # Disable all plots
                if key == Qt.Key.Key_2:
                    self.app.disable_all_plots()

                # Disable all other plots
                if key == Qt.Key.Key_3:
                    self.app.enable_other_plots()

                # Disable all other plots
                if key == Qt.Key.Key_4:
                    self.app.disable_other_plots()

                # Align in Object Tool
                if key == QtCore.Qt.Key.Key_A:
                    self.app.align_objects_tool.run(toggle=True)

                # Corner Markers Tool
                if key == QtCore.Qt.Key.Key_B:
                    self.app.markers_tool.run(toggle=True)
                    return

                # Calculator Tool
                if key == QtCore.Qt.Key.Key_C:
                    self.app.calculator_tool.run(toggle=True)

                # 2-Sided PCB Tool
                if key == QtCore.Qt.Key.Key_D:
                    self.app.dblsidedtool.run(toggle=True)
                    return

                # Extract Drills  Tool
                if key == QtCore.Qt.Key.Key_E:
                    self.app.extract_tool.run(toggle=True)
                    return

                # Fiducials Tool
                if key == QtCore.Qt.Key.Key_F:
                    self.app.fiducial_tool.run(toggle=True)
                    return

                # Invert Gerber Tool
                if key == QtCore.Qt.Key.Key_G:
                    self.app.invert_tool.run(toggle=True)

                # Punch Gerber Tool
                if key == QtCore.Qt.Key.Key_H:
                    self.app.punch_tool.run(toggle=True)

                # Isolation Tool
                if key == QtCore.Qt.Key.Key_I:
                    self.app.isolation_tool.run(toggle=True)

                # Copper Thieving Tool
                if key == QtCore.Qt.Key.Key_J:
                    self.app.copper_thieving_tool.run(toggle=True)
                    return

                # Solder Paste Dispensing Tool
                if key == QtCore.Qt.Key.Key_K:
                    self.app.paste_tool.run(toggle=True)
                    return

                # Film Tool
                if key == QtCore.Qt.Key.Key_L:
                    self.app.film_tool.run(toggle=True)
                    return

                # Milling Tool
                if key == QtCore.Qt.Key.Key_M:
                    self.app.milling_tool.run(toggle=True)
                    return

                # Non-Copper Clear Tool
                if key == QtCore.Qt.Key.Key_N:
                    self.app.ncclear_tool.run(toggle=True)
                    return

                # Optimal Tool
                if key == QtCore.Qt.Key.Key_O:
                    self.app.optimal_tool.run(toggle=True)
                    return

                # Paint Tool
                if key == QtCore.Qt.Key.Key_P:
                    self.app.paint_tool.run(toggle=True)
                    return

                # QRCode Tool
                if key == QtCore.Qt.Key.Key_Q:
                    self.app.qrcode_tool.run()
                    return

                # Rules Tool
                if key == QtCore.Qt.Key.Key_R:
                    self.app.rules_tool.run(toggle=True)
                    return

                # View Source Object Content
                if key == QtCore.Qt.Key.Key_S:
                    self.app.on_view_source()
                    return

                # Transformation Tool
                if key == QtCore.Qt.Key.Key_T:
                    self.app.transform_tool.run(toggle=True)
                    return

                # Substract Tool
                if key == QtCore.Qt.Key.Key_W:
                    self.app.sub_tool.run(toggle=True)
                    return

                # Cutout Tool
                if key == QtCore.Qt.Key.Key_X:
                    self.app.cutout_tool.run(toggle=True)
                    return

                # Panelize Tool
                if key == QtCore.Qt.Key.Key_Z:
                    self.app.panelize_tool.run(toggle=True)
                    return

                # Toggle Fullscreen
                if key == QtCore.Qt.Key.Key_F10 or key == 'F10':
                    self.on_fullscreen()
                    return
            # NO MODIFIER
            elif modifiers == QtCore.Qt.KeyboardModifier.NoModifier:
                # Open Manual
                if key == QtCore.Qt.Key.Key_F1 or key == 'F1':
                    webbrowser.open(self.app.manual_url)

                # Rename Objects in the Project Tab
                if key == QtCore.Qt.Key.Key_F2:
                    self.app.collection.view.edit(self.app.collection.view.currentIndex())

                # Show shortcut list
                if key == QtCore.Qt.Key.Key_F3 or key == 'F3':
                    self.on_shortcut_list()

                # Open Video Help
                if key == QtCore.Qt.Key.Key_F4 or key == 'F4':
                    webbrowser.open(self.app.video_url)

                # Open Video Help
                if key == QtCore.Qt.Key.Key_F5 or key == 'F5':
                    self.app.plot_all()

                # Switch to Project Tab
                if key == QtCore.Qt.Key.Key_1:
                    self.on_select_tab('project')

                # Switch to Selected Tab
                if key == QtCore.Qt.Key.Key_2:
                    self.on_select_tab('properties')

                # Switch to Tool Tab
                if key == QtCore.Qt.Key.Key_3:
                    self.on_select_tab('tool')

                # Delete from PyQt
                # It's meant to make a difference between delete objects and delete tools in
                # Geometry Selected tool table
                if key == QtCore.Qt.Key.Key_Delete and matplotlib_key_flag is False:
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
                if key == QtCore.Qt.Key.Key_Escape or key == 'Escape':
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
                if key == QtCore.Qt.Key.Key_Space:
                    for select in selected:
                        select.ui.plot_cb.toggle()
                        QtWidgets.QApplication.processEvents()
                    self.app.collection.update_view()
                    self.app.delete_selection_shape()

                # Select the object in the Tree above the current one
                if key == QtCore.Qt.Key.Key_Up:
                    # make sure it works only for the Project Tab who is an instance of EventSensitiveListView
                    focused_wdg = QtWidgets.QApplication.focusWidget()
                    if isinstance(focused_wdg, EventSensitiveListView):
                        self.app.collection.set_all_inactive()
                        if active is None:
                            return
                        active_name = active.obj_options['name']
                        active_index = names_list.index(active_name)
                        if active_index == 0:
                            self.app.collection.set_active(names_list[-1])
                        else:
                            self.app.collection.set_active(names_list[active_index - 1])

                # Select the object in the Tree below the current one
                if key == QtCore.Qt.Key.Key_Down:
                    # make sure it works only for the Project Tab who is an instance of EventSensitiveListView
                    focused_wdg = QtWidgets.QApplication.focusWidget()
                    if isinstance(focused_wdg, EventSensitiveListView):
                        self.app.collection.set_all_inactive()
                        if active is None:
                            return
                        active_name = active.obj_options['name']
                        active_index = names_list.index(active_name)
                        if active_index == len(names_list) - 1:
                            self.app.collection.set_active(names_list[0])
                        else:
                            self.app.collection.set_active(names_list[active_index + 1])

                # New Geometry
                if key == QtCore.Qt.Key.Key_B:
                    self.app.app_obj.new_gerber_object()

                # New Document Object
                if key == QtCore.Qt.Key.Key_D:
                    self.app.app_obj.new_document_object()

                # Copy Object Name
                if key == QtCore.Qt.Key.Key_E:
                    self.app.object2editor()

                # Grid toggle
                if key == QtCore.Qt.Key.Key_G:
                    self.app.ui.grid_snap_btn.trigger()

                # Jump to coords
                if key == QtCore.Qt.Key.Key_J:
                    self.app.on_jump_to()

                # New Excellon
                if key == QtCore.Qt.Key.Key_L:
                    self.app.app_obj.new_excellon_object()

                # Move tool toggle
                if key == QtCore.Qt.Key.Key_M:
                    self.app.move_tool.toggle()

                # New Geometry
                if key == QtCore.Qt.Key.Key_N:
                    self.app.app_obj.new_geometry_object()

                # Set Origin
                if key == QtCore.Qt.Key.Key_O:
                    self.app.on_set_origin()
                    return

                # Properties Tool
                if key == QtCore.Qt.Key.Key_P:
                    self.app.report_tool.run(toggle=True)
                    return

                # Change Units
                if key == QtCore.Qt.Key.Key_Q:
                    # if self.app.app_units == 'MM':
                    #     self.app.ui.general_pref_form.general_app_group.units_radio.set_value("IN")
                    # else:
                    #     self.app.ui.general_pref_form.general_app_group.units_radio.set_value("MM")
                    # self.app.on_toggle_units(no_pref=True)
                    self.app.on_toggle_units_click()

                # Rotate Object by 90 degree CW
                if key == QtCore.Qt.Key.Key_R:
                    self.app.on_rotate(silent=True, preset=self.app.options['tools_transform_rotate'])

                # Shell toggle
                if key == QtCore.Qt.Key.Key_S:
                    self.toggle_shell_ui()

                # Add a Tool from shortcut
                if key == QtCore.Qt.Key.Key_T:
                    widget_name = self.plot_tab_area.currentWidget().objectName()
                    if widget_name == 'database_tab':
                        # Tools DB saved, update flag
                        self.app.tools_db_changed_flag = True
                        self.app.tools_db_tab.on_tool_add()
                        return

                    self.app.on_tool_add_keypress()

                # Zoom Fit
                if key == QtCore.Qt.Key.Key_V:
                    self.app.on_zoom_fit()

                # Mirror on X the selected object(s)
                if key == QtCore.Qt.Key.Key_X:
                    self.app.on_flipx()

                # Mirror on Y the selected object(s)
                if key == QtCore.Qt.Key.Key_Y:
                    self.app.on_flipy()

                # Zoom In
                if key == QtCore.Qt.Key.Key_Equal:
                    self.app.plotcanvas.zoom(1 / self.app.defaults['global_zoom_ratio'], self.app.mouse_pos)

                # Zoom Out
                if key == QtCore.Qt.Key.Key_Minus:
                    self.app.plotcanvas.zoom(self.app.defaults['global_zoom_ratio'], self.app.mouse_pos)

                # toggle display of Notebook area
                if key == QtCore.Qt.Key.Key_QuoteLeft:
                    self.on_toggle_notebook()

                return
        elif self.app.call_source == 'geo_editor':
            # CTRL
            if modifiers == QtCore.Qt.KeyboardModifier.ControlModifier:
                # save (update) the current geometry and return to the App
                if key == QtCore.Qt.Key.Key_S or key == 'S':
                    self.app.editor2object()
                    return

                # toggle the measurement tool
                if key == QtCore.Qt.Key.Key_M or key == 'M':
                    self.app.distance_tool.run()
                    return

                # Cut Action Tool
                if key == QtCore.Qt.Key.Key_X or key == 'X':
                    if self.app.geo_editor.get_selected() is not None:
                        self.app.geo_editor.cutpath()
                    else:
                        msg = _('Please first select a geometry item to be cut\n'
                                'then select the geometry item that will be cut\n'
                                'out of the first item. In the end press ~X~ key or\n'
                                'the toolbar button.')

                        messagebox = FCMessageBox(parent=self)
                        title = _("Warning")
                        messagebox.setWindowTitle(title)  # taskbar still shows it
                        messagebox.setWindowIcon(QtGui.QIcon(self.app.resource_location + '/app128.png'))
                        messagebox.setText('<b>%s</b>' % title)
                        messagebox.setInformativeText(msg)
                        messagebox.setIcon(QtWidgets.QMessageBox.Icon.Warning)

                        messagebox.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)
                        messagebox.setDefaultButton(QtWidgets.QMessageBox.StandardButton.Ok)
                        messagebox.exec()
                    return
            # SHIFT
            elif modifiers == QtCore.Qt.KeyboardModifier.ShiftModifier:
                # Run Distance Minimum Tool
                if key == QtCore.Qt.Key.Key_M or key == 'M':
                    self.app.distance_min_tool.run()
                    return

                # Skew on X axis
                if key == QtCore.Qt.Key.Key_X or key == 'X':
                    self.app.geo_editor.transform_tool.on_skewx_key()
                    return

                # Skew on Y axis
                if key == QtCore.Qt.Key.Key_Y or key == 'Y':
                    self.app.geo_editor.transform_tool.on_skewy_key()
                    return
            # ALT
            elif modifiers == QtCore.Qt.KeyboardModifier.AltModifier:

                # Transformation Tool
                if key == QtCore.Qt.Key.Key_R or key == 'R':
                    self.app.geo_editor.select_tool('transform')
                    return

                # Offset on X axis
                if key == QtCore.Qt.Key.Key_X or key == 'X':
                    self.app.geo_editor.transform_tool.on_offx_key()
                    return

                # Offset on Y axis
                if key == QtCore.Qt.Key.Key_Y or key == 'Y':
                    self.app.geo_editor.transform_tool.on_offy_key()
                    return
            # NO MODIFIER
            elif modifiers == QtCore.Qt.KeyboardModifier.NoModifier or \
                    modifiers == QtCore.Qt.KeyboardModifier.KeypadModifier:
                # toggle display of Notebook area
                if key == QtCore.Qt.Key.Key_QuoteLeft or key == '`':
                    self.on_toggle_notebook()

                # Finish the current action. Use with tools that do not
                # complete automatically, like a polygon or path.
                if key == QtCore.Qt.Key.Key_Enter or key == 'Enter' or key == QtCore.Qt.Key.Key_Return:
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
                            if self.app.geo_editor.active_tool.name == 'path' \
                                    and self.app.geo_editor.active_tool.path_tool.length != 0.0:
                                pass
                            elif self.app.geo_editor.active_tool.name == 'polygon' \
                                    and self.app.geo_editor.active_tool.polygon_tool.length != 0.0:
                                pass
                            elif self.app.geo_editor.active_tool.name == 'circle' \
                                    and self.app.geo_editor.active_tool.circle_tool.x != 0.0 \
                                    and self.app.geo_editor.active_tool.circle_tool.y != 0.0:
                                pass
                            elif self.app.geo_editor.active_tool.name == 'rectangle' \
                                    and self.app.geo_editor.active_tool.rect_tool.length != 0.0 \
                                    and self.app.geo_editor.active_tool.rect_tool.width != 0.0:
                                pass
                            elif self.app.geo_editor.active_tool.name == 'move' \
                                    and self.app.geo_editor.active_tool.move_tool.length != 0.0 \
                                    and self.app.geo_editor.active_tool.move_tool.width != 0.0:
                                pass
                            elif self.app.geo_editor.active_tool.name == 'copy' \
                                    and self.app.geo_editor.active_tool.copy_tool.length != 0.0 \
                                    and self.app.geo_editor.active_tool.copy_tool.width != 0.0:
                                pass
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
                if key == QtCore.Qt.Key.Key_Escape or key == 'Escape':
                    # self.on_tool_select("select")
                    self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled."))

                    self.app.geo_editor.delete_utility_geometry()
                    self.app.geo_editor.active_tool.clean_up()
                    self.app.geo_editor.select_tool('select')

                    return

                # Delete selected object
                if key == QtCore.Qt.Key.Key_Delete or key == 'Delete':
                    self.app.geo_editor.delete_selected()
                    self.app.geo_editor.plot_all()

                # Rotate
                if key == QtCore.Qt.Key.Key_Space or key == 'Space':
                    self.app.geo_editor.transform_tool.on_rotate_key()

                # Zoom Out
                if key == QtCore.Qt.Key.Key_Minus or key == '-':
                    self.app.plotcanvas.zoom(1 / self.app.defaults['global_zoom_ratio'],
                                             [self.app.geo_editor.snap_x, self.app.geo_editor.snap_y])

                # Zoom In
                if key == QtCore.Qt.Key.Key_Equal or key == '=':
                    self.app.plotcanvas.zoom(self.app.defaults['global_zoom_ratio'],
                                             [self.app.geo_editor.snap_x, self.app.geo_editor.snap_y])

                # # Switch to Project Tab
                # if key == QtCore.Qt.Key.Key_1 or key == '1':
                #     self.on_select_tab('project')
                #
                # # Switch to Selected Tab
                # if key == QtCore.Qt.Key.Key_2 or key == '2':
                #     self.on_select_tab('selected')
                #
                # # Switch to Tool Tab
                # if key == QtCore.Qt.Key.Key_3 or key == '3':
                #     self.on_select_tab('tool')

                # Grid Snap
                if key == QtCore.Qt.Key.Key_G or key == 'G':
                    self.app.ui.grid_snap_btn.trigger()

                    # make sure that the cursor shape is enabled/disabled, too
                    if self.app.geo_editor.editor_options['grid_snap'] is True:
                        self.app.app_cursor.enabled = True
                    else:
                        self.app.app_cursor.enabled = False

                # Corner Snap
                if key == QtCore.Qt.Key.Key_K or key == 'K':
                    self.app.geo_editor.on_corner_snap()

                if key == QtCore.Qt.Key.Key_V or key == 'V':
                    self.app.on_zoom_fit()

                # we do this so we can reuse the following keys while inside a Tool
                # the above keys are general enough so were left outside
                if self.app.geo_editor.active_tool is not None and self.geo_select_btn.isChecked() is False:
                    response = self.app.geo_editor.active_tool.on_key(key=key)
                    if response is not None:
                        self.app.inform.emit(response)
                else:
                    # Arc Tool
                    if key == QtCore.Qt.Key.Key_A or key == 'A':
                        self.app.geo_editor.select_tool('arc')

                    # Buffer
                    if key == QtCore.Qt.Key.Key_B or key == 'B':
                        self.app.geo_editor.select_tool('buffer')

                    # Copy
                    if key == QtCore.Qt.Key.Key_C or key == 'C':
                        self.app.geo_editor.select_tool('copy')
                        # self.app.geo_editor.on_copy_click()

                    # Substract Tool
                    if key == QtCore.Qt.Key.Key_E or key == 'E':
                        if self.app.geo_editor.get_selected() is not None:
                            self.app.geo_editor.intersection()
                        else:
                            msg = _("Please select geometry items \n"
                                    "on which to perform Intersection Tool.")

                            messagebox = FCMessageBox(parent=self)
                            title = _("Warning")
                            messagebox.setWindowTitle(title)  # taskbar still shows it
                            messagebox.setWindowIcon(QtGui.QIcon(self.app.resource_location + '/app128.png'))
                            messagebox.setText('<b>%s</b>' % title)
                            messagebox.setInformativeText(msg)
                            messagebox.setIcon(QtWidgets.QMessageBox.Icon.Warning)

                            messagebox.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)
                            messagebox.setDefaultButton(QtWidgets.QMessageBox.StandardButton.Ok)
                            messagebox.exec()

                    # Paint
                    if key == QtCore.Qt.Key.Key_I or key == 'I':
                        self.app.geo_editor.select_tool('paint')

                    # Jump to coords
                    if key == QtCore.Qt.Key.Key_J or key == 'J':
                        self.app.on_jump_to()

                    # Move
                    if key == QtCore.Qt.Key.Key_M or key == 'M':
                        self.app.geo_editor.select_tool('move')
                        # self.app.geo_editor.on_move_click()

                    # Polygon Tool
                    if key == QtCore.Qt.Key.Key_N or key == 'N':
                        self.app.geo_editor.select_tool('polygon')

                    # Circle Tool
                    if key == QtCore.Qt.Key.Key_O or key == 'O':
                        self.app.geo_editor.select_tool('circle')

                    # Path Tool
                    if key == QtCore.Qt.Key.Key_P or key == 'P':
                        self.app.geo_editor.select_tool('path')

                    # Rectangle Tool
                    if key == QtCore.Qt.Key.Key_R or key == 'R':
                        self.app.geo_editor.select_tool('rectangle')

                    # Substract Tool
                    if key == QtCore.Qt.Key.Key_S or key == 'S':
                        if self.app.geo_editor.get_selected() is not None:
                            self.app.geo_editor.subtract()
                        else:
                            msg = _(
                                "Please select geometry items \n"
                                "on which to perform Subtraction.")

                            messagebox = FCMessageBox(parent=self)
                            title = _("Warning")
                            messagebox.setWindowTitle(title)  # taskbar still shows it
                            messagebox.setWindowIcon(QtGui.QIcon(self.app.resource_location + '/app128.png'))
                            messagebox.setText('<b>%s</b>' % title)
                            messagebox.setInformativeText(msg)
                            messagebox.setIcon(QtWidgets.QMessageBox.Icon.Warning)

                            messagebox.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)
                            messagebox.setDefaultButton(QtWidgets.QMessageBox.StandardButton.Ok)
                            messagebox.exec()

                    # Add Text Tool
                    if key == QtCore.Qt.Key.Key_T or key == 'T':
                        self.app.geo_editor.select_tool('text')

                    # Substract Tool
                    if key == QtCore.Qt.Key.Key_U or key == 'U':
                        if self.app.geo_editor.get_selected() is not None:
                            self.app.geo_editor.union()
                        else:
                            msg = _("Please select geometry items \n"
                                    "on which to perform union.")

                            messagebox = FCMessageBox(parent=self)
                            title = _("Warning")
                            messagebox.setWindowTitle(title)  # taskbar still shows it
                            messagebox.setWindowIcon(QtGui.QIcon(self.app.resource_location + '/app128.png'))
                            messagebox.setText('<b>%s</b>' % title)
                            messagebox.setInformativeText(msg)
                            messagebox.setIcon(QtWidgets.QMessageBox.Icon.Warning)

                            messagebox.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)
                            messagebox.setDefaultButton(QtWidgets.QMessageBox.StandardButton.Ok)
                            messagebox.exec()

                    # Flip on X axis
                    if key == QtCore.Qt.Key.Key_X or key == 'X':
                        self.app.geo_editor.transform_tool.on_flipx()
                        return

                    # Flip on Y axis
                    if key == QtCore.Qt.Key.Key_Y or key == 'Y':
                        self.app.geo_editor.transform_tool.on_flipy()
                        return

                # Show Shortcut list
                if key == 'F3':
                    self.on_shortcut_list()
        elif self.app.call_source == 'grb_editor':
            # CTRL
            if modifiers == QtCore.Qt.KeyboardModifier.ControlModifier:
                # Select All
                if key == QtCore.Qt.Key.Key_E or key == 'A':
                    self.app.grb_editor.ui.apertures_table.selectAll()
                    return

                # Eraser Tool
                if key == QtCore.Qt.Key.Key_E or key == 'E':
                    self.app.grb_editor.on_eraser()
                    return

                # save (update) the current geometry and return to the App
                if key == QtCore.Qt.Key.Key_S or key == 'S':
                    self.app.editor2object()
                    return

                # toggle the measurement tool
                if key == QtCore.Qt.Key.Key_M or key == 'M':
                    self.app.distance_tool.run()
                    return
            # SHIFT
            elif modifiers == QtCore.Qt.KeyboardModifier.ShiftModifier:
                # Run Distance Minimum Tool
                if key == QtCore.Qt.Key.Key_M or key == 'M':
                    self.app.distance_min_tool.run()
                    return
            # ALT
            elif modifiers == QtCore.Qt.KeyboardModifier.AltModifier:
                # Mark Area Tool
                if key == QtCore.Qt.Key.Key_A or key == 'A':
                    self.app.grb_editor.on_markarea()
                    return

                # Poligonize Tool
                if key == QtCore.Qt.Key.Key_N or key == 'N':
                    self.app.grb_editor.on_poligonize()
                    return
                # Transformation Tool
                if key == QtCore.Qt.Key.Key_R or key == 'R':
                    self.app.grb_editor.on_transform()
                    return
            # NO MODIFIER
            elif modifiers == QtCore.Qt.KeyboardModifier.NoModifier or \
                    modifiers == QtCore.Qt.KeyboardModifier.KeypadModifier:
                # Abort the current action
                if key == QtCore.Qt.Key.Key_Escape or key == 'Escape':
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
                if key == QtCore.Qt.Key.Key_Delete:
                    self.app.grb_editor.launched_from_shortcuts = True
                    self.app.grb_editor.on_aperture_delete()
                    return

                if key == QtCore.Qt.Key.Key_Minus or key == '-':
                    self.app.grb_editor.launched_from_shortcuts = True
                    self.app.plotcanvas.zoom(1 / self.app.defaults['global_zoom_ratio'],
                                             [self.app.grb_editor.snap_x, self.app.grb_editor.snap_y])
                    return

                if key == QtCore.Qt.Key.Key_Equal or key == '=':
                    self.app.grb_editor.launched_from_shortcuts = True
                    self.app.plotcanvas.zoom(self.app.defaults['global_zoom_ratio'],
                                             [self.app.grb_editor.snap_x, self.app.grb_editor.snap_y])
                    return

                # toggle display of Notebook area
                if key == QtCore.Qt.Key.Key_QuoteLeft or key == '`':
                    self.app.grb_editor.launched_from_shortcuts = True
                    self.on_toggle_notebook()
                    return

                # # Switch to Project Tab
                # if key == QtCore.Qt.Key.Key_1 or key == '1':
                #     self.app.grb_editor.launched_from_shortcuts = True
                #     self.on_select_tab('project')
                #     return
                #
                # # Switch to Selected Tab
                # if key == QtCore.Qt.Key.Key_2 or key == '2':
                #     self.app.grb_editor.launched_from_shortcuts = True
                #     self.on_select_tab('selected')
                #     return
                #
                # # Switch to Tool Tab
                # if key == QtCore.Qt.Key.Key_3 or key == '3':
                #     self.app.grb_editor.launched_from_shortcuts = True
                #     self.on_select_tab('tool')
                #     return

                # we do this so we can reuse the following keys while inside a Tool
                # the above keys are general enough so were left outside
                if self.app.grb_editor.active_tool is not None and self.grb_select_btn.isChecked() is False:
                    response = self.app.grb_editor.active_tool.on_key(key=key)
                    if response is not None:
                        self.app.inform.emit(response)
                else:

                    # Rotate
                    if key == QtCore.Qt.Key.Key_Space or key == 'Space':
                        self.app.grb_editor.transform_tool.on_rotate_key()

                    # Add Array of pads
                    if key == QtCore.Qt.Key.Key_A or key == 'A':
                        self.app.grb_editor.launched_from_shortcuts = True
                        self.app.inform.emit("Click on target point.")
                        self.app.ui.add_pad_ar_btn.setChecked(True)

                        self.app.grb_editor.x = self.app.mouse_pos[0]
                        self.app.grb_editor.y = self.app.mouse_pos[1]

                        self.app.grb_editor.select_tool('array')
                        return

                    # Scale Tool
                    if key == QtCore.Qt.Key.Key_B or key == 'B':
                        self.app.grb_editor.launched_from_shortcuts = True
                        self.app.grb_editor.select_tool('buffer')
                        return

                    # Copy
                    if key == QtCore.Qt.Key.Key_C or key == 'C':
                        self.app.grb_editor.launched_from_shortcuts = True
                        if self.app.grb_editor.selected:
                            self.app.inform.emit(_("Click on target point."))
                            self.app.ui.aperture_copy_btn.setChecked(True)
                            self.app.grb_editor.on_tool_select('copy')
                            if self.app.grb_editor.active_tool is not None:
                                self.app.grb_editor.active_tool.set_origin(
                                    (self.app.grb_editor.snap_x, self.app.grb_editor.snap_y))
                        else:
                            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled. Nothing selected."))
                        return

                    # Add Disc Tool
                    if key == QtCore.Qt.Key.Key_D or key == 'D':
                        self.app.grb_editor.launched_from_shortcuts = True
                        self.app.grb_editor.select_tool('disc')
                        return

                    # Add SemiDisc Tool
                    if key == QtCore.Qt.Key.Key_E or key == 'E':
                        self.app.grb_editor.launched_from_shortcuts = True
                        self.app.grb_editor.select_tool('semidisc')
                        return

                    # Grid Snap
                    if key == QtCore.Qt.Key.Key_G or key == 'G':
                        self.app.grb_editor.launched_from_shortcuts = True
                        # make sure that the cursor shape is enabled/disabled, too
                        if self.app.grb_editor.editor_options['grid_snap'] is True:
                            self.app.app_cursor.enabled = False
                        else:
                            self.app.app_cursor.enabled = True
                        self.app.ui.grid_snap_btn.trigger()
                        return

                    # Jump to coords
                    if key == QtCore.Qt.Key.Key_J or key == 'J':
                        self.app.on_jump_to()

                    # Corner Snap
                    if key == QtCore.Qt.Key.Key_K or key == 'K':
                        self.app.grb_editor.launched_from_shortcuts = True
                        self.app.ui.corner_snap_btn.trigger()
                        return

                    # Move
                    if key == QtCore.Qt.Key.Key_M or key == 'M':
                        self.app.grb_editor.launched_from_shortcuts = True
                        if self.app.grb_editor.selected:
                            self.app.inform.emit(_("Click on target point."))
                            self.app.ui.aperture_move_btn.setChecked(True)
                            self.app.grb_editor.on_tool_select('move')
                            if self.app.grb_editor.active_tool is not None:
                                self.app.grb_editor.active_tool.set_origin(
                                    (self.app.grb_editor.snap_x, self.app.grb_editor.snap_y))
                        else:
                            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled. Nothing selected."))
                        return

                    # Add Region Tool
                    if key == QtCore.Qt.Key.Key_N or key == 'N':
                        self.app.grb_editor.launched_from_shortcuts = True
                        self.app.grb_editor.select_tool('region')
                        return

                    # Add Pad Tool
                    if key == QtCore.Qt.Key.Key_P or key == 'P':
                        self.app.grb_editor.launched_from_shortcuts = True
                        self.app.inform.emit(_("Click on target point."))
                        self.app.ui.add_pad_ar_btn.setChecked(True)

                        self.app.grb_editor.x = self.app.mouse_pos[0]
                        self.app.grb_editor.y = self.app.mouse_pos[1]

                        self.app.grb_editor.select_tool('pad')
                        return

                    # Scale Tool
                    if key == QtCore.Qt.Key.Key_S or key == 'S':
                        self.app.grb_editor.launched_from_shortcuts = True
                        self.app.grb_editor.select_tool('scale')
                        return

                    # Add Track
                    if key == QtCore.Qt.Key.Key_T or key == 'T':
                        self.app.grb_editor.launched_from_shortcuts = True
                        # ## Current application units in Upper Case
                        self.app.grb_editor.select_tool('track')
                        return

                    # Zoom fit
                    if key == QtCore.Qt.Key.Key_V or key == 'V':
                        self.app.grb_editor.launched_from_shortcuts = True
                        self.app.grb_editor.on_zoom_fit()
                        return

                # Show Shortcut list
                if key == QtCore.Qt.Key.Key_F3 or key == 'F3':
                    self.on_shortcut_list()
                    return
        elif self.app.call_source == 'exc_editor':
            # CTRL
            if modifiers == QtCore.Qt.KeyboardModifier.ControlModifier:
                # Select All
                if key == QtCore.Qt.Key.Key_E or key == 'A':
                    self.app.exc_editor.ui.tools_table_exc.selectAll()
                    return

                # save (update) the current geometry and return to the App
                if key == QtCore.Qt.Key.Key_S or key == 'S':
                    self.app.editor2object()
                    return

                # toggle the measurement tool
                if key == QtCore.Qt.Key.Key_M or key == 'M':
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
            elif modifiers == QtCore.Qt.KeyboardModifier.ShiftModifier:
                # Run Distance Minimum Tool
                if key == QtCore.Qt.Key.Key_M or key == 'M':
                    self.app.distance_min_tool.run()
                    return
            # ALT
            elif modifiers == QtCore.Qt.KeyboardModifier.AltModifier:
                pass
            # NO MODIFIER
            elif modifiers == QtCore.Qt.KeyboardModifier.NoModifier or \
                    modifiers == QtCore.Qt.KeyboardModifier.KeypadModifier:
                # Abort the current action
                if key == QtCore.Qt.Key.Key_Escape or key == 'Escape':
                    self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled."))

                    self.app.exc_editor.delete_utility_geometry()
                    self.app.exc_editor.active_tool.clean_up()
                    self.app.exc_editor.select_tool('drill_select')
                    return

                # Finish the current action. Use with tools that do not
                # complete automatically.
                if key == QtCore.Qt.Key.Key_Enter or key == 'Enter' or key == QtCore.Qt.Key.Key_Return:
                    if isinstance(self.app.exc_editor.active_tool, FCShapeTool):
                        if self.app.exc_editor.active_tool.name == 'drill_add' \
                                and self.app.exc_editor.active_tool.drill_tool.length != 0.0:
                            pass
                        # elif self.app.exc_editor.active_tool.name == 'drill_array' \
                        #         and self.app.exc_editor.active_tool.darray_tool.length != 0.0:
                        #     pass
                        elif self.app.exc_editor.active_tool.name == 'slot_add' \
                                and self.app.exc_editor.active_tool.slot_tool.length != 0.0 :
                            pass
                        # elif self.app.exc_editor.active_tool.name == 'slot_array' \
                        #         and self.app.exc_editor.active_tool.sarray_tool.length != 0.0:
                        #     pass
                        elif self.app.exc_editor.active_tool.name == 'drill_move' \
                                and self.app.exc_editor.active_tool.move_tool.length != 0.0 \
                                and self.app.exc_editor.active_tool.move_tool.width != 0.0:
                            pass
                        elif self.app.exc_editor.active_tool.name == 'drill_copy' \
                                and self.app.exc_editor.active_tool.copy_tool.length != 0.0:
                            pass
                        else:
                            curr_pos = self.app.exc_editor.snap_x, self.app.exc_editor.snap_y
                            self.app.exc_editor.on_canvas_click_left_handler(curr_pos)

                            if self.app.exc_editor.active_tool.complete:
                                self.app.exc_editor.on_shape_complete()
                                self.app.inform.emit('[success] %s' % _("Done."))

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
                if key == QtCore.Qt.Key.Key_Delete:
                    self.app.exc_editor.launched_from_shortcuts = True
                    self.app.exc_editor.on_tool_delete()
                    return

                if key == QtCore.Qt.Key.Key_Minus or key == '-':
                    self.app.exc_editor.launched_from_shortcuts = True
                    self.app.plotcanvas.zoom(1 / self.app.defaults['global_zoom_ratio'],
                                             [self.app.exc_editor.snap_x, self.app.exc_editor.snap_y])
                    return

                if key == QtCore.Qt.Key.Key_Equal or key == '=':
                    self.app.exc_editor.launched_from_shortcuts = True
                    self.app.plotcanvas.zoom(self.app.defaults['global_zoom_ratio'],
                                             [self.app.exc_editor.snap_x, self.app.exc_editor.snap_y])
                    return

                # toggle display of Notebook area
                if key == QtCore.Qt.Key.Key_QuoteLeft or key == '`':
                    self.app.exc_editor.launched_from_shortcuts = True
                    self.on_toggle_notebook()
                    return

                # # Switch to Project Tab
                # if key == QtCore.Qt.Key.Key_1 or key == '1':
                #     self.app.exc_editor.launched_from_shortcuts = True
                #     self.on_select_tab('project')
                #     return
                #
                # # Switch to Selected Tab
                # if key == QtCore.Qt.Key.Key_2 or key == '2':
                #     self.app.exc_editor.launched_from_shortcuts = True
                #     self.on_select_tab('selected')
                #     return
                #
                # # Switch to Tool Tab
                # if key == QtCore.Qt.Key.Key_3 or key == '3':
                #     self.app.exc_editor.launched_from_shortcuts = True
                #     self.on_select_tab('tool')
                #     return

                # Grid Snap
                if key == QtCore.Qt.Key.Key_G or key == 'G':
                    self.app.exc_editor.launched_from_shortcuts = True
                    # make sure that the cursor shape is enabled/disabled, too
                    if self.app.exc_editor.editor_options['grid_snap'] is True:
                        self.app.app_cursor.enabled = False
                    else:
                        self.app.app_cursor.enabled = True
                    self.app.ui.grid_snap_btn.trigger()
                    return

                # Corner Snap
                if key == QtCore.Qt.Key.Key_K or key == 'K':
                    self.app.exc_editor.launched_from_shortcuts = True
                    self.app.ui.corner_snap_btn.trigger()
                    return

                # Zoom Fit
                if key == QtCore.Qt.Key.Key_V or key == 'V':
                    self.app.exc_editor.launched_from_shortcuts = True
                    self.app.on_zoom_fit()
                    return

                # Add Slot Hole Tool
                if key == QtCore.Qt.Key.Key_W or key == 'W':
                    self.app.exc_editor.launched_from_shortcuts = True
                    self.app.inform.emit(_("Click on target point."))
                    self.app.ui.add_slot_btn.setChecked(True)

                    self.app.exc_editor.x = self.app.mouse_pos[0]
                    self.app.exc_editor.y = self.app.mouse_pos[1]

                    self.app.exc_editor.select_tool('slot_add')
                    return

                # Show Shortcut list
                if key == QtCore.Qt.Key.Key_F3 or key == 'F3':
                    self.on_shortcut_list()
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
                    if key == QtCore.Qt.Key.Key_A or key == 'A':
                        self.app.exc_editor.launched_from_shortcuts = True
                        self.app.inform.emit("Click on target point.")
                        self.app.ui.add_drill_array_btn.setChecked(True)

                        self.app.exc_editor.x = self.app.mouse_pos[0]
                        self.app.exc_editor.y = self.app.mouse_pos[1]

                        self.app.exc_editor.select_tool('drill_array')
                        return

                    # Copy
                    if key == QtCore.Qt.Key.Key_C or key == 'C':
                        self.app.exc_editor.launched_from_shortcuts = True
                        if self.app.exc_editor.selected:
                            self.app.inform.emit(_("Click on target point."))
                            self.app.ui.copy_drill_btn.setChecked(True)
                            self.app.exc_editor.on_tool_select('drill_copy')
                            if self.app.exc_editor.active_tool is not None:
                                self.app.exc_editor.active_tool.set_origin(
                                    (self.app.exc_editor.snap_x, self.app.exc_editor.snap_y))
                        else:
                            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled. Nothing selected."))
                        return

                    # Add Drill Hole Tool
                    if key == QtCore.Qt.Key.Key_D or key == 'D':
                        self.app.exc_editor.launched_from_shortcuts = True
                        self.app.inform.emit(_("Click on target point."))
                        self.app.ui.add_drill_btn.setChecked(True)

                        self.app.exc_editor.x = self.app.mouse_pos[0]
                        self.app.exc_editor.y = self.app.mouse_pos[1]

                        self.app.exc_editor.select_tool('drill_add')
                        return

                    # Jump to coords
                    if key == QtCore.Qt.Key.Key_J or key == 'J':
                        self.app.on_jump_to()

                    # Move
                    if key == QtCore.Qt.Key.Key_M or key == 'M':
                        self.app.exc_editor.launched_from_shortcuts = True
                        if self.app.exc_editor.selected:
                            self.app.inform.emit(_("Click on target location ..."))
                            self.app.ui.move_drill_btn.setChecked(True)
                            self.app.exc_editor.on_tool_select('drill_move')
                            if self.app.exc_editor.active_tool is not None:
                                self.app.exc_editor.active_tool.set_origin(
                                    (self.app.exc_editor.snap_x, self.app.exc_editor.snap_y))
                        else:
                            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled. Nothing selected."))
                        return

                    # Add Array of Slots Hole Tool
                    if key == QtCore.Qt.Key.Key_Q or key == 'Q':
                        self.app.exc_editor.launched_from_shortcuts = True
                        self.app.inform.emit("Click on target point.")
                        self.app.ui.add_slot_array_btn.setChecked(True)

                        self.app.exc_editor.x = self.app.mouse_pos[0]
                        self.app.exc_editor.y = self.app.mouse_pos[1]

                        self.app.exc_editor.select_tool('slot_array')
                        return

                    # Resize Tool
                    if key == QtCore.Qt.Key.Key_R or key == 'R':
                        self.app.exc_editor.launched_from_shortcuts = True
                        self.app.exc_editor.select_tool('drill_resize')
                        return

                    # Add Tool
                    if key == QtCore.Qt.Key.Key_T or key == 'T':
                        self.app.exc_editor.launched_from_shortcuts = True
                        # ## Current application units in Upper Case
                        self.units = self.general_pref_form.general_app_group.units_radio.get_value().upper()
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
            if modifiers == QtCore.Qt.KeyboardModifier.ControlModifier:
                # save (update) the current geometry and return to the App
                if key == QtCore.Qt.Key.Key_S or key == 'S':
                    self.app.editor2object(force_cancel=True)
                    return
            # SHIFT
            elif modifiers == QtCore.Qt.KeyboardModifier.ShiftModifier:
                pass
            # ALT
            elif modifiers == QtCore.Qt.KeyboardModifier.AltModifier:
                pass
            # NO MODIFIER
            elif modifiers == QtCore.Qt.KeyboardModifier.NoModifier:
                pass
        elif self.app.call_source == 'measurement':
            if modifiers == QtCore.Qt.KeyboardModifier.ControlModifier:
                pass
            elif modifiers == QtCore.Qt.KeyboardModifier.AltModifier:
                pass
            elif modifiers == QtCore.Qt.KeyboardModifier.ShiftModifier:
                pass
            # NO MODIFIER
            elif modifiers == QtCore.Qt.KeyboardModifier.NoModifier:
                if key == QtCore.Qt.Key.Key_Escape or key == 'Escape':
                    # abort the measurement action
                    self.app.distance_tool.on_exit()
                    self.app.inform.emit(_("Cancelled."))
                    return

                if key == QtCore.Qt.Key.Key_G or key == 'G':
                    self.app.ui.grid_snap_btn.trigger()
                    if self.app.distance_tool.ui.big_cursor_cb.get_value():
                        self.app.app_cursor.enabled = True
                    return

                # Jump to coords
                if key == QtCore.Qt.Key.Key_J or key == 'J':
                    self.app.on_jump_to()
        elif self.app.call_source == 'qrcode_tool':
            # CTRL + ALT
            if modifiers == QtCore.Qt.KeyboardModifier.ControlModifier | QtCore.Qt.KeyboardModifier.AltModifier:
                if key == QtCore.Qt.Key.Key_X:
                    self.app.abort_all_tasks()
                    return

            elif modifiers == QtCore.Qt.KeyboardModifier.ControlModifier:
                pass
            elif modifiers == QtCore.Qt.KeyboardModifier.ShiftModifier:
                pass
            elif modifiers == QtCore.Qt.KeyboardModifier.AltModifier:
                pass
            # NO MODIFIER
            elif modifiers == QtCore.Qt.KeyboardModifier.NoModifier:
                # Escape = Deselect All
                if key == QtCore.Qt.Key.Key_Escape or key == 'Escape':
                    self.app.qrcode_tool.on_exit()

                # Grid toggle
                if key == QtCore.Qt.Key.Key_G:
                    self.app.ui.grid_snap_btn.trigger()

                # Jump to coords
                if key == QtCore.Qt.Key.Key_J:
                    self.app.on_jump_to()
        elif self.app.call_source == 'copper_thieving_tool':
            # CTRL + ALT
            if modifiers == QtCore.Qt.KeyboardModifier.ControlModifier | QtCore.Qt.KeyboardModifier.AltModifier:
                if key == QtCore.Qt.Key.Key_X:
                    self.app.abort_all_tasks()
                    return
            elif modifiers == QtCore.Qt.KeyboardModifier.ControlModifier:
                pass
            elif modifiers == QtCore.Qt.KeyboardModifier.ShiftModifier:
                pass
            elif modifiers == QtCore.Qt.KeyboardModifier.AltModifier:
                pass
            # NO MODIFIER
            elif modifiers == QtCore.Qt.KeyboardModifier.NoModifier:
                # Escape = Deselect All
                if key == QtCore.Qt.Key.Key_Escape or key == 'Escape':
                    self.app.copperfill_tool.on_exit()

                # Grid toggle
                if key == QtCore.Qt.Key.Key_G:
                    self.app.ui.grid_snap_btn.trigger()

                # Jump to coords
                if key == QtCore.Qt.Key.Key_J:
                    self.app.on_jump_to()
        elif self.app.call_source == '2_sided_tool':
            # CTRL + ALT
            if modifiers == QtCore.Qt.KeyboardModifier.ControlModifier | QtCore.Qt.KeyboardModifier.AltModifier:
                if key == QtCore.Qt.Key.Key_X:
                    self.app.abort_all_tasks()
                    return
            elif modifiers == QtCore.Qt.KeyboardModifier.ControlModifier:
                pass
            elif modifiers == QtCore.Qt.KeyboardModifier.ShiftModifier:
                pass
            elif modifiers == QtCore.Qt.KeyboardModifier.AltModifier:
                pass
            # NO MODIFIER
            elif modifiers == QtCore.Qt.KeyboardModifier.NoModifier:
                # Escape = Deselect All
                if key == QtCore.Qt.Key.Key_Escape or key == 'Escape':
                    self.app.dblsidedtool.on_exit(cancelled=True)

                # Grid toggle
                if key == QtCore.Qt.Key.Key_G:
                    self.app.ui.grid_snap_btn.trigger()

                # Jump to coords
                if key == QtCore.Qt.Key.Key_J:
                    self.app.on_jump_to()
        elif self.app.call_source == 'geometry':
            # used for Exclusion Areas
            if modifiers == QtCore.Qt.KeyboardModifier.ControlModifier:
                pass
            elif modifiers == QtCore.Qt.KeyboardModifier.AltModifier:
                pass
            elif modifiers == QtCore.Qt.KeyboardModifier.ShiftModifier:
                pass
            # NO MODIFIER
            elif modifiers == QtCore.Qt.KeyboardModifier.NoModifier:
                if key == QtCore.Qt.Key.Key_Escape or key == 'Escape':
                    sel_obj = self.app.collection.get_active()
                    assert sel_obj.kind == 'geometry' or sel_obj.kind == 'excellon', \
                        "Expected a Geometry or Excellon Object, got %s" % type(sel_obj)

                    sel_obj.area_disconnect()
                    return

                if key == QtCore.Qt.Key.Key_G or key == 'G':
                    self.app.ui.grid_snap_btn.trigger()
                    return

                # Jump to coords
                if key == QtCore.Qt.Key.Key_J or key == 'J':
                    self.app.on_jump_to()
        elif self.app.call_source == 'fiducials_tool':
            # CTRL + ALT
            if modifiers == QtCore.Qt.KeyboardModifier.ControlModifier | QtCore.Qt.KeyboardModifier.AltModifier:
                if key == QtCore.Qt.Key.Key_X:
                    self.app.abort_all_tasks()
                    return
            elif modifiers == QtCore.Qt.KeyboardModifier.ControlModifier:
                pass
            elif modifiers == QtCore.Qt.KeyboardModifier.ShiftModifier:
                pass
            elif modifiers == QtCore.Qt.KeyboardModifier.AltModifier:
                pass
            # NO MODIFIER
            elif modifiers == QtCore.Qt.KeyboardModifier.NoModifier:
                # Escape = Deselect All
                if key == QtCore.Qt.Key.Key_Escape or key == 'Escape':
                    self.app.fiducial_tool.on_exit(cancelled=True)

                # Grid toggle
                if key == QtCore.Qt.Key.Key_G:
                    self.app.ui.grid_snap_btn.trigger()

                # Jump to coords
                if key == QtCore.Qt.Key.Key_J:
                    self.app.on_jump_to()
        elif self.app.call_source == 'markers_tool':
            # CTRL + ALT
            if modifiers == QtCore.Qt.KeyboardModifier.ControlModifier | QtCore.Qt.KeyboardModifier.AltModifier:
                if key == QtCore.Qt.Key.Key_X:
                    self.app.abort_all_tasks()
                    return
            elif modifiers == QtCore.Qt.KeyboardModifier.ControlModifier:
                pass
            elif modifiers == QtCore.Qt.KeyboardModifier.ShiftModifier:
                pass
            elif modifiers == QtCore.Qt.KeyboardModifier.AltModifier:
                pass
            # NO MODIFIER
            elif modifiers == QtCore.Qt.KeyboardModifier.NoModifier:
                # Escape = Deselect All
                if key == QtCore.Qt.Key.Key_Escape or key == 'Escape':
                    self.app.markers_tool.on_exit(cancelled=True)

                # Grid toggle
                if key == QtCore.Qt.Key.Key_G:
                    self.app.ui.grid_snap_btn.trigger()

                # Jump to coords
                if key == QtCore.Qt.Key.Key_J:
                    self.app.on_jump_to()

    def eventFilter(self, obj, event):
        """
        Filter the ToolTips display based on a Preferences setting

        :param obj:
        :param event: QT event to filter
        :return:
        """
        if self.app.options["global_toggle_tooltips"] is False:
            if event.type() == QtCore.QEvent.Type.ToolTip:
                return True
            else:
                return False

        return False

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
            event.setDropAction(QtCore.Qt.DropAction.CopyAction)
            event.accept()
            for url in event.mimeData().urls():
                self.filename = str(url.toLocalFile())

                if self.filename == "":
                    self.app.inform.emit("Cancelled.")
                else:
                    extension = self.filename.lower().rpartition('.')[-1]

                    if extension in self.app.regFK.grb_list:
                        self.app.worker_task.emit({'fcn': self.app.f_handlers.open_gerber,
                                                   'params': [self.filename]})
                    else:
                        event.ignore()

                    if extension in self.app.regFK.exc_list:
                        self.app.worker_task.emit({'fcn': self.app.f_handlers.open_excellon,
                                                   'params': [self.filename]})
                    else:
                        event.ignore()

                    if extension in self.app.regFK.gcode_list:
                        self.app.worker_task.emit({'fcn': self.app.f_handlers.open_gcode,
                                                   'params': [self.filename]})
                    else:
                        event.ignore()

                    if extension in self.app.regFK.svg_list:
                        object_type = 'geometry'
                        self.app.worker_task.emit({'fcn': self.app.f_handlers.import_svg,
                                                   'params': [self.filename, object_type, None]})

                    if extension in self.app.regFK.dxf_list:
                        object_type = 'geometry'
                        self.app.worker_task.emit({'fcn': self.app.f_handlers.import_dxf,
                                                   'params': [self.filename, object_type, None]})

                    if extension in self.app.regFK.pdf_list:
                        self.app.pdf_tool.periodic_check(1000)
                        self.app.worker_task.emit({'fcn': self.app.pdf_tool.open_pdf,
                                                   'params': [self.filename]})

                    if extension in self.app.regFK.prj_list:
                        # self.app.open_project() is not Thread Safe
                        self.app.f_handlers.open_project(self.filename)

                    if extension in self.app.regFK.conf_list:
                        self.app.f_handlers.open_config_file(self.filename)
                    else:
                        event.ignore()
        else:
            event.ignore()

    def closeEvent(self, event):
        if self.app.save_in_progress:
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Application is saving the project. Please wait ..."))
        else:
            g_rect = self.geometry()

            qsettings = QSettings("Open Source", "FlatCAM")
            qsettings.setValue('saved_gui_state', self.saveState(0))
            qsettings.setValue('toolbar_lock', self.lock_action.isChecked())
            qsettings.setValue('menu_show_text', self.show_text_action.isChecked())
            if not self.isMaximized():
                qsettings.setValue('window_geometry', (g_rect.x(), g_rect.y(), g_rect.width(), g_rect.height()))
            qsettings.setValue('splitter_left', self.splitter.sizes()[0])
            # This will write the setting to the platform specific storage.
            del qsettings
            try:
                self.final_save.emit()
            except SystemError:
                QtWidgets.QApplication.quit()
                # sys.exit(0)
        event.ignore()

    # def moveEvent(self, event):
    #     oldScreen = QtWidgets.QApplication.screenAt(event.oldPos())
    #     newScreen = QtWidgets.QApplication.screenAt(event.pos())
    #
    #     if not oldScreen == newScreen:
    #         self.screenChanged.emit(oldScreen, newScreen)
    #
    #     return super().moveEvent(event)


class ShortcutsTab(QtWidgets.QWidget):

    def __init__(self):
        super(ShortcutsTab, self).__init__()

        self.sh_tab_layout = QtWidgets.QVBoxLayout()
        self.sh_tab_layout.setContentsMargins(2, 2, 2, 2)
        self.setLayout(self.sh_tab_layout)

        self.sh_hlay = QtWidgets.QHBoxLayout()

        self.sh_title = QtWidgets.QTextEdit('<b>%s</b>' % _('Shortcut Key List'))
        self.sh_title.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.NoTextInteraction)
        self.sh_title.setFrameStyle(QtWidgets.QFrame.Shape.NoFrame)
        self.sh_title.setMaximumHeight(30)

        font = self.sh_title.font()
        font.setPointSize(12)
        self.sh_title.setFont(font)

        self.sh_tab_layout.addWidget(self.sh_title)
        self.sh_tab_layout.addLayout(self.sh_hlay)

        self.app_sh_title = "<b>%s</b><br>" % _("General Shortcut list")

        self.app_sh_no_mod = """
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
                        <td height="20"><strong>%s</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                </tbody>
            </table>
        """ % (
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
            _('P'), _("Open Properties Plugin"),
            _('R'), _("Rotate by 90 degree CW"),
            _('S'), _("Shell Toggle"),
            _('T'), _("Add a Tool (when in Geometry Selected Tab or in Tools NCC or Tools Paint)"),
            _('V'), _("Zoom Fit"),
            _('X'), _("Flip on X_axis"),
            _('Y'), _("Flip on Y_axis"),
            _('-'), _("Zoom Out"),
            _('='), _("Zoom In"),
        )

        self.app_sh_ctrl_mod = """
            <table border="0" cellpadding="0" cellspacing="0" style="width:283px">
                <tbody>
                    <tr height="20">
                        <td height="20">&nbsp;</td>
                        <td>&nbsp;</td>
                    </tr>
                    <tr height="20">
                        <td height="20" width="89"><strong>%s</strong></td>
                        <td width="194"><span>&nbsp;%s</span></td>
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
                </tbody>
            </table>
        """ % (
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
            _('Ctrl+S'), _("Save Project"),
            _('Ctrl+F10'), _("Toggle Plot Area"),
        )

        self.app_sh_shift_mod = """
            <table border="0" cellpadding="0" cellspacing="0" style="width:283px">
                <tbody>
                    <tr height="20">
                        <td height="20">&nbsp;</td>
                        <td>&nbsp;</td>
                    </tr>
                    <tr height="20">
                        <td height="20" width="89"><strong>%s</strong></td>
                        <td width="194"><span>&nbsp;%s</span></td>
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
                </tbody>
            </table>
        """ % (
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
        )

        self.app_sh_alt_mod = """
            <table border="0" cellpadding="0" cellspacing="0" style="width:283px">
                <tbody>
                    <tr height="20">
                        <td height="20">&nbsp;</td>
                        <td>&nbsp;</td>
                    </tr>
                    <tr height="20">
                        <td height="20" width="89"><strong>%s</strong></td>
                        <td width="194"><span>&nbsp;%s</span></td>
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
                        <td height="20"><strong>&#39;%s&#39;</strong></td>
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
                        <td height="20"><strong>&#39;%s&#39;</strong></td>
                        <td>&nbsp;%s</td>
                    </tr>
                </tbody>
            </table>
        """ % (
            # ALT section
            _('Alt+A'), _("Align Objects"),
            _('Alt+B'), _("Markers"),
            _('Alt+C'), _("Calculators"),
            _('Alt+D'), _("2-Sided PCB"),
            _('Alt+E'), _("Extract"),
            _('Alt+F'), _("Fiducials"),
            _('Alt+G'), _("Invert Gerber"),
            _('Alt+H'), _("Punch Gerber"),
            _('Alt+I'), _("Isolation"),
            _('Alt+J'), _("Copper Thieving"),
            _('Alt+K'), _("Solder Paste Dispensing"),
            _('Alt+L'), _("Film PCB"),
            _('Alt+M'), _("Milling"),
            _('Alt+N'), _("Non-Copper Clearing"),
            _('Alt+O'), _("Optimal"),
            _('Alt+P'), _("Paint Area"),
            _('Alt+Q'), _("QRCode"),
            _('Alt+R'), _("Rules Check"),
            _('Alt+S'), _("View File Source"),
            _('Alt+T'), _("Transformations"),
            _('Alt+W'), _("Subtract"),
            _('Alt+X'), _("Cutout PCB"),
            _('Alt+Z'), _("Panelize PCB"),
            _('Alt+1'), _("Enable all"),
            _('Alt+2'), _("Disable all"),
            _('Alt+3'), _("Enable Non-selected Objects"),
            _('Alt+4'), _("Disable Non-selected Objects"),
            _('Alt+F10'), _("Toggle Full Screen"),
        )

        self.app_sh_combo_mod = """
            <table border="0" cellpadding="0" cellspacing="0" style="width:283px">
                <tbody>
                    <tr height="20">
                        <td height="20">&nbsp;</td>
                        <td>&nbsp;</td>
                    </tr>
                    <tr height="20">
                        <td height="20" width="89"><strong>%s</strong></td>
                        <td width="194"><span>&nbsp;%s</span></td>
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
        """ % (
            # CTRL + ALT section
            _('Ctrl+Alt+X'), _("Abort current task (gracefully)"),

            # CTRL + SHIFT section
            _('Ctrl+Shift+S'), _("Save Project As"),
            _('Ctrl+Shift+V'), _("Paste Special. "
                                 "Will convert a Windows path style to the one required in Tcl Shell"),

        )

        self.app_sh_div = """
            <table border="0" cellpadding="0" cellspacing="0" style="width:283px">
                <tbody>
                    <tr height="20">
                        <td height="20">&nbsp;</td>
                        <td>&nbsp;</td>
                    </tr>
                    <tr height="20">
                        <td height="20" width="89"><strong>%s</strong></td>
                        <td width="194"><span>&nbsp;%s</span></td>
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
                </tbody>
            </table>
        """ % (
            # F keys section
            _('F1'), _("Open Online Manual"),
            _('F2'), _("Rename Objects"),
            _('F4'), _("Open Online Tutorials"),
            _('F5'), _("Refresh Plots"),
            _('Del'), _("Delete Object"),
            _('Del'), _("Alternate: Delete Tool"),
            _('`'), _("(left to Key_1)Toggle Notebook Area (Left Side)"),
            _('Space'), _("En(Dis)able Obj Plot"),
            _('Esc'), _("Deselects all objects")
        )

        self.app_sh_msg = self.app_sh_title + self.app_sh_no_mod + self.app_sh_ctrl_mod \
                          + self.app_sh_shift_mod + self.app_sh_alt_mod + self.app_sh_combo_mod + self.app_sh_div
        self.sh_app = QtWidgets.QTextEdit()
        self.sh_app.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.NoTextInteraction)

        self.sh_app.setText(self.app_sh_msg)
        self.sh_app.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
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
            _('Del'), _("Delete")
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
            _('C'), _("Copy"),
            _('D'), _("Add Drill"),
            _('J'), _("Jump to Location (x, y)"),
            _('M'), _("Move"),
            _('Q'), _("Add Slot Array"),
            _('R'), _("Resize Drill"),
            _('T'), _("Add a new Tool"),
            _('W'), _("Add Slot"),
            _('Shift+M'), _("Distance Minimum Tool"),
            _('Del'), _("Delete"),
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
        self.sh_editor.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.NoTextInteraction)
        self.sh_editor.setText(self.editor_sh_msg)
        self.sh_editor.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        self.sh_hlay.addWidget(self.sh_editor)

# end of file
