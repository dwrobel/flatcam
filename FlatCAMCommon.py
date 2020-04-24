# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# Author: Juan Pablo Caram (c)                             #
# Date: 2/5/2014                                           #
# MIT Licence                                              #
# ##########################################################

# ##########################################################
# File Modified (major mod): Marius Adrian Stanciu         #
# Date: 11/4/2019                                          #
# ##########################################################

from PyQt5 import QtGui, QtCore, QtWidgets
from flatcamGUI.GUIElements import FCTable, FCEntry, FCButton, FCDoubleSpinner, FCComboBox, FCCheckBox, FCSpinner, \
    FCTree, RadioSet, FCFileSaveDialog
from camlib import to_dict

import sys
import webbrowser
import json

from copy import deepcopy
from datetime import datetime
import gettext
import FlatCAMTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class LoudDict(dict):
    """
    A Dictionary with a callback for
    item changes.
    """

    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self.callback = lambda x: None

    def __setitem__(self, key, value):
        """
        Overridden __setitem__ method. Will emit 'changed(QString)'
        if the item was changed, with key as parameter.
        """
        if key in self and self.__getitem__(key) == value:
            return

        dict.__setitem__(self, key, value)
        self.callback(key)

    def update(self, *args, **kwargs):
        if len(args) > 1:
            raise TypeError("update expected at most 1 arguments, got %d" % len(args))
        other = dict(*args, **kwargs)
        for key in other:
            self[key] = other[key]

    def set_change_callback(self, callback):
        """
        Assigns a function as callback on item change. The callback
        will receive the key of the object that was changed.

        :param callback: Function to call on item change.
        :type callback: func
        :return: None
        """

        self.callback = callback


class FCSignal:
    """
    Taken from here: https://blog.abstractfactory.io/dynamic-signals-in-pyqt/
    """

    def __init__(self):
        self.__subscribers = []

    def emit(self, *args, **kwargs):
        for subs in self.__subscribers:
            subs(*args, **kwargs)

    def connect(self, func):
        self.__subscribers.append(func)

    def disconnect(self, func):
        try:
            self.__subscribers.remove(func)
        except ValueError:
            print('Warning: function %s not removed '
                  'from signal %s' % (func, self))


class BookmarkManager(QtWidgets.QWidget):

    mark_rows = QtCore.pyqtSignal()

    def __init__(self, app, storage, parent=None):
        super(BookmarkManager, self).__init__(parent)

        self.app = app

        assert isinstance(storage, dict), "Storage argument is not a dictionary"

        self.bm_dict = deepcopy(storage)

        # Icon and title
        # self.setWindowIcon(parent.app_icon)
        # self.setWindowTitle(_("Bookmark Manager"))
        # self.resize(600, 400)

        # title = QtWidgets.QLabel(
        #     "<font size=8><B>FlatCAM</B></font><BR>"
        # )
        # title.setOpenExternalLinks(True)

        # layouts
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        table_hlay = QtWidgets.QHBoxLayout()
        layout.addLayout(table_hlay)

        self.table_widget = FCTable(drag_drop=True, protected_rows=[0, 1])
        self.table_widget.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        table_hlay.addWidget(self.table_widget)

        self.table_widget.setColumnCount(3)
        self.table_widget.setColumnWidth(0, 20)
        self.table_widget.setHorizontalHeaderLabels(
            [
                '#',
                _('Title'),
                _('Web Link')
            ]
        )
        self.table_widget.horizontalHeaderItem(0).setToolTip(
            _("Index.\n"
              "The rows in gray color will populate the Bookmarks menu.\n"
              "The number of gray colored rows is set in Preferences."))
        self.table_widget.horizontalHeaderItem(1).setToolTip(
            _("Description of the link that is set as an menu action.\n"
              "Try to keep it short because it is installed as a menu item."))
        self.table_widget.horizontalHeaderItem(2).setToolTip(
            _("Web Link. E.g: https://your_website.org "))

        # pal = QtGui.QPalette()
        # pal.setColor(QtGui.QPalette.Background, Qt.white)

        # New Bookmark
        new_vlay = QtWidgets.QVBoxLayout()
        layout.addLayout(new_vlay)

        new_title_lbl = QtWidgets.QLabel('<b>%s</b>' % _("New Bookmark"))
        new_vlay.addWidget(new_title_lbl)

        form0 = QtWidgets.QFormLayout()
        new_vlay.addLayout(form0)

        title_lbl = QtWidgets.QLabel('%s:' % _("Title"))
        self.title_entry = FCEntry()
        form0.addRow(title_lbl, self.title_entry)

        link_lbl = QtWidgets.QLabel('%s:' % _("Web Link"))
        self.link_entry = FCEntry()
        self.link_entry.set_value('http://')
        form0.addRow(link_lbl, self.link_entry)

        # Buttons Layout
        button_hlay = QtWidgets.QHBoxLayout()
        layout.addLayout(button_hlay)

        add_entry_btn = FCButton(_("Add Entry"))
        remove_entry_btn = FCButton(_("Remove Entry"))
        export_list_btn = FCButton(_("Export List"))
        import_list_btn = FCButton(_("Import List"))
        # closebtn = QtWidgets.QPushButton(_("Close"))

        # button_hlay.addStretch()
        button_hlay.addWidget(add_entry_btn)
        button_hlay.addWidget(remove_entry_btn)

        button_hlay.addWidget(export_list_btn)
        button_hlay.addWidget(import_list_btn)
        # button_hlay.addWidget(closebtn)
        # ##############################################################################
        # ######################## SIGNALS #############################################
        # ##############################################################################

        add_entry_btn.clicked.connect(self.on_add_entry)
        remove_entry_btn.clicked.connect(self.on_remove_entry)
        export_list_btn.clicked.connect(self.on_export_bookmarks)
        import_list_btn.clicked.connect(self.on_import_bookmarks)
        self.title_entry.returnPressed.connect(self.on_add_entry)
        self.link_entry.returnPressed.connect(self.on_add_entry)
        # closebtn.clicked.connect(self.accept)

        self.table_widget.drag_drop_sig.connect(self.mark_table_rows_for_actions)
        self.build_bm_ui()

    def build_bm_ui(self):

        self.table_widget.setRowCount(len(self.bm_dict))

        nr_crt = 0
        sorted_bookmarks = sorted(list(self.bm_dict.items()), key=lambda x: int(x[0]))
        for entry, bookmark in sorted_bookmarks:
            row = nr_crt
            nr_crt += 1

            title = bookmark[0]
            weblink = bookmark[1]

            id_item = QtWidgets.QTableWidgetItem('%d' % int(nr_crt))
            # id.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            self.table_widget.setItem(row, 0, id_item)  # Tool name/id

            title_item = QtWidgets.QTableWidgetItem(title)
            self.table_widget.setItem(row, 1, title_item)

            weblink_txt = QtWidgets.QTextBrowser()
            weblink_txt.setOpenExternalLinks(True)
            weblink_txt.setFrameStyle(QtWidgets.QFrame.NoFrame)
            weblink_txt.document().setDefaultStyleSheet("a{ text-decoration: none; }")

            weblink_txt.setHtml('<a href=%s>%s</a>' % (weblink, weblink))

            self.table_widget.setCellWidget(row, 2, weblink_txt)

            vertical_header = self.table_widget.verticalHeader()
            vertical_header.hide()

            horizontal_header = self.table_widget.horizontalHeader()
            horizontal_header.setMinimumSectionSize(10)
            horizontal_header.setDefaultSectionSize(70)
            horizontal_header.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
            horizontal_header.resizeSection(0, 20)
            horizontal_header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
            horizontal_header.setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)

        self.mark_table_rows_for_actions()

        self.app.defaults["global_bookmarks"].clear()
        for key, val in self.bm_dict.items():
            self.app.defaults["global_bookmarks"][key] = deepcopy(val)

    def on_add_entry(self, **kwargs):
        """
        Add a entry in the Bookmark Table and in the menu actions
        :return: None
        """
        if 'title' in kwargs:
            title = kwargs['title']
        else:
            title = self.title_entry.get_value()
        if title == '':
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("Title entry is empty."))
            return 'fail'

        if 'link' in kwargs:
            link = kwargs['link']
        else:
            link = self.link_entry.get_value()

        if link == 'http://':
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("Web link entry is empty."))
            return 'fail'

        # if 'http' not in link or 'https' not in link:
        #     link = 'http://' + link

        for bookmark in self.bm_dict.values():
            if title == bookmark[0] or link == bookmark[1]:
                self.app.inform.emit('[ERROR_NOTCL] %s' % _("Either the Title or the Weblink already in the table."))
                return 'fail'

        # for some reason if the last char in the weblink is a slash it does not make the link clickable
        # so I remove it
        if link[-1] == '/':
            link = link[:-1]
        # add the new entry to storage
        new_entry = len(self.bm_dict) + 1
        self.bm_dict[str(new_entry)] = [title, link]

        # add the link to the menu but only if it is within the set limit
        bm_limit = int(self.app.defaults["global_bookmarks_limit"])
        if len(self.bm_dict) < bm_limit:
            act = QtWidgets.QAction(parent=self.app.ui.menuhelp_bookmarks)
            act.setText(title)
            act.setIcon(QtGui.QIcon(self.app.resource_location + '/link16.png'))
            act.triggered.connect(lambda: webbrowser.open(link))
            self.app.ui.menuhelp_bookmarks.insertAction(self.app.ui.menuhelp_bookmarks_manager, act)

        self.app.inform.emit('[success] %s' % _("Bookmark added."))

        # add the new entry to the bookmark manager table
        self.build_bm_ui()

    def on_remove_entry(self):
        """
        Remove an Entry in the Bookmark table and from the menu actions
        :return:
        """
        index_list = []
        for model_index in self.table_widget.selectionModel().selectedRows():
            index = QtCore.QPersistentModelIndex(model_index)
            index_list.append(index)
            title_to_remove = self.table_widget.item(model_index.row(), 1).text()

            if title_to_remove == 'FlatCAM' or title_to_remove == 'Backup Site':
                self.app.inform.emit('[WARNING_NOTCL] %s.' % _("This bookmark can not be removed"))
                self.build_bm_ui()
                return
            else:
                for k, bookmark in list(self.bm_dict.items()):
                    if title_to_remove == bookmark[0]:
                        # remove from the storage
                        self.bm_dict.pop(k, None)

                        for act in self.app.ui.menuhelp_bookmarks.actions():
                            if act.text() == title_to_remove:
                                # disconnect the signal
                                try:
                                    act.triggered.disconnect()
                                except TypeError:
                                    pass
                                # remove the action from the menu
                                self.app.ui.menuhelp_bookmarks.removeAction(act)

        # house keeping: it pays to have keys increased by one
        new_key = 0
        new_dict = {}
        for k, v in self.bm_dict.items():
            # we start with key 1 so we can use the len(self.bm_dict)
            # when adding bookmarks (keys in bm_dict)
            new_key += 1
            new_dict[str(new_key)] = v

        self.bm_dict = deepcopy(new_dict)
        new_dict.clear()

        self.app.inform.emit('[success] %s' % _("Bookmark removed."))

        # for index in index_list:
        #     self.table_widget.model().removeRow(index.row())
        self.build_bm_ui()

    def on_export_bookmarks(self):
        self.app.report_usage("on_export_bookmarks")
        self.app.log.debug("on_export_bookmarks()")

        date = str(datetime.today()).rpartition('.')[0]
        date = ''.join(c for c in date if c not in ':-')
        date = date.replace(' ', '_')

        filter__ = "Text File (*.TXT);;All Files (*.*)"
        filename, _f = FCFileSaveDialog.get_saved_filename( caption=_("Export FlatCAM Bookmarks"),
                                                             directory='{l_save}/FlatCAM_{n}_{date}'.format(
                                                                 l_save=str(self.app.get_last_save_folder()),
                                                                 n=_("Bookmarks"),
                                                                 date=date),
                                                             filter=filter__)

        filename = str(filename)

        if filename == "":
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled."))
            return
        else:
            try:
                f = open(filename, 'w')
                f.close()
            except PermissionError:
                self.app.inform.emit('[WARNING] %s' %
                                     _("Permission denied, saving not possible.\n"
                                       "Most likely another app is holding the file open and not accessible."))
                return
            except IOError:
                self.app.log.debug('Creating a new bookmarks file ...')
                f = open(filename, 'w')
                f.close()
            except Exception:
                e = sys.exc_info()[0]
                self.app.log.error("Could not load defaults file.")
                self.app.log.error(str(e))
                self.app.inform.emit('[ERROR_NOTCL] %s' % _("Could not load bookmarks file."))
                return

            # Save Bookmarks to a file
            try:
                with open(filename, "w") as f:
                    for title, link in self.bm_dict.items():
                        line2write = str(title) + ':' + str(link) + '\n'
                        f.write(line2write)
            except Exception:
                self.app.inform.emit('[ERROR_NOTCL] %s' % _("Failed to write bookmarks to file."))
                return
        self.app.inform.emit('[success] %s: %s' % (_("Exported bookmarks to"), filename))

    def on_import_bookmarks(self):
        self.app.log.debug("on_import_bookmarks()")

        filter_ = "Text File (*.txt);;All Files (*.*)"
        filename, _f = QtWidgets.QFileDialog.getOpenFileName(caption=_("Import FlatCAM Bookmarks"), filter=filter_)

        filename = str(filename)

        if filename == "":
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled."))
        else:
            try:
                with open(filename) as f:
                    bookmarks = f.readlines()
            except IOError:
                self.app.log.error("Could not load bookmarks file.")
                self.app.inform.emit('[ERROR_NOTCL] %s' % _("Could not load bookmarks file."))
                return

            for line in bookmarks:
                proc_line = line.replace(' ', '').partition(':')
                self.on_add_entry(title=proc_line[0], link=proc_line[2])

            self.app.inform.emit('[success] %s: %s' % (_("Imported Bookmarks from"), filename))

    def mark_table_rows_for_actions(self):
        for row in range(self.table_widget.rowCount()):
            item_to_paint = self.table_widget.item(row, 0)
            if row < self.app.defaults["global_bookmarks_limit"]:
                item_to_paint.setBackground(QtGui.QColor('gray'))
                # item_to_paint.setForeground(QtGui.QColor('black'))
            else:
                item_to_paint.setBackground(QtGui.QColor('white'))
                # item_to_paint.setForeground(QtGui.QColor('black'))

    def rebuild_actions(self):
        # rebuild the storage to reflect the order of the lines
        self.bm_dict.clear()
        for row in range(self.table_widget.rowCount()):
            title = self.table_widget.item(row, 1).text()
            wlink = self.table_widget.cellWidget(row, 2).toPlainText()

            entry = int(row) + 1
            self.bm_dict.update(
                {
                    str(entry): [title, wlink]
                }
            )

        self.app.install_bookmarks(book_dict=self.bm_dict)

    # def accept(self):
    #     self.rebuild_actions()
    #     super().accept()

    def closeEvent(self, QCloseEvent):
        self.rebuild_actions()
        super().closeEvent(QCloseEvent)


