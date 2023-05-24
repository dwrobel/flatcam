# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# File Author: Matthieu Berthomé                           #
# Date: 5/26/2017                                          #
# MIT Licence                                              #
# ##########################################################

from appPreProcessor import PreProc
import math


class default(PreProc):

    include_header = True
    coordinate_format = "%.*f"
    feedrate_format = '%.*f'

    def start_code(self, p):
        units = ' ' + str(p['units']).lower()
        coords_xy = p['xy_toolchange']
        end_coords_xy = p['xy_end']
        gcode = '(This preprocessor is the default preprocessor.)\n'
        gcode += '(It is made to work with MACH3 compatible motion controllers.)\n\n'

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
        # executed once at the beginning of the CNC job
        if p.startz is not None:
            return 'G00 Z' + self.coordinate_format % (p.coords_decimals, p.startz)
        else:
            return ''

    def lift_code(self, p):
        # executed each time the router bit is raised at a safe distance above the material in order to travel
        # for the next location where a new cut into the material will start. It is a lift to a safe Z height.
        # It is a vertical upward move.
        return 'G00 Z' + self.coordinate_format % (p.coords_decimals, p.z_move)

    def down_code(self, p):
        # a vertical downward move.
        # Executed each time the router bit is lowered into the material to start a cutting move.
        return 'G01 Z' + self.coordinate_format % (p.coords_decimals, p.z_cut)

    def toolchange_code(self, p):
        # executed each time a tool is changed either manually or automatically
        z_toolchange = p.z_toolchange
        toolchangexy = p.xy_toolchange
        f_plunge = p.f_plunge

        if toolchangexy is not None:
            x_toolchange = toolchangexy[0]
            y_toolchange = toolchangexy[1]
        else:
            x_toolchange = 0.0
            y_toolchange = 0.0

        no_drills = 1

        if int(p.tool) == 1 and p.startz is not None:
            z_toolchange = p.startz

        toolC_formatted = '%.*f' % (p.decimals, p.toolC)

        if str(p['obj_options']['type']) == 'Excellon':
            no_drills = p['tools'][int(p['tool'])]['nr_drills']

            if toolchangexy is not None:
                gcode = """
M5
G00 Z{z_toolchange}
T{tool}
G00 X{x_toolchange} Y{y_toolchange}                
M6
(MSG, Change to Tool Dia = {toolC} ||| Total drills for tool T{tool} = {t_drills})
M0
G00 Z{z_toolchange}
""".format(x_toolchange=self.coordinate_format % (p.coords_decimals, x_toolchange),
           y_toolchange=self.coordinate_format % (p.coords_decimals, y_toolchange),
           z_toolchange=self.coordinate_format % (p.coords_decimals, z_toolchange),
           tool=int(p.tool),
           t_drills=no_drills,
           toolC=toolC_formatted)
            else:
                gcode = """
M5       
G00 Z{z_toolchange}
T{tool}
M6
(MSG, Change to Tool Dia = {toolC} ||| Total drills for tool T{tool} = {t_drills})
M0
G00 Z{z_toolchange}
""".format(z_toolchange=self.coordinate_format % (p.coords_decimals, z_toolchange),
           tool=int(p.tool),
           t_drills=no_drills,
           toolC=toolC_formatted)

            if f_plunge is True:
                gcode += '\nG00 Z%.*f' % (p.coords_decimals, p.z_move)
            return gcode

        else:
            if toolchangexy is not None:
                gcode = """
M5
G00 Z{z_toolchange}
G00 X{x_toolchange} Y{y_toolchange}
T{tool}
M6    
(MSG, Change to Tool Dia = {toolC})
M0
G00 Z{z_toolchange}
""".format(x_toolchange=self.coordinate_format % (p.coords_decimals, x_toolchange),
           y_toolchange=self.coordinate_format % (p.coords_decimals, y_toolchange),
           z_toolchange=self.coordinate_format % (p.coords_decimals, z_toolchange),
           tool=int(p.tool),
           toolC=toolC_formatted)

            else:
                gcode = """
M5
G00 Z{z_toolchange}
T{tool}
M6    
(MSG, Change to Tool Dia = {toolC})
M0
G00 Z{z_toolchange}
""".format(z_toolchange=self.coordinate_format % (p.coords_decimals, z_toolchange),
           tool=int(p.tool),
           toolC=toolC_formatted)

            if f_plunge is True:
                gcode += '\nG00 Z%.*f' % (p.coords_decimals, p.z_move)
            return gcode

    def up_to_zero_code(self, p):
        # this is an optional move that instead of moving vertically upward to the travel position (a safe position
        # outside the material) it move only up to the top of material. The reason is to break the move into a vertical
        # move inside the material followed by a vertical move outside the material up to the travel (safe) Z height
        return 'G01 Z0'

    def position_code(self, p):
        # used in for the linear motion
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
        # a fast linear motion using the G0 command which means: "move as fast as the CNC can handle and is set in the
        # CNC controller". It is a horizontal move in the X-Y CNC plane.
        return ('G00 ' + self.position_code(p)).format(**p)

    def linear_code(self, p):
        # a linear motion using the G1 command which means: "move with a set feedrate (speed)".
        # It is a horizontal move in the X-Y CNC plane.
        return ('G01 ' + self.position_code(p)).format(**p)

    def end_code(self, p):
        # a final move at the end of the CNC job. First it moves to a safe parking Z height followed by an X-Y move
        # to the parking location.
        end_coords_xy = p['xy_end']
        gcode = ('G00 Z' + self.feedrate_format % (p.fr_decimals, p.z_end) + "\n")

        if end_coords_xy and end_coords_xy != '':
            gcode += 'G00 X{x} Y{y}'.format(x=end_coords_xy[0], y=end_coords_xy[1]) + "\n"
        return gcode

    def feedrate_code(self, p):
        # set the feedrate for the linear move with G1 command on the X-Y CNC plane (horizontal move)
        return 'G01 F' + str(self.feedrate_format % (p.fr_decimals, p.feedrate))

    def z_feedrate_code(self, p):
        # set the feedrate for the linear move with G1 command on the Z CNC plane (vertical move)
        return 'G01 F' + str(self.feedrate_format % (p.fr_decimals, p.z_feedrate))

    def spindle_code(self, p):
        # set the ON state of the spindle (starts the spindle), the spindle speed and the spindle rotation direction
        sdir = {'CW': 'M03', 'CCW': 'M04'}[p.spindledir]
        if p.spindlespeed:
            return '%s S%s' % (sdir, str(p.spindlespeed))
        else:
            return sdir

    def dwell_code(self, p):
        # set a pause after the spindle is started allowing the spindle to reach the set spindle spped, before move
        if p.dwelltime:
            return 'G4 P' + str(p.dwelltime)

    def spindle_stop_code(self, p):
        # stop the spindle
        return 'M05'
