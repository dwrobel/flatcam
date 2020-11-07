import os
import stat
import sys
from copy import deepcopy
from appCommon.Common import LoudDict
from camlib import to_dict, CNCjob, Geometry
import simplejson
import logging
import gettext
import appTranslation as fcTranslate
import builtins

from appParsers.ParseExcellon import Excellon
from appParsers.ParseGerber import Gerber

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext
# log = logging.getLogger('FlatCAMDefaults')
log = logging.getLogger('base')


class FlatCAMDefaults:

    factory_defaults = {
        # Global
        "version": 8.992,  # defaults format version, not necessarily equal to app version
        "first_run": True,
        "root_folder_path": '',
        "global_serial": 0,
        "global_stats": dict(),
        "global_tabs_detachable": True,

        "global_coordsbar_show": True,
        "global_delta_coordsbar_show": False,
        "global_statusbar_show": True,

        "global_jump_ref": 'abs',
        "global_locate_pt": 'bl',

        "global_toolbar_view": 511,

        "global_background_timeout": 300000,  # Default value is 5 minutes
        "global_verbose_error_level": 0,  # Shell verbosity 0 = default
        # (python trace only for unknown errors),
        # 1 = show trace(show trace always),
        # 2 = (For the future).

        "global_grid_context_menu": {
            'in': [0.01, 0.02, 0.025, 0.05, 0.1],
            'mm': [0.1, 0.2, 0.5, 1, 2.54]
        },

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
        "global_recent_limit": 10,  # Max. items in recent list.

        "fit_key": 'V',
        "zoom_out_key": '-',
        "zoom_in_key": '=',
        "grid_toggle_key": 'G',
        "global_zoom_ratio": 1.5,
        "global_point_clipboard_format": "(%.*f, %.*f)",
        "global_zdownrate": None,

        "global_tcl_path": '',

        # General APP Preferences
        "units": "MM",
        "decimals_inch": 4,
        "decimals_metric": 4,
        "global_graphic_engine": '3D',
        "global_app_level": 'b',

        "global_portable": False,
        "global_language": 'English',

        "global_systray_icon": True,
        "global_shell_at_startup": False,  # Show the shell at startup.
        "global_project_at_startup": False,
        "global_version_check": True,
        "global_send_stats": True,
        "global_worker_number": int((os.cpu_count()) / 2) if os.cpu_count() > 4 else 2,
        "global_tolerance": 0.005,

        "global_save_compressed": True,
        "global_compression_level": 3,
        "global_autosave": False,
        "global_autosave_timeout": 300000,

        "global_tpdf_tmargin": 15.0,
        "global_tpdf_bmargin": 10.0,
        "global_tpdf_lmargin": 20.0,
        "global_tpdf_rmargin": 20.0,

        # General GUI Preferences
        "global_theme": 'white',
        "global_gray_icons": False,

        "global_layout": "compact",
        "global_hover": False,
        "global_selection_shape": True,

        "global_sel_fill": '#a5a5ffbf',
        "global_sel_line": '#0000ffbf',
        "global_alt_sel_fill": '#BBF268BF',
        "global_alt_sel_line": '#006E20BF',
        "global_draw_color": '#FF0000',
        "global_sel_draw_color": '#0000FF',
        "global_proj_item_color": '#000000',
        "global_proj_item_dis_color": '#b7b7cb',
        "global_project_autohide": True,

        # General App Settings
        "global_gridbar_show": True,
        "global_gridx": 1.0,
        "global_gridy": 1.0,
        "global_snap_max": 0.05,

        "global_workspace": False,
        "global_workspaceT": "A4",
        "global_workspace_orientation": 'p',
        "global_axis": True,
        "global_hud": True,
        "global_grid_lines": True,
        "global_grid_snap": True,

        "global_cursor_type": "small",
        "global_cursor_size": 20,
        "global_cursor_width": 2,
        "global_cursor_color": '#FF0000',
        "global_cursor_color_enabled": True,

        "global_pan_button": '2',
        "global_mselect_key": 'Control',

        "global_delete_confirmation": True,
        "global_allow_edit_in_project_tab": False,
        "global_open_style": True,
        "global_toggle_tooltips": True,
        "global_machinist_setting": False,
        "global_bookmarks": dict(),
        "global_bookmarks_limit": 10,
        "global_activity_icon": 'Ball green',

        # Gerber General
        "gerber_plot": True,
        "gerber_solid": True,
        "gerber_multicolored": False,
        "gerber_color_list": [],
        "gerber_store_color_list": True,

        "gerber_circle_steps": 64,
        "gerber_use_buffer_for_union": True,
        "gerber_clean_apertures": True,
        "gerber_extra_buffering": True,

        "gerber_plot_fill": '#BBF268BF',
        "gerber_plot_line": '#006E20BF',

        "gerber_def_units": 'IN',
        "gerber_def_zeros": 'L',
        "gerber_save_filters": "Gerber File .gbr (*.gbr);;Gerber File .bot (*.bot);;Gerber File .bsm (*.bsm);;"
                               "Gerber File .cmp (*.cmp);;Gerber File .crc (*.crc);;Gerber File .crs (*.crs);;"
                               "Gerber File .gb0 (*.gb0);;Gerber File .gb1 (*.gb1);;Gerber File .gb2 (*.gb2);;"
                               "Gerber File .gb3 (*.gb3);;Gerber File .gb4 (*.gb4);;Gerber File .gb5 (*.gb5);;"
                               "Gerber File .gb6 (*.gb6);;Gerber File .gb7 (*.gb7);;Gerber File .gb8 (*.gb8);;"
                               "Gerber File .gb9 (*.gb9);;Gerber File .gbd (*.gbd);;Gerber File .gbl (*.gbl);;"
                               "Gerber File .gbo (*.gbo);;Gerber File .gbp (*.gbp);;Gerber File .gbs (*.gbs);;"
                               "Gerber File .gdo (*.gdo);;Gerber File .ger (*.ger);;Gerber File .gko (*.gko);;"
                               "Gerber File .gm1 (*.gm1);;Gerber File .gm2 (*.gm2);;Gerber File .gm3 (*.gm3);;"
                               "Gerber File .grb (*.grb);;Gerber File .gtl (*.gtl);;Gerber File .gto (*.gto);;"
                               "Gerber File .gtp (*.gtp);;Gerber File .gts (*.gts);;Gerber File .ly15 (*.ly15);;"
                               "Gerber File .ly2 (*.ly2);;Gerber File .mil (*.mil);;"
                               "Gerber File .outline (*.outline);;Gerber File .pho (*.pho);;"
                               "Gerber File .plc (*.plc);;Gerber File .pls (*.pls);;Gerber File .smb (*.smb);;"
                               "Gerber File .smt (*.smt);;Gerber File .sol (*.sol);;Gerber File .spb (*.spb);;"
                               "Gerber File .spt (*.spt);;Gerber File .ssb (*.ssb);;Gerber File .sst (*.sst);;"
                               "Gerber File .stc (*.stc);;Gerber File .sts (*.sts);;Gerber File .top (*.top);;"
                               "Gerber File .tsm (*.tsm);;Gerber File .art (*.art)"
                               "All Files (*.*)",

        # Gerber Options
        "gerber_noncoppermargin": 0.1,
        "gerber_noncopperrounded": False,
        "gerber_bboxmargin": 0.1,
        "gerber_bboxrounded": False,

        # Gerber Advanced Options
        "gerber_aperture_display": False,
        "gerber_aperture_scale_factor": 1.0,
        "gerber_aperture_buffer_factor": 0.0,
        "gerber_follow": False,
        "gerber_buffering": "full",
        "gerber_delayed_buffering": True,
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
        "excellon_multicolored": False,
        "excellon_merge_fuse_tools": True,
        "excellon_format_upper_in": 2,
        "excellon_format_lower_in": 4,
        "excellon_format_upper_mm": 3,
        "excellon_format_lower_mm": 3,
        "excellon_zeros": "T",
        "excellon_units": "INCH",
        "excellon_update": True,

        "excellon_optimization_type": 'B',

        "excellon_search_time": 3,
        "excellon_save_filters": "Excellon File .txt (*.txt);;Excellon File .drd (*.drd);;"
                                 "Excellon File .drill (*.drill);;"
                                 "Excellon File .drl (*.drl);;Excellon File .exc (*.exc);;"
                                 "Excellon File .ncd (*.ncd);;Excellon File .tap (*.tap);;"
                                 "Excellon File .xln (*.xln);;All Files (*.*)",
        "excellon_plot_fill": '#C40000BF',
        "excellon_plot_line": '#750000BF',

        # Excellon Options
        "excellon_operation": "drill",
        "excellon_milling_type": "drills",

        "excellon_milling_dia": 0.8,

        "excellon_tooldia": 0.8,
        "excellon_slot_tooldia": 1.8,

        # Excellon Advanced options
        "excellon_tools_table_display": True,
        "excellon_autoload_db": False,

        # Excellon Export
        "excellon_exp_units": 'INCH',
        "excellon_exp_format": 'dec',
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
        "excellon_editor_slot_lin_dir": 'X',
        "excellon_editor_slot_lin_pitch": 2.54,
        "excellon_editor_slot_lin_angle": 0.0,
        "excellon_editor_slot_circ_dir": 'CW',
        "excellon_editor_slot_circ_angle": 0.0,

        # Geometry General
        "geometry_plot": True,
        "geometry_multicolored": False,
        "geometry_circle_steps": 64,
        "geometry_cnctooldia": "2.4",
        "geometry_merge_fuse_tools": True,
        "geometry_plot_line": "#FF0000",
        "geometry_optimization_type": 'R',
        "geometry_search_time": 3,

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
        "geometry_endxy": None,

        "geometry_feedrate": 120,
        "geometry_feedrate_z": 60,
        "geometry_spindlespeed": 0,
        "geometry_dwell": False,
        "geometry_dwelltime": 1,
        "geometry_ppname_g": 'default',

        # Geometry Advanced Options
        "geometry_toolchangexy": "0.0, 0.0",
        "geometry_startz": None,
        "geometry_feedrate_rapid": 1500,
        "geometry_extracut": False,
        "geometry_extracut_length": 0.1,
        "geometry_z_pdepth": -0.02,
        "geometry_f_plunge": False,
        "geometry_spindledir": 'CW',
        "geometry_feedrate_probe": 75,
        "geometry_segx": 0.0,
        "geometry_segy": 0.0,
        "geometry_area_exclusion": False,
        "geometry_area_shape": "polygon",
        "geometry_area_strategy": "over",
        "geometry_area_overz": 1.0,
        "geometry_polish": False,
        "geometry_polish_dia": 10.0,
        "geometry_polish_pressure": -1.0,
        "geometry_polish_travelz": 2.0,
        "geometry_polish_margin": 0.0,
        "geometry_polish_overlap": 5,
        "geometry_polish_method": 0,

        # Geometry Editor
        "geometry_editor_sel_limit": 30,
        "geometry_editor_milling_type": "cl",

        # CNC Job General
        "cncjob_plot": True,
        "cncjob_tooldia": 1.0,
        "cncjob_coords_type": "G90",
        "cncjob_coords_decimals": 4,
        "cncjob_fr_decimals": 2,
        "cncjob_steps_per_circle": 64,
        "cncjob_footer": False,
        "cncjob_line_ending": False,
        "cncjob_save_filters": "G-Code Files .nc (*.nc);;G-Code Files .din (*.din);;G-Code Files .dnc (*.dnc);;"
                               "G-Code Files .ecs (*.ecs);;G-Code Files .eia (*.eia);;G-Code Files .fan (*.fan);;"
                               "G-Code Files .fgc (*.fgc);;G-Code Files .fnc (*.fnc);;G-Code Files . gc (*.gc);;"
                               "G-Code Files .gcd (*.gcd);;G-Code Files .gcode (*.gcode);;G-Code Files .h (*.h);;"
                               "G-Code Files .hnc (*.hnc);;G-Code Files .i (*.i);;G-Code Files .min (*.min);;"
                               "G-Code Files .mpf (*.mpf);;G-Code Files .mpr (*.mpr);;G-Code Files .cnc (*.cnc);;"
                               "G-Code Files .ncc (*.ncc);;G-Code Files .ncg (*.ncg);;G-Code Files .ncp (*.ncp);;"
                               "G-Code Files .ngc (*.ngc);;G-Code Files .out (*.out);;G-Code Files .ply (*.ply);;"
                               "G-Code Files .sbp (*.sbp);;G-Code Files .tap (*.tap);;G-Code Files .xpi (*.xpi);;"
                               "All Files (*.*)",
        "cncjob_plot_line": '#4650BDFF',
        "cncjob_plot_fill": '#5E6CFFFF',
        "cncjob_travel_line": '#B5AB3A4C',
        "cncjob_travel_fill": '#F0E24D4C',

        # CNC Job Options
        "cncjob_plot_kind": 'all',
        "cncjob_annotation": True,

        # CNC Job Advanced Options
        "cncjob_annotation_fontsize": 9,
        "cncjob_annotation_fontcolor": '#990000',
        # Autolevelling
        "cncjob_al_status": False,
        "cncjob_al_mode": 'grid',
        "cncjob_al_method": 'v',
        "cncjob_al_rows": 4,
        "cncjob_al_columns": 4,
        "cncjob_al_travelz": 2.0,
        "cncjob_al_probe_depth": -1.0,
        "cncjob_al_probe_fr": 120,
        "cncjob_al_controller": 'MACH3',
        "cncjob_al_grbl_jog_step": 5,
        "cncjob_al_grbl_jog_fr": 1500,
        "cncjob_al_grbl_travelz": 15.0,

        # CNC Job (GCode) Editor
        "cncjob_prepend": "",
        "cncjob_append": "",

        # Isolation Routing Tool
        "tools_iso_tooldia": "0.1",
        "tools_iso_order": 'rev',
        "tools_iso_tool_type": 'C1',
        "tools_iso_tool_vtipdia": 0.1,
        "tools_iso_tool_vtipangle": 30,
        "tools_iso_tool_cutz": -0.05,
        "tools_iso_newdia": 0.1,

        "tools_iso_passes": 1,
        "tools_iso_overlap": 10,
        "tools_iso_milling_type": "cl",
        "tools_iso_follow": False,
        "tools_iso_isotype": "full",

        "tools_iso_rest":           False,
        "tools_iso_combine_passes": True,
        "tools_iso_check_valid":    False,
        "tools_iso_isoexcept":      False,
        "tools_iso_selection":      0,
        "tools_iso_poly_ints":      False,
        "tools_iso_force":          True,
        "tools_iso_area_shape":     "square",
        "tools_iso_plotting":       'normal',

        # Drilling Tool
        "tools_drill_tool_order": 'no',
        "tools_drill_cutz": -1.7,
        "tools_drill_multidepth": False,
        "tools_drill_depthperpass": 0.7,
        "tools_drill_travelz": 2,
        "tools_drill_endz": 0.5,
        "tools_drill_endxy": None,

        "tools_drill_feedrate_z": 300,
        "tools_drill_spindlespeed": 0,
        "tools_drill_dwell": False,
        "tools_drill_dwelltime": 1,
        "tools_drill_toolchange": False,
        "tools_drill_toolchangez": 15,
        "tools_drill_ppname_e": 'default',

        "tools_drill_drill_slots": False,
        "tools_drill_drill_overlap": 0.0,
        "tools_drill_last_drill": True,

        # Advanced Options
        "tools_drill_offset": 0.0,
        "tools_drill_toolchangexy": "0.0, 0.0",
        "tools_drill_startz": None,
        "tools_drill_feedrate_rapid": 1500,
        "tools_drill_z_pdepth": -0.02,
        "tools_drill_feedrate_probe": 75,
        "tools_drill_spindledir": 'CW',
        "tools_drill_f_plunge": False,
        "tools_drill_f_retract": False,

        "tools_drill_area_exclusion": False,
        "tools_drill_area_shape": "polygon",
        "tools_drill_area_strategy": "over",
        "tools_drill_area_overz": 1.0,

        # NCC Tool
        "tools_ncc_tools": "1.0, 0.5",
        "tools_ncc_order": 'rev',
        "tools_ncc_operation": 'clear',
        "tools_ncc_overlap": 40,
        "tools_ncc_margin": 1.0,
        "tools_ncc_method": 1,  # SEED
        "tools_ncc_connect": True,
        "tools_ncc_contour": True,
        "tools_ncc_rest": False,
        "tools_ncc_offset_choice": False,
        "tools_ncc_offset_value": 0.0000,
        "tools_ncc_ref": 0,     # ITSELF
        "tools_ncc_area_shape": "square",
        "tools_ncc_milling_type": 'cl',
        "tools_ncc_tool_type": 'C1',
        "tools_ncc_cutz": -0.05,
        "tools_ncc_tipdia": 0.1,
        "tools_ncc_tipangle": 30,
        "tools_ncc_newdia": 0.1,
        "tools_ncc_plotting": 'normal',
        "tools_ncc_check_valid": True,

        # Cutout Tool
        "tools_cutout_tooldia": 2.4,
        "tools_cutout_kind": "single",
        "tools_cutout_margin": 0.1,
        "tools_cutout_z": -1.8,
        "tools_cutout_depthperpass": 0.6,
        "tools_cutout_mdepth": True,
        "tools_cutout_gapsize": 4,
        "tools_cutout_gaps_ff": "4",
        "tools_cutout_convexshape": False,
        "tools_cutout_big_cursor": True,
        "tools_cutout_gap_type": 'b',
        "tools_cutout_gap_depth": -1.0,
        "tools_cutout_mb_dia": 0.6,
        "tools_cutout_mb_spacing": 0.3,

        # Paint Tool
        "tools_paint_tooldia": 0.3,
        "tools_paint_order": 'rev',
        "tools_paint_overlap": 20,
        "tools_paint_offset": 0.0,
        "tools_paint_method": 0,
        "tools_paint_selectmethod": 0,
        "tools_paint_area_shape": "square",
        "tools_paint_connect": True,
        "tools_paint_contour": True,
        "tools_paint_plotting": 'normal',
        "tools_paint_rest": False,
        "tools_paint_tool_type": 'C1',
        "tools_paint_cutz": -0.05,
        "tools_paint_tipdia": 0.1,
        "tools_paint_tipangle": 30,
        "tools_paint_newdia": 0.1,

        # 2-Sided Tool
        "tools_2sided_mirror_axis": "X",
        "tools_2sided_axis_loc": "point",
        "tools_2sided_drilldia": 3.125,
        "tools_2sided_allign_axis": "X",

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
        "tools_film_png_dpi": 96,

        # Panel Tool
        "tools_panelize_spacing_columns": 0.0,
        "tools_panelize_spacing_rows": 0.0,
        "tools_panelize_columns": 1,
        "tools_panelize_rows": 1,
        "tools_panelize_optimization": True,
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
        "tools_calc_electro_area": 100.0,
        "tools_calc_electro_cdensity": 13.0,
        "tools_calc_electro_growth": 10.0,

        # Transform Tool
        "tools_transform_reference": _("Selection"),
        "tools_transform_ref_object": _("Gerber"),
        "tools_transform_ref_point": "0, 0",

        "tools_transform_rotate": 90,
        "tools_transform_skew_x": 0.0,
        "tools_transform_skew_y": 0.0,
        "tools_transform_skew_link": True,

        "tools_transform_scale_x": 1.0,
        "tools_transform_scale_y": 1.0,
        "tools_transform_scale_link": True,

        "tools_transform_offset_x": 0.0,
        "tools_transform_offset_y": 0.0,

        "tools_transform_buffer_dis": 0.0,
        "tools_transform_buffer_factor": 100.0,
        "tools_transform_buffer_corner": True,

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
        "tools_sub_delete_sources": False,

        # Distance Tool
        "tools_dist_snap_center": False,

        # Corner Markers Tool
        "tools_corners_thickness": 0.1,
        "tools_corners_length": 3.0,
        "tools_corners_margin": 0.0,
        "tools_corners_type": 's',
        "tools_corners_drill_dia": 0.5,

        # ########################################################################################################
        # ################################ TOOLS 2 ###############################################################
        # ########################################################################################################

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
        "tools_copper_thieving_area": 0.1,
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
        "tools_copper_thieving_mask_clearance": 0.0,
        "tools_copper_thieving_geo_choice": 'b',

        # Fiducials Tool
        "tools_fiducials_dia": 1.0,
        "tools_fiducials_margin": 1.0,
        "tools_fiducials_mode": 'auto',
        "tools_fiducials_second_pos": 'up',
        "tools_fiducials_type": 'circular',
        "tools_fiducials_line_thickness": 0.25,

        # Calibration Tool
        "tools_cal_calsource": 'object',
        "tools_cal_travelz": 2.0,
        "tools_cal_verz": 0.1,
        "tools_cal_zeroz": False,
        "tools_cal_toolchangez": 15,
        "tools_cal_toolchange_xy": '',
        "tools_cal_sec_point": 'tl',

        # Drills Extraction Tool
        "tools_edrills_hole_type": 'fixed',
        "tools_edrills_hole_fixed_dia": 0.5,
        "tools_edrills_hole_prop_factor": 80.0,
        "tools_edrills_circular_ring": 0.2,
        "tools_edrills_oblong_ring": 0.2,
        "tools_edrills_square_ring": 0.2,
        "tools_edrills_rectangular_ring": 0.2,
        "tools_edrills_others_ring": 0.2,
        "tools_edrills_circular": True,
        "tools_edrills_oblong": False,
        "tools_edrills_square": False,
        "tools_edrills_rectangular": False,
        "tools_edrills_others": False,

        # Punch Gerber Tool
        "tools_punch_hole_type": 'exc',
        "tools_punch_hole_fixed_dia": 0.5,
        "tools_punch_hole_prop_factor": 80.0,
        "tools_punch_circular_ring": 0.2,
        "tools_punch_oblong_ring": 0.2,
        "tools_punch_square_ring": 0.2,
        "tools_punch_rectangular_ring": 0.2,
        "tools_punch_others_ring": 0.2,
        "tools_punch_circular": True,
        "tools_punch_oblong": False,
        "tools_punch_square": True,
        "tools_punch_rectangular": False,
        "tools_punch_others": False,

        # Align Objects Tool
        "tools_align_objects_align_type": 'sp',

        # Invert Gerber Tool
        "tools_invert_margin": 0.1,
        "tools_invert_join_style": 's',

        # Utilities
        # file associations
        "fa_excellon": 'drd, drill, drl, exc, ncd, tap, xln',
        "fa_gcode": 'cnc, din, dnc, ecs, eia, fan, fgc, fnc, gc, gcd, gcode, h, hnc, i, min, mpf, mpr, nc, ncc, '
                    'ncg, ncp, ngc, out, ply, rol, sbp, tap, xpi',
        "fa_gerber": 'art, bot, bsm, cmp, crc, crs, dim, gb0, gb1, gb2, gb3, gb4, gb5, gb6, gb7, gb8, gb9, gbd, '
                     'gbl, gbo, gbp, gbr, gbs, gdo, ger, gko, gm1, gm2, gm3, grb, gtl, gto, gtp, gts, ly15, ly2, '
                     'mil, outline, pho, plc, pls, smb, smt, sol, spb, spt, ssb, sst, stc, sts, top, tsm',
        # Keyword list
        "util_autocomplete_keywords": 'Desktop, Documents, FlatConfig, FlatPrj, False, '
                                      'Marius, My Documents, Paste_1, '
                                      'Repetier, Roland_MDX_20, True, Users, Toolchange_Custom, '
                                      'Toolchange_Probe_MACH3, '
                                      'Toolchange_manual, Users, all, axis, auto, axisoffset, '
                                      'box, center_x, center_y, columns, combine, connect, contour, default, '
                                      'depthperpass, dia, diatol, dist, drilled_dias, drillz, dpp, dwelltime, '
                                      'endxy, endz, extracut_length, f, feedrate, '
                                      'feedrate_z, grbl_11, GRBL_laser, gridoffsety, gridx, gridy, has_offset, '
                                      'holes, hpgl, iso_type, line_xyz, margin, marlin, method, milled_dias, '
                                      'minoffset, name, offset, opt_type, order, outname, overlap, '
                                      'passes, postamble, pp, ppname_e, ppname_g, preamble, radius, ref, rest, '
                                      'rows, shellvar_, scale_factor, spacing_columns, spacing_rows, spindlespeed, '
                                      'startz, startxy, toolchange_xy, toolchangez, '
                                      'tooldia, travelz, use_threads, value, x, x0, x1, y, y0, y1, z_cut, '
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
    }

    @classmethod
    def save_factory_defaults(cls, file_path: str, version: (float, str)):
        """Writes the factory defaults to a file at the given path, overwriting any existing file."""
        # If the file exists
        if os.path.isfile(file_path):
            # tst if it is empty
            with open(file_path, "r") as file:
                f_defaults = simplejson.loads(file.read())

            # if the file is not empty
            if f_defaults:
                # if it has the same version do nothing
                if str(f_defaults['version']) == str(version):
                    return
                # if the versions differ then remove the file
                os.chmod(file_path, stat.S_IRWXO | stat.S_IWRITE | stat.S_IWGRP)
                os.remove(file_path)

        cls.factory_defaults['version'] = version

        try:
            # recreate a new factory defaults file and save the factory defaults data into it
            f_f_def_s = open(file_path, "w")
            simplejson.dump(cls.factory_defaults, f_f_def_s, default=to_dict, indent=2, sort_keys=True)
            f_f_def_s.close()

            # and then make the factory_defaults.FlatConfig file read_only
            # so it can't be modified after creation.
            os.chmod(file_path, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)
            log.debug("FlatCAM factory defaults written to: %s" % file_path)
        except Exception as e:
            log.error("save_factory_defaults() -> %s" % str(e))

    def __init__(self, callback=lambda x: None, beta=True, version=8.9):
        """

        :param callback:    A method called each time that one of the values are changed in the self.defaults LouDict
        """
        self.defaults = LoudDict()

        self.beta = beta
        self.version = version
        self.factory_defaults['version'] = self.version

        self.defaults.update(self.factory_defaults)
        self.current_defaults = {}  # copy used for restoring after cancelled prefs changes
        self.current_defaults.update(self.factory_defaults)
        self.old_defaults_found = False

        self.defaults.set_change_callback(callback)

    # #### Pass-through to the defaults LoudDict #####
    def __len__(self):
        return self.defaults.__len__()

    def __getitem__(self, item):
        return self.defaults.__getitem__(item)

    def __setitem__(self, key, value):
        return self.defaults.__setitem__(key, value)

    def __delitem__(self, key):
        return self.defaults.__delitem__(key)

    def __iter__(self):
        return self.defaults.__iter__()

    def __getattr__(self, item):
        # Unfortunately this method alone is not enough to pass through the other magic methods above.
        return self.defaults.__getattribute__(item)

    # #### Additional Methods #####
    def write(self, filename: str):
        """Saves the defaults to a file on disk"""
        with open(filename, "w") as file:
            simplejson.dump(self.defaults, file, default=to_dict, indent=2, sort_keys=True)

    def load(self, filename: str, inform):
        """
        Loads the defaults from a file on disk, performing migration if required.

        :param filename:    a path to the file that is to be loaded
        :param inform:      a pyqtSignal used to display information's in the StatusBar of the GUI
        """

        # Read in the file
        try:
            f = open(filename)
            options = f.read()
            f.close()
        except IOError:
            log.error("Could not load defaults file.")
            inform.emit('[ERROR] %s' % _("Could not load the file."))
            # in case the defaults file can't be loaded, show all toolbars
            self.defaults["global_toolbar_view"] = 511
            return

        # Parse the JSON
        try:
            defaults = simplejson.loads(options)
        except Exception:
            # in case the defaults file can't be loaded, show all toolbars
            self.defaults["global_toolbar_view"] = 511
            e = sys.exc_info()[0]
            log.error(str(e))
            inform.emit('[ERROR] %s' % _("Failed to parse defaults file."))
            return
        if defaults is None:
            return

        # Perform migration if necessary but only if the defaults dict is not empty
        if self.__is_old_defaults(defaults) and defaults:
            self.old_defaults_found = True

            # while the app is in Beta status, delete the older Preferences files
            if self.beta is False:
                log.debug("Found old preferences files. Migrating.")
                defaults = self.__migrate_old_defaults(defaults=defaults)
                # Save the resulting defaults
                self.defaults.update(defaults)
                self.current_defaults.update(self.defaults)
            else:
                log.debug("Found old preferences files. Resetting the files.")
                # wipeout the old defaults
                self.reset_to_factory_defaults()
        else:
            self.old_defaults_found = False

            # Save the resulting defaults
            self.defaults.update(defaults)
            self.current_defaults.update(self.defaults)

        log.debug("FlatCAM defaults loaded from: %s" % filename)

    def __is_old_defaults(self, defaults: dict) -> bool:
        """Takes a defaults dict and determines whether or not migration is necessary."""
        return 'version' not in defaults or defaults['version'] != self.factory_defaults['version']

    def __migrate_old_defaults(self, defaults: dict) -> dict:
        """Performs migration on the passed-in defaults dictionary, and returns the migrated dict"""
        migrated = {}
        for k, v in defaults.items():
            if k in self.factory_defaults and k != 'version':
                # check if the types are the same. Because some types (tuple, float, int etc)
                # may be stored as strings we check their types.
                try:
                    target = eval(self.defaults[k])
                except (NameError, TypeError, SyntaxError):
                    # it's an unknown string leave it as it is
                    target = deepcopy(self.factory_defaults[k])

                try:
                    source = eval(v)
                except (NameError, TypeError, SyntaxError):
                    # it's an unknown string leave it as it is
                    source = deepcopy(v)

                if type(target) == type(source):
                    migrated[k] = v
        return migrated

    def reset_to_factory_defaults(self):
        self.defaults.update(self.factory_defaults)
        self.current_defaults.update(self.factory_defaults)
        self.old_defaults_found = False

    def propagate_defaults(self):
        """
        This method is used to set default values in classes. It's
        an alternative to project options but allows the use
        of values invisible to the user.
        """
        log.debug("propagate_defaults()")

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
                except KeyError:
                    log.error("FlatCAMApp.propagate_defaults() --> ERROR: " + param + " not in defaults.")
            else:
                # Try extracting the name:
                # classname_param here is param in the object
                if param.find(routes[param].__name__.lower() + "_") == 0:
                    p = param[len(routes[param].__name__) + 1:]
                    if p in routes[param].defaults:
                        routes[param].defaults[p] = self.defaults[param]

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
