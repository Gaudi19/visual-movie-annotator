# import pyqtgraph as pg
import time
import os
from PyQt5.QtWidgets import  QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene, QGraphicsTextItem, QCheckBox
from PyQt5.QtGui import *
from PyQt5.QtCore import *
import numpy as np
from core.data.computation import get_heatmap_value
from core.gui.ewidgetbase import EGraphicsView
from core.analysis.colorimetry.hilbert import create_hilbert_transform
from core.gui.tools import ExportImageDialog

class IVIANVisualization():
    def set_heads_up_widget(self, widget):
        pass

    def get_heads_up_widget(self):
        pass

    def get_raw_data(self):
        pass

    def apply_raw_data(self, raw_data):
        pass

    def export(self, main_window = None):
        if not isinstance(main_window, QWidget):
            main_window = None
        dialog = ExportImageDialog(main_window, self)
        dialog.show()

    def render_to_image(self, background: QColor, size: QSize):
        image = QImage(size, QImage.Format_RGBA8888)
        qp = QPainter()
        qp.begin(image)
        qp.fillRect(image.rect(), background)
        qp.end()
        return image


class VIANTextGraphicsItemSignals(QObject):
    onClicked = pyqtSignal(object)
    onEnter = pyqtSignal(object)
    onLeave = pyqtSignal(object)


class VIANTextGraphicsItem(QGraphicsTextItem):
    def __init__(self, text, font, meta = None):
        super(VIANTextGraphicsItem, self).__init__(text)
        self.setFont(font)
        self.signals = VIANTextGraphicsItemSignals()
        self.meta = meta

    def mousePressEvent(self, event: 'QGraphicsSceneMouseEvent'):
        super(VIANTextGraphicsItem, self).mousePressEvent(event)
        self.signals.onClicked.emit(self)

    def hoverEnterEvent(self, event: 'QGraphicsSceneHoverEvent'):
        super(VIANTextGraphicsItem, self).hoverEnterEvent(event)
        self.signals.onEnter.emit(self)

    def hoverLeaveEvent(self, event: 'QGraphicsSceneHoverEvent'):
        super(VIANTextGraphicsItem, self).hoverLeaveEvent(event)
        self.signals.onLeave.emit(self)


