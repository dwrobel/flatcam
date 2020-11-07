# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 4/24/2019                                          #
# MIT Licence                                              #
# ##########################################################

from PyQt5 import QtWidgets, QtCore, QtGui

from appTool import AppTool
from appGUI.GUIElements import FCCheckBox, FCButton, FCComboBox

from shapely.geometry import Polygon, MultiPolygon, MultiLineString, LineString
from shapely.ops import unary_union

import traceback
from copy import deepcopy
import time
import logging
import gettext
import appTranslation as fcTranslate
import builtins

fcTranslate.apply_language('strings')
if '_' not in builtins.__dict__:
    _ = gettext.gettext

log = logging.getLogger('base')


class ToolSub(AppTool):

    job_finished = QtCore.pyqtSignal(bool)

    # the string param is the outname and the list is a list of tuples each being formed from the new_aperture_geometry
    # list and the second element is also a list with possible geometry that needs to be added to the '0' aperture
    # meaning geometry that was deformed
    aperture_processing_finished = QtCore.pyqtSignal(str, list)

    def __init__(self, app):
        self.app = app
        self.decimals = self.app.decimals

        AppTool.__init__(self, app)

        # #############################################################################
        # ######################### Tool GUI ##########################################
        # #############################################################################
        self.ui = SubUI(layout=self.layout, app=self.app)
        self.toolName = self.ui.toolName

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

        # multiprocessing
        self.pool = self.app.pool
        self.results = []

        # Signals
        self.ui.intersect_btn.clicked.connect(self.on_subtract_gerber_click)
        self.ui.intersect_geo_btn.clicked.connect(self.on_subtract_geo_click)
        self.ui.reset_button.clicked.connect(self.set_tool_ui)

        # Custom Signals
        self.job_finished.connect(self.on_job_finished)
        self.aperture_processing_finished.connect(self.new_gerber_object)

    def install(self, icon=None, separator=None, **kwargs):
        AppTool.install(self, icon, separator, shortcut='Alt+W', **kwargs)

    def run(self, toggle=True):
        self.app.defaults.report_usage("ToolSub()")

        if toggle:
            # if the splitter is hidden, display it, else hide it but only if the current widget is the same
            if self.app.ui.splitter.sizes()[0] == 0:
                self.app.ui.splitter.setSizes([1, 1])
            else:
                try:
                    if self.app.ui.tool_scroll_area.widget().objectName() == self.toolName:
                        # if tab is populated with the tool but it does not have the focus, focus on it
                        if not self.app.ui.notebook.currentWidget() is self.app.ui.tool_tab:
                            # focus on Tool Tab
                            self.app.ui.notebook.setCurrentWidget(self.app.ui.tool_tab)
                        else:
                            self.app.ui.splitter.setSizes([0, 1])
                except AttributeError:
                    pass
        else:
            if self.app.ui.splitter.sizes()[0] == 0:
                self.app.ui.splitter.setSizes([1, 1])

        AppTool.run(self)
        self.set_tool_ui()

        self.app.ui.notebook.setTabText(2, _("Sub Tool"))

    def set_tool_ui(self):
        self.new_apertures.clear()
        self.new_tools.clear()
        self.new_solid_geometry = []
        self.target_options.clear()

        self.ui.tools_frame.show()
        self.ui.close_paths_cb.setChecked(self.app.defaults["tools_sub_close_paths"])
        self.ui.delete_sources_cb.setChecked(self.app.defaults["tools_sub_delete_sources"])

    def on_subtract_gerber_click(self):
        # reset previous values
        self.new_apertures.clear()
        self.new_solid_geometry = []
        self.sub_union = []

        self.sub_type = "gerber"

        # --------------------------------
        # Get TARGET name
        # --------------------------------
        self.target_grb_obj_name = self.ui.target_gerber_combo.currentText()
        if self.target_grb_obj_name == '':
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("No Target object loaded."))
            return

        self.app.inform.emit('%s' % _("Loading geometry from Gerber objects."))

        # --------------------------------
        # Get TARGET object.
        # --------------------------------
        try:
            self.target_grb_obj = self.app.collection.get_by_name(self.target_grb_obj_name)
        except Exception as e:
            log.debug("ToolSub.on_subtract_gerber_click() --> %s" % str(e))
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Could not retrieve object"), self.obj_name))
            return "Could not retrieve object: %s" % self.target_grb_obj_name

        # --------------------------------
        # Get SUBTRACTOR name
        # --------------------------------
        self.sub_grb_obj_name = self.ui.sub_gerber_combo.currentText()
        if self.sub_grb_obj_name == '':
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("No Subtractor object loaded."))
            return

        # --------------------------------
        # Get SUBTRACTOR object.
        # --------------------------------
        try:
            self.sub_grb_obj = self.app.collection.get_by_name(self.sub_grb_obj_name)
        except Exception as e:
            log.debug("ToolSub.on_subtract_gerber_click() --> %s" % str(e))
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Could not retrieve object"), self.obj_name))
            return "Could not retrieve object: %s" % self.sub_grb_obj_name

        # --------------------------------
        # crate the new_apertures
        # dict structure from TARGET apertures
        # --------------------------------
        for apid in self.target_grb_obj.apertures:
            self.new_apertures[apid] = {}
            for key in self.target_grb_obj.apertures[apid]:
                if key == 'geometry':
                    self.new_apertures[apid]['geometry'] = []
                else:
                    self.new_apertures[apid][key] = self.target_grb_obj.apertures[apid][key]

        def worker_job(app_obj):
            with app_obj.app.proc_container.new('%s' % _("Working ...")):
                # SUBTRACTOR geometry (always the same)
                sub_geometry = {'solid': [], 'clear': []}
                # iterate over SUBTRACTOR geometry and load it in the sub_geometry dict
                for s_apid in app_obj.sub_grb_obj.apertures:
                    for s_el in app_obj.sub_grb_obj.apertures[s_apid]['geometry']:
                        if "solid" in s_el:
                            sub_geometry['solid'].append(s_el["solid"])
                        if "clear" in s_el:
                            sub_geometry['clear'].append(s_el["clear"])

                for ap_id in app_obj.target_grb_obj.apertures:
                    # TARGET geometry
                    target_geo = [geo for geo in app_obj.target_grb_obj.apertures[ap_id]['geometry']]

                    # send the job to the multiprocessing JOB
                    app_obj.results.append(
                        app_obj.pool.apply_async(app_obj.aperture_intersection, args=(ap_id, target_geo, sub_geometry))
                    )

                output = []
                for p in app_obj.results:
                    res = p.get()
                    output.append(res)
                    app_obj.app.inform.emit('%s: %s...' % (_("Finished parsing geometry for aperture"), str(res[0])))

                app_obj.app.inform.emit("%s" % _("Subtraction aperture processing finished."))

                outname = app_obj.ui.target_gerber_combo.currentText() + '_sub'
                app_obj.aperture_processing_finished.emit(outname, output)

        self.app.worker_task.emit({'fcn': worker_job, 'params': [self]})

    @staticmethod
    def aperture_intersection(apid, target_geo, sub_geometry):
        """

        :param apid:            the aperture id for which we process geometry
        :type apid:             str
        :param target_geo:      the geometry list that holds the geometry from which we subtract
        :type target_geo:       list
        :param sub_geometry:    the apertures dict that holds all the geometry that is subtracted
        :type sub_geometry:     dict
        :return:                (apid, unaffected_geometry lsit, affected_geometry list)
        :rtype:                 tuple
        """

        unafected_geo = []
        affected_geo = []

        for target_geo_obj in target_geo:
            solid_is_modified = False
            destination_geo_obj = {}
            if "solid" in target_geo_obj:
                diff = []
                for sub_solid_geo in sub_geometry["solid"]:
                    if target_geo_obj["solid"].intersects(sub_solid_geo):
                        new_geo = target_geo_obj["solid"].difference(sub_solid_geo)
                        if not new_geo.is_empty:
                            diff.append(new_geo)
                            solid_is_modified = True
                if solid_is_modified:
                    target_geo_obj["solid"] = unary_union(diff)
                destination_geo_obj["solid"] = deepcopy(target_geo_obj["solid"])

            clear_is_modified = False
            if "clear" in target_geo_obj:
                clear_diff = []
                for sub_clear_geo in sub_geometry["clear"]:
                    if target_geo_obj["clear"].intersects(sub_clear_geo):
                        new_geo = target_geo_obj["clear"].difference(sub_clear_geo)
                        if not new_geo.is_empty:
                            clear_diff.append(new_geo)
                            clear_is_modified = True
                if clear_is_modified:
                    target_geo_obj["clear"] = unary_union(clear_diff)
                destination_geo_obj["clear"] = deepcopy(target_geo_obj["clear"])

            if solid_is_modified or clear_is_modified:
                affected_geo.append(deepcopy(destination_geo_obj))
            else:
                unafected_geo.append(deepcopy(destination_geo_obj))

        return apid, unafected_geo, affected_geo

    def new_gerber_object(self, outname, output):
        """

        :param outname:     name for the new Gerber object
        :type outname:      str
        :param output:      a list made of tuples in format:
                            (aperture id in the target Gerber, unaffected_geometry list, affected_geometry list)
        :type output:       list
        :return:
        :rtype:
        """

        def obj_init(grb_obj, app_obj):

            grb_obj.apertures = deepcopy(self.new_apertures)

            if '0' not in grb_obj.apertures:
                grb_obj.apertures['0'] = {}
                grb_obj.apertures['0']['type'] = 'REG'
                grb_obj.apertures['0']['size'] = 0.0
                grb_obj.apertures['0']['geometry'] = []

            for apid in list(grb_obj.apertures.keys()):
                # output is a tuple in the format (apid, surviving_geo, modified_geo)
                # apid is the aperture id (key in the obj.apertures and string)
                # unaffected_geo and affected_geo are lists
                for t in output:
                    new_apid = t[0]
                    if apid == new_apid:
                        surving_geo = t[1]
                        modified_geo = t[2]
                        if surving_geo:
                            grb_obj.apertures[apid]['geometry'] += deepcopy(surving_geo)

                        if modified_geo:
                            grb_obj.apertures['0']['geometry'] += modified_geo

                # if the current aperture does not have geometry then get rid of it
                if not grb_obj.apertures[apid]['geometry']:
                    grb_obj.apertures.pop(apid, None)

            # delete the '0' aperture if it has no geometry
            if not grb_obj.apertures['0']['geometry']:
                grb_obj.apertures.pop('0', None)

            poly_buff = []
            follow_buff = []
            for ap in grb_obj.apertures:
                for elem in grb_obj.apertures[ap]['geometry']:
                    if 'solid' in elem:
                        solid_geo = elem['solid']
                        poly_buff.append(solid_geo)
                    if 'follow' in elem:
                        follow_buff.append(elem['follow'])

            work_poly_buff = MultiPolygon(poly_buff)
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
            grb_obj.source_file = app_obj.f_handlers.export_gerber(obj_name=outname, filename=None,
                                                                   local_use=grb_obj, use_thread=False)

        with self.app.proc_container.new(_("New object ...")):
            ret = self.app.app_obj.new_object('gerber', outname, obj_init, autoselected=False)
            if ret == 'fail':
                self.app.inform.emit('[ERROR_NOTCL] %s' % _('Generating new object failed.'))
                return

            # GUI feedback
            self.app.inform.emit('[success] %s: %s' % (_("Created"), outname))

            # Delete source objects if it was selected
            if self.ui.delete_sources_cb.get_value():
                self.app.collection.delete_by_name(self.target_grb_obj_name)
                self.app.collection.delete_by_name(self.sub_grb_obj_name)

            # cleanup
            self.new_apertures.clear()
            self.new_solid_geometry[:] = []
            self.results = []

    def on_subtract_geo_click(self):
        # reset previous values
        self.new_tools.clear()
        self.target_options.clear()
        self.new_solid_geometry = []
        self.sub_union = []

        self.sub_type = "geo"

        self.target_geo_obj_name = self.ui.target_geo_combo.currentText()
        if self.target_geo_obj_name == '':
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("No Target object loaded."))
            return

        # Get target object.
        try:
            self.target_geo_obj = self.app.collection.get_by_name(self.target_geo_obj_name)
        except Exception as e:
            log.debug("ToolSub.on_subtract_geo_click() --> %s" % str(e))
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Could not retrieve object"), self.target_geo_obj_name))
            return "Could not retrieve object: %s" % self.target_grb_obj_name

        self.sub_geo_obj_name = self.ui.sub_geo_combo.currentText()
        if self.sub_geo_obj_name == '':
            self.app.inform.emit('[ERROR_NOTCL] %s' % _("No Subtractor object loaded."))
            return

        # Get substractor object.
        try:
            self.sub_geo_obj = self.app.collection.get_by_name(self.sub_geo_obj_name)
        except Exception as e:
            log.debug("ToolSub.on_subtract_geo_click() --> %s" % str(e))
            self.app.inform.emit('[ERROR_NOTCL] %s: %s' % (_("Could not retrieve object"), self.sub_geo_obj_name))
            return "Could not retrieve object: %s" % self.sub_geo_obj_name

        if self.sub_geo_obj.multigeo:
            self.app.inform.emit('[ERROR_NOTCL] %s' %
                                 _("Currently, the Subtractor geometry cannot be of type Multigeo."))
            return

        # create the target_options obj
        # self.target_options = {}
        # for k, v in self.target_geo_obj.options.items():
        #     if k != 'name':
        #         self.target_options[k] = v

        # crate the new_tools dict structure
        for tool in self.target_geo_obj.tools:
            self.new_tools[tool] = {}
            for key, v in self.target_geo_obj.tools[tool]:
                self.new_tools[tool][key] = [] if key == 'solid_geometry' else deepcopy(v)

        # add the promises
        if self.target_geo_obj.multigeo:
            for tool in self.target_geo_obj.tools:
                self.promises.append(tool)
        else:
            self.promises.append("single")

        self.sub_union = unary_union(self.sub_geo_obj.solid_geometry)

        # start the QTimer to check for promises with 0.5 second period check
        self.periodic_check(500, reset=True)

        if self.target_geo_obj.multigeo:
            for tool in self.target_geo_obj.tools:
                geo = self.target_geo_obj.tools[tool]['solid_geometry']
                self.app.worker_task.emit({'fcn': self.toolgeo_intersection, 'params': [tool, geo]})
        else:
            geo = self.target_geo_obj.solid_geometry
            self.app.worker_task.emit({'fcn': self.toolgeo_intersection, 'params': ["single", geo]})

    def toolgeo_intersection(self, tool, geo):
        new_geometry = []
        log.debug("Working on promise: %s" % str(tool))

        if tool == "single":
            text = _("Parsing solid_geometry ...")
        else:
            text = '%s: %s...' % (_("Parsing solid_geometry for tool"), str(tool))

        with self.app.proc_container.new(text):
            # resulting paths are closed resulting into Polygons
            if self.ui.close_paths_cb.isChecked():
                new_geo = (unary_union(geo)).difference(self.sub_union)
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
                                if new_geo and not new_geo.is_empty:
                                    new_geometry.append(new_geo)
                        elif isinstance(geo_elem, MultiPolygon):
                            for poly in geo_elem:
                                for ring in self.poly2rings(poly):
                                    new_geo = ring.difference(self.sub_union)
                                    if new_geo and not new_geo.is_empty:
                                        new_geometry.append(new_geo)
                        elif isinstance(geo_elem, LineString):
                            new_geo = geo_elem.difference(self.sub_union)
                            if new_geo:
                                if not new_geo.is_empty:
                                    new_geometry.append(new_geo)
                        elif isinstance(geo_elem, MultiLineString):
                            for line_elem in geo_elem:
                                new_geo = line_elem.difference(self.sub_union)
                                if new_geo and not new_geo.is_empty:
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
                        if new_geo and not new_geo.is_empty:
                            new_geometry.append(new_geo)
                    elif isinstance(geo, MultiLineString):
                        for line_elem in geo:
                            new_geo = line_elem.difference(self.sub_union)
                            if new_geo and not new_geo.is_empty:
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
        geo_name = outname
        def obj_init(geo_obj, app_obj):

            # geo_obj.options = self.target_options
            # create the target_options obj
            for k, v in self.target_geo_obj.options.items():
                geo_obj.options[k] = v
            geo_obj.options['name'] = geo_name

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
                    app_obj.log.debug("ToolSub.new_geo_object() --> %s" % str(e))
                geo_obj.multigeo = False

        with self.app.proc_container.new(_("New object ...")):
            ret = self.app.app_obj.new_object('geometry', outname, obj_init, autoselected=False)
            if ret == 'fail':
                self.app.inform.emit('[ERROR_NOTCL] %s' % _('Generating new object failed.'))
                return
            # Register recent file
            self.app.file_opened.emit('geometry', outname)
            # GUI feedback
            self.app.inform.emit('[success] %s: %s' % (_("Created"), outname))

            # Delete source objects if it was selected
            if self.ui.delete_sources_cb.get_value():
                self.app.collection.delete_by_name(self.target_geo_obj_name)
                self.app.collection.delete_by_name(self.sub_geo_obj_name)

            # cleanup
            self.new_tools.clear()
            self.new_solid_geometry[:] = []
            self.sub_union = []

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
                self.job_finished.emit(True)

                # reset the type of substraction for next time
                self.sub_type = None

                log.debug("ToolSub --> Periodic check finished.")
        except Exception as e:
            self.job_finished.emit(False)
            log.debug("ToolSub().periodic_check_handler() --> %s" % str(e))
            traceback.print_exc()

    def on_job_finished(self, succcess):
        """

        :param succcess: boolean, this parameter signal if all the apertures were processed
        :return: None
        """
        if succcess is True:
            if self.sub_type == "gerber":
                outname = self.ui.target_gerber_combo.currentText() + '_sub'

                # intersection jobs finished, start the creation of solid_geometry
                self.app.worker_task.emit({'fcn': self.new_gerber_object, 'params': [outname]})
            else:
                outname = self.ui.target_geo_combo.currentText() + '_sub'

                # intersection jobs finished, start the creation of solid_geometry
                self.app.worker_task.emit({'fcn': self.new_geo_object, 'params': [outname]})
        else:
            self.app.inform.emit('[ERROR_NOTCL] %s' % _('Generating new object failed.'))

    def reset_fields(self):
        self.ui.target_gerber_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.ui.sub_gerber_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))

        self.ui.target_geo_combo.setRootModelIndex(self.app.collection.index(2, 0, QtCore.QModelIndex()))
        self.ui.sub_geo_combo.setRootModelIndex(self.app.collection.index(2, 0, QtCore.QModelIndex()))

    @staticmethod
    def poly2rings(poly):
        return [poly.exterior] + [interior for interior in poly.interiors]


