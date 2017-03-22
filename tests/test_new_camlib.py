import difflib
import sys
import unittest
from pprint import pprint

from PyQt4 import QtGui
from FlatCAMApp import App, tclCommands
from FlatCAMObj import FlatCAMGerber, FlatCAMGeometry, FlatCAMCNCjob
from ObjectUI import GerberObjectUI, GeometryObjectUI
from time import sleep
import os
import tempfile


class NewCamLibTestCase(unittest.TestCase):
    """
    This is a test covering the output of the camlib v2 system

    THIS IS A REQUIRED TEST FOR ANY UPDATES.

    """


    def setUp(self):
        self.app = QtGui.QApplication(sys.argv)

        # Create App, keep app defaults (do not load
        # user-defined defaults).
        self.fc = App(user_defaults=False)

    def tearDown(self):
        del self.fc
        del self.app

    def test_gerber_equal_output(self):
        self.fc.open_gerber('tests/gerber_files/simple1.gbr')
        # Opens a gerber file, outputs gcode, then check the output
        names = self.fc.collection.get_names()

        gerber_name = names[0]
        gerber_obj = self.fc.collection.get_by_name(gerber_name)
        gerber_obj.build_ui()

        form_field = gerber_obj.form_fields['isotooldia']
        value = form_field.get_value()
        form_field.set_value(value * 1.1)  # Increase by 10%

        ui = gerber_obj.ui
        ui.generate_iso_button.click()  # Click

        geo_name = gerber_name + "_iso"
        geo_obj = self.fc.collection.get_by_name(geo_name)
        geo_obj.build_ui()
        ui = geo_obj.ui
        ui.generate_cnc_button.click()  # Click

        # Work is done in a separate thread and results are
        # passed via events to the main event loop which is
        # not running. Run only for pending events.
        #
        # I'm not sure why, but running it only once does
        # not catch the new object. Might be a timing issue.
        # http://pyqt.sourceforge.net/Docs/PyQt4/qeventloop.html#details
        for _ in range(2):
            sleep(0.1)
            self.app.processEvents()

        cnc_name = geo_name + "_cnc"
        cnc_obj = self.fc.collection.get_by_name(cnc_name)

        #-----------------------------------------
        # Export G-Code, check output
        #-----------------------------------------
        output_filename = ""
        # get system temporary file(try create it and  delete also)
        with tempfile.NamedTemporaryFile(prefix='unittest.',
                                         suffix="." + cnc_name + '.gcode',
                                         delete=True) as tmp_file:
            output_filename = tmp_file.name
        cnc_obj.export_gcode(output_filename)
        self.assertTrue(os.path.isfile(output_filename))

        with open(output_filename, 'r') as output_file:
            output_data = output_file.readlines()
        os.remove(output_filename)

        with open('tests/gerber_files/' + cnc_name + '.gcode', 'r') as expected_file:
            expected_data = expected_file.readlines()

        differ=difflib.Differ()
        pprint(list(differ.compare(expected_data,output_data)))
        self.assertEqual(expected_data,output_data)

    def test_excellon_equal_output(self):
        self.fc.open_excellon('tests/excellon_files/case1.drl')
        # Names of available objects.
        names = self.fc.collection.get_names()
        excellon_name = names[0]
        excellon_obj = self.fc.collection.get_by_name(excellon_name)
        excellon_obj.build_ui()
        form_field = excellon_obj.form_fields['feedrate']
        value = form_field.get_value()
        form_field.set_value(value * 1.1)  # Increase by 10%

        ui = excellon_obj.ui
        ui.tools_table.selectAll()  # Select All
        ui.generate_cnc_button.click()  # Click

        # Work is done in a separate thread and results are
        # passed via events to the main event loop which is
        # not running. Run only for pending events.
        #
        # I'm not sure why, but running it only once does
        # not catch the new object. Might be a timing issue.
        # http://pyqt.sourceforge.net/Docs/PyQt4/qeventloop.html#details
        for _ in range(2):
            sleep(0.1)
            self.app.processEvents()

        value = excellon_obj.options['feedrate']
        form_value = form_field.get_value()
        names = self.fc.collection.get_names()
        cncjob_name = excellon_name + "_cnc"
        cncjob_obj = self.fc.collection.get_by_name(cncjob_name)

        #-----------------------------------------
        # Export G-Code, check output
        #-----------------------------------------
        # get system temporary file(try create it and delete)
        with tempfile.NamedTemporaryFile(prefix='unittest.',
                                         suffix="." + cncjob_name + '.gcode',
                                         delete=True) as tmp_file:
            output_filename = tmp_file.name

        cncjob_obj.export_gcode(output_filename)
        self.assertTrue(os.path.isfile(output_filename))

        with open(output_filename, 'r') as output_file:
            output_data = output_file.readlines()
        os.remove(output_filename)

        with open('tests/excellon_files/' + cncjob_name + '.gcode', 'r') as expected_file:
            expected_data = expected_file.readlines()

        differ=difflib.Differ()
        pprint(list(differ.compare(expected_data,output_data)))
        self.assertEqual(expected_data,output_data)

