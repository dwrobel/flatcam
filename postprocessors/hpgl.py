from FlatCAMPostProc import *


# for Roland Postprocessors it is mandatory for the postprocessor name (python file and class name, both of them must be
# the same) to contain the following keyword, case-sensitive: 'Roland' without the quotes.
class hpgl(FlatCAMPostProc):

    coordinate_format = "%.*f"
    feedrate_format = '%.1f'
    feedrate_rapid_format = '%.1f'

    def start_code(self, p):
        gcode = 'IN;'
        return gcode

    def startz_code(self, p):
        return 'SP%d' % int(p.tool)

    def lift_code(self, p):
        gcode = 'PU;' + '\n'
        return gcode

    def down_code(self, p):
        gcode = 'PD;' + '\n'
        return gcode

    def toolchange_code(self, p):
        return ''

    def up_to_zero_code(self, p):
        return ''

    def position_code(self, p):
        return ('PA' + self.coordinate_format + ',' + self.coordinate_format) % \
               (p.coords_decimals, p.x, p.coords_decimals, p.y)

    def rapid_code(self, p):
        return self.position_code(p).format(**p)

    def linear_code(self, p):
        return self.position_code(p).format(**p)

    def end_code(self, p):
        gcode = self.position_code(p).format(**p)
        return gcode

    def feedrate_code(self, p):
        return ''

    def feedrate_z_code(self, p):
        return ''

    def feedrate_rapid_code(self, p):
        return ''

    def spindle_code(self, p):
        return ''

    def dwell_code(self, p):
        return ''

    def spindle_stop_code(self,p):
        return ''
