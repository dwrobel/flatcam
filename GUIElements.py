from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtCore import pyqtSignal, pyqtSlot

from copy import copy
import re
import logging

log = logging.getLogger('base')

EDIT_SIZE_HINT = 70

class RadioSet(QtWidgets.QWidget):
    activated_custom = QtCore.pyqtSignal()

    def __init__(self, choices, orientation='horizontal', parent=None, stretch=None):
        """
        The choices are specified as a list of dictionaries containing:

        * 'label': Shown in the UI
        * 'value': The value returned is selected

        :param choices: List of choices. See description.
        :param orientation: 'horizontal' (default) of 'vertical'.
        :param parent: Qt parent widget.
        :type choices: list
        """
        super(RadioSet, self).__init__(parent)
        self.choices = copy(choices)
        if orientation == 'horizontal':
            layout = QtWidgets.QHBoxLayout()
        else:
            layout = QtWidgets.QVBoxLayout()

        group = QtWidgets.QButtonGroup(self)

        for choice in self.choices:
            choice['radio'] = QtWidgets.QRadioButton(choice['label'])
            group.addButton(choice['radio'])
            layout.addWidget(choice['radio'], stretch=0)
            choice['radio'].toggled.connect(self.on_toggle)

        layout.setContentsMargins(0, 0, 0, 0)

        if stretch is False:
            pass
        else:
            layout.addStretch()

        self.setLayout(layout)

        self.group_toggle_fn = lambda: None

    def on_toggle(self):
        # log.debug("Radio toggled")
        radio = self.sender()
        if radio.isChecked():
            self.group_toggle_fn()
            self.activated_custom.emit()
        return

    def get_value(self):
        for choice in self.choices:
            if choice['radio'].isChecked():
                return choice['value']
        log.error("No button was toggled in RadioSet.")
        return None

    def set_value(self, val):
        for choice in self.choices:
            if choice['value'] == val:
                choice['radio'].setChecked(True)
                return
        log.error("Value given is not part of this RadioSet: %s" % str(val))


# class RadioGroupChoice(QtWidgets.QWidget):
#     def __init__(self, label_1, label_2, to_check, hide_list, show_list, parent=None):
#         """
#         The choices are specified as a list of dictionaries containing:
#
#         * 'label': Shown in the UI
#         * 'value': The value returned is selected
#
#         :param choices: List of choices. See description.
#         :param orientation: 'horizontal' (default) of 'vertical'.
#         :param parent: Qt parent widget.
#         :type choices: list
#         """
#         super().__init__(parent)
#
#         group = QtGui.QButtonGroup(self)
#
#         self.lbl1 = label_1
#         self.lbl2 = label_2
#         self.hide_list = hide_list
#         self.show_list = show_list
#
#         self.btn1 = QtGui.QRadioButton(str(label_1))
#         self.btn2 = QtGui.QRadioButton(str(label_2))
#         group.addButton(self.btn1)
#         group.addButton(self.btn2)
#
#         if to_check == 1:
#             self.btn1.setChecked(True)
#         else:
#             self.btn2.setChecked(True)
#
#         self.btn1.toggled.connect(lambda: self.btn_state(self.btn1))
#         self.btn2.toggled.connect(lambda: self.btn_state(self.btn2))
#
#     def btn_state(self, btn):
#         if btn.text() == self.lbl1:
#             if btn.isChecked() is True:
#                 self.show_widgets(self.show_list)
#                 self.hide_widgets(self.hide_list)
#             else:
#                 self.show_widgets(self.hide_list)
#                 self.hide_widgets(self.show_list)
#
#     def hide_widgets(self, lst):
#         for wgt in lst:
#             wgt.hide()
#
#     def show_widgets(self, lst):
#         for wgt in lst:
#             wgt.show()


