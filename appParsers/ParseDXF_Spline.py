# Author: vvlachoudis@gmail.com
# Vasilis Vlachoudis
# Date: 20-Oct-2015

# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File modified: Marius Adrian Stanciu                     #
# Date: 3/10/2019                                          #
# ##########################################################

import math


def norm(v):
    return math.sqrt(v[0]*v[0] + v[1]*v[1] + v[2]*v[2])


def normalize_2(v):
    m = norm(v)
    return [v[0]/m, v[1]/m, v[2]/m]


# ------------------------------------------------------------------------------
# Convert a B-spline to polyline with a fixed number of segments
# ------------------------------------------------------------------------------
def spline2Polyline(xyz, degree, closed, segments, knots):
    """
    :param xyz:         DXF spline control points
    :param degree:      degree of the Spline curve
    :param closed:      closed Spline
    :type closed:       bool
    :param segments:    how many lines to use for Spline approximation
    :param knots:       DXF spline knots
    :return:            x,y,z coordinates (each is a list)
    """

    # Check if last point coincide with the first one
    if (Vector(xyz[0]) - Vector(xyz[-1])).length2() < 1e-10:
        # it is already closed, treat it as open
        closed = False
        # FIXME we should verify if it is periodic,.... but...
        #       I am not sure :)

    if closed:
        xyz.extend(xyz[:degree])
        knots = None
    else:
        # make base-1
        # knots.insert(0, 0)
        pass

    npts = len(xyz)

    if degree < 1 or degree > 3:
        # print "invalid degree"
        return None, None, None

    # order:
    k = degree+1

    if npts < k:
        # print "not enough control points"
        return None, None, None

    # resolution:
    nseg = segments * npts

    # WARNING: base 1
    b = [0.0]*(npts*3+1)        # polygon points
    h = [1.0]*(npts+1)        # set all homogeneous weighting factors to 1.0
    p = [0.0]*(nseg*3+1)        # returned curved points

    i = 1
    for pt in xyz:
        b[i] = pt[0]
        b[i+1] = pt[1]
        b[i+2] = pt[2]
        i += 3

    # if periodic:
    if closed:
        _rbsplinu(npts, k, nseg, b, h, p, knots)
    else:
        _rbspline(npts, k, nseg, b, h, p, knots)

    x = []
    y = []
    z = []
    for i in range(1, 3*nseg+1, 3):
        x.append(p[i])
        y.append(p[i+1])
        z.append(p[i+2])

#    for i,xyz in enumerate(zip(x,y,z)):
#        print i,xyz

    return x, y, z


# ------------------------------------------------------------------------------
# Subroutine to generate a B-spline open knot vector with multiplicity
# equal to the order at the ends.
#    c            = order of the basis function
#    n            = the number of defining polygon vertices
#    n+2          = index of x[] for the first occurence of the maximum knot vector value
#    n+order      = maximum value of the knot vector -- $n + c$
#    x[]          = array containing the knot vector
# ------------------------------------------------------------------------------
def _knot(n, order):
    x = [0.0]*(n+order+1)
    for i in range(2, n+order+1):
        if order < i < n+2:
            x[i] = x[i-1] + 1.0
        else:
            x[i] = x[i-1]
    return x


# ------------------------------------------------------------------------------
# Subroutine to generate a B-spline uniform (periodic) knot vector.
#
# order        = order of the basis function
# n            = the number of defining polygon vertices
# n+order      = maximum value of the knot vector -- $n + order$
# x[]          = array containing the knot vector
# ------------------------------------------------------------------------------
def _knotu(n, order):
    x = [0]*(n+order+1)
    for i in range(2, n+order+1):
        x[i] = float(i-1)
    return x


# ------------------------------------------------------------------------------
# Subroutine to generate rational B-spline basis functions--open knot vector

# C code for An Introduction to NURBS
# by David F. Rogers. Copyright (C) 2000 David F. Rogers,
# All rights reserved.

# Name: rbasis
# Subroutines called: none
# Book reference: Chapter 4, Sec. 4. , p 296