class ToolsDB(QtWidgets.QWidget):

    mark_tools_rows = QtCore.pyqtSignal()

    def __init__(self, app, callback_on_edited, callback_on_tool_request, parent=None):
        super(ToolsDB, self).__init__(parent)

        self.app = app
        self.decimals = 4
        self.callback_app = callback_on_edited

        self.on_tool_request = callback_on_tool_request

        self.offset_item_options = ["Path", "In", "Out", "Custom"]
        self.type_item_options = ["Iso", "Rough", "Finish"]
        self.tool_type_item_options = ["C1", "C2", "C3", "C4", "B", "V"]

        '''
        dict to hold all the tools in the Tools DB
        format:
        {
            tool_id: {
                'name': 'new_tool'
                'tooldia': self.app.defaults["geometry_cnctooldia"]
                'offset': 'Path'
                'offset_value': 0.0
                'type':  _('Rough'),
                'tool_type': 'C1'
                'data': dict()
            }
        }
        '''
        self.db_tool_dict = {}

        # layouts
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        table_hlay = QtWidgets.QHBoxLayout()
        layout.addLayout(table_hlay)

        self.table_widget = FCTable(drag_drop=True)
        self.table_widget.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        table_hlay.addWidget(self.table_widget)

        # set the number of columns and the headers tool tips
        self.configure_table()

        # pal = QtGui.QPalette()
        # pal.setColor(QtGui.QPalette.Background, Qt.white)

        # New Bookmark
        new_vlay = QtWidgets.QVBoxLayout()
        layout.addLayout(new_vlay)

        # new_tool_lbl = QtWidgets.QLabel('<b>%s</b>' % _("New Tool"))
        # new_vlay.addWidget(new_tool_lbl, alignment=QtCore.Qt.AlignBottom)

        self.buttons_frame = QtWidgets.QFrame()
        self.buttons_frame.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.buttons_frame)
        self.buttons_box = QtWidgets.QHBoxLayout()
        self.buttons_box.setContentsMargins(0, 0, 0, 0)
        self.buttons_frame.setLayout(self.buttons_box)
        self.buttons_frame.show()

        add_entry_btn = FCButton(_("Add Geometry Tool in DB"))
        add_entry_btn.setToolTip(
            _("Add a new tool in the Tools Database.\n"
              "It will be used in the Geometry UI.\n"
              "You can edit it after it is added.")
        )
        self.buttons_box.addWidget(add_entry_btn)

        # add_fct_entry_btn = FCButton(_("Add Paint/NCC Tool in DB"))
        # add_fct_entry_btn.setToolTip(
        #     _("Add a new tool in the Tools Database.\n"
        #       "It will be used in the Paint/NCC Tools UI.\n"
        #       "You can edit it after it is added.")
        # )
        # self.buttons_box.addWidget(add_fct_entry_btn)

        remove_entry_btn = FCButton(_("Delete Tool from DB"))
        remove_entry_btn.setToolTip(
            _("Remove a selection of tools in the Tools Database.")
        )
        self.buttons_box.addWidget(remove_entry_btn)

        export_db_btn = FCButton(_("Export DB"))
        export_db_btn.setToolTip(
            _("Save the Tools Database to a custom text file.")
        )
        self.buttons_box.addWidget(export_db_btn)

        import_db_btn = FCButton(_("Import DB"))
        import_db_btn.setToolTip(
            _("Load the Tools Database information's from a custom text file.")
        )
        self.buttons_box.addWidget(import_db_btn)

        self.add_tool_from_db = FCButton(_("Add Tool from Tools DB"))
        self.add_tool_from_db.setToolTip(
            _("Add a new tool in the Tools Table of the\n"
              "active Geometry object after selecting a tool\n"
              "in the Tools Database.")
        )
        self.add_tool_from_db.hide()

        self.cancel_tool_from_db = FCButton(_("Cancel"))
        self.cancel_tool_from_db.hide()

        hlay = QtWidgets.QHBoxLayout()
        layout.addLayout(hlay)
        hlay.addWidget(self.add_tool_from_db)
        hlay.addWidget(self.cancel_tool_from_db)
        hlay.addStretch()

        # ##############################################################################
        # ######################## SIGNALS #############################################
        # ##############################################################################

        add_entry_btn.clicked.connect(self.on_tool_add)
        remove_entry_btn.clicked.connect(self.on_tool_delete)
        export_db_btn.clicked.connect(self.on_export_tools_db_file)
        import_db_btn.clicked.connect(self.on_import_tools_db_file)
        # closebtn.clicked.connect(self.accept)

        self.add_tool_from_db.clicked.connect(self.on_tool_requested_from_app)
        self.cancel_tool_from_db.clicked.connect(self.on_cancel_tool)

        self.setup_db_ui()

    def configure_table(self):
        self.table_widget.setColumnCount(27)
        # self.table_widget.setColumnWidth(0, 20)
        self.table_widget.setHorizontalHeaderLabels(
            [
                '#',
                _("Tool Name"),
                _("Tool Dia"),
                _("Tool Offset"),
                _("Custom Offset"),
                _("Tool Type"),
                _("Tool Shape"),
                _("Cut Z"),
                _("MultiDepth"),
                _("DPP"),
                _("V-Dia"),
                _("V-Angle"),
                _("Travel Z"),
                _("FR"),
                _("FR Z"),
                _("FR Rapids"),
                _("Spindle Speed"),
                _("Dwell"),
                _("Dwelltime"),
                _("Preprocessor"),
                _("ExtraCut"),
                _("E-Cut Length"),
                _("Toolchange"),
                _("Toolchange XY"),
                _("Toolchange Z"),
                _("Start Z"),
                _("End Z"),
            ]
        )
        self.table_widget.horizontalHeaderItem(0).setToolTip(
            _("Tool Index."))
        self.table_widget.horizontalHeaderItem(1).setToolTip(
            _("Tool name.\n"
              "This is not used in the app, it's function\n"
              "is to serve as a note for the user."))
        self.table_widget.horizontalHeaderItem(2).setToolTip(
            _("Tool Diameter."))
        self.table_widget.horizontalHeaderItem(3).setToolTip(
            _("Tool Offset.\n"
              "Can be of a few types:\n"
              "Path = zero offset\n"
              "In = offset inside by half of tool diameter\n"
              "Out = offset outside by half of tool diameter\n"
              "Custom = custom offset using the Custom Offset value"))
        self.table_widget.horizontalHeaderItem(4).setToolTip(
            _("Custom Offset.\n"
              "A value to be used as offset from the current path."))
        self.table_widget.horizontalHeaderItem(5).setToolTip(
            _("Tool Type.\n"
              "Can be:\n"
              "Iso = isolation cut\n"
              "Rough = rough cut, low feedrate, multiple passes\n"
              "Finish = finishing cut, high feedrate"))
        self.table_widget.horizontalHeaderItem(6).setToolTip(
            _("Tool Shape. \n"
              "Can be:\n"
              "C1 ... C4 = circular tool with x flutes\n"
              "B = ball tip milling tool\n"
              "V = v-shape milling tool"))
        self.table_widget.horizontalHeaderItem(7).setToolTip(
            _("Cutting Depth.\n"
              "The depth at which to cut into material."))
        self.table_widget.horizontalHeaderItem(8).setToolTip(
            _("Multi Depth.\n"
              "Selecting this will allow cutting in multiple passes,\n"
              "each pass adding a DPP parameter depth."))
        self.table_widget.horizontalHeaderItem(9).setToolTip(
            _("DPP. Depth per Pass.\n"
              "The value used to cut into material on each pass."))
        self.table_widget.horizontalHeaderItem(10).setToolTip(
            _("V-Dia.\n"
              "Diameter of the tip for V-Shape Tools."))
        self.table_widget.horizontalHeaderItem(11).setToolTip(
            _("V-Agle.\n"
              "Angle at the tip for the V-Shape Tools."))
        self.table_widget.horizontalHeaderItem(12).setToolTip(
            _("Clearance Height.\n"
              "Height at which the milling bit will travel between cuts,\n"
              "above the surface of the material, avoiding all fixtures."))
        self.table_widget.horizontalHeaderItem(13).setToolTip(
            _("FR. Feedrate\n"
              "The speed on XY plane used while cutting into material."))
        self.table_widget.horizontalHeaderItem(14).setToolTip(
            _("FR Z. Feedrate Z\n"
              "The speed on Z plane."))
        self.table_widget.horizontalHeaderItem(15).setToolTip(
            _("FR Rapids. Feedrate Rapids\n"
              "Speed used while moving as fast as possible.\n"
              "This is used only by some devices that can't use\n"
              "the G0 g-code command. Mostly 3D printers."))
        self.table_widget.horizontalHeaderItem(16).setToolTip(
            _("Spindle Speed.\n"
              "If it's left empty it will not be used.\n"
              "The speed of the spindle in RPM."))
        self.table_widget.horizontalHeaderItem(17).setToolTip(
            _("Dwell.\n"
              "Check this if a delay is needed to allow\n"
              "the spindle motor to reach it's set speed."))
        self.table_widget.horizontalHeaderItem(18).setToolTip(
            _("Dwell Time.\n"
              "A delay used to allow the motor spindle reach it's set speed."))
        self.table_widget.horizontalHeaderItem(19).setToolTip(
            _("Preprocessor.\n"
              "A selection of files that will alter the generated G-code\n"
              "to fit for a number of use cases."))
        self.table_widget.horizontalHeaderItem(20).setToolTip(
            _("Extra Cut.\n"
              "If checked, after a isolation is finished an extra cut\n"
              "will be added where the start and end of isolation meet\n"
              "such as that this point is covered by this extra cut to\n"
              "ensure a complete isolation."))
        self.table_widget.horizontalHeaderItem(21).setToolTip(
            _("Extra Cut length.\n"
              "If checked, after a isolation is finished an extra cut\n"
              "will be added where the start and end of isolation meet\n"
              "such as that this point is covered by this extra cut to\n"
              "ensure a complete isolation. This is the length of\n"
              "the extra cut."))
        self.table_widget.horizontalHeaderItem(22).setToolTip(
            _("Toolchange.\n"
              "It will create a toolchange event.\n"
              "The kind of toolchange is determined by\n"
              "the preprocessor file."))
        self.table_widget.horizontalHeaderItem(23).setToolTip(
            _("Toolchange XY.\n"
              "A set of coordinates in the format (x, y).\n"
              "Will determine the cartesian position of the point\n"
              "where the tool change event take place."))
        self.table_widget.horizontalHeaderItem(24).setToolTip(
            _("Toolchange Z.\n"
              "The position on Z plane where the tool change event take place."))
        self.table_widget.horizontalHeaderItem(25).setToolTip(
            _("Start Z.\n"
              "If it's left empty it will not be used.\n"
              "A position on Z plane to move immediately after job start."))
        self.table_widget.horizontalHeaderItem(26).setToolTip(
            _("End Z.\n"
              "A position on Z plane to move immediately after job stop."))

    def setup_db_ui(self):
        filename = self.app.data_path + '/geo_tools_db.FlatDB'

        # load the database tools from the file
        try:
            with open(filename) as f:
                tools = f.read()
        except IOError:
            self.app.log.error("Could not load tools DB file.")
            self.app.inform.emit('[ERROR] %s' % _("Could not load Tools DB file."))
            return

        try:
            self.db_tool_dict = json.loads(tools)
        except Exception:
            e = sys.exc_info()[0]
            self.app.log.error(str(e))
            self.app.inform.emit('[ERROR] %s' % _("Failed to parse Tools DB file."))
            return

        self.app.inform.emit('[success] %s: %s' % (_("Loaded FlatCAM Tools DB from"), filename))

        self.build_db_ui()

        self.table_widget.setupContextMenu()
        self.table_widget.addContextMenu(
            _("Add to DB"), self.on_tool_add, icon=QtGui.QIcon(self.app.resource_location + "/plus16.png"))
        self.table_widget.addContextMenu(
            _("Copy from DB"), self.on_tool_copy, icon=QtGui.QIcon(self.app.resource_location + "/copy16.png"))
        self.table_widget.addContextMenu(
            _("Delete from DB"), self.on_tool_delete, icon=QtGui.QIcon(self.app.resource_location + "/delete32.png"))

    def build_db_ui(self):
        self.ui_disconnect()
        self.table_widget.setRowCount(len(self.db_tool_dict))

        nr_crt = 0

        for toolid, dict_val in self.db_tool_dict.items():
            row = nr_crt
            nr_crt += 1

            t_name = dict_val['name']
            try:
                self.add_tool_table_line(row, name=t_name, widget=self.table_widget, tooldict=dict_val)
            except Exception as e:
                self.app.log.debug("ToolDB.build_db_ui.add_tool_table_line() --> %s" % str(e))
            vertical_header = self.table_widget.verticalHeader()
            vertical_header.hide()

            horizontal_header = self.table_widget.horizontalHeader()
            horizontal_header.setMinimumSectionSize(10)
            horizontal_header.setDefaultSectionSize(70)

            self.table_widget.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
            for x in range(27):
                self.table_widget.resizeColumnToContents(x)

            horizontal_header.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
            # horizontal_header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
            # horizontal_header.setSectionResizeMode(13, QtWidgets.QHeaderView.Fixed)

            horizontal_header.resizeSection(0, 20)
            # horizontal_header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
            # horizontal_header.setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)

        self.ui_connect()

    def add_tool_table_line(self, row, name, widget, tooldict):
        data = tooldict['data']

        nr_crt = row + 1
        id_item = QtWidgets.QTableWidgetItem('%d' % int(nr_crt))
        # id_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        flags = id_item.flags() & ~QtCore.Qt.ItemIsEditable
        id_item.setFlags(flags)
        widget.setItem(row, 0, id_item)  # Tool name/id

        tool_name_item = QtWidgets.QTableWidgetItem(name)
        widget.setItem(row, 1, tool_name_item)

        dia_item = FCDoubleSpinner()
        dia_item.set_precision(self.decimals)
        dia_item.setSingleStep(0.1)
        dia_item.set_range(0.0, 9999.9999)
        dia_item.set_value(float(tooldict['tooldia']))
        widget.setCellWidget(row, 2, dia_item)

        tool_offset_item = FCComboBox()
        for item in self.offset_item_options:
            tool_offset_item.addItem(item)
        tool_offset_item.set_value(tooldict['offset'])
        widget.setCellWidget(row, 3, tool_offset_item)

        c_offset_item = FCDoubleSpinner()
        c_offset_item.set_precision(self.decimals)
        c_offset_item.setSingleStep(0.1)
        c_offset_item.set_range(-9999.9999, 9999.9999)
        c_offset_item.set_value(float(tooldict['offset_value']))
        widget.setCellWidget(row, 4, c_offset_item)

        tt_item = FCComboBox()
        for item in self.type_item_options:
            tt_item.addItem(item)
        tt_item.set_value(tooldict['type'])
        widget.setCellWidget(row, 5, tt_item)

        tshape_item = FCComboBox()
        for item in self.tool_type_item_options:
            tshape_item.addItem(item)
        tshape_item.set_value(tooldict['tool_type'])
        widget.setCellWidget(row, 6, tshape_item)

        cutz_item = FCDoubleSpinner()
        cutz_item.set_precision(self.decimals)
        cutz_item.setSingleStep(0.1)
        if self.app.defaults['global_machinist_setting']:
            cutz_item.set_range(-9999.9999, 9999.9999)
        else:
            cutz_item.set_range(-9999.9999, -0.0000)

        cutz_item.set_value(float(data['cutz']))
        widget.setCellWidget(row, 7, cutz_item)

        multidepth_item = FCCheckBox()
        multidepth_item.set_value(data['multidepth'])
        widget.setCellWidget(row, 8, multidepth_item)

        # to make the checkbox centered but it can no longer have it's value accessed - needs a fix using findchild()
        # multidepth_item = QtWidgets.QWidget()
        # cb = FCCheckBox()
        # cb.set_value(data['multidepth'])
        # qhboxlayout = QtWidgets.QHBoxLayout(multidepth_item)
        # qhboxlayout.addWidget(cb)
        # qhboxlayout.setAlignment(QtCore.Qt.AlignCenter)
        # qhboxlayout.setContentsMargins(0, 0, 0, 0)
        # widget.setCellWidget(row, 8, multidepth_item)

        depth_per_pass_item = FCDoubleSpinner()
        depth_per_pass_item.set_precision(self.decimals)
        depth_per_pass_item.setSingleStep(0.1)
        depth_per_pass_item.set_range(0.0, 9999.9999)
        depth_per_pass_item.set_value(float(data['depthperpass']))
        widget.setCellWidget(row, 9, depth_per_pass_item)

        vtip_dia_item = FCDoubleSpinner()
        vtip_dia_item.set_precision(self.decimals)
        vtip_dia_item.setSingleStep(0.1)
        vtip_dia_item.set_range(0.0, 9999.9999)
        vtip_dia_item.set_value(float(data['vtipdia']))
        widget.setCellWidget(row, 10, vtip_dia_item)

        vtip_angle_item = FCDoubleSpinner()
        vtip_angle_item.set_precision(self.decimals)
        vtip_angle_item.setSingleStep(0.1)
        vtip_angle_item.set_range(-360.0, 360.0)
        vtip_angle_item.set_value(float(data['vtipangle']))
        widget.setCellWidget(row, 11, vtip_angle_item)

        travelz_item = FCDoubleSpinner()
        travelz_item.set_precision(self.decimals)
        travelz_item.setSingleStep(0.1)
        if self.app.defaults['global_machinist_setting']:
            travelz_item.set_range(-9999.9999, 9999.9999)
        else:
            travelz_item.set_range(0.0000, 9999.9999)

        travelz_item.set_value(float(data['travelz']))
        widget.setCellWidget(row, 12, travelz_item)

        fr_item = FCDoubleSpinner()
        fr_item.set_precision(self.decimals)
        fr_item.set_range(0.0, 9999.9999)
        fr_item.set_value(float(data['feedrate']))
        widget.setCellWidget(row, 13, fr_item)

        frz_item = FCDoubleSpinner()
        frz_item.set_precision(self.decimals)
        frz_item.set_range(0.0, 9999.9999)
        frz_item.set_value(float(data['feedrate_z']))
        widget.setCellWidget(row, 14, frz_item)

        frrapids_item = FCDoubleSpinner()
        frrapids_item.set_precision(self.decimals)
        frrapids_item.set_range(0.0, 9999.9999)
        frrapids_item.set_value(float(data['feedrate_rapid']))
        widget.setCellWidget(row, 15, frrapids_item)

        spindlespeed_item = FCSpinner()
        spindlespeed_item.set_range(0, 1000000)
        spindlespeed_item.set_value(int(data['spindlespeed']))
        spindlespeed_item.set_step(100)
        widget.setCellWidget(row, 16, spindlespeed_item)

        dwell_item = FCCheckBox()
        dwell_item.set_value(data['dwell'])
        widget.setCellWidget(row, 17, dwell_item)

        dwelltime_item = FCDoubleSpinner()
        dwelltime_item.set_precision(self.decimals)
        dwelltime_item.set_range(0.0000, 9999.9999)
        dwelltime_item.set_value(float(data['dwelltime']))
        widget.setCellWidget(row, 18, dwelltime_item)

        pp_item = FCComboBox()
        for item in self.app.preprocessors:
            pp_item.addItem(item)
        pp_item.set_value(data['ppname_g'])
        widget.setCellWidget(row, 19, pp_item)

        ecut_item = FCCheckBox()
        ecut_item.set_value(data['extracut'])
        widget.setCellWidget(row, 20, ecut_item)

        ecut_length_item = FCDoubleSpinner()
        ecut_length_item.set_precision(self.decimals)
        ecut_length_item.set_range(0.0000, 9999.9999)
        ecut_length_item.set_value(data['extracut_length'])
        widget.setCellWidget(row, 21, ecut_length_item)

        toolchange_item = FCCheckBox()
        toolchange_item.set_value(data['toolchange'])
        widget.setCellWidget(row, 22, toolchange_item)

        toolchangexy_item = QtWidgets.QTableWidgetItem(str(data['toolchangexy']) if data['toolchangexy'] else '')
        widget.setItem(row, 23, toolchangexy_item)

        toolchangez_item = FCDoubleSpinner()
        toolchangez_item.set_precision(self.decimals)
        toolchangez_item.setSingleStep(0.1)
        if self.app.defaults['global_machinist_setting']:
            toolchangez_item.set_range(-9999.9999, 9999.9999)
        else:
            toolchangez_item.set_range(0.0000, 9999.9999)

        toolchangez_item.set_value(float(data['toolchangez']))
        widget.setCellWidget(row, 24, toolchangez_item)

        startz_item = QtWidgets.QTableWidgetItem(str(data['startz']) if data['startz'] else '')
        widget.setItem(row, 25, startz_item)

        endz_item = FCDoubleSpinner()
        endz_item.set_precision(self.decimals)
        endz_item.setSingleStep(0.1)
        if self.app.defaults['global_machinist_setting']:
            endz_item.set_range(-9999.9999, 9999.9999)
        else:
            endz_item.set_range(0.0000, 9999.9999)

        endz_item.set_value(float(data['endz']))
        widget.setCellWidget(row, 26, endz_item)

    def on_tool_add(self):
        """
        Add a tool in the DB Tool Table
        :return: None
        """

        default_data = {}
        default_data.update({
            "cutz": float(self.app.defaults["geometry_cutz"]),
            "multidepth": self.app.defaults["geometry_multidepth"],
            "depthperpass": float(self.app.defaults["geometry_depthperpass"]),
            "vtipdia": float(self.app.defaults["geometry_vtipdia"]),
            "vtipangle": float(self.app.defaults["geometry_vtipangle"]),
            "travelz": float(self.app.defaults["geometry_travelz"]),
            "feedrate": float(self.app.defaults["geometry_feedrate"]),
            "feedrate_z": float(self.app.defaults["geometry_feedrate_z"]),
            "feedrate_rapid": float(self.app.defaults["geometry_feedrate_rapid"]),
            "spindlespeed": self.app.defaults["geometry_spindlespeed"],
            "dwell": self.app.defaults["geometry_dwell"],
            "dwelltime": float(self.app.defaults["geometry_dwelltime"]),
            "ppname_g": self.app.defaults["geometry_ppname_g"],
            "extracut": self.app.defaults["geometry_extracut"],
            "extracut_length": float(self.app.defaults["geometry_extracut_length"]),
            "toolchange": self.app.defaults["geometry_toolchange"],
            "toolchangexy": self.app.defaults["geometry_toolchangexy"],
            "toolchangez": float(self.app.defaults["geometry_toolchangez"]),
            "startz": self.app.defaults["geometry_startz"],
            "endz": float(self.app.defaults["geometry_endz"])
        })

        dict_elem = {}
        dict_elem['name'] = 'new_tool'
        if type(self.app.defaults["geometry_cnctooldia"]) == float:
            dict_elem['tooldia'] = self.app.defaults["geometry_cnctooldia"]
        else:
            try:
                tools_string = self.app.defaults["geometry_cnctooldia"].split(",")
                tools_diameters = [eval(a) for a in tools_string if a != '']
                dict_elem['tooldia'] = tools_diameters[0] if tools_diameters else 0.0
            except Exception as e:
                self.app.log.debug("ToolDB.on_tool_add() --> %s" % str(e))
                return

        dict_elem['offset'] = 'Path'
        dict_elem['offset_value'] = 0.0
        dict_elem['type'] = 'Rough'
        dict_elem['tool_type'] = 'C1'
        dict_elem['data'] = default_data

        new_toolid = len(self.db_tool_dict) + 1
        self.db_tool_dict[new_toolid] = deepcopy(dict_elem)

        # add the new entry to the Tools DB table
        self.build_db_ui()
        self.callback_on_edited()
        self.app.inform.emit('[success] %s' % _("Tool added to DB."))

    def on_tool_copy(self):
        """
        Copy a selection of Tools in the Tools DB table
        :return:
        """
        new_tool_id = self.table_widget.rowCount() + 1
        for model_index in self.table_widget.selectionModel().selectedRows():
            # index = QtCore.QPersistentModelIndex(model_index)
            old_tool_id = self.table_widget.item(model_index.row(), 0).text()
            new_tool_id += 1

            for toolid, dict_val in list(self.db_tool_dict.items()):
                if int(old_tool_id) == int(toolid):
                    self.db_tool_dict.update({
                        new_tool_id: deepcopy(dict_val)
                    })

        self.build_db_ui()
        self.callback_on_edited()
        self.app.inform.emit('[success] %s' % _("Tool copied from Tools DB."))

    def on_tool_delete(self):
        """
        Delete a selection of Tools in the Tools DB table
        :return:
        """
        for model_index in self.table_widget.selectionModel().selectedRows():
            # index = QtCore.QPersistentModelIndex(model_index)
            toolname_to_remove = self.table_widget.item(model_index.row(), 0).text()

            for toolid, dict_val in list(self.db_tool_dict.items()):
                if int(toolname_to_remove) == int(toolid):
                    # remove from the storage
                    self.db_tool_dict.pop(toolid, None)

        self.build_db_ui()
        self.callback_on_edited()
        self.app.inform.emit('[success] %s' % _("Tool removed from Tools DB."))

    def on_export_tools_db_file(self):
        self.app.report_usage("on_export_tools_db_file")
        self.app.log.debug("on_export_tools_db_file()")

        date = str(datetime.today()).rpartition('.')[0]
        date = ''.join(c for c in date if c not in ':-')
        date = date.replace(' ', '_')

        filter__ = "Text File (*.TXT);;All Files (*.*)"
        filename, _f = FCFileSaveDialog.get_saved_filename( caption=_("Export Tools Database"),
                                                             directory='{l_save}/FlatCAM_{n}_{date}'.format(
                                                                 l_save=str(self.app.get_last_save_folder()),
                                                                 n=_("Tools_Database"),
                                                                 date=date),
                                                             filter=filter__)

        filename = str(filename)

        if filename == "":
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled."))
            return
        else:
            try:
                f = open(filename, 'w')
                f.close()
            except PermissionError:
                self.app.inform.emit('[WARNING] %s' %
                                     _("Permission denied, saving not possible.\n"
                                       "Most likely another app is holding the file open and not accessible."))
                return
            except IOError:
                self.app.log.debug('Creating a new Tools DB file ...')
                f = open(filename, 'w')
                f.close()
            except Exception:
                e = sys.exc_info()[0]
                self.app.log.error("Could not load Tools DB file.")
                self.app.log.error(str(e))
                self.app.inform.emit('[ERROR_NOTCL] %s' % _("Could not load Tools DB file."))
                return

            # Save update options
            try:
                # Save Tools DB in a file
                try:
                    with open(filename, "w") as f:
                        json.dump(self.db_tool_dict, f, default=to_dict, indent=2)
                except Exception as e:
                    self.app.log.debug("App.on_save_tools_db() --> %s" % str(e))
                    self.inform.emit('[ERROR_NOTCL] %s' % _("Failed to write Tools DB to file."))
                    return
            except Exception:
                self.app.inform.emit('[ERROR_NOTCL] %s' % _("Failed to write Tools DB to file."))
                return

        self.app.inform.emit('[success] %s: %s' % (_("Exported Tools DB to"), filename))

    def on_import_tools_db_file(self):
        self.app.report_usage("on_import_tools_db_file")
        self.app.log.debug("on_import_tools_db_file()")

        filter__ = "Text File (*.TXT);;All Files (*.*)"
        filename, _f = QtWidgets.QFileDialog.getOpenFileName(caption=_("Import FlatCAM Tools DB"), filter=filter__)

        if filename == "":
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled."))
        else:
            try:
                with open(filename) as f:
                    tools_in_db = f.read()
            except IOError:
                self.app.log.error("Could not load Tools DB file.")
                self.app.inform.emit('[ERROR_NOTCL] %s' % _("Could not load Tools DB file."))
                return

            try:
                self.db_tool_dict = json.loads(tools_in_db)
            except Exception:
                e = sys.exc_info()[0]
                self.app.log.error(str(e))
                self.app.inform.emit('[ERROR] %s' % _("Failed to parse Tools DB file."))
                return

            self.app.inform.emit('[success] %s: %s' % (_("Loaded FlatCAM Tools DB from"), filename))
            self.build_db_ui()
            self.callback_on_edited()

    def on_save_tools_db(self, silent=False):
        self.app.log.debug("ToolsDB.on_save_button() --> Saving Tools Database to file.")

        filename = self.app.data_path + "/geo_tools_db.FlatDB"

        # Preferences save, update the color of the Tools DB Tab text
        for idx in range(self.app.ui.plot_tab_area.count()):
            if self.app.ui.plot_tab_area.tabText(idx) == _("Tools Database"):
                self.app.ui.plot_tab_area.tabBar.setTabTextColor(idx, QtGui.QColor('black'))

                # Save Tools DB in a file
                try:
                    f = open(filename, "w")
                    json.dump(self.db_tool_dict, f, default=to_dict, indent=2)
                    f.close()
                except Exception as e:
                    self.app.log.debug("ToolsDB.on_save_tools_db() --> %s" % str(e))
                    self.app.inform.emit('[ERROR_NOTCL] %s' % _("Failed to write Tools DB to file."))
                    return

                if not silent:
                    self.app.inform.emit('[success] %s' % _("Saved Tools DB."))

    def ui_connect(self):
        try:
            try:
                self.table_widget.itemChanged.disconnect(self.callback_on_edited)
            except (TypeError, AttributeError):
                pass
            self.table_widget.itemChanged.connect(self.callback_on_edited)
        except AttributeError:
            pass

        for row in range(self.table_widget.rowCount()):
            for col in range(self.table_widget.columnCount()):
                # ComboBox
                try:
                    try:
                        self.table_widget.cellWidget(row, col).currentIndexChanged.disconnect(self.callback_on_edited)
                    except (TypeError, AttributeError):
                        pass
                    self.table_widget.cellWidget(row, col).currentIndexChanged.connect(self.callback_on_edited)
                except AttributeError:
                    pass

                # CheckBox
                try:
                    try:
                        self.table_widget.cellWidget(row, col).toggled.disconnect(self.callback_on_edited)
                    except (TypeError, AttributeError):
                        pass
                    self.table_widget.cellWidget(row, col).toggled.connect(self.callback_on_edited)
                except AttributeError:
                    pass

                # SpinBox, DoubleSpinBox
                try:
                    try:
                        self.table_widget.cellWidget(row, col).valueChanged.disconnect(self.callback_on_edited)
                    except (TypeError, AttributeError):
                        pass
                    self.table_widget.cellWidget(row, col).valueChanged.connect(self.callback_on_edited)
                except AttributeError:
                    pass

    def ui_disconnect(self):
        try:
            self.table_widget.itemChanged.disconnect(self.callback_on_edited)
        except (TypeError, AttributeError):
            pass

        for row in range(self.table_widget.rowCount()):
            for col in range(self.table_widget.columnCount()):
                # ComboBox
                try:
                    self.table_widget.cellWidget(row, col).currentIndexChanged.disconnect(self.callback_on_edited)
                except (TypeError, AttributeError):
                    pass

                # CheckBox
                try:
                    self.table_widget.cellWidget(row, col).toggled.disconnect(self.callback_on_edited)
                except (TypeError, AttributeError):
                    pass

                # SpinBox, DoubleSpinBox
                try:
                    self.table_widget.cellWidget(row, col).valueChanged.disconnect(self.callback_on_edited)
                except (TypeError, AttributeError):
                    pass

    def callback_on_edited(self):

        # update the dictionary storage self.db_tool_dict
        self.db_tool_dict.clear()
        dict_elem = {}
        default_data = {}

        for row in range(self.table_widget.rowCount()):
            new_toolid = row + 1
            for col in range(self.table_widget.columnCount()):
                column_header_text = self.table_widget.horizontalHeaderItem(col).text()
                if column_header_text == _('Tool Name'):
                    dict_elem['name'] = self.table_widget.item(row, col).text()
                elif column_header_text == _('Tool Dia'):
                    dict_elem['tooldia'] = self.table_widget.cellWidget(row, col).get_value()
                elif column_header_text == _('Tool Offset'):
                    dict_elem['offset'] = self.table_widget.cellWidget(row, col).get_value()
                elif column_header_text == _('Custom Offset'):
                    dict_elem['offset_value'] = self.table_widget.cellWidget(row, col).get_value()
                elif column_header_text == _('Tool Type'):
                    dict_elem['type'] = self.table_widget.cellWidget(row, col).get_value()
                elif column_header_text == _('Tool Shape'):
                    dict_elem['tool_type'] = self.table_widget.cellWidget(row, col).get_value()
                else:
                    if column_header_text == _('Cut Z'):
                        default_data['cutz'] = self.table_widget.cellWidget(row, col).get_value()
                    elif column_header_text == _('MultiDepth'):
                        default_data['multidepth'] = self.table_widget.cellWidget(row, col).get_value()
                    elif column_header_text == _('DPP'):
                        default_data['depthperpass'] = self.table_widget.cellWidget(row, col).get_value()
                    elif column_header_text == _('V-Dia'):
                        default_data['vtipdia'] = self.table_widget.cellWidget(row, col).get_value()
                    elif column_header_text == _('V-Angle'):
                        default_data['vtipangle'] = self.table_widget.cellWidget(row, col).get_value()
                    elif column_header_text == _('Travel Z'):
                        default_data['travelz'] = self.table_widget.cellWidget(row, col).get_value()
                    elif column_header_text == _('FR'):
                        default_data['feedrate'] = self.table_widget.cellWidget(row, col).get_value()
                    elif column_header_text == _('FR Z'):
                        default_data['feedrate_z'] = self.table_widget.cellWidget(row, col).get_value()
                    elif column_header_text == _('FR Rapids'):
                        default_data['feedrate_rapid'] = self.table_widget.cellWidget(row, col).get_value()
                    elif column_header_text == _('Spindle Speed'):
                        default_data['spindlespeed'] = self.table_widget.cellWidget(row, col).get_value()
                    elif column_header_text == _('Dwell'):
                        default_data['dwell'] = self.table_widget.cellWidget(row, col).get_value()
                    elif column_header_text == _('Dwelltime'):
                        default_data['dwelltime'] = self.table_widget.cellWidget(row, col).get_value()
                    elif column_header_text == _('Preprocessor'):
                        default_data['ppname_g'] = self.table_widget.cellWidget(row, col).get_value()
                    elif column_header_text == _('ExtraCut'):
                        default_data['extracut'] = self.table_widget.cellWidget(row, col).get_value()
                    elif column_header_text == _("E-Cut Length"):
                        default_data['extracut_length'] = self.table_widget.cellWidget(row, col).get_value()
                    elif column_header_text == _('Toolchange'):
                        default_data['toolchange'] = self.table_widget.cellWidget(row, col).get_value()
                    elif column_header_text == _('Toolchange XY'):
                        default_data['toolchangexy'] = self.table_widget.item(row, col).text()
                    elif column_header_text == _('Toolchange Z'):
                        default_data['toolchangez'] = self.table_widget.cellWidget(row, col).get_value()
                    elif column_header_text == _('Start Z'):
                        default_data['startz'] = float(self.table_widget.item(row, col).text()) \
                            if self.table_widget.item(row, col).text() != '' else None
                    elif column_header_text == _('End Z'):
                        default_data['endz'] = self.table_widget.cellWidget(row, col).get_value()

            dict_elem['data'] = default_data
            self.db_tool_dict.update(
                {
                    new_toolid: deepcopy(dict_elem)
                }
            )

        self.callback_app()

    def on_tool_requested_from_app(self):
        if not self.table_widget.selectionModel().selectedRows():
            self.app.inform.emit('[WARNING_NOTCL] %s...' % _("No Tool/row selected in the Tools Database table"))
            return

        model_index_list = self.table_widget.selectionModel().selectedRows()
        for model_index in model_index_list:
            selected_row = model_index.row()
            tool_uid = selected_row + 1
            for key in self.db_tool_dict.keys():
                if str(key) == str(tool_uid):
                    selected_tool = self.db_tool_dict[key]
                    self.on_tool_request(tool=selected_tool)

    def on_cancel_tool(self):
        for idx in range(self.app.ui.plot_tab_area.count()):
            if self.app.ui.plot_tab_area.tabText(idx) == _("Tools Database"):
                wdg = self.app.ui.plot_tab_area.widget(idx)
                wdg.deleteLater()
                self.app.ui.plot_tab_area.removeTab(idx)
        self.app.inform.emit('%s' % _("Cancelled adding tool from DB."))

    def resize_new_tool_table_widget(self, min_size, max_size):
        """
        Resize the table widget responsible for adding new tool in the Tool Database

        :param min_size: passed by rangeChanged signal or the self.new_tool_table_widget.horizontalScrollBar()
        :param max_size: passed by rangeChanged signal or the self.new_tool_table_widget.horizontalScrollBar()
        :return:
        """
        t_height = self.t_height
        if max_size > min_size:
            t_height = self.t_height + self.new_tool_table_widget.verticalScrollBar().height()

        self.new_tool_table_widget.setMaximumHeight(t_height)

    def closeEvent(self, QCloseEvent):
        super().closeEvent(QCloseEvent)


