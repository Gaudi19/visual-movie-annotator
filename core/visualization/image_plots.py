import numpy as np
import cv2

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QColor, QImage, QPixmap, QWheelEvent, QKeyEvent, QMouseEvent, QPen, QFont
from PyQt5.QtWidgets import *
from PyQt5.QtCore import QPoint, Qt, QRectF, pyqtSlot, pyqtSignal

from core.data.computation import *

class ImagePlot(QGraphicsView):
    def __init__(self, parent, range_x = None, range_y = None, create_controls = False, title = ""):
        super(ImagePlot, self).__init__(parent)

        if range_x is None:
            range_x = [-128, 128]
        if range_y is None:
            range_y = [-128, 128]

        self.setStyleSheet("QWidget:focus{border: rgb(30,30,30); } QWidget:{border: rgb(30,30,30);}")

        self.setBackgroundBrush(QColor(30, 30, 30))
        self.setScene(QGraphicsScene(self))
        self.ctrl_is_pressed = False
        self.img_width = 192
        self.curr_scale = 1.0
        self.magnification = 100
        self.images = []
        self.range_x = range_x
        self.range_y = range_y
        self.font_size = 4
        self.title = title

        self.luminances = []

        self.n_grid = 12
        self.controls_itm = None

        self.fitInView(   range_x[0] * self.magnification,
                          range_y[0] * self.magnification,
                         (range_x[1] - range_x[0]) * self.magnification,
                         (range_y[1] - range_y[0]) * self.magnification, Qt.KeepAspectRatio)
        self.add_grid()
        self.create_title()

    def add_image(self, x, y, img, convert = True, luminance = None):
        pass

    def sort_images(self):
        self.luminances = sorted(self.luminances, key=lambda x: x[0])

    def add_grid(self):
        pass

    def create_title(self):
        if self.title == "":
            return
        font = QFont()
        font.setPointSize(self.font_size * self.magnification)
        t = self.scene().addText(self.title, font)
        t.setPos((self.range_x[0] + self.range_x[1]) / 2 * self.magnification, -20 * self.magnification)
        t.setDefaultTextColor(QColor(200, 200, 200, 200))

    def add_controls(self, ctrl):
        self.controls_itm = self.scene().addWidget(ctrl)
        self.controls_itm.show()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Control:
            self.ctrl_is_pressed = True
            event.ignore()
        else:
            event.ignore()

    def keyReleaseEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Control:
            self.ctrl_is_pressed = False
        else:
            event.ignore()

    def wheelEvent(self, event: QWheelEvent):
        # bbox = self.sceneRect()
        # self.controls_itm.setPos(bbox.x(), bbox.y())

        if self.ctrl_is_pressed:
            self.setTransformationAnchor(QGraphicsView.NoAnchor)
            self.setResizeAnchor(QGraphicsView.NoAnchor)

            old_pos = self.mapToScene(event.pos())

            h_factor = 1.1
            l_factor = 0.9

            viewport_size = self.mapToScene(QPoint(self.width(), self.height())) - self.mapToScene(QPoint(0, 0))
            self.curr_scale = round(self.img_width / (viewport_size.x()), 4)

            if event.angleDelta().y() > 0.0 and self.curr_scale < 100:
                self.scale(h_factor, h_factor)
                self.curr_scale *= h_factor

            elif event.angleDelta().y() < 0.0 and self.curr_scale > 0.001:
                self.curr_scale *= l_factor
                self.scale(l_factor, l_factor)

            cursor_pos = self.mapToScene(event.pos()) - old_pos

            self.translate(cursor_pos.x(), cursor_pos.y())

            for itm in self.images:
                itm.setScale(1 - self.curr_scale)

        else:
            super(QGraphicsView, self).wheelEvent(event)

    def clear_view(self):
        self.scene().clear()
        self.images.clear()
        self.luminances.clear()

    @pyqtSlot(int)
    def on_high_cut(self, value):
        for tpl in self.luminances:
            if tpl[0] > value:
                tpl[1].hide()
            else:
                tpl[1].show()


    @pyqtSlot(int)
    def on_low_cut(self, value):
        for tpl in self.luminances:
            if tpl[0] < value:
                tpl[1].hide()
            else:
                tpl[1].show()


