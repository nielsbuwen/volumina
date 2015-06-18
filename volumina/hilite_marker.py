from PyQt4.QtCore import Qt, QRectF, QPointF, QLineF
from PyQt4.QtGui import QPen, QGraphicsLineItem, QGraphicsItemGroup, QGraphicsRectItem


class HiliteCross(object):
    def __init__(self, coords, size, scene):
        self.coords = coords
        self.size = size
        self.scene = scene

        self.item = QGraphicsItemGroup()
        h, v = self.lines
        pen = QPen(Qt.yellow)
        pen.setWidth(2)
        h_line = QGraphicsLineItem(h)
        h_line.setPen(pen)
        self.item.addToGroup(h_line)
        v_line = QGraphicsLineItem(v)
        v_line.setPen(pen)
        self.item.addToGroup(v_line)

        self.show()

    def update(self):
        for item, line in zip(self.item.childItems(), self.lines):
            item.setLine(line)

    @property
    def actual_coords(self):
        return self.scene.adjust_object_position(*self.coords)

    @property
    def lines(self):
        x, y = self.actual_coords
        return [
            QLineF(x - self.size, y, x + self.size, y),
            QLineF(x, y - self.size, x, y + self.size)
        ]

    def remove(self):
        self.scene.removeItem(self.item)

    def show(self):
        self.scene.addItem(self.item)


class HiliteBB(object):
    def __init__(self, coords, size, scene):
        x1, y1, x2, y2 = coords
        self.coords = (x1 - size, y1 - size, x2 + size, y2 + size)
        self.scene = scene

        pen = QPen(Qt.yellow)
        pen.setWidth(2)
        self.item = QGraphicsRectItem(self.rect)
        self.item.setPen(pen)

        self.show()
        print "bb created at", self.coords, self.actual_coords

    def update(self):
        self.item.setRect(self.rect)

    @property
    def rect(self):
        x1, y1, x2, y2 = self.actual_coords
        return QRectF(QPointF(x1, y1),
                      QPointF(x2, y2))

    @property
    def actual_coords(self):
        x1, y1 = self.scene.adjust_object_position(*self.coords[:2])
        x2, y2 = self.scene.adjust_object_position(*self.coords[2:4])
        return x1, y1, x2, y2

    def remove(self):
        self.scene.removeItem(self.item)

    def show(self):
        self.scene.addItem(self.item)
