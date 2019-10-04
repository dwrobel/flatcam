# ########################################################## ##
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# Author: Juan Pablo Caram (c)                             #
# Date: 2/5/2014                                           #
# MIT Licence                                              #
# ########################################################## ##

# ########################################################## ##
# File modified by: Dennis Hayrullin                       #
# ########################################################## ##

# from PyQt5.QtCore import QModelIndex
from FlatCAMObj import *
import inspect  # TODO: Remove
import FlatCAMApp
from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtCore import Qt, QSettings
# import webbrowser

import gettext
import FlatCAMTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class KeySensitiveListView(QtWidgets.QTreeView):
    """
    QtGui.QListView extended to emit a signal on key press.
    """

    def __init__(self, app, parent=None):
        super(KeySensitiveListView, self).__init__(parent)
        self.setHeaderHidden(True)
        self.setEditTriggers(QtWidgets.QTreeView.SelectedClicked)

        # self.setRootIsDecorated(False)
        # self.setExpandsOnDoubleClick(False)

        # Enable dragging and dropping onto the GUI
        self.setAcceptDrops(True)
        self.filename = ""
        self.app = app

    keyPressed = QtCore.pyqtSignal(int)

    def keyPressEvent(self, event):
        # super(KeySensitiveListView, self).keyPressEvent(event)
        self.keyPressed.emit(event.key())

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls:
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        self.setDropIndicatorShown(True)
        if event.mimeData().hasUrls:
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        drop_indicator = self.dropIndicatorPosition()

        m = event.mimeData()
        if m.hasUrls:
            event.accept()

            for url in m.urls():
                self.filename = str(url.toLocalFile())

            # file drop from outside application
            if drop_indicator == QtWidgets.QAbstractItemView.OnItem:
                if self.filename == "":
                    self.app.inform.emit(_("Open cancelled."))
                else:
                    if self.filename.lower().rpartition('.')[-1] in self.app.grb_list:
                        self.app.worker_task.emit({'fcn': self.app.open_gerber,
                                                   'params': [self.filename]})
                    else:
                        event.ignore()

                    if self.filename.lower().rpartition('.')[-1] in self.app.exc_list:
                        self.app.worker_task.emit({'fcn': self.app.open_excellon,
                                                   'params': [self.filename]})
                    else:
                        event.ignore()

                    if self.filename.lower().rpartition('.')[-1] in self.app.gcode_list:
                        self.app.worker_task.emit({'fcn': self.app.open_gcode,
                                                   'params': [self.filename]})
                    else:
                        event.ignore()

                    if self.filename.lower().rpartition('.')[-1] in self.app.svg_list:
                        object_type = 'geometry'
                        self.app.worker_task.emit({'fcn': self.app.import_svg,
                                                   'params': [self.filename, object_type, None]})

                    if self.filename.lower().rpartition('.')[-1] in self.app.dxf_list:
                        object_type = 'geometry'
                        self.app.worker_task.emit({'fcn': self.app.import_dxf,
                                                   'params': [self.filename, object_type, None]})

                    if self.filename.lower().rpartition('.')[-1] in self.app.prj_list:
                        # self.app.open_project() is not Thread Safe
                        self.app.open_project(self.filename)
                    else:
                        event.ignore()
            else:
                pass
        else:
            event.ignore()


class TreeItem(KeySensitiveListView):
    """
    Item of a tree model
    """

    def __init__(self, data, icon=None, obj=None, parent_item=None):
        super(TreeItem, self).__init__(parent_item)
        self.parent_item = parent_item
        self.item_data = data  # Columns string data
        self.icon = icon  # Decoration
        self.obj = obj  # FlatCAMObj

        self.child_items = []

        if parent_item:
            parent_item.append_child(self)

    def append_child(self, item):
        self.child_items.append(item)
        item.set_parent_item(self)

    def remove_child(self, item):
        child = self.child_items.pop(self.child_items.index(item))
        child.obj.clear(True)
        child.obj.delete()
        del child.obj
        del child

    def remove_children(self):
        for child in self.child_items:
            child.obj.clear()
            child.obj.delete()
            del child.obj
            del child

        self.child_items = []

    def child(self, row):
        return self.child_items[row]

    def child_count(self):
        return len(self.child_items)

    def column_count(self):
        return len(self.item_data)

    def data(self, column):
        return self.item_data[column]

    def row(self):
        return self.parent_item.child_items.index(self)

    def set_parent_item(self, parent_item):
        self.parent_item = parent_item

    def __del__(self):
        del self.icon