class LengthEntry(QtWidgets.QLineEdit):
    def __init__(self, output_units='IN', parent=None):
        super(LengthEntry, self).__init__(parent)

        self.output_units = output_units
        self.format_re = re.compile(r"^([^\s]+)(?:\s([a-zA-Z]+))?$")

        # Unit conversion table OUTPUT-INPUT
        self.scales = {
            'IN': {'IN': 1.0,
                   'MM': 1/25.4},
            'MM': {'IN': 25.4,
                   'MM': 1.0}
        }
        self.readyToEdit = True

    def mousePressEvent(self, e, Parent=None):
        super(LengthEntry, self).mousePressEvent(e)  # required to deselect on 2e click
        if self.readyToEdit:
            self.selectAll()
            self.readyToEdit = False

    def focusOutEvent(self, e):
        super(LengthEntry, self).focusOutEvent(e)  # required to remove cursor on focusOut
        self.deselect()
        self.readyToEdit = True

    def returnPressed(self, *args, **kwargs):
        val = self.get_value()
        if val is not None:
            self.set_text(str(val))
        else:
            log.warning("Could not interpret entry: %s" % self.get_text())

    def get_value(self):
        raw = str(self.text()).strip(' ')
        # match = self.format_re.search(raw)

        try:
            units = raw[-2:]
            units = self.scales[self.output_units][units.upper()]
            value = raw[:-2]
            return float(eval(value))*units
        except IndexError:
            value = raw
            return float(eval(value))
        except KeyError:
            value = raw
            return float(eval(value))
        except:
            log.warning("Could not parse value in entry: %s" % str(raw))
            return None

    def set_value(self, val):
        self.setText(str('%.4f' % val))

    def sizeHint(self):
        default_hint_size = super(LengthEntry, self).sizeHint()
        return QtCore.QSize(EDIT_SIZE_HINT, default_hint_size.height())


class FloatEntry(QtWidgets.QLineEdit):
    def __init__(self, parent=None):
        super(FloatEntry, self).__init__(parent)
        self.readyToEdit = True

    def mousePressEvent(self, e, Parent=None):
        super(FloatEntry, self).mousePressEvent(e)  # required to deselect on 2e click
        if self.readyToEdit:
            self.selectAll()
            self.readyToEdit = False

    def focusOutEvent(self, e):
        super(FloatEntry, self).focusOutEvent(e)  # required to remove cursor on focusOut
        self.deselect()
        self.readyToEdit = True

    def returnPressed(self, *args, **kwargs):
        val = self.get_value()
        if val is not None:
            self.set_text(str(val))
        else:
            log.warning("Could not interpret entry: %s" % self.text())

    def get_value(self):
        raw = str(self.text()).strip(' ')
        evaled = 0.0

        try:
            evaled = eval(raw)
        except:
            if evaled is not None:
                log.error("Could not evaluate: %s" % str(raw))
            return None

        return float(evaled)

    def set_value(self, val):
        if val is not None:
            self.setText("%.6f" % val)
        else:
            self.setText("")


    def sizeHint(self):
        default_hint_size = super(FloatEntry, self).sizeHint()
        return QtCore.QSize(EDIT_SIZE_HINT, default_hint_size.height())


class FloatEntry2(QtWidgets.QLineEdit):
    def __init__(self, parent=None):
        super(FloatEntry2, self).__init__(parent)
        self.readyToEdit = True

    def mousePressEvent(self, e, Parent=None):
        super(FloatEntry2, self).mousePressEvent(e)  # required to deselect on 2e click
        if self.readyToEdit:
            self.selectAll()
            self.readyToEdit = False

    def focusOutEvent(self, e):
        super(FloatEntry2, self).focusOutEvent(e)  # required to remove cursor on focusOut
        self.deselect()
        self.readyToEdit = True

    def get_value(self):
        raw = str(self.text()).strip(' ')
        evaled = 0.0
        try:
            evaled = eval(raw)
        except:
            if evaled is not None:
                log.error("Could not evaluate: %s" % str(raw))
            return None

        return float(evaled)

    def set_value(self, val):
        self.setText("%.6f" % val)

    def sizeHint(self):
        default_hint_size = super(FloatEntry2, self).sizeHint()
        return QtCore.QSize(EDIT_SIZE_HINT, default_hint_size.height())


class IntEntry(QtWidgets.QLineEdit):

    def __init__(self, parent=None, allow_empty=False, empty_val=None):
        super(IntEntry, self).__init__(parent)
        self.allow_empty = allow_empty
        self.empty_val = empty_val
        self.readyToEdit = True

    def mousePressEvent(self, e, Parent=None):
        super(IntEntry, self).mousePressEvent(e)  # required to deselect on 2e click
        if self.readyToEdit:
            self.selectAll()
            self.readyToEdit = False

    def focusOutEvent(self, e):
        super(IntEntry, self).focusOutEvent(e)  # required to remove cursor on focusOut
        self.deselect()
        self.readyToEdit = True

    def get_value(self):

        if self.allow_empty:
            if str(self.text()) == "":
                return self.empty_val
        # make the text() first a float and then int because if text is a float type,
        # the int() can't convert directly a "text float" into a int type.
        ret_val = float(self.text())
        ret_val = int(ret_val)
        return ret_val

    def set_value(self, val):

        if val == self.empty_val and self.allow_empty:
            self.setText("")
            return

        self.setText(str(val))

    def sizeHint(self):
        default_hint_size = super(IntEntry, self).sizeHint()
        return QtCore.QSize(EDIT_SIZE_HINT, default_hint_size.height())


