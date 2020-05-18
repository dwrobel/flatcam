from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import QSettings, Qt

from AppGUI.GUIElements import FCTextArea, FCCheckBox, FCComboBox, FCSpinner, FCEntry
from AppGUI.preferences.OptionsGroupUI import OptionsGroupUI
import gettext
import AppTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

settings = QSettings("Open Source", "FlatCAM")
if settings.contains("machinist"):
    machinist_setting = settings.value('machinist', type=int)
else:
    machinist_setting = 0


class CNCJobAdvOptPrefGroupUI(OptionsGroupUI):
    def __init__(self, decimals=4, parent=None):
        # OptionsGroupUI.__init__(self, "CNC Job Advanced Options Preferences", parent=None)
        super(CNCJobAdvOptPrefGroupUI, self).__init__(self, parent=parent)
        self.decimals = decimals

        self.setTitle(str(_("CNC Job Adv. Options")))

        # ## Export G-Code
        self.export_gcode_label = QtWidgets.QLabel("<b>%s:</b>" % _("Export CNC Code"))
        self.export_gcode_label.setToolTip(
            _("Export and save G-Code to\n"
              "make this object to a file.")
        )
        self.layout.addWidget(self.export_gcode_label)

        # Prepend to G-Code
        toolchangelabel = QtWidgets.QLabel('%s' % _('Toolchange G-Code'))
        toolchangelabel.setToolTip(
            _(
                "Type here any G-Code commands you would\n"
                "like to be executed when Toolchange event is encountered.\n"
                "This will constitute a Custom Toolchange GCode,\n"
                "or a Toolchange Macro.\n"
                "The FlatCAM variables are surrounded by '%' symbol.\n\n"
                "WARNING: it can be used only with a preprocessor file\n"
                "that has 'toolchange_custom' in it's name and this is built\n"
                "having as template the 'Toolchange Custom' posprocessor file."
            )
        )
        self.layout.addWidget(toolchangelabel)

        qsettings = QSettings("Open Source", "FlatCAM")
        if qsettings.contains("textbox_font_size"):
            tb_fsize = qsettings.value('textbox_font_size', type=int)
        else:
            tb_fsize = 10
        font = QtGui.QFont()
        font.setPointSize(tb_fsize)

        self.toolchange_text = FCTextArea()
        self.toolchange_text.setPlaceholderText(
            _(
                "Type here any G-Code commands you would "
                "like to be executed when Toolchange event is encountered.\n"
                "This will constitute a Custom Toolchange GCode, "
                "or a Toolchange Macro.\n"
                "The FlatCAM variables are surrounded by '%' symbol.\n"
                "WARNING: it can be used only with a preprocessor file "
                "that has 'toolchange_custom' in it's name."
            )
        )
        self.layout.addWidget(self.toolchange_text)
        self.toolchange_text.setFont(font)

        hlay = QtWidgets.QHBoxLayout()
        self.layout.addLayout(hlay)

        # Toolchange Replacement GCode
        self.toolchange_cb = FCCheckBox(label='%s' % _('Use Toolchange Macro'))
        self.toolchange_cb.setToolTip(
            _("Check this box if you want to use\n"
              "a Custom Toolchange GCode (macro).")
        )
        hlay.addWidget(self.toolchange_cb)
        hlay.addStretch()

        hlay1 = QtWidgets.QHBoxLayout()
        self.layout.addLayout(hlay1)

        # Variable list
        self.tc_variable_combo = FCComboBox()
        self.tc_variable_combo.setToolTip(
            _("A list of the FlatCAM variables that can be used\n"
              "in the Toolchange event.\n"
              "They have to be surrounded by the '%' symbol")
        )
        hlay1.addWidget(self.tc_variable_combo)

        # Populate the Combo Box
        variables = [_('Parameters'), 'tool', 'tooldia', 't_drills', 'x_toolchange', 'y_toolchange', 'z_toolchange',
                     'z_cut', 'z_move', 'z_depthpercut', 'spindlespeed', 'dwelltime']
        self.tc_variable_combo.addItems(variables)
        self.tc_variable_combo.insertSeparator(1)

        self.tc_variable_combo.setItemData(0, _("FlatCAM CNC parameters"), Qt.ToolTipRole)
        fnt = QtGui.QFont()
        fnt.setBold(True)
        self.tc_variable_combo.setItemData(0, fnt, Qt.FontRole)

        self.tc_variable_combo.setItemData(2, 'tool = %s' % _("tool number"), Qt.ToolTipRole)
        self.tc_variable_combo.setItemData(3, 'tooldia = %s' % _("tool diameter"), Qt.ToolTipRole)
        self.tc_variable_combo.setItemData(4, 't_drills = %s' % _("for Excellon, total number of drills"),
                                           Qt.ToolTipRole)
        self.tc_variable_combo.setItemData(5, 'x_toolchange = %s' % _("X coord for Toolchange"), Qt.ToolTipRole)
        self.tc_variable_combo.setItemData(6, 'y_toolchange = %s' % _("Y coord for Toolchange"),
                                           Qt.ToolTipRole)
        self.tc_variable_combo.setItemData(7, 'z_toolchange = %s' % _("Z coord for Toolchange"), Qt.ToolTipRole)
        self.tc_variable_combo.setItemData(8, 'z_cut = %s' % _("Z depth for the cut"), Qt.ToolTipRole)
        self.tc_variable_combo.setItemData(9, 'z_move = %s' % _("Z height for travel"), Qt.ToolTipRole)
        self.tc_variable_combo.setItemData(10, 'z_depthpercut = %s' % _("the step value for multidepth cut"),
                                           Qt.ToolTipRole)
        self.tc_variable_combo.setItemData(11, 'spindlesspeed = %s' % _("the value for the spindle speed"),
                                           Qt.ToolTipRole)
        self.tc_variable_combo.setItemData(12,
                                           _("dwelltime = time to dwell to allow the spindle to reach it's set RPM"),
                                           Qt.ToolTipRole)

        # hlay1.addStretch()

        # Insert Variable into the Toolchange G-Code Text Box
        # self.tc_insert_buton = FCButton("Insert")
        # self.tc_insert_buton.setToolTip(
        #     "Insert the variable in the GCode Box\n"
        #     "surrounded by the '%' symbol."
        # )
        # hlay1.addWidget(self.tc_insert_buton)

        grid0 = QtWidgets.QGridLayout()
        self.layout.addLayout(grid0)

        grid0.addWidget(QtWidgets.QLabel(''), 1, 0, 1, 2)

        # Annotation Font Size
        self.annotation_fontsize_label = QtWidgets.QLabel('%s:' % _("Annotation Size"))
        self.annotation_fontsize_label.setToolTip(
            _("The font size of the annotation text. In pixels.")
        )
        grid0.addWidget(self.annotation_fontsize_label, 2, 0)
        self.annotation_fontsize_sp = FCSpinner()
        self.annotation_fontsize_sp.set_range(0, 9999)

        grid0.addWidget(self.annotation_fontsize_sp, 2, 1)
        grid0.addWidget(QtWidgets.QLabel(''), 2, 2)

        # Annotation Font Color
        self.annotation_color_label = QtWidgets.QLabel('%s:' % _('Annotation Color'))
        self.annotation_color_label.setToolTip(
            _("Set the font color for the annotation texts.")
        )
        self.annotation_fontcolor_entry = FCEntry()
        self.annotation_fontcolor_button = QtWidgets.QPushButton()
        self.annotation_fontcolor_button.setFixedSize(15, 15)

        self.form_box_child = QtWidgets.QHBoxLayout()
        self.form_box_child.setContentsMargins(0, 0, 0, 0)
        self.form_box_child.addWidget(self.annotation_fontcolor_entry)
        self.form_box_child.addWidget(self.annotation_fontcolor_button, alignment=Qt.AlignRight)
        self.form_box_child.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        color_widget = QtWidgets.QWidget()
        color_widget.setLayout(self.form_box_child)
        grid0.addWidget(self.annotation_color_label, 3, 0)
        grid0.addWidget(color_widget, 3, 1)
        grid0.addWidget(QtWidgets.QLabel(''), 3, 2)

        self.layout.addStretch()

        self.tc_variable_combo.currentIndexChanged[str].connect(self.on_cnc_custom_parameters)

        self.annotation_fontcolor_entry.editingFinished.connect(self.on_annotation_fontcolor_entry)
        self.annotation_fontcolor_button.clicked.connect(self.on_annotation_fontcolor_button)

    def on_cnc_custom_parameters(self, signal_text):
        if signal_text == 'Parameters':
            return
        else:
            self.toolchange_text.insertPlainText('%%%s%%' % signal_text)

    def on_annotation_fontcolor_entry(self):
        self.app.defaults['cncjob_annotation_fontcolor'] = self.annotation_fontcolor_entry.get_value()
        self.annotation_fontcolor_button.setStyleSheet(
            "background-color:%s" % str(self.app.defaults['cncjob_annotation_fontcolor']))

    def on_annotation_fontcolor_button(self):
        current_color = QtGui.QColor(self.app.defaults['cncjob_annotation_fontcolor'])

        c_dialog = QtWidgets.QColorDialog()
        annotation_color = c_dialog.getColor(initial=current_color)

        if annotation_color.isValid() is False:
            return

        self.annotation_fontcolor_button.setStyleSheet("background-color:%s" % str(annotation_color.name()))

        new_val_sel = str(annotation_color.name())
        self.annotation_fontcolor_entry.set_value(new_val_sel)
        self.app.defaults['cncjob_annotation_fontcolor'] = new_val_sel