class ToolsDB2(QtWidgets.QWidget):

    mark_tools_rows = QtCore.pyqtSignal()

    def __init__(self, app, callback_on_edited, callback_on_tool_request, parent=None):
        super(ToolsDB2, self).__init__(parent)

        self.app = app
        self.decimals = self.app.decimals
        self.callback_app = callback_on_edited

        self.on_tool_request = callback_on_tool_request

        self.offset_item_options = ["Path", "In", "Out", "Custom"]
        self.type_item_options = ["Iso", "Rough", "Finish"]
        self.tool_type_item_options = ["C1", "C2", "C3", "C4", "B", "V"]

        '''
        dict to hold all the tools in the Tools DB
        format:
        {
            tool_id: {
                'name': 'new_tool'
                'tooldia': self.app.defaults["geometry_cnctooldia"]
                'offset': 'Path'
                'offset_value': 0.0
                'type':  _('Rough'),
                'tool_type': 'C1'
                'data': dict()
            }
        }
        '''
        self.db_tool_dict = {}

        # layouts
        grid_layout = QtWidgets.QGridLayout()
        grid_layout.setColumnStretch(0, 0)
        grid_layout.setColumnStretch(1, 1)

        self.setLayout(grid_layout)

        tree_layout = QtWidgets.QVBoxLayout()
        grid_layout.addLayout(tree_layout, 0, 0)

        self.tree_widget = FCTree(columns=2, header_hidden=False, protected_column=[0])
        self.tree_widget.setHeaderLabels(["ID", "Tool Name"])
        self.tree_widget.setIndentation(0)
        self.tree_widget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tree_widget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

        # set alternating colors
        # self.tree_widget.setAlternatingRowColors(True)
        # p = QtGui.QPalette()
        # p.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(226, 237, 253) )
        # self.tree_widget.setPalette(p)

        self.tree_widget.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)
        tree_layout.addWidget(self.tree_widget)

        param_hlay = QtWidgets.QHBoxLayout()
        param_area = QtWidgets.QScrollArea()
        param_widget = QtWidgets.QWidget()
        param_widget.setLayout(param_hlay)

        param_area.setWidget(param_widget)
        param_area.setWidgetResizable(True)

        grid_layout.addWidget(param_area, 0, 1)

        # ###########################################################################
        # ############## The UI form ################################################
        # ###########################################################################
        self.basic_box = QtWidgets.QGroupBox()
        self.basic_box.setStyleSheet("""
        QGroupBox
        {
            font-size: 16px;
            font-weight: bold;
        }
        """)
        self.basic_vlay = QtWidgets.QVBoxLayout()
        self.basic_box.setTitle(_("Basic Geo Parameters"))
        self.basic_box.setFixedWidth(250)

        self.advanced_box = QtWidgets.QGroupBox()
        self.advanced_box.setStyleSheet("""
                QGroupBox
                {
                    font-size: 16px;
                    font-weight: bold;
                }
                """)
        self.advanced_vlay = QtWidgets.QVBoxLayout()
        self.advanced_box.setTitle(_("Advanced Geo Parameters"))
        self.advanced_box.setFixedWidth(250)

        self.ncc_box = QtWidgets.QGroupBox()
        self.ncc_box.setStyleSheet("""
                        QGroupBox
                        {
                            font-size: 16px;
                            font-weight: bold;
                        }
                        """)
        self.ncc_vlay = QtWidgets.QVBoxLayout()
        self.ncc_box.setTitle(_("NCC Parameters"))
        self.ncc_box.setFixedWidth(250)

        self.paint_box = QtWidgets.QGroupBox()
        self.paint_box.setStyleSheet("""
                        QGroupBox
                        {
                            font-size: 16px;
                            font-weight: bold;
                        }
                        """)
        self.paint_vlay = QtWidgets.QVBoxLayout()
        self.paint_box.setTitle(_("Paint Parameters"))
        self.paint_box.setFixedWidth(250)

        self.basic_box.setLayout(self.basic_vlay)
        self.advanced_box.setLayout(self.advanced_vlay)
        self.ncc_box.setLayout(self.ncc_vlay)
        self.paint_box.setLayout(self.paint_vlay)

        geo_vlay = QtWidgets.QVBoxLayout()
        geo_vlay.addWidget(self.basic_box)
        geo_vlay.addWidget(self.advanced_box)
        geo_vlay.addStretch()

        tools_vlay = QtWidgets.QVBoxLayout()
        tools_vlay.addWidget(self.ncc_box)
        tools_vlay.addWidget(self.paint_box)
        tools_vlay.addStretch()

        param_hlay.addLayout(geo_vlay)
        param_hlay.addLayout(tools_vlay)
        param_hlay.addStretch()

        # ###########################################################################
        # ############### BASIC UI form #############################################
        # ###########################################################################

        self.grid0 = QtWidgets.QGridLayout()
        self.basic_vlay.addLayout(self.grid0)
        self.grid0.setColumnStretch(0, 0)
        self.grid0.setColumnStretch(1, 1)
        self.basic_vlay.addStretch()

        # Tool Name
        self.name_label = QtWidgets.QLabel('<span style="color:red;"><b>%s:</b></span>' % _('Tool Name'))
        self.name_label.setToolTip(
            _("Tool name.\n"
              "This is not used in the app, it's function\n"
              "is to serve as a note for the user."))

        self.name_entry = FCEntry()
        self.name_entry.setObjectName('gdb_name')

        self.grid0.addWidget(self.name_label, 0, 0)
        self.grid0.addWidget(self.name_entry, 0, 1)

        # Tool Dia
        self.dia_label = QtWidgets.QLabel('%s:' % _('Tool Dia'))
        self.dia_label.setToolTip(
            _("Tool Diameter."))

        self.dia_entry = FCDoubleSpinner()
        self.dia_entry.set_range(-9999.9999, 9999.9999)
        self.dia_entry.set_precision(self.decimals)
        self.dia_entry.setObjectName('gdb_dia')

        self.grid0.addWidget(self.dia_label, 1, 0)
        self.grid0.addWidget(self.dia_entry, 1, 1)

        # Tool Shape
        self.shape_label = QtWidgets.QLabel('%s:' % _('Tool Shape'))
        self.shape_label.setToolTip(
            _("Tool Shape. \n"
              "Can be:\n"
              "C1 ... C4 = circular tool with x flutes\n"
              "B = ball tip milling tool\n"
              "V = v-shape milling tool"))

        self.shape_combo = FCComboBox()
        self.shape_combo.addItems(["C1", "C2", "C3", "C4", "B", "V"])
        self.shape_combo.setObjectName('gdb_shape')

        self.grid0.addWidget(self.shape_label, 2, 0)
        self.grid0.addWidget(self.shape_combo, 2, 1)

        # Cut Z
        self.cutz_label = QtWidgets.QLabel('%s:' % _("Cut Z"))
        self.cutz_label.setToolTip(
            _("Cutting Depth.\n"
              "The depth at which to cut into material."))

        self.cutz_entry = FCDoubleSpinner()
        self.cutz_entry.set_range(-9999.9999, 9999.9999)
        self.cutz_entry.set_precision(self.decimals)
        self.cutz_entry.setObjectName('gdb_cutz')

        self.grid0.addWidget(self.cutz_label, 4, 0)
        self.grid0.addWidget(self.cutz_entry, 4, 1)

        # Multi Depth
        self.multidepth_label = QtWidgets.QLabel('%s:' % _("MultiDepth"))
        self.multidepth_label.setToolTip(
            _("Multi Depth.\n"
              "Selecting this will allow cutting in multiple passes,\n"
              "each pass adding a DPP parameter depth."))

        self.multidepth_cb = FCCheckBox()
        self.multidepth_cb.setObjectName('gdb_multidepth')

        self.grid0.addWidget(self.multidepth_label, 5, 0)
        self.grid0.addWidget(self.multidepth_cb, 5, 1)

        # Depth Per Pass
        self.dpp_label = QtWidgets.QLabel('%s:' % _("DPP"))
        self.dpp_label.setToolTip(
            _("DPP. Depth per Pass.\n"
              "The value used to cut into material on each pass."))

        self.multidepth_entry = FCDoubleSpinner()
        self.multidepth_entry.set_range(-9999.9999, 9999.9999)
        self.multidepth_entry.set_precision(self.decimals)
        self.multidepth_entry.setObjectName('gdb_multidepth_entry')

        self.grid0.addWidget(self.dpp_label, 7, 0)
        self.grid0.addWidget(self.multidepth_entry, 7, 1)

        # Travel Z
        self.travelz_label = QtWidgets.QLabel('%s:' % _("Travel Z"))
        self.travelz_label.setToolTip(
            _("Clearance Height.\n"
              "Height at which the milling bit will travel between cuts,\n"
              "above the surface of the material, avoiding all fixtures."))

        self.travelz_entry = FCDoubleSpinner()
        self.travelz_entry.set_range(-9999.9999, 9999.9999)
        self.travelz_entry.set_precision(self.decimals)
        self.travelz_entry.setObjectName('gdb_travel')

        self.grid0.addWidget(self.travelz_label, 9, 0)
        self.grid0.addWidget(self.travelz_entry, 9, 1)

        # Feedrate X-Y
        self.frxy_label = QtWidgets.QLabel('%s:' % _("Feedrate X-Y"))
        self.frxy_label.setToolTip(
            _("Feedrate X-Y. Feedrate\n"
              "The speed on XY plane used while cutting into material."))

        self.frxy_entry = FCDoubleSpinner()
        self.frxy_entry.set_range(-999999.9999, 999999.9999)
        self.frxy_entry.set_precision(self.decimals)
        self.frxy_entry.setObjectName('gdb_frxy')

        self.grid0.addWidget(self.frxy_label, 12, 0)
        self.grid0.addWidget(self.frxy_entry, 12, 1)

        # Feedrate Z
        self.frz_label = QtWidgets.QLabel('%s:' % _("Feedrate Z"))
        self.frz_label.setToolTip(
            _("Feedrate Z\n"
              "The speed on Z plane."))

        self.frz_entry = FCDoubleSpinner()
        self.frz_entry.set_range(-999999.9999, 999999.9999)
        self.frz_entry.set_precision(self.decimals)
        self.frz_entry.setObjectName('gdb_frz')

        self.grid0.addWidget(self.frz_label, 14, 0)
        self.grid0.addWidget(self.frz_entry, 14, 1)

        # Spindle Spped
        self.spindle_label = QtWidgets.QLabel('%s:' % _("Spindle Speed"))
        self.spindle_label.setToolTip(
            _("Spindle Speed.\n"
              "If it's left empty it will not be used.\n"
              "The speed of the spindle in RPM."))

        self.spindle_entry = FCDoubleSpinner()
        self.spindle_entry.set_range(-999999.9999, 999999.9999)
        self.spindle_entry.set_precision(self.decimals)
        self.spindle_entry.setObjectName('gdb_spindle')

        self.grid0.addWidget(self.spindle_label, 15, 0)
        self.grid0.addWidget(self.spindle_entry, 15, 1)

        # Dwell
        self.dwell_label = QtWidgets.QLabel('%s:' % _("Dwell"))
        self.dwell_label.setToolTip(
            _("Dwell.\n"
              "Check this if a delay is needed to allow\n"
              "the spindle motor to reach it's set speed."))

        self.dwell_cb = FCCheckBox()
        self.dwell_cb.setObjectName('gdb_dwell')

        self.grid0.addWidget(self.dwell_label, 16, 0)
        self.grid0.addWidget(self.dwell_cb, 16, 1)

        # Dwell Time
        self.dwelltime_label = QtWidgets.QLabel('%s:' % _("Dwelltime"))
        self.dwelltime_label.setToolTip(
            _("Dwell Time.\n"
              "A delay used to allow the motor spindle reach it's set speed."))

        self.dwelltime_entry = FCDoubleSpinner()
        self.dwelltime_entry.set_range(0.0000, 9999.9999)
        self.dwelltime_entry.set_precision(self.decimals)
        self.dwelltime_entry.setObjectName('gdb_dwelltime')

        self.grid0.addWidget(self.dwelltime_label, 17, 0)
        self.grid0.addWidget(self.dwelltime_entry, 17, 1)

        # ###########################################################################
        # ############### ADVANCED UI form ##########################################
        # ###########################################################################

        self.grid1 = QtWidgets.QGridLayout()
        self.advanced_vlay.addLayout(self.grid1)
        self.grid1.setColumnStretch(0, 0)
        self.grid1.setColumnStretch(1, 1)
        self.advanced_vlay.addStretch()

        # Tool Type
        self.type_label = QtWidgets.QLabel('%s:' % _("Tool Type"))
        self.type_label.setToolTip(
            _("Tool Type.\n"
              "Can be:\n"
              "Iso = isolation cut\n"
              "Rough = rough cut, low feedrate, multiple passes\n"
              "Finish = finishing cut, high feedrate"))

        self.type_combo = FCComboBox()
        self.type_combo.addItems(["Iso", "Rough", "Finish"])
        self.type_combo.setObjectName('gdb_type')

        self.grid1.addWidget(self.type_label, 0, 0)
        self.grid1.addWidget(self.type_combo, 0, 1)

        # Tool Offset
        self.tooloffset_label = QtWidgets.QLabel('%s:' % _('Tool Offset'))
        self.tooloffset_label.setToolTip(
            _("Tool Offset.\n"
              "Can be of a few types:\n"
              "Path = zero offset\n"
              "In = offset inside by half of tool diameter\n"
              "Out = offset outside by half of tool diameter\n"
              "Custom = custom offset using the Custom Offset value"))

        self.tooloffset_combo = FCComboBox()
        self.tooloffset_combo.addItems(["Path", "In", "Out", "Custom"])
        self.tooloffset_combo.setObjectName('gdb_tool_offset')

        self.grid1.addWidget(self.tooloffset_label, 2, 0)
        self.grid1.addWidget(self.tooloffset_combo, 2, 1)

        # Custom Offset
        self.custom_offset_label = QtWidgets.QLabel('%s:' % _("Custom Offset"))
        self.custom_offset_label.setToolTip(
            _("Custom Offset.\n"
              "A value to be used as offset from the current path."))

        self.custom_offset_entry = FCDoubleSpinner()
        self.custom_offset_entry.set_range(-9999.9999, 9999.9999)
        self.custom_offset_entry.set_precision(self.decimals)
        self.custom_offset_entry.setObjectName('gdb_custom_offset')

        self.grid1.addWidget(self.custom_offset_label, 5, 0)
        self.grid1.addWidget(self.custom_offset_entry, 5, 1)

        # V-Dia
        self.vdia_label = QtWidgets.QLabel('%s:' % _("V-Dia"))
        self.vdia_label.setToolTip(
            _("V-Dia.\n"
              "Diameter of the tip for V-Shape Tools."))

        self.vdia_entry = FCDoubleSpinner()
        self.vdia_entry.set_range(0.0000, 9999.9999)
        self.vdia_entry.set_precision(self.decimals)
        self.vdia_entry.setObjectName('gdb_vdia')

        self.grid1.addWidget(self.vdia_label, 7, 0)
        self.grid1.addWidget(self.vdia_entry, 7, 1)

        # V-Angle
        self.vangle_label = QtWidgets.QLabel('%s:' % _("V-Angle"))
        self.vangle_label.setToolTip(
            _("V-Agle.\n"
              "Angle at the tip for the V-Shape Tools."))

        self.vangle_entry = FCDoubleSpinner()
        self.vangle_entry.set_range(-360.0, 360.0)
        self.vangle_entry.set_precision(self.decimals)
        self.vangle_entry.setObjectName('gdb_vangle')

        self.grid1.addWidget(self.vangle_label, 8, 0)
        self.grid1.addWidget(self.vangle_entry, 8, 1)

        # Feedrate Rapids
        self.frapids_label = QtWidgets.QLabel('%s:' % _("FR Rapids"))
        self.frapids_label.setToolTip(
            _("FR Rapids. Feedrate Rapids\n"
              "Speed used while moving as fast as possible.\n"
              "This is used only by some devices that can't use\n"
              "the G0 g-code command. Mostly 3D printers."))

        self.frapids_entry = FCDoubleSpinner()
        self.frapids_entry.set_range(0.0000, 9999.9999)
        self.frapids_entry.set_precision(self.decimals)
        self.frapids_entry.setObjectName('gdb_frapids')

        self.grid1.addWidget(self.frapids_label, 10, 0)
        self.grid1.addWidget(self.frapids_entry, 10, 1)

        # Extra Cut
        self.ecut_label = QtWidgets.QLabel('%s:' % _("ExtraCut"))
        self.ecut_label.setToolTip(
            _("Extra Cut.\n"
              "If checked, after a isolation is finished an extra cut\n"
              "will be added where the start and end of isolation meet\n"
              "such as that this point is covered by this extra cut to\n"
              "ensure a complete isolation."))

        self.ecut_cb = FCCheckBox()
        self.ecut_cb.setObjectName('gdb_ecut')

        self.grid1.addWidget(self.ecut_label, 12, 0)
        self.grid1.addWidget(self.ecut_cb, 12, 1)

        # Extra Cut Length
        self.ecut_length_label = QtWidgets.QLabel('%s:' % _("E-Cut Length"))
        self.ecut_length_label.setToolTip(
            _("Extra Cut length.\n"
              "If checked, after a isolation is finished an extra cut\n"
              "will be added where the start and end of isolation meet\n"
              "such as that this point is covered by this extra cut to\n"
              "ensure a complete isolation. This is the length of\n"
              "the extra cut."))

        self.ecut_length_entry = FCDoubleSpinner()
        self.ecut_length_entry.set_range(0.0000, 9999.9999)
        self.ecut_length_entry.set_precision(self.decimals)
        self.ecut_length_entry.setObjectName('gdb_ecut_length')

        self.grid1.addWidget(self.ecut_length_label, 13, 0)
        self.grid1.addWidget(self.ecut_length_entry, 13, 1)

        # ###########################################################################
        # ############### NCC UI form ###############################################
        # ###########################################################################

        self.grid2 = QtWidgets.QGridLayout()
        self.ncc_vlay.addLayout(self.grid2)
        self.grid2.setColumnStretch(0, 0)
        self.grid2.setColumnStretch(1, 1)
        self.ncc_vlay.addStretch()

        # Operation
        op_label = QtWidgets.QLabel('%s:' % _('Operation'))
        op_label.setToolTip(
            _("The 'Operation' can be:\n"
              "- Isolation -> will ensure that the non-copper clearing is always complete.\n"
              "If it's not successful then the non-copper clearing will fail, too.\n"
              "- Clear -> the regular non-copper clearing.")
        )

        self.op_radio = RadioSet([
            {"label": _("Clear"), "value": "clear"},
            {"label": _("Isolation"), "value": "iso"}
        ], orientation='horizontal', stretch=False)
        self.op_radio.setObjectName("gdb_n_operation")

        self.grid2.addWidget(op_label, 13, 0)
        self.grid2.addWidget(self.op_radio, 13, 1)

        # Milling Type Radio Button
        self.milling_type_label = QtWidgets.QLabel('%s:' % _('Milling Type'))
        self.milling_type_label.setToolTip(
            _("Milling type when the selected tool is of type: 'iso_op':\n"
              "- climb / best for precision milling and to reduce tool usage\n"
              "- conventional / useful when there is no backlash compensation")
        )

        self.milling_type_radio = RadioSet([{'label': _('Climb'), 'value': 'cl'},
                                            {'label': _('Conventional'), 'value': 'cv'}])
        self.milling_type_radio.setToolTip(
            _("Milling type when the selected tool is of type: 'iso_op':\n"
              "- climb / best for precision milling and to reduce tool usage\n"
              "- conventional / useful when there is no backlash compensation")
        )
        self.milling_type_radio.setObjectName("gdb_n_milling_type")

        self.grid2.addWidget(self.milling_type_label, 14, 0)
        self.grid2.addWidget(self.milling_type_radio, 14, 1)

        # Overlap Entry
        nccoverlabel = QtWidgets.QLabel('%s:' % _('Overlap'))
        nccoverlabel.setToolTip(
            _("How much (percentage) of the tool width to overlap each tool pass.\n"
              "Adjust the value starting with lower values\n"
              "and increasing it if areas that should be cleared are still \n"
              "not cleared.\n"
              "Lower values = faster processing, faster execution on CNC.\n"
              "Higher values = slow processing and slow execution on CNC\n"
              "due of too many paths.")
        )
        self.ncc_overlap_entry = FCDoubleSpinner(suffix='%')
        self.ncc_overlap_entry.set_precision(self.decimals)
        self.ncc_overlap_entry.setWrapping(True)
        self.ncc_overlap_entry.setRange(0.000, 99.9999)
        self.ncc_overlap_entry.setSingleStep(0.1)
        self.ncc_overlap_entry.setObjectName("gdb_n_overlap")

        self.grid2.addWidget(nccoverlabel, 15, 0)
        self.grid2.addWidget(self.ncc_overlap_entry, 15, 1)

        # Margin
        nccmarginlabel = QtWidgets.QLabel('%s:' % _('Margin'))
        nccmarginlabel.setToolTip(
            _("Bounding box margin.")
        )
        self.ncc_margin_entry = FCDoubleSpinner()
        self.ncc_margin_entry.set_precision(self.decimals)
        self.ncc_margin_entry.set_range(-9999.9999, 9999.9999)
        self.ncc_margin_entry.setObjectName("gdb_n_margin")

        self.grid2.addWidget(nccmarginlabel, 16, 0)
        self.grid2.addWidget(self.ncc_margin_entry, 16, 1)

        # Method
        methodlabel = QtWidgets.QLabel('%s:' % _('Method'))
        methodlabel.setToolTip(
            _("Algorithm for copper clearing:\n"
              "- Standard: Fixed step inwards.\n"
              "- Seed-based: Outwards from seed.\n"
              "- Line-based: Parallel lines.")
        )

        self.ncc_method_combo = FCComboBox()
        self.ncc_method_combo.addItems(
            [_("Standard"), _("Seed"), _("Lines")]
        )
        self.ncc_method_combo.setObjectName("gdb_n_method")

        self.grid2.addWidget(methodlabel, 17, 0)
        self.grid2.addWidget(self.ncc_method_combo, 17, 1)

        # Connect lines
        self.ncc_connect_cb = FCCheckBox('%s' % _("Connect"))
        self.ncc_connect_cb.setObjectName("gdb_n_connect")

        self.ncc_connect_cb.setToolTip(
            _("Draw lines between resulting\n"
              "segments to minimize tool lifts.")
        )
        self.grid2.addWidget(self.ncc_connect_cb, 18, 0)

        # Contour
        self.ncc_contour_cb = FCCheckBox('%s' % _("Contour"))
        self.ncc_contour_cb.setObjectName("gdb_n_contour")

        self.ncc_contour_cb.setToolTip(
            _("Cut around the perimeter of the polygon\n"
              "to trim rough edges.")
        )
        self.grid2.addWidget(self.ncc_contour_cb, 18, 1)

        # ## NCC Offset choice
        self.ncc_choice_offset_cb = FCCheckBox('%s' % _("Offset"))
        self.ncc_choice_offset_cb.setObjectName("gdb_n_offset")

        self.ncc_choice_offset_cb.setToolTip(
            _("If used, it will add an offset to the copper features.\n"
              "The copper clearing will finish to a distance\n"
              "from the copper features.\n"
              "The value can be between 0 and 10 FlatCAM units.")
        )
        self.grid2.addWidget(self.ncc_choice_offset_cb, 19, 0)

        # ## NCC Offset Entry
        self.ncc_offset_spinner = FCDoubleSpinner()
        self.ncc_offset_spinner.set_range(0.00, 10.00)
        self.ncc_offset_spinner.set_precision(4)
        self.ncc_offset_spinner.setWrapping(True)
        self.ncc_offset_spinner.setObjectName("gdb_n_offset_value")

        units = self.app.defaults['units'].upper()
        if units == 'MM':
            self.ncc_offset_spinner.setSingleStep(0.1)
        else:
            self.ncc_offset_spinner.setSingleStep(0.01)

        self.grid2.addWidget(self.ncc_offset_spinner, 19, 1)

        # ###########################################################################
        # ############### Paint UI form #############################################
        # ###########################################################################

        self.grid3 = QtWidgets.QGridLayout()
        self.paint_vlay.addLayout(self.grid3)
        self.grid3.setColumnStretch(0, 0)
        self.grid3.setColumnStretch(1, 1)
        self.paint_vlay.addStretch()

        # Overlap
        ovlabel = QtWidgets.QLabel('%s:' % _('Overlap'))
        ovlabel.setToolTip(
            _("How much (percentage) of the tool width to overlap each tool pass.\n"
              "Adjust the value starting with lower values\n"
              "and increasing it if areas that should be painted are still \n"
              "not painted.\n"
              "Lower values = faster processing, faster execution on CNC.\n"
              "Higher values = slow processing and slow execution on CNC\n"
              "due of too many paths.")
        )
        self.paintoverlap_entry = FCDoubleSpinner(suffix='%')
        self.paintoverlap_entry.set_precision(3)
        self.paintoverlap_entry.setWrapping(True)
        self.paintoverlap_entry.setRange(0.0000, 99.9999)
        self.paintoverlap_entry.setSingleStep(0.1)
        self.paintoverlap_entry.setObjectName('gdb_p_overlap')

        self.grid3.addWidget(ovlabel, 1, 0)
        self.grid3.addWidget(self.paintoverlap_entry, 1, 1)

        # Margin
        marginlabel = QtWidgets.QLabel('%s:' % _('Margin'))
        marginlabel.setToolTip(
            _("Distance by which to avoid\n"
              "the edges of the polygon to\n"
              "be painted.")
        )
        self.paintmargin_entry = FCDoubleSpinner()
        self.paintmargin_entry.set_precision(self.decimals)
        self.paintmargin_entry.set_range(-9999.9999, 9999.9999)
        self.paintmargin_entry.setObjectName('gdb_p_margin')

        self.grid3.addWidget(marginlabel, 2, 0)
        self.grid3.addWidget(self.paintmargin_entry, 2, 1)

        # Method
        methodlabel = QtWidgets.QLabel('%s:' % _('Method'))
        methodlabel.setToolTip(
            _("Algorithm for painting:\n"
              "- Standard: Fixed step inwards.\n"
              "- Seed-based: Outwards from seed.\n"
              "- Line-based: Parallel lines.\n"
              "- Laser-lines: Active only for Gerber objects.\n"
              "Will create lines that follow the traces.\n"
              "- Combo: In case of failure a new method will be picked from the above\n"
              "in the order specified.")
        )

        self.paintmethod_combo = FCComboBox()
        self.paintmethod_combo.addItems(
            [_("Standard"), _("Seed"), _("Lines"), _("Laser_lines"), _("Combo")]
        )
        idx = self.paintmethod_combo.findText(_("Laser_lines"))
        self.paintmethod_combo.model().item(idx).setEnabled(False)

        self.paintmethod_combo.setObjectName('gdb_p_method')

        self.grid3.addWidget(methodlabel, 7, 0)
        self.grid3.addWidget(self.paintmethod_combo, 7, 1)

        # Connect lines
        self.pathconnect_cb = FCCheckBox('%s' % _("Connect"))
        self.pathconnect_cb.setObjectName('gdb_p_connect')
        self.pathconnect_cb.setToolTip(
            _("Draw lines between resulting\n"
              "segments to minimize tool lifts.")
        )

        self.paintcontour_cb = FCCheckBox('%s' % _("Contour"))
        self.paintcontour_cb.setObjectName('gdb_p_contour')
        self.paintcontour_cb.setToolTip(
            _("Cut around the perimeter of the polygon\n"
              "to trim rough edges.")
        )

        self.grid3.addWidget(self.pathconnect_cb, 10, 0)
        self.grid3.addWidget(self.paintcontour_cb, 10, 1)

        # ####################################################################
        # ####################################################################
        # GUI for the lower part of the window
        # ####################################################################
        # ####################################################################

        new_vlay = QtWidgets.QVBoxLayout()
        grid_layout.addLayout(new_vlay, 1, 0, 1, 2)

        self.buttons_frame = QtWidgets.QFrame()
        self.buttons_frame.setContentsMargins(0, 0, 0, 0)
        new_vlay.addWidget(self.buttons_frame)
        self.buttons_box = QtWidgets.QHBoxLayout()
        self.buttons_box.setContentsMargins(0, 0, 0, 0)
        self.buttons_frame.setLayout(self.buttons_box)
        self.buttons_frame.show()

        add_entry_btn = FCButton(_("Add Tool in DB"))
        add_entry_btn.setToolTip(
            _("Add a new tool in the Tools Database.\n"
              "It will be used in the Geometry UI.\n"
              "You can edit it after it is added.")
        )
        self.buttons_box.addWidget(add_entry_btn)

        # add_fct_entry_btn = FCButton(_("Add Paint/NCC Tool in DB"))
        # add_fct_entry_btn.setToolTip(
        #     _("Add a new tool in the Tools Database.\n"
        #       "It will be used in the Paint/NCC Tools UI.\n"
        #       "You can edit it after it is added.")
        # )
        # self.buttons_box.addWidget(add_fct_entry_btn)

        remove_entry_btn = FCButton(_("Delete Tool from DB"))
        remove_entry_btn.setToolTip(
            _("Remove a selection of tools in the Tools Database.")
        )
        self.buttons_box.addWidget(remove_entry_btn)

        export_db_btn = FCButton(_("Export DB"))
        export_db_btn.setToolTip(
            _("Save the Tools Database to a custom text file.")
        )
        self.buttons_box.addWidget(export_db_btn)

        import_db_btn = FCButton(_("Import DB"))
        import_db_btn.setToolTip(
            _("Load the Tools Database information's from a custom text file.")
        )
        self.buttons_box.addWidget(import_db_btn)

        self.add_tool_from_db = FCButton(_("Add Tool from Tools DB"))
        self.add_tool_from_db.setToolTip(
            _("Add a new tool in the Tools Table of the\n"
              "active Geometry object after selecting a tool\n"
              "in the Tools Database.")
        )
        self.add_tool_from_db.hide()

        self.cancel_tool_from_db = FCButton(_("Cancel"))
        self.cancel_tool_from_db.hide()

        hlay = QtWidgets.QHBoxLayout()
        tree_layout.addLayout(hlay)
        hlay.addWidget(self.add_tool_from_db)
        hlay.addWidget(self.cancel_tool_from_db)
        hlay.addStretch()

        # ##############################################################################
        # ##############################################################################
        # ########## SETUP THE DICTIONARIES THAT HOLD THE WIDGETS #####################
        # ##############################################################################
        # ##############################################################################

        self.form_fields = {
            # Basic
            "name":             self.name_entry,
            "tooldia":          self.dia_entry,
            "tool_type":        self.shape_combo,
            "cutz":             self.cutz_entry,
            "multidepth":       self.multidepth_cb,
            "depthperpass":     self.multidepth_entry,
            "travelz":          self.travelz_entry,
            "feedrate":         self.frxy_entry,
            "feedrate_z":       self.frz_entry,
            "spindlespeed":     self.spindle_entry,
            "dwell":            self.dwell_cb,
            "dwelltime":        self.dwelltime_entry,

            # Advanced
            "type":             self.type_combo,
            "offset":           self.tooloffset_combo,
            "offset_value":     self.custom_offset_entry,
            "vtipdia":          self.vdia_entry,
            "vtipangle":        self.vangle_entry,
            "feedrate_rapid":   self.frapids_entry,
            "extracut":         self.ecut_cb,
            "extracut_length":  self.ecut_length_entry,

            # NCC
            "tools_nccoperation":       self.op_radio,
            "tools_nccmilling_type":    self.milling_type_radio,
            "tools_nccoverlap":         self.ncc_overlap_entry,
            "tools_nccmargin":          self.ncc_margin_entry,
            "tools_nccmethod":          self.ncc_method_combo,
            "tools_nccconnect":         self.ncc_connect_cb,
            "tools_ncccontour":         self.ncc_contour_cb,
            "tools_ncc_offset_choice":  self.ncc_choice_offset_cb,
            "tools_ncc_offset_value":   self.ncc_offset_spinner,

            # Paint
            "tools_paintoverlap":       self.paintoverlap_entry,
            "tools_paintmargin":        self.paintmargin_entry,
            "tools_paintmethod":        self.paintmethod_combo,
            "tools_pathconnect":        self.pathconnect_cb,
            "tools_paintcontour":       self.paintcontour_cb,
        }

        self.name2option = {
            # Basic
            "gdb_name":             "name",
            "gdb_dia":              "tooldia",
            "gdb_shape":            "tool_type",
            "gdb_cutz":             "cutz",
            "gdb_multidepth":       "multidepth",
            "gdb_multidepth_entry": "depthperpass",
            "gdb_travel":           "travelz",
            "gdb_frxy":             "feedrate",
            "gdb_frz":              "feedrate_z",
            "gdb_spindle":          "spindlespeed",
            "gdb_dwell":            "dwell",
            "gdb_dwelltime":        "dwelltime",

            # Advanced
            "gdb_type":             "type",
            "gdb_tool_offset":      "offset",
            "gdb_custom_offset":    "offset_value",
            "gdb_vdia":             "vtipdia",
            "gdb_vangle":           "vtipangle",
            "gdb_frapids":          "feedrate_rapid",
            "gdb_ecut":             "extracut",
            "gdb_ecut_length":      "extracut_length",

            # NCC
            "gdb_n_operation":      "tools_nccoperation",
            "gdb_n_overlap":        "tools_nccoverlap",
            "gdb_n_margin":         "tools_nccmargin",
            "gdb_n_method":         "tools_nccmethod",
            "gdb_n_connect":        "tools_nccconnect",
            "gdb_n_contour":        "tools_ncccontour",
            "gdb_n_offset":         "tools_ncc_offset_choice",
            "gdb_n_offset_value":   "tools_ncc_offset_value",
            "gdb_n_milling_type":   "tools_nccmilling_type",

            # Paint
            'gdb_p_overlap':        "tools_paintoverlap",
            'gdb_p_margin':         "tools_paintmargin",
            'gdb_p_method':         "tools_paintmethod",
            'gdb_p_connect':        "tools_pathconnect",
            'gdb_p_contour':        "tools_paintcontour",
        }

        self.current_toolid = None

        # variable to show if double clicking and item will trigger adding a tool from DB
        self.ok_to_add = False

        # ##############################################################################
        # ######################## SIGNALS #############################################
        # ##############################################################################

        add_entry_btn.clicked.connect(self.on_tool_add)
        remove_entry_btn.clicked.connect(self.on_tool_delete)
        export_db_btn.clicked.connect(self.on_export_tools_db_file)
        import_db_btn.clicked.connect(self.on_import_tools_db_file)
        # closebtn.clicked.connect(self.accept)

        self.add_tool_from_db.clicked.connect(self.on_tool_requested_from_app)
        self.cancel_tool_from_db.clicked.connect(self.on_cancel_tool)

        # self.tree_widget.selectionModel().selectionChanged.connect(self.on_list_selection_change)
        self.tree_widget.currentItemChanged.connect(self.on_list_selection_change)
        self.tree_widget.itemChanged.connect(self.on_list_item_edited)
        self.tree_widget.customContextMenuRequested.connect(self.on_menu_request)

        self.tree_widget.itemDoubleClicked.connect(self.on_item_double_clicked)

        self.setup_db_ui()

    def on_menu_request(self, pos):

        menu = QtWidgets.QMenu()
        add_tool = menu.addAction(QtGui.QIcon(self.app.resource_location + '/plus16.png'), _("Add to DB"))
        add_tool.triggered.connect(self.on_tool_add)

        copy_tool = menu.addAction(QtGui.QIcon(self.app.resource_location + '/copy16.png'), _("Copy from DB"))
        copy_tool.triggered.connect(self.on_tool_copy)

        delete_tool = menu.addAction(QtGui.QIcon(self.app.resource_location + '/delete32.png'), _("Delete from DB"))
        delete_tool.triggered.connect(self.on_tool_delete)

        # tree_item = self.tree_widget.itemAt(pos)
        menu.exec(self.tree_widget.viewport().mapToGlobal(pos))

    def on_item_double_clicked(self, item, column):
        if column == 0 and self.ok_to_add is True:
            self.ok_to_add = False
            self.on_tool_requested_from_app()

    def on_list_selection_change(self, current, previous):
        # for idx in current.indexes():
        #     print(idx.data())
        # print(current.text(0))
        self.current_toolid = int(current.text(0))

        self.storage_to_form(self.db_tool_dict[current.text(0)])

    def on_list_item_edited(self, item, column):
        if column == 0:
            return

        self.name_entry.set_value(item.text(1))

    def storage_to_form(self, dict_storage):
        for form_key in self.form_fields:
            for storage_key in dict_storage:
                if form_key == storage_key:
                    try:
                        self.form_fields[form_key].set_value(dict_storage[form_key])
                    except Exception as e:
                        print(str(e))
                if storage_key == 'data':
                    for data_key in dict_storage[storage_key]:
                        if form_key == data_key:
                            try:
                                self.form_fields[form_key].set_value(dict_storage['data'][data_key])
                            except Exception as e:
                                print(str(e))

    def form_to_storage(self, tool):
        self.blockSignals(True)

        widget_changed = self.sender()
        wdg_objname = widget_changed.objectName()
        option_changed = self.name2option[wdg_objname]

        tooluid_item = int(tool)

        for tooluid_key, tooluid_val in self.db_tool_dict.items():
            if int(tooluid_key) == tooluid_item:
                new_option_value = self.form_fields[option_changed].get_value()
                if option_changed in tooluid_val:
                    tooluid_val[option_changed] = new_option_value
                if option_changed in tooluid_val['data']:
                    tooluid_val['data'][option_changed] = new_option_value

        self.blockSignals(False)

    def setup_db_ui(self):
        filename = self.app.data_path + '/geo_tools_db.FlatDB'

        # load the database tools from the file
        try:
            with open(filename) as f:
                tools = f.read()
        except IOError:
            self.app.log.error("Could not load tools DB file.")
            self.app.inform.emit('[ERROR] %s' % _("Could not load Tools DB file."))
            return

        try:
            self.db_tool_dict = json.loads(tools)
        except Exception:
            e = sys.exc_info()[0]
            self.app.log.error(str(e))
            self.app.inform.emit('[ERROR] %s' % _("Failed to parse Tools DB file."))
            return

        self.app.inform.emit('[success] %s: %s' % (_("Loaded FlatCAM Tools DB from"), filename))

        self.build_db_ui()

    def build_db_ui(self):
        self.ui_disconnect()
        nr_crt = 0

        parent = self.tree_widget
        self.tree_widget.blockSignals(True)
        self.tree_widget.clear()
        self.tree_widget.blockSignals(False)

        for toolid, dict_val in self.db_tool_dict.items():
            row = nr_crt
            nr_crt += 1

            t_name = dict_val['name']
            try:
                # self.add_tool_table_line(row, name=t_name, tooldict=dict_val)
                self.tree_widget.blockSignals(True)
                try:
                    self.tree_widget.addParentEditable(parent=parent, title=[str(row+1), t_name], editable=True)
                except Exception as e:
                    print('FlatCAMCoomn.ToolDB2.build_db_ui() -> ', str(e))
                self.tree_widget.blockSignals(False)
            except Exception as e:
                self.app.log.debug("ToolDB.build_db_ui.add_tool_table_line() --> %s" % str(e))

        if self.current_toolid is None or self.current_toolid < 1:
            if self.db_tool_dict:
                self.storage_to_form(self.db_tool_dict['1'])

                # Enable GUI
                self.basic_box.setEnabled(True)
                self.advanced_box.setEnabled(True)
                self.ncc_box.setEnabled(True)
                self.paint_box.setEnabled(True)

                self.tree_widget.setCurrentItem(self.tree_widget.topLevelItem(0))
                # self.tree_widget.setFocus()

            else:
                # Disable GUI
                self.basic_box.setEnabled(False)
                self.advanced_box.setEnabled(False)
                self.ncc_box.setEnabled(False)
                self.paint_box.setEnabled(False)
        else:
            self.storage_to_form(self.db_tool_dict[str(self.current_toolid)])

        self.ui_connect()

    def on_tool_add(self):
        """
        Add a tool in the DB Tool Table
        :return: None
        """

        default_data = {}
        default_data.update({
            "plot":             True,
            "cutz":             float(self.app.defaults["geometry_cutz"]),
            "multidepth":       self.app.defaults["geometry_multidepth"],
            "depthperpass":     float(self.app.defaults["geometry_depthperpass"]),
            "vtipdia":          float(self.app.defaults["geometry_vtipdia"]),
            "vtipangle":        float(self.app.defaults["geometry_vtipangle"]),
            "travelz":          float(self.app.defaults["geometry_travelz"]),
            "feedrate":         float(self.app.defaults["geometry_feedrate"]),
            "feedrate_z":       float(self.app.defaults["geometry_feedrate_z"]),
            "feedrate_rapid":   float(self.app.defaults["geometry_feedrate_rapid"]),
            "spindlespeed":     self.app.defaults["geometry_spindlespeed"],
            "dwell":            self.app.defaults["geometry_dwell"],
            "dwelltime":        float(self.app.defaults["geometry_dwelltime"]),
            "ppname_g":         self.app.defaults["geometry_ppname_g"],
            "extracut":         self.app.defaults["geometry_extracut"],
            "extracut_length":  float(self.app.defaults["geometry_extracut_length"]),
            "toolchange":       self.app.defaults["geometry_toolchange"],
            "toolchangexy":     self.app.defaults["geometry_toolchangexy"],
            "toolchangez":      float(self.app.defaults["geometry_toolchangez"]),
            "startz":           self.app.defaults["geometry_startz"],
            "endz":             float(self.app.defaults["geometry_endz"]),

            # NCC
            "tools_nccoperation":       self.app.defaults["tools_nccoperation"],
            "tools_nccmilling_type":    self.app.defaults["tools_nccmilling_type"],
            "tools_nccoverlap":         float(self.app.defaults["tools_nccoverlap"]),
            "tools_nccmargin":          float(self.app.defaults["tools_nccmargin"]),
            "tools_nccmethod":          self.app.defaults["tools_nccmethod"],
            "tools_nccconnect":         self.app.defaults["tools_nccconnect"],
            "tools_ncccontour":         self.app.defaults["tools_ncccontour"],
            "tools_ncc_offset_choice":  self.app.defaults["tools_ncc_offset_choice"],
            "tools_ncc_offset_value":   float(self.app.defaults["tools_ncc_offset_value"]),

            # Paint
            "tools_paintoverlap":       float(self.app.defaults["tools_paintoverlap"]),
            "tools_paintmargin":        float(self.app.defaults["tools_paintmargin"]),
            "tools_paintmethod":        self.app.defaults["tools_paintmethod"],
            "tools_pathconnect":        self.app.defaults["tools_pathconnect"],
            "tools_paintcontour":       self.app.defaults["tools_paintcontour"],
        })

        dict_elem = {}
        dict_elem['name'] = 'new_tool'
        if type(self.app.defaults["geometry_cnctooldia"]) == float:
            dict_elem['tooldia'] = self.app.defaults["geometry_cnctooldia"]
        else:
            try:
                tools_string = self.app.defaults["geometry_cnctooldia"].split(",")
                tools_diameters = [eval(a) for a in tools_string if a != '']
                dict_elem['tooldia'] = tools_diameters[0] if tools_diameters else 0.0
            except Exception as e:
                self.app.log.debug("ToolDB.on_tool_add() --> %s" % str(e))
                return

        dict_elem['offset'] = 'Path'
        dict_elem['offset_value'] = 0.0
        dict_elem['type'] = 'Rough'
        dict_elem['tool_type'] = 'C1'
        dict_elem['data'] = default_data

        new_toolid = len(self.db_tool_dict) + 1
        self.db_tool_dict[str(new_toolid)] = deepcopy(dict_elem)

        # add the new entry to the Tools DB table
        self.update_storage()
        self.build_db_ui()
        self.app.inform.emit('[success] %s' % _("Tool added to DB."))

    def on_tool_copy(self):
        """
        Copy a selection of Tools in the Tools DB table
        :return:
        """
        new_tool_id = len(self.db_tool_dict)
        for item in self.tree_widget.selectedItems():
            old_tool_id = item.data(0, QtCore.Qt.DisplayRole)

            for toolid, dict_val in list(self.db_tool_dict.items()):
                if int(old_tool_id) == int(toolid):
                    new_tool_id += 1
                    new_key = str(new_tool_id)

                    self.db_tool_dict.update({
                        new_key: deepcopy(dict_val)
                    })

        self.current_toolid = new_tool_id

        self.update_storage()
        self.build_db_ui()
        self.app.inform.emit('[success] %s' % _("Tool copied from Tools DB."))

    def on_tool_delete(self):
        """
        Delete a selection of Tools in the Tools DB table
        :return:
        """
        for item in self.tree_widget.selectedItems():
            toolname_to_remove = item.data(0, QtCore.Qt.DisplayRole)

            for toolid, dict_val in list(self.db_tool_dict.items()):
                if int(toolname_to_remove) == int(toolid):
                    # remove from the storage
                    self.db_tool_dict.pop(toolid, None)

        self.current_toolid -= 1

        self.update_storage()
        self.build_db_ui()
        self.app.inform.emit('[success] %s' % _("Tool removed from Tools DB."))

    def on_export_tools_db_file(self):
        self.app.report_usage("on_export_tools_db_file")
        self.app.log.debug("on_export_tools_db_file()")

        date = str(datetime.today()).rpartition('.')[0]
        date = ''.join(c for c in date if c not in ':-')
        date = date.replace(' ', '_')

        filter__ = "Text File (*.TXT);;All Files (*.*)"
        filename, _f = FCFileSaveDialog.get_saved_filename( caption=_("Export Tools Database"),
                                                             directory='{l_save}/FlatCAM_{n}_{date}'.format(
                                                                 l_save=str(self.app.get_last_save_folder()),
                                                                 n=_("Tools_Database"),
                                                                 date=date),
                                                             filter=filter__)

        filename = str(filename)

        if filename == "":
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled."))
            return
        else:
            try:
                f = open(filename, 'w')
                f.close()
            except PermissionError:
                self.app.inform.emit('[WARNING] %s' %
                                     _("Permission denied, saving not possible.\n"
                                       "Most likely another app is holding the file open and not accessible."))
                return
            except IOError:
                self.app.log.debug('Creating a new Tools DB file ...')
                f = open(filename, 'w')
                f.close()
            except Exception:
                e = sys.exc_info()[0]
                self.app.log.error("Could not load Tools DB file.")
                self.app.log.error(str(e))
                self.app.inform.emit('[ERROR_NOTCL] %s' % _("Could not load Tools DB file."))
                return

            # Save update options
            try:
                # Save Tools DB in a file
                try:
                    with open(filename, "w") as f:
                        json.dump(self.db_tool_dict, f, default=to_dict, indent=2)
                except Exception as e:
                    self.app.log.debug("App.on_save_tools_db() --> %s" % str(e))
                    self.inform.emit('[ERROR_NOTCL] %s' % _("Failed to write Tools DB to file."))
                    return
            except Exception:
                self.app.inform.emit('[ERROR_NOTCL] %s' % _("Failed to write Tools DB to file."))
                return

        self.app.inform.emit('[success] %s: %s' % (_("Exported Tools DB to"), filename))

    def on_import_tools_db_file(self):
        self.app.report_usage("on_import_tools_db_file")
        self.app.log.debug("on_import_tools_db_file()")

        filter__ = "Text File (*.TXT);;All Files (*.*)"
        filename, _f = QtWidgets.QFileDialog.getOpenFileName(caption=_("Import FlatCAM Tools DB"), filter=filter__)

        if filename == "":
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled."))
        else:
            try:
                with open(filename) as f:
                    tools_in_db = f.read()
            except IOError:
                self.app.log.error("Could not load Tools DB file.")
                self.app.inform.emit('[ERROR_NOTCL] %s' % _("Could not load Tools DB file."))
                return

            try:
                self.db_tool_dict = json.loads(tools_in_db)
            except Exception:
                e = sys.exc_info()[0]
                self.app.log.error(str(e))
                self.app.inform.emit('[ERROR] %s' % _("Failed to parse Tools DB file."))
                return

            self.app.inform.emit('[success] %s: %s' % (_("Loaded FlatCAM Tools DB from"), filename))
            self.build_db_ui()
            self.update_storage()

    def on_save_tools_db(self, silent=False):
        self.app.log.debug("ToolsDB.on_save_button() --> Saving Tools Database to file.")

        filename = self.app.data_path + "/geo_tools_db.FlatDB"

        # Preferences save, update the color of the Tools DB Tab text
        for idx in range(self.app.ui.plot_tab_area.count()):
            if self.app.ui.plot_tab_area.tabText(idx) == _("Tools Database"):
                self.app.ui.plot_tab_area.tabBar.setTabTextColor(idx, QtGui.QColor('black'))

                # Save Tools DB in a file
                try:
                    f = open(filename, "w")
                    json.dump(self.db_tool_dict, f, default=to_dict, indent=2)
                    f.close()
                except Exception as e:
                    self.app.log.debug("ToolsDB.on_save_tools_db() --> %s" % str(e))
                    self.app.inform.emit('[ERROR_NOTCL] %s' % _("Failed to write Tools DB to file."))
                    return

                if not silent:
                    self.app.inform.emit('[success] %s' % _("Saved Tools DB."))

    def ui_connect(self):
        # make sure that we don't make multiple connections to the widgets
        self.ui_disconnect()

        self.name_entry.editingFinished.connect(self.update_tree_name)

        for key in self.form_fields:
            wdg = self.form_fields[key]

            # FCEntry
            if isinstance(wdg, FCEntry):
                wdg.textChanged.connect(self.update_storage)

            # ComboBox
            if isinstance(wdg, FCComboBox):
                wdg.currentIndexChanged.connect(self.update_storage)

            # CheckBox
            if isinstance(wdg, FCCheckBox):
                wdg.toggled.connect(self.update_storage)

            # FCRadio
            if isinstance(wdg, RadioSet):
                wdg.activated_custom.connect(self.update_storage)

            # SpinBox, DoubleSpinBox
            if isinstance(wdg, FCSpinner) or isinstance(wdg, FCDoubleSpinner):
                wdg.valueChanged.connect(self.update_storage)

    def ui_disconnect(self):
        try:
            self.name_entry.editingFinished.disconnect(self.update_tree_name)
        except (TypeError, AttributeError):
            pass

        for key in self.form_fields:
            wdg = self.form_fields[key]

            # FCEntry
            if isinstance(wdg, FCEntry):
                try:
                    wdg.textChanged.disconnect(self.update_storage)
                except (TypeError, AttributeError):
                    pass

            # ComboBox
            if isinstance(wdg, FCComboBox):
                try:
                    wdg.currentIndexChanged.disconnect(self.update_storage)
                except (TypeError, AttributeError):
                    pass

            # CheckBox
            if isinstance(wdg, FCCheckBox):
                try:
                    wdg.toggled.disconnect(self.update_storage)
                except (TypeError, AttributeError):
                    pass

            # FCRadio
            if isinstance(wdg, RadioSet):
                try:
                    wdg.activated_custom.disconnect(self.update_storage)
                except (TypeError, AttributeError):
                    pass

            # SpinBox, DoubleSpinBox
            if isinstance(wdg, FCSpinner) or isinstance(wdg, FCDoubleSpinner):
                try:
                    wdg.valueChanged.disconnect(self.update_storage)
                except (TypeError, AttributeError):
                    pass

    def update_tree_name(self):
        val = self.name_entry.get_value()

        item = self.tree_widget.currentItem()
        # I'm setting the value for the second column (designated by 1) because first column holds the ID
        # and second column holds the Name (this behavior is set in the build_ui method)
        item.setData(1, QtCore.Qt.DisplayRole, val)

    def update_storage(self):
        """
        Update the dictionary that is the storage of the tools 'database'
        :return:
        """
        tool_id = str(self.current_toolid)

        wdg = self.sender()
        if wdg is None:
            return

        wdg_name = wdg.objectName()

        try:
            val = wdg.get_value()
        except AttributeError:
            return

        if wdg_name == "gdb_name":
            self.db_tool_dict[tool_id]['name'] = val
        elif wdg_name == "gdb_dia":
            self.db_tool_dict[tool_id]['tooldia'] = val
        elif wdg_name == "gdb_tool_offset":
            self.db_tool_dict[tool_id]['offset'] = val
        elif wdg_name == "gdb_custom_offset":
            self.db_tool_dict[tool_id]['offset_value'] = val
        elif wdg_name == "gdb_type":
            self.db_tool_dict[tool_id]['type'] = val
        elif wdg_name == "gdb_shape":
            self.db_tool_dict[tool_id]['tool_type'] = val
        else:
            if wdg_name == "gdb_cutz":
                self.db_tool_dict[tool_id]['data']['cutz'] = val
            elif wdg_name == "gdb_multidepth":
                self.db_tool_dict[tool_id]['data']['multidepth'] = val
            elif wdg_name == "gdb_multidepth_entry":
                self.db_tool_dict[tool_id]['data']['depthperpass'] = val

            elif wdg_name == "gdb_travel":
                self.db_tool_dict[tool_id]['data']['travelz'] = val
            elif wdg_name == "gdb_frxy":
                self.db_tool_dict[tool_id]['data']['feedrate'] = val
            elif wdg_name == "gdb_frz":
                self.db_tool_dict[tool_id]['data']['feedrate_z'] = val
            elif wdg_name == "gdb_spindle":
                self.db_tool_dict[tool_id]['data']['spindlespeed'] = val
            elif wdg_name == "gdb_dwell":
                self.db_tool_dict[tool_id]['data']['dwell'] = val
            elif wdg_name == "gdb_dwelltime":
                self.db_tool_dict[tool_id]['data']['dwelltime'] = val

            elif wdg_name == "gdb_vdia":
                self.db_tool_dict[tool_id]['data']['vtipdia'] = val
            elif wdg_name == "gdb_vangle":
                self.db_tool_dict[tool_id]['data']['vtipangle'] = val
            elif wdg_name == "gdb_frapids":
                self.db_tool_dict[tool_id]['data']['feedrate_rapid'] = val
            elif wdg_name == "gdb_ecut":
                self.db_tool_dict[tool_id]['data']['extracut'] = val
            elif wdg_name == "gdb_ecut_length":
                self.db_tool_dict[tool_id]['data']['extracut_length'] = val

            # NCC Tool
            elif wdg_name == "gdb_n_operation":
                self.db_tool_dict[tool_id]['data']['tools_nccoperation'] = val
            elif wdg_name == "gdb_n_overlap":
                self.db_tool_dict[tool_id]['data']['tools_nccoverlap'] = val
            elif wdg_name == "gdb_n_margin":
                self.db_tool_dict[tool_id]['data']['tools_nccmargin'] = val
            elif wdg_name == "gdb_n_method":
                self.db_tool_dict[tool_id]['data']['tools_nccmethod'] = val
            elif wdg_name == "gdb_n_connect":
                self.db_tool_dict[tool_id]['data']['tools_nccconnect'] = val
            elif wdg_name == "gdb_n_contour":
                self.db_tool_dict[tool_id]['data']['tools_ncccontour'] = val
            elif wdg_name == "gdb_n_offset":
                self.db_tool_dict[tool_id]['data']['tools_ncc_offset_choice'] = val
            elif wdg_name == "gdb_n_offset_value":
                self.db_tool_dict[tool_id]['data']['tools_ncc_offset_value'] = val
            elif wdg_name == "gdb_n_milling_type":
                self.db_tool_dict[tool_id]['data']['tools_nccmilling_type'] = val

            # Paint Tool
            elif wdg_name == "gdb_p_overlap":
                self.db_tool_dict[tool_id]['data']['tools_paintoverlap'] = val
            elif wdg_name == "gdb_p_margin":
                self.db_tool_dict[tool_id]['data']['tools_paintmargin'] = val
            elif wdg_name == "gdb_p_method":
                self.db_tool_dict[tool_id]['data']['tools_paintmethod'] = val
            elif wdg_name == "gdb_p_connect":
                self.db_tool_dict[tool_id]['data']['tools_pathconnect'] = val
            elif wdg_name == "gdb_p_contour":
                self.db_tool_dict[tool_id]['data']['tools_paintcontour'] = val

        self.callback_app()

    def on_tool_requested_from_app(self):
        if not self.tree_widget.selectedItems():
            self.app.inform.emit('[WARNING_NOTCL] %s...' % _("No Tool/row selected in the Tools Database table"))
            return

        for item in self.tree_widget.selectedItems():
            tool_uid = item.data(0, QtCore.Qt.DisplayRole)

            for key in self.db_tool_dict.keys():
                if str(key) == str(tool_uid):
                    selected_tool = self.db_tool_dict[key]
                    self.on_tool_request(tool=selected_tool)

    def on_cancel_tool(self):
        for idx in range(self.app.ui.plot_tab_area.count()):
            if self.app.ui.plot_tab_area.tabText(idx) == _("Tools Database"):
                wdg = self.app.ui.plot_tab_area.widget(idx)
                wdg.deleteLater()
                self.app.ui.plot_tab_area.removeTab(idx)
        self.app.inform.emit('%s' % _("Cancelled adding tool from DB."))

    def resize_new_tool_table_widget(self, min_size, max_size):
        """
        Resize the table widget responsible for adding new tool in the Tool Database

        :param min_size: passed by rangeChanged signal or the self.new_tool_table_widget.horizontalScrollBar()
        :param max_size: passed by rangeChanged signal or the self.new_tool_table_widget.horizontalScrollBar()
        :return:
        """
        t_height = self.t_height
        if max_size > min_size:
            t_height = self.t_height + self.new_tool_table_widget.verticalScrollBar().height()

        self.new_tool_table_widget.setMaximumHeight(t_height)

    def closeEvent(self, QCloseEvent):
        super().closeEvent(QCloseEvent)


def color_variant(hex_color, bright_factor=1):
    """
    Takes a color in HEX format #FF00FF and produces a lighter or darker variant

    :param hex_color:           color to change
    :param bright_factor:   factor to change the color brightness [0 ... 1]
    :return:                    modified color
    """

    if len(hex_color) != 7:
        print("Color is %s, but needs to be in #FF00FF format. Returning original color." % hex_color)
        return hex_color

    if bright_factor > 1.0:
        bright_factor = 1.0
    if bright_factor < 0.0:
        bright_factor = 0.0

    rgb_hex = [hex_color[x:x + 2] for x in [1, 3, 5]]
    new_rgb = []
    for hex_value in rgb_hex:
        # adjust each color channel and turn it into a INT suitable as argument for hex()
        mod_color = round(int(hex_value, 16) * bright_factor)
        # make sure that each color channel has two digits without the 0x prefix
        mod_color_hex = str(hex(mod_color)[2:]).zfill(2)
        new_rgb.append(mod_color_hex)

    return "#" + "".join([i for i in new_rgb])
