from FlatCAMPostProc import *


class line_xyz(FlatCAMPostProc):

    coordinate_format = "%.*f"
    feedrate_format = '%.*f'

    def start_code(self, p):
        units = ' ' + str(p['units']).lower()
        coords_xy = p['toolchange_xy']
        gcode = ''

        xmin = '%.*f' % (p.coords_decimals, p['options']['xmin'])
        xmax = '%.*f' % (p.coords_decimals, p['options']['xmax'])
        ymin = '%.*f' % (p.coords_decimals, p['options']['ymin'])
        ymax = '%.*f' % (p.coords_decimals, p['options']['ymax'])

        if str(p['options']['type']) == 'Geometry':
            gcode += '(TOOL DIAMETER: ' + str(p['options']['tool_dia']) + units + ')\n'

        gcode += '(Feedrate: ' + str(p['feedrate']) + units + '/min' + ')\n'

        if str(p['options']['type']) == 'Geometry':
            gcode += '(Feedrate_Z: ' + str(p['feedrate_z']) + units + '/min' + ')\n'

        gcode += '(Feedrate rapids ' + str(p['feedrate_rapid']) + units + '/min' + ')\n' + '\n'
        gcode += '(Z_Cut: ' + str(p['z_cut']) + units + ')\n'

        if str(p['options']['type']) == 'Geometry':
            if p['multidepth'] is True:
                gcode += '(DepthPerCut: ' + str(p['depthpercut']) + units + ' <=>' + \
                         str(math.ceil(abs(p['z_cut']) / p['depthpercut'])) + ' passes' + ')\n'

        gcode += '(Z_Move: ' + str(p['z_move']) + units + ')\n'
        gcode += '(Z Toolchange: ' + str(p['toolchangez']) + units + ')\n'
        if coords_xy is not None:
            gcode += '(X,Y Toolchange: ' + "%.4f, %.4f" % (coords_xy[0], coords_xy[1]) + units + ')\n'
        else:
            gcode += '(X,Y Toolchange: ' + "None" + units + ')\n'
        gcode += '(Z Start: ' + str(p['startz']) + units + ')\n'
        gcode += '(Z End: ' + str(p['endz']) + units + ')\n'
        gcode += '(Steps per circle: ' + str(p['steps_per_circle']) + ')\n'

        if str(p['options']['type']) == 'Excellon' or str(p['options']['type']) == 'Excellon Geometry':
            gcode += '(Postprocessor Excellon: ' + str(p['pp_excellon_name']) + ')\n'
        else:
            gcode += '(Postprocessor Geometry: ' + str(p['pp_geometry_name']) + ')\n' + '\n'

        gcode += '(X range: ' + '{: >9s}'.format(xmin) + ' ... ' + '{: >9s}'.format(xmax) + ' ' + units + ')\n'
        gcode += '(Y range: ' + '{: >9s}'.format(ymin) + ' ... ' + '{: >9s}'.format(ymax) + ' ' + units + ')\n\n'

        gcode += '(Spindle Speed: %s RPM)\n' % str(p['spindlespeed'])

        gcode += ('G20\n' if p.units.upper() == 'IN' else 'G21\n')
        gcode += 'G90\n'
        gcode += 'G94\n'

        return gcode

    def startz_code(self, p):
        if p.startz is not None:
            g = 'G00 ' + 'X' + self.coordinate_format%(p.coords_decimals, p.x) + \
                ' Y' + self.coordinate_format%(p.coords_decimals, p.y) + \
                ' Z' + self.coordinate_format%(p.coords_decimals, p.startz)
            return g
        else:
            return ''

    def lift_code(self, p):
        g = 'G00 ' + 'X' + self.coordinate_format % (p.coords_decimals, p.x) + \
            ' Y' + self.coordinate_format % (p.coords_decimals, p.y) + \
            ' Z' + self.coordinate_format % (p.coords_decimals, p.z_move)
        return g

    def down_code(self, p):
        g = 'G01 ' + 'X' + self.coordinate_format % (p.coords_decimals, p.x) + \
            ' Y' + self.coordinate_format % (p.coords_decimals, p.y) + \
            ' Z' + self.coordinate_format % (p.coords_decimals, p.z_cut)
        return g

    def toolchange_code(self, p):
        toolchangez = p.toolchangez
        toolchangexy = p.toolchange_xy
        f_plunge = p.f_plunge
        gcode = ''

        if toolchangexy is not None:
            toolchangex = toolchangexy[0]
            toolchangey = toolchangexy[1]
        else:
            if str(p['options']['type']) == 'Excellon':
                toolchangex = p.oldx
                toolchangey = p.oldy
            else:
                toolchangex = p.x
                toolchangey = p.y

        no_drills = 1

        if int(p.tool) == 1 and p.startz is not None:
            toolchangez = p.startz

        if p.units.upper() == 'MM':
            toolC_formatted = format(p.toolC, '.2f')
        else:
            toolC_formatted = format(p.toolC, '.4f')

        if str(p['options']['type']) == 'Excellon':
            for i in p['options']['Tools_in_use']:
                if i[0] == p.tool:
                    no_drills = i[2]
            gcode = """
M5      
G00 X{toolchangex} Y{toolchangey} Z{toolchangez}
T{tool}
M6
(MSG, Change to Tool Dia = {toolC} ||| Total drills for tool T{tool} = {t_drills})
M0""".format(toolchangex=self.coordinate_format%(p.coords_decimals, toolchangex),
             toolchangey=self.coordinate_format % (p.coords_decimals, toolchangey),
             toolchangez=self.coordinate_format % (p.coords_decimals, toolchangez),
             tool=int(p.tool),
             t_drills=no_drills,
             toolC=toolC_formatted)

            if f_plunge is True:
                gcode += """\nG00 X{toolchangex} Y{toolchangey} Z{z_move}""".format(
                    toolchangex=self.coordinate_format%(p.coords_decimals, toolchangex),
                    toolchangey=self.coordinate_format % (p.coords_decimals, toolchangey),
                    z_move=self.coordinate_format % (p.coords_decimals, p.z_move))
            return gcode
        else:
            gcode = """
M5
G00 X{toolchangex} Y{toolchangey} Z{toolchangez}
T{tool}
M6    
(MSG, Change to Tool Dia = {toolC})
M0""".format(toolchangex=self.coordinate_format%(p.coords_decimals, toolchangex),
             toolchangey=self.coordinate_format % (p.coords_decimals, toolchangey),
             toolchangez=self.coordinate_format % (p.coords_decimals, toolchangez),
             tool=int(p.tool),
             toolC=toolC_formatted)

            if f_plunge is True:
                gcode += """\nG00 X{toolchangex} Y{toolchangey} Z{z_move}""".format(
                    toolchangex=self.coordinate_format % (p.coords_decimals, toolchangex),
                    toolchangey=self.coordinate_format % (p.coords_decimals, toolchangey),
                    z_move=self.coordinate_format % (p.coords_decimals, p.z_move))
            return gcode

    def up_to_zero_code(self, p):
        g = 'G01 ' + 'X' + self.coordinate_format % (p.coords_decimals, p.x) + \
            ' Y' + self.coordinate_format % (p.coords_decimals, p.y) + \
            ' Z0'
        return g

    def position_code(self, p):
        return ('X' + self.coordinate_format + ' Y' + self.coordinate_format) % \
               (p.coords_decimals, p.x, p.coords_decimals, p.y)

    def rapid_code(self, p):
        g = ('G00 ' + self.position_code(p)).format(**p)
        g += ' Z' + self.coordinate_format % (p.coords_decimals, p.z_move)
        return g

    def linear_code(self, p):
        g = ('G01 ' + self.position_code(p)).format(**p)
        g += ' Z' + self.coordinate_format % (p.coords_decimals, p.z_cut)
        return g

    def end_code(self, p):
        coords_xy = p['toolchange_xy']
        if coords_xy is not None:
            g = 'G00 X{x} Y{y}'.format(x=coords_xy[0], y=coords_xy[1]) + "\n"
        else:
            g = ('G00 ' + self.position_code(p)).format(**p)
        g += ' Z' + self.coordinate_format % (p.coords_decimals, p.endz)
        return g

    def feedrate_code(self, p):
        return 'G01 F' + str(self.feedrate_format %(p.fr_decimals, p.feedrate))

    def feedrate_z_code(self, p):
        return 'G01 F' + str(self.feedrate_format %(p.fr_decimals, p.feedrate_z))

    def spindle_code(self, p):
        if p.spindlespeed:
            return 'M03 S' + str(p.spindlespeed)
        else:
            return 'M03'

    def dwell_code(self, p):
        if p.dwelltime:
            return 'G4 P' + str(p.dwelltime)

    def spindle_stop_code(self,p):
        return 'M05'
