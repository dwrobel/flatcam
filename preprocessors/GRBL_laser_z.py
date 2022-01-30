# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# File Author: Matthieu Berthomé                           #
# Date: 5/26/2017                                          #
# Modified: Marius Stanciu                                 #
# Date: 01/19/2022                                         #
# MIT Licence                                              #
# ##########################################################

from appPreProcessor import *

# This post processor is configured to output code that
# is compatible with almost any version of Grbl.


class GRBL_laser_z(PreProc):

    include_header = True
    coordinate_format = "%.*f"
    feedrate_format = '%.*f'

    def start_code(self, p):
        units = ' ' + str(p['units']).lower()
        gcode = '(This preprocessor is used with a motion controller loaded with GRBL firmware. )\n'
        gcode += '(It is for the case when it is used together with a LASER connected on the SPINDLE connector.)\n'
        gcode += '(On toolchange event the laser will move to a defined Z height to change the laser dot size.)\n\n'

        xmin = '%.*f' % (p.coords_decimals, p['options']['xmin'])
        xmax = '%.*f' % (p.coords_decimals, p['options']['xmax'])
        ymin = '%.*f' % (p.coords_decimals, p['options']['ymin'])
        ymax = '%.*f' % (p.coords_decimals, p['options']['ymax'])

        if p['use_ui'] is True and p['multigeo']:
            gcode += '\n(TOOLS DIAMETER: )\n'
            for tool, val in p['tools'].items():
                gcode += '(Tool: %s -> ' % str(tool) + 'Dia: %s' % str(val["tooldia"]) + ')\n'
            gcode += '\n(FEEDRATE: )\n'
            for tool, val in p['tools'].items():
                gcode += '(Tool: %s -> ' % str(tool) + 'Feedrate: %s' % \
                         str(val['data']["tools_mill_feedrate"]) + ')\n'
            gcode += '\n(Z FOCUS: )\n'
            for tool, val in p['tools'].items():
                gcode += '(Tool: %s -> ' % str(tool) + 'Z: %s' % \
                         str(val['data']["tools_mill_travelz"]) + ')\n'
            gcode += '\n(LASER POWER: )\n'
            for tool, val in p['tools'].items():
                gcode += '(Tool: %s -> ' % str(tool) + 'Power: %s' % \
                         str(val['data']["tools_mill_spindlespeed"]) + ')\n'
        else:
            gcode += '(Feedrate: ' + str(p['feedrate']) + units + '/min' + ')\n'
            gcode += '(Z Focus: ' + str(p['z_move']) + units + ')\n'
            gcode += '(Laser Power: %s)\n' % str(p['spindlespeed'])

        gcode += '\n'
        gcode += '(X-Y End: ' + str(p['xy_end']) + units + ')\n'
        gcode += '(Z End: ' + str(p['z_end']) + units + ')\n'
        gcode += '(Steps per circle: ' + str(p['steps_per_circle']) + ')\n'

        if str(p['options']['type']) == 'Excellon' or str(p['options']['type']) == 'Excellon Geometry':
            gcode += '(Preprocessor Excellon: ' + str(p['pp_excellon_name']) + ')\n'
        else:
            gcode += '(Preprocessor Geometry: ' + str(p['pp_geometry_name']) + ')\n' + '\n'

        gcode += '(X range: ' + '{: >9s}'.format(xmin) + ' ... ' + '{: >9s}'.format(xmax) + ' ' + units + ')\n'
        gcode += '(Y range: ' + '{: >9s}'.format(ymin) + ' ... ' + '{: >9s}'.format(ymax) + ' ' + units + ')\n\n'

        gcode += 'G20\n' if p.units.upper() == 'IN' else 'G21\n'
        gcode += 'G90\n'
        gcode += 'G17\n'
        gcode += 'G94'

        return gcode

    def startz_code(self, p):
        gcode = 'G0 Z' + self.coordinate_format % (p.coords_decimals, p.z_move)
        return gcode

    def lift_code(self, p):
        return 'M5'

    def down_code(self, p):
        if p.spindlespeed:
            return '%s S%s' % ('M3', str(p.spindlespeed))
        else:
            return 'M3'

    def toolchange_code(self, p):
        return 'G0 Z' + self.coordinate_format % (p.coords_decimals, p.z_move)

    def up_to_zero_code(self, p):
        return 'M5'

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
        return ('G0 ' + self.position_code(p)).format(**p)

    def linear_code(self, p):
        return ('G1 ' + self.position_code(p)).format(**p) + \
               ' F' + str(self.feedrate_format % (p.fr_decimals, p.feedrate))

    def end_code(self, p):
        coords_xy = p['xy_end']
        gcode = ('G0 Z' + self.feedrate_format % (p.fr_decimals, p.z_end) + "\n")

        if coords_xy and coords_xy != '':
            gcode += 'G0 X{x} Y{y}'.format(x=coords_xy[0], y=coords_xy[1]) + "\n"
        return gcode

    def feedrate_code(self, p):
        return 'G1 F' + str(self.feedrate_format % (p.fr_decimals, p.feedrate))

    def z_feedrate_code(self, p):
        return 'G1 F' + str(self.feedrate_format % (p.fr_decimals, p.z_feedrate))

    def spindle_code(self, p):
        if p.spindlespeed:
            return '%s S%s' % ('M3', str(p.spindlespeed))
        else:
            return 'M3'

    def dwell_code(self, p):
        return ''

    def spindle_stop_code(self, p):
        return 'M5'