class ObjectCollection(QtCore.QAbstractItemModel):
    """
    Object storage and management.
    """

    groups = [
        ("gerber", "Gerber"),
        ("excellon", "Excellon"),
        ("geometry", "Geometry"),
        ("cncjob", "CNC Job"),
        ("script", "Scripts"),
        ("document", "Document"),
    ]

    classdict = {
        "gerber": FlatCAMGerber,
        "excellon": FlatCAMExcellon,
        "cncjob": FlatCAMCNCjob,
        "geometry": FlatCAMGeometry,
        "script": FlatCAMScript,
        "document": FlatCAMDocument
    }

    icon_files = {
        "gerber": "share/flatcam_icon16.png",
        "excellon": "share/drill16.png",
        "cncjob": "share/cnc16.png",
        "geometry": "share/geometry16.png",
        "script": "share/script_new16.png",
        "document": "share/notes16_1.png"
    }

    root_item = None
    # app = None

    def __init__(self, app, parent=None):

        QtCore.QAbstractItemModel.__init__(self)

        self.app = app

        # ## Icons for the list view
        self.icons = {}
        for kind in ObjectCollection.icon_files:
            self.icons[kind] = QtGui.QPixmap(ObjectCollection.icon_files[kind])

        # Create root tree view item
        self.root_item = TreeItem(["root"])

        # Create group items
        self.group_items = {}
        for kind, title in ObjectCollection.groups:
            item = TreeItem([title], self.icons[kind])
            self.group_items[kind] = item
            self.root_item.append_child(item)

        # Create test sub-items
        # for i in self.root_item.m_child_items:
        #     print i.data(0)
        #     i.append_child(TreeItem(["empty"]))

        # ## Data # ##
        self.checked_indexes = []

        # Names of objects that are expected to become available.
        # For example, when the creation of a new object will run
        # in the background and will complete some time in the
        # future. This is a way to reserve the name and to let other
        # tasks know that they have to wait until available.
        self.promises = set()

        # same as above only for objects that are plotted
        self.plot_promises = set()

        # ## View
        self.view = KeySensitiveListView(self.app)
        self.view.setModel(self)

        self.view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.view.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        # self.view.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        # self.view.setDragEnabled(True)
        # self.view.setAcceptDrops(True)
        # self.view.setDropIndicatorShown(True)

        settings = QSettings("Open Source", "FlatCAM")
        if settings.contains("notebook_font_size"):
            fsize = settings.value('notebook_font_size', type=int)
        else:
            fsize = 12

        font = QtGui.QFont()
        font.setPixelSize(fsize)
        font.setFamily("Seagoe UI")
        self.view.setFont(font)

        # ## GUI Events
        self.view.selectionModel().selectionChanged.connect(self.on_list_selection_change)
        # self.view.activated.connect(self.on_item_activated)
        self.view.keyPressed.connect(self.app.ui.keyPressEvent)
        # self.view.clicked.connect(self.on_mouse_down)
        self.view.customContextMenuRequested.connect(self.on_menu_request)

        self.click_modifier = None

    def promise(self, obj_name):
        FlatCAMApp.App.log.debug("Object %s has been promised." % obj_name)
        self.promises.add(obj_name)

    def has_promises(self):
        return len(self.promises) > 0

    def plot_promise(self, plot_obj_name):
        self.plot_promises.add(plot_obj_name)

    def plot_remove_promise(self, plot_obj_name):
        if plot_obj_name in self.plot_promises:
            self.plot_promises.remove(plot_obj_name)

    def has_plot_promises(self):
        return len(self.plot_promises) > 0

    def on_mouse_down(self, event):
        FlatCAMApp.App.log.debug("Mouse button pressed on list")

    def on_menu_request(self, pos):

        sel = len(self.view.selectedIndexes()) > 0
        self.app.ui.menuprojectenable.setEnabled(sel)
        self.app.ui.menuprojectdisable.setEnabled(sel)
        self.app.ui.menuprojectviewsource.setEnabled(sel)

        self.app.ui.menuprojectcopy.setEnabled(sel)
        self.app.ui.menuprojectedit.setEnabled(sel)
        self.app.ui.menuprojectdelete.setEnabled(sel)
        self.app.ui.menuprojectsave.setEnabled(sel)
        self.app.ui.menuprojectproperties.setEnabled(sel)

        if sel:
            self.app.ui.menuprojectgeneratecnc.setVisible(True)
            self.app.ui.menuprojectedit.setVisible(True)
            self.app.ui.menuprojectsave.setVisible(True)
            self.app.ui.menuprojectviewsource.setVisible(True)

            for obj in self.get_selected():
                if type(obj) != FlatCAMGeometry:
                    self.app.ui.menuprojectgeneratecnc.setVisible(False)
                if type(obj) != FlatCAMGeometry and type(obj) != FlatCAMExcellon and type(obj) != FlatCAMGerber:
                    self.app.ui.menuprojectedit.setVisible(False)
                if type(obj) != FlatCAMGerber and type(obj) != FlatCAMExcellon and type(obj) != FlatCAMCNCjob:
                    self.app.ui.menuprojectviewsource.setVisible(False)
                if type(obj) != FlatCAMGerber and type(obj) != FlatCAMGeometry and type(obj) != FlatCAMExcellon and \
                        type(obj) != FlatCAMCNCjob:
                    # meaning for Scripts and for Document type of FlatCAM object
                    self.app.ui.menuprojectenable.setVisible(False)
                    self.app.ui.menuprojectdisable.setVisible(False)
                    self.app.ui.menuprojectedit.setVisible(False)
                    self.app.ui.menuprojectproperties.setVisible(False)
                    self.app.ui.menuprojectgeneratecnc.setVisible(False)
        else:
            self.app.ui.menuprojectgeneratecnc.setVisible(False)

        self.app.ui.menuproject.popup(self.view.mapToGlobal(pos))

    def index(self, row, column=0, parent=None, *args, **kwargs):
        if not self.hasIndex(row, column, parent):
            return QtCore.QModelIndex()

        # if not parent.isValid():
        #     parent_item = self.root_item
        # else:
        #     parent_item = parent.internalPointer()
        parent_item = parent.internalPointer() if parent.isValid() else self.root_item

        child_item = parent_item.child(row)
        if child_item:
            return self.createIndex(row, column, child_item)
        else:
            return QtCore.QModelIndex()

    def parent(self, index=None):
        if not index.isValid():
            return QtCore.QModelIndex()

        parent_item = index.internalPointer().parent_item

        if parent_item == self.root_item:
            return QtCore.QModelIndex()

        return self.createIndex(parent_item.row(), 0, parent_item)

    def rowCount(self, index=None, *args, **kwargs):
        if index.column() > 0:
            return 0

        if not index.isValid():
            parent_item = self.root_item
        else:
            parent_item = index.internalPointer()

        return parent_item.child_count()

    def columnCount(self, index=None, *args, **kwargs):
        if index.isValid():
            return index.internalPointer().column_count()
        else:
            return self.root_item.column_count()

    def data(self, index, role=None):
        if not index.isValid():
            return None

        if role in [Qt.DisplayRole, Qt.EditRole]:
            obj = index.internalPointer().obj
            if obj:
                return obj.options["name"]
            else:
                return index.internalPointer().data(index.column())

        if role == Qt.ForegroundRole:
            color = QColor(self.app.defaults['global_proj_item_color'])
            color_disabled = QColor(self.app.defaults['global_proj_item_dis_color'])
            obj = index.internalPointer().obj
            if obj:
                return QtGui.QBrush(color) if obj.options["plot"] else QtGui.QBrush(color_disabled)
            else:
                return index.internalPointer().data(index.column())

        elif role == Qt.DecorationRole:
            icon = index.internalPointer().icon
            if icon:
                return icon
            else:
                return QtGui.QPixmap()
        else:
            return None

    def setData(self, index, data, role=None):
        if index.isValid():
            obj = index.internalPointer().obj

            if obj:
                old_name = deepcopy(obj.options['name'])
                new_name = str(data)
                if old_name != new_name and new_name != '':
                    # rename the object
                    obj.options["name"] = deepcopy(data)

                    self.app.object_status_changed.emit(obj, 'rename', old_name)

                    # update the SHELL auto-completer model data
                    try:
                        self.app.myKeywords.remove(old_name)
                        self.app.myKeywords.append(new_name)
                        self.app.shell._edit.set_model_data(self.app.myKeywords)
                    except Exception as e:
                        log.debug(
                            "setData() --> Could not remove the old object name from auto-completer model list. %s" %
                            str(e))
                    # obj.build_ui()
                    self.app.inform.emit(_("Object renamed from <b>{old}</b> to <b>{new}</b>").format(old=old_name,
                                                                                                      new=new_name))

        return True

    def supportedDropActions(self):
        return Qt.MoveAction

    def flags(self, index):
        default_flags = QtCore.QAbstractItemModel.flags(self, index)

        if not index.isValid():
            return Qt.ItemIsEnabled | default_flags

        # Prevent groups from selection
        if not index.internalPointer().obj:
            return Qt.ItemIsEnabled
        else:
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable | \
                   Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled

        # return QtWidgets.QAbstractItemModel.flags(self, index)

    def append(self, obj, active=False):
        FlatCAMApp.App.log.debug(str(inspect.stack()[1][3]) + " --> OC.append()")

        name = obj.options["name"]

        # Check promises and clear if exists
        if name in self.promises:
            self.promises.remove(name)
            # FlatCAMApp.App.log.debug("Promised object %s became available." % name)
            # FlatCAMApp.App.log.debug("%d promised objects remaining." % len(self.promises))

        # Prevent same name
        while name in self.get_names():
            # ## Create a new name
            # Ends with number?
            FlatCAMApp.App.log.debug("new_object(): Object name (%s) exists, changing." % name)
            match = re.search(r'(.*[^\d])?(\d+)$', name)
            if match:  # Yes: Increment the number!
                base = match.group(1) or ''
                num = int(match.group(2))
                name = base + str(num + 1)
            else:  # No: add a number!
                name += "_1"
        obj.options["name"] = name

        obj.set_ui(obj.ui_type())

        # Required before appending (Qt MVC)
        group = self.group_items[obj.kind]
        group_index = self.index(group.row(), 0, QtCore.QModelIndex())
        self.beginInsertRows(group_index, group.child_count(), group.child_count())

        # Append new item
        obj.item = TreeItem(None, self.icons[obj.kind], obj, group)

        # Required after appending (Qt MVC)
        self.endInsertRows()

        # Expand group
        if group.child_count() is 1:
            self.view.setExpanded(group_index, True)

        self.app.should_we_save = True

        self.app.object_status_changed.emit(obj, 'append', name)

        # decide if to show or hide the Notebook side of the screen
        if self.app.defaults["global_project_autohide"] is True:
            # always open the notebook on object added to collection
            self.app.ui.splitter.setSizes([1, 1])

    def get_names(self):
        """
        Gets a list of the names of all objects in the collection.

        :return: List of names.
        :rtype: list
        """

        # FlatCAMApp.App.log.debug(str(inspect.stack()[1][3]) + " --> OC.get_names()")
        return [x.options['name'] for x in self.get_list()]

    def get_bounds(self):
        """
        Finds coordinates bounding all objects in the collection.

        :return: [xmin, ymin, xmax, ymax]
        :rtype: list
        """
        FlatCAMApp.App.log.debug(str(inspect.stack()[1][3]) + "--> OC.get_bounds()")

        # TODO: Move the operation out of here.

        xmin = Inf
        ymin = Inf
        xmax = -Inf
        ymax = -Inf

        # for obj in self.object_list:
        for obj in self.get_list():
            try:
                gxmin, gymin, gxmax, gymax = obj.bounds()
                xmin = min([xmin, gxmin])
                ymin = min([ymin, gymin])
                xmax = max([xmax, gxmax])
                ymax = max([ymax, gymax])
            except Exception as e:
                FlatCAMApp.App.log.warning("DEV WARNING: Tried to get bounds of empty geometry. %s" % str(e))

        return [xmin, ymin, xmax, ymax]

    def get_by_name(self, name, isCaseSensitive=None):
        """
        Fetches the FlatCAMObj with the given `name`.

        :param name: The name of the object.
        :type name: str
        :param isCaseSensitive: whether searching of the object is done by name where the name is case sensitive
        :return: The requested object or None if no such object.
        :rtype: FlatCAMObj or None
        """
        FlatCAMApp.App.log.debug(str(inspect.stack()[1][3]) + "--> OC.get_by_name()")

        if isCaseSensitive is None or isCaseSensitive is True:
            for obj in self.get_list():
                if obj.options['name'] == name:
                    return obj
        else:
            for obj in self.get_list():
                if obj.options['name'].lower() == name.lower():
                    return obj
        return None

    def delete_active(self, select_project=True):
        selections = self.view.selectedIndexes()
        if len(selections) == 0:
            return

        active = selections[0].internalPointer()
        group = active.parent_item

        # send signal with the object that is deleted
        # self.app.object_status_changed.emit(active.obj, 'delete')

        # some objects add a Tab on creation, close it here
        for idx in range(self.app.ui.plot_tab_area.count()):
            if self.app.ui.plot_tab_area.widget(idx).objectName() == active.obj.options['name']:
                self.app.ui.plot_tab_area.removeTab(idx)
                break

        # update the SHELL auto-completer model data
        name = active.obj.options['name']
        try:
            self.app.myKeywords.remove(name)
            self.app.shell._edit.set_model_data(self.app.myKeywords)
            # this is not needed any more because now the code editor is created on demand
            # self.app.ui.code_editor.set_model_data(self.app.myKeywords)
        except Exception as e:
            log.debug(
                "delete_active() --> Could not remove the old object name from auto-completer model list. %s" % str(e))

        self.app.object_status_changed.emit(active.obj, 'delete', name)

        # ############ OBJECT DELETION FROM MODEL STARTS HERE ####################
        self.beginRemoveRows(self.index(group.row(), 0, QtCore.QModelIndex()), active.row(), active.row())
        group.remove_child(active)
        # after deletion of object store the current list of objects into the self.app.all_objects_list
        self.app.all_objects_list = self.get_list()
        self.endRemoveRows()
        # ############ OBJECT DELETION FROM MODEL STOPS HERE ####################

        if self.app.is_legacy is False:
            self.app.plotcanvas.redraw()

        if select_project:
            # always go to the Project Tab after object deletion as it may be done with a shortcut key
            self.app.ui.notebook.setCurrentWidget(self.app.ui.project_tab)

        self.app.should_we_save = True

        # decide if to show or hide the Notebook side of the screen
        if self.app.defaults["global_project_autohide"] is True:
            # hide the notebook if there are no objects in the collection
            if not self.get_list():
                self.app.ui.splitter.setSizes([0, 1])

    def delete_all(self):
        FlatCAMApp.App.log.debug(str(inspect.stack()[1][3]) + "--> OC.delete_all()")

        self.app.object_status_changed.emit(None, 'delete_all', '')

        try:
            self.app.all_objects_list.clear()

            self.app.geo_editor.clear()

            self.app.exc_editor.clear()

            self.app.dblsidedtool.reset_fields()

            self.app.panelize_tool.reset_fields()

            self.app.cutout_tool.reset_fields()

            self.app.film_tool.reset_fields()

            self.beginResetModel()

            self.checked_indexes = []

            for group in self.root_item.child_items:
                group.remove_children()

            self.endResetModel()

            self.app.plotcanvas.redraw()
        except Exception as e:
            log.debug("ObjectCollection.delete_all() --> %s" % str(e))

    def get_active(self):
        """
        Returns the active object or None

        :return: FlatCAMObj or None
        """
        selections = self.view.selectedIndexes()
        if len(selections) == 0:
            return None

        return selections[0].internalPointer().obj

    def get_selected(self):
        """
        Returns list of objects selected in the view.

        :return: List of objects
        """
        return [sel.internalPointer().obj for sel in self.view.selectedIndexes()]

    def get_non_selected(self):
        """
        Returns list of objects non-selected in the view.

        :return: List of objects
        """

        obj_list = self.get_list()

        for sel in self.get_selected():
            obj_list.remove(sel)

        return obj_list

    def set_active(self, name):
        """
        Selects object by name from the project list. This triggers the
        list_selection_changed event and call on_list_selection_changed.

        :param name: Name of the FlatCAM Object
        :return: None
        """
        try:
            obj = self.get_by_name(name)
            item = obj.item
            group = self.group_items[obj.kind]

            group_index = self.index(group.row(), 0, QtCore.QModelIndex())
            item_index = self.index(item.row(), 0, group_index)

            self.view.selectionModel().select(item_index, QtCore.QItemSelectionModel.Select)
        except Exception as e:
            log.error("[ERROR] Cause: %s" % str(e))
            raise

    def set_exclusive_active(self, name):
        """
        Make the object with the name in parameters the only selected object

        :param name: name of object to be selected and made the only active object
        :return: None
        """
        self.set_all_inactive()
        self.set_active(name)

    def set_inactive(self, name):
        """
        Unselect object by name from the project list. This triggers the
        list_selection_changed event and call on_list_selection_changed.

        :param name: Name of the FlatCAM Object
        :return: None
        """
        # log.debug("ObjectCollection.set_inactive()")

        obj = self.get_by_name(name)
        item = obj.item
        group = self.group_items[obj.kind]

        group_index = self.index(group.row(), 0, QtCore.QModelIndex())
        item_index = self.index(item.row(), 0, group_index)

        self.view.selectionModel().select(item_index, QtCore.QItemSelectionModel.Deselect)

    def set_all_inactive(self):
        """
        Unselect all objects from the project list. This triggers the
        list_selection_changed event and call on_list_selection_changed.

        :return: None
        """
        for name in self.get_names():
            self.set_inactive(name)

    def on_list_selection_change(self, current, previous):
        # FlatCAMApp.App.log.debug("on_list_selection_change()")
        # FlatCAMApp.App.log.debug("Current: %s, Previous %s" % (str(current), str(previous)))

        try:
            obj = current.indexes()[0].internalPointer().obj

            if obj.kind == 'gerber':
                self.app.inform.emit(_('[selected]<span style="color:{color};">{name}</span> selected').format(
                    color='green', name=str(obj.options['name'])))
            elif obj.kind == 'excellon':
                self.app.inform.emit(_('[selected]<span style="color:{color};">{name}</span> selected').format(
                    color='brown', name=str(obj.options['name'])))
            elif obj.kind == 'cncjob':
                self.app.inform.emit(_('[selected]<span style="color:{color};">{name}</span> selected').format(
                    color='blue', name=str(obj.options['name'])))
            elif obj.kind == 'geometry':
                self.app.inform.emit(_('[selected]<span style="color:{color};">{name}</span> selected').format(
                    color='red', name=str(obj.options['name'])))
            elif obj.kind == 'script':
                self.app.inform.emit(_('[selected]<span style="color:{color};">{name}</span> selected').format(
                    color='orange', name=str(obj.options['name'])))
            elif obj.kind == 'document':
                self.app.inform.emit(_('[selected]<span style="color:{color};">{name}</span> selected').format(
                    color='darkCyan', name=str(obj.options['name'])))
        except IndexError:
            # FlatCAMApp.App.log.debug("on_list_selection_change(): Index Error (Nothing selected?)")
            self.app.inform.emit('')
            try:
                self.app.ui.selected_scroll_area.takeWidget()
            except Exception as e:
                FlatCAMApp.App.log.debug("Nothing to remove. %s" % str(e))

            self.app.setup_component_editor()
            return

        if obj:
            obj.build_ui()

    def on_item_activated(self, index):
        """
        Double-click or Enter on item.

        :param index: Index of the item in the list.
        :return: None
        """
        a_idx = index.internalPointer().obj
        if a_idx is None:
            return
        else:
            try:
                a_idx.build_ui()
            except Exception as e:
                self.app.inform.emit('[ERROR] %s: %s' %
                                     (_("Cause of error"), str(e)))
                raise

    def get_list(self):
        obj_list = []
        for group in self.root_item.child_items:
            for item in group.child_items:
                obj_list.append(item.obj)

        return obj_list

    def update_view(self):
        self.dataChanged.emit(QtCore.QModelIndex(), QtCore.QModelIndex())
