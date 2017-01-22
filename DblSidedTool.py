from PyQt4 import QtGui
from GUIElements import RadioSet, EvalEntry, LengthEntry
from FlatCAMTool import FlatCAMTool
#from FlatCAMObj import FlatCAMGerber, FlatCAMExcellon
from FlatCAMObj import *
from shapely.geometry import Point
from shapely import affinity

# For the translation by Daniel Sallin Debut
# Use translate_("txt") for translate the "txt" string
# Using gettext for translate 
# Using os for def a locale path
# Using unidecode for accents compatibility
# coding: utf8
import gettext
import os
import sys
from unidecode import unidecode
if sys.platform == 'win32':
       import gettext_windows
       gettext_windows.setup_env()
pathname = os.path.dirname(sys.argv[0])
localdir = os.path.abspath(pathname) + "/locale"
gettext.install("messages", localdir)
def translate_(txt):
    return unicode(_(txt),'utf-8')
# For the translation by Daniel Sallin fin

class DblSidedTool(FlatCAMTool):

    toolName = translate_("Double-Sided PCB Tool")

    def __init__(self, app):
        FlatCAMTool.__init__(self, app)
		

        ## Title
        title_label = QtGui.QLabel("<font size=4><b>%s</b></font>" % self.toolName)
        self.layout.addWidget(title_label)

        ## Form Layout
        form_layout = QtGui.QFormLayout()
        self.layout.addLayout(form_layout)

        ## Layer to mirror
        self.object_combo = QtGui.QComboBox()
        self.object_combo.setModel(self.app.collection)
        self.botlay_label = QtGui.QLabel(translate_("Bottom Layer:"))
        self.botlay_label.setToolTip(translate_(
            "Layer to be mirrorer."
        ))
        # form_layout.addRow("Bottom Layer:", self.object_combo)
        form_layout.addRow(self.botlay_label, self.object_combo)

        ## Axis
        self.mirax_label = QtGui.QLabel(translate_("Mirror Axis:"))
        self.mirax_label.setToolTip(
            translate_("Mirror vertically (X) or horizontally (Y).")
        )
        self.mirror_axis = RadioSet([{'label': 'X', 'value': 'X'},
                                     {'label': 'Y', 'value': 'Y'}])		
        # form_layout.addRow("Mirror Axis:", self.mirror_axis)
        form_layout.addRow(self.mirax_label, self.mirror_axis)

        ## Axis Location
        self.axis_location = RadioSet([{'label': translate_('Point'), 'value': 'point'},
                                       {'label': translate_('Box'), 'value': 'box'}])
        self.axloc_label = QtGui.QLabel(translate_("Axis Location:"))
        self.axloc_label.setToolTip(translate_(
            "The axis should pass through a <b>point</b> or cut "
            "a specified <b>box</b> (in a Geometry object) in "
            "the middle."
        ))
        # form_layout.addRow("Axis Location:", self.axis_location)
        form_layout.addRow(self.axloc_label, self.axis_location)

        ## Point/Box
        self.point_box_container = QtGui.QVBoxLayout()
        self.pb_label = QtGui.QLabel(translate_("Point/Box:"))
        self.pb_label.setToolTip(translate_(
            "Specify the point (x, y) through which the mirror axis "
            "passes or the Geometry object containing a rectangle "
            "that the mirror axis cuts in half."
        ))
        # form_layout.addRow("Point/Box:", self.point_box_container)
        form_layout.addRow(self.pb_label, self.point_box_container)

        self.point = EvalEntry()
        self.point_box_container.addWidget(self.point)
        self.box_combo = QtGui.QComboBox()
        self.box_combo.setModel(self.app.collection)
        self.point_box_container.addWidget(self.box_combo)
        self.box_combo.hide()

        ## Alignment holes
        self.alignment_holes = EvalEntry()
        self.ah_label = QtGui.QLabel(translate_("Alignment Holes:"))
        self.ah_label.setToolTip(translate_(
            "Alignment holes (x1, y1), (x2, y2), ... "
            "on one side of the mirror axis."
        ))
        form_layout.addRow(self.ah_label, self.alignment_holes)

        ## Drill diameter for alignment holes
        self.drill_dia = LengthEntry()
        self.dd_label = QtGui.QLabel(translate_("Drill diam.:"))
        self.dd_label.setToolTip(translate_(
            "Diameter of the drill for the "
            "alignment holes."
        ))
        form_layout.addRow(self.dd_label, self.drill_dia)

        ## Buttons
        hlay = QtGui.QHBoxLayout()
        self.layout.addLayout(hlay)
        hlay.addStretch()
        self.create_alignment_hole_button = QtGui.QPushButton(translate_("Create Alignment Drill"))
        self.create_alignment_hole_button.setToolTip(translate_(
            "Creates an Excellon Object containing the "
            "specified alignment holes and their mirror "
            "images."
        ))
        self.mirror_object_button = QtGui.QPushButton(translate_("Mirror Object"))
        self.mirror_object_button.setToolTip(translate_(
            "Mirrors (flips) the specified object around "
            "the specified axis. Does not create a new "
            "object, but modifies it."
        ))
        hlay.addWidget(self.create_alignment_hole_button)
        hlay.addWidget(self.mirror_object_button)

        self.layout.addStretch()

        ## Signals
        self.create_alignment_hole_button.clicked.connect(self.on_create_alignment_holes)
        self.mirror_object_button.clicked.connect(self.on_mirror)

        self.axis_location.group_toggle_fn = self.on_toggle_pointbox

        ## Initialize form
        self.mirror_axis.set_value('X')
        self.axis_location.set_value('point')

    def on_create_alignment_holes(self):
        axis = self.mirror_axis.get_value()
        mode = self.axis_location.get_value()

        if mode == "point":
            px, py = self.point.get_value()
        else:
            selection_index = self.box_combo.currentIndex()
            bb_obj = self.app.collection.object_list[selection_index]  # TODO: Direct access??
            xmin, ymin, xmax, ymax = bb_obj.bounds()
            px = 0.5 * (xmin + xmax)
            py = 0.5 * (ymin + ymax)

        xscale, yscale = {"X": (1.0, -1.0), "Y": (-1.0, 1.0)}[axis]

        dia = self.drill_dia.get_value()
        tools = {"1": {"C": dia}}

        # holes = self.alignment_holes.get_value()
        holes = eval('[{}]'.format(self.alignment_holes.text()))
        drills = []

        for hole in holes:
            point = Point(hole)
            point_mirror = affinity.scale(point, xscale, yscale, origin=(px, py))
            drills.append({"point": point, "tool": "1"})
            drills.append({"point": point_mirror, "tool": "1"})

        def obj_init(obj_inst, app_inst):
            obj_inst.tools = tools
            obj_inst.drills = drills
            obj_inst.create_geometry()

        self.app.new_object("excellon", "Alignment Drills", obj_init)

    def on_mirror(self):
        selection_index = self.object_combo.currentIndex()
        fcobj = self.app.collection.object_list[selection_index]

        # For now, lets limit to Gerbers and Excellons.
        # assert isinstance(gerb, FlatCAMGerber)
        if not isinstance(fcobj, FlatCAMGerber) and \
                not isinstance(fcobj, FlatCAMExcellon) and \
                not isinstance(fcobj, FlatCAMGeometry):
            self.info("ERROR: Only Gerber, Excellon and Geometry objects can be mirrored.")
            return

        axis = self.mirror_axis.get_value()
        mode = self.axis_location.get_value()

        if mode == "point":
            px, py = self.point.get_value()
        else:
            selection_index = self.box_combo.currentIndex()
            bb_obj = self.app.collection.object_list[selection_index]  # TODO: Direct access??
            xmin, ymin, xmax, ymax = bb_obj.bounds()
            px = 0.5 * (xmin + xmax)
            py = 0.5 * (ymin + ymax)

        fcobj.mirror(axis, [px, py])
        fcobj.plot()

    def on_toggle_pointbox(self):
        if self.axis_location.get_value() == "point":
            self.point.show()
            self.box_combo.hide()
        else:
            self.point.hide()
            self.box_combo.show()