class FCEntry(QtWidgets.QLineEdit):
    def __init__(self, parent=None):
        super(FCEntry, self).__init__(parent)
        self.readyToEdit = True

    def mousePressEvent(self, e, Parent=None):
        super(FCEntry, self).mousePressEvent(e)  # required to deselect on 2e click
        if self.readyToEdit:
            self.selectAll()
            self.readyToEdit = False

    def focusOutEvent(self, e):
        super(FCEntry, self).focusOutEvent(e)  # required to remove cursor on focusOut
        self.deselect()
        self.readyToEdit = True

    def get_value(self):
        return str(self.text())

    def set_value(self, val):
        self.setText(str(val))

    def sizeHint(self):
        default_hint_size = super(FCEntry, self).sizeHint()
        return QtCore.QSize(EDIT_SIZE_HINT, default_hint_size.height())


class FCEntry2(FCEntry):
    def __init__(self, parent=None):
        super(FCEntry2, self).__init__(parent)
        self.readyToEdit = True

    def set_value(self, val):
        self.setText('%.5f' % float(val))


class EvalEntry(QtWidgets.QLineEdit):
    def __init__(self, parent=None):
        super(EvalEntry, self).__init__(parent)
        self.readyToEdit = True

    def mousePressEvent(self, e, Parent=None):
        super(EvalEntry, self).mousePressEvent(e)  # required to deselect on 2e click
        if self.readyToEdit:
            self.selectAll()
            self.readyToEdit = False

    def focusOutEvent(self, e):
        super(EvalEntry, self).focusOutEvent(e)  # required to remove cursor on focusOut
        self.deselect()
        self.readyToEdit = True

    def returnPressed(self, *args, **kwargs):
        val = self.get_value()
        if val is not None:
            self.setText(str(val))
        else:
            log.warning("Could not interpret entry: %s" % self.get_text())

    def get_value(self):
        raw = str(self.text()).strip(' ')
        evaled = 0.0
        try:
            evaled = eval(raw)
        except:
            if evaled is not None:
                log.error("Could not evaluate: %s" % str(raw))
            return None
        return evaled

    def set_value(self, val):
        self.setText(str(val))

    def sizeHint(self):
        default_hint_size = super(EvalEntry, self).sizeHint()
        return QtCore.QSize(EDIT_SIZE_HINT, default_hint_size.height())


class EvalEntry2(QtWidgets.QLineEdit):
    def __init__(self, parent=None):
        super(EvalEntry2, self).__init__(parent)
        self.readyToEdit = True

    def mousePressEvent(self, e, Parent=None):
        super(EvalEntry2, self).mousePressEvent(e)  # required to deselect on 2e click
        if self.readyToEdit:
            self.selectAll()
            self.readyToEdit = False

    def focusOutEvent(self, e):
        super(EvalEntry2, self).focusOutEvent(e)  # required to remove cursor on focusOut
        self.deselect()
        self.readyToEdit = True

    def get_value(self):
        raw = str(self.text()).strip(' ')
        evaled = 0.0
        try:
            evaled = eval(raw)
        except:
            if evaled is not None:
                log.error("Could not evaluate: %s" % str(raw))
            return None
        return evaled

    def set_value(self, val):
        self.setText(str(val))

    def sizeHint(self):
        default_hint_size = super(EvalEntry2, self).sizeHint()
        return QtCore.QSize(EDIT_SIZE_HINT, default_hint_size.height())


class FCCheckBox(QtWidgets.QCheckBox):
    def __init__(self, label='', parent=None):
        super(FCCheckBox, self).__init__(str(label), parent)

    def get_value(self):
        return self.isChecked()

    def set_value(self, val):
        self.setChecked(val)

    def toggle(self):
        self.set_value(not self.get_value())


class FCTextArea(QtWidgets.QPlainTextEdit):
    def __init__(self, parent=None):
        super(FCTextArea, self).__init__(parent)

    def set_value(self, val):
        self.setPlainText(val)

    def get_value(self):
        return str(self.toPlainText())

    def sizeHint(self):
        default_hint_size = super(FCTextArea, self).sizeHint()
        return QtCore.QSize(EDIT_SIZE_HINT, default_hint_size.height())


class FCTextAreaRich(QtWidgets.QTextEdit):
    def __init__(self, parent=None):
        super(FCTextAreaRich, self).__init__(parent)

    def set_value(self, val):
        self.setText(val)

    def get_value(self):
        return str(self.toPlainText())

    def sizeHint(self):
        default_hint_size = super(FCTextAreaRich, self).sizeHint()
        return QtCore.QSize(EDIT_SIZE_HINT, default_hint_size.height())

