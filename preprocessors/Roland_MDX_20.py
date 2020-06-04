# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 3/10/2019                                          #
# MIT Licence                                              #
# ##########################################################

from appPreProcessor import *


# for Roland Preprocessors it is mandatory for the preprocessor name (python file and class name, both of them must be
# the same) to contain the following keyword, case-sensitive: 'Roland' without the quotes.
class Roland_MDX_20(PreProc):

    include_header = False
    coordinate_format = "%.1f"
    feedrate_format = '%.1f'
    feedrate_rapid_format = '%.1f'

    def start_code(self, p):
        gcode = ';;^IN;' + '\n'
        gcode += '^PA;'
        return gcode

    def startz_code(self, p):
        return ''

    def lift_code(self, p):
        if p.units.upper() == 'IN':
            z = p.z_move / 25.4
        else:
            z = p.z_move
        gcode = self.feedrate_rapid_code(p) + '\n'
        gcode += self.position_code(p).format(**p) + ',' + str(float(z * 40.0)) + ';'
        return gcode

    def down_code(self, p):
        if p.units.upper() == 'IN':
            z = p.z_cut / 25.4
        else:
            z = p.z_cut
        gcode = self.feedrate_code(p) + '\n'
        gcode += self.position_code(p).format(**p) + ',' + str(float(z * 40.0)) + ';'
        return gcode

    def toolchange_code(self, p):
        return ''

    def up_to_zero_code(self, p):
        gcode = self.feedrate_code(p) + '\n'
        gcode += self.position_code(p).format(**p) + ',' + '0' + ';'
        return gcode

    def position_code(self, p):
        if p.units.upper() == 'IN':
            x = p.x / 25.4
            y = p.y / 25.4
        else:
            x = p.x
            y = p.y
        return ('Z' + self.coordinate_format + ',' + self.coordinate_format) % (float(x * 40.0), float(y * 40.0))

    def rapid_code(self, p):
        if p.units.upper() == 'IN':
            z = p.z_move / 25.4
        else:
            z = p.z_move
        gcode = self.feedrate_rapid_code(p) + '\n'
        gcode += self.position_code(p).format(**p) + ',' + str(float(z * 40.0)) + ';'
        return gcode

    def linear_code(self, p):
        if p.units.upper() == 'IN':
            z = p.z / 25.4
        else:
            z = p.z
        gcode = self.feedrate_code(p) + '\n'
        gcode += self.position_code(p).format(**p) + ',' + str(float(z * 40.0)) + ';'
        return gcode

    def end_code(self, p):
        if p.units.upper() == 'IN':
            z = p.z_end / 25.4
        else:
            z = p.z_end
        gcode = self.feedrate_rapid_code(p) + '\n'
        gcode += self.position_code(p).format(**p) + ',' + str(float(z * 40.0)) + ';'
        return gcode

    def feedrate_code(self, p):
        fr_sec = p.feedrate / 60

        # valid feedrate for MDX20 is between 0.1mm/sec and 15mm/sec (6mm/min to 900mm/min)
        if p.feedrate >= 900:
            fr_sec = 15
        if p.feedrate < 6:
            fr_sec = 6
        return 'V' + str(self.feedrate_format % fr_sec) + ';'

    def z_feedrate_code(self, p):
        fr_sec = p.z_feedrate / 60

        # valid feedrate for MDX20 is between 0.1mm/sec and 15mm/sec (6mm/min to 900mm/min)
        if p.z_feedrate >= 900:
            fr_sec = 15
        if p.z_feedrate < 6:
            fr_sec = 6
        return 'V' + str(self.feedrate_format % fr_sec) + ';'

    def feedrate_rapid_code(self, p):
        fr_sec = p.feedrate_rapid / 60

        # valid feedrate for MDX20 is between 0.1mm/sec and 15mm/sec (6mm/min to 900mm/min)
        if p.feedrate_rapid >= 900:
            fr_sec = 15
        if p.feedrate_rapid < 6:
            fr_sec = 6
        return 'V' + str(self.feedrate_format % fr_sec) + ';'

    def spindle_code(self, p):
        return '!MC1'

    def dwell_code(self, p):
        return''

    def spindle_stop_code(self, p):
        return '!MC0'
