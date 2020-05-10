import os
from typing import Any, Dict

from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtCore import QSettings
from defaults import FlatCAMDefaults
import logging

import gettext
import FlatCAMTranslation as fcTranslate
import builtins

from flatcamGUI.preferences.OptionUI import OptionUI

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

settings = QSettings("Open Source", "FlatCAM")
if settings.contains("machinist"):
    machinist_setting = settings.value('machinist', type=int)
else:
    machinist_setting = 0

log = logging.getLogger('PreferencesUIManager')

class PreferencesUIManager:

    def __init__(self, defaults: FlatCAMDefaults, data_path: str, ui, inform):
        """
        Class that control the Preferences Tab

        :param defaults:    a dictionary storage where all the application settings are stored
        :param data_path:   a path to the file where all the preferences are stored for persistence
        :param ui:          reference to the FlatCAMGUI class which constructs the UI
        :param inform:      a pyqtSignal used to display information in the StatusBar of the GUI
        """

        self.defaults = defaults
        self.data_path = data_path
        self.ui = ui
        self.inform = inform
        self.ignore_tab_close_event = False

        # if Preferences are changed in the Edit -> Preferences tab the value will be set to True
        self.preferences_changed_flag = False

        # when adding entries here read the comments in the  method found below named:
        # def new_object(self, kind, name, initialize, active=True, fit=True, plot=True)
        self.defaults_form_fields = {

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

            # NCC Tool
            "tools_ncctools": self.ui.tools_defaults_form.tools_ncc_group.ncc_tool_dia_entry,
            "tools_nccorder": self.ui.tools_defaults_form.tools_ncc_group.ncc_order_radio,
            "tools_nccoverlap": self.ui.tools_defaults_form.tools_ncc_group.ncc_overlap_entry,
            "tools_nccmargin": self.ui.tools_defaults_form.tools_ncc_group.ncc_margin_entry,
            "tools_nccmethod": self.ui.tools_defaults_form.tools_ncc_group.ncc_method_combo,
            "tools_nccconnect": self.ui.tools_defaults_form.tools_ncc_group.ncc_connect_cb,
            "tools_ncccontour": self.ui.tools_defaults_form.tools_ncc_group.ncc_contour_cb,
            "tools_nccrest": self.ui.tools_defaults_form.tools_ncc_group.ncc_rest_cb,
            "tools_ncc_offset_choice": self.ui.tools_defaults_form.tools_ncc_group.ncc_choice_offset_cb,
            "tools_ncc_offset_value": self.ui.tools_defaults_form.tools_ncc_group.ncc_offset_spinner,
            "tools_nccref": self.ui.tools_defaults_form.tools_ncc_group.select_combo,
            "tools_ncc_area_shape": self.ui.tools_defaults_form.tools_ncc_group.area_shape_radio,
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
            "tools_cutout_z": self.ui.tools_defaults_form.tools_cutout_group.cutz_entry,
            "tools_cutout_depthperpass": self.ui.tools_defaults_form.tools_cutout_group.maxdepth_entry,
            "tools_cutout_mdepth": self.ui.tools_defaults_form.tools_cutout_group.mpass_cb,
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
            "tools_paint_area_shape": self.ui.tools_defaults_form.tools_paint_group.area_shape_radio,
            "tools_pathconnect": self.ui.tools_defaults_form.tools_paint_group.pathconnect_cb,
            "tools_paintcontour": self.ui.tools_defaults_form.tools_paint_group.contour_cb,
            "tools_paint_plotting": self.ui.tools_defaults_form.tools_paint_group.paint_plotting_radio,

            "tools_paintrest": self.ui.tools_defaults_form.tools_paint_group.rest_cb,
            "tools_painttool_type": self.ui.tools_defaults_form.tools_paint_group.tool_type_radio,
            "tools_paintcutz": self.ui.tools_defaults_form.tools_paint_group.cutz_entry,
            "tools_painttipdia": self.ui.tools_defaults_form.tools_paint_group.tipdia_entry,
            "tools_painttipangle": self.ui.tools_defaults_form.tools_paint_group.tipangle_entry,
            "tools_paintnewdia": self.ui.tools_defaults_form.tools_paint_group.newdia_entry,

            # 2-sided Tool
            "tools_2sided_mirror_axis": self.ui.tools_defaults_form.tools_2sided_group.mirror_axis_radio,
            "tools_2sided_axis_loc": self.ui.tools_defaults_form.tools_2sided_group.axis_location_radio,
            "tools_2sided_drilldia": self.ui.tools_defaults_form.tools_2sided_group.drill_dia_entry,
            "tools_2sided_allign_axis": self.ui.tools_defaults_form.tools_2sided_group.align_axis_radio,

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
            "tools_transform_buffer_dis": self.ui.tools_defaults_form.tools_transform_group.buffer_entry,
            "tools_transform_buffer_factor": self.ui.tools_defaults_form.tools_transform_group.buffer_factor_entry,
            "tools_transform_buffer_corner": self.ui.tools_defaults_form.tools_transform_group.buffer_rounded_cb,

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

            # #######################################################################################################
            # ########################################## TOOLS 2 ####################################################
            # #######################################################################################################

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
            "tools_copper_thieving_mask_clearance": self.ui.tools2_defaults_form.tools2_cfill_group.clearance_ppm_entry,

            # Fiducials Tool
            "tools_fiducials_dia": self.ui.tools2_defaults_form.tools2_fiducials_group.dia_entry,
            "tools_fiducials_margin": self.ui.tools2_defaults_form.tools2_fiducials_group.margin_entry,
            "tools_fiducials_mode": self.ui.tools2_defaults_form.tools2_fiducials_group.mode_radio,
            "tools_fiducials_second_pos": self.ui.tools2_defaults_form.tools2_fiducials_group.pos_radio,
            "tools_fiducials_type": self.ui.tools2_defaults_form.tools2_fiducials_group.fid_type_radio,
            "tools_fiducials_line_thickness": self.ui.tools2_defaults_form.tools2_fiducials_group.line_thickness_entry,

            # Calibration Tool
            "tools_cal_calsource": self.ui.tools2_defaults_form.tools2_cal_group.cal_source_radio,
            "tools_cal_travelz": self.ui.tools2_defaults_form.tools2_cal_group.travelz_entry,
            "tools_cal_verz": self.ui.tools2_defaults_form.tools2_cal_group.verz_entry,
            "tools_cal_zeroz": self.ui.tools2_defaults_form.tools2_cal_group.zeroz_cb,
            "tools_cal_toolchangez": self.ui.tools2_defaults_form.tools2_cal_group.toolchangez_entry,
            "tools_cal_toolchange_xy": self.ui.tools2_defaults_form.tools2_cal_group.toolchange_xy_entry,
            "tools_cal_sec_point": self.ui.tools2_defaults_form.tools2_cal_group.second_point_radio,

            # Extract Drills Tool
            "tools_edrills_hole_type": self.ui.tools2_defaults_form.tools2_edrills_group.hole_size_radio,
            "tools_edrills_hole_fixed_dia": self.ui.tools2_defaults_form.tools2_edrills_group.dia_entry,
            "tools_edrills_hole_prop_factor": self.ui.tools2_defaults_form.tools2_edrills_group.factor_entry,
            "tools_edrills_circular_ring": self.ui.tools2_defaults_form.tools2_edrills_group.circular_ring_entry,
            "tools_edrills_oblong_ring": self.ui.tools2_defaults_form.tools2_edrills_group.oblong_ring_entry,
            "tools_edrills_square_ring": self.ui.tools2_defaults_form.tools2_edrills_group.square_ring_entry,
            "tools_edrills_rectangular_ring": self.ui.tools2_defaults_form.tools2_edrills_group.rectangular_ring_entry,
            "tools_edrills_others_ring": self.ui.tools2_defaults_form.tools2_edrills_group.other_ring_entry,
            "tools_edrills_circular": self.ui.tools2_defaults_form.tools2_edrills_group.circular_cb,
            "tools_edrills_oblong": self.ui.tools2_defaults_form.tools2_edrills_group.oblong_cb,
            "tools_edrills_square": self.ui.tools2_defaults_form.tools2_edrills_group.square_cb,
            "tools_edrills_rectangular": self.ui.tools2_defaults_form.tools2_edrills_group.rectangular_cb,
            "tools_edrills_others": self.ui.tools2_defaults_form.tools2_edrills_group.other_cb,

            # Punch Gerber Tool
            "tools_punch_hole_type": self.ui.tools2_defaults_form.tools2_punch_group.hole_size_radio,
            "tools_punch_hole_fixed_dia": self.ui.tools2_defaults_form.tools2_punch_group.dia_entry,
            "tools_punch_hole_prop_factor": self.ui.tools2_defaults_form.tools2_punch_group.factor_entry,
            "tools_punch_circular_ring": self.ui.tools2_defaults_form.tools2_punch_group.circular_ring_entry,
            "tools_punch_oblong_ring": self.ui.tools2_defaults_form.tools2_punch_group.oblong_ring_entry,
            "tools_punch_square_ring": self.ui.tools2_defaults_form.tools2_punch_group.square_ring_entry,
            "tools_punch_rectangular_ring": self.ui.tools2_defaults_form.tools2_punch_group.rectangular_ring_entry,
            "tools_punch_others_ring": self.ui.tools2_defaults_form.tools2_punch_group.other_ring_entry,
            "tools_punch_circular": self.ui.tools2_defaults_form.tools2_punch_group.circular_cb,
            "tools_punch_oblong": self.ui.tools2_defaults_form.tools2_punch_group.oblong_cb,
            "tools_punch_square": self.ui.tools2_defaults_form.tools2_punch_group.square_cb,
            "tools_punch_rectangular": self.ui.tools2_defaults_form.tools2_punch_group.rectangular_cb,
            "tools_punch_others": self.ui.tools2_defaults_form.tools2_punch_group.other_cb,

            # Invert Gerber Tool
            "tools_invert_margin": self.ui.tools2_defaults_form.tools2_invert_group.margin_entry,
            "tools_invert_join_style": self.ui.tools2_defaults_form.tools2_invert_group.join_radio,

            # Utilities
            # File associations
            "fa_excellon": self.ui.util_defaults_form.fa_excellon_group.exc_list_text,
            "fa_gcode": self.ui.util_defaults_form.fa_gcode_group.gco_list_text,
            # "fa_geometry": self.ui.util_defaults_form.fa_geometry_group.close_paths_cb,
            "fa_gerber": self.ui.util_defaults_form.fa_gerber_group.grb_list_text,
            "util_autocomplete_keywords": self.ui.util_defaults_form.kw_group.kw_list_text,

        }

        self.sections = [
            ui.general_defaults_form,
            ui.gerber_defaults_form,
            ui.excellon_defaults_form,
            ui.geometry_defaults_form,
            ui.cncjob_defaults_form,
            ui.tools_defaults_form,
            ui.tools2_defaults_form,
            ui.util_defaults_form
        ]

    def get_form_fields(self) -> Dict[str, Any]:
        result = {}
        result.update(self.defaults_form_fields)
        result.update(self._option_field_dict())
        return result

    def get_form_field(self, option: str) -> Any:
        return self.get_form_fields()[option]

    def option_dict(self) -> Dict[str, OptionUI]:
        result = {}
        for section in self.sections:
            sectionoptions = section.option_dict()
            result.update(sectionoptions)
        return result

    def _option_field_dict(self):
        result = {k: v.get_field() for k, v in self.option_dict().items()}
        return result

    def defaults_read_form(self):
        """
        Will read all the values in the Preferences GUI and update the defaults dictionary.

        :return: None
        """
        for option in self.get_form_fields():
            if option in self.defaults:
                try:
                    self.defaults[option] = self.get_form_field(option=option).get_value()
                except Exception as e:
                    log.debug("App.defaults_read_form() --> %s" % str(e))

    def defaults_write_form(self, factor=None, fl_units=None, source_dict=None):
        """
        Will set the values for all the GUI elements in Preferences GUI based on the values found in the
        self.defaults dictionary.

        :param factor: will apply a factor to the values that written in the GUI elements
        :param fl_units: current measuring units in FlatCAM: Metric or Inch
        :param source_dict: the repository of options, usually is the self.defaults
        :return: None
        """

        options_storage = self.defaults if source_dict is None else source_dict

        for option in options_storage:
            if source_dict:
                self.defaults_write_form_field(option, factor=factor, units=fl_units, defaults_dict=source_dict)
            else:
                self.defaults_write_form_field(option, factor=factor, units=fl_units)

    def defaults_write_form_field(self, field, factor=None, units=None, defaults_dict=None):
        """
        Basically it is the worker in the self.defaults_write_form()

        :param field: the GUI element in Preferences GUI to be updated
        :param factor: factor to be applied to the field parameter
        :param units: current FlatCAM measuring units
        :param defaults_dict: the defaults storage
        :return: None, it updates GUI elements
        """

        def_dict = self.defaults if defaults_dict is None else defaults_dict

        try:
            value = def_dict[field]
            log.debug("value is " + str(value) + " and factor is "+str(factor))
            if factor is not None:
                value *= factor

            form_field = self.get_form_field(option=field)
            if units is None:
                form_field.set_value(value)
            elif (units == 'IN' or units == 'MM') and (field == 'global_gridx' or field == 'global_gridy'):
                form_field.set_value(value)

        except KeyError:
            pass
        except AttributeError:
            log.debug(field)

    def show_preferences_gui(self):
        """
        Called to initialize and show the Preferences GUI

        :return: None
        """
        # FIXME this should be done in __init__

        for section in self.sections:
            tab = section.build_tab()
            tab.setObjectName(section.get_tab_id())
            self.ui.pref_tab_area.addTab(tab, section.get_tab_label())

        # Initialize the color box's color in Preferences -> Global -> Colo
        self.__init_color_pickers()

        # Button handlers
        self.ui.pref_save_button.clicked.connect(lambda: self.on_save_button(save_to_file=True))
        self.ui.pref_apply_button.clicked.connect(lambda: self.on_save_button(save_to_file=False))
        self.ui.pref_close_button.clicked.connect(self.on_pref_close_button)
        self.ui.pref_defaults_button.clicked.connect(self.on_restore_defaults_preferences)

        log.debug("Finished Preferences GUI form initialization.")

    def __init_color_pickers(self):
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

    def on_save_button(self, save_to_file=True):
        log.debug("on_save_button() --> Applying preferences to file.")

        # Preferences saved, update flag
        self.preferences_changed_flag = False

        # Preferences save, update the color of the Preferences Tab text
        for idx in range(self.ui.plot_tab_area.count()):
            if self.ui.plot_tab_area.tabText(idx) == _("Preferences"):
                self.ui.plot_tab_area.tabBar.setTabTextColor(idx, QtGui.QColor('black'))

        # restore the default stylesheet by setting a blank one
        self.ui.pref_apply_button.setStyleSheet("")

        self.inform.emit('%s' % _("Preferences applied."))

        # make sure we update the self.current_defaults dict used to undo changes to self.defaults
        self.defaults.current_defaults.update(self.defaults)

        # deal with theme change
        theme_settings = QtCore.QSettings("Open Source", "FlatCAM")
        if theme_settings.contains("theme"):
            theme = theme_settings.value('theme', type=str)
        else:
            theme = 'white'

        should_restart = False

        val = self.get_form_field("global_theme").get_value()
        if val != theme:
            msgbox = QtWidgets.QMessageBox()
            msgbox.setText(_("Are you sure you want to continue?"))
            msgbox.setWindowTitle(_("Application restart"))
            msgbox.setWindowIcon(QtGui.QIcon(self.ui.app.resource_location + '/warning.png'))

            bt_yes = msgbox.addButton(_('Yes'), QtWidgets.QMessageBox.YesRole)
            msgbox.addButton(_('Cancel'), QtWidgets.QMessageBox.NoRole)

            msgbox.setDefaultButton(bt_yes)
            msgbox.exec_()
            response = msgbox.clickedButton()

            if response == bt_yes:
                theme_settings.setValue('theme', val)

                # This will write the setting to the platform specific storage.
                del theme_settings

                should_restart = True
            else:
                self.ui.general_defaults_form.general_gui_group.theme_radio.set_value(theme)

        if save_to_file or should_restart is True:
            self.save_defaults(silent=False)
            # load the defaults so they are updated into the app
            self.defaults.load(filename=os.path.join(self.data_path, 'current_defaults.FlatConfig'))

        # Re-fresh project options
        self.ui.app.on_options_app2project()

        settgs = QSettings("Open Source", "FlatCAM")

        # save the notebook font size
        fsize = self.get_form_field("notebook_font_size").get_value()
        settgs.setValue('notebook_font_size', fsize)

        # save the axis font size
        g_fsize = self.get_form_field("axis_font_size").get_value()
        settgs.setValue('axis_font_size', g_fsize)

        # save the textbox font size
        tb_fsize = self.get_form_field("textbox_font_size").get_value()
        settgs.setValue('textbox_font_size', tb_fsize)

        settgs.setValue(
            'machinist',
            1 if self.get_form_field("global_machinist_setting").get_value() else 0
        )

        # This will write the setting to the platform specific storage.
        del settgs

        if save_to_file:
            # close the tab and delete it
            for idx in range(self.ui.plot_tab_area.count()):
                if self.ui.plot_tab_area.tabText(idx) == _("Preferences"):
                    self.ui.plot_tab_area.tabBar.setTabTextColor(idx, QtGui.QColor('black'))
                    self.ui.plot_tab_area.closeTab(idx)
                    break

        if should_restart is True:
            self.ui.app.on_app_restart()

    def on_pref_close_button(self):
        # Preferences saved, update flag
        self.preferences_changed_flag = False
        self.ignore_tab_close_event = True

        try:
            self.get_form_field("units").activated_custom.disconnect()
        except (TypeError, AttributeError):
            pass
        self.defaults_write_form(source_dict=self.defaults.current_defaults)
        self.get_form_field("units").activated_custom.connect(
            lambda: self.ui.app.on_toggle_units(no_pref=False))
        self.defaults.update(self.defaults.current_defaults)

        # Preferences save, update the color of the Preferences Tab text
        for idx in range(self.ui.plot_tab_area.count()):
            if self.ui.plot_tab_area.tabText(idx) == _("Preferences"):
                self.ui.plot_tab_area.tabBar.setTabTextColor(idx, QtGui.QColor('black'))
                self.ui.plot_tab_area.closeTab(idx)
                break

        self.inform.emit('%s' % _("Preferences closed without saving."))
        self.ignore_tab_close_event = False

    def on_restore_defaults_preferences(self):
        """
        Loads the application's factory default settings into ``self.defaults``.

        :return: None
        """
        log.debug("on_restore_defaults_preferences()")
        self.defaults.reset_to_factory_defaults()
        self.on_preferences_edited()
        self.inform.emit('[success] %s' % _("Preferences default values are restored."))

    def save_defaults(self, silent=False, data_path=None, first_time=False):
        """
        Saves application default options
        ``self.defaults`` to current_defaults.FlatConfig file.
        Save the toolbars visibility status to the preferences file (current_defaults.FlatConfig) to be
        used at the next launch of the application.

        :param silent:      Whether to display a message in status bar or not; boolean
        :param data_path:   The path where to save the preferences file (current_defaults.FlatConfig)
        When the application is portable it should be a mobile location.
        :param first_time:  Boolean. If True will execute some code when the app is run first time
        :return:            None
        """
        self.defaults.report_usage("save_defaults")

        if data_path is None:
            data_path = self.data_path

        self.defaults.propagate_defaults()

        if first_time is False:
            self.save_toolbar_view()

        # Save the options to disk
        filename = os.path.join(data_path, "current_defaults.FlatConfig")
        try:
            self.defaults.write(filename=filename)
        except Exception as e:
            log.error("save_defaults() --> Failed to write defaults to file %s" % str(e))
            self.inform.emit('[ERROR_NOTCL] %s %s' % (_("Failed to write defaults to file."), str(filename)))
            return

        if not silent:
            self.inform.emit('[success] %s' % _("Preferences saved."))

        # update the autosave timer
        self.ui.app.save_project_auto_update()

    def save_toolbar_view(self):
        """
        Will save the toolbar view state to the defaults

        :return:            None
        """

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

        self.defaults["global_toolbar_view"] = tb_status

    def on_preferences_edited(self):
        """
        Executed when a preference was changed in the Edit -> Preferences tab.
        Will color the Preferences tab text to Red color.
        :return:
        """
        if self.preferences_changed_flag is False:
            self.inform.emit('[WARNING_NOTCL] %s' % _("Preferences edited but not saved."))

            for idx in range(self.ui.plot_tab_area.count()):
                if self.ui.plot_tab_area.tabText(idx) == _("Preferences"):
                    self.ui.plot_tab_area.tabBar.setTabTextColor(idx, QtGui.QColor('red'))

            self.ui.pref_apply_button.setStyleSheet("QPushButton {color: red;}")

            self.preferences_changed_flag = True

    def on_close_preferences_tab(self):
        if self.ignore_tab_close_event:
            return

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

        # Prompt user to save
        if self.preferences_changed_flag is True:
            msgbox = QtWidgets.QMessageBox()
            msgbox.setText(_("One or more values are changed.\n"
                             "Do you want to save the Preferences?"))
            msgbox.setWindowTitle(_("Save Preferences"))
            msgbox.setWindowIcon(QtGui.QIcon(self.ui.app.resource_location + '/save_as.png'))

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
