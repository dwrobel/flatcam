# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# File Author: Marius Stanciu                              #
# Date: 11-Dec-2020                                        #
# MIT Licence                                              #
# ##########################################################

from appPreProcessor import PreProc
import math


class Check_points(PreProc):

    include_header = True
    coordinate_format = "%.*f"
    feedrate_format = '%.*f'

    def start_code(self, p):
        units = ' ' + str(p['units']).lower()
        coords_xy = p['xy_toolchange']
        end_coords_xy = p['xy_end']
        gcode = '(This preprocessor is used to check the positioning of the PCB,)\n'
        gcode += '(by moving a probe - possible a fine drill bit - to custom locations)\n'
        gcode += '(and wait for user interaction in order to continue to the next point.)\n\n'

        xmin = '%.*f' % (p.coords_decimals, p['obj_options']['xmin'])
        xmax = '%.*f' % (p.coords_decimals, p['obj_options']['xmax'])
        ymin = '%.*f' % (p.coords_decimals, p['obj_options']['ymin'])
        ymax = '%.*f' % (p.coords_decimals, p['obj_options']['ymax'])

        if str(p['obj_options']['type']) == 'Geometry':
            gcode += '(TOOL DIAMETER: ' + str(p['obj_options']['tool_dia']) + units + ')\n'
            gcode += '(Feedrate_XY: ' + str(p['feedrate']) + units + '/min' + ')\n'
            gcode += '(Feedrate_Z: ' + str(p['z_feedrate']) + units + '/min' + ')\n'
            gcode += '(Feedrate rapids ' + str(p['feedrate_rapid']) + units + '/min' + ')\n' + '\n'
            gcode += '(Z_Cut: ' + str(p['z_cut']) + units + ')\n'
            if p['multidepth'] is True:
                gcode += '(DepthPerCut: ' + str(p['z_depthpercut']) + units + ' <=>' + \
                         str(math.ceil(abs(p['z_cut']) / p['z_depthpercut'])) + ' passes' + ')\n'
            gcode += '(Z_Move: ' + str(p['z_move']) + units + ')\n'

        elif str(p['obj_options']['type']) == 'Excellon' and p['use_ui'] is True:
            gcode += '\n(TOOLS DIAMETER: )\n'
            for tool, val in p['tools'].items():
                gcode += '(Tool: %s -> ' % str(tool) + 'Dia: %s' % str(val["tooldia"]) + ')\n'

            gcode += '\n(FEEDRATE Z: )\n'
            for tool, val in p['tools'].items():
                gcode += '(Tool: %s -> ' % str(tool) + 'Feedrate: %s' % \
                         str(val['data']["tools_drill_feedrate_z"]) + ')\n'

            gcode += '\n(FEEDRATE RAPIDS: )\n'
            for tool, val in p['tools'].items():
                gcode += '(Tool: %s -> ' % str(tool) + 'Feedrate Rapids: %s' % \
                         str(val['data']["tools_drill_feedrate_rapid"]) + ')\n'

            gcode += '\n(Z_CUT: )\n'
            for tool, val in p['tools'].items():
                gcode += '(Tool: %s -> ' % str(tool) + 'Z_Cut: %s' % str(val['data']["tools_drill_cutz"]) + ')\n'

            gcode += '\n(Tools Offset: )\n'
            for tool, val in p['tools'].items():
                gcode += '(Tool: %s -> ' % str(tool) + 'Offset Z: %s' % \
                         str(val['data']["tools_drill_offset"]) + ')\n'

            if p['multidepth'] is True:
                gcode += '\n(DEPTH_PER_CUT: )\n'
                for tool, val in p['tools'].items():
                    gcode += '(Tool: %s -> ' % str(tool) + 'DeptPerCut: %s' % \
                             str(val['data']["tools_drill_depthperpass"]) + ')\n'

            gcode += '\n(Z_MOVE: )\n'
            for tool, val in p['tools'].items():
                gcode += '(Tool: %s -> ' % str(tool) + 'Z_Move: %s' % str(val['data']["tools_drill_travelz"]) + ')\n'
            gcode += '\n'

        if p['toolchange'] is True:
            gcode += '(Z Toolchange: ' + str(p['z_toolchange']) + units + ')\n'

            if coords_xy is not None:
                gcode += '(X,Y Toolchange: ' + "%.*f, %.*f" % (p.decimals, coords_xy[0],
                                                               p.decimals, coords_xy[1]) + units + ')\n'
            else:
                gcode += '(X,Y Toolchange: ' + "None" + units + ')\n'

        gcode += '(Z Start: ' + str(p['startz']) + units + ')\n'
        gcode += '(Z End: ' + str(p['z_end']) + units + ')\n'
        if end_coords_xy is not None:
            gcode += '(X,Y End: ' + "%.*f, %.*f" % (p.decimals, end_coords_xy[0],
                                                    p.decimals, end_coords_xy[1]) + units + ')\n'
        else:
            gcode += '(X,Y End: ' + "None" + units + ')\n'
        gcode += '(Steps per circle: ' + str(p['steps_per_circle']) + ')\n'

        if str(p['obj_options']['type']) == 'Excellon' or str(p['obj_options']['type']) == 'Excellon Geometry':
            gcode += '(Preprocessor Excellon: ' + str(p['pp_excellon_name']) + ')\n' + '\n'
        else:
            gcode += '(Preprocessor Geometry: ' + str(p['pp_geometry_name']) + ')\n' + '\n'

        gcode += '(X range: ' + '{: >9s}'.format(xmin) + ' ... ' + '{: >9s}'.format(xmax) + ' ' + units + ')\n'
        gcode += '(Y range: ' + '{: >9s}'.format(ymin) + ' ... ' + '{: >9s}'.format(ymax) + ' ' + units + ')\n\n'

        gcode += '(Spindle Speed: %s RPM)\n' % str(p['spindlespeed'])

        gcode += ('G20\n' if p.units.upper() == 'IN' else 'G21\n')
        gcode += 'G90\n'
        gcode += 'G94'

        return gcode

    def startz_code(self, p):
        if p.startz is not None:
            return 'G00 Z' + self.coordinate_format % (p.coords_decimals, p.startz)
        else:
            return ''

    def lift_code(self, p):
        return 'G00 Z' + self.coordinate_format % (p.coords_decimals, p.z_move)

    def down_code(self, p):
        # make sure that the probe will always be above the material
        cutz_val = -p.z_cut if p.z_cut < 0 else p.z_cut
        gcode = 'G01 Z' + self.coordinate_format % (p.coords_decimals, cutz_val) + '\n'
        # wait for user interaction
        gcode += 'M0'
        return gcode

    def toolchange_code(self, p):
        z_toolchange = p.z_toolchange
        toolchangexy = p.xy_toolchange
        f_plunge = p.f_plunge

        if toolchangexy is not None:
            x_toolchange = toolchangexy[0]
            y_toolchange = toolchangexy[1]
        else:
            x_toolchange = 0.0
            y_toolchange = 0.0

        if int(p.tool) == 1 and p.startz is not None:
            z_toolchange = p.startz

        if str(p['obj_options']['type']) == 'Excellon':
            if toolchangexy is not None:
                gcode = """
M5
G00 Z{z_toolchange}
G00 X{x_toolchange} Y{y_toolchange} 
(MSG, Change to Tool T{tool}. WARNING: the following move is FAST G0)
M0
G00 Z{z_move}
G01 Z0
(MSG, Adjust the tool T{tool} to touch the material and then tighten it.)
M0
(MSG, Changed to Tool T{tool})
""".format(x_toolchange=self.coordinate_format % (p.coords_decimals, x_toolchange),
           y_toolchange=self.coordinate_format % (p.coords_decimals, y_toolchange),
           z_toolchange=self.coordinate_format % (p.coords_decimals, z_toolchange),
           z_move=self.coordinate_format % (p.coords_decimals, p.z_move),
           tool=int(p.tool))

            else:
                gcode = """
M5
G00 Z{z_toolchange}
(MSG, Change to Tool T{tool}. WARNING: the following move is FAST G0)
M0
G00 Z{z_move}
G01 Z0
(MSG, Adjust the tool T{tool} to touch the material and then tighten it.)
M0
(MSG, Changed to Tool T{tool})
""".format(z_toolchange=self.coordinate_format % (p.coords_decimals, z_toolchange),
           z_move=self.coordinate_format % (p.coords_decimals, p.z_move),
           tool=int(p.tool))

            if f_plunge is True:
                gcode += '\nG00 Z%.*f' % (p.coords_decimals, p.z_move)
            return gcode

        else:
            if toolchangexy is not None:
                gcode = """
M5
G00 Z{z_toolchange}
G00 X{x_toolchange}Y{y_toolchange}    
(MSG, Change to Tool T{tool}. WARNING: the following move is FAST G0)
M0
G00 Z{z_move}
G01 Z0
(MSG, Adjust the tool T{tool} to touch the material and then tighten it.)
M0
(MSG, Changed to Tool T{tool})
""".format(x_toolchange=self.coordinate_format % (p.coords_decimals, x_toolchange),
           y_toolchange=self.coordinate_format % (p.coords_decimals, y_toolchange),
           z_toolchange=self.coordinate_format % (p.coords_decimals, z_toolchange),
           z_move=self.coordinate_format % (p.coords_decimals, p.z_move),
           tool=int(p.tool))
            else:
                gcode = """
M5  
G00 Z{z_toolchange}
(MSG, Change to Tool T{tool}. WARNING: the following move is FAST G0)
M0
G00 Z{z_move}
G01 Z0
(MSG, Adjust the tool T{tool} to touch the material and then tighten it.)
M0
(MSG, Changed to Tool T{tool})
""".format(z_toolchange=self.coordinate_format % (p.coords_decimals, z_toolchange),
           z_move=self.coordinate_format % (p.coords_decimals, p.z_move),
           tool=int(p.tool))

            if f_plunge is True:
                gcode += '\nG00 Z%.*f' % (p.coords_decimals, p.z_move)
            return gcode

    def up_to_zero_code(self, p):
        return ''

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
        return ('G00 ' + self.position_code(p)).format(**p)

    def linear_code(self, p):
        return ('G00 ' + self.position_code(p)).format(**p)

    def end_code(self, p):
        end_coords_xy = p['xy_end']
        gcode = ('G00 Z' + self.feedrate_format % (p.fr_decimals, p.z_end) + "\n")

        if end_coords_xy and end_coords_xy != '':
            gcode += 'G00 X{x} Y{y}'.format(x=end_coords_xy[0], y=end_coords_xy[1]) + "\n"
        return gcode

    def feedrate_code(self, p):
        return 'G01 F' + str(self.feedrate_format % (p.fr_decimals, p.feedrate))

    def z_feedrate_code(self, p):
        return 'G01 F' + str(self.feedrate_format % (p.fr_decimals, p.z_feedrate))

    def spindle_code(self, p):
        return ''

    def dwell_code(self, p):
        return ''

    def spindle_stop_code(self, p):
        return 'M05'