class MatrixPlot(EGraphicsView, IVIANVisualization):
    itemClicked = pyqtSignal(object)

    def __init__(self, parent, max=1.0, allow_hover = True):
        super(MatrixPlot, self).__init__(parent)
        self.dot_size = 1.0
        self.total_width = 1000
        self.max = max
        self.items = []
        self.setScene(QGraphicsScene(self))
        self.use_gray = True
        self.hover_frame = None
        self.allow_hover = allow_hover

        self.matrix = None

    def plot_data(self, matrix, names = None, meta = None, draw_image = False):
        self.scene().clear()
        self.items = []
        self.matrix = matrix
        p = QPen()
        f = QFont()
        f.setPointSize(20)
        self.dot_size = self.total_width / matrix.shape[0]

        if not draw_image:
            for x in range(matrix.shape[0]):
                for y in range(matrix.shape[1]):
                    col = get_heatmap_value(matrix[x, y], self.max, gray=self.use_gray)
                    itm = self.scene().addRect(x * self.dot_size, y * self.dot_size, self.dot_size, self.dot_size, p, QBrush(QColor(col[0], col[1], col[2])))
                    if names is not None:
                        itm.setToolTip(names[x] + "-" + names[y] + ":" + str(matrix[x,y]))
                    self.items.append(itm)
        else:
            painter = QPainter()
            img = QImage(QSize(1000,1000), QImage.Format_RGB888)
            img.fill(QColor(0,0,0))
            painter.begin(img)
            for x in range(matrix.shape[0]):
                for y in range(matrix.shape[1]):
                    col = get_heatmap_value(matrix[x, y], self.max, gray=self.use_gray)
                    painter.fillRect(QRectF(x * self.dot_size, y * self.dot_size, self.dot_size, self.dot_size), QBrush(QColor(col[0], col[1], col[2])))
            painter.end()
            self.scene().addPixmap(QPixmap().fromImage(img))
        if names is not None:
            for x in range(matrix.shape[0]):
                lbl = VIANTextGraphicsItem(names[x], f)
                self.scene().addItem(lbl)
                # lbl = self.scene().addText(names[x], f)
                lbl.setPos(x * self.dot_size + (self.dot_size / 2), -50)
                lbl.setRotation(-45.0)
                lbl.setDefaultTextColor(QColor(230, 230, 230))
                lbl.signals.onClicked.connect(self.on_text_clicked)

                if meta is not None:
                    lbl.meta = meta[x]
                if self.allow_hover:
                    lbl.signals.onEnter.connect(self.on_enter_text)
                    lbl.signals.onLeave.connect(self.on_leave_text)


                lbl = VIANTextGraphicsItem(names[x], f)
                self.scene().addItem(lbl)
                # lbl = self.scene().addText(names[x], f)
                lbl.setPos(-lbl.sceneBoundingRect().width() - 10, x * self.dot_size)
                lbl.setDefaultTextColor(QColor(230,230,230))
                lbl.signals.onClicked.connect(self.on_text_clicked)

                if meta is not None:
                    lbl.meta = meta[x]
                if self.allow_hover:
                    lbl.signals.onEnter.connect(self.on_enter_text)
                    lbl.signals.onLeave.connect(self.on_leave_text)

        self.add_value_bar(0, matrix.shape[0] * self.dot_size + 50, matrix.shape[0] * self.dot_size)

    def add_value_bar(self, x, y, width, height = 50, n_steps = 50):
        step = self.max / n_steps
        width_size = width / n_steps
        p = QPen()
        for i in range(n_steps):
            col = get_heatmap_value(i * step, self.max,gray=self.use_gray)
            itm = self.scene().addRect(i * width_size, y, width_size, height, p, QBrush(QColor(col[0], col[1], col[2])))

    @pyqtSlot(object)
    def on_text_clicked(self, object):
        pass

    @pyqtSlot(object)
    def on_enter_text(self, object):
        pass

    @pyqtSlot(object)
    def on_leave_text(self, object):
        pass


