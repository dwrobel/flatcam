import sys
import os
from PyQt6 import QtGui, QtCore
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from copy import deepcopy
import pickle
import typing

""" 
https://stackoverflow.com/questions/22020091/how-to-handle-drag-and-drop-properly-using-pyqt-qabstractitemmodel

Here is a code I ended up after two days of TreeView/Model madness. The subject appeared to be much more broad 
than I thought. 
I barely can spend so much time creating a singe widget. 
Anyway. 
The drag-and-drop functionality of TreeView items has been enabled. 
But other than few interesting printout there is not much there. 
The double click on an item allows the user to enter a new item name which won't be picked up.
EDITED A DAY LATER WITH A REVISED CODE.
It is now by 90% functional tool.

The user can manipulate the TreeView items by drag and dropping, creating/duplicating/deleting and renaming. 
The TreeView items are representing the directories or folders in hierarchical fashion before they are created on 
a drive by hitting 'Print' button (instead of os.makedirs() the tool still simply prints each directory as a string.
I would say I am pretty happy with the result. Thanks to hackyday and to everyone who responded and helped with my 
questions.

A few last wishes...
A wish number 01:

    I wish the PrintOut() method would use a more elegant smarter function to loop through the TreeView items to 
    build a dictionary that is being passed to make_dirs_from_dict() method.

A wish number 02:

    I wish deleting the items would be more stable. By some unknown reason a tool crashes on third/fourth Delete button 
    clicks. So far, I was unable to trace the problem down.

A wish number 03: 3. I wish everyone the best and thanks for your help :

REPLY:
I am not totally sure what you are trying to achieve, but it sounds like you want to retrieve the dragged item in the 
drop operation, and have double click save a new node name.

Firstly, you need to save the dragged item into the mimeData. Currently, you are only saving the string 'mimeData', 
which doesn't tell you much. The mimeType string that it is saved as (here I used 'bstream') can actually be anything. 
As long as it matches what you use to retrieve the data, and is in the list returned by the mimeTypes method of the 
model. 

To pass the object itself, you must first serialize it (you can convert your object to xml alternatively, 
if that was something you are planning on doing), since it is not a standard type for mime data.
In order for the data you enter to be saved you must re-implement the setData method of the model and define 
behaviour for EditRole.

EDIT:
That is a lot of code you updated, but I will oblige on the points you highlighted. Avoid calling createIndex outside 
of the model class. This is a protected method in Qt; Python doesn't enforce private/protected variables or methods, 
but when using a library from another language that does, I try to respect the intended organization of the classes,
 and access to them.

The purpose of the model is to provide an interface to your data. You should access it using the index, data, 
parent etc. public functions of the model. 
o get the parent of a given index, use that index's (or the model's) parent function, 
which will also return a QModelIndex. This way, you don't have to go through (or indeed know about) the internal 
structure of the data. This is what I did in the deleteLevel method.

From the qt docs:

    To ensure that the representation of the data is kept separate from the way it is accessed, the concept of a model 
    index is introduced. Each piece of information that can be obtained via a model is represented by a model index... 
    only the model needs to know how to obtain data, and the type of data managed by the model can be defined fairly 
    generally.

Also, you can use recursion to simplify the print method.
"""


class TreeItem(object):
    def __init__(self, name, parent=None):
        self.name = str(name)
        self.parent = parent
        self.children = []
        self.setParent(parent)

    def setParent(self, parent):
        if parent is not None:
            self.parent = parent
            self.parent.appendChild(self)
        else:
            self.parent = None

    def appendChild(self, child):
        self.children.append(child)

    def childAtRow(self, row):
        if len(self.children) > row:
            return self.children[row]

    def rowOfChild(self, child):
        for i, item in enumerate(self.children):
            if item == child:
                return i
        return -1

    def removeChild(self, row):
        value = self.children[row]
        self.children.remove(value)
        return True

    def __len__(self):
        return len(self.children)


