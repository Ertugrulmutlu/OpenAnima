from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QWidget


class CompositePreviewCanvas(QWidget):
    def __init__(self, dialog):
        super().__init__(dialog)
        self.dialog = dialog
        self.pixmap = QPixmap()
        self.scale = 1.0
        self.offset = QPointF(0, 0)
        self.dragging = False
        self.drag_offset = QPointF(0, 0)
        self.drag_started = False
        self.setMinimumSize(260, 180)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)

    def set_pixmap(self, pixmap):
        self.pixmap = pixmap
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        self.draw_checkerboard(painter)
        if self.pixmap.isNull():
            painter.setPen(QColor("#b8b8b8"))
            painter.drawText(self.rect(), Qt.AlignCenter, "No readable layers")
            return

        self.update_transform()
        target = QRectF(
            self.offset.x(),
            self.offset.y(),
            self.pixmap.width() * self.scale,
            self.pixmap.height() * self.scale,
        )
        painter.drawPixmap(target, self.pixmap, QRectF(self.pixmap.rect()))
        self.draw_grid(painter, target)
        self.draw_all_bounds(painter)
        self.draw_selected_bounds(painter)

    def draw_checkerboard(self, painter):
        painter.fillRect(self.rect(), QColor("#202020"))
        cell = 12
        color_a = QColor("#2a2a2a")
        color_b = QColor("#343434")
        for y in range(0, self.height(), cell):
            for x in range(0, self.width(), cell):
                painter.fillRect(x, y, cell, cell, color_a if ((x // cell + y // cell) % 2 == 0) else color_b)

    def draw_grid(self, painter, target):
        if not self.dialog.show_grid_check.isChecked():
            return
        grid = max(1, round(16 * self.scale))
        painter.setPen(QPen(QColor(255, 255, 255, 45), 1))
        x = target.left()
        while x <= target.right():
            painter.drawLine(x, target.top(), x, target.bottom())
            x += grid
        y = target.top()
        while y <= target.bottom():
            painter.drawLine(target.left(), y, target.right(), y)
            y += grid

    def update_transform(self):
        if self.pixmap.isNull():
            return
        zoom = self.dialog.preview_zoom
        if zoom == "fit":
            self.scale = min(
                self.width() / max(1, self.pixmap.width()),
                self.height() / max(1, self.pixmap.height()),
                1.0,
            )
        else:
            self.scale = float(zoom)
        draw_width = self.pixmap.width() * self.scale
        draw_height = self.pixmap.height() * self.scale
        self.offset = QPointF((self.width() - draw_width) / 2, (self.height() - draw_height) / 2)

    def draw_selected_bounds(self, painter):
        index = self.dialog.selected_layer_index
        if index < 0 or index >= len(self.dialog.layers):
            return
        layer = self.dialog.layers[index]
        rect = self.layer_rect(layer)
        if rect is None:
            return
        scaled = QRectF(
            self.offset.x() + rect.x() * self.scale,
            self.offset.y() + rect.y() * self.scale,
            rect.width() * self.scale,
            rect.height() * self.scale,
        )
        painter.setPen(QPen(QColor("#ffdd55"), 2, Qt.SolidLine))
        painter.drawRect(scaled)
        painter.setPen(QPen(QColor("#111111"), 1, Qt.DotLine))
        painter.drawLine(scaled.left(), scaled.top(), scaled.right(), scaled.bottom())
        painter.drawLine(scaled.right(), scaled.top(), scaled.left(), scaled.bottom())
        painter.setPen(QPen(QColor("#ffdd55"), 1))
        painter.drawText(scaled.adjusted(4, -18, 240, 0), str(layer.get("name") or "layer"))

    def draw_all_bounds(self, painter):
        if not self.dialog.show_bounds_check.isChecked():
            return
        painter.setPen(QPen(QColor("#66c2ff"), 1, Qt.DashLine))
        for index, layer in enumerate(self.dialog.layers):
            if index == self.dialog.selected_layer_index or not layer.get("visible", True):
                continue
            rect = self.layer_rect(layer)
            if rect is None:
                continue
            painter.drawRect(
                QRectF(
                    self.offset.x() + rect.x() * self.scale,
                    self.offset.y() + rect.y() * self.scale,
                    rect.width() * self.scale,
                    rect.height() * self.scale,
                )
            )

    def layer_rect(self, layer):
        image = layer.get("image")
        if not image:
            return None
        image_path = self.dialog.source_path / image if self.dialog.source_path.is_dir() else self.dialog.source_path
        pixmap = QPixmap(str(image_path))
        if pixmap.isNull():
            return None
        return QRectF(float(layer.get("x", 0)), float(layer.get("y", 0)), pixmap.width(), pixmap.height())

    def event_to_asset_point(self, event):
        if self.pixmap.isNull() or self.scale <= 0:
            return None
        point = event.position()
        return QPointF((point.x() - self.offset.x()) / self.scale, (point.y() - self.offset.y()) / self.scale)

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return super().mousePressEvent(event)
        self.setFocus()
        point = self.event_to_asset_point(event)
        if point is None:
            return
        cycle = bool(event.modifiers() & (Qt.AltModifier | Qt.ControlModifier))
        index = self.dialog.layer_at_point(point, cycle=cycle)
        if index >= 0:
            self.dialog.select_layer(index)
            layer = self.dialog.layers[index]
            self.dragging = True
            self.drag_started = False
            self.drag_offset = QPointF(point.x() - float(layer.get("x", 0)), point.y() - float(layer.get("y", 0)))
        event.accept()

    def mouseMoveEvent(self, event):
        if self.dragging and self.dialog.selected_layer_index >= 0:
            point = self.event_to_asset_point(event)
            if point is None:
                return
            if not self.drag_started:
                self.dialog.push_undo_state("Move layer")
                self.drag_started = True
            x = round(point.x() - self.drag_offset.x())
            y = round(point.y() - self.drag_offset.y())
            self.dialog.set_selected_layer_position(x, y)
            event.accept()
            return

        point = self.event_to_asset_point(event)
        index = self.dialog.layer_at_point(point) if point is not None else -1
        if index >= 0:
            layer = self.dialog.layers[index]
            self.setToolTip(f"{layer.get('name', 'layer')}\n{layer.get('image', '')}\nx={layer.get('x', 0)}, y={layer.get('y', 0)}")
        else:
            self.setToolTip("")
        return super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.dragging = False
        self.drag_started = False
        return super().mouseReleaseEvent(event)
