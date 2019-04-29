############################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 4/24/2019                                          #
# MIT Licence                                              #
############################################################


from FlatCAMTool import FlatCAMTool
# from copy import copy, deepcopy
from ObjectCollection import *
import time

import gettext
import FlatCAMTranslation as fcTranslate
from shapely.geometry import base
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class ToolSilk(FlatCAMTool):

    toolName = _("Silkscreen Tool")

    def __init__(self, app):
        self.app = app

        FlatCAMTool.__init__(self, app)

        self.tools_frame = QtWidgets.QFrame()
        self.tools_frame.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.tools_frame)
        self.tools_box = QtWidgets.QVBoxLayout()
        self.tools_box.setContentsMargins(0, 0, 0, 0)
        self.tools_frame.setLayout(self.tools_box)

        # Title
        title_label = QtWidgets.QLabel("%s" % self.toolName)
        title_label.setStyleSheet("""
                        QLabel
                        {
                            font-size: 16px;
                            font-weight: bold;
                        }
                        """)
        self.tools_box.addWidget(title_label)

        # Form Layout
        form_layout = QtWidgets.QFormLayout()
        self.tools_box.addLayout(form_layout)

        # Object Silkscreen
        self.silk_object_combo = QtWidgets.QComboBox()
        self.silk_object_combo.setModel(self.app.collection)
        self.silk_object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.silk_object_combo.setCurrentIndex(1)

        self.silk_object_label = QtWidgets.QLabel("Silk Gerber:")
        self.silk_object_label.setToolTip(
            _("Silkscreen Gerber object to be adjusted\n"
              "so it does not intersects the soldermask.")
        )
        e_lab_0 = QtWidgets.QLabel('')

        form_layout.addRow(self.silk_object_label, self.silk_object_combo)

        # Object Soldermask
        self.sm_object_combo = QtWidgets.QComboBox()
        self.sm_object_combo.setModel(self.app.collection)
        self.sm_object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.sm_object_combo.setCurrentIndex(1)

        self.sm_object_label = QtWidgets.QLabel("SM Gerber:")
        self.sm_object_label.setToolTip(
            _("Soldermask Gerber object that will adjust\n"
              "the silkscreen so it does not overlap.")
        )
        e_lab_1 = QtWidgets.QLabel('')

        form_layout.addRow(self.sm_object_label, self.sm_object_combo)
        form_layout.addRow(e_lab_1)

        self.intersect_btn = FCButton(_('Remove overlap'))
        self.intersect_btn.setToolTip(
            _("Remove the silkscreen geometry\n"
              "that overlaps over the soldermask.")
        )
        self.tools_box.addWidget(self.intersect_btn)

        self.tools_box.addStretch()

        # QTimer for periodic check
        self.check_thread = QtCore.QTimer()
        # Every time an intersection job is started we add a promise; every time an intersection job is finished
        # we remove a promise.
        # When empty we start the layer rendering
        self.promises = []

        self.new_apertures = {}
        self.new_solid_geometry = []

        self.solder_union = None

        # object to hold a flattened geometry
        self.flat_geometry = []

        self.sm_obj = None
        self.sm_obj_name = None
        self.silk_obj = None
        self.silk_obj_name = None

        try:
            self.intersect_btn.clicked.disconnect(self.on_intersection_click)
        except:
            pass
        self.intersect_btn.clicked.connect(self.on_intersection_click)

    def install(self, icon=None, separator=None, **kwargs):
        FlatCAMTool.install(self, icon, separator, shortcut='ALT+N', **kwargs)

    def run(self, toggle=True):
        self.app.report_usage("ToolNonCopperClear()")

        if toggle:
            # if the splitter is hidden, display it, else hide it but only if the current widget is the same
            if self.app.ui.splitter.sizes()[0] == 0:
                self.app.ui.splitter.setSizes([1, 1])
            else:
                try:
                    if self.app.ui.tool_scroll_area.widget().objectName() == self.toolName:
                        self.app.ui.splitter.setSizes([0, 1])
                except AttributeError:
                    pass
        else:
            if self.app.ui.splitter.sizes()[0] == 0:
                self.app.ui.splitter.setSizes([1, 1])

        FlatCAMTool.run(self)
        self.set_tool_ui()

        self.new_apertures.clear()
        self.new_solid_geometry = []

        self.app.ui.notebook.setTabText(2, _("Silk Tool"))

    def set_tool_ui(self):
        self.tools_frame.show()

    def on_intersection_click(self):
        self.silk_obj_name = self.silk_object_combo.currentText()
        # Get source object.
        try:
            self.silk_obj = self.app.collection.get_by_name(self.silk_obj_name)
        except:
            self.app.inform.emit(_("[ERROR_NOTCL] Could not retrieve object: %s") % self.obj_name)
            return "Could not retrieve object: %s" % self.silk_obj_name

        self.sm_obj_name = self.silk_object_combo.currentText()
        # Get source object.
        try:
            self.sm_obj = self.app.collection.get_by_name(self.sm_obj_name)
        except:
            self.app.inform.emit(_("[ERROR_NOTCL] Could not retrieve object: %s") % self.obj_name)
            return "Could not retrieve object: %s" % self.sm_obj_name

        # crate the new_apertures dict structure
        for apid in self.silk_obj.apertures:
            self.new_apertures[apid] = {}
            self.new_apertures[apid]['type'] = 'C'
            self.new_apertures[apid]['size'] = self.silk_obj.apertures[apid]['size']
            self.new_apertures[apid]['solid_geometry'] = []

        # geo_union_list = []
        # for apid1 in self.sm_obj.apertures:
        #     geo_union_list += self.sm_obj.apertures[apid1]['solid_geometry']
        # self.solder_union = cascaded_union(geo_union_list)

        # start the QTimer with 1 second period check
        self.periodic_check(1000)

        for apid in self.silk_obj.apertures:
            ap_size = self.silk_obj.apertures[apid]['size']
            geo = self.silk_obj.apertures[apid]['solid_geometry']
            self.app.worker_task.emit({'fcn': self.aperture_intersection,
                                       'params': [apid, geo]})

    def aperture_intersection(self, apid, geo):
        self.promises.append(apid)
        new_solid_geometry = []

        with self.app.proc_container.new(_("Parsing aperture %s geometry ..." % str(apid))):
            for geo_silk in geo:
                for ap in self.sm_obj.apertures:
                    for solder_poly in self.sm_obj.apertures[ap]['solid_geometry']:
                        if geo_silk.intersects(solder_poly):

                            new_geo = self.subtract_polygon(geo_silk, solder_poly.exterior)

                            if not new_geo.is_empty:
                                new_solid_geometry.append(new_geo)
                        else:
                            new_solid_geometry.append(geo)

        if new_solid_geometry:
            while True:
                if self.new_apertures[apid]['solid_geometry']:
                    break
                self.new_apertures[apid]['solid_geometry'] = new_solid_geometry
                time.sleep(0.5)

        while True:
            # removal from list is done in a multithreaded way therefore not always the removal can be done
            # so we keep trying until it's done
            if apid not in self.promises:
                break
            self.promises.remove(apid)
            time.sleep(0.5)

        log.debug("Promise fulfilled: %s" % str(apid))

    def subtract_polygon(self, silk_geo, sm_exterior):
        """
        Subtract polygon from the given object. This only operates on the paths in the original geometry, i.e.
        it converts polygons into paths.

        :param silk_geo: The geometry from which to substract.
        :param sm_exterior: The substractor geometry
        :return: none
        """

        geo = cascaded_union(silk_geo)
        diff_geo = geo.difference(sm_exterior)
        return diff_geo

    def flatten(self, geometry=None, reset=True, pathonly=False):
        """
        Creates a list of non-iterable linear geometry objects.
        Polygons are expanded into its exterior and interiors if specified.

        Results are placed in self.flat_geometry

        :param geometry: Shapely type or list or list of list of such.
        :param reset: Clears the contents of self.flat_geometry.
        :param pathonly: Expands polygons into linear elements.
        """

        if geometry is None:
            log.debug("ToolSilk.flatten() --> There is no Geometry to flatten")
            return

        if reset:
            self.flat_geometry = []

        # If iterable, expand recursively. 
        try:
            for geo in geometry:
                if geo is not None:
                    self.flatten(geometry=geo,
                                 reset=False,
                                 pathonly=pathonly)

        # Not iterable, do the actual indexing and add.
        except TypeError:
            if pathonly and type(geometry) == Polygon:
                self.flat_geometry.append(geometry.exterior)
                self.flatten(geometry=geometry.interiors,
                             reset=False,
                             pathonly=True)
            else:
                self.flat_geometry.append(geometry)

        log.debug("%d paths" % len(self.flat_geometry))
        return self.flat_geometry

    def periodic_check(self, check_period, reset=False):
        """
        This function starts an QTimer and it will periodically check if intersections are done

        :param check_period: time at which to check periodically
        :param reset: will reset the timer
        :return:
        """

        log.debug("ToolSilk --> Periodic Check started.")

        try:
            self.check_thread.stop()
        except:
            pass

        if reset:
            self.check_thread.setInterval(check_period)
            try:
                self.check_thread.timeout.disconnect(self.periodic_check_handler)
            except:
                pass

        self.check_thread.timeout.connect(self.periodic_check_handler)
        self.check_thread.start(QtCore.QThread.HighPriority)

    def periodic_check_handler(self):
        """
        If the intersections workers finished then start creating the solid_geometry
        :return:
        """
        # log.debug("checking parsing --> %s" % str(self.parsing_promises))

        outname = self.silk_object_combo.currentText() + '_cleaned'

        try:
            if not self.promises:
                self.check_thread.stop()
                # intersection jobs finished, start the creation of solid_geometry
                self.app.worker_task.emit({'fcn': self.new_silkscreen_object,
                                           'params': [outname]})

                log.debug("ToolSilk --> Periodic check finished.")
        except Exception:
            traceback.print_exc()

    def new_silkscreen_object(self, outname):

        def obj_init(grb_obj, app_obj):

            grb_obj.apertures = deepcopy(self.new_apertures)

            poly_buff = []
            for ap in self.new_apertures:
                for k in self.new_apertures[ap]:
                    if k == 'solid_geometry':
                        poly_buff += self.new_apertures[ap][k]

            poly_buff = unary_union(poly_buff)
            try:
                poly_buff = poly_buff.buffer(0.0000001)
            except ValueError:
                pass
            try:
                poly_buff = poly_buff.buffer(-0.0000001)
            except ValueError:
                pass

            grb_obj.solid_geometry = deepcopy(poly_buff)
            # self.new_apertures.clear()

        with self.app.proc_container.new(_("Generating cleaned SS object ...")):
            ret = self.app.new_object('gerber', outname, obj_init, autoselected=False)
            if ret == 'fail':
                self.app.inform.emit(_('[ERROR_NOTCL] Generating SilkScreen file failed.'))
                return
            # Register recent file
            self.app.file_opened.emit('gerber', outname)
            # GUI feedback
            self.app.inform.emit(_("[success] Created: %s") % outname)

    def reset_fields(self):
        self.silk_object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.sm_object_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
