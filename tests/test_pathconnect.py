import unittest

from shapely.geometry import LineString, Polygon
from shapely.ops import cascaded_union, unary_union
from matplotlib.pyplot import plot, subplot, show, cla, clf, xlim, ylim, title
from camlib import *
from random import random


def mkstorage(paths):
    """
    Returns a FlatCAMRTreeStorage with the provided
    paths indexed by their first and last points.

    :param paths:
    :return:
    """
    def get_pts(o):
        return [o.coords[0], o.coords[-1]]
    storage = FlatCAMRTreeStorage()
    storage.get_points = get_pts
    for p in paths:
        storage.insert(p)
    return storage


class PathConnectTest1(unittest.TestCase):

    def setUp(self):
        print "PathConnectTest1.setUp()"
        pass

    def test_simple_connect(self):
        """
        Two paths that touch each other on their
        endpoints are merged into a single one.

        :return: None
        """
        paths = [
            LineString([[0, 0], [1, 1]]),
            LineString([[1, 1], [2, 1]])
        ]

        result = Geometry.path_connect(mkstorage(paths))
        assert isinstance(result, FlatCAMRTreeStorage)

        result = list(result.get_objects())

        # The paths touch, so they should have been joined
        # into a single one.
        self.assertEqual(len(result), 1)

        # Exact expected path.
        self.assertTrue(result[0].equals(LineString([[0, 0], [1, 1], [2, 1]])))

    def test_interfere_connect(self):
        """
        A third path does not touch the other two.

        :return: None
        """
        paths = [
            LineString([[0, 0], [1, 1]]),
            LineString([[1, 1], [2, 1]]),
            LineString([[-0.5, 0.5], [0.5, 0]])
        ]

        result = Geometry.path_connect(mkstorage(paths))
        assert isinstance(result, FlatCAMRTreeStorage)

        result = list(result.get_objects())

        # Two separate paths.
        self.assertEqual(len(result), 2)

        # Exact shape
        matches = [p for p in result if p.equals(LineString([[0, 0], [1, 1], [2, 1]]))]
        self.assertEqual(len(matches), 1)

    def test_simple_connect_offset1(self):
        """
        Same as test_simple_connect, but with random points.

        :return: None
        """

        for i in range(20):
            offset_x = random()
            offset_y = random()

            paths = [
                LineString([[0 + offset_x, 0 + offset_y], [1 + offset_x, 1 + offset_y]]),
                LineString([[1 + offset_x, 1 + offset_y], [2 + offset_x, 1 + offset_y]])
            ]

            result = Geometry.path_connect(mkstorage(paths))
            assert isinstance(result, FlatCAMRTreeStorage)

            result = list(result.get_objects())

            # Paths touch, only one comes out.
            self.assertEqual(len(result), 1)
            self.assertTrue(result[0].equals(LineString([[0 + offset_x, 0 + offset_y],
                                                         [1 + offset_x, 1 + offset_y],
                                                         [2 + offset_x, 1 + offset_y]])))

    def test_ring_interfere_connect(self):
        print
        print "TEST STARTING ..."

        paths = [
            LineString([[0, 0], [1, 1]]),
            LineString([[1, 1], [2, 1]]),
            LinearRing([[1, 1], [2, 2], [1, 3], [0, 2]])
        ]

        result = Geometry.path_connect(mkstorage(paths))
        assert isinstance(result, FlatCAMRTreeStorage)

        result = list(result.get_objects())
        self.assertEqual(len(result), 2)
        matches = [p for p in result if p.equals(LineString([[0, 0], [1, 1], [2, 1]]))]
        self.assertEqual(len(matches), 1)

if __name__ == "__main__":
    unittest.main()