class HistogramVis(EGraphicsView, IVIANVisualization):
    def __init__(self, parent, cache_file = "data/hilbert.npz"):
        super(HistogramVis, self).__init__(parent)
        # self.view = EGraphicsView(self, auto_frame=False)
        self.setLayout(QVBoxLayout(self))
        # self.layout().addWidget(self.view)
        self.items = []

        # self.plt = pg.PlotItem()
        # self.view.addItem(self.plt)

        self.qimage = None
        if not os.path.isfile(cache_file):
            self.table, self.colors = create_hilbert_transform(16)
            np.savez(cache_file, table=self.table, colors=self.colors)
        else:
            d = np.load(cache_file)
            print(d.keys())
            self.table = (d['table'][0], d['table'][1], d['table'][2])
            self.colors = d['colors']

        self.raw_data = None

        self.plot_floor = True
        self.plot_zeros = False
        self.normalize = True
        self.draw_grid = False
        self.plot_log = True

    def plot_color_histogram(self, hist_cube):
        hist_lin = hist_cube[self.table]
        if not self.plot_zeros:
            nonz_idx =  np.nonzero(hist_lin)
            hist_lin = np.array(hist_lin)[nonz_idx]
            colors = np.array(self.colors)[nonz_idx[0]]
        else:
            colors = np.array(self.colors)
        if hist_lin.shape[0] == 0:
            return
        if self.plot_log:
            hist_lin = np.log10(hist_lin.astype(np.float32) + 1.0)
        if self.normalize:
            hist_lin = (hist_lin / np.amax(hist_lin) * 4096).astype(np.float32)

        self.raw_data = dict(hist=hist_lin, colors = colors)
        self.plot(hist_lin, colors)

    def redraw(self):
        if self.raw_data is not None:
            self.plot(self.raw_data['hist'], self.raw_data['colors'])

    def plot(self, ys, colors, width = 1):
        for i in self.items:
            self.view.removeItem(i)
        self.items.clear()
        self.scene().clear()
        img = QImage(QSize(4096,4096), QImage.Format_RGBA8888)
        img.fill(QColor(27,27,27,255))

        p = QPainter()
        p.begin(img)
        pen = QPen()
        pen.setColor(QColor(255,255,255, 255))
        pen.setWidth(5)
        p.setPen(pen)
        width = 4096 / ys.shape[0]
        if self.draw_grid:
            step = 4096 / 5
            for i in range(5):
                p.drawLine(0, i * step, 4096, i * step)

        for i in range(ys.shape[0]):
            p.fillRect(i * width, 4096 - int(ys[i]), width, int(ys[i]), QBrush(QColor(colors[i][0],colors[i][1],colors[i][2])))
            if self.plot_floor:
                p.fillRect(i * width, 4050, width, 46,
                           QBrush(QColor(colors[i][0], colors[i][1], colors[i][2])))

        p.end()
        self.qimage = img
        # self.scene().clear()
        img = self.scene().addPixmap(QPixmap().fromImage(self.qimage))
        self.fitInView(self.scene().itemsBoundingRect())

    def get_param_widget(self):
        w = QWidget()
        w.setLayout(QVBoxLayout())
        plot_floor = QCheckBox("Plot Floor")
        plot_zeros = QCheckBox("Plot Zeros")
        normalize = QCheckBox("Normalize")
        draw_grid = QCheckBox("Draw Grid")
        plot_log = QCheckBox("Plot Log")

        plot_floor.setChecked(self.plot_floor)
        plot_zeros.setChecked(self.plot_zeros)
        normalize.setChecked(self.normalize)
        draw_grid.setChecked(self.draw_grid)
        plot_log.setChecked(self.plot_log)

        plot_floor.stateChanged.connect(self.set_plot_floor)
        plot_zeros.stateChanged.connect(self.set_plot_zeros)
        normalize.stateChanged.connect(self.set_normalize)
        draw_grid.stateChanged.connect(self.set_draw_grid)
        plot_log.stateChanged.connect(self.set_plot_log)

        w.layout().addWidget(plot_floor)
        w.layout().addWidget(plot_zeros)
        w.layout().addWidget(normalize)
        w.layout().addWidget(draw_grid)
        w.layout().addWidget(plot_log)

        return w

    def set_plot_floor(self, state):
        self.plot_floor = state
        self.redraw()

    def set_plot_zeros(self, state):
        self.plot_zeros = state
        self.redraw()

    def set_normalize(self, state):
        self.normalize = state
        self.redraw()

    def set_draw_grid(self, state):
        self.draw_grid = state
        self.redraw()

    def set_plot_log(self, state):
        self.plot_log = state
        self.redraw()


class PaletteVis(QWidget, IVIANVisualization):
    def __init__(self, parent):
        super(PaletteVis, self).__init__(parent)
        self.view = QGraphicsView()
        self.view.setScene(QGraphicsScene())

        self.setLayout(QVBoxLayout(self))
        self.layout().addWidget(self.view)
        self.items = []
        # self.plt = pg.PlotItem()
        # self.view.addItem(self.plt)


    def plot(self, values, colors):
        size_factor = 1.0 / np.sum(values)
        cx = 0
        for i in self.items:
            self.view.scene().removeItem(i)
        self.items.clear()

        ax = 0.0
        bx = 0.0
        for i in range(len(values)):
            bx = ax + values[i] * size_factor
            itm = self.view.scene().addRect(QRectF(ax, 1.0, bx, 0.0),
                                            brush=QColor(colors[i][0],colors[i][1],colors[i][2]),
                                            pen=QPen(QColor(colors[i][0],colors[i][1],colors[i][2])))
            ax += values[i] * size_factor
            self.items.append(itm)

        self.view.fitInView(self.view.sceneRect())

