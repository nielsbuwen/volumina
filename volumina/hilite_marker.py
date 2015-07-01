from collections import defaultdict
from itertools import combinations
from PyQt4.QtCore import Qt, QRectF, QPointF
from PyQt4.QtGui import QPen, QGraphicsRectItem, QGraphicsPixmapItem, QPixmap, QImage, QColor, QGraphicsItemGroup,\
    QGraphicsEllipseItem, QGraphicsLineItem
from numpy import zeros, uint8, all as np_all


class HiliteList(object):
    def __init__(self, scenes):
        self.markers = defaultdict(dict)
        """:type: dict[int, dict[int, HiliteContainer]]"""
        self.scenes = scenes
        self.current_timestep = 0
        self.current_slice_position = None

    def print_(self):
        for key, value in self.markers.iteritems():
            print key
            for kkey, vvalue in value.iteritems():
                print "   ", kkey, vvalue

    def add(self, time, obj_id, mins, centers, maxs, slices):
        if obj_id in self.markers[time]:
            return

        marker = HiliteContainer(centers, mins, maxs, slices, self.scenes)
        self.markers[time][obj_id] = marker
        self.change_slice_position(self.current_slice_position, None, timestep=time)

    def remove(self, time, obj_id):
        if obj_id not in self.markers[time]:
            return
        marker = self.markers[time].pop(obj_id)
        marker.hide()

    def change_timestep(self, timestep):
        self._hide()
        self._show(timestep)
        self.current_timestep = timestep

    def change_slice_position(self, new_position, _, timestep=None):
        if timestep is None:
            timestep = self.current_timestep
        self.current_slice_position = new_position
        for marker in self.iter_markers(time=timestep):
            marker.update_position(new_position)

    def update(self):
        for marker in self.iter_markers(time=self.current_timestep):
            marker.update()

    def clear(self):
        for marker in self.all_markers:
            marker.hide()
        self.markers = defaultdict(dict)

    def _show(self, timestep=None, key=None):
        for marker in self.iter_markers(timestep, key):
            marker.show()

    def _hide(self, timestep=None, key=None):
        for marker in self.iter_markers(timestep, key):
            marker.hide()

    def iter_markers(self, time=None, obj_id=None):
        if time is None:
            return self.all_markers

        time_markers = self.markers[time]
        if obj_id is None:
            return time_markers.itervalues()

        return time_markers[obj_id],

    @property
    def all_markers(self):
        return (marker for time in self.markers.itervalues() for marker in time.itervalues())


def two_coords(position):
    return combinations(reversed(position), 2)


class HiliteContainer(object):
    def __init__(self, centers, mins, maxs, slices, scenes):
        zipped = [slices, scenes] + [two_coords(pos) for pos in (mins, centers, maxs)]
        self.items = [HiliteItem(*coords) for coords in zip(*zipped)]
        for item, low, up in zip(self.items, mins, maxs):
            item.depth = (low, up)

    def show(self):
        [item.show() for item in self.items]

    def hide(self):
        [item.hide() for item in self.items]

    def update(self):
        [item.update() for item in self.items]

    def update_position(self, positions):
        [item.update_position(pos) for item, pos in zip(self.items, positions)]

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return "Hilite [{}]".format(", ".join("None" if i.item is None else i.update.__name__ for i in self.items))


def extend_to4(x):
    return x + (4 - x % 4) % 4


