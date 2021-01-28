# ########################################################## ##
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# File Author: Georg Ziegler                               #
# Date: 1/16/2021                                          #
# MIT Licence                                              #
# ########################################################## ##

from appPreProcessor import *
# This post processor is configured to output code for
# lasers without Z Axis
# and to convert excellon drillcodes into arcs
# So after etching we have small holes in the copper plane
# which helps for centering the drill bit for manual drilling
# So the GRBL Controller has to support G2 commands


class grbl_laser_eleks_drd(PreProc):
    include_header = True
    coordinate_format = "%.*f"
    feedrate_format = '%.*f'

    def start_code(self, p):
        units = ' ' + str(p['units']).lower()
        gcode = ''
        xmin = '%.*f' % (p.coords_decimals, p['options']['xmin'])
        xmax = '%.*f' % (p.coords_decimals, p['options']['xmax'])
        ymin = '%.*f' % (p.coords_decimals, p['options']['ymin'])
        ymax = '%.*f' % (p.coords_decimals, p['options']['ymax'])
        gcode += '(Feedrate: ' + str(p['feedrate']) + units + '/min' + ')\n'
        gcode += '(Feedrate rapids ' + str(p['feedrate_rapid']) + units + '/min' + ')\n'
        gcode += '(Steps per circle: ' + str(p['steps_per_circle']) + ')\n'
        if str(p['options']['type']) == 'Excellon' or str(p['options']['type']) == 'Excellon Geometry':
            gcode += '(Preprocessor Excellon: ' + str(p['pp_excellon_name']) + ')\n'
        else:
            gcode += '(Preprocessor Geometry: ' + str(p['pp_geometry_name']) + ')\n'
        gcode += '(X range: ' + '{: >9s}'.format(xmin) + ' ... ' + '{: >9s}'.format(xmax) + ' ' + units + ')\n'
        gcode += '(Y range: ' + '{: >9s}'.format(ymin) + ' ... ' + '{: >9s}'.format(ymax) + ' ' + units + ')\n'
        gcode += '\n'
        if p.units.upper() == 'IN':
            gcode += 'G20;Inch Units\n'
        else:
            gcode += 'G21;Millimeter Units\n'
        gcode += 'G90;Absolute Positioning\n'
        # gcode += 'G17;Select Plane XY\n'
        # gcode += 'G94;Feedrate per minute\n'
        gcode += 'G00 F' + str(self.feedrate_format % (p.fr_decimals, p.feedrate_rapid)) + '\n'
        gcode += 'G01 F' + str(self.feedrate_format % (p.fr_decimals, p.feedrate)) + '\n'  # Is Z-Feedrate for Excellon
        if p.spindledir == 'CCW':
            gcode += 'M04'
        else:
            gcode += 'M03'
        if p.spindlespeed:
            gcode += ' ' + 'S%d' % p.spindlespeed
        gcode += ';' + p.spindledir
        return gcode

    def startz_code(self, p):
        return ';startz'

    def lift_code(self, p):
        return 'M05;lift'

    def down_code(self, p):
        if p.spindledir == 'CCW':
            gcode = 'M04'
        else:
            gcode = 'M03'
        gcode += ';down'
        if str(p['options']['type']) == 'Excellon' or str(p['options']['type']) == 'Excellon Geometry':
            gcode += '\n'
            gcode += 'G02 '  # Draw Top Little Arc
            gcode += ('X' + self.coordinate_format + ' Y' + self.coordinate_format) % \
                     (p.coords_decimals, p.x + 0.1, p.coords_decimals, p.y)
            gcode += (' I' + self.coordinate_format + ' J' + self.coordinate_format) % \
                     (p.coords_decimals, +0.1, p.coords_decimals, 0)
            gcode += '\n'
            gcode += 'G02 '  # Draw Bottom Little Arc
            gcode += ('X' + self.coordinate_format + ' Y' + self.coordinate_format) % \
                     (p.coords_decimals, p.x - 0.1, p.coords_decimals, p.y)
            gcode += (' I' + self.coordinate_format + ' J' + self.coordinate_format) % \
                     (p.coords_decimals, -0.1, p.coords_decimals, 0)
            gcode += '\n'
            gcode += 'G00 ' + (self.position_ldob_code(p)).format(**p)
            gcode += '\n'
            gcode += 'G02 '  # Draw Top Bigger Arc
            gcode += ('X' + self.coordinate_format + ' Y' + self.coordinate_format) % \
                     (p.coords_decimals, p.x + 0.2, p.coords_decimals, p.y)
            gcode += (' I' + self.coordinate_format + ' J' + self.coordinate_format) % \
                     (p.coords_decimals, +0.2, p.coords_decimals, 0)
            gcode += '\n'
            gcode += 'G02 '  # Draw Bottom Bigger Arc
            gcode += ('X' + self.coordinate_format + ' Y' + self.coordinate_format) % \
                     (p.coords_decimals, p.x - 0.2, p.coords_decimals, p.y)
            gcode += (' I' + self.coordinate_format + ' J' + self.coordinate_format) % \
                     (p.coords_decimals, -0.2, p.coords_decimals, 0)
        return gcode

    def toolchange_code(self, p):
        return ';toolchange'

    def up_to_zero_code(self, p):  # Only use for drilling, so no essentialy need for Laser
        return ';up_to_zero'

    def position_code(self, p):
        return ('X' + self.coordinate_format + ' Y' + self.coordinate_format) % \
               (p.coords_decimals, p.x, p.coords_decimals, p.y)

    def position_ldos_code(self, p):
        return ('X' + self.coordinate_format + ' Y' + self.coordinate_format) % \
               (p.coords_decimals, p.x-0.1, p.coords_decimals, p.y)  # -0.1 : ArcRadius Offset for smaller DrillHole Arc

    def position_ldob_code(self, p):
        return ('X' + self.coordinate_format + ' Y' + self.coordinate_format) % \
               (p.coords_decimals, p.x-0.2, p.coords_decimals, p.y)  # -0.1 : ArcRadius Offset for bigger DrillHole Arc

    def rapid_code(self, p):
        gcode = 'G00 '
        if str(p['options']['type']) == 'Excellon' or str(p['options']['type']) == 'Excellon Geometry':
            gcode += (self.position_ldos_code(p)).format(**p)
        else:
            gcode += (self.position_code(p)).format(**p)
        return gcode

    def linear_code(self, p):
        return 'G01 ' + (self.position_code(p)).format(**p)

    def end_code(self, p):
        gcode = ''
        coords_xy = p['xy_toolchange']
        if coords_xy is not None:
            gcode = 'G00 X{x} Y{y}'.format(x=coords_xy[0], y=coords_xy[1])
        return gcode

    def feedrate_code(self, p):
        return ';feedrate'

    def z_feedrate_code(self, p):
        return ';z_feedrate'

    def spindle_code(self, p):
        return ';spindle'

    def dwell_code(self, p):
        return ';dwell'

    def spindle_stop_code(self, p):
        return ';spindle_stop '