#   c        = order of the B-spline basis function
#   d        = first term of the basis function recursion relation
#   e        = second term of the basis function recursion relation
#   h[]      = array containing the homogeneous weights
#   npts     = number of defining polygon vertices
#   nplusc   = constant -- npts + c -- maximum number of knot values
#   r[]      = array containing the rational basis functions
#              r[1] contains the basis function associated with B1 etc.
#   t        = parameter value
#   temp[]   = temporary array
#   x[]      = knot vector
# ------------------------------------------------------------------------------
def _rbasis(c, t, npts, x, h, r):
    nplusc = npts + c
    temp = [0.0]*(nplusc+1)

    # calculate the first order non-rational basis functions n[i]
    for i in range(1, nplusc):
        if x[i] <= t < x[i+1]:
            temp[i] = 1.0
        else:
            temp[i] = 0.0

    # calculate the higher order non-rational basis functions
    for k in range(2, c+1):
        for i in range(1, nplusc-k+1):
            # if the lower order basis function is zero skip the calculation
            if temp[i] != 0.0:
                d = ((t-x[i])*temp[i])/(x[i+k-1]-x[i])
            else:
                d = 0.0

            # if the lower order basis function is zero skip the calculation
            if temp[i+1] != 0.0:
                e = ((x[i+k]-t)*temp[i+1])/(x[i+k]-x[i+1])
            else:
                e = 0.0
            temp[i] = d + e

    # pick up last point
    if t >= x[nplusc]:
        temp[npts] = 1.0

    # calculate sum for denominator of rational basis functions
    s = 0.0
    for i in range(1, npts+1):
        s += temp[i]*h[i]

    # form rational basis functions and put in r vector
    for i in range(1, npts+1):
        if s != 0.0:
            r[i] = (temp[i]*h[i])/s
        else:
            r[i] = 0


# ------------------------------------------------------------------------------
# Generates a rational B-spline curve using a uniform open knot vector.
#
# C code for An Introduction to NURBS
# by David F. Rogers. Copyright (C) 2000 David F. Rogers,
# All rights reserved.
#
# Name: rbspline.c
# Subroutines called: _knot, rbasis
# Book reference: Chapter 4, Alg. p. 297
#
#    b           = array containing the defining polygon vertices
#                  b[1] contains the x-component of the vertex
#                  b[2] contains the y-component of the vertex
#                  b[3] contains the z-component of the vertex
#    h           = array containing the homogeneous weighting factors
#    k           = order of the B-spline basis function
#    nbasis      = array containing the basis functions for a single value of t
#    nplusc      = number of knot values
#    npts        = number of defining polygon vertices
#    p[,]        = array containing the curve points
#                  p[1] contains the x-component of the point
#                  p[2] contains the y-component of the point
#                  p[3] contains the z-component of the point
#    p1          = number of points to be calculated on the curve
#    t           = parameter value 0 <= t <= npts - k + 1
#    x[]         = array containing the knot vector
# ------------------------------------------------------------------------------
def _rbspline(npts, k, p1, b, h, p, x):
    nplusc = npts + k
    nbasis = [0.0]*(npts+1)        # zero and re-dimension the basis array

    # generate the uniform open knot vector
    if x is None or len(x) != nplusc+1:
        x = _knot(npts, k)
    icount = 0
    # calculate the points on the rational B-spline curve
    t = 0
    step = float(x[nplusc])/float(p1-1)
    for i1 in range(1, p1+1):
        if x[nplusc] - t < 5e-6:
            t = x[nplusc]
        # generate the basis function for this value of t
        nbasis = [0.0]*(npts+1)    # zero and re-dimension the knot vector and the basis array
        _rbasis(k, t, npts, x, h, nbasis)
        # generate a point on the curve
        for j in range(1, 4):
            jcount = j
            p[icount+j] = 0.0
            # Do local matrix multiplication
            for i in range(1, npts+1):
                p[icount+j] += nbasis[i]*b[jcount]
                jcount += 3
        icount += 3
        t += step


