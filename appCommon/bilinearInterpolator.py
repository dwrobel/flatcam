# import csv
import math
import numpy as np


class bilinearInterpolator:
    """
    This class takes a collection of 3-dimensional points from a .csv file.  
    It contains a bilinear interpolator to find unknown points within the grid.
    """
    @property
    def probedGrid(self):
        return self._probedGrid

    """
    Constructor takes a file with a .csv extension and creates an evenly-spaced 'ideal' grid from the data points.
    This is done to get around any floating point errors that may exist in the data
    """
    def __init__(self, pointsFile):
        
        self.pointsFile = pointsFile
        self.points = np.loadtxt(self.pointsFile, delimiter=',')

        self.xMin, self.xMax, self.xSpacing, self.xCount = self._axisParams(0)
        self.yMin, self.yMax, self.ySpacing, self.yCount = self._axisParams(1)

        # generate ideal grid to match actually probed points -- this is due to floating-point error issues
        idealGrid = ([
            [(x, y) for x in np.linspace(self.xMin, self.xMax, self.xCount, True)]
            for y in np.linspace(self.yMin, self.yMax, self.yCount, True)
            ])

        self._probedGrid = [[0] * self.yCount for i in range(0, self.xCount)]

        # align ideal grid indices with probed data points
        for rowIndex, row in enumerate(idealGrid):
            for colIndex, idealPoint in enumerate(row):
                minSqDist = math.inf
                for probed in self.points:
                    # find closest point in ideal grid that corresponds to actual tested point
                    # put z value in correct index
                    sqDist = pow(probed[0] - idealPoint[0], 2) + pow(probed[1] - idealPoint[1], 2)
                    if sqDist <= minSqDist:
                        minSqDist = sqDist
                        indexX = rowIndex
                        indexY = colIndex
                        closestProbed = probed
                self.probedGrid[indexY][indexX] = closestProbed

    def Interpolate(self, point):
        """
        Bilinear interpolation method to determine unknown z-values within grid of known z-values.

        NOTE: If one axis is outside the grid, linear interpolation is used instead.
        If both axes are outside of the grid, the z-value of the closest corner of the grid is returned.
        """
        lin = False

        if point[0] < self.xMin:
            ix1 = 0
            lin = True
        elif point[0] > self.xMax:
            ix1 = self.xCount-1
            lin = True
        else:
            ix1 = math.floor((point[0] - self.xMin)/self.xSpacing)
            ix2 = math.ceil((point[0] - self.xMin)/self.xSpacing)

        def interpolatePoint(p1, p2, pt, axis):
            return (p2[2]*(pt[axis] - p1[axis]) + p1[2]*(p2[axis] - pt[axis]))/(p2[axis] - p1[axis])

        if point[1] < self.yMin:
            if lin:
                return self.probedGrid[ix1][0][2]
            return interpolatePoint(self.probedGrid[ix1][0], self.probedGrid[ix2][0], point, 0)
        elif point[1] > self.yMax:           
            if lin:
                return self.probedGrid[ix1][self.yCount - 1][2]
            return interpolatePoint(
                self.probedGrid[ix1][self.yCount - 1], self.probedGrid[ix2][self.yCount - 1], point, 0)
        else:
            iy1 = math.floor((point[1] - self.yMin)/self.ySpacing)
            iy2 = math.ceil((point[1] - self.yMin)/self.ySpacing)
            # if x was at an extrema, but y was not, perform linear interpolation on x axis
            if lin:
                return interpolatePoint(self.probedGrid[ix1][iy1], self.probedGrid[ix1][iy2], point, 1)

        def specialDiv(a, b):
            if b == 0:
                return 0.5
            else:
                return a/b      

        x1 = self.probedGrid[ix1][iy1][0]
        x2 = self.probedGrid[ix2][iy1][0]
        y1 = self.probedGrid[ix2][iy1][1]
        y2 = self.probedGrid[ix2][iy2][1]

        Q11 = self.probedGrid[ix1][iy1][2]
        Q12 = self.probedGrid[ix1][iy2][2]
        Q21 = self.probedGrid[ix2][iy1][2]
        Q22 = self.probedGrid[ix2][iy2][2]

        r1 = specialDiv(point[0]-x1, x2-x1)*Q21 + specialDiv(x2-point[0], x2-x1)*Q11
        r2 = specialDiv(point[0]-x1, x2-x1)*Q22 + specialDiv(x2-point[0], x2-x1)*Q12
        p = specialDiv(point[1]-y1, y2-y1)*r2 + specialDiv(y2-point[1], y2-y1)*r1
            
        return p

    # Returns the min, max, spacing and size of one axis of the 2D grid
    def _axisParams(self, sortAxis):
        # sort the set and eliminate the previous, unsorted set
        srtSet = sorted(self.points, key=lambda x: x[sortAxis])

        dists = []
        for item0, item1 in zip(srtSet[:(len(srtSet)-2)], srtSet[1:]):
            dists.append(float(item1[sortAxis]) - float(item0[sortAxis]))
        axisSpacing = max(dists)

        # add an extra one for axisCount to account for the starting point
        axisMin = float(min(srtSet, key=lambda x: x[sortAxis])[sortAxis])
        axisMax = float(max(srtSet, key=lambda x: x[sortAxis])[sortAxis])
        axisRange = axisMax - axisMin
        axisCount = round((axisRange/axisSpacing) + 1)

        return axisMin, axisMax, axisSpacing, axisCount