class FCComboBox(QtWidgets.QComboBox):
    def __init__(self, parent=None):
        super(FCComboBox, self).__init__(parent)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

    def wheelEvent(self, *args, **kwargs):
        pass

    def get_value(self):
        return str(self.currentText())

    def set_value(self, val):
        self.setCurrentIndex(self.findText(str(val)))


class FCInputDialog(QtWidgets.QInputDialog):
    def __init__(self, parent=None, ok=False, val=None, title=None, text=None, min=None, max=None, decimals=None):
        super(FCInputDialog, self).__init__(parent)
        self.allow_empty = ok
        self.empty_val = val
        if title is None:
            self.title = 'title'
        else:
            self.title = title
        if text is None:
            self.text = 'text'
        else:
            self.text = text
        if min is None:
            self.min = 0
        else:
            self.min = min
        if max is None:
            self.max = 0
        else:
            self.max = max
        if decimals is None:
            self.decimals = 6
        else:
            self.decimals = decimals


    def get_value(self):
        self.val,self.ok = self.getDouble(self, self.title, self.text, min=self.min,
                                                      max=self.max, decimals=self.decimals)
        return [self.val, self.ok]

    # "Transform", "Enter the Angle value:"
    def set_value(self, val):
        pass


class FCButton(QtWidgets.QPushButton):
    def __init__(self, parent=None):
        super(FCButton, self).__init__(parent)

    def get_value(self):
        return self.isChecked()

    def set_value(self, val):
        self.setText(str(val))


class FCTab(QtWidgets.QTabWidget):
    def __init__(self, parent=None):
        super(FCTab, self).__init__(parent)
        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self.closeTab)

    def deleteTab(self, currentIndex):
        widget = self.widget(currentIndex)
        if widget is not None:
            widget.deleteLater()
        self.removeTab(currentIndex)

    def closeTab(self, currentIndex):
        self.removeTab(currentIndex)

    def protectTab(self, currentIndex):
        self.tabBar().setTabButton(currentIndex, QtWidgets.QTabBar.RightSide, None)


