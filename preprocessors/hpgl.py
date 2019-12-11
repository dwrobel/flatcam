# ########################################################## ##
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 3/10/2019                                          #
# MIT Licence                                              #
# ########################################################## ##

from FlatCAMPostProc import *


# for Roland Preprocessors it is mandatory for the preprocessor name (python file and class name, both of them must be
# the same) to contain the following keyword, case-sensitive: 'Roland' without the quotes.
class hpgl(FlatCAMPostProc):

    coordinate_format = "%.*f"

    def start_code(self, p):
        gcode = 'IN;'
        return gcode

    def startz_code(self, p):
        return ''

    def lift_code(self, p):
        gcode = 'PU;' + '\n'
        return gcode

    def down_code(self, p):
        gcode = 'PD;' + '\n'
        return gcode

    def toolchange_code(self, p):
        return 'SP%d;' % int(p.tool)

    def up_to_zero_code(self, p):
        return ''

    def position_code(self, p):
        units = str(p['units']).lower()

        # we work only with METRIC units because HPGL mention only metric units so if FlatCAM units are INCH we
        # transform them in METRIC
        if units == 'in':
            x = p.x * 25.4
            y = p.y * 25.4
        else:
            x = p.x
            y = p.y

        # we need to have the coordinates as multiples of 0.025mm
        x = round(x / 0.025) * 25 / 1000
        y = round(y / 0.025) * 25 / 1000

        return ('PA' + self.coordinate_format + ',' + self.coordinate_format + ';') % \
               (p.coords_decimals, x, p.coords_decimals, y)

    def rapid_code(self, p):
        return self.position_code(p).format(**p)

    def linear_code(self, p):
        return self.position_code(p).format(**p)

    def end_code(self, p):
        gcode = self.position_code(p).format(**p)
        return gcode

    def feedrate_code(self, p):
        return ''

    def z_feedrate_code(self, p):
        return ''

    def feedrate_rapid_code(self, p):
        return ''

    def spindle_code(self, p):
        return ''

    def dwell_code(self, p):
        return ''

    def spindle_stop_code(self,p):
        return ''