# ########################################################## ##
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 09/27/2019                                          #
# MIT Licence                                              #
# ########################################################## ##

from FlatCAMTool import FlatCAMTool
from copy import copy, deepcopy
from ObjectCollection import *
import time

import gettext
import FlatCAMTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class RulesCheck(FlatCAMTool):

    toolName = _("Check Rules")

    def __init__(self, app):
        super(RulesCheck, self).__init__(self)
        self.app = app

        # ## Title
        title_label = QtWidgets.QLabel("%s" % self.toolName)
        title_label.setStyleSheet("""
                        QLabel
                        {
                            font-size: 16px;
                            font-weight: bold;
                        }
                        """)
        self.layout.addWidget(title_label)

        # Form Layout
        form_layout = QtWidgets.QFormLayout()
        self.layout.addLayout(form_layout)

        self.gerber_title_lbl = QtWidgets.QLabel('<b>%s</b>:' % _("Gerber Files"))
        self.gerber_title_lbl.setToolTip(
            _("Gerber files for which to check rules.")
        )

        # Copper object
        self.copper_object = QtWidgets.QComboBox()
        self.copper_object.setModel(self.app.collection)
        self.copper_object.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.copper_object.setCurrentIndex(1)

        self.copper_object_lbl = QtWidgets.QLabel('%s:' % _("Copper"))
        self.copper_object_lbl.setToolTip(
            _("Object to be panelized. This means that it will\n"
              "be duplicated in an array of rows and columns.")
        )

        # SolderMask object
        self.sm_object = QtWidgets.QComboBox()
        self.sm_object.setModel(self.app.collection)
        self.sm_object.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.sm_object.setCurrentIndex(1)

        self.sm_object_lbl = QtWidgets.QLabel('%s:' % _("SolderMask"))
        self.sm_object_lbl.setToolTip(
            _("Object to be panelized. This means that it will\n"
              "be duplicated in an array of rows and columns.")
        )

        # SilkScreen object
        self.ss_object = QtWidgets.QComboBox()
        self.ss_object.setModel(self.app.collection)
        self.ss_object.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.ss_object.setCurrentIndex(1)

        self.ss_object_lbl = QtWidgets.QLabel('%s:' % _("Silkscreen"))
        self.ss_object_lbl.setToolTip(
            _("Object to be panelized. This means that it will\n"
              "be duplicated in an array of rows and columns.")
        )

        # Outline object
        self.outline_object = QtWidgets.QComboBox()
        self.outline_object.setModel(self.app.collection)
        self.outline_object.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.outline_object.setCurrentIndex(1)

        self.outline_object_lbl = QtWidgets.QLabel('%s:' % _("Outline"))
        self.outline_object_lbl.setToolTip(
            _("Object to be panelized. This means that it will\n"
              "be duplicated in an array of rows and columns.")
        )
        form_layout.addRow(self.gerber_title_lbl)
        form_layout.addRow(self.copper_object_lbl, self.copper_object)
        form_layout.addRow(self.sm_object_lbl, self.sm_object)
        form_layout.addRow(self.ss_object_lbl, self.ss_object)
        form_layout.addRow(self.outline_object_lbl, self.outline_object)
        form_layout.addRow(QtWidgets.QLabel(""))

        self.excellon_title_lbl = QtWidgets.QLabel('<b>%s</b>:' % _("Excellon Files"))
        self.excellon_title_lbl.setToolTip(
            _("Excellon files for which to check rules.")
        )

        # Excellon 1 object
        self.e1_object = QtWidgets.QComboBox()
        self.e1_object.setModel(self.app.collection)
        self.e1_object.setRootModelIndex(self.app.collection.index(1, 0, QtCore.QModelIndex()))
        self.e1_object.setCurrentIndex(1)

        self.e1_object_lbl = QtWidgets.QLabel('%s:' % _("Excellon 1"))
        self.e1_object_lbl.setToolTip(
            _("Object to be panelized. This means that it will\n"
              "be duplicated in an array of rows and columns.")
        )

        # Excellon 2 object
        self.e2_object = QtWidgets.QComboBox()
        self.e2_object.setModel(self.app.collection)
        self.e2_object.setRootModelIndex(self.app.collection.index(1, 0, QtCore.QModelIndex()))
        self.e2_object.setCurrentIndex(1)

        self.e2_object_lbl = QtWidgets.QLabel('%s:' % _("Excellon 2"))
        self.e2_object_lbl.setToolTip(
            _("Object to be panelized. This means that it will\n"
              "be duplicated in an array of rows and columns.")
        )

        form_layout.addRow(self.excellon_title_lbl)
        form_layout.addRow(self.e1_object_lbl, self.e1_object)
        form_layout.addRow(self.e2_object_lbl, self.e2_object)
        form_layout.addRow(QtWidgets.QLabel(""))

        # Form Layout
        form_layout_1 = QtWidgets.QFormLayout()
        self.layout.addLayout(form_layout_1)

        # Copper2copper clearance
        self.clearance_copper2copper_cb = FCCheckBox('%s:' % _("Copper to copper clearance"))
        self.clearance_copper2copper_cb.setToolTip(
            _("This checks if the minimum clearance between copper\n"
              "features is met.")
        )
        form_layout_1.addRow(self.clearance_copper2copper_cb)

        # Copper2copper clearance value
        self.clearance_copper2copper_entry = FCEntry()
        self.clearance_copper2copper_lbl = QtWidgets.QLabel('%s:' % _("Min value"))
        self.clearance_copper2copper_lbl.setToolTip(
            _("Minimum acceptable clearance value.")
        )
        form_layout_1.addRow(self.clearance_copper2copper_lbl, self.clearance_copper2copper_entry)

        self.c2c = OptionalInputSection(
            self.clearance_copper2copper_cb, [self.clearance_copper2copper_lbl, self.clearance_copper2copper_entry])

        # Copper2soldermask clearance
        self.clearance_copper2sm_cb = FCCheckBox('%s:' % _("Copper to soldermask clearance"))
        self.clearance_copper2sm_cb.setToolTip(
            _("This checks if the minimum clearance between copper\n"
              "features and soldermask features is met.")
        )
        form_layout_1.addRow(self.clearance_copper2sm_cb)

        # Copper2soldermask clearance value
        self.clearance_copper2sm_entry = FCEntry()
        self.clearance_copper2sm_lbl = QtWidgets.QLabel('%s:' % _("Min value"))
        self.clearance_copper2sm_lbl.setToolTip(
            _("Minimum acceptable clearance value.")
        )
        form_layout_1.addRow(self.clearance_copper2sm_lbl, self.clearance_copper2sm_entry)

        self.c2sm = OptionalInputSection(
            self.clearance_copper2sm_cb, [self.clearance_copper2sm_lbl, self.clearance_copper2sm_entry])

        # Copper2silkscreen clearance
        self.clearance_copper2sk_cb = FCCheckBox('%s:' % _("Copper to silkscreen clearance"))
        self.clearance_copper2sk_cb.setToolTip(
            _("This checks if the minimum clearance between copper\n"
              "features and silkscreen features is met.")
        )
        form_layout_1.addRow(self.clearance_copper2sk_cb)

        # Copper2silkscreen clearance value
        self.clearance_copper2sk_entry = FCEntry()
        self.clearance_copper2sk_lbl = QtWidgets.QLabel('%s:' % _("Min value"))
        self.clearance_copper2sk_lbl.setToolTip(
            _("Minimum acceptable clearance value.")
        )
        form_layout_1.addRow(self.clearance_copper2sk_lbl, self.clearance_copper2sk_entry)

        self.c2sk = OptionalInputSection(
            self.clearance_copper2sk_cb, [self.clearance_copper2sk_lbl, self.clearance_copper2sk_entry])

        # Copper2outline clearance
        self.clearance_copper2ol_cb = FCCheckBox('%s:' % _("Copper to outline clearance"))
        self.clearance_copper2ol_cb.setToolTip(
            _("This checks if the minimum clearance between copper\n"
              "features and the outline is met.")
        )
        form_layout_1.addRow(self.clearance_copper2ol_cb)

        # Copper2outline clearance value
        self.clearance_copper2ol_entry = FCEntry()
        self.clearance_copper2ol_lbl = QtWidgets.QLabel('%s:' % _("Min value"))
        self.clearance_copper2ol_lbl.setToolTip(
            _("Minimum acceptable clearance value.")
        )
        form_layout_1.addRow(self.clearance_copper2ol_lbl, self.clearance_copper2ol_entry)

        self.c2ol = OptionalInputSection(
            self.clearance_copper2ol_cb, [self.clearance_copper2ol_lbl, self.clearance_copper2ol_entry])

        # Silkscreen2silkscreen clearance
        self.clearance_silk2silk_cb = FCCheckBox('%s:' % _("Silkscreen to silkscreen clearance"))
        self.clearance_silk2silk_cb.setToolTip(
            _("This checks if the minimum clearance between silkscreen\n"
              "features and silkscreen features is met.")
        )
        form_layout_1.addRow(self.clearance_silk2silk_cb)

        # Copper2silkscreen clearance value
        self.clearance_silk2silk_entry = FCEntry()
        self.clearance_silk2silk_lbl = QtWidgets.QLabel('%s:' % _("Min value"))
        self.clearance_silk2silk_lbl.setToolTip(
            _("Minimum acceptable clearance value.")
        )
        form_layout_1.addRow(self.clearance_silk2silk_lbl, self.clearance_silk2silk_entry)

        self.s2s = OptionalInputSection(
            self.clearance_silk2silk_cb, [self.clearance_silk2silk_lbl, self.clearance_silk2silk_entry])

        # Silkscreen2soldermask clearance
        self.clearance_silk2sm_cb = FCCheckBox('%s:' % _("Silkscreen to soldermask clearance"))
        self.clearance_silk2sm_cb.setToolTip(
            _("This checks if the minimum clearance between silkscreen\n"
              "features and soldermask features is met.")
        )
        form_layout_1.addRow(self.clearance_silk2sm_cb)

        # Silkscreen2soldermask clearance value
        self.clearance_silk2sm_entry = FCEntry()
        self.clearance_silk2sm_lbl = QtWidgets.QLabel('%s:' % _("Min value"))
        self.clearance_silk2sm_lbl.setToolTip(
            _("Minimum acceptable clearance value.")
        )
        form_layout_1.addRow(self.clearance_silk2sm_lbl, self.clearance_silk2sm_entry)

        self.s2sm = OptionalInputSection(
            self.clearance_silk2sm_cb, [self.clearance_silk2sm_lbl, self.clearance_silk2sm_entry])

        # Soldermask2soldermask clearance
        self.clearance_sm2sm_cb = FCCheckBox('%s:' % _("Soldermask to soldermask clearance"))
        self.clearance_sm2sm_cb.setToolTip(
            _("This checks if the minimum clearance between soldermask\n"
              "features and soldermask features is met.")
        )
        form_layout_1.addRow(self.clearance_sm2sm_cb)

        # Soldermask2soldermask clearance value
        self.clearance_sm2sm_entry = FCEntry()
        self.clearance_sm2sm_lbl = QtWidgets.QLabel('%s:' % _("Min value"))
        self.clearance_sm2sm_lbl.setToolTip(
            _("Minimum acceptable clearance value.")
        )
        form_layout_1.addRow(self.clearance_sm2sm_lbl, self.clearance_sm2sm_entry)

        self.sm2sm = OptionalInputSection(
            self.clearance_sm2sm_cb, [self.clearance_sm2sm_lbl, self.clearance_sm2sm_entry])

        form_layout_1.addRow(QtWidgets.QLabel(""))

        # Drill2Drill clearance
        self.clearance_d2d_cb = FCCheckBox('%s:' % _("Drill hole to drill hole clearance"))
        self.clearance_d2d_cb.setToolTip(
            _("This checks if the minimum clearance between a drill hole\n"
              "and another drill hole is met.")
        )
        form_layout_1.addRow(self.clearance_d2d_cb)

        # Drill2Drill clearance value
        self.clearance_d2d_entry = FCEntry()
        self.clearance_d2d_lbl = QtWidgets.QLabel('%s:' % _("Min value"))
        self.clearance_d2d_lbl.setToolTip(
            _("Minimum acceptable clearance value.")
        )
        form_layout_1.addRow(self.clearance_d2d_lbl, self.clearance_d2d_entry)

        self.d2d = OptionalInputSection(
            self.clearance_d2d_cb, [self.clearance_d2d_lbl, self.clearance_d2d_entry])

        # Ring integrity check
        self.ring_integrity_cb = FCCheckBox('%s:' % _("Ring integrity check"))
        self.ring_integrity_cb.setToolTip(
            _("This checks if the minimum copper ring left by drilling\n"
              "a hole into a pad is met.")
        )
        form_layout_1.addRow(self.ring_integrity_cb)

        # Ring integrity value
        self.ring_integrity_entry = FCEntry()
        self.ring_integrity_lbl = QtWidgets.QLabel('%s:' % _("Min value"))
        self.ring_integrity_lbl.setToolTip(
            _("Minimum acceptable ring value.")
        )
        form_layout_1.addRow(self.ring_integrity_lbl, self.ring_integrity_entry)

        self.d2d = OptionalInputSection(
            self.ring_integrity_cb, [self.ring_integrity_lbl, self.ring_integrity_entry])

        # Drill holes overlap check
        self.drill_overlap_cb = FCCheckBox('%s:' % _("Drill hole overlap check"))
        self.drill_overlap_cb.setToolTip(
            _("This checks if drill holes are overlapping\n"
              "one over another.")
        )
        form_layout_1.addRow(self.drill_overlap_cb)

        # Buttons
        hlay_2 = QtWidgets.QHBoxLayout()
        self.layout.addLayout(hlay_2)

        # hlay_2.addStretch()
        self.run_button = QtWidgets.QPushButton(_("Run Rules Check"))
        self.run_button.setToolTip(
            _("Panelize the specified object around the specified box.\n"
              "In other words it creates multiple copies of the source object,\n"
              "arranged in a 2D array of rows and columns.")
        )
        hlay_2.addWidget(self.run_button)

        self.layout.addStretch()

        # #######################################################
        # ################ SIGNALS ##############################
        # #######################################################

        # self.app.collection.rowsInserted.connect(self.on_object_loaded)

        # list to hold the temporary objects
        self.objs = []

        # final name for the panel object
        self.outname = ""

        # flag to signal the constrain was activated
        self.constrain_flag = False

    # def on_object_loaded(self, index, row):
    #     print(index.internalPointer().child_items[row].obj.options['name'], index.data())

    def run(self, toggle=True):
        self.app.report_usage("ToolRulesCheck()")

        if toggle:
            # if the splitter is hidden, display it, else hide it but only if the current widget is the same
            if self.app.ui.splitter.sizes()[0] == 0:
                self.app.ui.splitter.setSizes([1, 1])
            else:
                try:
                    if self.app.ui.tool_scroll_area.widget().objectName() == self.toolName:
                        # if tab is populated with the tool but it does not have the focus, focus on it
                        if not self.app.ui.notebook.currentWidget() is self.app.ui.tool_tab:
                            # focus on Tool Tab
                            self.app.ui.notebook.setCurrentWidget(self.app.ui.tool_tab)
                        else:
                            self.app.ui.splitter.setSizes([0, 1])
                except AttributeError:
                    pass
        else:
            if self.app.ui.splitter.sizes()[0] == 0:
                self.app.ui.splitter.setSizes([1, 1])

        FlatCAMTool.run(self)
        self.set_tool_ui()

        self.app.ui.notebook.setTabText(2, _("Rules Tool"))

    def install(self, icon=None, separator=None, **kwargs):
        FlatCAMTool.install(self, icon, separator, shortcut='ALT+R', **kwargs)

    def set_tool_ui(self):
        self.reset_fields()

    # def on_panelize(self):
    #     name = self.object_combo.currentText()
    #
    #     # Get source object.
    #     try:
    #         obj = self.app.collection.get_by_name(str(name))
    #     except Exception as e:
    #         log.debug("Panelize.on_panelize() --> %s" % str(e))
    #         self.app.inform.emit('[ERROR_NOTCL] %s: %s' %
    #                              (_("Could not retrieve object"), name))
    #         return "Could not retrieve object: %s" % name
    #
    #     panel_obj = obj
    #
    #     if panel_obj is None:
    #         self.app.inform.emit('[ERROR_NOTCL] %s: %s' %
    #                              (_("Object not found"), panel_obj))
    #         return "Object not found: %s" % panel_obj
    #
    #     boxname = self.box_combo.currentText()
    #
    #     try:
    #         box = self.app.collection.get_by_name(boxname)
    #     except Exception as e:
    #         log.debug("Panelize.on_panelize() --> %s" % str(e))
    #         self.app.inform.emit('[ERROR_NOTCL] %s: %s' %
    #                              (_("Could not retrieve object"), boxname))
    #         return "Could not retrieve object: %s" % boxname
    #
    #     if box is None:
    #         self.app.inform.emit('[WARNING_NOTCL]%s: %s' %
    #                              (_("No object Box. Using instead"), panel_obj))
    #         self.reference_radio.set_value('bbox')
    #
    #     if self.reference_radio.get_value() == 'bbox':
    #         box = panel_obj
    #
    #     self.outname = name + '_panelized'
    #
    #     try:
    #         spacing_columns = float(self.spacing_columns.get_value())
    #     except ValueError:
    #         # try to convert comma to decimal point. if it's still not working error message and return
    #         try:
    #             spacing_columns = float(self.spacing_columns.get_value().replace(',', '.'))
    #         except ValueError:
    #             self.app.inform.emit('[ERROR_NOTCL] %s' %
    #                                  _("Wrong value format entered, use a number."))
    #             return
    #     spacing_columns = spacing_columns if spacing_columns is not None else 0
    #
    #     try:
    #         spacing_rows = float(self.spacing_rows.get_value())
    #     except ValueError:
    #         # try to convert comma to decimal point. if it's still not working error message and return
    #         try:
    #             spacing_rows = float(self.spacing_rows.get_value().replace(',', '.'))
    #         except ValueError:
    #             self.app.inform.emit('[ERROR_NOTCL] %s' %
    #                                  _("Wrong value format entered, use a number."))
    #             return
    #     spacing_rows = spacing_rows if spacing_rows is not None else 0
    #
    #     try:
    #         rows = int(self.rows.get_value())
    #     except ValueError:
    #         # try to convert comma to decimal point. if it's still not working error message and return
    #         try:
    #             rows = float(self.rows.get_value().replace(',', '.'))
    #             rows = int(rows)
    #         except ValueError:
    #             self.app.inform.emit('[ERROR_NOTCL] %s' %
    #                                  _("Wrong value format entered, use a number."))
    #             return
    #     rows = rows if rows is not None else 1
    #
    #     try:
    #         columns = int(self.columns.get_value())
    #     except ValueError:
    #         # try to convert comma to decimal point. if it's still not working error message and return
    #         try:
    #             columns = float(self.columns.get_value().replace(',', '.'))
    #             columns = int(columns)
    #         except ValueError:
    #             self.app.inform.emit('[ERROR_NOTCL] %s' %
    #                                  _("Wrong value format entered, use a number."))
    #             return
    #     columns = columns if columns is not None else 1
    #
    #     try:
    #         constrain_dx = float(self.x_width_entry.get_value())
    #     except ValueError:
    #         # try to convert comma to decimal point. if it's still not working error message and return
    #         try:
    #             constrain_dx = float(self.x_width_entry.get_value().replace(',', '.'))
    #         except ValueError:
    #             self.app.inform.emit('[ERROR_NOTCL] %s' %
    #                                  _("Wrong value format entered, use a number."))
    #             return
    #
    #     try:
    #         constrain_dy = float(self.y_height_entry.get_value())
    #     except ValueError:
    #         # try to convert comma to decimal point. if it's still not working error message and return
    #         try:
    #             constrain_dy = float(self.y_height_entry.get_value().replace(',', '.'))
    #         except ValueError:
    #             self.app.inform.emit('[ERROR_NOTCL] %s' %
    #                                  _("Wrong value format entered, use a number."))
    #             return
    #
    #     panel_type = str(self.panel_type_radio.get_value())
    #
    #     if 0 in {columns, rows}:
    #         self.app.inform.emit('[ERROR_NOTCL] %s' %
    #                              _("Columns or Rows are zero value. Change them to a positive integer."))
    #         return "Columns or Rows are zero value. Change them to a positive integer."
    #
    #     xmin, ymin, xmax, ymax = box.bounds()
    #     lenghtx = xmax - xmin + spacing_columns
    #     lenghty = ymax - ymin + spacing_rows
    #
    #     # check if constrain within an area is desired
    #     if self.constrain_cb.isChecked():
    #         panel_lengthx = ((xmax - xmin) * columns) + (spacing_columns * (columns - 1))
    #         panel_lengthy = ((ymax - ymin) * rows) + (spacing_rows * (rows - 1))
    #
    #         # adjust the number of columns and/or rows so the panel will fit within the panel constraint area
    #         if (panel_lengthx > constrain_dx) or (panel_lengthy > constrain_dy):
    #             self.constrain_flag = True
    #
    #             while panel_lengthx > constrain_dx:
    #                 columns -= 1
    #                 panel_lengthx = ((xmax - xmin) * columns) + (spacing_columns * (columns - 1))
    #             while panel_lengthy > constrain_dy:
    #                 rows -= 1
    #                 panel_lengthy = ((ymax - ymin) * rows) + (spacing_rows * (rows - 1))
    #
    #     def panelize_2():
    #         if panel_obj is not None:
    #             self.app.inform.emit(_("Generating panel ... "))
    #
    #             self.app.progress.emit(0)
    #
    #             def job_init_excellon(obj_fin, app_obj):
    #                 currenty = 0.0
    #                 self.app.progress.emit(10)
    #                 obj_fin.tools = panel_obj.tools.copy()
    #                 obj_fin.drills = []
    #                 obj_fin.slots = []
    #                 obj_fin.solid_geometry = []
    #
    #                 for option in panel_obj.options:
    #                     if option is not 'name':
    #                         try:
    #                             obj_fin.options[option] = panel_obj.options[option]
    #                         except KeyError:
    #                             log.warning("Failed to copy option. %s" % str(option))
    #
    #                 geo_len_drills = len(panel_obj.drills) if panel_obj.drills else 0
    #                 geo_len_slots = len(panel_obj.slots) if panel_obj.slots else 0
    #
    #                 element = 0
    #                 for row in range(rows):
    #                     currentx = 0.0
    #                     for col in range(columns):
    #                         element += 1
    #                         disp_number = 0
    #                         old_disp_number = 0
    #
    #                         if panel_obj.drills:
    #                             drill_nr = 0
    #                             for tool_dict in panel_obj.drills:
    #                                 if self.app.abort_flag:
    #                                     # graceful abort requested by the user
    #                                     raise FlatCAMApp.GracefulException
    #
    #                                 point_offseted = affinity.translate(tool_dict['point'], currentx, currenty)
    #                                 obj_fin.drills.append(
    #                                     {
    #                                         "point": point_offseted,
    #                                         "tool": tool_dict['tool']
    #                                     }
    #                                 )
    #
    #                                 drill_nr += 1
    #                                 disp_number = int(np.interp(drill_nr, [0, geo_len_drills], [0, 100]))
    #
    #                                 if disp_number > old_disp_number and disp_number <= 100:
    #                                     self.app.proc_container.update_view_text(' %s: %d D:%d%%' %
    #                                                                              (_("Copy"),
    #                                                                               int(element),
    #                                                                               disp_number))
    #                                     old_disp_number = disp_number
    #
    #                         if panel_obj.slots:
    #                             slot_nr = 0
    #                             for tool_dict in panel_obj.slots:
    #                                 if self.app.abort_flag:
    #                                     # graceful abort requested by the user
    #                                     raise FlatCAMApp.GracefulException
    #
    #                                 start_offseted = affinity.translate(tool_dict['start'], currentx, currenty)
    #                                 stop_offseted = affinity.translate(tool_dict['stop'], currentx, currenty)
    #                                 obj_fin.slots.append(
    #                                     {
    #                                         "start": start_offseted,
    #                                         "stop": stop_offseted,
    #                                         "tool": tool_dict['tool']
    #                                     }
    #                                 )
    #
    #                                 slot_nr += 1
    #                                 disp_number = int(np.interp(slot_nr, [0, geo_len_slots], [0, 100]))
    #
    #                                 if disp_number > old_disp_number and disp_number <= 100:
    #                                     self.app.proc_container.update_view_text(' %s: %d S:%d%%' %
    #                                                                              (_("Copy"),
    #                                                                               int(element),
    #                                                                               disp_number))
    #                                     old_disp_number = disp_number
    #
    #                         currentx += lenghtx
    #                     currenty += lenghty
    #
    #                 obj_fin.create_geometry()
    #                 obj_fin.zeros = panel_obj.zeros
    #                 obj_fin.units = panel_obj.units
    #                 self.app.proc_container.update_view_text('')
    #
    #             def job_init_geometry(obj_fin, app_obj):
    #                 currentx = 0.0
    #                 currenty = 0.0
    #
    #                 def translate_recursion(geom):
    #                     if type(geom) == list:
    #                         geoms = list()
    #                         for local_geom in geom:
    #                             res_geo = translate_recursion(local_geom)
    #                             try:
    #                                 geoms += res_geo
    #                             except TypeError:
    #                                 geoms.append(res_geo)
    #                         return geoms
    #                     else:
    #                         return affinity.translate(geom, xoff=currentx, yoff=currenty)
    #
    #                 obj_fin.solid_geometry = []
    #
    #                 # create the initial structure on which to create the panel
    #                 if isinstance(panel_obj, FlatCAMGeometry):
    #                     obj_fin.multigeo = panel_obj.multigeo
    #                     obj_fin.tools = deepcopy(panel_obj.tools)
    #                     if panel_obj.multigeo is True:
    #                         for tool in panel_obj.tools:
    #                             obj_fin.tools[tool]['solid_geometry'][:] = []
    #                 elif isinstance(panel_obj, FlatCAMGerber):
    #                     obj_fin.apertures = deepcopy(panel_obj.apertures)
    #                     for ap in obj_fin.apertures:
    #                         obj_fin.apertures[ap]['geometry'] = list()
    #
    #                 # find the number of polygons in the source solid_geometry
    #                 geo_len = 0
    #                 if isinstance(panel_obj, FlatCAMGeometry):
    #                     if panel_obj.multigeo is True:
    #                         for tool in panel_obj.tools:
    #                             try:
    #                                 for pol in panel_obj.tools[tool]['solid_geometry']:
    #                                     geo_len += 1
    #                             except TypeError:
    #                                 geo_len = 1
    #                     else:
    #                         try:
    #                             for pol in panel_obj.solid_geometry:
    #                                 geo_len += 1
    #                         except TypeError:
    #                             geo_len = 1
    #                 elif isinstance(panel_obj, FlatCAMGerber):
    #                     for ap in panel_obj.apertures:
    #                         for elem in panel_obj.apertures[ap]['geometry']:
    #                             geo_len += 1
    #
    #                 self.app.progress.emit(0)
    #                 element = 0
    #                 for row in range(rows):
    #                     currentx = 0.0
    #
    #                     for col in range(columns):
    #                         element += 1
    #                         disp_number = 0
    #                         old_disp_number = 0
    #
    #                         if isinstance(panel_obj, FlatCAMGeometry):
    #                             if panel_obj.multigeo is True:
    #                                 for tool in panel_obj.tools:
    #                                     if self.app.abort_flag:
    #                                         # graceful abort requested by the user
    #                                         raise FlatCAMApp.GracefulException
    #
    #                                     # geo = translate_recursion(panel_obj.tools[tool]['solid_geometry'])
    #                                     # if isinstance(geo, list):
    #                                     #     obj_fin.tools[tool]['solid_geometry'] += geo
    #                                     # else:
    #                                     #     obj_fin.tools[tool]['solid_geometry'].append(geo)
    #
    #                                     # calculate the number of polygons
    #                                     geo_len = len(panel_obj.tools[tool]['solid_geometry'])
    #                                     pol_nr = 0
    #                                     for geo_el in panel_obj.tools[tool]['solid_geometry']:
    #                                         trans_geo = translate_recursion(geo_el)
    #                                         obj_fin.tools[tool]['solid_geometry'].append(trans_geo)
    #
    #                                         pol_nr += 1
    #                                         disp_number = int(np.interp(pol_nr, [0, geo_len], [0, 100]))
    #
    #                                         if old_disp_number < disp_number <= 100:
    #                                             self.app.proc_container.update_view_text(' %s: %d %d%%' %
    #                                                                                      (_("Copy"),
    #                                                                                       int(element),
    #                                                                                       disp_number))
    #                                             old_disp_number = disp_number
    #                             else:
    #                                 # geo = translate_recursion(panel_obj.solid_geometry)
    #                                 # if isinstance(geo, list):
    #                                 #     obj_fin.solid_geometry += geo
    #                                 # else:
    #                                 #     obj_fin.solid_geometry.append(geo)
    #                                 if self.app.abort_flag:
    #                                     # graceful abort requested by the user
    #                                     raise FlatCAMApp.GracefulException
    #
    #                                 try:
    #                                     # calculate the number of polygons
    #                                     geo_len = len(panel_obj.solid_geometry)
    #                                 except TypeError:
    #                                     geo_len = 1
    #                                 pol_nr = 0
    #                                 try:
    #                                     for geo_el in panel_obj.solid_geometry:
    #                                         if self.app.abort_flag:
    #                                             # graceful abort requested by the user
    #                                             raise FlatCAMApp.GracefulException
    #
    #                                         trans_geo = translate_recursion(geo_el)
    #                                         obj_fin.solid_geometry.append(trans_geo)
    #
    #                                         pol_nr += 1
    #                                         disp_number = int(np.interp(pol_nr, [0, geo_len], [0, 100]))
    #
    #                                         if old_disp_number < disp_number <= 100:
    #                                             self.app.proc_container.update_view_text(' %s: %d %d%%' %
    #                                                                                      (_("Copy"),
    #                                                                                       int(element),
    #                                                                                       disp_number))
    #                                             old_disp_number = disp_number
    #                                 except TypeError:
    #                                     trans_geo = translate_recursion(panel_obj.solid_geometry)
    #                                     obj_fin.solid_geometry.append(trans_geo)
    #                         else:
    #                             # geo = translate_recursion(panel_obj.solid_geometry)
    #                             # if isinstance(geo, list):
    #                             #     obj_fin.solid_geometry += geo
    #                             # else:
    #                             #     obj_fin.solid_geometry.append(geo)
    #                             if self.app.abort_flag:
    #                                 # graceful abort requested by the user
    #                                 raise FlatCAMApp.GracefulException
    #
    #                             try:
    #                                 for geo_el in panel_obj.solid_geometry:
    #                                     if self.app.abort_flag:
    #                                         # graceful abort requested by the user
    #                                         raise FlatCAMApp.GracefulException
    #
    #                                     trans_geo = translate_recursion(geo_el)
    #                                     obj_fin.solid_geometry.append(trans_geo)
    #                             except TypeError:
    #                                 trans_geo = translate_recursion(panel_obj.solid_geometry)
    #                                 obj_fin.solid_geometry.append(trans_geo)
    #
    #                             for apid in panel_obj.apertures:
    #                                 if self.app.abort_flag:
    #                                     # graceful abort requested by the user
    #                                     raise FlatCAMApp.GracefulException
    #
    #                                 try:
    #                                     # calculate the number of polygons
    #                                     geo_len = len(panel_obj.apertures[apid]['geometry'])
    #                                 except TypeError:
    #                                     geo_len = 1
    #                                 pol_nr = 0
    #                                 for el in panel_obj.apertures[apid]['geometry']:
    #                                     if self.app.abort_flag:
    #                                         # graceful abort requested by the user
    #                                         raise FlatCAMApp.GracefulException
    #
    #                                     new_el = dict()
    #                                     if 'solid' in el:
    #                                         geo_aper = translate_recursion(el['solid'])
    #                                         new_el['solid'] = geo_aper
    #
    #                                     if 'clear' in el:
    #                                         geo_aper = translate_recursion(el['clear'])
    #                                         new_el['clear'] = geo_aper
    #
    #                                     if 'follow' in el:
    #                                         geo_aper = translate_recursion(el['follow'])
    #                                         new_el['follow'] = geo_aper
    #
    #                                     obj_fin.apertures[apid]['geometry'].append(deepcopy(new_el))
    #
    #                                     pol_nr += 1
    #                                     disp_number = int(np.interp(pol_nr, [0, geo_len], [0, 100]))
    #
    #                                     if old_disp_number < disp_number <= 100:
    #                                         self.app.proc_container.update_view_text(' %s: %d %d%%' %
    #                                                                                  (_("Copy"),
    #                                                                                   int(element),
    #                                                                                   disp_number))
    #                                         old_disp_number = disp_number
    #
    #                         currentx += lenghtx
    #                     currenty += lenghty
    #
    #                 if panel_type == 'gerber':
    #                     self.app.inform.emit('%s' %
    #                                          _("Generating panel ... Adding the Gerber code."))
    #                     obj_fin.source_file = self.app.export_gerber(obj_name=self.outname, filename=None,
    #                                                                  local_use=obj_fin, use_thread=False)
    #
    #                 # app_obj.log.debug("Found %s geometries. Creating a panel geometry cascaded union ..." %
    #                 #                   len(obj_fin.solid_geometry))
    #
    #                 # obj_fin.solid_geometry = cascaded_union(obj_fin.solid_geometry)
    #                 # app_obj.log.debug("Finished creating a cascaded union for the panel.")
    #                 self.app.proc_container.update_view_text('')
    #
    #             self.app.inform.emit('%s: %d' %
    #                                  (_("Generating panel... Spawning copies"), (int(rows * columns))))
    #             if isinstance(panel_obj, FlatCAMExcellon):
    #                 self.app.progress.emit(50)
    #                 self.app.new_object("excellon", self.outname, job_init_excellon, plot=True, autoselected=True)
    #             else:
    #                 self.app.progress.emit(50)
    #                 self.app.new_object(panel_type, self.outname, job_init_geometry,
    #                                     plot=True, autoselected=True)
    #
    #     if self.constrain_flag is False:
    #         self.app.inform.emit('[success] %s' % _("Panel done..."))
    #     else:
    #         self.constrain_flag = False
    #         self.app.inform.emit(_("{text} Too big for the constrain area. "
    #                                "Final panel has {col} columns and {row} rows").format(
    #             text='[WARNING] ', col=columns, row=rows))
    #
    #     proc = self.app.proc_container.new(_("Working..."))
    #
    #     def job_thread(app_obj):
    #         try:
    #             panelize_2()
    #             self.app.inform.emit('[success] %s' % _("Panel created successfully."))
    #         except Exception as ee:
    #             proc.done()
    #             log.debug(str(ee))
    #             return
    #         proc.done()
    #
    #     self.app.collection.promise(self.outname)
    #     self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app]})

    def reset_fields(self):
        # self.object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        # self.box_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        pass
