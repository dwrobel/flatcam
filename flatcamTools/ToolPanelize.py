############################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 3/10/2019                                          #
# MIT Licence                                              #
############################################################

from FlatCAMTool import FlatCAMTool
from copy import copy, deepcopy
from ObjectCollection import *
import time

import gettext
import FlatCAMTranslation as fcTranslate

fcTranslate.apply_language('ToolPanelize')
import builtins
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class Panelize(FlatCAMTool):

    toolName = _("Panelize PCB")

    def __init__(self, app):
        super(Panelize, self).__init__(self)
        self.app = app

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

        ## Type of object to be panelized
        self.type_obj_combo = QtWidgets.QComboBox()
        self.type_obj_combo.addItem("Gerber")
        self.type_obj_combo.addItem("Excellon")
        self.type_obj_combo.addItem("Geometry")

        self.type_obj_combo.setItemIcon(0, QtGui.QIcon("share/flatcam_icon16.png"))
        self.type_obj_combo.setItemIcon(1, QtGui.QIcon("share/drill16.png"))
        self.type_obj_combo.setItemIcon(2, QtGui.QIcon("share/geometry16.png"))

        self.type_obj_combo_label = QtWidgets.QLabel(_("Object Type:"))
        self.type_obj_combo_label.setToolTip(
            _("Specify the type of object to be panelized\n"
            "It can be of type: Gerber, Excellon or Geometry.\n"
            "The selection here decide the type of objects that will be\n"
            "in the Object combobox.")
        )
        form_layout.addRow(self.type_obj_combo_label, self.type_obj_combo)

        ## Object to be panelized
        self.object_combo = QtWidgets.QComboBox()
        self.object_combo.setModel(self.app.collection)
        self.object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.object_combo.setCurrentIndex(1)

        self.object_label = QtWidgets.QLabel(_("Object:"))
        self.object_label.setToolTip(
            _("Object to be panelized. This means that it will\n"
            "be duplicated in an array of rows and columns.")
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

        self.type_box_combo_label = QtWidgets.QLabel(_("Box Type:"))
        self.type_box_combo_label.setToolTip(
            _("Specify the type of object to be used as an container for\n"
            "panelization. It can be: Gerber or Geometry type.\n"
            "The selection here decide the type of objects that will be\n"
            "in the Box Object combobox.")
        )
        form_layout.addRow(self.type_box_combo_label, self.type_box_combo)

        ## Box
        self.box_combo = QtWidgets.QComboBox()
        self.box_combo.setModel(self.app.collection)
        self.box_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.box_combo.setCurrentIndex(1)

        self.box_combo_label = QtWidgets.QLabel(_("Box Object:"))
        self.box_combo_label.setToolTip(
            _("The actual object that is used a container for the\n "
            "selected object that is to be panelized.")
        )
        form_layout.addRow(self.box_combo_label, self.box_combo)

        ## Spacing Columns
        self.spacing_columns = FCEntry()
        self.spacing_columns_label = QtWidgets.QLabel(_("Spacing cols:"))
        self.spacing_columns_label.setToolTip(
            _("Spacing between columns of the desired panel.\n"
            "In current units.")
        )
        form_layout.addRow(self.spacing_columns_label, self.spacing_columns)

        ## Spacing Rows
        self.spacing_rows = FCEntry()
        self.spacing_rows_label = QtWidgets.QLabel(_("Spacing rows:"))
        self.spacing_rows_label.setToolTip(
            _("Spacing between rows of the desired panel.\n"
            "In current units.")
        )
        form_layout.addRow(self.spacing_rows_label, self.spacing_rows)

        ## Columns
        self.columns = FCEntry()
        self.columns_label = QtWidgets.QLabel(_("Columns:"))
        self.columns_label.setToolTip(
            _("Number of columns of the desired panel")
        )
        form_layout.addRow(self.columns_label, self.columns)

        ## Rows
        self.rows = FCEntry()
        self.rows_label = QtWidgets.QLabel(_("Rows:"))
        self.rows_label.setToolTip(
            _("Number of rows of the desired panel")
        )
        form_layout.addRow(self.rows_label, self.rows)

        ## Type of resulting Panel object
        self.panel_type_radio = RadioSet([{'label': 'Gerber', 'value': 'gerber'},
                                     {'label': 'Geometry', 'value': 'geometry'}])
        self.panel_type_label = QtWidgets.QLabel(_("Panel Type:"))
        self.panel_type_label.setToolTip(
            _("Choose the type of object for the panel object:\n"
            "- Geometry\n"
            "- Gerber")
        )
        form_layout.addRow(self.panel_type_label)
        form_layout.addRow(self.panel_type_radio)

        ## Constrains
        self.constrain_cb = FCCheckBox(_("Constrain panel within:"))
        self.constrain_cb.setToolTip(
            _("Area define by DX and DY within to constrain the panel.\n"
            "DX and DY values are in current units.\n"
            "Regardless of how many columns and rows are desired,\n"
            "the final panel will have as many columns and rows as\n"
            "they fit completely within selected area.")
        )
        form_layout.addRow(self.constrain_cb)

        self.x_width_entry = FCEntry()
        self.x_width_lbl = QtWidgets.QLabel(_("Width (DX):"))
        self.x_width_lbl.setToolTip(
            _("The width (DX) within which the panel must fit.\n"
            "In current units.")
        )
        form_layout.addRow(self.x_width_lbl, self.x_width_entry)

        self.y_height_entry = FCEntry()
        self.y_height_lbl = QtWidgets.QLabel(_("Height (DY):"))
        self.y_height_lbl.setToolTip(
            _("The height (DY)within which the panel must fit.\n"
            "In current units.")
        )
        form_layout.addRow(self.y_height_lbl, self.y_height_entry)

        self.constrain_sel = OptionalInputSection(
            self.constrain_cb, [self.x_width_lbl, self.x_width_entry, self.y_height_lbl, self.y_height_entry])

        ## Buttons
        hlay_2 = QtWidgets.QHBoxLayout()
        self.layout.addLayout(hlay_2)

        hlay_2.addStretch()
        self.panelize_object_button = QtWidgets.QPushButton(_("Panelize Object"))
        self.panelize_object_button.setToolTip(
            _("Panelize the specified object around the specified box.\n"
            "In other words it creates multiple copies of the source object,\n"
            "arranged in a 2D array of rows and columns.")
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

    def run(self, toggle=True):
        self.app.report_usage("ToolPanelize()")

        FlatCAMTool.run(self, toggle=toggle)
        self.set_tool_ui()

        self.app.ui.notebook.setTabText(2, "Panel. Tool")

    def install(self, icon=None, separator=None, **kwargs):
        FlatCAMTool.install(self, icon, separator, shortcut='ALT+Z', **kwargs)

    def set_tool_ui(self):
        self.reset_fields()

        sp_c = self.app.defaults["tools_panelize_spacing_columns"] if \
            self.app.defaults["tools_panelize_spacing_columns"] else 0.0
        self.spacing_columns.set_value(float(sp_c))

        sp_r = self.app.defaults["tools_panelize_spacing_rows"] if \
            self.app.defaults["tools_panelize_spacing_rows"] else 0.0
        self.spacing_rows.set_value(float(sp_r))

        rr = self.app.defaults["tools_panelize_rows"] if \
            self.app.defaults["tools_panelize_rows"] else 0.0
        self.rows.set_value(int(rr))

        cc = self.app.defaults["tools_panelize_columns"] if \
            self.app.defaults["tools_panelize_columns"] else 0.0
        self.columns.set_value(int(cc))

        c_cb = self.app.defaults["tools_panelize_constrain"] if \
            self.app.defaults["tools_panelize_constrain"] else False
        self.constrain_cb.set_value(c_cb)

        x_w = self.app.defaults["tools_panelize_constrainx"] if \
            self.app.defaults["tools_panelize_constrainx"] else 0.0
        self.x_width_entry.set_value(float(x_w))

        y_w = self.app.defaults["tools_panelize_constrainy"] if \
            self.app.defaults["tools_panelize_constrainy"] else 0.0
        self.y_height_entry.set_value(float(y_w))

        panel_type = self.app.defaults["tools_panelize_panel_type"] if \
            self.app.defaults["tools_panelize_panel_type"] else 'gerber'
        self.panel_type_radio.set_value(panel_type)

    def on_type_obj_index_changed(self):
        obj_type = self.type_obj_combo.currentIndex()
        self.object_combo.setRootModelIndex(self.app.collection.index(obj_type, 0, QtCore.QModelIndex()))
        self.object_combo.setCurrentIndex(0)

    def on_type_box_index_changed(self):
        obj_type = self.type_box_combo.currentIndex()
        self.box_combo.setRootModelIndex(self.app.collection.index(obj_type, 0, QtCore.QModelIndex()))
        self.box_combo.setCurrentIndex(0)

    def on_panelize(self):
        name = self.object_combo.currentText()

        # Get source object.
        try:
            obj = self.app.collection.get_by_name(str(name))
        except:
            self.app.inform.emit(_("[ERROR_NOTCL]Could not retrieve object: %s") % name)
            return "Could not retrieve object: %s" % name

        panel_obj = obj

        if panel_obj is None:
            self.app.inform.emit(_("[ERROR_NOTCL]Object not found: %s") % panel_obj)
            return "Object not found: %s" % panel_obj

        boxname = self.box_combo.currentText()

        try:
            box = self.app.collection.get_by_name(boxname)
        except:
            self.app.inform.emit(_("[ERROR_NOTCL]Could not retrieve object: %s") % boxname)
            return "Could not retrieve object: %s" % boxname

        if box is None:
            self.app.inform.emit(_("[WARNING]No object Box. Using instead %s") % panel_obj)
            box = panel_obj

        self.outname = name + '_panelized'

        try:
            spacing_columns = float(self.spacing_columns.get_value())
        except ValueError:
            # try to convert comma to decimal point. if it's still not working error message and return
            try:
                spacing_columns = float(self.spacing_columns.get_value().replace(',', '.'))
            except ValueError:
                self.app.inform.emit(_("[ERROR_NOTCL]Wrong value format entered, "
                                     "use a number."))
                return
        spacing_columns = spacing_columns if spacing_columns is not None else 0

        try:
            spacing_rows = float(self.spacing_rows.get_value())
        except ValueError:
            # try to convert comma to decimal point. if it's still not working error message and return
            try:
                spacing_rows = float(self.spacing_rows.get_value().replace(',', '.'))
            except ValueError:
                self.app.inform.emit(_("[ERROR_NOTCL]Wrong value format entered, "
                                     "use a number."))
                return
        spacing_rows = spacing_rows if spacing_rows is not None else 0

        try:
            rows = int(self.rows.get_value())
        except ValueError:
            # try to convert comma to decimal point. if it's still not working error message and return
            try:
                rows = float(self.rows.get_value().replace(',', '.'))
                rows = int(rows)
            except ValueError:
                self.app.inform.emit(_("[ERROR_NOTCL]Wrong value format entered, "
                                     "use a number."))
                return
        rows = rows if rows is not None else 1

        try:
            columns = int(self.columns.get_value())
        except ValueError:
            # try to convert comma to decimal point. if it's still not working error message and return
            try:
                columns = float(self.columns.get_value().replace(',', '.'))
                columns = int(columns)
            except ValueError:
                self.app.inform.emit(_("[ERROR_NOTCL]Wrong value format entered, "
                                     "use a number."))
                return
        columns = columns if columns is not None else 1

        try:
            constrain_dx = float(self.x_width_entry.get_value())
        except ValueError:
            # try to convert comma to decimal point. if it's still not working error message and return
            try:
                constrain_dx = float(self.x_width_entry.get_value().replace(',', '.'))
            except ValueError:
                self.app.inform.emit(_("[ERROR_NOTCL]Wrong value format entered, "
                                     "use a number."))
                return

        try:
            constrain_dy = float(self.y_height_entry.get_value())
        except ValueError:
            # try to convert comma to decimal point. if it's still not working error message and return
            try:
                constrain_dy = float(self.y_height_entry.get_value().replace(',', '.'))
            except ValueError:
                self.app.inform.emit(_("[ERROR_NOTCL]Wrong value format entered, "
                                     "use a number."))
                return

        panel_type = str(self.panel_type_radio.get_value())


        if 0 in {columns, rows}:
            self.app.inform.emit(_("[ERROR_NOTCL]Columns or Rows are zero value. Change them to a positive integer."))
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

        def panelize_2():
            if panel_obj is not None:
                self.app.inform.emit(_("Generating panel ... Please wait."))

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
                    self.app.new_object(panel_type, self.outname, job_init_geometry,
                                        plot=True, autoselected=True)

        if self.constrain_flag is False:
            self.app.inform.emit(_("[success]Panel done..."))
        else:
            self.constrain_flag = False
            self.app.inform.emit(_("[WARNING] Too big for the constrain area. Final panel has %s columns and %s rows") %
                                 (columns, rows))

        proc = self.app.proc_container.new(_("Generating panel ... Please wait."))

        def job_thread(app_obj):
            try:
                panelize_2()
                self.app.inform.emit(_("[success]Panel created successfully."))
            except Exception as e:
                proc.done()
                log.debug(str(e))
                return
            proc.done()

        self.app.collection.promise(self.outname)
        self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app]})

    def reset_fields(self):
        self.object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.box_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