# ------------------------------------------------------------------------------
# Subroutine to generate a rational B-spline curve using an uniform periodic knot vector
#
# C code for An Introduction to NURBS
# by David F. Rogers. Copyright (C) 2000 David F. Rogers,
# All rights reserved.
#
# Name: rbsplinu.c
# Subroutines called: _knotu, _rbasis
# Book reference: Chapter 4, Alg. p. 298
#
#   b[]         = array containing the defining polygon vertices
#                 b[1] contains the x-component of the vertex
#                 b[2] contains the y-component of the vertex
#                 b[3] contains the z-component of the vertex
#   h[]         = array containing the homogeneous weighting factors
#   k           = order of the B-spline basis function
#   nbasis      = array containing the basis functions for a single value of t
#   nplusc      = number of knot values
#   npts        = number of defining polygon vertices
#   p[,]        = array containing the curve points
#                 p[1] contains the x-component of the point
#                 p[2] contains the y-component of the point
#                 p[3] contains the z-component of the point
#   p1          = number of points to be calculated on the curve
#   t           = parameter value 0 <= t <= npts - k + 1
#   x[]         = array containing the knot vector
# ------------------------------------------------------------------------------
def _rbsplinu(npts, k, p1, b, h, p, x=None):
    nplusc = npts + k
    nbasis = [0.0]*(npts+1)        # zero and re-dimension the basis array
    # generate the uniform periodic knot vector
    if x is None or len(x) != nplusc+1:
        # zero and re dimension the knot vector and the basis array
        x = _knotu(npts, k)
    icount = 0
    # calculate the points on the rational B-spline curve
    t = k-1
    step = (float(npts)-(k-1))/float(p1-1)
    for i1 in range(1, p1+1):
        if x[nplusc] - t < 5e-6:
            t = x[nplusc]
        # generate the basis function for this value of t
        nbasis = [0.0]*(npts+1)
        _rbasis(k, t, npts, x, h, nbasis)
        # generate a point on the curve
        for j in range(1, 4):
            jcount = j
            p[icount+j] = 0.0
            #  Do local matrix multiplication
            for i in range(1, npts+1):
                p[icount+j] += nbasis[i]*b[jcount]
                jcount += 3
        icount += 3
        t += step


# Accuracy for comparison operators
_accuracy = 1E-15


def Cmp0(x):
    """Compare against zero within _accuracy"""
    return abs(x) < _accuracy


def gauss(A, B):
    """Solve A*X = B using the Gauss elimination method"""

    n = len(A)
    s = [0.0] * n
    X = [0.0] * n

    p = [i for i in range(n)]
    for i in range(n):
        s[i] = max([abs(x) for x in A[i]])

    for k in range(n - 1):
        # select j>=k so that
        # |A[p[j]][k]| / s[p[i]] >= |A[p[i]][k]| / s[p[i]] for i = k,k+1,...,n
        j = k
        ap = abs(A[p[j]][k]) / s[p[j]]
        for i in range(k + 1, n):
            api = abs(A[p[i]][k]) / s[p[i]]
            if api > ap:
                j = i
                ap = api

        if j != k:
            p[k], p[j] = p[j], p[k]  # Swap values

        for i in range(k + 1, n):
            z = A[p[i]][k] / A[p[k]][k]
            A[p[i]][k] = z
            for j in range(k + 1, n):
                A[p[i]][j] -= z * A[p[k]][j]

    for k in range(n - 1):
        for i in range(k + 1, n):
            B[p[i]] -= A[p[i]][k] * B[p[k]]

    for i in range(n - 1, -1, -1):
        X[i] = B[p[i]]
        for j in range(i + 1, n):
            X[i] -= A[p[i]][j] * X[j]
        X[i] /= A[p[i]][i]

    return X


