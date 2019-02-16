from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtCore import Qt
from FlatCAMTool import FlatCAMTool
from FlatCAMObj import *


class Properties(FlatCAMTool):

    toolName = "Properties"

    def __init__(self, app):
        FlatCAMTool.__init__(self, app)

        self.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)

        # this way I can hide/show the frame
        self.properties_frame = QtWidgets.QFrame()
        self.properties_frame.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.properties_frame)
        self.properties_box = QtWidgets.QVBoxLayout()
        self.properties_box.setContentsMargins(0, 0, 0, 0)
        self.properties_frame.setLayout(self.properties_box)

        ## Title
        title_label = QtWidgets.QLabel("<font size=4><b>&nbsp;%s</b></font>" % self.toolName)
        self.properties_box.addWidget(title_label)

        # self.layout.setMargin(0)  # PyQt4
        self.properties_box.setContentsMargins(0, 0, 0, 0) # PyQt5

        self.vlay = QtWidgets.QVBoxLayout()

        self.properties_box.addLayout(self.vlay)

        self.treeWidget = QtWidgets.QTreeWidget()
        self.treeWidget.setColumnCount(2)
        self.treeWidget.setHeaderHidden(True)
        self.treeWidget.header().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.treeWidget.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Expanding)

        self.vlay.addWidget(self.treeWidget)
        self.vlay.setStretch(0,0)

    def run(self):
        self.app.report_usage("ToolProperties()")

        if self.app.tool_tab_locked is True:
            return
        self.set_tool_ui()

        # if the splitter us hidden, display it
        if self.app.ui.splitter.sizes()[0] == 0:
            self.app.ui.splitter.setSizes([1, 1])

        FlatCAMTool.run(self)
        self.properties()

    def install(self, icon=None, separator=None, **kwargs):
        FlatCAMTool.install(self, icon, separator, shortcut='P', **kwargs)

    def set_tool_ui(self):
        # this reset the TreeWidget
        self.treeWidget.clear()
        self.properties_frame.show()

    def properties(self):
        obj_list = self.app.collection.get_selected()
        if not obj_list:
            self.app.inform.emit("[ERROR_NOTCL] Properties Tool was not displayed. No object selected.")
            self.app.ui.notebook.setTabText(2, "Tools")
            self.properties_frame.hide()
            self.app.ui.notebook.setCurrentWidget(self.app.ui.project_tab)
            return
        for obj in obj_list:
            self.addItems(obj)
            self.app.inform.emit("[success] Object Properties are displayed.")
        self.app.ui.notebook.setTabText(2, "Properties Tool")

    def addItems(self, obj):
        parent = self.treeWidget.invisibleRootItem()

        font = QtGui.QFont()
        font.setBold(True)
        obj_type = self.addParent(parent, 'TYPE', expanded=True, color=QtGui.QColor("#000000"), font=font)
        obj_name = self.addParent(parent, 'NAME', expanded=True, color=QtGui.QColor("#000000"), font=font)
        dims = self.addParent(parent, 'Dimensions', expanded=True, color=QtGui.QColor("#000000"), font=font)
        options = self.addParent(parent, 'Options', color=QtGui.QColor("#000000"), font=font)
        separator = self.addParent(parent, '')

        self.addChild(obj_type, [obj.kind.upper()])
        self.addChild(obj_name, [obj.options['name']])

        # calculate physical dimensions
        xmin, ymin, xmax, ymax = obj.bounds()
        length = abs(xmax - xmin)
        width = abs(ymax - ymin)

        self.addChild(dims, ['Length:', '%.4f %s' % (
            length, self.app.general_options_form.general_app_group.units_radio.get_value().lower())], True)
        self.addChild(dims, ['Width:', '%.4f %s' % (
            width, self.app.general_options_form.general_app_group.units_radio.get_value().lower())], True)
        if self.app.general_options_form.general_app_group.units_radio.get_value().lower() == 'mm':
            area = (length * width) / 100
            self.addChild(dims, ['Box Area:', '%.4f %s' % (area, 'cm2')], True)
        else:
            area = length * width
            self.addChild(dims, ['Box Area:', '%.4f %s' % (area, 'in2')], True)

        for option in obj.options:
            if option is 'name':
                continue
            self.addChild(options, [str(option), str(obj.options[option])], True)

        self.addChild(separator, [''])

    def addParent(self, parent, title, expanded=False, color=None, font=None):
        item = QtWidgets.QTreeWidgetItem(parent, [title])
        item.setChildIndicatorPolicy(QtWidgets.QTreeWidgetItem.ShowIndicator)
        item.setExpanded(expanded)
        if color is not None:
            # item.setTextColor(0, color) # PyQt4
            item.setForeground(0, QtGui.QBrush(color))
        if font is not None:
            item.setFont(0, font)
        return item

    def addChild(self, parent, title, column1=None):
        item = QtWidgets.QTreeWidgetItem(parent)
        item.setText(0, str(title[0]))
        if column1 is not None:
            item.setText(1, str(title[1]))

# end of file
