# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# Author: Juan Pablo Caram (c)                             #
# Date: 2/5/2014                                           #
# MIT Licence                                              #
# ##########################################################

# ##########################################################
# File modified by: Marius Stanciu                         #
# ##########################################################
from appEditors.AppTextEditor import AppTextEditor
from appObjects.AppObjectTemplate import *

import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class DocumentObject(FlatCAMObj):
    """
    Represents a Document object.
    """
    optionChanged = QtCore.pyqtSignal(str)
    ui_type = DocumentObjectUI

    def __init__(self, name):
        self.decimals = self.app.decimals

        self.app.log.debug("Creating a Document object...")
        FlatCAMObj.__init__(self, name)

        self.kind = "document"
        self.units = ''

        self.ser_attrs = ['obj_options', 'kind', 'source_file']
        self.source_file = ''
        self.doc_code = ''

        self.font_name = None
        self.font_italic = None
        self.font_bold = None
        self.font_underline = None

        self.document_editor_tab = None

        self._read_only = False
        self.units_found = self.app.app_units

    def set_ui(self, ui):
        FlatCAMObj.set_ui(self, ui)
        self.app.log.debug("DocumentObject.set_ui()")

        assert isinstance(self.ui, DocumentObjectUI), \
            "Expected a DocumentObjectUI, got %s" % type(self.ui)

        self.units = self.app.app_units.upper()
        self.units_found = self.app.app_units

        # Fill form fields only on object create
        self.to_form()

        # Show/Hide Advanced Options
        app_mode = self.app.options["global_app_level"]
        self.change_level(app_mode)

        self.document_editor_tab = AppTextEditor(app=self.app)

        self.document_editor_tab.buttonRun.hide()

        self.ui.autocomplete_cb.set_value(self.app.options['document_autocompleter'])
        self.on_autocomplete_changed(state=self.app.options['document_autocompleter'])
        self.on_tab_size_change(val=self.app.options['document_tab_size'])

        self.ui.font_color_entry.set_value(self.app.options['document_font_color'])
        self.ui.sel_color_entry.set_value(self.app.options['document_sel_color'])
        self.ui.font_size_cb.setCurrentIndex(int(self.app.options['document_font_size']))

        font_sizes = self.app.options['document_font_sizes']
        self.ui.font_size_cb.addItems(font_sizes)

        flt = "FlatCAM Docs (*.FlatDoc);;All Files (*.*)"
        # ######################################################################
        # ######################## SIGNALS #####################################
        # ######################################################################
        self.ui.level.toggled.connect(self.on_level_changed)

        self.document_editor_tab.buttonOpen.clicked.disconnect()
        self.document_editor_tab.buttonOpen.clicked.connect(lambda: self.document_editor_tab.handleOpen(filt=flt))
        self.document_editor_tab.buttonSave.clicked.disconnect()
        self.document_editor_tab.buttonSave.clicked.connect(lambda: self.document_editor_tab.handleSaveGCode(filt=flt))

        self.document_editor_tab.code_editor.textChanged.connect(self.on_text_changed)

        self.ui.font_type_cb.currentFontChanged.connect(self.font_family)
        self.ui.font_size_cb.activated.connect(self.font_size)
        self.ui.font_bold_tb.clicked.connect(self.on_bold_button)
        self.ui.font_italic_tb.clicked.connect(self.on_italic_button)
        self.ui.font_under_tb.clicked.connect(self.on_underline_button)

        self.ui.font_color_entry.value_changed.connect(self.on_font_color_entry)
        self.ui.sel_color_entry.value_changed.connect(self.on_selection_color_entry)

        self.ui.al_left_tb.clicked.connect(
            lambda: self.document_editor_tab.code_editor.setAlignment(Qt.AlignmentFlag.AlignLeft))
        self.ui.al_center_tb.clicked.connect(
            lambda: self.document_editor_tab.code_editor.setAlignment(Qt.AlignmentFlag.AlignCenter))
        self.ui.al_right_tb.clicked.connect(
            lambda: self.document_editor_tab.code_editor.setAlignment(Qt.AlignmentFlag.AlignRight))
        self.ui.al_justify_tb.clicked.connect(
            lambda: self.document_editor_tab.code_editor.setAlignment(Qt.AlignmentFlag.AlignJustify)
        )

        self.ui.autocomplete_cb.stateChanged.connect(self.on_autocomplete_changed)
        self.ui.tab_size_spinner.returnPressed.connect(self.on_tab_size_change)
        # #######################################################################

        # self.document_editor_tab.handleTextChanged()
        self.ser_attrs = ['options', 'kind', 'source_file']

        try:
            if QtGui.Qt.mightBeRichText(self.source_file):
                # self.document_editor_tab.code_editor.setHtml(self.source_file)
                self.document_editor_tab.load_text(self.source_file, move_to_start=True, clear_text=True, as_html=True)
            else:
                # for line in self.source_file.splitlines():
                #     self.document_editor_tab.code_editor.append(line)
                self.document_editor_tab.load_text(self.source_file, move_to_start=True, clear_text=True, as_html=False)
        except AttributeError:
            self.document_editor_tab.load_text(self.source_file, move_to_start=True, clear_text=True, as_html=True)

        self.on_selection_color_entry(self.app.options["document_sel_color"])
        # self.on_font_color_entry(self.app.options["document_font_color"])

        self.build_ui()

        # TODO does not work, why?
        # switch the notebook area to Properties Tab
        # self.app.ui.notebook.setCurrentWidget(self.app.ui.properties_tab)

    @property
    def read_only(self):
        return self._read_only

    @read_only.setter
    def read_only(self, val):
        if val:
            self._read_only = True
        else:
            self._read_only = False

    def build_ui(self):
        FlatCAMObj.build_ui(self)
        tab_here = False

        # try to not add too many times a tab that it is already installed
        for idx in range(self.app.ui.plot_tab_area.count()):
            if self.app.ui.plot_tab_area.widget(idx).objectName() == self.obj_options['name'] + "_editor_tab":
                tab_here = True
                break

        # add the tab if it is not already added
        if tab_here is False:
            self.app.ui.plot_tab_area.addTab(self.document_editor_tab, '%s' % _("Document Editor"))
            self.document_editor_tab.setObjectName(self.obj_options['name'] + "_editor_tab")

        # Switch plot_area to CNCJob tab
        self.app.ui.plot_tab_area.setCurrentWidget(self.document_editor_tab)

    def change_level(self, level):
        """

        :param level:   application level: either 'b' or 'a'
        :type level:    str
        :return:
        """

        if level == 'a':
            self.ui.level.setChecked(True)
        else:
            self.ui.level.setChecked(False)
        self.on_level_changed(self.ui.level.isChecked())

    def on_level_changed(self, checked):
        if not checked:
            self.ui.level.setText('%s' % _('Beginner'))
            self.ui.level.setStyleSheet("""
                                                QToolButton
                                                {
                                                    color: green;
                                                }
                                                """)

        else:
            self.ui.level.setText('%s' % _('Advanced'))
            self.ui.level.setStyleSheet("""
                                                QToolButton
                                                {
                                                    color: red;
                                                }
                                                """)

    def on_autocomplete_changed(self, state):
        if state:
            self.document_editor_tab.code_editor.completer_enable = True
        else:
            self.document_editor_tab.code_editor.completer_enable = False

    def on_tab_size_change(self, val=None):
        try:
            self.ui.tab_size_spinner.returnPressed.disconnect(self.on_tab_size_change)
        except TypeError:
            pass

        if val:
            self.ui.tab_size_spinner.set_value(val)

        tab_balue = int(self.ui.tab_size_spinner.get_value())
        self.document_editor_tab.code_editor.setTabStopDistance(tab_balue)
        self.app.options['document_tab_size'] = tab_balue

        self.ui.tab_size_spinner.returnPressed.connect(self.on_tab_size_change)

    def on_text_changed(self):
        self.source_file = self.document_editor_tab.code_editor.toHtml()
        # print(self.source_file)

    def font_family(self, font):
        # self.document_editor_tab.code_editor.selectAll()
        font.setPointSize(float(self.ui.font_size_cb.get_value()))
        self.document_editor_tab.code_editor.setCurrentFont(font)
        self.font_name = self.ui.font_type_cb.currentFont().family()

    def font_size(self):
        # self.document_editor_tab.code_editor.selectAll()
        self.document_editor_tab.code_editor.setFontPointSize(float(self.ui.font_size_cb.get_value()))

    def on_bold_button(self):
        if self.ui.font_bold_tb.isChecked():
            self.document_editor_tab.code_editor.setFontWeight(QtGui.QFont.Weight.Bold)
            self.font_bold = True
        else:
            self.document_editor_tab.code_editor.setFontWeight(QtGui.QFont.Weight.Normal)
            self.font_bold = False

    def on_italic_button(self):
        if self.ui.font_italic_tb.isChecked():
            self.document_editor_tab.code_editor.setFontItalic(True)
            self.font_italic = True
        else:
            self.document_editor_tab.code_editor.setFontItalic(False)
            self.font_italic = False

    def on_underline_button(self):
        if self.ui.font_under_tb.isChecked():
            self.document_editor_tab.code_editor.setFontUnderline(True)
            self.font_underline = True
        else:
            self.document_editor_tab.code_editor.setFontUnderline(False)
            self.font_underline = False

    # Setting font colors handlers
    def on_font_color_entry(self, val):
        self.app.options['document_font_color'] = val
        new_color = QtGui.QColor(val[:-2])
        self.document_editor_tab.code_editor.setTextColor(new_color)

    # Setting selection colors handlers
    def on_selection_color_entry(self, val):
        self.app.options['document_sel_color'] = val
        # p = QtGui.QPalette()
        # p.setColor(QtGui.QPalette.ColorRole.Highlight, sel_color)
        # p.setColor(QtGui.QPalette.ColorRole.HighlightedText, QtGui.QColor('white'))
        # self.document_editor_tab.code_editor.setPalette(p)

        self.document_editor_tab.code_editor.setStyleSheet(
            """
                QTextEdit {selection-background-color:%s;
                           selection-color:white;
                }
            """ % QtGui.QColor(val[:-2]).name()
        )

    def mirror(self, axis, point):
        pass

    def offset(self, vect):
        pass

    def rotate(self, angle, point):
        pass

    def scale(self, xfactor, yfactor=None, point=None):
        pass

    def skew(self, angle_x, angle_y, point):
        pass

    def buffer(self, distance, join, factor=None):
        pass

    def bounds(self, flatten=False):
        return None, None, None, None

    def to_dict(self):
        """
        Returns a representation of the object as a dictionary.
        Attributes to include are listed in ``self.ser_attrs``.

        :return: A dictionary-encoded copy of the object.
        :rtype: dict
        """
        d = {}
        for attr in self.ser_attrs:
            d[attr] = getattr(self, attr)
        return d

    def from_dict(self, d):
        """
        Sets object's attributes from a dictionary.
        Attributes to include are listed in ``self.ser_attrs``.
        This method will look only for only and all the
        attributes in ``self.ser_attrs``. They must all
        be present. Use only for deserializing saved
        objects.

        :param d: Dictionary of attributes to set in the object.
        :type d: dict
        :return: None
        """
        for attr in self.ser_attrs:
            setattr(self, attr, d[attr])
