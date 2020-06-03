# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File by:  David Robertson (c)                            #
# Date:     5/2020                                         #
# License:  MIT Licence                                    #
# ##########################################################

import sys

from PyQt5.QtCore import QPoint, QRect, QSize, Qt
from PyQt5.QtWidgets import QLayout, QSizePolicy
import math


class ColumnarFlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, spacing=-1):
        super().__init__(parent)

        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)

        self.setSpacing(spacing)
        self.itemList = []

    def __del__(self):
        del_item = self.takeAt(0)
        while del_item:
            del_item = self.takeAt(0)

    def addItem(self, item):
        self.itemList.append(item)

    def count(self):
        return len(self.itemList)

    def itemAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        height = self.doLayout(QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()

        for item in self.itemList:
            size = size.expandedTo(item.minimumSize())

        margin, _, _, _ = self.getContentsMargins()

        size += QSize(2 * margin, 2 * margin)
        return size

    def doLayout(self, rect: QRect, testOnly: bool) -> int:
        spacing = self.spacing()
        x = rect.x()
        y = rect.y()

        # Determine width of widest item
        widest = 0
        for item in self.itemList:
            widest = max(widest, item.sizeHint().width())

        # Determine how many equal-width columns we can get, and how wide each one should be
        column_count = math.floor(rect.width() / (widest + spacing))
        column_count = min(column_count, len(self.itemList))
        column_count = max(1, column_count)
        column_width = math.floor((rect.width() - (column_count-1)*spacing - 1) / column_count)

        # Get the heights for all of our items
        item_heights = {}
        for item in self.itemList:
            height = item.heightForWidth(column_width) if item.hasHeightForWidth() else item.sizeHint().height()
            item_heights[item] = height

        # Prepare our column representation
        column_contents = []
        column_heights = []
        for column_index in range(column_count):
            column_contents.append([])
            column_heights.append(0)

        def add_to_column(column: int, item):
            column_contents[column].append(item)
            column_heights[column] += (item_heights[item] + spacing)

        def shove_one(from_column: int) -> bool:
            if len(column_contents[from_column]) >= 1:
                item = column_contents[from_column].pop(0)
                column_heights[from_column] -= (item_heights[item] + spacing)
                add_to_column(from_column-1, item)
                return True
            return False

        def shove_cascade_consider(from_column: int) -> bool:
            changed_item = False

            if len(column_contents[from_column]) > 1:
                item = column_contents[from_column][0]
                item_height = item_heights[item]
                if column_heights[from_column-1] + item_height < max(column_heights):
                    changed_item = shove_one(from_column) or changed_item

            if from_column+1 < column_count:
                changed_item = shove_cascade_consider(from_column+1) or changed_item

            return changed_item

        def shove_cascade() -> bool:
            if column_count < 2:
                return False
            changed_item = True
            while changed_item:
                changed_item = shove_cascade_consider(1)
            return changed_item

        def pick_best_shoving_position() -> int:
            best_pos = 1
            best_height = sys.maxsize
            for column_idx in range(1, column_count):
                if len(column_contents[column_idx]) == 0:
                    continue
                item = column_contents[column_idx][0]
                height_after_shove = column_heights[column_idx-1] + item_heights[item]
                if height_after_shove < best_height:
                    best_height = height_after_shove
                    best_pos = column_idx
            return best_pos

        # Calculate the best layout
        column_index = 0
        for item in self.itemList:
            item_height = item_heights[item]
            if column_heights[column_index] != 0 and (column_heights[column_index] + item_height) > max(column_heights):
                column_index += 1
                if column_index >= column_count:
                    # Run out of room, need to shove more stuff in each column
                    if column_count >= 2:
                        changed = shove_cascade()
                        if not changed:
                            shoving_pos = pick_best_shoving_position()
                            shove_one(shoving_pos)
                            shove_cascade()
                    column_index = column_count-1

            add_to_column(column_index, item)

        shove_cascade()

        # Set geometry according to the layout we have calculated
        if not testOnly:
            for column_index, items in enumerate(column_contents):
                x = column_index * (column_width + spacing)
                y = 0
                for item in items:
                    height = item_heights[item]
                    item.setGeometry(QRect(x, y, column_width, height))
                    y += (height + spacing)

        # Return the overall height
        return max(column_heights)
