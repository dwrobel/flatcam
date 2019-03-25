############################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# Author: Juan Pablo Caram (c)                             #
# Date: 2/5/2014                                           #
# MIT Licence                                              #
############################################################

import urllib.request, urllib.parse, urllib.error
import getopt
import random
import simplejson as json
import lzma

from stat import S_IREAD, S_IRGRP, S_IROTH
import subprocess

import tkinter as tk
from PyQt5 import QtPrintSupport

import urllib.request, urllib.parse, urllib.error
from contextlib import contextmanager
import gc

from xml.dom.minidom import parseString as parse_xml_string

########################################
##      Imports part of FlatCAM       ##
########################################
from ObjectCollection import *
from FlatCAMObj import *
from flatcamGUI.PlotCanvas import *
from flatcamGUI.FlatCAMGUI import *
from FlatCAMCommon import LoudDict
from FlatCAMPostProc import load_postprocessors

from FlatCAMEditor import FlatCAMGeoEditor, FlatCAMExcEditor
from FlatCAMProcess import *
from FlatCAMWorkerStack import WorkerStack
from flatcamGUI.VisPyVisuals import Color
from vispy.gloo.util import _screenshot
from vispy.io import write_png

from flatcamTools import *

from multiprocessing import Pool
import tclCommands

import gettext
import FlatCAMTranslation as fcTranslate

fcTranslate.apply_language('strings')
import builtins
if '_' not in builtins.__dict__:
    _ = gettext.gettext

########################################
##                App                 ##
########################################


