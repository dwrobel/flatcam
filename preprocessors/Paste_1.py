# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 3/10/2019                                          #
# MIT Licence                                              #
# ##########################################################

from appPreProcessor import *


class Paste_1(AppPreProcTools):

    include_header = True
    coordinate_format = "%.*f"
    feedrate_format = '%.*f'

    def start_code(self, p):
        units = ' ' + str(p['units']).lower()
        coords_xy = [float(eval(a)) for a in p['xy_toolchange'].split(",") if a != '']

        gcode = ''

        xmin = '%.*f' % (p.coords_decimals, p['options']['xmin'])
        xmax = '%.*f' % (p.coords_decimals, p['options']['xmax'])
        ymin = '%.*f' % (p.coords_decimals, p['options']['ymin'])
        ymax = '%.*f' % (p.coords_decimals, p['options']['ymax'])

        gcode += '(TOOL DIAMETER: ' + str(p['options']['tool_dia']) + units + ')\n'
        gcode += '(Feedrate_XY: ' + str(p['frxy']) + units + '/min' + ')\n'
        gcode += '(Feedrate_Z: ' + str(p['frz']) + units + '/min' + ')\n'
        gcode += '(Feedrate_Z_Dispense: ' + str(p['frz_dispense']) + units + '/min' + ')\n'

        gcode += '(Z_Dispense_Start: ' + str(p['z_start']) + units + ')\n'
        gcode += '(Z_Dispense: ' + str(p['z_dispense']) + units + ')\n'
        gcode += '(Z_Dispense_Stop: ' + str(p['z_stop']) + units + ')\n'
        gcode += '(Z_Travel: ' + str(p['z_travel']) + units + ')\n'
        gcode += '(Z Toolchange: ' + str(p['z_toolchange']) + units + ')\n'

        gcode += '(X,Y Toolchange: ' + "%.*f, %.*f" % (p.decimals, coords_xy[0],
                                                       p.decimals, coords_xy[1]) + units + ')\n'

        if 'Paste' in p.pp_solderpaste_name:
            gcode += '(Preprocessor SolderPaste Dispensing Geometry: ' + str(p.pp_solderpaste_name) + ')\n' + '\n'

        gcode += '(X range: ' + '{: >9s}'.format(xmin) + ' ... ' + '{: >9s}'.format(xmax) + ' ' + units + ')\n'
        gcode += '(Y range: ' + '{: >9s}'.format(ymin) + ' ... ' + '{: >9s}'.format(ymax) + ' ' + units + ')\n\n'

        gcode += '(Spindle Speed FWD: %s RPM)\n' % str(p['speedfwd'])
        gcode += '(Spindle Speed REV: %s RPM)\n' % str(p['speedrev'])
        gcode += '(Dwell FWD: %s RPM)\n' % str(p['dwellfwd'])
        gcode += '(Dwell REV: %s RPM)\n' % str(p['dwellrev'])

        gcode += ('G20\n' if p.units.upper() == 'IN' else 'G21\n')
        gcode += 'G90\n'
        gcode += 'G94\n'
        return gcode

    def lift_code(self, p):
        return 'G00 Z' + self.coordinate_format % (p.coords_decimals, float(p['z_travel']))

    def down_z_start_code(self, p):
        return 'G01 Z' + self.coordinate_format % (p.coords_decimals, float(p['z_start']))

    def lift_z_dispense_code(self, p):
        return 'G01 Z' + self.coordinate_format % (p.coords_decimals, float(p['z_dispense']))

    def down_z_stop_code(self, p):
        return 'G01 Z' + self.coordinate_format % (p.coords_decimals, float(p['z_stop']))

    def toolchange_code(self, p):
        z_toolchange = float(p['z_toolchange'])
        toolchangexy = [float(eval(a)) for a in p['xy_toolchange'].split(",") if a != '']

        if toolchangexy is not None:
            x_toolchange = toolchangexy[0]
            y_toolchange = toolchangexy[1]
        else:
            x_toolchange = 0.0
            y_toolchange = 0.0

        toolC_formatted = '%.*f' % (p.decimals, float(p['toolC']))

        if toolchangexy is not None:
            gcode = """
G00 Z{z_toolchange}
G00 X{x_toolchange} Y{y_toolchange}
T{tool}
M6    
(MSG, Change to Tool with Nozzle Dia = {toolC})
M0
G00 Z{z_toolchange}
""".format(x_toolchange=self.coordinate_format % (p.coords_decimals, x_toolchange),
           y_toolchange=self.coordinate_format % (p.coords_decimals, y_toolchange),
           z_toolchange=self.coordinate_format % (p.coords_decimals, z_toolchange),
           tool=int(int(p.tool)),
           toolC=toolC_formatted)

        else:
            gcode = """
G00 Z{z_toolchange}
T{tool}
M6    
(MSG, Change to Tool with Nozzle Dia = {toolC})
M0
G00 Z{z_toolchange}
""".format(z_toolchange=self.coordinate_format % (p.coords_decimals, z_toolchange),
           tool=int(int(p.tool)),
           toolC=toolC_formatted)

        return gcode

    def position_code(self, p):
        return ('X' + self.coordinate_format + ' Y' + self.coordinate_format) % \
               (p.coords_decimals, p.x, p.coords_decimals, p.y)

    def rapid_code(self, p):
        return ('G00 ' + self.position_code(p)).format(**p) + '\nG00 Z' + \
               self.coordinate_format % (p.coords_decimals, float(p['z_travel']))

    def linear_code(self, p):
        return ('G01 ' + self.position_code(p)).format(**p)

    def end_code(self, p):
        coords_xy = [float(eval(a)) for a in p['xy_end'].split(",") if a != '']
        gcode = ('G00 Z' + self.feedrate_format % (p.fr_decimals, float(p['z_toolchange'])) + "\n")

        if coords_xy and coords_xy != '':
            gcode += 'G00 X{x} Y{y}'.format(x=coords_xy[0], y=coords_xy[1]) + "\n"
        return gcode

    def feedrate_xy_code(self, p):
        return 'G01 F' + str(self.feedrate_format % (p.fr_decimals, float(p['frxy'])))

    def z_feedrate_code(self, p):
        return 'G01 F' + str(self.feedrate_format % (p.fr_decimals, float(p['frz'])))

    def feedrate_z_dispense_code(self, p):
        return 'G01 F' + str(self.feedrate_format % (p.fr_decimals, float(p['frz_dispense'])))

    def spindle_fwd_code(self, p):
        if p.spindlespeed:
            return 'M03 S' + str(float(p['speedfwd']))
        else:
            return 'M03'

    def spindle_rev_code(self, p):
        if p.spindlespeed:
            return 'M04 S' + str(float(p['speedrev']))
        else:
            return 'M04'

    def spindle_off_code(self, p):
        return 'M05'

    def dwell_fwd_code(self, p):
        if p.dwelltime:
            return 'G4 P' + str(float(p['dwellfwd']))

    def dwell_rev_code(self, p):
        if p.dwelltime:
            return 'G4 P' + str(float(p['dwellrev']))