class FCDetachableTab(QtWidgets.QTabWidget):
    # From here: https://stackoverflow.com/questions/47267195/in-pyqt4-is-it-possible-to-detach-tabs-from-a-qtabwidget
    def __init__(self, parent=None):

        super().__init__()

        self.tabBar = self.FCTabBar(self)
        self.tabBar.onDetachTabSignal.connect(self.detachTab)
        self.tabBar.onMoveTabSignal.connect(self.moveTab)
        self.tabBar.detachedTabDropSignal.connect(self.detachedTabDrop)

        self.setTabBar(self.tabBar)

        # Used to keep a reference to detached tabs since their QMainWindow
        # does not have a parent
        self.detachedTabs = {}

        # Close all detached tabs if the application is closed explicitly
        QtWidgets.qApp.aboutToQuit.connect(self.closeDetachedTabs) # @UndefinedVariable

        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self.closeTab)


    def deleteTab(self, currentIndex):
        widget = self.widget(currentIndex)
        if widget is not None:
            widget.deleteLater()
        self.removeTab(currentIndex)

    def closeTab(self, currentIndex):
        self.removeTab(currentIndex)

    def protectTab(self, currentIndex):
        # self.FCTabBar().setTabButton(currentIndex, QtWidgets.QTabBar.RightSide, None)
        self.tabBar.setTabButton(currentIndex, QtWidgets.QTabBar.RightSide, None)

    ##
    #  The default movable functionality of QTabWidget must remain disabled
    #  so as not to conflict with the added features
    def setMovable(self, movable):
        pass

    ##
    #  Move a tab from one position (index) to another
    #
    #  @param    fromIndex    the original index location of the tab
    #  @param    toIndex      the new index location of the tab
    @pyqtSlot(int, int)
    def moveTab(self, fromIndex, toIndex):
        widget = self.widget(fromIndex)
        icon = self.tabIcon(fromIndex)
        text = self.tabText(fromIndex)

        self.removeTab(fromIndex)
        self.insertTab(toIndex, widget, icon, text)
        self.setCurrentIndex(toIndex)


    ##
    #  Detach the tab by removing it's contents and placing them in
    #  a DetachedTab window
    #
    #  @param    index    the index location of the tab to be detached
    #  @param    point    the screen position for creating the new DetachedTab window
    @pyqtSlot(int, QtCore.QPoint)
    def detachTab(self, index, point):

        # Get the tab content
        name = self.tabText(index)
        icon = self.tabIcon(index)
        if icon.isNull():
            icon = self.window().windowIcon()
        contentWidget = self.widget(index)

        try:
            contentWidgetRect = contentWidget.frameGeometry()
        except AttributeError:
            return

        # Create a new detached tab window
        detachedTab = self.FCDetachedTab(name, contentWidget)
        detachedTab.setWindowModality(QtCore.Qt.NonModal)
        detachedTab.setWindowIcon(icon)
        detachedTab.setGeometry(contentWidgetRect)
        detachedTab.onCloseSignal.connect(self.attachTab)
        detachedTab.onDropSignal.connect(self.tabBar.detachedTabDrop)
        detachedTab.move(point)
        detachedTab.show()


        # Create a reference to maintain access to the detached tab
        self.detachedTabs[name] = detachedTab


    ##
    #  Re-attach the tab by removing the content from the DetachedTab window,
    #  closing it, and placing the content back into the DetachableTabWidget
    #
    #  @param    contentWidget    the content widget from the DetachedTab window
    #  @param    name             the name of the detached tab
    #  @param    icon             the window icon for the detached tab
    #  @param    insertAt         insert the re-attached tab at the given index
    def attachTab(self, contentWidget, name, icon, insertAt=None):

        # Make the content widget a child of this widget
        contentWidget.setParent(self)

        # Remove the reference
        del self.detachedTabs[name]

        # Create an image from the given icon (for comparison)
        if not icon.isNull():
            try:
                tabIconPixmap = icon.pixmap(icon.availableSizes()[0])
                tabIconImage = tabIconPixmap.toImage()
            except IndexError:
                tabIconImage = None
        else:
            tabIconImage = None

        # Create an image of the main window icon (for comparison)
        if not icon.isNull():
            try:
                windowIconPixmap = self.window().windowIcon().pixmap(icon.availableSizes()[0])
                windowIconImage = windowIconPixmap.toImage()
            except IndexError:
                windowIconImage = None
        else:
            windowIconImage = None

        # Determine if the given image and the main window icon are the same.
        # If they are, then do not add the icon to the tab
        if tabIconImage == windowIconImage:
            if insertAt == None:
                index = self.addTab(contentWidget, name)
            else:
                index = self.insertTab(insertAt, contentWidget, name)
        else:
            if insertAt == None:
                index = self.addTab(contentWidget, icon, name)
            else:
                index = self.insertTab(insertAt, contentWidget, icon, name)


        # Make this tab the current tab
        if index > -1:
            self.setCurrentIndex(index)


    ##
    #  Remove the tab with the given name, even if it is detached
    #
    #  @param    name    the name of the tab to be removed
    def removeTabByName(self, name):

        # Remove the tab if it is attached
        attached = False
        for index in range(self.count()):
            if str(name) == str(self.tabText(index)):
                self.removeTab(index)
                attached = True
                break


        # If the tab is not attached, close it's window and
        # remove the reference to it
        if not attached:
            for key in self.detachedTabs:
                if str(name) == str(key):
                    self.detachedTabs[key].onCloseSignal.disconnect()
                    self.detachedTabs[key].close()
                    del self.detachedTabs[key]
                    break


    ##
    #  Handle dropping of a detached tab inside the DetachableTabWidget
    #
    #  @param    name     the name of the detached tab
    #  @param    index    the index of an existing tab (if the tab bar
    #                     determined that the drop occurred on an
    #                     existing tab)
    #  @param    dropPos  the mouse cursor position when the drop occurred
    @QtCore.pyqtSlot(str, int, QtCore.QPoint)
    def detachedTabDrop(self, name, index, dropPos):

        # If the drop occurred on an existing tab, insert the detached
        # tab at the existing tab's location
        if index > -1:

            # Create references to the detached tab's content and icon
            contentWidget = self.detachedTabs[name].contentWidget
            icon = self.detachedTabs[name].windowIcon()

            # Disconnect the detached tab's onCloseSignal so that it
            # does not try to re-attach automatically
            self.detachedTabs[name].onCloseSignal.disconnect()

            # Close the detached
            self.detachedTabs[name].close()

            # Re-attach the tab at the given index
            self.attachTab(contentWidget, name, icon, index)


        # If the drop did not occur on an existing tab, determine if the drop
        # occurred in the tab bar area (the area to the side of the QTabBar)
        else:

            # Find the drop position relative to the DetachableTabWidget
            tabDropPos = self.mapFromGlobal(dropPos)

            # If the drop position is inside the DetachableTabWidget...
            if self.rect().contains(tabDropPos):

                # If the drop position is inside the tab bar area (the
                # area to the side of the QTabBar) or there are not tabs
                # currently attached...
                if tabDropPos.y() < self.tabBar.height() or self.count() == 0:

                    # Close the detached tab and allow it to re-attach
                    # automatically
                    self.detachedTabs[name].close()


    ##
    #  Close all tabs that are currently detached.
    def closeDetachedTabs(self):
        listOfDetachedTabs = []

        for key in self.detachedTabs:
            listOfDetachedTabs.append(self.detachedTabs[key])

        for detachedTab in listOfDetachedTabs:
            detachedTab.close()


    ##
    #  When a tab is detached, the contents are placed into this QMainWindow.  The tab
    #  can be re-attached by closing the dialog or by dragging the window into the tab bar
    class FCDetachedTab(QtWidgets.QMainWindow):
        onCloseSignal = pyqtSignal(QtWidgets.QWidget, str, QtGui.QIcon)
        onDropSignal = pyqtSignal(str, QtCore.QPoint)

        def __init__(self, name, contentWidget):
            QtWidgets.QMainWindow.__init__(self, None)

            self.setObjectName(name)
            self.setWindowTitle(name)

            self.contentWidget = contentWidget
            self.setCentralWidget(self.contentWidget)
            self.contentWidget.show()

            self.windowDropFilter = self.WindowDropFilter()
            self.installEventFilter(self.windowDropFilter)
            self.windowDropFilter.onDropSignal.connect(self.windowDropSlot)


        ##
        #  Handle a window drop event
        #
        #  @param    dropPos    the mouse cursor position of the drop
        @QtCore.pyqtSlot(QtCore.QPoint)
        def windowDropSlot(self, dropPos):
            self.onDropSignal.emit(self.objectName(), dropPos)


        ##
        #  If the window is closed, emit the onCloseSignal and give the
        #  content widget back to the DetachableTabWidget
        #
        #  @param    event    a close event
        def closeEvent(self, event):
            self.onCloseSignal.emit(self.contentWidget, self.objectName(), self.windowIcon())


        ##
        #  An event filter class to detect a QMainWindow drop event
        class WindowDropFilter(QtCore.QObject):
            onDropSignal = pyqtSignal(QtCore.QPoint)

            def __init__(self):
                QtCore.QObject.__init__(self)
                self.lastEvent = None


            ##
            #  Detect a QMainWindow drop event by looking for a NonClientAreaMouseMove (173)
            #  event that immediately follows a Move event
            #
            #  @param    obj    the object that generated the event
            #  @param    event  the current event
            def eventFilter(self, obj, event):

                # If a NonClientAreaMouseMove (173) event immediately follows a Move event...
                if self.lastEvent == QtCore.QEvent.Move and event.type() == 173:

                    # Determine the position of the mouse cursor and emit it with the
                    # onDropSignal
                    mouseCursor = QtGui.QCursor()
                    dropPos = mouseCursor.pos()
                    self.onDropSignal.emit(dropPos)
                    self.lastEvent = event.type()
                    return True

                else:
                    self.lastEvent = event.type()
                    return False

    class FCTabBar(QtWidgets.QTabBar):
        onDetachTabSignal = pyqtSignal(int, QtCore.QPoint)
        onMoveTabSignal = pyqtSignal(int, int)
        detachedTabDropSignal = pyqtSignal(str, int, QtCore.QPoint)

        def __init__(self, parent=None):
            QtWidgets.QTabBar.__init__(self, parent)

            self.setAcceptDrops(True)
            self.setElideMode(QtCore.Qt.ElideRight)
            self.setSelectionBehaviorOnRemove(QtWidgets.QTabBar.SelectLeftTab)

            self.dragStartPos = QtCore.QPoint()
            self.dragDropedPos = QtCore.QPoint()
            self.mouseCursor = QtGui.QCursor()
            self.dragInitiated = False


        #  Send the onDetachTabSignal when a tab is double clicked
        #
        #  @param    event    a mouse double click event
        def mouseDoubleClickEvent(self, event):
            event.accept()
            self.onDetachTabSignal.emit(self.tabAt(event.pos()), self.mouseCursor.pos())


        #  Set the starting position for a drag event when the mouse button is pressed
        #
        #  @param    event    a mouse press event
        def mousePressEvent(self, event):
            if event.button() == QtCore.Qt.LeftButton:
                self.dragStartPos = event.pos()

            self.dragDropedPos.setX(0)
            self.dragDropedPos.setY(0)

            self.dragInitiated = False

            QtWidgets.QTabBar.mousePressEvent(self, event)


        #  Determine if the current movement is a drag.  If it is, convert it into a QDrag.  If the
        #  drag ends inside the tab bar, emit an onMoveTabSignal.  If the drag ends outside the tab
        #  bar, emit an onDetachTabSignal.
        #
        #  @param    event    a mouse move event
        def mouseMoveEvent(self, event):

            # Determine if the current movement is detected as a drag
            if not self.dragStartPos.isNull() and ((event.pos() - self.dragStartPos).manhattanLength() < QtWidgets.QApplication.startDragDistance()):
                self.dragInitiated = True

            # If the current movement is a drag initiated by the left button
            if (((event.buttons() & QtCore.Qt.LeftButton)) and self.dragInitiated):

                # Stop the move event
                finishMoveEvent = QtGui.QMouseEvent(QtCore.QEvent.MouseMove, event.pos(), QtCore.Qt.NoButton, QtCore.Qt.NoButton, QtCore.Qt.NoModifier)
                QtWidgets.QTabBar.mouseMoveEvent(self, finishMoveEvent)

                # Convert the move event into a drag
                drag = QtGui.QDrag(self)
                mimeData = QtCore.QMimeData()
                # mimeData.setData('action', 'application/tab-detach')
                drag.setMimeData(mimeData)
                # screen = QScreen(self.parentWidget().currentWidget().winId())
                # Create the appearance of dragging the tab content
                pixmap = self.parent().widget(self.tabAt(self.dragStartPos)).grab()
                targetPixmap = QtGui.QPixmap(pixmap.size())
                targetPixmap.fill(QtCore.Qt.transparent)
                painter = QtGui.QPainter(targetPixmap)
                painter.setOpacity(0.85)
                painter.drawPixmap(0, 0, pixmap)
                painter.end()
                drag.setPixmap(targetPixmap)

                # Initiate the drag
                dropAction = drag.exec_(QtCore.Qt.MoveAction | QtCore.Qt.CopyAction)


                # For Linux:  Here, drag.exec_() will not return MoveAction on Linux.  So it
                #             must be set manually
                if self.dragDropedPos.x() != 0 and self.dragDropedPos.y() != 0:
                    dropAction = QtCore.Qt.MoveAction


                # If the drag completed outside of the tab bar, detach the tab and move
                # the content to the current cursor position
                if dropAction == QtCore.Qt.IgnoreAction:
                    event.accept()
                    self.onDetachTabSignal.emit(self.tabAt(self.dragStartPos), self.mouseCursor.pos())

                # Else if the drag completed inside the tab bar, move the selected tab to the new position
                elif dropAction == QtCore.Qt.MoveAction:
                    if not self.dragDropedPos.isNull():
                        event.accept()
                        self.onMoveTabSignal.emit(self.tabAt(self.dragStartPos), self.tabAt(self.dragDropedPos))
            else:
                QtWidgets.QTabBar.mouseMoveEvent(self, event)

        #  Determine if the drag has entered a tab position from another tab position
        #
        #  @param    event    a drag enter event
        def dragEnterEvent(self, event):
            mimeData = event.mimeData()
            # formats = mcd imeData.formats()

        # if formats.contains('action') and mimeData.data('action') == 'application/tab-detach':
        # event.acceptProposedAction()

            QtWidgets.QTabBar.dragMoveEvent(self, event)

        #  Get the position of the end of the drag
        #
        #  @param    event    a drop event
        def dropEvent(self, event):
            self.dragDropedPos = event.pos()
            QtWidgets.QTabBar.dropEvent(self, event)



        #  Determine if the detached tab drop event occurred on an existing tab,
        #  then send the event to the DetachableTabWidget
        def detachedTabDrop(self, name, dropPos):

            tabDropPos = self.mapFromGlobal(dropPos)

            index = self.tabAt(tabDropPos)

            self.detachedTabDropSignal.emit(name, index, dropPos)