# Vector class
# Inherits from List
class Vector(list):
    """Vector class"""

    def __init__(self, x=3, *args):
        """Create a new vector,
        Vector(size), Vector(list), Vector(x,y,z,...)"""
        list.__init__(self)

        if isinstance(x, int) and not args:
            for i in range(x):
                self.append(0.0)
        elif isinstance(x, (list, tuple)):
            for i in x:
                self.append(float(i))
        else:
            self.append(float(x))
            for i in args:
                self.append(float(i))

    # ----------------------------------------------------------------------
    def set(self, x, y, z=None):
        """Set vector"""
        self[0] = x
        self[1] = y
        if z:
            self[2] = z

    # ----------------------------------------------------------------------
    def __repr__(self):
        return "[%s]" % ", ".join([repr(x) for x in self])

    # ----------------------------------------------------------------------
    def __str__(self):
        return "[%s]" % ", ".join([("%15g" % x).strip() for x in self])

    # ----------------------------------------------------------------------
    def eq(self, v, acc=_accuracy):
        """Test for equality with vector v within accuracy"""
        if len(self) != len(v):
            return False
        s2 = 0.0
        for a, b in zip(self, v):
            s2 += (a - b) ** 2
        return s2 <= acc ** 2

    def __eq__(self, v):
        return self.eq(v)

    # ----------------------------------------------------------------------
    def __neg__(self):
        """Negate vector"""
        new = Vector(len(self))
        for i, s in enumerate(self):
            new[i] = -s
        return new

    # ----------------------------------------------------------------------
    def __add__(self, v):
        """Add 2 vectors"""
        size = min(len(self), len(v))
        new = Vector(size)
        for i in range(size):
            new[i] = self[i] + v[i]
        return new

    # ----------------------------------------------------------------------
    def __iadd__(self, v):
        """Add vector v to self"""
        for i in range(min(len(self), len(v))):
            self[i] += v[i]
        return self

    # ----------------------------------------------------------------------
    def __sub__(self, v):
        """Subtract 2 vectors"""
        size = min(len(self), len(v))
        new = Vector(size)
        for i in range(size):
            new[i] = self[i] - v[i]
        return new

    # ----------------------------------------------------------------------
    def __isub__(self, v):
        """Subtract vector v from self"""
        for i in range(min(len(self), len(v))):
            self[i] -= v[i]
        return self

    # ----------------------------------------------------------------------
    # Scale or Dot product
    # ----------------------------------------------------------------------
    def __mul__(self, v):
        """scale*Vector() or Vector()*Vector() - Scale vector or dot product"""
        if isinstance(v, list):
            return self.dot(v)
        else:
            return Vector([x * v for x in self])

    # ----------------------------------------------------------------------
    # Scale or Dot product
    # ----------------------------------------------------------------------
    def __rmul__(self, v):
        """scale*Vector() or Vector()*Vector() - Scale vector or dot product"""
        if isinstance(v, Vector):
            return self.dot(v)
        else:
            return Vector([x * v for x in self])

    # ----------------------------------------------------------------------
    # Divide by floating point
    # ----------------------------------------------------------------------
    def __div__(self, b):
        return Vector([x / b for x in self])

    # ----------------------------------------------------------------------
    def __xor__(self, v):
        """Cross product"""
        return self.cross(v)

    # ----------------------------------------------------------------------
    def dot(self, v):
        """Dot product of 2 vectors"""
        s = 0.0
        for a, b in zip(self, v):
            s += a * b
        return s

    # ----------------------------------------------------------------------
    def cross(self, v):
        """Cross product of 2 vectors"""
        if len(self) == 3:
            return Vector(self[1] * v[2] - self[2] * v[1],
                          self[2] * v[0] - self[0] * v[2],
                          self[0] * v[1] - self[1] * v[0])
        elif len(self) == 2:
            return self[0] * v[1] - self[1] * v[0]
        else:
            raise Exception("Cross product needs 2d or 3d vectors")

    # ----------------------------------------------------------------------
    def length2(self):
        """Return length squared of vector"""
        s2 = 0.0
        for s in self:
            s2 += s ** 2
        return s2

    # ----------------------------------------------------------------------
    def length(self):
        """Return length of vector"""
        s2 = 0.0
        for s in self:
            s2 += s ** 2
        return math.sqrt(s2)

    __abs__ = length

    # ----------------------------------------------------------------------
    def arg(self):
        """return vector angle"""
        return math.atan2(self[1], self[0])

    # ----------------------------------------------------------------------
    def norm(self):
        """Normalize vector and return length"""
        length = self.length()
        if length > 0.0:
            invlen = 1.0 / length
            for i in range(len(self)):
                self[i] *= invlen
        return length

    normalize = norm

    # ----------------------------------------------------------------------
    def unit(self):
        """return a unit vector"""
        v = self.clone()
        v.norm()
        return v

    # ----------------------------------------------------------------------
    def clone(self):
        """Clone vector"""
        return Vector(self)

    # ----------------------------------------------------------------------
    def x(self):
        return self[0]

    def y(self):
        return self[1]

    def z(self):
        return self[2]

    # ----------------------------------------------------------------------
    def orthogonal(self):
        """return a vector orthogonal to self"""
        xx = abs(self.x())
        yy = abs(self.y())

        if len(self) >= 3:
            zz = abs(self.z())
            if xx < yy:
                if xx < zz:
                    return Vector(0.0, self.z(), -self.y())
                else:
                    return Vector(self.y(), -self.x(), 0.0)
            else:
                if yy < zz:
                    return Vector(-self.z(), 0.0, self.x())
                else:
                    return Vector(self.y(), -self.x(), 0.0)
        else:
            return Vector(-self.y(), self.x())

    # ----------------------------------------------------------------------
    def direction(self, zero=_accuracy):
        """return containing the direction if normalized with any of the axis"""

        v = self.clone()
        length = v.norm()
        if abs(length) <= zero:
            return "O"

        if abs(v[0] - 1.0) < zero:
            return "X"
        elif abs(v[0] + 1.0) < zero:
            return "-X"
        elif abs(v[1] - 1.0) < zero:
            return "Y"
        elif abs(v[1] + 1.0) < zero:
            return "-Y"
        elif abs(v[2] - 1.0) < zero:
            return "Z"
        elif abs(v[2] + 1.0) < zero:
            return "-Z"
        else:
            # nothing special about the direction, return N
            return "N"

    # ----------------------------------------------------------------------
    # Set the vector directly in polar coordinates
    # @param ma magnitude of vector
    # @param ph azimuthal angle in radians
    # @param th polar angle in radians
    # ----------------------------------------------------------------------
    def setPolar(self, ma, ph, th):
        """Set the vector directly in polar coordinates"""
        sf = math.sin(ph)
        cf = math.cos(ph)
        st = math.sin(th)
        ct = math.cos(th)
        self[0] = ma * st * cf
        self[1] = ma * st * sf
        self[2] = ma * ct

    # ----------------------------------------------------------------------
    def phi(self):
        """return the azimuth angle."""
        if Cmp0(self.x()) and Cmp0(self.y()):
            return 0.0
        return math.atan2(self.y(), self.x())

    # ----------------------------------------------------------------------
    def theta(self):
        """return the polar angle."""
        if Cmp0(self.x()) and Cmp0(self.y()) and Cmp0(self.z()):
            return 0.0
        return math.atan2(self.perp(), self.z())

    # ----------------------------------------------------------------------
    def cosTheta(self):
        """return cosine of the polar angle."""
        ptot = self.length()
        if Cmp0(ptot):
            return 1.0
        else:
            return self.z() / ptot

    # ----------------------------------------------------------------------
    def perp2(self):
        """return the transverse component squared
        (R^2 in cylindrical coordinate system)."""
        return self.x() * self.x() + self.y() * self.y()

    # ----------------------------------------------------------------------
    def perp(self):
        """@return the transverse component
        (R in cylindrical coordinate system)."""
        return math.sqrt(self.perp2())

    # ----------------------------------------------------------------------
    # Return a random 3D vector
    # ----------------------------------------------------------------------
    # @staticmethod
    # def random():
    #     cosTheta = 2.0 * random.random() - 1.0
    #     sinTheta = math.sqrt(1.0 - cosTheta ** 2)
    #     phi = 2.0 * math.pi * random.random()
    #     return Vector(math.cos(phi) * sinTheta, math.sin(phi) * sinTheta, cosTheta)