class ImagePlotCircular(ImagePlot):
    def __init__(self, parent, range_x = None, range_y = None):
        super(ImagePlotCircular, self).__init__(parent, range_x, range_y)

    def add_image(self, x, y, img, convert = True, luminance = None):
        if convert:
            itm = QGraphicsPixmapItem(numpy_to_pixmap(img))
        else:
            itm = QGraphicsPixmapItem(numpy_to_pixmap(img, cvt=None))
        self.scene().addItem(itm)
        itm.setPos((x -128) * self.magnification, (y -128) * self.magnification)
        self.images.append(itm)

        if luminance is not None:
            self.luminances.append([luminance, itm])

        itm.show()

    def add_grid(self):
        pen = QPen()
        pen.setWidth(10)
        pen.setColor(QColor(200,200,200,150))

        font = QFont()
        font.setPointSize(self.font_size * self.magnification)

        for i in range(7):
            self.circle0 = self.scene().addEllipse(QRectF(0,
                                           0,
                                                          (255/6 * i) * self.magnification,
                                                          (255 / 6 * i) * self.magnification),
                                    pen)

            q = -(128/6 * i)
            self.circle0.setPos(q * self.magnification, q * self.magnification)
            text = self.scene().addText(str(round(i *(128/6),0)), font)
            text.setPos(0,(-i *(128/6) * self.magnification)- self.font_size *self.magnification)
            text.setDefaultTextColor(QColor(200,200,200,200))

        for i in range(self.n_grid):
            x = 128 * self.magnification * np.cos(i * (2 * np.pi / self.n_grid))
            y = 128 * self.magnification * np.sin(i * (2 * np.pi / self.n_grid))
            self.scene().addLine(0, 0 , x, y, pen)
        self.circle0.show()

class ImagePlotPlane(ImagePlot):
    def __init__(self, parent, range_x = None, range_y = None, title=""):
        super(ImagePlotPlane, self).__init__(parent, range_x, range_y, title=title)

    def add_image(self, x, y, img, convert = True):
        if convert:
            itm = QGraphicsPixmapItem(numpy_to_pixmap(img))
        else:
            itm = QGraphicsPixmapItem(numpy_to_pixmap(img, cvt=None))
        self.scene().addItem(itm)

        itm.setPos(x * self.magnification, self.range_y[1] * self.magnification - y * self.magnification)
        self.images.append(itm)

        self.luminances.append([y, itm])

        itm.show()

    def add_grid(self):
        pen = QPen()
        pen.setWidth(10)
        pen.setColor(QColor(200, 200, 200, 150))

        font = QFont()
        font.setPointSize(self.font_size * self.magnification)

        x0 = self.range_x[0] * self.magnification
        x1 = self.range_x[1] * self.magnification
        y0 = self.range_y[0] * self.magnification
        y1 = self.range_y[1] * self.magnification
        for x in range(self.range_x[0] * self.magnification, self.range_x[1] * self.magnification, 1):
            if x % (20 * self.magnification) == 0:
                self.scene().addLine(x, y0, x, y1, pen)

                text = self.scene().addText(str(round((x / self.magnification), 0)), font)
                text.setPos(x, self.range_y[1] * self.magnification)
                text.setDefaultTextColor(QColor(200, 200, 200, 200))


        for x in range(self.range_y[0] * self.magnification, self.range_y[1] * self.magnification, 1):
            if x % (20 * self.magnification) == 0:
                self.scene().addLine(x0, x, x1, x, pen)

                text = self.scene().addText(str(round(((self.range_y[1] * self.magnification - x) / self.magnification), 0)), font)
                text.setPos(self.range_x[0] * self.magnification, x)
                text.setDefaultTextColor(QColor(200, 200, 200, 200))


class ImagePlotControls(QWidget):
    onLowCutChange = pyqtSignal(int)
    onHighCutChange = pyqtSignal(int)

    def __init__(self, parent):
        super(ImagePlotControls, self).__init__(parent)
        self.view = parent
        self.low_cut = -128
        self.high_cut = 128

        self.setLayout(QVBoxLayout(self))

        self.lay_hcut = QHBoxLayout(self)
        self.sl_hcut = QSlider(Qt.Horizontal, self)
        self.sl_hcut.setRange(0, 100)
        self.sl_hcut.setValue(100)
        self.sl_hcut.valueChanged.connect(self.on_high_cut)
        self.lbl_hcut = QLabel("L-High Cut: 0", self)
        self.lbl_hcut.setStyleSheet("QLabel {color: rgb(255,255,255)}")
        self.lay_hcut.addWidget(self.sl_hcut)
        self.lay_hcut.addWidget(self.lbl_hcut)

        self.lay_lcut = QHBoxLayout(self)
        self.sl_lcut = QSlider(Qt.Horizontal, self)
        self.sl_lcut.setRange(0, 100)
        self.sl_hcut.setValue(0)
        self.sl_lcut.valueChanged.connect(self.on_low_cut)
        self.lbl_lcut = QLabel("L-Low Cut: 0", self)
        self.lbl_lcut.setStyleSheet("QLabel {color: rgb(255,255,255)}")
        self.lay_lcut.addWidget(self.sl_lcut)
        self.lay_lcut.addWidget(self.lbl_lcut)

        self.layout().addItem(self.lay_lcut)
        self.layout().addItem(self.lay_hcut)

        self.resize(200, 100)

    def on_low_cut(self):
        value = self.sl_lcut.value()
        self.lbl_lcut.setText("L-Low Cut:" + str(value))
        self.onLowCutChange.emit(value)

    def on_high_cut(self):
        value = self.sl_hcut.value()
        self.lbl_hcut.setText("L-Low Cut:" + str(value))
        self.onHighCutChange.emit(value)

