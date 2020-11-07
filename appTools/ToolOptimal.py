# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 09/27/2019                                         #
# MIT Licence                                              #
# ##########################################################

from PyQt5 import QtWidgets, QtCore, QtGui

from appTool import AppTool
from appGUI.GUIElements import OptionalHideInputSection, FCTextArea, FCEntry, FCSpinner, FCCheckBox, FCComboBox, \
    FCLabel, FCButton
from camlib import grace

from shapely.geometry import MultiPolygon
from shapely.ops import nearest_points

import numpy as np

import logging
import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class ToolOptimal(AppTool):

    update_text = QtCore.pyqtSignal(list)
    update_sec_distances = QtCore.pyqtSignal(dict)

    def __init__(self, app):
        AppTool.__init__(self, app)

        self.units = self.app.defaults['units'].upper()
        self.decimals = self.app.decimals

        # #############################################################################
        # ######################### Tool GUI ##########################################
        # #############################################################################
        self.ui = OptimalUI(layout=self.layout, app=self.app)
        self.toolName = self.ui.toolName

        # this is the line selected in the textbox with the locations of the minimum
        self.selected_text = ''

        # this is the line selected in the textbox with the locations of the other distances found in the Gerber object
        self.selected_locations_text = ''

        # dict to hold the distances between every two elements in Gerber as keys and the actual locations where that
        # distances happen as values
        self.min_dict = {}

        # ############################################################################
        # ############################ Signals #######################################
        # ############################################################################
        self.update_text.connect(self.on_update_text)
        self.update_sec_distances.connect(self.on_update_sec_distances_txt)

        self.ui.calculate_button.clicked.connect(self.find_minimum_distance)
        self.ui.locate_button.clicked.connect(self.on_locate_position)
        self.ui.locations_textb.cursorPositionChanged.connect(self.on_textbox_clicked)

        self.ui.locate_sec_button.clicked.connect(self.on_locate_sec_position)
        self.ui.distances_textb.cursorPositionChanged.connect(self.on_distances_textb_clicked)
        self.ui.locations_sec_textb.cursorPositionChanged.connect(self.on_locations_sec_clicked)

        self.ui.reset_button.clicked.connect(self.set_tool_ui)

    def install(self, icon=None, separator=None, **kwargs):
        AppTool.install(self, icon, separator, shortcut='Alt+O', **kwargs)

    def run(self, toggle=True):
        self.app.defaults.report_usage("ToolOptimal()")

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

        AppTool.run(self)
        self.set_tool_ui()

        self.app.ui.notebook.setTabText(2, _("Optimal Tool"))

    def set_tool_ui(self):
        self.ui.result_entry.set_value(0.0)
        self.ui.freq_entry.set_value('0')

        self.ui.precision_spinner.set_value(int(self.app.defaults["tools_opt_precision"]))
        self.ui.locations_textb.clear()
        # new cursor - select all document
        cursor = self.ui.locations_textb.textCursor()
        cursor.select(QtGui.QTextCursor.Document)

        # clear previous selection highlight
        tmp = cursor.blockFormat()
        tmp.clearBackground()
        cursor.setBlockFormat(tmp)

        self.ui.locations_textb.setVisible(False)
        self.ui.locate_button.setVisible(False)

        self.ui.result_entry.set_value(0.0)
        self.ui.freq_entry.set_value('0')
        self.reset_fields()

    def find_minimum_distance(self):
        self.units = self.app.defaults['units'].upper()
        self.decimals = int(self.ui.precision_spinner.get_value())

        selection_index = self.ui.gerber_object_combo.currentIndex()

        model_index = self.app.collection.index(selection_index, 0, self.ui.gerber_object_combo.rootModelIndex())
        try:
            fcobj = model_index.internalPointer().obj
        except Exception as e:
            log.debug("ToolOptimal.find_minimum_distance() --> %s" % str(e))
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("There is no Gerber object loaded ..."))
            return

        if fcobj.kind != 'gerber':
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("Only Gerber objects can be evaluated."))
            return

        proc = self.app.proc_container.new(_("Working ..."))

        def job_thread(app_obj):
            app_obj.inform.emit(_("Optimal Tool. Started to search for the minimum distance between copper features."))
            try:
                old_disp_number = 0
                pol_nr = 0
                app_obj.proc_container.update_view_text(' %d%%' % 0)
                total_geo = []

                for ap in list(fcobj.apertures.keys()):
                    if 'geometry' in fcobj.apertures[ap]:
                        app_obj.inform.emit(
                            '%s: %s' % (_("Optimal Tool. Parsing geometry for aperture"), str(ap)))

                        for geo_el in fcobj.apertures[ap]['geometry']:
                            if self.app.abort_flag:
                                # graceful abort requested by the user
                                raise grace

                            if 'solid' in geo_el and geo_el['solid'] is not None and geo_el['solid'].is_valid:
                                total_geo.append(geo_el['solid'])

                app_obj.inform.emit(
                    _("Optimal Tool. Creating a buffer for the object geometry."))
                total_geo = MultiPolygon(total_geo)
                total_geo = total_geo.buffer(0)

                try:
                    __ = iter(total_geo)
                    geo_len = len(total_geo)
                    geo_len = (geo_len * (geo_len - 1)) / 2
                except TypeError:
                    app_obj.inform.emit('[ERROR_NOTCL] %s' %
                                        _("The Gerber object has one Polygon as geometry.\n"
                                          "There are no distances between geometry elements to be found."))
                    return 'fail'

                app_obj.inform.emit(
                    '%s: %s' % (_("Optimal Tool. Finding the distances between each two elements. Iterations"),
                                str(geo_len)))

                self.min_dict = {}
                idx = 1
                for geo in total_geo:
                    for s_geo in total_geo[idx:]:
                        if self.app.abort_flag:
                            # graceful abort requested by the user
                            raise grace

                        # minimize the number of distances by not taking into considerations those that are too small
                        dist = geo.distance(s_geo)
                        dist = float('%.*f' % (self.decimals, dist))
                        loc_1, loc_2 = nearest_points(geo, s_geo)

                        proc_loc = (
                            (float('%.*f' % (self.decimals, loc_1.x)), float('%.*f' % (self.decimals, loc_1.y))),
                            (float('%.*f' % (self.decimals, loc_2.x)), float('%.*f' % (self.decimals, loc_2.y)))
                        )

                        if dist in self.min_dict:
                            self.min_dict[dist].append(proc_loc)
                        else:
                            self.min_dict[dist] = [proc_loc]

                        pol_nr += 1
                        disp_number = int(np.interp(pol_nr, [0, geo_len], [0, 100]))

                        if old_disp_number < disp_number <= 100:
                            app_obj.proc_container.update_view_text(' %d%%' % disp_number)
                            old_disp_number = disp_number
                    idx += 1

                app_obj.inform.emit(_("Optimal Tool. Finding the minimum distance."))

                min_list = list(self.min_dict.keys())
                min_dist = min(min_list)
                min_dist_string = '%.*f' % (self.decimals, float(min_dist))
                self.ui.result_entry.set_value(min_dist_string)

                freq = len(self.min_dict[min_dist])
                freq = '%d' % int(freq)
                self.ui.freq_entry.set_value(freq)

                min_locations = self.min_dict.pop(min_dist)

                self.update_text.emit(min_locations)
                self.update_sec_distances.emit(self.min_dict)

                app_obj.inform.emit('[success] %s' % _("Optimal Tool. Finished successfully."))
            except Exception as ee:
                proc.done()
                log.debug(str(ee))
                return
            proc.done()

        self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app]})

    def on_locate_position(self):
        # cursor = self.locations_textb.textCursor()
        # self.selected_text = cursor.selectedText()

        try:
            if self.selected_text != '':
                loc = eval(self.selected_text)
            else:
                return 'fail'
        except Exception as e:
            log.debug("ToolOptimal.on_locate_position() --> first try %s" % str(e))
            self.app.inform.emit("[ERROR_NOTCL] The selected text is no valid location in the format "
                                 "((x0, y0), (x1, y1)).")
            return

        try:
            loc_1 = loc[0]
            loc_2 = loc[1]
            dx = loc_1[0] - loc_2[0]
            dy = loc_1[1] - loc_2[1]
            loc = (float('%.*f' % (self.decimals, (min(loc_1[0], loc_2[0]) + (abs(dx) / 2)))),
                   float('%.*f' % (self.decimals, (min(loc_1[1], loc_2[1]) + (abs(dy) / 2)))))
            self.app.on_jump_to(custom_location=loc)
        except Exception as e:
            log.debug("ToolOptimal.on_locate_position() --> sec try %s" % str(e))
            return

    def on_update_text(self, data):
        txt = ''
        for loc in data:
            if loc:
                txt += '%s, %s\n' % (str(loc[0]), str(loc[1]))
        self.ui.locations_textb.setPlainText(txt)
        self.ui.locate_button.setDisabled(False)

    def on_textbox_clicked(self):
        # new cursor - select all document
        cursor = self.ui.locations_textb.textCursor()
        cursor.select(QtGui.QTextCursor.Document)

        # clear previous selection highlight
        tmp = cursor.blockFormat()
        tmp.clearBackground()
        cursor.setBlockFormat(tmp)

        # new cursor - select the current line
        cursor = self.ui.locations_textb.textCursor()
        cursor.select(QtGui.QTextCursor.LineUnderCursor)

        # highlight the current selected line
        tmp = cursor.blockFormat()
        tmp.setBackground(QtGui.QBrush(QtCore.Qt.yellow))
        cursor.setBlockFormat(tmp)

        self.selected_text = cursor.selectedText()

    def on_update_sec_distances_txt(self, data):
        distance_list = sorted(list(data.keys()))
        txt = ''
        for loc in distance_list:
            txt += '%s\n' % str(loc)
        self.ui.distances_textb.setPlainText(txt)
        self.ui.locate_sec_button.setDisabled(False)

    def on_distances_textb_clicked(self):
        # new cursor - select all document
        cursor = self.ui.distances_textb.textCursor()
        cursor.select(QtGui.QTextCursor.Document)

        # clear previous selection highlight
        tmp = cursor.blockFormat()
        tmp.clearBackground()
        cursor.setBlockFormat(tmp)

        # new cursor - select the current line
        cursor = self.ui.distances_textb.textCursor()
        cursor.select(QtGui.QTextCursor.LineUnderCursor)

        # highlight the current selected line
        tmp = cursor.blockFormat()
        tmp.setBackground(QtGui.QBrush(QtCore.Qt.yellow))
        cursor.setBlockFormat(tmp)

        distance_text = cursor.selectedText()
        key_in_min_dict = eval(distance_text)
        self.on_update_locations_text(dist=key_in_min_dict)

    def on_update_locations_text(self, dist):
        distance_list = self.min_dict[dist]
        txt = ''
        for loc in distance_list:
            if loc:
                txt += '%s, %s\n' % (str(loc[0]), str(loc[1]))
        self.ui.locations_sec_textb.setPlainText(txt)

    def on_locations_sec_clicked(self):
        # new cursor - select all document
        cursor = self.ui.locations_sec_textb.textCursor()
        cursor.select(QtGui.QTextCursor.Document)

        # clear previous selection highlight
        tmp = cursor.blockFormat()
        tmp.clearBackground()
        cursor.setBlockFormat(tmp)

        # new cursor - select the current line
        cursor = self.ui.locations_sec_textb.textCursor()
        cursor.select(QtGui.QTextCursor.LineUnderCursor)

        # highlight the current selected line
        tmp = cursor.blockFormat()
        tmp.setBackground(QtGui.QBrush(QtCore.Qt.yellow))
        cursor.setBlockFormat(tmp)

        self.selected_locations_text = cursor.selectedText()

    def on_locate_sec_position(self):
        try:
            if self.selected_locations_text != '':
                loc = eval(self.selected_locations_text)
            else:
                return
        except Exception as e:
            log.debug("ToolOptimal.on_locate_sec_position() --> first try %s" % str(e))
            self.app.inform.emit("[ERROR_NOTCL] The selected text is no valid location in the format "
                                 "((x0, y0), (x1, y1)).")
            return

        try:
            loc_1 = loc[0]
            loc_2 = loc[1]
            dx = loc_1[0] - loc_2[0]
            dy = loc_1[1] - loc_2[1]
            loc = (float('%.*f' % (self.decimals, (min(loc_1[0], loc_2[0]) + (abs(dx) / 2)))),
                   float('%.*f' % (self.decimals, (min(loc_1[1], loc_2[1]) + (abs(dy) / 2)))))
            self.app.on_jump_to(custom_location=loc)
        except Exception as e:
            log.debug("ToolOptimal.on_locate_sec_position() --> sec try %s" % str(e))
            return

    def reset_fields(self):
        self.ui.gerber_object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.ui.gerber_object_combo.setCurrentIndex(0)