class VerticalScrollArea(QtWidgets.QScrollArea):
    """
    This widget extends QtGui.QScrollArea to make a vertical-only
    scroll area that also expands horizontally to accomodate
    its contents.
    """
    def __init__(self, parent=None):
        QtWidgets.QScrollArea.__init__(self, parent=parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)

    def eventFilter(self, source, event):
        """
        The event filter gets automatically installed when setWidget()
        is called.

        :param source:
        :param event:
        :return:
        """
        if event.type() == QtCore.QEvent.Resize and source == self.widget():
            # log.debug("VerticalScrollArea: Widget resized:")
            # log.debug(" minimumSizeHint().width() = %d" % self.widget().minimumSizeHint().width())
            # log.debug(" verticalScrollBar().width() = %d" % self.verticalScrollBar().width())

            self.setMinimumWidth(self.widget().sizeHint().width() +
                                 self.verticalScrollBar().sizeHint().width())

            # if self.verticalScrollBar().isVisible():
            #     log.debug(" Scroll bar visible")
            #     self.setMinimumWidth(self.widget().minimumSizeHint().width() +
            #                          self.verticalScrollBar().width())
            # else:
            #     log.debug(" Scroll bar hidden")
            #     self.setMinimumWidth(self.widget().minimumSizeHint().width())
        return QtWidgets.QWidget.eventFilter(self, source, event)


