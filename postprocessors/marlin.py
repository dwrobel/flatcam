from FlatCAMPostProc import *


class marlin(FlatCAMPostProc):

    coordinate_format = "%.*f"
    feedrate_format = '%.*f'
    feedrate_rapid_format = feedrate_format

    def start_code(self, p):
        units = ' ' + str(p['units']).lower()
        gcode = ''

        if str(p['options']['type']) == 'Geometry':
            gcode += ';TOOL DIAMETER: ' + str(p['options']['tool_dia']) + units + '\n' + '\n'

        gcode += ';Feedrate: ' + str(p['feedrate']) + units + '/min' + '\n'

        if str(p['options']['type']) == 'Geometry':
            gcode += ';Feedrate_Z: ' + str(p['feedrate_z']) + units + '/min' + '\n'

        gcode += ';Feedrate rapids ' + str(p['feedrate_rapid']) + units + '/min' + '\n' + '\n'
        gcode += ';Z_Cut: ' + str(p['z_cut']) + units + '\n'

        if str(p['options']['type']) == 'Geometry':
            if p['multidepth'] is True:
                gcode += ';DepthPerCut: ' + str(p['depthpercut']) + units + ' <=>' + \
                         str(math.ceil(abs(p['z_cut']) / p['depthpercut'])) + ' passes' + '\n'

        gcode += ';Z_Move: ' + str(p['z_move']) + units + '\n'
        gcode += ';Z Toolchange: ' + str(p['toolchangez']) + units + '\n'
        gcode += ';Z Start: ' + str(p['startz']) + units + '\n'
        gcode += ';Z End: ' + str(p['endz']) + units + '\n'
        gcode += ';Steps per circle: ' + str(p['steps_per_circle']) + '\n'

        if str(p['options']['type']) == 'Excellon' or str(p['options']['type']) == 'Excellon Geometry':
            gcode += ';Postprocessor Excellon: ' + str(p['pp_excellon_name']) + '\n'
        else:
            gcode += ';Postprocessor Geometry: ' + str(p['pp_geometry_name']) + '\n'

        gcode += ';Spindle Speed: ' + str(p['spindlespeed']) + ' RPM' + '\n' + '\n'

        gcode += ('G20' if p.units.upper() == 'IN' else 'G21') + "\n"
        gcode += 'G90\n'

        return gcode

    def startz_code(self, p):
        if p.startz is not None:
            return 'G0 Z' + self.coordinate_format % (p.coords_decimals, p.startz)
        else:
            return ''

    def lift_code(self, p):
        return 'G0 Z' + self.coordinate_format%(p.coords_decimals, p.z_move) + " " + self.feedrate_rapid_code(p)

    def down_code(self, p):
        return 'G1 Z' + self.coordinate_format%(p.coords_decimals, p.z_cut) + " " + self.end_feedrate_code(p)

    def toolchange_code(self, p):
        toolchangez = p.toolchangez
        no_drills = 1

        if int(p.tool) == 1 and p.startz is not None:
            toolchangez = p.startz

        if p.units.upper() == 'MM':
            toolC_formatted = format(p.toolC, '.2f')
        else:
            toolC_formatted = format(p.toolC, '.4f')

        for i in p['options']['Tools_in_use']:
            if i[0] == p.tool:
                no_drills = i[2]

        if str(p['options']['type']) == 'Excellon':
            return """G0 Z{toolchangez}
M5
M0 Change to Tool Dia = {toolC}, Total drills for current tool = {t_drills}
""".format(toolchangez=self.coordinate_format%(p.coords_decimals, toolchangez),
           tool=int(p.tool),
           t_drills=no_drills,
           toolC=toolC_formatted)
        else:
            return """G0 Z{toolchangez}
M5
M0 Change to Tool Dia = {toolC}
""".format(toolchangez=self.coordinate_format%(p.coords_decimals, toolchangez),
           tool=int(p.tool),
           toolC=toolC_formatted)

    def up_to_zero_code(self, p):
        return 'G1 Z0' + " " + self.feedrate_code(p)

    def position_code(self, p):
        return ('X' + self.coordinate_format + ' Y' + self.coordinate_format) % \
               (p.coords_decimals, p.x, p.coords_decimals, p.y)

    def rapid_code(self, p):
        return ('G0 ' + self.position_code(p)).format(**p) + " " + self.feedrate_rapid_code(p)

    def linear_code(self, p):
        return ('G1 ' + self.position_code(p)).format(**p) + " " + self.end_feedrate_code(p)

    def end_code(self, p):
        coords_xy = p['toolchange_xy']
        gcode = ('G0 Z' + self.feedrate_format %(p.fr_decimals, p.endz) + " " + self.feedrate_rapid_code(p) + "\n")
        gcode += 'G0 X{x}Y{y}'.format(x=coords_xy[0], y=coords_xy[1]) + " " + self.feedrate_rapid_code(p) + "\n"

        return gcode

    def feedrate_code(self, p):
        return 'G1 F' + str(self.feedrate_format %(p.fr_decimals, p.feedrate))

    def end_feedrate_code(self, p):
        return 'F' + self.feedrate_format %(p.fr_decimals, p.feedrate)

    def feedrate_z_code(self, p):
        return 'G1 F' + str(self.feedrate_format %(p.fr_decimals, p.feedrate_z))

    def feedrate_rapid_code(self, p):
        return 'F' + self.feedrate_rapid_format % (p.fr_decimals, p.feedrate_rapid)

    def spindle_code(self,p):
        if p.spindlespeed:
            return 'M3 S%d' % p.spindlespeed
        else:
            return 'M3'

    def dwell_code(self, p):
        if p.dwelltime:
            return 'G4 P' + str(p.dwelltime)

    def spindle_stop_code(self,p):
        return 'M5'
