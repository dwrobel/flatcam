# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# Website:      http://flatcam.org                         #
# File Author:  Marius Adrian Stanciu (c)                  #
# Date:         8-Feb-2020                                 #
# License:      MIT Licence                                #
# ##########################################################

from appPreProcessor import *


class Marlin_laser_z(PreProc):

    include_header = True
    coordinate_format = "%.*f"
    feedrate_format = '%.*f'
    feedrate_rapid_format = feedrate_format

    def start_code(self, p):
        units = ' ' + str(p['units']).lower()
        coords_xy = p['xy_toolchange']
        end_coords_xy = p['xy_end']
        gcode = ';This preprocessor is used with a motion controller loaded with MARLIN firmware.\n'
        gcode += ';It is for the case when it is used together with a LASER connected on the SPINDLE connector.\n' \
                 ';On toolchange event the laser will move to a defined Z height to change the laser dot size.\n\n'

        xmin = '%.*f' % (p.coords_decimals, p['options']['xmin'])
        xmax = '%.*f' % (p.coords_decimals, p['options']['xmax'])
        ymin = '%.*f' % (p.coords_decimals, p['options']['ymin'])
        ymax = '%.*f' % (p.coords_decimals, p['options']['ymax'])

        if p['use_ui'] is True and p['multigeo']:
            gcode += '\n;TOOLS DIAMETER: \n'
            for tool, val in p['tools'].items():
                gcode += ';Tool: %s -> ' % str(tool) + 'Dia: %s' % str(val["tooldia"]) + '\n'
            gcode += '\n;FEEDRATE: \n'
            for tool, val in p['tools'].items():
                gcode += ';Tool: %s -> ' % str(tool) + 'Feedrate: %s' % \
                         str(val['data']["tools_mill_feedrate"]) + '\n'
            gcode += '\n;FEEDRATE RAPIDS: \n'
            for tool, val in p['tools'].items():
                gcode += '(Tool: %s -> ' % str(tool) + 'Feedrate rapids: %s' % \
                         str(val['data']["tools_mill_feedrate_rapid"]) + '\n'
            gcode += '\n;Z FOCUS: \n'
            for tool, val in p['tools'].items():
                gcode += ';Tool: %s -> ' % str(tool) + 'Z: %s' % \
                         str(val['data']["tools_mill_travelz"]) + '\n'
            gcode += '\n;LASER POWER: \n'
            for tool, val in p['tools'].items():
                gcode += ';Tool: %s -> ' % str(tool) + 'Power: %s' % \
                         str(val['data']["tools_mill_spindlespeed"]) + '\n'
            gcode += '\n;LASER MIN POWER: \n'
            for tool, val in p['tools'].items():
                if str(p['options']['type']) == 'Excellon':
                    gcode += ';Tool: %s -> ' % str(tool) + 'Power: %s' % \
                             str(val['data']["tools_drill_min_power"]) + '\n'
                else:
                    gcode += ';Tool: %s -> ' % str(tool) + 'Power: %s' % \
                             str(val['data']["tools_mill_min_power"]) + '\n'
        else:
            gcode += ';Feedrate: %s %s/min\n' % (str(p['feedrate']), units)
            gcode += ';Feedrate rapids: %s %s/min\n\n' % (str(p['feedrate_rapid']), units)
            gcode += ';Z Focus: %s %s\n' % (str(p['z_move']), units)
            gcode += ';Laser Power: %s\n' % str(p['spindlespeed'])
            gcode += ';Laser Minimum Power: %s\n\n' % str(p['laser_min_power'])

        gcode += '\n'
        if coords_xy is not None:
            gcode += ';X,Y Toolchange: ' + "%.*f, %.*f%s\n" % \
                     (p.decimals, coords_xy[0], p.decimals, coords_xy[1], units)
        else:
            gcode += ';X,Y End: None %s\n' % units
        if end_coords_xy is not None:
            gcode += ';X,Y End: ' + "%.*f, %.*f" % (p.decimals, end_coords_xy[0],
                                                    p.decimals, end_coords_xy[1]) + units + '\n'
        else:
            gcode += ';X,Y End: ' + "None" + units + '\n'
        gcode += ';Z End: ' + str(p['z_end']) + units + '\n'
        gcode += ';Steps per circle: ' + str(p['steps_per_circle']) + '\n'

        if str(p['options']['type']) == 'Excellon' or str(p['options']['type']) == 'Excellon Geometry':
            gcode += ';Preprocessor Excellon: ' + str(p['pp_excellon_name']) + '\n'
        else:
            gcode += ';Preprocessor Geometry: ' + str(p['pp_geometry_name']) + '\n'

        gcode += ';X range: ' + '{: >9s}'.format(xmin) + ' ... ' + '{: >9s}'.format(xmax) + ' ' + units + '\n'
        gcode += ';Y range: ' + '{: >9s}'.format(ymin) + ' ... ' + '{: >9s}'.format(ymax) + ' ' + units + '\n\n'

        gcode += 'G20\n' if p.units.upper() == 'IN' else 'G21\n'
        gcode += 'G90'

        return gcode

    def startz_code(self, p):
        if p.startz is not None:
            return 'G0 Z' + self.coordinate_format % (p.coords_decimals, p.z_move)
        else:
            return ''

    def lift_code(self, p):
        if float(p.laser_min_power) > 0.0:
            return 'M3 S%s' % str(p.laser_min_power)
        else:
            gcode = 'M400\n'
            gcode += 'M5'
            return gcode

    def down_code(self, p):
        if p.spindlespeed:
            return '%s S%s' % ('M3', str(p.spindlespeed))
        else:
            return 'M3'

    def toolchange_code(self, p):
        return 'G0 Z' + self.coordinate_format % (p.coords_decimals, p.z_move)

    def up_to_zero_code(self, p):
        if float(p.laser_min_power) > 0.0:
            return 'M3 S%s' % str(p.laser_min_power)
        else:
            gcode = 'M400\n'
            gcode += 'M5'
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
        return ('G0 ' + self.position_code(p)).format(**p) + " " + self.feedrate_rapid_code(p)

    def linear_code(self, p):
        return ('G1 ' + self.position_code(p)).format(**p) + " " + self.inline_feedrate_code(p)

    def end_code(self, p):
        coords_xy = p['xy_end']
        gcode = ('G0 Z' + self.feedrate_format % (p.fr_decimals, p.z_end) + " " + self.feedrate_rapid_code(p) + "\n")

        if coords_xy and coords_xy != '':
            gcode += 'G0 X{x} Y{y}'.format(x=coords_xy[0], y=coords_xy[1]) + " " + self.feedrate_rapid_code(p) + "\n"

        return gcode

    def feedrate_code(self, p):
        return 'G1 F' + str(self.feedrate_format % (p.fr_decimals, p.feedrate))

    def z_feedrate_code(self, p):
        return 'G1 F' + str(self.feedrate_format % (p.fr_decimals, p.z_feedrate))

    def inline_feedrate_code(self, p):
        return 'F' + self.feedrate_format % (p.fr_decimals, p.feedrate)

    def feedrate_rapid_code(self, p):
        return 'F' + self.feedrate_rapid_format % (p.fr_decimals, p.feedrate_rapid)

    def spindle_code(self, p):
        if p.spindlespeed:
            return '%s S%s' % ('M3', str(p.spindlespeed))
        else:
            return 'M3'

    def dwell_code(self, p):
        return ''

    def spindle_stop_code(self, p):
        if float(p.laser_min_power) > 0.0:
            return 'M3 S%s' % str(p.laser_min_power)
        else:
            gcode = 'M400\n'
            gcode += 'M5'
            return gcode