class OptionalInputSection:

    def __init__(self, cb, optinputs, logic=True):
        """
        Associates the a checkbox with a set of inputs.

        :param cb: Checkbox that enables the optional inputs.
        :param optinputs: List of widgets that are optional.
        :param logic: When True the logic is normal, when False the logic is in reverse
        It means that for logic=True, when the checkbox is checked the widgets are Enabled, and
        for logic=False, when the checkbox is checked the widgets are Disabled
        :return:
        """
        assert isinstance(cb, FCCheckBox), \
            "Expected an FCCheckBox, got %s" % type(cb)

        self.cb = cb
        self.optinputs = optinputs
        self.logic = logic

        self.on_cb_change()
        self.cb.stateChanged.connect(self.on_cb_change)

    def on_cb_change(self):

        if self.cb.checkState():
            for widget in self.optinputs:
                if self.logic is True:
                    widget.setEnabled(True)
                else:
                    widget.setEnabled(False)
        else:
            for widget in self.optinputs:
                if self.logic is True:
                    widget.setEnabled(False)
                else:
                    widget.setEnabled(True)


class FCTable(QtWidgets.QTableWidget):
    def __init__(self, parent=None):
        super(FCTable, self).__init__(parent)

    def sizeHint(self):
        default_hint_size = super(FCTable, self).sizeHint()
        return QtCore.QSize(EDIT_SIZE_HINT, default_hint_size.height())

    def getHeight(self):
        height = self.horizontalHeader().height()
        for i in range(self.rowCount()):
            height += self.rowHeight(i)
        return height

    def getWidth(self):
        width = self.verticalHeader().width()
        for i in range(self.columnCount()):
            width += self.columnWidth(i)
        return width

    # color is in format QtGui.Qcolor(r, g, b, alfa) with or without alfa
    def setColortoRow(self, rowIndex, color):
        for j in range(self.columnCount()):
            self.item(rowIndex, j).setBackground(color)

    # if user is clicking an blank area inside the QTableWidget it will deselect currently selected rows
    def mousePressEvent(self, event):
        if self.itemAt(event.pos()) is None:
            self.clearSelection()
        else:
            QtWidgets.QTableWidget.mousePressEvent(self, event)

    def setupContextMenu(self):
        self.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)

    def addContextMenu(self, entry, call_function, icon=None):
        action_name = str(entry)
        action = QtWidgets.QAction(self)
        action.setText(action_name)
        if icon:
            assert isinstance(icon, QtGui.QIcon), \
                "Expected the argument to be QtGui.QIcon. Instead it is %s" % type(icon)
            action.setIcon(icon)
        self.addAction(action)
        action.triggered.connect(call_function)

