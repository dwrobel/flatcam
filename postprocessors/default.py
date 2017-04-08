from FlatCAMPostProc import FlatCAMPostProc


class default(FlatCAMPostProc):
    def start_code(self, p):
        gcode = ('G20' if p.units else 'G21') + "\n"
        gcode += 'G90\n'
        gcode += 'G94'
        return gcode

    def lift_code(self, p):
        return 'G00 Z'+self.coordinate_format%p.z_move

    def down_code(self, p):
        return 'G01 Z'+self.coordinate_format%p.z_cut

    def toolchange_code(self, p):
        return """G00 Z{z_toolchange}
    T {tool}
    M5
    M6
    (MSG, Change to tool dia={toolC}
    M0""".format(z_toolchange=self.coordinate_format%p.z_toolchange,
                 tool=int(p.tool),
                 toolC=int(p.toolC))

    def up_to_zero_code(self, p):
        return 'G01 Z0'

    coordinate_format = "%.4f"
    feedrate_format = '%.2f'

    def position_code(self, p):
        return ('X' + self.coordinate_format + 'Y' + self.coordinate_format) % (p.x, p.y)

    def rapid_code(self, p):
        return ('G00 ' + self.position_code(p)).format(**p)

    def linear_code(self, p):
        return ('G01 ' + self.position_code(p)).format(**p)

    def end_code(self, p):
        return 'G00 X0Y0'

    def feedrate_code(self, p):
        return 'F' + self.feedrate_format % p.feedrate

    def spindle_code(self,p):
        if p.spindlespeed:
            return 'M03 S' + p.spindlespeed
        else:
            return 'M03'

    def spindle_stop_code(self,p):
        return 'M05'
