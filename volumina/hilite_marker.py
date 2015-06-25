from collections import defaultdict
from itertools import combinations
from PyQt4.QtCore import Qt, QRectF, QPointF, QLineF
from PyQt4.QtGui import QPen, QGraphicsLineItem, QGraphicsItemGroup, QGraphicsRectItem
from functools import partial


class HiliteList(object):
    def __init__(self, scenes):
        self.markers = defaultdict(partial(defaultdict, list))
        """:type: dict[int, dict[tuple, list[HiliteMarker]]]"""
        self.scenes = scenes
        self.current_timestep = 0
        self.current_hilite = 0, 0, 0

    def add_object(self, time, top_left, bottom_right, _):
        coords = self._iter_scenes_with_coords(top_left, bottom_right)
        self._add(HiliteBB, coords, 5, time, (tuple(top_left), tuple(bottom_right)))

    def add_cross(self, time, x, y, z, _):
        coords = self._iter_scenes_with_coords((x, y, z))
        self._add(HiliteCross, coords, 5, time, (x, y, z))

    def _add(self, class_, coords, size, timestep, position):
        if position in self.markers[timestep]:
            print "Already exists"
            return

        self.markers[timestep][position] = [class_(coord, size, scene) for scene, coord in coords]

    def _print(self):
        for key, value in self.markers.iteritems():
            print key
            for kkey, vvalue in value.iteritems():
                print "   ", kkey
                for m in vvalue:
                    print "       ", m

    def remove(self, *pos):
        if len(pos) == 5:
            timestep, x, y, z, c = pos
            key = x, y, z
        else:
            timestep, tl, br, c = pos
            key = (tuple(tl), tuple(br))
        if key not in self.markers[timestep]:
            print "Does not exist"
            return
        markers = self.markers[timestep].pop(key)
        for marker in markers:
            marker.hide()

    def change_timestep(self, timestep):
        self._hide(self.current_timestep)
        self._show(timestep)
        self.current_timestep = timestep

    def update(self):
        for marker in self._iter_time(self.current_timestep):
            marker.update()

    def clear(self):
        for marker in self._iter_all():
            marker.hide()
        self.markers = defaultdict(partial(defaultdict, list))

    def _show(self, timestep=None, key=None):
        for marker in self._iter_marker(timestep, key):
            marker.show()

    def _hide(self, timestep=None, key=None):
        for marker in self._iter_marker(timestep, key):
            marker.hide()

    def _iter_marker(self, time=None, key=None):
        if time is None and key is None:
            return self._iter_all()
        if key is None:
            return self._iter_time(time)
        if time is None:
            raise ValueError("key is not None and time is None")
        return self._iter_pos(time, key)

    def _iter_all(self):
        for time in self.markers.itervalues():
            for list_ in time.itervalues():
                for marker in list_:
                    yield marker

    def _iter_time(self, time):
        for list_ in self.markers[time].itervalues():
            for marker in list_:
                yield marker

    def _iter_pos(self, time, pos):
        for marker in self.markers[time][pos]:
            yield marker

    def _iter_scenes_with_coords(self, *positions):
        zipped = [self.scenes]
        for position in positions:
            zipped.append(combinations(reversed(position), 2))

        for it in zip(*zipped):
            yield it[0], it[1:]


class HiliteMarker(object):
    def update(self):
        raise NotImplementedError

    def hide(self):
        if self.item.scene() is not None:
            self._hide()

    def show(self):
        if self.item.scene() is None:
            self._show()

    def _hide(self):
        raise NotImplementedError

    def _show(self):
        raise NotImplementedError

    def __repr__(self):
        return self.__str__()


class HiliteCross(HiliteMarker):
    def __init__(self, coords, size, scene):
        self.coords = coords[0]
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
        return self.scene.adjust_object_position(*reversed(self.coords))

    @property
    def lines(self):
        x, y = self.actual_coords
        return [
            QLineF(x - self.size, y, x + self.size, y),
            QLineF(x, y - self.size, x, y + self.size)
        ]

    def _hide(self):
        self.scene.removeItem(self.item)

    def _show(self):
        self.scene.addItem(self.item)

    def __str__(self):
        return "Cross ({}/{})".format(*self.coords)


class HiliteBB(HiliteMarker):
    def __init__(self, coords, size, scene):
        (x1, y1), (x2, y2) = coords
        self.coords = (x1 - size, y1 - size, x2 + size, y2 + size)
        self.scene = scene

        pen = QPen(Qt.yellow)
        pen.setWidth(2)
        self.item = QGraphicsRectItem(self.rect)
        self.item.setPen(pen)

        self.show()

    def update(self):
        self.item.setRect(self.rect)

    @property
    def rect(self):
        x1, y1, x2, y2 = self.actual_coords
        return QRectF(QPointF(x1, y1),
                      QPointF(x2, y2))

    @property
    def actual_coords(self):
        x1, y1 = self.scene.adjust_object_position(*self.coords[1::-1])
        x2, y2 = self.scene.adjust_object_position(*self.coords[3:1:-1])
        return x1, y1, x2, y2

    def _hide(self):
        self.scene.removeItem(self.item)

    def _show(self):
        self.scene.addItem(self.item)

    def __str__(self):
        return "BB ({}/{} - {}/{})".format(*self.coords)