class FCSpinner(QtWidgets.QSpinBox):
    def __init__(self, parent=None):
        super(FCSpinner, self).__init__(parent)

    def get_value(self):
        return str(self.value())

    def set_value(self, val):
        try:
            k = int(val)
        except Exception as e:
            log.debug(str(e))
            return
        self.setValue(k)

    # def sizeHint(self):
    #     default_hint_size = super(FCSpinner, self).sizeHint()
    #     return QtCore.QSize(EDIT_SIZE_HINT, default_hint_size.height())


class FCDoubleSpinner(QtWidgets.QDoubleSpinBox):
    def __init__(self, parent=None):
        super(FCDoubleSpinner, self).__init__(parent)
        self.readyToEdit = True

    def mousePressEvent(self, e, parent=None):
        super(FCDoubleSpinner, self).mousePressEvent(e)  # required to deselect on 2e click
        if self.readyToEdit:
            self.lineEdit().selectAll()
            self.readyToEdit = False

    def focusOutEvent(self, e):
        super(FCDoubleSpinner, self).focusOutEvent(e)  # required to remove cursor on focusOut
        self.lineEdit().deselect()
        self.readyToEdit = True

    def get_value(self):
        return str(self.value())

    def set_value(self, val):
        try:
            k = int(val)
        except Exception as e:
            log.debug(str(e))
            return
        self.setValue(k)

    def set_precision(self, val):
        self.setDecimals(val)

    def set_range(self, min_val, max_val):
        self.setRange(self, min_val, max_val)


class Dialog_box(QtWidgets.QWidget):
    def __init__(self, title=None, label=None):
        """

        :param title: string with the window title
        :param label: string with the message inside the dialog box
        """
        super(Dialog_box, self).__init__()
        self.location = (0, 0)
        self.ok = False

        dialog_box = QtWidgets.QInputDialog()
        dialog_box.setFixedWidth(270)

        self.location, self.ok = dialog_box.getText(self, title, label)