# #===============================================================================
# # Cardinal cubic spline class
# #===============================================================================
# class CardinalSpline:
#     def __init__(self, A=0.5):
#         # The default matrix is the Catmull-Rom spline
#         # which is equal to Cardinal matrix
#         # for A = 0.5
#         #
#         # Note: Vasilis
#         #    The A parameter should be the fraction in t where
#         #    the second derivative is zero
#         self.setMatrix(A)
#
#     #-----------------------------------------------------------------------
#     # Set the matrix according to Cardinal
#     #-----------------------------------------------------------------------
#     def setMatrix(self, A=0.5):
#         self.M = []
#         self.M.append([  -A,  2.-A,    A-2.,   A ])
#         self.M.append([2.*A,  A-3., 3.-2.*A,  -A ])
#         self.M.append([  -A,    0.,       A,   0.])
#         self.M.append([  0.,    1.,       0,   0.])
#
#     #-----------------------------------------------------------------------
#     # Evaluate Cardinal spline at position t
#     # @param P      list or tuple with 4 points y positions
#     # @param t [0..1] fraction of interval from points 1..2
#     # @param k      index of starting 4 elements in P
#     # @return spline evaluation
#     #-----------------------------------------------------------------------
#     def __call__(self, P, t, k=1):
#         T = [t*t*t, t*t, t, 1.0]
#         R = [0.0]*4
#         for i in range(4):
#             for j in range(4):
#                 R[i] += T[j] * self.M[j][i]
#         y = 0.0
#         for i in range(4):
#             y += R[i]*P[k+i-1]
#
#         return y
#
#     #-----------------------------------------------------------------------
#     # Return the coefficients of a 3rd degree polynomial
#     #     f(x) = a t^3 + b t^2 + c t + d
#     # @return [a, b, c, d]
#     #-----------------------------------------------------------------------
#     def coefficients(self, P, k=1):
#         C = [0.0]*4
#         for i in range(4):
#             for j in range(4):
#                 C[i] += self.M[i][j] * P[k+j-1]
#         return C
#
#     #-----------------------------------------------------------------------
#     # Evaluate the value of the spline using the coefficients
#     #-----------------------------------------------------------------------
#     def evaluate(self, C, t):
#         return ((C[0]*t + C[1])*t + C[2])*t + C[3]
#
# #===============================================================================
# # Cubic spline ensuring that the first and second derivative are continuous
# # adapted from Penelope Manual Appending B.1
# # It requires all the points (xi,yi) and the assumption on how to deal
# # with the second derivative on the extremities
# # Option 1: assume zero as second derivative on both ends
# # Option 2: assume the same as the next or previous one
# #===============================================================================
# class CubicSpline:
#     def __init__(self, X, Y):
#         self.X = X
#         self.Y = Y
#         self.n = len(X)
#
#         # Option #1
#         s1 = 0.0    # zero based = s0
#         sN = 0.0    # zero based = sN-1
#
#         # Construct the tri-diagonal matrix
#         A = []
#         B = [0.0] * (self.n-2)
#         for i in range(self.n-2):
#             A.append([0.0] * (self.n-2))
#
#         for i in range(1,self.n-1):
#             hi = self.h(i)
#             Hi = 2.0*(self.h(i-1) + hi)
#             j = i-1
#             A[j][j] = Hi
#             if i+1<self.n-1:
#                 A[j][j+1] = A[j+1][j] = hi
#
#             if i==1:
#                 B[j] = 6.*(self.d(i) - self.d(j)) - hi*s1
#             elif i<self.n-2:
#                 B[j] = 6.*(self.d(i) - self.d(j))
#             else:
#                 B[j] = 6.*(self.d(i) - self.d(j)) - hi*sN
#
#
#         self.s = gauss(A,B)
#         self.s.insert(0,s1)
#         self.s.append(sN)
# #        print ">> s <<"
# #        pprint(self.s)
#
#     #-----------------------------------------------------------------------
#     def h(self, i):
#         return self.X[i+1] - self.X[i]
#
#     #-----------------------------------------------------------------------
#     def d(self, i):
#         return (self.Y[i+1] - self.Y[i]) / (self.X[i+1] - self.X[i])
#
#     #-----------------------------------------------------------------------
#     def coefficients(self, i):
#         """return coefficients of cubic spline for interval i a*x**3+b*x**2+c*x+d"""
#         hi  = self.h(i)
#         si  = self.s[i]
#         si1 = self.s[i+1]
#         xi  = self.X[i]
#         xi1 = self.X[i+1]
#         fi  = self.Y[i]
#         fi1 = self.Y[i+1]
#
#         a = 1./(6.*hi)*(si*xi1**3 - si1*xi**3 + 6.*(fi*xi1 - fi1*xi)) + hi/6.*(si1*xi - si*xi1)
#         b = 1./(2.*hi)*(si1*xi**2 - si*xi1**2 + 2*(fi1 - fi)) + hi/6.*(si - si1)
#         c = 1./(2.*hi)*(si*xi1 - si1*xi)
#         d = 1./(6.*hi)*(si1-si)
#
#         return [d,c,b,a]
#
#     #-----------------------------------------------------------------------
#     def __call__(self, i, x):
#         C = self.coefficients(i)
#         return ((C[0]*x + C[1])*x + C[2])*x + C[3]
#
#     #-----------------------------------------------------------------------
#     # @return evaluation of cubic spline at x using coefficients C
#     #-----------------------------------------------------------------------
#     def evaluate(self, C, x):
#         return ((C[0]*x + C[1])*x + C[2])*x + C[3]
#
#     #-----------------------------------------------------------------------
#     # Return evaluated derivative at x using coefficients C
#     #-----------------------------------------------------------------------
#     def derivative(self, C, x):
#         a = 3.0*C[0]            # derivative coefficients
#         b = 2.0*C[1]            # ... for sampling with rejection
#         c =     C[2]
#         return (3.0*C[0]*x + 2.0*C[1])*x + C[2]
#
