from core.gui.ewidgetbase import EDockWidget
from PyQt5 import uic, QtWidgets
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from core.data.interfaces import IProjectChangeNotify
from core.analysis.colorimetry.hilbert import create_hilbert_transform, hilbert_mapping_3d, HilbertMode
from core.visualization.palette_plot import PaletteWidget, PaletteLABWidget, PaletteTimeWidget
from core.visualization.basic_vis import HistogramVis
from core.gui.ewidgetbase import ExpandableWidget, ESimpleDockWidget
from core.visualization.line_plot import LinePlot
import cv2
import numpy as np

from core.visualization.basic_vis import *

class ColorimetryLiveWidget(EDockWidget, IProjectChangeNotify):
    def __init__(self, main_window):
        super(ColorimetryLiveWidget, self).__init__(main_window, limit_size=False)
        self.setWindowTitle("Colorimetry")
        self.lt = QVBoxLayout(self)
        self.central = QWidget()
        self.central.setFixedWidth(1)
        self.central.setLayout(self.lt)

        self.inner.setCentralWidget(self.central)
        self.use_tab_mode = False

        self.m_visualization = self.inner.menuBar().addMenu("Visualizations")
        self.a_palette = self.m_visualization.addAction("Palette")
        self.a_palette_ab = self.m_visualization.addAction("Palette AB")
        self.a_palette_dt = self.m_visualization.addAction("Palette dT")
        self.a_hist = self.m_visualization.addAction("Histogram dT")
        self.a_spatial = self.m_visualization.addAction("Spatial Complexity dT")

        # self.vis_tab = QTabWidget(self)
        # self.lt.addWidget(self.vis_tab)
        self.hilbert_table, self.hilbert_colors = create_hilbert_transform(16)

        # self.h_bgr = create_hilbert_color_pattern(8, multiplier=32, color_space=cv2.COLOR_Lab2RGB)
        # self.h_indices = hilbert_mapping_3d(8, np.zeros(shape=(8,8,8)), HilbertMode.Indices_All)
        #
        # self.h_indices = np.array(self.h_indices)
        # self.h_indices = np.array([self.h_indices[:, 0],self.h_indices[:, 1],self.h_indices[:, 2]])
        #
        # self.histogram = HistogramVis(self)
        # self.histogram.plot(8**3 * [1.0], self.h_bgr)
        # self.histogram.view.setYRange(min = 0.1, max = 1.0)
        # self.histogram.view.setXRange(min = 0, max = 255)

        # self.palette = PaletteVis(self)
        self.palette = PaletteWidget(self)
        self.lab_palette = PaletteLABWidget(self)
        self.time_palette = PaletteTimeWidget(self)
        self.hilbert_vis = HistogramVis(self)

        self.spatial_complexity_vis = LinePlot(self, x_label_format="ms")
        lt_spatial = QWidget()
        lt_spatial.setLayout(QVBoxLayout())
        lt_spatial.layout().addWidget(self.spatial_complexity_vis)
        self.spatial_complexity_param = ExpandableWidget(self, "Controls", self.spatial_complexity_vis.get_param_widget())
        lt_spatial.layout().addWidget(self.spatial_complexity_param)

        self.hilbert_param = ExpandableWidget(self, "Controls", self.hilbert_vis.get_param_widget())
        lt_hilbert = QWidget()
        lt_hilbert.setLayout(QVBoxLayout())
        lt_hilbert.layout().addWidget(self.hilbert_vis)
        lt_hilbert.layout().addWidget(self.hilbert_param)


        #
        # self.lt.addWidget(self.palette)
        if self.use_tab_mode:
            self.vis_tab.addTab(self.palette, "Tree-Palette")
            self.vis_tab.addTab(self.lab_palette, "LAB-Palette")
            self.vis_tab.addTab(self.time_palette, "Time Palette")
            self.vis_tab.addTab(lt_hilbert, "Color Histogram")
            self.vis_tab.addTab(lt_spatial, "Spatial Complexity")
            self.vis_tab.currentChanged.connect(self.on_tab_changed)
        else:
            t1 = ESimpleDockWidget(self.inner,  self.palette, "Palette")
            t2 = ESimpleDockWidget(self.inner, self.lab_palette, "Space Palette")
            t3 = ESimpleDockWidget(self.inner, self.time_palette, "Time Palette")
            t3.visibilityChanged.connect(self.on_tab_changed)
            t4 = ESimpleDockWidget(self.inner, lt_hilbert, "Histogram")
            t5 = ESimpleDockWidget(self.inner, lt_spatial, "Spatial Frequency")

            self.a_palette.triggered.connect(t1.show)
            self.a_palette_ab.triggered.connect(t2.show)
            self.a_palette_dt.triggered.connect(t3.show)
            self.a_hist.triggered.connect(t4.show)
            self.a_spatial.triggered.connect(t5.show)

            self.inner.addDockWidget(Qt.LeftDockWidgetArea, t1, Qt.Horizontal)
            self.inner.addDockWidget(Qt.RightDockWidgetArea, t2, Qt.Horizontal)
            self.inner.addDockWidget(Qt.BottomDockWidgetArea, t3, Qt.Horizontal)
            self.inner.addDockWidget(Qt.RightDockWidgetArea, t4, Qt.Horizontal)
            self.inner.addDockWidget(Qt.RightDockWidgetArea, t5, Qt.Horizontal)

            t3.hide()
            t4.hide()
            t5.hide()


        self.main_window.onTimeStep.connect(self.on_time_step)
        # self.vis_tab.addTab(self.histogram, "Histogram")

    @pyqtSlot(object, int)
    def update_timestep(self, data, time_ms):
        if data is not None:
            try:
                t = time.time()


                # print(self.palette.isVisible(), self.lab_palette.isVisible(), self.hilbert_vis.isVisible(),
                #       self.spatial_complexity_vis.isVisible())

                # print("Spacial Complexity", t - time.time())
                t = time.time()
                if self.palette.isVisible():
                    self.palette.set_palette(data['palette'])
                    self.palette.draw_palette()
                # print("Palette", time.time() - t )
                t = time.time()
                if self.lab_palette.isVisible():
                    self.lab_palette.set_palette(data['palette'])
                    self.lab_palette.draw_palette()
                # print("Palette AB", time.time() - t)
                t = time.time()
                if self.hilbert_vis.isVisible():
                    self.hilbert_vis.plot_color_histogram(data['histogram'])
                # print("Hilbert",  time.time() - t)
                if self.spatial_complexity_vis.isVisible():
                    self.spatial_complexity_vis.clear_view()
                    colors = [
                        QColor(200, 61, 50),
                        QColor(98, 161, 169),
                        QColor(153, 175, 93),
                        QColor(230, 183, 64)
                    ]
                    cidx = data['current_idx']
                    for i, key in enumerate(data['spatial'].keys()):
                        xs = data['times']
                        ys = data['spatial'][key]
                        self.spatial_complexity_vis.plot(xs[:cidx], ys[:cidx, 0], colors[i],
                                                         line_name=key,
                                                         force_xmax=self.main_window.project.movie_descriptor.duration)
            except Exception as e:
                raise e
                print("Exception in ColormetryWidget.update_timestep()", str(e))

    @pyqtSlot(int)
    def on_time_step(self, time_ms):
        self.spatial_complexity_vis.set_time_indicator(time_ms)

    def on_tab_changed(self):
        if self.project() is None:
            return

        if self.palette.isVisible():
            self.palette.draw_palette()
        if self.lab_palette.isVisible():
            self.lab_palette.draw_palette()
        if self.time_palette.isVisible():
            ret, col = self.project().get_colormetry()
            if ret:
                self.time_palette.set_palette(*col.get_time_palette())

    def plot_time_palette(self, data):
        try:
            self.time_palette.set_palette(data[0], data[1])
            self.time_palette.draw_palette()
        except:
            print("Exception in ColorimetryLiveWidget::plot_time_palette()")
            pass

    def resizeEvent(self, *args, **kwargs):
        super(ColorimetryLiveWidget, self).resizeEvent(*args, **kwargs)
        self.on_tab_changed()

    def on_selected(self, sender, selected):
        pass

    def on_closed(self):
        self.palette.clear_view()
        self.lab_palette.clear_view()

    def on_changed(self, project, item):
        pass

    def on_loaded(self, project):
        pass

    def get_settings(self):
        return dict(
            palette_sorting = self.palette.cb_sorting.currentText(),
            palette_mode = self.palette.cb_mode.currentText(),
            palette_index = self.palette.slider.value(),
            palette_ab_index = self.lab_palette.slider.value(),
            palette_ab_jitter = self.lab_palette.slider_jitter.value(),
            palette_ab_scale = self.lab_palette.slider_scale.value(),
            palette_ab_size = self.lab_palette.slider_size.value()
        )

    def apply_settings(self, settings):
        self.palette.cb_sorting.setCurrentText(settings['palette_sorting'])
        self.palette.cb_mode.setCurrentText(settings['palette_mode'])
        self.palette.slider.setValue(settings['palette_index'])
        self.lab_palette.slider.setValue(settings['palette_ab_index'])
        self.lab_palette.slider_jitter.setValue(settings['palette_ab_jitter'])
        self.lab_palette.slider_scale.setValue(settings['palette_ab_scale'])
        self.lab_palette.slider_size.setValue(settings['palette_ab_size'])