############################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# Author: Juan Pablo Caram (c)                             #
# Date: 2/5/2014                                           #
# MIT Licence                                              #
############################################################

# from PyQt5.QtCore import QModelIndex
from FlatCAMObj import *
import inspect  # TODO: Remove
import FlatCAMApp
from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtCore import Qt
# import webbrowser


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
                    self.app.inform.emit("Open cancelled.")
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


class TreeItem:
    """
    Item of a tree model
    """

    def __init__(self, data, icon=None, obj=None, parent_item=None):

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
        ("cncjob", "CNC Job")
    ]

    classdict = {
        "gerber": FlatCAMGerber,
        "excellon": FlatCAMExcellon,
        "cncjob": FlatCAMCNCjob,
        "geometry": FlatCAMGeometry
    }

    icon_files = {
        "gerber": "share/flatcam_icon16.png",
        "excellon": "share/drill16.png",
        "cncjob": "share/cnc16.png",
        "geometry": "share/geometry16.png"
    }

    root_item = None
    # app = None

    def __init__(self, app, parent=None):

        QtCore.QAbstractItemModel.__init__(self)

        ### Icons for the list view
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

        ### Data ###
        self.checked_indexes = []

        # Names of objects that are expected to become available.
        # For example, when the creation of a new object will run
        # in the background and will complete some time in the
        # future. This is a way to reserve the name and to let other
        # tasks know that they have to wait until available.
        self.promises = set()

        self.app = app

        ### View
        self.view = KeySensitiveListView(app)
        self.view.setModel(self)

        self.view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.view.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        # self.view.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        # self.view.setDragEnabled(True)
        # self.view.setAcceptDrops(True)
        # self.view.setDropIndicatorShown(True)

        font = QtGui.QFont()
        font.setPixelSize(12)
        font.setFamily("Seagoe UI")
        self.view.setFont(font)

        ## GUI Events
        self.view.selectionModel().selectionChanged.connect(self.on_list_selection_change)
        self.view.activated.connect(self.on_item_activated)
        # self.view.keyPressed.connect(self.on_key)
        self.view.keyPressed.connect(self.app.ui.keyPressEvent)
        self.view.clicked.connect(self.on_mouse_down)
        self.view.customContextMenuRequested.connect(self.on_menu_request)

        self.click_modifier = None

    def promise(self, obj_name):
        FlatCAMApp.App.log.debug("Object %s has been promised." % obj_name)
        self.promises.add(obj_name)

    def has_promises(self):
        return len(self.promises) > 0

    # def on_key(self, key):
    #     modifiers = QtWidgets.QApplication.keyboardModifiers()
    #     active = self.get_active()
    #     selected = self.get_selected()
    #
    #     if modifiers == QtCore.Qt.ControlModifier:
    #         if key == QtCore.Qt.Key_A:
    #             self.app.on_selectall()
    #
    #         if key == QtCore.Qt.Key_C:
    #             self.app.on_copy_object()
    #
    #         if key == QtCore.Qt.Key_E:
    #             self.app.on_fileopenexcellon()
    #
    #         if key == QtCore.Qt.Key_G:
    #             self.app.on_fileopengerber()
    #
    #         if key == QtCore.Qt.Key_N:
    #             self.app.on_file_new_click()
    #
    #         if key == QtCore.Qt.Key_M:
    #             self.app.measurement_tool.run()
    #         if key == QtCore.Qt.Key_O:
    #             self.app.on_file_openproject()
    #
    #         if key == QtCore.Qt.Key_S:
    #             self.app.on_file_saveproject()
    #
    #         # Toggle Plot Area
    #         if key == QtCore.Qt.Key_F10:
    #             self.app.on_toggle_plotarea()
    #
    #         return
    #     elif modifiers == QtCore.Qt.ShiftModifier:
    #
    #         # Copy Object Name
    #         # Copy Object Name
    #         if key == QtCore.Qt.Key_C:
    #             self.app.on_copy_name()
    #
    #         # Toggle axis
    #         if key == QtCore.Qt.Key_G:
    #             if self.toggle_axis is False:
    #                 self.app.plotcanvas.v_line.set_data(color=(0.70, 0.3, 0.3, 1.0))
    #                 self.app.plotcanvas.h_line.set_data(color=(0.70, 0.3, 0.3, 1.0))
    #                 self.app.plotcanvas.redraw()
    #                 self.app.toggle_axis = True
    #             else:
    #                 self.app.plotcanvas.v_line.set_data(color=(0.0, 0.0, 0.0, 0.0))
    #
    #                 self.app.plotcanvas.h_line.set_data(color=(0.0, 0.0, 0.0, 0.0))
    #                 self.appplotcanvas.redraw()
    #                 self.app.toggle_axis = False
    #
    #         # Open Preferences Window
    #         if key == QtCore.Qt.Key_P:
    #             self.app.on_preferences()
    #             return
    #
    #         # Rotate Object by 90 degree CCW
    #         if key == QtCore.Qt.Key_R:
    #             self.app.on_rotate(silent=True, preset=-90)
    #             return
    #
    #         # Run a Script
    #         if key == QtCore.Qt.Key_S:
    #             self.app.on_filerunscript()
    #             return
    #
    #         # Toggle Workspace
    #         if key == QtCore.Qt.Key_W:
    #             self.app.on_workspace_menu()
    #             return
    #
    #         # Skew on X axis
    #         if key == QtCore.Qt.Key_X:
    #             self.app.on_skewx()
    #             return
    #
    #         # Skew on Y axis
    #         if key == QtCore.Qt.Key_Y:
    #             self.app.on_skewy()
    #             return
    #
    #     elif modifiers == QtCore.Qt.AltModifier:
    #         # Eanble all plots
    #         if key == Qt.Key_1:
    #             self.app.enable_all_plots()
    #
    #         # Disable all plots
    #         if key == Qt.Key_2:
    #             self.app.disable_all_plots()
    #
    #         # Disable all other plots
    #         if key == Qt.Key_3:
    #             self.app.disable_other_plots()
    #
    #         # 2-Sided PCB Tool
    #         if key == QtCore.Qt.Key_D:
    #             self.app.dblsidedtool.run()
    #             return
    #
    #         # Non-Copper Clear Tool
    #         if key == QtCore.Qt.Key_N:
    #             self.app.ncclear_tool.run()
    #             return
    #
    #         # Transformation Tool
    #         if key == QtCore.Qt.Key_R:
    #             self.app.transform_tool.run()
    #             return
    #
    #         # Cutout Tool
    #         if key == QtCore.Qt.Key_U:
    #             self.app.cutout_tool.run()
    #             return
    #
    #     else:
    #         # Open Manual
    #         if key == QtCore.Qt.Key_F1:
    #             webbrowser.open(self.app.manual_url)
    #
    #         # Open Video Help
    #         if key == QtCore.Qt.Key_F2:
    #             webbrowser.open(self.app.video_url)
    #
    #         # Switch to Project Tab
    #         if key == QtCore.Qt.Key_1:
    #             self.app.on_select_tab('project')
    #
    #         # Switch to Selected Tab
    #         if key == QtCore.Qt.Key_2:
    #             self.app.on_select_tab('selected')
    #
    #         # Switch to Tool Tab
    #         if key == QtCore.Qt.Key_3:
    #             self.app.on_select_tab('tool')
    #
    #         # Delete
    #         if key == QtCore.Qt.Key_Delete and active:
    #             # Delete via the application to
    #             # ensure cleanup of the GUI
    #             active.app.on_delete()
    #
    #         # Space = Toggle Active/Inactive
    #         if key == QtCore.Qt.Key_Space:
    #             for select in selected:
    #                 select.ui.plot_cb.toggle()
    #             self.app.delete_selection_shape()
    #
    #         # Copy Object Name
    #         if key == QtCore.Qt.Key_E:
    #             self.app.object2editor()
    #
    #         # Grid toggle
    #         if key == QtCore.Qt.Key_G:
    #             self.app.ui.grid_snap_btn.trigger()
    #
    #         # Jump to coords
    #         if key == QtCore.Qt.Key_J:
    #             self.app.on_jump_to()
    #
    #         # New Excellon
    #         if key == QtCore.Qt.Key_L:
    #             self.app.new_excellon_object()
    #
    #         # Move tool toggle
    #         if key == QtCore.Qt.Key_M:
    #             self.app.move_tool.toggle()
    #
    #         # New Geometry
    #         if key == QtCore.Qt.Key_N:
    #             self.app.on_new_geometry()
    #
    #         # Set Origin
    #         if key == QtCore.Qt.Key_O:
    #             self.app.on_set_origin()
    #             return
    #
    #         # Set Origin
    #         if key == QtCore.Qt.Key_P:
    #             self.app.properties_tool.run()
    #             return
    #
    #         # Change Units
    #         if key == QtCore.Qt.Key_Q:
    #             if self.app.options["units"] == 'MM':
    #                 self.app.general_options_form.general_app_group.units_radio.set_value("IN")
    #             else:
    #                 self.app.general_options_form.general_app_group.units_radio.set_value("MM")
    #             self.app.on_toggle_units()
    #
    #         # Rotate Object by 90 degree CW
    #         if key == QtCore.Qt.Key_R:
    #             self.app.on_rotate(silent=True, preset=90)
    #
    #         # Shell toggle
    #         if key == QtCore.Qt.Key_S:
    #             self.app.on_toggle_shell()
    #
    #         # Transform Tool
    #         if key == QtCore.Qt.Key_T:
    #             self.app.transform_tool.run()
    #
    #         # Zoom Fit
    #         if key == QtCore.Qt.Key_V:
    #             self.app.on_zoom_fit(None)
    #
    #         # Mirror on X the selected object(s)
    #         if key == QtCore.Qt.Key_X:
    #             self.app.on_flipx()
    #
    #         # Mirror on Y the selected object(s)
    #         if key == QtCore.Qt.Key_Y:
    #             self.app.on_flipy()
    #
    #         # Zoom In
    #         if key == QtCore.Qt.Key_Equal:
    #             self.app.plotcanvas.zoom(1 / self.app.defaults['zoom_ratio'], self.app.mouse)
    #
    #         # Zoom Out
    #         if key == QtCore.Qt.Key_Minus:
    #             self.app.plotcanvas.zoom(self.app.defaults['zoom_ratio'], self.app.mouse)
    #
    #         # Show shortcut list
    #         if key == QtCore.Qt.Key_Ampersand:
    #             self.app.on_shortcut_list()
    #
    #         if key == QtCore.Qt.Key_QuoteLeft:
    #             self.app.on_shortcut_list()
    #         return

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
                if type(obj) != FlatCAMGeometry and type(obj) != FlatCAMExcellon:
                    self.app.ui.menuprojectedit.setVisible(False)
                if type(obj) != FlatCAMGerber and type(obj) != FlatCAMExcellon:
                    self.app.ui.menuprojectviewsource.setVisible(False)
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
            obj = index.internalPointer().obj
            if obj:
                return QtGui.QBrush(QtCore.Qt.black) if obj.options["plot"] else QtGui.QBrush(QtCore.Qt.darkGray)
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
                old_name = obj.options['name']
                # rename the object
                obj.options["name"] = str(data)
                new_name = obj.options['name']

                # update the SHELL auto-completer model data
                try:
                    self.app.myKeywords.remove(old_name)
                    self.app.myKeywords.append(new_name)
                    self.app.shell._edit.set_model_data(self.app.myKeywords)
                except:
                    log.debug(
                        "setData() --> Could not remove the old object name from auto-completer model list")

                obj.build_ui()
                self.app.inform.emit("Object renamed from %s to %s" % (old_name, new_name))

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
            ## Create a new name
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

        self.app.object_status_changed.emit(obj, 'append')

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
            except:
                FlatCAMApp.App.log.warning("DEV WARNING: Tried to get bounds of empty geometry.")

        return [xmin, ymin, xmax, ymax]

    def get_by_name(self, name, isCaseSensitive=None):
        """
        Fetches the FlatCAMObj with the given `name`.

        :param name: The name of the object.
        :type name: str
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

        # update the SHELL auto-completer model data
        name = active.obj.options['name']
        try:
            self.app.myKeywords.remove(name)
            self.app.shell._edit.set_model_data(self.app.myKeywords)
        except:
            log.debug(
                "delete_active() --> Could not remove the old object name from auto-completer model list")


        self.beginRemoveRows(self.index(group.row(), 0, QtCore.QModelIndex()), active.row(), active.row())

        group.remove_child(active)

        # after deletion of object store the current list of objects into the self.app.all_objects_list
        self.app.all_objects_list = self.get_list()

        self.endRemoveRows()

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

        self.beginResetModel()

        self.checked_indexes = []
        for group in self.root_item.child_items:
            group.remove_children()

        self.endResetModel()

        self.app.plotcanvas.redraw()

        self.app.all_objects_list.clear()

        self.app.geo_editor.clear()

        self.app.exc_editor.clear()

        self.app.dblsidedtool.reset_fields()

        self.app.panelize_tool.reset_fields()

        self.app.cutout_tool.reset_fields()

        self.app.film_tool.reset_fields()

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

        l = self.get_list()

        for sel in self.get_selected():
            l.remove(sel)

        return l

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

    def set_inactive(self, name):
        """
        Unselect object by name from the project list. This triggers the
        list_selection_changed event and call on_list_selection_changed.

        :param name: Name of the FlatCAM Object
        :return: None
        """
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
                self.app.inform.emit('[selected]<span style="color:%s;">%s</span> selected' %
                                 ('green', str(obj.options['name'])))
            elif obj.kind == 'excellon':
                self.app.inform.emit('[selected]<span style="color:%s;">%s</span> selected' %
                                 ('brown', str(obj.options['name'])))
            elif obj.kind == 'cncjob':
                self.app.inform.emit('[selected]<span style="color:%s;">%s</span> selected' %
                                 ('blue', str(obj.options['name'])))
            elif obj.kind == 'geometry':
                self.app.inform.emit('[selected]<span style="color:%s;">%s</span> selected' %
                                 ('red', str(obj.options['name'])))

        except IndexError:
            FlatCAMApp.App.log.debug("on_list_selection_change(): Index Error (Nothing selected?)")
            self.app.inform.emit('')
            try:
                self.app.ui.selected_scroll_area.takeWidget()
            except:
                FlatCAMApp.App.log.debug("Nothing to remove")

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
                self.app.inform.emit("[ERROR] Cause of error: %s" % str(e))
                raise

    def get_list(self):
        obj_list = []
        for group in self.root_item.child_items:
            for item in group.child_items:
                obj_list.append(item.obj)

        return obj_list

    def update_view(self):
        self.dataChanged.emit(QtCore.QModelIndex(), QtCore.QModelIndex())
