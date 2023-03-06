# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 3/10/2019                                          #
# MIT Licence                                              #
# ##########################################################

from appPreProcessor import AppPreProcTools


class Paste_Marlin(AppPreProcTools):

    include_header = True
    coordinate_format = "%.*f"
    feedrate_format = '%.*f'

    def start_code(self, p):
        units = ' ' + str(p['units']).lower()
        gcode = '(This preprocessor is used only with the SolderPaste Plugin and with MARLIN-like controllers.)\n\n'

        xmin = '%.*f' % (p.coords_decimals, p['obj_options']['xmin'])
        xmax = '%.*f' % (p.coords_decimals, p['obj_options']['xmax'])
        ymin = '%.*f' % (p.coords_decimals, p['obj_options']['ymin'])
        ymax = '%.*f' % (p.coords_decimals, p['obj_options']['ymax'])

        gcode += '\n;TOOLS DIAMETER: \n'
        for tool, val in p['tools'].items():
            gcode += ';Tool: %s -> ' % str(tool) + 'Dia: %s' % str(val["tooldia"]) + units + '\n'

        gcode += '\nMARGIN: ;\n'
        for tool, val in p['tools'].items():
            gcode += ';Tool: %s -> ' % str(tool) + 'Margin: %s' % str(
                val['data']["tools_solderpaste_margin"]) + '\n'

        gcode += '\n;FEEDRATE XY: \n'
        for tool, val in p['tools'].items():
            gcode += ';Tool: %s -> ' % str(tool) + 'Feedrate XY: %s' % \
                     str(val['data']["tools_solderpaste_frxy"]) + units + '/min' + '\n'

        gcode += '\n;FEEDRATE RAPIDS: \n'
        for tool, val in p['tools'].items():
            gcode += '(Tool: %s -> ' % str(tool) + 'Feedrate Rapids: %s' % \
                     str(val['data']["tools_solderpaste_fr_rapids"]) + units + '/min' + '\n'

        gcode += '\n;FEEDRATE Z: \n'
        for tool, val in p['tools'].items():
            gcode += '(Tool: %s -> ' % str(tool) + 'Feedrate Z: %s' % \
                     str(val['data']["tools_solderpaste_frz"]) + units + '/min' + '\n'

        gcode += '\n;FEEDRATE Z_DISPENSE: \n'
        for tool, val in p['tools'].items():
            gcode += ';Tool: %s -> ' % str(tool) + 'Feedrate Z_Dispense: %s' % \
                     str(val['data']["tools_solderpaste_frz_dispense"]) + units + '/min' + '\n'

        gcode += '\n;Z_DISPENSE START: \n'
        for tool, val in p['tools'].items():
            gcode += ';Tool: %s -> ' % str(tool) + 'Z_Dispense_Start: %s' % str(
                val['data']["tools_solderpaste_z_start"]) + units + '\n'

        gcode += '\n;Z_DISPENSE: \n'
        for tool, val in p['tools'].items():
            gcode += ';Tool: %s -> ' % str(tool) + 'Z_Dispense: %s' % str(
                val['data']["tools_solderpaste_z_dispense"]) + units + '\n'

        gcode += '\n;Z_DISPENSE STOP: \n'
        for tool, val in p['tools'].items():
            gcode += ';Tool: %s -> ' % str(tool) + 'Z_Dispense_Stop: %s' % str(
                val['data']["tools_solderpaste_z_stop"]) + units + '\n'

        gcode += '\n;Z_TRAVEL: \n'
        for tool, val in p['tools'].items():
            gcode += ';Tool: %s -> ' % str(tool) + 'Z_Travel: %s' % str(
                val['data']["tools_solderpaste_z_travel"]) + units + '\n'

        gcode += '\n;Z_TOOLCHANGE: \n'
        for tool, val in p['tools'].items():
            gcode += ';Tool: %s -> ' % str(tool) + 'Z_Toolchange: %s' % str(
                val['data']["tools_solderpaste_z_toolchange"]) + units + '\n'

        gcode += '\n;XY_TOOLCHANGE: \n'
        for tool, val in p['tools'].items():
            xy_tc_coords = val['data']["tools_solderpaste_xy_toolchange"]
            if isinstance(xy_tc_coords, str):
                temp_val = xy_tc_coords.replace('[', '').replace(']', '')
                coords_xy = [float(eval(a)) for a in temp_val.split(",") if a != '']
            else:
                coords_xy = xy_tc_coords

            xy_coords_formatted = "%.*f, %.*f" % (p.decimals, coords_xy[0], p.decimals, coords_xy[1])
            gcode += ';Tool: %s -> ' % str(tool) + 'X,Y Toolchange: %s' % xy_coords_formatted + units + '\n'

        gcode += '\n;Spindle Speed FWD: \n'
        for tool, val in p['tools'].items():
            gcode += ';Tool: %s -> ' % str(tool) + 'Spindle Speed FWD: %s RPM' % str(
                val['data']["tools_solderpaste_speedfwd"]) + units + '\n'

        gcode += '\n;Dwell FWD: \n'
        for tool, val in p['tools'].items():
            gcode += ';Tool: %s -> ' % str(tool) + 'Dwell FWD: %s' % str(
                val['data']["tools_solderpaste_dwellfwd"]) + units + '\n'

        gcode += '\n;Spindle Speed REV: \n'
        for tool, val in p['tools'].items():
            gcode += ';Tool: %s -> ' % str(tool) + 'Spindle Speed REV: %s RPM' % str(
                val['data']["tools_solderpaste_speedrev"]) + units + '\n'

        gcode += '\n;Dwell REV: \n'
        for tool, val in p['tools'].items():
            gcode += 'Tool: %s -> ' % str(tool) + 'Dwell REV: %s' % str(
                val['data']["tools_solderpaste_dwellrev"]) + units + '\n'

        if 'Paste' in p.pp_solderpaste_name:
            gcode += ';Preprocessor SolderPaste Dispensing Geometry: ' + str(p.pp_solderpaste_name) + '\n' + '\n'

        gcode += ';X range: ' + '{: >9s}'.format(xmin) + ' ... ' + '{: >9s}'.format(xmax) + ' ' + units + '\n'
        gcode += ';Y range: ' + '{: >9s}'.format(ymin) + ' ... ' + '{: >9s}'.format(ymax) + ' ' + units + '\n\n'

        gcode += ('G20\n' if p.units.upper() == 'IN' else 'G21\n')
        return gcode

    def lift_code(self, p):
        return 'G1 Z' + self.coordinate_format % (p.coords_decimals, float(p['z_travel'])) + \
               ' F%s' % str(p['fr_rapids'])

    def down_z_start_code(self, p):
        return 'G1 Z' + self.coordinate_format % (p.coords_decimals, float(p['z_start'])) + ' F%s' % str(p['frz'])

    def lift_z_dispense_code(self, p):
        return 'G01 Z' + self.coordinate_format % (p.coords_decimals, float(p['z_dispense'])) + \
               ' F%s' % str(p['frz_dispense'])

    def down_z_stop_code(self, p):
        return 'G1 Z' + self.coordinate_format % (p.coords_decimals, float(p['z_stop'])) + ' F%s' % str(p['frz'])

    def toolchange_code(self, p):
        fr_rapids = float(p['fr_rapids'])
        z_toolchange = float(p['z_toolchange'])

        if isinstance(p['xy_toolchange'], str):
            temp_val = p['xy_toolchange'].replace('[', '').replace(']', '')
            toolchangexy = [float(eval(a)) for a in temp_val.split(",") if a != '']
        else:
            toolchangexy = p['xy_toolchange']

        if toolchangexy is not None:
            x_toolchange = toolchangexy[0]
            y_toolchange = toolchangexy[1]
        else:
            x_toolchange = 0.0
            y_toolchange = 0.0

        toolC_formatted = '%.*f' % (p.decimals, float(p['toolC']))

        if toolchangexy is not None:
            gcode = """
;Toolchange: START
G1 Z{z_toolchange} F{fr_rapids}
G1 X{x_toolchange} Y{y_toolchange} F{fr_rapids}
T{tool}
M6    
;MSG, Change to Tool with Nozzle Dia = {toolC}
M0
G1 Z{z_toolchange} F{fr_rapids}
""".format(x_toolchange=self.coordinate_format % (p.coords_decimals, x_toolchange),
           y_toolchange=self.coordinate_format % (p.coords_decimals, y_toolchange),
           z_toolchange=self.coordinate_format % (p.coords_decimals, z_toolchange),
           tool=int(int(p.tool)),
           toolC=toolC_formatted,
           fr_rapids=fr_rapids)

        else:
            gcode = """
;Toolchange: START
G1 Z{z_toolchange} F{fr_rapids}
T{tool}
M6    
;MSG, Change to Tool with Nozzle Dia = {toolC}
M0
G1 Z{z_toolchange} F{fr_rapids}
""".format(z_toolchange=self.coordinate_format % (p.coords_decimals, z_toolchange),
           tool=int(int(p.tool)),
           toolC=toolC_formatted,
           fr_rapids=fr_rapids)

        return gcode

    def position_code(self, p):
        # formula for skewing on x for example is:
        # x_fin = x_init + y_init/slope where slope = p._bed_limit_y / p._bed_skew_x (a.k.a tangent)
        if p._bed_skew_x == 0:
            x_pos = p.x + p._bed_offset_x
        else:
            x_pos = (p.x + p._bed_offset_x) + ((p.y / p._bed_limit_y) * p._bed_skew_x)

        if p._bed_skew_y == 0:
            y_pos = p.y + p._bed_offset_y
        else:
            y_pos = (p.y + p._bed_offset_y) + ((p.x / p._bed_limit_x) * p._bed_skew_y)

        return ('X' + self.coordinate_format + ' Y' + self.coordinate_format) % \
               (p.coords_decimals, x_pos, p.coords_decimals, y_pos)

    def rapid_code(self, p):
        return ('G1 ' + self.position_code(p)).format(**p) + ' F%s' % str(p['fr_rapids']) + \
               '\nG1 Z' + self.coordinate_format % (p.coords_decimals, float(p['z_travel'])) + \
               ' F%s' % str(p['fr_rapids'])

    def linear_code(self, p):
        return ('G1 ' + self.position_code(p)).format(**p) + ' F' + \
               str(self.feedrate_format % (p.fr_decimals, float(p['frxy'])))

    def end_code(self, p):
        coords_xy = [float(eval(a)) for a in p['xy_end'].split(",") if a != '']
        gcode = ('G1 Z' + self.feedrate_format % (p.fr_decimals, float(p['z_toolchange'])) +
                 'F%s' % str(p['fr_rapids']) + "\n")

        if coords_xy and coords_xy != '':
            gcode += 'G1 X{x} Y{y}'.format(x=coords_xy[0], y=coords_xy[1]) + ' F%s' % str(p['fr_rapids']) + "\n"
        return gcode

    def feedrate_xy_code(self, p):
        return ''

    def z_feedrate_code(self, p):
        return 'G1 F' + str(self.feedrate_format % (p.fr_decimals, float(p['frz'])))

    def feedrate_z_dispense_code(self, p):
        return 'G1 F' + str(self.feedrate_format % (p.fr_decimals, float(p['frz_dispense'])))

    def spindle_fwd_code(self, p):
        if p.spindlespeed:
            return 'M3 S' + str(float(p['speedfwd']))
        else:
            return 'M3'

    def spindle_rev_code(self, p):
        if p.spindlespeed:
            return 'M4 S' + str(float(p['speedrev']))
        else:
            return 'M4'

    def spindle_off_code(self, p):
        return 'M5'

    def dwell_fwd_code(self, p):
        if p.dwelltime:
            return 'G4 P' + str(float(p['dwellfwd']))

    def dwell_rev_code(self, p):
        if p.dwelltime:
            return 'G4 P' + str(float(p['dwellrev']))
