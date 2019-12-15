# ########################################################## ##
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# File Author: Matthieu Berthomé, Daniel Friderich         #
# Date: 12/15/2019                                          #
# MIT Licence                                              #
# ########################################################## ##

from FlatCAMPostProc import *


class ISEL_ICP_CNC(FlatCAMPostProc):    
    def start_code(self, p):
        units = ' ' + str(p['units']).lower()
        coords_xy = p['xy_toolchange']
        gcode = ''

        xmin = '%.*f' % (p.coords_decimals, p['options']['xmin'])
        xmax = '%.*f' % (p.coords_decimals, p['options']['xmax'])
        ymin = '%.*f' % (p.coords_decimals, p['options']['ymin'])
        ymax = '%.*f' % (p.coords_decimals, p['options']['ymax'])
        
        gcode += 'IMF_PBL flatcam\r\n'
        
        if str(p['options']['type']) == 'Geometry':
            gcode += '; TOOL DIAMETER: ' + str(p['options']['tool_dia']) + units + '\r\n'
            
        gcode += '; Spindle Speed: %s RPM\r\n' % str(p['spindlespeed'])

        gcode += '; Feedrate: ' + str(p['feedrate']) + units + '/min' + '\r\n'

        if str(p['options']['type']) == 'Geometry':
            gcode += '; Feedrate_Z: ' + str(p['z_feedrate']) + units + '/min' + '\r\n'

        gcode += '; Feedrate rapids ' + str(p['feedrate_rapid']) + units + '/min' + '\r\n\r\n'
        gcode += '; Z_Cut: ' + str(p['z_cut']) + units + '\r\n'

        if str(p['options']['type']) == 'Geometry':
            if p['multidepth'] is True:
                gcode += '; DepthPerCut: ' + str(p['z_depthpercut']) + units + ' <=>' + \
                         str(math.ceil(abs(p['z_cut']) / p['z_depthpercut'])) + ' passes' + '\r\n'

        gcode += '; Z_Move: ' + str(p['z_move']) + units + '\r\n'
        gcode += '; Z Toolchange: ' + str(p['z_toolchange']) + units + '\r\n'

        if coords_xy is not None:
            gcode += '; X,Y Toolchange: ' + "%.*f, %.*f" % (p.decimals, coords_xy[0],
                                                           p.decimals, coords_xy[1]) + units + '\r\n'
        else:
            gcode += '; X,Y Toolchange: ' + "None" + units + '\r\n'

        gcode += '; Z Start: ' + str(p['startz']) + units + '\r\n'
        gcode += '; Z End: ' + str(p['z_end']) + units + '\r\n'
        gcode += '; Steps per circle: ' + str(p['steps_per_circle']) + '\r\n'

        if str(p['options']['type']) == 'Excellon' or str(p['options']['type']) == 'Excellon Geometry':
            gcode += '; Preprocessor Excellon: ' + str(p['pp_excellon_name']) + '\r\n'
        else:
            gcode += '; Preprocessor Geometry: ' + str(p['pp_geometry_name']) + '\r\n'

        gcode += '; X range: ' + '{: >9s}'.format(xmin) + ' ... ' + '{: >9s}'.format(xmax) + ' ' + units + '\r\n'
        gcode += '; Y range: ' + '{: >9s}'.format(ymin) + ' ... ' + '{: >9s}'.format(ymax) + ' ' + units + '\r\n'

        return gcode

    def startz_code(self, p):
        if p.startz is not None:
            return 'FASTABS Z' + str(int(p.startz * 1000))
        else:
            return ''

    def lift_code(self, p):
        return 'FASTABS Z' + str(int(p.z_move * 1000))

    def down_code(self, p):
        return 'MOVEABS Z' + str(int(p.z_cut * 1000))

    def toolchange_code(self, p):
        f_plunge = p.f_plunge
        no_drills = 1

        toolC_formatted = '%.*f' % (p.decimals, p.toolC)

        if str(p['options']['type']) == 'Excellon':
            for i in p['options']['Tools_in_use']:
                if i[0] == p.tool:
                    no_drills = i[2]

            gcode = "GETTOOL {tool}\r\n; Changed to Tool Dia = {toolC}".format(tool=int(p.tool), t_drills=no_drills, toolC=toolC_formatted)

            if f_plunge is True:
                gcode += '\r\nFASTABS Z' + str(int(p.z_move * 1000))
            return gcode

        else:
            gcode = "GETTOOL {tool}\r\n; Changed to Tool Dia = {toolC})".format(tool=int(p.tool), toolC=toolC_formatted)

            if f_plunge is True:
                gcode += '\r\nFASTABS Z' + str(int(p.z_move * 1000))
            return gcode

    def up_to_zero_code(self, p):
        return 'MOVEABS Z0'

    def position_code(self, p):
        return ('X' + str(int(p.x * 1000)) + ' Y' + str(int(p.y * 1000)))
    def rapid_code(self, p):
        return ('FASTABS ' + self.position_code(p)).format(**p)

    def linear_code(self, p):
        return ('MOVEABS ' + self.position_code(p)).format(**p)

    def end_code(self, p):
        gcode = ''
        gcode += 'WPCLEAR\r\n'
        gcode += 'FASTABS Z0\r\n'
        gcode += 'FASTABS X0 Y0\r\n'
        gcode += 'PROGEND'
        return gcode

    def feedrate_code(self, p):
        return 'VEL ' + str(int(p.feedrate / 60 * 1000))

    def z_feedrate_code(self, p):
        return 'VEL ' + str(int(p.z_feedrate / 60 * 1000))

    def spindle_code(self, p):
        sdir = {'CW': 'SPINDLE CW', 'CCW': 'SPINDLE CCW'}[p.spindledir]
        if p.spindlespeed:
            return '%s RPM%s' % (sdir, str(int(p.spindlespeed)))
        else:
            return sdir

    def dwell_code(self, p):
        if p.dwelltime:
            return 'WAIT ' + str(int(p.dwelltime * 1000))

    def spindle_stop_code(self,p):
        return 'SPINDLE OFF'