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
from appObjects.FlatCAMObj import *

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

        log.debug("Creating a Document object...")
        FlatCAMObj.__init__(self, name)

        self.kind = "document"
        self.units = ''

        self.ser_attrs = ['options', 'kind', 'source_file']
        self.source_file = ''
        self.doc_code = ''

        self.font_name = None
        self.font_italic = None
        self.font_bold = None
        self.font_underline = None

        self.document_editor_tab = None

        self._read_only = False
        self.units_found = self.app.defaults['units']

    def set_ui(self, ui):
        FlatCAMObj.set_ui(self, ui)
        log.debug("DocumentObject.set_ui()")

        assert isinstance(self.ui, DocumentObjectUI), \
            "Expected a DocumentObjectUI, got %s" % type(self.ui)

        self.units = self.app.defaults['units'].upper()
        self.units_found = self.app.defaults['units']

        # Fill form fields only on object create
        self.to_form()

        # Show/Hide Advanced Options
        if self.app.defaults["global_app_level"] == 'b':
            self.ui.level.setText('<span style="color:green;"><b>%s</b></span>' % _("Basic"))
        else:
            self.ui.level.setText('<span style="color:red;"><b>%s</b></span>' % _("Advanced"))

        self.document_editor_tab = AppTextEditor(app=self.app)
        stylesheet = """
                        QTextEdit {selection-background-color:%s;
                                   selection-color:white;
                        }
                     """ % self.app.defaults["document_sel_color"]

        self.document_editor_tab.code_editor.setStyleSheet(stylesheet)

        self.document_editor_tab.buttonRun.hide()

        self.ui.autocomplete_cb.set_value(self.app.defaults['document_autocompleter'])
        self.on_autocomplete_changed(state=self.app.defaults['document_autocompleter'])
        self.on_tab_size_change(val=self.app.defaults['document_tab_size'])

        flt = "FlatCAM Docs (*.FlatDoc);;All Files (*.*)"

        # ######################################################################
        # ######################## SIGNALS #####################################
        # ######################################################################
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

        self.ui.font_color_entry.editingFinished.connect(self.on_font_color_entry)
        self.ui.font_color_button.clicked.connect(self.on_font_color_button)
        self.ui.sel_color_entry.editingFinished.connect(self.on_selection_color_entry)
        self.ui.sel_color_button.clicked.connect(self.on_selection_color_button)

        self.ui.al_left_tb.clicked.connect(lambda: self.document_editor_tab.code_editor.setAlignment(Qt.AlignLeft))
        self.ui.al_center_tb.clicked.connect(lambda: self.document_editor_tab.code_editor.setAlignment(Qt.AlignCenter))
        self.ui.al_right_tb.clicked.connect(lambda: self.document_editor_tab.code_editor.setAlignment(Qt.AlignRight))
        self.ui.al_justify_tb.clicked.connect(
            lambda: self.document_editor_tab.code_editor.setAlignment(Qt.AlignJustify)
        )

        self.ui.autocomplete_cb.stateChanged.connect(self.on_autocomplete_changed)
        self.ui.tab_size_spinner.returnPressed.connect(self.on_tab_size_change)
        # #######################################################################

        self.ui.font_color_entry.set_value(self.app.defaults['document_font_color'])
        self.ui.font_color_button.setStyleSheet(
            "background-color:%s" % str(self.app.defaults['document_font_color']))

        self.ui.sel_color_entry.set_value(self.app.defaults['document_sel_color'])
        self.ui.sel_color_button.setStyleSheet(
            "background-color:%s" % self.app.defaults['document_sel_color'])

        self.ui.font_size_cb.setCurrentIndex(int(self.app.defaults['document_font_size']))

        # self.document_editor_tab.handleTextChanged()
        self.ser_attrs = ['options', 'kind', 'source_file']

        if Qt.mightBeRichText(self.source_file):
            # self.document_editor_tab.code_editor.setHtml(self.source_file)
            self.document_editor_tab.load_text(self.source_file, move_to_start=True, clear_text=True, as_html=True)
        else:
            # for line in self.source_file.splitlines():
            #     self.document_editor_tab.code_editor.append(line)
            self.document_editor_tab.load_text(self.source_file, move_to_start=True, clear_text=True, as_html=False)

        self.build_ui()

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
            if self.app.ui.plot_tab_area.widget(idx).objectName() == self.options['name']:
                tab_here = True
                break

        # add the tab if it is not already added
        if tab_here is False:
            self.app.ui.plot_tab_area.addTab(self.document_editor_tab, '%s' % _("Document Editor"))
            self.document_editor_tab.setObjectName(self.options['name'])

        # Switch plot_area to CNCJob tab
        self.app.ui.plot_tab_area.setCurrentWidget(self.document_editor_tab)

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
        self.document_editor_tab.code_editor.setTabStopWidth(tab_balue)
        self.app.defaults['document_tab_size'] = tab_balue

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
            self.document_editor_tab.code_editor.setFontWeight(QtGui.QFont.Bold)
            self.font_bold = True
        else:
            self.document_editor_tab.code_editor.setFontWeight(QtGui.QFont.Normal)
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
    def on_font_color_entry(self):
        self.app.defaults['document_font_color'] = self.ui.font_color_entry.get_value()
        self.ui.font_color_button.setStyleSheet("background-color:%s" % str(self.app.defaults['document_font_color']))

    def on_font_color_button(self):
        current_color = QtGui.QColor(self.app.defaults['document_font_color'])

        c_dialog = QtWidgets.QColorDialog()
        font_color = c_dialog.getColor(initial=current_color)

        if font_color.isValid() is False:
            return

        self.document_editor_tab.code_editor.setTextColor(font_color)
        self.ui.font_color_button.setStyleSheet("background-color:%s" % str(font_color.name()))

        new_val = str(font_color.name())
        self.ui.font_color_entry.set_value(new_val)
        self.app.defaults['document_font_color'] = new_val

    # Setting selection colors handlers
    def on_selection_color_entry(self):
        self.app.defaults['document_sel_color'] = self.ui.sel_color_entry.get_value()
        self.ui.sel_color_button.setStyleSheet("background-color:%s" % str(self.app.defaults['document_sel_color']))

    def on_selection_color_button(self):
        current_color = QtGui.QColor(self.app.defaults['document_sel_color'])

        c_dialog = QtWidgets.QColorDialog()
        sel_color = c_dialog.getColor(initial=current_color)

        if sel_color.isValid() is False:
            return

        p = QtGui.QPalette()
        p.setColor(QtGui.QPalette.Highlight, sel_color)
        p.setColor(QtGui.QPalette.HighlightedText, QtGui.QColor('white'))

        self.document_editor_tab.code_editor.setPalette(p)

        self.ui.sel_color_button.setStyleSheet("background-color:%s" % str(sel_color.name()))

        new_val = str(sel_color.name())
        self.ui.sel_color_entry.set_value(new_val)
        self.app.defaults['document_sel_color'] = new_val

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