class TreeModel(QtCore.QAbstractItemModel):
    def __init__(self):

        QtCore.QAbstractItemModel.__init__(self)

        self.columns = 1
        self.clickedItem = None

        self.root = TreeItem('root', None)
        # each instance of TreeItem adds himself as a child to its parent
        levelA = TreeItem('levelA', self.root)
        levelB = TreeItem('levelB', levelA)
        levelC1 = TreeItem('levelC1', levelB)
        levelC2 = TreeItem('levelC2', levelB)
        levelC3 = TreeItem('levelC3', levelB)
        levelD = TreeItem('levelD', levelC3)

        levelE = TreeItem('levelE', levelD)
        levelF = TreeItem('levelF', levelE)

    def nodeFromIndex(self, index):
        return index.internalPointer() if index.isValid() else self.root

    def index(self, row: int, column: int, parent: QModelIndex = ...) -> QModelIndex:
        node = self.nodeFromIndex(parent)
        return self.createIndex(row, column, node.childAtRow(row))

    def parent(self, child):
        # print '\n parent(child)', child  # PyQt4.QtCore.QModelIndex
        if not child.isValid():
            return QModelIndex()
        node = self.nodeFromIndex(child)
        if node is None:
            return QModelIndex()
        parent = node.parent
        if parent is None:
            return QModelIndex()
        grandparent = parent.parent

        if grandparent is None:
            return QModelIndex()

        row = grandparent.rowOfChild(parent)
        assert row != - 1

        return self.createIndex(row, 0, parent)

    def rowCount(self, parent: QModelIndex = ...) -> int:
        node = self.nodeFromIndex(parent)
        if node is None:
            return 0
        return len(node)

    def columnCount(self, parent: QModelIndex = ...) -> int:
        return self.columns

    def data(self, index: QModelIndex, role: int = ...) -> typing.Any:
        if role == Qt.ItemDataRole.DecorationRole:
            return QVariant()
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return QVariant(int(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft))
        if role != Qt.ItemDataRole.DisplayRole:
            return QVariant()

        node = self.nodeFromIndex(index)
        if index.column() == 0:
            return QVariant(node.name)
        elif index.column() == 1:
            return QVariant(node.state)
        elif index.column() == 2:
            return QVariant(node.description)
        else:
            return QVariant()

    def supportedDropActions(self):
        return Qt.DropAction.CopyAction | Qt.DropAction.MoveAction

    def flags(self, index):
        defaultFlags = QAbstractItemModel.flags(self, index)
        if index.isValid():
            return (Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsDragEnabled |
                    Qt.ItemFlag.ItemIsDropEnabled | defaultFlags)
        else:
            return Qt.ItemIsDropEnabled | defaultFlags

    def setData(self, index: QModelIndex, value: typing.Any, role: int = ...) -> bool:
        if role == Qt.EditRole:
            if value.toString() and len(value.toString()) > 0:
                self.nodeFromIndex(index).name = value.toString()
                self.dataChanged.emit(index, index)
                return True

    def mimeTypes(self):
        return ['bstream', 'text/xml']

    def mimeData(self, indexes):
        mimedata = QMimeData()
        bstream = pickle.dumps(self.nodeFromIndex(indexes[0]))
        mimedata.setData('bstream', bstream)
        return mimedata

    def dropMimeData(self, mimedata, action, row, column, parentIndex):
        if action == Qt.DropAction.IgnoreAction:
            return True

        droppedNode = pickle.loads(mimedata.data('bstream'))
        droppedIndex = self.createIndex(row, column, droppedNode)

        parentNode = self.nodeFromIndex(parentIndex)

        newNode = deepcopy(droppedNode)
        newNode.setParent(parentNode)

        self.insertRow(len(parentNode)-1, parentIndex)
        # self.emit(SIGNAL("dataChanged(QModelIndex,QModelIndex)"), parentIndex, parentIndex)
        self.dataChanged.emit(parentIndex, parentIndex)

        return True

    def insertRow(self, row: int, parent: QModelIndex = ...) -> bool:
        return self.insertRows(row, 1, parent)

    def insertRows(self, row: int, count: int, parent: QModelIndex = ...) -> bool:
        self.beginInsertRows(parent, row, (row + (count - 1)))
        self.endInsertRows()
        return True

    def removeRow(self, row: int, parent: QModelIndex = ...) -> bool:
        ret = self.removeRows(row, 1, parent)
        return ret

    def removeRows(self, row: int, count: int, parent: QModelIndex = ...) -> bool:
        self.beginRemoveRows(parent, row, row)
        node = self.nodeFromIndex(parent)
        node.removeChild(row)
        self.endRemoveRows()
        return True


