# ########################################################## ##
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 4/24/2019                                          #
# MIT Licence                                              #
# ########################################################## ##


from FlatCAMTool import FlatCAMTool
# from copy import copy, deepcopy
from ObjectCollection import *
import time

import gettext
import FlatCAMTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext


class ToolSub(FlatCAMTool):

    toolName = _("Substract Tool")

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

        self.gerber_title = QtWidgets.QLabel("<b>%s</b>" % _("Gerber Objects"))
        form_layout.addRow(self.gerber_title)

        # Target Gerber Object
        self.target_gerber_combo = QtWidgets.QComboBox()
        self.target_gerber_combo.setModel(self.app.collection)
        self.target_gerber_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.target_gerber_combo.setCurrentIndex(1)

        self.target_gerber_label = QtWidgets.QLabel('%s:' % _("Target"))
        self.target_gerber_label.setToolTip(
            _("Gerber object from which to substract\n"
              "the substractor Gerber object.")
        )

        form_layout.addRow(self.target_gerber_label, self.target_gerber_combo)

        # Substractor Gerber Object
        self.sub_gerber_combo = QtWidgets.QComboBox()
        self.sub_gerber_combo.setModel(self.app.collection)
        self.sub_gerber_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.sub_gerber_combo.setCurrentIndex(1)

        self.sub_gerber_label = QtWidgets.QLabel('%s:' % _("Substractor"))
        self.sub_gerber_label.setToolTip(
            _("Gerber object that will be substracted\n"
              "from the target Gerber object.")
        )
        e_lab_1 = QtWidgets.QLabel('')

        form_layout.addRow(self.sub_gerber_label, self.sub_gerber_combo)

        self.intersect_btn = FCButton(_('Substract Gerber'))
        self.intersect_btn.setToolTip(
            _("Will remove the area occupied by the substractor\n"
              "Gerber from the Target Gerber.\n"
              "Can be used to remove the overlapping silkscreen\n"
              "over the soldermask.")
        )
        self.tools_box.addWidget(self.intersect_btn)
        self.tools_box.addWidget(e_lab_1)

        # Form Layout
        form_geo_layout = QtWidgets.QFormLayout()
        self.tools_box.addLayout(form_geo_layout)

        self.geo_title = QtWidgets.QLabel("<b>%s</b>" % _("Geometry Objects"))
        form_geo_layout.addRow(self.geo_title)

        # Target Geometry Object
        self.target_geo_combo = QtWidgets.QComboBox()
        self.target_geo_combo.setModel(self.app.collection)
        self.target_geo_combo.setRootModelIndex(self.app.collection.index(2, 0, QtCore.QModelIndex()))
        self.target_geo_combo.setCurrentIndex(1)

        self.target_geo_label = QtWidgets.QLabel('%s:' % _("Target"))
        self.target_geo_label.setToolTip(
            _("Geometry object from which to substract\n"
              "the substractor Geometry object.")
        )

        form_geo_layout.addRow(self.target_geo_label, self.target_geo_combo)

        # Substractor Geometry Object
        self.sub_geo_combo = QtWidgets.QComboBox()
        self.sub_geo_combo.setModel(self.app.collection)
        self.sub_geo_combo.setRootModelIndex(self.app.collection.index(2, 0, QtCore.QModelIndex()))
        self.sub_geo_combo.setCurrentIndex(1)

        self.sub_geo_label = QtWidgets.QLabel('%s:' % _("Substractor"))
        self.sub_geo_label.setToolTip(
            _("Geometry object that will be substracted\n"
              "from the target Geometry object.")
        )
        e_lab_1 = QtWidgets.QLabel('')

        form_geo_layout.addRow(self.sub_geo_label, self.sub_geo_combo)

        self.close_paths_cb = FCCheckBox(_("Close paths"))
        self.close_paths_cb.setToolTip(_("Checking this will close the paths cut by the Geometry substractor object."))
        self.tools_box.addWidget(self.close_paths_cb)

        self.intersect_geo_btn = FCButton(_('Substract Geometry'))
        self.intersect_geo_btn.setToolTip(
            _("Will remove the area occupied by the substractor\n"
              "Geometry from the Target Geometry.")
        )
        self.tools_box.addWidget(self.intersect_geo_btn)
        self.tools_box.addWidget(e_lab_1)

        self.tools_box.addStretch()

        # QTimer for periodic check
        self.check_thread = QtCore.QTimer()
        # Every time an intersection job is started we add a promise; every time an intersection job is finished
        # we remove a promise.
        # When empty we start the layer rendering
        self.promises = []

        self.new_apertures = {}
        self.new_tools = {}
        self.new_solid_geometry = []

        self.sub_solid_union = None
        self.sub_follow_union = None
        self.sub_clear_union = None

        self.sub_grb_obj = None
        self.sub_grb_obj_name = None
        self.target_grb_obj = None
        self.target_grb_obj_name = None

        self.sub_geo_obj = None
        self.sub_geo_obj_name = None
        self.target_geo_obj = None
        self.target_geo_obj_name = None

        # signal which type of substraction to do: "geo" or "gerber"
        self.sub_type = None

        # store here the options from target_obj
        self.target_options = {}

        self.sub_union = []

        try:
            self.intersect_btn.clicked.disconnect(self.on_grb_intersection_click)
        except (TypeError, AttributeError):
            pass
        self.intersect_btn.clicked.connect(self.on_grb_intersection_click)

        try:
            self.intersect_geo_btn.clicked.disconnect()
        except (TypeError, AttributeError):
            pass
        self.intersect_geo_btn.clicked.connect(self.on_geo_intersection_click)

    def install(self, icon=None, separator=None, **kwargs):
        FlatCAMTool.install(self, icon, separator, shortcut='ALT+W', **kwargs)

    def run(self, toggle=True):
        self.app.report_usage("ToolSub()")

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
        self.new_tools.clear()
        self.new_solid_geometry = []
        self.target_options.clear()

        self.app.ui.notebook.setTabText(2, _("Sub Tool"))

    def set_tool_ui(self):
        self.tools_frame.show()
        self.close_paths_cb.setChecked(self.app.defaults["tools_sub_close_paths"])

    def on_grb_intersection_click(self):
        # reset previous values
        self.new_apertures.clear()
        self.new_solid_geometry = []
        self.sub_union = []

        self.sub_type = "gerber"

        self.target_grb_obj_name = self.target_gerber_combo.currentText()
        if self.target_grb_obj_name == '':
            self.app.inform.emit(_("[ERROR_NOTCL] No Target object loaded."))
            return

        # Get target object.
        try:
            self.target_grb_obj = self.app.collection.get_by_name(self.target_grb_obj_name)
        except Exception as e:
            log.debug("ToolSub.on_grb_intersection_click() --> %s" % str(e))
            self.app.inform.emit(_("[ERROR_NOTCL] Could not retrieve object: %s") % self.obj_name)
            return "Could not retrieve object: %s" % self.target_grb_obj_name

        self.sub_grb_obj_name = self.sub_gerber_combo.currentText()
        if self.sub_grb_obj_name == '':
            self.app.inform.emit(_("[ERROR_NOTCL] No Substractor object loaded."))
            return

        # Get substractor object.
        try:
            self.sub_grb_obj = self.app.collection.get_by_name(self.sub_grb_obj_name)
        except Exception as e:
            log.debug("ToolSub.on_grb_intersection_click() --> %s" % str(e))
            self.app.inform.emit(_("[ERROR_NOTCL] Could not retrieve object: %s") % self.obj_name)
            return "Could not retrieve object: %s" % self.sub_grb_obj_name

        # crate the new_apertures dict structure
        for apid in self.target_grb_obj.apertures:
            self.new_apertures[apid] = {}
            self.new_apertures[apid]['type'] = 'C'
            self.new_apertures[apid]['size'] = self.target_grb_obj.apertures[apid]['size']
            self.new_apertures[apid]['geometry'] = []

        geo_solid_union_list = []
        geo_follow_union_list = []
        geo_clear_union_list = []

        for apid1 in self.sub_grb_obj.apertures:
            if 'geometry' in self.sub_grb_obj.apertures[apid1]:
                for elem in self.sub_grb_obj.apertures[apid1]['geometry']:
                    if 'solid' in elem:
                        geo_solid_union_list.append(elem['solid'])
                    if 'follow' in elem:
                        geo_follow_union_list.append(elem['follow'])
                    if 'clear' in elem:
                        geo_clear_union_list.append(elem['clear'])

        self.sub_solid_union = cascaded_union(geo_solid_union_list)
        self.sub_follow_union = cascaded_union(geo_follow_union_list)
        self.sub_clear_union = cascaded_union(geo_clear_union_list)

        # add the promises
        for apid in self.target_grb_obj.apertures:
            self.promises.append(apid)

        # start the QTimer to check for promises with 1 second period check
        self.periodic_check(500, reset=True)

        for apid in self.target_grb_obj.apertures:
            geo = self.target_grb_obj.apertures[apid]['geometry']
            self.app.worker_task.emit({'fcn': self.aperture_intersection,
                                       'params': [apid, geo]})

    def aperture_intersection(self, apid, geo):
        new_geometry = []

        log.debug("Working on promise: %s" % str(apid))

        with self.app.proc_container.new(_("Parsing aperture %s geometry ..." % str(apid))):
            for geo_el in geo:
                new_el = dict()

                if 'solid' in geo_el:
                    work_geo = geo_el['solid']
                    if self.sub_solid_union:
                        if work_geo.intersects(self.sub_solid_union):
                            new_geo = work_geo.difference(self.sub_solid_union)
                            new_geo = new_geo.buffer(0)
                            if new_geo:
                                if not new_geo.is_empty:
                                    new_el['solid'] = new_geo
                                else:
                                    new_el['solid'] = work_geo
                            else:
                                new_el['solid'] = work_geo
                        else:
                            new_el['solid'] = work_geo
                    else:
                        new_el['solid'] = work_geo

                if 'follow' in geo_el:
                    work_geo = geo_el['follow']
                    if self.sub_follow_union:
                        if work_geo.intersects(self.sub_follow_union):
                            new_geo = work_geo.difference(self.sub_follow_union)
                            new_geo = new_geo.buffer(0)
                            if new_geo:
                                if not new_geo.is_empty:
                                    new_el['follow'] = new_geo
                                else:
                                    new_el['follow'] = work_geo
                            else:
                                new_el['follow'] = work_geo
                        else:
                            new_el['follow'] = work_geo
                    else:
                        new_el['follow'] = work_geo

                if 'clear' in geo_el:
                    work_geo = geo_el['clear']
                    if self.sub_clear_union:
                        if work_geo.intersects(self.sub_clear_union):
                            new_geo = work_geo.difference(self.sub_clear_union)
                            new_geo = new_geo.buffer(0)
                            if new_geo:
                                if not new_geo.is_empty:
                                    new_el['clear'] = new_geo
                                else:
                                    new_el['clear'] = work_geo
                            else:
                                new_el['clear'] = work_geo
                        else:
                            new_el['clear'] = work_geo
                    else:
                        new_el['clear'] = work_geo

                new_geometry.append(deepcopy(new_el))

        if new_geometry:
            while not self.new_apertures[apid]['geometry']:
                self.new_apertures[apid]['geometry'] = deepcopy(new_geometry)
                time.sleep(0.5)

        while True:
            # removal from list is done in a multithreaded way therefore not always the removal can be done
            # so we keep trying until it's done
            if apid not in self.promises:
                break

            self.promises.remove(apid)
            time.sleep(0.5)

        log.debug("Promise fulfilled: %s" % str(apid))

    def new_gerber_object(self, outname):

        def obj_init(grb_obj, app_obj):

            grb_obj.apertures = deepcopy(self.new_apertures)

            poly_buff = []
            follow_buff = []
            for ap in self.new_apertures:
                for elem in self.new_apertures[ap]['geometry']:
                    poly_buff.append(elem['solid'])
                    follow_buff.append(elem['follow'])

            work_poly_buff = cascaded_union(poly_buff)
            try:
                poly_buff = work_poly_buff.buffer(0.0000001)
            except ValueError:
                pass
            try:
                poly_buff = poly_buff.buffer(-0.0000001)
            except ValueError:
                pass

            grb_obj.solid_geometry = deepcopy(poly_buff)
            grb_obj.follow_geometry = deepcopy(follow_buff)

        with self.app.proc_container.new(_("Generating new object ...")):
            ret = self.app.new_object('gerber', outname, obj_init, autoselected=False)
            if ret == 'fail':
                self.app.inform.emit(_('[ERROR_NOTCL] Generating new object failed.'))
                return

            # GUI feedback
            self.app.inform.emit(_("[success] Created: %s") % outname)

            # cleanup
            self.new_apertures.clear()
            self.new_solid_geometry[:] = []
            self.sub_union[:] = []

    def on_geo_intersection_click(self):
        # reset previous values
        self.new_tools.clear()
        self.target_options.clear()
        self.new_solid_geometry = []
        self.sub_union = []

        self.sub_type = "geo"

        self.target_geo_obj_name = self.target_geo_combo.currentText()
        if self.target_geo_obj_name == '':
            self.app.inform.emit(_("[ERROR_NOTCL] No Target object loaded."))
            return

        # Get target object.
        try:
            self.target_geo_obj = self.app.collection.get_by_name(self.target_geo_obj_name)
        except Exception as e:
            log.debug("ToolSub.on_geo_intersection_click() --> %s" % str(e))
            self.app.inform.emit(_("[ERROR_NOTCL] Could not retrieve object: %s") % self.target_geo_obj_name)
            return "Could not retrieve object: %s" % self.target_grb_obj_name

        self.sub_geo_obj_name = self.sub_geo_combo.currentText()
        if self.sub_geo_obj_name == '':
            self.app.inform.emit(_("[ERROR_NOTCL] No Substractor object loaded."))
            return

        # Get substractor object.
        try:
            self.sub_geo_obj = self.app.collection.get_by_name(self.sub_geo_obj_name)
        except Exception as e:
            log.debug("ToolSub.on_geo_intersection_click() --> %s" % str(e))
            self.app.inform.emit(_("[ERROR_NOTCL] Could not retrieve object: %s") % self.sub_geo_obj_name)
            return "Could not retrieve object: %s" % self.sub_geo_obj_name

        if self.sub_geo_obj.multigeo:
            self.app.inform.emit(_("[ERROR_NOTCL] Currently, the Substractor geometry cannot be of type Multigeo."))
            return

        # create the target_options obj
        self.target_options = {}
        for opt in self.target_geo_obj.options:
            if opt != 'name':
                self.target_options[opt] = deepcopy(self.target_geo_obj.options[opt])

        # crate the new_tools dict structure
        for tool in self.target_geo_obj.tools:
            self.new_tools[tool] = {}
            for key in self.target_geo_obj.tools[tool]:
                if key == 'solid_geometry':
                    self.new_tools[tool][key] = []
                else:
                    self.new_tools[tool][key] = deepcopy(self.target_geo_obj.tools[tool][key])

        # add the promises
        if self.target_geo_obj.multigeo:
            for tool in self.target_geo_obj.tools:
                self.promises.append(tool)
        else:
            self.promises.append("single")

        self.sub_union = cascaded_union(self.sub_geo_obj.solid_geometry)

        # start the QTimer to check for promises with 0.5 second period check
        self.periodic_check(500, reset=True)

        if self.target_geo_obj.multigeo:
            for tool in self.target_geo_obj.tools:
                geo = self.target_geo_obj.tools[tool]['solid_geometry']
                self.app.worker_task.emit({'fcn': self.toolgeo_intersection,
                                           'params': [tool, geo]})
        else:
            geo = self.target_geo_obj.solid_geometry
            self.app.worker_task.emit({'fcn': self.toolgeo_intersection,
                                       'params': ["single", geo]})

    def toolgeo_intersection(self, tool, geo):
        new_geometry = []
        log.debug("Working on promise: %s" % str(tool))

        if tool == "single":
            text = _("Parsing solid_geometry ...")
        else:
            text = _("Parsing tool %s geometry ...") % str(tool)

        with self.app.proc_container.new(text):
            # resulting paths are closed resulting into Polygons
            if self.close_paths_cb.isChecked():
                new_geo = (cascaded_union(geo)).difference(self.sub_union)
                if new_geo:
                    if not new_geo.is_empty:
                        new_geometry.append(new_geo)
            # resulting paths are unclosed resulting in a multitude of rings
            else:
                try:
                    for geo_elem in geo:
                        if isinstance(geo_elem, Polygon):
                            for ring in self.poly2rings(geo_elem):
                                new_geo = ring.difference(self.sub_union)
                                if new_geo:
                                    if not new_geo.is_empty:
                                        new_geometry.append(new_geo)
                        elif isinstance(geo_elem, MultiPolygon):
                            for poly in geo_elem:
                                for ring in self.poly2rings(poly):
                                    new_geo = ring.difference(self.sub_union)
                                    if new_geo:
                                        if not new_geo.is_empty:
                                            new_geometry.append(new_geo)
                        elif isinstance(geo_elem, LineString):
                            new_geo = geo_elem.difference(self.sub_union)
                            if new_geo:
                                if not new_geo.is_empty:
                                    new_geometry.append(new_geo)
                        elif isinstance(geo_elem, MultiLineString):
                            for line_elem in geo_elem:
                                new_geo = line_elem.difference(self.sub_union)
                                if new_geo:
                                    if not new_geo.is_empty:
                                        new_geometry.append(new_geo)
                except TypeError:
                    if isinstance(geo, Polygon):
                        for ring in self.poly2rings(geo):
                            new_geo = ring.difference(self.sub_union)
                            if new_geo:
                                if not new_geo.is_empty:
                                    new_geometry.append(new_geo)
                    elif isinstance(geo, LineString):
                        new_geo = geo.difference(self.sub_union)
                        if new_geo:
                            if not new_geo.is_empty:
                                new_geometry.append(new_geo)
                    elif isinstance(geo, MultiLineString):
                        for line_elem in geo:
                            new_geo = line_elem.difference(self.sub_union)
                            if new_geo:
                                if not new_geo.is_empty:
                                    new_geometry.append(new_geo)

        if new_geometry:
            if tool == "single":
                while not self.new_solid_geometry:
                    self.new_solid_geometry = deepcopy(new_geometry)
                    time.sleep(0.5)
            else:
                while not self.new_tools[tool]['solid_geometry']:
                    self.new_tools[tool]['solid_geometry'] = deepcopy(new_geometry)
                    time.sleep(0.5)

        while True:
            # removal from list is done in a multithreaded way therefore not always the removal can be done
            # so we keep trying until it's done
            if tool not in self.promises:
                break

            self.promises.remove(tool)
            time.sleep(0.5)
        log.debug("Promise fulfilled: %s" % str(tool))

    def new_geo_object(self, outname):
        def obj_init(geo_obj, app_obj):

            geo_obj.options = deepcopy(self.target_options)
            geo_obj.options['name'] = outname

            if self.target_geo_obj.multigeo:
                geo_obj.tools = deepcopy(self.new_tools)
                # this turn on the FlatCAMCNCJob plot for multiple tools
                geo_obj.multigeo = True
                geo_obj.multitool = True
            else:
                geo_obj.solid_geometry = deepcopy(self.new_solid_geometry)
                try:
                    geo_obj.tools = deepcopy(self.new_tools)
                    for tool in geo_obj.tools:
                        geo_obj.tools[tool]['solid_geometry'] = deepcopy(self.new_solid_geometry)
                except Exception as e:
                    log.debug("ToolSub.new_geo_object() --> %s" % str(e))

        with self.app.proc_container.new(_("Generating new object ...")):
            ret = self.app.new_object('geometry', outname, obj_init, autoselected=False)
            if ret == 'fail':
                self.app.inform.emit(_('[ERROR_NOTCL] Generating new object failed.'))
                return
            # Register recent file
            self.app.file_opened.emit('geometry', outname)
            # GUI feedback
            self.app.inform.emit(_("[success] Created: %s") % outname)

            # cleanup
            self.new_tools.clear()
            self.new_solid_geometry[:] = []
            self.sub_union[:] = []

    def periodic_check(self, check_period, reset=False):
        """
        This function starts an QTimer and it will periodically check if intersections are done

        :param check_period: time at which to check periodically
        :param reset: will reset the timer
        :return:
        """

        log.debug("ToolSub --> Periodic Check started.")

        try:
            self.check_thread.stop()
        except (TypeError, AttributeError):
            pass

        if reset:
            self.check_thread.setInterval(check_period)
            try:
                self.check_thread.timeout.disconnect(self.periodic_check_handler)
            except (TypeError, AttributeError):
                pass

        self.check_thread.timeout.connect(self.periodic_check_handler)
        self.check_thread.start(QtCore.QThread.HighPriority)

    def periodic_check_handler(self):
        """
        If the intersections workers finished then start creating the solid_geometry
        :return:
        """
        # log.debug("checking parsing --> %s" % str(self.parsing_promises))

        try:
            if not self.promises:
                self.check_thread.stop()
                if self.sub_type == "gerber":
                    outname = self.target_gerber_combo.currentText() + '_sub'

                    # intersection jobs finished, start the creation of solid_geometry
                    self.app.worker_task.emit({'fcn': self.new_gerber_object,
                                               'params': [outname]})
                else:
                    outname = self.target_geo_combo.currentText() + '_sub'

                    # intersection jobs finished, start the creation of solid_geometry
                    self.app.worker_task.emit({'fcn': self.new_geo_object,
                                               'params': [outname]})

                # reset the type of substraction for next time
                self.sub_type = None

                log.debug("ToolSub --> Periodic check finished.")
        except Exception as e:
            log.debug("ToolSub().periodic_check_handler() --> %s" % str(e))
            traceback.print_exc()

    def reset_fields(self):
        self.target_gerber_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.sub_gerber_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))

        self.target_geo_combo.setRootModelIndex(self.app.collection.index(2, 0, QtCore.QModelIndex()))
        self.sub_geo_combo.setRootModelIndex(self.app.collection.index(2, 0, QtCore.QModelIndex()))

    @staticmethod
    def poly2rings(poly):
        return [poly.exterior] + [interior for interior in poly.interiors]
# end of file
