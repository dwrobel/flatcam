#############################################################################
# Copyright (c) 2013 by Panagiotis Mavrogiorgos
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
# * Neither the name(s) of the copyright holders nor the names of its
#   contributors may be used to endorse or promote products derived from this
#   software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AS IS AND ANY EXPRESS OR
# IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
# EVENT SHALL THE COPYRIGHT HOLDERS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
# OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#############################################################################
#
# @license: http://opensource.org/licenses/BSD-3-Clause

from bisect import bisect_left
import logging

log = logging.getLogger('base')


class BilinearInterpolation(object):
    """
    Bilinear interpolation with optional extrapolation.
    Usage:
    table = BilinearInterpolation(
        x_index=(1, 2, 3),
        y_index=(1, 2, 3),
        values=((110, 120, 130),
                (210, 220, 230),
                (310, 320, 330)),
        extrapolate=True)

    assert table(1, 1) == 110
    assert table(2.5, 2.5) == 275

    """
    def __init__(self, x_index, y_index, values):
        # sanity check
        x_length = len(x_index)
        y_length = len(y_index)

        if x_length < 2 or y_length < 2:
            raise ValueError("Table must be at least 2x2.")
        if y_length != len(values):
            raise ValueError("Table must have equal number of rows to y_index.")
        if any(x2 - x1 <= 0 for x1, x2 in zip(x_index, x_index[1:])):
            raise ValueError("x_index must be in strictly ascending order!")
        if any(y2 - y1 <= 0 for y1, y2 in zip(y_index, y_index[1:])):
            raise ValueError("y_index must be in strictly ascending order!")

        self.x_index = x_index
        self.y_index = y_index
        self.values = values
        self.x_length = x_length
        self.y_length = y_length
        self.extrapolate = True

        # slopes = self.slopes = []
        # for j in range(y_length):
        #     intervals = zip(x_index, x_index[1:], values[j], values[j][1:])
        #     slopes.append([(y2 - y1) / (x2 - x1) for x1, x2, y1, y2 in intervals])

    def __call__(self, x, y):
        # local lookups
        x_index, y_index, values = self.x_index, self.y_index, self.values

        i = bisect_left(x_index, x) - 1
        j = bisect_left(y_index, y) - 1

        if self.extrapolate:
            # fix x index
            if i == -1:
                x_slice = slice(None, 2)
            elif i == self.x_length - 1:
                x_slice = slice(-2, None)
            else:
                x_slice = slice(i, i + 2)

            # fix y index
            if j == -1:
                j = 0
                y_slice = slice(None, 2)
            elif j == self.y_length - 1:
                j = -2
                y_slice = slice(-2, None)
            else:
                y_slice = slice(j, j + 2)
        else:
            if i == -1 or i == self.x_length - 1:
                raise ValueError("Extrapolation not allowed!")
            if j == -1 or j == self.y_length - 1:
                raise ValueError("Extrapolation not allowed!")

        # if the extrapolations is False this will fail
        x1, x2 = x_index[x_slice]
        y1, y2 = y_index[y_slice]
        z11, z12 = values[j][x_slice]
        z21, z22 = values[j + 1][x_slice]

        return (z11 * (x2 - x) * (y2 - y) +
                z21 * (x - x1) * (y2 - y) +
                z12 * (x2 - x) * (y - y1) +
                z22 * (x - x1) * (y - y1)) / ((x2 - x1) * (y2 - y1))
