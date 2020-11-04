# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 4/15/2019                                          #
# MIT Licence                                              #
# ##########################################################

from PyQt5 import QtWidgets, QtCore

from appTool import AppTool
from appGUI.GUIElements import RadioSet, FCSpinner, FCButton, FCTable, FCLabel

import re
import os
from datetime import datetime
from io import StringIO

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class PcbWizard(AppTool):

    file_loaded = QtCore.pyqtSignal(str, str)

    def __init__(self, app):
        AppTool.__init__(self, app)

        self.app = app
        self.decimals = self.app.decimals

        # #############################################################################
        # ######################### Tool GUI ##########################################
        # #############################################################################
        self.ui = WizardUI(layout=self.layout, app=self.app)
        self.toolName = self.ui.toolName

        self.excellon_loaded = False
        self.inf_loaded = False
        self.process_finished = False

        self.modified_excellon_file = ''

        # ## Signals
        self.ui.excellon_brn.clicked.connect(self.on_load_excellon_click)
        self.ui.inf_btn.clicked.connect(self.on_load_inf_click)
        self.ui.import_button.clicked.connect(lambda: self.on_import_excellon(
            excellon_fileobj=self.modified_excellon_file))

        self.file_loaded.connect(self.on_file_loaded)
        self.ui.units_radio.activated_custom.connect(self.ui.on_units_change)

        self.units = 'INCH'
        self.zeros = 'LZ'
        self.integral = 2
        self.fractional = 4

        self.outname = 'file'

        self.exc_file_content = None
        self.tools_from_inf = {}

    def run(self, toggle=False):
        self.app.defaults.report_usage("PcbWizard Tool()")

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

        self.app.ui.notebook.setTabText(2, _("PCBWizard Tool"))

    def install(self, icon=None, separator=None, **kwargs):
        AppTool.install(self, icon, separator, **kwargs)

    def set_tool_ui(self):
        self.units = 'INCH'
        self.zeros = 'LZ'
        self.integral = 2
        self.fractional = 4

        self.outname = 'file'

        self.exc_file_content = None
        self.tools_from_inf = {}

        # ## Initialize form
        self.ui.int_entry.set_value(self.integral)
        self.ui.frac_entry.set_value(self.fractional)
        self.ui.zeros_radio.set_value(self.zeros)
        self.ui.units_radio.set_value(self.units)

        self.excellon_loaded = False
        self.inf_loaded = False
        self.process_finished = False
        self.modified_excellon_file = ''

        self.build_ui()

    def build_ui(self):
        sorted_tools = []

        if not self.tools_from_inf:
            self.ui.tools_table.setVisible(False)
        else:
            sort = []
            for k, v in list(self.tools_from_inf.items()):
                sort.append(int(k))
            sorted_tools = sorted(sort)
            n = len(sorted_tools)
            self.ui.tools_table.setRowCount(n)

        tool_row = 0
        for tool in sorted_tools:
            tool_id_item = QtWidgets.QTableWidgetItem('%d' % int(tool))
            tool_id_item.setFlags(QtCore.Qt.ItemIsEnabled)
            self.ui.tools_table.setItem(tool_row, 0, tool_id_item)  # Tool name/id

            tool_dia_item = QtWidgets.QTableWidgetItem(str(self.tools_from_inf[tool]))
            tool_dia_item.setFlags(QtCore.Qt.ItemIsEnabled)
            self.ui.tools_table.setItem(tool_row, 1, tool_dia_item)
            tool_row += 1

        self.ui.tools_table.resizeColumnsToContents()
        self.ui.tools_table.resizeRowsToContents()

        vertical_header = self.ui.tools_table.verticalHeader()
        vertical_header.hide()
        self.ui.tools_table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        horizontal_header = self.ui.tools_table.horizontalHeader()
        # horizontal_header.setMinimumSectionSize(10)
        # horizontal_header.setDefaultSectionSize(70)
        horizontal_header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        horizontal_header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)

        self.ui.tools_table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.ui.tools_table.setSortingEnabled(False)
        self.ui.tools_table.setMinimumHeight(self.ui.tools_table.getHeight())
        self.ui.tools_table.setMaximumHeight(self.ui.tools_table.getHeight())

    def update_params(self):
        self.units = self.ui.units_radio.get_value()
        self.zeros = self.ui.zeros_radio.get_value()
        self.integral = self.ui.int_entry.get_value()
        self.fractional = self.ui.frac_entry.get_value()

    def on_load_excellon_click(self):
        """

        :return: None
        """
        self.app.log.debug("on_load_excellon_click()")

        _filter = "Excellon Files(*.DRL *.DRD *.TXT);;All Files (*.*)"
        try:
            filename, _f = QtWidgets.QFileDialog.getOpenFileName(caption=_("Load PcbWizard Excellon file"),
                                                                 directory=self.app.get_last_folder(),
                                                                 filter=_filter)
        except TypeError:
            filename, _f = QtWidgets.QFileDialog.getOpenFileName(caption=_("Load PcbWizard Excellon file"),
                                                                 filter=_filter)

        filename = str(filename)

        if filename == "":
            self.app.inform.emit(_("Cancelled."))
        else:
            self.app.worker_task.emit({'fcn': self.load_excellon, 'params': [filename]})

    def on_load_inf_click(self):
        """

                :return: None
                """
        self.app.log.debug("on_load_inf_click()")

        _filter = "INF Files(*.INF);;All Files (*.*)"
        try:
            filename, _f = QtWidgets.QFileDialog.getOpenFileName(caption=_("Load PcbWizard INF file"),
                                                                 directory=self.app.get_last_folder(),
                                                                 filter=_filter)
        except TypeError:
            filename, _f = QtWidgets.QFileDialog.getOpenFileName(caption=_("Load PcbWizard INF file"),
                                                                 filter=_filter)

        filename = str(filename)

        if filename == "":
            self.app.inform.emit(_("Cancelled."))
        else:
            self.app.worker_task.emit({'fcn': self.load_inf, 'params': [filename]})

    def load_inf(self, filename):
        self.app.log.debug("ToolPcbWizard.load_inf()")

        with open(filename, 'r') as inf_f:
            inf_file_content = inf_f.readlines()

        tool_re = re.compile(r'^T(\d+)\s+(\d*\.?\d+)$')
        format_re = re.compile(r'^(\d+)\.?(\d+)\s*format,\s*(inches|metric)?,\s*(absolute|incremental)?.*$')

        for eline in inf_file_content:
            # Cleanup lines
            eline = eline.strip(' \r\n')

            match = tool_re.search(eline)
            if match:
                tool = int(match.group(1))
                dia = float(match.group(2))
                # if dia < 0.1:
                #     # most likely the file is in INCH
                #     self.units_radio.set_value('INCH')

                self.tools_from_inf[tool] = dia
                continue
            match = format_re.search(eline)
            if match:
                self.integral = int(match.group(1))
                self.fractional = int(match.group(2))
                units = match.group(3)
                if units == 'inches':
                    self.units = 'INCH'
                else:
                    self.units = 'METRIC'
                self.ui.units_radio.set_value(self.units)
                self.ui.int_entry.set_value(self.integral)
                self.ui.frac_entry.set_value(self.fractional)

        if not self.tools_from_inf:
            self.app.inform.emit('[ERROR] %s' %
                                 _("The INF file does not contain the tool table.\n"
                                   "Try to open the Excellon file from File -> Open -> Excellon\n"
                                   "and edit the drill diameters manually."))
            return "fail"

        self.file_loaded.emit('inf', filename)

    def load_excellon(self, filename):
        with open(filename, 'r') as exc_f:
            self.exc_file_content = exc_f.readlines()

        self.file_loaded.emit("excellon", filename)

    def on_file_loaded(self, signal, filename):
        self.build_ui()
        time_str = "{:%A, %d %B %Y at %H:%M}".format(datetime.now())

        if signal == 'inf':
            self.inf_loaded = True
            self.ui.tools_table.setVisible(True)
            self.app.inform.emit('[success] %s' % _("PcbWizard .INF file loaded."))
        elif signal == 'excellon':
            self.excellon_loaded = True
            self.outname = os.path.split(str(filename))[1]
            self.app.inform.emit('[success] %s' % _("Main PcbWizard Excellon file loaded."))

        if self.excellon_loaded and self.inf_loaded:
            self.update_params()
            excellon_string = ''
            for line in self.exc_file_content:
                excellon_string += line
                if 'M48' in line:
                    header = ';EXCELLON RE-GENERATED BY FLATCAM v%s - www.flatcam.org - Version Date: %s\n' % \
                              (str(self.app.version), str(self.app.version_date))
                    header += ';Created on : %s' % time_str + '\n'
                    header += ';FILE_FORMAT={integral}:{fractional}\n'.format(integral=self.integral,
                                                                              fractional=self.fractional)
                    header += '{units},{zeros}\n'.format(units=self.units, zeros=self.zeros)
                    for k, v in self.tools_from_inf.items():
                        header += 'T{tool}C{dia}\n'.format(tool=int(k), dia=float(v))
                    excellon_string += header
            self.modified_excellon_file = StringIO(excellon_string)
            self.process_finished = True

        # Register recent file
        self.app.defaults["global_last_folder"] = os.path.split(str(filename))[0]

    def on_import_excellon(self, signal=None, excellon_fileobj=None):
        self.app.log.debug("import_2files_excellon()")

        # How the object should be initialized
        def obj_init(excellon_obj, app_obj):
            try:
                ret = excellon_obj.parse_file(file_obj=excellon_fileobj)
                if ret == "fail":
                    app_obj.log.debug("Excellon parsing failed.")
                    app_obj.inform.emit('[ERROR_NOTCL] %s' % _("This is not Excellon file."))
                    return "fail"
            except IOError:
                app_obj.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Cannot parse file"), self.outname))
                app_obj.log.debug("Could not import Excellon object.")
                return "fail"
            except Exception as e:
                app_obj.log.debug("PcbWizard.on_import_excellon().obj_init() %s" % str(e))
                msg = '[ERROR_NOTCL] %s' % _("An internal error has occurred. See shell.\n")
                msg += app_obj.traceback.format_exc()
                app_obj.inform.emit(msg)
                return "fail"

            ret = excellon_obj.create_geometry()
            if ret == 'fail':
                app_obj.log.debug("Could not create geometry for Excellon object.")
                return "fail"

            for tool in excellon_obj.tools:
                if excellon_obj.tools[tool]['solid_geometry']:
                    return
            app_obj.inform.emit('[ERROR_NOTCL] %s: %s' % (_("No geometry found in file"), name))
            return "fail"

        if excellon_fileobj is not None and excellon_fileobj != '':
            if self.process_finished:
                with self.app.proc_container.new('%s ...' % _("Importing")):

                    # Object name
                    name = self.outname

                    ret_val = self.app.app_obj.new_object("excellon", name, obj_init, autoselected=False)
                    if ret_val == 'fail':
                        self.app.inform.emit('[ERROR_NOTCL] %s' % _('Import Excellon file failed.'))
                        return

                        # Register recent file
                    self.app.file_opened.emit("excellon", name)

                    # GUI feedback
                    self.app.inform.emit('[success] %s: %s' % (_("Imported"), name))
                    self.app.ui.notebook.setCurrentWidget(self.app.ui.project_tab)
            else:
                self.app.inform.emit('[WARNING_NOTCL] %s' % _('Excellon merging is in progress. Please wait...'))
        else:
            self.app.inform.emit('[ERROR_NOTCL] %s' % _('The imported Excellon file is empty.'))


