# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# Website:      http://flatcam.org                         #
# File Author:  Marius Adrian Stanciu (c)                  #
# Date:         8-Feb-2020                                 #
# License:      MIT Licence                                #
# ##########################################################

from appPreProcessor import *


class Marlin_laser_FAN_pin(PreProc):

    include_header = True
    coordinate_format = "%.*f"
    feedrate_format = '%.*f'
    feedrate_rapid_format = feedrate_format

    def start_code(self, p):
        units = ' ' + str(p['units']).lower()
        coords_xy = p['xy_toolchange']
        end_coords_xy = p['xy_end']
        gcode = ';This preprocessor is used with a motion controller loaded with MARLIN firmware.\n'
        gcode += ';It is for the case when it is used together with a LASER connected on one of the FAN pins.\n\n'

        xmin = '%.*f' % (p.coords_decimals, p['options']['xmin'])
        xmax = '%.*f' % (p.coords_decimals, p['options']['xmax'])
        ymin = '%.*f' % (p.coords_decimals, p['options']['ymin'])
        ymax = '%.*f' % (p.coords_decimals, p['options']['ymax'])

        gcode += ';Feedrate: ' + str(p['feedrate']) + units + '/min' + '\n'
        gcode += ';Feedrate rapids: ' + str(p['feedrate_rapid']) + units + '/min' + '\n\n'

        gcode += ';Z Focus: ' + str(p['z_move']) + units + '\n'

        gcode += ';Steps per circle: ' + str(p['steps_per_circle']) + '\n'

        if str(p['options']['type']) == 'Excellon' or str(p['options']['type']) == 'Excellon Geometry':
            gcode += ';Preprocessor Excellon: ' + str(p['pp_excellon_name']) + '\n'
        else:
            gcode += ';Preprocessor Geometry: ' + str(p['pp_geometry_name']) + '\n'
        if end_coords_xy is not None:
            gcode += '(X,Y End: ' + "%.*f, %.*f" % (p.decimals, end_coords_xy[0],
                                                    p.decimals, end_coords_xy[1]) + units + ')\n'
        else:
            gcode += '(X,Y End: ' + "None" + units + ')\n'
        gcode += '(Steps per circle: ' + str(p['steps_per_circle']) + ')\n'

        gcode += ';X range: ' + '{: >9s}'.format(xmin) + ' ... ' + '{: >9s}'.format(xmax) + ' ' + units + '\n'
        gcode += ';Y range: ' + '{: >9s}'.format(ymin) + ' ... ' + '{: >9s}'.format(ymax) + ' ' + units + '\n\n'

        gcode += ';Laser Power (Spindle Speed): ' + str(p['spindlespeed']) + '\n' + '\n'

        gcode += ('G20' if p.units.upper() == 'IN' else 'G21') + "\n"
        gcode += 'G90'

        return gcode

    def startz_code(self, p):
        if p.startz is not None:
            return 'G0 Z' + self.coordinate_format % (p.coords_decimals, p.z_move)
        else:
            return ''

    def lift_code(self, p):
        gcode = 'M400\n'
        gcode += 'M107'
        return gcode

    def down_code(self, p):
        if p.spindlespeed:
            return '%s S%s' % ('M106', str(p.spindlespeed))
        else:
            return 'M106'

    def toolchange_code(self, p):
        return ''

    def up_to_zero_code(self, p):
        gcode = 'M400\n'
        gcode += 'M107'
        return gcode

    def position_code(self, p):
        return ('X' + self.coordinate_format + ' Y' + self.coordinate_format) % \
               (p.coords_decimals, p.x, p.coords_decimals, p.y)

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
            return 'M106 S%s' % str(p.spindlespeed)
        else:
            return 'M106'

    def dwell_code(self, p):
        return ''

    def spindle_stop_code(self, p):
        gcode = 'M400\n'
        gcode += 'M106 S0'
        return gcode