class GUI(QDialog):
    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.myWidget = None
        self.boxLayout = None
        self.treeView = None
        self.treeModel = None
        self.PrintButton = None
        self.DeleteButton = None
        self.insertButton = None
        self.duplicateButton = None

    def build(self, my_window):
        my_window.resize(600, 400)
        self.myWidget = QWidget(my_window)
        self.boxLayout = QVBoxLayout(self.myWidget)

        self.treeView = QTreeView()

        self.treeModel = TreeModel()
        self.treeView.setModel(self.treeModel)
        self.treeView.expandAll()
        self.treeView.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        # self.treeView.connect(
        #     self.treeView.model(), SIGNAL("dataChanged(QModelIndex,QModelIndex)"), self.onDataChanged)
        self.treeView.model().dataChanged.connect(self.onDataChanged)
        # QtCore.QObject.connect(self.treeView, QtCore.SIGNAL("clicked (QModelIndex)"),  self.treeItemClicked)
        self.treeView.clicked.connect(self.treeItemClicked)
        self.boxLayout.addWidget(self.treeView)

        self.PrintButton = QPushButton("Print")
        self.PrintButton.clicked.connect(self.printOut)
        self.boxLayout.addWidget(self.PrintButton)

        self.DeleteButton = QPushButton("Delete")
        self.DeleteButton.clicked.connect(self.deleteLevel)
        self.boxLayout.addWidget(self.DeleteButton)

        self.insertButton = QPushButton("Insert")
        self.insertButton.clicked.connect(self.insertLevel)
        self.boxLayout.addWidget(self.insertButton)

        self.duplicateButton = QPushButton("Duplicate")
        self.duplicateButton.clicked.connect(self.duplicateLevel)
        self.boxLayout.addWidget(self.duplicateButton)

        my_window.setCentralWidget(self.myWidget)

    def make_dirs_from_dict(self, dirDict, current_dir='C:\\'):
        for key, val in dirDict.items():
            os.mkdir(os.path.join(current_dir, key))
            print("Creating directory: ", os.path.join(current_dir, key))
            if type(val) == dict and val:
                self.make_dirs_from_dict(val, os.path.join(current_dir, val))

    def printOut(self):
        result_dict = dictify(self.treeView.model().root)
        self.make_dirs_from_dict(result_dict)

    def deleteLevel(self):
        if len(self.treeView.selectedIndexes()) == 0:
            return

        currentIndex = self.treeView.selectedIndexes()[0]
        self.treeView.model().removeRow(currentIndex.row(), currentIndex.parent())

    def insertLevel(self):
        if len(self.treeView.selectedIndexes()) == 0:
            return

        currentIndex = self.treeView.selectedIndexes()[0]
        currentNode = currentIndex.internalPointer()
        try:
            newItem = TreeItem('Brand New', currentNode)
            self.treeView.model().insertRow(len(currentNode)-1, currentIndex)
            # self.treeView.model().emit(SIGNAL("dataChanged(QModelIndex,QModelIndex)"), currentIndex, currentIndex)
        except Exception as err:
            print(err)
        self.treeView.model().dataChanged.emit(currentIndex, currentIndex)

    def duplicateLevel(self):
        if len(self.treeView.selectedIndexes()) == 0:
            return

        currentIndex = self.treeView.selectedIndexes()[0]
        currentRow = currentIndex.row()
        currentColumn = currentIndex.column()
        currentNode = currentIndex.internalPointer()

        parentNode = currentNode.parent
        parentIndex = self.treeView.model().createIndex(currentRow, currentColumn, parentNode)
        parentRow = parentIndex.row()
        parentColumn = parentIndex.column()

        newNode = deepcopy(currentNode)
        newNode.setParent(parentNode)

        self.treeView.model().insertRow(len(parentNode)-1, parentIndex)
        # self.treeView.model().emit(SIGNAL("dataChanged(QModelIndex,QModelIndex)"), parentIndex, parentIndex)
        self.treeView.model().dataChanged.emit(parentIndex, parentIndex)

        print(
            '\n\t\t\t CurrentNode:', currentNode.name, ', ParentNode:', parentNode.name, ', currentColumn:',
            currentColumn, ', currentRow:', currentRow, ', parentColumn:', parentColumn, ', parentRow:', parentRow
        )
        self.treeView.update()
        self.treeView.expandAll()

    def treeItemClicked(self, index):
        print("\n clicked item ----------->", index.internalPointer().name)

    def onDataChanged(self, indexA, indexB):
        print("\n onDataChanged NEVER TRIGGERED! ####################### \n ", indexA.internalPointer().name)
        self.treeView.update(indexA)
        self.treeView.expandAll()
        # self.treeView.expanded()


def dictify(node):
    kids = {}
    try:
        for child in node.children:
            kids.update(dictify(child))
    except TypeError:
        return {str(node.name): kids}


if __name__ == '__main__':

    app = QApplication(sys.argv)

    myWindow = QMainWindow()
    myGui = GUI()
    myGui.build(myWindow)
    myWindow.show()
    sys.exit(app.exec())
