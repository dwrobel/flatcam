
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt

from appEditors.AppExcEditor import AppExcEditor
from appEditors.AppGeoEditor import AppGeoEditor
from appEditors.AppGerberEditor import AppGerberEditor

from appGUI.GUIElements import FCFileSaveDialog, FCMessageBox
from camlib import to_dict, dict2obj, ET, ParseError
from appParsers.ParseHPGL2 import HPGL2

from appObjects.ObjectCollection import GerberObject, ExcellonObject, GeometryObject, ScriptObject, CNCJobObject

from reportlab.graphics import renderPDF
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch, mm
from reportlab.lib.pagesizes import landscape, portrait
from svglib.svglib import svg2rlg
from xml.dom.minidom import parseString as parse_xml_string

import time
import sys
import os
from copy import deepcopy
import re

import numpy as np
from numpy import Inf

from datetime import datetime
import simplejson as json

from appCommon.Common import LoudDict

from vispy.gloo.util import _screenshot
from vispy.io import write_png

import traceback
import lzma
from io import StringIO

# App Translation
import gettext
import appTranslation as fcTranslate
import builtins

import typing

if typing.TYPE_CHECKING:
    import appMain

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class AppIO(QtCore.QObject):
    def __init__(self, app):
        """
        A class that holds all the menu -> file handlers
        """
        super().__init__()

        self.app = app
        self.log = self.app.log
        self.inform = self.app.inform
        self.splash = self.app.splash
        self.worker_task = self.app.worker_task
        self.options = self.app.options
        self.app_units = self.app.app_units
        self.pagesize = {}

        self.app.new_project_signal.connect(self.on_new_project_house_keeping)

    def on_file_open_gerber(self, name=None):
        """
        File menu callback for opening a Gerber.

        :param name:
        :return: None
        """

        self.log.debug("on_file_open_gerber()")

        _filter_ = "Gerber Files (*.gbr *.ger *.gtl *.gbl *.gts *.gbs *.gtp *.gbp *.gto *.gbo *.gm1 *.gml *.gm3 " \
                   "*.gko *.cmp *.sol *.stc *.sts *.plc *.pls *.crc *.crs *.tsm *.bsm *.ly2 *.ly15 *.dim *.mil *.grb " \
                   "*.top *.bot *.smt *.smb *.sst *.ssb *.spt *.spb *.pho *.gdo *.art *.gbd *.outline);;" \
                   "Protel Files (*.gtl *.gbl *.gts *.gbs *.gto *.gbo *.gtp *.gbp *.gml *.gm1 *.gm3 *.gko " \
                   "*.outline);;" \
                   "Eagle Files (*.cmp *.sol *.stc *.sts *.plc *.pls *.crc *.crs *.tsm *.bsm *.ly2 *.ly15 *.dim " \
                   "*.mil);;" \
                   "OrCAD Files (*.top *.bot *.smt *.smb *.sst *.ssb *.spt *.spb);;" \
                   "Allegro Files (*.art);;" \
                   "Mentor Files (*.pho *.gdo);;" \
                   "All Files (*.*)"

        if name is None:
            try:
                filenames, _f = QtWidgets.QFileDialog.getOpenFileNames(caption=_("Open Gerber"),
                                                                       directory=self.app.get_last_folder(),
                                                                       filter=_filter_,
                                                                       initialFilter=self.app.last_op_gerber_filter)
            except TypeError:
                filenames, _f = QtWidgets.QFileDialog.getOpenFileNames(caption=_("Open Gerber"), filter=_filter_)

            filenames = [str(filename) for filename in filenames]
            self.app.last_op_gerber_filter = _f
        else:
            filenames = [name]
            self.splash.showMessage('%s: %ssec\n%s' % (_("Canvas initialization started.\n"
                                                         "Canvas initialization finished in"),
                                                       '%.2f' % self.app.used_time,
                                                       _("Opening Gerber file.")),
                                    alignment=Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft,
                                    color=QtGui.QColor("lightgray"))

        if len(filenames) == 0:
            self.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled."))
        else:
            for filename in filenames:
                if filename != '':
                    self.worker_task.emit({'fcn': self.open_gerber, 'params': [filename]})

    def on_file_open_excellon(self, name=None):
        """
        File menu callback for opening an Excellon file.

        :param name:
        :return: None
        """

        self.log.debug("on_file_open_excellon()")

        _filter_ = "Excellon Files (*.drl *.txt *.xln *.drd *.tap *.exc *.ncd);;" \
                   "All Files (*.*)"
        if name is None:
            try:
                filenames, _f = QtWidgets.QFileDialog.getOpenFileNames(caption=_("Open Excellon"),
                                                                       directory=self.app.get_last_folder(),
                                                                       filter=_filter_,
                                                                       initialFilter=self.app.last_op_excellon_filter)
            except TypeError:
                filenames, _f = QtWidgets.QFileDialog.getOpenFileNames(caption=_("Open Excellon"), filter=_filter_)
            filenames = [str(filename) for filename in filenames]
            self.app.last_op_excellon_filter = _f
        else:
            filenames = [str(name)]
            self.splash.showMessage('%s: %ssec\n%s' % (_("Canvas initialization started.\n"
                                                         "Canvas initialization finished in"),
                                                       '%.2f' % self.app.used_time,
                                                       _("Opening Excellon file.")),
                                    alignment=Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft,
                                    color=QtGui.QColor("lightgray"))

        if len(filenames) == 0:
            self.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled."))
        else:
            for filename in filenames:
                if filename != '':
                    self.worker_task.emit({'fcn': self.open_excellon, 'params': [filename]})

    def on_file_open_gcode(self, name=None):
        """

        File menu call back for opening gcode.

        :param name:
        :return:
        """

        self.log.debug("on_file_open_gcode()")

        # https://bobcadsupport.com/helpdesk/index.php?/Knowledgebase/Article/View/13/5/known-g-code-file-extensions
        _filter_ = "G-Code Files (*.txt *.nc *.ncc *.tap *.gcode *.cnc *.ecs *.fnc *.dnc *.ncg *.gc *.fan *.fgc" \
                   " *.din *.xpi *.hnc *.h *.i *.ncp *.min *.gcd *.rol *.knc *.mpr *.ply *.out *.eia *.sbp *.mpf);;" \
                   "All Files (*.*)"

        if name is None:
            try:
                filenames, _f = QtWidgets.QFileDialog.getOpenFileNames(caption=_("Open G-Code"),
                                                                       directory=self.app.get_last_folder(),
                                                                       filter=_filter_,
                                                                       initialFilter=self.app.last_op_gcode_filter)
            except TypeError:
                filenames, _f = QtWidgets.QFileDialog.getOpenFileNames(caption=_("Open G-Code"), filter=_filter_)

            filenames = [str(filename) for filename in filenames]
            self.app.last_op_gcode_filter = _f
        else:
            filenames = [name]
            self.splash.showMessage('%s: %ssec\n%s' % (_("Canvas initialization started.\n"
                                                         "Canvas initialization finished in"),
                                                       '%.2f' % self.app.used_time,
                                                       _("Opening G-Code file.")),
                                    alignment=Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft,
                                    color=QtGui.QColor("lightgray"))

        if len(filenames) == 0:
            self.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled."))
        else:
            for filename in filenames:
                if filename != '':
                    self.worker_task.emit({'fcn': self.open_gcode, 'params': [filename, None, True]})

    def on_file_open_project(self):
        """
        File menu callback for opening a project.

        :return: None
        """

        self.log.debug("on_file_open_project()")

        _filter_ = "FlatCAM Project (*.FlatPrj);;All Files (*.*)"
        try:
            filename, _f = QtWidgets.QFileDialog.getOpenFileName(caption=_("Open Project"),
                                                                 directory=self.app.get_last_folder(), filter=_filter_)
        except TypeError:
            filename, _f = QtWidgets.QFileDialog.getOpenFileName(caption=_("Open Project"), filter=_filter_)

        filename = str(filename)

        if filename == "":
            self.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled."))
        else:
            # self.worker_task.emit({'fcn': self.open_project,
            #                        'params': [filename]})
            # The above was failing because open_project() is not
            # thread safe. The new_project()
            self.open_project(filename)

    def on_file_open_hpgl2(self, name=None):
        """
        File menu callback for opening a HPGL2.

        :param name:
        :return:        None
        """
        self.log.debug("on_file_open_hpgl2()")

        _filter_ = "HPGL2 Files (*.plt);;" \
                   "All Files (*.*)"

        if name is None:
            try:
                filenames, _f = QtWidgets.QFileDialog.getOpenFileNames(caption=_("Open HPGL2"),
                                                                       directory=self.app.get_last_folder(),
                                                                       filter=_filter_)
            except TypeError:
                filenames, _f = QtWidgets.QFileDialog.getOpenFileNames(caption=_("Open HPGL2"), filter=_filter_)

            filenames = [str(filename) for filename in filenames]
        else:
            filenames = [name]
            self.splash.showMessage('%s: %ssec\n%s' % (_("Canvas initialization started.\n"
                                                         "Canvas initialization finished in"),
                                                       '%.2f' % self.app.used_time,
                                                       _("Opening HPGL2 file.")),
                                    alignment=Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft,
                                    color=QtGui.QColor("lightgray"))

        if len(filenames) == 0:
            self.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled."))
        else:
            for filename in filenames:
                if filename != '':
                    self.worker_task.emit({'fcn': self.open_hpgl2, 'params': [filename]})

    def on_file_open_config(self):
        """
        File menu callback for opening a config file.

        :return:        None
        """

        self.log.debug("on_file_open_config()")

        _filter_ = "FlatCAM Config (*.FlatConfig);;FlatCAM Config (*.json);;All Files (*.*)"
        try:
            filename, _f = QtWidgets.QFileDialog.getOpenFileName(caption=_("Open Configuration File"),
                                                                 directory=self.app.data_path, filter=_filter_)
        except TypeError:
            filename, _f = QtWidgets.QFileDialog.getOpenFileName(caption=_("Open Configuration File"),
                                                                 filter=_filter_)

        if filename == "":
            self.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled."))
        else:
            self.open_config_file(filename)

    def on_file_export_svg(self):
        """
        Callback for menu item File->Export SVG.

        :return: None
        """
        self.log.debug("on_file_export_svg()")

        obj = self.app.collection.get_active()
        if obj is None:
            self.inform.emit('[ERROR_NOTCL] %s' % _("No object is selected."))
            return

        # Check for more compatible types and add as required
        if (not isinstance(obj, GeometryObject)
                and not isinstance(obj, GerberObject)
                and not isinstance(obj, CNCJobObject)
                and not isinstance(obj, ExcellonObject)):
            msg = _("Only Geometry, Gerber and CNCJob objects can be used.")
            msgbox = FCMessageBox(parent=self.app.ui)
            msgbox.setWindowTitle(msg)  # taskbar still shows it
            msgbox.setWindowIcon(QtGui.QIcon(self.app.resource_location + '/app128.png'))

            msgbox.setInformativeText(msg)
            msgbox.setIconPixmap(QtGui.QPixmap(self.app.resource_location + '/waning.png'))

            bt_ok = msgbox.addButton(_('Ok'), QtWidgets.QMessageBox.ButtonRole.AcceptRole)
            msgbox.setDefaultButton(bt_ok)
            msgbox.exec()
            return

        name = obj.obj_options["name"]

        _filter = "SVG File (*.svg);;All Files (*.*)"
        try:
            filename, _f = FCFileSaveDialog.get_saved_filename(
                caption=_("Export SVG"),
                directory=self.app.get_last_save_folder() + '/' + str(name) + '_svg',
                ext_filter=_filter)
        except TypeError:
            filename, _f = FCFileSaveDialog.get_saved_filename(
                caption=_("Export SVG"),
                ext_filter=_filter)

        filename = str(filename)

        if filename == "":
            self.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled."))
            return
        else:
            self.export_svg(name, filename)
            if self.options["global_open_style"] is False:
                self.app.file_opened.emit("SVG", filename)
            self.app.file_saved.emit("SVG", filename)

    def on_file_export_png(self):

        self.log.debug("on_file_export_png()")

        date = str(datetime.today()).rpartition('.')[0]
        date = ''.join(c for c in date if c not in ':-')
        date = date.replace(' ', '_')

        data = None
        if self.app.use_3d_engine:
            image = _screenshot(alpha=False)
            data = np.asarray(image)
            if not data.ndim == 3 and data.shape[-1] in (3, 4):
                self.inform.emit('[[WARNING_NOTCL]] %s' % _('Data must be a 3D array with last dimension 3 or 4'))
                return

        filter_ = "PNG File (*.png);;All Files (*.*)"
        try:
            filename, _f = FCFileSaveDialog.get_saved_filename(
                caption=_("Export PNG Image"),
                directory=self.app.get_last_save_folder() + '/png_' + date,
                ext_filter=filter_)
        except TypeError:
            filename, _f = FCFileSaveDialog.get_saved_filename(
                caption=_("Export PNG Image"),
                ext_filter=filter_)

        filename = str(filename)

        if filename == "":
            self.inform.emit(_("Cancelled."))
            return
        else:
            if self.app.use_3d_engine:
                write_png(filename, data)   # noqa
            else:
                self.app.plotcanvas.figure.savefig(filename)

            if self.options["global_open_style"] is False:
                self.app.file_opened.emit("png", filename)
            self.app.file_saved.emit("png", filename)

    def on_file_save_gerber(self):
        """
        Callback for menu item in Project context menu.

        :return: None
        """
        self.log.debug("on_file_save_gerber()")

        obj = self.app.collection.get_active()
        if obj is None:
            self.inform.emit('[ERROR_NOTCL] %s' % _("No object is selected."))
            return

        # Check for more compatible types and add as required
        if not isinstance(obj, GerberObject):
            self.inform.emit('[ERROR_NOTCL] %s' % _("Failed. Only Gerber objects can be saved as Gerber files..."))
            return

        name = self.app.collection.get_active().obj_options["name"]

        _filter = "Gerber File (*.GBR);;Gerber File (*.GRB);;All Files (*.*)"
        try:
            filename, _f = FCFileSaveDialog.get_saved_filename(
                caption="Save Gerber source file",
                directory=self.app.get_last_save_folder() + '/' + name,
                ext_filter=_filter)
        except TypeError:
            filename, _f = FCFileSaveDialog.get_saved_filename(
                caption=_("Save Gerber source file"),
                ext_filter=_filter)

        filename = str(filename)

        if filename == "":
            self.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled."))
            return
        else:
            self.save_source_file(name, filename)
            if self.options["global_open_style"] is False:
                self.app.file_opened.emit("Gerber", filename)
            self.app.file_saved.emit("Gerber", filename)

    def on_file_save_script(self):
        """
        Callback for menu item in Project context menu.

        :return: None
        """
        self.log.debug("on_file_save_script()")

        obj = self.app.collection.get_active()
        if obj is None:
            self.inform.emit('[ERROR_NOTCL] %s' % _("No object is selected."))
            return

        # Check for more compatible types and add as required
        if not isinstance(obj, ScriptObject):
            self.inform.emit('[ERROR_NOTCL] %s' % _("Failed. Only Script objects can be saved as TCL Script files..."))
            return

        name = self.app.collection.get_active().obj_options["name"]

        _filter = "FlatCAM Scripts (*.FlatScript);;All Files (*.*)"
        try:
            filename, _f = FCFileSaveDialog.get_saved_filename(
                caption="Save Script source file",
                directory=self.app.get_last_save_folder() + '/' + name,
                ext_filter=_filter)
        except TypeError:
            filename, _f = FCFileSaveDialog.get_saved_filename(
                caption=_("Save Script source file"),
                ext_filter=_filter)

        filename = str(filename)

        if filename == "":
            self.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled."))
            return
        else:
            self.save_source_file(name, filename)
            if self.options["global_open_style"] is False:
                self.app.file_opened.emit("Script", filename)
            self.app.file_saved.emit("Script", filename)

    def on_file_save_document(self):
        """
        Callback for menu item in Project context menu.

        :return: None
        """
        self.log.debug("on_file_save_document()")

        obj = self.app.collection.get_active()
        if obj is None:
            self.inform.emit('[ERROR_NOTCL] %s' % _("No object is selected."))
            return

        # Check for more compatible types and add as required
        if not isinstance(obj, ScriptObject):
            self.inform.emit('[ERROR_NOTCL] %s' % _("Failed. Only Document objects can be saved as Document files..."))
            return

        name = self.app.collection.get_active().obj_options["name"]

        _filter = "FlatCAM Documents (*.FlatDoc);;All Files (*.*)"
        try:
            filename, _f = FCFileSaveDialog.get_saved_filename(
                caption="Save Document source file",
                directory=self.app.get_last_save_folder() + '/' + name,
                ext_filter=_filter)
        except TypeError:
            filename, _f = FCFileSaveDialog.get_saved_filename(
                caption=_("Save Document source file"),
                ext_filter=_filter)

        filename = str(filename)

        if filename == "":
            self.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled."))
            return
        else:
            self.save_source_file(name, filename)
            if self.options["global_open_style"] is False:
                self.app.file_opened.emit("Document", filename)
            self.app.file_saved.emit("Document", filename)

    def on_file_save_excellon(self):
        """
        Callback for menu item in project context menu.

        :return: None
        """
        self.log.debug("on_file_save_excellon()")

        obj = self.app.collection.get_active()
        if obj is None:
            self.inform.emit('[ERROR_NOTCL] %s' % _("No object is selected."))
            return

        # Check for more compatible types and add as required
        if not isinstance(obj, ExcellonObject):
            self.inform.emit('[ERROR_NOTCL] %s' % _("Failed. Only Excellon objects can be saved as Excellon files..."))
            return

        name = self.app.collection.get_active().obj_options["name"]

        _filter = "Excellon File (*.DRL);;Excellon File (*.TXT);;All Files (*.*)"
        try:
            filename, _f = FCFileSaveDialog.get_saved_filename(
                caption=_("Save Excellon source file"),
                directory=self.app.get_last_save_folder() + '/' + name,
                ext_filter=_filter)
        except TypeError:
            filename, _f = FCFileSaveDialog.get_saved_filename(
                caption=_("Save Excellon source file"), ext_filter=_filter)

        filename = str(filename)

        if filename == "":
            self.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled."))
            return
        else:
            self.save_source_file(name, filename)
            if self.options["global_open_style"] is False:
                self.app.file_opened.emit("Excellon", filename)
            self.app.file_saved.emit("Excellon", filename)

    def on_file_export_excellon(self):
        """
        Callback for menu item File->Export->Excellon.

        :return: None
        """
        self.log.debug("on_file_export_excellon()")

        obj = self.app.collection.get_active()
        if obj is None:
            self.inform.emit('[ERROR_NOTCL] %s' % _("No object is selected."))
            return

        # Check for more compatible types and add as required
        if not isinstance(obj, ExcellonObject):
            self.inform.emit('[ERROR_NOTCL] %s' % _("Failed. Only Excellon objects can be saved as Excellon files..."))
            return

        name = self.app.collection.get_active().obj_options["name"]

        _filter = self.options["excellon_save_filters"]
        try:
            filename, _f = FCFileSaveDialog.get_saved_filename(
                caption=_("Export Excellon"),
                directory=self.app.get_last_save_folder() + '/' + name,
                ext_filter=_filter)
        except TypeError:
            filename, _f = FCFileSaveDialog.get_saved_filename(
                caption=_("Export Excellon"),
                ext_filter=_filter)

        filename = str(filename)

        if filename == "":
            self.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled."))
            return
        else:
            used_extension = filename.rpartition('.')[2]
            obj.update_filters(last_ext=used_extension, filter_string='excellon_save_filters')

            self.export_excellon(name, filename)
            if self.options["global_open_style"] is False:
                self.app.file_opened.emit("Excellon", filename)
            self.app.file_saved.emit("Excellon", filename)

    def on_file_export_gerber(self):
        """
        Callback for menu item File->Export->Gerber.

        :return: None
        """
        self.log.debug("on_file_export_gerber()")

        obj = self.app.collection.get_active()
        if obj is None:
            self.inform.emit('[ERROR_NOTCL] %s' % _("No object is selected."))
            return

        # Check for more compatible types and add as required
        if not isinstance(obj, GerberObject):
            self.inform.emit('[ERROR_NOTCL] %s' % _("Failed. Only Gerber objects can be saved as Gerber files..."))
            return

        name = self.app.collection.get_active().obj_options["name"]

        _filter_ = self.options['gerber_save_filters']
        try:
            filename, _f = FCFileSaveDialog.get_saved_filename(
                caption=_("Export Gerber"),
                directory=self.app.get_last_save_folder() + '/' + name,
                ext_filter=_filter_)
        except TypeError:
            filename, _f = FCFileSaveDialog.get_saved_filename(
                caption=_("Export Gerber"),
                ext_filter=_filter_)

        filename = str(filename)

        if filename == "":
            self.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled."))
            return
        else:
            used_extension = filename.rpartition('.')[2]
            obj.update_filters(last_ext=used_extension, filter_string='gerber_save_filters')

            self.export_gerber(name, filename)
            if self.options["global_open_style"] is False:
                self.app.file_opened.emit("Gerber", filename)
            self.app.file_saved.emit("Gerber", filename)

    def on_file_export_dxf(self):
        """
                Callback for menu item File->Export DXF.

                :return: None
                """
        self.log.debug("on_file_export_dxf()")

        obj = self.app.collection.get_active()
        if obj is None:
            self.inform.emit('[ERROR_NOTCL] %s' % _("No object is selected."))
            return

        # Check for more compatible types and add as required
        if obj.kind != 'geometry':
            msg = _("Only Geometry objects can be used.")
            msgbox = FCMessageBox(parent=self.app.ui)
            msgbox.setWindowTitle(msg)  # taskbar still shows it
            msgbox.setWindowIcon(QtGui.QIcon(self.app.resource_location + '/app128.png'))

            msgbox.setInformativeText(msg)
            msgbox.setIconPixmap(QtGui.QPixmap(self.app.resource_location + '/waning.png'))

            msgbox.setIcon(QtWidgets.QMessageBox.Icon.Warning)

            msgbox.setInformativeText(msg)
            bt_ok = msgbox.addButton(_('Ok'), QtWidgets.QMessageBox.ButtonRole.AcceptRole)
            msgbox.setDefaultButton(bt_ok)
            msgbox.exec()
            return

        name = self.app.collection.get_active().obj_options["name"]

        _filter_ = "DXF File .dxf (*.DXF);;All Files (*.*)"
        try:
            filename, _f = FCFileSaveDialog.get_saved_filename(
                caption=_("Export DXF"),
                directory=self.app.get_last_save_folder() + '/' + name,
                ext_filter=_filter_)
        except TypeError:
            filename, _f = FCFileSaveDialog.get_saved_filename(
                caption=_("Export DXF"),
                ext_filter=_filter_)

        filename = str(filename)

        if filename == "":
            self.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled."))
            return
        else:
            self.export_dxf(name, filename)
            if self.options["global_open_style"] is False:
                self.app.file_opened.emit("DXF", filename)
            self.app.file_saved.emit("DXF", filename)

    def on_file_import_svg(self, type_of_obj):
        """
        Callback for menu item File->Import SVG.
        :param type_of_obj: to import the SVG as Geometry or as Gerber
        :type type_of_obj: str
        :return: None
        """
        self.log.debug("on_file_import_svg()")

        _filter_ = "SVG File .svg (*.svg);;All Files (*.*)"
        try:
            filenames, _f = QtWidgets.QFileDialog.getOpenFileNames(caption=_("Import SVG"),
                                                                   directory=self.app.get_last_folder(),
                                                                   filter=_filter_)
        except TypeError:
            filenames, _f = QtWidgets.QFileDialog.getOpenFileNames(caption=_("Import SVG"),
                                                                   filter=_filter_)

        if type_of_obj != "geometry" and type_of_obj != "gerber":
            type_of_obj = "geometry"

        filenames = [str(filename) for filename in filenames]

        if len(filenames) == 0:
            self.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled."))
        else:
            for filename in filenames:
                if filename != '':
                    self.worker_task.emit({'fcn': self.import_svg, 'params': [filename, type_of_obj]})

    def on_file_import_dxf(self, type_of_obj):
        """
        Callback for menu item File->Import DXF.
        :param type_of_obj: to import the DXF as Geometry or as Gerber
        :type type_of_obj: str
        :return: None
        """
        self.log.debug("on_file_import_dxf()")

        _filter_ = "DXF File .dxf (*.DXF);;All Files (*.*)"
        try:
            filenames, _f = QtWidgets.QFileDialog.getOpenFileNames(caption=_("Import DXF"),
                                                                   directory=self.app.get_last_folder(),
                                                                   filter=_filter_)
        except TypeError:
            filenames, _f = QtWidgets.QFileDialog.getOpenFileNames(caption=_("Import DXF"),
                                                                   filter=_filter_)

        if type_of_obj != "geometry" and type_of_obj != "gerber":
            type_of_obj = "geometry"

        filenames = [str(filename) for filename in filenames]

        if len(filenames) == 0:
            self.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled."))
        else:
            for filename in filenames:
                if filename != '':
                    self.worker_task.emit({'fcn': self.import_dxf, 'params': [filename, type_of_obj]})

    def on_file_new_click(self):
        """
        Callback for menu item File -> New.
        Executed on clicking the Menu -> File -> New Project

        :return:
        """
        self.log.debug("on_file_new_click()")

        if self.app.collection.get_list() and self.app.should_we_save:
            msgbox = FCMessageBox(parent=self.app.ui)
            title = _("Save changes")
            txt = _("There are files/objects opened.\n"
                    "Creating a New project will delete them.\n"
                    "Do you want to Save the project?")
            msgbox.setWindowTitle(title)  # taskbar still shows it
            msgbox.setWindowIcon(QtGui.QIcon(self.app.resource_location + '/app128.png'))
            msgbox.setText('<b>%s</b>' % title)
            msgbox.setInformativeText(txt)
            msgbox.setIconPixmap(QtGui.QPixmap(self.app.resource_location + '/save_as.png'))

            bt_yes = msgbox.addButton(_('Yes'), QtWidgets.QMessageBox.ButtonRole.YesRole)
            bt_no = msgbox.addButton(_('No'), QtWidgets.QMessageBox.ButtonRole.NoRole)
            bt_cancel = msgbox.addButton(_('Cancel'), QtWidgets.QMessageBox.ButtonRole.RejectRole)

            msgbox.setDefaultButton(bt_yes)
            msgbox.exec()
            response = msgbox.clickedButton()

            if response == bt_yes:
                self.on_file_save_project_as(use_thread=True)
            elif response == bt_cancel:
                return
            elif response == bt_no:
                self.on_file_new_project(use_thread=True)
        else:
            self.on_file_new_project(use_thread=True)

    def on_file_new_project(self, cli=None, reset_tcl=True, use_thread=None, keep_scripts=True):
        """
        Returns the application to its startup state. This method is thread-safe.

        :param cli:         Boolean. If True this method was run from command line
        :param reset_tcl:   Boolean. If False, on new project creation the Tcl instance is not recreated, therefore it
                            will remember all the previous variables. If True then the Tcl is re-instantiated.
        :param use_thread:  Bool. If True some part of the initialization are done threaded
        :param keep_scripts: Bool. If True the Script objects are not deleted when creating a new project
        :return:            None
        """

        self.log.debug("on_file_new_project()")

        t_start_proj = time.time()

        # close any editor that might be open
        if self.app.call_source != 'app':
            self.app.on_editing_finished(cleanup=True)
            # ## EDITOR section
            self.app.geo_editor = AppGeoEditor(self.app)
            self.app.exc_editor = AppExcEditor(self.app)
            self.app.grb_editor = AppGerberEditor(self.app)

        for obj in self.app.collection.get_list():
            # delete shapes left drawn from mark shape_collections, if any
            if isinstance(obj, GerberObject):
                try:
                    obj.mark_shapes_storage.clear()
                    obj.mark_shapes.clear(update=True)
                    obj.mark_shapes.enabled = False
                except AttributeError:
                    pass

            # also delete annotation shapes, if any
            elif isinstance(obj, CNCJobObject):
                try:
                    obj.text_col.enabled = False
                    del obj.text_col
                    obj.annotation.clear(update=True)
                    del obj.annotation
                except AttributeError:
                    pass

        # clear the possible drawn probing shapes for Levelling Tool
        try:
            self.app.levelling_tool.probing_shapes.clear(update=True)
        except AttributeError:
            pass

        # clean possible tool shapes for Isolation, NCC, Paint, Punch Gerber Plugins
        try:
            self.app.tool_shapes.clear(update=True)
        except AttributeError:
            pass

        # delete the exclusion areas
        self.app.exc_areas.clear_shapes()

        # delete any selection shape on canvas
        self.app.delete_selection_shape()

        # delete any hover shapes on canvas
        try:
            self.app.hover_shapes.clear(update=True)
        except AttributeError:
            pass

        # delete all App objects
        if keep_scripts is True:
            for prj_obj in self.app.collection.get_list():
                if prj_obj.kind != 'script':
                    self.app.collection.delete_by_name(prj_obj.obj_options['name'], select_project=False)
        else:
            self.app.collection.delete_all()

        self.log.debug('%s: %s %s.' %
                       ("Deleted all the application objects", str(time.time() - t_start_proj), _("seconds")))

        # add in Selected tab an initial text that describe the flow of work in FlatCAm
        self.app.setup_default_properties_tab()

        # Clear project filename
        self.app.project_filename = None

        default_file = self.app.defaults_path()
        # Load the application options
        self.options.load(filename=default_file, inform=self.inform)

        # Re-fresh project options
        self.app.on_defaults2options()

        if use_thread is True:
            self.app.new_project_signal.emit()
        else:
            t0 = time.time()
            # Clear pool
            self.app.clear_pool()

            # Init FlatCAMTools
            if reset_tcl is True:
                self.app.init_tools(init_tcl=True)
            else:
                self.app.init_tools(init_tcl=False)
            self.log.debug(
                '%s: %s %s.' % ("Initiated the MP pool and plugins in: ", str(time.time() - t0), _("seconds")))

            # tcl needs to be reinitialized, otherwise old shell variables etc  remains
            # self.app.shell.init_tcl()

        # Try to close all tabs in the PlotArea but only if the appGUI is active (CLI is None)
        if cli is None:
            # we need to go in reverse because once we remove a tab then the index changes
            # meaning that removing the first tab (idx = 0) then the tab at former idx = 1 will assume idx = 0
            # and so on. Therefore, the deletion should be done in reverse
            wdg_count = self.app.ui.plot_tab_area.tabBar.count() - 1
            for index in range(wdg_count, -1, -1):
                try:
                    self.app.ui.plot_tab_area.closeTab(index)
                except Exception as e:
                    self.log.error("App.on_file_new_project() --> %s" % str(e))

            # # And then add again the Plot Area
            self.app.ui.plot_tab_area.insertTab(0, self.app.ui.plot_tab, _("Plot Area"))
            self.app.ui.plot_tab_area.protectTab(0)

        # take the focus of the Notebook on Project Tab.
        self.app.ui.notebook.setCurrentWidget(self.app.ui.project_tab)

        self.log.debug('%s: %s %s.' % (_("Project created in"), str(time.time() - t_start_proj), _("seconds")))
        self.app.ui.set_ui_title(name=_("New Project - Not saved"))

        self.inform.emit('[success] %s...' % _("New Project created"))

    def on_new_project_house_keeping(self):
        """
        Do dome of the new project initialization in a threaded way

        :return:
        :rtype:
        """
        t0 = time.time()

        # Clear pool
        self.log.debug("New Project: cleaning multiprocessing pool.")
        self.app.clear_pool()

        # Init FlatCAMTools
        self.log.debug("New Project: initializing the Tools and Tcl Shell.")
        self.app.init_tools(init_tcl=True)
        self.log.debug('%s: %s %s.' % ("Initiated the MP pool and plugins in: ", str(time.time() - t0), _("seconds")))

    def on_file_new_script(self, silent=False):
        """
        Will create a new script file and open it in the Code Editor

        :param silent:  if True will not display status messages
        :return:        None
        """
        self.log.debug("on_file_new_script()")

        if silent is False:
            self.inform.emit('[success] %s' % _("New TCL script file created in Code Editor."))

        # hide coordinates toolbars in the infobar while in DB
        self.app.ui.coords_toolbar.hide()
        self.app.ui.delta_coords_toolbar.hide()

        self.app.app_obj.new_script_object()

    def on_file_open_script(self, name=None, silent=False):
        """
        Will open a Tcl script file into the Code Editor

        :param silent:  if True will not display status messages
        :param name:    name of a Tcl script file to open
        :return:        None
        """

        self.log.debug("on_file_open_script()")

        _filter_ = "TCL script .FlatScript (*.FlatScript);;TCL script .tcl (*.TCL);;TCL script .txt (*.TXT);;" \
                   "All Files (*.*)"

        if name:
            filenames = [name]
        else:
            try:
                filenames, _f = QtWidgets.QFileDialog.getOpenFileNames(
                    caption=_("Open TCL script"), directory=self.app.get_last_folder(), filter=_filter_)
            except TypeError:
                filenames, _f = QtWidgets.QFileDialog.getOpenFileNames(caption=_("Open TCL script"), filter=_filter_)

        if len(filenames) == 0:
            if silent is False:
                self.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled."))
        else:
            for filename in filenames:
                if filename != '':
                    self.worker_task.emit({'fcn': self.open_script, 'params': [filename]})

    def on_file_open_script_example(self, name=None, silent=False):
        """
        Will open a Tcl script file into the Code Editor

        :param silent: if True will not display status messages
        :param name: name of a Tcl script file to open
        :return:
        """

        self.log.debug("on_file_open_script_example()")

        _filter_ = "TCL script .FlatScript (*.FlatScript);;TCL script .tcl (*.TCL);;TCL script .txt (*.TXT);;" \
                   "All Files (*.*)"

        # test if the app was frozen and choose the path for the configuration file
        if getattr(sys, "frozen", False) is True:
            example_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__))) + '\\assets\\examples'
        else:
            example_path = os.path.dirname(os.path.realpath(__file__)) + '\\assets\\examples'

        if name:
            filenames = [name]
        else:
            try:
                filenames, _f = QtWidgets.QFileDialog.getOpenFileNames(
                    caption=_("Open TCL script"), directory=example_path, filter=_filter_)
            except TypeError:
                filenames, _f = QtWidgets.QFileDialog.getOpenFileNames(caption=_("Open TCL script"), filter=_filter_)

        if len(filenames) == 0:
            if silent is False:
                self.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled."))
        else:
            for filename in filenames:
                if filename != '':
                    self.worker_task.emit({'fcn': self.open_script, 'params': [filename]})

    def on_file_run_cript(self, name=None, silent=False):
        """
        File menu callback for loading and running a TCL script.

        :param silent: if True will not display status messages
        :param name: name of a Tcl script file to be run by FlatCAM
        :return: None
        """

        self.log.debug("on_file_runscript()")

        if name:
            filename = name
            if self.app.cmd_line_headless != 1:
                self.splash.showMessage('%s: %ssec\n%s' %
                                        (_("Canvas initialization started.\n"
                                           "Canvas initialization finished in"), '%.2f' % self.app.used_time,
                                         _("Executing ScriptObject file.")
                                         ),
                                        alignment=Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft,
                                        color=QtGui.QColor("lightgray"))
        else:
            _filter_ = "TCL script .FlatScript (*.FlatScript);;TCL script .tcl (*.TCL);;TCL script .txt (*.TXT);;" \
                       "All Files (*.*)"
            try:
                filename, _f = QtWidgets.QFileDialog.getOpenFileName(caption=_("Run TCL script"),
                                                                     directory=self.app.get_last_folder(),
                                                                     filter=_filter_)
            except TypeError:
                filename, _f = QtWidgets.QFileDialog.getOpenFileName(caption=_("Run TCL script"), filter=_filter_)

        # The Qt methods above will return a QString which can cause problems later.
        # So far json.dump() will fail to serialize it.
        filename = str(filename)

        if filename == "":
            if silent is False:
                self.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled."))
        else:
            if self.app.cmd_line_headless != 1:
                if self.app.ui.shell_dock.isHidden():
                    self.app.ui.shell_dock.show()

            try:
                with open(filename, "r") as tcl_script:
                    cmd_line_shell_file_content = tcl_script.read()
                    if self.app.cmd_line_headless != 1:
                        self.app.shell.exec_command(cmd_line_shell_file_content)
                    else:
                        self.app.shell.exec_command(cmd_line_shell_file_content, no_echo=True)

                if silent is False:
                    self.inform.emit('[success] %s' % _("TCL script file opened in Code Editor and executed."))
            except Exception as e:
                self.app.error("App.on_file_run_cript() -> %s" % str(e))
                sys.exit(2)

    def on_file_save_project(self, silent=False):
        """
        Callback for menu item File->Save Project. Saves the project to
        ``self.project_filename`` or calls ``self.on_file_save_project_as()``
        if set to None. The project is saved by calling ``self.save_project()``.

        :param silent: if True will not display status messages
        :return: None
        """
        self.log.debug("on_file_save_project()")

        if self.app.project_filename is None:
            self.on_file_save_project_as()
        else:
            self.worker_task.emit({'fcn': self.save_project, 'params': [self.app.project_filename, silent]})
            if self.options["global_open_style"] is False:
                self.app.file_opened.emit("project", self.app.project_filename)
            self.app.file_saved.emit("project", self.app.project_filename)

        self.app.ui.set_ui_title(name=self.app.project_filename)

        self.app.should_we_save = False

    def on_file_save_project_as(self, make_copy=False, use_thread=True, quit_action=False):
        """
        Save the project to a given file by opening a file chooser via self.save_project().

        :param make_copy: boolean, whether to make a copy of the project
        :param use_thread: boolean, whether to run in a separate thread
        :param quit_action: boolean, whether to quit the application after
        :return: None """
        self.log.debug("on_file_save_project_as()")

        date = str(datetime.today()).rpartition('.')[0]
        date = ''.join(c for c in date if c not in ':-')
        date = date.replace(' ', '_')

        filter_ = "FlatCAM Project .FlatPrj (*.FlatPrj);; All Files (*.*)"
        try:
            filename, _f = FCFileSaveDialog.get_saved_filename(
                caption=_("Save Project As ..."),
                directory='{l_save}/{proj}_{date}'.format(l_save=str(self.app.get_last_save_folder()), date=date,
                                                          proj=_("Project")),
                ext_filter=filter_
            )
        except TypeError:
            filename, _f = FCFileSaveDialog.get_saved_filename(
                caption=_("Save Project As ..."),
                ext_filter=filter_)

        filename = str(filename)

        if filename == '':
            self.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled."))
            return

        if use_thread is True:
            self.worker_task.emit({'fcn': self.save_project, 'params': [filename, quit_action]})
        else:
            self.save_project(filename, quit_action)

        # self.save_project(filename)
        if self.options["global_open_style"] is False:
            self.app.file_opened.emit("project", filename)
        self.app.file_saved.emit("project", filename)

        if not make_copy:
            self.app.project_filename = filename

        self.app.ui.set_ui_title(name=self.app.project_filename)
        self.app.should_we_save = False

    def on_file_save_objects_pdf(self, use_thread=True):
        self.log.debug("on_file_save_objects_pdf()")

        date = str(datetime.today()).rpartition('.')[0]
        date = ''.join(c for c in date if c not in ':-')
        date = date.replace(' ', '_')

        try:
            obj_selection = self.app.collection.get_selected()
            if len(obj_selection) == 1:
                obj_name = str(obj_selection[0].obj_options['name'])
            else:
                obj_name = _("General_print")
        except AttributeError as att_err:
            self.log.debug("App.on_file_save_object_pdf() --> %s" % str(att_err))
            self.inform.emit('[ERROR_NOTCL] %s' % _("Failed."))
            return

        if not obj_selection:
            self.inform.emit(
                '[WARNING_NOTCL] %s %s' % (_("No object is selected."), _("Print everything in the workspace.")))
            obj_selection = self.app.collection.get_list()

        filter_ = "PDF File .pdf (*.PDF);; All Files (*.*)"
        try:
            filename, _f = FCFileSaveDialog.get_saved_filename(
                caption=_("Save Object as PDF ..."),
                directory='{l_save}/{obj_name}_{date}'.format(l_save=str(self.app.get_last_save_folder()),
                                                              obj_name=obj_name,
                                                              date=date),
                ext_filter=filter_
            )
        except TypeError:
            filename, _f = FCFileSaveDialog.get_saved_filename(
                caption=_("Save Object as PDF ..."),
                ext_filter=filter_)

        filename = str(filename)

        if filename == '':
            self.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled."))
            return

        if use_thread is True:
            self.app.proc_container.new(_("Printing PDF ..."))
            self.worker_task.emit({'fcn': self.save_pdf, 'params': [filename, obj_selection]})
        else:
            self.save_pdf(filename, obj_selection)

        # self.save_project(filename)
        if self.options["global_open_style"] is False:
            self.app.file_opened.emit("pdf", filename)
        self.app.file_saved.emit("pdf", filename)

    def save_pdf(self, file_name, obj_selection):
        self.log.debug("save_pdf()")

        p_size = self.options['global_workspaceT']
        orientation = self.options['global_workspace_orientation']
        color = 'black'
        transparency_level = 1.0

        self.pagesize.update(
            {
                'Bounds': None,
                'A0': (841 * mm, 1189 * mm),
                'A1': (594 * mm, 841 * mm),
                'A2': (420 * mm, 594 * mm),
                'A3': (297 * mm, 420 * mm),
                'A4': (210 * mm, 297 * mm),
                'A5': (148 * mm, 210 * mm),
                'A6': (105 * mm, 148 * mm),
                'A7': (74 * mm, 105 * mm),
                'A8': (52 * mm, 74 * mm),
                'A9': (37 * mm, 52 * mm),
                'A10': (26 * mm, 37 * mm),

                'B0': (1000 * mm, 1414 * mm),
                'B1': (707 * mm, 1000 * mm),
                'B2': (500 * mm, 707 * mm),
                'B3': (353 * mm, 500 * mm),
                'B4': (250 * mm, 353 * mm),
                'B5': (176 * mm, 250 * mm),
                'B6': (125 * mm, 176 * mm),
                'B7': (88 * mm, 125 * mm),
                'B8': (62 * mm, 88 * mm),
                'B9': (44 * mm, 62 * mm),
                'B10': (31 * mm, 44 * mm),

                'C0': (917 * mm, 1297 * mm),
                'C1': (648 * mm, 917 * mm),
                'C2': (458 * mm, 648 * mm),
                'C3': (324 * mm, 458 * mm),
                'C4': (229 * mm, 324 * mm),
                'C5': (162 * mm, 229 * mm),
                'C6': (114 * mm, 162 * mm),
                'C7': (81 * mm, 114 * mm),
                'C8': (57 * mm, 81 * mm),
                'C9': (40 * mm, 57 * mm),
                'C10': (28 * mm, 40 * mm),

                # American paper sizes
                'LETTER': (8.5 * inch, 11 * inch),
                'LEGAL': (8.5 * inch, 14 * inch),
                'ELEVENSEVENTEEN': (11 * inch, 17 * inch),

                # From https://en.wikipedia.org/wiki/Paper_size
                'JUNIOR_LEGAL': (5 * inch, 8 * inch),
                'HALF_LETTER': (5.5 * inch, 8 * inch),
                'GOV_LETTER': (8 * inch, 10.5 * inch),
                'GOV_LEGAL': (8.5 * inch, 13 * inch),
                'LEDGER': (17 * inch, 11 * inch),
            }
        )

        # make sure that the Excellon objects are drawn on top of everything
        excellon_objs = [obj for obj in obj_selection if obj.kind == 'excellon']
        cncjob_objs = [obj for obj in obj_selection if obj.kind == 'cncjob']
        # reverse the object order such that the first selected is on top
        rest_objs = [obj for obj in obj_selection if obj.kind != 'excellon' and obj.kind != 'cncjob'][::-1]
        obj_selection = rest_objs + cncjob_objs + excellon_objs

        # generate the SVG files from the application objects
        exported_svg = []
        for obj in obj_selection:
            svg_obj = obj.export_svg(scale_stroke_factor=0.0)

            if obj.kind.lower() == 'gerber' or obj.kind.lower() == 'excellon':
                color = obj.fill_color[:-2]
                transparency_level = obj.fill_color[-2:]
            elif obj.kind.lower() == 'geometry':
                color = self.options["global_draw_color"]

            # Change the attributes of the exported SVG
            # We don't need stroke-width
            # We set opacity to maximum
            # We set the colour to WHITE

            try:
                root = ET.fromstring(svg_obj)
            except Exception as e:
                self.log.debug("AppIO.save_pdf() -> Missing root node -> %s" % str(e))
                self.app.inform.emit("[ERROR_NOTCL] %s" % _("Failed."))
                return

            for child in root:
                child.set('fill', str(color))
                child.set('opacity', str(transparency_level))
                child.set('stroke', str(color))

            exported_svg.append(ET.tostring(root))

        xmin = Inf
        ymin = Inf
        xmax = -Inf
        ymax = -Inf

        for obj in obj_selection:
            try:
                g_xmin, g_ymin, g_xmax, g_ymax = obj.bounds()
                xmin = min([xmin, g_xmin])
                ymin = min([ymin, g_ymin])
                xmax = max([xmax, g_xmax])
                ymax = max([ymax, g_ymax])
            except Exception as e:
                self.log.error("Tried to get bounds of empty geometry in App.save_pdf(). %s" % str(e))

        # Determine bounding area for svg export
        bounds = [xmin, ymin, xmax, ymax]
        size = bounds[2] - bounds[0], bounds[3] - bounds[1]

        # This contains the measure units
        uom = obj_selection[0].units.lower()

        # Define a boundary around SVG of about 1.0mm (~39mils)
        if uom in "mm":
            boundary = 1.0
        else:
            boundary = 0.0393701

        # Convert everything to strings for use in the xml doc
        svgwidth = str(size[0] + (2 * boundary))
        svgheight = str(size[1] + (2 * boundary))
        minx = str(bounds[0] - boundary)
        miny = str(bounds[1] + boundary + size[1])

        # Add an SVG Header and footer to the svg output from shapely
        # The transform flips the Y Axis so that everything renders
        # properly within svg apps such as inkscape
        svg_header = '<svg xmlns="http://www.w3.org/2000/svg" ' \
                     'version="1.1" xmlns:xlink="http://www.w3.org/1999/xlink" '
        svg_header += 'width="' + svgwidth + uom + '" '
        svg_header += 'height="' + svgheight + uom + '" '
        svg_header += 'viewBox="' + minx + ' -' + miny + ' ' + svgwidth + ' ' + svgheight + '" '
        svg_header += '>'
        svg_header += '<g transform="scale(1,-1)">'
        svg_footer = '</g> </svg>'

        svg_elem = str(svg_header)
        for svg_item in exported_svg:
            svg_elem += str(svg_item)
        svg_elem += str(svg_footer)

        # Parse the xml through a xml parser just to add line feeds
        # and to make it look more pretty for the output
        doc = parse_xml_string(svg_elem)
        doc_final = doc.toprettyxml()

        try:
            if self.app_units.upper() == 'IN':
                unit = inch
            else:
                unit = mm

            doc_final = StringIO(doc_final)
            drawing = svg2rlg(doc_final)

            if p_size == 'Bounds':
                renderPDF.drawToFile(drawing, file_name)
            else:
                if orientation == 'p':
                    page_size = portrait(self.pagesize[p_size])
                else:
                    page_size = landscape(self.pagesize[p_size])

                my_canvas = canvas.Canvas(file_name, pagesize=page_size)
                my_canvas.translate(bounds[0] * unit, bounds[1] * unit)
                renderPDF.draw(drawing, my_canvas, 0, 0)
                my_canvas.save()
        except Exception as e:
            self.log.error("AppIO.save_pdf() --> PDF output --> %s" % str(e))
            return 'fail'

        self.inform.emit('[success] %s: %s' % (_("PDF file saved to"), file_name))

    def export_svg(self, obj_name, filename, scale_stroke_factor=0.00):
        """
        Exports a Geometry Object to an SVG file.

        :param obj_name: the name of the FlatCAM object to be saved as SVG
        :param filename: Path to the SVG file to save to.
        :param scale_stroke_factor: factor by which to change/scale the thickness of the features
        :return:
        """
        if filename is None:
            filename = self.app.options["global_last_save_folder"] if \
                self.app.options["global_last_save_folder"] is not None else self.app.options["global_last_folder"]

        self.log.debug("export_svg()")

        try:
            obj = self.app.collection.get_by_name(str(obj_name))
        except Exception:
            return 'fail'

        with self.app.proc_container.new(_("Exporting ...")):
            exported_svg = obj.export_svg(scale_stroke_factor=scale_stroke_factor)

            # Determine bounding area for svg export
            bounds = obj.bounds()
            size = obj.size()

            # Convert everything to strings for use in the xml doc
            svg_width = str(size[0])
            svg_height = str(size[1])
            minx = str(bounds[0])
            miny = str(bounds[1] - size[1])
            uom = obj.units.lower()

            # Add an SVG Header and footer to the svg output from shapely
            # The transform flips the Y Axis so that everything renders
            # properly within svg apps such as inkscape
            svg_header = '<svg xmlns="http://www.w3.org/2000/svg" ' \
                         'version="1.1" xmlns:xlink="http://www.w3.org/1999/xlink" '
            svg_header += 'width="' + svg_width + uom + '" '
            svg_header += 'height="' + svg_height + uom + '" '
            svg_header += 'viewBox="' + minx + ' ' + miny + ' ' + svg_width + ' ' + svg_height + '">'
            svg_header += '<g transform="scale(1,-1)">'
            svg_footer = '</g> </svg>'
            svg_elem = svg_header + exported_svg + svg_footer

            # Parse the xml through a xml parser just to add line feeds
            # and to make it look more pretty for the output
            svg_code = parse_xml_string(svg_elem)
            svg_code = svg_code.toprettyxml()

            try:
                with open(filename, 'w') as fp:
                    fp.write(svg_code)
            except PermissionError:
                self.inform.emit('[WARNING] %s' %
                                 _("Permission denied, saving not possible.\n"
                                   "Most likely another app is holding the file open and not accessible."))
                return 'fail'

            if self.options["global_open_style"] is False:
                self.app.file_opened.emit("SVG", filename)
            self.app.file_saved.emit("SVG", filename)
            self.inform.emit('[success] %s: %s' % (_("SVG file exported to"), filename))

    def on_import_preferences(self):
        """
        Loads the application default settings from a saved file into
        ``self.options`` dictionary.

        :return: None
        """

        self.log.debug("App.on_import_preferences()")

        # Show file chooser
        filter_ = "Config File (*.FlatConfig);;All Files (*.*)"
        try:
            filename, _f = QtWidgets.QFileDialog.getOpenFileName(caption=_("Import FlatCAM Preferences"),
                                                                 directory=self.app.data_path,
                                                                 filter=filter_)
        except TypeError:
            filename, _f = QtWidgets.QFileDialog.getOpenFileName(caption=_("Import FlatCAM Preferences"),
                                                                 filter=filter_)
        filename = str(filename)
        if filename == "":
            self.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled."))
            return

        # Load in the options from the chosen file
        self.options.load(filename=filename, inform=self.inform)

        self.app.preferencesUiManager.on_preferences_edited()
        self.inform.emit('[success] %s: %s' % (_("Imported Defaults from"), filename))

    def on_export_preferences(self):
        """
        Save the options dictionary to a file.

        :return: None
        """
        self.log.debug("on_export_preferences()")

        # defaults_file_content = None

        # Show file chooser
        date = str(datetime.today()).rpartition('.')[0]
        date = ''.join(c for c in date if c not in ':-')
        date = date.replace(' ', '_')
        filter__ = "Config File .FlatConfig (*.FlatConfig);;All Files (*.*)"
        try:
            filename, _f = FCFileSaveDialog.get_saved_filename(
                caption=_("Export FlatCAM Preferences"),
                directory=os.path.join(self.app.data_path, 'preferences_%s' % date),
                ext_filter=filter__
            )
        except TypeError:
            filename, _f = FCFileSaveDialog.get_saved_filename(
                caption=_("Export FlatCAM Preferences"), ext_filter=filter__)
        filename = str(filename)
        if filename == "":
            self.inform.emit('[WARNING_NOTCL] %s' % _("Cancelled."))
            return 'fail'

        # Update options
        self.app.preferencesUiManager.defaults_read_form()
        self.options.propagate_defaults()

        # Save update options
        try:
            self.options.write(filename=filename)
        except Exception:
            self.inform.emit('[ERROR_NOTCL] %s %s' % (_("Failed to write defaults to file."), str(filename)))
            return

        if self.options["global_open_style"] is False:
            self.app.file_opened.emit("preferences", filename)
        self.app.file_saved.emit("preferences", filename)
        self.inform.emit('[success] %s: %s' % (_("Exported preferences to"), filename))

    def export_excellon(self, obj_name, filename, local_use=None, use_thread=True):
        """
        Exports an Excellon Object to an Excellon file.

        :param obj_name: the name of the FlatCAM object to be saved as Excellon
        :param filename: Path to the Excellon file to save to.
        :param local_use:
        :param use_thread: if to be run in a separate thread
        :return:
        """

        if filename is None:
            if self.app.options["global_last_save_folder"]:
                filename = self.app.options["global_last_save_folder"] + '/' + 'exported_excellon'
            else:
                filename = self.app.options["global_last_folder"] + '/' + 'exported_excellon'

        self.log.debug("export_excellon()")

        format_exc = ';FILE_FORMAT=%d:%d\n' % (self.options["excellon_exp_integer"],
                                               self.options["excellon_exp_decimals"]
                                               )

        if local_use is None:
            try:
                obj = self.app.collection.get_by_name(str(obj_name))
            except Exception:
                return "Could not retrieve object: %s" % obj_name
        else:
            obj = local_use

        if not isinstance(obj, ExcellonObject):
            self.inform.emit('[ERROR_NOTCL] %s' %
                             _("Failed. Only Excellon objects can be saved as Excellon files..."))
            return

        # updated units
        e_units = self.options["excellon_exp_units"]
        e_whole = self.options["excellon_exp_integer"]
        e_fract = self.options["excellon_exp_decimals"]
        e_zeros = self.options["excellon_exp_zeros"]
        e_format = self.options["excellon_exp_format"]
        slot_type = self.options["excellon_exp_slot_type"]

        fc_units = self.app_units.upper()
        if fc_units == 'MM':
            factor = 1 if e_units == 'METRIC' else 0.03937
        else:
            factor = 25.4 if e_units == 'METRIC' else 1

        def make_excellon():
            try:
                time_str = "{:%A, %d %B %Y at %H:%M}".format(datetime.now())

                header = 'M48\n'
                header += ';EXCELLON GENERATED BY FLATCAM v%s - www.flatcam.org - Version Date: %s\n' % \
                          (str(self.app.version), str(self.app.version_date))

                header += ';Filename: %s' % str(obj_name) + '\n'
                header += ';Created on : %s' % time_str + '\n'

                if e_format == 'dec':
                    has_slots, excellon_code = obj.export_excellon(e_whole, e_fract, factor=factor, slot_type=slot_type)
                    header += e_units + '\n'

                    for tool in obj.tools:
                        if e_units == 'METRIC':
                            header += "T{tool}F00S00C{:.{dec}f}\n".format(float(obj.tools[tool]['tooldia']) * factor,
                                                                          tool=str(tool),
                                                                          dec=2)
                        else:
                            header += "T{tool}F00S00C{:.{dec}f}\n".format(float(obj.tools[tool]['tooldia']) * factor,
                                                                          tool=str(tool),
                                                                          dec=4)
                else:
                    if e_zeros == 'LZ':
                        has_slots, excellon_code = obj.export_excellon(e_whole, e_fract,
                                                                       form='ndec', e_zeros='LZ', factor=factor,
                                                                       slot_type=slot_type)
                        header += '%s,%s\n' % (e_units, 'LZ')
                        header += format_exc

                        for tool in obj.tools:
                            if e_units == 'METRIC':
                                header += "T{tool}F00S00C{:.{dec}f}\n".format(
                                    float(obj.tools[tool]['tooldia']) * factor,
                                    tool=str(tool),
                                    dec=2)
                            else:
                                header += "T{tool}F00S00C{:.{dec}f}\n".format(
                                    float(obj.tools[tool]['tooldia']) * factor,
                                    tool=str(tool),
                                    dec=4)
                    else:
                        has_slots, excellon_code = obj.export_excellon(e_whole, e_fract,
                                                                       form='ndec', e_zeros='TZ', factor=factor,
                                                                       slot_type=slot_type)
                        header += '%s,%s\n' % (e_units, 'TZ')
                        header += format_exc

                        for tool in obj.tools:
                            if e_units == 'METRIC':
                                header += "T{tool}F00S00C{:.{dec}f}\n".format(
                                    float(obj.tools[tool]['tooldia']) * factor,
                                    tool=str(tool),
                                    dec=2)
                            else:
                                header += "T{tool}F00S00C{:.{dec}f}\n".format(
                                    float(obj.tools[tool]['tooldia']) * factor,
                                    tool=str(tool),
                                    dec=4)
                header += '%\n'
                footer = 'M30\n'

                exported_excellon = header
                exported_excellon += excellon_code
                exported_excellon += footer

                if local_use is None:
                    try:
                        with open(filename, 'w') as fp:
                            fp.write(exported_excellon)
                    except PermissionError:
                        self.inform.emit('[WARNING] %s' %
                                         _("Permission denied, saving not possible.\n"
                                           "Most likely another app is holding the file open and not accessible."))
                        return 'fail'

                    if self.options["global_open_style"] is False:
                        self.app.file_opened.emit("Excellon", filename)
                    self.app.file_saved.emit("Excellon", filename)
                    self.inform.emit('[success] %s: %s' % (_("Excellon file exported to"), filename))
                else:
                    return exported_excellon
            except Exception as e:
                self.log.error("App.export_excellon.make_excellon() --> %s" % str(e))
                return 'fail'

        if use_thread is True:

            with self.app.proc_container.new(_("Exporting ...")):

                def job_thread_exc(app_obj):
                    ret = make_excellon()
                    if ret == 'fail':
                        app_obj.inform.emit('[ERROR_NOTCL] %s' % _('Could not export.'))
                        return

                self.worker_task.emit({'fcn': job_thread_exc, 'params': [self]})
        else:
            ret_val = make_excellon()
            if ret_val == 'fail':
                self.inform.emit('[ERROR_NOTCL] %s' % _('Could not export.'))
                return 'fail'
            if local_use is not None:
                return ret_val

    def export_gerber(self, obj_name, filename, local_use=None, use_thread=True):
        """
        Exports a Gerber Object to a Gerber file.

        :param obj_name:    the name of the FlatCAM object to be saved as Gerber
        :param filename:    Path to the Gerber file to save to.
        :param local_use:   if the Gerber code is to be saved to a file (None) or used within FlatCAM.
                            When not None, the value will be the actual Gerber object for which to create
                            the Gerber code
        :param use_thread:  if to be run in a separate thread
        :return:
        """
        if filename is None:
            filename = self.app.options["global_last_save_folder"] if \
                self.app.options["global_last_save_folder"] is not None else self.app.options["global_last_folder"]

        self.log.debug("export_gerber()")

        if local_use is None:
            try:
                obj = self.app.collection.get_by_name(str(obj_name))
            except Exception:
                return 'fail'
        else:
            obj = local_use

        # updated units
        g_units = self.options["gerber_exp_units"]
        g_whole = self.options["gerber_exp_integer"]
        g_fract = self.options["gerber_exp_decimals"]
        g_zeros = self.options["gerber_exp_zeros"]

        fc_units = self.app_units.upper()
        if fc_units == 'MM':
            factor = 1 if g_units == 'MM' else 0.03937
        else:
            factor = 25.4 if g_units == 'MM' else 1

        def make_gerber():
            try:
                time_str = "{:%A, %d %B %Y at %H:%M}".format(datetime.now())

                header = 'G04*\n'
                header += 'G04 RS-274X GERBER GENERATED BY FLATCAM v%s - www.flatcam.org - Version Date: %s*\n' % \
                          (str(self.app.version), str(self.app.version_date))

                header += 'G04 Filename: %s*' % str(obj_name) + '\n'
                header += 'G04 Created on : %s*' % time_str + '\n'
                header += '%%FS%sAX%s%sY%s%s*%%\n' % (g_zeros, g_whole, g_fract, g_whole, g_fract)
                header += "%MO{units}*%\n".format(units=g_units)

                for apid in obj.tools:
                    if obj.tools[apid]['type'] == 'C':
                        header += "%ADD{apid}{type},{size}*%\n".format(
                            apid=str(apid),
                            type='C',
                            size=(factor * obj.tools[apid]['size'])
                        )
                    elif obj.tools[apid]['type'] == 'R':
                        header += "%ADD{apid}{type},{width}X{height}*%\n".format(
                            apid=str(apid),
                            type='R',
                            width=(factor * obj.tools[apid]['width']),
                            height=(factor * obj.tools[apid]['height'])
                        )
                    elif obj.tools[apid]['type'] == 'O':
                        header += "%ADD{apid}{type},{width}X{height}*%\n".format(
                            apid=str(apid),
                            type='O',
                            width=(factor * obj.tools[apid]['width']),
                            height=(factor * obj.tools[apid]['height'])
                        )

                header += '\n'

                # obsolete units but some software may need it
                if g_units == 'IN':
                    header += 'G70*\n'
                else:
                    header += 'G71*\n'

                # Absolute Mode
                header += 'G90*\n'

                header += 'G01*\n'
                # positive polarity
                header += '%LPD*%\n'

                footer = 'M02*\n'

                gerber_code = obj.export_gerber(g_whole, g_fract, g_zeros=g_zeros, factor=factor)

                exported_gerber = header
                exported_gerber += gerber_code
                exported_gerber += footer

                if local_use is None:
                    try:
                        with open(filename, 'w') as fp:
                            fp.write(exported_gerber)
                    except PermissionError:
                        self.inform.emit('[WARNING] %s' %
                                         _("Permission denied, saving not possible.\n"
                                           "Most likely another app is holding the file open and not accessible."))
                        return 'fail'

                    if self.options["global_open_style"] is False:
                        self.app.file_opened.emit("Gerber", filename)
                    self.app.file_saved.emit("Gerber", filename)
                    self.inform.emit('[success] %s: %s' % (_("Gerber file exported to"), filename))
                else:
                    return exported_gerber
            except Exception as e:
                self.log.error("App.export_gerber.make_gerber() --> %s" % str(e))
                return 'fail'

        if use_thread is True:
            with self.app.proc_container.new(_("Exporting ...")):

                def job_thread_grb(app_obj):
                    ret = make_gerber()
                    if ret == 'fail':
                        app_obj.inform.emit('[ERROR_NOTCL] %s' % _('Could not export.'))
                        return 'fail'

                self.worker_task.emit({'fcn': job_thread_grb, 'params': [self]})
        else:
            gret = make_gerber()
            if gret == 'fail':
                self.inform.emit('[ERROR_NOTCL] %s' % _('Could not export.'))
                return 'fail'
            if local_use is not None:
                return gret

    def export_dxf(self, obj_name, filename, local_use=None, use_thread=True):
        """
        Exports a Geometry Object to an DXF file.

        :param obj_name:    the name of the FlatCAM object to be saved as DXF
        :param filename:    Path to the DXF file to save to.
        :param local_use:   if the Gerber code is to be saved to a file (None) or used within FlatCAM.
                            When not None, the value will be the actual Geometry object for which to create
                            the Geometry/DXF code
        :param use_thread:  if to be run in a separate thread
        :return:
        """
        if filename is None:
            filename = self.app.options["global_last_save_folder"] if \
                self.app.options["global_last_save_folder"] is not None else self.app.options["global_last_folder"]

        self.log.debug("export_dxf()")

        if local_use is None:
            try:
                obj = self.app.collection.get_by_name(str(obj_name))
            except Exception:
                return 'fail'
        else:
            obj = local_use

        def make_dxf():
            try:
                dxf_code = obj.export_dxf()
                if local_use is None:
                    try:
                        dxf_code.saveas(filename)
                    except PermissionError:
                        self.inform.emit('[WARNING] %s' %
                                         _("Permission denied, saving not possible.\n"
                                           "Most likely another app is holding the file open and not accessible."))
                        return 'fail'

                    if self.options["global_open_style"] is False:
                        self.app.file_opened.emit("DXF", filename)
                    self.app.file_saved.emit("DXF", filename)
                    self.inform.emit('[success] %s: %s' % (_("DXF file exported to"), filename))
                else:
                    return dxf_code
            except Exception as e:
                self.log.error("App.export_dxf.make_dxf() --> %s" % str(e))
                return 'fail'

        if use_thread is True:

            with self.app.proc_container.new(_("Exporting ...")):

                def job_thread_exc(app_obj):
                    ret_dxf_val = make_dxf()
                    if ret_dxf_val == 'fail':
                        app_obj.inform.emit('[WARNING_NOTCL] %s' % _('Could not export.'))
                        return

                self.worker_task.emit({'fcn': job_thread_exc, 'params': [self]})
        else:
            ret = make_dxf()
            if ret == 'fail':
                self.inform.emit('[WARNING_NOTCL] %s' % _('Could not export.'))
                return
            if local_use is not None:
                return ret

    def import_svg(self, filename, geo_type='geometry', outname=None, plot=True):
        """
        Adds a new Geometry Object to the projects and populates
        it with shapes extracted from the SVG file.

        :param plot:        If True then the resulting object will be plotted on canvas
        :param filename:    Path to the SVG file.
        :param geo_type:    Type of FlatCAM object that will be created from SVG
        :param outname:     The name given to the resulting FlatCAM object
        :return:
        """
        self.log.debug("App.import_svg()")
        if not os.path.exists(filename):
            self.inform.emit('[ERROR_NOTCL] %s' % _("File no longer available."))
            return

        obj_type = ""
        if geo_type is None or geo_type == "geometry":
            obj_type = "geometry"
        elif geo_type == "gerber":
            obj_type = "gerber"
        else:
            self.inform.emit('[ERROR_NOTCL] %s' %
                             _("Not supported type is picked as parameter. Only Geometry and Gerber are supported"))
            return

        units = self.app_units.upper()

        def obj_init(geo_obj, app_obj):
            res = geo_obj.import_svg(filename, obj_type, units=units)
            if res == 'fail':
                return 'fail'

            geo_obj.multigeo = True

            with open(filename) as f:
                file_content = f.read()
            geo_obj.source_file = file_content

            # appGUI feedback
            app_obj.inform.emit('[success] %s: %s' % (_("Opened"), filename))

        with self.app.proc_container.new('%s ...' % _("Importing")):

            # Object name
            name = outname or filename.split('/')[-1].split('\\')[-1]

            ret = self.app.app_obj.new_object(obj_type, name, obj_init, autoselected=False, plot=plot)

            if ret == 'fail':
                self.inform.emit('[ERROR_NOTCL]%s' % _('Import failed.'))
                return 'fail'

            # Register recent file
            self.app.file_opened.emit("svg", filename)

    def import_dxf(self, filename, geo_type='geometry', outname=None, plot=True):
        """
        Adds a new Geometry Object to the projects and populates
        it with shapes extracted from the DXF file.

        :param filename:    Path to the DXF file.
        :param geo_type:    Type of FlatCAM object that will be created from DXF
        :param outname:     Name for the imported Geometry
        :param plot:        If True then the resulting object will be plotted on canvas
        :return:
        """
        self.log.debug(" ********* Importing DXF as: %s ********* " % geo_type.capitalize())
        if not os.path.exists(filename):
            self.inform.emit('[ERROR_NOTCL] %s' % _("File no longer available."))
            return

        obj_type = ""
        if geo_type is None or geo_type == "geometry":
            obj_type = "geometry"
        elif geo_type == "gerber":
            obj_type = geo_type
        else:
            self.inform.emit('[ERROR_NOTCL] %s' %
                             _("Not supported type is picked as parameter. Only Geometry and Gerber are supported"))
            return

        units = self.app_units.upper()

        def obj_init(geo_obj, app_obj):
            if obj_type == "geometry":
                geo_obj.import_dxf_as_geo(filename, units=units)
            elif obj_type == "gerber":
                geo_obj.import_dxf_as_gerber(filename, units=units)
            else:
                return "fail"

            with open(filename) as f:
                file_content = f.read()
            geo_obj.source_file = file_content

            # appGUI feedback
            app_obj.inform.emit('[success] %s: %s' % (_("Opened"), filename))

        with self.app.proc_container.new('%s ...' % _("Importing")):

            # Object name
            name = outname or filename.split('/')[-1].split('\\')[-1]

            ret = self.app.app_obj.new_object(obj_type, name, obj_init, autoselected=False, plot=plot)

            if ret == 'fail':
                self.inform.emit('[ERROR_NOTCL]%s' % _('Import failed.'))
                return 'fail'

            # Register recent file
            self.app.file_opened.emit("dxf", filename)

    def import_pdf(self, filename):
        self.app.pdf_tool.periodic_check(1000)
        self.worker_task.emit({'fcn': self.app.pdf_tool.open_pdf, 'params': [filename]})

    def open_gerber(self, filename, outname=None, plot=True, from_tcl=False):
        """
        Opens a Gerber file, parses it and creates a new object for
        it in the program. Thread-safe.

        :param outname:     Name of the resulting object. None causes the
                            name to be that of the file. Str.
        :param filename:    Gerber file filename
        :type filename:     str
        :param plot:        boolean, to plot or not the resulting object
        :param from_tcl:    True if run from Tcl Shell
        :return: None
        """

        # How the object should be initialized
        def obj_init(gerber_obj, app_obj):

            assert isinstance(gerber_obj, GerberObject), \
                "Expected to initialize a GerberObject but got %s" % type(gerber_obj)

            # Opening the file happens here
            try:
                parse_ret_val = gerber_obj.parse_file(filename)
            except IOError:
                app_obj.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Failed to open file"), filename))
                return "fail"
            except ParseError as parse_err:
                app_obj.inform.emit('[ERROR_NOTCL] %s: %s. %s' % (_("Failed to parse file"), filename, str(parse_err)))
                app_obj.log.error(str(parse_err))
                return "fail"
            except Exception as e:
                app_obj.log.error("App.open_gerber() --> %s" % str(e))
                msg = '[ERROR] %s' % _("An internal error has occurred. See shell.\n")
                msg += traceback.format_exc()
                app_obj.inform.emit(msg)
                return "fail"

            if gerber_obj.is_empty():
                app_obj.inform.emit('[ERROR_NOTCL] %s' %
                                    _("Object is not Gerber file or empty. Aborting object creation."))
                return "fail"

            if parse_ret_val:
                return parse_ret_val

        self.log.debug("open_gerber()")
        if not os.path.exists(filename):
            self.inform.emit('[ERROR_NOTCL] %s. %s' % (filename, _("File no longer available.")))
            return

        with self.app.proc_container.new('%s...' % _("Opening")):
            # Object name
            name = outname or filename.split('/')[-1].split('\\')[-1]

            # # ## Object creation # ##
            ret_val = self.app.app_obj.new_object("gerber", name, obj_init, autoselected=False, plot=plot)
            if ret_val == "defective":
                message = '[ERROR] %s' % \
                          _('The Gerber file is DAMAGED. We could open it but the file parsing PARTIALLY FAILED.\n'
                            '!!! CHECK THE FILE !!! --- SOME copper features (pads, traces etc) ARE MISSING !!!\n'
                            '!!! CHECK THE FILE !!! --- SOME copper features (pads, traces etc) ARE MISSING !!!\n'
                            '!!! CHECK THE FILE !!! --- SOME copper features (pads, traces etc) ARE MISSING !!!\n')
                self.inform.emit(message)
                return
            if ret_val == 'fail':
                if from_tcl:
                    filename = self.options['global_tcl_path'] + '/' + name
                    ret_val = self.app.app_obj.new_object("gerber", name, obj_init, autoselected=False, plot=plot)
                if ret_val == 'fail':
                    self.inform.emit('[ERROR_NOTCL] %s' % _('Open Gerber failed. Probable not a Gerber file.'))
                    return 'fail'

            # Register recent file
            self.app.file_opened.emit("gerber", filename)

            # appGUI feedback
            self.app.inform.emit('[success] %s: %s' % (_("Opened"), filename))

    def open_excellon(self, filename, outname=None, plot=True, from_tcl=False):
        """
        Opens an Excellon file, parses it and creates a new object for
        it in the program. Thread-safe.

        :param outname:     Name of the resulting object. None causes the name to be that of the file.
        :param filename:    Excellon file filename
        :type filename:     str
        :param plot:        boolean, to plot or not the resulting object
        :param from_tcl:    True if run from Tcl Shell
        :return:            None
        """

        self.log.debug("open_excellon()")

        if not os.path.exists(filename):
            self.inform.emit('[ERROR_NOTCL] %s. %s' % (filename, _("File no longer available.")))
            return

        # How the object should be initialized
        def obj_init(excellon_obj, app_obj):
            # populate excellon_obj.tools dict
            try:
                ret = excellon_obj.parse_file(filename=filename)
                if ret == "fail":
                    app_obj.log.debug("Excellon parsing failed.")
                    self.inform.emit('[ERROR_NOTCL] %s' % _("This is not Excellon file."))
                    return "fail"
            except IOError:
                app_obj.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Cannot open file"), filename))
                app_obj.log.debug("Could not open Excellon object.")
                return "fail"
            except Exception:
                msg = '[ERROR_NOTCL] %s' % _("An internal error has occurred. See shell.\n")
                msg += traceback.format_exc()
                app_obj.inform.emit(msg)
                return "fail"

            # populate excellon_obj.solid_geometry list
            ret = excellon_obj.create_geometry()
            if ret == 'fail':
                app_obj.log.debug("Could not create geometry for Excellon object.")
                return "fail"

            for tool in excellon_obj.tools:
                if excellon_obj.tools[tool]['solid_geometry']:
                    return
            app_obj.inform.emit('[ERROR_NOTCL] %s: %s' % (_("No geometry found in file"), filename))
            return "fail"

        with self.app.proc_container.new('%s...' % _("Opening")):
            # Object name
            name = outname or filename.split('/')[-1].split('\\')[-1]
            ret_val = self.app.app_obj.new_object("excellon", name, obj_init, autoselected=False, plot=plot)
            if ret_val == 'fail':
                if from_tcl:
                    filename = self.options['global_tcl_path'] + '/' + name
                    ret_val = self.app.app_obj.new_object("excellon", name, obj_init, autoselected=False, plot=plot)
                if ret_val == 'fail':
                    self.inform.emit('[ERROR_NOTCL] %s' %
                                     _('Open Excellon file failed. Probable not an Excellon file.'))
                    return

            # Register recent file
            self.app.file_opened.emit("excellon", filename)

            # appGUI feedback
            self.inform.emit('[success] %s: %s' % (_("Opened"), filename))

    def open_gcode(self, filename, outname=None, force_parsing=None, plot=True, from_tcl=False):
        """
        Opens a G-gcode file, parses it and creates a new object for
        it in the program. Thread-safe.

        :param filename:        G-code file filename
        :param outname:         Name of the resulting object. None causes the name to be that of the file.
        :param force_parsing:
        :param plot:            If True, then plot the object on canvas
        :param from_tcl:        True if run from Tcl Shell
        :return:                None
        """
        self.log.debug("open_gcode()")

        if not os.path.exists(filename):
            self.inform.emit('[ERROR_NOTCL] %s' % _("File no longer available."))
            return

        # How the object should be initialized
        def obj_init(job_obj, app_obj_: "appMain.App"):
            """
            :param job_obj: the resulting object
            :type app_obj_: App
            """

            app_obj_.inform.emit('%s...' % _("Reading GCode file"))     # noqa
            try:
                f = open(filename)
                gcode = f.read()
                f.close()
            except IOError:
                app_obj_.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Failed to open"), filename))      # noqa
                return "fail"

            # try to find from what kind of object this GCode was created
            gcode_origin = 'Geometry'
            match = re.search(r'^.*Type:\s*.*(\bGeometry\b|\bExcellon\b)', gcode, re.MULTILINE)
            if match:
                gcode_origin = match.group(1)
                job_obj.obj_options['type'] = gcode_origin
                # add at least one default tool
                if 'excellon' in gcode_origin.lower():
                    job_obj.tools = {1: {'data': {'tools_drill_ppname_e': 'default'}}}
                if 'geometry' in gcode_origin.lower():
                    job_obj.tools = {1: {'data': {'tools_mill_ppname_g': 'default'}}}

            # try to find from what kind of object this GCode was created
            match = re.search(r'^.*Preprocessor:\s*.*\bGeometry\b|\bExcellon\b:\s(\b.*\b)', gcode, re.MULTILINE)
            detected_preprocessor = 'default'
            if match:
                detected_preprocessor = match.group(1)
            # determine if there is any tool data
            match_list = re.findall(r'^.*Tool:\s*(\d*)\s*->\s*Dia:\s*(\d*\.?\d*)', gcode, re.MULTILINE)
            if match_list:
                job_obj.tools = {}
                for match in match_list:
                    tool = int(match[0])
                    if 'excellon' in gcode_origin.lower():
                        job_obj.tools[tool] = {
                            'tooldia': float(match[1]),
                            'nr_drills': 0,
                            'nr_slots': 0,
                            'offset_z': 0.0,
                            'data': {'tools_drill_ppname_e': detected_preprocessor}
                        }
                    # if 'geometry' in gcode_origin.lower():
                    #     job_obj.tools[int(m[0])] = {
                    #         'tooldia': float(m[1]),
                    #         'data': {
                    #             'tools_mill_ppname_g': detected_preprocessor,
                    #             'tools_mill_offset_value': 0.0,
                    #             'tools_mill_job_type': _('Roughing'),
                    #             'tools_mill_tool_shape': "C1"
                    #
                    #         }
                    #     }
                job_obj.used_tools = list(job_obj.tools.keys())
            # determine if there is any Cut Z data
            match_list = re.findall(r'^.*Tool:\s*(\d*)\s*->\s*Z_Cut:\s*([\-|+]?\d*\.?\d*)', gcode, re.MULTILINE)
            if match_list:
                for match in match_list:
                    tool = int(match[0])
                    if 'excellon' in gcode_origin.lower():
                        if tool in job_obj.tools:
                            job_obj.tools[tool]['offset_z'] = 0.0
                            job_obj.tools[tool]['data']['tools_drill_cutz'] = float(match[1])
                    # if 'geometry' in gcode_origin.lower():
                    #     if int(m[0]) in job_obj.tools:
                    #         job_obj.tools[int(m[0])]['data']['tools_mill_cutz'] = float(m[1])

            job_obj.gcode = gcode

            gcode_ret = job_obj.gcode_parse(force_parsing=force_parsing)
            if gcode_ret == "fail":
                self.inform.emit('[ERROR_NOTCL] %s' % _("This is not GCODE"))
                return "fail"

            for k in job_obj.tools:
                job_obj.tools[k]['gcode'] = gcode
                job_obj.tools[k]['gcode_parsed'] = []

            for k in job_obj.tools:
                print(k, job_obj.tools[k])
            job_obj.create_geometry()

        with self.app.proc_container.new('%s...' % _("Opening")):

            # Object name
            name = outname or filename.split('/')[-1].split('\\')[-1]

            # New object creation and file processing
            ret_val = self.app.app_obj.new_object("cncjob", name, obj_init, autoselected=False, plot=plot)
            if ret_val == 'fail':
                if from_tcl:
                    filename = self.options['global_tcl_path'] + '/' + name
                    ret_val = self.app.app_obj.new_object("cncjob", name, obj_init, autoselected=False, plot=plot)
                if ret_val == 'fail':
                    self.inform.emit('[ERROR_NOTCL] %s' %
                                     _("Failed to create CNCJob Object. Probable not a GCode file. "
                                       "Try to load it from File menu.\n "
                                       "Attempting to create a FlatCAM CNCJob Object from "
                                       "G-Code file failed during processing"))
                    return "fail"

            # Register recent file
            self.app.file_opened.emit("cncjob", filename)

            # appGUI feedback
            self.inform.emit('[success] %s: %s' % (_("Opened"), filename))

    def open_hpgl2(self, filename, outname=None):
        """
        Opens a HPGL2 file, parses it and creates a new object for
        it in the program. Thread-safe.

        :param outname:     Name of the resulting object. None causes the name to be that of the file.
        :param filename:    HPGL2 file filename
        :return:            None
        """
        filename = filename

        # How the object should be initialized
        def obj_init(geo_obj, app_obj):

            assert isinstance(geo_obj, GeometryObject), \
                "Expected to initialize a GeometryObject but got %s" % type(geo_obj)

            # Opening the file happens here
            obj = HPGL2(self.app)
            try:
                HPGL2.parse_file(obj, filename)
            except IOError:
                app_obj.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Failed to open file"), filename))
                return "fail"
            except ParseError as parse_err:
                app_obj.inform.emit('[ERROR_NOTCL] %s: %s. %s' % (_("Failed to parse file"), filename, str(parse_err)))
                app_obj.log.error(str(parse_err))
                return "fail"
            except Exception as e:
                app_obj.log.error("App.open_hpgl2() --> %s" % str(e))
                msg = '[ERROR] %s' % _("An internal error has occurred. See shell.\n")
                msg += traceback.format_exc()
                app_obj.inform.emit(msg)
                return "fail"

            geo_obj.multigeo = True
            geo_obj.solid_geometry = deepcopy(obj.solid_geometry)
            geo_obj.tools = deepcopy(obj.tools)
            geo_obj.source_file = deepcopy(obj.source_file)

            del obj

            if not geo_obj.solid_geometry:
                app_obj.inform.emit('[ERROR_NOTCL] %s' %
                                    _("Object is not HPGL2 file or empty. Aborting object creation."))
                return "fail"

        self.log.debug("open_hpgl2()")

        with self.app.proc_container.new('%s...' % _("Opening")):
            # Object name
            name = outname or filename.split('/')[-1].split('\\')[-1]

            # # ## Object creation # ##
            ret = self.app.app_obj.new_object("geometry", name, obj_init, autoselected=False)
            if ret == 'fail':
                self.inform.emit('[ERROR_NOTCL]%s' % _('Failed. Probable not a HPGL2 file.'))
                return 'fail'

            # Register recent file
            self.app.file_opened.emit("geometry", filename)

            # appGUI feedback
            self.inform.emit('[success] %s: %s' % (_("Opened"), filename))

    def open_script(self, filename, outname=None, silent=False):
        """
        Opens a Script file, parses it and creates a new object for
        it in the program. Thread-safe.

        :param outname:     Name of the resulting object. None causes the name to be that of the file.
        :param filename:    Script file filename
        :param silent:      If True there will be no messages printed to StatusBar
        :return:            None
        """

        def obj_init(script_obj, app_obj):

            assert isinstance(script_obj, ScriptObject), \
                "Expected to initialize a ScriptObject but got %s" % type(script_obj)

            if silent is False:
                app_obj.inform.emit('[success] %s' % _("TCL script file opened in Code Editor."))

            try:
                script_obj.parse_file(filename)
            except IOError:
                app_obj.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Failed to open file"), filename))
                return "fail"
            except ParseError as parse_err:
                app_obj.inform.emit('[ERROR_NOTCL] %s: %s. %s' % (_("Failed to parse file"), filename, str(parse_err)))
                app_obj.log.error(str(parse_err))
                return "fail"
            except Exception as e:
                app_obj.log.error("App.open_script() -> %s" % str(e))
                msg = '[ERROR] %s' % _("An internal error has occurred. See shell.\n")
                msg += traceback.format_exc()
                app_obj.inform.emit(msg)
                return "fail"

        self.log.debug("open_script()")
        if not os.path.exists(filename):
            self.inform.emit('[ERROR_NOTCL] %s' % _("File no longer available."))
            return

        with self.app.proc_container.new('%s...' % _("Opening")):

            # Object name
            script_name = outname or filename.split('/')[-1].split('\\')[-1]

            # Object creation
            ret_val = self.app.app_obj.new_object("script", script_name, obj_init, autoselected=False, plot=False)
            if ret_val == 'fail':
                filename = self.options['global_tcl_path'] + '/' + script_name
                ret_val = self.app.app_obj.new_object("script", script_name, obj_init, autoselected=False, plot=False)
                if ret_val == 'fail':
                    self.inform.emit('[ERROR_NOTCL]%s' % _('Failed to open TCL Script.'))
                    return 'fail'

            # Register recent file
            self.app.file_opened.emit("script", filename)

            # appGUI feedback
            self.inform.emit('[success] %s: %s' % (_("Opened"), filename))

    def open_config_file(self, filename, run_from_arg=None):
        """
        Loads a config file from the specified file.

        :param filename:        Name of the file from which to load.
        :param run_from_arg:    if True the FlatConfig file will be open as a command line argument
        :return:                None
        """
        self.log.debug("Opening config file: " + filename)

        if run_from_arg:
            self.splash.showMessage('%s: %ssec\n%s' % (_("Canvas initialization started.\n"
                                                         "Canvas initialization finished in"),
                                                       '%.2f' % self.app.used_time,
                                                       _("Opening FlatCAM Config file.")),
                                    alignment=Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft,
                                    color=QtGui.QColor("lightgray"))
        # # add the tab if it was closed
        # self.ui.plot_tab_area.addTab(self.ui.text_editor_tab, _("Code Editor"))
        # # first clear previous text in text editor (if any)
        # self.ui.text_editor_tab.code_editor.clear()
        #
        # # Switch plot_area to CNCJob tab
        # self.ui.plot_tab_area.setCurrentWidget(self.ui.text_editor_tab)

        # close the Code editor if already open
        if self.app.toggle_codeeditor:
            self.app.on_toggle_code_editor()

        self.app.on_toggle_code_editor()

        try:
            if filename:
                f = QtCore.QFile(filename)
                if f.open(QtCore.QIODevice.OpenModeFlag.ReadOnly):
                    stream = QtCore.QTextStream(f)
                    code_edited = stream.readAll()
                    self.app.text_editor_tab.load_text(code_edited, clear_text=True, move_to_start=True)
                    f.close()
        except IOError:
            self.log.error("Failed to open config file: %s" % filename)
            self.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Failed."), filename))
            return

    def open_project(self, filename, run_from_arg=False, plot=True, cli=False, from_tcl=False):
        """
        Loads a project from the specified file.

        1) Loads and parses file
        2) Registers the file as recently opened.
        3) Calls on_file_new_project()
        4) Updates options
        5) Calls app_obj.new_object() with the object's from_dict() as init method.
        6) Calls plot_all() if plot=True

        :param filename:        Name of the file from which to load.
        :param run_from_arg:    True if run for arguments
        :param plot:            If True plot all objects in the project
        :param cli:             Run from command line
        :param from_tcl:        True if run from Tcl Shell
        :return:                None
        """

        project_filename = filename

        self.log.debug("Opening project: " + project_filename)
        if not os.path.exists(project_filename):
            self.inform.emit('[ERROR_NOTCL] %s' % _("File no longer available."))
            return

        # block auto-saving while a project is loaded
        self.app.block_autosave = True

        # for some reason, setting ui_title does not work when this method is called from Tcl Shell
        # it's because the TclCommand is run in another thread (it inherit TclCommandSignaled)
        if cli is None:
            self.app.ui.set_ui_title(name=_("Loading Project ... Please Wait ..."))

        if run_from_arg:
            self.splash.showMessage('%s: %ssec\n%s' % (_("Canvas initialization started.\n"
                                                         "Canvas initialization finished in"),
                                                       '%.2f' % self.app.used_time,
                                                       _("Opening FlatCAM Project file.")),
                                    alignment=Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft,
                                    color=QtGui.QColor("lightgray"))

        def parse_worker(prj_filename):
            with self.app.proc_container.new('%s' % _("Parsing...")):
                # Open and parse an uncompressed Project file
                try:
                    f = open(prj_filename, 'r')
                except IOError:
                    if from_tcl:
                        name = prj_filename.split('/')[-1].split('\\')[-1]
                        prj_filename = os.path.join(self.options['global_tcl_path'], name)
                        try:
                            f = open(prj_filename, 'r')
                        except IOError:
                            self.log.error("Failed to open project file: %s" % prj_filename)
                            self.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Failed to open project file"), prj_filename))
                            return
                    else:
                        self.log.error("Failed to open project file: %s" % prj_filename)
                        self.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Failed to open project file"), prj_filename))
                        return

                try:
                    d = json.load(f, object_hook=dict2obj)
                except Exception as e:
                    self.log.debug(
                        "Failed to parse project file, trying to see if it loads as an LZMA archive: %s because %s" %
                        (prj_filename, str(e)))
                    f.close()

                    # Open and parse a compressed Project file
                    try:
                        with lzma.open(prj_filename) as f:
                            file_content = f.read().decode('utf-8')
                            d = json.loads(file_content, object_hook=dict2obj)
                    except Exception as e:
                        self.log.error("Failed to open project file: %s with error: %s" % (prj_filename, str(e)))
                        self.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Failed to open project file"), prj_filename))
                        return

                # Check for older projects
                found_older_project = False
                for obj in d['objs']:
                    if 'cnc_tools' in obj or 'exc_cnc_tools' in obj or 'apertures' in obj:
                        self.app.log.error(
                            'AppIO.open_project() --> %s %s. %s' %
                            ("Failed to open the CNCJob file:", str(obj['options']['name']),
                             "Maybe it is an old project."))
                        found_older_project = True

                if found_older_project:
                    if not run_from_arg or not cli or from_tcl is False:
                        msgbox = FCMessageBox(parent=self.app.ui)
                        title = _("Legacy Project")
                        txt = _("The project was made with an older app version.\n"
                                "It may not load correctly.\n\n"
                                "Do you want to continue?")
                        msgbox.setWindowTitle(title)  # taskbar still shows it
                        msgbox.setWindowIcon(QtGui.QIcon(self.app.resource_location + '/app128.png'))
                        msgbox.setText('<b>%s</b>' % title)
                        msgbox.setInformativeText(txt)
                        msgbox.setIcon(QtWidgets.QMessageBox.Icon.Question)

                        bt_ok = msgbox.addButton(_('Ok'), QtWidgets.QMessageBox.ButtonRole.AcceptRole)
                        bt_cancel = msgbox.addButton(_('Cancel'), QtWidgets.QMessageBox.ButtonRole.RejectRole)

                        msgbox.setDefaultButton(bt_ok)
                        msgbox.exec()
                        response = msgbox.clickedButton()

                        if response == bt_cancel:
                            return
                    else:
                        self.app.log.error("Legacy Project. Loading not supported.")
                        return

                self.app.restore_project.emit(d, prj_filename, run_from_arg, from_tcl, cli, plot)

        self.app.worker_task.emit({'fcn': parse_worker, 'params': [project_filename]})

    def restore_project_handler(self, proj_dict, filename, run_from_arg, from_tcl, cli, plot):
        # Clear the current project
        # # NOT THREAD SAFE # ##
        if run_from_arg is True:
            pass
        elif cli is True:
            self.app.delete_selection_shape()
        else:
            self.on_file_new_project()

        if not run_from_arg or not cli or from_tcl is False:
            msgbox = FCMessageBox(parent=self.app.ui)
            title = _("Import Settings")
            txt = _("Do you want to import the loaded project settings?")
            msgbox.setWindowTitle(title)  # taskbar still shows it
            msgbox.setWindowIcon(QtGui.QIcon(self.app.resource_location + '/app128.png'))
            msgbox.setText('<b>%s</b>' % title)
            msgbox.setInformativeText(txt)
            msgbox.setIconPixmap(QtGui.QPixmap(self.app.resource_location + '/import.png'))

            bt_yes = msgbox.addButton(_('Yes'), QtWidgets.QMessageBox.ButtonRole.YesRole)
            bt_no = msgbox.addButton(_('No'), QtWidgets.QMessageBox.ButtonRole.NoRole)
            # bt_cancel = msgbox.addButton(_('Cancel'), QtWidgets.QMessageBox.ButtonRole.RejectRole)

            msgbox.setDefaultButton(bt_yes)
            msgbox.exec()
            response = msgbox.clickedButton()

            if response == bt_yes:
                # self.app.defaults.update(self.app.options)
                # self.app.preferencesUiManager.save_defaults()
                # Project options
                self.app.options.update(proj_dict['options'])
            if response == bt_no:
                pass
        else:
            # Load by default new options when not using GUI
            # Project options
            self.app.options.update(proj_dict['options'])

        self.app.project_filename = filename

        # for some reason, setting ui_title does not work when this method is called from Tcl Shell
        # it's because the TclCommand is run in another thread (it inherits TclCommandSignaled)

        self.app.restore_project_objects_sig.emit(proj_dict, filename, cli, plot)

    def restore_project_objects(self, proj_dict, filename, cli, plot):

        def worker_task():
            with self.app.proc_container.new('%s' % _("Loading...")):
                # Re-create objects
                self.log.debug(" **************** Started PROEJCT loading... **************** ")
                for obj in proj_dict['objs']:
                    try:
                        obj_name = obj['obj_options']['name']
                    except KeyError:
                        # allowance for older projects
                        obj_name = obj['options']['name']
                    self.app.log.debug(
                        f"Recreating from opened project an {obj['kind'].capitalize()} object: {obj_name}")

                    def obj_init(new_obj, app_inst):
                        try:
                            new_obj.from_dict(obj)
                        except Exception as except_error:
                            app_inst.log.error('AppIO.open_project() --> ' + str(except_error))
                            return 'fail'

                        # make the 'obj_options' dict a LoudDict
                        new_obj_options = LoudDict()
                        try:
                            new_obj_options.update(new_obj.obj_options)
                        except AttributeError:
                            new_obj_options.update(new_obj.options)
                        except Exception as except_error:
                            app_inst.log.error('AppIO.open_project() make a LoudDict--> ' + str(except_error))
                            return 'fail'

                        new_obj.obj_options = new_obj_options

                        # #############################################################################################
                        # for older projects loading try to convert the 'apertures' or 'cnc_tools' or 'exc_cnc_tools'
                        # attributes, if found, to 'tools'
                        # #############################################################################################
                        # for older loaded projects
                        if 'apertures' in obj:
                            new_obj.tools = obj['apertures']
                        if 'cnc_tools' in obj and obj['cnc_tools']:
                            new_obj.tools = obj['cnc_tools']
                        if 'exc_cnc_tools' in obj and obj['exc_cnc_tools']:
                            new_obj.tools = obj['exc_cnc_tools']
                            # add the used_tools (all of them will be used)
                            new_obj.used_tools = [float(k) for k in new_obj.tools.keys()]
                            # add a missing key, 'tooldia' used for plotting CNCJob objects
                            for td in new_obj.tools:
                                new_obj.tools[td]['tooldia'] = float(td)
                        # #############################################################################################
                        # #############################################################################################

                        # try to make the keys in the tools dictionary to be integers
                        # JSON serialization makes them strings
                        # not all FlatCAM objects have the 'tools' dictionary attribute
                        try:
                            new_obj.tools = {
                                int(tool): tool_dict for tool, tool_dict in list(new_obj.tools.items())
                            }
                        except ValueError:
                            # for older loaded projects
                            new_obj.tools = {
                                float(tool): tool_dict for tool, tool_dict in list(new_obj.tools.items())
                            }
                        except Exception as other_error_msg:
                            app_inst.log.error('AppIO.open_project() keys to int--> ' + str(other_error_msg))
                            return 'fail'

                        # #############################################################################################
                        # for older loaded projects
                        # ony older CNCJob objects hold those
                        if 'cnc_tools' in obj:
                            new_obj.obj_options['type'] = 'Geometry'
                        if 'exc_cnc_tools' in obj:
                            new_obj.obj_options['type'] = 'Excellon'
                        # #############################################################################################

                        if new_obj.kind == 'cncjob':
                            # some attributes are serialized, so we need to take this into consideration in
                            # CNCJob.set_ui()
                            new_obj.is_loaded_from_project = True

                    # for some reason, setting ui_title does not work when this method is called from Tcl Shell
                    # it's because the TclCommand is run in another thread (it inherits TclCommandSignaled)
                    try:
                        if cli is None:
                            self.app.ui.set_ui_title(name="{} {}: {}".format(
                                _("Loading Project ... restoring"), obj['kind'].upper(), obj_name))

                        ret = self.app.app_obj.new_object(obj['kind'], obj['obj_options']['name'], obj_init, plot=plot)
                    except KeyError:
                        # allowance for older projects
                        if cli is None:
                            self.app.ui.set_ui_title(name="{} {}: {}".format(
                                _("Loading Project ... restoring"), obj['kind'].upper(), obj_name))
                        try:
                            ret = self.app.app_obj.new_object(obj['kind'], obj_name, obj_init, plot=plot)
                        except Exception:
                            continue
                    if ret == 'fail':
                        continue

                self.inform.emit('[success] %s: %s' % (_("Project loaded from"), filename))

                self.app.should_we_save = False
                self.app.file_opened.emit("project", filename)

                # restore auto-saving after a project was loaded
                self.app.block_autosave = False

                # for some reason, setting ui_title does not work when this method is called from Tcl Shell
                # it's because the TclCommand is run in another thread (it inherit TclCommandSignaled)
                if cli is None:
                    self.app.ui.set_ui_title(name=self.app.project_filename)

                self.log.debug(" **************** Finished PROJECT loading... **************** ")

        self.app.worker_task.emit({'fcn': worker_task, 'params': []})

    def save_project(self, filename, quit_action=False, silent=False, from_tcl=False):
        """
        Saves the current project to the specified file.

        :param filename:        Name of the file in which to save.
        :type filename:         str
        :param quit_action:     if the project saving will be followed by an app quit; boolean
        :param silent:          if True will not display status messages
        :param from_tcl         True is run from Tcl Shell
        :return:                None
        """
        self.log.debug("save_project() -> Saving Project")
        self.app.save_in_progress = True

        if from_tcl:
            self.log.debug("AppIO.save_project() -> Project saved from TCL command.")

        with self.app.proc_container.new(_("Saving Project ...")):
            # Capture the latest changes
            # Current object
            try:
                current_object = self.app.collection.get_active()
                if current_object:
                    current_object.read_form()
            except Exception as e:
                self.log.error("save_project() --> There was no active object. Skipping read_form. %s" % str(e))

            app_options = {k: v for k, v in self.app.options.items()}
            d = {
                "objs":             [obj.to_dict() for obj in self.app.collection.get_list()],
                "options":          app_options,
                "version":          self.app.version
            }

            if self.options["global_save_compressed"] is True:
                try:
                    project_as_json = json.dumps(d, default=to_dict, indent=2, sort_keys=True).encode('utf-8')
                except Exception as e:
                    self.log.error(
                        "Failed to serialize file before compression: %s because: %s" % (str(filename), str(e)))
                    self.inform.emit('[ERROR_NOTCL] %s' % _("Failed."))
                    self.app.save_in_progress = False
                    return

                try:
                    # with lzma.open(filename, "w", preset=int(self.options['global_compression_level'])) as f:
                    #     # # Write
                    #     f.write(project_as_json)

                    compressor_obj = lzma.LZMACompressor(preset=int(self.options['global_compression_level']))
                    out1 = compressor_obj.compress(project_as_json)
                    out2 = compressor_obj.flush()
                    project_zipped = b"".join([out1, out2])
                except Exception as error_msg:
                    self.log.error("Failed to save compressed file: %s because: %s" % (str(filename), str(error_msg)))
                    self.inform.emit('[ERROR_NOTCL] %s' % _("Failed."))
                    self.app.save_in_progress = False
                    return

                if project_zipped != b'':
                    with open(filename, "wb") as f_to_write:
                        f_to_write.write(project_zipped)

                    self.inform.emit('[success] %s: %s' % (_("Project saved to"), str(filename)))
                else:
                    self.log.error("Failed to save file: %s. Empty binary file.", str(filename))
                    self.inform.emit('[ERROR_NOTCL] %s' % _("Failed."))
                    self.app.save_in_progress = False
                    return
            else:
                # Open file
                try:
                    f = open(filename, 'w')
                except IOError:
                    self.log.error("Failed to open file for saving: %s", str(filename))
                    self.inform.emit('[ERROR_NOTCL] %s' % _("The object is used by another application."))
                    self.app.save_in_progress = False
                    return

                # Write
                try:
                    json.dump(d, f, default=to_dict, indent=2, sort_keys=True)
                except Exception as e:
                    self.log.error(
                        "Failed to serialize file: %s because: %s" % (str(filename), str(e)))
                    self.inform.emit('[ERROR_NOTCL] %s' % _("Failed."))
                    self.app.save_in_progress = False
                    return
                f.close()

                # verification of the saved project
                # Open and parse
                try:
                    saved_f = open(filename, 'r')
                except IOError:
                    if silent is False:
                        self.inform.emit('[ERROR_NOTCL] %s: %s %s' %
                                         (_("Failed to verify project file"), str(filename), _("Retry to save it.")))
                        self.app.save_in_progress = False
                    return

                try:
                    saved_d = json.load(saved_f, object_hook=dict2obj)
                    if not saved_d:
                        self.inform.emit('[ERROR_NOTCL] %s: %s %s' %
                                         (_("Failed to parse saved project file"),
                                          str(filename),
                                          _("Retry to save it.")))  # noqa
                        f.close()
                        self.app.save_in_progress = False
                        return
                except Exception:
                    if silent is False:
                        self.inform.emit('[ERROR_NOTCL] %s: %s %s' %
                                         (_("Failed to parse saved project file"),
                                          str(filename),
                                          _("Retry to save it.")))  # noqa
                    f.close()
                    self.app.save_in_progress = False
                    return

                saved_f.close()

                if silent is False:
                    if 'version' in saved_d:
                        self.inform.emit('[success] %s: %s' % (_("Project saved to"), str(filename)))
                    else:
                        self.inform.emit('[ERROR_NOTCL] %s: %s %s' %
                                         (_("Failed to parse saved project file"),
                                          str(filename),
                                          _("Retry to save it.")))  # noqa

            # if quit:
            # t = threading.Thread(target=lambda: self.check_project_file_size(1, filename=filename))
            # t.start()
            self.app.start_delayed_quit(delay=500, filename=filename, should_quit=quit_action)

    def save_source_file(self, obj_name, filename):
        """
        Exports a FlatCAM Object to a Gerber/Excellon file.

        :param obj_name: the name of the FlatCAM object for which to save its embedded source file
        :param filename: Path to the Gerber file to save to.
        :return:
        """

        if filename is None:
            filename = self.app.options["global_last_save_folder"] or self.app.options["global_last_folder"]

        self.log.debug("save_source_file()")

        obj = self.app.collection.get_by_name(obj_name)

        if not obj.source_file:
            msg = _("Save cancelled because source file is empty. Try to export the file.")
            self.inform.emit('[ERROR_NOTCL] %s' % msg)  # noqa
            return 'fail'

        time_string = "{:%A, %d %B %Y at %H:%M}".format(datetime.now())

        try:
            with open(filename, 'w') as file:
                file.write('G04*\n')
                file.write('G04 %s (RE)GENERATED BY FLATCAM v%s - www.flatcam.org - Version Date: %s*\n' %
                           (obj.kind.upper(), str(self.app.version), str(self.app.version_date)))
                file.write('G04 Filename: %s*\n' % str(obj_name))
                file.write('G04 Created on : %s*\n' % time_string)
                file.write(obj.source_file)
        except PermissionError:
            self.inform.emit('[WARNING] %s' %
                             _("Permission denied, saving not possible.\n"
                               "Most likely another app is holding the file open and not accessible."))  # noqa
            return 'fail'

    def on_file_save_defaults(self):
        """
        Callback for menu item File->Save Defaults. Saves application default options
        ``self.options`` to current_defaults.FlatConfig.

        :return: None
        """
        self.app.defaults.update(self.app.options)
        self.app.preferencesUiManager.save_defaults()