class OptimalUI:

    toolName = _("Optimal Tool")

    def __init__(self, layout, app):
        self.app = app
        self.decimals = self.app.decimals
        self.layout = layout
        self.units = self.app.defaults['units'].upper()

        # ## Title
        title_label = FCLabel("%s" % self.toolName)
        title_label.setStyleSheet("""
                                QLabel
                                {
                                    font-size: 16px;
                                    font-weight: bold;
                                }
                                """)
        self.layout.addWidget(title_label)
        self.layout.addWidget(FCLabel(""))

        # ## Form Layout
        form_lay = QtWidgets.QFormLayout()
        self.layout.addLayout(form_lay)

        # ## Gerber Object to mirror
        self.gerber_object_combo = FCComboBox()
        self.gerber_object_combo.setModel(self.app.collection)
        self.gerber_object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.gerber_object_combo.is_last = True
        self.gerber_object_combo.obj_type = "Gerber"

        self.gerber_object_label = FCLabel("<b>%s:</b>" % _("GERBER"))
        self.gerber_object_label.setToolTip(
            "Gerber object for which to find the minimum distance between copper features."
        )
        form_lay.addRow(self.gerber_object_label)
        form_lay.addRow(self.gerber_object_combo)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        form_lay.addRow(separator_line)

        # Precision = nr of decimals
        self.precision_label = FCLabel('%s:' % _("Precision"))
        self.precision_label.setToolTip(_("Number of decimals kept for found distances."))

        self.precision_spinner = FCSpinner(callback=self.confirmation_message_int)
        self.precision_spinner.set_range(2, 10)
        self.precision_spinner.setWrapping(True)
        form_lay.addRow(self.precision_label, self.precision_spinner)

        # Results Title
        self.title_res_label = FCLabel('<b>%s:</b>' % _("Minimum distance"))
        self.title_res_label.setToolTip(_("Display minimum distance between copper features."))
        form_lay.addRow(self.title_res_label)

        # Result value
        self.result_label = FCLabel('%s:' % _("Determined"))
        self.result_entry = FCEntry()
        self.result_entry.setReadOnly(True)

        self.units_lbl = FCLabel(self.units.lower())
        self.units_lbl.setDisabled(True)

        hlay = QtWidgets.QHBoxLayout()
        hlay.addWidget(self.result_entry)
        hlay.addWidget(self.units_lbl)

        form_lay.addRow(self.result_label, hlay)

        # Frequency of minimum encounter
        self.freq_label = FCLabel('%s:' % _("Occurring"))
        self.freq_label.setToolTip(_("How many times this minimum is found."))
        self.freq_entry = FCEntry()
        self.freq_entry.setReadOnly(True)
        form_lay.addRow(self.freq_label, self.freq_entry)

        # Control if to display the locations of where the minimum was found
        self.locations_cb = FCCheckBox(_("Minimum points coordinates"))
        self.locations_cb.setToolTip(_("Coordinates for points where minimum distance was found."))
        form_lay.addRow(self.locations_cb)

        # Locations where minimum was found
        self.locations_textb = FCTextArea()
        self.locations_textb.setPlaceholderText(
            _("Coordinates for points where minimum distance was found.")
        )
        self.locations_textb.setReadOnly(True)
        stylesheet = """
                                QTextEdit { selection-background-color:blue;
                                            selection-color:white;
                                }
                             """

        self.locations_textb.setStyleSheet(stylesheet)
        form_lay.addRow(self.locations_textb)

        # Jump button
        self.locate_button = FCButton(_("Jump to selected position"))
        self.locate_button.setToolTip(
            _("Select a position in the Locations text box and then\n"
              "click this button.")
        )
        self.locate_button.setMinimumWidth(60)
        self.locate_button.setDisabled(True)
        form_lay.addRow(self.locate_button)

        # Other distances in Gerber
        self.title_second_res_label = FCLabel('<b>%s:</b>' % _("Other distances"))
        self.title_second_res_label.setToolTip(_("Will display other distances in the Gerber file ordered from\n"
                                                 "the minimum to the maximum, not including the absolute minimum."))
        form_lay.addRow(self.title_second_res_label)

        # Control if to display the locations of where the minimum was found
        self.sec_locations_cb = FCCheckBox(_("Other distances points coordinates"))
        self.sec_locations_cb.setToolTip(_("Other distances and the coordinates for points\n"
                                           "where the distance was found."))
        form_lay.addRow(self.sec_locations_cb)

        # this way I can hide/show the frame
        self.sec_locations_frame = QtWidgets.QFrame()
        self.sec_locations_frame.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.sec_locations_frame)
        self.distances_box = QtWidgets.QVBoxLayout()
        self.distances_box.setContentsMargins(0, 0, 0, 0)
        self.sec_locations_frame.setLayout(self.distances_box)

        # Other Distances label
        self.distances_label = FCLabel('%s' % _("Gerber distances"))
        self.distances_label.setToolTip(_("Other distances and the coordinates for points\n"
                                          "where the distance was found."))
        self.distances_box.addWidget(self.distances_label)

        # Other distances
        self.distances_textb = FCTextArea()
        self.distances_textb.setPlaceholderText(
            _("Other distances and the coordinates for points\n"
              "where the distance was found.")
        )
        self.distances_textb.setReadOnly(True)
        stylesheet = """
                                QTextEdit { selection-background-color:blue;
                                            selection-color:white;
                                }
                             """

        self.distances_textb.setStyleSheet(stylesheet)
        self.distances_box.addWidget(self.distances_textb)

        self.distances_box.addWidget(FCLabel(''))

        # Other Locations label
        self.locations_label = FCLabel('%s' % _("Points coordinates"))
        self.locations_label.setToolTip(_("Other distances and the coordinates for points\n"
                                          "where the distance was found."))
        self.distances_box.addWidget(self.locations_label)

        # Locations where minimum was found
        self.locations_sec_textb = FCTextArea()
        self.locations_sec_textb.setPlaceholderText(
            _("Other distances and the coordinates for points\n"
              "where the distance was found.")
        )
        self.locations_sec_textb.setReadOnly(True)
        stylesheet = """
                                QTextEdit { selection-background-color:blue;
                                            selection-color:white;
                                }
                             """

        self.locations_sec_textb.setStyleSheet(stylesheet)
        self.distances_box.addWidget(self.locations_sec_textb)

        # Jump button
        self.locate_sec_button = FCButton(_("Jump to selected position"))
        self.locate_sec_button.setToolTip(
            _("Select a position in the Locations text box and then\n"
              "click this button.")
        )
        self.locate_sec_button.setMinimumWidth(60)
        self.locate_sec_button.setDisabled(True)
        self.distances_box.addWidget(self.locate_sec_button)

        # GO button
        self.calculate_button = FCButton(_("Find Minimum"))
        self.calculate_button.setIcon(QtGui.QIcon(self.app.resource_location + '/open_excellon32.png'))
        self.calculate_button.setToolTip(
            _("Calculate the minimum distance between copper features,\n"
              "this will allow the determination of the right tool to\n"
              "use for isolation or copper clearing.")
        )
        self.calculate_button.setStyleSheet("""
                                QPushButton
                                {
                                    font-weight: bold;
                                }
                                """)
        self.calculate_button.setMinimumWidth(60)
        self.layout.addWidget(self.calculate_button)

        self.layout.addStretch()

        # ## Reset Tool
        self.reset_button = FCButton(_("Reset Tool"))
        self.reset_button.setIcon(QtGui.QIcon(self.app.resource_location + '/reset32.png'))
        self.reset_button.setToolTip(
            _("Will reset the tool parameters.")
        )
        self.reset_button.setStyleSheet("""
                                QPushButton
                                {
                                    font-weight: bold;
                                }
                                """)
        self.layout.addWidget(self.reset_button)

        self.loc_ois = OptionalHideInputSection(self.locations_cb, [self.locations_textb, self.locate_button])
        self.sec_loc_ois = OptionalHideInputSection(self.sec_locations_cb, [self.sec_locations_frame])

        # #################################### FINSIHED GUI ###########################
        # #############################################################################

    def confirmation_message(self, accepted, minval, maxval):
        if accepted is False:
            self.app.inform[str, bool].emit('[WARNING_NOTCL] %s: [%.*f, %.*f]' % (_("Edited value is out of range"),
                                                                                  self.decimals,
                                                                                  minval,
                                                                                  self.decimals,
                                                                                  maxval), False)
        else:
            self.app.inform[str, bool].emit('[success] %s' % _("Edited value is within limits."), False)

    def confirmation_message_int(self, accepted, minval, maxval):
        if accepted is False:
            self.app.inform[str, bool].emit('[WARNING_NOTCL] %s: [%d, %d]' %
                                            (_("Edited value is out of range"), minval, maxval), False)
        else:
            self.app.inform[str, bool].emit('[success] %s' % _("Edited value is within limits."), False)
