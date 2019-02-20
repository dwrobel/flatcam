from FlatCAMTool import FlatCAMTool
from copy import copy,deepcopy
from ObjectCollection import *
from FlatCAMApp import *
from PyQt5 import QtGui, QtCore, QtWidgets
from GUIElements import IntEntry, RadioSet, LengthEntry

from FlatCAMObj import FlatCAMGeometry, FlatCAMExcellon, FlatCAMGerber


class ToolSolderPaste(FlatCAMTool):

    toolName = "Solder Paste Tool"

    def __init__(self, app):
        FlatCAMTool.__init__(self, app)

        ## Title
        title_label = QtWidgets.QLabel("%s" % self.toolName)
        title_label.setStyleSheet("""
                        QLabel
                        {
                            font-size: 16px;
                            font-weight: bold;
                        }
                        """)
        self.layout.addWidget(title_label)

        ## Form Layout
        form_layout = QtWidgets.QFormLayout()
        self.layout.addLayout(form_layout)

        ## Type of object to be cutout
        self.type_obj_combo = QtWidgets.QComboBox()
        self.type_obj_combo.addItem("Gerber")
        self.type_obj_combo.addItem("Excellon")
        self.type_obj_combo.addItem("Geometry")

        # we get rid of item1 ("Excellon") as it is not suitable for creating solderpaste
        self.type_obj_combo.view().setRowHidden(1, True)
        self.type_obj_combo.setItemIcon(0, QtGui.QIcon("share/flatcam_icon16.png"))
        self.type_obj_combo.setItemIcon(2, QtGui.QIcon("share/geometry16.png"))

        self.type_obj_combo_label = QtWidgets.QLabel("Object Type:")
        self.type_obj_combo_label.setToolTip(
            "Specify the type of object to be used for solder paste dispense.\n"
            "It can be of type: Gerber or Geometry.\n"
            "What is selected here will dictate the kind\n"
            "of objects that will populate the 'Object' combobox."
        )
        form_layout.addRow(self.type_obj_combo_label, self.type_obj_combo)

        ## Object to be used for solderpaste dispensing
        self.obj_combo = QtWidgets.QComboBox()
        self.obj_combo.setModel(self.app.collection)
        self.obj_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.obj_combo.setCurrentIndex(1)

        self.object_label = QtWidgets.QLabel("Object:")
        self.object_label.setToolTip(
            "Solder paste object.                        "
        )
        form_layout.addRow(self.object_label, self.obj_combo)

        # Offset distance
        self.nozzle_dia_entry = FloatEntry()
        self.nozzle_dia_entry.setValidator(QtGui.QDoubleValidator(0.0000, 9.9999, 4))
        self.nozzle_dia_label = QtWidgets.QLabel("Nozzle Diameter:")
        self.nozzle_dia_label.setToolTip(
            "The offset for the solder paste.\n"
            "Due of the diameter of the solder paste dispenser\n"
            "we need to adjust the quantity of solder paste."
        )
        form_layout.addRow(self.nozzle_dia_label, self.nozzle_dia_entry)

        # Z dispense start
        self.z_start_entry = FCEntry()
        self.z_start_label = QtWidgets.QLabel("Z Dispense Start:")
        self.z_start_label.setToolTip(
            "The size of the gaps in the cutout\n"
            "used to keep the board connected to\n"
            "the surrounding material (the one \n"
            "from which the PCB is cutout)."
        )
        form_layout.addRow(self.z_start_label, self.z_start_entry)

        # Z dispense
        self.z_dispense_entry = FCEntry()
        self.z_dispense_label = QtWidgets.QLabel("Z Dispense:")
        self.z_dispense_label.setToolTip(
            "Margin over bounds. A positive value here\n"
            "will make the cutout of the PCB further from\n"
            "the actual PCB border"
        )
        form_layout.addRow(self.z_dispense_label, self.z_dispense_entry)

        # Z dispense stop
        self.z_stop_entry = FCEntry()
        self.z_stop_label = QtWidgets.QLabel("Z Dispense Stop:")
        self.z_stop_label.setToolTip(
            "The size of the gaps in the cutout\n"
            "used to keep the board connected to\n"
            "the surrounding material (the one \n"
            "from which the PCB is cutout)."
        )
        form_layout.addRow(self.z_stop_label, self.z_stop_entry)

        # Z travel
        self.z_travel_entry = FCEntry()
        self.z_travel_label = QtWidgets.QLabel("Z Travel:")
        self.z_travel_label.setToolTip(
            "The size of the gaps in the cutout\n"
            "used to keep the board connected to\n"
            "the surrounding material (the one \n"
            "from which the PCB is cutout)."
        )
        form_layout.addRow(self.z_travel_label, self.z_travel_entry)

        # Feedrate X-Y
        self.frxy_entry = FCEntry()
        self.frxy_label = QtWidgets.QLabel("Feedrate X-Y:")
        self.frxy_label.setToolTip(
            "The size of the gaps in the cutout\n"
            "used to keep the board connected to\n"
            "the surrounding material (the one \n"
            "from which the PCB is cutout)."
        )
        form_layout.addRow(self.frxy_label, self.frxy_entry)

        # Feedrate Z
        self.frz_entry = FCEntry()
        self.frz_label = QtWidgets.QLabel("Feedrate Z:")
        self.frz_label.setToolTip(
            "The size of the gaps in the cutout\n"
            "used to keep the board connected to\n"
            "the surrounding material (the one \n"
            "from which the PCB is cutout)."
        )
        form_layout.addRow(self.frz_label, self.frz_entry)

        # Spindle Speed Forward
        self.speedfwd_entry = FCEntry()
        self.speedfwd_label = QtWidgets.QLabel("Spindle Speed FWD:")
        self.speedfwd_label.setToolTip(
            "The size of the gaps in the cutout\n"
            "used to keep the board connected to\n"
            "the surrounding material (the one \n"
            "from which the PCB is cutout)."
        )
        form_layout.addRow(self.speedfwd_label, self.speedfwd_entry)

        # Dwell Forward
        self.dwellfwd_entry = FCEntry()
        self.dwellfwd_label = QtWidgets.QLabel("Dwell FWD:")
        self.dwellfwd_label.setToolTip(
            "The size of the gaps in the cutout\n"
            "used to keep the board connected to\n"
            "the surrounding material (the one \n"
            "from which the PCB is cutout)."
        )
        form_layout.addRow(self.dwellfwd_label, self.dwellfwd_entry)

        # Spindle Speed Reverse
        self.speedrev_entry = FCEntry()
        self.speedrev_label = QtWidgets.QLabel("Spindle Speed REV:")
        self.speedrev_label.setToolTip(
            "The size of the gaps in the cutout\n"
            "used to keep the board connected to\n"
            "the surrounding material (the one \n"
            "from which the PCB is cutout)."
        )
        form_layout.addRow(self.speedrev_label, self.speedrev_entry)

        # Dwell Reverse
        self.dwellrev_entry = FCEntry()
        self.dwellrev_label = QtWidgets.QLabel("Dwell REV:")
        self.dwellrev_label.setToolTip(
            "The size of the gaps in the cutout\n"
            "used to keep the board connected to\n"
            "the surrounding material (the one \n"
            "from which the PCB is cutout)."
        )
        form_layout.addRow(self.dwellrev_label, self.dwellrev_entry)

        # Postprocessors
        pp_label = QtWidgets.QLabel('PostProcessors:')
        pp_label.setToolTip(
            "Files that control the GCoe generation."
        )

        self.pp_combo = FCComboBox()
        pp_items = [1, 2, 3, 4, 5]
        for it in pp_items:
            self.pp_combo.addItem(str(it))
            self.pp_combo.setStyleSheet('background-color: rgb(255,255,255)')
        form_layout.addRow(pp_label, self.pp_combo)

        ## Buttons
        hlay = QtWidgets.QHBoxLayout()
        self.layout.addLayout(hlay)

        hlay.addStretch()
        self.soldergeo_btn = QtWidgets.QPushButton("Generate Geo")
        self.soldergeo_btn.setToolTip(
            "Generate solder paste dispensing geometry."
        )
        hlay.addWidget(self.soldergeo_btn)


        self.solder_gcode = QtWidgets.QPushButton("Generate GCode")
        self.solder_gcode.setToolTip(
            "Generate GCode to dispense Solder Paste\n"
            "on PCB pads."
        )
        hlay.addWidget(self.solder_gcode)


        self.layout.addStretch()

        ## Signals
        self.soldergeo_btn.clicked.connect(self.on_create_geo)
        self.solder_gcode.clicked.connect(self.on_create_gcode)

        self.type_obj_combo.currentIndexChanged.connect(self.on_type_obj_index_changed)

    def on_type_obj_index_changed(self, index):
        obj_type = self.type_obj_combo.currentIndex()
        self.obj_combo.setRootModelIndex(self.app.collection.index(obj_type, 0, QtCore.QModelIndex()))
        self.obj_combo.setCurrentIndex(0)

    def run(self):
        self.app.report_usage("ToolSolderPaste()")

        FlatCAMTool.run(self)
        self.set_tool_ui()

        # if the splitter us hidden, display it
        if self.app.ui.splitter.sizes()[0] == 0:
            self.app.ui.splitter.setSizes([1, 1])

        self.app.ui.notebook.setTabText(2, "SolderPaste Tool")

    def install(self, icon=None, separator=None, **kwargs):
        FlatCAMTool.install(self, icon, separator, shortcut='ALT+K', **kwargs)

    def set_tool_ui(self):
        self.reset_fields()
        pass

    @staticmethod
    def distance(pt1, pt2):
        return sqrt((pt1[0] - pt2[0]) ** 2 + (pt1[1] - pt2[1]) ** 2)

    def on_create_geo(self):
        proc = self.app.proc_container.new("Creating Solder Paste dispensing geometry.")

        name = self.obj_combo.currentText()
        obj = self.app.collection.get_by_name(name)

        if type(obj.solid_geometry) is not list:
            obj.solid_geometry = [obj.solid_geometry]

        try:
            offset = self.nozzle_dia_entry.get_value() / 2
        except Exception as e:
            log.debug("ToolSoderPaste.on_create_geo() --> %s" % str(e))
            self.app.inform.emit("[ERROR_NOTCL] Failed. Offset value is missing ...")
            return

        if offset is None:
            self.app.inform.emit("[ERROR_NOTCL] Failed. Offset value is missing ...")
            return

        def geo_init(geo_obj, app_obj):
            geo_obj.solid_geometry = []
            geo_obj.multigeo = False
            geo_obj.multitool = False
            geo_obj.tools = {}

            def solder_line(p, offset):
                xmin, ymin, xmax, ymax = p.bounds

                min = [xmin, ymin]
                max = [xmax, ymax]
                min_r = [xmin, ymax]
                max_r = [xmax, ymin]

                diagonal_1 = LineString([min, max])
                diagonal_2 = LineString([min_r, max_r])
                round_diag_1 = round(diagonal_1.intersection(p).length, 4)
                round_diag_2 = round(diagonal_2.intersection(p).length, 4)

                if round_diag_1 == round_diag_2:
                    l = distance((xmin, ymin), (xmax, ymin))
                    h = distance((xmin, ymin), (xmin, ymax))
                    if offset >= l /2 or offset >= h / 2:
                        return "fail"
                    if l > h:
                        h_half = h / 2
                        start = [xmin, (ymin + h_half)]
                        stop = [(xmin + l), (ymin + h_half)]
                    else:
                        l_half = l / 2
                        start = [(xmin + l_half), ymin]
                        stop = [(xmin + l_half), (ymin + h)]
                    geo = LineString([start, stop])
                elif round_diag_1 > round_diag_2:
                    geo = diagonal_1.intersection(p)
                else:
                    geo = diagonal_2.intersection(p)

                offseted_poly = p.buffer(-offset)
                geo = geo.intersection(offseted_poly)
                return geo

            for g in obj.solid_geometry:
                if type(g) == MultiPolygon:
                    for poly in g:
                        geom = solder_line(poly, offset=offset)
                        if geom == 'fail':
                            app_obj.inform.emit("[ERROR_NOTCL] The Nozzle diameter is too big for certain features.")
                            return 'fail'
                        if not geom.is_empty:
                            geo_obj.solid_geometry.append(geom)
                elif type(g) == Polygon:
                    geom = solder_line(g, offset=offset)
                    if geom == 'fail':
                        app_obj.inform.emit("[ERROR_NOTCL] The Nozzle diameter is too big for certain features.")
                        return 'fail'
                    if not geom.is_empty:
                        geo_obj.solid_geometry.append(geom)

        def job_thread(app_obj):
            try:
                app_obj.new_object("geometry", name + "_temp_solderpaste", geo_init)
            except Exception as e:
                proc.done()
                traceback.print_stack()
                return
            proc.done()

        self.app.inform.emit("Generating Solder Paste dispensing geometry...")
        # Promise object with the new name
        self.app.collection.promise(name)

        # Background
        self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app]})
        # self.app.ui.notebook.setCurrentWidget(self.app.ui.project_tab)

    def on_create_gcode(self):
        name = self.obj_combo.currentText()

        def geo_init(geo_obj, app_obj):
           pass

        # self.app.new_object("geometry", name + "_cutout", geo_init)
        # self.app.inform.emit("[success] Rectangular CutOut operation finished.")
        # self.app.ui.notebook.setCurrentWidget(self.app.ui.project_tab)

    def reset_fields(self):
        self.obj_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
