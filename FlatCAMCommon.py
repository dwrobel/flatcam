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
from flatcamGUI.GUIElements import FCTable, FCEntry, FCButton, FCDoubleSpinner, FCComboBox, FCCheckBox, FCSpinner
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

        if 'link' is kwargs:
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
        new_dict = dict()
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
        filename, _f = QtWidgets.QFileDialog.getSaveFileName(caption=_("Export FlatCAM Bookmarks"),
                                                             directory='{l_save}/FlatCAM_{n}_{date}'.format(
                                                                 l_save=str(self.app.get_last_save_folder()),
                                                                 n=_("Bookmarks"),
                                                                 date=date),
                                                             filter=filter__)

        filename = str(filename)

        if filename == "":
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("FlatCAM bookmarks export cancelled."))
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
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("FlatCAM bookmarks import cancelled."))
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
        self.db_tool_dict = dict()

        # layouts
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        table_hlay = QtWidgets.QHBoxLayout()
        layout.addLayout(table_hlay)

        self.table_widget = FCTable(drag_drop=True)
        self.table_widget.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        table_hlay.addWidget(self.table_widget)

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

        add_entry_btn = FCButton(_("Add Tool to Tools DB"))
        add_entry_btn.setToolTip(
            _("Add a new tool in the Tools Database.\n"
              "You can edit it after it is added.")
        )
        remove_entry_btn = FCButton(_("Remove Tool from Tools DB"))
        remove_entry_btn.setToolTip(
            _("Remove a selection of tools in the Tools Database.")
        )
        export_db_btn = FCButton(_("Export Tool DB"))
        export_db_btn.setToolTip(
            _("Save the Tools Database to a custom text file.")
        )
        import_db_btn = FCButton(_("Import Tool DB"))
        import_db_btn.setToolTip(
            _("Load the Tools Database information's from a custom text file.")
        )
        # button_hlay.addStretch()
        self.buttons_box.addWidget(add_entry_btn)
        self.buttons_box.addWidget(remove_entry_btn)

        self.buttons_box.addWidget(export_db_btn)
        self.buttons_box.addWidget(import_db_btn)
        # self.buttons_box.addWidget(closebtn)

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

    def setup_db_ui(self):
        filename = self.app.data_path + '/tools_db.FlatConfig'

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
        spindlespeed_item.setSingleStep(100)
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

        default_data = dict()
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

        dict_elem = dict()
        dict_elem['name'] = 'new_tool'
        dict_elem['tooldia'] = self.app.defaults["geometry_cnctooldia"]
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
        filename, _f = QtWidgets.QFileDialog.getSaveFileName(caption=_("Export Tools Database"),
                                                             directory='{l_save}/FlatCAM_{n}_{date}'.format(
                                                                 l_save=str(self.app.get_last_save_folder()),
                                                                 n=_("Tools_Database"),
                                                                 date=date),
                                                             filter=filter__)

        filename = str(filename)

        if filename == "":
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("FlatCAM Tools DB export cancelled."))
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
            self.app.inform.emit('[WARNING_NOTCL] %s' % _("FlatCAM Tools DB import cancelled."))
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

        filename = self.app.data_path + "/tools_db.FlatConfig"

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
        dict_elem = dict()
        default_data = dict()

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
                            if self.table_widget.item(row, col).text() is not '' else None
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
    new_rgb = list()
    for hex_value in rgb_hex:
        # adjust each color channel and turn it into a INT suitable as argument for hex()
        mod_color = round(int(hex_value, 16) * bright_factor)
        # make sure that each color channel has two digits without the 0x prefix
        mod_color_hex = str(hex(mod_color)[2:]).zfill(2)
        new_rgb.append(mod_color_hex)

    return "#" + "".join([i for i in new_rgb])
