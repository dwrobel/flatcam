############################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# Author: Juan Pablo Caram (c)                             #
# Date: 2/5/2014                                           #
# MIT Licence                                              #
############################################################

from PyQt5 import QtGui, QtCore, QtWidgets, QtWidgets
from PyQt5.QtCore import Qt


class FlatCAMTool(QtWidgets.QWidget):

    toolName = "FlatCAM Generic Tool"

    def __init__(self, app, parent=None):
        """

        :param app: The application this tool will run in.
        :type app: App
        :param parent: Qt Parent
        :return: FlatCAMTool
        """
        QtWidgets.QWidget.__init__(self, parent)

        # self.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum)

        self.layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.layout)

        self.app = app

        self.menuAction = None

    def install(self, icon=None, separator=None, **kwargs):
        before = None

        # 'pos' is the menu where the Action has to be installed
        # if no 'pos' kwarg is provided then by default our Action will be installed in the menutool
        # as it previously was
        if 'pos' in kwargs:
            pos = kwargs['pos']
        else:
            pos = self.app.ui.menutool

        # 'before' is the Action in the menu stated by 'pos' kwarg, before which we want our Action to be installed
        # if 'before' kwarg is not provided, by default our Action will be added in the last place.
        if 'before' in kwargs:
            before = (kwargs['before'])

        # create the new Action
        self.menuAction = QtWidgets.QAction(self)
        # if provided, add an icon to this Action
        if icon is not None:
            self.menuAction.setIcon(icon)
        # set the text name of the Action, which will be displayed in the menu
        self.menuAction.setText(self.toolName)
        # add a ToolTip to the new Action
        # self.menuAction.setToolTip(self.toolTip) # currently not available

        # insert the action in the position specified by 'before' and 'pos' kwargs
        pos.insertAction(before, self.menuAction)

        # if separator parameter is True add a Separator after the newly created Action
        if separator is True:
            pos.addSeparator()

        self.menuAction.triggered.connect(self.run)

    def run(self):

        if self.app.tool_tab_locked is True:
            return
        # Remove anything else in the GUI
        self.app.ui.tool_scroll_area.takeWidget()

        # Put ourself in the GUI
        self.app.ui.tool_scroll_area.setWidget(self)

        # Switch notebook to tool page
        self.app.ui.notebook.setCurrentWidget(self.app.ui.tool_tab)

        self.show()

