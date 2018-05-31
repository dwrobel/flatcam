import sys
import unittest
from PyQt4 import QtGui
from FlatCAMApp import App
from FlatCAMObj import FlatCAMGeometry, FlatCAMCNCjob
from ObjectUI import GerberObjectUI, GeometryObjectUI
from time import sleep
import os
import tempfile
from shapely.geometry import LineString, LinearRing, Polygon, MultiPolygon


class PolyPaintTestCase(unittest.TestCase):

    def setUp(self):
        self.app = QtGui.QApplication(sys.argv)

        # Create App, keep app defaults (do not load
        # user-defined defaults).
        self.fc = App(user_defaults=False)

    def tearDown(self):

        for _ in range(2):
            self.app.processEvents()

        # NOTE: These are creating problems...
        # del self.fc
        # del self.app

    def test_poly_paint_svg_all(self):

        print("*********************************")
        print("*         svg_all               *")
        print("*********************************")

        # Clear workspace
        self.fc.on_file_new()
        for _ in range(2):
            self.app.processEvents()

        # Open SVG with polygons
        self.fc.import_svg('tests/svg/drawing.svg')

        name = self.fc.collection.get_names()[0]

        self.fc.collection.set_active(name)

        geo_obj = self.fc.collection.get_by_name(name)

        # Paint all polygons
        geo_obj.paint_poly_all(5, 0.2, 1)
        sleep(5)  # Todo: Do not base it on fixed time.
        for _ in range(2):
            self.app.processEvents()

        # New object should be available
        names = self.fc.collection.get_names()

        self.assertEqual(len(names), 2)

        # Verify new geometry makes sense
        painted = self.fc.collection.get_by_name(names[-1])
        for geo in painted.solid_geometry:
            # Correct Type
            self.assertTrue(isinstance(geo, LineString))
            # Lots of points (Should be 1000s)
            self.assertGreater(len(geo.coords), 2)

    def test_poly_paint_svg_click(self):

        print("*********************************")
        print("*         svg_click             *")
        print("*********************************")

        # Clear workspace
        self.fc.on_file_new()
        for _ in range(2):
            self.app.processEvents()

        # Open SVG with polygons
        self.fc.import_svg('tests/svg/drawing.svg')

        name = self.fc.collection.get_names()[0]

        self.fc.collection.set_active(name)

        geo_obj = self.fc.collection.get_by_name(name)

        # Paint all polygons
        geo_obj.paint_poly_single_click([300, 700], 5, 0.2, 1)
        sleep(5)
        for _ in range(2):
            self.app.processEvents()

        # New object should be available
        names = self.fc.collection.get_names()

        sleep(1)
        self.assertEqual(len(names), 2)

        # Verify new geometry makes sense
        painted = self.fc.collection.get_by_name(names[-1])
        for geo in painted.solid_geometry:
            # Correct Type
            self.assertTrue(isinstance(geo, LineString))
            # Lots of points (Should be 1000s)
            self.assertGreater(len(geo.coords), 2)

    def test_poly_paint_noncopper_all(self):

        print("*********************************")
        print("*         noncopper_all         *")
        print("*********************************")

        # Clear workspace
        self.fc.on_file_new()
        for _ in range(2):
            self.app.processEvents()

        self.fc.open_gerber('tests/gerber_files/simple1.gbr')
        sleep(1)
        for _ in range(2):
            self.app.processEvents()

        name = self.fc.collection.get_names()[0]

        gerber_obj = self.fc.collection.get_by_name(name)

        self.fc.collection.set_active(name)

        gerber_obj.on_generatenoncopper_button_click()
        sleep(1)
        for _ in range(2):
            self.app.processEvents()

        # New object should be available
        names = self.fc.collection.get_names()

        sleep(1)
        self.assertEqual(len(names), 2)

        geoname = "simple1.gbr_noncopper"
        geo_obj = self.fc.collection.get_by_name(geoname)
        self.fc.collection.set_active(geoname)

        geo_obj.paint_poly_all(0.02, 0.2, 0)
        sleep(5)
        for _ in range(2):
            self.app.processEvents()

        # New object should be available
        names = self.fc.collection.get_names()

        sleep(1)
        self.assertEqual(len(names), 3)

        # Verify new geometry makes sense
        painted = self.fc.collection.get_by_name(names[-1])
        for geo in painted.solid_geometry:
            # Correct Type
            self.assertTrue(isinstance(geo, LineString))
            # Lots of points (Should be 1000s)
            self.assertGreater(len(geo.coords), 2)

    def test_poly_paint_noncopper_click(self):

        print("*********************************")
        print("*         noncopper_click       *")
        print("*********************************")

        # Clear workspace
        self.fc.on_file_new()
        for _ in range(2):
            self.app.processEvents()

        self.fc.open_gerber('tests/gerber_files/simple1.gbr')
        sleep(1)
        for _ in range(2):
            self.app.processEvents()

        name = self.fc.collection.get_names()[0]

        gerber_obj = self.fc.collection.get_by_name(name)

        self.fc.collection.set_active(name)

        gerber_obj.on_generatenoncopper_button_click()
        sleep(1)
        for _ in range(2):
            self.app.processEvents()

        # New object should be available
        names = self.fc.collection.get_names()

        sleep(1)
        self.assertEqual(len(names), 2)

        geoname = "simple1.gbr_noncopper"
        geo_obj = self.fc.collection.get_by_name(geoname)
        self.fc.collection.set_active(geoname)

        geo_obj.paint_poly_single_click([2.7, 1.0], 0.02, 0.2, 0)
        sleep(5)
        for _ in range(2):
            self.app.processEvents()

        # New object should be available
        names = self.fc.collection.get_names()

        sleep(1)
        self.assertEqual(len(names), 3)

        # Verify new geometry makes sense
        painted = self.fc.collection.get_by_name(names[-1])
        for geo in painted.solid_geometry:
            # Correct Type
            self.assertTrue(isinstance(geo, LineString))
            # Lots of points (Should be 1000s)
            self.assertGreater(len(geo.coords), 2)