class HiliteItem(object):
    active_color = Qt.yellow
    active_width = 2
    inactive_color = Qt.yellow
    inactive_width = 1
    hidden_color = QColor(Qt.darkYellow).rgba()
    margin = 5

    def __init__(self, slice_, scene, top_left, center, bot_right):
        self.center = center[::-1]
        self.top_left = [c - self.margin for c in top_left][::-1]
        self.bot_right = [c + self.margin for c in bot_right][::-1]

        if len(slice_.shape) == 2:
            image_data = zeros(map(extend_to4, slice_.shape), dtype=uint8)
            image_data[:slice_.shape[0], :slice_.shape[1]] = slice_
            self.image = self.create_image(image_data)
            self.outline = self.create_outline_image(image_data)
            self.dmode = 3
        else:
            self.dmode = 2

        self.scene = scene
        self.depth = None

        self.active_pen = QPen(self.active_color)
        self.active_pen.setWidth(self.active_width)
        self.active_pen.setCosmetic(True)
        self.inactive_pen = QPen(self.inactive_color)
        self.inactive_pen.setWidth(self.inactive_width)
        self.inactive_pen.setCosmetic(True)

        self.item = None
        """:type: None"""
        self.update = lambda: None

    @classmethod
    def create_outline_image(cls, data):
        for y in xrange(1, data.shape[0] - 1):
            for x in xrange(1, data.shape[1] - 1):
                try:
                    if np_all(data[y-1:y+2, x-1:x+2] != 0):
                        data[y, x] = 1
                except IndexError:
                    pass
        data[data == 1] = 0
        return cls.create_image(data)

    @classmethod
    def create_image(cls, data):
        image = QImage(data.data, data.shape[1], data.shape[0], QImage.Format_Indexed8)
        image.setColor(0, 0x00000000)
        image.setColor(255, cls.hidden_color)
        return image

    def hide(self):
        if self.item is not None and self.item.scene() is not None:
            self.item.scene().removeItem(self.item)

    def show(self):
        if self.item is not None and self.item.scene() is None:
            self.update()
            self.scene.addItem(self.item)

    @property
    def actual_tl(self):
        return self.scene.adjust_object_position(*[tl + self.margin for tl in self.top_left])

    @property
    def actual_bb(self):
        return self.scene.adjust_object_position(*self.top_left), \
            self.scene.adjust_object_position(*self.bot_right)

    @property
    def rect(self):
        (x1, y1), (x2, y2) = self.actual_bb
        return QRectF(QPointF(x1, y1),
                      QPointF(x2, y2))

    def update_rect(self):
        self.item.setRect(self.rect)

    def update_outline(self):
        x, y = self.actual_tl
        rotate, swap_y = self.scene.orientation
        shape, image = self.item.childItems()
        image.setPos(QPointF(x, y))
        image.setRotation(rotate)
        image.scale(1, swap_y)
        shape.setRect(self.rect)

    def update_image(self):
        (otlx, otly), (obrx, obry) = self.actual_bb
        tlx, tly = self.actual_tl
        rotate, swap_y = self.scene.orientation
        image, neg, pos = self.item.childItems()
        image.setPos(QPointF(tlx, tly))
        image.setRotation(rotate)
        image.scale(1, swap_y)

        neg.setLine(otlx, otly, obrx, obry)
        pos.setLine(otlx, obry, obrx, otly)

    def update_position(self, position):
        self.hide()
        if self.dmode == 2 or self.depth[0] <= position <= self.depth[1]:
            self.item = QGraphicsRectItem(self.rect)
            self.item.setPen(self.active_pen)
            self.update = self.update_rect
            self.show()
        elif position < self.depth[0]:
            pixmap = QPixmap.fromImage(self.outline)
            group = QGraphicsItemGroup()
            image = QGraphicsPixmapItem(pixmap, self.item)
            circle = QGraphicsEllipseItem(self.rect)
            circle.setPen(self.inactive_pen)
            group.addToGroup(circle)
            group.addToGroup(image)
            self.item = group
            self.update = self.update_outline
            self.show()
        else:
            pixmap = QPixmap.fromImage(self.image)
            group = QGraphicsItemGroup()
            image = QGraphicsPixmapItem(pixmap, self.item)
            group.addToGroup(image)
            for _ in xrange(2):
                line = QGraphicsLineItem()
                line.setPen(self.inactive_pen)
                group.addToGroup(line)
            self.item = group
            self.update = self.update_image
            self.show()