class App(QtCore.QObject):
    """
    The main application class. The constructor starts the GUI.
    """

    # Get Cmd Line Options
    cmd_line_shellfile = ''
    cmd_line_help = "FlatCam.py --shellfile=<cmd_line_shellfile>"
    try:
        # Multiprocessing pool will spawn additional processes with 'multiprocessing-fork' flag
        cmd_line_options, args = getopt.getopt(sys.argv[1:], "h:", ["shellfile=", "multiprocessing-fork="])
    except getopt.GetoptError:
        print(cmd_line_help)
        sys.exit(2)
    for opt, arg in cmd_line_options:
        if opt == '-h':
            print(cmd_line_help)
            sys.exit()
        elif opt == '--shellfile':
            cmd_line_shellfile = arg

    # Logging ##
    log = logging.getLogger('base')
    log.setLevel(logging.DEBUG)
    # log.setLevel(logging.WARNING)
    formatter = logging.Formatter('[%(levelname)s][%(threadName)s] %(message)s')
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    log.addHandler(handler)

    # Version
    version = 8.913
    version_date = "2019/03/25"
    beta = True

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

    should_we_quit = True

    # this variable will hold the project status
    # if True it will mean that the project was modified and not saved
    should_we_save = False

    ##################
    ##    Signals   ##
    ##################

    # Inform the user
    # Handled by:
    #  * App.info() --> Print on the status bar
    inform = QtCore.pyqtSignal(str)

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
    object_status_changed = QtCore.pyqtSignal(object, str)

    message = QtCore.pyqtSignal(str, str, str)

    # Emmited when shell command is finished(one command only)
    shell_command_finished = QtCore.pyqtSignal(object)

    # Emitted when multiprocess pool has been recreated
    pool_recreated = QtCore.pyqtSignal(object)

    # Emitted when an unhandled exception happens
    # in the worker task.
    thread_exception = QtCore.pyqtSignal(object)

    def __init__(self, user_defaults=True, post_gui=None):
        """
        Starts the application.

        :return: app
        :rtype: App
        """

        App.log.info("FlatCAM Starting...")

        ###################
        ### OS-specific ###
        ###################

        # Folder for user settings.
        if sys.platform == 'win32':
            from win32com.shell import shell, shellcon
            if platform.architecture()[0] == '32bit':
                App.log.debug("Win32!")
            else:
                App.log.debug("Win64!")

            self.data_path = shell.SHGetFolderPath(0, shellcon.CSIDL_APPDATA, None, 0) + '\FlatCAM'
            self.os = 'windows'
        else:  # Linux/Unix/MacOS
            self.data_path = os.path.expanduser('~') + '/.FlatCAM'
            self.os = 'unix'

        ###############################
        ### Setup folders and files ###
        ###############################

        if not os.path.exists(self.data_path):
            os.makedirs(self.data_path)
            App.log.debug('Created data folder: ' + self.data_path)
            os.makedirs(os.path.join(self.data_path, 'postprocessors'))
            App.log.debug('Created data postprocessors folder: ' + os.path.join(self.data_path, 'postprocessors'))

        self.postprocessorpaths = os.path.join(self.data_path,'postprocessors')
        if not os.path.exists(self.postprocessorpaths):
            os.makedirs(self.postprocessorpaths)
            App.log.debug('Created postprocessors folder: ' + self.postprocessorpaths)

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

        try:
            f = open(self.data_path + '/recent.json')
            f.close()
        except IOError:
            App.log.debug('Creating empty recent.json')
            f = open(self.data_path + '/recent.json', 'w')
            json.dump([], f)
            f.close()

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

        # Create multiprocessing pool
        self.pool = Pool()

        # variable to store mouse coordinates
        self.mouse = [0, 0]

        ####################
        ## Initialize GUI ##
        ####################

        # FlatCAM colors used in plotting
        self.FC_light_green = '#BBF268BF'
        self.FC_dark_green = '#006E20BF'
        self.FC_light_blue = '#a5a5ffbf'
        self.FC_dark_blue = '#0000ffbf'

        QtCore.QObject.__init__(self)
        self.ui = FlatCAMGUI(self.version, self.beta, self)


        # self.connect(self.ui,
        #              QtCore.SIGNAL("geomUpdate(int, int, int, int, int)"),
        #              self.save_geometry) PyQt4
        self.ui.geom_update[int, int, int, int, int].connect(self.save_geometry)
        self.ui.final_save.connect(self.final_save)

        ##############
        #### Data ####
        ##############
        self.recent = []
        self.clipboard = QtWidgets.QApplication.clipboard()
        self.proc_container = FCVisibleProcessContainer(self.ui.activity_view)

        self.project_filename = None
        self.toggle_units_ignore = False

        # self.defaults_form = PreferencesUI()

        # when adding entries here read the comments in the  method found bellow named:
        # def new_object(self, kind, name, initialize, active=True, fit=True, plot=True)
        self.defaults_form_fields = {
            # General App
            "units": self.ui.general_defaults_form.general_app_group.units_radio,
            "global_app_level": self.ui.general_defaults_form.general_app_group.app_level_radio,
            "global_language": self.ui.general_defaults_form.general_app_group.language_cb,

            "global_shell_at_startup": self.ui.general_defaults_form.general_app_group.shell_startup_cb,
            "global_version_check": self.ui.general_defaults_form.general_app_group.version_check_cb,
            "global_send_stats": self.ui.general_defaults_form.general_app_group.send_stats_cb,
            "global_pan_button": self.ui.general_defaults_form.general_app_group.pan_button_radio,
            "global_mselect_key": self.ui.general_defaults_form.general_app_group.mselect_radio,

            "global_project_at_startup": self.ui.general_defaults_form.general_app_group.project_startup_cb,
            "global_project_autohide": self.ui.general_defaults_form.general_app_group.project_autohide_cb,
            "global_toggle_tooltips": self.ui.general_defaults_form.general_app_group.toggle_tooltips_cb,

            "global_compression_level": self.ui.general_defaults_form.general_app_group.compress_combo,
            "global_save_compressed": self.ui.general_defaults_form.general_app_group.save_type_cb,

            # General GUI Preferences
            "global_gridx": self.ui.general_defaults_form.general_gui_group.gridx_entry,
            "global_gridy": self.ui.general_defaults_form.general_gui_group.gridy_entry,
            "global_snap_max": self.ui.general_defaults_form.general_gui_group.snap_max_dist_entry,
            "global_workspace": self.ui.general_defaults_form.general_gui_group.workspace_cb,
            "global_workspaceT": self.ui.general_defaults_form.general_gui_group.wk_cb,

            "global_plot_fill": self.ui.general_defaults_form.general_gui_group.pf_color_entry,
            "global_plot_line": self.ui.general_defaults_form.general_gui_group.pl_color_entry,
            "global_sel_fill": self.ui.general_defaults_form.general_gui_group.sf_color_entry,
            "global_sel_line": self.ui.general_defaults_form.general_gui_group.sl_color_entry,
            "global_alt_sel_fill": self.ui.general_defaults_form.general_gui_group.alt_sf_color_entry,
            "global_alt_sel_line": self.ui.general_defaults_form.general_gui_group.alt_sl_color_entry,
            "global_draw_color": self.ui.general_defaults_form.general_gui_group.draw_color_entry,
            "global_sel_draw_color": self.ui.general_defaults_form.general_gui_group.sel_draw_color_entry,

            # General GUI Settings
            "global_hover": self.ui.general_defaults_form.general_gui_set_group.hover_cb,

            # Gerber General
            "gerber_plot": self.ui.gerber_defaults_form.gerber_gen_group.plot_cb,
            "gerber_solid": self.ui.gerber_defaults_form.gerber_gen_group.solid_cb,
            "gerber_multicolored": self.ui.gerber_defaults_form.gerber_gen_group.multicolored_cb,
            "gerber_circle_steps": self.ui.gerber_defaults_form.gerber_gen_group.circle_steps_entry,

            # Gerber Options
            "gerber_isotooldia": self.ui.gerber_defaults_form.gerber_opt_group.iso_tool_dia_entry,
            "gerber_isopasses": self.ui.gerber_defaults_form.gerber_opt_group.iso_width_entry,
            "gerber_isooverlap": self.ui.gerber_defaults_form.gerber_opt_group.iso_overlap_entry,
            "gerber_combine_passes": self.ui.gerber_defaults_form.gerber_opt_group.combine_passes_cb,
            "gerber_milling_type": self.ui.gerber_defaults_form.gerber_opt_group.milling_type_radio,
            "gerber_noncoppermargin": self.ui.gerber_defaults_form.gerber_opt_group.noncopper_margin_entry,
            "gerber_noncopperrounded": self.ui.gerber_defaults_form.gerber_opt_group.noncopper_rounded_cb,
            "gerber_bboxmargin": self.ui.gerber_defaults_form.gerber_opt_group.bbmargin_entry,
            "gerber_bboxrounded": self.ui.gerber_defaults_form.gerber_opt_group.bbrounded_cb,

            # Gerber Advanced Options
            "gerber_aperture_display": self.ui.gerber_defaults_form.gerber_adv_opt_group.aperture_table_visibility_cb,
            "gerber_aperture_scale_factor": self.ui.gerber_defaults_form.gerber_adv_opt_group.scale_aperture_entry,
            "gerber_aperture_buffer_factor": self.ui.gerber_defaults_form.gerber_adv_opt_group.buffer_aperture_entry,
            "gerber_follow": self.ui.gerber_defaults_form.gerber_adv_opt_group.follow_cb,

            # Excellon General
            "excellon_plot": self.ui.excellon_defaults_form.excellon_gen_group.plot_cb,
            "excellon_solid": self.ui.excellon_defaults_form.excellon_gen_group.solid_cb,
            "excellon_format_upper_in": self.ui.excellon_defaults_form.excellon_gen_group.excellon_format_upper_in_entry,
            "excellon_format_lower_in": self.ui.excellon_defaults_form.excellon_gen_group.excellon_format_lower_in_entry,
            "excellon_format_upper_mm": self.ui.excellon_defaults_form.excellon_gen_group.excellon_format_upper_mm_entry,
            "excellon_format_lower_mm": self.ui.excellon_defaults_form.excellon_gen_group.excellon_format_lower_mm_entry,
            "excellon_zeros": self.ui.excellon_defaults_form.excellon_gen_group.excellon_zeros_radio,
            "excellon_units": self.ui.excellon_defaults_form.excellon_gen_group.excellon_units_radio,
            "excellon_optimization_type": self.ui.excellon_defaults_form.excellon_gen_group.excellon_optimization_radio,
            "excellon_search_time": self.ui.excellon_defaults_form.excellon_gen_group.optimization_time_entry,

            # Excellon Options
            "excellon_drillz": self.ui.excellon_defaults_form.excellon_opt_group.cutz_entry,
            "excellon_travelz": self.ui.excellon_defaults_form.excellon_opt_group.travelz_entry,
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
            "excellon_endz": self.ui.excellon_defaults_form.excellon_adv_opt_group.eendz_entry,
            "excellon_feedrate_rapid": self.ui.excellon_defaults_form.excellon_adv_opt_group.feedrate_rapid_entry,
            "excellon_z_pdepth": self.ui.excellon_defaults_form.excellon_adv_opt_group.pdepth_entry,
            "excellon_feedrate_probe": self.ui.excellon_defaults_form.excellon_adv_opt_group.feedrate_probe_entry,
            "excellon_f_plunge": self.ui.excellon_defaults_form.excellon_adv_opt_group.fplunge_cb,
            "excellon_f_retract": self.ui.excellon_defaults_form.excellon_adv_opt_group.fretract_cb,

            # Excellon Export
            "excellon_exp_units": self.ui.excellon_defaults_form.excellon_exp_group.excellon_units_radio,
            "excellon_exp_format": self.ui.excellon_defaults_form.excellon_exp_group.format_radio,
            "excellon_exp_integer": self.ui.excellon_defaults_form.excellon_exp_group.format_whole_entry,
            "excellon_exp_decimals": self.ui.excellon_defaults_form.excellon_exp_group.format_dec_entry,
            "excellon_exp_zeros": self.ui.excellon_defaults_form.excellon_exp_group.zeros_radio,

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
            "geometry_depthperpass": self.ui.geometry_defaults_form.geometry_opt_group.depthperpass_entry,
            "geometry_multidepth": self.ui.geometry_defaults_form.geometry_opt_group.multidepth_cb,

            # Geometry Advanced Options
            "geometry_toolchangexy": self.ui.geometry_defaults_form.geometry_adv_opt_group.toolchangexy_entry,
            "geometry_startz": self.ui.geometry_defaults_form.geometry_adv_opt_group.gstartz_entry,
            "geometry_endz": self.ui.geometry_defaults_form.geometry_adv_opt_group.gendz_entry,
            "geometry_feedrate_rapid": self.ui.geometry_defaults_form.geometry_adv_opt_group.cncfeedrate_rapid_entry,
            "geometry_extracut": self.ui.geometry_defaults_form.geometry_adv_opt_group.extracut_cb,
            "geometry_z_pdepth": self.ui.geometry_defaults_form.geometry_adv_opt_group.pdepth_entry,
            "geometry_feedrate_probe": self.ui.geometry_defaults_form.geometry_adv_opt_group.feedrate_probe_entry,
            "geometry_f_plunge": self.ui.geometry_defaults_form.geometry_adv_opt_group.fplunge_cb,
            "geometry_segx": self.ui.geometry_defaults_form.geometry_adv_opt_group.segx_entry,
            "geometry_segy": self.ui.geometry_defaults_form.geometry_adv_opt_group.segy_entry,

            # CNCJob General
            "cncjob_plot": self.ui.cncjob_defaults_form.cncjob_gen_group.plot_cb,
            "cncjob_plot_kind": self.ui.cncjob_defaults_form.cncjob_gen_group.cncplot_method_radio,
            "cncjob_tooldia": self.ui.cncjob_defaults_form.cncjob_gen_group.tooldia_entry,
            "cncjob_coords_decimals": self.ui.cncjob_defaults_form.cncjob_gen_group.coords_dec_entry,
            "cncjob_fr_decimals": self.ui.cncjob_defaults_form.cncjob_gen_group.fr_dec_entry,
            "cncjob_steps_per_circle": self.ui.cncjob_defaults_form.cncjob_gen_group.steps_per_circle_entry,

            # CNC Job Options
            "cncjob_prepend": self.ui.cncjob_defaults_form.cncjob_opt_group.prepend_text,
            "cncjob_append": self.ui.cncjob_defaults_form.cncjob_opt_group.append_text,

            # CNC Job Advanced Options
            "cncjob_toolchange_macro": self.ui.cncjob_defaults_form.cncjob_adv_opt_group.toolchange_text,
            "cncjob_toolchange_macro_enable": self.ui.cncjob_defaults_form.cncjob_adv_opt_group.toolchange_cb,

            # NCC Tool
            "tools_ncctools": self.ui.tools_defaults_form.tools_ncc_group.ncc_tool_dia_entry,
            "tools_nccoverlap": self.ui.tools_defaults_form.tools_ncc_group.ncc_overlap_entry,
            "tools_nccmargin": self.ui.tools_defaults_form.tools_ncc_group.ncc_margin_entry,
            "tools_nccmethod": self.ui.tools_defaults_form.tools_ncc_group.ncc_method_radio,
            "tools_nccconnect": self.ui.tools_defaults_form.tools_ncc_group.ncc_connect_cb,
            "tools_ncccontour": self.ui.tools_defaults_form.tools_ncc_group.ncc_contour_cb,
            "tools_nccrest": self.ui.tools_defaults_form.tools_ncc_group.ncc_rest_cb,

            # CutOut Tool
            "tools_cutouttooldia": self.ui.tools_defaults_form.tools_cutout_group.cutout_tooldia_entry,
            "tools_cutoutmargin": self.ui.tools_defaults_form.tools_cutout_group.cutout_margin_entry,
            "tools_cutoutgapsize": self.ui.tools_defaults_form.tools_cutout_group.cutout_gap_entry,
            "tools_gaps_ff": self.ui.tools_defaults_form.tools_cutout_group.gaps_combo,

            # Paint Area Tool
            "tools_painttooldia": self.ui.tools_defaults_form.tools_paint_group.painttooldia_entry,
            "tools_paintoverlap": self.ui.tools_defaults_form.tools_paint_group.paintoverlap_entry,
            "tools_paintmargin": self.ui.tools_defaults_form.tools_paint_group.paintmargin_entry,
            "tools_paintmethod": self.ui.tools_defaults_form.tools_paint_group.paintmethod_combo,
            "tools_selectmethod": self.ui.tools_defaults_form.tools_paint_group.selectmethod_combo,
            "tools_pathconnect": self.ui.tools_defaults_form.tools_paint_group.pathconnect_cb,
            "tools_paintcontour": self.ui.tools_defaults_form.tools_paint_group.contour_cb,

            # 2-sided Tool
            "tools_2sided_mirror_axis": self.ui.tools_defaults_form.tools_2sided_group.mirror_axis_radio,
            "tools_2sided_axis_loc": self.ui.tools_defaults_form.tools_2sided_group.axis_location_radio,
            "tools_2sided_drilldia": self.ui.tools_defaults_form.tools_2sided_group.drill_dia_entry,

            # Film Tool
            "tools_film_type": self.ui.tools_defaults_form.tools_film_group.film_type_radio,
            "tools_film_boundary": self.ui.tools_defaults_form.tools_film_group.film_boundary_entry,
            "tools_film_scale": self.ui.tools_defaults_form.tools_film_group.film_scale_entry,

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
            "tools_solderpaste_pp": self.ui.tools_defaults_form.tools_solderpaste_group.pp_combo

        }

        #############################
        #### LOAD POSTPROCESSORS ####
        #############################

        self.postprocessors = load_postprocessors(self)

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

        #############################
        #### LOAD LANGUAGES ####
        #############################

        self.languages = fcTranslate.load_languages()
        for name in sorted(self.languages.values()):
            self.ui.general_defaults_form.general_app_group.language_cb.addItem(name)

        self.defaults = LoudDict()
        self.defaults.set_change_callback(self.on_defaults_dict_change)  # When the dictionary changes.
        self.defaults.update({
            # Global APP Preferences
            "global_serial": 0,
            "global_stats": {},
            "units": "IN",
            "global_app_level": 'b',
            "global_language": 'English',
            "global_version_check": True,
            "global_send_stats": True,
            "global_pan_button": '2',
            "global_mselect_key": 'Control',
            "global_project_at_startup": False,
            "global_project_autohide": True,
            "global_toggle_tooltips": True,
            "global_compression_level": 3,
            "global_save_compressed": True,

            # Global GUI Preferences
            "global_gridx": 0.0393701,
            "global_gridy": 0.0393701,
            "global_snap_max": 0.001968504,
            "global_workspace": False,
            "global_workspaceT": "A4P",

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

            "global_toolbar_view": 127,

            "global_background_timeout": 300000,  # Default value is 5 minutes
            "global_verbose_error_level": 0,  # Shell verbosity 0 = default
            # (python trace only for unknown errors),
            # 1 = show trace(show trace allways),
            # 2 = (For the future).

            # Persistence
            "global_last_folder": None,
            "global_last_save_folder": None,

            # Default window geometry
            "global_def_win_x": 100,
            "global_def_win_y": 100,
            "global_def_win_w": 1024,
            "global_def_win_h": 650,

            # Constants...
            "global_defaults_save_period_ms": 20000,  # Time between default saves.
            "global_shell_shape": [500, 300],  # Shape of the shell in pixels.
            "global_shell_at_startup": False,  # Show the shell at startup.
            "global_recent_limit": 10,  # Max. items in recent list.

            "fit_key": 'V',
            "zoom_out_key": '-',
            "zoom_in_key": '=',
            "grid_toggle_key": 'G',
            "zoom_ratio": 1.5,
            "global_point_clipboard_format": "(%.4f, %.4f)",
            "global_zdownrate": None,

            # General GUI Settings
            "global_hover": True,

            # Gerber General
            "gerber_plot": True,
            "gerber_solid": True,
            "gerber_multicolored": False,
            "gerber_isotooldia": 0.016,
            "gerber_isopasses": 1,
            "gerber_isooverlap": 0.15,

            # Gerber Options
            "gerber_combine_passes": False,
            "gerber_milling_type": "cl",
            "gerber_noncoppermargin": 0.1,
            "gerber_noncopperrounded": False,
            "gerber_bboxmargin": 0.1,
            "gerber_bboxrounded": False,
            "gerber_circle_steps": 64,
            "gerber_use_buffer_for_union": True,

            # Gerber Advanced Options
            "gerber_aperture_display": False,
            "gerber_aperture_scale_factor": 1.0,
            "gerber_aperture_buffer_factor": 0.0,
            "gerber_follow": False,

            # Excellon General
            "excellon_plot": True,
            "excellon_solid": True,
            "excellon_format_upper_in": 2,
            "excellon_format_lower_in": 4,
            "excellon_format_upper_mm": 3,
            "excellon_format_lower_mm": 3,
            "excellon_zeros": "L",
            "excellon_units": "INCH",
            "excellon_optimization_type": 'B',
            "excellon_search_time": 3,

            # Excellon Options
            "excellon_drillz": -0.1,
            "excellon_travelz": 0.1,
            "excellon_feedrate": 3.0,
            "excellon_spindlespeed": None,
            "excellon_dwell": False,
            "excellon_dwelltime": 1,
            "excellon_toolchange": False,
            "excellon_toolchangez": 1.0,
            "excellon_ppname_e": 'default',
            "excellon_tooldia": 0.016,
            "excellon_slot_tooldia": 0.016,
            "excellon_gcode_type": "drills",

            # Excellon Advanced Options
            "excellon_offset": 0.0,
            "excellon_toolchangexy": "0.0, 0.0",
            "excellon_startz": None,
            "excellon_endz": 2.0,
            "excellon_feedrate_rapid": 3.0,
            "excellon_z_pdepth": -0.02,
            "excellon_feedrate_probe": 3.0,
            "excellon_f_plunge": False,
            "excellon_f_retract": False,

            # Excellon Export
            "excellon_exp_units": 'INCH',
            "excellon_exp_format": 'ndec',
            "excellon_exp_integer": 2,
            "excellon_exp_decimals": 4,
            "excellon_exp_zeros": 'LZ',

            # Geometry General
            "geometry_plot": True,
            "geometry_circle_steps": 64,
            "geometry_cnctooldia": 0.016,

            # Geometry Options
            "geometry_cutz": -0.002,
            "geometry_multidepth": False,
            "geometry_depthperpass": 0.002,
            "geometry_travelz": 0.1,
            "geometry_toolchange": False,
            "geometry_toolchangez": 1.0,
            "geometry_feedrate": 3.0,
            "geometry_feedrate_z": 3.0,
            "geometry_spindlespeed": None,
            "geometry_dwell": False,
            "geometry_dwelltime": 1,
            "geometry_ppname_g": 'default',

            # Geometry Advanced Options
            "geometry_toolchangexy": "0.0, 0.0",
            "geometry_startz": None,
            "geometry_endz": 2.0,
            "geometry_feedrate_rapid": 3.0,
            "geometry_extracut": False,
            "geometry_z_pdepth": -0.02,
            "geometry_f_plunge": False,
            "geometry_feedrate_probe": 3.0,
            "geometry_segx": 0.0,
            "geometry_segy": 0.0,

            # CNC Job General
            "cncjob_plot": True,
            "cncjob_plot_kind": 'all',
            "cncjob_tooldia": 0.0393701,
            "cncjob_coords_decimals": 4,
            "cncjob_fr_decimals": 2,
            "cncjob_steps_per_circle": 64,

            # CNC Job Options
            "cncjob_prepend": "",
            "cncjob_append": "",

            # CNC Job Advanced Options
            "cncjob_toolchange_macro": "",
            "cncjob_toolchange_macro_enable": False,

            "tools_ncctools": "0.0393701, 0.019685",
            "tools_nccoverlap": 0.015748,
            "tools_nccmargin": 0.00393701,
            "tools_nccmethod": "seed",
            "tools_nccconnect": True,
            "tools_ncccontour": True,
            "tools_nccrest": False,

            "tools_cutouttooldia": 0.00393701,
            "tools_cutoutmargin": 0.00393701,
            "tools_cutoutgapsize": 0.005905512,
            "tools_gaps_ff": "8",

            "tools_painttooldia": 0.07,
            "tools_paintoverlap": 0.15,
            "tools_paintmargin": 0.0,
            "tools_paintmethod": "seed",
            "tools_selectmethod": "single",
            "tools_pathconnect": True,
            "tools_paintcontour": True,

            "tools_2sided_mirror_axis": "X",
            "tools_2sided_axis_loc": "point",
            "tools_2sided_drilldia": 0.0393701,

            "tools_film_type": 'neg',
            "tools_film_boundary": 0.0393701,
            "tools_film_scale": 0,

            "tools_panelize_spacing_columns": 0,
            "tools_panelize_spacing_rows": 0,
            "tools_panelize_columns": 1,
            "tools_panelize_rows": 1,
            "tools_panelize_constrain": False,
            "tools_panelize_constrainx": 0.0,
            "tools_panelize_constrainy": 0.0,
            "tools_panelize_panel_type": 'gerber',

            "tools_calc_vshape_tip_dia": 0.007874,
            "tools_calc_vshape_tip_angle": 30,
            "tools_calc_vshape_cut_z": 0.000787,
            "tools_calc_electro_length": 10.0,
            "tools_calc_electro_width": 10.0,
            "tools_calc_electro_cdensity":13.0,
            "tools_calc_electro_growth": 10.0,

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

            "tools_solderpaste_tools": "0.0393701, 0.011811",
            "tools_solderpaste_new": 0.011811,
            "tools_solderpaste_z_start": 0.00019685039,
            "tools_solderpaste_z_dispense": 0.00393701,
            "tools_solderpaste_z_stop": 0.00019685039,
            "tools_solderpaste_z_travel": 0.00393701,
            "tools_solderpaste_z_toolchange": 0.0393701,
            "tools_solderpaste_xy_toolchange": "0.0, 0.0",
            "tools_solderpaste_frxy": 3.0,
            "tools_solderpaste_frz": 3.0,
            "tools_solderpaste_frz_dispense": 0.0393701,
            "tools_solderpaste_speedfwd": 20,
            "tools_solderpaste_dwellfwd": 1,
            "tools_solderpaste_speedrev": 10,
            "tools_solderpaste_dwellrev": 1,
            "tools_solderpaste_pp": 'Paste_1'
        })

        ###############################
        ### Load defaults from file ###
        ###############################

        if user_defaults:
            self.load_defaults(filename='current_defaults')

        ############################
        ##### APPLY APP LANGUAGE ###
        ############################

        ret_val = fcTranslate.apply_language('strings')

        if ret_val == "no language":
            self.inform.emit(_("[ERROR] Could not find the Language files. The App strings are missing."))
            log.debug("Could not find the Language files. The App strings are missing.")
        else:
            # make the current language the current selection on the language combobox
            self.ui.general_defaults_form.general_app_group.language_cb.setCurrentText(ret_val)
            log.debug("App.__init__() --> Applied %s language." % str(ret_val).capitalize())


        ###################################
        ### CREATE UNIQUE SERIAL NUMBER ###
        ###################################

        chars = 'abcdefghijklmnopqrstuvwxyz0123456789'
        if self.defaults['global_serial'] == 0 or len(str(self.defaults['global_serial'])) < 10:
            self.defaults['global_serial'] = ''.join([random.choice(chars) for i in range(20)])
            self.save_defaults(silent=True)

        self.propagate_defaults(silent=True)
        self.restore_main_win_geom()

        def auto_save_defaults():
            try:
                self.save_defaults(silent=True)
                self.propagate_defaults(silent=True)
            finally:
                QtCore.QTimer.singleShot(self.defaults["global_defaults_save_period_ms"], auto_save_defaults)

        # the following lines activates automatic defaults save
        # if user_defaults:
        #     QtCore.QTimer.singleShot(self.defaults["global_defaults_save_period_ms"], auto_save_defaults)

        # self.options_form = PreferencesUI()

        self.options_form_fields = {
            "units": self.ui.general_options_form.general_app_group.units_radio,
            "global_gridx": self.ui.general_options_form.general_gui_group.gridx_entry,
            "global_gridy": self.ui.general_options_form.general_gui_group.gridy_entry,
            "global_snap_max": self.ui.general_options_form.general_gui_group.snap_max_dist_entry,

            "gerber_plot": self.ui.gerber_options_form.gerber_gen_group.plot_cb,
            "gerber_solid": self.ui.gerber_options_form.gerber_gen_group.solid_cb,
            "gerber_multicolored": self.ui.gerber_options_form.gerber_gen_group.multicolored_cb,

            "gerber_isotooldia": self.ui.gerber_options_form.gerber_opt_group.iso_tool_dia_entry,
            "gerber_isopasses": self.ui.gerber_options_form.gerber_opt_group.iso_width_entry,
            "gerber_isooverlap": self.ui.gerber_options_form.gerber_opt_group.iso_overlap_entry,
            "gerber_combine_passes": self.ui.gerber_options_form.gerber_opt_group.combine_passes_cb,
            "gerber_noncoppermargin": self.ui.gerber_options_form.gerber_opt_group.noncopper_margin_entry,
            "gerber_noncopperrounded": self.ui.gerber_options_form.gerber_opt_group.noncopper_rounded_cb,
            "gerber_bboxmargin": self.ui.gerber_options_form.gerber_opt_group.bbmargin_entry,
            "gerber_bboxrounded": self.ui.gerber_options_form.gerber_opt_group.bbrounded_cb,

            "excellon_plot": self.ui.excellon_options_form.excellon_gen_group.plot_cb,
            "excellon_solid": self.ui.excellon_options_form.excellon_gen_group.solid_cb,
            "excellon_format_upper_in": self.ui.excellon_options_form.excellon_gen_group.excellon_format_upper_in_entry,
            "excellon_format_lower_in": self.ui.excellon_options_form.excellon_gen_group.excellon_format_lower_in_entry,
            "excellon_format_upper_mm": self.ui.excellon_options_form.excellon_gen_group.excellon_format_upper_mm_entry,
            "excellon_format_lower_mm": self.ui.excellon_options_form.excellon_gen_group.excellon_format_lower_mm_entry,
            "excellon_zeros": self.ui.excellon_options_form.excellon_gen_group.excellon_zeros_radio,
            "excellon_units": self.ui.excellon_options_form.excellon_gen_group.excellon_units_radio,
            "excellon_optimization_type": self.ui.excellon_options_form.excellon_gen_group.excellon_optimization_radio,

            "excellon_drillz": self.ui.excellon_options_form.excellon_opt_group.cutz_entry,
            "excellon_travelz": self.ui.excellon_options_form.excellon_opt_group.travelz_entry,
            "excellon_feedrate": self.ui.excellon_options_form.excellon_opt_group.feedrate_entry,
            "excellon_spindlespeed": self.ui.excellon_options_form.excellon_opt_group.spindlespeed_entry,
            "excellon_dwell": self.ui.excellon_options_form.excellon_opt_group.dwell_cb,
            "excellon_dwelltime": self.ui.excellon_options_form.excellon_opt_group.dwelltime_entry,
            "excellon_toolchange": self.ui.excellon_options_form.excellon_opt_group.toolchange_cb,
            "excellon_toolchangez": self.ui.excellon_options_form.excellon_opt_group.toolchangez_entry,
            "excellon_tooldia": self.ui.excellon_options_form.excellon_opt_group.tooldia_entry,
            "excellon_ppname_e": self.ui.excellon_options_form.excellon_opt_group.pp_excellon_name_cb,

            "excellon_feedrate_rapid": self.ui.excellon_options_form.excellon_adv_opt_group.feedrate_rapid_entry,
            "excellon_toolchangexy": self.ui.excellon_options_form.excellon_adv_opt_group.toolchangexy_entry,
            "excellon_f_plunge": self.ui.excellon_options_form.excellon_adv_opt_group.fplunge_cb,
            "excellon_startz": self.ui.excellon_options_form.excellon_adv_opt_group.estartz_entry,
            "excellon_endz": self.ui.excellon_options_form.excellon_adv_opt_group.eendz_entry,

            "geometry_plot": self.ui.geometry_options_form.geometry_gen_group.plot_cb,
            "geometry_cnctooldia": self.ui.geometry_options_form.geometry_gen_group.cnctooldia_entry,

            "geometry_cutz": self.ui.geometry_options_form.geometry_opt_group.cutz_entry,
            "geometry_travelz": self.ui.geometry_options_form.geometry_opt_group.travelz_entry,
            "geometry_feedrate": self.ui.geometry_options_form.geometry_opt_group.cncfeedrate_entry,
            "geometry_feedrate_z": self.ui.geometry_options_form.geometry_opt_group.cncplunge_entry,
            "geometry_spindlespeed": self.ui.geometry_options_form.geometry_opt_group.cncspindlespeed_entry,
            "geometry_dwell": self.ui.geometry_options_form.geometry_opt_group.dwell_cb,
            "geometry_dwelltime": self.ui.geometry_options_form.geometry_opt_group.dwelltime_entry,
            "geometry_ppname_g": self.ui.geometry_options_form.geometry_opt_group.pp_geometry_name_cb,
            "geometry_toolchange": self.ui.geometry_options_form.geometry_opt_group.toolchange_cb,
            "geometry_toolchangez": self.ui.geometry_options_form.geometry_opt_group.toolchangez_entry,
            "geometry_depthperpass": self.ui.geometry_options_form.geometry_opt_group.depthperpass_entry,
            "geometry_multidepth": self.ui.geometry_options_form.geometry_opt_group.multidepth_cb,

            "geometry_segx": self.ui.geometry_options_form.geometry_adv_opt_group.segx_entry,
            "geometry_segy": self.ui.geometry_options_form.geometry_adv_opt_group.segy_entry,
            "geometry_feedrate_rapid": self.ui.geometry_options_form.geometry_adv_opt_group.cncfeedrate_rapid_entry,
            "geometry_f_plunge": self.ui.geometry_options_form.geometry_adv_opt_group.fplunge_cb,
            "geometry_toolchangexy": self.ui.geometry_options_form.geometry_adv_opt_group.toolchangexy_entry,
            "geometry_startz": self.ui.geometry_options_form.geometry_adv_opt_group.gstartz_entry,
            "geometry_endz": self.ui.geometry_options_form.geometry_adv_opt_group.gendz_entry,
            "geometry_extracut": self.ui.geometry_options_form.geometry_adv_opt_group.extracut_cb,

            "cncjob_plot": self.ui.cncjob_options_form.cncjob_gen_group.plot_cb,
            "cncjob_tooldia": self.ui.cncjob_options_form.cncjob_gen_group.tooldia_entry,

            "cncjob_prepend": self.ui.cncjob_options_form.cncjob_opt_group.prepend_text,
            "cncjob_append": self.ui.cncjob_options_form.cncjob_opt_group.append_text,

            "tools_ncctools": self.ui.tools_options_form.tools_ncc_group.ncc_tool_dia_entry,
            "tools_nccoverlap": self.ui.tools_options_form.tools_ncc_group.ncc_overlap_entry,
            "tools_nccmargin": self.ui.tools_options_form.tools_ncc_group.ncc_margin_entry,

            "tools_cutouttooldia": self.ui.tools_options_form.tools_cutout_group.cutout_tooldia_entry,
            "tools_cutoutmargin": self.ui.tools_options_form.tools_cutout_group.cutout_margin_entry,
            "tools_cutoutgapsize": self.ui.tools_options_form.tools_cutout_group.cutout_gap_entry,
            "tools_gaps_ff": self.ui.tools_options_form.tools_cutout_group.gaps_combo,

            "tools_painttooldia": self.ui.tools_options_form.tools_paint_group.painttooldia_entry,
            "tools_paintoverlap": self.ui.tools_options_form.tools_paint_group.paintoverlap_entry,
            "tools_paintmargin": self.ui.tools_options_form.tools_paint_group.paintmargin_entry,
            "tools_paintmethod": self.ui.tools_options_form.tools_paint_group.paintmethod_combo,
            "tools_selectmethod": self.ui.tools_options_form.tools_paint_group.selectmethod_combo,
            "tools_pathconnect": self.ui.tools_options_form.tools_paint_group.pathconnect_cb,
            "tools_paintcontour": self.ui.tools_options_form.tools_paint_group.contour_cb,

            "tools_2sided_mirror_axis": self.ui.tools_options_form.tools_2sided_group.mirror_axis_radio,
            "tools_2sided_axis_loc": self.ui.tools_options_form.tools_2sided_group.axis_location_radio,
            "tools_2sided_drilldia": self.ui.tools_options_form.tools_2sided_group.drill_dia_entry,

            "tools_film_type": self.ui.tools_options_form.tools_film_group.film_type_radio,
            "tools_film_boundary": self.ui.tools_options_form.tools_film_group.film_boundary_entry,
            "tools_film_scale": self.ui.tools_options_form.tools_film_group.film_scale_entry,

            "tools_panelize_spacing_columns": self.ui.tools_options_form.tools_panelize_group.pspacing_columns,
            "tools_panelize_spacing_rows": self.ui.tools_options_form.tools_panelize_group.pspacing_rows,
            "tools_panelize_columns": self.ui.tools_options_form.tools_panelize_group.pcolumns,
            "tools_panelize_rows": self.ui.tools_options_form.tools_panelize_group.prows,
            "tools_panelize_constrain": self.ui.tools_options_form.tools_panelize_group.pconstrain_cb,
            "tools_panelize_constrainx": self.ui.tools_options_form.tools_panelize_group.px_width_entry,
            "tools_panelize_constrainy": self.ui.tools_options_form.tools_panelize_group.py_height_entry

        }

        for name in list(self.postprocessors.keys()):
            self.ui.geometry_options_form.geometry_opt_group.pp_geometry_name_cb.addItem(name)
            self.ui.excellon_options_form.excellon_opt_group.pp_excellon_name_cb.addItem(name)

        self.options = LoudDict()
        self.options.set_change_callback(self.on_options_dict_change)
        self.options.update({
            "units": "IN",
            "global_gridx": 1.0,
            "global_gridy": 1.0,
            "global_snap_max": 0.05,
            "global_background_timeout": 300000,  # Default value is 5 minutes
            "global_verbose_error_level": 0,  # Shell verbosity:
            # 0 = default(python trace only for unknown errors),
            # 1 = show trace(show trace allways), 2 = (For the future).

            "gerber_plot": True,
            "gerber_solid": True,
            "gerber_multicolored": False,
            "gerber_isotooldia": 0.016,
            "gerber_isopasses": 1,
            "gerber_isooverlap": 0.15,
            "gerber_combine_passes": True,
            "gerber_noncoppermargin": 0.0,
            "gerber_noncopperrounded": False,
            "gerber_bboxmargin": 0.0,
            "gerber_bboxrounded": False,

            "excellon_plot": True,
            "excellon_solid": False,
            "excellon_format_upper_in": 2,
            "excellon_format_lower_in": 4,
            "excellon_format_upper_mm": 3,
            "excellon_format_lower_mm": 3,
            "excellon_units": 'INCH',
            "excellon_optimization_type": 'B',
            "excellon_search_time": 3,
            "excellon_zeros": "L",

            "excellon_drillz": -0.1,
            "excellon_travelz": 0.1,
            "excellon_feedrate": 3.0,
            "excellon_feedrate_rapid": 3.0,
            "excellon_spindlespeed": None,
            "excellon_dwell": True,
            "excellon_dwelltime": 1000,
            "excellon_toolchange": False,
            "excellon_toolchangez": 1.0,
            "excellon_toolchangexy": "0.0, 0.0",
            "excellon_tooldia": 0.016,
            "excellon_ppname_e": 'default',
            "excellon_f_plunge": False,
            "excellon_startz": None,
            "excellon_endz": 2.0,

            "geometry_plot": True,
            "geometry_segx": 0.0,
            "geometry_segy": 0.0,
            "geometry_cutz": -0.002,
            "geometry_travelz": 0.1,
            "geometry_feedrate": 3.0,
            "geometry_feedrate_z": 3.0,
            "geometry_feedrate_rapid": 3.0,
            "geometry_spindlespeed": None,
            "geometry_dwell": True,
            "geometry_dwelltime": 1000,
            "geometry_cnctooldia": 0.016,
            "geometry_toolchange": False,
            "geometry_toolchangez": 2.0,
            "geometry_toolchangexy": "0.0, 0.0",
            "geometry_startz": None,
            "geometry_endz": 2.0,
            "geometry_ppname_g": "default",
            "geometry_f_plunge": False,
            "geometry_depthperpass": 0.002,
            "geometry_multidepth": False,
            "geometry_extracut": False,

            "cncjob_plot": True,
            "cncjob_tooldia": 0.016,
            "cncjob_prepend": "",
            "cncjob_append": "",

            "tools_ncctools": "1.0, 0.5",
            "tools_nccoverlap": 0.4,
            "tools_nccmargin": 1,

            "tools_cutouttooldia": 0.07,
            "tools_cutoutmargin": 0.1,
            "tools_cutoutgapsize": 0.15,
            "tools_gaps_ff": "8",

            "tools_painttooldia": 0.07,
            "tools_paintoverlap": 0.15,
            "tools_paintmargin": 0.0,
            "tools_paintmethod": "seed",
            "tools_selectmethod": "single",
            "tools_pathconnect": True,
            "tools_paintcontour": True,

            "tools_2sided_mirror_axis": "X",
            "tools_2sided_axis_loc": 'point',
            "tools_2sided_drilldia": 1,

            "tools_film_type": 'neg',
            "tools_film_boundary": 1,
            "tools_film_scale": 0,

            "tools_panelize_spacing_columns": 0,
            "tools_panelize_spacing_rows": 0,
            "tools_panelize_columns": 1,
            "tools_panelize_rows": 1,
            "tools_panelize_constrain": False,
            "tools_panelize_constrainx": 0.0,
            "tools_panelize_constrainy": 0.0

        })

        self.options.update(self.defaults)  # Copy app defaults to project options

        self.gen_form = None
        self.ger_form = None
        self.exc_form = None
        self.geo_form = None
        self.cnc_form = None
        self.tools_form = None
        self.on_options_combo_change(0)  # Will show the initial form

        ### Define OBJECT COLLECTION ###
        self.collection = ObjectCollection(self)
        self.ui.project_tab_layout.addWidget(self.collection.view)
        ###

        self.log.debug("Finished creating Object Collection.")

        ### Initialize the color box's color in Preferences -> Global -> Color
        # Init Plot Colors
        self.ui.general_defaults_form.general_gui_group.pf_color_entry.set_value(self.defaults['global_plot_fill'])
        self.ui.general_defaults_form.general_gui_group.pf_color_button.setStyleSheet(
            "background-color:%s" % str(self.defaults['global_plot_fill'])[:7])
        self.ui.general_defaults_form.general_gui_group.pf_color_alpha_spinner.set_value(
            int(self.defaults['global_plot_fill'][7:9], 16))
        self.ui.general_defaults_form.general_gui_group.pf_color_alpha_slider.setValue(
            int(self.defaults['global_plot_fill'][7:9], 16))

        self.ui.general_defaults_form.general_gui_group.pl_color_entry.set_value(self.defaults['global_plot_line'])
        self.ui.general_defaults_form.general_gui_group.pl_color_button.setStyleSheet(
            "background-color:%s" % str(self.defaults['global_plot_line'])[:7])

        # Init Left-Right Selection colors
        self.ui.general_defaults_form.general_gui_group.sf_color_entry.set_value(self.defaults['global_sel_fill'])
        self.ui.general_defaults_form.general_gui_group.sf_color_button.setStyleSheet(
            "background-color:%s" % str(self.defaults['global_sel_fill'])[:7])
        self.ui.general_defaults_form.general_gui_group.sf_color_alpha_spinner.set_value(
            int(self.defaults['global_sel_fill'][7:9], 16))
        self.ui.general_defaults_form.general_gui_group.sf_color_alpha_slider.setValue(
            int(self.defaults['global_sel_fill'][7:9], 16))

        self.ui.general_defaults_form.general_gui_group.sl_color_entry.set_value(self.defaults['global_sel_line'])
        self.ui.general_defaults_form.general_gui_group.sl_color_button.setStyleSheet(
            "background-color:%s" % str(self.defaults['global_sel_line'])[:7])

        # Init Right-Left Selection colors
        self.ui.general_defaults_form.general_gui_group.alt_sf_color_entry.set_value(self.defaults['global_alt_sel_fill'])
        self.ui.general_defaults_form.general_gui_group.alt_sf_color_button.setStyleSheet(
            "background-color:%s" % str(self.defaults['global_alt_sel_fill'])[:7])
        self.ui.general_defaults_form.general_gui_group.alt_sf_color_alpha_spinner.set_value(
            int(self.defaults['global_sel_fill'][7:9], 16))
        self.ui.general_defaults_form.general_gui_group.alt_sf_color_alpha_slider.setValue(
            int(self.defaults['global_sel_fill'][7:9], 16))

        self.ui.general_defaults_form.general_gui_group.alt_sl_color_entry.set_value(self.defaults['global_alt_sel_line'])
        self.ui.general_defaults_form.general_gui_group.alt_sl_color_button.setStyleSheet(
            "background-color:%s" % str(self.defaults['global_alt_sel_line'])[:7])

        # Init Draw color and Selection Draw Color
        self.ui.general_defaults_form.general_gui_group.draw_color_entry.set_value(self.defaults['global_draw_color'])
        self.ui.general_defaults_form.general_gui_group.draw_color_button.setStyleSheet(
            "background-color:%s" % str(self.defaults['global_draw_color'])[:7])

        self.ui.general_defaults_form.general_gui_group.sel_draw_color_entry.set_value(self.defaults['global_sel_draw_color'])
        self.ui.general_defaults_form.general_gui_group.sel_draw_color_button.setStyleSheet(
            "background-color:%s" % str(self.defaults['global_sel_draw_color'])[:7])
        #### End of Data ####

        #### Plot Area ####
        start_plot_time = time.time()   # debug
        self.plotcanvas = PlotCanvas(self.ui.right_layout, self)

        self.plotcanvas.vis_connect('mouse_move', self.on_mouse_move_over_plot)
        self.plotcanvas.vis_connect('mouse_press', self.on_mouse_click_over_plot)
        self.plotcanvas.vis_connect('mouse_release', self.on_mouse_click_release_over_plot)
        self.plotcanvas.vis_connect('mouse_double_click', self.on_double_click_over_plot)

        # Keys over plot enabled
        self.plotcanvas.vis_connect('key_press', self.ui.keyPressEvent)

        self.ui.splitter.setStretchFactor(1, 2)

        # So it can receive key presses
        self.plotcanvas.vispy_canvas.native.setFocus()

        self.app_cursor = self.plotcanvas.new_cursor()
        self.app_cursor.enabled = False

        # to use for tools like Measurement tool who depends on the event sources who are changed inside the Editors
        # depending on from where those tools are called different actions can be done
        self.call_source = 'app'

        end_plot_time = time.time()
        self.log.debug("Finished Canvas initialization in %s seconds." % (str(end_plot_time - start_plot_time)))

        ### EDITOR section
        self.geo_editor = FlatCAMGeoEditor(self, disabled=True)
        self.exc_editor = FlatCAMExcEditor(self)


        #### Adjust tabs width ####
        # self.collection.view.setMinimumWidth(self.ui.options_scroll_area.widget().sizeHint().width() +
        #     self.ui.options_scroll_area.verticalScrollBar().sizeHint().width())
        self.collection.view.setMinimumWidth(290)

        self.log.debug("Finished adding Geometry and Excellon Editor's.")

        #### Worker ####
        self.workers = WorkerStack()
        self.worker_task.connect(self.workers.add_task)


        ### Signal handling ###
        ## Custom signals
        self.inform.connect(self.info)
        self.message.connect(self.message_dialog)
        self.progress.connect(self.set_progress_bar)
        self.object_created.connect(self.on_object_created)
        self.object_changed.connect(self.on_object_changed)
        self.object_plotted.connect(self.on_object_plotted)
        self.plots_updated.connect(self.on_plots_updated)
        self.file_opened.connect(self.register_recent)
        self.file_opened.connect(lambda kind, filename: self.register_folder(filename))
        self.file_saved.connect(lambda kind, filename: self.register_save_folder(filename))


        ## Standard signals
        # Menu
        self.ui.menufilenewproject.triggered.connect(self.on_file_new_click)
        self.ui.menufilenewgeo.triggered.connect(self.new_geometry_object)
        self.ui.menufilenewexc.triggered.connect(self.new_excellon_object)

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


        self.ui.menufileexportdxf.triggered.connect(self.on_file_exportdxf)

        self.ui.menufilesaveproject.triggered.connect(self.on_file_saveproject)
        self.ui.menufilesaveprojectas.triggered.connect(self.on_file_saveprojectas)
        self.ui.menufilesaveprojectcopy.triggered.connect(lambda: self.on_file_saveprojectas(make_copy=True))
        self.ui.menufilesavedefaults.triggered.connect(self.on_file_savedefaults)
        self.ui.menufile_exit.triggered.connect(self.on_app_exit)

        self.ui.menueditedit.triggered.connect(self.object2editor)
        self.ui.menueditok.triggered.connect(self.editor2object)

        self.ui.menuedit_convertjoin.triggered.connect(self.on_edit_join)
        self.ui.menuedit_convertjoinexc.triggered.connect(self.on_edit_join_exc)
        self.ui.menuedit_convertjoingrb.triggered.connect(self.on_edit_join_grb)

        self.ui.menuedit_convert_sg2mg.triggered.connect(self.on_convert_singlegeo_to_multigeo)
        self.ui.menuedit_convert_mg2sg.triggered.connect(self.on_convert_multigeo_to_singlegeo)

        self.ui.menueditdelete.triggered.connect(self.on_delete)

        self.ui.menueditcopyobject.triggered.connect(self.on_copy_object)
        self.ui.menueditcopyobjectasgeom.triggered.connect(self.on_copy_object_as_geometry)
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

        self.ui.menuviewdisableall.triggered.connect(self.disable_all_plots)
        self.ui.menuviewdisableother.triggered.connect(self.disable_other_plots)
        self.ui.menuviewenable.triggered.connect(self.enable_all_plots)
        self.ui.menuview_zoom_fit.triggered.connect(self.on_zoom_fit)
        self.ui.menuview_zoom_in.triggered.connect(lambda: self.plotcanvas.zoom(1 / 1.5))
        self.ui.menuview_zoom_out.triggered.connect(lambda: self.plotcanvas.zoom(1.5))
        self.ui.menuview_toggle_code_editor.triggered.connect(self.on_toggle_code_editor)
        self.ui.menuview_toggle_fscreen.triggered.connect(self.on_fullscreen)
        self.ui.menuview_toggle_parea.triggered.connect(self.on_toggle_plotarea)
        self.ui.menuview_toggle_notebook.triggered.connect(self.on_toggle_notebook)

        self.ui.menuview_toggle_grid.triggered.connect(self.on_toggle_grid)
        self.ui.menuview_toggle_axis.triggered.connect(self.on_toggle_axis)
        self.ui.menuview_toggle_workspace.triggered.connect(self.on_workspace_menu)

        self.ui.menutoolshell.triggered.connect(self.on_toggle_shell)

        self.ui.menuhelp_about.triggered.connect(self.on_about)
        self.ui.menuhelp_home.triggered.connect(lambda: webbrowser.open(self.app_url))
        self.ui.menuhelp_manual.triggered.connect(lambda: webbrowser.open(self.manual_url))
        self.ui.menuhelp_videohelp.triggered.connect(lambda: webbrowser.open(self.video_url))
        self.ui.menuhelp_shortcut_list.triggered.connect(self.on_shortcut_list)

        self.ui.menuprojectenable.triggered.connect(lambda: self.enable_plots(self.collection.get_selected()))
        self.ui.menuprojectdisable.triggered.connect(lambda: self.disable_plots(self.collection.get_selected()))
        self.ui.menuprojectgeneratecnc.triggered.connect(lambda: self.generate_cnc_job(self.collection.get_selected()))
        self.ui.menuprojectviewsource.triggered.connect(self.on_view_source)

        self.ui.menuprojectcopy.triggered.connect(self.on_copy_object)
        self.ui.menuprojectedit.triggered.connect(self.object2editor)

        self.ui.menuprojectdelete.triggered.connect(self.on_delete)
        self.ui.menuprojectsave.triggered.connect(self.on_project_context_save)
        self.ui.menuprojectproperties.triggered.connect(self.obj_properties)

        # ToolBar signals
        self.connect_toolbar_signals()

        # Context Menu
        self.ui.popmenu_disable.triggered.connect(lambda: self.disable_plots(self.collection.get_selected()))

        self.ui.popmenu_new_geo.triggered.connect(self.new_geometry_object)
        self.ui.popmenu_new_exc.triggered.connect(self.new_excellon_object)
        self.ui.popmenu_new_prj.triggered.connect(self.on_file_new)

        self.ui.draw_line.triggered.connect(self.geo_editor.draw_tool_path)
        self.ui.draw_rect.triggered.connect(self.geo_editor.draw_tool_rectangle)
        self.ui.draw_cut.triggered.connect(self.geo_editor.cutpath)
        self.ui.draw_move.triggered.connect(self.geo_editor.on_move)

        self.ui.drill.triggered.connect(self.exc_editor.exc_add_drill)
        self.ui.drill_array.triggered.connect(self.exc_editor.exc_add_drill_array)
        self.ui.drill_copy.triggered.connect(self.exc_editor.exc_copy_drills)


        self.ui.zoomfit.triggered.connect(self.on_zoom_fit)
        self.ui.clearplot.triggered.connect(self.clear_plots)
        self.ui.replot.triggered.connect(self.plot_all)

        self.ui.popmenu_copy.triggered.connect(self.on_copy_object)
        self.ui.popmenu_delete.triggered.connect(self.on_delete)
        self.ui.popmenu_edit.triggered.connect(self.object2editor)
        self.ui.popmenu_save.triggered.connect(self.editor2object)
        self.ui.popmenu_move.triggered.connect(self.obj_move)

        self.ui.popmenu_properties.triggered.connect(self.obj_properties)

        # Preferences Plot Area TAB
        self.ui.options_combo.activated.connect(self.on_options_combo_change)
        self.ui.pref_save_button.clicked.connect(self.on_save_button)
        self.ui.pref_import_button.clicked.connect(self.on_import_preferences)
        self.ui.pref_export_button.clicked.connect(self.on_export_preferences)
        self.ui.pref_open_button.clicked.connect(self.on_preferences_open_folder)

        ###############################
        ### GUI PREFERENCES SIGNALS ###
        ###############################
        self.ui.general_options_form.general_app_group.units_radio.group_toggle_fn = self.on_toggle_units
        self.ui.general_defaults_form.general_app_group.language_apply_btn.clicked.connect(
            lambda: fcTranslate.on_language_apply_click(self, restart=True)
        )
        self.ui.general_defaults_form.general_app_group.units_radio.activated_custom.connect(self.on_toggle_units)

        ###############################
        ### GUI PREFERENCES SIGNALS ###
        ###############################

        # Setting plot colors signals
        self.ui.general_defaults_form.general_gui_group.pf_color_entry.editingFinished.connect(self.on_pf_color_entry)
        self.ui.general_defaults_form.general_gui_group.pf_color_button.clicked.connect(self.on_pf_color_button)
        self.ui.general_defaults_form.general_gui_group.pf_color_alpha_spinner.valueChanged.connect(self.on_pf_color_spinner)
        self.ui.general_defaults_form.general_gui_group.pf_color_alpha_slider.valueChanged.connect(self.on_pf_color_slider)
        self.ui.general_defaults_form.general_gui_group.pl_color_entry.editingFinished.connect(self.on_pl_color_entry)
        self.ui.general_defaults_form.general_gui_group.pl_color_button.clicked.connect(self.on_pl_color_button)
        # Setting selection (left - right) colors signals
        self.ui.general_defaults_form.general_gui_group.sf_color_entry.editingFinished.connect(self.on_sf_color_entry)
        self.ui.general_defaults_form.general_gui_group.sf_color_button.clicked.connect(self.on_sf_color_button)
        self.ui.general_defaults_form.general_gui_group.sf_color_alpha_spinner.valueChanged.connect(self.on_sf_color_spinner)
        self.ui.general_defaults_form.general_gui_group.sf_color_alpha_slider.valueChanged.connect(self.on_sf_color_slider)
        self.ui.general_defaults_form.general_gui_group.sl_color_entry.editingFinished.connect(self.on_sl_color_entry)
        self.ui.general_defaults_form.general_gui_group.sl_color_button.clicked.connect(self.on_sl_color_button)
        # Setting selection (right - left) colors signals
        self.ui.general_defaults_form.general_gui_group.alt_sf_color_entry.editingFinished.connect(self.on_alt_sf_color_entry)
        self.ui.general_defaults_form.general_gui_group.alt_sf_color_button.clicked.connect(self.on_alt_sf_color_button)
        self.ui.general_defaults_form.general_gui_group.alt_sf_color_alpha_spinner.valueChanged.connect(
            self.on_alt_sf_color_spinner)
        self.ui.general_defaults_form.general_gui_group.alt_sf_color_alpha_slider.valueChanged.connect(
            self.on_alt_sf_color_slider)
        self.ui.general_defaults_form.general_gui_group.alt_sl_color_entry.editingFinished.connect(self.on_alt_sl_color_entry)
        self.ui.general_defaults_form.general_gui_group.alt_sl_color_button.clicked.connect(self.on_alt_sl_color_button)
        # Setting Editor Draw colors signals
        self.ui.general_defaults_form.general_gui_group.draw_color_entry.editingFinished.connect(self.on_draw_color_entry)
        self.ui.general_defaults_form.general_gui_group.draw_color_button.clicked.connect(self.on_draw_color_button)

        self.ui.general_defaults_form.general_gui_group.sel_draw_color_entry.editingFinished.connect(self.on_sel_draw_color_entry)
        self.ui.general_defaults_form.general_gui_group.sel_draw_color_button.clicked.connect(self.on_sel_draw_color_button)

        self.ui.general_defaults_form.general_gui_group.wk_cb.currentIndexChanged.connect(self.on_workspace_modified)
        self.ui.general_defaults_form.general_gui_group.workspace_cb.stateChanged.connect(self.on_workspace)

        self.ui.general_defaults_form.general_gui_set_group.layout_combo.activated.connect(self.on_layout)

        self.ui.cncjob_defaults_form.cncjob_adv_opt_group.tc_variable_combo.currentIndexChanged[str].connect(
            self.on_cnc_custom_parameters)

        # Modify G-CODE Plot Area TAB
        self.ui.code_editor.textChanged.connect(self.handleTextChanged)
        self.ui.buttonOpen.clicked.connect(self.handleOpen)
        self.ui.buttonSave.clicked.connect(self.handleSaveGCode)
        self.ui.buttonPrint.clicked.connect(self.handlePrint)
        self.ui.buttonPreview.clicked.connect(self.handlePreview)
        self.ui.buttonFind.clicked.connect(self.handleFindGCode)
        self.ui.buttonReplace.clicked.connect(self.handleReplaceGCode)

        # Object list
        self.collection.view.activated.connect(self.on_row_activated)

        # Monitor the checkbox from the Application Defaults Tab and show the TCL shell or not depending on it's value
        self.ui.general_defaults_form.general_app_group.shell_startup_cb.clicked.connect(self.on_toggle_shell)

        # Load the defaults values into the Excellon Format and Excellon Zeros fields
        self.ui.excellon_defaults_form.excellon_opt_group.excellon_defaults_button.clicked.connect(
            self.on_excellon_defaults_button)

        # Load the defaults values into the Excellon Format and Excellon Zeros fields
        self.ui.excellon_options_form.excellon_opt_group.excellon_defaults_button.clicked.connect(
            self.on_excellon_options_button)

        # this is a flag to signal to other tools that the ui tooltab is locked and not accessible
        self.tool_tab_locked = False

        # decide if to show or hide the Notebook side of the screen at startup
        if self.defaults["global_project_at_startup"] is True:
            self.ui.splitter.setSizes([1, 1])
        else:
            self.ui.splitter.setSizes([0, 1])


        ####################
        ### Other setups ###
        ####################
        # Sets up FlatCAMObj, FCProcess and FCProcessContainer.
        self.setup_obj_classes()

        self.setup_recent_items()
        self.setup_component_editor()

        #############
        ### Shell ###
        #############

        ###
        # Auto-complete KEYWORDS
        self.tcl_commands_list = ['add_circle', 'add_poly', 'add_polygon', 'add_polyline', 'add_rectangle',
                                  'aligndrill', 'clear',
                                  'aligndrillgrid', 'cncjob', 'cutout', 'delete', 'drillcncjob',
                                  'export_gcode',
                                  'export_svg', 'ext', 'exteriors', 'follow', 'geo_union', 'geocutout', 'get_names',
                                  'get_sys', 'getsys', 'help', 'import_svg', 'interiors', 'isolate', 'join_excellon',
                                  'join_excellons', 'join_geometries', 'join_geometry', 'list_sys', 'listsys', 'mill',
                                  'millholes', 'mirror', 'new', 'new_geometry', 'offset', 'open_excellon', 'open_gcode',
                                  'open_gerber', 'open_project', 'options', 'paint', 'pan', 'panel', 'panelize', 'plot',
                                  'save', 'save_project', 'save_sys', 'scale', 'set_active', 'set_sys', 'setsys',
                                  'skew', 'subtract_poly', 'subtract_rectangle', 'version', 'write_gcode'
                              ]

        self.ordinary_keywords = ['name', 'center_x', 'center_y', 'radius', 'x0', 'y0', 'x1', 'y1', 'box', 'axis',
                                  'holes','grid', 'minoffset', 'gridoffset','axisoffset', 'dia', 'dist', 'gridoffsetx',
                                  'gridoffsety', 'columns', 'rows', 'z_cut', 'z_move', 'feedrate', 'feedrate_rapid',
                                  'tooldia', 'multidepth', 'extracut', 'depthperpass', 'ppname_g', 'outname', 'margin',
                                  'gaps', 'gapsize', 'tools', 'drillz', 'travelz', 'spindlespeed', 'toolchange',
                                  'toolchangez', 'endz', 'ppname_e', 'opt_type', 'preamble', 'postamble', 'filename',
                                  'scale_factor', 'type', 'passes', 'overlap', 'combine', 'use_threads', 'x', 'y',
                                  'follow', 'all', 'spacing_columns', 'spacing_rows', 'factor', 'value', 'angle_x',
                                  'angle_y', 'gridx', 'gridy', 'True', 'False'
                             ]

        self.tcl_keywords = [
                                "abort", "absolute file name", "access", "access mode", "access point",
                                "access position", "add", "AddErrInfo", "after", "alias", "Alloc", "allocation",
                                "AllowExc", "alpha", "anonymous function", "API", "append", "AppInit", "application",
                                "application-specific initialization", "apply", "architecture", "argc", "argument",
                                "argv", "argv0", "arithmetic", "array", "assign", "AssocData", "association", "Async",
                                "asynchronous event", "asynchronous I/O", "attemptckalloc", "attemptckrealloc",
                                "attributes", "auto-exec", "auto-load", "auto-loading", "auto_execok", "auto_import",
                                "auto_load", "auto_mkindex", "auto_path", "auto_qualify", "auto_reset", "BackgdErr",
                                "background", "background error", "backslash", "backslash substitution", "base class",
                                "beta", "bgerror", "binary", "binary code", "binary data", "binary library",
                                "binary search", "bind", "blocking", "boolean", "BoolObj", "braces", "break", "buffer",
                                "buffered I/O", "buffering", "byte array", "ByteArrObj", "bytecode", "call", "callback",
                                "CallDel", "cancel", "carriage return", "case", "case conversion", "catch", "CConcat",
                                "cd", "CEncoding", "CEval", "CExit", "chan", "channel", "channel closing",
                                "channel driver", "channel registration", "channel type", "character", "child",
                                "ChnlStack", "CInterp", "ckalloc", "ckfree", "ckrealloc", "class", "classification",
                                "cleanup", "client", "clientData", "clock", "clone", "close", "CmdCmplt", "command",
                                "command substitution", "command-line arguments", "commands", "comment", "compare",
                                "compiler", "complete command", "compress", "compression", "concat", "concatenate",
                                "condition variable", "conditional", "configuration", "connection", "constructor",
                                "context", "continue", "conversion", "conversion specifier", "convert", "copy",
                                "copy files", "coroutine", "cpu architecture", "create", "CRegExp", "CrtChannel",
                                "CrtChnlHdlr", "CrtCloseHdlr", "CrtCommand", "CrtFileHdlr", "CrtInterp", "CrtMathFnc",
                                "CrtObjCmd", "CrtSlave", "CrtTimerHdlr", "CrtTrace", "ctype", "CUpVar",
                                "current directory", "data", "date", "dde", "debug", "decompress", "defer", "define",
                                "definition", "deflate", "delay", "delete", "delete files", "deletion procedure",
                                "detach", "DetachPids", "dict", "dict value", "dictionary", "dictionary value",
                                "DictObj", "directory", "domain name", "DoOneEvent", "double", "double type",
                                "double value", "double-precision", "DoubleObj", "DoWhenIdle", "DString",
                                "DumpActiveMemory", "duplication", "dynamic library", "dynamic loading",
                                "dynamic string", "element", "element names", "else", "embedding", "encoding",
                                "end application", "end of file", "end of line", "ensemble", "env", "environment",
                                "eof", "equal", "errno", "error", "error code", "error message", "error messages",
                                "errorCode", "errorInfo", "eval", "evaluate", "event", "event handler", "event queue",
                                "event sources", "events", "exception", "exec", "executable file", "execute", "exist",
                                "exit", "exported", "exposed commands", "expr", "expression", "ExprLong", "ExprLongObj",
                                "fatal", "fblocked", "fconfigure", "fcopy", "file", "file events", "file handle",
                                "file name", "fileevent", "filename", "FileSystem", "filter", "final", "FindExec",
                                "floating-point", "flush", "flushing", "for", "foreach", "format", "frame", "free",
                                "fuzzy comparison", "generator", "get variable", "GetCwd", "GetHostName", "GetIndex",
                                "GetInt", "GetOpnFl", "gets", "GetStdChan", "GetTime", "GetVersion", "glob", "global",
                                "global variables", "gzip", "half-close", "handler", "Hash", "hash table",
                                "hidden commands", "history", "home directory", "host", "hostname", "http", "i18n",
                                "idle", "idle callback", "if", "incr", "increment", "index", "inflate", "info",
                                "information", "Init", "initialization", "initialization procedure", "initialized",
                                "InitStubs", "input", "insert", "integer", "integer type", "integer value", "internal",
                                "internal representation", "internationalization", "internet", "interp", "interpreter",
                                "IntObj", "introspection", "invoke", "iterate", "iteration", "join", "key", "l10n",
                                "lambda", "lappend", "lassign", "length", "level", "library", "Limit", "lindex", "line",
                                "linear search", "linemode", "link", "linked variable", "LinkVar", "linsert", "list",
                                "list type", "list value", "ListObj", "llength", "load", "localization", "lookup",
                                "loop", "lrange", "lrepeat", "lreplace", "lreverse", "lsearch", "lset", "lsort",
                                "main program", "major", "malloc", "map", "master", "master interpreter", "match",
                                "mathematical function", "mathfunc", "mathop", "memory", "merge", "message",
                                "metaclass", "method", "method chain", "method visibility", "minor", "modules",
                                "move files", "msgcat", "multiple", "mutex", "my", "name", "namespace", "nesting depth",
                                "network address", "newline", "next", "nextto", "non-blocking", "non-existent command",
                                "nonblocking", "nonblocking.", "nonrecursive", "Notifier", "NRE", "object",
                                "ObjectType", "offset", "oo::class", "oo::copy", "oo::define", "oo::objdefine",
                                "oo::object", "open", "OpenFileChnl", "OpenTcp", "operating system", "operator",
                                "option", "order", "output", "package", "packagens", "Panic", "parray", "parse",
                                "ParseArgs", "ParseCmd", "parsing", "partial command", "patchlevel", "path", "pattern",
                                "permissions", "pid", "pipeline", "pkg::create", "pkg_mkIndex", "pkgMkIndex",
                                "PkgRequire", "platform", "platform::shell", "platform_shell", "portability", "POSIX",
                                "precision", "prefix", "present", "Preserve", "PrintDbl", "private method", "proc",
                                "procedure", "process", "process identifier", "prompt", "provide", "public method",
                                "puts", "pwd", "quoting", "range", "rc file", "re_sorry", "re_syntax", "read",
                                "read-only", "readable", "real", "realloc", "RecEvalObj", "record", "RecordEval",
                                "recursion", "redirection", "refchan", "reference count", "reference counting",
                                "reflection", "RegConfig", "regexp", "registry", "regsub", "regular expression",
                                "relative file name", "release", "remote execution", "remove", "rename", "rename files",
                                "replace", "reporting", "require", "resource", "resource management", "result",
                                "return", "return value", "reverse", "root class", "safe", "safe interpreter",
                                "safe interpreter", "SaveResult", "scalar", "scan", "script", "script file", "search",
                                "security policy", "seek", "seeking", "self", "separator", "serial", "server",
                                "service mode", "set", "SetChanErr", "SetErrno", "SetRecLmt", "SetResult", "SetVar",
                                "shared library", "shell", "signal", "signal numbers", "signals", "slave",
                                "slave interpreter", "sleep", "slot", "socket", "sort", "source", "SourceRCFile",
                                "split", "SplitList", "SplitPath", "splitting", "sprintf", "stack", "stack frame",
                                "stackless", "standard channel", "standard channels", "standard error",
                                "standard input", "standard output", "stat", "state", "static linking", "StaticPkg",
                                "StdChannels", "storage", "string", "string representation", "string type",
                                "string value", "StringObj", "strings", "StrMatch", "stubs", "subexpression", "sublist",
                                "subprocess", "subst", "substitution", "SubstObj", "switch", "table lookup",
                                "tail recursion", "tailcall", "Tcl", "tcl::prefix", "Tcl_Access", "Tcl_AddErrorInfo",
                                "Tcl_AddObjErrorInfo", "Tcl_AlertNotifier", "Tcl_Alloc", "Tcl_AllocHashEntryProc",
                                "Tcl_AllocStatBuf", "Tcl_AllowExceptions", "Tcl_AppendAllObjTypes", "Tcl_AppendElement",
                                "Tcl_AppendExportList", "Tcl_AppendFormatToObj", "Tcl_AppendLimitedToObj",
                                "Tcl_AppendObjToErrorInfo", "Tcl_AppendObjToObj", "Tcl_AppendPrintfToObj",
                                "Tcl_AppendResult", "Tcl_AppendResultVA", "Tcl_AppendStringsToObj",
                                "Tcl_AppendStringsToObjVA", "Tcl_AppendToObj", "Tcl_AppendUnicodeToObj", "Tcl_AppInit",
                                "Tcl_AppInitProc", "Tcl_ArgvInfo", "Tcl_AsyncCreate", "Tcl_AsyncDelete",
                                "Tcl_AsyncInvoke", "Tcl_AsyncMark", "Tcl_AsyncProc", "Tcl_AsyncReady",
                                "Tcl_AttemptAlloc", "Tcl_AttemptRealloc", "Tcl_AttemptSetObjLength",
                                "Tcl_BackgroundError", "Tcl_BackgroundException", "Tcl_Backslash",
                                "Tcl_BadChannelOption", "Tcl_CallWhenDeleted", "Tcl_Canceled", "Tcl_CancelEval",
                                "Tcl_CancelIdleCall", "Tcl_ChannelBlockModeProc", "Tcl_ChannelBuffered",
                                "Tcl_ChannelClose2Proc", "Tcl_ChannelCloseProc", "Tcl_ChannelFlushProc",
                                "Tcl_ChannelGetHandleProc", "Tcl_ChannelGetOptionProc", "Tcl_ChannelHandlerProc",
                                "Tcl_ChannelInputProc", "Tcl_ChannelName", "Tcl_ChannelOutputProc", "Tcl_ChannelProc",
                                "Tcl_ChannelSeekProc", "Tcl_ChannelSetOptionProc", "Tcl_ChannelThreadActionProc",
                                "Tcl_ChannelTruncateProc", "Tcl_ChannelType", "Tcl_ChannelVersion",
                                "Tcl_ChannelWatchProc", "Tcl_ChannelWideSeekProc", "Tcl_Chdir", "Tcl_ClassGetMetadata",
                                "Tcl_ClassSetConstructor", "Tcl_ClassSetDestructor", "Tcl_ClassSetMetadata",
                                "Tcl_ClearChannelHandlers", "Tcl_CloneProc", "Tcl_Close", "Tcl_CloseProc",
                                "Tcl_CmdDeleteProc", "Tcl_CmdInfo", "Tcl_CmdObjTraceDeleteProc", "Tcl_CmdObjTraceProc",
                                "Tcl_CmdProc", "Tcl_CmdTraceProc", "Tcl_CommandComplete", "Tcl_CommandTraceInfo",
                                "Tcl_CommandTraceProc", "Tcl_CompareHashKeysProc", "Tcl_Concat", "Tcl_ConcatObj",
                                "Tcl_ConditionFinalize", "Tcl_ConditionNotify", "Tcl_ConditionWait", "Tcl_Config",
                                "Tcl_ConvertCountedElement", "Tcl_ConvertElement", "Tcl_ConvertToType",
                                "Tcl_CopyObjectInstance", "Tcl_CreateAlias", "Tcl_CreateAliasObj", "Tcl_CreateChannel",
                                "Tcl_CreateChannelHandler", "Tcl_CreateCloseHandler", "Tcl_CreateCommand",
                                "Tcl_CreateEncoding", "Tcl_CreateEnsemble", "Tcl_CreateEventSource",
                                "Tcl_CreateExitHandler", "Tcl_CreateFileHandler", "Tcl_CreateHashEntry",
                                "Tcl_CreateInterp", "Tcl_CreateMathFunc", "Tcl_CreateNamespace", "Tcl_CreateObjCommand",
                                "Tcl_CreateObjTrace", "Tcl_CreateSlave", "Tcl_CreateThread",
                                "Tcl_CreateThreadExitHandler", "Tcl_CreateTimerHandler", "Tcl_CreateTrace",
                                "Tcl_CutChannel", "Tcl_DecrRefCount", "Tcl_DeleteAssocData", "Tcl_DeleteChannelHandler",
                                "Tcl_DeleteCloseHandler", "Tcl_DeleteCommand", "Tcl_DeleteCommandFromToken",
                                "Tcl_DeleteEvents", "Tcl_DeleteEventSource", "Tcl_DeleteExitHandler",
                                "Tcl_DeleteFileHandler", "Tcl_DeleteHashEntry", "Tcl_DeleteHashTable",
                                "Tcl_DeleteInterp", "Tcl_DeleteNamespace", "Tcl_DeleteThreadExitHandler",
                                "Tcl_DeleteTimerHandler", "Tcl_DeleteTrace", "Tcl_DetachChannel", "Tcl_DetachPids",
                                "Tcl_DictObjDone", "Tcl_DictObjFirst", "Tcl_DictObjGet", "Tcl_DictObjNext",
                                "Tcl_DictObjPut", "Tcl_DictObjPutKeyList", "Tcl_DictObjRemove",
                                "Tcl_DictObjRemoveKeyList", "Tcl_DictObjSize", "Tcl_DiscardInterpState",
                                "Tcl_DiscardResult", "Tcl_DontCallWhenDeleted", "Tcl_DoOneEvent", "Tcl_DoWhenIdle",
                                "Tcl_DriverBlockModeProc", "Tcl_DriverClose2Proc", "Tcl_DriverCloseProc",
                                "Tcl_DriverFlushProc", "Tcl_DriverGetHandleProc", "Tcl_DriverGetOptionProc",
                                "Tcl_DriverHandlerProc", "Tcl_DriverInputProc", "Tcl_DriverOutputProc",
                                "Tcl_DriverSeekProc", "Tcl_DriverSetOptionProc", "Tcl_DriverThreadActionProc",
                                "Tcl_DriverTruncateProc", "Tcl_DriverWatchProc", "Tcl_DriverWideSeekProc",
                                "Tcl_DStringAppend", "Tcl_DStringAppendElement", "Tcl_DStringEndSublist",
                                "Tcl_DStringFree", "Tcl_DStringGetResult", "Tcl_DStringInit", "Tcl_DStringLength",
                                "Tcl_DStringResult", "Tcl_DStringSetLength", "Tcl_DStringStartSublist",
                                "Tcl_DStringTrunc", "Tcl_DStringValue", "Tcl_DumpActiveMemory",
                                "Tcl_DupInternalRepProc", "Tcl_DuplicateObj", "Tcl_EncodingConvertProc",
                                "Tcl_EncodingFreeProc", "Tcl_EncodingType", "tcl_endOfWord", "Tcl_Eof", "Tcl_ErrnoId",
                                "Tcl_ErrnoMsg", "Tcl_Eval", "Tcl_EvalEx", "Tcl_EvalFile", "Tcl_EvalObjEx",
                                "Tcl_EvalObjv", "Tcl_EvalTokens", "Tcl_EvalTokensStandard", "Tcl_Event",
                                "Tcl_EventCheckProc", "Tcl_EventDeleteProc", "Tcl_EventProc", "Tcl_EventSetupProc",
                                "Tcl_EventuallyFree", "Tcl_Exit", "Tcl_ExitProc", "Tcl_ExitThread", "Tcl_Export",
                                "Tcl_ExposeCommand", "Tcl_ExprBoolean", "Tcl_ExprBooleanObj", "Tcl_ExprDouble",
                                "Tcl_ExprDoubleObj", "Tcl_ExprLong", "Tcl_ExprLongObj", "Tcl_ExprObj", "Tcl_ExprString",
                                "Tcl_ExternalToUtf", "Tcl_ExternalToUtfDString", "Tcl_FileProc", "Tcl_Filesystem",
                                "Tcl_Finalize", "Tcl_FinalizeNotifier", "Tcl_FinalizeThread", "Tcl_FindCommand",
                                "Tcl_FindEnsemble", "Tcl_FindExecutable", "Tcl_FindHashEntry", "tcl_findLibrary",
                                "Tcl_FindNamespace", "Tcl_FirstHashEntry", "Tcl_Flush", "Tcl_ForgetImport",
                                "Tcl_Format", "Tcl_Free", "Tcl_FreeEncoding", "Tcl_FreeHashEntryProc",
                                "Tcl_FreeInternalRepProc", "Tcl_FreeParse", "Tcl_FreeProc", "Tcl_FreeResult",
                                "Tcl_FSAccess", "Tcl_FSAccessProc", "Tcl_FSChdir", "Tcl_FSChdirProc",
                                "Tcl_FSConvertToPathType", "Tcl_FSCopyDirectory", "Tcl_FSCopyDirectoryProc",
                                "Tcl_FSCopyFile", "Tcl_FSCopyFileProc", "Tcl_FSCreateDirectory",
                                "Tcl_FSCreateDirectoryProc", "Tcl_FSCreateInternalRepProc", "Tcl_FSData",
                                "Tcl_FSDeleteFile", "Tcl_FSDeleteFileProc", "Tcl_FSDupInternalRepProc",
                                "Tcl_FSEqualPaths", "Tcl_FSEvalFile", "Tcl_FSEvalFileEx", "Tcl_FSFileAttrsGet",
                                "Tcl_FSFileAttrsGetProc", "Tcl_FSFileAttrsSet", "Tcl_FSFileAttrsSetProc",
                                "Tcl_FSFileAttrStrings", "Tcl_FSFileSystemInfo", "Tcl_FSFilesystemPathTypeProc",
                                "Tcl_FSFilesystemSeparatorProc", "Tcl_FSFreeInternalRepProc", "Tcl_FSGetCwd",
                                "Tcl_FSGetCwdProc", "Tcl_FSGetFileSystemForPath", "Tcl_FSGetInternalRep",
                                "Tcl_FSGetNativePath", "Tcl_FSGetNormalizedPath", "Tcl_FSGetPathType",
                                "Tcl_FSGetTranslatedPath", "Tcl_FSGetTranslatedStringPath",
                                "Tcl_FSInternalToNormalizedProc", "Tcl_FSJoinPath", "Tcl_FSJoinToPath", "Tcl_FSLink",
                                "Tcl_FSLinkProc", "Tcl_FSListVolumes", "Tcl_FSListVolumesProc", "Tcl_FSLoadFile",
                                "Tcl_FSLoadFileProc", "Tcl_FSLstat", "Tcl_FSLstatProc", "Tcl_FSMatchInDirectory",
                                "Tcl_FSMatchInDirectoryProc", "Tcl_FSMountsChanged", "Tcl_FSNewNativePath",
                                "Tcl_FSNormalizePathProc", "Tcl_FSOpenFileChannel", "Tcl_FSOpenFileChannelProc",
                                "Tcl_FSPathInFilesystemProc", "Tcl_FSPathSeparator", "Tcl_FSRegister",
                                "Tcl_FSRemoveDirectory", "Tcl_FSRemoveDirectoryProc", "Tcl_FSRenameFile",
                                "Tcl_FSRenameFileProc", "Tcl_FSSplitPath", "Tcl_FSStat", "Tcl_FSStatProc",
                                "Tcl_FSUnloadFile", "Tcl_FSUnloadFileProc", "Tcl_FSUnregister", "Tcl_FSUtime",
                                "Tcl_FSUtimeProc", "Tcl_GetAccessTimeFromStat", "Tcl_GetAlias", "Tcl_GetAliasObj",
                                "Tcl_GetAssocData", "Tcl_GetBignumFromObj", "Tcl_GetBlocksFromStat",
                                "Tcl_GetBlockSizeFromStat", "Tcl_GetBoolean", "Tcl_GetBooleanFromObj",
                                "Tcl_GetByteArrayFromObj", "Tcl_GetChangeTimeFromStat", "Tcl_GetChannel",
                                "Tcl_GetChannelBufferSize", "Tcl_GetChannelError", "Tcl_GetChannelErrorInterp",
                                "Tcl_GetChannelHandle", "Tcl_GetChannelInstanceData", "Tcl_GetChannelMode",
                                "Tcl_GetChannelName", "Tcl_GetChannelNames", "Tcl_GetChannelNamesEx",
                                "Tcl_GetChannelOption", "Tcl_GetChannelThread", "Tcl_GetChannelType",
                                "Tcl_GetCharLength", "Tcl_GetClassAsObject", "Tcl_GetCommandFromObj",
                                "Tcl_GetCommandFullName", "Tcl_GetCommandInfo", "Tcl_GetCommandInfoFromToken",
                                "Tcl_GetCommandName", "Tcl_GetCurrentNamespace", "Tcl_GetCurrentThread", "Tcl_GetCwd",
                                "Tcl_GetDefaultEncodingDir", "Tcl_GetDeviceTypeFromStat", "Tcl_GetDouble",
                                "Tcl_GetDoubleFromObj", "Tcl_GetEncoding", "Tcl_GetEncodingFromObj",
                                "Tcl_GetEncodingName", "Tcl_GetEncodingNameFromEnvironment", "Tcl_GetEncodingNames",
                                "Tcl_GetEncodingSearchPath", "Tcl_GetEnsembleFlags", "Tcl_GetEnsembleMappingDict",
                                "Tcl_GetEnsembleNamespace", "Tcl_GetEnsembleParameterList",
                                "Tcl_GetEnsembleSubcommandList", "Tcl_GetEnsembleUnknownHandler", "Tcl_GetErrno",
                                "Tcl_GetErrorLine", "Tcl_GetFSDeviceFromStat", "Tcl_GetFSInodeFromStat",
                                "Tcl_GetGlobalNamespace", "Tcl_GetGroupIdFromStat", "Tcl_GetHashKey",
                                "Tcl_GetHashValue", "Tcl_GetHostName", "Tcl_GetIndexFromObj",
                                "Tcl_GetIndexFromObjStruct", "Tcl_GetInt", "Tcl_GetInterpPath", "Tcl_GetIntFromObj",
                                "Tcl_GetLinkCountFromStat", "Tcl_GetLongFromObj", "Tcl_GetMaster",
                                "Tcl_GetMathFuncInfo", "Tcl_GetModeFromStat", "Tcl_GetModificationTimeFromStat",
                                "Tcl_GetNameOfExecutable", "Tcl_GetNamespaceUnknownHandler", "Tcl_GetObjectAsClass",
                                "Tcl_GetObjectCommand", "Tcl_GetObjectFromObj", "Tcl_GetObjectName",
                                "Tcl_GetObjectNamespace", "Tcl_GetObjResult", "Tcl_GetObjType", "Tcl_GetOpenFile",
                                "Tcl_GetPathType", "Tcl_GetRange", "Tcl_GetRegExpFromObj", "Tcl_GetReturnOptions",
                                "Tcl_Gets", "Tcl_GetServiceMode", "Tcl_GetSizeFromStat", "Tcl_GetSlave", "Tcl_GetsObj",
                                "Tcl_GetStackedChannel", "Tcl_GetStartupScript", "Tcl_GetStdChannel", "Tcl_GetString",
                                "Tcl_GetStringFromObj", "Tcl_GetStringResult", "Tcl_GetThreadData", "Tcl_GetTime",
                                "Tcl_GetTopChannel", "Tcl_GetUniChar", "Tcl_GetUnicode", "Tcl_GetUnicodeFromObj",
                                "Tcl_GetUserIdFromStat", "Tcl_GetVar", "Tcl_GetVar2", "Tcl_GetVar2Ex", "Tcl_GetVersion",
                                "Tcl_GetWideIntFromObj", "Tcl_GlobalEval", "Tcl_GlobalEvalObj", "Tcl_GlobTypeData",
                                "Tcl_HashKeyType", "Tcl_HashStats", "Tcl_HideCommand", "Tcl_IdleProc", "Tcl_Import",
                                "Tcl_IncrRefCount", "Tcl_Init", "Tcl_InitCustomHashTable", "Tcl_InitHashTable",
                                "Tcl_InitMemory", "Tcl_InitNotifier", "Tcl_InitObjHashTable", "Tcl_InitStubs",
                                "Tcl_InputBlocked", "Tcl_InputBuffered", "tcl_interactive", "Tcl_Interp",
                                "Tcl_InterpActive", "Tcl_InterpDeleted", "Tcl_InterpDeleteProc",
                                "Tcl_InvalidateStringRep", "Tcl_IsChannelExisting", "Tcl_IsChannelRegistered",
                                "Tcl_IsChannelShared", "Tcl_IsEnsemble", "Tcl_IsSafe", "Tcl_IsShared",
                                "Tcl_IsStandardChannel", "Tcl_JoinPath", "Tcl_JoinThread", "tcl_library",
                                "Tcl_LimitAddHandler", "Tcl_LimitCheck", "Tcl_LimitExceeded", "Tcl_LimitGetCommands",
                                "Tcl_LimitGetGranularity", "Tcl_LimitGetTime", "Tcl_LimitHandlerDeleteProc",
                                "Tcl_LimitHandlerProc", "Tcl_LimitReady", "Tcl_LimitRemoveHandler",
                                "Tcl_LimitSetCommands", "Tcl_LimitSetGranularity", "Tcl_LimitSetTime",
                                "Tcl_LimitTypeEnabled", "Tcl_LimitTypeExceeded", "Tcl_LimitTypeReset",
                                "Tcl_LimitTypeSet", "Tcl_LinkVar", "Tcl_ListMathFuncs", "Tcl_ListObjAppendElement",
                                "Tcl_ListObjAppendList", "Tcl_ListObjGetElements", "Tcl_ListObjIndex",
                                "Tcl_ListObjLength", "Tcl_ListObjReplace", "Tcl_LogCommandInfo", "Tcl_Main",
                                "Tcl_MainLoopProc", "Tcl_MakeFileChannel", "Tcl_MakeSafe", "Tcl_MakeTcpClientChannel",
                                "Tcl_MathProc", "TCL_MEM_DEBUG", "Tcl_Merge", "Tcl_MethodCallProc",
                                "Tcl_MethodDeclarerClass", "Tcl_MethodDeclarerObject", "Tcl_MethodDeleteProc",
                                "Tcl_MethodIsPublic", "Tcl_MethodIsType", "Tcl_MethodName", "Tcl_MethodType",
                                "Tcl_MutexFinalize", "Tcl_MutexLock", "Tcl_MutexUnlock", "Tcl_NamespaceDeleteProc",
                                "Tcl_NewBignumObj", "Tcl_NewBooleanObj", "Tcl_NewByteArrayObj", "Tcl_NewDictObj",
                                "Tcl_NewDoubleObj", "Tcl_NewInstanceMethod", "Tcl_NewIntObj", "Tcl_NewListObj",
                                "Tcl_NewLongObj", "Tcl_NewMethod", "Tcl_NewObj", "Tcl_NewObjectInstance",
                                "Tcl_NewStringObj", "Tcl_NewUnicodeObj", "Tcl_NewWideIntObj", "Tcl_NextHashEntry",
                                "tcl_nonwordchars", "Tcl_NotifierProcs", "Tcl_NotifyChannel", "Tcl_NRAddCallback",
                                "Tcl_NRCallObjProc", "Tcl_NRCmdSwap", "Tcl_NRCreateCommand", "Tcl_NREvalObj",
                                "Tcl_NREvalObjv", "Tcl_NumUtfChars", "Tcl_Obj", "Tcl_ObjCmdProc",
                                "Tcl_ObjectContextInvokeNext", "Tcl_ObjectContextIsFiltering",
                                "Tcl_ObjectContextMethod", "Tcl_ObjectContextObject", "Tcl_ObjectContextSkippedArgs",
                                "Tcl_ObjectDeleted", "Tcl_ObjectGetMetadata", "Tcl_ObjectGetMethodNameMapper",
                                "Tcl_ObjectMapMethodNameProc", "Tcl_ObjectMetadataDeleteProc", "Tcl_ObjectSetMetadata",
                                "Tcl_ObjectSetMethodNameMapper", "Tcl_ObjGetVar2", "Tcl_ObjPrintf", "Tcl_ObjSetVar2",
                                "Tcl_ObjType", "Tcl_OpenCommandChannel", "Tcl_OpenFileChannel", "Tcl_OpenTcpClient",
                                "Tcl_OpenTcpServer", "Tcl_OutputBuffered", "Tcl_PackageInitProc",
                                "Tcl_PackageUnloadProc", "Tcl_Panic", "Tcl_PanicProc", "Tcl_PanicVA",
                                "Tcl_ParseArgsObjv", "Tcl_ParseBraces", "Tcl_ParseCommand", "Tcl_ParseExpr",
                                "Tcl_ParseQuotedString", "Tcl_ParseVar", "Tcl_ParseVarName", "tcl_patchLevel",
                                "tcl_pkgPath", "Tcl_PkgPresent", "Tcl_PkgPresentEx", "Tcl_PkgProvide",
                                "Tcl_PkgProvideEx", "Tcl_PkgRequire", "Tcl_PkgRequireEx", "Tcl_PkgRequireProc",
                                "tcl_platform", "Tcl_PosixError", "tcl_precision", "Tcl_Preserve", "Tcl_PrintDouble",
                                "Tcl_PutEnv", "Tcl_QueryTimeProc", "Tcl_QueueEvent", "tcl_rcFileName", "Tcl_Read",
                                "Tcl_ReadChars", "Tcl_ReadRaw", "Tcl_Realloc", "Tcl_ReapDetachedProcs",
                                "Tcl_RecordAndEval", "Tcl_RecordAndEvalObj", "Tcl_RegExpCompile", "Tcl_RegExpExec",
                                "Tcl_RegExpExecObj", "Tcl_RegExpGetInfo", "Tcl_RegExpIndices", "Tcl_RegExpInfo",
                                "Tcl_RegExpMatch", "Tcl_RegExpMatchObj", "Tcl_RegExpRange", "Tcl_RegisterChannel",
                                "Tcl_RegisterConfig", "Tcl_RegisterObjType", "Tcl_Release", "Tcl_ResetResult",
                                "Tcl_RestoreInterpState", "Tcl_RestoreResult", "Tcl_SaveInterpState", "Tcl_SaveResult",
                                "Tcl_ScaleTimeProc", "Tcl_ScanCountedElement", "Tcl_ScanElement", "Tcl_Seek",
                                "Tcl_ServiceAll", "Tcl_ServiceEvent", "Tcl_ServiceModeHook", "Tcl_SetAssocData",
                                "Tcl_SetBignumObj", "Tcl_SetBooleanObj", "Tcl_SetByteArrayLength",
                                "Tcl_SetByteArrayObj", "Tcl_SetChannelBufferSize", "Tcl_SetChannelError",
                                "Tcl_SetChannelErrorInterp", "Tcl_SetChannelOption", "Tcl_SetCommandInfo",
                                "Tcl_SetCommandInfoFromToken", "Tcl_SetDefaultEncodingDir", "Tcl_SetDoubleObj",
                                "Tcl_SetEncodingSearchPath", "Tcl_SetEnsembleFlags", "Tcl_SetEnsembleMappingDict",
                                "Tcl_SetEnsembleParameterList", "Tcl_SetEnsembleSubcommandList",
                                "Tcl_SetEnsembleUnknownHandler", "Tcl_SetErrno", "Tcl_SetErrorCode",
                                "Tcl_SetErrorCodeVA", "Tcl_SetErrorLine", "Tcl_SetExitProc", "Tcl_SetFromAnyProc",
                                "Tcl_SetHashValue", "Tcl_SetIntObj", "Tcl_SetListObj", "Tcl_SetLongObj",
                                "Tcl_SetMainLoop", "Tcl_SetMaxBlockTime", "Tcl_SetNamespaceUnknownHandler",
                                "Tcl_SetNotifier", "Tcl_SetObjErrorCode", "Tcl_SetObjLength", "Tcl_SetObjResult",
                                "Tcl_SetPanicProc", "Tcl_SetRecursionLimit", "Tcl_SetResult", "Tcl_SetReturnOptions",
                                "Tcl_SetServiceMode", "Tcl_SetStartupScript", "Tcl_SetStdChannel", "Tcl_SetStringObj",
                                "Tcl_SetSystemEncoding", "Tcl_SetTimeProc", "Tcl_SetTimer", "Tcl_SetUnicodeObj",
                                "Tcl_SetVar", "Tcl_SetVar2", "Tcl_SetVar2Ex", "Tcl_SetWideIntObj", "Tcl_SignalId",
                                "Tcl_SignalMsg", "Tcl_Sleep", "Tcl_SourceRCFile", "Tcl_SpliceChannel", "Tcl_SplitList",
                                "Tcl_SplitPath", "Tcl_StackChannel", "Tcl_StandardChannels", "tcl_startOfNextWord",
                                "tcl_startOfPreviousWord", "Tcl_Stat", "Tcl_StaticPackage", "Tcl_StringCaseMatch",
                                "Tcl_StringMatch", "Tcl_SubstObj", "Tcl_TakeBignumFromObj", "Tcl_TcpAcceptProc",
                                "Tcl_Tell", "Tcl_ThreadAlert", "Tcl_ThreadQueueEvent", "Tcl_Time", "Tcl_TimerProc",
                                "Tcl_Token", "Tcl_TraceCommand", "tcl_traceCompile", "tcl_traceEval", "tcl_traceExec",
                                "Tcl_TraceVar", "Tcl_TraceVar2", "Tcl_TransferResult", "Tcl_TranslateFileName",
                                "Tcl_TruncateChannel", "Tcl_Ungets", "Tcl_UniChar", "Tcl_UniCharAtIndex",
                                "Tcl_UniCharCaseMatch", "Tcl_UniCharIsAlnum", "Tcl_UniCharIsAlpha",
                                "Tcl_UniCharIsControl", "Tcl_UniCharIsDigit", "Tcl_UniCharIsGraph",
                                "Tcl_UniCharIsLower", "Tcl_UniCharIsPrint", "Tcl_UniCharIsPunct", "Tcl_UniCharIsSpace",
                                "Tcl_UniCharIsUpper", "Tcl_UniCharIsWordChar", "Tcl_UniCharLen", "Tcl_UniCharNcasecmp",
                                "Tcl_UniCharNcmp", "Tcl_UniCharToLower", "Tcl_UniCharToTitle", "Tcl_UniCharToUpper",
                                "Tcl_UniCharToUtf", "Tcl_UniCharToUtfDString", "Tcl_UnlinkVar", "Tcl_UnregisterChannel",
                                "Tcl_UnsetVar", "Tcl_UnsetVar2", "Tcl_UnstackChannel", "Tcl_UntraceCommand",
                                "Tcl_UntraceVar", "Tcl_UntraceVar2", "Tcl_UpdateLinkedVar", "Tcl_UpdateStringProc",
                                "Tcl_UpVar", "Tcl_UpVar2", "Tcl_UtfAtIndex", "Tcl_UtfBackslash", "Tcl_UtfCharComplete",
                                "Tcl_UtfFindFirst", "Tcl_UtfFindLast", "Tcl_UtfNext", "Tcl_UtfPrev",
                                "Tcl_UtfToExternal", "Tcl_UtfToExternalDString", "Tcl_UtfToLower", "Tcl_UtfToTitle",
                                "Tcl_UtfToUniChar", "Tcl_UtfToUniCharDString", "Tcl_UtfToUpper",
                                "Tcl_ValidateAllMemory", "Tcl_Value", "Tcl_VarEval", "Tcl_VarEvalVA",
                                "Tcl_VarTraceInfo", "Tcl_VarTraceInfo2", "Tcl_VarTraceProc", "tcl_version",
                                "Tcl_WaitForEvent", "Tcl_WaitPid", "Tcl_WinTCharToUtf", "Tcl_WinUtfToTChar",
                                "tcl_wordBreakAfter", "tcl_wordBreakBefore", "tcl_wordchars", "Tcl_Write",
                                "Tcl_WriteChars", "Tcl_WriteObj", "Tcl_WriteRaw", "Tcl_WrongNumArgs", "Tcl_ZlibAdler32",
                                "Tcl_ZlibCRC32", "Tcl_ZlibDeflate", "Tcl_ZlibInflate", "Tcl_ZlibStreamChecksum",
                                "Tcl_ZlibStreamClose", "Tcl_ZlibStreamEof", "Tcl_ZlibStreamGet",
                                "Tcl_ZlibStreamGetCommandName", "Tcl_ZlibStreamInit", "Tcl_ZlibStreamPut", "tclsh",
                                "tcltest", "tclvars", "TclZlib", "tcp", "tell", "test", "test harness", "test suite",
                                "text", "thread", "thread local storage", "threads", "throw", "tilde", "time", "timer",
                                "tm", "token", "tolower", "totitle", "ToUpper", "trace", "TraceCmd", "TraceVar",
                                "transchan", "transformation", "Translate", "translation", "try", "type",
                                "type conversion", "UniCharIsAlpha", "unicode", "unknown", "unload", "unloading",
                                "unset", "unwind", "update", "uplevel", "upvar", "user", "utf", "value",
                                "value creation", "value result", "value type", "variable", "variable substitution",
                                "variables", "version", "vfs", "virtual filesystem", "volume-relative file name",
                                "vwait", "wait", "while", "whitespace", "word", "working directory", "writable.",
                                "write", "wrong number of arguments", "WrongNumArgs", "www", "yield", "yieldto",
                                "zlib"
        ]

        self.myKeywords = self.tcl_commands_list + self.ordinary_keywords + self.tcl_keywords

        self.shell = FCShell(self, version=self.version)
        self.shell._edit.set_model_data(self.myKeywords)
        self.ui.code_editor.set_model_data(self.myKeywords)
        self.shell.setWindowIcon(self.ui.app_icon)
        self.shell.setWindowTitle("FlatCAM Shell")
        self.shell.resize(*self.defaults["global_shell_shape"])
        self.shell.append_output("FlatCAM %s (c)2014-2019 Juan Pablo Caram " % self.version)
        self.shell.append_output("(Type help to get started)\n\n")

        self.init_tcl()

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

        #########################
        ### Tools and Plugins ###
        #########################

        # always install tools only after the shell is initialized because the self.inform.emit() depends on shell
        self.install_tools()

        ### System Font Parsing ###
        # self.f_parse = ParseFont(self)
        # self.parse_system_fonts()

        # test if the program was started with a script as parameter
        if self.cmd_line_shellfile:
            try:
                with open(self.cmd_line_shellfile, "r") as myfile:
                    cmd_line_shellfile_text = myfile.read()
                    self.shell._sysShell.exec_command(cmd_line_shellfile_text)
            except Exception as ext:
                print("ERROR: ", ext)
                sys.exit(2)

        ###########################
        #### Check for updates ####
        ###########################

        # Separate thread (Not worker)
        # Check for updates on startup but only if the user consent and the app is not in Beta version
        if (self.beta is False or self.beta is None) and \
                self.ui.general_defaults_form.general_gui_group.version_check_cb.get_value() is True:
            App.log.info("Checking for updates in backgroud (this is version %s)." % str(self.version))

            self.thr2 = QtCore.QThread()
            self.worker_task.emit({'fcn': self.version_check,
                                   'params': []})
            self.thr2.start()


        ####################################
        #### Variables for global usage ####
        ####################################

        # coordinates for relative position display
        self.rel_point1 = (0, 0)
        self.rel_point2 = (0, 0)

        # variable to store coordinates
        self.pos = (0, 0)
        self.pos_jump = (0, 0)

        # decide if we have a double click or single click
        self.doubleclick = False

        # variable to store if there was motion before right mouse button click (panning)
        self.panning_action = False
        # variable to store if a command is active (then the var is not None) and which one it is
        self.command_active = None
        # variable to store the status of moving selection action
        # None value means that it's not an selection action
        # True value = a selection from left to right
        # False value = a selection from right to left
        self.selection_type = None

        # List to store the objects that are currently loaded in FlatCAM
        # This list is updated on each object creation or object delete
        self.all_objects_list = []

        # List to store the objects that are selected
        self.sel_objects_list = []

        # holds the key modifier if pressed (CTRL, SHIFT or ALT)
        self.key_modifiers = None

        # Variable to hold the status of the axis
        self.toggle_axis = True

        # Variable to store the status of the fullscreen event
        self.toggle_fscreen = False

        # Variable to store the status of the code editor
        self.toggle_codeeditor = False

        # Variable to be used for situations when we don't want the LMB click on canvas to auto open the Project Tab
        self.click_noproject = False

        self.cursor = None

        # Variable to store the GCODE that was edited
        self.gcode_edited = ""

        self.grb_list = ['gbr', 'ger', 'gtl', 'gbl', 'gts', 'gbs', 'gtp', 'gbp', 'gto', 'gbo', 'gm1', 'gm2', 'gm3', 'gko',
                    'cmp', 'sol', 'stc', 'sts', 'plc', 'pls', 'crc', 'crs', 'tsm', 'bsm', 'ly2', 'ly15', 'dim', 'mil',
                    'grb', 'top', 'bot', 'smt', 'smb', 'sst', 'ssb', 'spt', 'spb', 'pho', 'gdo', 'art', 'gbd']
        self.exc_list = ['drl', 'txt', 'xln', 'drd', 'tap', 'exc']
        self.gcode_list = ['nc', 'ncc', 'tap', 'gcode', 'cnc', 'ecs', 'fnc', 'dnc', 'ncg', 'gc', 'fan', 'fgc', 'din',
                      'xpi', 'hnc', 'h', 'i', 'ncp', 'min', 'gcd', 'rol', 'mpr', 'ply', 'out', 'eia', 'plt', 'sbp',
                      'mpf']
        self.svg_list = ['svg']
        self.dxf_list = ['dxf']
        self.prj_list = ['flatprj']

        # global variable used by NCC Tool to signal that some polygons could not be cleared, if True
        # flag for polygons not cleared
        self.poly_not_cleared = False

        # VisPy visuals
        self.hover_shapes = ShapeCollection(parent=self.plotcanvas.vispy_canvas.view.scene, layers=1)
        self.isHovering = False
        self.notHovering = True

        ### Save defaults to factory_defaults.FlatConfig file ###
        ### It's done only once after install #############
        factory_file = open(self.data_path + '/factory_defaults.FlatConfig')
        fac_def_from_file = factory_file.read()
        factory_defaults = json.loads(fac_def_from_file)

        # if the file contain an empty dictionary then save the factory defaults into the file
        if not factory_defaults:
            self.save_factory_defaults(silent=False)
            # ONLY AT FIRST STARTUP INIT THE GUI LAYOUT TO 'COMPACT'
            initial_lay = 'Compact'
            self.on_layout(index=None, lay=initial_lay)
            # Set the combobox in Preferences to the current layout
            idx = self.ui.general_defaults_form.general_gui_set_group.layout_combo.findText(initial_lay)
            self.ui.general_defaults_form.general_gui_set_group.layout_combo.setCurrentIndex(idx)
        factory_file.close()

        # and then make the  factory_defaults.FlatConfig file read_only os it can't be modified after creation.
        filename_factory = self.data_path + '/factory_defaults.FlatConfig'
        os.chmod(filename_factory, S_IREAD | S_IRGRP | S_IROTH)

        # Post-GUI initialization: Experimental attempt
        # to perform unit tests on the GUI.
        # if post_gui is not None:
        #     post_gui(self)

        App.log.debug("END of constructor. Releasing control.")

        # accept a project file as command line parameter
        # the path/file_name must be enclosed in quotes if it contain spaces
        for argument in App.args:
            if '.FlatPrj' in argument:
                try:
                    project_name = str(argument)

                    if project_name == "":
                        self.inform.emit(_("Open cancelled."))
                    else:
                        # self.open_project(project_name)
                        run_from_arg = True
                        self.worker_task.emit({'fcn': self.open_project,
                                               'params': [project_name, run_from_arg]})
                except Exception as e:
                    log.debug("Could not open FlatCAM project file as App parameter due: %s" % str(e))

            if '.FlatConfig' in argument:
                try:
                    file_name = str(argument)

                    if file_name == "":
                        self.inform.emit(_("Open Config file failed."))
                    else:
                        # run_from_arg = True
                        # self.worker_task.emit({'fcn': self.open_config_file,
                        #                        'params': [file_name, run_from_arg]})
                        self.open_config_file(file_name, run_from_arg=True)
                except Exception as e:
                    log.debug("Could not open FlatCAM Config file as App parameter due: %s" % str(e))

            if '.FlatScript' in argument:
                try:
                    file_name = str(argument)

                    if file_name == "":
                        self.inform.emit(_("Open Script file failed."))
                    else:
                        # run_from_arg = True
                        # self.worker_task.emit({'fcn': self.open_script_file,
                        #                        'params': [file_name, run_from_arg]})
                        self.on_filerunscript(name=file_name)
                except Exception as e:
                    log.debug("Could not open FlatCAM Script file as App parameter due: %s" % str(e))

    def defaults_read_form(self):
        for option in self.defaults_form_fields:
            try:
                self.defaults[option] = self.defaults_form_fields[option].get_value()
            except:
                pass

    def defaults_write_form(self, factor=None):
        for option in self.defaults:
            self.defaults_write_form_field(option, factor=factor)
            # try:
            #     self.defaults_form_fields[option].set_value(self.defaults[option])
            # except KeyError:
            #     #self.log.debug("defaults_write_form(): No field for: %s" % option)
            #     # TODO: Rethink this?
            #     pass

    def defaults_write_form_field(self, field, factor=None):
        try:
            if factor is None:
                self.defaults_form_fields[field].set_value(self.defaults[field])
            else:
                self.defaults_form_fields[field].set_value(self.defaults[field] * factor)

        except KeyError:
            #self.log.debug("defaults_write_form(): No field for: %s" % option)
            # TODO: Rethink this?
            pass
        except AttributeError:
            log.debug(field)

    def clear_pool(self):
        self.pool.close()

        self.pool = Pool()
        self.pool_recreated.emit(self.pool)

        gc.collect()

    # the order that the tools are installed is important as they can depend on each other install position
    def install_tools(self):
        self.dblsidedtool = DblSidedTool(self)
        self.dblsidedtool.install(icon=QtGui.QIcon('share/doubleside16.png'), separator=True)

        self.measurement_tool = Measurement(self)
        self.measurement_tool.install(icon=QtGui.QIcon('share/measure16.png'), separator=True)

        self.panelize_tool = Panelize(self)
        self.panelize_tool.install(icon=QtGui.QIcon('share/panel16.png'))

        self.film_tool = Film(self)
        self.film_tool.install(icon=QtGui.QIcon('share/film16.png'))

        self.paste_tool = SolderPaste(self)
        self.paste_tool.install(icon=QtGui.QIcon('share/solderpastebis32.png'), separator=True)

        self.move_tool = ToolMove(self)
        self.move_tool.install(icon=QtGui.QIcon('share/move16.png'), pos=self.ui.menuedit,
                               before=self.ui.menueditorigin)

        self.cutout_tool = CutOut(self)
        self.cutout_tool.install(icon=QtGui.QIcon('share/cut16_bis.png'), pos=self.ui.menutool,
                                 before=self.measurement_tool.menuAction)

        self.ncclear_tool = NonCopperClear(self)
        self.ncclear_tool.install(icon=QtGui.QIcon('share/ncc16.png'), pos=self.ui.menutool,
                                 before=self.measurement_tool.menuAction, separator=True)

        self.paint_tool = ToolPaint(self)
        self.paint_tool.install(icon=QtGui.QIcon('share/paint16.png'), pos=self.ui.menutool,
                                  before=self.measurement_tool.menuAction, separator=True)

        self.calculator_tool = ToolCalculator(self)
        self.calculator_tool.install(icon=QtGui.QIcon('share/calculator24.png'))

        self.transform_tool = ToolTransform(self)
        self.transform_tool.install(icon=QtGui.QIcon('share/transform.png'), pos=self.ui.menuoptions, separator=True)

        self.properties_tool = Properties(self)
        self.properties_tool.install(icon=QtGui.QIcon('share/properties32.png'), pos=self.ui.menuoptions)

        self.image_tool = ToolImage(self)
        self.image_tool.install(icon=QtGui.QIcon('share/image32.png'), pos=self.ui.menufileimport,
                                separator=True)

        self.log.debug("Tools are installed.")

    def remove_tools(self):
        for act in self.ui.menutool.actions():
            self.ui.menutool.removeAction(act)

    def init_tools(self):
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
        # second re add the TCL Shell action to the Tools menu and reconnect it to ist slot function
        self.ui.menutoolshell = self.ui.menutool.addAction(QtGui.QIcon('share/shell16.png'), '&Command Line\tS')
        self.ui.menutoolshell.triggered.connect(self.on_toggle_shell)
        # third install all of them
        self.install_tools()
        self.log.debug("Tools are initialized.")

    # def parse_system_fonts(self):
    #     self.worker_task.emit({'fcn': self.f_parse.get_fonts_by_types,
    #                            'params': []})

    def connect_toolbar_signals(self):
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
        self.ui.newexc_btn.triggered.connect(self.new_excellon_object)
        self.ui.editgeo_btn.triggered.connect(self.object2editor)
        self.ui.update_obj_btn.triggered.connect(self.editor2object)
        self.ui.delete_btn.triggered.connect(self.on_delete)
        self.ui.shell_btn.triggered.connect(self.on_toggle_shell)

        # Tools Toolbar Signals
        self.ui.dblsided_btn.triggered.connect(lambda: self.dblsidedtool.run(toggle=True))
        self.ui.cutout_btn.triggered.connect(lambda: self.cutout_tool.run(toggle=True))
        self.ui.ncc_btn.triggered.connect(lambda: self.ncclear_tool.run(toggle=True))
        self.ui.paint_btn.triggered.connect(lambda: self.paint_tool.run(toggle=True))

        self.ui.panelize_btn.triggered.connect(lambda: self.panelize_tool.run(toggle=True))
        self.ui.film_btn.triggered.connect(lambda: self.film_tool.run(toggle=True))
        self.ui.solder_btn.triggered.connect(lambda: self.paste_tool.run(toggle=True))

        self.ui.calculators_btn.triggered.connect(lambda: self.calculator_tool.run(toggle=True))
        self.ui.transform_btn.triggered.connect(lambda: self.transform_tool.run(toggle=True))

    def object2editor(self):
        """
        Send the current Geometry or Excellon object (if any) into the editor.

        :return: None
        """
        self.report_usage("object2editor()")

        # adjust the visibility of some of the canvas context menu
        self.ui.popmenu_edit.setVisible(False)
        self.ui.popmenu_save.setVisible(True)

        # adjust the status of the menu entries related to the editor
        self.ui.menueditedit.setDisabled(True)
        self.ui.menueditok.setDisabled(False)

        edited_object = self.collection.get_active()

        if isinstance(edited_object, FlatCAMGeometry):
            # for now, if the Geometry is MultiGeo do not allow the editing
            if edited_object.multigeo is True:
                self.inform.emit(_("[WARNING_NOTCL] Editing a MultiGeo Geometry is not possible for the moment."))
                return

            # store the Geometry Editor Toolbar visibility before entering in the Editor
            self.geo_editor.toolbar_old_state = True if self.ui.geo_edit_toolbar.isVisible() else False
            self.geo_editor.edit_fcgeometry(edited_object)

            # we set the notebook to hidden
            self.ui.splitter.setSizes([0, 1])

            # set call source to the Editor we go into
            self.call_source = 'geo_editor'

        elif isinstance(edited_object, FlatCAMExcellon):
            # store the Excellon Editor Toolbar visibility before entering in the Editor
            self.exc_editor.toolbar_old_state = True if self.ui.exc_edit_toolbar.isVisible() else False
            self.exc_editor.edit_fcexcellon(edited_object)

            # set call source to the Editor we go into
            self.call_source = 'exc_editor'
        else:
            self.inform.emit(_("[WARNING_NOTCL]Select a Geometry or Excellon Object to edit."))
            return

        # make sure that we can't select another object while in Editor Mode:
        self.collection.view.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)

        # delete any selection shape that might be active as they are not relevant in Editor
        self.delete_selection_shape()

        self.ui.plot_tab_area.setTabText(0, "EDITOR Area")
        self.ui.plot_tab_area.protectTab(0)
        self.inform.emit(_("[WARNING_NOTCL]Editor is activated ..."))

        self.should_we_save = True

    def editor2object(self):
        """
        Transfers the Geometry or Excellon from the editor to the current object.

        :return: None
        """
        self.report_usage("editor2object()")

        # adjust the status of the menu entries related to the editor
        self.ui.menueditedit.setDisabled(False)
        self.ui.menueditok.setDisabled(True)

        # do not update a geometry or excellon object unless it comes out of an editor
        if self.call_source != 'app':
            # adjust the visibility of some of the canvas context menu
            self.ui.popmenu_edit.setVisible(True)
            self.ui.popmenu_save.setVisible(False)

            edited_obj = self.collection.get_active()
            obj_type = ""

            if isinstance(edited_obj, FlatCAMGeometry):
                obj_type = "Geometry"
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
                except AttributeError:
                    self.inform.emit(_("[WARNING] Object empty after edit."))

            elif isinstance(edited_obj, FlatCAMExcellon):
                obj_type = "Excellon"
                self.exc_editor.update_fcexcellon(edited_obj)
                self.exc_editor.update_options(edited_obj)
                self.exc_editor.deactivate()

            else:
                self.inform.emit(_("[WARNING_NOTCL]Select a Geometry or Excellon Object to update."))
                return

            # if notebook is hidden we show it
            if self.ui.splitter.sizes()[0] == 0:
                self.ui.splitter.setSizes([1, 1])

            # restore the call_source to app
            self.call_source = 'app'

            edited_obj.plot()
            self.ui.plot_tab_area.setTabText(0, "Plot Area")
            self.ui.plot_tab_area.protectTab(0)
            self.inform.emit(_("[selected] %s is updated, returning to App...") % obj_type)

            # reset the Object UI to original settings
            # edited_obj.set_ui(edited_obj.ui_type())
            # edited_obj.build_ui()
            # make sure that we reenable the selection on Project Tab after returning from Editor Mode:
            self.collection.view.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)


    def get_last_folder(self):
        return self.defaults["global_last_folder"]

    def get_last_save_folder(self):
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
        if hasattr(self,'tcl'):
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
        this exception is deffined here, to be able catch it if we sucessfully handle all errors from shell command
        """
        pass

    def shell_message(self, msg, show=False, error=False, warning=False, success=False, selected=False):
        """
        Shows a message on the FlatCAM Shell

        :param msg: Message to display.
        :param show: Opens the shell.
        :param error: Shows the message as an error.
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
        escape bracket [ with \  otherwise there is error
        "ERROR: missing close-bracket" instead of real error
        :param error: it may be text  or exception
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
                text = "%s\nPython traceback: %s\n%s" % (exc_value,
                                 exc_type,
                                 "\n".join(trc_formated))

            else:
                text = "%s" % error
        else:
            text = error

        text = text.replace('[', '\\[').replace('"', '\\"')

        self.tcl.eval('return -code error "%s"' % text)

    def raise_tcl_error(self, text):
        """
        this method  pass exception from python into TCL as error, so we get stacktrace and reason
        :param text: text of error
        :return: raise exception
        """

        self.display_tcl_error(text)
        raise self.TclErrorException(text)

    def exec_command(self, text):
        """
        Handles input from the shell. See FlatCAMApp.setup_shell for shell commands.
        Also handles execution in separated threads

        :param text:
        :return: output if there was any
        """

        self.report_usage('exec_command')

        result = self.exec_command_test(text, False)

        #MS: added this method call so the geometry is updated once the TCL
        #command is executed
        self.plot_all()

        return result

    def exec_command_test(self, text, reraise=True):
        """
        Same as exec_command(...) with additional control over  exceptions.
        Handles input from the shell. See FlatCAMApp.setup_shell for shell commands.

        :param text: Input command
        :param reraise: Re-raise TclError exceptions in Python (mostly for unitttests).
        :return: Output from the command
        """

        text = str(text)

        try:
            self.shell.open_proccessing()  # Disables input box.
            result = self.tcl.eval(str(text))
            if result != 'None':
                self.shell.append_output(result + '\n')

        except tk.TclError as e:
            # This will display more precise answer if something in TCL shell fails
            result = self.tcl.eval("set errorInfo")
            self.log.error("Exec command Exception: %s" % (result + '\n'))
            self.shell.append_error('ERROR: ' + result + '\n')
            # Show error in console and just return or in test raise exception
            if reraise:
                raise e

        finally:
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

        # Type of message in brackets at the begining of the message.
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
            self.ui.snap_toolbar.setVisible(True)
        else:
            self.ui.snap_toolbar.setVisible(False)

        if tb & 128:
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
            self.inform.emit(_("[ERROR] Could not load defaults file."))
            # in case the defaults file can't be loaded, show all toolbars
            self.defaults["global_toolbar_view"] = 255
            return

        try:
            defaults = json.loads(options)
        except:
            # in case the defaults file can't be loaded, show all toolbars
            self.defaults["global_toolbar_view"] = 255
            e = sys.exc_info()[0]
            App.log.error(str(e))
            self.inform.emit(_("[ERROR] Failed to parse defaults file."))
            return
        self.defaults.update(defaults)
        log.debug("FlatCAM defaults loaded from: %s" % filename)

        # restore the toolbar view
        self.restore_toolbar_view()

    def on_import_preferences(self):
        """
        Loads the aplication's factory default settings from factory_defaults.FlatConfig into
        ``self.defaults``.

        :return: None
        """

        self.report_usage("on_import_preferences")
        App.log.debug("on_import_preferences()")

        filter = "Config File (*.FlatConfig);;All Files (*.*)"
        try:
            filename, _f = QtWidgets.QFileDialog.getOpenFileName(caption=_("Import FlatCAM Preferences"),
                                                                directory=self.data_path, filter=filter)
        except TypeError:
            filename, _f = QtWidgets.QFileDialog.getOpenFileName(caption=_("Import FlatCAM Preferences"), filter=filter)

        filename = str(filename)

        if filename == "":
            self.inform.emit(_("[WARNING_NOTCL]FlatCAM preferences import cancelled."))
        else:
            try:
                f = open(filename)
                options = f.read()
                f.close()
            except IOError:
                self.log.error("Could not load defaults file.")
                self.inform.emit(_("[ERROR_NOTCL] Could not load defaults file."))
                return

            try:
                defaults_from_file = json.loads(options)
            except:
                e = sys.exc_info()[0]
                App.log.error(str(e))
                self.inform.emit(_("[ERROR_NOTCL] Failed to parse defaults file."))
                return
            self.defaults.update(defaults_from_file)
            self.inform.emit(_("[success]Imported Defaults from %s") %filename)

    def on_export_preferences(self):

        self.report_usage("on_export_preferences")
        App.log.debug("on_export_preferences()")

        filter = "Config File (*.FlatConfig);;All Files (*.*)"
        try:
            filename, _f = QtWidgets.QFileDialog.getSaveFileName(
                caption=_("Export FlatCAM Preferences"),
                directory=self.data_path + '/preferences_' + self.date, filter=filter
            )
        except TypeError:
            filename, _f = QtWidgets.QFileDialog.getSaveFileName(caption=_("Export FlatCAM Preferences"), filter=filter)

        filename = str(filename)
        defaults_from_file = {}

        if filename == "":
            self.inform.emit(_("[WARNING_NOTCL]FlatCAM preferences export cancelled."))
            return
        else:
            try:
                f = open(filename, 'w')
                defaults_file_content = f.read()
                f.close()
            except IOError:
                App.log.debug('Creating a new preferences file ...')
                f = open(filename, 'w')
                json.dump({}, f)
                f.close()
            except:
                e = sys.exc_info()[0]
                App.log.error("Could not load defaults file.")
                App.log.error(str(e))
                self.inform.emit(_("[ERROR_NOTCL]Could not load defaults file."))
                return

            try:
                defaults_from_file = json.loads(defaults_file_content)
            except:
                App.log.warning("Trying to read an empty Preferences file. Continue.")

            # Update options
            self.defaults_read_form()
            defaults_from_file.update(self.defaults)
            self.propagate_defaults(silent=True)

            # Save update options
            try:
                f = open(filename, "w")
                json.dump(defaults_from_file, f)
                f.close()
            except:
                self.inform.emit(_("[ERROR_NOTCL] Failed to write defaults to file."))
                return

        self.file_saved.emit("preferences", filename)
        self.inform.emit("[success]Exported Defaults to %s" % filename)

    def on_preferences_open_folder(self):
        self.report_usage("on_preferences_open_folder()")

        if sys.platform == 'win32':
            subprocess.Popen('explorer %s' % self.data_path)
        elif sys.platform == 'darwin':
            os.system('open "%s"' % self.data_path)
        else:
            subprocess.Popen(['xdg-open', self.data_path])
        self.inform.emit("[success]FlatCAM Preferences Folder opened.")

    def save_geometry(self, x, y, width, height, notebook_width):
        self.defaults["global_def_win_x"] = x
        self.defaults["global_def_win_y"] = y
        self.defaults["global_def_win_w"] = width
        self.defaults["global_def_win_h"] = height
        self.defaults["def_notebook_width"] = notebook_width
        self.save_defaults()

    def message_dialog(self, title, message, kind="info"):
        icon = {"info": QtWidgets.QMessageBox.Information,
                "warning": QtWidgets.QMessageBox.Warning,
                "error": QtWidgets.QMessageBox.Critical}[str(kind)]
        dlg = QtWidgets.QMessageBox(icon, title, message, parent=self.ui)
        dlg.setText(message)
        dlg.exec_()

    def register_recent(self, kind, filename):

        self.log.debug("register_recent()")
        self.log.debug("   %s" % kind)
        self.log.debug("   %s" % filename)

        record = {'kind': str(kind), 'filename': str(filename)}
        if record in self.recent:
            return

        self.recent.insert(0, record)

        if len(self.recent) > self.defaults['global_recent_limit']:  # Limit reached
            self.recent.pop()

        try:
            f = open(self.data_path + '/recent.json', 'w')
        except IOError:
            App.log.error("Failed to open recent items file for writing.")
            self.inform.emit(_('[ERROR_NOTCL]Failed to open recent files file for writing.'))
            return

        #try:
        json.dump(self.recent, f, default=to_dict, indent=2, sort_keys=True)
        # except:
        #     App.log.error("Failed to write to recent items file.")
        #     self.inform.emit('ERROR: Failed to write to recent items file.')
        #     f.close()

        f.close()

        # Re-buid the recent items menu
        self.setup_recent_items()

    def new_object(self, kind, name, initialize, active=True, fit=True, plot=True, autoselected=True):
        """
        Creates a new specalized FlatCAMObj and attaches it to the application,
        this is, updates the GUI accordingly, any other records and plots it.
        This method is thread-safe.

        Notes:
            * If the name is in use, the self.collection will modify it
              when appending it to the collection. There is no need to handle
              name conflicts here.

        :param kind: The kind of object to create. One of 'gerber',
         'excellon', 'cncjob' and 'geometry'.
        :type kind: str
        :param name: Name for the object.
        :type name: str
        :param initialize: Function to run after creation of the object
         but before it is attached to the application. The function is
         called with 2 parameters: the new object and the App instance.
        :type initialize: function
        :return: None
        :rtype: None
        """

        App.log.debug("new_object()")
        obj_plot = plot
        obj_autoselected = autoselected

        t0 = time.time()  # Debug

        ## Create object
        classdict = {
            "gerber": FlatCAMGerber,
            "excellon": FlatCAMExcellon,
            "cncjob": FlatCAMCNCjob,
            "geometry": FlatCAMGeometry
        }

        App.log.debug("Calling object constructor...")
        obj = classdict[kind](name)
        obj.units = self.options["units"]  # TODO: The constructor should look at defaults.

        # Set options from "Project options" form
        self.options_read_form()

        # IMPORTANT
        # The key names in defaults and options dictionary's are not random:
        # they have to have in name first the type of the object (geometry, excellon, cncjob and gerber) or how it's
        # called here, the 'kind' followed by an underline. The function called above (self.options_read_form()) copy
        # the options from project options form into the self.options. After that, below, depending on the type of
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
            msg = _("[ERROR_NOTCL] An internal error has ocurred. See shell.\n")
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
            self.inform.emit(_("Converting units to ") + self.options["units"] + ".")
            obj.convert_units(self.options["units"])
            t3 = time.time()
            self.log.debug("%f seconds converting units." % (t3 - t2))

        # Create the bounding box for the object and then add the results to the obj.options
        try:
            xmin, ymin, xmax, ymax = obj.bounds()
            obj.options['xmin'] = xmin
            obj.options['ymin'] = ymin
            obj.options['xmax'] = xmax
            obj.options['ymax'] = ymax
        except:
            log.warning("The object has no bounds properties.")
            # don't plot objects with no bounds, there is nothing to plot
            self.plot = False
            pass

        FlatCAMApp.App.log.debug("Moving new object back to main thread.")

        # Move the object to the main thread and let the app know that it is available.
        obj.moveToThread(QtWidgets.QApplication.instance().thread())
        self.object_created.emit(obj, obj_plot, obj_autoselected)

        return obj

    def new_excellon_object(self):
        self.report_usage("new_excellon_object()")

        self.new_object('excellon', 'new_e', lambda x, y: None, plot=False)

    def new_geometry_object(self):
        self.report_usage("new_geometry_object()")

        def initialize(obj, self):
            obj.multitool = False

        self.new_object('geometry', 'new_g', initialize, plot=False)

    def on_object_created(self, obj, plot, autoselect):
        """
        Event callback for object creation.

        :param obj: The newly created FlatCAM object.
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
            self.inform.emit(_('[selected]{kind} created/selected: <span style="color:{color};">{name}</span>').format(
                kind=obj.kind.capitalize(), color='green', name=str(obj.options['name'])))
        elif obj.kind == 'excellon':
            self.inform.emit(_('[selected]{kind} created/selected: <span style="color:{color};">{name}</span>').format(
                kind=obj.kind.capitalize(), color='brown', name=str(obj.options['name'])))
        elif obj.kind == 'cncjob':
            self.inform.emit(_('[selected]{kind} created/selected: <span style="color:{color};">{name}</span>').format(
                kind=obj.kind.capitalize(), color='blue', name=str(obj.options['name'])))
        elif obj.kind == 'geometry':
            self.inform.emit(_('[selected]{kind} created/selected: <span style="color:{color};">{name}</span>').format(
                kind=obj.kind.capitalize(), color='red', name=str(obj.options['name'])))

        # update the SHELL auto-completer model with the name of the new object
        self.myKeywords.append(obj.options['name'])
        self.shell._edit.set_model_data(self.myKeywords)
        self.ui.code_editor.set_model_data(self.myKeywords)

        if autoselect:
            # select the just opened object but deselect the previous ones
            self.collection.set_all_inactive()
            self.collection.set_active(obj.options["name"])

        # here it is done the object plotting
        def worker_task(obj):
            with self.proc_container.new("Plotting"):
                if isinstance(obj, FlatCAMCNCjob):
                    obj.plot(kind=self.defaults["cncjob_plot_kind"])
                else:
                    obj.plot()
                t1 = time.time()  # DEBUG
                self.log.debug("%f seconds adding object and plotting." % (t1 - t0))
                self.object_plotted.emit(obj)

        # Send to worker
        # self.worker.add_task(worker_task, [self])
        if plot is True:
            self.worker_task.emit({'fcn': worker_task, 'params': [obj]})

    def on_object_changed(self, obj):
        # update the bounding box data from obj.options
        xmin, ymin, xmax, ymax = obj.bounds()
        obj.options['xmin'] = xmin
        obj.options['ymin'] = ymin
        obj.options['xmax'] = xmax
        obj.options['ymax'] = ymax

        log.debug("Object changed, updating the bounding box data on self.options")
        # delete the old selection shape
        self.delete_selection_shape()
        self.should_we_save = True

    def on_object_plotted(self, obj):
        self.on_zoom_fit(None)

    def options_read_form(self):
        for option in self.options_form_fields:
            self.options[option] = self.options_form_fields[option].get_value()

    def options_write_form(self):
        for option in self.options:
            self.options_write_form_field(option)

    def options_write_form_field(self, field):
        try:
            self.options_form_fields[field].set_value(self.options[field])
        except KeyError:
            # Changed from error to debug. This allows to have data stored
            # which is not user-editable.
            # self.log.debug("options_write_form_field(): No field for: %s" % field)
            pass

    def on_about(self):
        """
        Displays the "about" dialog.

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
                self.setWindowTitle("FlatCAM")

                layout1 = QtWidgets.QVBoxLayout()
                self.setLayout(layout1)

                layout2 = QtWidgets.QHBoxLayout()
                layout1.addLayout(layout2)

                logo = QtWidgets.QLabel()
                logo.setPixmap(QtGui.QPixmap('share/flatcam_icon256.png'))
                layout2.addWidget(logo, stretch=0)

                title = QtWidgets.QLabel(
                    _(
                        "<font size=8><B>FlatCAM</B></font><BR>"
                        "Version {version} {beta} ({date}) - {arch} <BR>"
                        "<BR>"
                        "2D Computer-Aided Printed Circuit Board<BR>"
                        "Manufacturing.<BR>"
                        "<BR>"
                        "(c) 2014-2019 <B>Juan Pablo Caram</B><BR>"
                        "<BR>"
                        "<B> Main Contributors:</B><BR>"
                        "Denis Hayrullin<BR>"
                        "Kamil Sopko<BR>"
                        "Marius Stanciu<BR>"
                        "Matthieu Berthomé<BR>"
                        "and many others found "
                        "<a href = \"https://bitbucket.org/jpcgt/flatcam/pull-requests/?state=MERGED\">here.</a><BR>"
                        "<BR>"
                        "Development is done "
                        "<a href = \"https://bitbucket.org/jpcgt/flatcam/src/Beta/\">here.</a><BR>"
                        "DOWNLOAD area "
                        "<a href = \"https://bitbucket.org/jpcgt/flatcam/downloads/\">here.</a><BR>"
                        ""
                    ).format(version=version,
                             beta=('BETA' if beta else ''),
                             date=version_date,
                             arch=platform.architecture()[0])
                )
                title.setOpenExternalLinks(True)

                layout2.addWidget(title, stretch=1)

                layout3 = QtWidgets.QHBoxLayout()
                layout1.addLayout(layout3)
                layout3.addStretch()
                okbtn = QtWidgets.QPushButton("Close")
                layout3.addWidget(okbtn)

                okbtn.clicked.connect(self.accept)

        AboutDialog(self.ui).exec_()

    def on_file_savedefaults(self):
        """
        Callback for menu item File->Save Defaults. Saves application default options
        ``self.defaults`` to current_defaults.FlatConfig.

        :return: None
        """

        self.save_defaults()

    def on_app_exit(self):
        self.report_usage("on_app_exit()")

        if self.collection.get_list():
            msgbox = QtWidgets.QMessageBox()
            # msgbox.setText("<B>Save changes ...</B>")
            msgbox.setText("There are files/objects opened in FlatCAM. "
                           "\n"
                           "Do you want to Save the project?")
            msgbox.setWindowTitle("Save changes")
            msgbox.setWindowIcon(QtGui.QIcon('share/save_as.png'))
            msgbox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No |
                                      QtWidgets.QMessageBox.Cancel)
            msgbox.setDefaultButton(QtWidgets.QMessageBox.Yes)

            response = msgbox.exec_()

            if response == QtWidgets.QMessageBox.Yes:
                self.on_file_saveprojectas(thread=False)
            elif response == QtWidgets.QMessageBox.Cancel:
                return
            self.save_defaults()
        else:
            self.save_defaults()
        log.debug("Application defaults saved ... Exit event.")
        QtWidgets.qApp.quit()

    def save_defaults(self, silent=False):
        """
        Saves application default options
        ``self.defaults`` to current_defaults.FlatConfig.

        :return: None
        """
        self.report_usage("save_defaults")

        # Read options from file
        try:
            f = open(self.data_path + "/current_defaults.FlatConfig")
            defaults_file_content = f.read()
            f.close()
        except:
            e = sys.exc_info()[0]
            App.log.error("Could not load defaults file.")
            App.log.error(str(e))
            self.inform.emit(_("[ERROR_NOTCL] Could not load defaults file."))
            return

        try:
            defaults = json.loads(defaults_file_content)
        except:
            e = sys.exc_info()[0]
            App.log.error("Failed to parse defaults file.")
            App.log.error(str(e))
            self.inform.emit(_("[ERROR_NOTCL] Failed to parse defaults file."))
            return

        # Update options
        self.defaults_read_form()
        defaults.update(self.defaults)
        self.propagate_defaults(silent=True)

        # Save update options
        try:
            f = open(self.data_path + "/current_defaults.FlatConfig", "w")
            json.dump(defaults, f, default=to_dict, indent=2, sort_keys=True)
            f.close()
        except:
            self.inform.emit(_("[ERROR_NOTCL] Failed to write defaults to file."))
            return

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

        if self.ui.snap_toolbar.isVisible():
            tb_status += 64

        if self.ui.toolbarshell.isVisible():
            tb_status += 128

        self.defaults["global_toolbar_view"] = tb_status

        if not silent:
            self.inform.emit(_("[success]Defaults saved."))

    def save_factory_defaults(self, silent=False):
        """
                Saves application factory default options
                ``self.defaults`` to factory_defaults.FlatConfig.
                It's a one time job done just after the first install.

                :return: None
                """
        self.report_usage("save_factory_defaults")

        # Read options from file
        try:
            f_f_def = open(self.data_path + "/factory_defaults.FlatConfig")
            factory_defaults_file_content = f_f_def.read()
            f_f_def.close()
        except:
            e = sys.exc_info()[0]
            App.log.error("Could not load factory defaults file.")
            App.log.error(str(e))
            self.inform.emit(_("[ERROR_NOTCL] Could not load factory defaults file."))
            return

        try:
            factory_defaults = json.loads(factory_defaults_file_content)
        except:
            e = sys.exc_info()[0]
            App.log.error("Failed to parse factory defaults file.")
            App.log.error(str(e))
            self.inform.emit(_("[ERROR_NOTCL] Failed to parse factory defaults file."))
            return

        # Update options
        self.defaults_read_form()
        factory_defaults.update(self.defaults)
        self.propagate_defaults(silent=True)

        # Save update options
        try:
            f_f_def_s = open(self.data_path + "/factory_defaults.FlatConfig", "w")
            json.dump(factory_defaults, f_f_def_s, default=to_dict, indent=2, sort_keys=True)
            f_f_def_s.close()
        except:
            self.inform.emit(_("[ERROR_NOTCL] Failed to write factory defaults to file."))
            return

        if silent is False:
            self.inform.emit(_("Factory defaults saved."))

    def final_save(self):
        if self.should_we_save and self.collection.get_list():
            msgbox = QtWidgets.QMessageBox()
            msgbox.setText(_("There are files/objects modified in FlatCAM. "
                           "\n"
                           "Do you want to Save the project?"))
            msgbox.setWindowTitle(_("Save changes"))
            msgbox.setWindowIcon(QtGui.QIcon('share/save_as.png'))
            msgbox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No |
                                      QtWidgets.QMessageBox.Cancel)
            msgbox.setDefaultButton(QtWidgets.QMessageBox.Yes)

            response = msgbox.exec_()

            if response == QtWidgets.QMessageBox.Yes:
                self.on_file_saveprojectas(thread=False)
            elif response == QtWidgets.QMessageBox.Cancel:
                self.should_we_quit = False
                return

        self.save_defaults()
        log.debug("App.final_save() --> App Defaults saved.")

        # save toolbar state to file
        settings = QSettings("Open Source", "FlatCAM")
        settings.setValue('saved_gui_state', self.ui.saveState())
        settings.setValue('maximized_gui', self.ui.isMaximized())

        # This will write the setting to the platform specific storage.
        del settings
        log.debug("App.final_save() --> App UI state saved.")
        QtWidgets.qApp.quit()

    def on_toggle_shell(self):
        """
        toggle shell if is  visible close it if  closed open it
        :return:
        """
        self.report_usage("on_toggle_shell()")

        if self.ui.shell_dock.isVisible():
            self.ui.shell_dock.hide()
        else:
            self.ui.shell_dock.show()

    def on_edit_join(self, name=None):
        """
        Callback for Edit->Join. Joins the selected geometry objects into
        a new one.

        :return: None
        """
        self.report_usage("on_edit_join()")

        obj_name_single = str(name) if name else "Combo_SingleGeo"
        obj_name_multi = str(name) if name else "Combo_MultiGeo"

        tooldias = []
        geo_type_list = []

        objs = self.collection.get_selected()
        for obj in objs:
            geo_type_list.append(obj.multigeo)

        # if len(set(geo_type_list)) == 1 means that all list elements are the same
        if len(set(geo_type_list)) != 1:
            self.inform.emit(_("[ERROR] Failed join. The Geometry objects are of different types.\n"
                             "At least one is MultiGeo type and the other is SingleGeo type. A possibility is to "
                             "convert from one to another and retry joining \n"
                             "but in the case of converting from MultiGeo to SingleGeo, informations may be lost and "
                             "the result may not be what was expected. \n"
                             "Check the generated GCODE."))
            return

        # if at least one True object is in the list then due of the previous check, all list elements are True objects
        if True in geo_type_list:
            def initialize(obj, app):
                FlatCAMGeometry.merge(objs, obj, multigeo=True)

                # rename all the ['name] key in obj.tools[tooluid]['data'] to the obj_name_multi
                for v in obj.tools.values():
                    v['data']['name'] = obj_name_multi
            self.new_object("geometry", obj_name_multi, initialize)
        else:
            def initialize(obj, app):
                FlatCAMGeometry.merge(objs, obj, multigeo=False)

                # rename all the ['name] key in obj.tools[tooluid]['data'] to the obj_name_multi
                for v in obj.tools.values():
                    v['data']['name'] = obj_name_single
            self.new_object("geometry", obj_name_single, initialize)

        self.should_we_save = True

    def on_edit_join_exc(self):
        """
        Callback for Edit->Join Excellon. Joins the selected excellon objects into
        a new one.

        :return: None
        """
        self.report_usage("on_edit_join_exc()")

        objs = self.collection.get_selected()

        for obj in objs:
            if not isinstance(obj, FlatCAMExcellon):
                self.inform.emit(_("[ERROR_NOTCL]Failed. Excellon joining works only on Excellon objects."))
                return

        def initialize(obj, app):
            FlatCAMExcellon.merge(objs, obj)

        self.new_object("excellon", 'Combo_Excellon', initialize)
        self.should_we_save = True

    def on_edit_join_grb(self):
        """
                Callback for Edit->Join Gerber. Joins the selected Gerber objects into
                a new one.

                :return: None
                """
        self.report_usage("on_edit_join_grb()")

        objs = self.collection.get_selected()

        for obj in objs:
            if not isinstance(obj, FlatCAMGerber):
                self.inform.emit(_("[ERROR_NOTCL]Failed. Gerber joining works only on Gerber objects."))
                return

        def initialize(obj, app):
            FlatCAMGerber.merge(objs, obj)

        self.new_object("gerber", 'Combo_Gerber', initialize)
        self.should_we_save = True

    def on_convert_singlegeo_to_multigeo(self):
        self.report_usage("on_convert_singlegeo_to_multigeo()")

        obj = self.collection.get_active()

        if obj is None:
            self.inform.emit(_("[ERROR_NOTCL]Failed. Select a Geometry Object and try again."))
            return

        if not isinstance(obj, FlatCAMGeometry):
            self.inform.emit(_("[ERROR_NOTCL]Expected a FlatCAMGeometry, got %s") % type(obj))
            return

        obj.multigeo = True
        for tooluid, dict_value in obj.tools.items():
            dict_value['solid_geometry'] = deepcopy(obj.solid_geometry)
        if not isinstance(obj.solid_geometry, list):
            obj.solid_geometry = [obj.solid_geometry]
        obj.solid_geometry[:] = []
        obj.plot()

        self.should_we_save = True

        self.inform.emit(_("[success] A Geometry object was converted to MultiGeo type."))

    def on_convert_multigeo_to_singlegeo(self):
        self.report_usage("on_convert_multigeo_to_singlegeo()")

        obj = self.collection.get_active()

        if obj is None:
            self.inform.emit(_("[ERROR_NOTCL]Failed. Select a Geometry Object and try again."))
            return

        if not isinstance(obj, FlatCAMGeometry):
            self.inform.emit(_("[ERROR_NOTCL]Expected a FlatCAMGeometry, got %s") % type(obj))
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

        self.inform.emit(_("[success] A Geometry object was converted to SingleGeo type."))

    def on_options_dict_change(self, field):
        self.options_write_form_field(field)

        if field == "units":
            self.set_screen_units(self.options['units'])

    def on_defaults_dict_change(self, field):
        self.defaults_write_form_field(field)

        if field == "units":
            self.set_screen_units(self.defaults['units'])

    def set_screen_units(self, units):
        self.ui.units_label.setText("[" + self.defaults["units"].lower() + "]")

    def on_toggle_units(self):
        """
        Callback for the Units radio-button change in the Options tab.
        Changes the application's default units or the current project's units.
        If changing the project's units, the change propagates to all of
        the objects in the project.

        :return: None
        """

        self.report_usage("on_toggle_units")

        if self.toggle_units_ignore:
            return

        # If option is the same, then ignore
        if self.ui.general_defaults_form.general_app_group.units_radio.get_value().upper() == \
                self.defaults["units"].upper():
            self.log.debug("on_toggle_units(): Same as defaults, so ignoring.")
            return

        # Options to scale
        dimensions = ['gerber_isotooldia', 'gerber_noncoppermargin', 'gerber_bboxmargin',

                      'excellon_drillz',  'excellon_travelz', "excellon_toolchangexy",
                      'excellon_feedrate', 'excellon_feedrate_rapid', 'excellon_toolchangez',
                      'excellon_tooldia', 'excellon_slot_tooldia', 'excellon_endz', "excellon_feedrate_probe",
                      "excellon_z_pdepth",

                      'geometry_cutz',  "geometry_depthperpass", 'geometry_travelz', 'geometry_feedrate',
                      'geometry_feedrate_rapid', "geometry_toolchangez", "geometry_feedrate_z",
                      "geometry_toolchangexy", 'geometry_cnctooldia', 'geometry_endz', "geometry_z_pdepth",
                      "geometry_feedrate_probe",

                      'cncjob_tooldia',

                      'tools_paintmargin', 'tools_painttooldia', 'tools_paintoverlap',
                      "tools_ncctools", "tools_nccoverlap", "tools_nccmargin",
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

                      'global_gridx', 'global_gridy', 'global_snap_max']

        def scale_options(sfactor):
            for dim in dimensions:
                if dim == 'excellon_toolchangexy':
                    coords_xy = [float(eval(a)) for a in self.defaults["excellon_toolchangexy"].split(",")]
                    coords_xy[0] *= sfactor
                    coords_xy[1] *= sfactor
                    self.options['excellon_toolchangexy'] = "%f, %f" % (coords_xy[0], coords_xy[1])
                elif dim == 'geometry_toolchangexy':
                    coords_xy = [float(eval(a)) for a in self.defaults["geometry_toolchangexy"].split(",")]
                    coords_xy[0] *= sfactor
                    coords_xy[1] *= sfactor
                    self.options['geometry_toolchangexy'] = "%f, %f" % (coords_xy[0], coords_xy[1])
                elif dim == 'tools_ncctools':
                    ncctols = [float(eval(a)) for a in self.defaults["tools_ncctools"].split(",")]
                    ncctols[0] *= sfactor
                    ncctols[1] *= sfactor
                    self.options['tools_ncctools'] = "%f, %f" % (ncctols[0], ncctols[1])
                elif dim == 'tools_solderpaste_tools':
                    sp_tools = [float(eval(a)) for a in self.defaults["tools_solderpaste_tools"].split(",")]
                    sp_tools[0] *= sfactor
                    sp_tools[1] *= sfactor
                    self.options['tools_solderpaste_tools'] = "%f, %f" % (sp_tools[0], sp_tools[1])
                elif dim == 'tools_solderpaste_xy_toolchange':
                    sp_coords = [float(eval(a)) for a in self.defaults["tools_solderpaste_xy_toolchange"].split(",")]
                    sp_coords[0] *= sfactor
                    sp_coords[1] *= sfactor
                    self.options['tools_solderpaste_xy_toolchange'] = "%f, %f" % (sp_coords[0], sp_coords[1])
                else:
                    try:
                        self.options[dim] = float(self.options[dim]) * sfactor
                    except Exception as e:
                        log.debug('App.on_toggle_units().scale_options() --> %s' % str(e))

        def scale_defaults(sfactor):
            for dim in dimensions:
                if dim == 'excellon_toolchangexy':
                    coords_xy = [float(eval(a)) for a in self.defaults["excellon_toolchangexy"].split(",")]
                    coords_xy[0] *= sfactor
                    coords_xy[1] *= sfactor
                    self.defaults['excellon_toolchangexy'] = "%.4f, %.4f" % (coords_xy[0], coords_xy[1])
                elif dim == 'geometry_toolchangexy':
                    coords_xy = [float(eval(a)) for a in self.defaults["geometry_toolchangexy"].split(",")]
                    coords_xy[0] *= sfactor
                    coords_xy[1] *= sfactor
                    self.defaults['geometry_toolchangexy'] = "%.4f, %.4f" % (coords_xy[0], coords_xy[1])
                elif dim == 'tools_ncctools':
                    ncctols = [float(eval(a)) for a in self.defaults["tools_ncctools"].split(",")]
                    ncctols[0] *= sfactor
                    ncctols[1] *= sfactor
                    self.defaults['tools_ncctools'] = "%.4f, %.4f" % (ncctols[0], ncctols[1])
                elif dim == 'tools_solderpaste_tools':
                    sp_tools = [float(eval(a)) for a in self.defaults["tools_solderpaste_tools"].split(",")]
                    sp_tools[0] *= sfactor
                    sp_tools[1] *= sfactor
                    self.defaults['tools_solderpaste_tools'] = "%.4f, %.4f" % (sp_tools[0], sp_tools[1])
                elif dim == 'tools_solderpaste_xy_toolchange':
                    sp_coords = [float(eval(a)) for a in self.defaults["tools_solderpaste_xy_toolchange"].split(",")]
                    sp_coords[0] *= sfactor
                    sp_coords[1] *= sfactor
                    self.defaults['tools_solderpaste_xy_toolchange'] = "%.4f, %.4f" % (sp_coords[0], sp_coords[1])
                else:
                    try:
                        self.defaults[dim] = float(self.defaults[dim]) * sfactor
                    except Exception as e:
                        log.debug('App.on_toggle_units().scale_defaults() --> %s' % str(e))

        # The scaling factor depending on choice of units.
        factor = 1/25.4
        if self.ui.general_defaults_form.general_app_group.units_radio.get_value().upper() == 'MM':
            factor = 25.4

        # Changing project units. Warn user.
        msgbox = QtWidgets.QMessageBox()
        msgbox.setWindowTitle("Toggle Units")
        msgbox.setWindowIcon(QtGui.QIcon('share/toggle_units32.png'))
        msgbox.setText("<B>Change project units ...</B>")
        msgbox.setInformativeText("Changing the units of the project causes all geometrical "
                                  "properties of all objects to be scaled accordingly.\nContinue?")
        msgbox.setStandardButtons(QtWidgets.QMessageBox.Cancel | QtWidgets.QMessageBox.Ok)
        msgbox.setDefaultButton(QtWidgets.QMessageBox.Ok)

        response = msgbox.exec_()

        if response == QtWidgets.QMessageBox.Ok:
            self.options_read_form()
            scale_options(factor)
            self.options_write_form()

            self.defaults_read_form()
            scale_defaults(factor)
            self.defaults_write_form()

            self.should_we_save = True

            # change this only if the workspace is active
            if self.defaults['global_workspace'] is True:
                self.plotcanvas.draw_workspace()

            # adjust the grid values on the main toolbar
            self.ui.grid_gap_x_entry.set_value(float(self.ui.grid_gap_x_entry.get_value()) * factor)
            self.ui.grid_gap_y_entry.set_value(float(self.ui.grid_gap_y_entry.get_value()) * factor)

            for obj in self.collection.get_list():
                units = self.ui.general_defaults_form.general_app_group.units_radio.get_value().upper()
                obj.convert_units(units)

                # make that the properties stored in the object are also updated
                self.object_changed.emit(obj)
                obj.build_ui()

            current = self.collection.get_active()
            if current is not None:
                # the transfer of converted values to the UI form for Geometry is done local in the FlatCAMObj.py
                if not isinstance(current, FlatCAMGeometry):
                    current.to_form()

            self.plot_all()
            self.inform.emit(_("[success]Converted units to %s") % self.defaults["units"])
            # self.ui.units_label.setText("[" + self.options["units"] + "]")
            self.set_screen_units(self.defaults["units"])
        else:
            # Undo toggling
            self.toggle_units_ignore = True
            if self.ui.general_defaults_form.general_app_group.units_radio.get_value().upper() == 'MM':
                self.ui.general_defaults_form.general_app_group.units_radio.set_value('IN')
            else:
                self.ui.general_defaults_form.general_app_group.units_radio.set_value('MM')
            self.toggle_units_ignore = False
            self.inform.emit(_("[WARNING_NOTCL]Units conversion cancelled."))

        self.options_read_form()
        self.defaults_read_form()

    def on_toggle_units_click(self):
        if self.options["units"] == 'MM':
            self.ui.general_defaults_form.general_app_group.units_radio.set_value("IN")
        else:
            self.ui.general_defaults_form.general_app_group.units_radio.set_value("MM")
        self.on_toggle_units()

    def on_fullscreen(self):
        self.report_usage("on_fullscreen()")

        if self.toggle_fscreen is False:
            if sys.platform == 'win32':
                self.ui.showFullScreen()
            for tb in self.ui.findChildren(QtWidgets.QToolBar):
                tb.setVisible(False)
            self.ui.splitter_left.setVisible(False)
            self.toggle_fscreen = True
        else:
            if sys.platform == 'win32':
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
        else:
            self.ui.splitter.setSizes([0, 1])

    def on_toggle_axis(self):
        self.report_usage("on_toggle_axis()")

        if self.toggle_axis is False:
            self.plotcanvas.v_line.set_data(color=(0.70, 0.3, 0.3, 1.0))
            self.plotcanvas.h_line.set_data(color=(0.70, 0.3, 0.3, 1.0))
            self.plotcanvas.redraw()
            self.toggle_axis = True
        else:
            self.plotcanvas.v_line.set_data(color=(0.0, 0.0, 0.0, 0.0))

            self.plotcanvas.h_line.set_data(color=(0.0, 0.0, 0.0, 0.0))
            self.plotcanvas.redraw()
            self.toggle_axis = False

    def on_toggle_grid(self):
        self.report_usage("on_toggle_grid()")

        self.ui.grid_snap_btn.trigger()

    def on_options_combo_change(self, sel):
        """
        Called when the combo box to choose between application defaults and
        project option changes value. The corresponding variables are
        copied to the UI.

        :param sel: The option index that was chosen.
        :return: None
        """

        # combo_sel = self.ui.notebook.combo_options.get_active()
        App.log.debug("Options --> %s" % sel)

        # form = [self.defaults_form, self.options_form][sel]
        # self.ui.notebook.options_contents.pack_start(form, False, False, 1)

        if sel == 0:
            self.gen_form = self.ui.general_defaults_form
            self.ger_form = self.ui.gerber_defaults_form
            self.exc_form = self.ui.excellon_defaults_form
            self.geo_form = self.ui.geometry_defaults_form
            self.cnc_form = self.ui.cncjob_defaults_form
            self.tools_form = self.ui.tools_defaults_form
        elif sel == 1:
            self.gen_form = self.ui.general_options_form
            self.ger_form = self.ui.gerber_options_form
            self.exc_form = self.ui.excellon_options_form
            self.geo_form = self.ui.geometry_options_form
            self.cnc_form = self.ui.cncjob_options_form
            self.tools_form = self.ui.tools_options_form
        else:
            return

        try:
            self.ui.general_scroll_area.takeWidget()
        except:
            self.log.debug("Nothing to remove")
        self.ui.general_scroll_area.setWidget(self.gen_form)
        self.gen_form.show()

        try:
            self.ui.gerber_scroll_area.takeWidget()
        except:
            self.log.debug("Nothing to remove")
        self.ui.gerber_scroll_area.setWidget(self.ger_form)
        self.ger_form.show()

        try:
            self.ui.excellon_scroll_area.takeWidget()
        except:
            self.log.debug("Nothing to remove")
        self.ui.excellon_scroll_area.setWidget(self.exc_form)
        self.exc_form.show()

        try:
            self.ui.geometry_scroll_area.takeWidget()
        except:
            self.log.debug("Nothing to remove")
        self.ui.geometry_scroll_area.setWidget(self.geo_form)
        self.geo_form.show()

        try:
            self.ui.cncjob_scroll_area.takeWidget()
        except:
            self.log.debug("Nothing to remove")
        self.ui.cncjob_scroll_area.setWidget(self.cnc_form)
        self.cnc_form.show()

        try:
            self.ui.tools_scroll_area.takeWidget()
        except:
            self.log.debug("Nothing to remove")
        self.ui.tools_scroll_area.setWidget(self.tools_form)
        self.tools_form.show()

        self.log.debug("Finished GUI form initialization.")

        # self.options2form()

    def on_excellon_defaults_button(self):
        self.defaults_form_fields["excellon_format_lower_in"].set_value('4')
        self.defaults_form_fields["excellon_format_upper_in"].set_value('2')
        self.defaults_form_fields["excellon_format_lower_mm"].set_value('3')
        self.defaults_form_fields["excellon_format_upper_mm"].set_value('3')
        self.defaults_form_fields["excellon_zeros"].set_value('L')
        self.defaults_form_fields["excellon_units"].set_value('INCH')
        log.debug("Excellon app defaults loaded ...")

    def on_excellon_options_button(self):

        self.options_form_fields["excellon_format_lower_in"].set_value('4')
        self.options_form_fields["excellon_format_upper_in"].set_value('2')
        self.options_form_fields["excellon_format_lower_mm"].set_value('3')
        self.options_form_fields["excellon_format_upper_mm"].set_value('3')
        self.options_form_fields["excellon_zeros"].set_value('L')
        self.options_form_fields["excellon_units"].set_value('INCH')
        log.debug("Excellon options defaults loaded ...")

    # Setting plot colors handlers
    def on_pf_color_entry(self):
        self.defaults['global_plot_fill'] = self.ui.general_defaults_form.general_gui_group.pf_color_entry.get_value()[:7] + \
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
        self.defaults['global_plot_fill'] = self.defaults['global_plot_fill'][:7] + \
                                            (hex(spinner_value)[2:] if int(hex(spinner_value)[2:], 16) > 0 else '00')
        self.defaults['global_plot_line'] = self.defaults['global_plot_line'][:7] + \
                                            (hex(spinner_value)[2:] if int(hex(spinner_value)[2:], 16) > 0 else '00')

    def on_pf_color_slider(self):
        slider_value = self.ui.general_defaults_form.general_gui_group.pf_color_alpha_slider.value()
        self.ui.general_defaults_form.general_gui_group.pf_color_alpha_spinner.setValue(slider_value)

    def on_pl_color_entry(self):
        self.defaults['global_plot_line'] = self.ui.general_defaults_form.general_gui_group.pl_color_entry.get_value()[:7] + \
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
        self.defaults['global_sel_fill'] = self.ui.general_defaults_form.general_gui_group.sf_color_entry.get_value()[:7] + \
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
        self.defaults['global_sel_fill'] = self.defaults['global_sel_fill'][:7] + \
                                            (hex(spinner_value)[2:] if int(hex(spinner_value)[2:], 16) > 0 else '00')
        self.defaults['global_sel_line'] = self.defaults['global_sel_line'][:7] + \
                                            (hex(spinner_value)[2:] if int(hex(spinner_value)[2:], 16) > 0 else '00')

    def on_sf_color_slider(self):
        slider_value = self.ui.general_defaults_form.general_gui_group.sf_color_alpha_slider.value()
        self.ui.general_defaults_form.general_gui_group.sf_color_alpha_spinner.setValue(slider_value)

    def on_sl_color_entry(self):
        self.defaults['global_sel_line'] = self.ui.general_defaults_form.general_gui_group.sl_color_entry.get_value()[:7] + \
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
        self.defaults['global_alt_sel_fill'] = self.defaults['global_alt_sel_fill'][:7] + \
                                            (hex(spinner_value)[2:] if int(hex(spinner_value)[2:], 16) > 0 else '00')
        self.defaults['global_alt_sel_line'] = self.defaults['global_alt_sel_line'][:7] + \
                                            (hex(spinner_value)[2:] if int(hex(spinner_value)[2:], 16) > 0 else '00')

    def on_alt_sf_color_slider(self):
        slider_value = self.ui.general_defaults_form.general_gui_group.alt_sf_color_alpha_slider.value()
        self.ui.general_defaults_form.general_gui_group.alt_sf_color_alpha_spinner.setValue(slider_value)

    def on_alt_sl_color_entry(self):
        self.defaults['global_alt_sel_line'] = self.ui.general_defaults_form.general_gui_group \
                                   .alt_sl_color_entry.get_value()[:7] + self.defaults['global_alt_sel_line'][7:9]
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

    def on_deselect_all(self):
        self.collection.set_all_inactive()
        self.delete_selection_shape()

    def on_workspace_modified(self):
        self.save_defaults(silent=True)
        self.plotcanvas.draw_workspace()

    def on_workspace(self):
        self.report_usage("on_workspace()")

        if self.ui.general_defaults_form.general_gui_group.workspace_cb.isChecked():
            self.plotcanvas.restore_workspace()
        else:
            self.plotcanvas.delete_workspace()

        self.save_defaults(silent=True)

    def on_workspace_menu(self):
        if self.ui.general_defaults_form.general_gui_group.workspace_cb.isChecked():
            self.ui.general_defaults_form.general_gui_group.workspace_cb.setChecked(False)
        else:
            self.ui.general_defaults_form.general_gui_group.workspace_cb.setChecked(True)
        self.on_workspace()

    def on_layout(self, index, lay=None):
        self.report_usage("on_layout()")
        if lay:
            current_layout = lay
        else:
            current_layout = self.ui.general_defaults_form.general_gui_set_group.layout_combo.get_value()

        settings = QSettings("Open Source", "FlatCAM")
        settings.setValue('layout', current_layout)

        # This will write the setting to the platform specific storage.
        del settings

        # first remove the toolbars:
        try:
            self.ui.removeToolBar(self.ui.toolbarfile)
            self.ui.removeToolBar(self.ui.toolbargeo)
            self.ui.removeToolBar(self.ui.toolbarview)
            self.ui.removeToolBar(self.ui.toolbarshell)
            self.ui.removeToolBar(self.ui.toolbartools)
            self.ui.removeToolBar(self.ui.exc_edit_toolbar)
            self.ui.removeToolBar(self.ui.geo_edit_toolbar)
            self.ui.removeToolBar(self.ui.snap_toolbar)
            self.ui.removeToolBar(self.ui.toolbarshell)
        except:
            pass

        if current_layout == 'Standard':
            ### TOOLBAR INSTALLATION ###
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
            self.ui.exc_edit_toolbar.setVisible(False)
            self.ui.exc_edit_toolbar.setObjectName('ExcEditor_TB')
            self.ui.addToolBar(self.ui.exc_edit_toolbar)

            self.ui.geo_edit_toolbar = QtWidgets.QToolBar('Geometry Editor Toolbar')
            self.ui.geo_edit_toolbar.setVisible(False)
            self.ui.geo_edit_toolbar.setObjectName('GeoEditor_TB')
            self.ui.addToolBar(self.ui.geo_edit_toolbar)

            self.ui.snap_toolbar = QtWidgets.QToolBar('Grid Toolbar')
            self.ui.snap_toolbar.setObjectName('Snap_TB')
            # self.ui.snap_toolbar.setMaximumHeight(30)
            self.ui.addToolBar(self.ui.snap_toolbar)

            self.ui.corner_snap_btn.setVisible(False)
            self.ui.snap_magnet.setVisible(False)
        elif current_layout == 'Compact':
            ### TOOLBAR INSTALLATION ###
            self.ui.toolbarfile = QtWidgets.QToolBar('File Toolbar')
            self.ui.toolbarfile.setObjectName('File_TB')
            self.ui.addToolBar(Qt.LeftToolBarArea, self.ui.toolbarfile)
            self.ui.toolbargeo = QtWidgets.QToolBar('Edit Toolbar')
            self.ui.toolbargeo.setObjectName('Edit_TB')
            self.ui.addToolBar(Qt.LeftToolBarArea, self.ui.toolbargeo)
            self.ui.toolbarview = QtWidgets.QToolBar('View Toolbar')
            self.ui.toolbarview.setObjectName('View_TB')
            self.ui.addToolBar(Qt.LeftToolBarArea, self.ui.toolbarview)

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

    def on_cnc_custom_parameters(self, signal_text):
        if signal_text == 'Parameters':
            return
        else:
            self.ui.cncjob_defaults_form.cncjob_adv_opt_group.toolchange_text.insertPlainText('%%%s%%' % signal_text)

    def on_save_button(self):
        self.save_defaults(silent=False)
        # load the defaults so they are updated into the app
        self.load_defaults(filename='current_defaults')
        # Re-fresh project options
        self.on_options_app2project()

    def handlePrint(self):
        self.report_usage("handlePrint()")

        dialog = QtPrintSupport.QPrintDialog()
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.ui.code_editor.document().print_(dialog.printer())

    def handlePreview(self):
        self.report_usage("handlePreview()")

        dialog = QtPrintSupport.QPrintPreviewDialog()
        dialog.paintRequested.connect(self.ui.code_editor.print_)
        dialog.exec_()

    def handleTextChanged(self):
        # enable = not self.ui.code_editor.document().isEmpty()
        # self.ui.buttonPrint.setEnabled(enable)
        # self.ui.buttonPreview.setEnabled(enable)
        pass

    def handleOpen(self, filt=None):
        self.report_usage("handleOpen()")

        if filt:
            _filter_ = filt
        else:
            _filter_ = "G-Code Files (*.nc);; G-Code Files (*.txt);; G-Code Files (*.tap);; G-Code Files (*.cnc);; " \
                       "All Files (*.*)"

        path, _f = QtWidgets.QFileDialog.getOpenFileName(
            caption=_('Open file'), directory=self.get_last_folder(), filter=_filter_)

        if path:
            file = QtCore.QFile(path)
            if file.open(QtCore.QIODevice.ReadOnly):
                stream = QtCore.QTextStream(file)
                self.gcode_edited = stream.readAll()
                self.ui.code_editor.setPlainText(self.gcode_edited)
                file.close()

    def handleSaveGCode(self,name=None, filt=None):
        self.report_usage("handleSaveGCode()")

        if filt:
            _filter_ = filt
        else:
            _filter_ = "G-Code Files (*.nc);; G-Code Files (*.txt);; G-Code Files (*.tap);; G-Code Files (*.cnc);; " \
                       "All Files (*.*)"

        if name:
            obj_name = name
        else:
            try:
                obj_name = self.collection.get_active().options['name']
            except AttributeError:
                obj_name = 'file'
                if filt is None:
                    _filter_ = "FlatConfig Files (*.FlatConfig);;All Files (*.*)"

        try:
            filename = str(QtWidgets.QFileDialog.getSaveFileName(
                caption=_("Export G-Code ..."),
                directory=self.defaults["global_last_folder"] + '/' + str(obj_name),
                filter=_filter_
            )[0])
        except TypeError:
            filename = str(QtWidgets.QFileDialog.getSaveFileName(caption=_("Export G-Code ..."), filter=_filter_)[0])

        if filename == "":
            self.inform.emit(_("[WARNING_NOTCL]Export Code cancelled."))
            return
        else:
            try:
                my_gcode = self.ui.code_editor.toPlainText()
                with open(filename, 'w') as f:
                    for line in my_gcode:
                        f.write(line)

            except FileNotFoundError:
                self.inform.emit(_("[WARNING] No such file or directory"))
                return

        # Just for adding it to the recent files list.
        self.file_opened.emit("cncjob", filename)

        self.file_saved.emit("cncjob", filename)
        self.inform.emit(_("Saved to: %s") % filename)

    def handleFindGCode(self):
        self.report_usage("handleFindGCode()")

        flags = QtGui.QTextDocument.FindCaseSensitively
        text_to_be_found = self.ui.entryFind.get_value()

        r = self.ui.code_editor.find(str(text_to_be_found), flags)
        if r is False:
            self.ui.code_editor.moveCursor(QtGui.QTextCursor.Start)

    def handleReplaceGCode(self):
        self.report_usage("handleReplaceGCode()")

        old = self.ui.entryFind.get_value()
        new = self.ui.entryReplace.get_value()

        if self.ui.sel_all_cb.isChecked():
            while True:
                cursor = self.ui.code_editor.textCursor()
                cursor.beginEditBlock()
                flags = QtGui.QTextDocument.FindCaseSensitively
                # self.ui.editor is the QPlainTextEdit
                r = self.ui.code_editor.find(str(old), flags)
                if r:
                    qc = self.ui.code_editor.textCursor()
                    if qc.hasSelection():
                        qc.insertText(new)
                else:
                    self.ui.code_editor.moveCursor(QtGui.QTextCursor.Start)
                    break
            # Mark end of undo block
            cursor.endEditBlock()
        else:
            cursor = self.ui.code_editor.textCursor()
            cursor.beginEditBlock()
            qc = self.ui.code_editor.textCursor()
            if qc.hasSelection():
                qc.insertText(new)
            # Mark end of undo block
            cursor.endEditBlock()

    def on_tool_add_keypress(self):
        ## Current application units in Upper Case
        self.units = self.ui.general_defaults_form.general_app_group.units_radio.get_value().upper()

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
                            self.inform.emit(
                                _("[WARNING_NOTCL] Please enter a tool diameter with non-zero value, in Float format."))
                            return
                        self.collection.get_active().on_tool_add(dia=float(val))
                    else:
                        self.inform.emit(
                            _("[WARNING_NOTCL] Adding Tool cancelled ..."))
                else:
                    msgbox = QtWidgets.QMessageBox()
                    msgbox.setText(_("Adding Tool works only when Advanced is checked.\n"
                                   "Go to Preferences -> General - Show Advanced Options."))
                    msgbox.setWindowTitle("Tool adding ...")
                    msgbox.setWindowIcon(QtGui.QIcon('share/warning.png'))
                    msgbox.setStandardButtons(QtWidgets.QMessageBox.Ok)
                    msgbox.setDefaultButton(QtWidgets.QMessageBox.Ok)
                    msgbox.exec_()

        # work only if the notebook tab on focus is the Tools_Tab
        if notebook_widget_name == 'tool_tab':
            tool_widget = self.ui.tool_scroll_area.widget().objectName()

            tool_add_popup = FCInputDialog(title="New Tool ...",
                                           text='Enter a Tool Diameter:',
                                           min=0.0000, max=99.9999, decimals=4)
            tool_add_popup.setWindowIcon(QtGui.QIcon('share/letter_t_32.png'))

            val, ok = tool_add_popup.get_value()

            # and only if the tool is NCC Tool
            if tool_widget == self.ncclear_tool.toolName:
                if ok:
                    if float(val) == 0:
                        self.inform.emit(
                            _("[WARNING_NOTCL] Please enter a tool diameter with non-zero value, in Float format."))
                        return
                    self.ncclear_tool.on_tool_add(dia=float(val))
                else:
                    self.inform.emit(
                        _("[WARNING_NOTCL] Adding Tool cancelled ..."))
            # and only if the tool is Paint Area Tool
            elif tool_widget == self.paint_tool.toolName:
                if ok:
                    if float(val) == 0:
                        self.inform.emit(
                            _("[WARNING_NOTCL] Please enter a tool diameter with non-zero value, in Float format."))
                        return
                    self.paint_tool.on_tool_add(dia=float(val))
                else:
                    self.inform.emit(
                        _("[WARNING_NOTCL] Adding Tool cancelled ..."))
            # and only if the tool is Solder Paste Dispensing Tool
            elif tool_widget == self.paste_tool.toolName:
                if ok:
                    if float(val) == 0:
                        self.inform.emit(
                            _("[WARNING_NOTCL] Please enter a tool diameter with non-zero value, in Float format."))
                        return
                    self.paste_tool.on_tool_add(dia=float(val))
                else:
                    self.inform.emit(
                        _("[WARNING_NOTCL] Adding Tool cancelled ..."))


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

        # Make sure that the deletion will happen only after the Editor is no longer active otherwise we might delete
        # a geometry object before we update it.
        if self.geo_editor.editor_active is False and self.exc_editor.editor_active is False:
            if self.collection.get_active():
                self.log.debug("on_delete()")
                self.report_usage("on_delete")

                while (self.collection.get_active()):
                    self.delete_first_selected()

                self.inform.emit(_("Object(s) deleted ..."))
                # make sure that the selection shape is deleted, too
                self.delete_selection_shape()
            else:
                self.inform.emit(_("Failed. No object(s) selected..."))
        else:
            self.inform.emit(_("Save the work in Editor and try again ..."))

    def on_set_origin(self):
        """
        Set the origin to the left mouse click position

        :return: None
        """

        #display the message for the user
        #and ask him to click on the desired position
        self.report_usage("on_set_origin()")

        self.inform.emit(_('Click to set the origin ...'))

        self.plotcanvas.vis_connect('mouse_press', self.on_set_zero_click)

    def on_jump_to(self):
        """
        Jump to a location by setting the mouse cursor location
        :return:

        """
        self.report_usage("on_jump_to()")

        dia_box = Dialog_box(title=_("Jump to ..."),
                             label=_("Enter the coordinates in format X,Y:"),
                             icon=QtGui.QIcon('share/jump_to16.png'))

        if dia_box.ok is True:
            try:
                location = eval(dia_box.location)
                if not isinstance(location, tuple):
                    self.inform.emit(_("Wrong coordinates. Enter coordinates in format: X,Y"))
                    return
            except:
                return
        else:
            return

        self.plotcanvas.fit_center(loc=location)

        cursor = QtGui.QCursor()

        canvas_origin = self.plotcanvas.vispy_canvas.native.mapToGlobal(QtCore.QPoint(0, 0))
        jump_loc = self.plotcanvas.vispy_canvas.translate_coords_2((location[0], location[1]))

        cursor.setPos(canvas_origin.x() + jump_loc[0], (canvas_origin.y() + jump_loc[1]))
        self.inform.emit(_("Done."))

    def on_copy_object(self):
        self.report_usage("on_copy_object()")

        def initialize(obj_init, app):
            obj_init.solid_geometry = obj.solid_geometry
            try:
                if obj.tools:
                    obj_init.tools = obj.tools
            except Exception as e:
                log.debug("on_copy_object() --> %s" % str(e))

        def initialize_excellon(obj_init, app):
            obj_init.tools = obj.tools

            # drills are offset, so they need to be deep copied
            obj_init.drills = deepcopy(obj.drills)
            # slots are offset, so they need to be deep copied
            obj_init.slots = deepcopy(obj.slots)
            obj_init.create_geometry()

        for obj in self.collection.get_selected():

            obj_name = obj.options["name"]

            try:
                if isinstance(obj, FlatCAMExcellon):
                    self.new_object("excellon", str(obj_name) + "_copy", initialize_excellon)
                elif isinstance(obj,FlatCAMGerber):
                    self.new_object("gerber", str(obj_name) + "_copy", initialize)
                elif isinstance(obj,FlatCAMGeometry):
                    self.new_object("geometry", str(obj_name) + "_copy", initialize)
            except Exception as e:
                return "Operation failed: %s" % str(e)

    def on_copy_object2(self, custom_name):

        def initialize_geometry(obj_init, app):
            obj_init.solid_geometry = obj.solid_geometry
            try:
                if obj.tools:
                    obj_init.tools = obj.tools
            except Exception as e:
                log.debug("on_copy_object2() --> %s" % str(e))

        def initialize_gerber(obj_init, app):
            obj_init.solid_geometry = obj.solid_geometry
            obj_init.apertures = deepcopy(obj.apertures)
            obj_init.aperture_macros = deepcopy(obj.aperture_macros)

        def initialize_excellon(obj_init, app):
            obj_init.tools = obj.tools
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
                elif isinstance(obj,FlatCAMGerber):
                    self.new_object("gerber", str(obj_name) + custom_name, initialize_gerber)
                elif isinstance(obj,FlatCAMGeometry):
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
                except:
                    log.warning("Could not rename the object in the list")

    def on_copy_object_as_geometry(self):
        self.report_usage("on_copy_object_as_geometry()")

        def initialize(obj_init, app):
            obj_init.solid_geometry = obj.solid_geometry
            if obj.tools:
                obj_init.tools = obj.tools

        def initialize_excellon(obj, app):
            objs = self.collection.get_selected()
            FlatCAMGeometry.merge(objs, obj)

        for obj in self.collection.get_selected():

            obj_name = obj.options["name"]

            try:
                if isinstance(obj, FlatCAMExcellon):
                    self.new_object("geometry", str(obj_name) + "_gcopy", initialize_excellon)
                else:
                    self.new_object("geometry", str(obj_name) + "_gcopy", initialize)

            except Exception as e:
                return "Operation failed: %s" % str(e)

    def on_set_zero_click(self, event):
        #this function will be available only for mouse left click
        pos =[]
        pos_canvas = self.plotcanvas.vispy_canvas.translate_coords(event.pos)
        if event.button == 1:
            if self.grid_status() == True:
                pos = self.geo_editor.snap(pos_canvas[0], pos_canvas[1])
            else:
                pos = pos_canvas

            x = 0 - pos[0]
            y = 0 - pos[1]
            for obj in self.collection.get_list():
                obj.offset((x,y))
                self.object_changed.emit(obj)
                obj.plot()
                # Update the object bounding box options
                a, b, c, d = obj.bounds()
                obj.options['xmin'] = a
                obj.options['ymin'] = b
                obj.options['xmax'] = c
                obj.options['ymax'] = d
            # self.plot_all(zoom=False)
            self.inform.emit(_('[success] Origin set ...'))
            self.plotcanvas.vis_disconnect('mouse_press', self.on_set_zero_click)
            self.should_we_save = True

    def on_selectall(self):
        self.report_usage("on_selectall()")

        # delete the possible selection box around a possible selected object
        self.delete_selection_shape()
        for name in self.collection.get_names():
            self.collection.set_active(name)
            curr_sel_obj = self.collection.get_by_name(name)
            # create the selection box around the selected object
            self.draw_selection_shape(curr_sel_obj)

    def on_preferences(self):

        # add the tab if it was closed
        self.ui.plot_tab_area.addTab(self.ui.preferences_tab, _("Preferences"))

        # delete the absolute and relative position and messages in the infobar
        self.ui.position_label.setText("")
        self.ui.rel_position_label.setText("")

        # Switch plot_area to preferences page
        self.ui.plot_tab_area.setCurrentWidget(self.ui.preferences_tab)
        self.ui.show()

    def on_flipy(self):
        self.report_usage("on_flipy()")

        obj_list = self.collection.get_selected()
        xminlist = []
        yminlist = []
        xmaxlist = []
        ymaxlist = []

        if not obj_list:
            self.inform.emit(_("[WARNING_NOTCL] No object selected to Flip on Y axis."))
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
                self.inform.emit(_("[success] Flip on Y axis done."))
            except Exception as e:
                self.inform.emit(_("[ERROR_NOTCL] Due of %s, Flip action was not executed.") % str(e))
                return

    def on_flipx(self):
        self.report_usage("on_flipx()")

        obj_list = self.collection.get_selected()
        xminlist = []
        yminlist = []
        xmaxlist = []
        ymaxlist = []

        if not obj_list:
            self.inform.emit(_("[WARNING_NOTCL] No object selected to Flip on X axis."))
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
                self.inform.emit(_("[success] Flip on X axis done."))
            except Exception as e:
                self.inform.emit(_("[ERROR_NOTCL] Due of %s, Flip action was not executed.") % str(e))
                return

    def on_rotate(self, silent=False, preset=None):
        self.report_usage("on_rotate()")

        obj_list = self.collection.get_selected()
        xminlist = []
        yminlist = []
        xmaxlist = []
        ymaxlist = []

        if not obj_list:
            self.inform.emit(_("[WARNING_NOTCL] No object selected to Rotate."))
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
                    self.inform.emit(_("[success] Rotation done."))
                except Exception as e:
                    self.inform.emit(_("[ERROR_NOTCL] Due of %s, rotation movement was not executed.") % str(e))
                    return

    def on_skewx(self):
        self.report_usage("on_skewx()")

        obj_list = self.collection.get_selected()
        xminlist = []
        yminlist = []

        if not obj_list:
            self.inform.emit(_("[WARNING_NOTCL] No object selected to Skew/Shear on X axis."))
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
                self.inform.emit(_("[success] Skew on X axis done."))

    def on_skewy(self):
        self.report_usage("on_skewy()")

        obj_list = self.collection.get_selected()
        xminlist = []
        yminlist = []

        if not obj_list:
            self.inform.emit(_("[WARNING_NOTCL] No object selected to Skew/Shear on Y axis."))
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
                self.inform.emit(_("[success] Skew on Y axis done."))

    def delete_first_selected(self):
        # Keep this for later
        try:
            name = self.collection.get_active().options["name"]
        except AttributeError:
            self.log.debug("Nothing selected for deletion")
            return

        # Remove plot
        # self.plotcanvas.figure.delaxes(self.collection.get_active().axes)
        # self.plotcanvas.auto_adjust_axes()

        # Clear form
        self.setup_component_editor()

        # Remove from dictionary
        self.collection.delete_active()

        self.inform.emit("Object deleted: %s" % name)

    def on_plots_updated(self):
        """
        Callback used to report when the plots have changed.
        Adjust axes and zooms to fit.

        :return: None
        """
        # self.plotcanvas.auto_adjust_axes()
        self.plotcanvas.vispy_canvas.update()           # TODO: Need update canvas?
        self.on_zoom_fit(None)

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

    def grid_status(self):
        if self.ui.grid_snap_btn.isChecked():
            return 1
        else:
            return 0

    def populate_cmenu_grids(self):
        units = self.ui.general_defaults_form.general_app_group.units_radio.get_value().lower()

        self.ui.cmenu_gridmenu.clear()
        sorted_list = sorted(self.defaults["global_grid_context_menu"][str(units)])

        for grid in sorted_list:
            action = self.ui.cmenu_gridmenu.addAction(QtGui.QIcon('share/grid32_menu.png'), "%s" % str(grid))
            action.triggered.connect(self.set_grid)

        self.ui.cmenu_gridmenu.addSeparator()
        grid_add = self.ui.cmenu_gridmenu.addAction(QtGui.QIcon('share/plus32.png'), "Add")
        grid_add.triggered.connect(self.on_grid_add)
        grid_delete = self.ui.cmenu_gridmenu.addAction(QtGui.QIcon('share/delete32.png'), "Delete")
        grid_delete.triggered.connect(self.on_grid_delete)

    def set_grid(self):
        self.ui.grid_gap_x_entry.setText(self.sender().text())
        self.ui.grid_gap_y_entry.setText(self.sender().text())

    def on_grid_add(self):
        ## Current application units in lower Case
        units = self.ui.general_defaults_form.general_app_group.units_radio.get_value().lower()

        grid_add_popup = FCInputDialog(title="New Grid ...",
                                       text='Enter a Grid VAlue:',
                                       min=0.0000, max=99.9999, decimals=4)
        grid_add_popup.setWindowIcon(QtGui.QIcon('share/plus32.png'))

        val, ok = grid_add_popup.get_value()
        if ok:
            if float(val) == 0:
                self.inform.emit(
                    _("[WARNING_NOTCL] Please enter a grid value with non-zero value, in Float format."))
                return
            else:
                if val not in self.defaults["global_grid_context_menu"][str(units)]:
                    self.defaults["global_grid_context_menu"][str(units)].append(val)
                    self.inform.emit(
                        _("[success] New Grid added ..."))
                else:
                    self.inform.emit(
                        _("[WARNING_NOTCL] Grid already exists ..."))
        else:
            self.inform.emit(
                _("[WARNING_NOTCL] Adding New Grid cancelled ..."))

    def on_grid_delete(self):
        ## Current application units in lower Case
        units = self.ui.general_defaults_form.general_app_group.units_radio.get_value().lower()

        grid_del_popup = FCInputDialog(title="Delete Grid ...",
                                       text='Enter a Grid Value:',
                                       min=0.0000, max=99.9999, decimals=4)
        grid_del_popup.setWindowIcon(QtGui.QIcon('share/delete32.png'))

        val, ok = grid_del_popup.get_value()
        if ok:
            if float(val) == 0:
                self.inform.emit(
                    _("[WARNING_NOTCL] Please enter a grid value with non-zero value, in Float format."))
                return
            else:
                try:
                    self.defaults["global_grid_context_menu"][str(units)].remove(val)
                except ValueError:
                    self.inform.emit(
                        _("[ERROR_NOTCL] Grid Value does not exist ..."))
                    return
                self.inform.emit(
                    _("[success] Grid Value deleted ..."))
        else:
            self.inform.emit(
                _("[WARNING_NOTCL] Delete Grid value cancelled ..."))

    def on_shortcut_list(self):
        self.report_usage("on_shortcut_list()")

        # add the tab if it was closed
        self.ui.plot_tab_area.addTab(self.ui.shortcuts_tab, "Key Shortcut List")

        # delete the absolute and relative position and messages in the infobar
        self.ui.position_label.setText("")
        self.ui.rel_position_label.setText("")

        # Switch plot_area to preferences page
        self.ui.plot_tab_area.setCurrentWidget(self.ui.shortcuts_tab)
        self.ui.show()

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
            self.inform.emit(_("[WARNING_NOTCL]No object selected to copy it's name"))
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

        # So it can receive key presses
        self.plotcanvas.vispy_canvas.native.setFocus()
        # Set the mouse button for panning
        self.plotcanvas.vispy_canvas.view.camera.pan_button_setting = self.defaults['global_pan_button']

        self.pos_canvas = self.plotcanvas.vispy_canvas.translate_coords(event.pos)

        if self.grid_status() == True:
            self.pos = self.geo_editor.snap(self.pos_canvas[0], self.pos_canvas[1])
            self.app_cursor.enabled = True
        else:
            self.pos = (self.pos_canvas[0], self.pos_canvas[1])
            self.app_cursor.enabled = False

        try:
            modifiers = QtWidgets.QApplication.keyboardModifiers()

            if event.button == 1:
                # Reset here the relative coordinates so there is a new reference on the click position
                if self.rel_point1 is None:
                    self.rel_point1 = self.pos
                else:
                    self.rel_point2 = copy(self.rel_point1)
                    self.rel_point1 = self.pos

                # If the SHIFT key is pressed when LMB is clicked then the coordinates are copied to clipboard
                if modifiers == QtCore.Qt.ShiftModifier:
                    # do not auto open the Project Tab
                    self.click_noproject = True

                    self.clipboard.setText(self.defaults["global_point_clipboard_format"] % (self.pos[0], self.pos[1]))
                    return

            self.on_mouse_move_over_plot(event, origin_click=True)
        except Exception as e:
            App.log.debug("App.on_mouse_click_over_plot() --> Outside plot? --> %s" % str(e))

    def on_double_click_over_plot(self, event):
        self.doubleclick = True

    def on_mouse_move_over_plot(self, event, origin_click=None):
        """
        Callback for the mouse motion event over the plot. This event is generated
        by the Matplotlib backend and has been registered in ``self.__init__()``.
        For details, see: http://matplotlib.org/users/event_handling.html

        :param event: Contains information about the event.
        :param origin_click
        :return: None
        """

        # So it can receive key presses
        self.plotcanvas.vispy_canvas.native.setFocus()
        self.pos_jump = event.pos

        if origin_click is True:
            pass
        else:
            # if the RMB is clicked and mouse is moving over plot then 'panning_action' is True
            if event.button == 2:
                self.panning_action = True
                return
            else:
                self.panning_action = False

        if self.rel_point1 is not None:
            try:  # May fail in case mouse not within axes
                pos_canvas = self.plotcanvas.vispy_canvas.translate_coords(event.pos)
                if self.grid_status():
                    pos = self.geo_editor.snap(pos_canvas[0], pos_canvas[1])
                    self.app_cursor.enabled = True
                    # Update cursor
                    self.app_cursor.set_data(np.asarray([(pos[0], pos[1])]), symbol='++', edge_color='black', size=20)
                else:
                    pos = (pos_canvas[0], pos_canvas[1])
                    self.app_cursor.enabled = False

                self.ui.position_label.setText("&nbsp;&nbsp;&nbsp;&nbsp;<b>X</b>: %.4f&nbsp;&nbsp;   "
                                               "<b>Y</b>: %.4f" % (pos[0], pos[1]))

                dx = pos[0] - self.rel_point1[0]
                dy = pos[1] - self.rel_point1[1]
                self.ui.rel_position_label.setText("<b>Dx</b>: %.4f&nbsp;&nbsp;  <b>Dy</b>: "
                                                   "%.4f&nbsp;&nbsp;&nbsp;&nbsp;" % (dx, dy))
                self.mouse = [pos[0], pos[1]]

                # if the mouse is moved and the LMB is clicked then the action is a selection
                if event.is_dragging == 1 and event.button == 1:
                    self.delete_selection_shape()
                    if dx < 0:
                        self.draw_moving_selection_shape(self.pos, pos, color=self.defaults['global_alt_sel_line'],
                                                     face_color=self.defaults['global_alt_sel_fill'])
                        self.selection_type = False
                    else:
                        self.draw_moving_selection_shape(self.pos, pos)
                        self.selection_type = True

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
                                            self.draw_hover_shape(obj, color='#d1e0e0')
                                    else:
                                        if obj.notHovering is True:
                                            obj.notHovering = False
                                            obj.isHovering = False
                                            self.delete_hover_shape()
                        except:
                            # the Exception here will happen if we try to select on screen and we have an
                            # newly (and empty) just created Geometry or Excellon object that do not have the
                            # xmin, xmax, ymin, ymax options.
                            # In this case poly_obj creation (see above) will fail
                            pass

            except:
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

        pos_canvas = self.plotcanvas.vispy_canvas.translate_coords(event.pos)
        if self.grid_status():
            pos = self.geo_editor.snap(pos_canvas[0], pos_canvas[1])
        else:
            pos = (pos_canvas[0], pos_canvas[1])

        # if the released mouse button was RMB then test if it was a panning motion or not, if not it was a context
        # canvas menu
        try:
            if event.button == 2:  # right click
                if self.panning_action is True:
                    self.panning_action = False
                else:
                    self.cursor = QtGui.QCursor()
                    self.populate_cmenu_grids()
                    self.ui.popMenu.popup(self.cursor.pos())
        except Exception as e:
            log.warning("Error: %s" % str(e))
            return

        # if the released mouse button was LMB then test if we had a right-to-left selection or a left-to-right
        # selection and then select a type of selection ("enclosing" or "touching")
        try:
            if event.button == 1:  # left click
                if self.doubleclick is True:
                    self.doubleclick = False
                    if self.collection.get_selected():
                        self.ui.notebook.setCurrentWidget(self.ui.selected_tab)
                        if self.ui.splitter.sizes()[0] == 0:
                            self.ui.splitter.setSizes([1, 1])

                        # delete the selection shape(S) as it may be in the way
                        self.delete_selection_shape()
                        self.delete_hover_shape()

                else:
                    if self.selection_type is not None:
                        self.selection_area_handler(self.pos, pos, self.selection_type)
                        self.selection_type = None
                    else:
                        modifiers = QtWidgets.QApplication.keyboardModifiers()

                        # If the CTRL key is pressed when the LMB is clicked then if the object is selected it will deselect,
                        # and if it's not selected then it will be selected
                        if modifiers == QtCore.Qt.ControlModifier:
                            # If there is no active command (self.command_active is None) then we check if we clicked on
                            # a object by checking the bounding limits against mouse click position
                            if self.command_active is None:
                                self.select_objects(key='CTRL')
                                self.delete_hover_shape()
                        else:
                            # If there is no active command (self.command_active is None) then we check if we clicked on a object by
                            # checking the bounding limits against mouse click position
                            if self.command_active is None:
                                self.select_objects()
                                self.delete_hover_shape()

        except Exception as e:
            log.warning("Error: %s" % str(e))
            return

    def selection_area_handler(self, start_pos, end_pos, sel_type):
        """
        :param start_pos: mouse position when the selection LMB click was done
        :param end_pos: mouse position when the left mouse button is released
        :param sel_type: if True it's a left to right selection (enclosure), if False it's a 'touch' selection
        :return:
        """
        poly_selection = Polygon([start_pos, (end_pos[0], start_pos[1]), end_pos, (start_pos[0], end_pos[1])])

        self.delete_selection_shape()
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
                            self.draw_selection_shape(obj)
                            self.collection.set_active(obj.options['name'])
                    else:
                        if poly_selection.intersects(poly_obj):
                            # create the selection box around the selected object
                            self.draw_selection_shape(obj)
                            self.collection.set_active(obj.options['name'])
            except:
                # the Exception here will happen if we try to select on screen and we have an newly (and empty)
                # just created Geometry or Excellon object that do not have the xmin, xmax, ymin, ymax options.
                # In this case poly_obj creation (see above) will fail
                pass

    def select_objects(self, key=None):
        # list where we store the overlapped objects under our mouse left click position
        objects_under_the_click_list = []

        # Populate the list with the overlapped objects on the click position
        curr_x, curr_y = self.pos
        for obj in self.all_objects_list:
            if (curr_x >= obj.options['xmin']) and (curr_x <= obj.options['xmax']) and \
                    (curr_y >= obj.options['ymin']) and (curr_y <= obj.options['ymax']):
                if obj.options['name'] not in objects_under_the_click_list:
                    if obj.options['plot']:
                        # add objects to the objects_under_the_click list only if the object is plotted
                        # (active and not disabled)
                        objects_under_the_click_list.append(obj.options['name'])
        try:
            # If there is no element in the overlapped objects list then make everyone inactive
            # because we selected "nothing"
            if not objects_under_the_click_list:
                self.collection.set_all_inactive()
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
                    self.inform.emit("")
                else:
                    self.call_source = 'app'

            else:
                # case when there is only an object under the click and we toggle it
                if len(objects_under_the_click_list) == 1:
                    if self.collection.get_active() is None :
                        self.collection.set_active(objects_under_the_click_list[0])
                        # create the selection box around the selected object
                        curr_sel_obj = self.collection.get_active()
                        self.draw_selection_shape(curr_sel_obj)

                        # self.inform.emit('[selected] %s: %s selected' %
                        #                  (str(curr_sel_obj.kind).capitalize(), str(curr_sel_obj.options['name'])))
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

                    elif self.collection.get_active().options['name'] not in objects_under_the_click_list:
                        self.collection.set_all_inactive()
                        self.delete_selection_shape()
                        self.collection.set_active(objects_under_the_click_list[0])
                        # create the selection box around the selected object
                        curr_sel_obj = self.collection.get_active()
                        self.draw_selection_shape(curr_sel_obj)

                        # self.inform.emit('[selected] %s: %s selected' %
                        #                  (str(curr_sel_obj.kind).capitalize(), str(curr_sel_obj.options['name'])))
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

                    else:
                        self.collection.set_all_inactive()
                        self.delete_selection_shape()
                        if self.call_source == 'app':
                            # delete any text in the status bar, implicitly the last object name that was selected
                            self.inform.emit("")
                        else:
                            self.call_source = 'app'
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
                        name_sel_obj_idx = objects_under_the_click_list.index(name_sel_obj)
                        self.collection.set_all_inactive()
                        self.collection.set_active(objects_under_the_click_list[(name_sel_obj_idx + 1) %
                                                                                len(objects_under_the_click_list)])

                    curr_sel_obj = self.collection.get_active()
                    # delete the possible selection box around a possible selected object
                    self.delete_selection_shape()
                    # create the selection box around the selected object
                    self.draw_selection_shape(curr_sel_obj)

                    # self.inform.emit('[selected] %s: %s selected' %
                    #                  (str(curr_sel_obj.kind).capitalize(), str(curr_sel_obj.options['name'])))
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

                    # for obj in self.collection.get_list():
                    #     obj.plot()
                    # curr_sel_obj.plot(color=self.FC_dark_blue, face_color=self.FC_light_blue)

                    # TODO: on selected objects change the object colors and do not draw the selection box
                    # self.plotcanvas.vispy_canvas.update() # this updates the canvas
        except Exception as e:
            log.error("[ERROR] Something went bad. %s" % str(e))
            return

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
        if self.ui.general_defaults_form.general_app_group.units_radio.get_value().upper() == 'MM':
            hover_rect = hover_rect.buffer(-0.1)
            hover_rect = hover_rect.buffer(0.2)

        else:
            hover_rect = hover_rect.buffer(-0.00393)
            hover_rect = hover_rect.buffer(0.00787)

        if color:
            face = Color(color)
            face.alpha = 0.2
            outline = Color(color, alpha=0.8)
        else:
            face = Color(self.defaults['global_sel_fill'])
            face.alpha = 0.2
            outline = self.defaults['global_sel_line']

        self.hover_shapes.add(hover_rect, color=outline, face_color=face, update=True, layer=0, tolerance=None)

    def delete_selection_shape(self):
        self.move_tool.sel_shapes.clear()
        self.move_tool.sel_shapes.redraw()

    def draw_selection_shape(self, sel_obj, color=None):
        """

        :param sel_obj: the object for which the selection shape must be drawn
        :return:
        """

        pt1 = (float(sel_obj.options['xmin']), float(sel_obj.options['ymin']))
        pt2 = (float(sel_obj.options['xmax']), float(sel_obj.options['ymin']))
        pt3 = (float(sel_obj.options['xmax']), float(sel_obj.options['ymax']))
        pt4 = (float(sel_obj.options['xmin']), float(sel_obj.options['ymax']))

        sel_rect = Polygon([pt1, pt2, pt3, pt4])
        if self.ui.general_defaults_form.general_app_group.units_radio.get_value().upper() == 'MM':
            sel_rect = sel_rect.buffer(-0.1)
            sel_rect = sel_rect.buffer(0.2)
        else:
            sel_rect = sel_rect.buffer(-0.00393)
            sel_rect = sel_rect.buffer(0.00787)

        if color:
            face = Color(color, alpha=0.2)
            outline = Color(color, alpha=0.8)
        else:
            face = Color(self.defaults['global_sel_fill'], alpha=0.2)
            outline = Color(self.defaults['global_sel_line'], alpha=0.8)

        self.sel_objects_list.append(self.move_tool.sel_shapes.add(sel_rect, color=outline,
                                                               face_color=face, update=True, layer=0, tolerance=None))

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
        x0, y0 = old_coords
        x1, y1 = coords
        pt1 = (x0, y0)
        pt2 = (x1, y0)
        pt3 = (x1, y1)
        pt4 = (x0, y1)
        sel_rect = Polygon([pt1, pt2, pt3, pt4])

        color_t = Color(face_color)
        color_t.alpha = 0.3
        self.move_tool.sel_shapes.add(sel_rect, color=color, face_color=color_t, update=True,
                                      layer=0, tolerance=None)

    def on_file_new_click(self):
        if self.collection.get_list() and self.should_we_save:
            msgbox = QtWidgets.QMessageBox()
            # msgbox.setText("<B>Save changes ...</B>")
            msgbox.setText(_("There are files/objects opened in FlatCAM.\n"
                           "Creating a New project will delete them.\n"
                           "Do you want to Save the project?"))
            msgbox.setWindowTitle(_("Save changes"))
            msgbox.setWindowIcon(QtGui.QIcon('share/save_as.png'))
            msgbox.setStandardButtons(QtWidgets.QMessageBox.Cancel | QtWidgets.QMessageBox.Yes |
                                      QtWidgets.QMessageBox.No)
            msgbox.setDefaultButton(QtWidgets.QMessageBox.Ok)

            response = msgbox.exec_()

            if response == QtWidgets.QMessageBox.Yes:
                self.on_file_saveprojectas()
            elif response == QtWidgets.QMessageBox.Cancel:
                return
            self.on_file_new()
        else:
            self.on_file_new()
        self.inform.emit(_("[success] New Project created..."))

    def on_file_new(self):
        """
        Callback for menu item File->New. Returns the application to its
        startup state. This method is thread-safe.

        :return: None
        """

        self.report_usage("on_file_new")

        # Remove everything from memory
        App.log.debug("on_file_new()")

        # Clear pool
        self.clear_pool()

        #delete shapes left drawn from mark shape_collections, if any
        for obj in self.collection.get_list():
            try:
                obj.mark_shapes.enabled = False
                obj.mark_shapes.clear(update=True)
            except:
                pass

        # tcl needs to be reinitialized, otherwise  old shell variables etc  remains
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

    def obj_properties(self):
        self.report_usage("obj_properties()")

        self.properties_tool.run(toggle=False)

    def on_project_context_save(self):
        obj = self.collection.get_active()
        if type(obj) == FlatCAMGeometry:
            self.on_file_exportdxf()
        elif type(obj) == FlatCAMExcellon:
            self.on_file_saveexcellon()
        elif type(obj) == FlatCAMCNCjob:
            obj.on_exportgcode_button_click()
        elif type(obj) == FlatCAMGerber:
            self.on_file_savegerber()

    def obj_move(self):
        self.report_usage("obj_move()")
        self.move_tool.run()

    def on_fileopengerber(self):
        """
        File menu callback for opening a Gerber.

        :return: None
        """

        self.report_usage("on_fileopengerber")
        App.log.debug("on_fileopengerber()")

        _filter_ = "Gerber Files (*.gbr *.ger *.gtl *.gbl *.gts *.gbs *.gtp *.gbp *.gto *.gbo *.gm1 *.gml *.gm3 *.gko " \
                   "*.cmp *.sol *.stc *.sts *.plc *.pls *.crc *.crs *.tsm *.bsm *.ly2 *.ly15 *.dim *.mil *.grb" \
                   "*.top *.bot *.smt *.smb *.sst *.ssb *.spt *.spb *.pho *.gdo *.art *.gbd);;" \
                   "Protel Files (*.gtl *.gbl *.gts *.gbs *.gto *.gbo *.gtp *.gbp *.gml *.gm1 *.gm3 *.gko);;" \
                   "Eagle Files (*.cmp *.sol *.stc *.sts *.plc *.pls *.crc *.crs *.tsm *.bsm *.ly2 *.ly15 *.dim *.mil);;" \
                   "OrCAD Files (*.top *.bot *.smt *.smb *.sst *.ssb *.spt *.spb);;" \
                   "Allegro Files (*.art);;" \
                   "Mentor Files (*.pho *.gdo);;" \
                   "All Files (*.*)"

        try:
            filenames, _f = QtWidgets.QFileDialog.getOpenFileNames(caption=_("Open Gerber"),
                                                         directory=self.get_last_folder(), filter=_filter_)
        except TypeError:
            filenames, _f = QtWidgets.QFileDialog.getOpenFileNames(caption=_("Open Gerber"), filter=_filter_)

        filenames = [str(filename) for filename in filenames]

        if len(filenames) == 0:
            self.inform.emit(_("[WARNING_NOTCL] Open Gerber cancelled."))
        else:
            for filename in filenames:
                if filename != '':
                    self.worker_task.emit({'fcn': self.open_gerber,
                                           'params': [filename]})

    def on_fileopenexcellon(self):
        """
        File menu callback for opening an Excellon file.

        :return: None
        """

        self.report_usage("on_fileopenexcellon")
        App.log.debug("on_fileopenexcellon()")

        _filter_ = "Excellon Files (*.drl *.txt *.xln *.drd *.tap *.exc);;" \
                   "All Files (*.*)"

        try:
            filenames, _f = QtWidgets.QFileDialog.getOpenFileNames(caption=_("Open Excellon"),
                                                         directory=self.get_last_folder(), filter=_filter_)
        except TypeError:
            filenames, _f = QtWidgets.QFileDialog.getOpenFileNames(caption=_("Open Excellon"), filter=_filter_)

        filenames = [str(filename) for filename in filenames]

        if len(filenames) == 0:
            self.inform.emit(_("[WARNING_NOTCL]Open Excellon cancelled."))
        else:
            for filename in filenames:
                if filename != '':
                    self.worker_task.emit({'fcn': self.open_excellon,
                                           'params': [filename]})

    def on_fileopengcode(self):
        """
        File menu call back for opening gcode.

        :return: None
        """

        self.report_usage("on_fileopengcode")
        App.log.debug("on_fileopengcode()")

        # https://bobcadsupport.com/helpdesk/index.php?/Knowledgebase/Article/View/13/5/known-g-code-file-extensions
        _filter_ = "G-Code Files (*.txt *.nc *.ncc *.tap *.gcode *.cnc *.ecs *.fnc *.dnc *.ncg *.gc *.fan *.fgc" \
                   " *.din *.xpi *.hnc *.h *.i *.ncp *.min *.gcd *.rol *.mpr *.ply *.out *.eia *.plt *.sbp *.mpf);;" \
                   "All Files (*.*)"
        try:
            filenames, _f = QtWidgets.QFileDialog.getOpenFileNames(caption=_("Open G-Code"),
                                                         directory=self.get_last_folder(), filter=_filter_)
        except TypeError:
            filenames, _f = QtWidgets.QFileDialog.getOpenFileNames(caption=_("Open G-Code"), filter=_filter_)

        filenames = [str(filename) for filename in filenames]

        if len(filenames) == 0:
            self.inform.emit(_("[WARNING_NOTCL]Open G-Code cancelled."))
        else:
            for filename in filenames:
                if filename != '':
                    self.worker_task.emit({'fcn': self.open_gcode,
                                           'params': [filename]})

    def on_file_openproject(self):
        """
        File menu callback for opening a project.

        :return: None
        """

        self.report_usage("on_file_openproject")
        App.log.debug("on_file_openproject()")
        _filter_ = "FlatCAM Project (*.FlatPrj);;All Files (*.*)"
        try:
            filename, _f = QtWidgets.QFileDialog.getOpenFileName(caption=_("Open Project"),
                                                         directory=self.get_last_folder(), filter=_filter_)
        except TypeError:
            filename, _f = QtWidgets.QFileDialog.getOpenFileName(caption=_("Open Project"), filter = _filter_)

        # The Qt methods above will return a QString which can cause problems later.
        # So far json.dump() will fail to serialize it.
        # TODO: Improve the serialization methods and remove this fix.
        filename = str(filename)

        if filename == "":
            self.inform.emit(_("[WARNING_NOTCL]Open Project cancelled."))
        else:
            # self.worker_task.emit({'fcn': self.open_project,
            #                        'params': [filename]})
            # The above was failing because open_project() is not
            # thread safe. The new_project()
            self.open_project(filename)

    def on_file_openconfig(self):
        """
        File menu callback for opening a config file.

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
                                                                 filter = _filter_)

        if filename == "":
            self.inform.emit(_("[WARNING_NOTCL]Open Config cancelled."))
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
            self.inform.emit(_("[WARNING_NOTCL] No object selected."))
            msg = _("Please Select a Geometry object to export")
            msgbox = QtWidgets.QMessageBox()
            msgbox.setInformativeText(msg)
            msgbox.setStandardButtons(QtWidgets.QMessageBox.Ok)
            msgbox.setDefaultButton(QtWidgets.QMessageBox.Ok)
            msgbox.exec_()
            return

        # Check for more compatible types and add as required
        if (not isinstance(obj, FlatCAMGeometry) and not isinstance(obj, FlatCAMGerber) and not isinstance(obj, FlatCAMCNCjob)
            and not isinstance(obj, FlatCAMExcellon)):
            msg = _("[ERROR_NOTCL] Only Geometry, Gerber and CNCJob objects can be used.")
            msgbox = QtWidgets.QMessageBox()
            msgbox.setInformativeText(msg)
            msgbox.setStandardButtons(QtWidgets.QMessageBox.Ok)
            msgbox.setDefaultButton(QtWidgets.QMessageBox.Ok)
            msgbox.exec_()
            return

        name = self.collection.get_active().options["name"]

        filter = "SVG File (*.svg);;All Files (*.*)"
        try:
            filename, _f = QtWidgets.QFileDialog.getSaveFileName(
                caption=_("Export SVG"),
                directory=self.get_last_save_folder() + '/' + str(name),
                filter=filter)
        except TypeError:
            filename, _f = QtWidgets.QFileDialog.getSaveFileName(caption=_("Export SVG"), filter=filter)

        filename = str(filename)

        if filename == "":
            self.inform.emit(_("[WARNING_NOTCL]Export SVG cancelled."))
            return
        else:
            self.export_svg(name, filename)
            self.file_saved.emit("SVG", filename)

    def on_file_exportpng(self):

        self.report_usage("on_file_exportpng")
        App.log.debug("on_file_exportpng()")

        image = _screenshot()
        data = np.asarray(image)
        if not data.ndim == 3 and data.shape[-1] in (3, 4):
            self.inform.emit(_('[[WARNING_NOTCL]] Data must be a 3D array with last dimension 3 or 4'))
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
            write_png(filename, data)
            self.file_saved.emit("png", filename)

    def on_file_savegerber(self):
        """
        Callback for menu item File->Export Gerber.

        :return: None
        """
        self.report_usage("on_file_savegerber")
        App.log.debug("on_file_savegerber()")

        obj = self.collection.get_active()
        if obj is None:
            self.inform.emit(_("[WARNING_NOTCL] No object selected. Please select an Gerber object to export."))
            return

        # Check for more compatible types and add as required
        if not isinstance(obj, FlatCAMGerber):
            self.inform.emit(_("[ERROR_NOTCL] Failed. Only Gerber objects can be saved as Gerber files..."))
            return

        name = self.collection.get_active().options["name"]

        filter = "Gerber File (*.GBR);;Gerber File (*.GRB);;All Files (*.*)"
        try:
            filename, _f = QtWidgets.QFileDialog.getSaveFileName(
                caption="Save Gerber source file",
                directory=self.get_last_save_folder() + '/' + name,
                filter=filter)
        except TypeError:
            filename, _f = QtWidgets.QFileDialog.getSaveFileName(caption=_("Save Gerber source file"), filter=filter)

        filename = str(filename)

        if filename == "":
            self.inform.emit(_("[WARNING_NOTCL] Save Gerber source file cancelled."))
            return
        else:
            self.save_source_file(name, filename)
            self.file_saved.emit("Gerber", filename)

    def on_file_saveexcellon(self):
        """
        Callback for menu item File->Export Gerber.

        :return: None
        """
        self.report_usage("on_file_saveexcellon")
        App.log.debug("on_file_saveexcellon()")

        obj = self.collection.get_active()
        if obj is None:
            self.inform.emit(_("[WARNING_NOTCL] No object selected. Please select an Excellon object to export."))
            return

        # Check for more compatible types and add as required
        if not isinstance(obj, FlatCAMExcellon):
            self.inform.emit(_("[ERROR_NOTCL] Failed. Only Excellon objects can be saved as Excellon files..."))
            return

        name = self.collection.get_active().options["name"]

        filter = "Excellon File (*.DRL);;Excellon File (*.TXT);;All Files (*.*)"
        try:
            filename, _f = QtWidgets.QFileDialog.getSaveFileName(
                caption=_("Save Excellon source file"),
                directory=self.get_last_save_folder() + '/' + name,
                filter=filter)
        except TypeError:
            filename, _f = QtWidgets.QFileDialog.getSaveFileName(caption=_("Save Excellon source file"), filter=filter)

        filename = str(filename)

        if filename == "":
            self.inform.emit(_("[WARNING_NOTCL] Saving Excellon source file cancelled."))
            return
        else:
            self.save_source_file(name, filename)
            self.file_saved.emit("Excellon", filename)

    def on_file_exportexcellon(self):
        """
        Callback for menu item File->Export SVG.

        :return: None
        """
        self.report_usage("on_file_exportexcellon")
        App.log.debug("on_file_exportexcellon()")

        obj = self.collection.get_active()
        if obj is None:
            self.inform.emit(_("[WARNING_NOTCL] No object selected. Please Select an Excellon object to export."))
            return

        # Check for more compatible types and add as required
        if not isinstance(obj, FlatCAMExcellon):
            self.inform.emit(_("[ERROR_NOTCL] Failed. Only Excellon objects can be saved as Excellon files..."))
            return

        name = self.collection.get_active().options["name"]

        filter = "Excellon File (*.DRL);;Excellon File (*.TXT);;All Files (*.*)"
        try:
            filename, _f = QtWidgets.QFileDialog.getSaveFileName(
                caption=_("Export Excellon"),
                directory=self.get_last_save_folder() + '/' + name,
                filter=filter)
        except TypeError:
            filename, _f = QtWidgets.QFileDialog.getSaveFileName(caption=_("Export Excellon"), filter=filter)

        filename = str(filename)

        if filename == "":
            self.inform.emit(_("[WARNING_NOTCL]Export Excellon cancelled."))
            return
        else:
            self.export_excellon(name, filename)
            self.file_saved.emit("Excellon", filename)

    def on_file_exportdxf(self):
        """
                Callback for menu item File->Export DXF.

                :return: None
                """
        self.report_usage("on_file_exportdxf")
        App.log.debug("on_file_exportdxf()")

        obj = self.collection.get_active()
        if obj is None:
            self.inform.emit(_("[WARNING_NOTCL] No object selected."))
            msg = _("Please Select a Geometry object to export")
            msgbox = QtWidgets.QMessageBox()
            msgbox.setInformativeText(msg)
            msgbox.setStandardButtons(QtWidgets.QMessageBox.Ok)
            msgbox.setDefaultButton(QtWidgets.QMessageBox.Ok)
            msgbox.exec_()
            return

        # Check for more compatible types and add as required
        if not isinstance(obj, FlatCAMGeometry):
            msg = _("[ERROR_NOTCL] Only Geometry objects can be used.")
            msgbox = QtWidgets.QMessageBox()
            msgbox.setInformativeText(msg)
            msgbox.setStandardButtons(QtWidgets.QMessageBox.Ok)
            msgbox.setDefaultButton(QtWidgets.QMessageBox.Ok)
            msgbox.exec_()
            return

        name = self.collection.get_active().options["name"]

        filter = "DXF File (*.DXF);;All Files (*.*)"
        try:
            filename, _f = QtWidgets.QFileDialog.getSaveFileName(
                caption=_("Export DXF"),
                directory=self.get_last_save_folder() + '/' + name,
                filter=filter)
        except TypeError:
            filename, _f = QtWidgets.QFileDialog.getSaveFileName(caption=_("Export DXF"), filter=filter)

        filename = str(filename)

        if filename == "":
            self.inform.emit(_("[WARNING_NOTCL] Export DXF cancelled."))
            return
        else:
            self.export_dxf(name, filename)
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

        filter = "SVG File (*.svg);;All Files (*.*)"
        try:
            filenames, _f = QtWidgets.QFileDialog.getOpenFileNames(caption=_("Import SVG"),
                                                         directory=self.get_last_folder(), filter=filter)
        except TypeError:
            filenames, _f = QtWidgets.QFileDialog.getOpenFileNames(caption=_("Import SVG"), filter=filter)

        if type_of_obj is not "geometry" and type_of_obj is not "gerber":
            type_of_obj = "geometry"

        filenames = [str(filename) for filename in filenames]

        if len(filenames) == 0:
            self.inform.emit(_("[WARNING_NOTCL] Open SVG cancelled."))
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

        filter = "DXF File (*.DXF);;All Files (*.*)"
        try:
            filenames, _f = QtWidgets.QFileDialog.getOpenFileNames(caption=_("Import DXF"),
                                                         directory=self.get_last_folder(), filter=filter)
        except TypeError:
            filenames, _f = QtWidgets.QFileDialog.getOpenFileNames(caption=_("Import DXF"), filter=filter)

        if type_of_obj is not "geometry" and type_of_obj is not "gerber":
            type_of_obj = "geometry"

        filenames = [str(filename) for filename in filenames]

        if len(filenames) == 0:
            self.inform.emit(_("[WARNING_NOTCL]Open DXF cancelled."))
        else:
            for filename in filenames:
                if filename != '':
                    self.worker_task.emit({'fcn': self.import_dxf,
                                           'params': [filename, type_of_obj]})

    ###################################################################################################################
    ### The following section has the functions that are displayed are call the Editoe tab CNCJob Tab #################
    ###################################################################################################################

    def init_code_editor(self, name):
        # Signals section
        # Disconnect the old signals
        self.ui.buttonOpen.clicked.disconnect()
        self.ui.buttonSave.clicked.disconnect()

        # add the tab if it was closed
        self.ui.plot_tab_area.addTab(self.ui.cncjob_tab, _('%s') % name)
        self.ui.cncjob_tab.setObjectName('cncjob_tab')

        # delete the absolute and relative position and messages in the infobar
        self.ui.position_label.setText("")
        self.ui.rel_position_label.setText("")

        # first clear previous text in text editor (if any)
        self.ui.code_editor.clear()
        self.ui.code_editor.setReadOnly(False)
        self.toggle_codeeditor = True
        self.ui.code_editor.completer_enable = False

        # Switch plot_area to CNCJob tab
        self.ui.plot_tab_area.setCurrentWidget(self.ui.cncjob_tab)

    def on_view_source(self):
        try:
            obj = self.collection.get_active()
        except:
            self.inform.emit(_("[WARNING_NOTCL] Select an Gerber or Excellon file to view it's source file."))
            return 'fail'

        # then append the text from GCode to the text editor
        try:
            file = StringIO(obj.source_file)
        except AttributeError:
            self.inform.emit(_("[WARNING_NOTCL] There is no selected object for which to see it's source file code."))
            return 'fail'

        if obj.kind == 'gerber':
            flt = "Gerber Files (*.GBR);;All Files (*.*)"
        elif obj.kind == 'excellon':
            flt = "Excellon Files (*.DRL);;All Files (*.*)"

        self.init_code_editor(name=_("Source Editor"))
        self.ui.buttonOpen.clicked.connect(lambda: self.handleOpen(filt=flt))
        self.ui.buttonSave.clicked.connect(lambda: self.handleSaveGCode(filt=flt))

        try:
            for line in file:
                proc_line = str(line).strip('\n')
                self.ui.code_editor.append(proc_line)
        except Exception as e:
            log.debug('App.on_view_source() -->%s' % str(e))
            self.inform.emit(_('[ERROR]App.on_view_source() -->%s') % str(e))
            return

        self.ui.code_editor.moveCursor(QtGui.QTextCursor.Start)

        self.handleTextChanged()
        self.ui.show()

    def on_toggle_code_editor(self):
        self.report_usage("on_toggle_code_editor()")

        if self.toggle_codeeditor is False:
            self.init_code_editor(name=_("Code Editor"))
            self.ui.buttonOpen.clicked.connect(lambda: self.handleOpen())
            self.ui.buttonSave.clicked.connect(lambda: self.handleSaveGCode())
        else:
            for idx in range(self.ui.plot_tab_area.count()):
                if self.ui.plot_tab_area.widget(idx).objectName() == "cncjob_tab":
                    self.ui.plot_tab_area.closeTab(idx)
                    break
            self.toggle_codeeditor = False

    def on_filenewscript(self):
        flt = "FlatCAM Scripts (*.FlatScript);;All Files (*.*)"
        self.init_code_editor(name=_("Script Editor"))
        self.ui.code_editor.completer_enable = True
        self.ui.code_editor.append(_(
            "#\n"
            "# CREATE A NEW FLATCAM TCL SCRIPT\n"
            "# TCL Tutorial here: https://www.tcl.tk/man/tcl8.5/tutorial/tcltutorial.html\n"
            "#\n\n"
            "# FlatCAM commands list:\n"
            "# AddCircle, AddPolygon, AddPolyline, AddRectangle, AlignDrill, AlignDrillGrid, ClearShell, Cncjob,\n"
            "# Cutout, Delete, Drillcncjob, ExportGcode, ExportSVG, Exteriors, GeoCutout, GeoUnion, GetNames, GetSys,\n"
            "# ImportSvg, Interiors, Isolate, Follow, JoinExcellon, JoinGeometry, ListSys, MillHoles, Mirror, New,\n"
            "# NewGeometry, Offset, OpenExcellon, OpenGCode, OpenGerber, OpenProject, Options, Paint, Panelize,\n"
            "# Plot, SaveProject, SaveSys, Scale, SetActive, SetSys, Skew, SubtractPoly,SubtractRectangle, Version,\n"
            "# WriteGCode\n"
            "#\n\n"
        ))

        self.ui.buttonOpen.clicked.connect(lambda: self.handleOpen(filt=flt))
        self.ui.buttonSave.clicked.connect(lambda: self.handleSaveGCode(filt=flt))

        self.handleTextChanged()
        self.ui.code_editor.show()

    def on_fileopenscript(self):
        _filter_ = "TCL script (*.FlatScript);;TCL script (*.TCL);;TCL script (*.TXT);;All Files (*.*)"
        try:
            filename, _f = QtWidgets.QFileDialog.getOpenFileName(caption=_("Open TCL script"),
                                                                 directory=self.get_last_folder(), filter=_filter_)
        except TypeError:
            filename, _f = QtWidgets.QFileDialog.getOpenFileName(caption=_("Open TCL script"), filter=_filter_)

        # The Qt methods above will return a QString which can cause problems later.
        # So far json.dump() will fail to serialize it.
        # TODO: Improve the serialization methods and remove this fix.
        filename = str(filename)

        if filename == "":
            self.inform.emit(_("[WARNING_NOTCL]Open TCL script cancelled."))
        else:
            self.on_filenewscript()

            try:
                with open(filename, "r") as opened_script:
                    try:
                        for line in opened_script:
                            proc_line = str(line).strip('\n')
                            self.ui.code_editor.append(proc_line)
                    except Exception as e:
                        log.debug('App.on_fileopenscript() -->%s' % str(e))
                        self.inform.emit(_('[ERROR]App.on_fileopenscript() -->%s') % str(e))
                        return

                    self.ui.code_editor.moveCursor(QtGui.QTextCursor.Start)

                    self.handleTextChanged()
                    self.ui.show()

            except Exception as e:
                log.debug("App.on_fileopenscript() -> %s" % str(e))

    def on_filerunscript(self, name=None):
        """
                File menu callback for loading and running a TCL script.

                :return: None
                """

        self.report_usage("on_filerunscript")
        App.log.debug("on_file_runscript()")

        if name:
            filename = name
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
            self.inform.emit(_("[WARNING_NOTCL]Run TCL script cancelled."))
        else:
            try:
                with open(filename, "r") as tcl_script:
                    cmd_line_shellfile_content = tcl_script.read()
                    self.shell._sysShell.exec_command(cmd_line_shellfile_content)
            except Exception as e:
                log.debug("App.on_filerunscript() -> %s" % str(e))
                sys.exit(2)

    def on_file_saveproject(self):
        """
        Callback for menu item File->Save Project. Saves the project to
        ``self.project_filename`` or calls ``self.on_file_saveprojectas()``
        if set to None. The project is saved by calling ``self.save_project()``.

        :return: None
        """

        self.report_usage("on_file_saveproject")

        if self.project_filename is None:
            self.on_file_saveprojectas()
        else:
            self.worker_task.emit({'fcn': self.save_project,
                                   'params': [self.project_filename]})

            self.file_opened.emit("project", self.project_filename)
            self.file_saved.emit("project", self.project_filename)

        self.should_we_save = False

    def on_file_saveprojectas(self, make_copy=False, thread=True):
        """
        Callback for menu item File->Save Project As... Opens a file
        chooser and saves the project to the given file via
        ``self.save_project()``.

        :return: None
        """

        self.report_usage("on_file_saveprojectas")

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
            self.inform.emit(_("[WARNING_NOTCL] Save Project cancelled."))
            return

        try:
            f = open(filename, 'r')
            f.close()
            exists = True
        except IOError:
            exists = False

        if thread is True:
            self.worker_task.emit({'fcn': self.save_project,
                                   'params': [filename]})
        else:
            self.save_project(filename)

        # self.save_project(filename)
        self.file_opened.emit("project", filename)

        self.file_saved.emit("project", filename)
        if not make_copy:
            self.project_filename = filename

        self.should_we_save = False

    def export_svg(self, obj_name, filename, scale_factor=0.00):
        """
        Exports a Geometry Object to an SVG file.

        :param filename: Path to the SVG file to save to.
        :return:
        """
        self.report_usage("export_svg()")

        if filename is None:
            filename = self.defaults["global_last_save_folder"]

        self.log.debug("export_svg()")

        try:
            obj = self.collection.get_by_name(str(obj_name))
        except:
            # TODO: The return behavior has not been established... should raise exception?
            return "Could not retrieve object: %s" % obj_name

        with self.proc_container.new(_("Exporting SVG")) as proc:
            exported_svg = obj.export_svg(scale_factor=scale_factor)

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
            with open(filename, 'w') as fp:
                fp.write(svgcode.toprettyxml())

            self.file_saved.emit("SVG", filename)
            self.inform.emit(_("[success] SVG file exported to %s") % filename)

    def export_svg_negative(self, obj_name, box_name, filename, boundary, scale_factor=0.00, use_thread=True):
        """
        Exports a Geometry Object to an SVG file in negative.

        :param filename: Path to the SVG file to save to.
        :param: use_thread: If True use threads
        :type: Bool
        :return:
        """
        self.report_usage("export_negative()")

        if filename is None:
            filename = self.defaults["global_last_save_folder"]

        self.log.debug("export_svg() negative")

        try:
            obj = self.collection.get_by_name(str(obj_name))
        except:
            # TODO: The return behavior has not been established... should raise exception?
            return "Could not retrieve object: %s" % obj_name

        try:
            box = self.collection.get_by_name(str(box_name))
        except:
            # TODO: The return behavior has not been established... should raise exception?
            return "Could not retrieve object: %s" % box_name

        if box is None:
            self.inform.emit(_("[WARNING_NOTCL]No object Box. Using instead %s") % obj)
            box = obj

        def make_negative_film():
            exported_svg = obj.export_svg(scale_factor=scale_factor)

            self.progress.emit(40)

            # Determine bounding area for svg export
            bounds = box.bounds()
            size = box.size()

            uom = obj.units.lower()

            # Convert everything to strings for use in the xml doc
            svgwidth = str(size[0] + (2 * boundary))
            svgheight = str(size[1] + (2 * boundary))
            minx = str(bounds[0] - boundary)
            miny = str(bounds[1] + boundary + size[1])
            miny_rect = str(bounds[1] - boundary)

            # Add a SVG Header and footer to the svg output from shapely
            # The transform flips the Y Axis so that everything renders
            # properly within svg apps such as inkscape
            svg_header = '<svg xmlns="http://www.w3.org/2000/svg" ' \
                         'version="1.1" xmlns:xlink="http://www.w3.org/1999/xlink" '
            svg_header += 'width="' + svgwidth + uom + '" '
            svg_header += 'height="' + svgheight + uom + '" '
            svg_header += 'viewBox="' + minx + ' -' + miny + ' ' + svgwidth + ' ' + svgheight + '" '
            svg_header += '>'
            svg_header += '<g transform="scale(1,-1)">'
            svg_footer = '</g> </svg>'

            self.progress.emit(60)

            # Change the attributes of the exported SVG
            # We don't need stroke-width - wrong, we do when we have lines with certain width
            # We set opacity to maximum
            # We set the color to WHITE
            root = ET.fromstring(exported_svg)
            for child in root:
                child.set('fill', '#FFFFFF')
                child.set('opacity', '1.0')
                child.set('stroke', '#FFFFFF')

            # first_svg_elem = 'rect x="' + minx + '" ' + 'y="' + miny_rect + '" '
            # first_svg_elem += 'width="' + svgwidth + '" ' + 'height="' + svgheight + '" '
            # first_svg_elem += 'fill="#000000" opacity="1.0" stroke-width="0.0"'

            first_svg_elem_tag = 'rect'
            first_svg_elem_attribs = {
                'x': minx,
                'y': miny_rect,
                'width': svgwidth,
                'height': svgheight,
                'id': 'neg_rect',
                'style': 'fill:#000000;opacity:1.0;stroke-width:0.0'
            }

            root.insert(0, ET.Element(first_svg_elem_tag, first_svg_elem_attribs))
            exported_svg = ET.tostring(root)

            svg_elem = svg_header + str(exported_svg) + svg_footer
            self.progress.emit(80)

            # Parse the xml through a xml parser just to add line feeds
            # and to make it look more pretty for the output
            doc = parse_xml_string(svg_elem)
            with open(filename, 'w') as fp:
                fp.write(doc.toprettyxml())

            self.progress.emit(100)

            self.file_saved.emit("SVG", filename)
            self.inform.emit(_("[success] SVG file exported to %s") % filename)

        if use_thread is True:
            proc = self.proc_container.new(_("Generating Film ... Please wait."))

            def job_thread_film(app_obj):
                try:
                    make_negative_film()
                except Exception as e:
                    proc.done()
                    return
                proc.done()

            self.worker_task.emit({'fcn': job_thread_film, 'params': [self]})
        else:
            make_negative_film()

    def export_svg_black(self, obj_name, box_name, filename, scale_factor=0.00, use_thread=True):
        """
        Exports a Geometry Object to an SVG file in negative.

        :param filename: Path to the SVG file to save to.
        :param: use_thread: If True use threads
        :type: Bool
        :return:
        """
        self.report_usage("export_svg_black()")

        if filename is None:
            filename = self.defaults["global_last_save_folder"]

        self.log.debug("export_svg() black")

        try:
            obj = self.collection.get_by_name(str(obj_name))
        except:
            # TODO: The return behavior has not been established... should raise exception?
            return "Could not retrieve object: %s" % obj_name

        try:
            box = self.collection.get_by_name(str(box_name))
        except:
            # TODO: The return behavior has not been established... should raise exception?
            return "Could not retrieve object: %s" % box_name

        if box is None:
            self.inform.emit(_("[WARNING_NOTCL]No object Box. Using instead %s") % obj)
            box = obj

        def make_black_film():
            exported_svg = obj.export_svg(scale_factor=scale_factor)

            self.progress.emit(40)

            # Change the attributes of the exported SVG
            # We don't need stroke-width
            # We set opacity to maximum
            # We set the colour to WHITE
            root = ET.fromstring(exported_svg)
            for child in root:
                child.set('fill', '#000000')
                child.set('opacity', '1.0')
                child.set('stroke', '#000000')

            exported_svg = ET.tostring(root)

            # Determine bounding area for svg export
            bounds = box.bounds()
            size = box.size()

            # This contain the measure units
            uom = obj.units.lower()

            # Define a boundary around SVG of about 1.0mm (~39mils)
            if uom in "mm":
                boundary = 1.0
            else:
                boundary = 0.0393701

            self.progress.emit(80)

            # Convert everything to strings for use in the xml doc
            svgwidth = str(size[0] + (2 * boundary))
            svgheight = str(size[1] + (2 * boundary))
            minx = str(bounds[0] - boundary)
            miny = str(bounds[1] + boundary + size[1])

            self.log.debug(minx)
            self.log.debug(miny)

            # Add a SVG Header and footer to the svg output from shapely
            # The transform flips the Y Axis so that everything renders
            # properly within svg apps such as inkscape
            svg_header = '<svg xmlns="http://www.w3.org/2000/svg" ' \
                         'version="1.1" xmlns:xlink="http://www.w3.org/1999/xlink" '
            svg_header += 'width="' + svgwidth + uom + '" '
            svg_header += 'height="' + svgheight + uom + '" '
            svg_header += 'viewBox="' + minx + ' -' + miny + ' ' + svgwidth + ' ' + svgheight + '" '
            svg_header += '>'
            svg_header += '<g transform="scale(1,-1)">'
            svg_footer = '</g> </svg>'

            svg_elem = str(svg_header) + str(exported_svg) + str(svg_footer)

            self.progress.emit(90)

            # Parse the xml through a xml parser just to add line feeds
            # and to make it look more pretty for the output
            doc = parse_xml_string(svg_elem)
            with open(filename, 'w') as fp:
                fp.write(doc.toprettyxml())
            self.progress.emit(100)

            self.file_saved.emit("SVG", filename)
            self.inform.emit(_("[success] SVG file exported to %s") % filename)

        if use_thread is True:
            proc = self.proc_container.new(_("Generating Film ... Please wait."))

            def job_thread_film(app_obj):
                try:
                    make_black_film()
                except Exception as e:
                    proc.done()
                    return
                proc.done()

            self.worker_task.emit({'fcn': job_thread_film, 'params': [self]})
        else:
            make_black_film()

    def save_source_file(self, obj_name, filename, use_thread=True):
        """
        Exports a Gerber Object to an Gerber file.

        :param filename: Path to the Gerber file to save to.
        :return:
        """
        self.report_usage("save source file()")

        if filename is None:
            filename = self.defaults["global_last_save_folder"]

        self.log.debug("save source file()")

        obj = self.collection.get_by_name(obj_name)

        file_string = StringIO(obj.source_file)
        time_string = "{:%A, %d %B %Y at %H:%M}".format(datetime.now())

        with open(filename, 'w') as file:
            file.writelines('G04*\n')
            file.writelines('G04 %s (RE)GENERATED BY FLATCAM v%s - www.flatcam.org - Version Date: %s*\n' %
                            (obj.kind.upper(), str(self.version), str(self.version_date)))
            file.writelines('G04 Filename: %s*\n' % str(obj_name))
            file.writelines('G04 Created on : %s*\n' % time_string)

            for line in file_string:
                file.writelines(line)

    def export_excellon(self, obj_name, filename, use_thread=True):
        """
        Exports a Excellon Object to an Excellon file.

        :param filename: Path to the Excellon file to save to.
        :return:
        """
        self.report_usage("export_excellon()")

        if filename is None:
            filename = self.defaults["global_last_save_folder"]

        self.log.debug("export_excellon()")

        format_exc = ';FILE_FORMAT=%d:%d\n' % (self.defaults["excellon_exp_integer"],
                                               self.defaults["excellon_exp_decimals"]
                                               )
        units = ''

        try:
            obj = self.collection.get_by_name(str(obj_name))
        except:
            # TODO: The return behavior has not been established... should raise exception?
            return "Could not retrieve object: %s" % obj_name

        # updated units
        eunits = self.defaults["excellon_exp_units"]
        ewhole = self.defaults["excellon_exp_integer"]
        efract = self.defaults["excellon_exp_decimals"]
        ezeros = self.defaults["excellon_exp_zeros"]
        eformat = self.defaults[ "excellon_exp_format"]

        fc_units = self.ui.general_defaults_form.general_app_group.units_radio.get_value().upper()
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
                    has_slots, excellon_code = obj.export_excellon(ewhole, efract, factor=factor)
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
                                                                       form='ndec', e_zeros='LZ', factor=factor)
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
                                                                       form='ndec', e_zeros='TZ', factor=factor)
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

                with open(filename, 'w') as fp:
                    fp.write(exported_excellon)

                self.file_saved.emit("Excellon", filename)
                self.inform.emit(_("[success] Excellon file exported to %s") % filename)
            except Exception as e:
                log.debug("App.export_excellon.make_excellon() --> %s" % str(e))
                return 'fail'

        if use_thread is True:

            with self.proc_container.new(_("Exporting Excellon")) as proc:

                def job_thread_exc(app_obj):
                    ret = make_excellon()
                    if ret == 'fail':
                        self.inform.emit(_('[ERROR_NOTCL] Could not export Excellon file.'))
                        return

                self.worker_task.emit({'fcn': job_thread_exc, 'params': [self]})
        else:
            ret = make_excellon()
            if ret == 'fail':
                self.inform.emit(_('[ERROR_NOTCL] Could not export Excellon file.'))
                return

    def export_dxf(self, obj_name, filename, use_thread=True):
        """
        Exports a Geometry Object to an DXF file.

        :param filename: Path to the DXF file to save to.
        :return:
        """
        self.report_usage("export_dxf()")

        if filename is None:
            filename = self.defaults["global_last_save_folder"]

        self.log.debug("export_dxf()")

        format_exc = ''
        units = ''

        try:
            obj = self.collection.get_by_name(str(obj_name))
        except:
            # TODO: The return behavior has not been established... should raise exception?
            return "Could not retrieve object: %s" % obj_name

        # updated units
        units = self.ui.general_defaults_form.general_app_group.units_radio.get_value().upper()
        if units == 'IN' or units == 'INCH':
            units = 'INCH'
        elif units == 'MM' or units == 'METIRC':
            units ='METRIC'

        def make_dxf():
            try:
                dxf_code = obj.export_dxf()
                dxf_code.saveas(filename)

                self.file_saved.emit("DXF", filename)
                self.inform.emit(_("[success] DXF file exported to %s") % filename)
            except:
                return 'fail'

        if use_thread is True:

            with self.proc_container.new(_("Exporting DXF")) as proc:

                def job_thread_exc(app_obj):
                    ret = make_dxf()
                    if ret == 'fail':
                        self.inform.emit(_('[[WARNING_NOTCL]] Could not export DXF file.'))
                        return

                self.worker_task.emit({'fcn': job_thread_exc, 'params': [self]})
        else:
            ret = make_dxf()
            if ret == 'fail':
                self.inform.emit(_('[[WARNING_NOTCL]] Could not export DXF file.'))
                return

    def import_svg(self, filename, geo_type='geometry', outname=None):
        """
        Adds a new Geometry Object to the projects and populates
        it with shapes extracted from the SVG file.

        :param filename: Path to the SVG file.
        :param outname:
        :return:
        """
        self.report_usage("import_svg()")

        obj_type = ""
        if geo_type is None or geo_type == "geometry":
            obj_type = "geometry"
        elif geo_type == "gerber":
            obj_type = geo_type
        else:
            self.inform.emit(_("[ERROR_NOTCL] Not supported type is picked as parameter. "
                             "Only Geometry and Gerber are supported"))
            return

        units = self.ui.general_defaults_form.general_app_group.units_radio.get_value().upper()

        def obj_init(geo_obj, app_obj):
            geo_obj.import_svg(filename, obj_type, units=units)
            geo_obj.multigeo = False

        with self.proc_container.new(_("Importing SVG")) as proc:

            # Object name
            name = outname or filename.split('/')[-1].split('\\')[-1]

            self.new_object(obj_type, name, obj_init, autoselected=False)
            self.progress.emit(20)
            # Register recent file
            self.file_opened.emit("svg", filename)

            # GUI feedback
            self.inform.emit(_("[success] Opened: %s") % filename)
            self.progress.emit(100)

    def import_dxf(self, filename, geo_type='geometry', outname=None):
        """
        Adds a new Geometry Object to the projects and populates
        it with shapes extracted from the DXF file.

        :param filename: Path to the DXF file.
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
            self.inform.emit(_("[ERROR_NOTCL] Not supported type is picked as parameter. "
                             "Only Geometry and Gerber are supported"))
            return

        units = self.ui.general_defaults_form.general_app_group.units_radio.get_value().upper()

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
            self.inform.emit(_("[success] Opened: %s") % filename)
            self.progress.emit(100)

    def import_image(self, filename, type='gerber', dpi=96, mode='black', mask=[250, 250, 250, 250], outname=None):
        """
        Adds a new Geometry Object to the projects and populates
        it with shapes extracted from the SVG file.

        :param filename: Path to the SVG file.
        :param outname:
        :return:
        """
        self.report_usage("import_image()")

        obj_type = ""
        if type is None or type == "geometry":
            obj_type = "geometry"
        elif type == "gerber":
            obj_type = type
        else:
            self.inform.emit(_("[ERROR_NOTCL] Not supported type is picked as parameter. "
                             "Only Geometry and Gerber are supported"))
            return

        def obj_init(geo_obj, app_obj):
            geo_obj.import_image(filename, units=units, dpi=dpi, mode=mode, mask=mask)
            geo_obj.multigeo = False

        with self.proc_container.new(_("Importing Image")) as proc:

            # Object name
            name = outname or filename.split('/')[-1].split('\\')[-1]
            units = self.ui.general_defaults_form.general_app_group.units_radio.get_value()

            self.new_object(obj_type, name, obj_init)
            self.progress.emit(20)
            # Register recent file
            self.file_opened.emit("image", filename)

            # GUI feedback
            self.inform.emit(_("[success] Opened: %s") % filename)
            self.progress.emit(100)

    def open_gerber(self, filename, outname=None):
        """
        Opens a Gerber file, parses it and creates a new object for
        it in the program. Thread-safe.

        :param outname: Name of the resulting object. None causes the
            name to be that of the file.
        :param filename: Gerber file filename
        :type filename: str
        :param follow: If true, the parser will not create polygons, just lines
            following the gerber path.
        :type follow: bool
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
                app_obj.inform.emit(_("[ERROR_NOTCL] Failed to open file: %s") % filename)
                app_obj.progress.emit(0)
                self.inform.emit(_('[ERROR_NOTCL] Failed to open file: %s') % filename)
                return "fail"
            except ParseError as err:
                app_obj.inform.emit(_("[ERROR_NOTCL] Failed to parse file: {name}. {error}").format(name=filename,  error=str(err)))
                app_obj.progress.emit(0)
                self.log.error(str(err))
                return "fail"

            except:
                msg = _("[ERROR] An internal error has ocurred. See shell.\n")
                msg += traceback.format_exc()
                app_obj.inform.emit(msg)
                return "fail"

            if gerber_obj.is_empty():
                # app_obj.inform.emit("[ERROR] No geometry found in file: " + filename)
                # self.collection.set_active(gerber_obj.options["name"])
                # self.collection.delete_active()
                self.inform.emit(_("[ERROR_NOTCL] Object is not Gerber file or empty. Aborting object creation."))
                return "fail"

            # Further parsing
            self.progress.emit(70)  # TODO: Note the mixture of self and app_obj used here

        App.log.debug("open_gerber()")

        with self.proc_container.new(_("Opening Gerber")) as proc:

            self.progress.emit(10)

            # Object name
            name = outname or filename.split('/')[-1].split('\\')[-1]

            ### Object creation ###
            ret = self.new_object("gerber", name, obj_init, autoselected=False)
            if ret == 'fail':
                self.inform.emit(_('[ERROR_NOTCL] Open Gerber failed. Probable not a Gerber file.'))
                return

            # Register recent file
            self.file_opened.emit("gerber", filename)

            self.progress.emit(100)

            # GUI feedback
            self.inform.emit(_("[success] Opened: %s") % filename)

    def open_excellon(self, filename, outname=None):
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

        #self.progress.emit(10)

        # How the object should be initialized
        def obj_init(excellon_obj, app_obj):
            # self.progress.emit(20)

            try:
                ret = excellon_obj.parse_file(filename)
                if ret == "fail":
                    log.debug("Excellon parsing failed.")
                    self.inform.emit(_("[ERROR_NOTCL] This is not Excellon file."))
                    return "fail"
            except IOError:
                app_obj.inform.emit(_("[ERROR_NOTCL] Cannot open file: %s") % filename)
                log.debug("Could not open Excellon object.")
                self.progress.emit(0)  # TODO: self and app_bjj mixed
                return "fail"
            except:
                msg = _("[ERROR_NOTCL] An internal error has occurred. See shell.\n")
                msg += traceback.format_exc()
                app_obj.inform.emit(msg)
                return "fail"

            ret = excellon_obj.create_geometry()
            if ret == 'fail':
                log.debug("Could not create geometry for Excellon object.")
                return "fail"

            # if excellon_obj.is_empty():
            #     app_obj.inform.emit("[ERROR_NOTCL] No geometry found in file: " + filename)
            #     return "fail"
            for tool in excellon_obj.tools:
                if excellon_obj.tools[tool]['solid_geometry']:
                    return
            app_obj.inform.emit(_("[ERROR_NOTCL] No geometry found in file: %s") % filename)
            return "fail"

        with self.proc_container.new(_("Opening Excellon.")):

            # Object name
            name = outname or filename.split('/')[-1].split('\\')[-1]

            ret = self.new_object("excellon", name, obj_init, autoselected=False)
            if ret == 'fail':
                self.inform.emit(_('[ERROR_NOTCL] Open Excellon file failed. Probable not an Excellon file.'))
                return

                # Register recent file
            self.file_opened.emit("excellon", filename)

            # GUI feedback
            self.inform.emit(_("[success] Opened: %s") % filename)
            # self.progress.emit(100)

    def open_gcode(self, filename, outname=None):
        """
        Opens a G-gcode file, parses it and creates a new object for
        it in the program. Thread-safe.

        :param outname: Name of the resulting object. None causes the
            name to be that of the file.
        :param filename: G-code file filename
        :type filename: str
        :return: None
        """
        App.log.debug("open_gcode()")

        # How the object should be initialized
        def obj_init(job_obj, app_obj_):
            """

            :type app_obj_: App
            """
            assert isinstance(app_obj_, App), \
                "Initializer expected App, got %s" % type(app_obj_)

            self.progress.emit(10)

            try:
                f = open(filename)
                gcode = f.read()
                f.close()
            except IOError:
                app_obj_.inform.emit(_("[ERROR_NOTCL] Failed to open %s") % filename)
                self.progress.emit(0)
                return "fail"

            job_obj.gcode = gcode

            self.progress.emit(20)

            ret = job_obj.gcode_parse()
            if ret == "fail":
                self.inform.emit(_("[ERROR_NOTCL] This is not GCODE"))
                return "fail"

            self.progress.emit(60)
            job_obj.create_geometry()

        with self.proc_container.new(_("Opening G-Code.")):

            # Object name
            name = outname or filename.split('/')[-1].split('\\')[-1]

            # New object creation and file processing
            ret = self.new_object("cncjob", name, obj_init, autoselected=False)
            if ret == 'fail':
                self.inform.emit(_("[ERROR_NOTCL] Failed to create CNCJob Object. Probable not a GCode file.\n "
                                 "Attempting to create a FlatCAM CNCJob Object from "
                                 "G-Code file failed during processing"))
                return "fail"

            # Register recent file
            self.file_opened.emit("cncjob", filename)

            # GUI feedback
            self.inform.emit(_("[success] Opened: %s") % filename)
            self.progress.emit(100)

    def open_config_file(self, filename, run_from_arg=None):
        """
        Loads a config file from the specified file.

        :param filename:  Name of the file from which to load.
        :type filename: str
        :return: None
        """
        App.log.debug("Opening config file: " + filename)

        # add the tab if it was closed
        self.ui.plot_tab_area.addTab(self.ui.cncjob_tab, _("Code Editor"))
        # first clear previous text in text editor (if any)
        self.ui.code_editor.clear()

        # Switch plot_area to CNCJob tab
        self.ui.plot_tab_area.setCurrentWidget(self.ui.cncjob_tab)

        try:
            if filename:
                f = QtCore.QFile(filename)
                if f.open(QtCore.QIODevice.ReadOnly):
                    stream = QtCore.QTextStream(f)
                    gcode_edited = stream.readAll()
                    self.ui.code_editor.setPlainText(gcode_edited)
                    f.close()
        except IOError:
            App.log.error("Failed to open config file: %s" % filename)
            self.inform.emit(_("[ERROR_NOTCL] Failed to open config file: %s") % filename)
            return

    def open_project(self, filename, run_from_arg=None):
        """
        Loads a project from the specified file.

        1) Loads and parses file
        2) Registers the file as recently opened.
        3) Calls on_file_new()
        4) Updates options
        5) Calls new_object() with the object's from_dict() as init method.
        6) Calls plot_all()

        :param filename:  Name of the file from which to load.
        :type filename: str
        :return: None
        """
        App.log.debug("Opening project: " + filename)

        # Open and parse an uncompressed Project file
        try:
            f = open(filename, 'r')
        except IOError:
            App.log.error("Failed to open project file: %s" % filename)
            self.inform.emit(_("[ERROR_NOTCL] Failed to open project file: %s") % filename)
            return

        try:
            d = json.load(f, object_hook=dict2obj)
        except:
            App.log.error("Failed to parse project file: %s" % filename)
            self.inform.emit(_("[ERROR_NOTCL] Failed to parse project file: %s") % filename)
            f.close()

            # Open and parse a compressed Project file
            try:
                with lzma.open(filename) as f:
                    file_content = f.read().decode('utf-8')
                    d = json.loads(file_content, object_hook=dict2obj)
            except IOError:
                App.log.error("Failed to open project file: %s" % filename)
                self.inform.emit(_("[ERROR_NOTCL] Failed to open project file: %s") % filename)
                return

        self.file_opened.emit("project", filename)

        # Clear the current project
        ## NOT THREAD SAFE ##
        if run_from_arg is True:
            pass
        else:
            self.on_file_new()

        #Project options
        self.options.update(d['options'])
        self.project_filename = filename
        # self.ui.units_label.setText("[" + self.options["units"] + "]")
        self.set_screen_units(self.options["units"])

        # Re create objects
        App.log.debug("Re-creating objects...")
        for obj in d['objs']:
            def obj_init(obj_inst, app_inst):
                obj_inst.from_dict(obj)
            App.log.debug(obj['kind'] + ":  " + obj['options']['name'])
            self.new_object(obj['kind'], obj['options']['name'], obj_init, active=False, fit=False, plot=True)
        self.plot_all()
        self.inform.emit(_("[success] Project loaded from: %s") % filename)

        self.should_we_save = False

        App.log.debug("Project loaded")

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
                        self.log.debug("  ERROR: " + param + " not in defaults.")
            else:
                # Try extracting the name:
                # classname_param here is param in the object
                if param.find(routes[param].__name__.lower() + "_") == 0:
                    p = param[len(routes[param].__name__) + 1:]
                    if p in routes[param].defaults:
                        routes[param].defaults[p] = self.defaults[param]
                        if silent is False:
                            self.log.debug("  " + param + " OK!")

    def restore_main_win_geom(self):
        try:
            self.ui.setGeometry(self.defaults["global_def_win_x"],
                                self.defaults["global_def_win_y"],
                                self.defaults["global_def_win_w"],
                                self.defaults["global_def_win_h"])
            self.ui.splitter.setSizes([self.defaults["def_notebook_width"], 0])

            settings = QSettings("Open Source", "FlatCAM")
            if settings.contains("maximized_gui"):
                maximized_ui = settings.value('maximized_gui', type=bool)
                if maximized_ui is True:
                    self.ui.showMaximized()
        except KeyError:
            pass

    def plot_all(self, zoom=True):
        """
        Re-generates all plots from all objects.

        :return: None
        """
        self.log.debug("Plot_all()")

        for obj in self.collection.get_list():
            def worker_task(obj):
                with self.proc_container.new("Plotting"):
                    obj.plot(kind=self.defaults["cncjob_plot_kind"])
                    if zoom:
                        self.object_plotted.emit(obj)

            # Send to worker
            self.worker_task.emit({'fcn': worker_task, 'params': [obj]})


        # self.progress.emit(10)
        #
        # def worker_task(app_obj):
        #     print "worker task"
        #     percentage = 0.1
        #     try:
        #         delta = 0.9 / len(self.collection.get_list())
        #     except ZeroDivisionError:
        #         self.progress.emit(0)
        #         return
        #     for obj in self.collection.get_list():
        #         with self.proc_container.new("Plotting"):
        #             obj.plot()
        #             app_obj.object_plotted.emit(obj)
        #
        #         percentage += delta
        #         self.progress.emit(int(percentage*100))
        #
        #     self.progress.emit(0)
        #     self.plots_updated.emit()
        #
        # # Send to worker
        # #self.worker.add_task(worker_task, [self])
        # self.worker_task.emit({'fcn': worker_task, 'params': [self]})

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

            #### Block ####
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
            TODO: this problem have to be addressed somehow, maybe rewrite promissing to be blocking somehow for TCL shell.

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
            "cncjob": "share/cnc16.png",
            "project": "share/project16.png",
            "svg": "share/geometry16.png",
            "dxf": "share/dxf16.png",
            "image": "share/image16.png"

        }

        openers = {
            'gerber': lambda fname: self.worker_task.emit({'fcn': self.open_gerber, 'params': [fname]}),
            'excellon': lambda fname: self.worker_task.emit({'fcn': self.open_excellon, 'params': [fname]}),
            'cncjob': lambda fname: self.worker_task.emit({'fcn': self.open_gcode, 'params': [fname]}),
            'project': self.open_project,
            'svg': self.import_svg,
            'dxf': self.import_dxf,
            'image': self.import_image
        }

        # Open file
        try:
            f = open(self.data_path + '/recent.json')
        except IOError:
            App.log.error("Failed to load recent item list.")
            self.inform.emit(_("[ERROR_NOTCL] Failed to load recent item list."))
            return

        try:
            self.recent = json.load(f)
        except json.scanner.JSONDecodeError:
            App.log.error("Failed to parse recent item list.")
            self.inform.emit(_("[ERROR_NOTCL] Failed to parse recent item list."))
            f.close()
            return
        f.close()

        # Closure needed to create callbacks in a loop.
        # Otherwise late binding occurs.
        def make_callback(func, fname):
            def opener():
                func(fname)
            return opener

        def reset_recent():
            # Reset menu
            self.ui.recent.clear()
            self.recent = []
            try:
                f = open(self.data_path + '/recent.json', 'w')
            except IOError:
                App.log.error("Failed to open recent items file for writing.")
                return

            json.dump(self.recent, f)

        # Reset menu
        self.ui.recent.clear()

        # Create menu items
        for recent in self.recent:
            filename = recent['filename'].split('/')[-1].split('\\')[-1]

            try:
                action = QtWidgets.QAction(QtGui.QIcon(icons[recent["kind"]]), filename, self)

                # Attach callback
                o = make_callback(openers[recent["kind"]], recent['filename'])
                action.triggered.connect(o)

                self.ui.recent.addAction(action)

            except KeyError:
                App.log.error("Unsupported file type: %s" % recent["kind"])

        # Last action in Recent Files menu is one that Clear the content
        clear_action = QtWidgets.QAction(QtGui.QIcon('share/trash32.png'), "Clear Recent files", self)
        clear_action.triggered.connect(reset_recent)
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
        # font = self.sel_title.font()
        # font.setPointSize(12)
        # self.sel_title.setFont(font)

        selected_text = _('''
<p><span style="font-size:14px"><strong>Selected Tab - Choose an Item from Project Tab</strong></span></p>

<p><span style="font-size:10px"><strong>Details</strong>:<br />
The normal flow when working in FlatCAM is the following:</span></p>

<ol>
	<li><span style="font-size:10px">Loat/Import a Gerber, Excellon, Gcode, DXF, Raster Image or SVG file into FlatCAM using either the menu&#39;s, toolbars, key shortcuts or even dragging and dropping the files on the GUI.<br />
	<br />
	You can also load a <strong>FlatCAM project</strong> by double clicking on the project file, drag &amp; drop of the file into the FLATCAM GUI or through the menu/toolbar links offered within the app.</span><br />
	&nbsp;</li>
	<li><span style="font-size:10px">Once an object is available in the Project Tab, by selecting it and then focusing on <strong>SELECTED TAB </strong>(more simpler is to double click the object name in the Project Tab), <strong>SELECTED TAB </strong>will be updated with the object properties according to it&#39;s kind: Gerber, Excellon, Geometry or CNCJob object.<br />
	<br />
	If the selection of the object is done on the canvas by single click instead, and the <strong>SELECTED TAB</strong> is in focus, again the object properties will be displayed into the Selected Tab. Alternatively, double clicking on the object on the canvas will bring the <strong>SELECTED TAB</strong> and populate it even if it was out of focus.<br />
	<br />
	You can change the parameters in this screen and the flow direction is like this:<br />
	<br />
	<strong>Gerber/Excellon Object</strong> -&gt; Change Param -&gt; Generate Geometry -&gt;<strong> Geometry Object </strong>-&gt; Add tools (change param in Selected Tab) -&gt; Generate CNCJob -&gt;<strong> CNCJob Object </strong>-&gt; Verify GCode (through Edit CNC Code) and/or append/prepend to GCode (again, done in <strong>SELECTED TAB)&nbsp;</strong>-&gt; Save GCode</span></li>
</ol>

<p><span style="font-size:10px">A list of key shortcuts is available through an menu entry in <strong>Help -&gt; Shortcuts List</strong>&nbsp;or through it&#39;s own key shortcut: <strng>F3</strong>.</span></p>

        ''')

        sel_title.setText(selected_text)
        sel_title.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        self.ui.selected_scroll_area.setWidget(sel_title)

#         tool_title = QtWidgets.QTextEdit(
#             '<b>Shortcut Key List</b>')
#         tool_title.setTextInteractionFlags(QtCore.Qt.NoTextInteraction)
#         tool_title.setFrameStyle(QtWidgets.QFrame.NoFrame)
#         # font = self.sel_title.font()
#         # font.setPointSize(12)
#         # self.sel_title.setFont(font)
#
#         tool_text = '''
# <p><span style="font-size:14px"><strong>Tool Tab - Choose an Item in Tools Menu</strong></span></p>
#
# <p><span style="font-size:10px"><strong>Details</strong>:<br />
# Some of the functionality of FlatCAM have been implemented as tools (a sort of plugins). </span></p>
#
# <p><span style="font-size:10px">Most of the tools are accessible through&nbsp;the Tools menu or by using the associated shortcut keys.<br />
# Each such a tool, if it needs an object to be used as a source it will provide the way to select this object(s) through a series of comboboxes. The result of using a tool is either a Geometry, an information that can be used in the app or it can be a file that can be saved.</span></p>
#
# <ol>
# </ol>
#
# <p><span style="font-size:10px">A list of key shortcuts is available through an menu entry in <strong>Help -&gt; Shortcuts List</strong>&nbsp;or through it&#39;s own key shortcut: &#39;`&#39; (key left to 1).</span></p>
#
#                 '''
#
#         tool_title.setText(tool_text)
#         tool_title.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
#
#         self.ui.tool_scroll_area.setWidget(tool_title)

    def setup_obj_classes(self):
        """
        Sets up application specifics on the FlatCAMObj class.

        :return: None
        """
        FlatCAMObj.app = self
        ObjectCollection.app = self

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

        if self.ui.general_defaults_form.general_gui_group.send_stats_cb.get_value() is True:
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
        ### Get the data
        try:
            f = urllib.request.urlopen(full_url)
        except:
            # App.log.warning("Failed checking for latest version. Could not connect.")
            self.log.warning("Failed checking for latest version. Could not connect.")
            self.inform.emit(_("[WARNING_NOTCL] Failed checking for latest version. Could not connect."))
            return

        try:
            data = json.load(f)
        except Exception as e:
            App.log.error("Could not parse information about latest version.")
            self.inform.emit(_("[ERROR_NOTCL] Could not parse information about latest version."))
            App.log.debug("json.load(): %s" % str(e))
            f.close()
            return

        f.close()

        ### Latest version?
        if self.version >= data["version"]:
            App.log.debug("FlatCAM is up to date!")
            self.inform.emit(_("[success] FlatCAM is up to date!"))
            return

        App.log.debug("Newer version available.")
        self.message.emit(
            _("Newer Version Available"),
            _("There is a newer version of FlatCAM available for download:\n\n") +
            "<b>%s</b>" % str(data["name"]) + "\n%s" % str(data["message"]),
            _("info")
        )

    def on_zoom_fit(self, event):
        """
        Callback for zoom-out request. This can be either from the corresponding
        toolbar button or the '1' key when the canvas is focused. Calls ``self.adjust_axes()``
        with axes limits from the geometry bounds of all objects.

        :param event: Ignored.
        :return: None
        """

        self.plotcanvas.fit_view()

    def disable_all_plots(self):
        self.report_usage("disable_all_plots()")

        self.disable_plots(self.collection.get_list())
        self.inform.emit(_("[success]All plots disabled."))

    def disable_other_plots(self):
        self.report_usage("disable_other_plots()")

        self.disable_plots(self.collection.get_non_selected())
        self.inform.emit(_("[success]All non selected plots disabled."))

    def enable_all_plots(self):
        self.report_usage("enable_all_plots()")

        self.enable_plots(self.collection.get_list())
        self.inform.emit(_("[success]All plots enabled."))

    # TODO: FIX THIS
    '''
    By default this is not threaded
    If threaded the app give warnings like this:
    
    QObject::connect: Cannot queue arguments of type 'QVector<int>' 
    (Make sure 'QVector<int>' is registered using qRegisterMetaType().
    '''
    def enable_plots(self, objects, threaded=False):
        if threaded is True:
            def worker_task(app_obj):
                percentage = 0.1
                try:
                    delta = 0.9 / len(objects)
                except ZeroDivisionError:
                    self.progress.emit(0)
                    return
                for obj in objects:
                    obj.options['plot'] = True
                    percentage += delta
                    self.progress.emit(int(percentage*100))

                self.progress.emit(0)
                self.plots_updated.emit()
                self.collection.update_view()

            # Send to worker
            # self.worker.add_task(worker_task, [self])
            self.worker_task.emit({'fcn': worker_task, 'params': [self]})
        else:
            for obj in objects:
                obj.options['plot'] = True
            self.progress.emit(0)
            self.plots_updated.emit()
            self.collection.update_view()

    # TODO: FIX THIS
    '''
    By default this is not threaded
    If threaded the app give warnings like this:

    QObject::connect: Cannot queue arguments of type 'QVector<int>' 
    (Make sure 'QVector<int>' is registered using qRegisterMetaType().
    '''
    def disable_plots(self, objects, threaded=False):
        # TODO: This method is very similar to replot_all. Try to merge.
        """
        Disables plots
        :param objects: list
            Objects to be disabled
        :return:
        """

        if threaded is True:
            self.progress.emit(10)
            def worker_task(app_obj):
                percentage = 0.1
                try:
                    delta = 0.9 / len(objects)
                except ZeroDivisionError:
                    self.progress.emit(0)
                    return

                for obj in objects:
                    obj.options['plot'] = False
                    percentage += delta
                    self.progress.emit(int(percentage*100))

                self.progress.emit(0)
                self.plots_updated.emit()
                self.collection.update_view()

            # Send to worker
            self.worker_task.emit({'fcn': worker_task, 'params': [self]})
        else:
            for obj in objects:
                obj.options['plot'] = False
            self.plots_updated.emit()
            self.collection.update_view()

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

    def save_project(self, filename):
        """
        Saves the current project to the specified file.

        :param filename: Name of the file in which to save.
        :type filename: str
        :return: None
        """
        self.log.debug("save_project()")

        with self.proc_container.new(_("Saving FlatCAM Project")) as proc:
            ## Capture the latest changes
            # Current object
            try:
                self.collection.get_active().read_form()
            except:
                self.log.debug("There was no active object")
                pass
            # Project options
            self.options_read_form()

            # Serialize the whole project
            d = {"objs": [obj.to_dict() for obj in self.collection.get_list()],
                 "options": self.options,
                 "version": self.version}

            if self.defaults["global_save_compressed"] is True:
                with lzma.open(filename, "w", preset=int(self.defaults['global_compression_level'])) as f:
                    g = json.dumps(d, default=to_dict, indent=2, sort_keys=True).encode('utf-8')
                    # # Write
                    f.write(g)
                self.inform.emit(_("[success] Project saved to: %s") % filename)
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
                    self.inform.emit(_("[ERROR_NOTCL] Failed to verify project file: %s. Retry to save it.") % filename)
                    return

                try:
                    saved_d = json.load(saved_f, object_hook=dict2obj)
                except:
                    self.inform.emit(
                        _("[ERROR_NOTCL] Failed to parse saved project file: %s. Retry to save it.") % filename)
                    f.close()
                    return
                saved_f.close()

                if 'version' in saved_d:
                    self.inform.emit(_("[success] Project saved to: %s") % filename)
                else:
                    self.inform.emit(_("[ERROR_NOTCL] Failed to save project file: %s. Retry to save it.") % filename)

    def on_options_app2project(self):
        """
        Callback for Options->Transfer Options->App=>Project. Copies options
        from application defaults to project defaults.

        :return: None
        """

        self.report_usage("on_options_app2project")

        self.defaults_read_form()
        self.options.update(self.defaults)
        self.options_write_form()

    def on_options_project2app(self):
        """
        Callback for Options->Transfer Options->Project=>App. Copies options
        from project defaults to application defaults.

        :return: None
        """

        self.report_usage("on_options_project2app")

        self.options_read_form()
        self.defaults.update(self.options)
        self.defaults_write_form()

    def on_options_project2object(self):
        """
        Callback for Options->Transfer Options->Project=>Object. Copies options
        from project defaults to the currently selected object.

        :return: None
        """

        self.report_usage("on_options_project2object")

        self.options_read_form()
        obj = self.collection.get_active()
        if obj is None:
            self.inform.emit(_("[WARNING_NOTCL] No object selected."))
            return
        for option in self.options:
            if option.find(obj.kind + "_") == 0:
                oname = option[len(obj.kind) + 1:]
                obj.options[oname] = self.options[option]
        obj.to_form()  # Update UI

    def on_options_object2project(self):
        """
        Callback for Options->Transfer Options->Object=>Project. Copies options
        from the currently selected object to project defaults.

        :return: None
        """

        self.report_usage("on_options_object2project")

        obj = self.collection.get_active()
        if obj is None:
            self.inform.emit(_("[WARNING_NOTCL] No object selected."))
            return
        obj.read_form()
        for option in obj.options:
            if option in ['name']:  # TODO: Handle this better...
                continue
            self.options[obj.kind + "_" + option] = obj.options[option]
        self.options_write_form()

    def on_options_object2app(self):
        """
        Callback for Options->Transfer Options->Object=>App. Copies options
        from the currently selected object to application defaults.

        :return: None
        """

        self.report_usage("on_options_object2app")

        obj = self.collection.get_active()
        if obj is None:
            self.inform.emit(_("[WARNING_NOTCL] No object selected."))
            return
        obj.read_form()
        for option in obj.options:
            if option in ['name']:  # TODO: Handle this better...
                continue
            self.defaults[obj.kind + "_" + option] = obj.options[option]
        self.defaults_write_form()

    def on_options_app2object(self):
        """
        Callback for Options->Transfer Options->App=>Object. Copies options
        from application defaults to the currently selected object.

        :return: None
        """

        self.report_usage("on_options_app2object")

        self.defaults_read_form()
        obj = self.collection.get_active()
        if obj is None:
            self.inform.emit(_("[WARNING_NOTCL] No object selected."))
            return
        for option in self.defaults:
            if option.find(obj.kind + "_") == 0:
                oname = option[len(obj.kind) + 1:]
                obj.options[oname] = self.defaults[option]
        obj.to_form()  # Update UI

# end of file