class SubUI:

    toolName = _("Subtract Tool")

    def __init__(self, layout, app):
        self.app = app
        self.decimals = self.app.decimals
        self.layout = layout

        # ## Title
        title_label = QtWidgets.QLabel("%s" % self.toolName)
        title_label.setStyleSheet("""
                                QLabel
                                {
                                    font-size: 16px;
                                    font-weight: bold;
                                }
                                """)
        self.layout.addWidget(title_label)
        self.layout.addWidget(QtWidgets.QLabel(""))

        self.tools_frame = QtWidgets.QFrame()
        self.tools_frame.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.tools_frame)
        self.tools_box = QtWidgets.QVBoxLayout()
        self.tools_box.setContentsMargins(0, 0, 0, 0)
        self.tools_frame.setLayout(self.tools_box)

        # Form Layout
        grid0 = QtWidgets.QGridLayout()
        grid0.setColumnStretch(0, 0)
        grid0.setColumnStretch(1, 1)
        self.tools_box.addLayout(grid0)

        self.delete_sources_cb = FCCheckBox(_("Delete source"))
        self.delete_sources_cb.setToolTip(
            _("When checked will delete the source objects\n"
              "after a successful operation.")
        )
        grid0.addWidget(self.delete_sources_cb, 0, 0, 1, 2)

        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.HLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        grid0.addWidget(separator_line, 2, 0, 1, 3)

        grid0.addWidget(QtWidgets.QLabel(''), 4, 0, 1, 2)

        self.gerber_title = QtWidgets.QLabel("<b>%s</b>" % _("GERBER"))
        grid0.addWidget(self.gerber_title, 6, 0, 1, 2)

        # Target Gerber Object
        self.target_gerber_combo = FCComboBox()
        self.target_gerber_combo.setModel(self.app.collection)
        self.target_gerber_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        # self.target_gerber_combo.setCurrentIndex(1)
        self.target_gerber_combo.is_last = True
        self.target_gerber_combo.obj_type = "Gerber"

        self.target_gerber_label = QtWidgets.QLabel('%s:' % _("Target"))
        self.target_gerber_label.setToolTip(
            _("Gerber object from which to subtract\n"
              "the subtractor Gerber object.")
        )

        grid0.addWidget(self.target_gerber_label, 8, 0)
        grid0.addWidget(self.target_gerber_combo, 8, 1)

        # Substractor Gerber Object
        self.sub_gerber_combo = FCComboBox()
        self.sub_gerber_combo.setModel(self.app.collection)
        self.sub_gerber_combo.setRootModelIndex(self.app.collection.index(0, 0, QtCore.QModelIndex()))
        self.sub_gerber_combo.is_last = True
        self.sub_gerber_combo.obj_type = "Gerber"

        self.sub_gerber_label = QtWidgets.QLabel('%s:' % _("Subtractor"))
        self.sub_gerber_label.setToolTip(
            _("Gerber object that will be subtracted\n"
              "from the target Gerber object.")
        )

        grid0.addWidget(self.sub_gerber_label, 10, 0)
        grid0.addWidget(self.sub_gerber_combo, 10, 1)

        self.intersect_btn = FCButton(_('Subtract Gerber'))
        self.intersect_btn.setIcon(QtGui.QIcon(self.app.resource_location + '/subtract_btn32.png'))
        self.intersect_btn.setToolTip(
            _("Will remove the area occupied by the subtractor\n"
              "Gerber from the Target Gerber.\n"
              "Can be used to remove the overlapping silkscreen\n"
              "over the soldermask.")
        )
        self.intersect_btn.setStyleSheet("""
                                QPushButton
                                {
                                    font-weight: bold;
                                }
                                """)
        grid0.addWidget(self.intersect_btn, 12, 0, 1, 2)
        grid0.addWidget(QtWidgets.QLabel(''), 14, 0, 1, 2)

        self.geo_title = QtWidgets.QLabel("<b>%s</b>" % _("GEOMETRY"))
        grid0.addWidget(self.geo_title, 16, 0, 1, 2)

        # Target Geometry Object
        self.target_geo_combo = FCComboBox()
        self.target_geo_combo.setModel(self.app.collection)
        self.target_geo_combo.setRootModelIndex(self.app.collection.index(2, 0, QtCore.QModelIndex()))
        # self.target_geo_combo.setCurrentIndex(1)
        self.target_geo_combo.is_last = True
        self.target_geo_combo.obj_type = "Geometry"

        self.target_geo_label = QtWidgets.QLabel('%s:' % _("Target"))
        self.target_geo_label.setToolTip(
            _("Geometry object from which to subtract\n"
              "the subtractor Geometry object.")
        )

        grid0.addWidget(self.target_geo_label, 18, 0)
        grid0.addWidget(self.target_geo_combo, 18, 1)

        # Substractor Geometry Object
        self.sub_geo_combo = FCComboBox()
        self.sub_geo_combo.setModel(self.app.collection)
        self.sub_geo_combo.setRootModelIndex(self.app.collection.index(2, 0, QtCore.QModelIndex()))
        self.sub_geo_combo.is_last = True
        self.sub_geo_combo.obj_type = "Geometry"

        self.sub_geo_label = QtWidgets.QLabel('%s:' % _("Subtractor"))
        self.sub_geo_label.setToolTip(
            _("Geometry object that will be subtracted\n"
              "from the target Geometry object.")
        )

        grid0.addWidget(self.sub_geo_label, 20, 0)
        grid0.addWidget(self.sub_geo_combo, 20, 1)

        self.close_paths_cb = FCCheckBox(_("Close paths"))
        self.close_paths_cb.setToolTip(_("Checking this will close the paths cut by the subtractor object."))

        grid0.addWidget(self.close_paths_cb, 22, 0, 1, 2)

        self.intersect_geo_btn = FCButton(_('Subtract Geometry'))
        self.intersect_geo_btn.setIcon(QtGui.QIcon(self.app.resource_location + '/subtract_btn32.png'))
        self.intersect_geo_btn.setToolTip(
            _("Will remove the area occupied by the subtractor\n"
              "Geometry from the Target Geometry.")
        )
        self.intersect_geo_btn.setStyleSheet("""
                                QPushButton
                                {
                                    font-weight: bold;
                                }
                                """)

        grid0.addWidget(self.intersect_geo_btn, 24, 0, 1, 2)
        grid0.addWidget(QtWidgets.QLabel(''), 26, 0, 1, 2)

        self.tools_box.addStretch()

        # ## Reset Tool
        self.reset_button = QtWidgets.QPushButton(_("Reset Tool"))
        self.reset_button.setIcon(QtGui.QIcon(self.app.resource_location + '/reset32.png'))
        self.reset_button.setToolTip(
            _("Will reset the tool parameters.")
        )
        self.reset_button.setStyleSheet("""
                                QPushButton
                                {
                                    font-weight: bold;
                                }
                                """)
        self.tools_box.addWidget(self.reset_button)

        # #################################### FINSIHED GUI ###########################
        # #############################################################################

    def confirmation_message(self, accepted, minval, maxval):
        if accepted is False:
            self.app.inform[str, bool].emit('[WARNING_NOTCL] %s: [%.*f, %.*f]' % (_("Edited value is out of range"),
                                                                                  self.decimals,
                                                                                  minval,
                                                                                  self.decimals,
                                                                                  maxval), False)
        else:
            self.app.inform[str, bool].emit('[success] %s' % _("Edited value is within limits."), False)

    def confirmation_message_int(self, accepted, minval, maxval):
        if accepted is False:
            self.app.inform[str, bool].emit('[WARNING_NOTCL] %s: [%d, %d]' %
                                            (_("Edited value is out of range"), minval, maxval), False)
        else:
            self.app.inform[str, bool].emit('[success] %s' % _("Edited value is within limits."), False)
