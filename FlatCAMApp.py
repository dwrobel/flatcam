# ###########################################################
# FlatCAM: 2D Post-processing for Manufacturing             #
# http://flatcam.org                                        #
# Author: Juan Pablo Caram (c)                              #
# Date: 2/5/2014                                            #
# MIT Licence                                               #
# ###########################################################

import urllib.request
import urllib.parse
import urllib.error
import webbrowser

import getopt
import random
import simplejson as json
import lzma
import threading
import shutil

from stat import S_IREAD, S_IRGRP, S_IROTH
import subprocess
import ctypes

import tkinter as tk
from PyQt5 import QtPrintSupport

from contextlib import contextmanager
import gc

from xml.dom.minidom import parseString as parse_xml_string

from multiprocessing.connection import Listener, Client
from multiprocessing import Pool, cpu_count
import socket
from array import array

import vispy.scene as scene

# #######################################
# #      Imports part of FlatCAM       ##
# #######################################
from ObjectCollection import *
from FlatCAMObj import *
from camlib import to_dict, dict2obj, ET, ParseError

from flatcamGUI.PlotCanvas import *
from flatcamGUI.PlotCanvasLegacy import *
from flatcamGUI.FlatCAMGUI import *

from FlatCAMCommon import LoudDict, BookmarkManager, ToolsDB
from FlatCAMPostProc import load_postprocessors

from flatcamEditors.FlatCAMGeoEditor import FlatCAMGeoEditor
from flatcamEditors.FlatCAMExcEditor import FlatCAMExcEditor
from flatcamEditors.FlatCAMGrbEditor import FlatCAMGrbEditor
from flatcamEditors.FlatCAMTextEditor import TextEditor

from FlatCAMProcess import *
from FlatCAMWorkerStack import WorkerStack
# from flatcamGUI.VisPyVisuals import Color
from vispy.gloo.util import _screenshot
from vispy.io import write_png

from flatcamTools import *

import tclCommands

import gettext
import FlatCAMTranslation as fcTranslate
import builtins

if sys.platform == 'win32':
    import winreg

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class App(QtCore.QObject):
    # ########################################
    # #                App                 ###
    # ########################################

    """
    The main application class. The constructor starts the GUI.
    """

    # Get Cmd Line Options
    cmd_line_shellfile = ''
    cmd_line_shellvar = ''
    cmd_line_headless = None

    cmd_line_help = "FlatCam.py --shellfile=<cmd_line_shellfile>\n" \
                    "FlatCam.py --shellvar=<1,'C:\\path',23>\n" \
                    "FlatCam.py --headless=1"
    try:
        # Multiprocessing pool will spawn additional processes with 'multiprocessing-fork' flag
        cmd_line_options, args = getopt.getopt(sys.argv[1:], "h:", ["shellfile=",
                                                                    "shellvar=",
                                                                    "headless=",
                                                                    "multiprocessing-fork="])
    except getopt.GetoptError:
        print(cmd_line_help)
        sys.exit(2)

    for opt, arg in cmd_line_options:
        if opt == '-h':
            print(cmd_line_help)
            sys.exit()
        elif opt == '--shellfile':
            cmd_line_shellfile = arg
        elif opt == '--shellvar':
            cmd_line_shellvar = arg
        elif opt == '--headless':
            try:
                cmd_line_headless = eval(arg)
            except NameError:
                pass

    # ## Logging ###
    log = logging.getLogger('base')
    log.setLevel(logging.DEBUG)
    # log.setLevel(logging.WARNING)
    formatter = logging.Formatter('[%(levelname)s][%(threadName)s] %(message)s')
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    log.addHandler(handler)

    # ##########################################################################
    # ################## Version and VERSION DATE ##############################
    # ##########################################################################
    version = 8.99
    version_date = "2019/12/7"
    beta = True
    engine = '3D'

    # current date now
    date = str(datetime.today()).rpartition('.')[0]
    date = ''.join(c for c in date if c not in ':-')
    date = date.replace(' ', '_')

    # URL for update checks and statistics
    version_url = "http://flatcam.org/version"

    # App URL
    app_url = "http://flatcam.org"

    # Manual URL
    manual_url = "http://flatcam.org/manual/index.html"
    video_url = "https://www.youtube.com/playlist?list=PLVvP2SYRpx-AQgNlfoxw93tXUXon7G94_"
    gerber_spec_url = "https://www.ucamco.com/files/downloads/file/81/The_Gerber_File_Format_specification." \
                      "pdf?7ac957791daba2cdf4c2c913f67a43da"
    excellon_spec_url = "https://www.ucamco.com/files/downloads/file/305/the_xnc_file_format_specification.pdf"
    bug_report_url = "https://bitbucket.org/jpcgt/flatcam/issues?status=new&status=open"

    # this variable will hold the project status
    # if True it will mean that the project was modified and not saved
    should_we_save = False

    # flag is True if saving action has been triggered
    save_in_progress = False

    # ###########################################################################
    # #############################    Signals   ################################
    # ###########################################################################

    # Inform the user
    # Handled by:
    #  * App.info() --> Print on the status bar
    inform = QtCore.pyqtSignal(str)

    app_quit = QtCore.pyqtSignal()

    # General purpose background task
    worker_task = QtCore.pyqtSignal(dict)

    # File opened
    # Handled by:
    #  * register_folder()
    #  * register_recent()
    # Note: Setting the parameters to unicode does not seem
    #       to have an effect. Then are received as Qstring
    #       anyway.

    # File type and filename
    file_opened = QtCore.pyqtSignal(str, str)
    # File type and filename
    file_saved = QtCore.pyqtSignal(str, str)

    # Percentage of progress
    progress = QtCore.pyqtSignal(int)

    plots_updated = QtCore.pyqtSignal()

    # Emitted by new_object() and passes the new object as argument, plot flag.
    # on_object_created() adds the object to the collection, plots on appropriate flag
    # and emits new_object_available.
    object_created = QtCore.pyqtSignal(object, bool, bool)

    # Emitted when a object has been changed (like scaled, mirrored)
    object_changed = QtCore.pyqtSignal(object)

    # Emitted after object has been plotted.
    # Calls 'on_zoom_fit' method to fit object in scene view in main thread to prevent drawing glitches.
    object_plotted = QtCore.pyqtSignal(object)

    # Emitted when a new object has been added or deleted from/to the collection
    object_status_changed = QtCore.pyqtSignal(object, str, str)

    message = QtCore.pyqtSignal(str, str, str)

    # Emmited when shell command is finished(one command only)
    shell_command_finished = QtCore.pyqtSignal(object)

    # Emitted when multiprocess pool has been recreated
    pool_recreated = QtCore.pyqtSignal(object)

    # Emitted when an unhandled exception happens
    # in the worker task.
    thread_exception = QtCore.pyqtSignal(object)

    # used to signal that there are arguments for the app
    args_at_startup = QtCore.pyqtSignal(list)

    # a reusable signal to replot a list of objects
    # should be disconnected after use so it can be reused
    replot_signal = pyqtSignal(list)

    def __init__(self, user_defaults=True):
        """
        Starts the application.

        :return: app
        :rtype: App
        """

        App.log.info("FlatCAM Starting...")

        self.main_thread = QtWidgets.QApplication.instance().thread()

        # ############################################################################
        # # ################# OS-specific ############################################
        # ############################################################################
        portable = False

        # Folder for user settings.
        if sys.platform == 'win32':

            # #########################################################################
            # Setup the listening thread for another instance launching with args #####
            # #########################################################################

            # make sure the thread is stored by using a self. otherwise it's garbage collected
            self.th = QtCore.QThread()
            self.th.start(priority=QtCore.QThread.LowestPriority)

            self.new_launch = ArgsThread()
            self.new_launch.open_signal[list].connect(self.on_startup_args)
            self.new_launch.moveToThread(self.th)
            self.new_launch.start.emit()

            from win32com.shell import shell, shellcon
            if platform.architecture()[0] == '32bit':
                App.log.debug("Win32!")
            else:
                App.log.debug("Win64!")

            # #########################################################################
            # ####### CONFIG FILE WITH PARAMETERS REGARDING PORTABILITY ###############
            # #########################################################################
            config_file = os.path.dirname(os.path.dirname(os.path.realpath(__file__))) + '\\config\\configuration.txt'
            try:
                with open(config_file, 'r'):
                    pass
            except FileNotFoundError:
                config_file = os.path.dirname(os.path.realpath(__file__)) + '\\config\\configuration.txt'

            try:
                with open(config_file, 'r') as f:
                    try:
                        for line in f:
                            param = str(line).replace('\n', '').rpartition('=')

                            if param[0] == 'portable':
                                try:
                                    portable = eval(param[2])
                                except NameError:
                                    portable = False
                            if param[0] == 'headless':
                                if param[2].lower() == 'true':
                                    self.cmd_line_headless = 1
                                else:
                                    self.cmd_line_headless = None
                    except Exception as e:
                        log.debug('App.__init__() -->%s' % str(e))
                        return
            except FileNotFoundError as e:
                log.debug(str(e))
                pass

            if portable is False:
                self.data_path = shell.SHGetFolderPath(0, shellcon.CSIDL_APPDATA, None, 0) + '\\FlatCAM'
            else:
                self.data_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__))) + '\\config'

            self.os = 'windows'
        else:  # Linux/Unix/MacOS
            self.data_path = os.path.expanduser('~') + '/.FlatCAM'
            self.os = 'unix'

        # ##########################################################################
        # ################## Setup folders and files ###############################
        # ##########################################################################

        if not os.path.exists(self.data_path):
            os.makedirs(self.data_path)
            App.log.debug('Created data folder: ' + self.data_path)
            os.makedirs(os.path.join(self.data_path, 'postprocessors'))
            App.log.debug('Created data postprocessors folder: ' + os.path.join(self.data_path, 'postprocessors'))

        self.postprocessorpaths = os.path.join(self.data_path, 'postprocessors')
        if not os.path.exists(self.postprocessorpaths):
            os.makedirs(self.postprocessorpaths)
            App.log.debug('Created postprocessors folder: ' + self.postprocessorpaths)

        # create tools_db.FlatConfig file if there is none
        try:
            f = open(self.data_path + '/tools_db.FlatConfig')
            f.close()
        except IOError:
            App.log.debug('Creating empty tool_db.FlatConfig')
            f = open(self.data_path + '/tools_db.FlatConfig', 'w')
            json.dump({}, f)
            f.close()

        # create current_defaults.FlatConfig file if there is none
        try:
            f = open(self.data_path + '/current_defaults.FlatConfig')
            f.close()
        except IOError:
            App.log.debug('Creating empty current_defaults.FlatConfig')
            f = open(self.data_path + '/current_defaults.FlatConfig', 'w')
            json.dump({}, f)
            f.close()

        # create factory_defaults.FlatConfig file if there is none
        try:
            f = open(self.data_path + '/factory_defaults.FlatConfig')
            f.close()
        except IOError:
            App.log.debug('Creating empty factory_defaults.FlatConfig')
            f = open(self.data_path + '/factory_defaults.FlatConfig', 'w')
            json.dump({}, f)
            f.close()

        # create a recent files json file if there is none
        try:
            f = open(self.data_path + '/recent.json')
            f.close()
        except IOError:
            App.log.debug('Creating empty recent.json')
            f = open(self.data_path + '/recent.json', 'w')
            json.dump([], f)
            f.close()

        # create a recent projects json file if there is none
        try:
            fp = open(self.data_path + '/recent_projects.json')
            fp.close()
        except IOError:
            App.log.debug('Creating empty recent_projects.json')
            fp = open(self.data_path + '/recent_projects.json', 'w')
            json.dump([], fp)
            fp.close()

        # Application directory. CHDIR to it. Otherwise, trying to load
        # GUI icons will fail as their path is relative.
        # This will fail under cx_freeze ...
        self.app_home = os.path.dirname(os.path.realpath(__file__))

        App.log.debug("Application path is " + self.app_home)
        App.log.debug("Started in " + os.getcwd())

        # cx_freeze workaround
        if os.path.isfile(self.app_home):
            self.app_home = os.path.dirname(self.app_home)

        os.chdir(self.app_home)

        # #################################################################################
        # #################### DEFAULTS - PREFERENCES STORAGE #############################
        # #################################################################################

        self.defaults = LoudDict()
        self.defaults.update({
            # Global APP Preferences
            "first_run": True,
            "units": "MM",
            "global_serial": 0,
            "global_stats": dict(),
            "global_tabs_detachable": True,
            "global_graphic_engine": '3D',
            "global_app_level": 'b',
            "global_portable": False,
            "global_language": 'English',
            "global_version_check": True,
            "global_send_stats": True,
            "global_pan_button": '2',
            "global_mselect_key": 'Control',
            "global_project_at_startup": False,
            "global_systray_icon": True,
            "global_project_autohide": True,
            "global_toggle_tooltips": True,
            "global_worker_number": 2,
            "global_tolerance": 0.005,
            "global_open_style": True,
            "global_delete_confirmation": True,
            "global_compression_level": 3,
            "global_save_compressed": True,

            "global_machinist_setting": False,

            # Global GUI Preferences
            "global_gridx": 1.0,
            "global_gridy": 1.0,
            "global_snap_max": 0.05,
            "global_workspace": False,
            "global_workspaceT": "A4",
            "global_workspace_orientation": 'p',

            "global_grid_context_menu": {
                'in': [0.01, 0.02, 0.025, 0.05, 0.1],
                'mm': [0.1, 0.2, 0.5, 1, 2.54]
            },

            "global_plot_fill": '#BBF268BF',
            "global_plot_line": '#006E20BF',
            "global_sel_fill": '#a5a5ffbf',
            "global_sel_line": '#0000ffbf',
            "global_alt_sel_fill": '#BBF268BF',
            "global_alt_sel_line": '#006E20BF',
            "global_draw_color": '#FF0000',
            "global_sel_draw_color": '#0000FF',
            "global_proj_item_color": '#000000',
            "global_proj_item_dis_color": '#b7b7cb',
            "global_activity_icon": 'Ball green',

            "global_toolbar_view": 511,

            "global_background_timeout": 300000,  # Default value is 5 minutes
            "global_verbose_error_level": 0,  # Shell verbosity 0 = default
            # (python trace only for unknown errors),
            # 1 = show trace(show trace always),
            # 2 = (For the future).

            # Persistence
            "global_last_folder": None,
            "global_last_save_folder": None,

            # Default window geometry
            "global_def_win_x": 100,
            "global_def_win_y": 100,
            "global_def_win_w": 1024,
            "global_def_win_h": 650,
            "global_def_notebook_width": 1,

            # Constants...
            "global_defaults_save_period_ms": 20000,  # Time between default saves.
            "global_shell_shape": [500, 300],  # Shape of the shell in pixels.
            "global_shell_at_startup": False,  # Show the shell at startup.
            "global_recent_limit": 10,  # Max. items in recent list.

            "global_bookmarks": dict(),
            "global_bookmarks_limit": 10,

            "fit_key": 'V',
            "zoom_out_key": '-',
            "zoom_in_key": '=',
            "grid_toggle_key": 'G',
            "global_zoom_ratio": 1.5,
            "global_point_clipboard_format": "(%.4f, %.4f)",
            "global_zdownrate": None,

            # General GUI Settings
            "global_theme": 'white',
            "global_hover": False,
            "global_selection_shape": True,
            "global_layout": "compact",
            "global_cursor_type": "small",
            "global_cursor_size": 20,

            # Gerber General
            "gerber_plot": True,
            "gerber_solid": True,
            "gerber_multicolored": False,
            "gerber_circle_steps": 64,
            "gerber_use_buffer_for_union": True,
            "gerber_def_units": 'IN',
            "gerber_def_zeros": 'L',
            "gerber_save_filters": "Gerber File (*.gbr);;Gerber File (*.bot);;Gerber File (*.bsm);;"
                                   "Gerber File (*.cmp);;Gerber File (*.crc);;Gerber File (*.crs);;"
                                   "Gerber File (*.gb0);;Gerber File (*.gb1);;Gerber File (*.gb2);;"
                                   "Gerber File (*.gb3);;Gerber File (*.gb4);;Gerber File (*.gb5);;"
                                   "Gerber File (*.gb6);;Gerber File (*.gb7);;Gerber File (*.gb8);;"
                                   "Gerber File (*.gb9);;Gerber File (*.gbd);;Gerber File (*.gbl);;"
                                   "Gerber File (*.gbo);;Gerber File (*.gbp);;Gerber File (*.gbs);;"
                                   "Gerber File (*.gdo);;Gerber File (*.ger);;Gerber File (*.gko);;"
                                   "Gerber File (*.gm1);;Gerber File (*.gm2);;Gerber File (*.gm3);;"
                                   "Gerber File (*.grb);;Gerber File (*.gtl);;Gerber File (*.gto);;"
                                   "Gerber File (*.gtp);;Gerber File (*.gts);;Gerber File (*.ly15);;"
                                   "Gerber File (*.ly2);;Gerber File (*.mil);;Gerber File (*.pho);;"
                                   "Gerber File (*.plc);;Gerber File (*.pls);;Gerber File (*.smb);;"
                                   "Gerber File (*.smt);;Gerber File (*.sol);;Gerber File (*.spb);;"
                                   "Gerber File (*.spt);;Gerber File (*.ssb);;Gerber File (*.sst);;"
                                   "Gerber File (*.stc);;Gerber File (*.sts);;Gerber File (*.top);;"
                                   "Gerber File (*.tsm);;Gerber File (*.art)"
                                   "All Files (*.*)",

            # Gerber Options
            "gerber_isotooldia": 0.1,
            "gerber_isopasses": 1,
            "gerber_isooverlap": 0.1,
            "gerber_milling_type": "cl",
            "gerber_combine_passes": False,
            "gerber_iso_scope": 'all',
            "gerber_noncoppermargin": 0.1,
            "gerber_noncopperrounded": False,
            "gerber_bboxmargin": 0.1,
            "gerber_bboxrounded": False,

            # Gerber Advanced Options
            "gerber_aperture_display": False,
            "gerber_aperture_scale_factor": 1.0,
            "gerber_aperture_buffer_factor": 0.0,
            "gerber_follow": False,
            "gerber_tool_type": 'circular',
            "gerber_vtipdia": 0.1,
            "gerber_vtipangle": 30,
            "gerber_vcutz": -0.05,
            "gerber_iso_type": "full",
            "gerber_buffering": "full",
            "gerber_simplification": False,
            "gerber_simp_tolerance": 0.0005,

            # Gerber Export
            "gerber_exp_units": 'IN',
            "gerber_exp_integer": 2,
            "gerber_exp_decimals": 4,
            "gerber_exp_zeros": 'L',

            # Gerber Editor
            "gerber_editor_sel_limit": 30,
            "gerber_editor_newcode": 10,
            "gerber_editor_newsize": 0.8,
            "gerber_editor_newtype": 'C',
            "gerber_editor_newdim": "0.5, 0.5",
            "gerber_editor_array_size": 5,
            "gerber_editor_lin_axis": 'X',
            "gerber_editor_lin_pitch": 0.1,
            "gerber_editor_lin_angle": 0.0,
            "gerber_editor_circ_dir": 'CW',
            "gerber_editor_circ_angle": 0.0,
            "gerber_editor_scale_f": 1.0,
            "gerber_editor_buff_f": 0.1,
            "gerber_editor_ma_low": 0.0,
            "gerber_editor_ma_high": 1.0,

            # Excellon General
            "excellon_plot": True,
            "excellon_solid": True,
            "excellon_format_upper_in": 2,
            "excellon_format_lower_in": 4,
            "excellon_format_upper_mm": 3,
            "excellon_format_lower_mm": 3,
            "excellon_zeros": "L",
            "excellon_units": "INCH",
            "excellon_update": True,
            "excellon_optimization_type": 'B',
            "excellon_search_time": 3,
            "excellon_save_filters": "Excellon File (*.txt);;Excellon File (*.drd);;Excellon File (*.drl);;"
                                     "Excellon File (*.exc);;Excellon File (*.ncd);;Excellon File (*.tap);;"
                                     "Excellon File (*.xln);;All Files (*.*)",

            # Excellon Options
            "excellon_drillz": -1.7,
            "excellon_travelz": 2,
            "excellon_endz": 0.5,
            "excellon_feedrate": 300,
            "excellon_spindlespeed": None,
            "excellon_dwell": False,
            "excellon_dwelltime": 1,
            "excellon_toolchange": False,
            "excellon_toolchangez": 15,
            "excellon_ppname_e": 'default',
            "excellon_tooldia": 0.8,
            "excellon_slot_tooldia": 1.8,
            "excellon_gcode_type": "drills",

            # Excellon Advanced Options
            "excellon_offset": 0.0,
            "excellon_toolchangexy": "0.0, 0.0",
            "excellon_startz": None,
            "excellon_feedrate_rapid": 1500,
            "excellon_z_pdepth": -0.02,
            "excellon_feedrate_probe": 75,
            "excellon_spindledir": 'CW',
            "excellon_f_plunge": False,
            "excellon_f_retract": False,

            # Excellon Export
            "excellon_exp_units": 'INCH',
            "excellon_exp_format": 'ndec',
            "excellon_exp_integer": 2,
            "excellon_exp_decimals": 4,
            "excellon_exp_zeros": 'LZ',
            "excellon_exp_slot_type": 'routing',

            # Excellon Editor
            "excellon_editor_sel_limit": 30,
            "excellon_editor_newdia": 1.0,
            "excellon_editor_array_size": 5,
            "excellon_editor_lin_dir": 'X',
            "excellon_editor_lin_pitch": 2.54,
            "excellon_editor_lin_angle": 0.0,
            "excellon_editor_circ_dir": 'CW',
            "excellon_editor_circ_angle": 12,
            # Excellon Slots
            "excellon_editor_slot_direction": 'X',
            "excellon_editor_slot_angle": 0.0,
            "excellon_editor_slot_length": 5.0,
            # Excellon Slot Array
            "excellon_editor_slot_array_size": 5,
            "excellon_editor_slot_lin_dir":  'X',
            "excellon_editor_slot_lin_pitch": 2.54,
            "excellon_editor_slot_lin_angle": 0.0,
            "excellon_editor_slot_circ_dir": 'CW',
            "excellon_editor_slot_circ_angle": 0.0,

            # Geometry General
            "geometry_plot": True,
            "geometry_circle_steps": 64,
            "geometry_cnctooldia": "2.4",

            # Geometry Options
            "geometry_cutz": -2.4,
            "geometry_vtipdia": 0.1,
            "geometry_vtipangle": 30,
            "geometry_multidepth": False,
            "geometry_depthperpass": 0.8,
            "geometry_travelz": 2,
            "geometry_toolchange": False,
            "geometry_toolchangez": 15.0,
            "geometry_endz": 15.0,
            "geometry_feedrate": 120,
            "geometry_feedrate_z": 60,
            "geometry_spindlespeed": None,
            "geometry_dwell": False,
            "geometry_dwelltime": 1,
            "geometry_ppname_g": 'default',

            # Geometry Advanced Options
            "geometry_toolchangexy": "0.0, 0.0",
            "geometry_startz": None,
            "geometry_feedrate_rapid": 1500,
            "geometry_extracut": False,
            "geometry_z_pdepth": -0.02,
            "geometry_f_plunge": False,
            "geometry_spindledir": 'CW',
            "geometry_feedrate_probe": 75,
            "geometry_segx": 0.0,
            "geometry_segy": 0.0,

            # Geometry Editor
            "geometry_editor_sel_limit": 30,
            "geometry_editor_milling_type": "cl",

            # CNC Job General
            "cncjob_plot": True,
            "cncjob_plot_kind": 'all',
            "cncjob_annotation": True,
            "cncjob_tooldia": 1.0,
            "cncjob_coords_type": "G90",
            "cncjob_coords_decimals": 4,
            "cncjob_fr_decimals": 2,
            "cncjob_steps_per_circle": 64,
            "cncjob_footer": False,
            "cncjob_line_ending": False,
            "cncjob_save_filters": "G-Code Files (*.nc);;G-Code Files (*.din);;G-Code Files (*.dnc);;"
                                   "G-Code Files (*.ecs);;G-Code Files (*.eia);;G-Code Files (*.fan);;"
                                   "G-Code Files (*.fgc);;G-Code Files (*.fnc);;G-Code Files (*.gc);;"
                                   "G-Code Files (*.gcd);;G-Code Files (*.gcode);;G-Code Files (*.h);;"
                                   "G-Code Files (*.hnc);;G-Code Files (*.i);;G-Code Files (*.min);;"
                                   "G-Code Files (*.mpf);;G-Code Files (*.mpr);;G-Code Files (*.cnc);;"
                                   "G-Code Files (*.ncc);;G-Code Files (*.ncg);;G-Code Files (*.ncp);;"
                                   "G-Code Files (*.ngc);;G-Code Files (*.out);;G-Code Files (*.ply);;"
                                   "G-Code Files (*.sbp);;G-Code Files (*.tap);;G-Code Files (*.xpi);;"
                                   "All Files (*.*)",

            # CNC Job Options
            "cncjob_prepend": "",
            "cncjob_append": "",

            # CNC Job Advanced Options
            "cncjob_toolchange_macro": "",
            "cncjob_toolchange_macro_enable": False,
            "cncjob_annotation_fontsize": 9,
            "cncjob_annotation_fontcolor": '#990000',

            # NCC Tool
            "tools_ncctools": "1.0, 0.5",
            "tools_nccorder": 'rev',
            "tools_nccoverlap": 0.4,
            "tools_nccmargin": 1.0,
            "tools_nccmethod": "seed",
            "tools_nccconnect": True,
            "tools_ncccontour": True,
            "tools_nccrest": False,
            "tools_ncc_offset_choice": False,
            "tools_ncc_offset_value": 0.0000,
            "tools_nccref": 'itself',
            "tools_ncc_plotting": 'normal',
            "tools_nccmilling_type": 'cl',
            "tools_ncctool_type": 'V',
            "tools_ncccutz": -0.05,
            "tools_ncctipdia": 0.1,
            "tools_ncctipangle": 30,
            "tools_nccnewdia": 1.0,

            # Cutout Tool
            "tools_cutouttooldia": 2.4,
            "tools_cutoutkind": "single",
            "tools_cutoutmargin": 0.1,
            "tools_cutoutgapsize": 4,
            "tools_gaps_ff": "4",
            "tools_cutout_convexshape": False,

            # Paint Tool
            "tools_painttooldia": 0.3,
            "tools_paintorder": 'rev',
            "tools_paintoverlap": 0.2,
            "tools_paintmargin": 0.0,
            "tools_paintmethod": "seed",
            "tools_selectmethod": "all",
            "tools_pathconnect": True,
            "tools_paintcontour": True,
            "tools_paint_plotting": 'normal',

            # 2-Sided Tool
            "tools_2sided_mirror_axis": "X",
            "tools_2sided_axis_loc": "point",
            "tools_2sided_drilldia": 3.125,

            # Film Tool
            "tools_film_type": 'neg',
            "tools_film_boundary": 1.0,
            "tools_film_scale_stroke": 0,
            "tools_film_color": '#000000',
            "tools_film_scale_cb": False,
            "tools_film_scale_x_entry": 1.0,
            "tools_film_scale_y_entry": 1.0,
            "tools_film_skew_cb": False,
            "tools_film_skew_x_entry": 0.0,
            "tools_film_skew_y_entry": 0.0,
            "tools_film_skew_ref_radio": 'bottomleft',
            "tools_film_mirror_cb": False,
            "tools_film_mirror_axis_radio": 'none',
            "tools_film_file_type_radio": 'svg',
            "tools_film_orientation": 'p',
            "tools_film_pagesize": 'A4',

            # Panel Tool
            "tools_panelize_spacing_columns": 0,
            "tools_panelize_spacing_rows": 0,
            "tools_panelize_columns": 1,
            "tools_panelize_rows": 1,
            "tools_panelize_constrain": False,
            "tools_panelize_constrainx": 200.0,
            "tools_panelize_constrainy": 290.0,
            "tools_panelize_panel_type": 'gerber',

            # Calculators Tool
            "tools_calc_vshape_tip_dia": 0.2,
            "tools_calc_vshape_tip_angle": 30,
            "tools_calc_vshape_cut_z": 0.05,
            "tools_calc_electro_length": 10.0,
            "tools_calc_electro_width": 10.0,
            "tools_calc_electro_cdensity": 13.0,
            "tools_calc_electro_growth": 10.0,

            # Transform Tool
            "tools_transform_rotate": 90,
            "tools_transform_skew_x": 0.0,
            "tools_transform_skew_y": 0.0,
            "tools_transform_scale_x": 1.0,
            "tools_transform_scale_y": 1.0,
            "tools_transform_scale_link": True,
            "tools_transform_scale_reference": True,
            "tools_transform_offset_x": 0.0,
            "tools_transform_offset_y": 0.0,
            "tools_transform_mirror_reference": False,
            "tools_transform_mirror_point": (0, 0),

            # SolderPaste Tool
            "tools_solderpaste_tools": "1.0, 0.3",
            "tools_solderpaste_new": 0.3,
            "tools_solderpaste_z_start": 0.05,
            "tools_solderpaste_z_dispense": 0.1,
            "tools_solderpaste_z_stop": 0.05,
            "tools_solderpaste_z_travel": 0.1,
            "tools_solderpaste_z_toolchange": 1.0,
            "tools_solderpaste_xy_toolchange": "0.0, 0.0",
            "tools_solderpaste_frxy": 150,
            "tools_solderpaste_frz": 150,
            "tools_solderpaste_frz_dispense": 1.0,
            "tools_solderpaste_speedfwd": 300,
            "tools_solderpaste_dwellfwd": 1,
            "tools_solderpaste_speedrev": 200,
            "tools_solderpaste_dwellrev": 1,
            "tools_solderpaste_pp": 'Paste_1',

            # Subtract Tool
            "tools_sub_close_paths": True,

            # ###################################################################################
            # ################################ TOOLS 2 ##########################################
            # ###################################################################################

            # Optimal Tool
            "tools_opt_precision": 4,

            # Check Rules Tool
            "tools_cr_trace_size": True,
            "tools_cr_trace_size_val": 0.25,
            "tools_cr_c2c": True,
            "tools_cr_c2c_val": 0.25,
            "tools_cr_c2o": True,
            "tools_cr_c2o_val": 1.0,
            "tools_cr_s2s": True,
            "tools_cr_s2s_val": 0.25,
            "tools_cr_s2sm": True,
            "tools_cr_s2sm_val": 0.25,
            "tools_cr_s2o": True,
            "tools_cr_s2o_val": 1.0,
            "tools_cr_sm2sm": True,
            "tools_cr_sm2sm_val": 0.25,
            "tools_cr_ri": True,
            "tools_cr_ri_val": 0.3,
            "tools_cr_h2h": True,
            "tools_cr_h2h_val": 0.3,
            "tools_cr_dh": True,
            "tools_cr_dh_val": 0.3,

            # QRCode Tool
            "tools_qrcode_version": 1,
            "tools_qrcode_error": 'L',
            "tools_qrcode_box_size": 3,
            "tools_qrcode_border_size": 4,
            "tools_qrcode_qrdata": '',
            "tools_qrcode_polarity": 'pos',
            "tools_qrcode_rounded": 's',
            "tools_qrcode_fill_color": '#000000',
            "tools_qrcode_back_color": '#FFFFFF',
            "tools_qrcode_sel_limit": 330,

            # Copper Thieving Tool
            "tools_copper_thieving_clearance": 0.25,
            "tools_copper_thieving_margin": 1.0,
            "tools_copper_thieving_reference": 'itself',
            "tools_copper_thieving_box_type": 'rect',
            "tools_copper_thieving_circle_steps": 64,
            "tools_copper_thieving_fill_type": 'solid',
            "tools_copper_thieving_dots_dia": 1.0,
            "tools_copper_thieving_dots_spacing": 2.0,
            "tools_copper_thieving_squares_size": 1.0,
            "tools_copper_thieving_squares_spacing": 2.0,
            "tools_copper_thieving_lines_size": 0.25,
            "tools_copper_thieving_lines_spacing": 2.0,
            "tools_copper_thieving_rb_margin": 1.0,
            "tools_copper_thieving_rb_thickness": 1.0,

            # Fiducials Tool
            "tools_fiducials_dia": 1.0,
            "tools_fiducials_margin": 1.0,
            "tools_fiducials_mode": 'auto',
            "tools_fiducials_second_pos": 'up',
            "tools_fiducials_type": 'circular',
            "tools_fiducials_line_thickness": 0.25,

            # Utilities
            # file associations
            "fa_excellon": 'drd, drl, exc, ncd, tap, xln',
            "fa_gcode": 'cnc, din, dnc, ecs, eia, fan, fgc, fnc, gc, gcd, gcode, h, hnc, i, min, mpf, mpr, nc, ncc, '
                        'ncg, ncp, ngc, out, plt, ply, rol, sbp, tap, xpi',
            "fa_gerber": 'art, bot, bsm, cmp, crc, crs, dim, gb0, gb1, gb2, gb3, gb4, gb5, gb6, gb7, gb8, gb9, gbd, '
                         'gbl, gbo, gbp, gbr, gbs, gdo, ger, gko, gm1, gm2, gm3, grb, gtl, gto, gtp, gts, ly15, ly2, '
                         'mil, pho, plc, pls, smb, smt, sol, spb, spt, ssb, sst, stc, sts, top, tsm',
            # Keyword list
            "util_autocomplete_keywords": 'Desktop, Documents, FlatConfig, FlatPrj, Marius, My Documents, Paste_1, '
                                          'Repetier, Roland_MDX_20, Users, Toolchange_Custom, Toolchange_Probe_MACH3, '
                                          'Toolchange_manual, Users, all, angle_x, angle_y, axis, auto, axisoffset, '
                                          'box, center_x, center_y, columns, combine, connect, contour, default, '
                                          'depthperpass, dia, diatol, dist, drilled_dias, drillz, dwell, dwelltime, '
                                          'feedrate_z, grbl_11, grbl_laser, gridoffsety, gridx, gridy, has_offset, '
                                          'holes, hpgl, iso_type, line_xyz, margin, marlin, method, milled_dias, '
                                          'minoffset, multidepth, name, offset, opt_type, order, outname, overlap, '
                                          'passes, postamble, pp, ppname_e, ppname_g, preamble, radius, ref, rest, '
                                          'rows, shellvar_, scale_factor, spacing_columns, spacing_rows, spindlespeed, '
                                          'toolchange_xy, tooldia, use_threads, value, x, x0, x1, y, y0, y1, z_cut, '
                                          'z_move',
            "script_autocompleter": True,
            "script_text": "",
            "script_plot": True,
            "script_source_file": "",

            "document_autocompleter": False,
            "document_text": "",
            "document_plot": True,
            "document_source_file": "",
            "document_font_color": '#000000',
            "document_sel_color": '#0055ff',
            "document_font_size": 6,
            "document_tab_size": 80,
        })

        # ############################################################
        # ############### Load defaults from file ####################
        # ############################################################

        if user_defaults:
            self.load_defaults(filename='current_defaults')

        # #############################################################################
        # ##################### CREATE MULTIPROCESSING POOL ###########################
        # #############################################################################

        self.pool = Pool(processes=cpu_count())

        # ##########################################################################
        # ################## Setting the Splash Screen #############################
        # ##########################################################################

        splash_settings = QSettings("Open Source", "FlatCAM")
        if splash_settings.contains("splash_screen"):
            show_splash = splash_settings.value("splash_screen")
        else:
            splash_settings.setValue('splash_screen', 1)

            # This will write the setting to the platform specific storage.
            del splash_settings
            show_splash = 1

        if show_splash and self.cmd_line_headless != 1:
            splash_pix = QtGui.QPixmap('share/splash.png')
            self.splash = QtWidgets.QSplashScreen(splash_pix, Qt.WindowStaysOnTopHint)
            # self.splash.setMask(splash_pix.mask())

            # move splashscreen to the current monitor
            desktop = QtWidgets.QApplication.desktop()
            screen = desktop.screenNumber(QtGui.QCursor.pos())
            current_screen_center = desktop.availableGeometry(screen).center()
            self.splash.move(current_screen_center - self.splash.rect().center())

            self.splash.show()
            self.splash.showMessage(_("FlatCAM is initializing ..."),
                                    alignment=Qt.AlignBottom | Qt.AlignLeft,
                                    color=QtGui.QColor("gray"))
        else:
            show_splash = 0

        # #############################################################################
        # ##################### Initialize GUI ########################################
        # #############################################################################

        # FlatCAM colors used in plotting
        self.FC_light_green = '#BBF268BF'
        self.FC_dark_green = '#006E20BF'
        self.FC_light_blue = '#a5a5ffbf'
        self.FC_dark_blue = '#0000ffbf'

        QtCore.QObject.__init__(self)

        self.ui = FlatCAMGUI(self.version, self.beta, self)

        theme_settings = QtCore.QSettings("Open Source", "FlatCAM")
        if theme_settings.contains("theme"):
            theme = theme_settings.value('theme', type=str)
        else:
            theme = 'white'

        if theme == 'white':
            self.cursor_color_3D = 'black'
        else:
            self.cursor_color_3D = 'gray'

        self.ui.geom_update[int, int, int, int, int].connect(self.save_geometry)
        self.ui.final_save.connect(self.final_save)

        # restore the toolbar view
        self.restore_toolbar_view()

        # restore the GUI geometry
        self.restore_main_win_geom()

        # set FlatCAM units in the Status bar
        self.set_screen_units(self.defaults['units'])

        # #############################################################################
        # ######################## UPDATE PREFERENCES GUI FORMS #######################
        # #############################################################################

        # when adding entries here read the comments in the  method found bellow named:
        # def new_object(self, kind, name, initialize, active=True, fit=True, plot=True)
        self.defaults_form_fields = {
            # General App
            "units": self.ui.general_defaults_form.general_app_group.units_radio,
            "global_graphic_engine": self.ui.general_defaults_form.general_app_group.ge_radio,
            "global_app_level": self.ui.general_defaults_form.general_app_group.app_level_radio,
            "global_portable": self.ui.general_defaults_form.general_app_group.portability_cb,
            "global_language": self.ui.general_defaults_form.general_app_group.language_cb,

            "global_version_check": self.ui.general_defaults_form.general_app_group.version_check_cb,
            "global_send_stats": self.ui.general_defaults_form.general_app_group.send_stats_cb,
            "global_pan_button": self.ui.general_defaults_form.general_app_group.pan_button_radio,
            "global_mselect_key": self.ui.general_defaults_form.general_app_group.mselect_radio,

            "global_worker_number": self.ui.general_defaults_form.general_app_group.worker_number_sb,
            "global_tolerance": self.ui.general_defaults_form.general_app_group.tol_entry,

            "global_open_style": self.ui.general_defaults_form.general_app_group.open_style_cb,

            "global_compression_level": self.ui.general_defaults_form.general_app_group.compress_spinner,
            "global_save_compressed": self.ui.general_defaults_form.general_app_group.save_type_cb,

            "global_bookmarks_limit": self.ui.general_defaults_form.general_app_group.bm_limit_spinner,
            "global_machinist_setting": self.ui.general_defaults_form.general_app_group.machinist_cb,

            # General GUI Preferences
            "global_gridx": self.ui.general_defaults_form.general_gui_group.gridx_entry,
            "global_gridy": self.ui.general_defaults_form.general_gui_group.gridy_entry,
            "global_snap_max": self.ui.general_defaults_form.general_gui_group.snap_max_dist_entry,
            "global_workspace": self.ui.general_defaults_form.general_gui_group.workspace_cb,
            "global_workspaceT": self.ui.general_defaults_form.general_gui_group.wk_cb,
            "global_workspace_orientation": self.ui.general_defaults_form.general_gui_group.wk_orientation_radio,

            "global_plot_fill": self.ui.general_defaults_form.general_gui_group.pf_color_entry,
            "global_plot_line": self.ui.general_defaults_form.general_gui_group.pl_color_entry,
            "global_sel_fill": self.ui.general_defaults_form.general_gui_group.sf_color_entry,
            "global_sel_line": self.ui.general_defaults_form.general_gui_group.sl_color_entry,
            "global_alt_sel_fill": self.ui.general_defaults_form.general_gui_group.alt_sf_color_entry,
            "global_alt_sel_line": self.ui.general_defaults_form.general_gui_group.alt_sl_color_entry,
            "global_draw_color": self.ui.general_defaults_form.general_gui_group.draw_color_entry,
            "global_sel_draw_color": self.ui.general_defaults_form.general_gui_group.sel_draw_color_entry,

            "global_proj_item_color": self.ui.general_defaults_form.general_gui_group.proj_color_entry,
            "global_proj_item_dis_color": self.ui.general_defaults_form.general_gui_group.proj_color_dis_entry,
            "global_activity_icon": self.ui.general_defaults_form.general_gui_group.activity_combo,

            # General GUI Settings
            "global_theme": self.ui.general_defaults_form.general_gui_set_group.theme_radio,
            "global_layout": self.ui.general_defaults_form.general_gui_set_group.layout_combo,
            "global_hover": self.ui.general_defaults_form.general_gui_set_group.hover_cb,
            "global_selection_shape": self.ui.general_defaults_form.general_gui_set_group.selection_cb,
            "global_systray_icon": self.ui.general_defaults_form.general_gui_set_group.systray_cb,
            "global_shell_at_startup": self.ui.general_defaults_form.general_gui_set_group.shell_startup_cb,
            "global_project_at_startup": self.ui.general_defaults_form.general_gui_set_group.project_startup_cb,
            "global_project_autohide": self.ui.general_defaults_form.general_gui_set_group.project_autohide_cb,
            "global_toggle_tooltips": self.ui.general_defaults_form.general_gui_set_group.toggle_tooltips_cb,
            "global_delete_confirmation": self.ui.general_defaults_form.general_gui_set_group.delete_conf_cb,
            "global_cursor_type": self.ui.general_defaults_form.general_gui_set_group.cursor_radio,
            "global_cursor_size": self.ui.general_defaults_form.general_gui_set_group.cursor_size_entry,

            # Gerber General
            "gerber_plot": self.ui.gerber_defaults_form.gerber_gen_group.plot_cb,
            "gerber_solid": self.ui.gerber_defaults_form.gerber_gen_group.solid_cb,
            "gerber_multicolored": self.ui.gerber_defaults_form.gerber_gen_group.multicolored_cb,
            "gerber_circle_steps": self.ui.gerber_defaults_form.gerber_gen_group.circle_steps_entry,
            "gerber_def_units": self.ui.gerber_defaults_form.gerber_gen_group.gerber_units_radio,
            "gerber_def_zeros": self.ui.gerber_defaults_form.gerber_gen_group.gerber_zeros_radio,

            # Gerber Options
            "gerber_isotooldia": self.ui.gerber_defaults_form.gerber_opt_group.iso_tool_dia_entry,
            "gerber_isopasses": self.ui.gerber_defaults_form.gerber_opt_group.iso_width_entry,
            "gerber_isooverlap": self.ui.gerber_defaults_form.gerber_opt_group.iso_overlap_entry,
            "gerber_combine_passes": self.ui.gerber_defaults_form.gerber_opt_group.combine_passes_cb,
            "gerber_iso_scope": self.ui.gerber_defaults_form.gerber_opt_group.iso_scope_radio,
            "gerber_milling_type": self.ui.gerber_defaults_form.gerber_opt_group.milling_type_radio,
            "gerber_noncoppermargin": self.ui.gerber_defaults_form.gerber_opt_group.noncopper_margin_entry,
            "gerber_noncopperrounded": self.ui.gerber_defaults_form.gerber_opt_group.noncopper_rounded_cb,
            "gerber_bboxmargin": self.ui.gerber_defaults_form.gerber_opt_group.bbmargin_entry,
            "gerber_bboxrounded": self.ui.gerber_defaults_form.gerber_opt_group.bbrounded_cb,

            # Gerber Advanced Options
            "gerber_aperture_display": self.ui.gerber_defaults_form.gerber_adv_opt_group.aperture_table_visibility_cb,
            # "gerber_aperture_scale_factor": self.ui.gerber_defaults_form.gerber_adv_opt_group.scale_aperture_entry,
            # "gerber_aperture_buffer_factor": self.ui.gerber_defaults_form.gerber_adv_opt_group.buffer_aperture_entry,
            "gerber_follow": self.ui.gerber_defaults_form.gerber_adv_opt_group.follow_cb,
            "gerber_tool_type": self.ui.gerber_defaults_form.gerber_adv_opt_group.tool_type_radio,
            "gerber_vtipdia": self.ui.gerber_defaults_form.gerber_adv_opt_group.tipdia_spinner,
            "gerber_vtipangle": self.ui.gerber_defaults_form.gerber_adv_opt_group.tipangle_spinner,
            "gerber_vcutz": self.ui.gerber_defaults_form.gerber_adv_opt_group.cutz_spinner,
            "gerber_iso_type": self.ui.gerber_defaults_form.gerber_adv_opt_group.iso_type_radio,

            "gerber_buffering": self.ui.gerber_defaults_form.gerber_adv_opt_group.buffering_radio,
            "gerber_simplification": self.ui.gerber_defaults_form.gerber_adv_opt_group.simplify_cb,
            "gerber_simp_tolerance": self.ui.gerber_defaults_form.gerber_adv_opt_group.simplification_tol_spinner,

            # Gerber Export
            "gerber_exp_units": self.ui.gerber_defaults_form.gerber_exp_group.gerber_units_radio,
            "gerber_exp_integer": self.ui.gerber_defaults_form.gerber_exp_group.format_whole_entry,
            "gerber_exp_decimals": self.ui.gerber_defaults_form.gerber_exp_group.format_dec_entry,
            "gerber_exp_zeros": self.ui.gerber_defaults_form.gerber_exp_group.zeros_radio,

            # Gerber Editor
            "gerber_editor_sel_limit": self.ui.gerber_defaults_form.gerber_editor_group.sel_limit_entry,
            "gerber_editor_newcode": self.ui.gerber_defaults_form.gerber_editor_group.addcode_entry,
            "gerber_editor_newsize": self.ui.gerber_defaults_form.gerber_editor_group.addsize_entry,
            "gerber_editor_newtype": self.ui.gerber_defaults_form.gerber_editor_group.addtype_combo,
            "gerber_editor_newdim": self.ui.gerber_defaults_form.gerber_editor_group.adddim_entry,
            "gerber_editor_array_size": self.ui.gerber_defaults_form.gerber_editor_group.grb_array_size_entry,
            "gerber_editor_lin_axis": self.ui.gerber_defaults_form.gerber_editor_group.grb_axis_radio,
            "gerber_editor_lin_pitch": self.ui.gerber_defaults_form.gerber_editor_group.grb_pitch_entry,
            "gerber_editor_lin_angle": self.ui.gerber_defaults_form.gerber_editor_group.grb_angle_entry,
            "gerber_editor_circ_dir": self.ui.gerber_defaults_form.gerber_editor_group.grb_circular_dir_radio,
            "gerber_editor_circ_angle":
                self.ui.gerber_defaults_form.gerber_editor_group.grb_circular_angle_entry,
            "gerber_editor_scale_f": self.ui.gerber_defaults_form.gerber_editor_group.grb_scale_entry,
            "gerber_editor_buff_f": self.ui.gerber_defaults_form.gerber_editor_group.grb_buff_entry,
            "gerber_editor_ma_low": self.ui.gerber_defaults_form.gerber_editor_group.grb_ma_low_entry,
            "gerber_editor_ma_high": self.ui.gerber_defaults_form.gerber_editor_group.grb_ma_high_entry,

            # Excellon General
            "excellon_plot": self.ui.excellon_defaults_form.excellon_gen_group.plot_cb,
            "excellon_solid": self.ui.excellon_defaults_form.excellon_gen_group.solid_cb,
            "excellon_format_upper_in":
                self.ui.excellon_defaults_form.excellon_gen_group.excellon_format_upper_in_entry,
            "excellon_format_lower_in":
                self.ui.excellon_defaults_form.excellon_gen_group.excellon_format_lower_in_entry,
            "excellon_format_upper_mm":
                self.ui.excellon_defaults_form.excellon_gen_group.excellon_format_upper_mm_entry,
            "excellon_format_lower_mm":
                self.ui.excellon_defaults_form.excellon_gen_group.excellon_format_lower_mm_entry,
            "excellon_zeros": self.ui.excellon_defaults_form.excellon_gen_group.excellon_zeros_radio,
            "excellon_units": self.ui.excellon_defaults_form.excellon_gen_group.excellon_units_radio,
            "excellon_update": self.ui.excellon_defaults_form.excellon_gen_group.update_excellon_cb,
            "excellon_optimization_type": self.ui.excellon_defaults_form.excellon_gen_group.excellon_optimization_radio,
            "excellon_search_time": self.ui.excellon_defaults_form.excellon_gen_group.optimization_time_entry,

            # Excellon Options
            "excellon_drillz": self.ui.excellon_defaults_form.excellon_opt_group.cutz_entry,
            "excellon_travelz": self.ui.excellon_defaults_form.excellon_opt_group.travelz_entry,
            "excellon_endz": self.ui.excellon_defaults_form.excellon_opt_group.eendz_entry,
            "excellon_feedrate": self.ui.excellon_defaults_form.excellon_opt_group.feedrate_entry,
            "excellon_spindlespeed": self.ui.excellon_defaults_form.excellon_opt_group.spindlespeed_entry,
            "excellon_dwell": self.ui.excellon_defaults_form.excellon_opt_group.dwell_cb,
            "excellon_dwelltime": self.ui.excellon_defaults_form.excellon_opt_group.dwelltime_entry,
            "excellon_toolchange": self.ui.excellon_defaults_form.excellon_opt_group.toolchange_cb,
            "excellon_toolchangez": self.ui.excellon_defaults_form.excellon_opt_group.toolchangez_entry,
            "excellon_ppname_e": self.ui.excellon_defaults_form.excellon_opt_group.pp_excellon_name_cb,
            "excellon_tooldia": self.ui.excellon_defaults_form.excellon_opt_group.tooldia_entry,
            "excellon_slot_tooldia": self.ui.excellon_defaults_form.excellon_opt_group.slot_tooldia_entry,
            "excellon_gcode_type": self.ui.excellon_defaults_form.excellon_opt_group.excellon_gcode_type_radio,

            # Excellon Advanced Options
            "excellon_offset": self.ui.excellon_defaults_form.excellon_adv_opt_group.offset_entry,
            "excellon_toolchangexy": self.ui.excellon_defaults_form.excellon_adv_opt_group.toolchangexy_entry,
            "excellon_startz": self.ui.excellon_defaults_form.excellon_adv_opt_group.estartz_entry,
            "excellon_feedrate_rapid": self.ui.excellon_defaults_form.excellon_adv_opt_group.feedrate_rapid_entry,
            "excellon_z_pdepth": self.ui.excellon_defaults_form.excellon_adv_opt_group.pdepth_entry,
            "excellon_feedrate_probe": self.ui.excellon_defaults_form.excellon_adv_opt_group.feedrate_probe_entry,
            "excellon_spindledir": self.ui.excellon_defaults_form.excellon_adv_opt_group.spindledir_radio,
            "excellon_f_plunge": self.ui.excellon_defaults_form.excellon_adv_opt_group.fplunge_cb,
            "excellon_f_retract": self.ui.excellon_defaults_form.excellon_adv_opt_group.fretract_cb,

            # Excellon Export
            "excellon_exp_units": self.ui.excellon_defaults_form.excellon_exp_group.excellon_units_radio,
            "excellon_exp_format": self.ui.excellon_defaults_form.excellon_exp_group.format_radio,
            "excellon_exp_integer": self.ui.excellon_defaults_form.excellon_exp_group.format_whole_entry,
            "excellon_exp_decimals": self.ui.excellon_defaults_form.excellon_exp_group.format_dec_entry,
            "excellon_exp_zeros": self.ui.excellon_defaults_form.excellon_exp_group.zeros_radio,
            "excellon_exp_slot_type": self.ui.excellon_defaults_form.excellon_exp_group.slot_type_radio,

            # Excellon Editor
            "excellon_editor_sel_limit": self.ui.excellon_defaults_form.excellon_editor_group.sel_limit_entry,
            "excellon_editor_newdia": self.ui.excellon_defaults_form.excellon_editor_group.addtool_entry,
            "excellon_editor_array_size": self.ui.excellon_defaults_form.excellon_editor_group.drill_array_size_entry,
            "excellon_editor_lin_dir": self.ui.excellon_defaults_form.excellon_editor_group.drill_axis_radio,
            "excellon_editor_lin_pitch": self.ui.excellon_defaults_form.excellon_editor_group.drill_pitch_entry,
            "excellon_editor_lin_angle": self.ui.excellon_defaults_form.excellon_editor_group.drill_angle_entry,
            "excellon_editor_circ_dir": self.ui.excellon_defaults_form.excellon_editor_group.drill_circular_dir_radio,
            "excellon_editor_circ_angle":
                self.ui.excellon_defaults_form.excellon_editor_group.drill_circular_angle_entry,
            # Excellon Slots
            "excellon_editor_slot_direction":
                self.ui.excellon_defaults_form.excellon_editor_group.slot_axis_radio,
            "excellon_editor_slot_angle":
                self.ui.excellon_defaults_form.excellon_editor_group.slot_angle_spinner,
            "excellon_editor_slot_length":
                self.ui.excellon_defaults_form.excellon_editor_group.slot_length_entry,
            # Excellon Slots
            "excellon_editor_slot_array_size":
                self.ui.excellon_defaults_form.excellon_editor_group.slot_array_size_entry,
            "excellon_editor_slot_lin_dir": self.ui.excellon_defaults_form.excellon_editor_group.slot_array_axis_radio,
            "excellon_editor_slot_lin_pitch":
                self.ui.excellon_defaults_form.excellon_editor_group.slot_array_pitch_entry,
            "excellon_editor_slot_lin_angle":
                self.ui.excellon_defaults_form.excellon_editor_group.slot_array_angle_entry,
            "excellon_editor_slot_circ_dir":
                self.ui.excellon_defaults_form.excellon_editor_group.slot_array_circular_dir_radio,
            "excellon_editor_slot_circ_angle":
                self.ui.excellon_defaults_form.excellon_editor_group.slot_array_circular_angle_entry,

            # Geometry General
            "geometry_plot": self.ui.geometry_defaults_form.geometry_gen_group.plot_cb,
            "geometry_circle_steps": self.ui.geometry_defaults_form.geometry_gen_group.circle_steps_entry,
            "geometry_cnctooldia": self.ui.geometry_defaults_form.geometry_gen_group.cnctooldia_entry,

            # Geometry Options
            "geometry_cutz": self.ui.geometry_defaults_form.geometry_opt_group.cutz_entry,
            "geometry_travelz": self.ui.geometry_defaults_form.geometry_opt_group.travelz_entry,
            "geometry_feedrate": self.ui.geometry_defaults_form.geometry_opt_group.cncfeedrate_entry,
            "geometry_feedrate_z": self.ui.geometry_defaults_form.geometry_opt_group.cncplunge_entry,
            "geometry_spindlespeed": self.ui.geometry_defaults_form.geometry_opt_group.cncspindlespeed_entry,
            "geometry_dwell": self.ui.geometry_defaults_form.geometry_opt_group.dwell_cb,
            "geometry_dwelltime": self.ui.geometry_defaults_form.geometry_opt_group.dwelltime_entry,
            "geometry_ppname_g": self.ui.geometry_defaults_form.geometry_opt_group.pp_geometry_name_cb,
            "geometry_toolchange": self.ui.geometry_defaults_form.geometry_opt_group.toolchange_cb,
            "geometry_toolchangez": self.ui.geometry_defaults_form.geometry_opt_group.toolchangez_entry,
            "geometry_endz": self.ui.geometry_defaults_form.geometry_opt_group.gendz_entry,
            "geometry_depthperpass": self.ui.geometry_defaults_form.geometry_opt_group.depthperpass_entry,
            "geometry_multidepth": self.ui.geometry_defaults_form.geometry_opt_group.multidepth_cb,

            # Geometry Advanced Options
            "geometry_toolchangexy": self.ui.geometry_defaults_form.geometry_adv_opt_group.toolchangexy_entry,
            "geometry_startz": self.ui.geometry_defaults_form.geometry_adv_opt_group.gstartz_entry,
            "geometry_feedrate_rapid": self.ui.geometry_defaults_form.geometry_adv_opt_group.cncfeedrate_rapid_entry,
            "geometry_extracut": self.ui.geometry_defaults_form.geometry_adv_opt_group.extracut_cb,
            "geometry_z_pdepth": self.ui.geometry_defaults_form.geometry_adv_opt_group.pdepth_entry,
            "geometry_feedrate_probe": self.ui.geometry_defaults_form.geometry_adv_opt_group.feedrate_probe_entry,
            "geometry_spindledir": self.ui.geometry_defaults_form.geometry_adv_opt_group.spindledir_radio,
            "geometry_f_plunge": self.ui.geometry_defaults_form.geometry_adv_opt_group.fplunge_cb,
            "geometry_segx": self.ui.geometry_defaults_form.geometry_adv_opt_group.segx_entry,
            "geometry_segy": self.ui.geometry_defaults_form.geometry_adv_opt_group.segy_entry,

            # Geometry Editor
            "geometry_editor_sel_limit": self.ui.geometry_defaults_form.geometry_editor_group.sel_limit_entry,
            "geometry_editor_milling_type": self.ui.geometry_defaults_form.geometry_editor_group.milling_type_radio,

            # CNCJob General
            "cncjob_plot": self.ui.cncjob_defaults_form.cncjob_gen_group.plot_cb,
            "cncjob_plot_kind": self.ui.cncjob_defaults_form.cncjob_gen_group.cncplot_method_radio,
            "cncjob_annotation": self.ui.cncjob_defaults_form.cncjob_gen_group.annotation_cb,

            "cncjob_tooldia": self.ui.cncjob_defaults_form.cncjob_gen_group.tooldia_entry,
            "cncjob_coords_type": self.ui.cncjob_defaults_form.cncjob_gen_group.coords_type_radio,
            "cncjob_coords_decimals": self.ui.cncjob_defaults_form.cncjob_gen_group.coords_dec_entry,
            "cncjob_fr_decimals": self.ui.cncjob_defaults_form.cncjob_gen_group.fr_dec_entry,
            "cncjob_steps_per_circle": self.ui.cncjob_defaults_form.cncjob_gen_group.steps_per_circle_entry,
            "cncjob_line_ending":  self.ui.cncjob_defaults_form.cncjob_gen_group.line_ending_cb,

            # CNC Job Options
            "cncjob_prepend": self.ui.cncjob_defaults_form.cncjob_opt_group.prepend_text,
            "cncjob_append": self.ui.cncjob_defaults_form.cncjob_opt_group.append_text,

            # CNC Job Advanced Options
            "cncjob_toolchange_macro": self.ui.cncjob_defaults_form.cncjob_adv_opt_group.toolchange_text,
            "cncjob_toolchange_macro_enable": self.ui.cncjob_defaults_form.cncjob_adv_opt_group.toolchange_cb,
            "cncjob_annotation_fontsize": self.ui.cncjob_defaults_form.cncjob_adv_opt_group.annotation_fontsize_sp,
            "cncjob_annotation_fontcolor": self.ui.cncjob_defaults_form.cncjob_adv_opt_group.annotation_fontcolor_entry,

            # NCC Tool
            "tools_ncctools": self.ui.tools_defaults_form.tools_ncc_group.ncc_tool_dia_entry,
            "tools_nccorder": self.ui.tools_defaults_form.tools_ncc_group.ncc_order_radio,
            "tools_nccoverlap": self.ui.tools_defaults_form.tools_ncc_group.ncc_overlap_entry,
            "tools_nccmargin": self.ui.tools_defaults_form.tools_ncc_group.ncc_margin_entry,
            "tools_nccmethod": self.ui.tools_defaults_form.tools_ncc_group.ncc_method_radio,
            "tools_nccconnect": self.ui.tools_defaults_form.tools_ncc_group.ncc_connect_cb,
            "tools_ncccontour": self.ui.tools_defaults_form.tools_ncc_group.ncc_contour_cb,
            "tools_nccrest": self.ui.tools_defaults_form.tools_ncc_group.ncc_rest_cb,
            "tools_ncc_offset_choice": self.ui.tools_defaults_form.tools_ncc_group.ncc_choice_offset_cb,
            "tools_ncc_offset_value": self.ui.tools_defaults_form.tools_ncc_group.ncc_offset_spinner,
            "tools_nccref": self.ui.tools_defaults_form.tools_ncc_group.reference_radio,
            "tools_ncc_plotting": self.ui.tools_defaults_form.tools_ncc_group.ncc_plotting_radio,
            "tools_nccmilling_type": self.ui.tools_defaults_form.tools_ncc_group.milling_type_radio,
            "tools_ncctool_type": self.ui.tools_defaults_form.tools_ncc_group.tool_type_radio,
            "tools_ncccutz": self.ui.tools_defaults_form.tools_ncc_group.cutz_entry,
            "tools_ncctipdia": self.ui.tools_defaults_form.tools_ncc_group.tipdia_entry,
            "tools_ncctipangle": self.ui.tools_defaults_form.tools_ncc_group.tipangle_entry,
            "tools_nccnewdia": self.ui.tools_defaults_form.tools_ncc_group.newdia_entry,

            # CutOut Tool
            "tools_cutouttooldia": self.ui.tools_defaults_form.tools_cutout_group.cutout_tooldia_entry,
            "tools_cutoutkind": self.ui.tools_defaults_form.tools_cutout_group.obj_kind_combo,
            "tools_cutoutmargin": self.ui.tools_defaults_form.tools_cutout_group.cutout_margin_entry,
            "tools_cutoutgapsize": self.ui.tools_defaults_form.tools_cutout_group.cutout_gap_entry,
            "tools_gaps_ff": self.ui.tools_defaults_form.tools_cutout_group.gaps_combo,
            "tools_cutout_convexshape": self.ui.tools_defaults_form.tools_cutout_group.convex_box,

            # Paint Area Tool
            "tools_painttooldia": self.ui.tools_defaults_form.tools_paint_group.painttooldia_entry,
            "tools_paintorder": self.ui.tools_defaults_form.tools_paint_group.paint_order_radio,
            "tools_paintoverlap": self.ui.tools_defaults_form.tools_paint_group.paintoverlap_entry,
            "tools_paintmargin": self.ui.tools_defaults_form.tools_paint_group.paintmargin_entry,
            "tools_paintmethod": self.ui.tools_defaults_form.tools_paint_group.paintmethod_combo,
            "tools_selectmethod": self.ui.tools_defaults_form.tools_paint_group.selectmethod_combo,
            "tools_pathconnect": self.ui.tools_defaults_form.tools_paint_group.pathconnect_cb,
            "tools_paintcontour": self.ui.tools_defaults_form.tools_paint_group.contour_cb,
            "tools_paint_plotting": self.ui.tools_defaults_form.tools_paint_group.paint_plotting_radio,

            # 2-sided Tool
            "tools_2sided_mirror_axis": self.ui.tools_defaults_form.tools_2sided_group.mirror_axis_radio,
            "tools_2sided_axis_loc": self.ui.tools_defaults_form.tools_2sided_group.axis_location_radio,
            "tools_2sided_drilldia": self.ui.tools_defaults_form.tools_2sided_group.drill_dia_entry,

            # Film Tool
            "tools_film_type": self.ui.tools_defaults_form.tools_film_group.film_type_radio,
            "tools_film_boundary": self.ui.tools_defaults_form.tools_film_group.film_boundary_entry,
            "tools_film_scale_stroke": self.ui.tools_defaults_form.tools_film_group.film_scale_stroke_entry,
            "tools_film_color": self.ui.tools_defaults_form.tools_film_group.film_color_entry,
            "tools_film_scale_cb": self.ui.tools_defaults_form.tools_film_group.film_scale_cb,
            "tools_film_scale_x_entry": self.ui.tools_defaults_form.tools_film_group.film_scalex_entry,
            "tools_film_scale_y_entry": self.ui.tools_defaults_form.tools_film_group.film_scaley_entry,
            "tools_film_skew_cb": self.ui.tools_defaults_form.tools_film_group.film_skew_cb,
            "tools_film_skew_x_entry": self.ui.tools_defaults_form.tools_film_group.film_skewx_entry,
            "tools_film_skew_y_entry": self.ui.tools_defaults_form.tools_film_group.film_skewy_entry,
            "tools_film_skew_ref_radio": self.ui.tools_defaults_form.tools_film_group.film_skew_reference,
            "tools_film_mirror_cb": self.ui.tools_defaults_form.tools_film_group.film_mirror_cb,
            "tools_film_mirror_axis_radio": self.ui.tools_defaults_form.tools_film_group.film_mirror_axis,
            "tools_film_file_type_radio": self.ui.tools_defaults_form.tools_film_group.file_type_radio,
            "tools_film_orientation": self.ui.tools_defaults_form.tools_film_group.orientation_radio,
            "tools_film_pagesize": self.ui.tools_defaults_form.tools_film_group.pagesize_combo,

            # Panelize Tool
            "tools_panelize_spacing_columns": self.ui.tools_defaults_form.tools_panelize_group.pspacing_columns,
            "tools_panelize_spacing_rows": self.ui.tools_defaults_form.tools_panelize_group.pspacing_rows,
            "tools_panelize_columns": self.ui.tools_defaults_form.tools_panelize_group.pcolumns,
            "tools_panelize_rows": self.ui.tools_defaults_form.tools_panelize_group.prows,
            "tools_panelize_constrain": self.ui.tools_defaults_form.tools_panelize_group.pconstrain_cb,
            "tools_panelize_constrainx": self.ui.tools_defaults_form.tools_panelize_group.px_width_entry,
            "tools_panelize_constrainy": self.ui.tools_defaults_form.tools_panelize_group.py_height_entry,
            "tools_panelize_panel_type": self.ui.tools_defaults_form.tools_panelize_group.panel_type_radio,

            # Calculators Tool
            "tools_calc_vshape_tip_dia": self.ui.tools_defaults_form.tools_calculators_group.tip_dia_entry,
            "tools_calc_vshape_tip_angle": self.ui.tools_defaults_form.tools_calculators_group.tip_angle_entry,
            "tools_calc_vshape_cut_z": self.ui.tools_defaults_form.tools_calculators_group.cut_z_entry,
            "tools_calc_electro_length": self.ui.tools_defaults_form.tools_calculators_group.pcblength_entry,
            "tools_calc_electro_width": self.ui.tools_defaults_form.tools_calculators_group.pcbwidth_entry,
            "tools_calc_electro_cdensity": self.ui.tools_defaults_form.tools_calculators_group.cdensity_entry,
            "tools_calc_electro_growth": self.ui.tools_defaults_form.tools_calculators_group.growth_entry,

            # Transformations Tool
            "tools_transform_rotate": self.ui.tools_defaults_form.tools_transform_group.rotate_entry,
            "tools_transform_skew_x": self.ui.tools_defaults_form.tools_transform_group.skewx_entry,
            "tools_transform_skew_y": self.ui.tools_defaults_form.tools_transform_group.skewy_entry,
            "tools_transform_scale_x": self.ui.tools_defaults_form.tools_transform_group.scalex_entry,
            "tools_transform_scale_y": self.ui.tools_defaults_form.tools_transform_group.scaley_entry,
            "tools_transform_scale_link": self.ui.tools_defaults_form.tools_transform_group.link_cb,
            "tools_transform_scale_reference": self.ui.tools_defaults_form.tools_transform_group.reference_cb,
            "tools_transform_offset_x": self.ui.tools_defaults_form.tools_transform_group.offx_entry,
            "tools_transform_offset_y": self.ui.tools_defaults_form.tools_transform_group.offy_entry,
            "tools_transform_mirror_reference": self.ui.tools_defaults_form.tools_transform_group.mirror_reference_cb,
            "tools_transform_mirror_point": self.ui.tools_defaults_form.tools_transform_group.flip_ref_entry,

            # SolderPaste Dispensing Tool
            "tools_solderpaste_tools": self.ui.tools_defaults_form.tools_solderpaste_group.nozzle_tool_dia_entry,
            "tools_solderpaste_new": self.ui.tools_defaults_form.tools_solderpaste_group.addtool_entry,
            "tools_solderpaste_z_start": self.ui.tools_defaults_form.tools_solderpaste_group.z_start_entry,
            "tools_solderpaste_z_dispense": self.ui.tools_defaults_form.tools_solderpaste_group.z_dispense_entry,
            "tools_solderpaste_z_stop": self.ui.tools_defaults_form.tools_solderpaste_group.z_stop_entry,
            "tools_solderpaste_z_travel": self.ui.tools_defaults_form.tools_solderpaste_group.z_travel_entry,
            "tools_solderpaste_z_toolchange": self.ui.tools_defaults_form.tools_solderpaste_group.z_toolchange_entry,
            "tools_solderpaste_xy_toolchange": self.ui.tools_defaults_form.tools_solderpaste_group.xy_toolchange_entry,
            "tools_solderpaste_frxy": self.ui.tools_defaults_form.tools_solderpaste_group.frxy_entry,
            "tools_solderpaste_frz": self.ui.tools_defaults_form.tools_solderpaste_group.frz_entry,
            "tools_solderpaste_frz_dispense": self.ui.tools_defaults_form.tools_solderpaste_group.frz_dispense_entry,
            "tools_solderpaste_speedfwd": self.ui.tools_defaults_form.tools_solderpaste_group.speedfwd_entry,
            "tools_solderpaste_dwellfwd": self.ui.tools_defaults_form.tools_solderpaste_group.dwellfwd_entry,
            "tools_solderpaste_speedrev": self.ui.tools_defaults_form.tools_solderpaste_group.speedrev_entry,
            "tools_solderpaste_dwellrev": self.ui.tools_defaults_form.tools_solderpaste_group.dwellrev_entry,
            "tools_solderpaste_pp": self.ui.tools_defaults_form.tools_solderpaste_group.pp_combo,
            "tools_sub_close_paths": self.ui.tools_defaults_form.tools_sub_group.close_paths_cb,

            # ###################################################################################
            # ################################ TOOLS 2 ##########################################
            # ###################################################################################

            # Optimal Tool
            "tools_opt_precision": self.ui.tools2_defaults_form.tools2_optimal_group.precision_sp,

            # Check Rules Tool
            "tools_cr_trace_size": self.ui.tools2_defaults_form.tools2_checkrules_group.trace_size_cb,
            "tools_cr_trace_size_val": self.ui.tools2_defaults_form.tools2_checkrules_group.trace_size_entry,
            "tools_cr_c2c": self.ui.tools2_defaults_form.tools2_checkrules_group.clearance_copper2copper_cb,
            "tools_cr_c2c_val": self.ui.tools2_defaults_form.tools2_checkrules_group.clearance_copper2copper_entry,
            "tools_cr_c2o": self.ui.tools2_defaults_form.tools2_checkrules_group.clearance_copper2ol_cb,
            "tools_cr_c2o_val": self.ui.tools2_defaults_form.tools2_checkrules_group.clearance_copper2ol_entry,
            "tools_cr_s2s": self.ui.tools2_defaults_form.tools2_checkrules_group.clearance_silk2silk_cb,
            "tools_cr_s2s_val": self.ui.tools2_defaults_form.tools2_checkrules_group.clearance_silk2silk_entry,
            "tools_cr_s2sm": self.ui.tools2_defaults_form.tools2_checkrules_group.clearance_silk2sm_cb,
            "tools_cr_s2sm_val": self.ui.tools2_defaults_form.tools2_checkrules_group.clearance_silk2sm_entry,
            "tools_cr_s2o": self.ui.tools2_defaults_form.tools2_checkrules_group.clearance_silk2ol_cb,
            "tools_cr_s2o_val": self.ui.tools2_defaults_form.tools2_checkrules_group.clearance_silk2ol_entry,
            "tools_cr_sm2sm": self.ui.tools2_defaults_form.tools2_checkrules_group.clearance_sm2sm_cb,
            "tools_cr_sm2sm_val": self.ui.tools2_defaults_form.tools2_checkrules_group.clearance_sm2sm_entry,
            "tools_cr_ri": self.ui.tools2_defaults_form.tools2_checkrules_group.ring_integrity_cb,
            "tools_cr_ri_val": self.ui.tools2_defaults_form.tools2_checkrules_group.ring_integrity_entry,
            "tools_cr_h2h": self.ui.tools2_defaults_form.tools2_checkrules_group.clearance_d2d_cb,
            "tools_cr_h2h_val": self.ui.tools2_defaults_form.tools2_checkrules_group.clearance_d2d_entry,
            "tools_cr_dh": self.ui.tools2_defaults_form.tools2_checkrules_group.drill_size_cb,
            "tools_cr_dh_val": self.ui.tools2_defaults_form.tools2_checkrules_group.drill_size_entry,

            # QRCode Tool
            "tools_qrcode_version": self.ui.tools2_defaults_form.tools2_qrcode_group.version_entry,
            "tools_qrcode_error": self.ui.tools2_defaults_form.tools2_qrcode_group.error_radio,
            "tools_qrcode_box_size": self.ui.tools2_defaults_form.tools2_qrcode_group.bsize_entry,
            "tools_qrcode_border_size": self.ui.tools2_defaults_form.tools2_qrcode_group.border_size_entry,
            "tools_qrcode_qrdata": self.ui.tools2_defaults_form.tools2_qrcode_group.text_data,
            "tools_qrcode_polarity": self.ui.tools2_defaults_form.tools2_qrcode_group.pol_radio,
            "tools_qrcode_rounded": self.ui.tools2_defaults_form.tools2_qrcode_group.bb_radio,
            "tools_qrcode_fill_color": self.ui.tools2_defaults_form.tools2_qrcode_group.fill_color_entry,
            "tools_qrcode_back_color": self.ui.tools2_defaults_form.tools2_qrcode_group.back_color_entry,
            "tools_qrcode_sel_limit": self.ui.tools2_defaults_form.tools2_qrcode_group.sel_limit_entry,

            # Copper Thieving Tool
            "tools_copper_thieving_clearance": self.ui.tools2_defaults_form.tools2_cfill_group.clearance_entry,
            "tools_copper_thieving_margin": self.ui.tools2_defaults_form.tools2_cfill_group.margin_entry,
            "tools_copper_thieving_reference": self.ui.tools2_defaults_form.tools2_cfill_group.reference_radio,
            "tools_copper_thieving_box_type": self.ui.tools2_defaults_form.tools2_cfill_group.bbox_type_radio,
            "tools_copper_thieving_circle_steps": self.ui.tools2_defaults_form.tools2_cfill_group.circlesteps_entry,
            "tools_copper_thieving_fill_type": self.ui.tools2_defaults_form.tools2_cfill_group.fill_type_radio,
            "tools_copper_thieving_dots_dia": self.ui.tools2_defaults_form.tools2_cfill_group.dot_dia_entry,
            "tools_copper_thieving_dots_spacing": self.ui.tools2_defaults_form.tools2_cfill_group.dot_spacing_entry,
            "tools_copper_thieving_squares_size": self.ui.tools2_defaults_form.tools2_cfill_group.square_size_entry,
            "tools_copper_thieving_squares_spacing":
                self.ui.tools2_defaults_form.tools2_cfill_group.squares_spacing_entry,
            "tools_copper_thieving_lines_size": self.ui.tools2_defaults_form.tools2_cfill_group.line_size_entry,
            "tools_copper_thieving_lines_spacing": self.ui.tools2_defaults_form.tools2_cfill_group.lines_spacing_entry,
            "tools_copper_thieving_rb_margin": self.ui.tools2_defaults_form.tools2_cfill_group.rb_margin_entry,
            "tools_copper_thieving_rb_thickness": self.ui.tools2_defaults_form.tools2_cfill_group.rb_thickness_entry,

            # Fiducials Tool
            "tools_fiducials_dia": self.ui.tools2_defaults_form.tools2_fiducials_group.dia_entry,
            "tools_fiducials_margin": self.ui.tools2_defaults_form.tools2_fiducials_group.margin_entry,
            "tools_fiducials_mode": self.ui.tools2_defaults_form.tools2_fiducials_group.mode_radio,
            "tools_fiducials_second_pos": self.ui.tools2_defaults_form.tools2_fiducials_group.pos_radio,
            "tools_fiducials_type": self.ui.tools2_defaults_form.tools2_fiducials_group.fid_type_radio,
            "tools_fiducials_line_thickness": self.ui.tools2_defaults_form.tools2_fiducials_group.line_thickness_entry,

            # Utilities
            # File associations
            "fa_excellon": self.ui.util_defaults_form.fa_excellon_group.exc_list_text,
            "fa_gcode": self.ui.util_defaults_form.fa_gcode_group.gco_list_text,
            # "fa_geometry": self.ui.util_defaults_form.fa_geometry_group.close_paths_cb,
            "fa_gerber": self.ui.util_defaults_form.fa_gerber_group.grb_list_text,
            "util_autocomplete_keywords": self.ui.util_defaults_form.kw_group.kw_list_text,

        }

        # update the Preferences GUI elements with the values in the self.defaults
        self.defaults_write_form()

        # When the self.defaults dictionary changes will update the Preferences GUI forms
        self.defaults.set_change_callback(self.on_defaults_dict_change)

        # #############################################################################
        # ############################## Data #########################################
        # #############################################################################

        self.recent = []
        self.recent_projects = []

        self.clipboard = QtWidgets.QApplication.clipboard()

        self.project_filename = None
        self.toggle_units_ignore = False

        # #############################################################################
        # ########################## LOAD POSTPROCESSORS ##############################
        # #############################################################################

        # a dictionary that have as keys the name of the postprocessor files and the value is the class from
        # the postprocessor file
        self.postprocessors = load_postprocessors(self)

        # make sure that always the 'default' postprocessor is the first item in the dictionary
        if 'default' in self.postprocessors.keys():
            new_ppp_dict = dict()

            # add the 'default' name first in the dict after removing from the postprocessor's dictionary
            default_pp = self.postprocessors.pop('default')
            new_ppp_dict['default'] = default_pp

            # then add the rest of the keys
            for name, val_class in self.postprocessors.items():
                new_ppp_dict[name] = val_class

            # and now put back the ordered dict with 'default' key first
            self.postprocessors = new_ppp_dict

        for name in list(self.postprocessors.keys()):
            # 'Paste' postprocessors are to be used only in the Solder Paste Dispensing Tool
            if name.partition('_')[0] == 'Paste':
                self.ui.tools_defaults_form.tools_solderpaste_group.pp_combo.addItem(name)
                continue

            self.ui.geometry_defaults_form.geometry_opt_group.pp_geometry_name_cb.addItem(name)
            # HPGL postprocessor is only for Geometry objects therefore it should not be in the Excellon Preferences
            if name == 'hpgl':
                continue

            self.ui.excellon_defaults_form.excellon_opt_group.pp_excellon_name_cb.addItem(name)

        # #############################################################################
        # ########################## LOAD LANGUAGES  ##################################
        # #############################################################################

        self.languages = fcTranslate.load_languages()
        for name in sorted(self.languages.values()):
            self.ui.general_defaults_form.general_app_group.language_cb.addItem(name)

        # #############################################################################
        # ############################ APPLY APP LANGUAGE #############################
        # #############################################################################

        ret_val = fcTranslate.apply_language('strings')

        if ret_val == "no language":
            self.inform.emit('[ERROR] %s' %
                             _("Could not find the Language files. The App strings are missing."))
            log.debug("Could not find the Language files. The App strings are missing.")
        else:
            # make the current language the current selection on the language combobox
            self.ui.general_defaults_form.general_app_group.language_cb.setCurrentText(ret_val)
            log.debug("App.__init__() --> Applied %s language." % str(ret_val).capitalize())

        # #############################################################################
        # ########################### CREATE UNIQUE SERIAL NUMBER #####################
        # #############################################################################

        chars = 'abcdefghijklmnopqrstuvwxyz0123456789'
        if self.defaults['global_serial'] == 0 or len(str(self.defaults['global_serial'])) < 10:
            self.defaults['global_serial'] = ''.join([random.choice(chars) for __ in range(20)])
            self.save_defaults(silent=True, first_time=True)

        self.propagate_defaults(silent=True)

        # def auto_save_defaults():
        #     try:
        #         self.save_defaults(silent=True)
        #         self.propagate_defaults(silent=True)
        #     finally:
        #         QtCore.QTimer.singleShot(self.defaults["global_defaults_save_period_ms"], auto_save_defaults)

        # the following lines activates automatic defaults save
        # if user_defaults:
        #     QtCore.QTimer.singleShot(self.defaults["global_defaults_save_period_ms"], auto_save_defaults)

        # #############################################################################
        # ########################### UPDATE THE OPTIONS ##############################
        # #############################################################################

        self.options = LoudDict()
        # ----------------------------------------------------------------------------------------------------
        #   Update the self.options from the self.defaults
        #   The self.defaults holds the application defaults while the self.options holds the object defaults
        # -----------------------------------------------------------------------------------------------------
        # Copy app defaults to project options
        for def_key, def_val in self.defaults.items():
            self.options[def_key] = deepcopy(def_val)
        # self.options.update(self.defaults)

        self.gen_form = None
        self.ger_form = None
        self.exc_form = None
        self.geo_form = None
        self.cnc_form = None
        self.tools_form = None
        self.tools2_form = None
        self.fa_form = None

        # Will show the Preferences GUI
        self.show_preferences_gui()
        # Initialize the color box's color in Preferences -> Global -> Color
        self.init_color_pickers_in_preferences_gui()

        # ### End of Data ####

        # #############################################################################
        # ######################## SETUP OBJECT COLLECTION ############################
        # #############################################################################

        self.collection = ObjectCollection(self)
        self.ui.project_tab_layout.addWidget(self.collection.view)

        # ### Adjust tabs width ## ##
        # self.collection.view.setMinimumWidth(self.ui.options_scroll_area.widget().sizeHint().width() +
        #     self.ui.options_scroll_area.verticalScrollBar().sizeHint().width())
        self.collection.view.setMinimumWidth(290)
        self.log.debug("Finished creating Object Collection.")

        # #############################################################################
        # ############################## SETUP Plot Area ##############################
        # #############################################################################

        # determine if the Legacy Graphic Engine is to be used or the OpenGL one
        if self.defaults["global_graphic_engine"] == '3D':
            self.is_legacy = False
        else:
            self.is_legacy = True

        # Event signals disconnect id holders
        self.mp = None
        self.mm = None
        self.mr = None
        self.mdc = None
        self.mp_zc = None

        # Matplotlib axis
        self.axes = None

        if show_splash:
            self.splash.showMessage(_("FlatCAM is initializing ...\n"
                                      "Canvas initialization started."),
                                    alignment=Qt.AlignBottom | Qt.AlignLeft,
                                    color=QtGui.QColor("gray"))
        start_plot_time = time.time()   # debug
        self.plotcanvas = None

        self.app_cursor = None
        self.hover_shapes = None

        # setup the PlotCanvas
        self.on_plotcanvas_setup()

        end_plot_time = time.time()
        self.used_time = end_plot_time - start_plot_time
        self.log.debug("Finished Canvas initialization in %s seconds." % str(self.used_time))

        if show_splash:
            self.splash.showMessage('%s: %ssec' % (_("FlatCAM is initializing ...\n"
                                                     "Canvas initialization started.\n"
                                                     "Canvas initialization finished in"), '%.2f' % self.used_time),
                                    alignment=Qt.AlignBottom | Qt.AlignLeft,
                                    color=QtGui.QColor("gray"))
        self.ui.splitter.setStretchFactor(1, 2)

        # #############################################################################
        # ################################### SYS TRAY ################################
        # #############################################################################
        if self.defaults["global_systray_icon"]:
            self.parent_w = QtWidgets.QWidget()

            if self.cmd_line_headless == 1:
                self.trayIcon = FlatCAMSystemTray(app=self, icon=QtGui.QIcon('share/flatcam_icon32_green.png'),
                                                  headless=True,
                                                  parent=self.parent_w)
            else:
                self.trayIcon = FlatCAMSystemTray(app=self, icon=QtGui.QIcon('share/flatcam_icon32_green.png'),
                                                  parent=self.parent_w)

        # #############################################################################
        # ################################## Worker SETUP #############################
        # #############################################################################
        if self.defaults["global_worker_number"]:
            self.workers = WorkerStack(workers_number=int(self.defaults["global_worker_number"]))
        else:
            self.workers = WorkerStack(workers_number=2)
        self.worker_task.connect(self.workers.add_task)
        self.log.debug("Finished creating Workers crew.")

        # #############################################################################
        # ################################# Activity Monitor ##########################
        # #############################################################################
        self.activity_view = FlatCAMActivityView(app=self)
        self.ui.infobar.addWidget(self.activity_view)
        self.proc_container = FCVisibleProcessContainer(self.activity_view)

        # #############################################################################
        # ################################## Signal handling ##########################
        # #############################################################################

        # ################################# Custom signals  ###########################
        # signal for displaying messages in status bar
        self.inform.connect(self.info)
        # signal to be called when the app is quiting
        self.app_quit.connect(self.quit_application)
        self.message.connect(self.message_dialog)
        self.progress.connect(self.set_progress_bar)

        # signals that are emitted when object state changes
        self.object_created.connect(self.on_object_created)
        self.object_changed.connect(self.on_object_changed)
        self.object_plotted.connect(self.on_object_plotted)
        self.plots_updated.connect(self.on_plots_updated)

        # signals emitted when file state change
        self.file_opened.connect(self.register_recent)
        self.file_opened.connect(lambda kind, filename: self.register_folder(filename))
        self.file_saved.connect(lambda kind, filename: self.register_save_folder(filename))

        # ############# Standard signals ###################
        # ### Menu
        self.ui.menufilenewproject.triggered.connect(self.on_file_new_click)
        self.ui.menufilenewgeo.triggered.connect(self.new_geometry_object)
        self.ui.menufilenewgrb.triggered.connect(self.new_gerber_object)
        self.ui.menufilenewexc.triggered.connect(self.new_excellon_object)
        self.ui.menufilenewdoc.triggered.connect(self.new_document_object)

        self.ui.menufileopengerber.triggered.connect(self.on_fileopengerber)
        self.ui.menufileopenexcellon.triggered.connect(self.on_fileopenexcellon)
        self.ui.menufileopengcode.triggered.connect(self.on_fileopengcode)
        self.ui.menufileopenproject.triggered.connect(self.on_file_openproject)
        self.ui.menufileopenconfig.triggered.connect(self.on_file_openconfig)

        self.ui.menufilenewscript.triggered.connect(self.on_filenewscript)
        self.ui.menufileopenscript.triggered.connect(self.on_fileopenscript)

        self.ui.menufilerunscript.triggered.connect(self.on_filerunscript)

        self.ui.menufileimportsvg.triggered.connect(lambda: self.on_file_importsvg("geometry"))
        self.ui.menufileimportsvg_as_gerber.triggered.connect(lambda: self.on_file_importsvg("gerber"))

        self.ui.menufileimportdxf.triggered.connect(lambda: self.on_file_importdxf("geometry"))
        self.ui.menufileimportdxf_as_gerber.triggered.connect(lambda: self.on_file_importdxf("gerber"))

        self.ui.menufileexportsvg.triggered.connect(self.on_file_exportsvg)
        self.ui.menufileexportpng.triggered.connect(self.on_file_exportpng)
        self.ui.menufileexportexcellon.triggered.connect(self.on_file_exportexcellon)
        self.ui.menufileexportgerber.triggered.connect(self.on_file_exportgerber)

        self.ui.menufileexportdxf.triggered.connect(self.on_file_exportdxf)

        self.ui.menufilesaveproject.triggered.connect(self.on_file_saveproject)
        self.ui.menufilesaveprojectas.triggered.connect(self.on_file_saveprojectas)
        self.ui.menufilesaveprojectcopy.triggered.connect(lambda: self.on_file_saveprojectas(make_copy=True))
        self.ui.menufilesavedefaults.triggered.connect(self.on_file_savedefaults)

        self.ui.menufileexportpref.triggered.connect(self.on_export_preferences)
        self.ui.menufileimportpref.triggered.connect(self.on_import_preferences)

        self.ui.menufile_exit.triggered.connect(self.final_save)

        self.ui.menueditedit.triggered.connect(lambda: self.object2editor())
        self.ui.menueditok.triggered.connect(lambda: self.editor2object())

        self.ui.menuedit_convertjoin.triggered.connect(self.on_edit_join)
        self.ui.menuedit_convertjoinexc.triggered.connect(self.on_edit_join_exc)
        self.ui.menuedit_convertjoingrb.triggered.connect(self.on_edit_join_grb)

        self.ui.menuedit_convert_sg2mg.triggered.connect(self.on_convert_singlegeo_to_multigeo)
        self.ui.menuedit_convert_mg2sg.triggered.connect(self.on_convert_multigeo_to_singlegeo)

        self.ui.menueditdelete.triggered.connect(self.on_delete)

        self.ui.menueditcopyobject.triggered.connect(self.on_copy_object)
        self.ui.menueditconvert_any2geo.triggered.connect(self.convert_any2geo)
        self.ui.menueditconvert_any2gerber.triggered.connect(self.convert_any2gerber)

        self.ui.menueditorigin.triggered.connect(self.on_set_origin)
        self.ui.menueditjump.triggered.connect(self.on_jump_to)

        self.ui.menuedittoggleunits.triggered.connect(self.on_toggle_units_click)
        self.ui.menueditselectall.triggered.connect(self.on_selectall)
        self.ui.menueditpreferences.triggered.connect(self.on_preferences)

        # self.ui.menuoptions_transfer_a2o.triggered.connect(self.on_options_app2object)
        # self.ui.menuoptions_transfer_a2p.triggered.connect(self.on_options_app2project)
        # self.ui.menuoptions_transfer_o2a.triggered.connect(self.on_options_object2app)
        # self.ui.menuoptions_transfer_p2a.triggered.connect(self.on_options_project2app)
        # self.ui.menuoptions_transfer_o2p.triggered.connect(self.on_options_object2project)
        # self.ui.menuoptions_transfer_p2o.triggered.connect(self.on_options_project2object)

        self.ui.menuoptions_transform_rotate.triggered.connect(self.on_rotate)

        self.ui.menuoptions_transform_skewx.triggered.connect(self.on_skewx)
        self.ui.menuoptions_transform_skewy.triggered.connect(self.on_skewy)

        self.ui.menuoptions_transform_flipx.triggered.connect(self.on_flipx)
        self.ui.menuoptions_transform_flipy.triggered.connect(self.on_flipy)
        self.ui.menuoptions_view_source.triggered.connect(self.on_view_source)
        self.ui.menuoptions_tools_db.triggered.connect(self.on_tools_database)

        self.ui.menuviewdisableall.triggered.connect(self.disable_all_plots)
        self.ui.menuviewdisableother.triggered.connect(self.disable_other_plots)
        self.ui.menuviewenable.triggered.connect(self.enable_all_plots)

        self.ui.menuview_zoom_fit.triggered.connect(self.on_zoom_fit)
        self.ui.menuview_zoom_in.triggered.connect(self.on_zoom_in)
        self.ui.menuview_zoom_out.triggered.connect(self.on_zoom_out)
        self.ui.menuview_replot.triggered.connect(self.plot_all)

        self.ui.menuview_toggle_code_editor.triggered.connect(self.on_toggle_code_editor)
        self.ui.menuview_toggle_fscreen.triggered.connect(self.on_fullscreen)
        self.ui.menuview_toggle_parea.triggered.connect(self.on_toggle_plotarea)
        self.ui.menuview_toggle_notebook.triggered.connect(self.on_toggle_notebook)
        self.ui.menu_toggle_nb.triggered.connect(self.on_toggle_notebook)
        self.ui.menuview_toggle_grid.triggered.connect(self.on_toggle_grid)
        self.ui.menuview_toggle_grid_lines.triggered.connect(self.on_toggle_grid_lines)
        self.ui.menuview_toggle_axis.triggered.connect(self.on_toggle_axis)
        self.ui.menuview_toggle_workspace.triggered.connect(self.on_workspace_toggle)

        self.ui.menutoolshell.triggered.connect(self.on_toggle_shell)

        self.ui.menuhelp_about.triggered.connect(self.on_about)
        self.ui.menuhelp_manual.triggered.connect(lambda: webbrowser.open(self.manual_url))
        self.ui.menuhelp_report_bug.triggered.connect(lambda: webbrowser.open(self.bug_report_url))
        self.ui.menuhelp_exc_spec.triggered.connect(lambda: webbrowser.open(self.excellon_spec_url))
        self.ui.menuhelp_gerber_spec.triggered.connect(lambda: webbrowser.open(self.gerber_spec_url))
        self.ui.menuhelp_videohelp.triggered.connect(lambda: webbrowser.open(self.video_url))
        self.ui.menuhelp_shortcut_list.triggered.connect(self.on_shortcut_list)

        self.ui.menuprojectenable.triggered.connect(self.on_enable_sel_plots)
        self.ui.menuprojectdisable.triggered.connect(self.on_disable_sel_plots)
        self.ui.menuprojectgeneratecnc.triggered.connect(lambda: self.generate_cnc_job(self.collection.get_selected()))
        self.ui.menuprojectviewsource.triggered.connect(self.on_view_source)

        self.ui.menuprojectcopy.triggered.connect(self.on_copy_object)
        self.ui.menuprojectedit.triggered.connect(self.object2editor)

        self.ui.menuprojectdelete.triggered.connect(self.on_delete)
        self.ui.menuprojectsave.triggered.connect(self.on_project_context_save)
        self.ui.menuprojectproperties.triggered.connect(self.obj_properties)

        # ToolBar signals
        self.connect_toolbar_signals()

        # Notebook and Plot Tab Area signals
        # make the right click on the notebook tab and plot tab area tab raise a menu
        self.ui.notebook.tabBar.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.ui.plot_tab_area.tabBar.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.on_tab_setup_context_menu()
        # activate initial state
        self.on_tab_rmb_click(self.defaults["global_tabs_detachable"])

        # Context Menu
        self.ui.popmenu_disable.triggered.connect(lambda: self.toggle_plots(self.collection.get_selected()))
        self.ui.popmenu_panel_toggle.triggered.connect(self.on_toggle_notebook)

        self.ui.popmenu_new_geo.triggered.connect(self.new_geometry_object)
        self.ui.popmenu_new_grb.triggered.connect(self.new_gerber_object)
        self.ui.popmenu_new_exc.triggered.connect(self.new_excellon_object)
        self.ui.popmenu_new_prj.triggered.connect(self.on_file_new)

        self.ui.zoomfit.triggered.connect(self.on_zoom_fit)
        self.ui.clearplot.triggered.connect(self.clear_plots)
        self.ui.replot.triggered.connect(self.plot_all)

        self.ui.popmenu_copy.triggered.connect(self.on_copy_object)
        self.ui.popmenu_delete.triggered.connect(self.on_delete)
        self.ui.popmenu_edit.triggered.connect(self.object2editor)
        self.ui.popmenu_save.triggered.connect(lambda: self.editor2object())
        self.ui.popmenu_move.triggered.connect(self.obj_move)

        self.ui.popmenu_properties.triggered.connect(self.obj_properties)

        # Preferences Plot Area TAB
        self.ui.pref_save_button.clicked.connect(lambda: self.on_save_button(save_to_file=True))
        self.ui.pref_apply_button.clicked.connect(lambda: self.on_save_button(save_to_file=False))

        self.ui.pref_import_button.clicked.connect(self.on_import_preferences)
        self.ui.pref_export_button.clicked.connect(self.on_export_preferences)
        self.ui.pref_open_button.clicked.connect(self.on_preferences_open_folder)

        # #############################################################################
        # ######################### GUI PREFERENCES SIGNALS ###########################
        # #############################################################################

        self.ui.general_defaults_form.general_app_group.ge_radio.activated_custom.connect(self.on_app_restart)
        self.ui.general_defaults_form.general_app_group.language_apply_btn.clicked.connect(
            lambda: fcTranslate.on_language_apply_click(self, restart=True)
        )
        self.ui.general_defaults_form.general_app_group.units_radio.activated_custom.connect(
            lambda: self.on_toggle_units(no_pref=False))

        # #############################################################################
        # ############################# GUI COLORS SIGNALS ############################
        # #############################################################################

        # Setting plot colors signals
        self.ui.general_defaults_form.general_gui_group.pf_color_entry.editingFinished.connect(
            self.on_pf_color_entry)
        self.ui.general_defaults_form.general_gui_group.pf_color_button.clicked.connect(
            self.on_pf_color_button)
        self.ui.general_defaults_form.general_gui_group.pf_color_alpha_spinner.valueChanged.connect(
            self.on_pf_color_spinner)
        self.ui.general_defaults_form.general_gui_group.pf_color_alpha_slider.valueChanged.connect(
            self.on_pf_color_slider)
        self.ui.general_defaults_form.general_gui_group.pl_color_entry.editingFinished.connect(
            self.on_pl_color_entry)
        self.ui.general_defaults_form.general_gui_group.pl_color_button.clicked.connect(
            self.on_pl_color_button)
        # Setting selection (left - right) colors signals
        self.ui.general_defaults_form.general_gui_group.sf_color_entry.editingFinished.connect(
            self.on_sf_color_entry)
        self.ui.general_defaults_form.general_gui_group.sf_color_button.clicked.connect(
            self.on_sf_color_button)
        self.ui.general_defaults_form.general_gui_group.sf_color_alpha_spinner.valueChanged.connect(
            self.on_sf_color_spinner)
        self.ui.general_defaults_form.general_gui_group.sf_color_alpha_slider.valueChanged.connect(
            self.on_sf_color_slider)
        self.ui.general_defaults_form.general_gui_group.sl_color_entry.editingFinished.connect(
            self.on_sl_color_entry)
        self.ui.general_defaults_form.general_gui_group.sl_color_button.clicked.connect(
            self.on_sl_color_button)
        # Setting selection (right - left) colors signals
        self.ui.general_defaults_form.general_gui_group.alt_sf_color_entry.editingFinished.connect(
            self.on_alt_sf_color_entry)
        self.ui.general_defaults_form.general_gui_group.alt_sf_color_button.clicked.connect(
            self.on_alt_sf_color_button)
        self.ui.general_defaults_form.general_gui_group.alt_sf_color_alpha_spinner.valueChanged.connect(
            self.on_alt_sf_color_spinner)
        self.ui.general_defaults_form.general_gui_group.alt_sf_color_alpha_slider.valueChanged.connect(
            self.on_alt_sf_color_slider)
        self.ui.general_defaults_form.general_gui_group.alt_sl_color_entry.editingFinished.connect(
            self.on_alt_sl_color_entry)
        self.ui.general_defaults_form.general_gui_group.alt_sl_color_button.clicked.connect(
            self.on_alt_sl_color_button)
        # Setting Editor Draw colors signals
        self.ui.general_defaults_form.general_gui_group.draw_color_entry.editingFinished.connect(
            self.on_draw_color_entry)
        self.ui.general_defaults_form.general_gui_group.draw_color_button.clicked.connect(
            self.on_draw_color_button)

        self.ui.general_defaults_form.general_gui_group.sel_draw_color_entry.editingFinished.connect(
            self.on_sel_draw_color_entry)
        self.ui.general_defaults_form.general_gui_group.sel_draw_color_button.clicked.connect(
            self.on_sel_draw_color_button)

        self.ui.general_defaults_form.general_gui_group.proj_color_entry.editingFinished.connect(
            self.on_proj_color_entry)
        self.ui.general_defaults_form.general_gui_group.proj_color_button.clicked.connect(
            self.on_proj_color_button)

        self.ui.general_defaults_form.general_gui_group.proj_color_dis_entry.editingFinished.connect(
            self.on_proj_color_dis_entry)
        self.ui.general_defaults_form.general_gui_group.proj_color_dis_button.clicked.connect(
            self.on_proj_color_dis_button)

        # ############################# workspace setting signals #####################
        self.ui.general_defaults_form.general_gui_group.wk_cb.currentIndexChanged.connect(self.on_workspace_modified)
        self.ui.general_defaults_form.general_gui_group.wk_orientation_radio.activated_custom.connect(
            self.on_workspace_modified
        )

        self.ui.general_defaults_form.general_gui_group.workspace_cb.stateChanged.connect(self.on_workspace)

        self.ui.general_defaults_form.general_gui_set_group.layout_combo.activated.connect(self.on_layout)

        # #############################################################################
        # ############################# GUI SETTINGS SIGNALS ##########################
        # #############################################################################

        self.ui.general_defaults_form.general_gui_set_group.theme_radio.activated_custom.connect(self.on_theme_change)
        self.ui.general_defaults_form.general_gui_set_group.cursor_radio.activated_custom.connect(self.on_cursor_type)

        # ########## CNC Job related signals #############
        self.ui.cncjob_defaults_form.cncjob_adv_opt_group.tc_variable_combo.currentIndexChanged[str].connect(
            self.on_cnc_custom_parameters)
        self.ui.cncjob_defaults_form.cncjob_adv_opt_group.annotation_fontcolor_entry.editingFinished.connect(
            self.on_annotation_fontcolor_entry)
        self.ui.cncjob_defaults_form.cncjob_adv_opt_group.annotation_fontcolor_button.clicked.connect(
            self.on_annotation_fontcolor_button)

        # ########## Tools related signals #############
        # Film Tool
        self.ui.tools_defaults_form.tools_film_group.film_color_entry.editingFinished.connect(
            self.on_film_color_entry)
        self.ui.tools_defaults_form.tools_film_group.film_color_button.clicked.connect(
            self.on_film_color_button)

        # QRCode Tool
        self.ui.tools2_defaults_form.tools2_qrcode_group.fill_color_entry.editingFinished.connect(
            self.on_qrcode_fill_color_entry)
        self.ui.tools2_defaults_form.tools2_qrcode_group.fill_color_button.clicked.connect(
            self.on_qrcode_fill_color_button)
        self.ui.tools2_defaults_form.tools2_qrcode_group.back_color_entry.editingFinished.connect(
            self.on_qrcode_back_color_entry)
        self.ui.tools2_defaults_form.tools2_qrcode_group.back_color_button.clicked.connect(
            self.on_qrcode_back_color_button)

        # portability changed signal
        self.ui.general_defaults_form.general_app_group.portability_cb.stateChanged.connect(self.on_portable_checked)

        # Object list
        self.collection.view.activated.connect(self.on_row_activated)
        self.collection.item_selected.connect(self.on_row_selected)

        self.object_status_changed.connect(self.on_collection_updated)

        # Monitor the checkbox from the Application Defaults Tab and show the TCL shell or not depending on it's value
        self.ui.general_defaults_form.general_gui_set_group.shell_startup_cb.clicked.connect(self.on_toggle_shell)

        # Make sure that when the Excellon loading parameters are changed, the change is reflected in the
        # Export Excellon parameters.
        self.ui.excellon_defaults_form.excellon_gen_group.update_excellon_cb.stateChanged.connect(
            self.on_update_exc_export
        )
        # call it once to make sure it is updated at startup
        self.on_update_exc_export(state=self.defaults["excellon_update"])

        # Load the defaults values into the Excellon Format and Excellon Zeros fields
        self.ui.excellon_defaults_form.excellon_opt_group.excellon_defaults_button.clicked.connect(
            self.on_excellon_defaults_button)

        # when there are arguments at application startup this get launched
        self.args_at_startup[list].connect(self.on_startup_args)

        # #############################################################################
        # ########################## FILE ASSOCIATIONS SIGNALS ########################
        # #############################################################################

        self.ui.util_defaults_form.fa_excellon_group.restore_btn.clicked.connect(
            lambda: self.restore_extensions(ext_type='excellon'))
        self.ui.util_defaults_form.fa_gcode_group.restore_btn.clicked.connect(
            lambda: self.restore_extensions(ext_type='gcode'))
        self.ui.util_defaults_form.fa_gerber_group.restore_btn.clicked.connect(
            lambda: self.restore_extensions(ext_type='gerber'))

        self.ui.util_defaults_form.fa_excellon_group.del_all_btn.clicked.connect(
            lambda: self.delete_all_extensions(ext_type='excellon'))
        self.ui.util_defaults_form.fa_gcode_group.del_all_btn.clicked.connect(
            lambda: self.delete_all_extensions(ext_type='gcode'))
        self.ui.util_defaults_form.fa_gerber_group.del_all_btn.clicked.connect(
            lambda: self.delete_all_extensions(ext_type='gerber'))

        self.ui.util_defaults_form.fa_excellon_group.add_btn.clicked.connect(
            lambda: self.add_extension(ext_type='excellon'))
        self.ui.util_defaults_form.fa_gcode_group.add_btn.clicked.connect(
            lambda: self.add_extension(ext_type='gcode'))
        self.ui.util_defaults_form.fa_gerber_group.add_btn.clicked.connect(
            lambda: self.add_extension(ext_type='gerber'))

        self.ui.util_defaults_form.fa_excellon_group.del_btn.clicked.connect(
            lambda: self.del_extension(ext_type='excellon'))
        self.ui.util_defaults_form.fa_gcode_group.del_btn.clicked.connect(
            lambda: self.del_extension(ext_type='gcode'))
        self.ui.util_defaults_form.fa_gerber_group.del_btn.clicked.connect(
            lambda: self.del_extension(ext_type='gerber'))

        # connect the 'Apply' buttons from the Preferences/File Associations
        self.ui.util_defaults_form.fa_excellon_group.exc_list_btn.clicked.connect(
            lambda: self.on_register_files(obj_type='excellon'))
        self.ui.util_defaults_form.fa_gcode_group.gco_list_btn.clicked.connect(
            lambda: self.on_register_files(obj_type='gcode'))
        self.ui.util_defaults_form.fa_gerber_group.grb_list_btn.clicked.connect(
            lambda: self.on_register_files(obj_type='gerber'))

        # #############################################################################
        # ################################ KEYWORDS SIGNALS ###########################
        # #############################################################################
        self.ui.util_defaults_form.kw_group.restore_btn.clicked.connect(
            lambda: self.restore_extensions(ext_type='keyword'))
        self.ui.util_defaults_form.kw_group.del_all_btn.clicked.connect(
            lambda: self.delete_all_extensions(ext_type='keyword'))
        self.ui.util_defaults_form.kw_group.add_btn.clicked.connect(
            lambda: self.add_extension(ext_type='keyword'))
        self.ui.util_defaults_form.kw_group.del_btn.clicked.connect(
            lambda: self.del_extension(ext_type='keyword'))

        # splash screen button signal
        self.ui.general_defaults_form.general_gui_set_group.splash_cb.stateChanged.connect(self.on_splash_changed)

        # connect the abort_all_tasks related slots to the related signals
        self.proc_container.idle_flag.connect(self.app_is_idle)

        # signal emitted when a tab is closed in the Plot Area
        self.ui.plot_tab_area.tab_closed_signal.connect(self.on_plot_area_tab_closed)

        # #####################################################################################
        # ########### FINISHED CONNECTING SIGNALS #############################################
        # #####################################################################################
        self.log.debug("Finished connecting Signals.")

        # #####################################################################################
        # ########################## Other setups #############################################
        # #####################################################################################

        # to use for tools like Distance tool who depends on the event sources who are changed inside the Editors
        # depending on from where those tools are called different actions can be done
        self.call_source = 'app'

        # this is a flag to signal to other tools that the ui tooltab is locked and not accessible
        self.tool_tab_locked = False

        # decide if to show or hide the Notebook side of the screen at startup
        if self.defaults["global_project_at_startup"] is True:
            self.ui.splitter.setSizes([1, 1])
        else:
            self.ui.splitter.setSizes([0, 1])

        # Sets up FlatCAMObj, FCProcess and FCProcessContainer.
        self.setup_obj_classes()
        self.setup_component_editor()

        # #####################################################################################
        # ######################### Auto-complete KEYWORDS ####################################
        # #####################################################################################
        self.tcl_commands_list = ['add_circle', 'add_poly', 'add_polygon', 'add_polyline', 'add_rectangle',
                                  'aligndrill', 'aligndrillgrid', 'bbox', 'bounding_box', 'clear', 'cncjob', 'cutout',
                                  'delete', 'drillcncjob', 'export_dxf', 'edxf', 'export_excellon', 'ee', 'export_exc',
                                  'export_gcode', 'export_gerber', 'egr', 'export_svg', 'ext', 'exteriors', 'follow',
                                  'geo_union', 'geocutout', 'get_names', 'get_sys', 'getsys', 'help', 'import_svg',
                                  'interiors', 'isolate', 'join_excellon', 'join_excellons', 'join_geometries',
                                  'join_geometry', 'list_sys', 'listsys', 'milld', 'mills', 'milldrills', 'millslots',
                                  'mirror', 'ncc',
                                  'ncc_clear', 'ncr', 'new', 'new_geometry', 'non_copper_regions', 'offset',
                                  'open_excellon', 'open_gcode', 'open_gerber', 'open_project', 'options', 'origin',
                                  'paint', 'pan', 'panel', 'panelize', 'plot_all', 'plot_objects', 'quit_flatcam',
                                  'save', 'save_project',
                                  'save_sys', 'scale', 'set_active', 'set_origin', 'set_sys',
                                  'setsys', 'skew', 'subtract_poly', 'subtract_rectangle',
                                  'version', 'write_gcode'
                                  ]

        self.default_keywords = ['Desktop', 'Documents', 'FlatConfig', 'FlatPrj', 'Marius', 'My Documents', 'Paste_1',
                                 'Repetier', 'Roland_MDX_20', 'Users', 'Toolchange_Custom', 'Toolchange_Probe_MACH3',
                                 'Toolchange_manual', 'Users', 'all', 'angle_x', 'angle_y', 'auto', 'axis',
                                 'axisoffset',
                                 'box', 'center_x', 'center_y', 'columns', 'combine', 'connect', 'contour', 'default',
                                 'depthperpass', 'dia', 'diatol', 'dist', 'drilled_dias', 'drillz', 'dwell',
                                 'dwelltime', 'feedrate_z', 'grbl_11', 'grbl_laser', 'gridoffsety', 'gridx', 'gridy',
                                 'has_offset', 'holes', 'hpgl', 'iso_type', 'line_xyz', 'margin', 'marlin', 'method',
                                 'milled_dias', 'minoffset', 'multidepth', 'name', 'offset', 'opt_type', 'order',
                                 'outname', 'overlap', 'passes', 'postamble', 'pp', 'ppname_e', 'ppname_g',
                                 'preamble', 'radius', 'ref', 'rest', 'rows', 'shellvar_', 'scale_factor',
                                 'spacing_columns',
                                 'spacing_rows', 'spindlespeed', 'toolchange_xy', 'tooldia', 'use_threads', 'value',
                                 'x', 'x0', 'x1', 'y', 'y0', 'y1', 'z_cut', 'z_move'
                                 ]

        self.tcl_keywords = [
            'after', 'append', 'apply', 'argc', 'argv', 'argv0', 'array', 'attemptckalloc', 'attemptckrealloc',
            'auto_execok', 'auto_import', 'auto_load', 'auto_mkindex', 'auto_path', 'auto_qualify', 'auto_reset',
            'bgerror', 'binary', 'break', 'case', 'catch', 'cd', 'chan', 'ckalloc', 'ckfree', 'ckrealloc', 'clock',
            'close', 'concat', 'continue', 'coroutine', 'dde', 'dict', 'encoding', 'env', 'eof', 'error', 'errorCode',
            'errorInfo', 'eval', 'exec', 'exit', 'expr', 'fblocked', 'fconfigure', 'fcopy', 'file', 'fileevent',
            'filename', 'flush', 'for', 'foreach', 'format', 'gets', 'glob', 'global', 'history', 'http', 'if', 'incr',
            'info', 'interp', 'join', 'lappend', 'lassign', 'lindex', 'linsert', 'list', 'llength', 'load', 'lrange',
            'lrepeat', 'lreplace', 'lreverse', 'lsearch', 'lset', 'lsort', 'mathfunc', 'mathop', 'memory', 'msgcat',
            'my', 'namespace', 'next', 'nextto', 'open', 'package', 'parray', 'pid', 'pkg_mkIndex', 'platform',
            'proc', 'puts', 'pwd', 're_syntax', 'read', 'refchan', 'regexp', 'registry', 'regsub', 'rename', 'return',
            'safe', 'scan', 'seek', 'self', 'set', 'socket', 'source', 'split', 'string', 'subst', 'switch',
            'tailcall', 'Tcl', 'Tcl_Access', 'Tcl_AddErrorInfo', 'Tcl_AddObjErrorInfo', 'Tcl_AlertNotifier',
            'Tcl_Alloc', 'Tcl_AllocHashEntryProc', 'Tcl_AllocStatBuf', 'Tcl_AllowExceptions', 'Tcl_AppendAllObjTypes',
            'Tcl_AppendElement', 'Tcl_AppendExportList', 'Tcl_AppendFormatToObj', 'Tcl_AppendLimitedToObj',
            'Tcl_AppendObjToErrorInfo', 'Tcl_AppendObjToObj', 'Tcl_AppendPrintfToObj', 'Tcl_AppendResult',
            'Tcl_AppendResultVA', 'Tcl_AppendStringsToObj', 'Tcl_AppendStringsToObjVA', 'Tcl_AppendToObj',
            'Tcl_AppendUnicodeToObj', 'Tcl_AppInit', 'Tcl_AppInitProc', 'Tcl_ArgvInfo', 'Tcl_AsyncCreate',
            'Tcl_AsyncDelete', 'Tcl_AsyncInvoke', 'Tcl_AsyncMark', 'Tcl_AsyncProc', 'Tcl_AsyncReady',
            'Tcl_AttemptAlloc', 'Tcl_AttemptRealloc', 'Tcl_AttemptSetObjLength', 'Tcl_BackgroundError',
            'Tcl_BackgroundException', 'Tcl_Backslash', 'Tcl_BadChannelOption', 'Tcl_CallWhenDeleted', 'Tcl_Canceled',
            'Tcl_CancelEval', 'Tcl_CancelIdleCall', 'Tcl_ChannelBlockModeProc', 'Tcl_ChannelBuffered',
            'Tcl_ChannelClose2Proc', 'Tcl_ChannelCloseProc', 'Tcl_ChannelFlushProc', 'Tcl_ChannelGetHandleProc',
            'Tcl_ChannelGetOptionProc', 'Tcl_ChannelHandlerProc', 'Tcl_ChannelInputProc', 'Tcl_ChannelName',
            'Tcl_ChannelOutputProc', 'Tcl_ChannelProc', 'Tcl_ChannelSeekProc', 'Tcl_ChannelSetOptionProc',
            'Tcl_ChannelThreadActionProc', 'Tcl_ChannelTruncateProc', 'Tcl_ChannelType', 'Tcl_ChannelVersion',
            'Tcl_ChannelWatchProc', 'Tcl_ChannelWideSeekProc', 'Tcl_Chdir', 'Tcl_ClassGetMetadata',
            'Tcl_ClassSetConstructor', 'Tcl_ClassSetDestructor', 'Tcl_ClassSetMetadata', 'Tcl_ClearChannelHandlers',
            'Tcl_CloneProc', 'Tcl_Close', 'Tcl_CloseProc', 'Tcl_CmdDeleteProc', 'Tcl_CmdInfo',
            'Tcl_CmdObjTraceDeleteProc', 'Tcl_CmdObjTraceProc', 'Tcl_CmdProc', 'Tcl_CmdTraceProc',
            'Tcl_CommandComplete', 'Tcl_CommandTraceInfo', 'Tcl_CommandTraceProc', 'Tcl_CompareHashKeysProc',
            'Tcl_Concat', 'Tcl_ConcatObj', 'Tcl_ConditionFinalize', 'Tcl_ConditionNotify', 'Tcl_ConditionWait',
            'Tcl_Config', 'Tcl_ConvertCountedElement', 'Tcl_ConvertElement', 'Tcl_ConvertToType',
            'Tcl_CopyObjectInstance', 'Tcl_CreateAlias', 'Tcl_CreateAliasObj', 'Tcl_CreateChannel',
            'Tcl_CreateChannelHandler', 'Tcl_CreateCloseHandler', 'Tcl_CreateCommand', 'Tcl_CreateEncoding',
            'Tcl_CreateEnsemble', 'Tcl_CreateEventSource', 'Tcl_CreateExitHandler', 'Tcl_CreateFileHandler',
            'Tcl_CreateHashEntry', 'Tcl_CreateInterp', 'Tcl_CreateMathFunc', 'Tcl_CreateNamespace',
            'Tcl_CreateObjCommand', 'Tcl_CreateObjTrace', 'Tcl_CreateSlave', 'Tcl_CreateThread',
            'Tcl_CreateThreadExitHandler', 'Tcl_CreateTimerHandler', 'Tcl_CreateTrace',
            'Tcl_CutChannel', 'Tcl_DecrRefCount', 'Tcl_DeleteAssocData', 'Tcl_DeleteChannelHandler',
            'Tcl_DeleteCloseHandler', 'Tcl_DeleteCommand', 'Tcl_DeleteCommandFromToken', 'Tcl_DeleteEvents',
            'Tcl_DeleteEventSource', 'Tcl_DeleteExitHandler', 'Tcl_DeleteFileHandler', 'Tcl_DeleteHashEntry',
            'Tcl_DeleteHashTable', 'Tcl_DeleteInterp', 'Tcl_DeleteNamespace', 'Tcl_DeleteThreadExitHandler',
            'Tcl_DeleteTimerHandler', 'Tcl_DeleteTrace', 'Tcl_DetachChannel', 'Tcl_DetachPids', 'Tcl_DictObjDone',
            'Tcl_DictObjFirst', 'Tcl_DictObjGet', 'Tcl_DictObjNext', 'Tcl_DictObjPut', 'Tcl_DictObjPutKeyList',
            'Tcl_DictObjRemove', 'Tcl_DictObjRemoveKeyList', 'Tcl_DictObjSize', 'Tcl_DiscardInterpState',
            'Tcl_DiscardResult', 'Tcl_DontCallWhenDeleted', 'Tcl_DoOneEvent', 'Tcl_DoWhenIdle',
            'Tcl_DriverBlockModeProc', 'Tcl_DriverClose2Proc', 'Tcl_DriverCloseProc', 'Tcl_DriverFlushProc',
            'Tcl_DriverGetHandleProc', 'Tcl_DriverGetOptionProc', 'Tcl_DriverHandlerProc', 'Tcl_DriverInputProc',
            'Tcl_DriverOutputProc', 'Tcl_DriverSeekProc', 'Tcl_DriverSetOptionProc', 'Tcl_DriverThreadActionProc',
            'Tcl_DriverTruncateProc', 'Tcl_DriverWatchProc', 'Tcl_DriverWideSeekProc', 'Tcl_DStringAppend',
            'Tcl_DStringAppendElement', 'Tcl_DStringEndSublist', 'Tcl_DStringFree', 'Tcl_DStringGetResult',
            'Tcl_DStringInit', 'Tcl_DStringLength', 'Tcl_DStringResult', 'Tcl_DStringSetLength',
            'Tcl_DStringStartSublist', 'Tcl_DStringTrunc', 'Tcl_DStringValue', 'Tcl_DumpActiveMemory',
            'Tcl_DupInternalRepProc', 'Tcl_DuplicateObj', 'Tcl_EncodingConvertProc', 'Tcl_EncodingFreeProc',
            'Tcl_EncodingType', 'tcl_endOfWord', 'Tcl_Eof', 'Tcl_ErrnoId', 'Tcl_ErrnoMsg', 'Tcl_Eval', 'Tcl_EvalEx',
            'Tcl_EvalFile', 'Tcl_EvalObjEx', 'Tcl_EvalObjv', 'Tcl_EvalTokens', 'Tcl_EvalTokensStandard', 'Tcl_Event',
            'Tcl_EventCheckProc', 'Tcl_EventDeleteProc', 'Tcl_EventProc', 'Tcl_EventSetupProc', 'Tcl_EventuallyFree',
            'Tcl_Exit', 'Tcl_ExitProc', 'Tcl_ExitThread', 'Tcl_Export', 'Tcl_ExposeCommand', 'Tcl_ExprBoolean',
            'Tcl_ExprBooleanObj', 'Tcl_ExprDouble', 'Tcl_ExprDoubleObj', 'Tcl_ExprLong', 'Tcl_ExprLongObj',
            'Tcl_ExprObj', 'Tcl_ExprString', 'Tcl_ExternalToUtf', 'Tcl_ExternalToUtfDString', 'Tcl_FileProc',
            'Tcl_Filesystem', 'Tcl_Finalize', 'Tcl_FinalizeNotifier', 'Tcl_FinalizeThread', 'Tcl_FindCommand',
            'Tcl_FindEnsemble', 'Tcl_FindExecutable', 'Tcl_FindHashEntry', 'tcl_findLibrary', 'Tcl_FindNamespace',
            'Tcl_FirstHashEntry', 'Tcl_Flush', 'Tcl_ForgetImport', 'Tcl_Format', 'Tcl_FreeHashEntryProc',
            'Tcl_FreeInternalRepProc', 'Tcl_FreeParse', 'Tcl_FreeProc', 'Tcl_FreeResult',
            'Tcl_Free·\xa0Tcl_FreeEncoding', 'Tcl_FSAccess', 'Tcl_FSAccessProc', 'Tcl_FSChdir',
            'Tcl_FSChdirProc', 'Tcl_FSConvertToPathType', 'Tcl_FSCopyDirectory', 'Tcl_FSCopyDirectoryProc',
            'Tcl_FSCopyFile', 'Tcl_FSCopyFileProc', 'Tcl_FSCreateDirectory', 'Tcl_FSCreateDirectoryProc',
            'Tcl_FSCreateInternalRepProc', 'Tcl_FSData', 'Tcl_FSDeleteFile', 'Tcl_FSDeleteFileProc',
            'Tcl_FSDupInternalRepProc', 'Tcl_FSEqualPaths', 'Tcl_FSEvalFile', 'Tcl_FSEvalFileEx',
            'Tcl_FSFileAttrsGet', 'Tcl_FSFileAttrsGetProc', 'Tcl_FSFileAttrsSet', 'Tcl_FSFileAttrsSetProc',
            'Tcl_FSFileAttrStrings', 'Tcl_FSFileSystemInfo', 'Tcl_FSFilesystemPathTypeProc',
            'Tcl_FSFilesystemSeparatorProc', 'Tcl_FSFreeInternalRepProc', 'Tcl_FSGetCwd', 'Tcl_FSGetCwdProc',
            'Tcl_FSGetFileSystemForPath', 'Tcl_FSGetInternalRep', 'Tcl_FSGetNativePath', 'Tcl_FSGetNormalizedPath',
            'Tcl_FSGetPathType', 'Tcl_FSGetTranslatedPath', 'Tcl_FSGetTranslatedStringPath',
            'Tcl_FSInternalToNormalizedProc', 'Tcl_FSJoinPath', 'Tcl_FSJoinToPath', 'Tcl_FSLinkProc',
            'Tcl_FSLink·\xa0Tcl_FSListVolumes', 'Tcl_FSListVolumesProc', 'Tcl_FSLoadFile', 'Tcl_FSLoadFileProc',
            'Tcl_FSLstat', 'Tcl_FSLstatProc', 'Tcl_FSMatchInDirectory', 'Tcl_FSMatchInDirectoryProc',
            'Tcl_FSMountsChanged', 'Tcl_FSNewNativePath', 'Tcl_FSNormalizePathProc', 'Tcl_FSOpenFileChannel',
            'Tcl_FSOpenFileChannelProc', 'Tcl_FSPathInFilesystemProc', 'Tcl_FSPathSeparator', 'Tcl_FSRegister',
            'Tcl_FSRemoveDirectory', 'Tcl_FSRemoveDirectoryProc', 'Tcl_FSRenameFile', 'Tcl_FSRenameFileProc',
            'Tcl_FSSplitPath', 'Tcl_FSStat', 'Tcl_FSStatProc', 'Tcl_FSUnloadFile', 'Tcl_FSUnloadFileProc',
            'Tcl_FSUnregister', 'Tcl_FSUtime', 'Tcl_FSUtimeProc', 'Tcl_GetAccessTimeFromStat', 'Tcl_GetAlias',
            'Tcl_GetAliasObj', 'Tcl_GetAssocData', 'Tcl_GetBignumFromObj', 'Tcl_GetBlocksFromStat',
            'Tcl_GetBlockSizeFromStat', 'Tcl_GetBoolean', 'Tcl_GetBooleanFromObj', 'Tcl_GetByteArrayFromObj',
            'Tcl_GetChangeTimeFromStat', 'Tcl_GetChannel', 'Tcl_GetChannelBufferSize', 'Tcl_GetChannelError',
            'Tcl_GetChannelErrorInterp', 'Tcl_GetChannelHandle', 'Tcl_GetChannelInstanceData', 'Tcl_GetChannelMode',
            'Tcl_GetChannelName', 'Tcl_GetChannelNames', 'Tcl_GetChannelNamesEx', 'Tcl_GetChannelOption',
            'Tcl_GetChannelThread', 'Tcl_GetChannelType', 'Tcl_GetCharLength', 'Tcl_GetClassAsObject',
            'Tcl_GetCommandFromObj', 'Tcl_GetCommandFullName', 'Tcl_GetCommandInfo', 'Tcl_GetCommandInfoFromToken',
            'Tcl_GetCommandName', 'Tcl_GetCurrentNamespace', 'Tcl_GetCurrentThread', 'Tcl_GetCwd',
            'Tcl_GetDefaultEncodingDir', 'Tcl_GetDeviceTypeFromStat', 'Tcl_GetDouble', 'Tcl_GetDoubleFromObj',
            'Tcl_GetEncoding', 'Tcl_GetEncodingFromObj', 'Tcl_GetEncodingName', 'Tcl_GetEncodingNameFromEnvironment',
            'Tcl_GetEncodingNames', 'Tcl_GetEncodingSearchPath', 'Tcl_GetEnsembleFlags', 'Tcl_GetEnsembleMappingDict',
            'Tcl_GetEnsembleNamespace', 'Tcl_GetEnsembleParameterList', 'Tcl_GetEnsembleSubcommandList',
            'Tcl_GetEnsembleUnknownHandler', 'Tcl_GetErrno', 'Tcl_GetErrorLine', 'Tcl_GetFSDeviceFromStat',
            'Tcl_GetFSInodeFromStat', 'Tcl_GetGlobalNamespace', 'Tcl_GetGroupIdFromStat', 'Tcl_GetHashKey',
            'Tcl_GetHashValue', 'Tcl_GetHostName', 'Tcl_GetIndexFromObj', 'Tcl_GetIndexFromObjStruct', 'Tcl_GetInt',
            'Tcl_GetInterpPath', 'Tcl_GetIntFromObj', 'Tcl_GetLinkCountFromStat', 'Tcl_GetLongFromObj',
            'Tcl_GetMaster', 'Tcl_GetMathFuncInfo', 'Tcl_GetModeFromStat', 'Tcl_GetModificationTimeFromStat',
            'Tcl_GetNameOfExecutable', 'Tcl_GetNamespaceUnknownHandler', 'Tcl_GetObjectAsClass', 'Tcl_GetObjectCommand',
            'Tcl_GetObjectFromObj', 'Tcl_GetObjectName', 'Tcl_GetObjectNamespace', 'Tcl_GetObjResult', 'Tcl_GetObjType',
            'Tcl_GetOpenFile', 'Tcl_GetPathType', 'Tcl_GetRange', 'Tcl_GetRegExpFromObj', 'Tcl_GetReturnOptions',
            'Tcl_Gets', 'Tcl_GetServiceMode', 'Tcl_GetSizeFromStat', 'Tcl_GetSlave', 'Tcl_GetsObj',
            'Tcl_GetStackedChannel', 'Tcl_GetStartupScript', 'Tcl_GetStdChannel', 'Tcl_GetString',
            'Tcl_GetStringFromObj', 'Tcl_GetStringResult', 'Tcl_GetThreadData', 'Tcl_GetTime', 'Tcl_GetTopChannel',
            'Tcl_GetUniChar', 'Tcl_GetUnicode', 'Tcl_GetUnicodeFromObj', 'Tcl_GetUserIdFromStat', 'Tcl_GetVar',
            'Tcl_GetVar2', 'Tcl_GetVar2Ex', 'Tcl_GetVersion', 'Tcl_GetWideIntFromObj', 'Tcl_GlobalEval',
            'Tcl_GlobalEvalObj', 'Tcl_GlobTypeData', 'Tcl_HashKeyType', 'Tcl_HashStats', 'Tcl_HideCommand',
            'Tcl_IdleProc', 'Tcl_Import', 'Tcl_IncrRefCount', 'Tcl_Init', 'Tcl_InitCustomHashTable',
            'Tcl_InitHashTable', 'Tcl_InitMemory', 'Tcl_InitNotifier', 'Tcl_InitObjHashTable', 'Tcl_InitStubs',
            'Tcl_InputBlocked', 'Tcl_InputBuffered', 'tcl_interactive', 'Tcl_Interp', 'Tcl_InterpActive',
            'Tcl_InterpDeleted', 'Tcl_InterpDeleteProc', 'Tcl_InvalidateStringRep', 'Tcl_IsChannelExisting',
            'Tcl_IsChannelRegistered', 'Tcl_IsChannelShared', 'Tcl_IsEnsemble', 'Tcl_IsSafe', 'Tcl_IsShared',
            'Tcl_IsStandardChannel', 'Tcl_JoinPath', 'Tcl_JoinThread', 'tcl_library', 'Tcl_LimitAddHandler',
            'Tcl_LimitCheck', 'Tcl_LimitExceeded', 'Tcl_LimitGetCommands', 'Tcl_LimitGetGranularity',
            'Tcl_LimitGetTime', 'Tcl_LimitHandlerDeleteProc', 'Tcl_LimitHandlerProc', 'Tcl_LimitReady',
            'Tcl_LimitRemoveHandler', 'Tcl_LimitSetCommands', 'Tcl_LimitSetGranularity', 'Tcl_LimitSetTime',
            'Tcl_LimitTypeEnabled', 'Tcl_LimitTypeExceeded', 'Tcl_LimitTypeReset', 'Tcl_LimitTypeSet',
            'Tcl_LinkVar', 'Tcl_ListMathFuncs', 'Tcl_ListObjAppendElement', 'Tcl_ListObjAppendList',
            'Tcl_ListObjGetElements', 'Tcl_ListObjIndex', 'Tcl_ListObjLength', 'Tcl_ListObjReplace',
            'Tcl_LogCommandInfo', 'Tcl_Main', 'Tcl_MainLoopProc', 'Tcl_MakeFileChannel', 'Tcl_MakeSafe',
            'Tcl_MakeTcpClientChannel', 'Tcl_MathProc', 'TCL_MEM_DEBUG', 'Tcl_Merge', 'Tcl_MethodCallProc',
            'Tcl_MethodDeclarerClass', 'Tcl_MethodDeclarerObject', 'Tcl_MethodDeleteProc', 'Tcl_MethodIsPublic',
            'Tcl_MethodIsType', 'Tcl_MethodName', 'Tcl_MethodType', 'Tcl_MutexFinalize', 'Tcl_MutexLock',
            'Tcl_MutexUnlock', 'Tcl_NamespaceDeleteProc', 'Tcl_NewBignumObj', 'Tcl_NewBooleanObj',
            'Tcl_NewByteArrayObj', 'Tcl_NewDictObj', 'Tcl_NewDoubleObj', 'Tcl_NewInstanceMethod', 'Tcl_NewIntObj',
            'Tcl_NewListObj', 'Tcl_NewLongObj', 'Tcl_NewMethod', 'Tcl_NewObj', 'Tcl_NewObjectInstance',
            'Tcl_NewStringObj', 'Tcl_NewUnicodeObj', 'Tcl_NewWideIntObj', 'Tcl_NextHashEntry', 'tcl_nonwordchars',
            'Tcl_NotifierProcs', 'Tcl_NotifyChannel', 'Tcl_NRAddCallback', 'Tcl_NRCallObjProc', 'Tcl_NRCmdSwap',
            'Tcl_NRCreateCommand', 'Tcl_NREvalObj', 'Tcl_NREvalObjv', 'Tcl_NumUtfChars', 'Tcl_Obj', 'Tcl_ObjCmdProc',
            'Tcl_ObjectContextInvokeNext', 'Tcl_ObjectContextIsFiltering', 'Tcl_ObjectContextMethod',
            'Tcl_ObjectContextObject', 'Tcl_ObjectContextSkippedArgs', 'Tcl_ObjectDeleted', 'Tcl_ObjectGetMetadata',
            'Tcl_ObjectGetMethodNameMapper', 'Tcl_ObjectMapMethodNameProc', 'Tcl_ObjectMetadataDeleteProc',
            'Tcl_ObjectSetMetadata', 'Tcl_ObjectSetMethodNameMapper', 'Tcl_ObjGetVar2', 'Tcl_ObjPrintf',
            'Tcl_ObjSetVar2', 'Tcl_ObjType', 'Tcl_OpenCommandChannel', 'Tcl_OpenFileChannel', 'Tcl_OpenTcpClient',
            'Tcl_OpenTcpServer', 'Tcl_OutputBuffered', 'Tcl_PackageInitProc', 'Tcl_PackageUnloadProc', 'Tcl_Panic',
            'Tcl_PanicProc', 'Tcl_PanicVA', 'Tcl_ParseArgsObjv', 'Tcl_ParseBraces', 'Tcl_ParseCommand', 'Tcl_ParseExpr',
            'Tcl_ParseQuotedString', 'Tcl_ParseVar', 'Tcl_ParseVarName', 'tcl_patchLevel', 'tcl_pkgPath',
            'Tcl_PkgPresent', 'Tcl_PkgPresentEx', 'Tcl_PkgProvide', 'Tcl_PkgProvideEx', 'Tcl_PkgRequire',
            'Tcl_PkgRequireEx', 'Tcl_PkgRequireProc', 'tcl_platform', 'Tcl_PosixError', 'tcl_precision',
            'Tcl_Preserve', 'Tcl_PrintDouble', 'Tcl_PutEnv', 'Tcl_QueryTimeProc', 'Tcl_QueueEvent', 'tcl_rcFileName',
            'Tcl_Read', 'Tcl_ReadChars', 'Tcl_ReadRaw', 'Tcl_Realloc', 'Tcl_ReapDetachedProcs', 'Tcl_RecordAndEval',
            'Tcl_RecordAndEvalObj', 'Tcl_RegExpCompile', 'Tcl_RegExpExec', 'Tcl_RegExpExecObj', 'Tcl_RegExpGetInfo',
            'Tcl_RegExpIndices', 'Tcl_RegExpInfo', 'Tcl_RegExpMatch', 'Tcl_RegExpMatchObj', 'Tcl_RegExpRange',
            'Tcl_RegisterChannel', 'Tcl_RegisterConfig', 'Tcl_RegisterObjType', 'Tcl_Release', 'Tcl_ResetResult',
            'Tcl_RestoreInterpState', 'Tcl_RestoreResult', 'Tcl_SaveInterpState', 'Tcl_SaveResult', 'Tcl_ScaleTimeProc',
            'Tcl_ScanCountedElement', 'Tcl_ScanElement', 'Tcl_Seek', 'Tcl_ServiceAll', 'Tcl_ServiceEvent',
            'Tcl_ServiceModeHook', 'Tcl_SetAssocData', 'Tcl_SetBignumObj', 'Tcl_SetBooleanObj',
            'Tcl_SetByteArrayLength', 'Tcl_SetByteArrayObj', 'Tcl_SetChannelBufferSize', 'Tcl_SetChannelError',
            'Tcl_SetChannelErrorInterp', 'Tcl_SetChannelOption', 'Tcl_SetCommandInfo', 'Tcl_SetCommandInfoFromToken',
            'Tcl_SetDefaultEncodingDir', 'Tcl_SetDoubleObj', 'Tcl_SetEncodingSearchPath', 'Tcl_SetEnsembleFlags',
            'Tcl_SetEnsembleMappingDict', 'Tcl_SetEnsembleParameterList', 'Tcl_SetEnsembleSubcommandList',
            'Tcl_SetEnsembleUnknownHandler', 'Tcl_SetErrno', 'Tcl_SetErrorCode', 'Tcl_SetErrorCodeVA',
            'Tcl_SetErrorLine', 'Tcl_SetExitProc', 'Tcl_SetFromAnyProc', 'Tcl_SetHashValue', 'Tcl_SetIntObj',
            'Tcl_SetListObj', 'Tcl_SetLongObj', 'Tcl_SetMainLoop', 'Tcl_SetMaxBlockTime',
            'Tcl_SetNamespaceUnknownHandler', 'Tcl_SetNotifier', 'Tcl_SetObjErrorCode', 'Tcl_SetObjLength',
            'Tcl_SetObjResult', 'Tcl_SetPanicProc', 'Tcl_SetRecursionLimit', 'Tcl_SetResult', 'Tcl_SetReturnOptions',
            'Tcl_SetServiceMode', 'Tcl_SetStartupScript', 'Tcl_SetStdChannel', 'Tcl_SetStringObj',
            'Tcl_SetSystemEncoding', 'Tcl_SetTimeProc', 'Tcl_SetTimer', 'Tcl_SetUnicodeObj', 'Tcl_SetVar',
            'Tcl_SetVar2', 'Tcl_SetVar2Ex', 'Tcl_SetWideIntObj', 'Tcl_SignalId', 'Tcl_SignalMsg', 'Tcl_Sleep',
            'Tcl_SourceRCFile', 'Tcl_SpliceChannel', 'Tcl_SplitList', 'Tcl_SplitPath', 'Tcl_StackChannel',
            'Tcl_StandardChannels', 'tcl_startOfNextWord', 'tcl_startOfPreviousWord', 'Tcl_Stat', 'Tcl_StaticPackage',
            'Tcl_StringCaseMatch', 'Tcl_StringMatch', 'Tcl_SubstObj', 'Tcl_TakeBignumFromObj', 'Tcl_TcpAcceptProc',
            'Tcl_Tell', 'Tcl_ThreadAlert', 'Tcl_ThreadQueueEvent', 'Tcl_Time', 'Tcl_TimerProc', 'Tcl_Token',
            'Tcl_TraceCommand', 'tcl_traceCompile', 'tcl_traceEval', 'Tcl_TraceVar', 'Tcl_TraceVar2',
            'Tcl_TransferResult', 'Tcl_TranslateFileName', 'Tcl_TruncateChannel', 'Tcl_Ungets', 'Tcl_UniChar',
            'Tcl_UniCharAtIndex', 'Tcl_UniCharCaseMatch', 'Tcl_UniCharIsAlnum', 'Tcl_UniCharIsAlpha',
            'Tcl_UniCharIsControl', 'Tcl_UniCharIsDigit', 'Tcl_UniCharIsGraph', 'Tcl_UniCharIsLower',
            'Tcl_UniCharIsPrint', 'Tcl_UniCharIsPunct', 'Tcl_UniCharIsSpace', 'Tcl_UniCharIsUpper',
            'Tcl_UniCharIsWordChar', 'Tcl_UniCharLen', 'Tcl_UniCharNcasecmp', 'Tcl_UniCharNcmp', 'Tcl_UniCharToLower',
            'Tcl_UniCharToTitle', 'Tcl_UniCharToUpper', 'Tcl_UniCharToUtf', 'Tcl_UniCharToUtfDString', 'Tcl_UnlinkVar',
            'Tcl_UnregisterChannel', 'Tcl_UnsetVar', 'Tcl_UnsetVar2', 'Tcl_UnstackChannel', 'Tcl_UntraceCommand',
            'Tcl_UntraceVar', 'Tcl_UntraceVar2', 'Tcl_UpdateLinkedVar', 'Tcl_UpdateStringProc', 'Tcl_UpVar',
            'Tcl_UpVar2', 'Tcl_UtfAtIndex', 'Tcl_UtfBackslash', 'Tcl_UtfCharComplete', 'Tcl_UtfFindFirst',
            'Tcl_UtfFindLast', 'Tcl_UtfNext', 'Tcl_UtfPrev', 'Tcl_UtfToExternal', 'Tcl_UtfToExternalDString',
            'Tcl_UtfToLower', 'Tcl_UtfToTitle', 'Tcl_UtfToUniChar', 'Tcl_UtfToUniCharDString', 'Tcl_UtfToUpper',
            'Tcl_ValidateAllMemory', 'Tcl_Value', 'Tcl_VarEval', 'Tcl_VarEvalVA', 'Tcl_VarTraceInfo',
            'Tcl_VarTraceInfo2', 'Tcl_VarTraceProc', 'tcl_version', 'Tcl_WaitForEvent', 'Tcl_WaitPid',
            'Tcl_WinTCharToUtf', 'Tcl_WinUtfToTChar', 'tcl_wordBreakAfter', 'tcl_wordBreakBefore', 'tcl_wordchars',
            'Tcl_Write', 'Tcl_WriteChars', 'Tcl_WriteObj', 'Tcl_WriteRaw', 'Tcl_WrongNumArgs', 'Tcl_ZlibAdler32',
            'Tcl_ZlibCRC32', 'Tcl_ZlibDeflate', 'Tcl_ZlibInflate', 'Tcl_ZlibStreamChecksum', 'Tcl_ZlibStreamClose',
            'Tcl_ZlibStreamEof', 'Tcl_ZlibStreamGet', 'Tcl_ZlibStreamGetCommandName', 'Tcl_ZlibStreamInit',
            'Tcl_ZlibStreamPut', 'tcltest', 'tell', 'throw', 'time', 'tm', 'trace', 'transchan', 'try', 'unknown',
            'unload', 'unset', 'update', 'uplevel', 'upvar', 'variable', 'vwait', 'while', 'yield', 'yieldto', 'zlib'
        ]

        self.autocomplete_kw_list = self.defaults['util_autocomplete_keywords'].replace(' ', '').split(',')
        self.myKeywords = self.tcl_commands_list + self.autocomplete_kw_list + self.tcl_keywords

        # ####################################################################################
        # ####################### Shell SETUP ################################################
        # ####################################################################################
        # this will hold the TCL instance
        self.tcl = None

        self.init_tcl()

        self.shell = FCShell(self, version=self.version)
        self.shell._edit.set_model_data(self.myKeywords)
        self.shell.setWindowIcon(self.ui.app_icon)
        self.shell.setWindowTitle("FlatCAM Shell")
        self.shell.resize(*self.defaults["global_shell_shape"])
        self.shell.append_output("FlatCAM %s - " % self.version)
        self.shell.append_output(_("Type >help< to get started\n\n"))

        self.ui.shell_dock = QtWidgets.QDockWidget("FlatCAM TCL Shell")
        self.ui.shell_dock.setObjectName('Shell_DockWidget')
        self.ui.shell_dock.setWidget(self.shell)
        self.ui.shell_dock.setAllowedAreas(QtCore.Qt.AllDockWidgetAreas)
        self.ui.shell_dock.setFeatures(QtWidgets.QDockWidget.DockWidgetMovable |
                                       QtWidgets.QDockWidget.DockWidgetFloatable |
                                       QtWidgets.QDockWidget.DockWidgetClosable)
        self.ui.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.ui.shell_dock)

        # show TCL shell at start-up based on the Menu -? Edit -> Preferences setting.
        if self.defaults["global_shell_at_startup"]:
            self.ui.shell_dock.show()
        else:
            self.ui.shell_dock.hide()

        # ##################################################################################
        # ###################### Tools and Plugins #########################################
        # ##################################################################################

        self.dblsidedtool = None
        self.distance_tool = None
        self.distance_min_tool = None
        self.panelize_tool = None
        self.film_tool = None
        self.paste_tool = None
        self.calculator_tool = None
        self.rules_tool = None
        self.sub_tool = None
        self.move_tool = None
        self.cutout_tool = None
        self.ncclear_tool = None
        self.optimal_tool = None
        self.paint_tool = None
        self.transform_tool = None
        self.properties_tool = None
        self.pdf_tool = None
        self.image_tool = None
        self.pcb_wizard_tool = None
        self.cal_exc_tool = None
        self.qrcode_tool = None
        self.copper_thieving_tool = None
        self.fiducial_tool = None

        # always install tools only after the shell is initialized because the self.inform.emit() depends on shell
        self.install_tools()

        # ##################################################################################
        # ########################### SETUP RECENT ITEMS ###################################
        # ##################################################################################
        self.setup_recent_items()

        # ##################################################################################
        # ########################### BookMarks Manager ####################################
        # ##################################################################################

        # install Bookmark Manager and populate bookmarks in the Help -> Bookmarks
        self.install_bookmarks()
        self.book_dialog_tab = BookmarkManager(app=self, storage=self.defaults["global_bookmarks"])

        # ##################################################################################
        # ############################## Tools Database ####################################
        # ##################################################################################

        self.tools_db_tab = None

        # ### System Font Parsing ###
        # self.f_parse = ParseFont(self)
        # self.parse_system_fonts()

        # #####################################################################################
        # ######################## Check for updates ##########################################
        # #####################################################################################

        # Separate thread (Not worker)
        # Check for updates on startup but only if the user consent and the app is not in Beta version
        if (self.beta is False or self.beta is None) and \
                self.ui.general_defaults_form.general_app_group.version_check_cb.get_value() is True:
            App.log.info("Checking for updates in backgroud (this is version %s)." % str(self.version))

            self.thr2 = QtCore.QThread()
            self.worker_task.emit({'fcn': self.version_check,
                                   'params': []})
            self.thr2.start(QtCore.QThread.LowPriority)

        # #####################################################################################
        # ######################### Register files with FlatCAM;  #############################
        # ######################### It works only for Windows for now  ########################
        # #####################################################################################
        if sys.platform == 'win32' and self.defaults["first_run"] is True:
            self.on_register_files()

        # #####################################################################################
        # ###################### Variables for global usage ###################################
        # #####################################################################################

        # hold the App units
        self.units = 'IN'

        # coordinates for relative position display
        self.rel_point1 = (0, 0)
        self.rel_point2 = (0, 0)

        # variable to store coordinates
        self.pos = (0, 0)
        self.pos_jump = (0, 0)

        # variable to store mouse coordinates
        self.mouse = [0, 0]

        # decide if we have a double click or single click
        self.doubleclick = False

        # store here the is_dragging value
        self.event_is_dragging = False

        # variable to store if a command is active (then the var is not None) and which one it is
        self.command_active = None
        # variable to store the status of moving selection action
        # None value means that it's not an selection action
        # True value = a selection from left to right
        # False value = a selection from right to left
        self.selection_type = None

        # List to store the objects that are currently loaded in FlatCAM
        # This list is updated on each object creation or object delete
        self.all_objects_list = list()

        # List to store the objects that are selected
        self.sel_objects_list = list()

        # holds the key modifier if pressed (CTRL, SHIFT or ALT)
        self.key_modifiers = None

        # Variable to hold the status of the axis
        self.toggle_axis = True

        # Variable to hold the status of the grid lines
        self.toggle_grid_lines = True

        # Variable to store the status of the fullscreen event
        self.toggle_fscreen = False

        # Variable to store the status of the code editor
        self.toggle_codeeditor = False

        # Variable to be used for situations when we don't want the LMB click on canvas to auto open the Project Tab
        self.click_noproject = False

        self.cursor = None

        # Variable to store the GCODE that was edited
        self.gcode_edited = ""

        self.text_editor_tab = None

        # reference for the self.ui.code_editor
        self.reference_code_editor = None
        self.script_code = ''

        # if Preferences are changed in the Edit -> Preferences tab the value will be set to True
        self.preferences_changed_flag = False

        # if Tools DB are changed/edited in the Edit -> Tools Database tab the value will be set to True
        self.tools_db_changed_flag = False

        self.grb_list = ['art', 'bot', 'bsm', 'cmp', 'crc', 'crs', 'dim', 'g4', 'gb0', 'gb1', 'gb2', 'gb3', 'gb5',
                         'gb6', 'gb7', 'gb8', 'gb9', 'gbd', 'gbl', 'gbo', 'gbp', 'gbr', 'gbs', 'gdo', 'ger', 'gko',
                         'gml', 'gm1', 'gm2', 'gm3', 'grb', 'gtl', 'gto', 'gtp', 'gts', 'ly15', 'ly2', 'mil', 'pho',
                         'plc', 'pls', 'smb', 'smt', 'sol', 'spb', 'spt', 'ssb', 'sst', 'stc', 'sts', 'top', 'tsm']

        self.exc_list = ['drd', 'drl', 'exc', 'ncd', 'tap', 'txt', 'xln']

        self.gcode_list = ['cnc', 'din', 'dnc', 'ecs', 'eia', 'fan', 'fgc', 'fnc', 'gc', 'gcd', 'gcode', 'h', 'hnc',
                           'i', 'min', 'mpf', 'mpr', 'nc', 'ncc', 'ncg', 'ngc', 'ncp', 'out', 'plt', 'ply', 'rol',
                           'sbp', 'tap', 'xpi']
        self.svg_list = ['svg']
        self.dxf_list = ['dxf']
        self.pdf_list = ['pdf']
        self.prj_list = ['flatprj']
        self.conf_list = ['flatconfig']

        # global variable used by NCC Tool to signal that some polygons could not be cleared, if True
        # flag for polygons not cleared
        self.poly_not_cleared = False

        # VisPy visuals
        self.isHovering = False
        self.notHovering = True

        # Window geometry
        self.x_pos = None
        self.y_pos = None
        self.width = None
        self.height = None

        # when True, the app has to return from any thread
        self.abort_flag = False

        # set the value used in the Windows Title
        self.engine = self.ui.general_defaults_form.general_app_group.ge_radio.get_value()

        # this holds a widget that is installed in the Plot Area when View Source option is used
        self.source_editor_tab = None

        # Storage for shapes, storage that can be used by FlatCAm tools for utility geometry
        # VisPy visuals
        if self.is_legacy is False:
            self.tool_shapes = ShapeCollection(parent=self.plotcanvas.view.scene, layers=1)
        else:
            from flatcamGUI.PlotCanvasLegacy import ShapeCollectionLegacy
            self.tool_shapes = ShapeCollectionLegacy(obj=self, app=self, name="tool")

        # ###############################################################################
        # ############# Save defaults to factory_defaults.FlatConfig file ###############
        # ############# It's done only once after install                 ###############
        # ###############################################################################
        factory_file = open(self.data_path + '/factory_defaults.FlatConfig')
        fac_def_from_file = factory_file.read()
        factory_defaults = json.loads(fac_def_from_file)

        # if the file contain an empty dictionary then save the factory defaults into the file
        if not factory_defaults:
            self.save_factory_defaults(silent_message=False)

            # ONLY AT FIRST STARTUP INIT THE GUI LAYOUT TO 'COMPACT'
            initial_lay = 'compact'
            self.on_layout(lay=initial_lay)

            # Set the combobox in Preferences to the current layout
            idx = self.ui.general_defaults_form.general_gui_set_group.layout_combo.findText(initial_lay)
            self.ui.general_defaults_form.general_gui_set_group.layout_combo.setCurrentIndex(idx)

        factory_file.close()

        # and then make the  factory_defaults.FlatConfig file read_only os it can't be modified after creation.
        filename_factory = self.data_path + '/factory_defaults.FlatConfig'
        os.chmod(filename_factory, S_IREAD | S_IRGRP | S_IROTH)

        # after the first run, this object should be False
        self.defaults["first_run"] = False

        # ###############################################################################
        # ################# ADDING FlatCAM EDITORS section ##############################
        # ###############################################################################

        # watch out for the position of the editors instantiation ... if it is done before a save of the default values
        # at the first launch of the App , the editors will not be functional.
        self.geo_editor = FlatCAMGeoEditor(self, disabled=True)
        self.exc_editor = FlatCAMExcEditor(self)
        self.grb_editor = FlatCAMGrbEditor(self)
        self.log.debug("Finished adding FlatCAM Editor's.")

        self.set_ui_title(name=_("New Project - Not saved"))

        # disable the Excellon path optimizations made with Google OR-Tools if the app is run on a 32bit platform
        current_platform = platform.architecture()[0]
        if current_platform != '64bit':
            self.ui.excellon_defaults_form.excellon_gen_group.excellon_optimization_radio.set_value('T')
            self.ui.excellon_defaults_form.excellon_gen_group.excellon_optimization_radio.setDisabled(True)

        # ###############################################################################
        # ####################### Finished the CONSTRUCTOR ##############################
        # ###############################################################################
        App.log.debug("END of constructor. Releasing control.")

        # #####################################################################################
        # ########################## SHOW GUI #################################################
        # #####################################################################################

        # if the app is not started as headless, show it
        if self.cmd_line_headless != 1:
            if show_splash:
                # finish the splash
                self.splash.finish(self.ui)

            mgui_settings = QSettings("Open Source", "FlatCAM")
            if mgui_settings.contains("maximized_gui"):
                maximized_ui = mgui_settings.value('maximized_gui', type=bool)
                if maximized_ui is True:
                    self.ui.showMaximized()
                else:
                    self.ui.show()
            else:
                self.ui.show()

            if self.defaults["global_systray_icon"]:
                self.trayIcon.show()
        else:
            log.warning("*******************  RUNNING HEADLESS  *******************")

        # #####################################################################################
        # ########################## START-UP ARGUMENTS #######################################
        # #####################################################################################

        # test if the program was started with a script as parameter
        if self.cmd_line_shellvar:
            try:
                cnt = 0
                command_tcl = 0
                for i in self.cmd_line_shellvar.split(','):
                    if i is not None:
                        # noinspection PyBroadException
                        try:
                            command_tcl = eval(i)
                        except Exception:
                            command_tcl = i

                    command_tcl_formatted = 'set shellvar_{nr} "{cmd}"'.format(cmd=str(command_tcl), nr=str(cnt))

                    cnt += 1

                    # if there are Windows paths then replace the path separator with a Unix like one
                    if sys.platform == 'win32':
                        command_tcl_formatted = command_tcl_formatted.replace('\\', '/')
                    self.shell._sysShell.exec_command(command_tcl_formatted, no_echo=True)
            except Exception as ext:
                print("ERROR: ", ext)
                sys.exit(2)

        if self.cmd_line_shellfile:
            try:
                if self.ui.shell_dock.isHidden():
                    self.ui.shell_dock.show()

                with open(self.cmd_line_shellfile, "r") as myfile:
                    if show_splash:
                        self.splash.showMessage('%s: %ssec\n%s' % (
                            _("Canvas initialization started.\n"
                              "Canvas initialization finished in"), '%.2f' % self.used_time,
                            _("Executing Tcl Script ...")),
                                                alignment=Qt.AlignBottom | Qt.AlignLeft,
                                                color=QtGui.QColor("gray"))
                    cmd_line_shellfile_text = myfile.read()
                    self.shell._sysShell.exec_command(cmd_line_shellfile_text)
            except Exception as ext:
                print("ERROR: ", ext)
                sys.exit(2)

        # accept some type file as command line parameter: FlatCAM project, FlatCAM preferences or scripts
        # the path/file_name must be enclosed in quotes if it contain spaces
        if App.args:
            self.args_at_startup.emit(App.args)

    @staticmethod
    def copy_and_overwrite(from_path, to_path):
        """
        From here:
        https://stackoverflow.com/questions/12683834/how-to-copy-directory-recursively-in-python-and-overwrite-all

        :param from_path: source path
        :param to_path: destination path
        :return: None
        """
        if os.path.exists(to_path):
            shutil.rmtree(to_path)
        try:
            shutil.copytree(from_path, to_path)
        except FileNotFoundError:
            from_new_path = os.path.dirname(os.path.realpath(__file__)) + '\\flatcamGUI\\VisPyData\\data'
            shutil.copytree(from_new_path, to_path)

    def on_startup_args(self, args, silent=False):
        """
        This will process any arguments provided to the application at startup. Like trying to launch a file or project.

        :param silent: when True it will not print messages on Tcl Shell and/or status bar
        :param args: a list containing the application args at startup
        :return: None
        """

        if args is not None:
            args_to_process = args
        else:
            args_to_process = App.args

        log.debug("Application was started with arguments: %s. Processing ..." % str(args_to_process))
        for argument in args_to_process:
            if '.FlatPrj'.lower() in argument.lower():
                try:
                    project_name = str(argument)

                    if project_name == "":
                        if silent is False:
                            self.inform.emit(_("Open cancelled."))
                    else:
                        # self.open_project(project_name)
                        run_from_arg = True
                        # self.worker_task.emit({'fcn': self.open_project,
                        #                        'params': [project_name, run_from_arg]})
                        self.open_project(filename=project_name, run_from_arg=run_from_arg)
                except Exception as e:
                    log.debug("Could not open FlatCAM project file as App parameter due: %s" % str(e))

            elif '.FlatConfig'.lower() in argument.lower():
                try:
                    file_name = str(argument)

                    if file_name == "":
                        if silent is False:
                            self.inform.emit(_("Open Config file failed."))
                    else:
                        run_from_arg = True
                        # self.worker_task.emit({'fcn': self.open_config_file,
                        #                        'params': [file_name, run_from_arg]})
                        self.open_config_file(file_name, run_from_arg=run_from_arg)
                except Exception as e:
                    log.debug("Could not open FlatCAM Config file as App parameter due: %s" % str(e))

            elif '.FlatScript'.lower() in argument.lower() or '.TCL'.lower() in argument.lower():
                try:
                    file_name = str(argument)

                    if file_name == "":
                        if silent is False:
                            self.inform.emit(_("Open Script file failed."))
                    else:
                        if silent is False:
                            self.on_fileopenscript(name=file_name)
                            self.ui.plot_tab_area.setCurrentWidget(self.ui.plot_tab)
                        self.on_filerunscript(name=file_name)
                except Exception as e:
                    log.debug("Could not open FlatCAM Script file as App parameter due: %s" % str(e))

            elif 'quit'.lower() in argument.lower() or 'exit'.lower() in argument.lower():
                log.debug("App.on_startup_args() --> Quit event.")
                sys.exit()

            elif 'save'.lower() in argument.lower():
                log.debug("App.on_startup_args() --> Save event. App Defaults saved.")
                self.save_defaults()
            else:
                exc_list = self.ui.util_defaults_form.fa_excellon_group.exc_list_text.get_value().split(',')
                proc_arg = argument.lower()
                for ext in exc_list:
                    proc_ext = ext.replace(' ', '')
                    proc_ext = '.%s' % proc_ext
                    if proc_ext.lower() in proc_arg and proc_ext != '.':
                        file_name = str(argument)
                        if file_name == "":
                            if silent is False:
                                self.inform.emit(_("Open Excellon file failed."))
                        else:
                            self.on_fileopenexcellon(name=file_name)
                            return

                gco_list = self.ui.util_defaults_form.fa_gcode_group.gco_list_text.get_value().split(',')
                for ext in gco_list:
                    proc_ext = ext.replace(' ', '')
                    proc_ext = '.%s' % proc_ext
                    if proc_ext.lower() in proc_arg and proc_ext != '.':
                        file_name = str(argument)
                        if file_name == "":
                            if silent is False:
                                self.inform.emit(_("Open GCode file failed."))
                        else:
                            self.on_fileopengcode(name=file_name)
                            return

                grb_list = self.ui.util_defaults_form.fa_gerber_group.grb_list_text.get_value().split(',')
                for ext in grb_list:
                    proc_ext = ext.replace(' ', '')
                    proc_ext = '.%s' % proc_ext
                    if proc_ext.lower() in proc_arg and proc_ext != '.':
                        file_name = str(argument)
                        if file_name == "":
                            if silent is False:
                                self.inform.emit(_("Open Gerber file failed."))
                        else:
                            self.on_fileopengerber(name=file_name)
                            return

        # if it reached here without already returning then the app was registered with a file that it does not
        # recognize therefore we must quit but take into consideration the app reboot from within, in that case
        # the args_to_process will contain the path to the FlatCAM.exe (cx_freezed executable)

        # for arg in args_to_process:
        #     if 'FlatCAM.exe' in arg:
        #         continue
        #     else:
        #         sys.exit(2)

    def set_ui_title(self, name):
        """
        Sets the title of the main window.

        :param name: String that store the project path and project name
        :return: None
        """
        self.ui.setWindowTitle('FlatCAM %s %s - %s - [%s]    %s' %
                               (self.version,
                                ('BETA' if self.beta else ''),
                                platform.architecture()[0],
                                self.engine,
                                name)
                               )

    def on_theme_change(self, val):
        t_settings = QSettings("Open Source", "FlatCAM")
        t_settings.setValue('theme', val)

        # This will write the setting to the platform specific storage.
        del t_settings

        self.on_app_restart()

    def on_app_restart(self):

        # make sure that the Sys Tray icon is hidden before restart otherwise it will
        # be left in the SySTray
        try:
            self.trayIcon.hide()
        except Exception:
            pass

        fcTranslate.restart_program(app=self)

    def defaults_read_form(self):
        """
        Will read all the values in the Preferences GUI and update the defaults dictionary.

        :return: None
        """
        for option in self.defaults_form_fields:
            try:
                self.defaults[option] = self.defaults_form_fields[option].get_value()
            except Exception as e:
                log.debug("App.defaults_read_form() --> %s" % str(e))

    def defaults_write_form(self, factor=None, fl_units=None):
        """
        Will set the values for all the GUI elements in Preferences GUI based on the values found in the
        self.defaults dictionary.

        :param factor: will apply a factor to the values that written in the GUI elements
        :param fl_units: current measuring units in FlatCAM: Metric or Inch
        :return: None
        """
        for option in self.defaults:
            self.defaults_write_form_field(option, factor=factor, units=fl_units)
            # try:
            #     self.defaults_form_fields[option].set_value(self.defaults[option])
            # except KeyError:
            #     #self.log.debug("defaults_write_form(): No field for: %s" % option)
            #     # TODO: Rethink this?
            #     pass

    def defaults_write_form_field(self, field, factor=None, units=None):
        """
        Basically it is the worker in the self.defaults_write_form()

        :param field: the GUI element in Preferences GUI to be updated
        :param factor: factor to be applied to the field parameter
        :param units: current FLatCAM measuring units
        :return: None, it updates GUI elements
        """
        try:
            if factor is None:
                if units is None:
                    self.defaults_form_fields[field].set_value(self.defaults[field])
                elif units == 'IN' and (field == 'global_gridx' or field == 'global_gridy'):
                    self.defaults_form_fields[field].set_value(self.defaults[field])
                elif units == 'MM' and (field == 'global_gridx' or field == 'global_gridy'):
                    self.defaults_form_fields[field].set_value(self.defaults[field])
            else:
                if units is None:
                    self.defaults_form_fields[field].set_value(self.defaults[field] * factor)
                elif units == 'IN' and (field == 'global_gridx' or field == 'global_gridy'):
                    self.defaults_form_fields[field].set_value((self.defaults[field] * factor))
                elif units == 'MM' and (field == 'global_gridx' or field == 'global_gridy'):
                    self.defaults_form_fields[field].set_value((self.defaults[field] * factor))
        except KeyError:
            # self.log.debug("defaults_write_form(): No field for: %s" % option)
            # TODO: Rethink this?
            pass
        except AttributeError:
            log.debug(field)

    def clear_pool(self):
        """
        Clear the multiprocessing pool and calls garbage collector.

        :return: None
        """
        self.pool.close()

        self.pool = Pool()
        self.pool_recreated.emit(self.pool)

        gc.collect()

    def install_tools(self):
        """
        This installs the FlatCAM tools (plugin-like) which reside in their own classes.
        Instantiation of the Tools classes.
        The order that the tools are installed is important as they can depend on each other install position.

        :return: None
        """
        self.dblsidedtool = DblSidedTool(self)
        self.dblsidedtool.install(icon=QtGui.QIcon('share/doubleside16.png'), separator=True)

        self.cal_exc_tool = ToolCalibrateExcellon(self)
        self.cal_exc_tool.install(icon=QtGui.QIcon('share/drill16.png'), pos=self.ui.menutool,
                                  before=self.dblsidedtool.menuAction,
                                  separator=False)
        self.distance_tool = Distance(self)
        self.distance_tool.install(icon=QtGui.QIcon('share/distance16.png'), pos=self.ui.menuedit,
                                   before=self.ui.menueditorigin,
                                   separator=False)

        self.distance_min_tool = DistanceMin(self)
        self.distance_min_tool.install(icon=QtGui.QIcon('share/distance_min16.png'), pos=self.ui.menuedit,
                                       before=self.ui.menueditorigin,
                                       separator=True)

        self.panelize_tool = Panelize(self)
        self.panelize_tool.install(icon=QtGui.QIcon('share/panelize16.png'))

        self.film_tool = Film(self)
        self.film_tool.install(icon=QtGui.QIcon('share/film16.png'))

        self.paste_tool = SolderPaste(self)
        self.paste_tool.install(icon=QtGui.QIcon('share/solderpastebis32.png'))

        self.calculator_tool = ToolCalculator(self)
        self.calculator_tool.install(icon=QtGui.QIcon('share/calculator16.png'), separator=True)

        self.sub_tool = ToolSub(self)
        self.sub_tool.install(icon=QtGui.QIcon('share/sub32.png'), pos=self.ui.menutool, separator=True)

        self.rules_tool = RulesCheck(self)
        self.rules_tool.install(icon=QtGui.QIcon('share/rules32.png'), pos=self.ui.menutool, separator=False)

        self.optimal_tool = ToolOptimal(self)
        self.optimal_tool.install(icon=QtGui.QIcon('share/open_excellon32.png'), pos=self.ui.menutool, separator=True)

        self.move_tool = ToolMove(self)
        self.move_tool.install(icon=QtGui.QIcon('share/move16.png'), pos=self.ui.menuedit,
                               before=self.ui.menueditorigin, separator=True)

        self.cutout_tool = CutOut(self)
        self.cutout_tool.install(icon=QtGui.QIcon('share/cut16_bis.png'), pos=self.ui.menutool,
                                 before=self.sub_tool.menuAction)

        self.ncclear_tool = NonCopperClear(self)
        self.ncclear_tool.install(icon=QtGui.QIcon('share/ncc16.png'), pos=self.ui.menutool,
                                  before=self.sub_tool.menuAction, separator=True)

        self.paint_tool = ToolPaint(self)
        self.paint_tool.install(icon=QtGui.QIcon('share/paint16.png'), pos=self.ui.menutool,
                                before=self.sub_tool.menuAction, separator=True)

        self.copper_thieving_tool = ToolCopperThieving(self)
        self.copper_thieving_tool.install(icon=QtGui.QIcon('share/copperfill32.png'), pos=self.ui.menutool)

        self.fiducial_tool = ToolFiducials(self)
        self.fiducial_tool.install(icon=QtGui.QIcon('share/fiducials_32.png'), pos=self.ui.menutool)

        self.qrcode_tool = QRCode(self)
        self.qrcode_tool.install(icon=QtGui.QIcon('share/qrcode32.png'), pos=self.ui.menutool)

        self.transform_tool = ToolTransform(self)
        self.transform_tool.install(icon=QtGui.QIcon('share/transform.png'), pos=self.ui.menuoptions, separator=True)

        self.properties_tool = Properties(self)
        self.properties_tool.install(icon=QtGui.QIcon('share/properties32.png'), pos=self.ui.menuoptions)

        self.pdf_tool = ToolPDF(self)
        self.pdf_tool.install(icon=QtGui.QIcon('share/pdf32.png'), pos=self.ui.menufileimport,
                              separator=True)

        self.image_tool = ToolImage(self)
        self.image_tool.install(icon=QtGui.QIcon('share/image32.png'), pos=self.ui.menufileimport,
                                separator=True)

        self.pcb_wizard_tool = PcbWizard(self)
        self.pcb_wizard_tool.install(icon=QtGui.QIcon('share/drill32.png'), pos=self.ui.menufileimport)

        self.log.debug("Tools are installed.")

    def remove_tools(self):
        """
        Will remove all the actions in the Tool menu.
        :return: None
        """
        for act in self.ui.menutool.actions():
            self.ui.menutool.removeAction(act)

    def init_tools(self):
        """
        Initialize the Tool tab in the notebook side of the central widget.
        Remove the actions in the Tools menu.
        Instantiate again the FlatCAM tools (plugins).
        All this is required when changing the layout: standard, compact etc.

        :return: None
        """

        log.debug("init_tools()")

        # delete the data currently in the Tools Tab and the Tab itself
        widget = QtWidgets.QTabWidget.widget(self.ui.notebook, 2)
        if widget is not None:
            widget.deleteLater()
        self.ui.notebook.removeTab(2)

        # rebuild the Tools Tab
        self.ui.tool_tab = QtWidgets.QWidget()
        self.ui.tool_tab_layout = QtWidgets.QVBoxLayout(self.ui.tool_tab)
        self.ui.tool_tab_layout.setContentsMargins(2, 2, 2, 2)
        self.ui.notebook.addTab(self.ui.tool_tab, "Tool")
        self.ui.tool_scroll_area = VerticalScrollArea()
        self.ui.tool_tab_layout.addWidget(self.ui.tool_scroll_area)

        # reinstall all the Tools as some may have been removed when the data was removed from the Tools Tab
        # first remove all of them
        self.remove_tools()

        # re-add the TCL Shell action to the Tools menu and reconnect it to ist slot function
        self.ui.menutoolshell = self.ui.menutool.addAction(QtGui.QIcon('share/shell16.png'), '&Command Line\tS')
        self.ui.menutoolshell.triggered.connect(self.on_toggle_shell)

        # third install all of them
        self.install_tools()
        self.log.debug("Tools are initialized.")

    # def parse_system_fonts(self):
    #     self.worker_task.emit({'fcn': self.f_parse.get_fonts_by_types,
    #                            'params': []})

    def connect_toolbar_signals(self):
        """
        Reconnect the signals to the actions in the toolbar.
        This has to be done each time after the FlatCAM tools are removed/installed.

        :return: None
        """

        # Toolbar
        # self.ui.file_new_btn.triggered.connect(self.on_file_new)
        self.ui.file_open_btn.triggered.connect(self.on_file_openproject)
        self.ui.file_save_btn.triggered.connect(self.on_file_saveproject)
        self.ui.file_open_gerber_btn.triggered.connect(self.on_fileopengerber)
        self.ui.file_open_excellon_btn.triggered.connect(self.on_fileopenexcellon)

        self.ui.clear_plot_btn.triggered.connect(self.clear_plots)
        self.ui.replot_btn.triggered.connect(self.plot_all)
        self.ui.zoom_fit_btn.triggered.connect(self.on_zoom_fit)
        self.ui.zoom_in_btn.triggered.connect(lambda: self.plotcanvas.zoom(1 / 1.5))
        self.ui.zoom_out_btn.triggered.connect(lambda: self.plotcanvas.zoom(1.5))

        self.ui.newgeo_btn.triggered.connect(self.new_geometry_object)
        self.ui.newgrb_btn.triggered.connect(self.new_gerber_object)
        self.ui.newexc_btn.triggered.connect(self.new_excellon_object)
        self.ui.editgeo_btn.triggered.connect(self.object2editor)
        self.ui.update_obj_btn.triggered.connect(lambda: self.editor2object())
        self.ui.copy_btn.triggered.connect(self.on_copy_object)
        self.ui.delete_btn.triggered.connect(self.on_delete)

        self.ui.distance_btn.triggered.connect(lambda: self.distance_tool.run(toggle=True))
        self.ui.distance_min_btn.triggered.connect(lambda: self.distance_min_tool.run(toggle=True))
        self.ui.origin_btn.triggered.connect(self.on_set_origin)
        self.ui.jmp_btn.triggered.connect(self.on_jump_to)

        self.ui.shell_btn.triggered.connect(self.on_toggle_shell)
        self.ui.new_script_btn.triggered.connect(self.on_filenewscript)
        self.ui.open_script_btn.triggered.connect(self.on_fileopenscript)
        self.ui.run_script_btn.triggered.connect(self.on_filerunscript)

        # Tools Toolbar Signals
        self.ui.dblsided_btn.triggered.connect(lambda: self.dblsidedtool.run(toggle=True))
        self.ui.cutout_btn.triggered.connect(lambda: self.cutout_tool.run(toggle=True))
        self.ui.ncc_btn.triggered.connect(lambda: self.ncclear_tool.run(toggle=True))
        self.ui.paint_btn.triggered.connect(lambda: self.paint_tool.run(toggle=True))

        self.ui.panelize_btn.triggered.connect(lambda: self.panelize_tool.run(toggle=True))
        self.ui.film_btn.triggered.connect(lambda: self.film_tool.run(toggle=True))
        self.ui.solder_btn.triggered.connect(lambda: self.paste_tool.run(toggle=True))
        self.ui.sub_btn.triggered.connect(lambda: self.sub_tool.run(toggle=True))
        self.ui.rules_btn.triggered.connect(lambda: self.rules_tool.run(toggle=True))
        self.ui.optimal_btn.triggered.connect(lambda: self.optimal_tool.run(toggle=True))

        self.ui.calculators_btn.triggered.connect(lambda: self.calculator_tool.run(toggle=True))
        self.ui.transform_btn.triggered.connect(lambda: self.transform_tool.run(toggle=True))
        self.ui.qrcode_btn.triggered.connect(lambda: self.qrcode_tool.run(toggle=True))
        self.ui.copperfill_btn.triggered.connect(lambda: self.copper_thieving_tool.run(toggle=True))
        self.ui.fiducials_btn.triggered.connect(lambda: self.fiducial_tool.run(toggle=True))

    def object2editor(self):
        """
        Send the current Geometry or Excellon object (if any) into the it's editor.

        :return: None
        """
        self.report_usage("object2editor()")

        # disable the objects menu as it may interfere with the Editors
        self.ui.menuobjects.setDisabled(True)

        edited_object = self.collection.get_active()

        if isinstance(edited_object, FlatCAMGerber) or isinstance(edited_object, FlatCAMGeometry) or \
                isinstance(edited_object, FlatCAMExcellon):
            pass
        else:
            self.inform.emit('[WARNING_NOTCL] %s' %
                             _("Select a Geometry, Gerber or Excellon Object to edit."))
            return

        if isinstance(edited_object, FlatCAMGeometry):
            # store the Geometry Editor Toolbar visibility before entering in the Editor
            self.geo_editor.toolbar_old_state = True if self.ui.geo_edit_toolbar.isVisible() else False

            # we set the notebook to hidden
            self.ui.splitter.setSizes([0, 1])

            if edited_object.multigeo is True:
                sel_rows = [item.row() for item in edited_object.ui.geo_tools_table.selectedItems()]

                if len(sel_rows) > 1:
                    self.inform.emit('[WARNING_NOTCL] %s' %
                                     _("Simultaneous editing of tools geometry in a MultiGeo Geometry "
                                       "is not possible.\n"
                                       "Edit only one geometry at a time."))

                # determine the tool dia of the selected tool
                selected_tooldia = float(edited_object.ui.geo_tools_table.item(sel_rows[0], 1).text())

                # now find the key in the edited_object.tools that has this tooldia
                multi_tool = 1
                for tool in edited_object.tools:
                    if edited_object.tools[tool]['tooldia'] == selected_tooldia:
                        multi_tool = tool
                        break

                self.geo_editor.edit_fcgeometry(edited_object, multigeo_tool=multi_tool)
            else:
                self.geo_editor.edit_fcgeometry(edited_object)

            # set call source to the Editor we go into
            self.call_source = 'geo_editor'

        elif isinstance(edited_object, FlatCAMExcellon):
            # store the Excellon Editor Toolbar visibility before entering in the Editor
            self.exc_editor.toolbar_old_state = True if self.ui.exc_edit_toolbar.isVisible() else False

            if self.ui.splitter.sizes()[0] == 0:
                self.ui.splitter.setSizes([1, 1])

            self.exc_editor.edit_fcexcellon(edited_object)

            # set call source to the Editor we go into
            self.call_source = 'exc_editor'

        elif isinstance(edited_object, FlatCAMGerber):
            # store the Gerber Editor Toolbar visibility before entering in the Editor
            self.grb_editor.toolbar_old_state = True if self.ui.grb_edit_toolbar.isVisible() else False

            if self.ui.splitter.sizes()[0] == 0:
                self.ui.splitter.setSizes([1, 1])

            self.grb_editor.edit_fcgerber(edited_object)

            # set call source to the Editor we go into
            self.call_source = 'grb_editor'

        # make sure that we can't select another object while in Editor Mode:
        # self.collection.view.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.ui.project_frame.setDisabled(True)

        # delete any selection shape that might be active as they are not relevant in Editor
        self.delete_selection_shape()

        self.ui.plot_tab_area.setTabText(0, "EDITOR Area")
        self.ui.plot_tab_area.protectTab(0)
        self.inform.emit('[WARNING_NOTCL] %s' %
                         _("Editor is activated ..."))

        self.should_we_save = True

    def editor2object(self, cleanup=None):
        """
        Transfers the Geometry or Excellon from it's editor to the current object.

        :return: None
        """
        self.report_usage("editor2object()")

        # re-enable the objects menu that was disabled on entry in Editor mode
        self.ui.menuobjects.setDisabled(False)

        # do not update a geometry or excellon object unless it comes out of an editor
        if self.call_source != 'app':
            edited_obj = self.collection.get_active()

            if cleanup is None:
                msgbox = QtWidgets.QMessageBox()
                msgbox.setText(_("Do you want to save the edited object?"))
                msgbox.setWindowTitle(_("Close Editor"))
                msgbox.setWindowIcon(QtGui.QIcon('share/save_as.png'))

                bt_yes = msgbox.addButton(_('Yes'), QtWidgets.QMessageBox.YesRole)
                bt_no = msgbox.addButton(_('No'), QtWidgets.QMessageBox.NoRole)
                bt_cancel = msgbox.addButton(_('Cancel'), QtWidgets.QMessageBox.RejectRole)

                msgbox.setDefaultButton(bt_yes)
                msgbox.exec_()
                response = msgbox.clickedButton()

                if response == bt_yes:
                    # clean the Tools Tab
                    self.ui.tool_scroll_area.takeWidget()
                    self.ui.tool_scroll_area.setWidget(QtWidgets.QWidget())
                    self.ui.notebook.setTabText(2, "Tool")

                    if isinstance(edited_obj, FlatCAMGeometry):
                        obj_type = "Geometry"
                        if cleanup is None:
                            self.geo_editor.update_fcgeometry(edited_obj)
                            self.geo_editor.update_options(edited_obj)
                        self.geo_editor.deactivate()

                        # update the geo object options so it is including the bounding box values
                        try:
                            xmin, ymin, xmax, ymax = edited_obj.bounds()
                            edited_obj.options['xmin'] = xmin
                            edited_obj.options['ymin'] = ymin
                            edited_obj.options['xmax'] = xmax
                            edited_obj.options['ymax'] = ymax
                        except AttributeError as e:
                            self.inform.emit('[WARNING] %s' %
                                             _("Object empty after edit."))
                            log.debug("App.editor2object() --> Geometry --> %s" % str(e))
                    elif isinstance(edited_obj, FlatCAMGerber):
                        obj_type = "Gerber"
                        if cleanup is None:
                            self.grb_editor.update_fcgerber()
                            self.grb_editor.update_options(edited_obj)
                        self.grb_editor.deactivate_grb_editor()

                        # delete the old object (the source object) if it was an empty one
                        try:
                            if len(edited_obj.solid_geometry) == 0:
                                old_name = edited_obj.options['name']
                                self.collection.set_active(old_name)
                                self.collection.delete_active()
                        except TypeError:
                            # if the solid_geometry is a single Polygon the len() will not work
                            # in any case, falling here means that we have something in the solid_geometry, even if only
                            # a single Polygon, therefore we pass this
                            pass

                        # restore GUI to the Selected TAB
                        # Remove anything else in the GUI
                        self.ui.selected_scroll_area.takeWidget()
                        # Switch notebook to Selected page
                        self.ui.notebook.setCurrentWidget(self.ui.selected_tab)

                    elif isinstance(edited_obj, FlatCAMExcellon):
                        obj_type = "Excellon"
                        if cleanup is None:
                            self.exc_editor.update_fcexcellon(edited_obj)
                            self.exc_editor.update_options(edited_obj)

                        self.exc_editor.deactivate()

                        # delete the old object (the source object) if it was an empty one
                        if len(edited_obj.drills) == 0 and len(edited_obj.slots) == 0:
                            old_name = edited_obj.options['name']
                            self.collection.set_active(old_name)
                            self.collection.delete_active()

                        # restore GUI to the Selected TAB
                        # Remove anything else in the GUI
                        self.ui.tool_scroll_area.takeWidget()
                        # Switch notebook to Selected page
                        self.ui.notebook.setCurrentWidget(self.ui.selected_tab)

                    else:
                        self.inform.emit('[WARNING_NOTCL] %s' %
                                         _("Select a Gerber, Geometry or Excellon Object to update."))
                        return

                    self.inform.emit('[selected] %s %s' %
                                     (obj_type, _("is updated, returning to App...")))
                elif response == bt_no:
                    # clean the Tools Tab
                    self.ui.tool_scroll_area.takeWidget()
                    self.ui.tool_scroll_area.setWidget(QtWidgets.QWidget())
                    self.ui.notebook.setTabText(2, "Tool")

                    if isinstance(edited_obj, FlatCAMGeometry):
                        self.geo_editor.deactivate()
                    elif isinstance(edited_obj, FlatCAMGerber):
                        self.grb_editor.deactivate_grb_editor()
                    elif isinstance(edited_obj, FlatCAMExcellon):
                        self.exc_editor.deactivate()
                        # set focus on the project tab
                    else:
                        self.inform.emit('[WARNING_NOTCL] %s' %
                                         _("Select a Gerber, Geometry or Excellon Object to update."))
                        return
                    edited_obj.set_ui(edited_obj.ui_type())
                    self.ui.notebook.setCurrentWidget(self.ui.selected_tab)
                elif response == bt_cancel:
                    return
            else:
                if isinstance(edited_obj, FlatCAMGeometry):
                    self.geo_editor.deactivate()
                elif isinstance(edited_obj, FlatCAMGerber):
                    self.grb_editor.deactivate_grb_editor()
                elif isinstance(edited_obj, FlatCAMExcellon):
                    self.exc_editor.deactivate()
                else:
                    self.inform.emit('[WARNING_NOTCL] %s' %
                                     _("Select a Gerber, Geometry or Excellon Object to update."))
                    return

            # if notebook is hidden we show it
            if self.ui.splitter.sizes()[0] == 0:
                self.ui.splitter.setSizes([1, 1])

            # restore the call_source to app
            self.call_source = 'app'

            edited_obj.plot()
            self.ui.plot_tab_area.setTabText(0, "Plot Area")
            self.ui.plot_tab_area.protectTab(0)

            # make sure that we reenable the selection on Project Tab after returning from Editor Mode:
            # self.collection.view.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
            self.ui.project_frame.setDisabled(False)

    def get_last_folder(self):
        """
        Get the folder path from where the last file was opened.
        :return: String, last opened folder path
        """
        return self.defaults["global_last_folder"]

    def get_last_save_folder(self):
        """
        Get the folder path from where the last file was saved.
        :return: String, last saved folder path
        """
        loc = self.defaults["global_last_save_folder"]
        if loc is None:
            loc = self.defaults["global_last_folder"]
        if loc is None:
            loc = os.path.dirname(__file__)
        return loc

    def report_usage(self, resource):
        """
        Increments usage counter for the given resource
        in self.defaults['global_stats'].

        :param resource: Name of the resource.
        :return: None
        """

        if resource in self.defaults['global_stats']:
            self.defaults['global_stats'][resource] += 1
        else:
            self.defaults['global_stats'][resource] = 1

    def init_tcl(self):
        """
        Initialize the TCL Shell. A dock widget that holds the GUI interface to the FlatCAM command line.
        :return: None
        """
        if hasattr(self, 'tcl') and self.tcl is not None:
            # self.tcl = None
            # TODO  we need  to clean  non default variables and procedures here
            # new object cannot be used here as it  will not remember values created for next passes,
            # because tcl  was execudted in old instance of TCL
            pass
        else:
            self.tcl = tk.Tcl()
            self.setup_shell()
        self.log.debug("TCL Shell has been initialized.")

    # TODO: This shouldn't be here.
    class TclErrorException(Exception):
        """
        this exception is defined here, to be able catch it if we successfully handle all errors from shell command
        """
        pass

    def shell_message(self, msg, show=False, error=False, warning=False, success=False, selected=False):
        """
        Shows a message on the FlatCAM Shell

        :param msg: Message to display.
        :param show: Opens the shell.
        :param error: Shows the message as an error.
        :param warning: Shows the message as an warning.
        :param success: Shows the message as an success.
        :param selected: Indicate that something was selected on canvas
        :return: None
        """
        if show:
            self.ui.shell_dock.show()
        try:
            if error:
                self.shell.append_error(msg + "\n")
            elif warning:
                self.shell.append_warning(msg + "\n")
            elif success:
                self.shell.append_success(msg + "\n")
            elif selected:
                self.shell.append_selected(msg + "\n")
            else:
                self.shell.append_output(msg + "\n")
        except AttributeError:
            log.debug("shell_message() is called before Shell Class is instantiated. The message is: %s", str(msg))

    def raise_tcl_unknown_error(self, unknownException):
        """
        Raise exception if is different type than TclErrorException
        this is here mainly to show unknown errors inside TCL shell console.

        :param unknownException:
        :return:
        """

        if not isinstance(unknownException, self.TclErrorException):
            self.raise_tcl_error("Unknown error: %s" % str(unknownException))
        else:
            raise unknownException

    def display_tcl_error(self, error, error_info=None):
        """
        Escape bracket [ with '\' otherwise there is error
        "ERROR: missing close-bracket" instead of real error

        :param error: it may be text  or exception
        :param error_info: Some informations about the error
        :return: None
        """

        if isinstance(error, Exception):
            exc_type, exc_value, exc_traceback = error_info
            if not isinstance(error, self.TclErrorException):
                show_trace = 1
            else:
                show_trace = int(self.defaults['global_verbose_error_level'])

            if show_trace > 0:
                trc = traceback.format_list(traceback.extract_tb(exc_traceback))
                trc_formated = []
                for a in reversed(trc):
                    trc_formated.append(a.replace("    ", " > ").replace("\n", ""))
                text = "%s\nPython traceback: %s\n%s" % (exc_value, exc_type, "\n".join(trc_formated))
            else:
                text = "%s" % error
        else:
            text = error

        text = text.replace('[', '\\[').replace('"', '\\"')
        self.tcl.eval('return -code error "%s"' % text)

    def raise_tcl_error(self, text):
        """
        This method  pass exception from python into TCL as error, so we get stacktrace and reason

        :param text: text of error
        :return: raise exception
        """

        self.display_tcl_error(text)
        raise self.TclErrorException(text)

    def exec_command(self, text, no_echo=False):
        """
        Handles input from the shell. See FlatCAMApp.setup_shell for shell commands.
        Also handles execution in separated threads

        :param text: FlatCAM TclCommand with parameters
        :param no_echo: If True it will not try to print to the Shell because most likely the shell is hidden and it
        will create crashes of the _Expandable_Edit widget
        :return: output if there was any
        """

        self.report_usage('exec_command')

        result = self.exec_command_test(text, False, no_echo=no_echo)

        # MS: added this method call so the geometry is updated once the TCL command is executed
        # if no_plot is None:
        #     self.plot_all()

        return result

    def exec_command_test(self, text, reraise=True, no_echo=False):
        """
        Same as exec_command(...) with additional control over  exceptions.
        Handles input from the shell. See FlatCAMApp.setup_shell for shell commands.

        :param text: Input command
        :param reraise: Re-raise TclError exceptions in Python (mostly for unitttests).
        :param no_echo: If True it will not try to print to the Shell because most likely the shell is hidden and it
        will create crashes of the _Expandable_Edit widget
        :return: Output from the command
        """

        tcl_command_string = str(text)

        try:
            if no_echo is False:
                self.shell.open_proccessing()  # Disables input box.

            result = self.tcl.eval(str(tcl_command_string))
            if result != 'None' and no_echo is False:
                self.shell.append_output(result + '\n')

        except tk.TclError as e:
            # This will display more precise answer if something in TCL shell fails
            result = self.tcl.eval("set errorInfo")
            self.log.error("Exec command Exception: %s" % (result + '\n'))
            if no_echo is False:
                self.shell.append_error('ERROR: ' + result + '\n')
            # Show error in console and just return or in test raise exception
            if reraise:
                raise e
        finally:
            if no_echo is False:
                self.shell.close_proccessing()
            pass
        return result

        # """
        # Code below is unsused. Saved for later.
        # """

        # parts = re.findall(r'([\w\\:\.]+|".*?")+', text)
        # parts = [p.replace('\n', '').replace('"', '') for p in parts]
        # self.log.debug(parts)
        # try:
        #     if parts[0] not in commands:
        #         self.shell.append_error("Unknown command\n")
        #         return
        #
        #     #import inspect
        #     #inspect.getargspec(someMethod)
        #     if (type(commands[parts[0]]["params"]) is not list and len(parts)-1 != commands[parts[0]]["params"]) or \
        #             (type(commands[parts[0]]["params"]) is list and len(parts)-1 not in commands[parts[0]]["params"]):
        #         self.shell.append_error(
        #             "Command %s takes %d arguments. %d given.\n" %
        #             (parts[0], commands[parts[0]]["params"], len(parts)-1)
        #         )
        #         return
        #
        #     cmdfcn = commands[parts[0]]["fcn"]
        #     cmdconv = commands[parts[0]]["converters"]
        #     if len(parts) - 1 > 0:
        #         retval = cmdfcn(*[cmdconv[i](parts[i + 1]) for i in range(len(parts)-1)])
        #     else:
        #         retval = cmdfcn()
        #     retfcn = commands[parts[0]]["retfcn"]
        #     if retval and retfcn(retval):
        #         self.shell.append_output(retfcn(retval) + "\n")
        #
        # except Exception as e:
        #     #self.shell.append_error(''.join(traceback.format_exc()))
        #     #self.shell.append_error("?\n")
        #     self.shell.append_error(str(e) + "\n")

    def info(self, msg):
        """
        Informs the user. Normally on the status bar, optionally
        also on the shell.

        :param msg: Text to write.
        :return: None
        """

        # Type of message in brackets at the beginning of the message.
        match = re.search("\[([^\]]+)\](.*)", msg)
        if match:
            level = match.group(1)
            msg_ = match.group(2)
            self.ui.fcinfo.set_status(str(msg_), level=level)

            if level.lower() == "error":
                self.shell_message(msg, error=True, show=True)
            elif level.lower() == "warning":
                self.shell_message(msg, warning=True, show=True)

            elif level.lower() == "error_notcl":
                self.shell_message(msg, error=True, show=False)

            elif level.lower() == "warning_notcl":
                self.shell_message(msg, warning=True, show=False)

            elif level.lower() == "success":
                self.shell_message(msg, success=True, show=False)

            elif level.lower() == "selected":
                self.shell_message(msg, selected=True, show=False)

            else:
                self.shell_message(msg, show=False)

        else:
            self.ui.fcinfo.set_status(str(msg), level="info")

            # make sure that if the message is to clear the infobar with a space
            # is not printed over and over on the shell
            if msg != '':
                self.shell_message(msg)

    def restore_toolbar_view(self):
        """
        Some toolbars may be hidden by user and here we restore the state of the toolbars visibility that
        was saved in the defaults dictionary.

        :return: None
        """
        tb = self.defaults["global_toolbar_view"]

        if tb & 1:
            self.ui.toolbarfile.setVisible(True)
        else:
            self.ui.toolbarfile.setVisible(False)

        if tb & 2:
            self.ui.toolbargeo.setVisible(True)
        else:
            self.ui.toolbargeo.setVisible(False)

        if tb & 4:
            self.ui.toolbarview.setVisible(True)
        else:
            self.ui.toolbarview.setVisible(False)

        if tb & 8:
            self.ui.toolbartools.setVisible(True)
        else:
            self.ui.toolbartools.setVisible(False)

        if tb & 16:
            self.ui.exc_edit_toolbar.setVisible(True)
        else:
            self.ui.exc_edit_toolbar.setVisible(False)

        if tb & 32:
            self.ui.geo_edit_toolbar.setVisible(True)
        else:
            self.ui.geo_edit_toolbar.setVisible(False)

        if tb & 64:
            self.ui.grb_edit_toolbar.setVisible(True)
        else:
            self.ui.grb_edit_toolbar.setVisible(False)

        if tb & 128:
            self.ui.snap_toolbar.setVisible(True)
        else:
            self.ui.snap_toolbar.setVisible(False)

        if tb & 256:
            self.ui.toolbarshell.setVisible(True)
        else:
            self.ui.toolbarshell.setVisible(False)

    def load_defaults(self, filename):
        """
        Loads the aplication's default settings from current_defaults.FlatConfig into
        ``self.defaults``.

        :return: None
        """
        try:
            f = open(self.data_path + "/" + filename + ".FlatConfig")
            options = f.read()
            f.close()
        except IOError:
            self.log.error("Could not load defaults file.")
            self.inform.emit('[ERROR] %s' %
                             _("Could not load defaults file."))
            # in case the defaults file can't be loaded, show all toolbars
            self.defaults["global_toolbar_view"] = 511
            return

        try:
            defaults = json.loads(options)
        except Exception:
            # in case the defaults file can't be loaded, show all toolbars
            self.defaults["global_toolbar_view"] = 511
            e = sys.exc_info()[0]
            App.log.error(str(e))
            self.inform.emit('[ERROR] %s' % _("Failed to parse defaults file."))
            return
        self.defaults.update(defaults)
        log.debug("FlatCAM defaults loaded from: %s" % filename)

    def on_import_preferences(self):
        """
        Loads the aplication's factory default settings from factory_defaults.FlatConfig into
        ``self.defaults``.

        :return: None
        """

        self.report_usage("on_import_preferences")
        App.log.debug("on_import_preferences()")

        filter_ = "Config File (*.FlatConfig);;All Files (*.*)"
        try:
            filename, _f = QtWidgets.QFileDialog.getOpenFileName(caption=_("Import FlatCAM Preferences"),
                                                                 directory=self.data_path,
                                                                 filter=filter_)
        except TypeError:
            filename, _f = QtWidgets.QFileDialog.getOpenFileName(caption=_("Import FlatCAM Preferences"),
                                                                 filter=filter_)

        filename = str(filename)

        if filename == "":
            self.inform.emit('[WARNING_NOTCL] %s' %
                             _("FlatCAM preferences import cancelled."))
        else:
            try:
                f = open(filename)
                options = f.read()
                f.close()
            except IOError:
                self.log.error("Could not load defaults file.")
                self.inform.emit('[ERROR_NOTCL] %s' %
                                 _("Could not load defaults file."))
                return

            try:
                defaults_from_file = json.loads(options)
            except Exception:
                e = sys.exc_info()[0]
                App.log.error(str(e))
                self.inform.emit('[ERROR_NOTCL] %s' %
                                 _("Failed to parse defaults file."))
                return
            self.defaults.update(defaults_from_file)
            self.on_preferences_edited()
            self.inform.emit('[success] %s: %s' %
                             (_("Imported Defaults from"), filename))

    def on_export_preferences(self):
        """
        Save the defaults dictionary to a file.

        :return: None
        """
        self.report_usage("on_export_preferences")
        App.log.debug("on_export_preferences()")

        defaults_file_content = None

        self.date = str(datetime.today()).rpartition('.')[0]
        self.date = ''.join(c for c in self.date if c not in ':-')
        self.date = self.date.replace(' ', '_')

        filter__ = "Config File (*.FlatConfig);;All Files (*.*)"
        try:
            filename, _f = QtWidgets.QFileDialog.getSaveFileName(
                caption=_("Export FlatCAM Preferences"),
                directory=self.data_path + '/preferences_' + self.date,
                filter=filter__
            )
        except TypeError:
            filename, _f = QtWidgets.QFileDialog.getSaveFileName(caption=_("Export FlatCAM Preferences"),
                                                                 filter=filter__)

        filename = str(filename)
        defaults_from_file = {}

        if filename == "":
            self.inform.emit('[WARNING_NOTCL] %s' %
                             _("FlatCAM preferences export cancelled."))
            return
        else:
            try:
                f = open(filename, 'w')
                defaults_file_content = f.read()
                f.close()
            except PermissionError:
                self.inform.emit('[WARNING] %s' %
                                 _("Permission denied, saving not possible.\n"
                                   "Most likely another app is holding the file open and not accessible."))
                return
            except IOError:
                App.log.debug('Creating a new preferences file ...')
                f = open(filename, 'w')
                json.dump({}, f)
                f.close()
            except Exception:
                e = sys.exc_info()[0]
                App.log.error("Could not load defaults file.")
                App.log.error(str(e))
                self.inform.emit('[ERROR_NOTCL] %s' %
                                 _("Could not load preferences file."))
                return

            try:
                defaults_from_file = json.loads(defaults_file_content)
            except Exception:
                App.log.warning("Trying to read an empty Preferences file. Continue.")

            # Update options
            self.defaults_read_form()
            defaults_from_file.update(self.defaults)
            self.propagate_defaults(silent=True)

            # Save update options
            try:
                f = open(filename, "w")
                json.dump(defaults_from_file, f, default=to_dict, indent=2, sort_keys=True)
                f.close()
            except Exception:
                self.inform.emit('[ERROR_NOTCL] %s' %
                                 _("Failed to write defaults to file."))
                return
        if self.defaults["global_open_style"] is False:
            self.file_opened.emit("preferences", filename)
        self.file_saved.emit("preferences", filename)
        self.inform.emit('[success] %s: %s' %
                         (_("Exported preferences to"), filename))

    def on_preferences_open_folder(self):
        """
        Will open an Explorer window set to the folder path where the FlatCAM preferences files are usually saved.

        :return: None
        """
        self.report_usage("on_preferences_open_folder()")

        if sys.platform == 'win32':
            subprocess.Popen('explorer %s' % self.data_path)
        elif sys.platform == 'darwin':
            os.system('open "%s"' % self.data_path)
        else:
            subprocess.Popen(['xdg-open', self.data_path])
        self.inform.emit('[success] %s' %
                         _("FlatCAM Preferences Folder opened."))

    def save_geometry(self, x, y, width, height, notebook_width):
        """
        Will save the application geometry and positions in the defaults discitionary to be restored at the next
        launch of the application.

        :param x: X position of the main window
        :param y: Y position of the main window
        :param width: width of the main window
        :param height: height of the main window
        :param notebook_width: the notebook width is adjustable so it get saved here, too.

        :return: None
        """
        self.defaults["global_def_win_x"] = x
        self.defaults["global_def_win_y"] = y
        self.defaults["global_def_win_w"] = width
        self.defaults["global_def_win_h"] = height
        self.defaults["global_def_notebook_width"] = notebook_width
        self.save_defaults()

    def restore_main_win_geom(self):
        try:
            self.ui.setGeometry(self.defaults["global_def_win_x"],
                                self.defaults["global_def_win_y"],
                                self.defaults["global_def_win_w"],
                                self.defaults["global_def_win_h"])
            self.ui.splitter.setSizes([self.defaults["global_def_notebook_width"], 0])
        except KeyError as e:
            log.debug("App.restore_main_win_geom() --> %s" % str(e))

    def message_dialog(self, title, message, kind="info"):
        """
        Builds and show a custom QMessageBox to be used in FlatCAM.

        :param title: title of the QMessageBox
        :param message: message to be displayed
        :param kind: type of QMessageBox; will display a specific icon.
        :return:
        """
        icon = {"info": QtWidgets.QMessageBox.Information,
                "warning": QtWidgets.QMessageBox.Warning,
                "error": QtWidgets.QMessageBox.Critical}[str(kind)]
        dlg = QtWidgets.QMessageBox(icon, title, message, parent=self.ui)
        dlg.setText(message)
        dlg.exec_()

    def register_recent(self, kind, filename):
        """
        Will register the files opened into record dictionaries. The FlatCAM projects has it's own
        dictionary.

        :param kind: type of file that was opened
        :param filename: the path and file name for the file that was opened
        :return:
        """
        self.log.debug("register_recent()")
        self.log.debug("   %s" % kind)
        self.log.debug("   %s" % filename)

        record = {'kind': str(kind), 'filename': str(filename)}
        if record in self.recent:
            return
        if record in self.recent_projects:
            return

        if record['kind'] == 'project':
            self.recent_projects.insert(0, record)
        else:
            self.recent.insert(0, record)

        if len(self.recent) > self.defaults['global_recent_limit']:  # Limit reached
            self.recent.pop()

        if len(self.recent_projects) > self.defaults['global_recent_limit']:  # Limit reached
            self.recent_projects.pop()

        try:
            f = open(self.data_path + '/recent.json', 'w')
        except IOError:
            App.log.error("Failed to open recent items file for writing.")
            self.inform.emit('[ERROR_NOTCL] %s' %
                             _('Failed to open recent files file for writing.'))
            return

        json.dump(self.recent, f, default=to_dict, indent=2, sort_keys=True)
        f.close()

        try:
            fp = open(self.data_path + '/recent_projects.json', 'w')
        except IOError:
            App.log.error("Failed to open recent items file for writing.")
            self.inform.emit('[ERROR_NOTCL] %s' %
                             _('Failed to open recent projects file for writing.'))
            return

        json.dump(self.recent_projects, fp, default=to_dict, indent=2, sort_keys=True)
        fp.close()

        # Re-build the recent items menu
        self.setup_recent_items()

    def new_object(self, kind, name, initialize, active=True, fit=True, plot=True, autoselected=True):
        """
        Creates a new specialized FlatCAMObj and attaches it to the application,
        this is, updates the GUI accordingly, any other records and plots it.
        This method is thread-safe.

        Notes:
            * If the name is in use, the self.collection will modify it
              when appending it to the collection. There is no need to handle
              name conflicts here.

        :param kind: The kind of object to create. One of 'gerber', 'excellon', 'cncjob' and 'geometry'.
        :type kind: str
        :param name: Name for the object.
        :type name: str
        :param initialize: Function to run after creation of the object but before it is attached to the application.
        The function is called with 2 parameters: the new object and the App instance.
        :type initialize: function
        :param active:
        :param fit:
        :param plot: If to plot the resulting object
        :param autoselected: if the resulting object is autoselected in the Project tab and therefore in the
        self.colleaction
        :return: None
        :rtype: None
        """

        App.log.debug("new_object()")
        obj_plot = plot
        obj_autoselected = autoselected

        t0 = time.time()  # Debug

        # ## Create object
        classdict = {
            "gerber": FlatCAMGerber,
            "excellon": FlatCAMExcellon,
            "cncjob": FlatCAMCNCjob,
            "geometry": FlatCAMGeometry,
            "script": FlatCAMScript,
            "document": FlatCAMDocument
        }

        App.log.debug("Calling object constructor...")

        # Object creation/instantiation
        obj = classdict[kind](name)

        obj.units = self.options["units"]  # TODO: The constructor should look at defaults.

        # IMPORTANT
        # The key names in defaults and options dictionary's are not random:
        # they have to have in name first the type of the object (geometry, excellon, cncjob and gerber) or how it's
        # called here, the 'kind' followed by an underline. Above the App default values from self.defaults are
        # copied to self.options. After that, below, depending on the type of
        # object that is created, it will strip the name of the object and the underline (if the original key was
        # let's say "excellon_toolchange", it will strip the excellon_) and to the obj.options the key will become
        # "toolchange"

        for option in self.options:
            if option.find(kind + "_") == 0:
                oname = option[len(kind) + 1:]
                obj.options[oname] = self.options[option]

        obj.isHovering = False
        obj.notHovering = True

        # Initialize as per user request
        # User must take care to implement initialize
        # in a thread-safe way as is is likely that we
        # have been invoked in a separate thread.
        t1 = time.time()
        self.log.debug("%f seconds before initialize()." % (t1 - t0))
        try:
            return_value = initialize(obj, self)
        except Exception as e:
            msg = '[ERROR_NOTCL] %s' % \
                  _("An internal error has ocurred. See shell.\n")
            msg += _("Object ({kind}) failed because: {error} \n\n").format(kind=kind, error=str(e))
            msg += traceback.format_exc()
            self.inform.emit(msg)

            # if str(e) == "Empty Geometry":
            #     self.inform.emit("[ERROR_NOTCL] )
            # else:
            #     self.inform.emit("[ERROR] Object (%s) failed because: %s" % (kind, str(e)))
            return "fail"

        t2 = time.time()
        self.log.debug("%f seconds executing initialize()." % (t2 - t1))

        if return_value == 'fail':
            log.debug("Object (%s) parsing and/or geometry creation failed." % kind)
            return "fail"

        # Check units and convert if necessary
        # This condition CAN be true because initialize() can change obj.units
        if self.options["units"].upper() != obj.units.upper():
            self.inform.emit('%s: %s' %
                             (_("Converting units to "), self.options["units"]))
            obj.convert_units(self.options["units"])
            t3 = time.time()
            self.log.debug("%f seconds converting units." % (t3 - t2))

        # Create the bounding box for the object and then add the results to the obj.options
        # But not for Scripts or for Documents
        if kind != 'document' and kind != 'script':
            try:
                xmin, ymin, xmax, ymax = obj.bounds()
                obj.options['xmin'] = xmin
                obj.options['ymin'] = ymin
                obj.options['xmax'] = xmax
                obj.options['ymax'] = ymax
            except Exception as e:
                log.warning("The object has no bounds properties. %s" % str(e))
                return "fail"

        # update the KeyWords list with the name of the file
        self.myKeywords.append(obj.options['name'])

        FlatCAMApp.App.log.debug("Moving new object back to main thread.")

        # Move the object to the main thread and let the app know that it is available.
        obj.moveToThread(self.main_thread)

        self.object_created.emit(obj, obj_plot, obj_autoselected)

        return obj

    def new_excellon_object(self):
        """
        Creates a new, blank Excellon object.

        :return: None
        """
        self.report_usage("new_excellon_object()")

        self.new_object('excellon', 'new_exc', lambda x, y: None, plot=False)

    def new_geometry_object(self):
        """
        Creates a new, blank and single-tool Geometry object.

        :return: None
        """
        self.report_usage("new_geometry_object()")

        def initialize(obj, app):
            obj.multitool = False

        self.new_object('geometry', 'new_geo', initialize, plot=False)

    def new_gerber_object(self):
        """
        Creates a new, blank Gerber object.

        :return: None
        """
        self.report_usage("new_gerber_object()")

        def initialize(grb_obj, app):
            grb_obj.multitool = False
            grb_obj.source_file = []
            grb_obj.multigeo = False
            grb_obj.follow = False
            grb_obj.apertures = {}
            grb_obj.solid_geometry = []

            try:
                grb_obj.options['xmin'] = 0
                grb_obj.options['ymin'] = 0
                grb_obj.options['xmax'] = 0
                grb_obj.options['ymax'] = 0
            except KeyError:
                pass

        self.new_object('gerber', 'new_grb', initialize, plot=False)

    def new_script_object(self, name=None, text=None):
        """
        Creates a new, blank TCL Script object.
        :param name: a name for the new object
        :param text: pass a source file to the newly created script to be loaded in it
        :return: None
        """
        self.report_usage("new_script_object()")

        if text is not None:
            new_source_file = text
        else:
            commands_list = "# AddCircle, AddPolygon, AddPolyline, AddRectangle, AlignDrill, " \
                            "AlignDrillGrid, Bbox, Bounds, ClearShell, CopperClear,\n"\
                            "# Cncjob, Cutout, Delete, Drillcncjob, ExportDXF, ExportExcellon, ExportGcode,\n" \
                            "ExportGerber, ExportSVG, Exteriors, Follow, GeoCutout, GeoUnion, GetNames,\n"\
                            "# GetSys, ImportSvg, Interiors, Isolate, JoinExcellon, JoinGeometry, " \
                            "ListSys, MillDrills,\n"\
                            "# MillSlots, Mirror, New, NewExcellon, NewGeometry, NewGerber, Nregions, " \
                            "Offset, OpenExcellon, OpenGCode, OpenGerber, OpenProject,\n"\
                            "# Options, Paint, Panelize, PlotAl, PlotObjects, SaveProject, " \
                            "SaveSys, Scale, SetActive, SetSys, SetOrigin, Skew, SubtractPoly,\n" \
                            "# SubtractRectangle, Version, WriteGCode\n"

            new_source_file = '# %s\n' % _('CREATE A NEW FLATCAM TCL SCRIPT') + \
                              '# %s:\n' % _('TCL Tutorial is here') + \
                              '# https://www.tcl.tk/man/tcl8.5/tutorial/tcltutorial.html\n' + '\n\n' + \
                              '# %s:\n' % _("FlatCAM commands list")
            new_source_file += commands_list + '\n'

        def initialize(obj, app):
            obj.source_file = deepcopy(new_source_file)

        if name is None:
            outname = 'new_script'
        else:
            outname = name

        self.new_object('script', outname, initialize, plot=False)

    def new_document_object(self):
        """
        Creates a new, blank Document object.

        :return: None
        """
        self.report_usage("new_document_object()")

        def initialize(obj, app):
            obj.source_file = ""

        self.new_object('document', 'new_document', initialize, plot=False)

    def on_object_created(self, obj, plot, auto_select):
        """
        Event callback for object creation.
        It will add the new object to the collection. After that it will plot the object in a threaded way

        :param obj: The newly created FlatCAM object.
        :param plot: if the newly create object t obe plotted
        :param auto_select: if the newly created object to be autoselected after creation
        :return: None
        """
        t0 = time.time()  # DEBUG
        self.log.debug("on_object_created()")

        # The Collection might change the name if there is a collision
        self.collection.append(obj)

        # after adding the object to the collection always update the list of objects that are in the collection
        self.all_objects_list = self.collection.get_list()

        # self.inform.emit('[selected] %s created & selected: %s' %
        #                  (str(obj.kind).capitalize(), str(obj.options['name'])))
        if obj.kind == 'gerber':
            self.inform.emit(_('[selected] {kind} created/selected: <span style="color:{color};">{name}</span>').format(
                kind=obj.kind.capitalize(), color='green', name=str(obj.options['name'])))
        elif obj.kind == 'excellon':
            self.inform.emit(_('[selected] {kind} created/selected: <span style="color:{color};">{name}</span>').format(
                kind=obj.kind.capitalize(), color='brown', name=str(obj.options['name'])))
        elif obj.kind == 'cncjob':
            self.inform.emit(_('[selected] {kind} created/selected: <span style="color:{color};">{name}</span>').format(
                kind=obj.kind.capitalize(), color='blue', name=str(obj.options['name'])))
        elif obj.kind == 'geometry':
            self.inform.emit(_('[selected] {kind} created/selected: <span style="color:{color};">{name}</span>').format(
                kind=obj.kind.capitalize(), color='red', name=str(obj.options['name'])))
        elif obj.kind == 'script':
            self.inform.emit(_('[selected] {kind} created/selected: <span style="color:{color};">{name}</span>').format(
                kind=obj.kind.capitalize(), color='orange', name=str(obj.options['name'])))
        elif obj.kind == 'document':
            self.inform.emit(_('[selected] {kind} created/selected: <span style="color:{color};">{name}</span>').format(
                kind=obj.kind.capitalize(), color='darkCyan', name=str(obj.options['name'])))

        # update the SHELL auto-completer model with the name of the new object
        self.shell._edit.set_model_data(self.myKeywords)

        if auto_select:
            # select the just opened object but deselect the previous ones
            self.collection.set_all_inactive()
            self.collection.set_active(obj.options["name"])
        else:
            self.collection.set_all_inactive()

        # here it is done the object plotting
        def worker_task(t_obj):
            with self.proc_container.new(_("Plotting")):
                if isinstance(t_obj, FlatCAMCNCjob):
                    t_obj.plot(kind=self.defaults["cncjob_plot_kind"])
                else:
                    t_obj.plot()
                t1 = time.time()  # DEBUG
                self.log.debug("%f seconds adding object and plotting." % (t1 - t0))
                self.object_plotted.emit(t_obj)

        # Send to worker
        # self.worker.add_task(worker_task, [self])
        if plot is True:
            self.worker_task.emit({'fcn': worker_task, 'params': [obj]})

    def on_object_changed(self, obj):
        """
        Called whenever the geometry of the object was changed in some way.
        This require the update of it's bounding values so it can be the selected on canvas.
        Update the bounding box data from obj.options

        :param obj: the object that was changed
        :return: None
        """

        xmin, ymin, xmax, ymax = obj.bounds()
        obj.options['xmin'] = xmin
        obj.options['ymin'] = ymin
        obj.options['xmax'] = xmax
        obj.options['ymax'] = ymax

        log.debug("Object changed, updating the bounding box data on self.options")
        # delete the old selection shape
        self.delete_selection_shape()
        self.should_we_save = True

    def on_object_plotted(self):
        """
        Callback called whenever the plotted object needs to be fit into the viewport (canvas)

        :return: None
        """
        self.on_zoom_fit(None)

    def on_about(self):
        """
        Displays the "about" dialog found in the Menu --> Help.

        :return: None
        """
        self.report_usage("on_about")

        version = self.version
        version_date = self.version_date
        beta = self.beta

        class AboutDialog(QtWidgets.QDialog):
            def __init__(self, parent=None):
                QtWidgets.QDialog.__init__(self, parent)

                # Icon and title
                self.setWindowIcon(parent.app_icon)
                self.setWindowTitle(_("About FlatCAM"))
                self.resize(600, 200)
                # self.setStyleSheet("background-image: url(share/flatcam_icon256.png); background-attachment: fixed")
                # self.setStyleSheet(
                #     "border-image: url(share/flatcam_icon256.png) 0 0 0 0 stretch stretch; "
                #     "background-attachment: fixed"
                # )

                # bgimage = QtGui.QImage('share/flatcam_icon256.png')
                # s_bgimage = bgimage.scaled(QtCore.QSize(self.frameGeometry().width(), self.frameGeometry().height()))
                # palette = QtGui.QPalette()
                # palette.setBrush(10, QtGui.QBrush(bgimage))  # 10 = Windowrole
                # self.setPalette(palette)

                logo = QtWidgets.QLabel()
                logo.setPixmap(QtGui.QPixmap('share/flatcam_icon256.png'))

                title = QtWidgets.QLabel(
                    "<font size=8><B>FlatCAM</B></font><BR>"
                    "{title}<BR>"
                    "<BR>"
                    "<BR>"
                    "<a href = \"https://bitbucket.org/jpcgt/flatcam/src/Beta/\"><B>{devel}</B></a><BR>"
                    "<a href = \"https://bitbucket.org/jpcgt/flatcam/downloads/\"><b>{down}</B></a><BR>"
                    "<a href = \"https://bitbucket.org/jpcgt/flatcam/issues?status=new&status=open/\">"
                    "<B>{issue}</B></a><BR>".format(
                        title=_("2D Computer-Aided Printed Circuit Board Manufacturing"),
                        devel=_("Development"),
                        down=_("DOWNLOAD"),
                        issue=_("Issue tracker"))
                )
                title.setOpenExternalLinks(True)

                closebtn = QtWidgets.QPushButton(_("Close"))

                tab_widget = QtWidgets.QTabWidget()
                description_label = QtWidgets.QLabel(
                    "FlatCAM {version} {beta} ({date}) - {arch}<br>"
                    "<a href = \"http://flatcam.org/\">http://flatcam.org</a><br>".format(
                        version=version,
                        beta=('BETA' if beta else ''),
                        date=version_date,
                        arch=platform.architecture()[0])
                )
                description_label.setOpenExternalLinks(True)

                lic_lbl_header = QtWidgets.QLabel(
                    '%s:<br>%s<br>' % (
                        _('Licensed under the MIT license'),
                        "<a href = \"http://www.opensource.org/licenses/mit-license.php\">"
                        "http://www.opensource.org/licenses/mit-license.php</a>"
                    )
                )
                lic_lbl_header.setOpenExternalLinks(True)

                lic_lbl_body = QtWidgets.QLabel(
                    _(
                        'Permission is hereby granted, free of charge, to any person obtaining a copy\n'
                        'of this software and associated documentation files (the "Software"), to deal\n'
                        'in the Software without restriction, including without limitation the rights\n'
                        'to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n'
                        'copies of the Software, and to permit persons to whom the Software is\n'
                        'furnished to do so, subject to the following conditions:\n\n'
    
                        'The above copyright notice and this permission notice shall be included in\n'
                        'all copies or substantial portions of the Software.\n\n'
    
                        'THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n'
                        'IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n'
                        'FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n'
                        'AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n'
                        'LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n'
                        'OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN\n'
                        'THE SOFTWARE.'
                    )
                )

                attributions_label = QtWidgets.QLabel(
                    _(
                        'Some of the icons used are from the following sources:<br>'
                        '<div>Icons made by <a href="https://www.flaticon.com/authors/freepik" '
                        'title="Freepik">Freepik</a> from <a href="https://www.flaticon.com/"             '
                        'title="Flaticon">www.flaticon.com</a></div>'
                        'Icons by <a target="_blank" href="https://icons8.com">Icons8</a>'
                    )
                )

                # layouts
                layout1 = QtWidgets.QVBoxLayout()
                layout1_1 = QtWidgets.QHBoxLayout()
                layout1_2 = QtWidgets.QHBoxLayout()

                layout2 = QtWidgets.QHBoxLayout()
                layout3 = QtWidgets.QHBoxLayout()

                self.setLayout(layout1)
                layout1.addLayout(layout1_1)
                layout1.addLayout(layout1_2)

                layout1.addLayout(layout2)
                layout1.addLayout(layout3)

                layout1_1.addStretch()
                layout1_1.addWidget(description_label)
                layout1_2.addWidget(tab_widget)

                self.splash_tab = QtWidgets.QWidget()
                self.splash_tab.setObjectName("splash_about")
                self.splash_tab_layout = QtWidgets.QHBoxLayout(self.splash_tab)
                self.splash_tab_layout.setContentsMargins(2, 2, 2, 2)
                tab_widget.addTab(self.splash_tab, _("Splash"))

                self.programmmers_tab = QtWidgets.QWidget()
                self.programmmers_tab.setObjectName("programmers_about")
                self.programmmers_tab_layout = QtWidgets.QVBoxLayout(self.programmmers_tab)
                self.programmmers_tab_layout.setContentsMargins(2, 2, 2, 2)
                tab_widget.addTab(self.programmmers_tab, _("Programmers"))

                self.translators_tab = QtWidgets.QWidget()
                self.translators_tab.setObjectName("translators_about")
                self.translators_tab_layout = QtWidgets.QVBoxLayout(self.translators_tab)
                self.translators_tab_layout.setContentsMargins(2, 2, 2, 2)
                tab_widget.addTab(self.translators_tab, _("Translators"))

                self.license_tab = QtWidgets.QWidget()
                self.license_tab.setObjectName("license_about")
                self.license_tab_layout = QtWidgets.QVBoxLayout(self.license_tab)
                self.license_tab_layout.setContentsMargins(2, 2, 2, 2)
                tab_widget.addTab(self.license_tab, _("License"))

                self.attributions_tab = QtWidgets.QWidget()
                self.attributions_tab.setObjectName("attributions_about")
                self.attributions_tab_layout = QtWidgets.QVBoxLayout(self.attributions_tab)
                self.attributions_tab_layout.setContentsMargins(2, 2, 2, 2)
                tab_widget.addTab(self.attributions_tab, _("Attributions"))

                self.splash_tab_layout.addWidget(logo, stretch=0)
                self.splash_tab_layout.addWidget(title, stretch=1)

                pal = QtGui.QPalette()
                pal.setColor(QtGui.QPalette.Background, Qt.white)

                self.prog_grid_lay = QtWidgets.QGridLayout()
                self.prog_grid_lay.setHorizontalSpacing(20)
                self.prog_grid_lay.setColumnStretch(0, 0)
                self.prog_grid_lay.setColumnStretch(2, 1)

                prog_widget = QtWidgets.QWidget()
                prog_widget.setLayout(self.prog_grid_lay)
                prog_scroll = QtWidgets.QScrollArea()
                prog_scroll.setWidget(prog_widget)
                prog_scroll.setWidgetResizable(True)
                prog_scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
                prog_scroll.setPalette(pal)

                self.programmmers_tab_layout.addWidget(prog_scroll)

                self.prog_grid_lay.addWidget(QtWidgets.QLabel('<b>%s</b>' % _("Programmer")), 0, 0)
                self.prog_grid_lay.addWidget(QtWidgets.QLabel('<b>%s</b>' % _("Status")), 0, 1)
                self.prog_grid_lay.addWidget(QtWidgets.QLabel('<b>%s</b>' % _("E-mail")), 0, 2)
                self.prog_grid_lay.addWidget(QtWidgets.QLabel('%s' % "Juan Pablo Caram"), 1, 0)
                self.prog_grid_lay.addWidget(QtWidgets.QLabel('%s' % "Program Author"), 1, 1)
                self.prog_grid_lay.addWidget(QtWidgets.QLabel('%s' % "<>"), 1, 2)
                self.prog_grid_lay.addWidget(QtWidgets.QLabel('%s' % "Denis Hayrullin"), 2, 0)

                self.prog_grid_lay.addWidget(QtWidgets.QLabel('%s' % "Kamil Sopko"), 3, 0)
                self.prog_grid_lay.addWidget(QtWidgets.QLabel('%s' % "Marius Stanciu"), 4, 0)
                self.prog_grid_lay.addWidget(QtWidgets.QLabel('%s' % _("BETA Maintainer >= 2019")), 4, 1)
                self.prog_grid_lay.addWidget(QtWidgets.QLabel('%s' % "<marius_adrian@yahoo.com>"), 4, 2)
                self.prog_grid_lay.addWidget(QtWidgets.QLabel(''), 5, 0)

                self.prog_grid_lay.addWidget(QtWidgets.QLabel('%s' % "Alex Lazar"), 6, 0)
                self.prog_grid_lay.addWidget(QtWidgets.QLabel('%s' % "Matthieu Berthomé"), 7, 0)
                self.prog_grid_lay.addWidget(QtWidgets.QLabel('%s' % "Mike Evans"), 8, 0)
                self.prog_grid_lay.addWidget(QtWidgets.QLabel('%s' % "Victor Benso"), 9, 0)
                self.prog_grid_lay.addWidget(QtWidgets.QLabel(''), 10, 0)

                self.prog_grid_lay.addWidget(QtWidgets.QLabel('%s' % "Barnaby Walters"), 11, 0)
                self.prog_grid_lay.addWidget(QtWidgets.QLabel('%s' % "Jørn Sandvik Nilsson"), 12, 0)
                self.prog_grid_lay.addWidget(QtWidgets.QLabel('%s' % "Lei Zheng"), 13, 0)
                self.prog_grid_lay.addWidget(QtWidgets.QLabel('%s' % "Marco A Quezada"), 14, 0)
                self.prog_grid_lay.addWidget(QtWidgets.QLabel(''), 12, 0)

                self.prog_grid_lay.addWidget(QtWidgets.QLabel('%s' % "Cedric Dussud"), 15, 0)
                self.prog_grid_lay.addWidget(QtWidgets.QLabel('%s' % "Chris Hemingway"), 16, 0)
                self.prog_grid_lay.addWidget(QtWidgets.QLabel('%s' % "Damian Wrobel"), 17, 0)
                self.prog_grid_lay.addWidget(QtWidgets.QLabel('%s' % "Daniel Sallin"), 18, 0)
                self.prog_grid_lay.addWidget(QtWidgets.QLabel(''), 19, 0)

                self.prog_grid_lay.addWidget(QtWidgets.QLabel('%s' % "Bruno Vunderl"), 20, 0)
                self.prog_grid_lay.addWidget(QtWidgets.QLabel('%s' % "Gonzalo Lopez"), 21, 0)
                self.prog_grid_lay.addWidget(QtWidgets.QLabel('%s' % "Jakob Staudt"), 22, 0)
                self.prog_grid_lay.addWidget(QtWidgets.QLabel('%s' % "Mike Smith"), 23, 0)

                self.prog_grid_lay.addWidget(QtWidgets.QLabel(''), 24, 0)

                self.prog_grid_lay.addWidget(QtWidgets.QLabel('%s' % "Lubos Medovarsky"), 25, 0)
                self.prog_grid_lay.addWidget(QtWidgets.QLabel('%s' % "Steve Martina"), 26, 0)
                self.prog_grid_lay.addWidget(QtWidgets.QLabel('%s' % "Thomas Duffin"), 27, 0)
                self.prog_grid_lay.addWidget(QtWidgets.QLabel(''), 28, 0)

                self.prog_grid_lay.addWidget(QtWidgets.QLabel('%s' % "@Idechix"), 29, 0)
                self.prog_grid_lay.addWidget(QtWidgets.QLabel('%s' % "@SM"), 30, 0)
                self.prog_grid_lay.addWidget(QtWidgets.QLabel('%s' % "@grbf"), 31, 0)
                self.prog_grid_lay.addWidget(QtWidgets.QLabel('%s' % "@Symonty"), 32, 0)
                self.prog_grid_lay.addWidget(QtWidgets.QLabel('%s' % "@mgix"), 33, 0)

                self.translator_grid_lay = QtWidgets.QGridLayout()
                self.translator_grid_lay.setColumnStretch(0, 0)
                self.translator_grid_lay.setColumnStretch(1, 0)
                self.translator_grid_lay.setColumnStretch(2, 1)
                self.translator_grid_lay.setColumnStretch(3, 0)

                # trans_widget = QtWidgets.QWidget()
                # trans_widget.setLayout(self.translator_grid_lay)
                # self.translators_tab_layout.addWidget(trans_widget)
                # self.translators_tab_layout.addStretch()

                trans_widget = QtWidgets.QWidget()
                trans_widget.setLayout(self.translator_grid_lay)
                trans_scroll = QtWidgets.QScrollArea()
                trans_scroll.setWidget(trans_widget)
                trans_scroll.setWidgetResizable(True)
                trans_scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
                trans_scroll.setPalette(pal)
                self.translators_tab_layout.addWidget(trans_scroll)

                self.translator_grid_lay.addWidget(QtWidgets.QLabel('<b>%s</b>' % _("Language")), 0, 0)
                self.translator_grid_lay.addWidget(QtWidgets.QLabel('<b>%s</b>' % _("Translator")), 0, 1)
                self.translator_grid_lay.addWidget(QtWidgets.QLabel('<b>%s</b>' % _("Corrections")), 0, 2)
                self.translator_grid_lay.addWidget(QtWidgets.QLabel('<b>%s</b>' % _("E-mail")), 0, 3)
                self.translator_grid_lay.addWidget(QtWidgets.QLabel('%s' % "BR - Portuguese"), 1, 0)
                self.translator_grid_lay.addWidget(QtWidgets.QLabel('%s' % "Carlos Stein"), 1, 1)
                self.translator_grid_lay.addWidget(QtWidgets.QLabel('%s' % "<carlos.stein@gmail.com>"),  1, 3)
                self.translator_grid_lay.addWidget(QtWidgets.QLabel('%s' % "French"), 2, 0)
                self.translator_grid_lay.addWidget(QtWidgets.QLabel('%s' % "Marius Stanciu"), 2, 1)
                self.translator_grid_lay.addWidget(QtWidgets.QLabel('%s' % "(Google-Translation)"), 2, 2)
                self.translator_grid_lay.addWidget(QtWidgets.QLabel('%s' % " "), 2, 3)
                self.translator_grid_lay.addWidget(QtWidgets.QLabel('%s' % "German"), 3, 0)
                self.translator_grid_lay.addWidget(QtWidgets.QLabel('%s' % "Marius Stanciu"), 3, 1)
                self.translator_grid_lay.addWidget(QtWidgets.QLabel('%s' % "Jens Karstedt"), 3, 2)
                self.translator_grid_lay.addWidget(QtWidgets.QLabel('%s' % " "), 3, 3)
                self.translator_grid_lay.addWidget(QtWidgets.QLabel('%s' % "Romanian"), 4, 0)
                self.translator_grid_lay.addWidget(QtWidgets.QLabel('%s' % "Marius Stanciu"), 4, 1)
                self.translator_grid_lay.addWidget(QtWidgets.QLabel('%s' % "<marius_adrian@yahoo.com>"), 4, 3)
                self.translator_grid_lay.addWidget(QtWidgets.QLabel('%s' % "Russian"), 5, 0)
                self.translator_grid_lay.addWidget(QtWidgets.QLabel('%s' % "Andrey Kultyapov"), 5, 1)
                self.translator_grid_lay.addWidget(QtWidgets.QLabel('%s' % "<camellan@yandex.ru>"), 5, 3)
                self.translator_grid_lay.addWidget(QtWidgets.QLabel('%s' % "Spanish"), 6, 0)
                self.translator_grid_lay.addWidget(QtWidgets.QLabel('%s' % "Marius Stanciu"), 6, 1)
                self.translator_grid_lay.addWidget(QtWidgets.QLabel('%s' % "(Google-Translation)"), 6, 2)
                self.translator_grid_lay.addWidget(QtWidgets.QLabel('%s' % " "), 6, 3)
                self.translator_grid_lay.setColumnStretch(0, 0)
                self.translators_tab_layout.addStretch()

                self.license_tab_layout.addWidget(lic_lbl_header)
                self.license_tab_layout.addWidget(lic_lbl_body)

                self.license_tab_layout.addStretch()

                self.attributions_tab_layout.addWidget(attributions_label)
                self.attributions_tab_layout.addStretch()

                layout3.addStretch()
                layout3.addWidget(closebtn)

                closebtn.clicked.connect(self.accept)

        AboutDialog(self.ui).exec_()

    def install_bookmarks(self, book_dict=None):
        """
        Install the bookmarks actions in the Help menu -> Bookmarks

        :param book_dict: a dict having the actions text as keys and the weblinks as the values
        :return: None
        """

        if book_dict is None:
            self.defaults["global_bookmarks"].update(
                {
                    '1': ['FlatCAM', "http://flatcam.org"],
                    '2': ['Backup Site', ""]
                }
            )
        else:
            self.defaults["global_bookmarks"].clear()
            self.defaults["global_bookmarks"].update(book_dict)

        # first try to disconnect if somehow they get connected from elsewhere
        for act in self.ui.menuhelp_bookmarks.actions():
            try:
                act.triggered.disconnect()
            except TypeError:
                pass

            # clear all actions except the last one who is the Bookmark manager
            if act is self.ui.menuhelp_bookmarks.actions()[-1]:
                pass
            else:
                self.ui.menuhelp_bookmarks.removeAction(act)

        bm_limit = int(self.defaults["global_bookmarks_limit"])
        if self.defaults["global_bookmarks"]:

            # order the self.defaults["global_bookmarks"] dict keys by the value as integer
            # the whole convoluted things is because when serializing the self.defaults (on app close or save)
            # the JSON is first making the keys as strings (therefore I have to use strings too
            # or do the conversion :(
            # )
            # and it is ordering them (actually I want that to make the defaults easy to search within) but making
            # the '10' entry jsut after '1' therefore ordering as strings

            sorted_bookmarks = sorted(list(self.defaults["global_bookmarks"].items())[:bm_limit],
                                      key=lambda x: int(x[0]))
            for entry, bookmark in sorted_bookmarks:
                title = bookmark[0]
                weblink = bookmark[1]

                act = QtWidgets.QAction(parent=self.ui.menuhelp_bookmarks)
                act.setText(title)

                act.setIcon(QtGui.QIcon('share/link16.png'))
                # from here: https://stackoverflow.com/questions/20390323/pyqt-dynamic-generate-qmenu-action-and-connect
                if title == 'Backup Site' and weblink == "":
                    act.triggered.connect(self.on_backup_site)
                else:
                    act.triggered.connect(lambda sig, link=weblink: webbrowser.open(link))
                self.ui.menuhelp_bookmarks.insertAction(self.ui.menuhelp_bookmarks_manager, act)

        self.ui.menuhelp_bookmarks_manager.triggered.connect(self.on_bookmarks_manager)

    def on_bookmarks_manager(self):
        """
        Adds the bookmark manager in a Tab in Plot Area
        :return:
        """
        for idx in range(self.ui.plot_tab_area.count()):
            if self.ui.plot_tab_area.tabText(idx) == _("Bookmarks Manager"):
                # there can be only one instance of Bookmark Manager at one time
                return

        # BookDialog(app=self, storage=self.defaults["global_bookmarks"], parent=self.ui).exec_()
        self.book_dialog_tab = BookmarkManager(app=self, storage=self.defaults["global_bookmarks"], parent=self.ui)

        # add the tab if it was closed
        self.ui.plot_tab_area.addTab(self.book_dialog_tab, _("Bookmarks Manager"))

        # delete the absolute and relative position and messages in the infobar
        self.ui.position_label.setText("")
        self.ui.rel_position_label.setText("")

        # Switch plot_area to preferences page
        self.ui.plot_tab_area.setCurrentWidget(self.book_dialog_tab)

    @staticmethod
    def on_backup_site():
        msgbox = QtWidgets.QMessageBox()
        msgbox.setText(_("This entry will resolve to another website if:\n\n"
                         "1. FlatCAM.org website is down\n"
                         "2. Someone forked FlatCAM project and wants to point\n"
                         "to his own website\n\n"
                         "If you can't get any informations about FlatCAM beta\n"
                         "use the YouTube channel link from the Help menu."))

        msgbox.setWindowTitle(_("Alternative website"))
        msgbox.setWindowIcon(QtGui.QIcon('share/globe16.png'))
        bt_yes = msgbox.addButton(_('Close'), QtWidgets.QMessageBox.YesRole)

        msgbox.setDefaultButton(bt_yes)
        msgbox.exec_()
        # response = msgbox.clickedButton()

    def on_file_savedefaults(self):
        """
        Callback for menu item File->Save Defaults. Saves application default options
        ``self.defaults`` to current_defaults.FlatConfig.

        :return: None
        """

        self.save_defaults()

    # def on_app_exit(self):
    #     self.report_usage("on_app_exit()")
    #
    #     if self.collection.get_list():
    #         msgbox = QtWidgets.QMessageBox()
    #         # msgbox.setText("<B>Save changes ...</B>")
    #         msgbox.setText("There are files/objects opened in FlatCAM. "
    #                        "\n"
    #                        "Do you want to Save the project?")
    #         msgbox.setWindowTitle("Save changes")
    #         msgbox.setWindowIcon(QtGui.QIcon('share/save_as.png'))
    #         msgbox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No |
    #                                   QtWidgets.QMessageBox.Cancel)
    #         msgbox.setDefaultButton(QtWidgets.QMessageBox.Yes)
    #
    #         response = msgbox.exec_()
    #
    #         if response == QtWidgets.QMessageBox.Yes:
    #             self.on_file_saveprojectas(thread=False)
    #         elif response == QtWidgets.QMessageBox.Cancel:
    #             return
    #         self.save_defaults()
    #     else:
    #         self.save_defaults()
    #     log.debug("Application defaults saved ... Exit event.")
    #     QtWidgets.qApp.quit()

    def save_defaults(self, silent=False, data_path=None, first_time=False):
        """
        Saves application default options
        ``self.defaults`` to current_defaults.FlatConfig file.
        Save the toolbars visibility status to the preferences file (current_defaults.FlatConfig) to be
        used at the next launch of the application.

        :param silent: whether to display a message in status bar or not; boolean
        :param data_path: the path where to save the preferences file (current_defaults.FlatConfig)
        When the application is portable it should be a mobile location.
        :return: None
        """
        self.report_usage("save_defaults")

        if data_path is None:
            data_path = self.data_path

        # Read options from file
        try:
            f = open(data_path + "/current_defaults.FlatConfig")
            defaults_file_content = f.read()
            f.close()
        except Exception:
            e = sys.exc_info()[0]
            App.log.error("Could not load defaults file.")
            App.log.error(str(e))
            self.inform.emit('[ERROR_NOTCL] %s' % _("Could not load defaults file."))
            return

        try:
            defaults = json.loads(defaults_file_content)
        except Exception:
            e = sys.exc_info()[0]
            App.log.error("Failed to parse defaults file.")
            App.log.error(str(e))
            self.inform.emit('[ERROR_NOTCL] %s' % _("Failed to parse defaults file."))
            return

        # Update options
        self.defaults_read_form()
        defaults.update(self.defaults)
        self.propagate_defaults(silent=True)

        # Save the toolbar view
        tb_status = 0
        if self.ui.toolbarfile.isVisible():
            tb_status += 1

        if self.ui.toolbargeo.isVisible():
            tb_status += 2

        if self.ui.toolbarview.isVisible():
            tb_status += 4

        if self.ui.toolbartools.isVisible():
            tb_status += 8

        if self.ui.exc_edit_toolbar.isVisible():
            tb_status += 16

        if self.ui.geo_edit_toolbar.isVisible():
            tb_status += 32

        if self.ui.grb_edit_toolbar.isVisible():
            tb_status += 64

        if self.ui.snap_toolbar.isVisible():
            tb_status += 128

        if self.ui.toolbarshell.isVisible():
            tb_status += 256

        if first_time is False:
            self.defaults["global_toolbar_view"] = tb_status

        # Save update options
        try:
            f = open(data_path + "/current_defaults.FlatConfig", "w")
            json.dump(defaults, f, default=to_dict, indent=2, sort_keys=True)
            f.close()
        except Exception as e:
            log.debug("App.save_defaults() --> %s" % str(e))
            self.inform.emit('[ERROR_NOTCL] %s' % _("Failed to write defaults to file."))
            return

        if not silent:
            self.inform.emit('[success] %s' % _("Preferences saved."))

    def save_factory_defaults(self, silent_message=False, data_path=None):
        """
        Saves application factory default options
        ``self.defaults`` to factory_defaults.FlatConfig.
        It's a one time job done just after the first install.

        :param silent_message: whether to display a message in status bar or not; boolean
        :param data_path: the path where to save the default preferences file (factory_defaults.FlatConfig)
        When the application is portable it should be a mobile location.
        :return: None
        """

        self.report_usage("save_factory_defaults")

        if data_path is None:
            data_path = self.data_path

        # Read options from file
        try:
            f_f_def = open(data_path + "/factory_defaults.FlatConfig")
            factory_defaults_file_content = f_f_def.read()
            f_f_def.close()
        except Exception:
            e = sys.exc_info()[0]
            App.log.error("Could not load factory defaults file.")
            App.log.error(str(e))
            self.inform.emit('[ERROR_NOTCL] %s' % _("Could not load factory defaults file."))
            return

        try:
            factory_defaults = json.loads(factory_defaults_file_content)
        except Exception:
            e = sys.exc_info()[0]
            App.log.error("Failed to parse factory defaults file.")
            App.log.error(str(e))
            self.inform.emit('[ERROR_NOTCL] %s' % _("Failed to parse factory defaults file."))
            return

        # Update options
        self.defaults_read_form()
        factory_defaults.update(self.defaults)
        self.propagate_defaults(silent=True)

        # Save update options
        try:
            f_f_def_s = open(data_path + "/factory_defaults.FlatConfig", "w")
            json.dump(factory_defaults, f_f_def_s, default=to_dict, indent=2, sort_keys=True)
            f_f_def_s.close()
        except Exception as e:
            log.debug("App.save_factory_default() save update --> %s" % str(e))
            self.inform.emit('[ERROR_NOTCL] %s' % _("Failed to write factory defaults to file."))
            return

        if silent_message is False:
            self.inform.emit(_("Factory defaults saved."))

    def final_save(self):
        """
        Callback for doing a preferences save to file whenever the application is about to quit.
        If the project has changes, it will ask the user to save the project.

        :return: None
        """
        if self.save_in_progress:
            self.inform.emit('[WARNING_NOTCL] %s' % _("Application is saving the project. Please wait ..."))
            return

        if self.should_we_save and self.collection.get_list():
            msgbox = QtWidgets.QMessageBox()
            msgbox.setText(_("There are files/objects modified in FlatCAM. "
                             "\n"
                             "Do you want to Save the project?"))
            msgbox.setWindowTitle(_("Save changes"))
            msgbox.setWindowIcon(QtGui.QIcon('share/save_as.png'))
            bt_yes = msgbox.addButton(_('Yes'), QtWidgets.QMessageBox.YesRole)
            bt_no = msgbox.addButton(_('No'), QtWidgets.QMessageBox.NoRole)
            bt_cancel = msgbox.addButton(_('Cancel'), QtWidgets.QMessageBox.RejectRole)

            msgbox.setDefaultButton(bt_yes)
            msgbox.exec_()
            response = msgbox.clickedButton()

            if response == bt_yes:
                try:
                    self.trayIcon.hide()
                except Exception:
                    pass
                self.on_file_saveprojectas(use_thread=True, quit_action=True)
            elif response == bt_no:
                try:
                    self.trayIcon.hide()
                except Exception:
                    pass
                self.quit_application()
            elif response == bt_cancel:
                return
        else:
            try:
                self.trayIcon.hide()
            except Exception:
                pass
            self.quit_application()

    def quit_application(self):
        """
        Called (as a pyslot or not) when the application is quit.

        :return: None
        """
        self.save_defaults()
        log.debug("App.final_save() --> App Defaults saved.")

        if self.cmd_line_headless != 1:
            # save app state to file
            stgs = QSettings("Open Source", "FlatCAM")
            stgs.setValue('saved_gui_state', self.ui.saveState())
            stgs.setValue('maximized_gui', self.ui.isMaximized())
            stgs.setValue(
                'language',
                self.ui.general_defaults_form.general_app_group.language_cb.get_value()
            )
            stgs.setValue(
                'notebook_font_size',
                self.ui.general_defaults_form.general_gui_set_group.notebook_font_size_spinner.get_value()
            )
            stgs.setValue(
                'axis_font_size',
                self.ui.general_defaults_form.general_gui_set_group.axis_font_size_spinner.get_value()
            )
            stgs.setValue(
                'textbox_font_size',
                self.ui.general_defaults_form.general_gui_set_group.textbox_font_size_spinner.get_value()
            )
            stgs.setValue('toolbar_lock', self.ui.lock_action.isChecked())
            stgs.setValue(
                'machinist',
                1 if self.ui.general_defaults_form.general_app_group.machinist_cb.get_value() else 0
            )

            # This will write the setting to the platform specific storage.
            del stgs

        log.debug("App.final_save() --> App UI state saved.")
        QtWidgets.qApp.quit()

    def on_portable_checked(self, state):
        """
        Callback called when the checkbox in Preferences GUI is checked.
        It will set the application as portable by creating the preferences and recent files in the
        'config' folder found in the FlatCAM installation folder.

        :param state: boolean, the state of the checkbox when clicked/checked
        :return:
        """

        line_no = 0
        data = None

        if sys.platform != 'win32':
            # this won't work in Linux or MacOS
            return

        # test if the app was frozen and choose the path for the configuration file
        if getattr(sys, "frozen", False) is True:
            current_data_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__))) + '\\config'
        else:
            current_data_path = os.path.dirname(os.path.realpath(__file__)) + '\\config'

        config_file = current_data_path + '\\configuration.txt'
        try:
            with open(config_file, 'r') as f:
                try:
                    data = f.readlines()
                except Exception as e:
                    log.debug('App.__init__() -->%s' % str(e))
                    return
        except FileNotFoundError:
            pass

        for line in data:
            line = line.strip('\n')
            param = str(line).rpartition('=')
            if param[0] == 'portable':
                break
            line_no += 1

        if state:
            data[line_no] = 'portable=True\n'
            # create the new defauults files
            # create current_defaults.FlatConfig file if there is none
            try:
                f = open(current_data_path + '/current_defaults.FlatConfig')
                f.close()
            except IOError:
                App.log.debug('Creating empty current_defaults.FlatConfig')
                f = open(current_data_path + '/current_defaults.FlatConfig', 'w')
                json.dump({}, f)
                f.close()

            # create factory_defaults.FlatConfig file if there is none
            try:
                f = open(current_data_path + '/factory_defaults.FlatConfig')
                f.close()
            except IOError:
                App.log.debug('Creating empty factory_defaults.FlatConfig')
                f = open(current_data_path + '/factory_defaults.FlatConfig', 'w')
                json.dump({}, f)
                f.close()

            try:
                f = open(current_data_path + '/recent.json')
                f.close()
            except IOError:
                App.log.debug('Creating empty recent.json')
                f = open(current_data_path + '/recent.json', 'w')
                json.dump([], f)
                f.close()

            try:
                fp = open(current_data_path + '/recent_projects.json')
                fp.close()
            except IOError:
                App.log.debug('Creating empty recent_projects.json')
                fp = open(current_data_path + '/recent_projects.json', 'w')
                json.dump([], fp)
                fp.close()

            # save the current defaults to the new defaults file
            self.save_defaults(silent=True, data_path=current_data_path)
            self.save_factory_defaults(silent_message=True, data_path=current_data_path)

        else:
            data[line_no] = 'portable=False\n'

        with open(config_file, 'w') as f:
            f.writelines(data)

    def on_toggle_shell(self):
        """
        Toggle shell: if is visible close it, if it is closed then open it
        :return: None
        """

        self.report_usage("on_toggle_shell()")

        if self.ui.shell_dock.isVisible():
            self.ui.shell_dock.hide()
        else:
            self.ui.shell_dock.show()

    def on_register_files(self, obj_type=None):
        """
        Called whenever there is a need to register file extensions with FlatCAM.
        Works only in Windows and should be called only when FlatCAM is run in Windows.

        :param obj_type: the type of object to be register for.
        Can be: 'gerber', 'excellon' or 'gcode'. 'geometry' is not used for the moment.

        :return: None
        """
        log.debug("Manufacturing files extensions are registered with FlatCAM.")

        new_reg_path = 'Software\\Classes\\'
        # find if the current user is admin
        try:
            is_admin = os.getuid() == 0
        except AttributeError:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() == 1

        if is_admin is True:
            root_path = winreg.HKEY_LOCAL_MACHINE
        else:
            root_path = winreg.HKEY_CURRENT_USER

        # create the keys
        def set_reg(name, root_path, new_reg_path, value):
            try:
                winreg.CreateKey(root_path, new_reg_path)
                with winreg.OpenKey(root_path, new_reg_path, 0, winreg.KEY_WRITE) as registry_key:
                    winreg.SetValueEx(registry_key, name, 0, winreg.REG_SZ, value)
                return True
            except WindowsError:
                return False

        # delete key in registry
        def delete_reg(root_path, reg_path, key_to_del):
            key_to_del_path = reg_path + key_to_del
            try:
                winreg.DeleteKey(root_path, key_to_del_path)
                return True
            except WindowsError:
                return False

        if obj_type is None or obj_type == 'excellon':
            exc_list = \
                self.ui.util_defaults_form.fa_excellon_group.exc_list_text.get_value().replace(' ', '').split(',')
            exc_list = [x for x in exc_list if x != '']

            # register all keys in the Preferences window
            for ext in exc_list:
                new_k = new_reg_path + '.%s' % ext
                set_reg('', root_path=root_path, new_reg_path=new_k, value='FlatCAM')

            # and unregister those that are no longer in the Preferences windows but are in the file
            for ext in self.defaults["fa_excellon"].replace(' ', '').split(','):
                if ext not in exc_list:
                    delete_reg(root_path=root_path, reg_path=new_reg_path, key_to_del='.%s' % ext)

            # now write the updated extensions to the self.defaults
            # new_ext = ''
            # for ext in exc_list:
            #     new_ext = new_ext + ext + ', '
            # self.defaults["fa_excellon"] = new_ext
            self.inform.emit('[success] %s' % _("Selected Excellon file extensions registered with FlatCAM."))

        if obj_type is None or obj_type == 'gcode':
            gco_list = self.ui.util_defaults_form.fa_gcode_group.gco_list_text.get_value().replace(' ', '').split(',')
            gco_list = [x for x in gco_list if x != '']

            # register all keys in the Preferences window
            for ext in gco_list:
                new_k = new_reg_path + '.%s' % ext
                set_reg('', root_path=root_path, new_reg_path=new_k, value='FlatCAM')

            # and unregister those that are no longer in the Preferences windows but are in the file
            for ext in self.defaults["fa_gcode"].replace(' ', '').split(','):
                if ext not in gco_list:
                    delete_reg(root_path=root_path, reg_path=new_reg_path, key_to_del='.%s' % ext)

            # now write the updated extensions to the self.defaults
            # new_ext = ''
            # for ext in gco_list:
            #     new_ext = new_ext + ext + ', '
            # self.defaults["fa_gcode"] = new_ext
            self.inform.emit('[success] %s' %
                             _("Selected GCode file extensions registered with FlatCAM."))

        if obj_type is None or obj_type == 'gerber':
            grb_list = self.ui.util_defaults_form.fa_gerber_group.grb_list_text.get_value().replace(' ', '').split(',')
            grb_list = [x for x in grb_list if x != '']

            # register all keys in the Preferences window
            for ext in grb_list:
                new_k = new_reg_path + '.%s' % ext
                set_reg('', root_path=root_path, new_reg_path=new_k, value='FlatCAM')

            # and unregister those that are no longer in the Preferences windows but are in the file
            for ext in self.defaults["fa_gerber"].replace(' ', '').split(','):
                if ext not in grb_list:
                    delete_reg(root_path=root_path, reg_path=new_reg_path, key_to_del='.%s' % ext)

            # now write the updated extensions to the self.defaults
            # new_ext = ''
            # for ext in grb_list:
            #     new_ext = new_ext + ext + ', '
            # self.defaults["fa_gerber"] = new_ext
            self.inform.emit('[success] %s' %
                             _("Selected Gerber file extensions registered with FlatCAM."))

    def add_extension(self, ext_type):
        """
        Add a file extension to the list for a specific object

        :param ext_type: type of FlatCAM object: excellon, gerber, geometry and then 'not FlatCAM object' keyword
        :return:
        """

        if ext_type == 'excellon':
            new_ext = self.ui.util_defaults_form.fa_excellon_group.ext_entry.get_value()
            if new_ext == '':
                return

            old_val = self.ui.util_defaults_form.fa_excellon_group.exc_list_text.get_value().replace(' ', '').split(',')
            if new_ext in old_val:
                return
            old_val.append(new_ext)
            old_val.sort()
            self.ui.util_defaults_form.fa_excellon_group.exc_list_text.set_value(', '.join(old_val))
        if ext_type == 'gcode':
            new_ext = self.ui.util_defaults_form.fa_gcode_group.ext_entry.get_value()
            if new_ext == '':
                return

            old_val = self.ui.util_defaults_form.fa_gcode_group.gco_list_text.get_value().replace(' ', '').split(',')
            if new_ext in old_val:
                return
            old_val.append(new_ext)
            old_val.sort()
            self.ui.util_defaults_form.fa_gcode_group.gco_list_text.set_value(', '.join(old_val))
        if ext_type == 'gerber':
            new_ext = self.ui.util_defaults_form.fa_gerber_group.ext_entry.get_value()
            if new_ext == '':
                return

            old_val = self.ui.util_defaults_form.fa_gerber_group.grb_list_text.get_value().replace(' ', '').split(',')
            if new_ext in old_val:
                return
            old_val.append(new_ext)
            old_val.sort()
            self.ui.util_defaults_form.fa_gerber_group.grb_list_text.set_value(', '.join(old_val))
        if ext_type == 'keyword':
            new_kw = self.ui.util_defaults_form.kw_group.kw_entry.get_value()
            if new_kw == '':
                return

            old_val = self.ui.util_defaults_form.kw_group.kw_list_text.get_value().replace(' ', '').split(',')
            if new_kw in old_val:
                return
            old_val.append(new_kw)
            old_val.sort()
            self.ui.util_defaults_form.kw_group.kw_list_text.set_value(', '.join(old_val))

            # update the self.myKeywords so the model is updated
            self.autocomplete_kw_list = \
                self.ui.util_defaults_form.kw_group.kw_list_text.get_value().replace(' ', '').split(',')
            self.myKeywords = self.tcl_commands_list + self.autocomplete_kw_list + self.tcl_keywords
            self.shell._edit.set_model_data(self.myKeywords)

    def del_extension(self, ext_type):
        """
        Remove a file extension from the list for a specific object

        :param ext_type: type of FlatCAM object: excellon, gerber, geometry and then 'not FlatCAM object' keyword
        :return:
        """
        if ext_type == 'excellon':
            new_ext = self.ui.util_defaults_form.fa_excellon_group.ext_entry.get_value()
            if new_ext == '':
                return

            old_val = self.ui.util_defaults_form.fa_excellon_group.exc_list_text.get_value().replace(' ', '').split(',')
            if new_ext not in old_val:
                return
            old_val.remove(new_ext)
            old_val.sort()
            self.ui.util_defaults_form.fa_excellon_group.exc_list_text.set_value(', '.join(old_val))
        if ext_type == 'gcode':
            new_ext = self.ui.util_defaults_form.fa_gcode_group.ext_entry.get_value()
            if new_ext == '':
                return

            old_val = self.ui.util_defaults_form.fa_gcode_group.gco_list_text.get_value().replace(' ', '').split(',')
            if new_ext not in old_val:
                return
            old_val.remove(new_ext)
            old_val.sort()
            self.ui.util_defaults_form.fa_gcode_group.gco_list_text.set_value(', '.join(old_val))
        if ext_type == 'gerber':
            new_ext = self.ui.util_defaults_form.fa_gerber_group.ext_entry.get_value()
            if new_ext == '':
                return

            old_val = self.ui.util_defaults_form.fa_gerber_group.grb_list_text.get_value().replace(' ', '').split(',')
            if new_ext not in old_val:
                return
            old_val.remove(new_ext)
            old_val.sort()
            self.ui.util_defaults_form.fa_gerber_group.grb_list_text.set_value(', '.join(old_val))
        if ext_type == 'keyword':
            new_kw = self.ui.util_defaults_form.kw_group.kw_entry.get_value()
            if new_kw == '':
                return

            old_val = self.ui.util_defaults_form.kw_group.kw_list_text.get_value().replace(' ', '').split(',')
            if new_kw not in old_val:
                return
            old_val.remove(new_kw)
            old_val.sort()
            self.ui.util_defaults_form.kw_group.kw_list_text.set_value(', '.join(old_val))

            # update the self.myKeywords so the model is updated
            self.autocomplete_kw_list = \
                self.ui.util_defaults_form.kw_group.kw_list_text.get_value().replace(' ', '').split(',')
            self.myKeywords = self.tcl_commands_list + self.autocomplete_kw_list + self.tcl_keywords
            self.shell._edit.set_model_data(self.myKeywords)

    def restore_extensions(self, ext_type):
        """
        Restore all file extensions associations with FlatCAM, for a specific object

        :param ext_type: type of FlatCAM object: excellon, gerber, geometry and then 'not FlatCAM object' keyword
        :return:
        """

        if ext_type == 'excellon':
            # don't add 'txt' to the associations (too many files are .txt and not Excellon) but keep it in the list
            # for the ability to open Excellon files with .txt extension
            new_exc_list = deepcopy(self.exc_list)

            try:
                new_exc_list.remove('txt')
            except ValueError:
                pass
            self.ui.util_defaults_form.fa_excellon_group.exc_list_text.set_value(', '.join(new_exc_list))
        if ext_type == 'gcode':
            self.ui.util_defaults_form.fa_gcode_group.gco_list_text.set_value(', '.join(self.gcode_list))
        if ext_type == 'gerber':
            self.ui.util_defaults_form.fa_gerber_group.grb_list_text.set_value(', '.join(self.grb_list))
        if ext_type == 'keyword':
            self.ui.util_defaults_form.kw_group.kw_list_text.set_value(', '.join(self.default_keywords))

            # update the self.myKeywords so the model is updated
            self.autocomplete_kw_list = self.default_keywords
            self.myKeywords = self.tcl_commands_list + self.autocomplete_kw_list + self.tcl_keywords
            self.shell._edit.set_model_data(self.myKeywords)

    def delete_all_extensions(self, ext_type):
        """
        Delete all file extensions associations with FlatCAM, for a specific object

        :param ext_type: type of FlatCAM object: excellon, gerber, geometry and then 'not FlatCAM object' keyword
        :return:
        """

        if ext_type == 'excellon':
            self.ui.util_defaults_form.fa_excellon_group.exc_list_text.set_value('')
        if ext_type == 'gcode':
            self.ui.util_defaults_form.fa_gcode_group.gco_list_text.set_value('')
        if ext_type == 'gerber':
            self.ui.util_defaults_form.fa_gerber_group.grb_list_text.set_value('')
        if ext_type == 'keyword':
            self.ui.util_defaults_form.kw_group.kw_list_text.set_value('')

            # update the self.myKeywords so the model is updated
            self.myKeywords = self.tcl_commands_list + self.tcl_keywords
            self.shell._edit.set_model_data(self.myKeywords)

    def on_edit_join(self, name=None):
        """
        Callback for Edit->Join. Joins the selected geometry objects into
        a new one.

        :return: None
        """
        self.report_usage("on_edit_join()")

        obj_name_single = str(name) if name else "Combo_SingleGeo"
        obj_name_multi = str(name) if name else "Combo_MultiGeo"

        geo_type_set = set()

        objs = self.collection.get_selected()

        if len(objs) < 2:
            self.inform.emit('[ERROR_NOTCL] %s: %d' %
                             (_("At least two objects are required for join. Objects currently selected"), len(objs)))
            return 'fail'

        for obj in objs:
            geo_type_set.add(obj.multigeo)

        # if len(geo_type_list) == 1 means that all list elements are the same
        if len(geo_type_set) != 1:
            self.inform.emit('[ERROR] %s' %
                             _("Failed join. The Geometry objects are of different types.\n"
                               "At least one is MultiGeo type and the other is SingleGeo type. A possibility is to "
                               "convert from one to another and retry joining \n"
                               "but in the case of converting from MultiGeo to SingleGeo, informations may be lost and "
                               "the result may not be what was expected. \n"
                               "Check the generated GCODE."))
            return

        # if at least one True object is in the list then due of the previous check, all list elements are True objects
        if True in geo_type_set:
            def initialize(geo_obj, app):
                FlatCAMGeometry.merge(self, geo_list=objs, geo_final=geo_obj, multigeo=True)
                app.inform.emit('[success] %s.' % _("Multigeo. Geometry merging finished"))

                # rename all the ['name] key in obj.tools[tooluid]['data'] to the obj_name_multi
                for v in obj.tools.values():
                    v['data']['name'] = obj_name_multi
            self.new_object("geometry", obj_name_multi, initialize)
        else:
            def initialize(geo_obj, app):
                FlatCAMGeometry.merge(self, geo_list=objs, geo_final=geo_obj, multigeo=False)
                app.inform.emit('[success] %s.' % _("Geometry merging finished"))

                # rename all the ['name] key in obj.tools[tooluid]['data'] to the obj_name_multi
                for v in obj.tools.values():
                    v['data']['name'] = obj_name_single
            self.new_object("geometry", obj_name_single, initialize)

        self.should_we_save = True

    def on_edit_join_exc(self):
        """
        Callback for Edit->Join Excellon. Joins the selected Excellon objects into
        a new Excellon.

        :return: None
        """
        self.report_usage("on_edit_join_exc()")

        objs = self.collection.get_selected()

        for obj in objs:
            if not isinstance(obj, FlatCAMExcellon):
                self.inform.emit('[ERROR_NOTCL] %s' % _("Failed. Excellon joining works only on Excellon objects."))
                return

        if len(objs) < 2:
            self.inform.emit('[ERROR_NOTCL] %s: %d' %
                             (_("At least two objects are required for join. Objects currently selected"), len(objs)))
            return 'fail'

        def initialize(exc_obj, app):
            FlatCAMExcellon.merge(self, exc_list=objs, exc_final=exc_obj)
            app.inform.emit('[success] %s.' % _("Excellon merging finished"))

        self.new_object("excellon", 'Combo_Excellon', initialize)
        self.should_we_save = True

    def on_edit_join_grb(self):
        """
        Callback for Edit->Join Gerber. Joins the selected Gerber objects into
        a new Gerber object.

        :return: None
        """
        self.report_usage("on_edit_join_grb()")

        objs = self.collection.get_selected()

        for obj in objs:
            if not isinstance(obj, FlatCAMGerber):
                self.inform.emit('[ERROR_NOTCL] %s' % _("Failed. Gerber joining works only on Gerber objects."))
                return

        if len(objs) < 2:
            self.inform.emit('[ERROR_NOTCL] %s: %d' %
                             (_("At least two objects are required for join. Objects currently selected"), len(objs)))
            return 'fail'

        def initialize(grb_obj, app):
            FlatCAMGerber.merge(self, grb_list=objs, grb_final=grb_obj)
            app.inform.emit('[success] %s.' % _("Gerber merging finished"))

        self.new_object("gerber", 'Combo_Gerber', initialize)
        self.should_we_save = True

    def on_convert_singlegeo_to_multigeo(self):
        """
        Called for converting a Geometry object from single-geo to multi-geo.
        Single-geo Geometry objects store their geometry data into self.solid_geometry.
        Multi-geo Geometry objects store their geometry data into the self.tools dictionary, each key (a tool actually)
        having as a value another dictionary. This value dictionary has one of it's keys 'solid_geometry' which holds
        the solid-geometry of that tool.

        :return: None
        """
        self.report_usage("on_convert_singlegeo_to_multigeo()")

        obj = self.collection.get_active()

        if obj is None:
            self.inform.emit('[ERROR_NOTCL] %s' % _("Failed. Select a Geometry Object and try again."))
            return

        if not isinstance(obj, FlatCAMGeometry):
            self.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Expected a FlatCAMGeometry, got"), type(obj)))
            return

        obj.multigeo = True
        for tooluid, dict_value in obj.tools.items():
            dict_value['solid_geometry'] = deepcopy(obj.solid_geometry)
        if not isinstance(obj.solid_geometry, list):
            obj.solid_geometry = [obj.solid_geometry]
        obj.solid_geometry[:] = []
        obj.plot()

        self.should_we_save = True

        self.inform.emit('[success] %s' % _("A Geometry object was converted to MultiGeo type."))

    def on_convert_multigeo_to_singlegeo(self):
        """
        Called for converting a Geometry object from multi-geo to single-geo.
        Single-geo Geometry objects store their geometry data into self.solid_geometry.
        Multi-geo Geometry objects store their geometry data into the self.tools dictionary, each key (a tool actually)
        having as a value another dictionary. This value dictionary has one of it's keys 'solid_geometry' which holds
        the solid-geometry of that tool.

        :return: None
        """
        self.report_usage("on_convert_multigeo_to_singlegeo()")

        obj = self.collection.get_active()

        if obj is None:
            self.inform.emit('[ERROR_NOTCL] %s' %
                             _("Failed. Select a Geometry Object and try again."))
            return

        if not isinstance(obj, FlatCAMGeometry):
            self.inform.emit('[ERROR_NOTCL] %s: %s' %
                             (_("Expected a FlatCAMGeometry, got"), type(obj)))
            return

        obj.multigeo = False
        total_solid_geometry = []
        for tooluid, dict_value in obj.tools.items():
            total_solid_geometry += deepcopy(dict_value['solid_geometry'])
            # clear the original geometry
            dict_value['solid_geometry'][:] = []
        obj.solid_geometry = deepcopy(total_solid_geometry)
        obj.plot()

        self.should_we_save = True

        self.inform.emit('[success] %s' %
                         _("A Geometry object was converted to SingleGeo type."))

    def on_defaults_dict_change(self, field):
        """
        Called whenever a key changed in the self.defaults dictionary. It will set the required GUI element in the
        Edit -> Preferences tab window.

        :param field: the key of the self.defaults dictionary that was changed.
        :return: None
        """
        self.defaults_write_form_field(field)

        if field == "units":
            self.set_screen_units(self.defaults['units'])

    def set_screen_units(self, units):
        """
        Set the FlatCAM units on the status bar.

        :param units: the new measuring units to be displayed in FlatCAM's status bar.
        :return: None
        """
        self.ui.units_label.setText("[" + units.lower() + "]")

    def on_toggle_units(self, no_pref=False):
        """
        Callback for the Units radio-button change in the Preferences tab.
        Changes the application's default units adn for the project too.
        If changing the project's units, the change propagates to all of
        the objects in the project.

        :return: None
        """

        self.report_usage("on_toggle_units")

        if self.toggle_units_ignore:
            return

        new_units = self.ui.general_defaults_form.general_app_group.units_radio.get_value().upper()

        # If option is the same, then ignore
        if new_units == self.defaults["units"].upper():
            self.log.debug("on_toggle_units(): Same as defaults, so ignoring.")
            return

        # Options to scale
        dimensions = ['gerber_isotooldia', 'gerber_noncoppermargin', 'gerber_bboxmargin', "gerber_isooverlap",
                      "gerber_editor_newsize", "gerber_editor_lin_pitch", "gerber_editor_buff_f",

                      'excellon_drillz',  'excellon_travelz', "excellon_toolchangexy",
                      'excellon_feedrate', 'excellon_feedrate_rapid', 'excellon_toolchangez',
                      'excellon_tooldia', 'excellon_slot_tooldia', 'excellon_endz', "excellon_feedrate_probe",
                      "excellon_z_pdepth", "excellon_editor_newdia", "excellon_editor_lin_pitch",
                      "excellon_editor_slot_lin_pitch",

                      'geometry_cutz',  "geometry_depthperpass", 'geometry_travelz', 'geometry_feedrate',
                      'geometry_feedrate_rapid', "geometry_toolchangez", "geometry_feedrate_z",
                      "geometry_toolchangexy", 'geometry_cnctooldia', 'geometry_endz', "geometry_z_pdepth",
                      "geometry_feedrate_probe", "geometry_startz",

                      'cncjob_tooldia',

                      'tools_paintmargin', 'tools_painttooldia', 'tools_paintoverlap',
                      "tools_ncctools", "tools_nccoverlap", "tools_nccmargin", "tools_ncccutz", "tools_ncctipdia",
                      "tools_nccnewdia",
                      "tools_2sided_drilldia", "tools_film_boundary",
                      "tools_cutouttooldia", 'tools_cutoutmargin', 'tools_cutoutgapsize',
                      "tools_panelize_constrainx", "tools_panelize_constrainy",
                      "tools_calc_vshape_tip_dia", "tools_calc_vshape_cut_z",
                      "tools_transform_skew_x", "tools_transform_skew_y", "tools_transform_offset_x",
                      "tools_transform_offset_y",

                      "tools_solderpaste_tools", "tools_solderpaste_new", "tools_solderpaste_z_start",
                      "tools_solderpaste_z_dispense", "tools_solderpaste_z_stop", "tools_solderpaste_z_travel",
                      "tools_solderpaste_z_toolchange", "tools_solderpaste_xy_toolchange", "tools_solderpaste_frxy",
                      "tools_solderpaste_frz", "tools_solderpaste_frz_dispense",
                      "tools_cr_trace_size_val", "tools_cr_c2c_val", "tools_cr_c2o_val", "tools_cr_s2s_val",
                      "tools_cr_s2sm_val", "tools_cr_s2o_val", "tools_cr_sm2sm_val", "tools_cr_ri_val",
                      "tools_cr_h2h_val", "tools_cr_dh_val", "tools_fiducials_dia", "tools_fiducials_margin",
                      "tools_fiducials_mode", "tools_fiducials_second_pos", "tools_fiducials_type",
                      "tools_fiducials_line_thickness",
                      "tools_copper_thieving_clearance", "tools_copper_thieving_margin",
                      "tools_copper_thieving_dots_dia", "tools_copper_thieving_dots_spacing",
                      "tools_copper_thieving_squares_size", "tools_copper_thieving_squares_spacing",
                      "tools_copper_thieving_lines_size", "tools_copper_thieving_lines_spacing",
                      "tools_copper_thieving_rb_margin", "tools_copper_thieving_rb_thickness",
                      'global_gridx', 'global_gridy', 'global_snap_max', "global_tolerance"]

        def scale_defaults(sfactor):
            for dim in dimensions:
                if dim == 'excellon_toolchangexy':
                    coordinates = self.defaults["excellon_toolchangexy"].split(",")
                    coords_xy = [float(eval(a)) for a in coordinates if a != '']
                    coords_xy[0] *= sfactor
                    coords_xy[1] *= sfactor
                    self.defaults['excellon_toolchangexy'] = "%.4f, %.4f" % (coords_xy[0], coords_xy[1])
                elif dim == 'geometry_toolchangexy':
                    coordinates = self.defaults["geometry_toolchangexy"].split(",")
                    coords_xy = [float(eval(a)) for a in coordinates if a != '']
                    coords_xy[0] *= sfactor
                    coords_xy[1] *= sfactor
                    self.defaults['geometry_toolchangexy'] = "%.4f, %.4f" % (coords_xy[0], coords_xy[1])
                elif dim == 'geometry_cnctooldia':
                    tools_diameters = []
                    try:
                        tools_string = self.defaults["geometry_cnctooldia"].split(",")
                        tools_diameters = [eval(a) for a in tools_string if a != '']
                    except Exception as e:
                        log.debug("App.on_toggle_units().scale_options() --> %s" % str(e))

                    self.defaults['geometry_cnctooldia'] = ''
                    for t in range(len(tools_diameters)):
                        tools_diameters[t] *= sfactor
                        self.defaults['geometry_cnctooldia'] += "%.4f," % tools_diameters[t]
                elif dim == 'tools_ncctools':
                    ncctools = []
                    try:
                        tools_string = self.defaults["tools_ncctools"].split(",")
                        ncctools = [eval(a) for a in tools_string if a != '']
                    except Exception as e:
                        log.debug("App.on_toggle_units().scale_options() --> %s" % str(e))

                    self.defaults['tools_ncctools'] = ''
                    for t in range(len(ncctools)):
                        ncctools[t] *= sfactor
                        self.defaults['tools_ncctools'] += "%.4f," % ncctools[t]
                elif dim == 'tools_solderpaste_tools':
                    sptools = []
                    try:
                        tools_string = self.defaults["tools_solderpaste_tools"].split(",")
                        sptools = [eval(a) for a in tools_string if a != '']
                    except Exception as e:
                        log.debug("App.on_toggle_units().scale_options() --> %s" % str(e))

                    self.defaults['tools_solderpaste_tools'] = ""
                    for t in range(len(sptools)):
                        sptools[t] *= sfactor
                        self.defaults['tools_solderpaste_tools'] += "%.4f," % sptools[t]
                elif dim == 'tools_solderpaste_xy_toolchange':
                    coordinates = self.defaults["tools_solderpaste_xy_toolchange"].split(",")
                    sp_coords = [float(eval(a)) for a in coordinates if a != '']
                    sp_coords[0] *= sfactor
                    sp_coords[1] *= sfactor
                    self.defaults['tools_solderpaste_xy_toolchange'] = "%.4f, %.4f" % (sp_coords[0], sp_coords[1])
                elif dim == 'global_gridx' or dim == 'global_gridy':
                    if new_units == 'IN':
                        val = 0.1
                        try:
                            val = float(self.defaults[dim]) * sfactor
                        except Exception as e:
                            log.debug('App.on_toggle_units().scale_defaults() --> %s' % str(e))

                        self.defaults[dim] = float('%.6f' % val)
                    else:
                        val = 0.1
                        try:
                            val = float(self.defaults[dim]) * sfactor
                        except Exception as e:
                            log.debug('App.on_toggle_units().scale_defaults() --> %s' % str(e))

                        self.defaults[dim] = float('%.4f' % val)
                else:
                    val = 0.1
                    if self.defaults[dim]:
                        try:
                            val = float(self.defaults[dim]) * sfactor
                        except Exception as e:
                            log.debug('App.on_toggle_units().scale_defaults() --> %s' % str(e))

                        self.defaults[dim] = val

        # The scaling factor depending on choice of units.
        factor = 1/25.4
        if new_units == 'MM':
            factor = 25.4

        # Changing project units. Warn user.
        msgbox = QtWidgets.QMessageBox()
        msgbox.setWindowTitle(_("Toggle Units"))
        msgbox.setWindowIcon(QtGui.QIcon('share/toggle_units32.png'))
        msgbox.setText("<B>%s</B>" % _("Change project units ..."))
        msgbox.setInformativeText(_("Changing the units of the project causes all geometrical "
                                    "properties of all objects to be scaled accordingly.\nContinue?"))
        bt_ok = msgbox.addButton(_('Ok'), QtWidgets.QMessageBox.AcceptRole)
        msgbox.addButton(_('Cancel'), QtWidgets.QMessageBox.RejectRole)

        msgbox.setDefaultButton(bt_ok)
        msgbox.exec_()
        response = msgbox.clickedButton()

        if response == bt_ok:
            if no_pref is False:
                self.defaults_read_form()
                scale_defaults(factor)
                self.defaults_write_form(fl_units=new_units)

                self.defaults["units"] = new_units

                # save the defaults to file, some may assume that the conversion is enough and it's not
                self.on_save_button(save_to_file=True)

            self.should_we_save = True

            # change this only if the workspace is active
            if self.defaults['global_workspace'] is True:
                self.plotcanvas.draw_workspace(pagesize=self.defaults['global_workspaceT'])

            # adjust the grid values on the main toolbar
            dec = 6 if new_units == 'IN'else 4
            val_x = float(self.ui.grid_gap_x_entry.get_value()) * factor
            self.ui.grid_gap_x_entry.set_value(val_x, decimals=dec)
            if not self.ui.grid_gap_link_cb.isChecked():
                val_y = float(self.ui.grid_gap_y_entry.get_value()) * factor
                self.ui.grid_gap_y_entry.set_value(val_y, decimals=dec)

            for obj in self.collection.get_list():
                obj.convert_units(new_units)

                # make that the properties stored in the object are also updated
                self.object_changed.emit(obj)
                obj.build_ui()

            current = self.collection.get_active()
            if current is not None:
                # the transfer of converted values to the UI form for Geometry is done local in the FlatCAMObj.py
                if not isinstance(current, FlatCAMGeometry):
                    current.to_form()

            self.plot_all()
            self.inform.emit('[success] %s: %s' %
                             (_("Converted units to"), new_units))
            # self.ui.units_label.setText("[" + self.options["units"] + "]")
            self.set_screen_units(new_units)
        else:
            # Undo toggling
            self.toggle_units_ignore = True
            if self.defaults['units'].upper() == 'MM':
                self.ui.general_defaults_form.general_app_group.units_radio.set_value('IN')
            else:
                self.ui.general_defaults_form.general_app_group.units_radio.set_value('MM')
            self.toggle_units_ignore = False
            self.inform.emit('[WARNING_NOTCL]%s' %
                             _(" Units conversion cancelled."))

        self.defaults_read_form()

    def on_toggle_units_click(self):
        try:
            self.ui.general_defaults_form.general_app_group.units_radio.activated_custom.disconnect()
        except (TypeError, AttributeError):
            pass

        if self.defaults["units"] == 'MM':
            self.ui.general_defaults_form.general_app_group.units_radio.set_value("IN")
        else:
            self.ui.general_defaults_form.general_app_group.units_radio.set_value("MM")

        self.on_toggle_units(no_pref=True)

        self.ui.general_defaults_form.general_app_group.units_radio.activated_custom.connect(
            lambda: self.on_toggle_units(no_pref=False))

    def on_fullscreen(self, disable=False):
        self.report_usage("on_fullscreen()")

        if self.toggle_fscreen is False and disable is False:
            # self.ui.showFullScreen()
            self.ui.setWindowFlags(self.ui.windowFlags() | Qt.FramelessWindowHint)
            a = self.ui.geometry()
            self.x_pos = a.x()
            self.y_pos = a.y()
            self.width = a.width()
            self.height = a.height()

            # set new geometry to full desktop rect
            # Subtracting and adding the pixels below it's hack to bypass a bug in Qt5 and OpenGL that made that a
            # window drawn with OpenGL in fullscreen will not show any other windows on top which means that menus and
            # everything else will not work without this hack. This happen in Windows.
            # https://bugreports.qt.io/browse/QTBUG-41309
            desktop = QtWidgets.QApplication.desktop()
            screen = desktop.screenNumber(QtGui.QCursor.pos())

            rec = desktop.screenGeometry(screen)
            x = rec.x() - 1
            y = rec.y() - 1
            h = rec.height() + 2
            w = rec.width() + 2
            self.ui.setGeometry(x, y, w, h)
            self.ui.show()

            for tb in self.ui.findChildren(QtWidgets.QToolBar):
                tb.setVisible(False)
            self.ui.splitter_left.setVisible(False)
            self.toggle_fscreen = True
        elif self.toggle_fscreen is True or disable is True:
            self.ui.setWindowFlags(self.ui.windowFlags() & ~Qt.FramelessWindowHint)
            self.ui.setGeometry(self.x_pos, self.y_pos, self.width, self.height)
            self.ui.showNormal()
            self.restore_toolbar_view()
            self.ui.splitter_left.setVisible(True)
            self.toggle_fscreen = False

    def on_toggle_plotarea(self):
        self.report_usage("on_toggle_plotarea()")

        try:
            name = self.ui.plot_tab_area.widget(0).objectName()
        except AttributeError:
            self.ui.plot_tab_area.addTab(self.ui.plot_tab, "Plot Area")
            # remove the close button from the Plot Area tab (first tab index = 0) as this one will always be ON
            self.ui.plot_tab_area.protectTab(0)
            return

        if name != 'plotarea':
            self.ui.plot_tab_area.insertTab(0, self.ui.plot_tab, "Plot Area")
            # remove the close button from the Plot Area tab (first tab index = 0) as this one will always be ON
            self.ui.plot_tab_area.protectTab(0)
        else:
            self.ui.plot_tab_area.closeTab(0)

    def on_toggle_notebook(self):
        if self.ui.splitter.sizes()[0] == 0:
            self.ui.splitter.setSizes([1, 1])
            self.ui.menu_toggle_nb.setChecked(True)
        else:
            self.ui.splitter.setSizes([0, 1])
            self.ui.menu_toggle_nb.setChecked(False)

    def on_toggle_axis(self):
        self.report_usage("on_toggle_axis()")

        if self.toggle_axis is False:
            if self.is_legacy is False:
                self.plotcanvas.v_line = InfiniteLine(pos=0, color=(0.70, 0.3, 0.3, 1.0), vertical=True,
                                                      parent=self.plotcanvas.view.scene)

                self.plotcanvas.h_line = InfiniteLine(pos=0, color=(0.70, 0.3, 0.3, 1.0), vertical=False,
                                                      parent=self.plotcanvas.view.scene)
            else:
                if self.plotcanvas.h_line not in self.plotcanvas.axes.lines and \
                        self.plotcanvas.v_line not in self.plotcanvas.axes.lines:
                    self.plotcanvas.h_line = self.plotcanvas.axes.axhline(color=(0.70, 0.3, 0.3), linewidth=2)
                    self.plotcanvas.v_line = self.plotcanvas.axes.axvline(color=(0.70, 0.3, 0.3), linewidth=2)
                    self.plotcanvas.canvas.draw()

            self.toggle_axis = True
        else:
            if self.is_legacy is False:
                self.plotcanvas.v_line.parent = None
                self.plotcanvas.h_line.parent = None
            else:
                if self.plotcanvas.h_line in self.plotcanvas.axes.lines and \
                        self.plotcanvas.v_line in self.plotcanvas.axes.lines:
                    self.plotcanvas.axes.lines.remove(self.plotcanvas.h_line)
                    self.plotcanvas.axes.lines.remove(self.plotcanvas.v_line)
                    self.plotcanvas.canvas.draw()
            self.toggle_axis = False

    def on_toggle_grid(self):
        self.report_usage("on_toggle_grid()")

        self.ui.grid_snap_btn.trigger()

    def on_toggle_grid_lines(self):
        self.report_usage("on_toggle_grd_lines()")

        tt_settings = QtCore.QSettings("Open Source", "FlatCAM")
        if tt_settings.contains("theme"):
            theme = tt_settings.value('theme', type=str)
        else:
            theme = 'white'

        if self.toggle_grid_lines is False:
            if self.is_legacy is False:
                if theme == 'white':
                    self.plotcanvas.grid._grid_color_fn['color'] = Color('dimgray').rgba
                else:
                    self.plotcanvas.grid._grid_color_fn['color'] = Color('#dededeff').rgba
            else:
                self.plotcanvas.axes.grid(True)
                try:
                    self.plotcanvas.canvas.draw()
                except IndexError:
                    pass
                pass
            self.toggle_grid_lines = True
        else:
            if self.is_legacy is False:
                if theme == 'white':
                    self.plotcanvas.grid._grid_color_fn['color'] = Color('#ffffffff').rgba
                else:
                    self.plotcanvas.grid._grid_color_fn['color'] = Color('#000000FF').rgba
            else:
                self.plotcanvas.axes.grid(False)
                try:
                    self.plotcanvas.canvas.draw()
                except IndexError:
                    pass
            self.toggle_grid_lines = False

        if self.is_legacy is False:
            # HACK: enabling/disabling the cursor seams to somehow update the shapes on screen
            # - perhaps is a bug in VisPy implementation
            if self.grid_status() is True:
                self.app_cursor.enabled = False
                self.app_cursor.enabled = True
            else:
                self.app_cursor.enabled = True
                self.app_cursor.enabled = False

    def show_preferences_gui(self):
        """
        Called to initialize and show the Preferences GUI

        :return: None
        """

        self.gen_form = self.ui.general_defaults_form
        self.ger_form = self.ui.gerber_defaults_form
        self.exc_form = self.ui.excellon_defaults_form
        self.geo_form = self.ui.geometry_defaults_form
        self.cnc_form = self.ui.cncjob_defaults_form
        self.tools_form = self.ui.tools_defaults_form
        self.tools2_form = self.ui.tools2_defaults_form
        self.fa_form = self.ui.util_defaults_form

        try:
            self.ui.general_scroll_area.takeWidget()
        except Exception:
            self.log.debug("Nothing to remove")
        self.ui.general_scroll_area.setWidget(self.gen_form)
        self.gen_form.show()

        try:
            self.ui.gerber_scroll_area.takeWidget()
        except Exception:
            self.log.debug("Nothing to remove")
        self.ui.gerber_scroll_area.setWidget(self.ger_form)
        self.ger_form.show()

        try:
            self.ui.excellon_scroll_area.takeWidget()
        except Exception:
            self.log.debug("Nothing to remove")
        self.ui.excellon_scroll_area.setWidget(self.exc_form)
        self.exc_form.show()

        try:
            self.ui.geometry_scroll_area.takeWidget()
        except Exception:
            self.log.debug("Nothing to remove")
        self.ui.geometry_scroll_area.setWidget(self.geo_form)
        self.geo_form.show()

        try:
            self.ui.cncjob_scroll_area.takeWidget()
        except Exception:
            self.log.debug("Nothing to remove")
        self.ui.cncjob_scroll_area.setWidget(self.cnc_form)
        self.cnc_form.show()

        try:
            self.ui.tools_scroll_area.takeWidget()
        except Exception:
            self.log.debug("Nothing to remove")
        self.ui.tools_scroll_area.setWidget(self.tools_form)
        self.tools_form.show()

        try:
            self.ui.tools2_scroll_area.takeWidget()
        except Exception:
            self.log.debug("Nothing to remove")
        self.ui.tools2_scroll_area.setWidget(self.tools2_form)
        self.tools2_form.show()

        try:
            self.ui.fa_scroll_area.takeWidget()
        except Exception:
            self.log.debug("Nothing to remove")
        self.ui.fa_scroll_area.setWidget(self.fa_form)
        self.fa_form.show()

        self.log.debug("Finished Preferences GUI form initialization.")

        # self.options2form()

    def init_color_pickers_in_preferences_gui(self):
        # Init Plot Colors
        self.ui.general_defaults_form.general_gui_group.pf_color_entry.set_value(self.defaults['global_plot_fill'])
        self.ui.general_defaults_form.general_gui_group.pf_color_button.setStyleSheet(
            "background-color:%s;"
            "border-color: dimgray" % str(self.defaults['global_plot_fill'])[:7])
        self.ui.general_defaults_form.general_gui_group.pf_color_alpha_spinner.set_value(
            int(self.defaults['global_plot_fill'][7:9], 16))
        self.ui.general_defaults_form.general_gui_group.pf_color_alpha_slider.setValue(
            int(self.defaults['global_plot_fill'][7:9], 16))

        self.ui.general_defaults_form.general_gui_group.pl_color_entry.set_value(self.defaults['global_plot_line'])
        self.ui.general_defaults_form.general_gui_group.pl_color_button.setStyleSheet(
            "background-color:%s;"
            "border-color: dimgray" % str(self.defaults['global_plot_line'])[:7])

        # Init Left-Right Selection colors
        self.ui.general_defaults_form.general_gui_group.sf_color_entry.set_value(self.defaults['global_sel_fill'])
        self.ui.general_defaults_form.general_gui_group.sf_color_button.setStyleSheet(
            "background-color:%s;"
            "border-color: dimgray" % str(self.defaults['global_sel_fill'])[:7])
        self.ui.general_defaults_form.general_gui_group.sf_color_alpha_spinner.set_value(
            int(self.defaults['global_sel_fill'][7:9], 16))
        self.ui.general_defaults_form.general_gui_group.sf_color_alpha_slider.setValue(
            int(self.defaults['global_sel_fill'][7:9], 16))

        self.ui.general_defaults_form.general_gui_group.sl_color_entry.set_value(self.defaults['global_sel_line'])
        self.ui.general_defaults_form.general_gui_group.sl_color_button.setStyleSheet(
            "background-color:%s;"
            "border-color: dimgray" % str(self.defaults['global_sel_line'])[:7])

        # Init Right-Left Selection colors
        self.ui.general_defaults_form.general_gui_group.alt_sf_color_entry.set_value(
            self.defaults['global_alt_sel_fill'])
        self.ui.general_defaults_form.general_gui_group.alt_sf_color_button.setStyleSheet(
            "background-color:%s;"
            "border-color: dimgray" % str(self.defaults['global_alt_sel_fill'])[:7])
        self.ui.general_defaults_form.general_gui_group.alt_sf_color_alpha_spinner.set_value(
            int(self.defaults['global_sel_fill'][7:9], 16))
        self.ui.general_defaults_form.general_gui_group.alt_sf_color_alpha_slider.setValue(
            int(self.defaults['global_sel_fill'][7:9], 16))

        self.ui.general_defaults_form.general_gui_group.alt_sl_color_entry.set_value(
            self.defaults['global_alt_sel_line'])
        self.ui.general_defaults_form.general_gui_group.alt_sl_color_button.setStyleSheet(
            "background-color:%s;"
            "border-color: dimgray" % str(self.defaults['global_alt_sel_line'])[:7])

        # Init Draw color and Selection Draw Color
        self.ui.general_defaults_form.general_gui_group.draw_color_entry.set_value(
            self.defaults['global_draw_color'])
        self.ui.general_defaults_form.general_gui_group.draw_color_button.setStyleSheet(
            "background-color:%s;"
            "border-color: dimgray" % str(self.defaults['global_draw_color'])[:7])

        self.ui.general_defaults_form.general_gui_group.sel_draw_color_entry.set_value(
            self.defaults['global_sel_draw_color'])
        self.ui.general_defaults_form.general_gui_group.sel_draw_color_button.setStyleSheet(
            "background-color:%s;"
            "border-color: dimgray" % str(self.defaults['global_sel_draw_color'])[:7])

        # Init Project Items color
        self.ui.general_defaults_form.general_gui_group.proj_color_entry.set_value(
            self.defaults['global_proj_item_color'])
        self.ui.general_defaults_form.general_gui_group.proj_color_button.setStyleSheet(
            "background-color:%s;"
            "border-color: dimgray" % str(self.defaults['global_proj_item_color'])[:7])

        self.ui.general_defaults_form.general_gui_group.proj_color_dis_entry.set_value(
            self.defaults['global_proj_item_dis_color'])
        self.ui.general_defaults_form.general_gui_group.proj_color_dis_button.setStyleSheet(
            "background-color:%s;"
            "border-color: dimgray" % str(self.defaults['global_proj_item_dis_color'])[:7])

        # Init the Annotation CNC Job color
        self.ui.cncjob_defaults_form.cncjob_adv_opt_group.annotation_fontcolor_entry.set_value(
            self.defaults['cncjob_annotation_fontcolor'])
        self.ui.cncjob_defaults_form.cncjob_adv_opt_group.annotation_fontcolor_button.setStyleSheet(
            "background-color:%s;"
            "border-color: dimgray" % str(self.defaults['cncjob_annotation_fontcolor'])[:7])

        # Init the Tool Film color
        self.ui.tools_defaults_form.tools_film_group.film_color_entry.set_value(
            self.defaults['tools_film_color'])
        self.ui.tools_defaults_form.tools_film_group.film_color_button.setStyleSheet(
            "background-color:%s;"
            "border-color: dimgray" % str(self.defaults['tools_film_color'])[:7]
        )

        # Init the Tool QRCode colors
        self.ui.tools2_defaults_form.tools2_qrcode_group.fill_color_entry.set_value(
            self.defaults['tools_qrcode_fill_color'])
        self.ui.tools2_defaults_form.tools2_qrcode_group.fill_color_button.setStyleSheet(
            "background-color:%s;"
            "border-color: dimgray" % str(self.defaults['tools_qrcode_fill_color'])[:7])

        self.ui.tools2_defaults_form.tools2_qrcode_group.back_color_entry.set_value(
            self.defaults['tools_qrcode_back_color'])
        self.ui.tools2_defaults_form.tools2_qrcode_group.back_color_button.setStyleSheet(
            "background-color:%s;"
            "border-color: dimgray" % str(self.defaults['tools_qrcode_back_color'])[:7])

    def on_excellon_defaults_button(self):
        self.defaults_form_fields["excellon_format_lower_in"].set_value('4')
        self.defaults_form_fields["excellon_format_upper_in"].set_value('2')
        self.defaults_form_fields["excellon_format_lower_mm"].set_value('3')
        self.defaults_form_fields["excellon_format_upper_mm"].set_value('3')
        self.defaults_form_fields["excellon_zeros"].set_value('L')
        self.defaults_form_fields["excellon_units"].set_value('INCH')
        log.debug("Excellon app defaults loaded ...")

    def on_update_exc_export(self, state):
        """
        This is handling the update of Excellon Export parameters based on the ones in the Excellon General but only
        if the update_excellon_cb checkbox is checked

        :param state: state of the checkbox whose signals is tied to his slot
        :return:
        """
        if state:
            # first try to disconnect
            try:
                self.ui.excellon_defaults_form.excellon_gen_group.excellon_format_upper_in_entry.returnPressed.\
                    disconnect(self.on_excellon_format_changed)
            except TypeError:
                pass
            try:
                self.ui.excellon_defaults_form.excellon_gen_group.excellon_format_lower_in_entry.returnPressed.\
                    disconnect(self.on_excellon_format_changed)
            except TypeError:
                pass
            try:
                self.ui.excellon_defaults_form.excellon_gen_group.excellon_format_upper_mm_entry.returnPressed.\
                    disconnect(self.on_excellon_format_changed)
            except TypeError:
                pass
            try:
                self.ui.excellon_defaults_form.excellon_gen_group.excellon_format_lower_mm_entry.returnPressed.\
                    disconnect(self.on_excellon_format_changed)
            except TypeError:
                pass

            try:
                self.ui.excellon_defaults_form.excellon_gen_group.excellon_zeros_radio.activated_custom.\
                    disconnect(self.on_excellon_zeros_changed)
            except TypeError:
                pass
            try:
                self.ui.excellon_defaults_form.excellon_gen_group.excellon_units_radio.activated_custom.\
                    disconnect(self.on_excellon_zeros_changed)
            except TypeError:
                pass

            # the connect them
            self.ui.excellon_defaults_form.excellon_gen_group.excellon_format_upper_in_entry.returnPressed.connect(
                self.on_excellon_format_changed)
            self.ui.excellon_defaults_form.excellon_gen_group.excellon_format_lower_in_entry.returnPressed.connect(
                self.on_excellon_format_changed)
            self.ui.excellon_defaults_form.excellon_gen_group.excellon_format_upper_mm_entry.returnPressed.connect(
                self.on_excellon_format_changed)
            self.ui.excellon_defaults_form.excellon_gen_group.excellon_format_lower_mm_entry.returnPressed.connect(
                self.on_excellon_format_changed)
            self.ui.excellon_defaults_form.excellon_gen_group.excellon_zeros_radio.activated_custom.connect(
                self.on_excellon_zeros_changed)
            self.ui.excellon_defaults_form.excellon_gen_group.excellon_units_radio.activated_custom.connect(
                self.on_excellon_units_changed)
        else:
            # disconnect the signals
            try:
                self.ui.excellon_defaults_form.excellon_gen_group.excellon_format_upper_in_entry.returnPressed. \
                    disconnect(self.on_excellon_format_changed)
            except TypeError:
                pass
            try:
                self.ui.excellon_defaults_form.excellon_gen_group.excellon_format_lower_in_entry.returnPressed. \
                    disconnect(self.on_excellon_format_changed)
            except TypeError:
                pass
            try:
                self.ui.excellon_defaults_form.excellon_gen_group.excellon_format_upper_mm_entry.returnPressed. \
                    disconnect(self.on_excellon_format_changed)
            except TypeError:
                pass
            try:
                self.ui.excellon_defaults_form.excellon_gen_group.excellon_format_lower_mm_entry.returnPressed. \
                    disconnect(self.on_excellon_format_changed)
            except TypeError:
                pass

            try:
                self.ui.excellon_defaults_form.excellon_gen_group.excellon_zeros_radio.activated_custom. \
                    disconnect(self.on_excellon_zeros_changed)
            except TypeError:
                pass
            try:
                self.ui.excellon_defaults_form.excellon_gen_group.excellon_units_radio.activated_custom. \
                    disconnect(self.on_excellon_zeros_changed)
            except TypeError:
                pass

    def on_excellon_format_changed(self):
        """
        Slot activated when the user changes the Excellon format values in Preferences -> Excellon -> Excellon General
        :return: None
        """
        if self.ui.excellon_defaults_form.excellon_gen_group.excellon_units_radio.get_value().upper() == 'METRIC':
            self.ui.excellon_defaults_form.excellon_exp_group.format_whole_entry.set_value(
                self.ui.excellon_defaults_form.excellon_gen_group.excellon_format_upper_mm_entry.get_value()
            )
            self.ui.excellon_defaults_form.excellon_exp_group.format_dec_entry.set_value(
                self.ui.excellon_defaults_form.excellon_gen_group.excellon_format_lower_mm_entry.get_value()
            )
        else:
            self.ui.excellon_defaults_form.excellon_exp_group.format_whole_entry.set_value(
                self.ui.excellon_defaults_form.excellon_gen_group.excellon_format_upper_in_entry.get_value()
            )
            self.ui.excellon_defaults_form.excellon_exp_group.format_dec_entry.set_value(
                self.ui.excellon_defaults_form.excellon_gen_group.excellon_format_lower_in_entry.get_value()
            )

    def on_excellon_zeros_changed(self):
        """
        Slot activated when the user changes the Excellon zeros values in Preferences -> Excellon -> Excellon General
        :return: None
        """
        self.ui.excellon_defaults_form.excellon_exp_group.zeros_radio.set_value(
            self.ui.excellon_defaults_form.excellon_gen_group.excellon_zeros_radio.get_value() + 'Z'
        )

    def on_excellon_units_changed(self):
        """
        Slot activated when the user changes the Excellon unit values in Preferences -> Excellon -> Excellon General
        :return: None
        """
        self.ui.excellon_defaults_form.excellon_exp_group.excellon_units_radio.set_value(
            self.ui.excellon_defaults_form.excellon_gen_group.excellon_units_radio.get_value()
        )
        self.on_excellon_format_changed()

    # Setting plot colors handlers
    def on_pf_color_entry(self):
        self.defaults['global_plot_fill'] = \
            self.ui.general_defaults_form.general_gui_group.pf_color_entry.get_value()[:7] + \
            self.defaults['global_plot_fill'][7:9]
        self.ui.general_defaults_form.general_gui_group.pf_color_button.setStyleSheet(
            "background-color:%s" % str(self.defaults['global_plot_fill'])[:7])

    def on_pf_color_button(self):
        current_color = QtGui.QColor(self.defaults['global_plot_fill'][:7])

        c_dialog = QtWidgets.QColorDialog()
        plot_fill_color = c_dialog.getColor(initial=current_color)

        if plot_fill_color.isValid() is False:
            return

        self.ui.general_defaults_form.general_gui_group.pf_color_button.setStyleSheet(
            "background-color:%s" % str(plot_fill_color.name()))

        new_val = str(plot_fill_color.name()) + str(self.defaults['global_plot_fill'][7:9])
        self.ui.general_defaults_form.general_gui_group.pf_color_entry.set_value(new_val)
        self.defaults['global_plot_fill'] = new_val

    def on_pf_color_spinner(self):
        spinner_value = self.ui.general_defaults_form.general_gui_group.pf_color_alpha_spinner.value()
        self.ui.general_defaults_form.general_gui_group.pf_color_alpha_slider.setValue(spinner_value)
        self.defaults['global_plot_fill'] = \
            self.defaults['global_plot_fill'][:7] + \
            (hex(spinner_value)[2:] if int(hex(spinner_value)[2:], 16) > 0 else '00')
        self.defaults['global_plot_line'] = \
            self.defaults['global_plot_line'][:7] + \
            (hex(spinner_value)[2:] if int(hex(spinner_value)[2:], 16) > 0 else '00')

    def on_pf_color_slider(self):
        slider_value = self.ui.general_defaults_form.general_gui_group.pf_color_alpha_slider.value()
        self.ui.general_defaults_form.general_gui_group.pf_color_alpha_spinner.setValue(slider_value)

    def on_pl_color_entry(self):
        self.defaults['global_plot_line'] = \
            self.ui.general_defaults_form.general_gui_group.pl_color_entry.get_value()[:7] + \
            self.defaults['global_plot_line'][7:9]
        self.ui.general_defaults_form.general_gui_group.pl_color_button.setStyleSheet(
            "background-color:%s" % str(self.defaults['global_plot_line'])[:7])

    def on_pl_color_button(self):
        current_color = QtGui.QColor(self.defaults['global_plot_line'][:7])
        # print(current_color)

        c_dialog = QtWidgets.QColorDialog()
        plot_line_color = c_dialog.getColor(initial=current_color)

        if plot_line_color.isValid() is False:
            return

        self.ui.general_defaults_form.general_gui_group.pl_color_button.setStyleSheet(
            "background-color:%s" % str(plot_line_color.name()))

        new_val_line = str(plot_line_color.name()) + str(self.defaults['global_plot_line'][7:9])
        self.ui.general_defaults_form.general_gui_group.pl_color_entry.set_value(new_val_line)
        self.defaults['global_plot_line'] = new_val_line

    # Setting selection colors (left - right) handlers
    def on_sf_color_entry(self):
        self.defaults['global_sel_fill'] = \
            self.ui.general_defaults_form.general_gui_group.sf_color_entry.get_value()[:7] + \
            self.defaults['global_sel_fill'][7:9]
        self.ui.general_defaults_form.general_gui_group.sf_color_button.setStyleSheet(
            "background-color:%s" % str(self.defaults['global_sel_fill'])[:7])

    def on_sf_color_button(self):
        current_color = QtGui.QColor(self.defaults['global_sel_fill'][:7])

        c_dialog = QtWidgets.QColorDialog()
        plot_fill_color = c_dialog.getColor(initial=current_color)

        if plot_fill_color.isValid() is False:
            return

        self.ui.general_defaults_form.general_gui_group.sf_color_button.setStyleSheet(
            "background-color:%s" % str(plot_fill_color.name()))

        new_val = str(plot_fill_color.name()) + str(self.defaults['global_sel_fill'][7:9])
        self.ui.general_defaults_form.general_gui_group.sf_color_entry.set_value(new_val)
        self.defaults['global_sel_fill'] = new_val

    def on_sf_color_spinner(self):
        spinner_value = self.ui.general_defaults_form.general_gui_group.sf_color_alpha_spinner.value()
        self.ui.general_defaults_form.general_gui_group.sf_color_alpha_slider.setValue(spinner_value)
        self.defaults['global_sel_fill'] = \
            self.defaults['global_sel_fill'][:7] + \
            (hex(spinner_value)[2:] if int(hex(spinner_value)[2:], 16) > 0 else '00')
        self.defaults['global_sel_line'] = \
            self.defaults['global_sel_line'][:7] + \
            (hex(spinner_value)[2:] if int(hex(spinner_value)[2:], 16) > 0 else '00')

    def on_sf_color_slider(self):
        slider_value = self.ui.general_defaults_form.general_gui_group.sf_color_alpha_slider.value()
        self.ui.general_defaults_form.general_gui_group.sf_color_alpha_spinner.setValue(slider_value)

    def on_sl_color_entry(self):
        self.defaults['global_sel_line'] = \
            self.ui.general_defaults_form.general_gui_group.sl_color_entry.get_value()[:7] + \
            self.defaults['global_sel_line'][7:9]
        self.ui.general_defaults_form.general_gui_group.sl_color_button.setStyleSheet(
            "background-color:%s" % str(self.defaults['global_sel_line'])[:7])

    def on_sl_color_button(self):
        current_color = QtGui.QColor(self.defaults['global_sel_line'][:7])

        c_dialog = QtWidgets.QColorDialog()
        plot_line_color = c_dialog.getColor(initial=current_color)

        if plot_line_color.isValid() is False:
            return

        self.ui.general_defaults_form.general_gui_group.sl_color_button.setStyleSheet(
            "background-color:%s" % str(plot_line_color.name()))

        new_val_line = str(plot_line_color.name()) + str(self.defaults['global_sel_line'][7:9])
        self.ui.general_defaults_form.general_gui_group.sl_color_entry.set_value(new_val_line)
        self.defaults['global_sel_line'] = new_val_line

    # Setting selection colors (right - left) handlers
    def on_alt_sf_color_entry(self):
        self.defaults['global_alt_sel_fill'] = self.ui.general_defaults_form.general_gui_group \
                                   .alt_sf_color_entry.get_value()[:7] + self.defaults['global_alt_sel_fill'][7:9]
        self.ui.general_defaults_form.general_gui_group.alt_sf_color_button.setStyleSheet(
            "background-color:%s" % str(self.defaults['global_alt_sel_fill'])[:7])

    def on_alt_sf_color_button(self):
        current_color = QtGui.QColor(self.defaults['global_alt_sel_fill'][:7])

        c_dialog = QtWidgets.QColorDialog()
        plot_fill_color = c_dialog.getColor(initial=current_color)

        if plot_fill_color.isValid() is False:
            return

        self.ui.general_defaults_form.general_gui_group.alt_sf_color_button.setStyleSheet(
            "background-color:%s" % str(plot_fill_color.name()))

        new_val = str(plot_fill_color.name()) + str(self.defaults['global_alt_sel_fill'][7:9])
        self.ui.general_defaults_form.general_gui_group.alt_sf_color_entry.set_value(new_val)
        self.defaults['global_alt_sel_fill'] = new_val

    def on_alt_sf_color_spinner(self):
        spinner_value = self.ui.general_defaults_form.general_gui_group.alt_sf_color_alpha_spinner.value()
        self.ui.general_defaults_form.general_gui_group.alt_sf_color_alpha_slider.setValue(spinner_value)
        self.defaults['global_alt_sel_fill'] = \
            self.defaults['global_alt_sel_fill'][:7] + \
            (hex(spinner_value)[2:] if int(hex(spinner_value)[2:], 16) > 0 else '00')
        self.defaults['global_alt_sel_line'] = \
            self.defaults['global_alt_sel_line'][:7] + \
            (hex(spinner_value)[2:] if int(hex(spinner_value)[2:], 16) > 0 else '00')

    def on_alt_sf_color_slider(self):
        slider_value = self.ui.general_defaults_form.general_gui_group.alt_sf_color_alpha_slider.value()
        self.ui.general_defaults_form.general_gui_group.alt_sf_color_alpha_spinner.setValue(slider_value)

    def on_alt_sl_color_entry(self):
        self.defaults['global_alt_sel_line'] = \
            self.ui.general_defaults_form.general_gui_group.alt_sl_color_entry.get_value()[:7] + \
            self.defaults['global_alt_sel_line'][7:9]
        self.ui.general_defaults_form.general_gui_group.alt_sl_color_button.setStyleSheet(
            "background-color:%s" % str(self.defaults['global_alt_sel_line'])[:7])

    def on_alt_sl_color_button(self):
        current_color = QtGui.QColor(self.defaults['global_alt_sel_line'][:7])

        c_dialog = QtWidgets.QColorDialog()
        plot_line_color = c_dialog.getColor(initial=current_color)

        if plot_line_color.isValid() is False:
            return

        self.ui.general_defaults_form.general_gui_group.alt_sl_color_button.setStyleSheet(
            "background-color:%s" % str(plot_line_color.name()))

        new_val_line = str(plot_line_color.name()) + str(self.defaults['global_alt_sel_line'][7:9])
        self.ui.general_defaults_form.general_gui_group.alt_sl_color_entry.set_value(new_val_line)
        self.defaults['global_alt_sel_line'] = new_val_line

    # Setting Editor colors
    def on_draw_color_entry(self):
        self.defaults['global_draw_color'] = self.ui.general_defaults_form.general_gui_group \
                                                   .draw_color_entry.get_value()
        self.ui.general_defaults_form.general_gui_group.draw_color_button.setStyleSheet(
            "background-color:%s" % str(self.defaults['global_draw_color']))

    def on_draw_color_button(self):
        current_color = QtGui.QColor(self.defaults['global_draw_color'])

        c_dialog = QtWidgets.QColorDialog()
        draw_color = c_dialog.getColor(initial=current_color)

        if draw_color.isValid() is False:
            return

        self.ui.general_defaults_form.general_gui_group.draw_color_button.setStyleSheet(
            "background-color:%s" % str(draw_color.name()))

        new_val = str(draw_color.name())
        self.ui.general_defaults_form.general_gui_group.draw_color_entry.set_value(new_val)
        self.defaults['global_draw_color'] = new_val

    def on_sel_draw_color_entry(self):
        self.defaults['global_sel_draw_color'] = self.ui.general_defaults_form.general_gui_group \
                                                   .sel_draw_color_entry.get_value()
        self.ui.general_defaults_form.general_gui_group.sel_draw_color_button.setStyleSheet(
            "background-color:%s" % str(self.defaults['global_sel_draw_color']))

    def on_sel_draw_color_button(self):
        current_color = QtGui.QColor(self.defaults['global_sel_draw_color'])

        c_dialog = QtWidgets.QColorDialog()
        sel_draw_color = c_dialog.getColor(initial=current_color)

        if sel_draw_color.isValid() is False:
            return

        self.ui.general_defaults_form.general_gui_group.sel_draw_color_button.setStyleSheet(
            "background-color:%s" % str(sel_draw_color.name()))

        new_val_sel = str(sel_draw_color.name())
        self.ui.general_defaults_form.general_gui_group.sel_draw_color_entry.set_value(new_val_sel)
        self.defaults['global_sel_draw_color'] = new_val_sel

    def on_proj_color_entry(self):
        self.defaults['global_proj_item_color'] = self.ui.general_defaults_form.general_gui_group \
                                                   .proj_color_entry.get_value()
        self.ui.general_defaults_form.general_gui_group.proj_color_button.setStyleSheet(
            "background-color:%s" % str(self.defaults['global_proj_item_color']))

    def on_proj_color_button(self):
        current_color = QtGui.QColor(self.defaults['global_proj_item_color'])

        c_dialog = QtWidgets.QColorDialog()
        proj_color = c_dialog.getColor(initial=current_color)

        if proj_color.isValid() is False:
            return

        self.ui.general_defaults_form.general_gui_group.proj_color_button.setStyleSheet(
            "background-color:%s" % str(proj_color.name()))

        new_val_sel = str(proj_color.name())
        self.ui.general_defaults_form.general_gui_group.proj_color_entry.set_value(new_val_sel)
        self.defaults['global_proj_item_color'] = new_val_sel

    def on_proj_color_dis_entry(self):
        self.defaults['global_proj_item_dis_color'] = self.ui.general_defaults_form.general_gui_group \
                                                   .proj_color_dis_entry.get_value()
        self.ui.general_defaults_form.general_gui_group.proj_color_dis_button.setStyleSheet(
            "background-color:%s" % str(self.defaults['global_proj_item_dis_color']))

    def on_proj_color_dis_button(self):
        current_color = QtGui.QColor(self.defaults['global_proj_item_dis_color'])

        c_dialog = QtWidgets.QColorDialog()
        proj_color = c_dialog.getColor(initial=current_color)

        if proj_color.isValid() is False:
            return

        self.ui.general_defaults_form.general_gui_group.proj_color_dis_button.setStyleSheet(
            "background-color:%s" % str(proj_color.name()))

        new_val_sel = str(proj_color.name())
        self.ui.general_defaults_form.general_gui_group.proj_color_dis_entry.set_value(new_val_sel)
        self.defaults['global_proj_item_dis_color'] = new_val_sel

    def on_annotation_fontcolor_entry(self):
        self.defaults['cncjob_annotation_fontcolor'] = \
            self.ui.cncjob_defaults_form.cncjob_adv_opt_group.annotation_fontcolor_entry.get_value()
        self.ui.cncjob_defaults_form.cncjob_adv_opt_group.annotation_fontcolor_button.setStyleSheet(
            "background-color:%s" % str(self.defaults['cncjob_annotation_fontcolor']))

    def on_annotation_fontcolor_button(self):
        current_color = QtGui.QColor(self.defaults['cncjob_annotation_fontcolor'])

        c_dialog = QtWidgets.QColorDialog()
        annotation_color = c_dialog.getColor(initial=current_color)

        if annotation_color.isValid() is False:
            return

        self.ui.cncjob_defaults_form.cncjob_adv_opt_group.annotation_fontcolor_button.setStyleSheet(
            "background-color:%s" % str(annotation_color.name()))

        new_val_sel = str(annotation_color.name())
        self.ui.cncjob_defaults_form.cncjob_adv_opt_group.annotation_fontcolor_entry.set_value(new_val_sel)
        self.defaults['cncjob_annotation_fontcolor'] = new_val_sel

    def on_film_color_entry(self):
        self.defaults['tools_film_color'] = \
            self.ui.tools_defaults_form.tools_film_group.film_color_entry.get_value()
        self.ui.tools_defaults_form.tools_film_group.film_color_button.setStyleSheet(
            "background-color:%s;"
            "border-color: dimgray" % str(self.defaults['tools_film_color'])
        )

    def on_film_color_button(self):
        current_color = QtGui.QColor(self.defaults['tools_film_color'])

        c_dialog = QtWidgets.QColorDialog()
        film_color = c_dialog.getColor(initial=current_color)

        if film_color.isValid() is False:
            return

        # if new color is different then mark that the Preferences are changed
        if film_color != current_color:
            self.on_preferences_edited()

        self.ui.tools_defaults_form.tools_film_group.film_color_button.setStyleSheet(
            "background-color:%s;"
            "border-color: dimgray" % str(film_color.name())
        )
        new_val_sel = str(film_color.name())
        self.ui.tools_defaults_form.tools_film_group.film_color_entry.set_value(new_val_sel)
        self.defaults['tools_film_color'] = new_val_sel

    def on_qrcode_fill_color_entry(self):
        self.defaults['tools_qrcode_fill_color'] = \
            self.ui.tools2_defaults_form.tools2_qrcode_group.fill_color_entry.get_value()
        self.ui.tools2_defaults_form.tools2_qrcode_group.fill_color_button.setStyleSheet(
            "background-color:%s;"
            "border-color: dimgray" % str(self.defaults['tools_qrcode_fill_color'])
        )

    def on_qrcode_fill_color_button(self):
        current_color = QtGui.QColor(self.defaults['tools_qrcode_fill_color'])

        c_dialog = QtWidgets.QColorDialog()
        fill_color = c_dialog.getColor(initial=current_color)

        if fill_color.isValid() is False:
            return

        # if new color is different then mark that the Preferences are changed
        if fill_color != current_color:
            self.on_preferences_edited()

        self.ui.tools2_defaults_form.tools2_qrcode_group.fill_color_button.setStyleSheet(
            "background-color:%s;"
            "border-color: dimgray" % str(fill_color.name())
        )

        new_val_sel = str(fill_color.name())
        self.ui.tools2_defaults_form.tools2_qrcode_group.fill_color_entry.set_value(new_val_sel)
        self.defaults['tools_qrcode_fill_color'] = new_val_sel

    def on_qrcode_back_color_entry(self):
        self.defaults['tools_qrcode_back_color'] = \
            self.ui.tools2_defaults_form.tools2_qrcode_group.back_color_entry.get_value()
        self.ui.tools2_defaults_form.tools2_qrcode_group.back_color_button.setStyleSheet(
            "background-color:%s;"
            "border-color: dimgray" % str(self.defaults['tools_qrcode_back_color'])
        )

    def on_qrcode_back_color_button(self):
        current_color = QtGui.QColor(self.defaults['tools_qrcode_back_color'])

        c_dialog = QtWidgets.QColorDialog()
        back_color = c_dialog.getColor(initial=current_color)

        if back_color.isValid() is False:
            return

        # if new color is different then mark that the Preferences are changed
        if back_color != current_color:
            self.on_preferences_edited()

        self.ui.tools2_defaults_form.tools2_qrcode_group.back_color_button.setStyleSheet(
            "background-color:%s;"
            "border-color: dimgray" % str(back_color.name())
        )

        new_val_sel = str(back_color.name())
        self.ui.tools2_defaults_form.tools2_qrcode_group.back_color_entry.set_value(new_val_sel)
        self.defaults['tools_qrcode_back_color'] = new_val_sel

    def on_splash_changed(self, state):
        settings = QSettings("Open Source", "FlatCAM")
        settings.setValue('splash_screen', 1) if state else settings.setValue('splash_screen', 0)

        # This will write the setting to the platform specific storage.
        del settings

    def on_tab_rmb_click(self, checked):
        self.ui.notebook.set_detachable(val=checked)
        self.defaults["global_tabs_detachable"] = checked

        self.ui.plot_tab_area.set_detachable(val=checked)
        self.defaults["global_tabs_detachable"] = checked

    def on_tab_setup_context_menu(self):
        initial_checked = self.defaults["global_tabs_detachable"]
        action_name = str(_("Detachable Tabs"))
        action = QtWidgets.QAction(self)
        action.setCheckable(True)
        action.setText(action_name)
        action.setChecked(initial_checked)

        self.ui.notebook.tabBar.addAction(action)
        self.ui.plot_tab_area.tabBar.addAction(action)

        try:
            action.triggered.disconnect()
        except TypeError:
            pass
        action.triggered.connect(self.on_tab_rmb_click)

    def on_deselect_all(self):
        self.collection.set_all_inactive()
        self.delete_selection_shape()

    def on_workspace_modified(self):
        # self.save_defaults(silent=True)
        if self.is_legacy is True:
            self.plotcanvas.delete_workspace()
        self.defaults_read_form()
        self.plotcanvas.draw_workspace(workspace_size=self.defaults['global_workspaceT'])

    def on_workspace(self):
        if self.ui.general_defaults_form.general_gui_group.workspace_cb.get_value():
            self.plotcanvas.draw_workspace(workspace_size=self.defaults['global_workspaceT'])
        else:
            self.plotcanvas.delete_workspace()
        self.defaults_read_form()
        # self.save_defaults(silent=True)

    def on_workspace_toggle(self):
        state = False if self.ui.general_defaults_form.general_gui_group.workspace_cb.get_value() else True
        try:
            self.ui.general_defaults_form.general_gui_group.workspace_cb.stateChanged.disconnect(self.on_workspace)
        except TypeError:
            pass
        self.ui.general_defaults_form.general_gui_group.workspace_cb.set_value(state)
        self.ui.general_defaults_form.general_gui_group.workspace_cb.stateChanged.connect(self.on_workspace)
        self.on_workspace()

    def on_layout(self, index=None, lay=None):
        """
        Set the toolbars layout (location)

        :param index:
        :param lay: type of layout to be set on the toolbard
        :return: None
        """
        self.report_usage("on_layout()")
        if lay:
            current_layout = lay
        else:
            current_layout = self.ui.general_defaults_form.general_gui_set_group.layout_combo.get_value()

        lay_settings = QSettings("Open Source", "FlatCAM")
        lay_settings.setValue('layout', current_layout)

        # This will write the setting to the platform specific storage.
        del lay_settings

        # first remove the toolbars:
        try:
            self.ui.removeToolBar(self.ui.toolbarfile)
            self.ui.removeToolBar(self.ui.toolbargeo)
            self.ui.removeToolBar(self.ui.toolbarview)
            self.ui.removeToolBar(self.ui.toolbarshell)
            self.ui.removeToolBar(self.ui.toolbartools)
            self.ui.removeToolBar(self.ui.exc_edit_toolbar)
            self.ui.removeToolBar(self.ui.geo_edit_toolbar)
            self.ui.removeToolBar(self.ui.grb_edit_toolbar)
            self.ui.removeToolBar(self.ui.snap_toolbar)
            self.ui.removeToolBar(self.ui.toolbarshell)
        except Exception:
            pass

        if current_layout == 'standard':
            # ## TOOLBAR INSTALLATION # ##
            self.ui.toolbarfile = QtWidgets.QToolBar('File Toolbar')
            self.ui.toolbarfile.setObjectName('File_TB')
            self.ui.addToolBar(self.ui.toolbarfile)

            self.ui.toolbargeo = QtWidgets.QToolBar('Edit Toolbar')
            self.ui.toolbargeo.setObjectName('Edit_TB')
            self.ui.addToolBar(self.ui.toolbargeo)

            self.ui.toolbarview = QtWidgets.QToolBar('View Toolbar')
            self.ui.toolbarview.setObjectName('View_TB')
            self.ui.addToolBar(self.ui.toolbarview)

            self.ui.toolbarshell = QtWidgets.QToolBar('Shell Toolbar')
            self.ui.toolbarshell.setObjectName('Shell_TB')
            self.ui.addToolBar(self.ui.toolbarshell)

            self.ui.toolbartools = QtWidgets.QToolBar('Tools Toolbar')
            self.ui.toolbartools.setObjectName('Tools_TB')
            self.ui.addToolBar(self.ui.toolbartools)

            self.ui.exc_edit_toolbar = QtWidgets.QToolBar('Excellon Editor Toolbar')
            # self.ui.exc_edit_toolbar.setVisible(False)
            self.ui.exc_edit_toolbar.setObjectName('ExcEditor_TB')
            self.ui.addToolBar(self.ui.exc_edit_toolbar)

            self.ui.addToolBarBreak()

            self.ui.geo_edit_toolbar = QtWidgets.QToolBar('Geometry Editor Toolbar')
            # self.ui.geo_edit_toolbar.setVisible(False)
            self.ui.geo_edit_toolbar.setObjectName('GeoEditor_TB')
            self.ui.addToolBar(self.ui.geo_edit_toolbar)

            self.ui.grb_edit_toolbar = QtWidgets.QToolBar('Gerber Editor Toolbar')
            # self.ui.grb_edit_toolbar.setVisible(False)
            self.ui.grb_edit_toolbar.setObjectName('GrbEditor_TB')
            self.ui.addToolBar(self.ui.grb_edit_toolbar)

            self.ui.snap_toolbar = QtWidgets.QToolBar('Grid Toolbar')
            self.ui.snap_toolbar.setObjectName('Snap_TB')
            # self.ui.snap_toolbar.setMaximumHeight(30)
            self.ui.addToolBar(self.ui.snap_toolbar)

            self.ui.corner_snap_btn.setVisible(False)
            self.ui.snap_magnet.setVisible(False)
        elif current_layout == 'compact':
            # ## TOOLBAR INSTALLATION # ##
            self.ui.toolbarfile = QtWidgets.QToolBar('File Toolbar')
            self.ui.toolbarfile.setObjectName('File_TB')
            self.ui.addToolBar(Qt.LeftToolBarArea, self.ui.toolbarfile)

            self.ui.toolbargeo = QtWidgets.QToolBar('Edit Toolbar')
            self.ui.toolbargeo.setObjectName('Edit_TB')
            self.ui.addToolBar(Qt.LeftToolBarArea, self.ui.toolbargeo)

            self.ui.toolbarshell = QtWidgets.QToolBar('Shell Toolbar')
            self.ui.toolbarshell.setObjectName('Shell_TB')
            self.ui.addToolBar(Qt.LeftToolBarArea, self.ui.toolbarshell)

            self.ui.toolbartools = QtWidgets.QToolBar('Tools Toolbar')
            self.ui.toolbartools.setObjectName('Tools_TB')
            self.ui.addToolBar(Qt.LeftToolBarArea, self.ui.toolbartools)

            self.ui.geo_edit_toolbar = QtWidgets.QToolBar('Geometry Editor Toolbar')
            # self.ui.geo_edit_toolbar.setVisible(False)
            self.ui.geo_edit_toolbar.setObjectName('GeoEditor_TB')
            self.ui.addToolBar(Qt.RightToolBarArea, self.ui.geo_edit_toolbar)

            self.ui.toolbarview = QtWidgets.QToolBar('View Toolbar')
            self.ui.toolbarview.setObjectName('View_TB')
            self.ui.addToolBar(Qt.RightToolBarArea, self.ui.toolbarview)

            self.ui.addToolBarBreak(area=Qt.RightToolBarArea)

            self.ui.grb_edit_toolbar = QtWidgets.QToolBar('Gerber Editor Toolbar')
            # self.ui.grb_edit_toolbar.setVisible(False)
            self.ui.grb_edit_toolbar.setObjectName('GrbEditor_TB')
            self.ui.addToolBar(Qt.RightToolBarArea, self.ui.grb_edit_toolbar)

            self.ui.exc_edit_toolbar = QtWidgets.QToolBar('Excellon Editor Toolbar')
            self.ui.exc_edit_toolbar.setObjectName('ExcEditor_TB')
            self.ui.addToolBar(Qt.RightToolBarArea, self.ui.exc_edit_toolbar)

            self.ui.snap_toolbar = QtWidgets.QToolBar('Grid Toolbar')
            self.ui.snap_toolbar.setObjectName('Snap_TB')
            self.ui.snap_toolbar.setMaximumHeight(30)
            self.ui.splitter_left.addWidget(self.ui.snap_toolbar)

            self.ui.corner_snap_btn.setVisible(True)
            self.ui.snap_magnet.setVisible(True)

        # add all the actions to the toolbars
        self.ui.populate_toolbars()

        # reconnect all the signals to the toolbar actions
        self.connect_toolbar_signals()

        self.ui.grid_snap_btn.setChecked(True)
        self.ui.grid_gap_x_entry.setText(str(self.defaults["global_gridx"]))
        self.ui.grid_gap_y_entry.setText(str(self.defaults["global_gridy"]))
        self.ui.snap_max_dist_entry.setText(str(self.defaults["global_snap_max"]))
        self.ui.grid_gap_link_cb.setChecked(True)

    def on_cursor_type(self, val):
        """

        :param val: type of mouse cursor, set in Preferences ('small' or 'big')
        :return: None
        """
        self.app_cursor.enabled = False

        if val == 'small':
            self.ui.general_defaults_form.general_gui_set_group.cursor_size_entry.setDisabled(False)
            self.ui.general_defaults_form.general_gui_set_group.cursor_size_lbl.setDisabled(False)
            self.app_cursor = self.plotcanvas.new_cursor()
        else:
            self.ui.general_defaults_form.general_gui_set_group.cursor_size_entry.setDisabled(True)
            self.ui.general_defaults_form.general_gui_set_group.cursor_size_lbl.setDisabled(True)
            self.app_cursor = self.plotcanvas.new_cursor(big=True)

        if self.ui.grid_snap_btn.isChecked():
            self.app_cursor.enabled = True
        else:
            self.app_cursor.enabled = False

    def on_cnc_custom_parameters(self, signal_text):
        if signal_text == 'Parameters':
            return
        else:
            self.ui.cncjob_defaults_form.cncjob_adv_opt_group.toolchange_text.insertPlainText('%%%s%%' % signal_text)

    def on_save_button(self, save_to_file=True):
        log.debug("App.on_save_button() --> Applying preferences to file.")

        # Preferences saved, update flag
        self.preferences_changed_flag = False

        # Preferences save, update the color of the Preferences Tab text
        for idx in range(self.ui.plot_tab_area.count()):
            if self.ui.plot_tab_area.tabText(idx) == _("Preferences"):
                self.ui.plot_tab_area.tabBar.setTabTextColor(idx, QtGui.QColor('black'))

        self.inform.emit('%s' % _("Preferences applied."))

        if save_to_file:
            self.save_defaults(silent=False)
            # load the defaults so they are updated into the app
            self.load_defaults(filename='current_defaults')

        # Re-fresh project options
        self.on_options_app2project()

        settgs = QSettings("Open Source", "FlatCAM")

        # save the notebook font size
        fsize = self.ui.general_defaults_form.general_gui_set_group.notebook_font_size_spinner.get_value()
        settgs.setValue('notebook_font_size', fsize)

        # save the axis font size
        g_fsize = self.ui.general_defaults_form.general_gui_set_group.axis_font_size_spinner.get_value()
        settgs.setValue('axis_font_size', g_fsize)

        # save the textbox font size
        tb_fsize = self.ui.general_defaults_form.general_gui_set_group.textbox_font_size_spinner.get_value()
        settgs.setValue('textbox_font_size', tb_fsize)

        settgs.setValue(
            'machinist',
            1 if self.ui.general_defaults_form.general_app_group.machinist_cb.get_value() else 0
        )

        # This will write the setting to the platform specific storage.
        del settgs

    def on_tool_add_keypress(self):
        # ## Current application units in Upper Case
        self.units = self.defaults['units'].upper()

        notebook_widget_name = self.ui.notebook.currentWidget().objectName()

        # work only if the notebook tab on focus is the Selected_Tab and only if the object is Geometry
        if notebook_widget_name == 'selected_tab':
            if str(type(self.collection.get_active())) == "<class 'FlatCAMObj.FlatCAMGeometry'>":
                # Tool add works for Geometry only if Advanced is True in Preferences
                if self.defaults["global_app_level"] == 'a':
                    tool_add_popup = FCInputDialog(title="New Tool ...",
                                                   text='Enter a Tool Diameter:',
                                                   min=0.0000, max=99.9999, decimals=4)
                    tool_add_popup.setWindowIcon(QtGui.QIcon('share/letter_t_32.png'))

                    val, ok = tool_add_popup.get_value()
                    if ok:
                        if float(val) == 0:
                            self.inform.emit('[WARNING_NOTCL] %s' %
                                             _("Please enter a tool diameter with non-zero value, in Float format."))
                            return
                        self.collection.get_active().on_tool_add(dia=float(val))
                    else:
                        self.inform.emit('[WARNING_NOTCL] %s...' %
                                         _("Adding Tool cancelled"))
                else:
                    msgbox = QtWidgets.QMessageBox()
                    msgbox.setText(_("Adding Tool works only when Advanced is checked.\n"
                                   "Go to Preferences -> General - Show Advanced Options."))
                    msgbox.setWindowTitle("Tool adding ...")
                    msgbox.setWindowIcon(QtGui.QIcon('share/warning.png'))
                    bt_ok = msgbox.addButton(_('Ok'), QtWidgets.QMessageBox.AcceptRole)

                    msgbox.setDefaultButton(bt_ok)
                    msgbox.exec_()

        # work only if the notebook tab on focus is the Tools_Tab
        if notebook_widget_name == 'tool_tab':
            tool_widget = self.ui.tool_scroll_area.widget().objectName()

            # and only if the tool is NCC Tool
            if tool_widget == self.ncclear_tool.toolName:
                self.ncclear_tool.on_add_tool_by_key()

            # and only if the tool is Paint Area Tool
            elif tool_widget == self.paint_tool.toolName:
                self.paint_tool.on_add_tool_by_key()

            # and only if the tool is Solder Paste Dispensing Tool
            elif tool_widget == self.paste_tool.toolName:
                self.paste_tool.on_add_tool_by_key()

    # It's meant to delete tools in tool tables via a 'Delete' shortcut key but only if certain conditions are met
    # See description bellow.
    def on_delete_keypress(self):
        notebook_widget_name = self.ui.notebook.currentWidget().objectName()

        # work only if the notebook tab on focus is the Selected_Tab and only if the object is Geometry
        if notebook_widget_name == 'selected_tab':
            if str(type(self.collection.get_active())) == "<class 'FlatCAMObj.FlatCAMGeometry'>":
                self.collection.get_active().on_tool_delete()

        # work only if the notebook tab on focus is the Tools_Tab
        elif notebook_widget_name == 'tool_tab':
            tool_widget = self.ui.tool_scroll_area.widget().objectName()

            # and only if the tool is NCC Tool
            if tool_widget == self.ncclear_tool.toolName:
                self.ncclear_tool.on_tool_delete()

            # and only if the tool is Paint Tool
            elif tool_widget == self.paint_tool.toolName:
                self.paint_tool.on_tool_delete()

            # and only if the tool is Solder Paste Dispensing Tool
            elif tool_widget == self.paste_tool.toolName:
                self.paste_tool.on_tool_delete()
        else:
            self.on_delete()

    # It's meant to delete selected objects. It work also activated by a shortcut key 'Delete' same as above so in
    # some screens you have to be careful where you hover with your mouse.
    # Hovering over Selected tab, if the selected tab is a Geometry it will delete tools in tool table. But even if
    # there is a Selected tab in focus with a Geometry inside, if you hover over canvas it will delete an object.
    # Complicated, I know :)
    def on_delete(self):
        """
        Delete the currently selected FlatCAMObjs.

        :return: None
        """
        self.report_usage("on_delete()")

        response = None
        bt_ok = None

        # Make sure that the deletion will happen only after the Editor is no longer active otherwise we might delete
        # a geometry object before we update it.
        if self.geo_editor.editor_active is False and self.exc_editor.editor_active is False \
                and self.grb_editor.editor_active is False:
            if self.defaults["global_delete_confirmation"] is True:
                msgbox = QtWidgets.QMessageBox()
                msgbox.setWindowTitle(_("Delete objects"))
                msgbox.setWindowIcon(QtGui.QIcon('share/deleteshape32.png'))
                # msgbox.setText("<B>%s</B>" % _("Change project units ..."))
                msgbox.setText(_("Are you sure you want to permanently delete\n"
                                 "the selected objects?"))
                bt_ok = msgbox.addButton(_('Ok'), QtWidgets.QMessageBox.AcceptRole)
                msgbox.addButton(_('Cancel'), QtWidgets.QMessageBox.RejectRole)

                msgbox.setDefaultButton(bt_ok)
                msgbox.exec_()
                response = msgbox.clickedButton()

            if response == bt_ok or self.defaults["global_delete_confirmation"] is False:
                if self.collection.get_active():
                    self.log.debug("App.on_delete()")

                    while self.collection.get_active():
                        obj_active = self.collection.get_active()
                        # if the deleted object is FlatCAMGerber then make sure to delete the possible mark shapes
                        if isinstance(obj_active, FlatCAMGerber):
                            for el in obj_active.mark_shapes:
                                obj_active.mark_shapes[el].clear(update=True)
                                obj_active.mark_shapes[el].enabled = False
                                # obj_active.mark_shapes[el] = None
                                del el
                        elif isinstance(obj_active, FlatCAMCNCjob):
                            try:
                                obj_active.annotation.clear(update=True)
                                obj_active.annotation.enabled = False
                            except AttributeError:
                                pass
                        self.delete_first_selected()

                    self.inform.emit('%s...' %
                                     _("Object(s) deleted"))
                    # make sure that the selection shape is deleted, too
                    self.delete_selection_shape()
                else:
                    self.inform.emit(_("Failed. No object(s) selected..."))
        else:
            self.inform.emit(_("Save the work in Editor and try again ..."))

    def delete_first_selected(self):
        # Keep this for later
        try:
            sel_obj = self.collection.get_active()
            name = sel_obj.options["name"]
            isPlotted = sel_obj.options["plot"]
        except AttributeError:
            self.log.debug("Nothing selected for deletion")
            return

        if self.is_legacy is True:
            # Remove plot only if the object was plotted otherwise delaxes will fail
            if isPlotted:
                try:
                    # self.plotcanvas.figure.delaxes(self.collection.get_active().axes)
                    self.plotcanvas.figure.delaxes(self.collection.get_active().shapes.axes)
                except Exception as e:
                    log.debug("App.delete_first_selected() --> %s" % str(e))

            self.plotcanvas.auto_adjust_axes()

        # Remove from dictionary
        self.collection.delete_active()

        # Clear form
        self.setup_component_editor()

        self.inform.emit('%s: %s' %
                         (_("Object deleted"), name))

    def on_set_origin(self):
        """
        Set the origin to the left mouse click position

        :return: None
        """

        # display the message for the user
        # and ask him to click on the desired position
        self.report_usage("on_set_origin()")

        def origin_replot():

            def worker_task():
                with self.proc_container.new('%s...' % _("Plotting")):
                    for obj in self.collection.get_list():
                        obj.plot()
                    self.plotcanvas.fit_view()
                if self.is_legacy:
                    self.plotcanvas.graph_event_disconnect(self.mp_zc)
                else:
                    self.plotcanvas.graph_event_disconnect('mouse_press', self.on_set_zero_click)

            self.worker_task.emit({'fcn': worker_task, 'params': []})

        self.inform.emit(_('Click to set the origin ...'))
        self.mp_zc = self.plotcanvas.graph_event_connect('mouse_press', self.on_set_zero_click)

        # first disconnect it as it may have been used by something else
        try:
            self.replot_signal.disconnect()
        except TypeError:
            pass
        self.replot_signal[list].connect(origin_replot)

    def on_set_zero_click(self, event, location=None, noplot=False, use_thread=True):
        """

        :param event:
        :param location:
        :param noplot:
        :param use_thread:
        :return:
        """
        noplot_sig = noplot

        def worker_task():
            with self.proc_container.new(_("Setting Origin...")):
                for obj in self.collection.get_list():
                    obj.offset((x, y))
                    self.object_changed.emit(obj)

                    # Update the object bounding box options
                    a, b, c, d = obj.bounds()
                    obj.options['xmin'] = a
                    obj.options['ymin'] = b
                    obj.options['xmax'] = c
                    obj.options['ymax'] = d
                self.inform.emit('[success] %s...' %
                                 _('Origin set'))
                if noplot_sig is False:
                    self.replot_signal.emit([])

        if location is not None:
            if len(location) != 2:
                self.inform.emit('[ERROR_NOTCL] %s...' %
                                 _("Origin coordinates specified but incomplete."))
                return 'fail'

            x, y = location

            if use_thread is True:
                self.worker_task.emit({'fcn': worker_task, 'params': []})
            else:
                worker_task()
            self.should_we_save = True
            return

        if event.button == 1:
            if self.is_legacy is False:
                event_pos = event.pos
            else:
                event_pos = (event.xdata, event.ydata)
            pos_canvas = self.plotcanvas.translate_coords(event_pos)

            if self.grid_status() == True:
                pos = self.geo_editor.snap(pos_canvas[0], pos_canvas[1])
            else:
                pos = pos_canvas

            x = 0 - pos[0]
            y = 0 - pos[1]

            if use_thread is True:
                self.worker_task.emit({'fcn': worker_task, 'params': []})
            else:
                worker_task()
            self.should_we_save = True

    def on_jump_to(self, custom_location=None, fit_center=True):
        """
        Jump to a location by setting the mouse cursor location
        :return:

        """
        self.report_usage("on_jump_to()")

        # if self.is_legacy is True:
        #     self.inform.emit(_("Not available with the current Graphic Engine Legacy(2D)."))
        #     return

        if not custom_location:
            dia_box_location = None

            try:
                dia_box_location = eval(self.clipboard.text())
            except Exception:
                pass

            if type(dia_box_location) == tuple:
                dia_box_location = str(dia_box_location)
            else:
                dia_box_location = None

            dia_box = Dialog_box(title=_("Jump to ..."),
                                 label=_("Enter the coordinates in format X,Y:"),
                                 icon=QtGui.QIcon('share/jump_to16.png'),
                                 initial_text=dia_box_location)

            if dia_box.ok is True:
                try:
                    location = eval(dia_box.location)
                    if not isinstance(location, tuple):
                        self.inform.emit(_("Wrong coordinates. Enter coordinates in format: X,Y"))
                        return
                except Exception:
                    return
            else:
                return
        else:
            location = custom_location

        if fit_center:
            self.plotcanvas.fit_center(loc=location)

        cursor = QtGui.QCursor()

        if self.is_legacy is False:
            canvas_origin = self.plotcanvas.native.mapToGlobal(QtCore.QPoint(0, 0))
            jump_loc = self.plotcanvas.translate_coords_2((location[0], location[1]))
            j_pos = (canvas_origin.x() + jump_loc[0], (canvas_origin.y() + jump_loc[1]))
            cursor.setPos(j_pos[0], j_pos[1])
        else:
            # find the canvas origin which is in the top left corner
            canvas_origin = self.plotcanvas.native.mapToGlobal(QtCore.QPoint(0, 0))
            # determine the coordinates for the lowest left point of the canvas
            x0, y0 = canvas_origin.x(), canvas_origin.y() + self.ui.right_layout.geometry().height()

            # transform the given location from data coordinates to display coordinates. THe display coordinates are
            # in pixels where the origin 0,0 is in the lowest left point of the display window (in our case is the
            # canvas) and the point (width, height) is in the top-right location
            loc = self.plotcanvas.axes.transData.transform_point(location)
            j_pos = (x0 + loc[0], y0 - loc[1])
            cursor.setPos(j_pos[0], j_pos[1])

        if self.grid_status() == True:
            # Update cursor
            self.app_cursor.set_data(np.asarray([(location[0], location[1])]),
                                     symbol='++', edge_color=self.cursor_color_3D,
                                     size=self.defaults["global_cursor_size"])

        # Set the position label
        self.ui.position_label.setText("&nbsp;&nbsp;&nbsp;&nbsp;<b>X</b>: %.4f&nbsp;&nbsp;   "
                                       "<b>Y</b>: %.4f" % (location[0], location[1]))
        # Set the relative position label
        dx = location[0] - float(self.rel_point1[0])
        dy = location[1] - float(self.rel_point1[1])
        self.ui.rel_position_label.setText("<b>Dx</b>: %.4f&nbsp;&nbsp;  <b>Dy</b>: "
                                           "%.4f&nbsp;&nbsp;&nbsp;&nbsp;" % (dx, dy))

        self.inform.emit('[success] %s' %
                         _("Done."))
        return location

    def on_copy_object(self):
        self.report_usage("on_copy_object()")

        def initialize(obj_init, app):
            obj_init.solid_geometry = deepcopy(obj.solid_geometry)
            try:
                obj_init.follow_geometry = deepcopy(obj.follow_geometry)
            except AttributeError:
                pass
            try:
                obj_init.apertures = deepcopy(obj.apertures)
            except AttributeError:
                pass

            try:
                if obj.tools:
                    obj_init.tools = deepcopy(obj.tools)
            except Exception as e:
                log.debug("App.on_copy_object() --> %s" % str(e))

        def initialize_excellon(obj_init, app):
            obj_init.tools = deepcopy(obj.tools)

            # drills are offset, so they need to be deep copied
            obj_init.drills = deepcopy(obj.drills)
            # slots are offset, so they need to be deep copied
            obj_init.slots = deepcopy(obj.slots)
            obj_init.create_geometry()

        def initialize_script(obj_init, app_obj):
            obj_init.source_file = deepcopy(obj.source_file)

        def initialize_document(obj_init, app_obj):
            obj_init.source_file = deepcopy(obj.source_file)

        for obj in self.collection.get_selected():
            obj_name = obj.options["name"]

            try:
                if isinstance(obj, FlatCAMExcellon):
                    self.new_object("excellon", str(obj_name) + "_copy", initialize_excellon)
                elif isinstance(obj, FlatCAMGerber):
                    self.new_object("gerber", str(obj_name) + "_copy", initialize)
                elif isinstance(obj, FlatCAMGeometry):
                    self.new_object("geometry", str(obj_name) + "_copy", initialize)
                elif isinstance(obj, FlatCAMScript):
                    self.new_object("script", str(obj_name) + "_copy", initialize_script)
                elif isinstance(obj, FlatCAMDocument):
                    self.new_object("document", str(obj_name) + "_copy", initialize_document)
            except Exception as e:
                return "Operation failed: %s" % str(e)

    def on_copy_object2(self, custom_name):

        def initialize_geometry(obj_init, app):
            obj_init.solid_geometry = deepcopy(obj.solid_geometry)
            try:
                obj_init.follow_geometry = deepcopy(obj.follow_geometry)
            except AttributeError:
                pass
            try:
                obj_init.apertures = deepcopy(obj.apertures)
            except AttributeError:
                pass

            try:
                if obj.tools:
                    obj_init.tools = deepcopy(obj.tools)
            except Exception as ee:
                log.debug("on_copy_object2() --> %s" % str(ee))

        def initialize_gerber(obj_init, app):
            obj_init.solid_geometry = deepcopy(obj.solid_geometry)
            obj_init.apertures = deepcopy(obj.apertures)
            obj_init.aperture_macros = deepcopy(obj.aperture_macros)

        def initialize_excellon(obj_init, app):
            obj_init.tools = deepcopy(obj.tools)
            # drills are offset, so they need to be deep copied
            obj_init.drills = deepcopy(obj.drills)
            # slots are offset, so they need to be deep copied
            obj_init.slots = deepcopy(obj.slots)
            obj_init.create_geometry()

        for obj in self.collection.get_selected():
            obj_name = obj.options["name"]
            try:
                if isinstance(obj, FlatCAMExcellon):
                    self.new_object("excellon", str(obj_name) + custom_name, initialize_excellon)
                elif isinstance(obj, FlatCAMGerber):
                    self.new_object("gerber", str(obj_name) + custom_name, initialize_gerber)
                elif isinstance(obj, FlatCAMGeometry):
                    self.new_object("geometry", str(obj_name) + custom_name, initialize_geometry)
            except Exception as e:
                return "Operation failed: %s" % str(e)

    def on_rename_object(self, text):
        self.report_usage("on_rename_object()")

        named_obj = self.collection.get_active()
        for obj in named_obj:
            if obj is list:
                self.on_rename_object(text)
            else:
                try:
                    obj.options['name'] = text
                except Exception as e:
                    log.warning("App.on_rename_object() --> Could not rename the object in the list. --> %s" % str(e))

    def convert_any2geo(self):
        self.report_usage("convert_any2geo()")

        def initialize(obj_init, app):
            obj_init.solid_geometry = obj.solid_geometry
            try:
                obj_init.follow_geometry = obj.follow_geometry
            except AttributeError:
                pass
            try:
                obj_init.apertures = obj.apertures
            except AttributeError:
                pass

            try:
                if obj.tools:
                    obj_init.tools = obj.tools
            except AttributeError:
                pass

        def initialize_excellon(obj_init, app):
            # objs = self.collection.get_selected()
            # FlatCAMGeometry.merge(objs, obj)
            solid_geo = []
            for tool in obj.tools:
                for geo in obj.tools[tool]['solid_geometry']:
                    solid_geo.append(geo)
            obj_init.solid_geometry = deepcopy(solid_geo)

        if not self.collection.get_selected():
            log.warning("App.convert_any2geo --> No object selected")
            self.inform.emit('[WARNING_NOTCL] %s' %
                             _("No object is selected. Select an object and try again."))
            return

        for obj in self.collection.get_selected():
            obj_name = obj.options["name"]

            try:
                if isinstance(obj, FlatCAMExcellon):
                    self.new_object("geometry", str(obj_name) + "_conv", initialize_excellon)
                else:
                    self.new_object("geometry", str(obj_name) + "_conv", initialize)
            except Exception as e:
                return "Operation failed: %s" % str(e)

    def convert_any2gerber(self):
        self.report_usage("convert_any2gerber()")

        def initialize_geometry(obj_init, app):
            apertures = {}
            apid = 0

            apertures[str(apid)] = {}
            apertures[str(apid)]['geometry'] = []
            for obj_orig in obj.solid_geometry:
                new_elem = dict()
                new_elem['solid'] = obj_orig
                try:
                    new_elem['follow'] = obj_orig.exterior
                except AttributeError:
                    pass
                apertures[str(apid)]['geometry'].append(deepcopy(new_elem))
            apertures[str(apid)]['size'] = 0.0
            apertures[str(apid)]['type'] = 'C'

            obj_init.solid_geometry = deepcopy(obj.solid_geometry)
            obj_init.apertures = deepcopy(apertures)

        def initialize_excellon(obj_init, app):
            apertures = {}

            apid = 10
            for tool in obj.tools:
                apertures[str(apid)] = {}
                apertures[str(apid)]['geometry'] = []
                for geo in obj.tools[tool]['solid_geometry']:
                    new_el = dict()
                    new_el['solid'] = geo
                    new_el['follow'] = geo.exterior
                    apertures[str(apid)]['geometry'].append(deepcopy(new_el))

                apertures[str(apid)]['size'] = float(obj.tools[tool]['C'])
                apertures[str(apid)]['type'] = 'C'
                apid += 1

            # create solid_geometry
            solid_geometry = []
            for apid in apertures:
                for geo_el in apertures[apid]['geometry']:
                    solid_geometry.append(geo_el['solid'])

            solid_geometry = MultiPolygon(solid_geometry)
            solid_geometry = solid_geometry.buffer(0.0000001)

            obj_init.solid_geometry = deepcopy(solid_geometry)
            obj_init.apertures = deepcopy(apertures)
            # clear the working objects (perhaps not necessary due of Python GC)
            apertures.clear()

        if not self.collection.get_selected():
            log.warning("App.convert_any2gerber --> No object selected")
            self.inform.emit('[WARNING_NOTCL] %s' %
                             _("No object is selected. Select an object and try again."))
            return

        for obj in self.collection.get_selected():

            obj_name = obj.options["name"]

            try:
                if isinstance(obj, FlatCAMExcellon):
                    self.new_object("gerber", str(obj_name) + "_conv", initialize_excellon)
                elif isinstance(obj, FlatCAMGeometry):
                    self.new_object("gerber", str(obj_name) + "_conv", initialize_geometry)
                else:
                    log.warning("App.convert_any2gerber --> This is no vaild object for conversion.")

            except Exception as e:
                return "Operation failed: %s" % str(e)

    def abort_all_tasks(self):
        if self.abort_flag is False:
            self.inform.emit(_("Aborting. The current task will be gracefully closed as soon as possible..."))
            self.abort_flag = True

    def app_is_idle(self):
        if self.abort_flag:
            self.inform.emit('[WARNING_NOTCL] %s' %
                             _("The current task was gracefully closed on user request..."))
            self.abort_flag = False

    def on_selectall(self):
        self.report_usage("on_selectall()")

        # delete the possible selection box around a possible selected object
        self.delete_selection_shape()
        for name in self.collection.get_names():
            self.collection.set_active(name)
            curr_sel_obj = self.collection.get_by_name(name)
            # create the selection box around the selected object
            if self.defaults['global_selection_shape'] is True:
                self.draw_selection_shape(curr_sel_obj)

    def on_preferences(self):
        """
        Adds the Preferences in a Tab in Plot Area

        :return:
        """

        # add the tab if it was closed
        self.ui.plot_tab_area.addTab(self.ui.preferences_tab, _("Preferences"))

        # delete the absolute and relative position and messages in the infobar
        self.ui.position_label.setText("")
        self.ui.rel_position_label.setText("")

        # Switch plot_area to preferences page
        self.ui.plot_tab_area.setCurrentWidget(self.ui.preferences_tab)
        # self.ui.show()

        # detect changes in the preferences
        for idx in range(self.ui.pref_tab_area.count()):
            for tb in self.ui.pref_tab_area.widget(idx).findChildren(QtCore.QObject):
                try:
                    try:
                        tb.textEdited.disconnect(self.on_preferences_edited)
                    except (TypeError, AttributeError):
                        pass
                    tb.textEdited.connect(self.on_preferences_edited)
                except AttributeError:
                    pass

                try:
                    try:
                        tb.modificationChanged.disconnect(self.on_preferences_edited)
                    except (TypeError, AttributeError):
                        pass
                    tb.modificationChanged.connect(self.on_preferences_edited)
                except AttributeError:
                    pass

                try:
                    try:
                        tb.toggled.disconnect(self.on_preferences_edited)
                    except (TypeError, AttributeError):
                        pass
                    tb.toggled.connect(self.on_preferences_edited)
                except AttributeError:
                    pass

                try:
                    try:
                        tb.valueChanged.disconnect(self.on_preferences_edited)
                    except (TypeError, AttributeError):
                        pass
                    tb.valueChanged.connect(self.on_preferences_edited)
                except AttributeError:
                    pass

                try:
                    try:
                        tb.currentIndexChanged.disconnect(self.on_preferences_edited)
                    except (TypeError, AttributeError):
                        pass
                    tb.currentIndexChanged.connect(self.on_preferences_edited)
                except AttributeError:
                    pass

    def on_preferences_edited(self):
        self.inform.emit('[WARNING_NOTCL] %s' %
                         _("Preferences edited but not saved."))

        for idx in range(self.ui.plot_tab_area.count()):
            if self.ui.plot_tab_area.tabText(idx) == _("Preferences"):
                self.ui.plot_tab_area.tabBar.setTabTextColor(idx, QtGui.QColor('red'))

        self.preferences_changed_flag = True

    def on_tools_database(self):
        """
        Adds the Tools Database in a Tab in Plot Area
        :return:
        """
        for idx in range(self.ui.plot_tab_area.count()):
            if self.ui.plot_tab_area.tabText(idx) == _("Tools Database"):
                # there can be only one instance of Tools Database at one time
                return

        self.tools_db_tab = ToolsDB(
            app=self,
            parent=self.ui,
            callback_on_edited=self.on_tools_db_edited,
            callback_on_tool_request=self.on_geometry_tool_add_from_db_executed
        )

        # add the tab if it was closed
        self.ui.plot_tab_area.addTab(self.tools_db_tab, _("Tools Database"))
        self.tools_db_tab.setObjectName("database_tab")

        # delete the absolute and relative position and messages in the infobar
        self.ui.position_label.setText("")
        self.ui.rel_position_label.setText("")

        # Switch plot_area to preferences page
        self.ui.plot_tab_area.setCurrentWidget(self.tools_db_tab)

        # detect changes in the Tools in Tools DB, connect signals from table widget in tab
        self.tools_db_tab.ui_connect()

    def on_tools_db_edited(self):
        self.inform.emit('[WARNING_NOTCL] %s' % _("Tools in Tools Database edited but not saved."))

        for idx in range(self.ui.plot_tab_area.count()):
            if self.ui.plot_tab_area.tabText(idx) == _("Tools Database"):
                self.ui.plot_tab_area.tabBar.setTabTextColor(idx, QtGui.QColor('red'))

        self.tools_db_changed_flag = True

    def on_geometry_tool_add_from_db_executed(self, tool):
        """
        Here add the tool from DB  in the selected geometry object
        :return:
        """
        tool_from_db = deepcopy(tool)

        obj = self.collection.get_active()
        if isinstance(obj, FlatCAMGeometry):
            obj.on_tool_from_db_inserted(tool=tool_from_db)

            for idx in range(self.ui.plot_tab_area.count()):
                if self.ui.plot_tab_area.tabText(idx) == _("Tools Database"):
                    wdg = self.ui.plot_tab_area.widget(idx)
                    wdg.deleteLater()
                    self.ui.plot_tab_area.removeTab(idx)
            self.inform.emit('[success] %s' % _("Tool from DB added in Tool Table."))
        else:
            self.inform.emit('[ERROR_NOTCL] %s' % _("Adding tool from DB is not allowed for this object."))

    def on_plot_area_tab_closed(self, title):
        if title == _("Preferences"):
            # disconnect
            for idx in range(self.ui.pref_tab_area.count()):
                for tb in self.ui.pref_tab_area.widget(idx).findChildren(QtCore.QObject):
                    try:
                        tb.textEdited.disconnect(self.on_preferences_edited)
                    except (TypeError, AttributeError):
                        pass

                    try:
                        tb.modificationChanged.disconnect(self.on_preferences_edited)
                    except (TypeError, AttributeError):
                        pass

                    try:
                        tb.toggled.disconnect(self.on_preferences_edited)
                    except (TypeError, AttributeError):
                        pass

                    try:
                        tb.valueChanged.disconnect(self.on_preferences_edited)
                    except (TypeError, AttributeError):
                        pass

                    try:
                        tb.currentIndexChanged.disconnect(self.on_preferences_edited)
                    except (TypeError, AttributeError):
                        pass

            if self.preferences_changed_flag is True:
                msgbox = QtWidgets.QMessageBox()
                msgbox.setText(_("One or more values are changed.\n"
                                 "Do you want to save the Preferences?"))
                msgbox.setWindowTitle(_("Save Preferences"))
                msgbox.setWindowIcon(QtGui.QIcon('share/save_as.png'))

                bt_yes = msgbox.addButton(_('Yes'), QtWidgets.QMessageBox.YesRole)
                msgbox.addButton(_('No'), QtWidgets.QMessageBox.NoRole)

                msgbox.setDefaultButton(bt_yes)
                msgbox.exec_()
                response = msgbox.clickedButton()

                if response == bt_yes:
                    self.on_save_button(save_to_file=True)
                    self.inform.emit('[success] %s' % _("Preferences saved."))
                else:
                    self.preferences_changed_flag = False
                    self.inform.emit('')
                    return

        if title == _("Tools Database"):
            # disconnect the signals from the table widget in tab
            self.tools_db_tab.ui_disconnect()

            if self.tools_db_changed_flag is True:
                msgbox = QtWidgets.QMessageBox()
                msgbox.setText(_("One or more Tools are edited.\n"
                                 "Do you want to update the Tools Database?"))
                msgbox.setWindowTitle(_("Save Tools Database"))
                msgbox.setWindowIcon(QtGui.QIcon('share/save_as.png'))

                bt_yes = msgbox.addButton(_('Yes'), QtWidgets.QMessageBox.YesRole)
                msgbox.addButton(_('No'), QtWidgets.QMessageBox.NoRole)

                msgbox.setDefaultButton(bt_yes)
                msgbox.exec_()
                response = msgbox.clickedButton()

                if response == bt_yes:
                    self.tools_db_tab.on_save_tools_db()
                    self.inform.emit('[success] %s' % "Tools DB saved to file.")
                else:
                    self.tools_db_changed_flag = False
                    self.inform.emit('')
                    return
            self.tools_db_tab.deleteLater()

        if title == _("Code Editor"):
            self.toggle_codeeditor = False

        if title == _("Bookmarks Manager"):
            self.book_dialog_tab.rebuild_actions()
            self.book_dialog_tab.deleteLater()

    def on_flipy(self):
        self.report_usage("on_flipy()")

        obj_list = self.collection.get_selected()
        xminlist = []
        yminlist = []
        xmaxlist = []
        ymaxlist = []

        if not obj_list:
            self.inform.emit('[WARNING_NOTCL] %s' %
                             _("No object selected to Flip on Y axis."))
        else:
            try:
                # first get a bounding box to fit all
                for obj in obj_list:
                    xmin, ymin, xmax, ymax = obj.bounds()
                    xminlist.append(xmin)
                    yminlist.append(ymin)
                    xmaxlist.append(xmax)
                    ymaxlist.append(ymax)

                # get the minimum x,y and maximum x,y for all objects selected
                xminimal = min(xminlist)
                yminimal = min(yminlist)
                xmaximal = max(xmaxlist)
                ymaximal = max(ymaxlist)

                px = 0.5 * (xminimal + xmaximal)
                py = 0.5 * (yminimal + ymaximal)

                # execute mirroring
                for obj in obj_list:
                    obj.mirror('X', [px, py])
                    obj.plot()
                    self.object_changed.emit(obj)
                self.inform.emit('[success] %s' %
                                 _("Flip on Y axis done."))
            except Exception as e:
                self.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Flip action was not executed."), str(e)))
                return

    def on_flipx(self):
        self.report_usage("on_flipx()")

        obj_list = self.collection.get_selected()
        xminlist = []
        yminlist = []
        xmaxlist = []
        ymaxlist = []

        if not obj_list:
            self.inform.emit('[WARNING_NOTCL] %s' %
                             _("No object selected to Flip on X axis."))
        else:
            try:
                # first get a bounding box to fit all
                for obj in obj_list:
                    xmin, ymin, xmax, ymax = obj.bounds()
                    xminlist.append(xmin)
                    yminlist.append(ymin)
                    xmaxlist.append(xmax)
                    ymaxlist.append(ymax)

                # get the minimum x,y and maximum x,y for all objects selected
                xminimal = min(xminlist)
                yminimal = min(yminlist)
                xmaximal = max(xmaxlist)
                ymaximal = max(ymaxlist)

                px = 0.5 * (xminimal + xmaximal)
                py = 0.5 * (yminimal + ymaximal)

                # execute mirroring
                for obj in obj_list:
                    obj.mirror('Y', [px, py])
                    obj.plot()
                    self.object_changed.emit(obj)
                self.inform.emit('[success] %s' %
                                 _("Flip on X axis done."))
            except Exception as e:
                self.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Flip action was not executed."), str(e)))
                return

    def on_rotate(self, silent=False, preset=None):
        self.report_usage("on_rotate()")

        obj_list = self.collection.get_selected()
        xminlist = []
        yminlist = []
        xmaxlist = []
        ymaxlist = []

        if not obj_list:
            self.inform.emit('[WARNING_NOTCL] %s' %
                             _("No object selected to Rotate."))
        else:
            if silent is False:
                rotatebox = FCInputDialog(title=_("Transform"), text=_("Enter the Angle value:"),
                                          min=-360, max=360, decimals=4,
                                          init_val=float(self.defaults['tools_transform_rotate']))
                num, ok = rotatebox.get_value()
            else:
                num = preset
                ok = True

            if ok:
                try:
                    # first get a bounding box to fit all
                    for obj in obj_list:
                        xmin, ymin, xmax, ymax = obj.bounds()
                        xminlist.append(xmin)
                        yminlist.append(ymin)
                        xmaxlist.append(xmax)
                        ymaxlist.append(ymax)

                    # get the minimum x,y and maximum x,y for all objects selected
                    xminimal = min(xminlist)
                    yminimal = min(yminlist)
                    xmaximal = max(xmaxlist)
                    ymaximal = max(ymaxlist)
                    px = 0.5 * (xminimal + xmaximal)
                    py = 0.5 * (yminimal + ymaximal)

                    for sel_obj in obj_list:
                        sel_obj.rotate(-float(num), point=(px, py))
                        sel_obj.plot()
                        self.object_changed.emit(sel_obj)
                    self.inform.emit('[success] %s' %
                                     _("Rotation done."))
                except Exception as e:
                    self.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Rotation movement was not executed."), str(e)))
                    return

    def on_skewx(self):
        self.report_usage("on_skewx()")

        obj_list = self.collection.get_selected()
        xminlist = []
        yminlist = []

        if not obj_list:
            self.inform.emit('[WARNING_NOTCL] %s' %
                             _("No object selected to Skew/Shear on X axis."))
        else:
            skewxbox = FCInputDialog(title=_("Transform"), text=_("Enter the Angle value:"),
                                     min=-360, max=360, decimals=4,
                                     init_val=float(self.defaults['tools_transform_skew_x']))
            num, ok = skewxbox.get_value()
            if ok:
                # first get a bounding box to fit all
                for obj in obj_list:
                    xmin, ymin, xmax, ymax = obj.bounds()
                    xminlist.append(xmin)
                    yminlist.append(ymin)

                # get the minimum x,y and maximum x,y for all objects selected
                xminimal = min(xminlist)
                yminimal = min(yminlist)

                for obj in obj_list:
                    obj.skew(num, 0, point=(xminimal, yminimal))
                    obj.plot()
                    self.object_changed.emit(obj)
                self.inform.emit('[success] %s' %
                                 _("Skew on X axis done."))

    def on_skewy(self):
        self.report_usage("on_skewy()")

        obj_list = self.collection.get_selected()
        xminlist = []
        yminlist = []

        if not obj_list:
            self.inform.emit('[WARNING_NOTCL] %s' %
                             _("No object selected to Skew/Shear on Y axis."))
        else:
            skewybox = FCInputDialog(title=_("Transform"), text=_("Enter the Angle value:"),
                                     min=-360, max=360, decimals=4,
                                     init_val=float(self.defaults['tools_transform_skew_y']))
            num, ok = skewybox.get_value()
            if ok:
                # first get a bounding box to fit all
                for obj in obj_list:
                    xmin, ymin, xmax, ymax = obj.bounds()
                    xminlist.append(xmin)
                    yminlist.append(ymin)

                # get the minimum x,y and maximum x,y for all objects selected
                xminimal = min(xminlist)
                yminimal = min(yminlist)

                for obj in obj_list:
                    obj.skew(0, num, point=(xminimal, yminimal))
                    obj.plot()
                    self.object_changed.emit(obj)
                self.inform.emit('[success] %s' %
                                 _("Skew on Y axis done."))

    def on_plots_updated(self):
        """
        Callback used to report when the plots have changed.
        Adjust axes and zooms to fit.

        :return: None
        """
        if self.is_legacy is False:
            self.plotcanvas.update()           # TODO: Need update canvas?
        else:
            self.plotcanvas.auto_adjust_axes()

        self.on_zoom_fit(None)
        self.collection.update_view()
        # self.inform.emit(_("Plots updated ..."))

    # TODO: Rework toolbar 'clear', 'replot' functions
    def on_toolbar_replot(self):
        """
        Callback for toolbar button. Re-plots all objects.

        :return: None
        """

        self.report_usage("on_toolbar_replot")
        self.log.debug("on_toolbar_replot()")

        try:
            self.collection.get_active().read_form()
        except AttributeError:
            self.log.debug("on_toolbar_replot(): AttributeError")
            pass

        self.plot_all()

    def on_row_activated(self, index):
        if index.isValid():
            if index.internalPointer().parent_item != self.collection.root_item:
                self.ui.notebook.setCurrentWidget(self.ui.selected_tab)
        self.collection.on_item_activated(index)

    def on_row_selected(self, obj_name):
        # this is a special string; when received it will make all entries unchecked
        # it mean we clicked outside of the items and deselected all
        if obj_name == 'none':
            for act in self.ui.menuobjects.actions():
                act.setChecked(False)
            return

        # get the name of the selected objects and add them to a list
        name_list = list()
        for obj in self.collection.get_selected():
            name_list.append(obj.options['name'])

        # set all actions as unchecked but the ones selected make them checked
        for act in self.ui.menuobjects.actions():
            act.setChecked(False)
            if act.text() in name_list:
                act.setChecked(True)

    def on_collection_updated(self, obj, state, old_name):
        """
        Create a menu from the object loaded in the collection.
        TODO: should use the collection model to do this

        :param obj: object that was changd (added, deleted, renamed)
        :param state: what was done with the objectCand be: added, deleted, delete_all, renamed
        :param old_name: the old name of the object before the action that triggered this slot happened
        :return: None
        """
        icon_files = {
            "gerber": "share/flatcam_icon16.png",
            "excellon": "share/drill16.png",
            "cncjob": "share/cnc16.png",
            "geometry": "share/geometry16.png",
            "script": "share/script_new16.png",
            "document": "share/notes16_1.png"
        }

        if state == 'append':
            for act in self.ui.menuobjects.actions():
                try:
                    act.triggered.disconnect()
                except TypeError:
                    pass
            self.ui.menuobjects.clear()

            gerber_list = list()
            exc_list = list()
            cncjob_list = list()
            geo_list = list()
            script_list = list()
            doc_list = list()

            for name in self.collection.get_names():
                obj_named = self.collection.get_by_name(name)
                if obj_named.kind == 'gerber':
                    gerber_list.append(name)
                elif obj_named.kind == 'excellon':
                    exc_list.append(name)
                elif obj_named.kind == 'cncjob':
                    cncjob_list.append(name)
                elif obj_named.kind == 'geometry':
                    geo_list.append(name)
                elif obj_named.kind == 'script':
                    script_list.append(name)
                elif obj_named.kind == 'document':
                    doc_list.append(name)

            def add_act(o_name):
                obj_for_icon = self.collection.get_by_name(o_name)
                add_action = QtWidgets.QAction(parent=self.ui.menuobjects)
                add_action.setCheckable(True)
                add_action.setText(o_name)
                add_action.setIcon(QtGui.QIcon(icon_files[obj_for_icon.kind]))
                add_action.triggered.connect(
                    lambda: self.collection.set_active(o_name) if add_action.isChecked() is True else
                    self.collection.set_inactive(o_name))
                self.ui.menuobjects.addAction(add_action)

            for name in gerber_list:
                add_act(name)
            self.ui.menuobjects.addSeparator()

            for name in exc_list:
                add_act(name)
            self.ui.menuobjects.addSeparator()

            for name in cncjob_list:
                add_act(name)
            self.ui.menuobjects.addSeparator()

            for name in geo_list:
                add_act(name)
            self.ui.menuobjects.addSeparator()

            for name in script_list:
                add_act(name)
            self.ui.menuobjects.addSeparator()

            for name in doc_list:
                add_act(name)

            self.ui.menuobjects.addSeparator()
            self.ui.menuobjects_selall = self.ui.menuobjects.addAction(
                QtGui.QIcon('share/select_all.png'),
                _('Select All')
            )
            self.ui.menuobjects_unselall = self.ui.menuobjects.addAction(
                QtGui.QIcon('share/deselect_all32.png'),
                _('Deselect All')
            )
            self.ui.menuobjects_selall.triggered.connect(lambda: self.on_objects_selection(True))
            self.ui.menuobjects_unselall.triggered.connect(lambda: self.on_objects_selection(False))

        elif state == 'delete':
            for act in self.ui.menuobjects.actions():
                if act.text() == obj.options['name']:
                    try:
                        act.triggered.disconnect()
                    except TypeError:
                        pass
                    self.ui.menuobjects.removeAction(act)
                    break
        elif state == 'rename':
            for act in self.ui.menuobjects.actions():
                if act.text() == old_name:
                    add_action = QtWidgets.QAction(parent=self.ui.menuobjects)
                    add_action.setText(obj.options['name'])
                    add_action.setIcon(QtGui.QIcon(icon_files[obj.kind]))
                    add_action.triggered.connect(
                        lambda: self.collection.set_active(obj.options['name']) if add_action.isChecked() is True else
                        self.collection.set_inactive(obj.options['name']))

                    self.ui.menuobjects.insertAction(act, add_action)

                    try:
                        act.triggered.disconnect()
                    except TypeError:
                        pass
                    self.ui.menuobjects.removeAction(act)
                    break
        elif state == 'delete_all':
            for act in self.ui.menuobjects.actions():
                try:
                    act.triggered.disconnect()
                except TypeError:
                    pass
            self.ui.menuobjects.clear()

            self.ui.menuobjects.addSeparator()
            self.ui.menuobjects_selall = self.ui.menuobjects.addAction(
                QtGui.QIcon('share/select_all.png'),
                _('Select All')
            )
            self.ui.menuobjects_unselall = self.ui.menuobjects.addAction(
                QtGui.QIcon('share/deselect_all32.png'),
                _('Deselect All')
            )
            self.ui.menuobjects_selall.triggered.connect(lambda: self.on_objects_selection(True))
            self.ui.menuobjects_unselall.triggered.connect(lambda: self.on_objects_selection(False))

    def on_objects_selection(self, on_off):
        obj_list = self.collection.get_names()

        if on_off is True:
            self.collection.set_all_active()
            for act in self.ui.menuobjects.actions():
                try:
                    act.setChecked(True)
                except Exception:
                    pass
            if obj_list:
                self.inform.emit('[selected] %s' % _("All objects are selected."))
        else:
            self.collection.set_all_inactive()
            for act in self.ui.menuobjects.actions():
                try:
                    act.setChecked(False)
                except Exception:
                    pass

            if obj_list:
                self.inform.emit('%s' % _("Objects selection is cleared."))
            else:
                self.inform.emit('')

    def grid_status(self):
        if self.ui.grid_snap_btn.isChecked():
            return True
        else:
            return False

    def populate_cmenu_grids(self):
        units = self.defaults['units'].lower()

        self.ui.cmenu_gridmenu.clear()
        sorted_list = sorted(self.defaults["global_grid_context_menu"][str(units)])

        grid_toggle = self.ui.cmenu_gridmenu.addAction(QtGui.QIcon('share/grid32_menu.png'), _("Grid On/Off"))
        grid_toggle.setCheckable(True)
        if self.grid_status() == True:
            grid_toggle.setChecked(True)
        else:
            grid_toggle.setChecked(False)

        self.ui.cmenu_gridmenu.addSeparator()
        for grid in sorted_list:
            action = self.ui.cmenu_gridmenu.addAction(QtGui.QIcon('share/grid32_menu.png'), "%s" % str(grid))
            action.triggered.connect(self.set_grid)

        self.ui.cmenu_gridmenu.addSeparator()
        grid_add = self.ui.cmenu_gridmenu.addAction(QtGui.QIcon('share/plus32.png'), _("Add"))
        grid_delete = self.ui.cmenu_gridmenu.addAction(QtGui.QIcon('share/delete32.png'), _("Delete"))
        grid_add.triggered.connect(self.on_grid_add)
        grid_delete.triggered.connect(self.on_grid_delete)
        grid_toggle.triggered.connect(lambda: self.ui.grid_snap_btn.trigger())

    def set_grid(self):
        self.ui.grid_gap_x_entry.setText(self.sender().text())
        self.ui.grid_gap_y_entry.setText(self.sender().text())

    def on_grid_add(self):
        # ## Current application units in lower Case
        units = self.defaults['units'].lower()

        grid_add_popup = FCInputDialog(title=_("New Grid ..."),
                                       text=_('Enter a Grid Value:'),
                                       min=0.0000, max=99.9999, decimals=4)
        grid_add_popup.setWindowIcon(QtGui.QIcon('share/plus32.png'))

        val, ok = grid_add_popup.get_value()
        if ok:
            if float(val) == 0:
                self.inform.emit('[WARNING_NOTCL] %s' %
                                 _("Please enter a grid value with non-zero value, in Float format."))
                return
            else:
                if val not in self.defaults["global_grid_context_menu"][str(units)]:
                    self.defaults["global_grid_context_menu"][str(units)].append(val)
                    self.inform.emit('[success] %s...' %
                                     _("New Grid added"))
                else:
                    self.inform.emit('[WARNING_NOTCL] %s...' %
                                     _("Grid already exists"))
        else:
            self.inform.emit('[WARNING_NOTCL] %s...' %
                             _("Adding New Grid cancelled"))

    def on_grid_delete(self):
        # ## Current application units in lower Case
        units = self.defaults['units'].lower()

        grid_del_popup = FCInputDialog(title="Delete Grid ...",
                                       text='Enter a Grid Value:',
                                       min=0.0000, max=99.9999, decimals=4)
        grid_del_popup.setWindowIcon(QtGui.QIcon('share/delete32.png'))

        val, ok = grid_del_popup.get_value()
        if ok:
            if float(val) == 0:
                self.inform.emit('[WARNING_NOTCL] %s' %
                                 _("Please enter a grid value with non-zero value, in Float format."))
                return
            else:
                try:
                    self.defaults["global_grid_context_menu"][str(units)].remove(val)
                except ValueError:
                    self.inform.emit('[ERROR_NOTCL]%s...' %
                                     _(" Grid Value does not exist"))
                    return
                self.inform.emit('[success] %s...' %
                                 _("Grid Value deleted"))
        else:
            self.inform.emit('[WARNING_NOTCL] %s...' %
                             _("Delete Grid value cancelled"))

    def on_shortcut_list(self):
        self.report_usage("on_shortcut_list()")

        # add the tab if it was closed
        self.ui.plot_tab_area.addTab(self.ui.shortcuts_tab, _("Key Shortcut List"))

        # delete the absolute and relative position and messages in the infobar
        self.ui.position_label.setText("")
        self.ui.rel_position_label.setText("")

        # Switch plot_area to preferences page
        self.ui.plot_tab_area.setCurrentWidget(self.ui.shortcuts_tab)
        # self.ui.show()

    def on_select_tab(self, name):
        # if the splitter is hidden, display it, else hide it but only if the current widget is the same
        if self.ui.splitter.sizes()[0] == 0:
            self.ui.splitter.setSizes([1, 1])
        else:
            if self.ui.notebook.currentWidget().objectName() == name + '_tab':
                self.ui.splitter.setSizes([0, 1])

        if name == 'project':
            self.ui.notebook.setCurrentWidget(self.ui.project_tab)
        elif name == 'selected':
            self.ui.notebook.setCurrentWidget(self.ui.selected_tab)
        elif name == 'tool':
            self.ui.notebook.setCurrentWidget(self.ui.tool_tab)

    def on_copy_name(self):
        self.report_usage("on_copy_name()")

        obj = self.collection.get_active()
        try:
            name = obj.options["name"]
        except AttributeError:
            log.debug("on_copy_name() --> No object selected to copy it's name")
            self.inform.emit('[WARNING_NOTCL]%s' %
                             _(" No object selected to copy it's name"))
            return

        self.clipboard.setText(name)
        self.inform.emit(_("Name copied on clipboard ..."))

    def on_mouse_click_over_plot(self, event):
        """
        Default actions are:
        :param event: Contains information about the event, like which button
            was clicked, the pixel coordinates and the axes coordinates.
        :return: None
        """
        self.pos = []

        if self.is_legacy is False:
            event_pos = event.pos
            if self.defaults["global_pan_button"] == '2':
                pan_button = 2
            else:
                pan_button = 3
            # Set the mouse button for panning
            self.plotcanvas.view.camera.pan_button_setting = pan_button
        else:
            event_pos = (event.xdata, event.ydata)
            # Matplotlib has the middle and right buttons mapped in reverse compared with VisPy
            if self.defaults["global_pan_button"] == '2':
                pan_button = 3
            else:
                pan_button = 2

        # So it can receive key presses
        self.plotcanvas.native.setFocus()

        self.pos_canvas = self.plotcanvas.translate_coords(event_pos)

        if self.grid_status() == True:
            self.pos = self.geo_editor.snap(self.pos_canvas[0], self.pos_canvas[1])
        else:
            self.pos = (self.pos_canvas[0], self.pos_canvas[1])

        try:
            if event.button == 1:
                # Reset here the relative coordinates so there is a new reference on the click position
                if self.rel_point1 is None:
                    self.rel_point1 = self.pos
                else:
                    self.rel_point2 = copy(self.rel_point1)
                    self.rel_point1 = self.pos

            self.on_mouse_move_over_plot(event, origin_click=True)
        except Exception as e:
            App.log.debug("App.on_mouse_click_over_plot() --> Outside plot? --> %s" % str(e))

    def on_mouse_double_click_over_plot(self, event):
        if event.button == 1:
            self.doubleclick = True

    def on_mouse_move_over_plot(self, event, origin_click=None):
        """
        Callback for the mouse motion event over the plot.

        :param event: Contains information about the event.
        :param origin_click
        :return: None
        """

        if self.is_legacy is False:
            event_pos = event.pos
            if self.defaults["global_pan_button"] == '2':
                pan_button = 2
            else:
                pan_button = 3
            self.event_is_dragging = event.is_dragging
        else:
            event_pos = (event.xdata, event.ydata)
            # Matplotlib has the middle and right buttons mapped in reverse compared with VisPy
            if self.defaults["global_pan_button"] == '2':
                pan_button = 3
            else:
                pan_button = 2
            self.event_is_dragging = self.plotcanvas.is_dragging

        # So it can receive key presses
        self.plotcanvas.native.setFocus()
        self.pos_jump = event_pos

        self.ui.popMenu.mouse_is_panning = False

        if not origin_click:
            # if the RMB is clicked and mouse is moving over plot then 'panning_action' is True
            if event.button == pan_button and self.event_is_dragging == 1:
                self.ui.popMenu.mouse_is_panning = True
                return

        if self.rel_point1 is not None:
            try:  # May fail in case mouse not within axes
                pos_canvas = self.plotcanvas.translate_coords(event_pos)

                if self.grid_status() == True:
                    pos = self.geo_editor.snap(pos_canvas[0], pos_canvas[1])

                    # Update cursor
                    self.app_cursor.set_data(np.asarray([(pos[0], pos[1])]),
                                             symbol='++', edge_color=self.cursor_color_3D,
                                             size=self.defaults["global_cursor_size"])
                else:
                    pos = (pos_canvas[0], pos_canvas[1])

                self.ui.position_label.setText("&nbsp;&nbsp;&nbsp;&nbsp;<b>X</b>: %.4f&nbsp;&nbsp;   "
                                               "<b>Y</b>: %.4f" % (pos[0], pos[1]))

                dx = pos[0] - float(self.rel_point1[0])
                dy = pos[1] - float(self.rel_point1[1])
                self.ui.rel_position_label.setText("<b>Dx</b>: %.4f&nbsp;&nbsp;  <b>Dy</b>: "
                                                   "%.4f&nbsp;&nbsp;&nbsp;&nbsp;" % (dx, dy))
                self.mouse = [pos[0], pos[1]]

                # if the mouse is moved and the LMB is clicked then the action is a selection
                if self.event_is_dragging == 1 and event.button == 1:
                    self.delete_selection_shape()
                    if dx < 0:
                        self.draw_moving_selection_shape(self.pos, pos, color=self.defaults['global_alt_sel_line'],
                                                         face_color=self.defaults['global_alt_sel_fill'])
                        self.selection_type = False
                    elif dx > 0:
                        self.draw_moving_selection_shape(self.pos, pos)
                        self.selection_type = True
                    else:
                        self.selection_type = None

                # hover effect - enabled in Preferences -> General -> GUI Settings
                if self.defaults['global_hover']:
                    for obj in self.collection.get_list():
                        try:
                            # select the object(s) only if it is enabled (plotted)
                            if obj.options['plot']:
                                if obj not in self.collection.get_selected():
                                    poly_obj = Polygon(
                                        [(obj.options['xmin'], obj.options['ymin']),
                                         (obj.options['xmax'], obj.options['ymin']),
                                         (obj.options['xmax'], obj.options['ymax']),
                                         (obj.options['xmin'], obj.options['ymax'])]
                                    )
                                    if Point(pos).within(poly_obj):
                                        if obj.isHovering is False:
                                            obj.isHovering = True
                                            obj.notHovering = True
                                            # create the selection box around the selected object
                                            self.draw_hover_shape(obj, color='#d1e0e0FF')
                                    else:
                                        if obj.notHovering is True:
                                            obj.notHovering = False
                                            obj.isHovering = False
                                            self.delete_hover_shape()
                        except Exception:
                            # the Exception here will happen if we try to select on screen and we have an
                            # newly (and empty) just created Geometry or Excellon object that do not have the
                            # xmin, xmax, ymin, ymax options.
                            # In this case poly_obj creation (see above) will fail
                            pass

            except Exception:
                self.ui.position_label.setText("")
                self.ui.rel_position_label.setText("")
                self.mouse = None

    def on_mouse_click_release_over_plot(self, event):
        """
        Callback for the mouse click release over plot. This event is generated by the Matplotlib backend
        and has been registered in ''self.__init__()''.
        :param event: contains information about the event.
        :return:
        """

        if self.is_legacy is False:
            event_pos = event.pos
            right_button = 2
        else:
            event_pos = (event.xdata, event.ydata)
            # Matplotlib has the middle and right buttons mapped in reverse compared with VisPy
            right_button = 3

        pos_canvas = self.plotcanvas.translate_coords(event_pos)
        if self.grid_status() == True:
            pos = self.geo_editor.snap(pos_canvas[0], pos_canvas[1])
        else:
            pos = (pos_canvas[0], pos_canvas[1])

        # if the released mouse button was RMB then test if it was a panning motion or not, if not it was a context
        # canvas menu
        if event.button == right_button and self.ui.popMenu.mouse_is_panning is False:  # right click
            self.cursor = QtGui.QCursor()
            self.populate_cmenu_grids()
            self.ui.popMenu.popup(self.cursor.pos())

        # if the released mouse button was LMB then test if we had a right-to-left selection or a left-to-right
        # selection and then select a type of selection ("enclosing" or "touching")

        if event.button == 1:  # left click
            modifiers = QtWidgets.QApplication.keyboardModifiers()
            # If the SHIFT key is pressed when LMB is clicked then the coordinates are copied to clipboard
            if modifiers == QtCore.Qt.ShiftModifier:
                # do not auto open the Project Tab
                self.click_noproject = True

                self.clipboard.setText(self.defaults["global_point_clipboard_format"] % (self.pos[0], self.pos[1]))
                self.inform.emit('[success] %s' % _("Coordinates copied to clipboard."))
                return

            if self.doubleclick is True:
                self.doubleclick = False
                if self.collection.get_selected():
                    self.ui.notebook.setCurrentWidget(self.ui.selected_tab)
                    if self.ui.splitter.sizes()[0] == 0:
                        self.ui.splitter.setSizes([1, 1])
                    try:
                        # delete the selection shape(S) as it may be in the way
                        self.delete_selection_shape()
                        self.delete_hover_shape()
                    except Exception as e:
                        log.warning("FlatCAMApp.on_mouse_click_release_over_plot() double click --> Error: %s" % str(e))
                        return
            else:
                if self.selection_type is not None:
                    try:
                        self.selection_area_handler(self.pos, pos, self.selection_type)
                        self.selection_type = None
                    except Exception as e:
                        log.warning("FlatCAMApp.on_mouse_click_release_over_plot() select area --> Error: %s" % str(e))
                        return
                else:
                    key_modifier = QtWidgets.QApplication.keyboardModifiers()

                    if key_modifier == QtCore.Qt.ShiftModifier:
                        mod_key = 'Shift'
                    elif key_modifier == QtCore.Qt.ControlModifier:
                        mod_key = 'Control'
                    else:
                        mod_key = None

                    try:
                        if mod_key == self.defaults["global_mselect_key"]:
                            # If the CTRL key is pressed when the LMB is clicked then if the object is selected it will
                            # deselect, and if it's not selected then it will be selected
                            # If there is no active command (self.command_active is None) then we check if we clicked
                            # on a object by checking the bounding limits against mouse click position
                            if self.command_active is None:
                                self.select_objects(key='CTRL')
                                self.delete_hover_shape()
                        else:
                            # If there is no active command (self.command_active is None) then we check if we clicked
                            # on a object by checking the bounding limits against mouse click position
                            if self.command_active is None:
                                self.select_objects()
                                self.delete_hover_shape()
                    except Exception as e:
                        log.warning("FlatCAMApp.on_mouse_click_release_over_plot() select click --> Error: %s" % str(e))
                        return

    def selection_area_handler(self, start_pos, end_pos, sel_type):
        """
        :param start_pos: mouse position when the selection LMB click was done
        :param end_pos: mouse position when the left mouse button is released
        :param sel_type: if True it's a left to right selection (enclosure), if False it's a 'touch' selection
        :return:
        """
        poly_selection = Polygon([start_pos, (end_pos[0], start_pos[1]), end_pos, (start_pos[0], end_pos[1])])

        # delete previous selection shape
        self.delete_selection_shape()

        # make all objects inactive
        self.collection.set_all_inactive()
        
        for obj in self.collection.get_list():
            try:
                # select the object(s) only if it is enabled (plotted)
                if obj.options['plot']:
                    poly_obj = Polygon([(obj.options['xmin'], obj.options['ymin']),
                                        (obj.options['xmax'], obj.options['ymin']),
                                        (obj.options['xmax'], obj.options['ymax']),
                                        (obj.options['xmin'], obj.options['ymax'])])
                    if sel_type is True:
                        if poly_obj.within(poly_selection):
                            # create the selection box around the selected object
                            if self.defaults['global_selection_shape'] is True:
                                self.draw_selection_shape(obj)
                            self.collection.set_active(obj.options['name'])
                    else:
                        if poly_selection.intersects(poly_obj):
                            # create the selection box around the selected object
                            if self.defaults['global_selection_shape'] is True:
                                self.draw_selection_shape(obj)
                            self.collection.set_active(obj.options['name'])
            except Exception as e:
                # the Exception here will happen if we try to select on screen and we have an newly (and empty)
                # just created Geometry or Excellon object that do not have the xmin, xmax, ymin, ymax options.
                # In this case poly_obj creation (see above) will fail
                log.debug("App.selection_area_handler() --> %s" % str(e))

    def select_objects(self, key=None):
        """
        Will select objects clicked on canvas

        :param key: for future use in cumulative selection
        :return:
        """

        # list where we store the overlapped objects under our mouse left click position
        objects_under_the_click_list = []

        # Populate the list with the overlapped objects on the click position
        curr_x, curr_y = self.pos

        for obj in self.all_objects_list:
            # FlatCAMScript and FlatCAMDocument objects can't be selected
            if isinstance(obj, FlatCAMScript) or isinstance(obj, FlatCAMDocument):
                continue

            if (curr_x >= obj.options['xmin']) and (curr_x <= obj.options['xmax']) and \
                    (curr_y >= obj.options['ymin']) and (curr_y <= obj.options['ymax']):
                if obj.options['name'] not in objects_under_the_click_list:
                    if obj.options['plot']:
                        # add objects to the objects_under_the_click list only if the object is plotted
                        # (active and not disabled)
                        objects_under_the_click_list.append(obj.options['name'])

        try:
            if objects_under_the_click_list:
                curr_sel_obj = self.collection.get_active()
                # case when there is only an object under the click and we toggle it
                if len(objects_under_the_click_list) == 1:
                    if curr_sel_obj is None:
                        self.collection.set_active(objects_under_the_click_list[0])
                        curr_sel_obj = self.collection.get_active()

                        # create the selection box around the selected object
                        if self.defaults['global_selection_shape'] is True:
                            self.draw_selection_shape(curr_sel_obj)

                    elif self.collection.get_active().options['name'] not in objects_under_the_click_list:
                        self.on_objects_selection(False)
                        self.delete_selection_shape()

                        self.collection.set_active(objects_under_the_click_list[0])
                        curr_sel_obj = self.collection.get_active()

                        # create the selection box around the selected object
                        if self.defaults['global_selection_shape'] is True:
                            self.draw_selection_shape(curr_sel_obj)

                        self.selected_message(curr_sel_obj=curr_sel_obj)

                    else:
                        self.on_objects_selection(False)
                        self.delete_selection_shape()

                        if self.call_source != 'app':
                            self.call_source = 'app'

                    self.selected_message(curr_sel_obj=curr_sel_obj)

                else:
                    # If there is no selected object
                    # make active the first element of the overlapped objects list
                    if self.collection.get_active() is None:
                        self.collection.set_active(objects_under_the_click_list[0])

                    name_sel_obj = self.collection.get_active().options['name']
                    # In case that there is a selected object but it is not in the overlapped object list
                    # make that object inactive and activate the first element in the overlapped object list
                    if name_sel_obj not in objects_under_the_click_list:
                        self.collection.set_inactive(name_sel_obj)
                        name_sel_obj = objects_under_the_click_list[0]
                        self.collection.set_active(name_sel_obj)
                    else:
                        sel_idx = objects_under_the_click_list.index(name_sel_obj)
                        self.collection.set_all_inactive()
                        self.collection.set_active(objects_under_the_click_list[(sel_idx + 1) %
                                                                                len(objects_under_the_click_list)])

                    curr_sel_obj = self.collection.get_active()
                    # delete the possible selection box around a possible selected object
                    self.delete_selection_shape()
                    # create the selection box around the selected object
                    if self.defaults['global_selection_shape'] is True:
                        self.draw_selection_shape(curr_sel_obj)

                    self.selected_message(curr_sel_obj=curr_sel_obj)

            else:
                # deselect everything
                self.on_objects_selection(False)
                # delete the possible selection box around a possible selected object
                self.delete_selection_shape()

                # and as a convenience move the focus to the Project tab because Selected tab is now empty but
                # only when working on App
                if self.call_source == 'app':
                    if self.click_noproject is False:
                        self.ui.notebook.setCurrentWidget(self.ui.project_tab)
                    else:
                        # restore auto open the Project Tab
                        self.click_noproject = False

                    # delete any text in the status bar, implicitly the last object name that was selected
                    # self.inform.emit("")
                else:
                    self.call_source = 'app'
        except Exception as e:
            log.error("[ERROR] Something went bad in App.select_objects(). %s" % str(e))

    def selected_message(self, curr_sel_obj):
        if curr_sel_obj:
            if curr_sel_obj.kind == 'gerber':
                self.inform.emit(_('[selected]<span style="color:{color};">{name}</span> selected').format(
                    color='green', name=str(curr_sel_obj.options['name'])))
            elif curr_sel_obj.kind == 'excellon':
                self.inform.emit(_('[selected]<span style="color:{color};">{name}</span> selected').format(
                    color='brown', name=str(curr_sel_obj.options['name'])))
            elif curr_sel_obj.kind == 'cncjob':
                self.inform.emit(_('[selected]<span style="color:{color};">{name}</span> selected').format(
                    color='blue', name=str(curr_sel_obj.options['name'])))
            elif curr_sel_obj.kind == 'geometry':
                self.inform.emit(_('[selected]<span style="color:{color};">{name}</span> selected').format(
                    color='red', name=str(curr_sel_obj.options['name'])))

    def delete_hover_shape(self):
        self.hover_shapes.clear()
        self.hover_shapes.redraw()

    def draw_hover_shape(self, sel_obj, color=None):
        """

        :param sel_obj: the object for which the hover shape must be drawn
        :return:
        """

        pt1 = (float(sel_obj.options['xmin']), float(sel_obj.options['ymin']))
        pt2 = (float(sel_obj.options['xmax']), float(sel_obj.options['ymin']))
        pt3 = (float(sel_obj.options['xmax']), float(sel_obj.options['ymax']))
        pt4 = (float(sel_obj.options['xmin']), float(sel_obj.options['ymax']))

        hover_rect = Polygon([pt1, pt2, pt3, pt4])
        if self.defaults['units'].upper() == 'MM':
            hover_rect = hover_rect.buffer(-0.1)
            hover_rect = hover_rect.buffer(0.2)

        else:
            hover_rect = hover_rect.buffer(-0.00393)
            hover_rect = hover_rect.buffer(0.00787)

        # if color:
        #     face = Color(color)
        #     face.alpha = 0.2
        #     outline = Color(color, alpha=0.8)
        # else:
        #     face = Color(self.defaults['global_sel_fill'])
        #     face.alpha = 0.2
        #     outline = self.defaults['global_sel_line']

        if color:
            face = color[:-2] + str(hex(int(0.2 * 255)))[2:]
            outline = color[:-2] + str(hex(int(0.8 * 255)))[2:]
        else:
            face = self.defaults['global_sel_fill'][:-2] + str(hex(int(0.2 * 255)))[2:]
            outline = self.defaults['global_sel_line']

        self.hover_shapes.add(hover_rect, color=outline, face_color=face, update=True, layer=0, tolerance=None)

        if self.is_legacy is True:
            self.hover_shapes.redraw()

    def delete_selection_shape(self):
        self.move_tool.sel_shapes.clear()
        self.move_tool.sel_shapes.redraw()

    def draw_selection_shape(self, sel_obj, color=None):
        """

        :param sel_obj: the object for which the selection shape must be drawn
        :return:
        """

        if sel_obj is None:
            return

        pt1 = (float(sel_obj.options['xmin']), float(sel_obj.options['ymin']))
        pt2 = (float(sel_obj.options['xmax']), float(sel_obj.options['ymin']))
        pt3 = (float(sel_obj.options['xmax']), float(sel_obj.options['ymax']))
        pt4 = (float(sel_obj.options['xmin']), float(sel_obj.options['ymax']))

        sel_rect = Polygon([pt1, pt2, pt3, pt4])
        if self.defaults['units'].upper() == 'MM':
            sel_rect = sel_rect.buffer(-0.1)
            sel_rect = sel_rect.buffer(0.2)
        else:
            sel_rect = sel_rect.buffer(-0.00393)
            sel_rect = sel_rect.buffer(0.00787)

        if color:
            face = color[:-2] + str(hex(int(0.2 * 255)))[2:]
            outline = color[:-2] + str(hex(int(0.8 * 255)))[2:]
        else:
            if self.is_legacy is False:
                face = self.defaults['global_sel_fill'][:-2] + str(hex(int(0.2 * 255)))[2:]
                outline = self.defaults['global_sel_line'][:-2] + str(hex(int(0.8 * 255)))[2:]
            else:
                face = self.defaults['global_sel_fill'][:-2] + str(hex(int(0.4 * 255)))[2:]
                outline = self.defaults['global_sel_line'][:-2] + str(hex(int(1.0 * 255)))[2:]

        self.sel_objects_list.append(self.move_tool.sel_shapes.add(sel_rect,
                                                                   color=outline,
                                                                   face_color=face,
                                                                   update=True,
                                                                   layer=0,
                                                                   tolerance=None))
        if self.is_legacy is True:
            self.move_tool.sel_shapes.redraw()

    def draw_moving_selection_shape(self, old_coords, coords, **kwargs):
        """

        :param old_coords: old coordinates
        :param coords: new coordinates
        :return:
        """

        if 'color' in kwargs:
            color = kwargs['color']
        else:
            color = self.defaults['global_sel_line']

        if 'face_color' in kwargs:
            face_color = kwargs['face_color']
        else:
            face_color = self.defaults['global_sel_fill']

        if 'face_alpha' in kwargs:
            face_alpha = kwargs['face_alpha']
        else:
            face_alpha = 0.3

        x0, y0 = old_coords
        x1, y1 = coords

        pt1 = (x0, y0)
        pt2 = (x1, y0)
        pt3 = (x1, y1)
        pt4 = (x0, y1)
        sel_rect = Polygon([pt1, pt2, pt3, pt4])

        # color_t = Color(face_color)
        # color_t.alpha = face_alpha

        color_t = face_color[:-2] + str(hex(int(face_alpha * 255)))[2:]

        self.move_tool.sel_shapes.add(sel_rect, color=color, face_color=color_t, update=True,
                                      layer=0, tolerance=None)
        if self.is_legacy is True:
            self.move_tool.sel_shapes.redraw()

    def on_file_new_click(self):
        if self.collection.get_list() and self.should_we_save:
            msgbox = QtWidgets.QMessageBox()
            # msgbox.setText("<B>Save changes ...</B>")
            msgbox.setText(_("There are files/objects opened in FlatCAM.\n"
                             "Creating a New project will delete them.\n"
                             "Do you want to Save the project?"))
            msgbox.setWindowTitle(_("Save changes"))
            msgbox.setWindowIcon(QtGui.QIcon('share/save_as.png'))
            bt_yes = msgbox.addButton(_('Yes'), QtWidgets.QMessageBox.YesRole)
            bt_no = msgbox.addButton(_('No'), QtWidgets.QMessageBox.NoRole)
            bt_cancel = msgbox.addButton(_('Cancel'), QtWidgets.QMessageBox.RejectRole)

            msgbox.setDefaultButton(bt_yes)
            msgbox.exec_()
            response = msgbox.clickedButton()

            if response == bt_yes:
                self.on_file_saveprojectas()
            elif response == bt_cancel:
                return
            elif response == bt_no:
                self.on_file_new()
        else:
            self.on_file_new()
        self.inform.emit('[success] %s...' %
                         _("New Project created"))

    def on_file_new(self, cli=None):
        """
        Callback for menu item File -> New. Returns the application to its
        startup state. This method is thread-safe.

        :return: None
        """

        self.report_usage("on_file_new")

        # Remove everything from memory
        App.log.debug("on_file_new()")

        if self.call_source != 'app':
            self.editor2object(cleanup=True)
            # ## EDITOR section
            self.geo_editor = FlatCAMGeoEditor(self, disabled=True)
            self.exc_editor = FlatCAMExcEditor(self)
            self.grb_editor = FlatCAMGrbEditor(self)

        # Clear pool
        self.clear_pool()

        for obj in self.collection.get_list():
            # delete shapes left drawn from mark shape_collections, if any
            if isinstance(obj, FlatCAMGerber):
                try:
                    obj.mark_shapes.enabled = False
                    obj.mark_shapes.clear(update=True)
                except AttributeError:
                    pass

            # also delete annotation shapes, if any
            elif isinstance(obj, FlatCAMCNCjob):
                try:
                    obj.annotation.enabled = False
                    obj.annotation.clear(update=True)
                except AttributeError:
                    pass

        # tcl needs to be reinitialized, otherwise old shell variables etc  remains
        self.init_tcl()

        self.delete_selection_shape()
        self.collection.delete_all()

        self.setup_component_editor()

        # Clear project filename
        self.project_filename = None

        # Load the application defaults
        self.load_defaults(filename='current_defaults')

        # Re-fresh project options
        self.on_options_app2project()

        # Init Tools
        self.init_tools()

        if cli is None:
            # Close any Tabs opened in the Plot Tab Area section
            for index in range(self.ui.plot_tab_area.count()):
                self.ui.plot_tab_area.closeTab(index)
                # for whatever reason previous command does not close the last tab so I do it manually
            self.ui.plot_tab_area.closeTab(0)

            # # And then add again the Plot Area
            self.ui.plot_tab_area.addTab(self.ui.plot_tab, "Plot Area")
            self.ui.plot_tab_area.protectTab(0)

        # take the focus of the Notebook on Project Tab.
        self.ui.notebook.setCurrentWidget(self.ui.project_tab)

        self.set_ui_title(name=_("New Project - Not saved"))

    def obj_properties(self):
        """
        Will launch the object Properties Tool
        :return:
        """

        self.report_usage("obj_properties()")
        self.properties_tool.run(toggle=False)

    def on_project_context_save(self):
        """
        Wrapper, will save the object function of it's type
        :return:
        """

        obj = self.collection.get_active()
        if type(obj) == FlatCAMGeometry:
            self.on_file_exportdxf()
        elif type(obj) == FlatCAMExcellon:
            self.on_file_saveexcellon()
        elif type(obj) == FlatCAMCNCjob:
            obj.on_exportgcode_button_click()
        elif type(obj) == FlatCAMGerber:
            self.on_file_savegerber()
        elif type(obj) == FlatCAMScript:
            self.on_file_savescript()
        elif type(obj) == FlatCAMDocument:
            self.on_file_savedocument()

    def obj_move(self):
        self.report_usage("obj_move()")
        self.move_tool.run(toggle=False)

    def on_fileopengerber(self, signal: bool = None, name=None):
        """
        File menu callback for opening a Gerber.

        :param signal: required because clicking the entry will generate a checked signal which needs a container
        :return: None
        """

        self.report_usage("on_fileopengerber")
        App.log.debug("on_fileopengerber()")

        _filter_ = "Gerber Files (*.gbr *.ger *.gtl *.gbl *.gts *.gbs *.gtp *.gbp *.gto *.gbo *.gm1 *.gml *.gm3 *" \
                   ".gko *.cmp *.sol *.stc *.sts *.plc *.pls *.crc *.crs *.tsm *.bsm *.ly2 *.ly15 *.dim *.mil *.grb" \
                   "*.top *.bot *.smt *.smb *.sst *.ssb *.spt *.spb *.pho *.gdo *.art *.gbd *.gb*);;" \
                   "Protel Files (*.gtl *.gbl *.gts *.gbs *.gto *.gbo *.gtp *.gbp *.gml *.gm1 *.gm3 *.gko);;" \
                   "Eagle Files (*.cmp *.sol *.stc *.sts *.plc *.pls *.crc *.crs *.tsm *.bsm *.ly2 *.ly15 *.dim " \
                   "*.mil);;" \
                   "OrCAD Files (*.top *.bot *.smt *.smb *.sst *.ssb *.spt *.spb);;" \
                   "Allegro Files (*.art);;" \
                   "Mentor Files (*.pho *.gdo);;" \
                   "All Files (*.*)"

        if name is None:
            try:
                filenames, _f = QtWidgets.QFileDialog.getOpenFileNames(caption=_("Open Gerber"),
                                                                       directory=self.get_last_folder(),
                                                                       filter=_filter_)
            except TypeError:
                filenames, _f = QtWidgets.QFileDialog.getOpenFileNames(caption=_("Open Gerber"), filter=_filter_)

            filenames = [str(filename) for filename in filenames]
        else:
            filenames = [name]
            self.splash.showMessage('%s: %ssec\n%s' % (_("Canvas initialization started.\n"
                                                         "Canvas initialization finished in"), '%.2f' % self.used_time,
                                                       _("Opening Gerber file.")),
                                    alignment=Qt.AlignBottom | Qt.AlignLeft,
                                    color=QtGui.QColor("gray"))

        if len(filenames) == 0:
            self.inform.emit('[WARNING_NOTCL] %s' %
                             _("Open Gerber cancelled."))
        else:
            for filename in filenames:
                if filename != '':
                    self.worker_task.emit({'fcn': self.open_gerber, 'params': [filename]})

    def on_fileopenexcellon(self, signal: bool = None, name=None):
        """
        File menu callback for opening an Excellon file.

        :param signal: required because clicking the entry will generate a checked signal which needs a container
        :return: None
        """

        self.report_usage("on_fileopenexcellon")
        App.log.debug("on_fileopenexcellon()")

        _filter_ = "Excellon Files (*.drl *.txt *.xln *.drd *.tap *.exc *.ncd);;" \
                   "All Files (*.*)"
        if name is None:
            try:
                filenames, _f = QtWidgets.QFileDialog.getOpenFileNames(caption=_("Open Excellon"),
                                                                       directory=self.get_last_folder(),
                                                                       filter=_filter_)
            except TypeError:
                filenames, _f = QtWidgets.QFileDialog.getOpenFileNames(caption=_("Open Excellon"), filter=_filter_)
            filenames = [str(filename) for filename in filenames]
        else:
            filenames = [str(name)]
            self.splash.showMessage('%s: %ssec\n%s' % (_("Canvas initialization started.\n"
                                                         "Canvas initialization finished in"), '%.2f' % self.used_time,
                                                       _("Opening Excellon file.")),
                                    alignment=Qt.AlignBottom | Qt.AlignLeft,
                                    color=QtGui.QColor("gray"))

        if len(filenames) == 0:
            self.inform.emit('[WARNING_NOTCL]%s' %
                             _(" Open Excellon cancelled."))
        else:
            for filename in filenames:
                if filename != '':
                    self.worker_task.emit({'fcn': self.open_excellon, 'params': [filename]})

    def on_fileopengcode(self, signal: bool = None, name=None):
        """
        File menu call back for opening gcode.

        :param signal: required because clicking the entry will generate a checked signal which needs a container
        :return: None
        """

        self.report_usage("on_fileopengcode")
        App.log.debug("on_fileopengcode()")

        # https://bobcadsupport.com/helpdesk/index.php?/Knowledgebase/Article/View/13/5/known-g-code-file-extensions
        _filter_ = "G-Code Files (*.txt *.nc *.ncc *.tap *.gcode *.cnc *.ecs *.fnc *.dnc *.ncg *.gc *.fan *.fgc" \
                   " *.din *.xpi *.hnc *.h *.i *.ncp *.min *.gcd *.rol *.mpr *.ply *.out *.eia *.plt *.sbp *.mpf);;" \
                   "All Files (*.*)"

        if name is None:
            try:
                filenames, _f = QtWidgets.QFileDialog.getOpenFileNames(caption=_("Open G-Code"),
                                                                       directory=self.get_last_folder(),
                                                                       filter=_filter_)
            except TypeError:
                filenames, _f = QtWidgets.QFileDialog.getOpenFileNames(caption=_("Open G-Code"), filter=_filter_)

            filenames = [str(filename) for filename in filenames]
        else:
            filenames = [name]
            self.splash.showMessage('%s: %ssec\n%s' % (_("Canvas initialization started.\n"
                                                         "Canvas initialization finished in"), '%.2f' % self.used_time,
                                                       _("Opening G-Code file.")),
                                    alignment=Qt.AlignBottom | Qt.AlignLeft,
                                    color=QtGui.QColor("gray"))

        if len(filenames) == 0:
            self.inform.emit('[WARNING_NOTCL] %s' %
                             _("Open G-Code cancelled."))
        else:
            for filename in filenames:
                if filename != '':
                    self.worker_task.emit({'fcn': self.open_gcode, 'params': [filename, None, True]})

    def on_file_openproject(self, signal: bool = None):
        """
        File menu callback for opening a project.

        :param signal: required because clicking the entry will generate a checked signal which needs a container
        :return: None
        """

        self.report_usage("on_file_openproject")
        App.log.debug("on_file_openproject()")
        _filter_ = "FlatCAM Project (*.FlatPrj);;All Files (*.*)"
        try:
            filename, _f = QtWidgets.QFileDialog.getOpenFileName(caption=_("Open Project"),
                                                                 directory=self.get_last_folder(), filter=_filter_)
        except TypeError:
            filename, _f = QtWidgets.QFileDialog.getOpenFileName(caption=_("Open Project"), filter=_filter_)

        # The Qt methods above will return a QString which can cause problems later.
        # So far json.dump() will fail to serialize it.
        # TODO: Improve the serialization methods and remove this fix.
        filename = str(filename)

        if filename == "":
            self.inform.emit('[WARNING_NOTCL] %s' %
                             _("Open Project cancelled."))
        else:
            # self.worker_task.emit({'fcn': self.open_project,
            #                        'params': [filename]})
            # The above was failing because open_project() is not
            # thread safe. The new_project()
            self.open_project(filename)

    def on_file_openconfig(self, signal: bool = None):
        """
        File menu callback for opening a config file.

        :param signal: required because clicking the entry will generate a checked signal which needs a container
        :return: None
        """

        self.report_usage("on_file_openconfig")
        App.log.debug("on_file_openconfig()")
        _filter_ = "FlatCAM Config (*.FlatConfig);;FlatCAM Config (*.json);;All Files (*.*)"
        try:
            filename, _f = QtWidgets.QFileDialog.getOpenFileName(caption=_("Open Configuration File"),
                                                                 directory=self.data_path, filter=_filter_)
        except TypeError:
            filename, _f = QtWidgets.QFileDialog.getOpenFileName(caption=_("Open Configuration File"),
                                                                 filter=_filter_)

        if filename == "":
            self.inform.emit('[WARNING_NOTCL] %s' %
                             _("Open Config cancelled."))
        else:
            self.open_config_file(filename)

    def on_file_exportsvg(self):
        """
        Callback for menu item File->Export SVG.

        :return: None
        """
        self.report_usage("on_file_exportsvg")
        App.log.debug("on_file_exportsvg()")

        obj = self.collection.get_active()
        if obj is None:
            self.inform.emit('[WARNING_NOTCL] %s' %
                             _("No object selected."))
            msg = _("Please Select a Geometry object to export")
            msgbox = QtWidgets.QMessageBox()
            msgbox.setInformativeText(msg)
            bt_ok = msgbox.addButton(_('Ok'), QtWidgets.QMessageBox.AcceptRole)
            msgbox.setDefaultButton(bt_ok)
            msgbox.exec_()
            return

        # Check for more compatible types and add as required
        if (not isinstance(obj, FlatCAMGeometry)
                and not isinstance(obj, FlatCAMGerber)
                and not isinstance(obj, FlatCAMCNCjob)
                and not isinstance(obj, FlatCAMExcellon)):
            msg = '[ERROR_NOTCL] %s' % \
                  _("Only Geometry, Gerber and CNCJob objects can be used.")
            msgbox = QtWidgets.QMessageBox()
            msgbox.setInformativeText(msg)
            bt_ok = msgbox.addButton(_('Ok'), QtWidgets.QMessageBox.AcceptRole)
            msgbox.setDefaultButton(bt_ok)
            msgbox.exec_()
            return

        name = obj.options["name"]

        _filter = "SVG File (*.svg);;All Files (*.*)"
        try:
            filename, _f = QtWidgets.QFileDialog.getSaveFileName(
                caption=_("Export SVG"),
                directory=self.get_last_save_folder() + '/' + str(name) + '_svg',
                filter=_filter)
        except TypeError:
            filename, _f = QtWidgets.QFileDialog.getSaveFileName(caption=_("Export SVG"), filter=_filter)

        filename = str(filename)

        if filename == "":
            self.inform.emit('[WARNING_NOTCL]%s' %
                             _(" Export SVG cancelled."))
            return
        else:
            self.export_svg(name, filename)
            if self.defaults["global_open_style"] is False:
                self.file_opened.emit("SVG", filename)
            self.file_saved.emit("SVG", filename)

    def on_file_exportpng(self):
        self.report_usage("on_file_exportpng")
        App.log.debug("on_file_exportpng()")

        self.date = str(datetime.today()).rpartition('.')[0]
        self.date = ''.join(c for c in self.date if c not in ':-')
        self.date = self.date.replace(' ', '_')

        if self.is_legacy is False:
            image = _screenshot()
            data = np.asarray(image)
            if not data.ndim == 3 and data.shape[-1] in (3, 4):
                self.inform.emit('[[WARNING_NOTCL]] %s' %
                                 _('Data must be a 3D array with last dimension 3 or 4'))
                return

        filter_ = "PNG File (*.png);;All Files (*.*)"
        try:
            filename, _f = QtWidgets.QFileDialog.getSaveFileName(
                caption=_("Export PNG Image"),
                directory=self.get_last_save_folder() + '/png_' + self.date,
                filter=filter_)
        except TypeError:
            filename, _f = QtWidgets.QFileDialog.getSaveFileName(caption=_("Export PNG Image"), filter=filter_)

        filename = str(filename)

        if filename == "":
            self.inform.emit(_("Export PNG cancelled."))
            return
        else:
            if self.is_legacy is False:
                write_png(filename, data)
            else:
                self.plotcanvas.figure.savefig(filename)

            if self.defaults["global_open_style"] is False:
                self.file_opened.emit("png", filename)
            self.file_saved.emit("png", filename)

    def on_file_savegerber(self):
        """
        Callback for menu item in Project context menu.

        :return: None
        """
        self.report_usage("on_file_savegerber")
        App.log.debug("on_file_savegerber()")

        obj = self.collection.get_active()
        if obj is None:
            self.inform.emit('[WARNING_NOTCL] %s' %
                             _("No object selected. Please select an Gerber object to export."))
            return

        # Check for more compatible types and add as required
        if not isinstance(obj, FlatCAMGerber):
            self.inform.emit('[ERROR_NOTCL] %s' %
                             _("Failed. Only Gerber objects can be saved as Gerber files..."))
            return

        name = self.collection.get_active().options["name"]

        _filter = "Gerber File (*.GBR);;Gerber File (*.GRB);;All Files (*.*)"
        try:
            filename, _f = QtWidgets.QFileDialog.getSaveFileName(
                caption="Save Gerber source file",
                directory=self.get_last_save_folder() + '/' + name,
                filter=_filter)
        except TypeError:
            filename, _f = QtWidgets.QFileDialog.getSaveFileName(caption=_("Save Gerber source file"), filter=_filter)

        filename = str(filename)

        if filename == "":
            self.inform.emit('[WARNING_NOTCL] %s' %
                             _("Save Gerber source file cancelled."))
            return
        else:
            self.save_source_file(name, filename)
            if self.defaults["global_open_style"] is False:
                self.file_opened.emit("Gerber", filename)
            self.file_saved.emit("Gerber", filename)

    def on_file_savescript(self):
        """
        Callback for menu item in Project context menu.

        :return: None
        """
        self.report_usage("on_file_savescript")
        App.log.debug("on_file_savescript()")

        obj = self.collection.get_active()
        if obj is None:
            self.inform.emit('[WARNING_NOTCL] %s' %
                             _("No object selected. Please select an Script object to export."))
            return

        # Check for more compatible types and add as required
        if not isinstance(obj, FlatCAMScript):
            self.inform.emit('[ERROR_NOTCL] %s' %
                             _("Failed. Only Script objects can be saved as TCL Script files..."))
            return

        name = self.collection.get_active().options["name"]

        _filter = "FlatCAM Scripts (*.FlatScript);;All Files (*.*)"
        try:
            filename, _f = QtWidgets.QFileDialog.getSaveFileName(
                caption="Save Script source file",
                directory=self.get_last_save_folder() + '/' + name,
                filter=_filter)
        except TypeError:
            filename, _f = QtWidgets.QFileDialog.getSaveFileName(caption=_("Save Script source file"), filter=_filter)

        filename = str(filename)

        if filename == "":
            self.inform.emit('[WARNING_NOTCL] %s' %
                             _("Save Script source file cancelled."))
            return
        else:
            self.save_source_file(name, filename)
            if self.defaults["global_open_style"] is False:
                self.file_opened.emit("Script", filename)
            self.file_saved.emit("Script", filename)

    def on_file_savedocument(self):
        """
        Callback for menu item in Project context menu.

        :return: None
        """
        self.report_usage("on_file_savedocument")
        App.log.debug("on_file_savedocument()")

        obj = self.collection.get_active()
        if obj is None:
            self.inform.emit('[WARNING_NOTCL] %s' %
                             _("No object selected. Please select an Document object to export."))
            return

        # Check for more compatible types and add as required
        if not isinstance(obj, FlatCAMScript):
            self.inform.emit('[ERROR_NOTCL] %s' %
                             _("Failed. Only Document objects can be saved as Document files..."))
            return

        name = self.collection.get_active().options["name"]

        _filter = "FlatCAM Documents (*.FlatDoc);;All Files (*.*)"
        try:
            filename, _f = QtWidgets.QFileDialog.getSaveFileName(
                caption="Save Document source file",
                directory=self.get_last_save_folder() + '/' + name,
                filter=_filter)
        except TypeError:
            filename, _f = QtWidgets.QFileDialog.getSaveFileName(caption=_("Save Document source file"), filter=_filter)

        filename = str(filename)

        if filename == "":
            self.inform.emit('[WARNING_NOTCL] %s' %
                             _("Save Document source file cancelled."))
            return
        else:
            self.save_source_file(name, filename)
            if self.defaults["global_open_style"] is False:
                self.file_opened.emit("Document", filename)
            self.file_saved.emit("Document", filename)

    def on_file_saveexcellon(self):
        """
        Callback for menu item in project context menu.

        :return: None
        """
        self.report_usage("on_file_saveexcellon")
        App.log.debug("on_file_saveexcellon()")

        obj = self.collection.get_active()
        if obj is None:
            self.inform.emit('[WARNING_NOTCL] %s' %
                             _("No object selected. Please select an Excellon object to export."))
            return

        # Check for more compatible types and add as required
        if not isinstance(obj, FlatCAMExcellon):
            self.inform.emit('[ERROR_NOTCL] %s' %
                             _("Failed. Only Excellon objects can be saved as Excellon files..."))
            return

        name = self.collection.get_active().options["name"]

        _filter = "Excellon File (*.DRL);;Excellon File (*.TXT);;All Files (*.*)"
        try:
            filename, _f = QtWidgets.QFileDialog.getSaveFileName(
                caption=_("Save Excellon source file"),
                directory=self.get_last_save_folder() + '/' + name,
                filter=_filter)
        except TypeError:
            filename, _f = QtWidgets.QFileDialog.getSaveFileName(caption=_("Save Excellon source file"), filter=_filter)

        filename = str(filename)

        if filename == "":
            self.inform.emit('[WARNING_NOTCL] %s' %
                             _("Saving Excellon source file cancelled."))
            return
        else:
            self.save_source_file(name, filename)
            if self.defaults["global_open_style"] is False:
                self.file_opened.emit("Excellon", filename)
            self.file_saved.emit("Excellon", filename)

    def on_file_exportexcellon(self):
        """
        Callback for menu item File->Export->Excellon.

        :return: None
        """
        self.report_usage("on_file_exportexcellon")
        App.log.debug("on_file_exportexcellon()")

        obj = self.collection.get_active()
        if obj is None:
            self.inform.emit('[WARNING_NOTCL] %s' %
                             _("No object selected. Please Select an Excellon object to export."))
            return

        # Check for more compatible types and add as required
        if not isinstance(obj, FlatCAMExcellon):
            self.inform.emit('[ERROR_NOTCL] %s' %
                             _("Failed. Only Excellon objects can be saved as Excellon files..."))
            return

        name = self.collection.get_active().options["name"]

        _filter = self.defaults["excellon_save_filters"]
        try:
            filename, _f = QtWidgets.QFileDialog.getSaveFileName(
                caption=_("Export Excellon"),
                directory=self.get_last_save_folder() + '/' + name,
                filter=_filter)
        except TypeError:
            filename, _f = QtWidgets.QFileDialog.getSaveFileName(caption=_("Export Excellon"), filter=_filter)

        filename = str(filename)

        if filename == "":
            self.inform.emit('[WARNING_NOTCL] %s' %
                             _("Export Excellon cancelled."))
            return
        else:
            used_extension = filename.rpartition('.')[2]
            obj.update_filters(last_ext=used_extension, filter_string='excellon_save_filters')

            self.export_excellon(name, filename)
            if self.defaults["global_open_style"] is False:
                self.file_opened.emit("Excellon", filename)
            self.file_saved.emit("Excellon", filename)

    def on_file_exportgerber(self):
        """
        Callback for menu item File->Export->Gerber.

        :return: None
        """
        self.report_usage("on_file_exportgerber")
        App.log.debug("on_file_exportgerber()")

        obj = self.collection.get_active()
        if obj is None:
            self.inform.emit('[WARNING_NOTCL] %s' %
                             _("No object selected. Please Select an Gerber object to export."))
            return

        # Check for more compatible types and add as required
        if not isinstance(obj, FlatCAMGerber):
            self.inform.emit('[ERROR_NOTCL] %s' %
                             _("Failed. Only Gerber objects can be saved as Gerber files..."))
            return

        name = self.collection.get_active().options["name"]

        _filter_ = self.defaults['gerber_save_filters']
        try:
            filename, _f = QtWidgets.QFileDialog.getSaveFileName(
                caption=_("Export Gerber"),
                directory=self.get_last_save_folder() + '/' + name,
                filter=_filter_)
        except TypeError:
            filename, _f = QtWidgets.QFileDialog.getSaveFileName(caption=_("Export Gerber"), filter=_filter_)

        filename = str(filename)

        if filename == "":
            self.inform.emit('[WARNING_NOTCL] %s' %
                             _("Export Gerber cancelled."))
            return
        else:
            used_extension = filename.rpartition('.')[2]
            obj.update_filters(last_ext=used_extension, filter_string='gerber_save_filters')

            self.export_gerber(name, filename)
            if self.defaults["global_open_style"] is False:
                self.file_opened.emit("Gerber", filename)
            self.file_saved.emit("Gerber", filename)

    def on_file_exportdxf(self):
        """
                Callback for menu item File->Export DXF.

                :return: None
                """
        self.report_usage("on_file_exportdxf")
        App.log.debug("on_file_exportdxf()")

        obj = self.collection.get_active()
        if obj is None:
            self.inform.emit('[WARNING_NOTCL] %s' %
                             _("No object selected."))
            msg = _("Please Select a Geometry object to export")
            msgbox = QtWidgets.QMessageBox()
            msgbox.setInformativeText(msg)
            bt_ok = msgbox.addButton(_('Ok'), QtWidgets.QMessageBox.AcceptRole)
            msgbox.setDefaultButton(bt_ok)
            msgbox.exec_()
            return

        # Check for more compatible types and add as required
        if not isinstance(obj, FlatCAMGeometry):
            msg = '[ERROR_NOTCL] %s' % \
                  _("Only Geometry objects can be used.")
            msgbox = QtWidgets.QMessageBox()
            msgbox.setInformativeText(msg)
            bt_ok = msgbox.addButton(_('Ok'), QtWidgets.QMessageBox.AcceptRole)
            msgbox.setDefaultButton(bt_ok)
            msgbox.exec_()

            return

        name = self.collection.get_active().options["name"]

        _filter_ = "DXF File (*.DXF);;All Files (*.*)"
        try:
            filename, _f = QtWidgets.QFileDialog.getSaveFileName(
                caption=_("Export DXF"),
                directory=self.get_last_save_folder() + '/' + name,
                filter=_filter_)
        except TypeError:
            filename, _f = QtWidgets.QFileDialog.getSaveFileName(caption=_("Export DXF"),
                                                                 filter=_filter_)

        filename = str(filename)

        if filename == "":
            self.inform.emit('[WARNING_NOTCL] %s' %
                             _("Export DXF cancelled."))
            return
        else:
            self.export_dxf(name, filename)
            if self.defaults["global_open_style"] is False:
                self.file_opened.emit("DXF", filename)
            self.file_saved.emit("DXF", filename)

    def on_file_importsvg(self, type_of_obj):
        """
        Callback for menu item File->Import SVG.
        :param type_of_obj: to import the SVG as Geometry or as Gerber
        :type type_of_obj: str
        :return: None
        """
        self.report_usage("on_file_importsvg")
        App.log.debug("on_file_importsvg()")

        _filter_ = "SVG File (*.svg);;All Files (*.*)"
        try:
            filenames, _f = QtWidgets.QFileDialog.getOpenFileNames(caption=_("Import SVG"),
                                                                   directory=self.get_last_folder(), filter=_filter_)
        except TypeError:
            filenames, _f = QtWidgets.QFileDialog.getOpenFileNames(caption=_("Import SVG"),
                                                                   filter=_filter_)

        if type_of_obj is not "geometry" and type_of_obj is not "gerber":
            type_of_obj = "geometry"

        filenames = [str(filename) for filename in filenames]

        if len(filenames) == 0:
            self.inform.emit('[WARNING_NOTCL] %s' %
                             _("Open SVG cancelled."))
        else:
            for filename in filenames:
                if filename != '':
                    self.worker_task.emit({'fcn': self.import_svg,
                                           'params': [filename, type_of_obj]})

    def on_file_importdxf(self, type_of_obj):
        """
        Callback for menu item File->Import DXF.
        :param type_of_obj: to import the DXF as Geometry or as Gerber
        :type type_of_obj: str
        :return: None
        """
        self.report_usage("on_file_importdxf")
        App.log.debug("on_file_importdxf()")

        _filter_ = "DXF File (*.DXF);;All Files (*.*)"
        try:
            filenames, _f = QtWidgets.QFileDialog.getOpenFileNames(caption=_("Import DXF"),
                                                                   directory=self.get_last_folder(),
                                                                   filter=_filter_)
        except TypeError:
            filenames, _f = QtWidgets.QFileDialog.getOpenFileNames(caption=_("Import DXF"),
                                                                   filter=_filter_)

        if type_of_obj is not "geometry" and type_of_obj is not "gerber":
            type_of_obj = "geometry"

        filenames = [str(filename) for filename in filenames]

        if len(filenames) == 0:
            self.inform.emit('[WARNING_NOTCL] %s' %
                             _("Open DXF cancelled."))
        else:
            for filename in filenames:
                if filename != '':
                    self.worker_task.emit({'fcn': self.import_dxf,
                                           'params': [filename, type_of_obj]})

    # ###############################################################################################################
    # ### The following section has the functions that are displayed and call the Editor tab CNCJob Tab #############
    # ###############################################################################################################

    def init_code_editor(self, name):

        self.text_editor_tab = TextEditor(app=self)

        # add the tab if it was closed
        self.ui.plot_tab_area.addTab(self.text_editor_tab, '%s' % name)
        self.text_editor_tab.setObjectName('text_editor_tab')

        # delete the absolute and relative position and messages in the infobar
        self.ui.position_label.setText("")
        self.ui.rel_position_label.setText("")

        # first clear previous text in text editor (if any)
        self.text_editor_tab.code_editor.clear()
        self.text_editor_tab.code_editor.setReadOnly(False)
        self.toggle_codeeditor = True
        self.text_editor_tab.code_editor.completer_enable = False
        self.text_editor_tab.buttonRun.hide()

        # make sure to keep a reference to the code editor
        self.reference_code_editor = self.text_editor_tab.code_editor

        # Switch plot_area to CNCJob tab
        self.ui.plot_tab_area.setCurrentWidget(self.text_editor_tab)

    def on_view_source(self):
        """
        Called when the user wants to see the source file of the selected object
        :return:
        """

        self.inform.emit('%s' % _("Viewing the source code of the selected object."))
        self.proc_container.view.set_busy(_("Loading..."))

        try:
            obj = self.collection.get_active()
        except Exception as e:
            log.debug("App.on_view_source() --> %s" % str(e))
            self.inform.emit('[WARNING_NOTCL] %s' % _("Select an Gerber or Excellon file to view it's source file."))
            return 'fail'

        if obj is None:
            self.inform.emit('[WARNING_NOTCL] %s' % _("Select an Gerber or Excellon file to view it's source file."))
            return 'fail'

        flt = "All Files (*.*)"
        if obj.kind == 'gerber':
            flt = "Gerber Files (*.GBR);;All Files (*.*)"
        elif obj.kind == 'excellon':
            flt = "Excellon Files (*.DRL);;All Files (*.*)"
        elif obj.kind == 'cncjob':
            "GCode Files (*.NC);;All Files (*.*)"

        self.source_editor_tab = TextEditor(app=self, plain_text=True)

        # add the tab if it was closed
        self.ui.plot_tab_area.addTab(self.source_editor_tab, '%s' % _("Source Editor"))
        self.source_editor_tab.setObjectName('source_editor_tab')

        # delete the absolute and relative position and messages in the infobar
        self.ui.position_label.setText("")
        self.ui.rel_position_label.setText("")

        # first clear previous text in text editor (if any)
        self.source_editor_tab.code_editor.clear()
        self.source_editor_tab.code_editor.setReadOnly(False)

        self.source_editor_tab.code_editor.completer_enable = False
        self.source_editor_tab.buttonRun.hide()

        # Switch plot_area to CNCJob tab
        self.ui.plot_tab_area.setCurrentWidget(self.source_editor_tab)

        try:
            self.source_editor_tab.buttonOpen.clicked.disconnect()
        except TypeError:
            pass
        self.source_editor_tab.buttonOpen.clicked.connect(lambda: self.source_editor_tab.handleOpen(filt=flt))

        try:
            self.source_editor_tab.buttonSave.clicked.disconnect()
        except TypeError:
            pass
        self.source_editor_tab.buttonSave.clicked.connect(lambda: self.source_editor_tab.handleSaveGCode(filt=flt))

        # then append the text from GCode to the text editor
        if obj.kind == 'cncjob':
            try:
                file = obj.export_gcode(
                    preamble=self.defaults["cncjob_prepend"],
                    postamble=self.defaults["cncjob_append"],
                    to_file=True)
                if file == 'fail':
                    return 'fail'
            except AttributeError:
                self.inform.emit('[WARNING_NOTCL] %s' %
                                 _("There is no selected object for which to see it's source file code."))
                return 'fail'
        else:
            try:
                file = StringIO(obj.source_file)
            except (AttributeError, TypeError):
                self.inform.emit('[WARNING_NOTCL] %s' %
                                 _("There is no selected object for which to see it's source file code."))
                return 'fail'

        self.source_editor_tab.t_frame.hide()
        try:
            self.source_editor_tab.code_editor.setPlainText(file.getvalue())
            # for line in file:
            #     QtWidgets.QApplication.processEvents()
            #     proc_line = str(line).strip('\n')
            #     self.source_editor_tab.code_editor.append(proc_line)
        except Exception as e:
            log.debug('App.on_view_source() -->%s' % str(e))
            self.inform.emit('[ERROR] %s: %s' % (_('Failed to load the source code for the selected object'), str(e)))
            return

        self.source_editor_tab.handleTextChanged()
        self.source_editor_tab.t_frame.show()

        self.source_editor_tab.code_editor.moveCursor(QtGui.QTextCursor.Start)
        self.proc_container.view.set_idle()
        # self.ui.show()

    def on_toggle_code_editor(self):
        self.report_usage("on_toggle_code_editor()")

        if self.toggle_codeeditor is False:
            self.init_code_editor(name=_("Code Editor"))

            self.text_editor_tab.buttonOpen.clicked.disconnect()
            self.text_editor_tab.buttonOpen.clicked.connect(self.text_editor_tab.handleOpen)
            self.text_editor_tab.buttonSave.clicked.disconnect()
            self.text_editor_tab.buttonSave.clicked.connect(self.text_editor_tab.handleSaveGCode)
        else:
            for idx in range(self.ui.plot_tab_area.count()):
                if self.ui.plot_tab_area.widget(idx).objectName() == "text_editor_tab":
                    self.ui.plot_tab_area.closeTab(idx)
                    break
            self.toggle_codeeditor = False

    def on_code_editor_close(self):
        print("closed")
        self.toggle_codeeditor = False

    def on_filenewscript(self, silent=False, name=None, text=None):
        """
        Will create a new script file and open it in the Code Editor

        :param silent: if True will not display status messages
        :param name: if specified will be the name of the new script
        :param text: pass a source file to the newly created script to be loaded in it
        :return: None
        """
        if silent is False:
            self.inform.emit('[success] %s' %
                             _("New TCL script file created in Code Editor."))

        # delete the absolute and relative position and messages in the infobar
        self.ui.position_label.setText("")
        self.ui.rel_position_label.setText("")

        if name is not None:
            self.new_script_object(name=name, text=text)
        else:
            self.new_script_object(text=text)

        # script_text = script_obj.source_file
        #
        # self.proc_container.view.set_busy(_("Loading..."))
        # script_obj.script_editor_tab.t_frame.hide()
        #
        # script_obj.script_editor_tab.t_frame.show()
        # self.proc_container.view.set_idle()

    def on_fileopenscript(self, name=None, silent=False):
        """
        Will open a Tcl script file into the Code Editor

        :param silent: if True will not display status messages
        :param name: name of a Tcl script file to open
        :return:
        """

        self.report_usage("on_fileopenscript")
        App.log.debug("on_fileopenscript()")

        _filter_ = "TCL script (*.FlatScript);;TCL script (*.TCL);;TCL script (*.TXT);;All Files (*.*)"

        if name:
            filenames = [name]
        else:
            try:
                filenames, _f = QtWidgets.QFileDialog.getOpenFileNames(
                    caption=_("Open TCL script"), directory=self.get_last_folder(), filter=_filter_)
            except TypeError:
                filenames, _f = QtWidgets.QFileDialog.getOpenFileNames(caption=_("Open TCL script"), filter=_filter_)

        if len(filenames) == 0:
            if silent is False:
                self.inform.emit('[WARNING_NOTCL] %s' % _("Open TCL script cancelled."))
        else:
            for filename in filenames:
                if filename != '':
                    self.worker_task.emit({'fcn': self.open_script, 'params': [filename]})

    def on_filerunscript(self, name=None, silent=False):
        """
        File menu callback for loading and running a TCL script.

        :param silent: if True will not display status messages
        :param name: name of a Tcl script file to be run by FlatCAM
        :return: None
        """

        self.report_usage("on_filerunscript")
        App.log.debug("on_file_runscript()")

        if name:
            filename = name
            if self.cmd_line_headless != 1:
                self.splash.showMessage('%s: %ssec\n%s' %
                                        (_("Canvas initialization started.\n"
                                           "Canvas initialization finished in"), '%.2f' % self.used_time,
                                         _("Executing FlatCAMScript file.")
                                         ),
                                        alignment=Qt.AlignBottom | Qt.AlignLeft,
                                        color=QtGui.QColor("gray"))
        else:
            _filter_ = "TCL script (*.FlatScript);;TCL script (*.TCL);;TCL script (*.TXT);;All Files (*.*)"
            try:
                filename, _f = QtWidgets.QFileDialog.getOpenFileName(caption=_("Run TCL script"),
                                                                     directory=self.get_last_folder(), filter=_filter_)
            except TypeError:
                filename, _f = QtWidgets.QFileDialog.getOpenFileName(caption=_("Run TCL script"), filter=_filter_)

        # The Qt methods above will return a QString which can cause problems later.
        # So far json.dump() will fail to serialize it.
        # TODO: Improve the serialization methods and remove this fix.
        filename = str(filename)

        if filename == "":
            if silent is False:
                self.inform.emit('[WARNING_NOTCL] %s' %
                                 _("Run TCL script cancelled."))
        else:
            if self.cmd_line_headless != 1:
                if self.ui.shell_dock.isHidden():
                    self.ui.shell_dock.show()

            try:
                with open(filename, "r") as tcl_script:
                    cmd_line_shellfile_content = tcl_script.read()
                    if self.cmd_line_headless != 1:
                        self.shell._sysShell.exec_command(cmd_line_shellfile_content)
                    else:
                        self.shell._sysShell.exec_command(cmd_line_shellfile_content, no_echo=True)

                if silent is False:
                    self.inform.emit('[success] %s' %
                                     _("TCL script file opened in Code Editor and executed."))
            except Exception as e:
                log.debug("App.on_filerunscript() -> %s" % str(e))
                sys.exit(2)

    def on_file_saveproject(self, silent=False):
        """
        Callback for menu item File->Save Project. Saves the project to
        ``self.project_filename`` or calls ``self.on_file_saveprojectas()``
        if set to None. The project is saved by calling ``self.save_project()``.

        :param silent: if True will not display status messages
        :return: None
        """

        self.report_usage("on_file_saveproject")

        if self.project_filename is None:
            self.on_file_saveprojectas()
        else:
            self.worker_task.emit({'fcn': self.save_project,
                                   'params': [self.project_filename, silent]})
            if self.defaults["global_open_style"] is False:
                self.file_opened.emit("project", self.project_filename)
            self.file_saved.emit("project", self.project_filename)

        self.set_ui_title(name=self.project_filename)

        self.should_we_save = False

    def on_file_saveprojectas(self, make_copy=False, use_thread=True, quit_action=False):
        """
        Callback for menu item File->Save Project As... Opens a file
        chooser and saves the project to the given file via
        ``self.save_project()``.

        :param make_copy if to be create a copy of the project; boolean
        :param use_thread: if to be run in a separate thread; boolean
        :param quit_action: if to be followed by quiting the application; boolean
        :return: None
        """

        self.report_usage("on_file_saveprojectas")

        self.date = str(datetime.today()).rpartition('.')[0]
        self.date = ''.join(c for c in self.date if c not in ':-')
        self.date = self.date.replace(' ', '_')

        filter_ = "FlatCAM Project (*.FlatPrj);; All Files (*.*)"
        try:
            filename, _f = QtWidgets.QFileDialog.getSaveFileName(
                caption=_("Save Project As ..."),
                directory=_('{l_save}/Project_{date}').format(l_save=str(self.get_last_save_folder()), date=self.date),
                filter=filter_)
        except TypeError:
            filename, _f = QtWidgets.QFileDialog.getSaveFileName(caption=_("Save Project As ..."), filter=filter_)

        filename = str(filename)

        if filename == '':
            self.inform.emit('[WARNING_NOTCL] %s' %
                             _("Save Project cancelled."))
            return

        try:
            f = open(filename, 'r')
            f.close()
        except IOError:
            pass

        if use_thread is True:
            self.worker_task.emit({'fcn': self.save_project,
                                   'params': [filename, quit_action]})
        else:
            self.save_project(filename, quit_action)

        # self.save_project(filename)
        if self.defaults["global_open_style"] is False:
            self.file_opened.emit("project", filename)
        self.file_saved.emit("project", filename)

        if not make_copy:
            self.project_filename = filename

        self.set_ui_title(name=self.project_filename)
        self.should_we_save = False

    def export_svg(self, obj_name, filename, scale_stroke_factor=0.00):
        """
        Exports a Geometry Object to an SVG file.

        :param obj_name: the name of the FlatCAM object to be saved as SVG
        :param filename: Path to the SVG file to save to.
        :param scale_stroke_factor: factor by which to change/scale the thickness of the features
        :return:
        """
        self.report_usage("export_svg()")

        if filename is None:
            filename = self.defaults["global_last_save_folder"]

        self.log.debug("export_svg()")

        try:
            obj = self.collection.get_by_name(str(obj_name))
        except Exception:
            # TODO: The return behavior has not been established... should raise exception?
            return "Could not retrieve object: %s" % obj_name

        with self.proc_container.new(_("Exporting SVG")) as proc:
            exported_svg = obj.export_svg(scale_stroke_factor=scale_stroke_factor)

            # Determine bounding area for svg export
            bounds = obj.bounds()
            size = obj.size()

            # Convert everything to strings for use in the xml doc
            svgwidth = str(size[0])
            svgheight = str(size[1])
            minx = str(bounds[0])
            miny = str(bounds[1] - size[1])
            uom = obj.units.lower()

            # Add a SVG Header and footer to the svg output from shapely
            # The transform flips the Y Axis so that everything renders
            # properly within svg apps such as inkscape
            svg_header = '<svg xmlns="http://www.w3.org/2000/svg" ' \
                         'version="1.1" xmlns:xlink="http://www.w3.org/1999/xlink" '
            svg_header += 'width="' + svgwidth + uom + '" '
            svg_header += 'height="' + svgheight + uom + '" '
            svg_header += 'viewBox="' + minx + ' ' + miny + ' ' + svgwidth + ' ' + svgheight + '">'
            svg_header += '<g transform="scale(1,-1)">'
            svg_footer = '</g> </svg>'
            svg_elem = svg_header + exported_svg + svg_footer

            # Parse the xml through a xml parser just to add line feeds
            # and to make it look more pretty for the output
            svgcode = parse_xml_string(svg_elem)
            svgcode = svgcode.toprettyxml()

            try:
                with open(filename, 'w') as fp:
                    fp.write(svgcode)
            except PermissionError:
                self.inform.emit('[WARNING] %s' %
                                 _("Permission denied, saving not possible.\n"
                                   "Most likely another app is holding the file open and not accessible."))
                return 'fail'

            if self.defaults["global_open_style"] is False:
                self.file_opened.emit("SVG", filename)
            self.file_saved.emit("SVG", filename)
            self.inform.emit('[success] %s: %s' %
                             (_("SVG file exported to"), filename))

    def save_source_file(self, obj_name, filename, use_thread=True):
        """
        Exports a FlatCAM Object to an Gerber/Excellon file.

        :param obj_name: the name of the FlatCAM object for which to save it's embedded source file
        :param filename: Path to the Gerber file to save to.
        :param use_thread: if to be run in a separate thread
        :return:
        """
        self.report_usage("save source file()")

        if filename is None:
            filename = self.defaults["global_last_save_folder"]

        self.log.debug("save source file()")

        obj = self.collection.get_by_name(obj_name)

        file_string = StringIO(obj.source_file)
        time_string = "{:%A, %d %B %Y at %H:%M}".format(datetime.now())

        if file_string.getvalue() == '':
            self.inform.emit('[ERROR_NOTCL] %s' %
                             _("Save cancelled because source file is empty. Try to export the Gerber file."))
            return 'fail'

        try:
            with open(filename, 'w') as file:
                file.writelines('G04*\n')
                file.writelines('G04 %s (RE)GENERATED BY FLATCAM v%s - www.flatcam.org - Version Date: %s*\n' %
                                (obj.kind.upper(), str(self.version), str(self.version_date)))
                file.writelines('G04 Filename: %s*\n' % str(obj_name))
                file.writelines('G04 Created on : %s*\n' % time_string)

                for line in file_string:
                    file.writelines(line)
        except PermissionError:
            self.inform.emit('[WARNING] %s' %
                             _("Permission denied, saving not possible.\n"
                               "Most likely another app is holding the file open and not accessible."))
            return 'fail'

    def export_excellon(self, obj_name, filename, local_use=None, use_thread=True):
        """
        Exports a Excellon Object to an Excellon file.

        :param obj_name: the name of the FlatCAM object to be saved as Excellon
        :param filename: Path to the Excellon file to save to.
        :param local_use:
        :param use_thread: if to be run in a separate thread
        :return:
        """
        self.report_usage("export_excellon()")

        if filename is None:
            filename = self.defaults["global_last_save_folder"] + '/' + 'exported_excellon'

        self.log.debug("export_excellon()")

        format_exc = ';FILE_FORMAT=%d:%d\n' % (self.defaults["excellon_exp_integer"],
                                               self.defaults["excellon_exp_decimals"]
                                               )

        if local_use is None:
            try:
                obj = self.collection.get_by_name(str(obj_name))
            except Exception:
                # TODO: The return behavior has not been established... should raise exception?
                return "Could not retrieve object: %s" % obj_name
        else:
            obj = local_use

        if not isinstance(obj, FlatCAMExcellon):
            self.inform.emit('[ERROR_NOTCL] %s' %
                             _("Failed. Only Excellon objects can be saved as Excellon files..."))
            return

        # updated units
        eunits = self.defaults["excellon_exp_units"]
        ewhole = self.defaults["excellon_exp_integer"]
        efract = self.defaults["excellon_exp_decimals"]
        ezeros = self.defaults["excellon_exp_zeros"]
        eformat = self.defaults["excellon_exp_format"]
        slot_type = self.defaults["excellon_exp_slot_type"]

        fc_units = self.defaults['units'].upper()
        if fc_units == 'MM':
            factor = 1 if eunits == 'METRIC' else 0.03937
        else:
            factor = 25.4 if eunits == 'METRIC' else 1

        def make_excellon():
            try:
                time_str = "{:%A, %d %B %Y at %H:%M}".format(datetime.now())

                header = 'M48\n'
                header += ';EXCELLON GENERATED BY FLATCAM v%s - www.flatcam.org - Version Date: %s\n' % \
                          (str(self.version), str(self.version_date))

                header += ';Filename: %s' % str(obj_name) + '\n'
                header += ';Created on : %s' % time_str + '\n'

                if eformat == 'dec':
                    has_slots, excellon_code = obj.export_excellon(ewhole, efract, factor=factor, slot_type=slot_type)
                    header += eunits + '\n'

                    for tool in obj.tools:
                        if eunits == 'METRIC':
                            header += "T{tool}F00S00C{:.{dec}f}\n".format(float(obj.tools[tool]['C']) * factor,
                                                                          tool=str(tool),
                                                                          dec=2)
                        else:
                            header += "T{tool}F00S00C{:.{dec}f}\n".format(float(obj.tools[tool]['C']) * factor,
                                                                          tool=str(tool),
                                                                          dec=4)
                else:
                    if ezeros == 'LZ':
                        has_slots, excellon_code = obj.export_excellon(ewhole, efract,
                                                                       form='ndec', e_zeros='LZ', factor=factor,
                                                                       slot_type=slot_type)
                        header += '%s,%s\n' % (eunits, 'LZ')
                        header += format_exc

                        for tool in obj.tools:
                            if eunits == 'METRIC':
                                header += "T{tool}F00S00C{:.{dec}f}\n".format(float(obj.tools[tool]['C']) * factor,
                                                                              tool=str(tool),
                                                                              dec=2)
                            else:
                                header += "T{tool}F00S00C{:.{dec}f}\n".format(float(obj.tools[tool]['C']) * factor,
                                                                              tool=str(tool),
                                                                              dec=4)
                    else:
                        has_slots, excellon_code = obj.export_excellon(ewhole, efract,
                                                                       form='ndec', e_zeros='TZ', factor=factor,
                                                                       slot_type=slot_type)
                        header += '%s,%s\n' % (eunits, 'TZ')
                        header += format_exc

                        for tool in obj.tools:
                            if eunits == 'METRIC':
                                header += "T{tool}F00S00C{:.{dec}f}\n".format(float(obj.tools[tool]['C']) * factor,
                                                                              tool=str(tool),
                                                                              dec=2)
                            else:
                                header += "T{tool}F00S00C{:.{dec}f}\n".format(float(obj.tools[tool]['C']) * factor,
                                                                              tool=str(tool),
                                                                              dec=4)
                header += '%\n'
                footer = 'M30\n'

                exported_excellon = header
                exported_excellon += excellon_code
                exported_excellon += footer

                if local_use is None:
                    try:
                        with open(filename, 'w') as fp:
                            fp.write(exported_excellon)
                    except PermissionError:
                        self.inform.emit('[WARNING] %s' %
                                         _("Permission denied, saving not possible.\n"
                                           "Most likely another app is holding the file open and not accessible."))
                        return 'fail'

                    if self.defaults["global_open_style"] is False:
                        self.file_opened.emit("Excellon", filename)
                    self.file_saved.emit("Excellon", filename)
                    self.inform.emit('[success] %s: %s' %
                                     (_("Excellon file exported to"), filename))
                else:
                    return exported_excellon
            except Exception as e:
                log.debug("App.export_excellon.make_excellon() --> %s" % str(e))
                return 'fail'

        if use_thread is True:

            with self.proc_container.new(_("Exporting Excellon")) as proc:

                def job_thread_exc(app_obj):
                    ret = make_excellon()
                    if ret == 'fail':
                        self.inform.emit('[ERROR_NOTCL] %s' %
                                         _('Could not export Excellon file.'))
                        return

                self.worker_task.emit({'fcn': job_thread_exc, 'params': [self]})
        else:
            ret = make_excellon()
            if ret == 'fail':
                self.inform.emit('[ERROR_NOTCL] %s' %
                                 _('Could not export Excellon file.'))
                return 'fail'
            if local_use is not None:
                return ret

    def export_gerber(self, obj_name, filename, local_use=None, use_thread=True):
        """
        Exports a Gerber Object to an Gerber file.

        :param obj_name: the name of the FlatCAM object to be saved as Gerber
        :param filename: Path to the Gerber file to save to.
        :param local_use: if the Gerber code is to be saved to a file (None) or used within FlatCAM.
        When not None, the value will be the actual Gerber object for which to create the Gerber code
        :param use_thread: if to be run in a separate thread
        :return:
        """
        self.report_usage("export_gerber()")

        if filename is None:
            filename = self.defaults["global_last_save_folder"]

        self.log.debug("export_gerber()")

        if local_use is None:
            try:
                obj = self.collection.get_by_name(str(obj_name))
            except Exception:
                # TODO: The return behavior has not been established... should raise exception?
                return "Could not retrieve object: %s" % obj_name
        else:
            obj = local_use

        # updated units
        gunits = self.defaults["gerber_exp_units"]
        gwhole = self.defaults["gerber_exp_integer"]
        gfract = self.defaults["gerber_exp_decimals"]
        gzeros = self.defaults["gerber_exp_zeros"]

        fc_units = self.defaults['units'].upper()
        if fc_units == 'MM':
            factor = 1 if gunits == 'MM' else 0.03937
        else:
            factor = 25.4 if gunits == 'MM' else 1

        def make_gerber():
            try:
                time_str = "{:%A, %d %B %Y at %H:%M}".format(datetime.now())

                header = 'G04*\n'
                header += 'G04 RS-274X GERBER GENERATED BY FLATCAM v%s - www.flatcam.org - Version Date: %s*\n' % \
                          (str(self.version), str(self.version_date))

                header += 'G04 Filename: %s*' % str(obj_name) + '\n'
                header += 'G04 Created on : %s*' % time_str + '\n'
                header += '%%FS%sAX%s%sY%s%s*%%\n' % (gzeros, gwhole, gfract, gwhole, gfract)
                header += "%MO{units}*%\n".format(units=gunits)

                for apid in obj.apertures:
                    if obj.apertures[apid]['type'] == 'C':
                        header += "%ADD{apid}{type},{size}*%\n".format(
                            apid=str(apid),
                            type='C',
                            size=(factor * obj.apertures[apid]['size'])
                        )
                    elif obj.apertures[apid]['type'] == 'R':
                        header += "%ADD{apid}{type},{width}X{height}*%\n".format(
                            apid=str(apid),
                            type='R',
                            width=(factor * obj.apertures[apid]['width']),
                            height=(factor * obj.apertures[apid]['height'])
                        )
                    elif obj.apertures[apid]['type'] == 'O':
                        header += "%ADD{apid}{type},{width}X{height}*%\n".format(
                            apid=str(apid),
                            type='O',
                            width=(factor * obj.apertures[apid]['width']),
                            height=(factor * obj.apertures[apid]['height'])
                        )

                header += '\n'

                # obsolete units but some software may need it
                if gunits == 'IN':
                    header += 'G70*\n'
                else:
                    header += 'G71*\n'

                # Absolute Mode
                header += 'G90*\n'

                header += 'G01*\n'
                # positive polarity
                header += '%LPD*%\n'

                footer = 'M02*\n'

                gerber_code = obj.export_gerber(gwhole, gfract, g_zeros=gzeros, factor=factor)

                exported_gerber = header
                exported_gerber += gerber_code
                exported_gerber += footer

                if local_use is None:
                    try:
                        with open(filename, 'w') as fp:
                            fp.write(exported_gerber)
                    except PermissionError:
                        self.inform.emit('[WARNING] %s' %
                                         _("Permission denied, saving not possible.\n"
                                           "Most likely another app is holding the file open and not accessible."))
                        return 'fail'

                    if self.defaults["global_open_style"] is False:
                        self.file_opened.emit("Gerber", filename)
                    self.file_saved.emit("Gerber", filename)
                    self.inform.emit('[success] %s: %s' %
                                     (_("Gerber file exported to"), filename))
                else:
                    return exported_gerber
            except Exception as e:
                log.debug("App.export_gerber.make_gerber() --> %s" % str(e))
                return 'fail'

        if use_thread is True:
            with self.proc_container.new(_("Exporting Gerber")) as proc:

                def job_thread_grb(app_obj):
                    ret = make_gerber()
                    if ret == 'fail':
                        self.inform.emit('[ERROR_NOTCL] %s' %
                                         _('Could not export Gerber file.'))
                        return

                self.worker_task.emit({'fcn': job_thread_grb, 'params': [self]})
        else:
            ret = make_gerber()
            if ret == 'fail':
                self.inform.emit('[ERROR_NOTCL] %s' %
                                 _('Could not export Gerber file.'))
                return 'fail'
            if local_use is not None:
                return ret

    def export_dxf(self, obj_name, filename, use_thread=True):
        """
        Exports a Geometry Object to an DXF file.

        :param obj_name: the name of the FlatCAM object to be saved as DXF
        :param filename: Path to the DXF file to save to.
        :param use_thread: if to be run in a separate thread
        :return:
        """
        self.report_usage("export_dxf()")

        if filename is None:
            filename = self.defaults["global_last_save_folder"]

        self.log.debug("export_dxf()")

        try:
            obj = self.collection.get_by_name(str(obj_name))
        except Exception:
            # TODO: The return behavior has not been established... should raise exception?
            return "Could not retrieve object: %s" % obj_name

        def make_dxf():
            try:
                dxf_code = obj.export_dxf()
                dxf_code.saveas(filename)
                if self.defaults["global_open_style"] is False:
                    self.file_opened.emit("DXF", filename)
                self.file_saved.emit("DXF", filename)
                self.inform.emit('[success] %s: %s' % (_("DXF file exported to"), filename))
            except Exception:
                return 'fail'

        if use_thread is True:

            with self.proc_container.new(_("Exporting DXF")) as proc:

                def job_thread_exc(app_obj):
                    ret_dxf_val = make_dxf()
                    if ret_dxf_val == 'fail':
                        app_obj.inform.emit('[WARNING_NOTCL] %s' % _('Could not export DXF file.'))
                        return

                self.worker_task.emit({'fcn': job_thread_exc, 'params': [self]})
        else:
            ret = make_dxf()
            if ret == 'fail':
                self.inform.emit('[WARNING_NOTCL] %s' % _('Could not export DXF file.'))
                return

    def import_svg(self, filename, geo_type='geometry', outname=None):
        """
        Adds a new Geometry Object to the projects and populates
        it with shapes extracted from the SVG file.

        :param filename: Path to the SVG file.
        :param geo_type: Type of FlatCAM object that will be created from SVG
        :param outname:
        :return:
        """
        self.report_usage("import_svg()")
        log.debug("App.import_svg()")

        obj_type = ""
        if geo_type is None or geo_type == "geometry":
            obj_type = "geometry"
        elif geo_type == "gerber":
            obj_type = "gerber"
        else:
            self.inform.emit('[ERROR_NOTCL] %s' %
                             _("Not supported type is picked as parameter. Only Geometry and Gerber are supported"))
            return

        units = self.defaults['units'].upper()

        def obj_init(geo_obj, app_obj):
            geo_obj.import_svg(filename, obj_type, units=units)
            geo_obj.multigeo = False
            geo_obj.source_file = self.export_gerber(obj_name=name, filename=None, local_use=geo_obj, use_thread=False)

        with self.proc_container.new(_("Importing SVG")) as proc:

            # Object name
            name = outname or filename.split('/')[-1].split('\\')[-1]

            self.new_object(obj_type, name, obj_init, autoselected=False)

            # Register recent file
            self.file_opened.emit("svg", filename)

            # GUI feedback
            self.inform.emit('[success] %s: %s' % (_("Opened"), filename))

    def import_dxf(self, filename, geo_type='geometry', outname=None):
        """
        Adds a new Geometry Object to the projects and populates
        it with shapes extracted from the DXF file.

        :param filename: Path to the DXF file.
        :param geo_type: Type of FlatCAM object that will be created from DXF
        :param outname:
        :type putname: str
        :return:
        """
        self.report_usage("import_dxf()")

        obj_type = ""
        if geo_type is None or geo_type == "geometry":
            obj_type = "geometry"
        elif geo_type == "gerber":
            obj_type = geo_type
        else:
            self.inform.emit('[ERROR_NOTCL] %s' %
                             _("Not supported type is picked as parameter. Only Geometry and Gerber are supported"))
            return

        units = self.defaults['units'].upper()

        def obj_init(geo_obj, app_obj):
            geo_obj.import_dxf(filename, obj_type, units=units)
            geo_obj.multigeo = False

        with self.proc_container.new(_("Importing DXF")) as proc:

            # Object name
            name = outname or filename.split('/')[-1].split('\\')[-1]

            self.new_object(obj_type, name, obj_init, autoselected=False)
            self.progress.emit(20)
            # Register recent file
            self.file_opened.emit("dxf", filename)

            # GUI feedback
            self.inform.emit('[success] %s: %s' % (_("Opened"), filename))
            self.progress.emit(100)

    def open_gerber(self, filename, outname=None):
        """
        Opens a Gerber file, parses it and creates a new object for
        it in the program. Thread-safe.

        :param outname: Name of the resulting object. None causes the
            name to be that of the file.
        :param filename: Gerber file filename
        :type filename: str
        :return: None
        """

        # How the object should be initialized
        def obj_init(gerber_obj, app_obj):

            assert isinstance(gerber_obj, FlatCAMGerber), \
                "Expected to initialize a FlatCAMGerber but got %s" % type(gerber_obj)

            # Opening the file happens here
            self.progress.emit(30)
            try:
                gerber_obj.parse_file(filename)
            except IOError:
                app_obj.inform.emit('[ERROR_NOTCL] %s: %s' %
                                    (_("Failed to open file"), filename))
                app_obj.progress.emit(0)
                return "fail"
            except ParseError as err:
                app_obj.inform.emit('[ERROR_NOTCL] %s: %s. %s' %
                                    (_("Failed to parse file"), filename, str(err)))
                app_obj.progress.emit(0)
                self.log.error(str(err))
                return "fail"
            except Exception as e:
                log.debug("App.open_gerber() --> %s" % str(e))
                msg = '[ERROR] %s' % \
                      _("An internal error has occurred. See shell.\n")
                msg += traceback.format_exc()
                app_obj.inform.emit(msg)
                return "fail"

            if gerber_obj.is_empty():
                # app_obj.inform.emit("[ERROR] No geometry found in file: " + filename)
                # self.collection.set_active(gerber_obj.options["name"])
                # self.collection.delete_active()
                self.inform.emit('[ERROR_NOTCL] %s' %
                                 _("Object is not Gerber file or empty. Aborting object creation."))
                return "fail"

            # Further parsing
            self.progress.emit(70)  # TODO: Note the mixture of self and app_obj used here

        App.log.debug("open_gerber()")

        with self.proc_container.new(_("Opening Gerber")) as proc:

            self.progress.emit(10)

            # Object name
            name = outname or filename.split('/')[-1].split('\\')[-1]

            # # ## Object creation # ##
            ret = self.new_object("gerber", name, obj_init, autoselected=False)
            if ret == 'fail':
                self.inform.emit('[ERROR_NOTCL]%s' %
                                 _(' Open Gerber failed. Probable not a Gerber file.'))
                return

            # Register recent file
            self.file_opened.emit("gerber", filename)

            self.progress.emit(100)

            # GUI feedback
            self.inform.emit('[success] %s: %s' %
                             (_("Opened"), filename))

    def open_excellon(self, filename, outname=None, plot=True):
        """
        Opens an Excellon file, parses it and creates a new object for
        it in the program. Thread-safe.

        :param outname: Name of the resulting object. None causes the
            name to be that of the file.
        :param filename: Excellon file filename
        :type filename: str
        :return: None
        """

        App.log.debug("open_excellon()")

        # How the object should be initialized
        def obj_init(excellon_obj, app_obj):
            # self.progress.emit(20)

            try:
                ret = excellon_obj.parse_file(filename=filename)
                if ret == "fail":
                    log.debug("Excellon parsing failed.")
                    self.inform.emit('[ERROR_NOTCL] %s' %
                                     _("This is not Excellon file."))
                    return "fail"
            except IOError:
                app_obj.inform.emit('[ERROR_NOTCL] %s: %s' %
                                    (_("Cannot open file"), filename))
                log.debug("Could not open Excellon object.")
                self.progress.emit(0)  # TODO: self and app_bjj mixed
                return "fail"
            except Exception:
                msg = '[ERROR_NOTCL] %s' % \
                      _("An internal error has occurred. See shell.\n")
                msg += traceback.format_exc()
                app_obj.inform.emit(msg)
                return "fail"

            ret = excellon_obj.create_geometry()
            if ret == 'fail':
                log.debug("Could not create geometry for Excellon object.")
                return "fail"

            for tool in excellon_obj.tools:
                if excellon_obj.tools[tool]['solid_geometry']:
                    return
            app_obj.inform.emit('[ERROR_NOTCL] %s: %s' %
                                (_("No geometry found in file"), filename))
            return "fail"

        with self.proc_container.new(_("Opening Excellon.")):

            # Object name
            name = outname or filename.split('/')[-1].split('\\')[-1]
            ret_val = self.new_object("excellon", name, obj_init, autoselected=False, plot=plot)
            if ret_val == 'fail':
                self.inform.emit('[ERROR_NOTCL] %s' %
                                 _('Open Excellon file failed. Probable not an Excellon file.'))
                return

            # Register recent file
            self.file_opened.emit("excellon", filename)

            # GUI feedback
            self.inform.emit('[success] %s: %s' %
                             (_("Opened"), filename))

    def open_gcode(self, filename, outname=None, force_parsing=None, plot=True):
        """
        Opens a G-gcode file, parses it and creates a new object for
        it in the program. Thread-safe.

        :param outname: Name of the resulting object. None causes the name to be that of the file.
        :param filename: G-code file filename
        :type filename: str
        :return: None
        """
        App.log.debug("open_gcode()")

        # How the object should be initialized
        def obj_init(job_obj, app_obj_):
            """
            :param job_obj: the resulting object
            :type app_obj_: App
            """
            assert isinstance(app_obj_, App), \
                "Initializer expected App, got %s" % type(app_obj_)

            app_obj_.inform.emit('%s...' % _("Reading GCode file"))
            try:
                f = open(filename)
                gcode = f.read()
                f.close()
            except IOError:
                app_obj_.inform.emit('[ERROR_NOTCL] %s: %s' %
                                     (_("Failed to open"), filename))
                return "fail"

            job_obj.gcode = gcode

            gcode_ret = job_obj.gcode_parse(force_parsing=force_parsing)
            if gcode_ret == "fail":
                self.inform.emit('[ERROR_NOTCL] %s' %
                                 _("This is not GCODE"))
                return "fail"

            job_obj.create_geometry()

        with self.proc_container.new(_("Opening G-Code.")):

            # Object name
            name = outname or filename.split('/')[-1].split('\\')[-1]

            # New object creation and file processing
            obj_ret = self.new_object("cncjob", name, obj_init, autoselected=False, plot=plot)
            if obj_ret == 'fail':
                self.inform.emit('[ERROR_NOTCL] %s' %
                                 _("Failed to create CNCJob Object. Probable not a GCode file. "
                                   "Try to load it from File menu.\n "
                                   "Attempting to create a FlatCAM CNCJob Object from "
                                   "G-Code file failed during processing"))
                return "fail"

            # Register recent file
            self.file_opened.emit("cncjob", filename)

            # GUI feedback
            self.inform.emit('[success] %s: %s' %
                             (_("Opened"), filename))

    def open_script(self, filename, outname=None, silent=False):
        """
        Opens a Script file, parses it and creates a new object for
        it in the program. Thread-safe.

        :param outname: Name of the resulting object. None causes the name to be that of the file.
        :param filename: Script file filename
        :type filename: str
        :return: None
        """
        App.log.debug("open_script()")

        with self.proc_container.new(_("Opening TCL Script...")):

            try:
                with open(filename, "r") as opened_script:
                    script_content = opened_script.readlines()
                    script_content = ''.join(script_content)

                    if silent is False:
                        self.inform.emit('[success] %s' % _("TCL script file opened in Code Editor."))
            except Exception as e:
                log.debug("App.open_script() -> %s" % str(e))
                self.inform.emit('[ERROR_NOTCL] %s' % _("Failed to open TCL Script."))
                return

            # Object name
            script_name = outname or filename.split('/')[-1].split('\\')[-1]

            # New object creation and file processing
            self.on_filenewscript(name=script_name, text=script_content)

            # Register recent file
            self.file_opened.emit("script", filename)

            # GUI feedback
            self.inform.emit('[success] %s: %s' % (_("Opened"), filename))

    def open_config_file(self, filename, run_from_arg=None):
        """
        Loads a config file from the specified file.

        :param filename:  Name of the file from which to load.
        :type filename: str
        :return: None
        """
        App.log.debug("Opening config file: " + filename)

        if run_from_arg:
            self.splash.showMessage('%s: %ssec\n%s' % (_("Canvas initialization started.\n"
                                                         "Canvas initialization finished in"), '%.2f' % self.used_time,
                                                       _("Opening FlatCAM Config file.")),
                                    alignment=Qt.AlignBottom | Qt.AlignLeft,
                                    color=QtGui.QColor("gray"))
        # # add the tab if it was closed
        # self.ui.plot_tab_area.addTab(self.ui.text_editor_tab, _("Code Editor"))
        # # first clear previous text in text editor (if any)
        # self.ui.text_editor_tab.code_editor.clear()
        #
        # # Switch plot_area to CNCJob tab
        # self.ui.plot_tab_area.setCurrentWidget(self.ui.text_editor_tab)

        # close the Code editor if already open
        if self.toggle_codeeditor:
            self.on_toggle_code_editor()

        self.on_toggle_code_editor()

        try:
            if filename:
                f = QtCore.QFile(filename)
                if f.open(QtCore.QIODevice.ReadOnly):
                    stream = QtCore.QTextStream(f)
                    code_edited = stream.readAll()
                    self.text_editor_tab.code_editor.setPlainText(code_edited)
                    f.close()
        except IOError:
            App.log.error("Failed to open config file: %s" % filename)
            self.inform.emit('[ERROR_NOTCL] %s: %s' %
                             (_("Failed to open config file"), filename))
            return

    def open_project(self, filename, run_from_arg=None, plot=True, cli=None):
        """
        Loads a project from the specified file.

        1) Loads and parses file
        2) Registers the file as recently opened.
        3) Calls on_file_new()
        4) Updates options
        5) Calls new_object() with the object's from_dict() as init method.
        6) Calls plot_all() if plot=True

        :param filename:  Name of the file from which to load.
        :type filename: str
        :param run_from_arg: True if run for arguments
        :param plot: If True plot all objects in the project
        :param cli: run from command line
        :return: None
        """
        App.log.debug("Opening project: " + filename)

        # for some reason, setting ui_title does not work when this method is called from Tcl Shell
        # it's because the TclCommand is run in another thread (it inherit TclCommandSignaled)
        if cli is None:
            self.set_ui_title(name=_("Loading Project ... Please Wait ..."))

        if run_from_arg:
            self.splash.showMessage('%s: %ssec\n%s' % (_("Canvas initialization started.\n"
                                                         "Canvas initialization finished in"), '%.2f' % self.used_time,
                                                       _("Opening FlatCAM Project file.")),
                                    alignment=Qt.AlignBottom | Qt.AlignLeft,
                                    color=QtGui.QColor("gray"))

        # Open and parse an uncompressed Project file
        try:
            f = open(filename, 'r')
        except IOError:
            App.log.error("Failed to open project file: %s" % filename)
            self.inform.emit('[ERROR_NOTCL] %s: %s' %
                             (_("Failed to open project file"), filename))
            return

        try:
            d = json.load(f, object_hook=dict2obj)
        except Exception as e:
            App.log.error("Failed to parse project file, trying to see if it loads as an LZMA archive: %s because %s" %
                          (filename, str(e)))
            f.close()

            # Open and parse a compressed Project file
            try:
                with lzma.open(filename) as f:
                    file_content = f.read().decode('utf-8')
                    d = json.loads(file_content, object_hook=dict2obj)
            except Exception as e:
                App.log.error("Failed to open project file: %s with error: %s" % (filename, str(e)))
                self.inform.emit('[ERROR_NOTCL] %s: %s' %
                                 (_("Failed to open project file"), filename))
                return

        # Clear the current project
        # # NOT THREAD SAFE # ##
        if run_from_arg is True:
            pass
        elif cli is True:
            self.delete_selection_shape()
        else:
            self.on_file_new()

        # Project options
        self.options.update(d['options'])
        self.project_filename = filename

        # for some reason, setting ui_title does not work when this method is called from Tcl Shell
        # it's because the TclCommand is run in another thread (it inherit TclCommandSignaled)
        if cli is None:
            self.set_screen_units(self.options["units"])

        # Re create objects
        App.log.debug(" **************** Started PROEJCT loading... **************** ")

        for obj in d['objs']:
            def obj_init(obj_inst, app_inst):
                obj_inst.from_dict(obj)

            App.log.debug("Recreating from opened project an %s object: %s" %
                          (obj['kind'].capitalize(), obj['options']['name']))

            # for some reason, setting ui_title does not work when this method is called from Tcl Shell
            # it's because the TclCommand is run in another thread (it inherit TclCommandSignaled)
            if cli is None:
                self.set_ui_title(name="{} {}: {}".format(_("Loading Project ... restoring"),
                                                          obj['kind'].upper(),
                                                          obj['options']['name']
                                                          )
                                  )

            self.new_object(obj['kind'], obj['options']['name'], obj_init, active=False, fit=False, plot=plot)

        self.inform.emit('[success] %s: %s' %
                         (_("Project loaded from"), filename))

        self.should_we_save = False
        self.file_opened.emit("project", filename)

        # for some reason, setting ui_title does not work when this method is called from Tcl Shell
        # it's because the TclCommand is run in another thread (it inherit TclCommandSignaled)
        if cli is None:
            self.set_ui_title(name=self.project_filename)

        App.log.debug(" **************** Finished PROJECT loading... **************** ")

    def propagate_defaults(self, silent=False):
        """
        This method is used to set default values in classes. It's
        an alternative to project options but allows the use
        of values invisible to the user.

        :return: None
        """

        if silent is False:
            self.log.debug("propagate_defaults()")

        # Which objects to update the given parameters.
        routes = {
            "global_zdownrate": CNCjob,
            "excellon_zeros": Excellon,
            "excellon_format_upper_in": Excellon,
            "excellon_format_lower_in": Excellon,
            "excellon_format_upper_mm": Excellon,
            "excellon_format_lower_mm": Excellon,
            "excellon_units": Excellon,
            "gerber_use_buffer_for_union": Gerber,
            "geometry_multidepth": Geometry
        }

        for param in routes:
            if param in routes[param].defaults:
                try:
                    routes[param].defaults[param] = self.defaults[param]
                    if silent is False:
                        self.log.debug("  " + param + " OK")
                except KeyError:
                    if silent is False:
                        self.log.debug("FlatCAMApp.propagate_defaults() --> ERROR: " + param + " not in defaults.")
            else:
                # Try extracting the name:
                # classname_param here is param in the object
                if param.find(routes[param].__name__.lower() + "_") == 0:
                    p = param[len(routes[param].__name__) + 1:]
                    if p in routes[param].defaults:
                        routes[param].defaults[p] = self.defaults[param]
                        if silent is False:
                            self.log.debug("  " + param + " OK!")

    def plot_all(self, zoom=True):
        """
        Re-generates all plots from all objects.

        :return: None
        """
        self.log.debug("Plot_all()")
        self.inform.emit('[success] %s...' % _("Redrawing all objects"))

        for obj in self.collection.get_list():
            def worker_task(obj):
                with self.proc_container.new("Plotting"):
                    obj.plot(kind=self.defaults["cncjob_plot_kind"])
                    if zoom:
                        self.object_plotted.emit(obj)

            # Send to worker
            self.worker_task.emit({'fcn': worker_task, 'params': [obj]})

    def register_folder(self, filename):
        self.defaults["global_last_folder"] = os.path.split(str(filename))[0]

    def register_save_folder(self, filename):
        self.defaults["global_last_save_folder"] = os.path.split(str(filename))[0]

    def set_progress_bar(self, percentage, text=""):
        self.ui.progress_bar.setValue(int(percentage))

    def setup_shell(self):
        """
        Creates shell functions. Runs once at startup.

        :return: None
        """

        self.log.debug("setup_shell()")

        def shelp(p=None):
            if not p:
                return _("Available commands:\n") + \
                       '\n'.join(['  ' + cmd for cmd in sorted(commands)]) + \
                       _("\n\nType help <command_name> for usage.\n Example: help open_gerber")

            if p not in commands:
                return "Unknown command: %s" % p

            return commands[p]["help"]

        # --- Migrated to new architecture ---
        # def options(name):
        #     ops = self.collection.get_by_name(str(name)).options
        #     return '\n'.join(["%s: %s" % (o, ops[o]) for o in ops])

        def h(*args):
            """
            Pre-processes arguments to detect '-keyword value' pairs into dictionary
            and standalone parameters into list.
            """

            kwa = {}
            a = []
            n = len(args)
            name = None
            for i in range(n):
                match = re.search(r'^-([a-zA-Z].*)', args[i])
                if match:
                    assert name is None
                    name = match.group(1)
                    continue

                if name is None:
                    a.append(args[i])
                else:
                    kwa[name] = args[i]
                    name = None

            return a, kwa

        @contextmanager
        def wait_signal(signal, timeout=10000):
            """
            Block loop until signal emitted, timeout (ms) elapses
            or unhandled exception happens in a thread.

            :param timeout: time after which the loop is exited
            :param signal: Signal to wait for.
            """
            loop = QtCore.QEventLoop()

            # Normal termination
            signal.connect(loop.quit)

            # Termination by exception in thread
            self.thread_exception.connect(loop.quit)

            status = {'timed_out': False}

            def report_quit():
                status['timed_out'] = True
                loop.quit()

            yield

            # Temporarily change how exceptions are managed.
            oeh = sys.excepthook
            ex = []

            def except_hook(type_, value, traceback_):
                ex.append(value)
                oeh(type_, value, traceback_)
            sys.excepthook = except_hook

            # Terminate on timeout
            if timeout is not None:
                QtCore.QTimer.singleShot(timeout, report_quit)

            # # ## Block ## ##
            loop.exec_()

            # Restore exception management
            sys.excepthook = oeh
            if ex:
                self.raiseTclError(str(ex[0]))

            if status['timed_out']:
                raise Exception('Timed out!')

        def make_docs():
            output = ''
            import collections
            od = collections.OrderedDict(sorted(commands.items()))
            for cmd_, val in od.items():
                output += cmd_ + ' \n' + ''.join(['~'] * len(cmd_)) + '\n'

                t = val['help']
                usage_i = t.find('>')
                if usage_i < 0:
                    expl = t
                    output += expl + '\n\n'
                    continue

                expl = t[:usage_i - 1]
                output += expl + '\n\n'

                end_usage_i = t[usage_i:].find('\n')

                if end_usage_i < 0:
                    end_usage_i = len(t[usage_i:])
                    output += '    ' + t[usage_i:] + '\n       No parameters.\n'
                else:
                    extras = t[usage_i+end_usage_i+1:]
                    parts = [s.strip() for s in extras.split('\n')]

                    output += '    ' + t[usage_i:usage_i+end_usage_i] + '\n'
                    for p in parts:
                        output += '       ' + p + '\n\n'

            return output

        '''
            Howto implement TCL shell commands:

            All parameters passed to command should be possible to set as None and test it afterwards.
            This is because we need to see error caused in tcl,
            if None value as default parameter is not allowed TCL will return empty error.
            Use:
                def mycommand(name=None,...):

            Test it like this:
            if name is None:

                self.raise_tcl_error('Argument name is missing.')

            When error ocurre, always use raise_tcl_error, never return "sometext" on error,
            otherwise we will miss it and processing will silently continue.
            Method raise_tcl_error  pass error into TCL interpreter, then raise python exception,
            which is catched in exec_command and displayed in TCL shell console with red background.
            Error in console is displayed  with TCL  trace.

            This behavior works only within main thread,
            errors with promissed tasks can be catched and detected only with log.
            TODO: this problem have to be addressed somehow, maybe rewrite promissing to be blocking somehow for
            TCL shell.

            Kamil's comment: I will rewrite existing TCL commands from time to time to follow this rules.

        '''

        commands = {
            'help': {
                'fcn': shelp,
                'help': _("Shows list of commands.")
            },
        }

        # Import/overwrite tcl commands as objects of TclCommand descendants
        # This modifies the variable 'commands'.
        tclCommands.register_all_commands(self, commands)

        # Add commands to the tcl interpreter
        for cmd in commands:
            self.tcl.createcommand(cmd, commands[cmd]['fcn'])

        # Make the tcl puts function return instead of print to stdout
        self.tcl.eval('''
            rename puts original_puts
            proc puts {args} {
                if {[llength $args] == 1} {
                    return "[lindex $args 0]"
                } else {
                    eval original_puts $args
                }
            }
            ''')

    def setup_recent_items(self):

        # TODO: Move this to constructor
        icons = {
            "gerber": "share/flatcam_icon16.png",
            "excellon": "share/drill16.png",
            'geometry': "share/geometry16.png",
            "cncjob": "share/cnc16.png",
            "script": "share/script_new24.png",
            "document": "share/notes16_1.png",
            "project": "share/project16.png",
            "svg": "share/geometry16.png",
            "dxf": "share/dxf16.png",
            "pdf": "share/pdf32.png",
            "image": "share/image16.png"

        }

        openers = {
            'gerber': lambda fname: self.worker_task.emit({'fcn': self.open_gerber, 'params': [fname]}),
            'excellon': lambda fname: self.worker_task.emit({'fcn': self.open_excellon, 'params': [fname]}),
            'geometry': lambda fname: self.worker_task.emit({'fcn': self.import_dxf, 'params': [fname]}),
            'cncjob': lambda fname: self.worker_task.emit({'fcn': self.open_gcode, 'params': [fname]}),
            "script": lambda fname: self.worker_task.emit({'fcn': self.open_script, 'params': [fname]}),
            "document": None,
            'project': self.open_project,
            'svg': self.import_svg,
            'dxf': self.import_dxf,
            'image': self.image_tool.import_image,
            'pdf': lambda fname: self.worker_task.emit({'fcn': self.pdf_tool.open_pdf, 'params': [fname]})
        }

        # Open recent file for files
        try:
            f = open(self.data_path + '/recent.json')
        except IOError:
            App.log.error("Failed to load recent item list.")
            self.inform.emit('[ERROR_NOTCL] %s' %
                             _("Failed to load recent item list."))
            return

        try:
            self.recent = json.load(f)
        except json.scanner.JSONDecodeError:
            App.log.error("Failed to parse recent item list.")
            self.inform.emit('[ERROR_NOTCL] %s' %
                             _("Failed to parse recent item list."))
            f.close()
            return
        f.close()

        # Open recent file for projects
        try:
            fp = open(self.data_path + '/recent_projects.json')
        except IOError:
            App.log.error("Failed to load recent project item list.")
            self.inform.emit('[ERROR_NOTCL] %s' %
                             _("Failed to load recent projects item list."))
            return

        try:
            self.recent_projects = json.load(fp)
        except json.scanner.JSONDecodeError:
            App.log.error("Failed to parse recent project item list.")
            self.inform.emit('[ERROR_NOTCL] %s' %
                             _("Failed to parse recent project item list."))
            fp.close()
            return
        fp.close()

        # Closure needed to create callbacks in a loop.
        # Otherwise late binding occurs.
        def make_callback(func, fname):
            def opener():
                func(fname)
            return opener

        def reset_recent_files():
            # Reset menu
            self.ui.recent.clear()
            self.recent = []
            try:
                ff = open(self.data_path + '/recent.json', 'w')
            except IOError:
                App.log.error("Failed to open recent items file for writing.")
                return

            json.dump(self.recent, ff)

        def reset_recent_projects():
            # Reset menu
            self.ui.recent_projects.clear()
            self.recent_projects = []

            try:
                fp = open(self.data_path + '/recent_projects.json', 'w')
            except IOError:
                App.log.error("Failed to open recent projects items file for writing.")
                return

            json.dump(self.recent, fp)

        # Reset menu
        self.ui.recent.clear()
        self.ui.recent_projects.clear()

        # Create menu items for projects
        for recent in self.recent_projects:
            filename = recent['filename'].split('/')[-1].split('\\')[-1]

            if recent['kind'] == 'project':
                try:
                    action = QtWidgets.QAction(QtGui.QIcon(icons[recent["kind"]]), filename, self)

                    # Attach callback
                    o = make_callback(openers[recent["kind"]], recent['filename'])
                    action.triggered.connect(o)

                    self.ui.recent_projects.addAction(action)

                except KeyError:
                    App.log.error("Unsupported file type: %s" % recent["kind"])

        # Last action in Recent Files menu is one that Clear the content
        clear_action_proj = QtWidgets.QAction(QtGui.QIcon('share/trash32.png'), (_("Clear Recent projects")), self)
        clear_action_proj.triggered.connect(reset_recent_projects)
        self.ui.recent_projects.addSeparator()
        self.ui.recent_projects.addAction(clear_action_proj)

        # Create menu items for files
        for recent in self.recent:
            filename = recent['filename'].split('/')[-1].split('\\')[-1]

            if recent['kind'] != 'project':
                try:
                    action = QtWidgets.QAction(QtGui.QIcon(icons[recent["kind"]]), filename, self)

                    # Attach callback
                    o = make_callback(openers[recent["kind"]], recent['filename'])
                    action.triggered.connect(o)

                    self.ui.recent.addAction(action)

                except KeyError:
                    App.log.error("Unsupported file type: %s" % recent["kind"])

        # Last action in Recent Files menu is one that Clear the content
        clear_action = QtWidgets.QAction(QtGui.QIcon('share/trash32.png'), (_("Clear Recent files")), self)
        clear_action.triggered.connect(reset_recent_files)
        self.ui.recent.addSeparator()
        self.ui.recent.addAction(clear_action)

        # self.builder.get_object('open_recent').set_submenu(recent_menu)
        # self.ui.menufilerecent.set_submenu(recent_menu)
        # recent_menu.show_all()
        # self.ui.recent.show()

        self.log.debug("Recent items list has been populated.")

    def setup_component_editor(self):
        # label = QtWidgets.QLabel("Choose an item from Project")
        # label.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)

        sel_title = QtWidgets.QTextEdit(
            _('<b>Shortcut Key List</b>'))
        sel_title.setTextInteractionFlags(QtCore.Qt.NoTextInteraction)
        sel_title.setFrameStyle(QtWidgets.QFrame.NoFrame)

        settings = QSettings("Open Source", "FlatCAM")
        if settings.contains("notebook_font_size"):
            fsize = settings.value('notebook_font_size', type=int)
        else:
            fsize = 12

        tsize = fsize + int(fsize / 2)

#         selected_text = (_('''
# <p><span style="font-size:{tsize}px"><strong>Selected Tab - Choose an Item from Project Tab</strong></span></p>
#
# <p><span style="font-size:{fsize}px"><strong>Details</strong>:<br />
# The normal flow when working in FlatCAM is the following:</span></p>
#
# <ol>
# 	<li><span style="font-size:{fsize}px">Loat/Import a Gerber, Excellon, Gcode, DXF, Raster Image or SVG file into
        # 	FlatCAM using either the menu&#39;s, toolbars, key shortcuts or
        # 	even dragging and dropping the files on the GUI.<br />
# 	<br />
# 	You can also load a <strong>FlatCAM project</strong> by double clicking on the project file, drag &amp; drop of the
        # 	file into the FLATCAM GUI or through the menu/toolbar links offered within the app.</span><br />
# 	&nbsp;</li>
# 	<li><span style="font-size:{fsize}px">Once an object is available in the Project Tab, by selecting it and then
        # 	focusing on <strong>SELECTED TAB </strong>(more simpler is to double click the object name in the
        # 	Project Tab), <strong>SELECTED TAB </strong>will be updated with the object properties according to
        # 	it&#39;s kind: Gerber, Excellon, Geometry or CNCJob object.<br />
# 	<br />
# 	If the selection of the object is done on the canvas by single click instead, and the <strong>SELECTED TAB</strong>
        # 	is in focus, again the object properties will be displayed into the Selected Tab. Alternatively,
        # 	double clicking on the object on the canvas will bring the <strong>SELECTED TAB</strong> and populate
        # 	it even if it was out of focus.<br />
# 	<br />
# 	You can change the parameters in this screen and the flow direction is like this:<br />
# 	<br />
# 	<strong>Gerber/Excellon Object</strong> -&gt; Change Param -&gt; Generate Geometry -&gt;<strong> Geometry Object
        # 	</strong>-&gt; Add tools (change param in Selected Tab) -&gt; Generate CNCJob -&gt;<strong> CNCJob Object
        # 	</strong>-&gt; Verify GCode (through Edit CNC Code) and/or append/prepend to GCode (again, done in
        # 	<strong>SELECTED TAB)&nbsp;</strong>-&gt; Save GCode</span></li>
# </ol>
#
# <p><span style="font-size:{fsize}px">A list of key shortcuts is available through an menu entry in
        # <strong>Help -&gt; Shortcuts List</strong>&nbsp;or through it&#39;s own key shortcut:
        # <strong>F3</strong>.</span></p>
#
#         ''').format(fsize=fsize, tsize=tsize))

        selected_text = '''
        <p><span style="font-size:{tsize}px"><strong>{title}</strong></span></p>

        <p><span style="font-size:{fsize}px"><strong>{subtitle}</strong>:<br />
        {s1}</span></p>

        <ol>
            <li><span style="font-size:{fsize}px">{s2}<br />
            <br />
            {s3}</span><br />
            &nbsp;</li>
            <li><span style="font-size:{fsize}px">{s4}<br />
            &nbsp;</li>
            <br />
            <li><span style="font-size:{fsize}px">{s5}<br />
            &nbsp;</li>
            <br />
            <li><span style="font-size:{fsize}px">{s6}<br />
            <br />
            {s7}</span></li>
        </ol>

        <p><span style="font-size:{fsize}px">{s8}</span></p>
        '''.format(
            title=_("Selected Tab - Choose an Item from Project Tab"),
            subtitle=_("Details"),

            s1=_("The normal flow when working in FlatCAM is the following:"),
            s2=_("Load/Import a Gerber, Excellon, Gcode, DXF, Raster Image or SVG file into FlatCAM "
                 "using either the toolbars, key shortcuts or even dragging and dropping the "
                 "files on the GUI."),
            s3=_("You can also load a FlatCAM project by double clicking on the project file, "
                 "drag and drop of the file into the FLATCAM GUI or through the menu (or toolbar) "
                 "actions offered within the app."),
            s4=_("Once an object is available in the Project Tab, by selecting it and then focusing "
                 "on SELECTED TAB (more simpler is to double click the object name in the Project Tab, "
                 "SELECTED TAB will be updated with the object properties according to its kind: "
                 "Gerber, Excellon, Geometry or CNCJob object."),
            s5=_("If the selection of the object is done on the canvas by single click instead, "
                 "and the SELECTED TAB is in focus, again the object properties will be displayed into the "
                 "Selected Tab. Alternatively, double clicking on the object on the canvas will bring "
                 "the SELECTED TAB and populate it even if it was out of focus."),
            s6=_("You can change the parameters in this screen and the flow direction is like this:"),
            s7=_("Gerber/Excellon Object --> Change Parameter --> Generate Geometry --> Geometry Object --> "
                 "Add tools (change param in Selected Tab) --> Generate CNCJob --> CNCJob Object --> "
                 "Verify GCode (through Edit CNC Code) and/or append/prepend to GCode "
                 "(again, done in SELECTED TAB) --> Save GCode."),
            s8=_("A list of key shortcuts is available through an menu entry in Help --> Shortcuts List "
                 "or through its own key shortcut: <b>F3</b>."),
            tsize=tsize,
            fsize=fsize
        )

        sel_title.setText(selected_text)
        sel_title.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        self.ui.selected_scroll_area.setWidget(sel_title)

    def setup_obj_classes(self):
        """
        Sets up application specifics on the FlatCAMObj class.

        :return: None
        """
        FlatCAMObj.app = self
        ObjectCollection.app = self
        Gerber.app = self
        Excellon.app = self
        Geometry.app = self
        CNCjob.app = self
        FCProcess.app = self
        FCProcessContainer.app = self

    def version_check(self):
        """
        Checks for the latest version of the program. Alerts the
        user if theirs is outdated. This method is meant to be run
        in a separate thread.

        :return: None
        """

        self.log.debug("version_check()")

        if self.ui.general_defaults_form.general_app_group.send_stats_cb.get_value() is True:
            full_url = App.version_url + \
                       "?s=" + str(self.defaults['global_serial']) + \
                       "&v=" + str(self.version) + \
                       "&os=" + str(self.os) + \
                       "&" + urllib.parse.urlencode(self.defaults["global_stats"])
        else:
            # no_stats dict; just so it won't break things on website
            no_ststs_dict = {}
            no_ststs_dict["global_ststs"] = {}
            full_url = App.version_url + \
                       "?s=" + str(self.defaults['global_serial']) + \
                       "&v=" + str(self.version) + \
                       "&os=" + str(self.os) + \
                       "&" + urllib.parse.urlencode(no_ststs_dict["global_ststs"])

        App.log.debug("Checking for updates @ %s" % full_url)
        # ## Get the data
        try:
            f = urllib.request.urlopen(full_url)
        except Exception:
            # App.log.warning("Failed checking for latest version. Could not connect.")
            self.log.warning("Failed checking for latest version. Could not connect.")
            self.inform.emit('[WARNING_NOTCL] %s' %
                             _("Failed checking for latest version. Could not connect."))
            return

        try:
            data = json.load(f)
        except Exception as e:
            App.log.error("Could not parse information about latest version.")
            self.inform.emit('[ERROR_NOTCL] %s' %
                             _("Could not parse information about latest version."))
            App.log.debug("json.load(): %s" % str(e))
            f.close()
            return

        f.close()

        # ## Latest version?
        if self.version >= data["version"]:
            App.log.debug("FlatCAM is up to date!")
            self.inform.emit('[success] %s' %
                             _("FlatCAM is up to date!"))
            return

        App.log.debug("Newer version available.")
        self.message.emit(
            _("Newer Version Available"),
            _("There is a newer version of FlatCAM available for download:\n\n") +
            "<b>%s</b>" % str(data["name"]) + "\n%s" % str(data["message"]),
            _("info")
        )

    def on_plotcanvas_setup(self, container=None):
        """
        This is doing the setup for the plot area (VisPy canvas)

        :param container: widget where to install the canvas
        :return: None
        """
        if container:
            plot_container = container
        else:
            plot_container = self.ui.right_layout

        if self.is_legacy is False:
            self.plotcanvas = PlotCanvas(plot_container, self)
        else:
            self.plotcanvas = PlotCanvasLegacy(plot_container, self)

        # So it can receive key presses
        self.plotcanvas.native.setFocus()

        self.mm = self.plotcanvas.graph_event_connect('mouse_move', self.on_mouse_move_over_plot)
        self.mp = self.plotcanvas.graph_event_connect('mouse_press', self.on_mouse_click_over_plot)
        self.mr = self.plotcanvas.graph_event_connect('mouse_release', self.on_mouse_click_release_over_plot)
        self.mdc = self.plotcanvas.graph_event_connect('mouse_double_click', self.on_mouse_double_click_over_plot)

        # Keys over plot enabled
        self.kp = self.plotcanvas.graph_event_connect('key_press', self.ui.keyPressEvent)

        if self.defaults['global_cursor_type'] == 'small':
            self.app_cursor = self.plotcanvas.new_cursor()
        else:
            self.app_cursor = self.plotcanvas.new_cursor(big=True)

        if self.ui.grid_snap_btn.isChecked():
            self.app_cursor.enabled = True
        else:
            self.app_cursor.enabled = False

        if self.is_legacy is False:
            self.hover_shapes = ShapeCollection(parent=self.plotcanvas.view.scene, layers=1)
        else:
            # will use the default Matplotlib axes
            self.hover_shapes = ShapeCollectionLegacy(obj=self, app=self, name='hover')

    def on_zoom_fit(self, event):
        """
        Callback for zoom-out request. This can be either from the corresponding
        toolbar button or the '1' key when the canvas is focused. Calls ``self.adjust_axes()``
        with axes limits from the geometry bounds of all objects.

        :param event: Ignored.
        :return: None
        """
        if self.is_legacy is False:
            self.plotcanvas.fit_view()
        else:
            xmin, ymin, xmax, ymax = self.collection.get_bounds()
            width = xmax - xmin
            height = ymax - ymin
            xmin -= 0.05 * width
            xmax += 0.05 * width
            ymin -= 0.05 * height
            ymax += 0.05 * height
            self.plotcanvas.adjust_axes(xmin, ymin, xmax, ymax)

    def on_zoom_in(self):
        self.plotcanvas.zoom(1 / float(self.defaults['global_zoom_ratio']))

    def on_zoom_out(self):
        self.plotcanvas.zoom(float(self.defaults['global_zoom_ratio']))

    def disable_all_plots(self):
        self.report_usage("disable_all_plots()")

        self.disable_plots(self.collection.get_list())
        self.inform.emit('[success] %s' %
                         _("All plots disabled."))

    def disable_other_plots(self):
        self.report_usage("disable_other_plots()")

        self.disable_plots(self.collection.get_non_selected())
        self.inform.emit('[success] %s' %
                         _("All non selected plots disabled."))

    def enable_all_plots(self):
        self.report_usage("enable_all_plots()")

        self.enable_plots(self.collection.get_list())
        self.inform.emit('[success] %s' %
                         _("All plots enabled."))

    def on_enable_sel_plots(self):
        log.debug("App.on_enable_sel_plot()")
        object_list = self.collection.get_selected()
        self.enable_plots(objects=object_list)
        self.inform.emit('[success] %s' %
                         _("Selected plots enabled..."))

    def on_disable_sel_plots(self):
        log.debug("App.on_disable_sel_plot()")

        # self.inform.emit(_("Disabling plots ..."))
        object_list = self.collection.get_selected()
        self.disable_plots(objects=object_list)
        self.inform.emit('[success] %s' %
                         _("Selected plots disabled..."))

    def enable_plots(self, objects):
        """
        Disables plots

        :param objects: list of Objects to be enabled
        :return:
        """
        log.debug("Enabling plots ...")
        # self.inform.emit(_("Working ..."))

        for obj in objects:
            if obj.options['plot'] is False:
                obj.options.set_change_callback(lambda x: None)
                obj.options['plot'] = True
                obj.options.set_change_callback(obj.on_options_change)

        def worker_task(objs):
            with self.proc_container.new(_("Enabling plots ...")):
                for obj in objs:
                    # obj.options['plot'] = True
                    if isinstance(obj, FlatCAMCNCjob):
                        obj.plot(visible=True, kind=self.defaults["cncjob_plot_kind"])
                    else:
                        obj.plot(visible=True)

        self.worker_task.emit({'fcn': worker_task, 'params': [objects]})

        # self.plots_updated.emit()

    def disable_plots(self, objects):
        """
        Disables plots

        :param objects: list of Objects to be disabled
        :return:
        """

        # if no objects selected then do nothing
        if not self.collection.get_selected():
            return

        log.debug("Disabling plots ...")
        # self.inform.emit(_("Working ..."))

        for obj in objects:
            if obj.options['plot'] is True:
                obj.options.set_change_callback(lambda x: None)
                obj.options['plot'] = False
                obj.options.set_change_callback(obj.on_options_change)

        try:
            self.delete_selection_shape()
        except Exception as e:
            log.debug("App.disable_plots() --> %s" % str(e))

        # self.plots_updated.emit()
        def worker_task(objs):
            with self.proc_container.new(_("Disabling plots ...")):
                for obj in objs:
                    # obj.options['plot'] = True
                    if isinstance(obj, FlatCAMCNCjob):
                        obj.plot(visible=False, kind=self.defaults["cncjob_plot_kind"])
                    else:
                        obj.plot(visible=False)

        self.worker_task.emit({'fcn': worker_task, 'params': [objects]})

    def toggle_plots(self, objects):
        """
        Toggle plots visibility
        :param objects: list of Objects for which to be toggled the visibility
        :return:
        """

        # if no objects selected then do nothing
        if not self.collection.get_selected():
            return

        log.debug("Toggling plots ...")
        self.inform.emit(_("Working ..."))
        for obj in objects:
            if obj.options['plot'] is False:
                obj.options['plot'] = True
            else:
                obj.options['plot'] = False
        self.plots_updated.emit()

    def clear_plots(self):

        objects = self.collection.get_list()

        for obj in objects:
            obj.clear(obj == objects[-1])

        # Clear pool to free memory
        self.clear_pool()

    def generate_cnc_job(self, objects):
        self.report_usage("generate_cnc_job()")

        # for obj in objects:
        #     obj.generatecncjob()
        for obj in objects:
            obj.on_generatecnc_button_click()

    def save_project(self, filename, quit_action=False, silent=False):
        """
        Saves the current project to the specified file.

        :param filename: Name of the file in which to save.
        :type filename: str
        :param quit_action: if the project saving will be followed by an app quit; boolean
        :param silent: if True will not display status messages
        :return: None
        """
        self.log.debug("save_project()")
        self.save_in_progress = True

        with self.proc_container.new(_("Saving FlatCAM Project")):
            # Capture the latest changes
            # Current object
            try:
                self.collection.get_active().read_form()
            except Exception as e:
                self.log.debug("There was no active object. %s" % str(e))
                pass

            # Serialize the whole project
            d = {"objs": [obj.to_dict() for obj in self.collection.get_list()],
                 "options": self.options,
                 "version": self.version}

            if self.defaults["global_save_compressed"] is True:
                with lzma.open(filename, "w", preset=int(self.defaults['global_compression_level'])) as f:
                    g = json.dumps(d, default=to_dict, indent=2, sort_keys=True).encode('utf-8')
                    # # Write
                    f.write(g)
                self.inform.emit('[success] %s: %s' %
                                 (_("Project saved to"), filename))
            else:
                # Open file
                try:
                    f = open(filename, 'w')
                except IOError:
                    App.log.error("Failed to open file for saving: %s", filename)
                    return

                # Write
                json.dump(d, f, default=to_dict, indent=2, sort_keys=True)
                f.close()

                # verification of the saved project
                # Open and parse
                try:
                    saved_f = open(filename, 'r')
                except IOError:
                    if silent is False:
                        self.inform.emit('[ERROR_NOTCL] %s: %s %s' %
                                         (_("Failed to verify project file"), filename, _("Retry to save it."))
                                         )
                    return

                try:
                    saved_d = json.load(saved_f, object_hook=dict2obj)
                except Exception:
                    if silent is False:
                        self.inform.emit('[ERROR_NOTCL] %s: %s %s' %
                                         (_("Failed to parse saved project file"), filename, _("Retry to save it."))
                                         )
                    f.close()
                    return
                saved_f.close()

                if silent is False:
                    if 'version' in saved_d:
                        self.inform.emit('[success] %s: %s' %
                                         (_("Project saved to"), filename))
                    else:
                        self.inform.emit('[ERROR_NOTCL] %s: %s %s' %
                                         (_("Failed to parse saved project file"), filename, _("Retry to save it."))
                                         )

                tb_settings = QSettings("Open Source", "FlatCAM")
                lock_state = self.ui.lock_action.isChecked()
                tb_settings.setValue('toolbar_lock', lock_state)

                # This will write the setting to the platform specific storage.
                del tb_settings

            # if quit:
                # t = threading.Thread(target=lambda: self.check_project_file_size(1, filename=filename))
                # t.start()
            self.start_delayed_quit(delay=500, filename=filename, should_quit=quit_action)

    def start_delayed_quit(self, delay, filename, should_quit=None):
        """

        :param delay:       period of checking if project file size is more than zero; in seconds
        :param filename:    the name of the project file to be checked periodically for size more than zero
        :param should_quit: if the task finished will be followed by an app quit; boolean
        :return:
        """
        to_quit = should_quit
        self.save_timer = QtCore.QTimer()
        self.save_timer.setInterval(delay)
        self.save_timer.timeout.connect(lambda: self.check_project_file_size(filename=filename, should_quit=to_quit))
        self.save_timer.start()

    def check_project_file_size(self, filename, should_quit=None):
        """

        :param filename: the name of the project file to be checked periodically for size more than zero
        :param should_quit: will quit the app if True; boolean
        :return:
        """

        try:
            if os.stat(filename).st_size > 0:
                self.save_in_progress = False
                self.save_timer.stop()
                if should_quit:
                    self.app_quit.emit()
        except Exception:
            traceback.print_exc()

    def on_plotarea_tab_closed(self, tab_idx):
        widget = self.ui.plot_tab_area.widget(tab_idx)

        if widget is not None:
            widget.deleteLater()
        self.ui.plot_tab_area.removeTab(tab_idx)

    def on_options_app2project(self):
        """
        Callback for Options->Transfer Options->App=>Project. Copies options
        from application defaults to project defaults.

        :return: None
        """

        self.report_usage("on_options_app2project")

        self.defaults_read_form()
        self.options.update(self.defaults)
        # self.options_write_form()


class ArgsThread(QtCore.QObject):
    open_signal = pyqtSignal(list)
    start = pyqtSignal()

    if sys.platform == 'win32':
        address = (r'\\.\pipe\NPtest', 'AF_PIPE')
    else:
        address = ('/tmp/testipc', 'AF_UNIX')

    def __init__(self):
        super(ArgsThread, self).__init__()
        self.start.connect(self.run)

    def my_loop(self, address):
        try:
            listener = Listener(*address)
            while True:
                conn = listener.accept()
                self.serve(conn)
        except socket.error:
            conn = Client(*address)
            conn.send(sys.argv)
            conn.send('close')
            # close the current instance only if there are args
            if len(sys.argv) > 1:
                sys.exit()

    def serve(self, conn):
        while True:
            msg = conn.recv()
            if msg == 'close':
                break
            self.open_signal.emit(msg)
        conn.close()

    # the decorator is a must; without it this technique will not work unless the start signal is connected
    # in the main thread (where this class is instantiated) after the instance is moved o the new thread
    @pyqtSlot()
    def run(self):
        self.my_loop(self.address)


class GracefulException(Exception):
    # Graceful Exception raised when the user is requesting to cancel the current threaded task
    def __init__(self):
        super().__init__()

    def __str__(self):
        return '\n\n%s' % _("The user requested a graceful exit of the current task.")

# end of file
