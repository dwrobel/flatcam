# -*- coding: utf-8 -*-
"""
Created on Sun Jan 05 13:30:47 2014

@author: jpcaram
"""

import os
os.chdir('../')

from flatcamParsers.ParseGerber import *
from flatcamParsers.ParseExcellon import *

from matplotlib import pyplot

# Gerber. To see if the Excellon is correct
project_dir = "tests/gerber_files"
gerber_filename = project_dir + "KiCad_Squarer-F_Cu.gtl"
g = Gerber()
g.parse_file(gerber_filename)
g.create_geometry()

excellon_filename = project_dir + "KiCad_Squarer.drl"
ex = Excellon()
ex.parse_file(excellon_filename)
ex.create_geometry()

#fig = Figure()
fig = pyplot.figure()
ax = fig.add_subplot(111)
ax.set_aspect(1)

# Plot gerber
for geo in g.solid_geometry:
    x, y = geo.exterior.coords.xy
    pyplot.plot(x, y, 'k-')
    for ints in geo.interiors:
        x, y = ints.coords.xy
        ax.plot(x, y, 'k-')
        
# Plot excellon
for geo in ex.solid_geometry:
    x, y = geo.exterior.coords.xy
    pyplot.plot(x, y, 'r-')
    for ints in geo.interiors:
        x, y = ints.coords.xy
        ax.plot(x, y, 'g-')
        
fig.show()