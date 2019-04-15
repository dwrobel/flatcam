############################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 4/15/2019                                          #
# MIT Licence                                              #
############################################################

from FlatCAMTool import FlatCAMTool

from flatcamGUI.GUIElements import RadioSet, FCComboBox, FCSpinner, FCButton, FCTable
from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtCore import pyqtSignal
import re
import os

import gettext
import FlatCAMTranslation as fcTranslate

fcTranslate.apply_language('strings')
import builtins
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class PcbWizard(FlatCAMTool):

    file_loaded = pyqtSignal(str, str)

    toolName = _("PcbWizard Import Tool")

    def __init__(self, app):
        FlatCAMTool.__init__(self, app)

        self.app = app

        # Title
        title_label = QtWidgets.QLabel("%s" % _('Import 2-file Excellon'))
        title_label.setStyleSheet("""
                        QLabel
                        {
                            font-size: 16px;
                            font-weight: bold;
                        }
                        """)
        self.layout.addWidget(title_label)

        self.layout.addWidget(QtWidgets.QLabel(""))
        self.layout.addWidget(QtWidgets.QLabel("<b>Load files:</b>"))

        # Form Layout
        form_layout = QtWidgets.QFormLayout()
        self.layout.addLayout(form_layout)

        self.excellon_label = QtWidgets.QLabel(_("Excellon file:"))
        self.excellon_label.setToolTip(
           _( "Load the Excellon file.\n"
              "Usually it has a .DRL extension")

        )
        self.excellon_brn = FCButton(_("Open"))
        form_layout.addRow(self.excellon_label, self.excellon_brn)

        self.inf_label = QtWidgets.QLabel(_("INF file:"))
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

        self.layout.addWidget(QtWidgets.QLabel(""))
        self.layout.addWidget(QtWidgets.QLabel("<b>Excellon format:</b>"))
        # Form Layout
        form_layout1 = QtWidgets.QFormLayout()
        self.layout.addLayout(form_layout1)

        # Integral part of the coordinates
        self.int_entry = FCSpinner()
        self.int_entry.set_range(1, 10)
        self.int_label = QtWidgets.QLabel(_("Int. digits:"))
        self.int_label.setToolTip(
           _( "The number of digits for the integral part of the coordinates.")
        )
        form_layout1.addRow(self.int_label, self.int_entry)

        # Fractional part of the coordinates
        self.frac_entry = FCSpinner()
        self.frac_entry.set_range(1, 10)
        self.frac_label = QtWidgets.QLabel(_("Frac. digits:"))
        self.frac_label.setToolTip(
            _("The number of digits for the fractional part of the coordinates.")
        )
        form_layout1.addRow(self.frac_label, self.frac_entry)

        # Zeros suppression for coordinates
        self.zeros_radio = RadioSet([{'label': 'LZ', 'value': 'L'},
                                     {'label': 'TZ', 'value': 'T'},
                                     {'label': 'No Suppression', 'value': 'D'}])
        self.zeros_label = QtWidgets.QLabel(_("Zeros supp.:"))
        self.zeros_label.setToolTip(
            _("The type of zeros suppression used.\n"
              "Can be of type:\n"
              "- LZ = leading zeros are kept\n"
              "- TZ = trailing zeros are kept\n"
              "- No Suppression = no zero suppression")
        )
        form_layout1.addRow(self.zeros_label, self.zeros_radio)

        # Units type
        self.units_radio = RadioSet([{'label': 'INCH', 'value': 'INCH'},
                                    {'label': 'MM', 'value': 'METRIC'}])
        self.units_label = QtWidgets.QLabel("<b>%s:</b>" % _('Units'))
        self.units_label.setToolTip(
            _("The type of units that the coordinates and tool\n"
              "diameters are using. Can be INCH or MM.")
        )
        form_layout1.addRow(self.units_label, self.units_radio)

        # Buttons

        self.import_button = QtWidgets.QPushButton(_("Import Excellon"))
        self.import_button.setToolTip(
            _("Import in FlatCAM an Excellon file\n"
              "that store it's information's in 2 files.\n"
              "One usually has .DRL extension while\n"
              "the other has .INF extension.")
        )
        self.layout.addWidget(self.import_button)

        self.layout.addStretch()

        self.excellon_loaded = False
        self.inf_loaded = False
        self.process_finished = False

        ## Signals
        self.excellon_brn.clicked.connect(self.on_load_excellon_click)
        self.inf_btn.clicked.connect(self.on_load_inf_click)
        self.import_button.clicked.connect(self.on_import_excellon)
        self.file_loaded.connect(self.on_file_loaded)
        self.units_radio.activated_custom.connect(self.on_units_change)

        self.units = 'INCH'
        self.zeros = 'L'
        self.integral = 2
        self.fractional = 4

        self.outname = 'file'

        self.exc_file_content = None
        self.tools_from_inf = {}

    def run(self, toggle=False):
        self.app.report_usage("PcbWizard Tool()")

        if toggle:
            # if the splitter is hidden, display it, else hide it but only if the current widget is the same
            if self.app.ui.splitter.sizes()[0] == 0:
                self.app.ui.splitter.setSizes([1, 1])
            else:
                try:
                    if self.app.ui.tool_scroll_area.widget().objectName() == self.toolName:
                        self.app.ui.splitter.setSizes([0, 1])
                except AttributeError:
                    pass
        else:
            if self.app.ui.splitter.sizes()[0] == 0:
                self.app.ui.splitter.setSizes([1, 1])

        FlatCAMTool.run(self)
        self.set_tool_ui()

        self.app.ui.notebook.setTabText(2, _("PCBWizard Tool"))

    def install(self, icon=None, separator=None, **kwargs):
        FlatCAMTool.install(self, icon, separator, **kwargs)

    def set_tool_ui(self):
        ## Initialize form
        self.int_entry.set_value(self.integral)
        self.frac_entry.set_value(self.fractional)
        self.zeros_radio.set_value(self.zeros)
        self.units_radio.set_value(self.units)

        self.excellon_loaded = False
        self.inf_loaded = False
        self.process_finished = False

        self.build_ui()

    def build_ui(self):
        sorted_tools = []

        if not self.tools_from_inf:
            self.tools_table.setRowCount(1)
        else:
            sort = []
            for k, v in list(self.tools_from_inf.items()):
                sort.append(int(k))
            sorted_tools = sorted(sort)
            n = len(sorted_tools)
            self.tools_table.setRowCount(n)

        tool_row = 0
        for tool in sorted_tools:
            tool_id_item = QtWidgets.QTableWidgetItem('%d' % int(tool))
            tool_id_item.setFlags(QtCore.Qt.ItemIsEnabled)
            self.tools_table.setItem(tool_row, 0, tool_id_item)  # Tool name/id

            tool_dia_item = QtWidgets.QTableWidgetItem(str(self.tools_from_inf[tool]))
            tool_dia_item.setFlags(QtCore.Qt.ItemIsEnabled)
            self.tools_table.setItem(tool_row, 1, tool_dia_item)
            tool_row += 1

        self.tools_table.resizeColumnsToContents()
        self.tools_table.resizeRowsToContents()

        vertical_header = self.tools_table.verticalHeader()
        vertical_header.hide()
        self.tools_table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        horizontal_header = self.tools_table.horizontalHeader()
        # horizontal_header.setMinimumSectionSize(10)
        # horizontal_header.setDefaultSectionSize(70)
        horizontal_header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        horizontal_header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)

        self.tools_table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.tools_table.setSortingEnabled(False)
        self.tools_table.setMinimumHeight(self.tools_table.getHeight())
        self.tools_table.setMaximumHeight(self.tools_table.getHeight())

    def update_params(self):
        self.units = self.units_radio.get_value()
        self.zeros = self.zeros_radio.get_value()
        self.integral = self.int_entry.get_value()
        self.fractional = self.frac_entry.get_value()

    def on_units_change(self, val):
        if val == 'INCH':
            self.int_entry.set_value(2)
            self.frac_entry.set_value(4)
        else:
            self.int_entry.set_value(3)
            self.frac_entry.set_value(3)

    def on_load_excellon_click(self):
        """

        :return: None
        """
        self.app.log.debug("on_load_excellon_click()")

        filter = "Excellon Files(*.DRL *.DRD *.TXT);;All Files (*.*)"
        try:
            filename, _f = QtWidgets.QFileDialog.getOpenFileName(caption=_("Load PcbWizard Excellon file"),
                                                                 directory=self.app.get_last_folder(),
                                                                 filter=filter)
        except TypeError:
            filename, _f = QtWidgets.QFileDialog.getOpenFileName(caption=_("Load PcbWizard Excellon file"),
                                                                 filter=filter)

        filename = str(filename)


        if filename == "":
            self.app.inform.emit(_("Open cancelled."))
        else:
            self.app.worker_task.emit({'fcn': self.load_excellon,
                                       'params': [self, filename]})

    def on_load_inf_click(self):
        """

                :return: None
                """
        self.app.log.debug("on_load_inf_click()")

        filter = "INF Files(*.INF);;All Files (*.*)"
        try:
            filename, _f = QtWidgets.QFileDialog.getOpenFileName(caption=_("Load PcbWizard INF file"),
                                                                 directory=self.app.get_last_folder(),
                                                                 filter=filter)
        except TypeError:
            filename, _f = QtWidgets.QFileDialog.getOpenFileName(caption=_("Load PcbWizard INF file"),
                                                                 filter=filter)

        filename = str(filename)

        if filename == "":
            self.app.inform.emit(_("Open cancelled."))
        else:
            self.app.worker_task.emit({'fcn': self.load_inf, 'params': [filename]})

    def load_inf(self, filename):
        self.app.log.debug("ToolPcbWizard.load_inf()")

        with open(filename, 'r') as inf_f:
            inf_file_content = inf_f.readlines()

        tool_re = re.compile(r'^T(\d+)\s+(\d*\.?\d+)$')

        for eline in inf_file_content:
            # Cleanup lines
            eline = eline.strip(' \r\n')

            match = tool_re.search(eline)
            if match:
                tool =int( match.group(1))
                dia = float(match.group(2))
                if dia < 0.1:
                    # most likely the file is in INCH
                    self.units_radio.set_value('INCH')

                self.tools_from_inf[tool] = dia

        if not self.tools_from_inf:
            self.app.inform.emit(_("[ERROR] The INF file does not contain the tool table.\n"
                                   "Try to open the Excellon file from File -> Open -> Excellon\n"
                                   "and edit the drill diameters manually."))
            return "fail"

        self.tools_table.setVisible(True)
        self.file_loaded.emit('inf', filename)

    def load_excellon(self, filename):
        with open(filename, 'r') as exc_f:
            self.exc_file_content = exc_f.readlines()

        self.file_loaded.emit("excellon", filename)

    def on_file_loaded(self, signal, filename):
        self.build_ui()

        if signal == 'inf':
            self.inf_loaded = True
        elif signal == 'excellon':
            self.excellon_loaded = True

        if self.excellon_loaded and self.inf_loaded:
            pass


        # Register recent file
        self.app.defaults["global_last_folder"] = os.path.split(str(filename))[0]

    def on_import_excellon(self, signal, excellon_fileobj):
        self.app.log.debug("import_2files_excellon()")

        # How the object should be initialized
        def obj_init(excellon_obj, app_obj):
            # self.progress.emit(20)

            try:
                ret = excellon_obj.parse_file(file_obj=excellon_fileobj)
                if ret == "fail":
                    app_obj.log.debug("Excellon parsing failed.")
                    app_obj.inform.emit(_("[ERROR_NOTCL] This is not Excellon file."))
                    return "fail"
            except IOError:
                app_obj.inform.emit(_("[ERROR_NOTCL] Cannot parse file: %s") % self.outname)
                app_obj.log.debug("Could not import Excellon object.")
                app_obj.progress.emit(0)
                return "fail"
            except:
                msg = _("[ERROR_NOTCL] An internal error has occurred. See shell.\n")
                msg += app_obj.traceback.format_exc()
                app_obj.inform.emit(msg)
                return "fail"

            ret = excellon_obj.create_geometry()
            if ret == 'fail':
                app_obj.log.debug("Could not create geometry for Excellon object.")
                return "fail"
            app_obj.progress.emit(100)
            for tool in excellon_obj.tools:
                if excellon_obj.tools[tool]['solid_geometry']:
                    return
            app_obj.inform.emit(_("[ERROR_NOTCL] No geometry found in file: %s") % name)
            return "fail"

        if self.process_finished:
            with self.app.proc_container.new(_("Importing Excellon.")):

                # Object name
                name = self.outname

                ret = self.app.new_object("excellon", name, obj_init, autoselected=False)
                if ret == 'fail':
                    self.app.inform.emit(_('[ERROR_NOTCL] Import Excellon file failed.'))
                    return

                    # Register recent file
                self.app.file_opened.emit("excellon", name)

                # GUI feedback
                self.app.inform.emit(_("[success] Opened: %s") % name)
        else:
            self.app.inform.emit(_('[WARNING_NOTCL] Excellon merging is in progress. Please wait...'))