class WizardUI:
    
    toolName = _("PcbWizard Import Tool")

    def __init__(self, layout, app):
        self.app = app
        self.decimals = self.app.decimals
        self.layout = layout

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

        self.layout.addWidget(FCLabel("<b>%s:</b>" % _("Load files")))

        # Form Layout
        form_layout = QtWidgets.QFormLayout()
        self.layout.addLayout(form_layout)

        self.excellon_label = FCLabel('%s:' % _("Excellon file"))
        self.excellon_label.setToolTip(
            _("Load the Excellon file.\n"
              "Usually it has a .DRL extension")
        )
        self.excellon_brn = FCButton(_("Open"))
        form_layout.addRow(self.excellon_label, self.excellon_brn)

        self.inf_label = FCLabel('%s:' % _("INF file"))
        self.inf_label.setToolTip(
            _("Load the INF file.")
        )
        self.inf_btn = FCButton(_("Open"))
        form_layout.addRow(self.inf_label, self.inf_btn)

        self.tools_table = FCTable()
        self.layout.addWidget(self.tools_table)

        self.tools_table.setColumnCount(2)
        self.tools_table.setHorizontalHeaderLabels(['#Tool', _('Diameter')])

        self.tools_table.horizontalHeaderItem(0).setToolTip(
            _("Tool Number"))
        self.tools_table.horizontalHeaderItem(1).setToolTip(
            _("Tool diameter in file units."))

        # start with apertures table hidden
        self.tools_table.setVisible(False)

        self.layout.addWidget(FCLabel(""))
        self.layout.addWidget(FCLabel("<b>%s:</b>" % _("Excellon Format")))
        # Form Layout
        form_layout1 = QtWidgets.QFormLayout()
        self.layout.addLayout(form_layout1)

        # Integral part of the coordinates
        self.int_entry = FCSpinner(callback=self.confirmation_message_int)
        self.int_entry.set_range(1, 10)
        self.int_label = FCLabel('%s:' % _("Int. digits"))
        self.int_label.setToolTip(
            _("The number of digits for the integral part of the coordinates.")
        )
        form_layout1.addRow(self.int_label, self.int_entry)

        # Fractional part of the coordinates
        self.frac_entry = FCSpinner(callback=self.confirmation_message_int)
        self.frac_entry.set_range(1, 10)
        self.frac_label = FCLabel('%s:' % _("Frac. digits"))
        self.frac_label.setToolTip(
            _("The number of digits for the fractional part of the coordinates.")
        )
        form_layout1.addRow(self.frac_label, self.frac_entry)

        # Zeros suppression for coordinates
        self.zeros_radio = RadioSet([{'label': _('LZ'), 'value': 'LZ'},
                                     {'label': _('TZ'), 'value': 'TZ'},
                                     {'label': _('No Suppression'), 'value': 'D'}])
        self.zeros_label = FCLabel('%s:' % _("Zeros supp."))
        self.zeros_label.setToolTip(
            _("The type of zeros suppression used.\n"
              "Can be of type:\n"
              "- LZ = leading zeros are kept\n"
              "- TZ = trailing zeros are kept\n"
              "- No Suppression = no zero suppression")
        )
        form_layout1.addRow(self.zeros_label, self.zeros_radio)

        # Units type
        self.units_radio = RadioSet([{'label': _('Inch'), 'value': 'INCH'},
                                     {'label': _('mm'), 'value': 'METRIC'}])
        self.units_label = FCLabel("<b>%s:</b>" % _('Units'))
        self.units_label.setToolTip(
            _("The type of units that the coordinates and tool\n"
              "diameters are using. Can be INCH or MM.")
        )
        form_layout1.addRow(self.units_label, self.units_radio)

        # Buttons

        self.import_button = QtWidgets.QPushButton(_("Import Excellon"))
        self.import_button.setToolTip(
            _("Import an Excellon file\n"
              "that store it's information's in 2 files.\n"
              "One usually has .DRL extension while\n"
              "the other has .INF extension.")
        )
        self.layout.addWidget(self.import_button)

        self.layout.addStretch()

        # #################################### FINSIHED GUI ###########################
        # #############################################################################

    def on_units_change(self, val):
        if val == 'INCH':
            self.int_entry.set_value(2)
            self.frac_entry.set_value(4)
        else:
            self.int_entry.set_value(3)
            self.frac_entry.set_value(3)
            
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
