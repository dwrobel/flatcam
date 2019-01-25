from FlatCAMTool import FlatCAMTool
from copy import copy, deepcopy
from ObjectCollection import *
import time


class Panelize(FlatCAMTool):

    toolName = "Panelize PCB Tool"

    def __init__(self, app):
        super(Panelize, self).__init__(self)
        self.app = app

        ## Title
        title_label = QtWidgets.QLabel("<font size=4><b>%s</b></font>" % self.toolName)
        self.layout.addWidget(title_label)

        ## Form Layout
        form_layout = QtWidgets.QFormLayout()
        self.layout.addLayout(form_layout)

        ## Type of object to be panelized
        self.type_obj_combo = QtWidgets.QComboBox()
        self.type_obj_combo.addItem("Gerber")
        self.type_obj_combo.addItem("Excellon")
        self.type_obj_combo.addItem("Geometry")

        self.type_obj_combo.setItemIcon(0, QtGui.QIcon("share/flatcam_icon16.png"))
        self.type_obj_combo.setItemIcon(1, QtGui.QIcon("share/drill16.png"))
        self.type_obj_combo.setItemIcon(2, QtGui.QIcon("share/geometry16.png"))

        self.type_obj_combo_label = QtWidgets.QLabel("Object Type:")
        self.type_obj_combo_label.setToolTip(
            "Specify the type of object to be panelized\n"
            "It can be of type: Gerber, Excellon or Geometry.\n"
            "The selection here decide the type of objects that will be\n"
            "in the Object combobox."
        )
        form_layout.addRow(self.type_obj_combo_label, self.type_obj_combo)

        ## Object to be panelized
        self.object_combo = QtWidgets.QComboBox()
        self.object_combo.setModel(self.app.collection)
        self.object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.object_combo.setCurrentIndex(1)
        self.object_label = QtWidgets.QLabel("Object:")
        self.object_label.setToolTip(
            "Object to be panelized. This means that it will\n"
            "be duplicated in an array of rows and columns."
        )
        form_layout.addRow(self.object_label, self.object_combo)

        ## Type of Box Object to be used as an envelope for panelization
        self.type_box_combo = QtWidgets.QComboBox()
        self.type_box_combo.addItem("Gerber")
        self.type_box_combo.addItem("Excellon")
        self.type_box_combo.addItem("Geometry")

        # we get rid of item1 ("Excellon") as it is not suitable for use as a "box" for panelizing
        self.type_box_combo.view().setRowHidden(1, True)
        self.type_box_combo.setItemIcon(0, QtGui.QIcon("share/flatcam_icon16.png"))
        self.type_box_combo.setItemIcon(2, QtGui.QIcon("share/geometry16.png"))

        self.type_box_combo_label = QtWidgets.QLabel("Box Type:")
        self.type_box_combo_label.setToolTip(
            "Specify the type of object to be used as an container for\n"
            "panelization. It can be: Gerber or Geometry type.\n"
            "The selection here decide the type of objects that will be\n"
            "in the Box Object combobox."
        )
        form_layout.addRow(self.type_box_combo_label, self.type_box_combo)

        ## Box
        self.box_combo = QtWidgets.QComboBox()
        self.box_combo.setModel(self.app.collection)
        self.box_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.box_combo.setCurrentIndex(1)
        self.box_combo_label = QtWidgets.QLabel("Box Object:")
        self.box_combo_label.setToolTip(
            "The actual object that is used a container for the\n "
            "selected object that is to be panelized."
        )
        form_layout.addRow(self.box_combo_label, self.box_combo)

        ## Spacing Columns
        self.spacing_columns = FloatEntry()
        self.spacing_columns.set_value(0.0)
        self.spacing_columns_label = QtWidgets.QLabel("Spacing cols:")
        self.spacing_columns_label.setToolTip(
            "Spacing between columns of the desired panel.\n"
            "In current units."
        )
        form_layout.addRow(self.spacing_columns_label, self.spacing_columns)

        ## Spacing Rows
        self.spacing_rows = FloatEntry()
        self.spacing_rows.set_value(0.0)
        self.spacing_rows_label = QtWidgets.QLabel("Spacing rows:")
        self.spacing_rows_label.setToolTip(
            "Spacing between rows of the desired panel.\n"
            "In current units."
        )
        form_layout.addRow(self.spacing_rows_label, self.spacing_rows)

        ## Columns
        self.columns = IntEntry()
        self.columns.set_value(1)
        self.columns_label = QtWidgets.QLabel("Columns:")
        self.columns_label.setToolTip(
            "Number of columns of the desired panel"
        )
        form_layout.addRow(self.columns_label, self.columns)

        ## Rows
        self.rows = IntEntry()
        self.rows.set_value(1)
        self.rows_label = QtWidgets.QLabel("Rows:")
        self.rows_label.setToolTip(
            "Number of rows of the desired panel"
        )
        form_layout.addRow(self.rows_label, self.rows)

        ## Constrains
        self.constrain_cb = FCCheckBox("Constrain panel within:")
        self.constrain_cb.setToolTip(
            "Area define by DX and DY within to constrain the panel.\n"
            "DX and DY values are in current units.\n"
            "Regardless of how many columns and rows are desired,\n"
            "the final panel will have as many columns and rows as\n"
            "they fit completely within selected area."
        )
        form_layout.addRow(self.constrain_cb)

        self.x_width_entry = FloatEntry()
        self.x_width_entry.set_value(0.0)
        self.x_width_lbl = QtWidgets.QLabel("Width (DX):")
        self.x_width_lbl.setToolTip(
            "The width (DX) within which the panel must fit.\n"
            "In current units."
        )
        form_layout.addRow(self.x_width_lbl, self.x_width_entry)

        self.y_height_entry = FloatEntry()
        self.y_height_entry.set_value(0.0)
        self.y_height_lbl = QtWidgets.QLabel("Height (DY):")
        self.y_height_lbl.setToolTip(
            "The height (DY)within which the panel must fit.\n"
            "In current units."
        )
        form_layout.addRow(self.y_height_lbl, self.y_height_entry)

        self.constrain_sel = OptionalInputSection(
            self.constrain_cb, [self.x_width_lbl, self.x_width_entry, self.y_height_lbl, self.y_height_entry])


        ## Buttons
        hlay_2 = QtWidgets.QHBoxLayout()
        self.layout.addLayout(hlay_2)

        hlay_2.addStretch()
        self.panelize_object_button = QtWidgets.QPushButton("Panelize Object")
        self.panelize_object_button.setToolTip(
            "Panelize the specified object around the specified box.\n"
            "In other words it creates multiple copies of the source object,\n"
            "arranged in a 2D array of rows and columns."
        )
        hlay_2.addWidget(self.panelize_object_button)

        self.layout.addStretch()

        ## Signals
        self.panelize_object_button.clicked.connect(self.on_panelize)
        self.type_obj_combo.currentIndexChanged.connect(self.on_type_obj_index_changed)
        self.type_box_combo.currentIndexChanged.connect(self.on_type_box_index_changed)

        # list to hold the temporary objects
        self.objs = []

        # final name for the panel object
        self.outname = ""

        # flag to signal the constrain was activated
        self.constrain_flag = False

    def on_type_obj_index_changed(self):
        obj_type = self.type_obj_combo.currentIndex()
        self.object_combo.setRootModelIndex(self.app.collection.index(obj_type, 0, QtCore.QModelIndex()))
        self.object_combo.setCurrentIndex(0)

    def on_type_box_index_changed(self):
        obj_type = self.type_box_combo.currentIndex()
        self.box_combo.setRootModelIndex(self.app.collection.index(obj_type, 0, QtCore.QModelIndex()))
        self.box_combo.setCurrentIndex(0)

    def run(self):
        FlatCAMTool.run(self)
        self.app.ui.notebook.setTabText(2, "Panel. Tool")

    def on_panelize(self):
        name = self.object_combo.currentText()

        # Get source object.
        try:
            obj = self.app.collection.get_by_name(str(name))
        except:
            self.app.inform.emit("[error_notcl]Could not retrieve object: %s" % name)
            return "Could not retrieve object: %s" % name

        panel_obj = obj

        if panel_obj is None:
            self.app.inform.emit("[error_notcl]Object not found: %s" % panel_obj)
            return "Object not found: %s" % panel_obj

        boxname = self.box_combo.currentText()

        try:
            box = self.app.collection.get_by_name(boxname)
        except:
            self.app.inform.emit("[error_notcl]Could not retrieve object: %s" % boxname)
            return "Could not retrieve object: %s" % boxname

        if box is None:
            self.app.inform.emit("[warning]No object Box. Using instead %s" % panel_obj)
            box = panel_obj

        self.outname = name + '_panelized'

        spacing_columns = self.spacing_columns.get_value()
        spacing_columns = spacing_columns if spacing_columns is not None else 0

        spacing_rows = self.spacing_rows.get_value()
        spacing_rows = spacing_rows if spacing_rows is not None else 0

        rows = self.rows.get_value()
        rows = rows if rows is not None else 1

        columns = self.columns.get_value()
        columns = columns if columns is not None else 1

        constrain_dx = self.x_width_entry.get_value()
        constrain_dy = self.y_height_entry.get_value()

        if 0 in {columns, rows}:
            self.app.inform.emit("[error_notcl]Columns or Rows are zero value. Change them to a positive integer.")
            return "Columns or Rows are zero value. Change them to a positive integer."

        xmin, ymin, xmax, ymax = box.bounds()
        lenghtx = xmax - xmin + spacing_columns
        lenghty = ymax - ymin + spacing_rows

        # check if constrain within an area is desired
        if self.constrain_cb.isChecked():
            panel_lengthx = ((xmax - xmin) * columns) + (spacing_columns * (columns - 1))
            panel_lengthy = ((ymax - ymin) * rows) + (spacing_rows * (rows - 1))

            # adjust the number of columns and/or rows so the panel will fit within the panel constraint area
            if (panel_lengthx > constrain_dx) or (panel_lengthy > constrain_dy):
                self.constrain_flag = True

                while panel_lengthx > constrain_dx:
                    columns -= 1
                    panel_lengthx = ((xmax - xmin) * columns) + (spacing_columns * (columns - 1))
                while panel_lengthy > constrain_dy:
                    rows -= 1
                    panel_lengthy = ((ymax - ymin) * rows) + (spacing_rows * (rows - 1))

        def clean_temp():
            # deselect all  to avoid  delete selected object when run  delete  from  shell
            self.app.collection.set_all_inactive()

            for del_obj in self.objs:
                self.app.collection.set_active(del_obj.options['name'])
                self.app.on_delete()

            self.objs[:] = []

        # def panelize():
        #     if panel_obj is not None:
        #         self.app.inform.emit("Generating panel ... Please wait.")
        #
        #         self.app.progress.emit(10)
        #
        #         if isinstance(panel_obj, FlatCAMExcellon):
        #             currenty = 0.0
        #             self.app.progress.emit(0)
        #
        #             def initialize_local_excellon(obj_init, app):
        #                 obj_init.tools = panel_obj.tools
        #                 # drills are offset, so they need to be deep copied
        #                 obj_init.drills = deepcopy(panel_obj.drills)
        #                 obj_init.offset([float(currentx), float(currenty)])
        #                 obj_init.create_geometry()
        #                 self.objs.append(obj_init)
        #
        #             self.app.progress.emit(0)
        #             for row in range(rows):
        #                 currentx = 0.0
        #                 for col in range(columns):
        #                     local_outname = self.outname + ".tmp." + str(col) + "." + str(row)
        #                     self.app.new_object("excellon", local_outname, initialize_local_excellon, plot=False,
        #                                         autoselected=False)
        #                     currentx += lenghtx
        #                 currenty += lenghty
        #         else:
        #             currenty = 0
        #             self.app.progress.emit(0)
        #
        #             def initialize_local_geometry(obj_init, app):
        #                 obj_init.solid_geometry = panel_obj.solid_geometry
        #                 obj_init.offset([float(currentx), float(currenty)])
        #                 self.objs.append(obj_init)
        #
        #             self.app.progress.emit(0)
        #             for row in range(rows):
        #                 currentx = 0
        #
        #                 for col in range(columns):
        #                     local_outname = self.outname + ".tmp." + str(col) + "." + str(row)
        #                     self.app.new_object("geometry", local_outname, initialize_local_geometry, plot=False,
        #                                         autoselected=False)
        #                     currentx += lenghtx
        #                 currenty += lenghty
        #
        #         def job_init_geometry(obj_fin, app_obj):
        #             FlatCAMGeometry.merge(self.objs, obj_fin)
        #
        #         def job_init_excellon(obj_fin, app_obj):
        #             # merge expects tools to exist in the target object
        #             obj_fin.tools = panel_obj.tools.copy()
        #             FlatCAMExcellon.merge(self.objs, obj_fin)
        #
        #         if isinstance(panel_obj, FlatCAMExcellon):
        #             self.app.progress.emit(50)
        #             self.app.new_object("excellon", self.outname, job_init_excellon, plot=True, autoselected=True)
        #         else:
        #             self.app.progress.emit(50)
        #             self.app.new_object("geometry", self.outname, job_init_geometry, plot=True, autoselected=True)
        #
        #     else:
        #         self.app.inform.emit("[error_notcl] Obj is None")
        #         return "ERROR: Obj is None"

        # panelize()
        # clean_temp()

        def panelize_2():
            if panel_obj is not None:
                self.app.inform.emit("Generating panel ... Please wait.")

                self.app.progress.emit(0)

                def job_init_excellon(obj_fin, app_obj):
                    currenty = 0.0
                    self.app.progress.emit(10)
                    obj_fin.tools = panel_obj.tools.copy()
                    obj_fin.drills = []
                    obj_fin.slots = []
                    obj_fin.solid_geometry = []

                    for option in panel_obj.options:
                        if option is not 'name':
                            try:
                                obj_fin.options[option] = panel_obj.options[option]
                            except:
                                log.warning("Failed to copy option.", option)

                    for row in range(rows):
                        currentx = 0.0
                        for col in range(columns):
                            if panel_obj.drills:
                                for tool_dict in panel_obj.drills:
                                    point_offseted = affinity.translate(tool_dict['point'], currentx, currenty)
                                    obj_fin.drills.append(
                                        {
                                            "point": point_offseted,
                                            "tool": tool_dict['tool']
                                        }
                                    )
                            if panel_obj.slots:
                                for tool_dict in panel_obj.slots:
                                    start_offseted = affinity.translate(tool_dict['start'], currentx, currenty)
                                    stop_offseted = affinity.translate(tool_dict['stop'], currentx, currenty)
                                    obj_fin.slots.append(
                                        {
                                            "start": start_offseted,
                                            "stop": stop_offseted,
                                            "tool": tool_dict['tool']
                                        }
                                    )
                            currentx += lenghtx
                        currenty += lenghty

                    obj_fin.create_geometry()
                    obj_fin.zeros = panel_obj.zeros
                    obj_fin.units = panel_obj.units

                def job_init_geometry(obj_fin, app_obj):
                    currentx = 0.0
                    currenty = 0.0

                    def translate_recursion(geom):
                        if type(geom) == list:
                            geoms = list()
                            for local_geom in geom:
                                geoms.append(translate_recursion(local_geom))
                            return geoms
                        else:
                            return affinity.translate(geom, xoff=currentx, yoff=currenty)

                    obj_fin.solid_geometry = []

                    if isinstance(panel_obj, FlatCAMGeometry):
                        obj_fin.multigeo = panel_obj.multigeo
                        obj_fin.tools = deepcopy(panel_obj.tools)
                        if panel_obj.multigeo is True:
                            for tool in panel_obj.tools:
                                obj_fin.tools[tool]['solid_geometry'][:] = []

                    self.app.progress.emit(0)
                    for row in range(rows):
                        currentx = 0.0

                        for col in range(columns):
                            if isinstance(panel_obj, FlatCAMGeometry):
                                if panel_obj.multigeo is True:
                                    for tool in panel_obj.tools:
                                        obj_fin.tools[tool]['solid_geometry'].append(translate_recursion(
                                            panel_obj.tools[tool]['solid_geometry'])
                                        )
                                else:
                                    obj_fin.solid_geometry.append(
                                        translate_recursion(panel_obj.solid_geometry)
                                    )
                            else:
                                obj_fin.solid_geometry.append(
                                    translate_recursion(panel_obj.solid_geometry)
                                )

                            currentx += lenghtx
                        currenty += lenghty

                if isinstance(panel_obj, FlatCAMExcellon):
                    self.app.progress.emit(50)
                    self.app.new_object("excellon", self.outname, job_init_excellon, plot=True, autoselected=True)
                else:
                    self.app.progress.emit(50)
                    self.app.new_object("geometry", self.outname, job_init_geometry, plot=True, autoselected=True)

        if self.constrain_flag is False:
            self.app.inform.emit("[success]Panel done...")
        else:
            self.constrain_flag = False
            self.app.inform.emit("[warning] Too big for the constrain area. Final panel has %s columns and %s rows" %
                                 (columns, rows))

        proc = self.app.proc_container.new("Generating panel ... Please wait.")

        def job_thread(app_obj):
            try:
                panelize_2()
                self.app.inform.emit("[success]Panel created successfully.")
            except Exception as e:
                proc.done()
                raise e
            proc.done()

        self.app.collection.promise(self.outname)
        self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app]})

    def reset_fields(self):
        self.object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.box_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
