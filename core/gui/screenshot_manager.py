import os
import cv2
import numpy as np

from PyQt5 import QtCore, QtGui, uic, QtWidgets
from PyQt5.QtCore import Qt, QPoint, QRectF
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtWidgets import *

from collections import namedtuple

from core.data.computation import *
from core.data.containers import Screenshot, ElanExtensionProject
from core.data.exporters import ScreenshotsExporter
from core.data.interfaces import IProjectChangeNotify
from core.gui.Dialogs.screenshot_exporter_dialog import DialogScreenshotExporter
from core.gui.ewidgetbase import EDockWidget, EToolBar

SCALING_MODE_NONE = 0
SCALING_MODE_WIDTH = 1
SCALING_MODE_HEIGHT = 2
SCALING_MODE_BOTH = 3

class ScreenshotsToolbar(EToolBar):
    def __init__(self, main_window, screenshot_manager):
        super(ScreenshotsToolbar, self).__init__(main_window, "Screenshots Toolbar")
        self.setWindowTitle("Screenshots")

        self.manager = screenshot_manager
        self.action_export = self.addAction(create_icon("qt_ui/icons/icon_export_screenshot.png"), "")
        self.toggle_annotation = self.addAction(create_icon("qt_ui/icons/icon_toggle_annotations.png"), "")
        self.action_export.triggered.connect(self.on_export)
        self.toggle_annotation.triggered.connect(self.on_toggle_annotations)
        self.show()

    def on_export(self):
        self.exporter_dialog = DialogScreenshotExporter( self.main_window, self.manager)
        self.exporter_dialog.show()

    def on_toggle_annotations(self):
        self.manager.toggle_annotations()


class SMSegment(object):
    def __init__(self, name, segm_id, segm_start):
        self.segm_name = name
        self.segm_id = segm_id
        self.segm_start = segm_start
        self.segm_images = []


class ScreenshotsManagerDockWidget(EDockWidget):
    def __init__(self, main_window):
        super(ScreenshotsManagerDockWidget, self).__init__(main_window, limit_size=False)
        self.setWindowTitle("Screenshot Manager")
        self.m_display = self.inner.menuBar().addMenu("Display")
        self.a_static = self.m_display.addAction("Static")
        self.a_scale_width =self.m_display.addAction("Reorder by Width")

        self.a_static.triggered.connect(self.on_static)
        self.a_scale_width.triggered.connect(self.on_scale_to_width)
        self.m_display.addSeparator()
        self.a_follow_time = self.m_display.addAction(" Follow Time")
        self.a_follow_time.setCheckable(True)
        self.a_follow_time.setChecked(True)
        self.a_follow_time.triggered.connect(self.on_follow_time)

        # self.inner.addToolBar(ScreenshotsToolbar(main_window, self.main_window.screenshots_manager))

    def on_static(self):
        self.screenshot_manager.scaling_mode = SCALING_MODE_NONE

    def on_scale_to_width(self):
        self.screenshot_manager.scaling_mode = SCALING_MODE_WIDTH
        self.screenshot_manager.arrange_images()

    def on_scale_to_height(self):
        self.screenshot_manager.scaling_mode = SCALING_MODE_HEIGHT

    def on_scale_to_both(self):
        self.screenshot_manager.scaling_mode = SCALING_MODE_BOTH

    def on_follow_time(self):
        self.screenshot_manager.follow_time = self.a_follow_time.isChecked()

    def set_manager(self, screenshot_manager):
        self.setWidget(screenshot_manager)
        self.screenshot_manager = screenshot_manager


class ScreenshotsManagerWidget(QGraphicsView, IProjectChangeNotify):
    """
    Implements IProjectChangeNotify
    """
    def __init__(self,main_window, key_event_handler, parent = None):
        super(ScreenshotsManagerWidget, self).__init__(parent)

        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.setRenderHints(QtGui.QPainter.Antialiasing|QtGui.QPainter.SmoothPixmapTransform)

        self.is_hovered = False
        self.ctrl_is_pressed = False
        self.shift_is_pressed = False
        self.follow_time = False

        self.font = QFont("Consolas")
        self.font_size = 128
        self.font_size_segments = 120
        self.font.setPointSize(self.font_size)
        self.color = QColor(255,255,255)

        self.setDragMode(self.RubberBandDrag)
        self.setRubberBandSelectionMode(Qt.IntersectsItemShape)
        self.rubberband_rect = QtCore.QRect(0, 0, 0, 0)
        self.curr_scale = 1.0
        self.curr_image_scale = 1.0

        self.scaling_mode = SCALING_MODE_NONE

        self.main_window = main_window
        self.main_window.onSegmentStep.connect(self.frame_segment)

        self.scene = ScreenshotsManagerScene(self)
        self.setScene(self.scene)

        self.project = None
        self.images_plain = []
        self.images_segmentation = []
        self.captions = []
        self.selected = []
        self.selection_frames = []

        self.selected = []
        self.current_segment_frame = None

        self.x_offset = 100
        self.y_offset = 200
        self.border_width = 1500
        self.border_height = 1000
        self.segment_distance = 100
        self.img_height = 0
        self.img_width = 0

        self.n_per_row = 10

        self.n_images = 0
        self.rubberBandChanged.connect(self.rubber_band_selection)



        # SEGMENT EVALUATOR
        # self.main_window.currentSegmentChanged.connect(self.frame_segment)

    def toggle_annotations(self):
        pass

    def update_manager(self):
        """
        Recreating the Data Structures
        :return: 
        """

        if self.project is None:
            return

        self.clear_manager()

        current_segment_id = 0
        current_sm_object = None
        for s in self.project.screenshots:
            # s = Screenshot()

            # If this Screenshot belongs to a new Segment, append the last SMObject to the list
            if s.scene_id != current_segment_id:
                if current_sm_object is not None:
                    self.images_segmentation.append(current_sm_object)

                current_segment_id = s.scene_id
                segment = self.project.get_segment_of_main_segmentation(current_segment_id - 1)
                current_sm_object = SMSegment(segment.get_name(), segment.ID, segment.get_start())

            # Should we use the Annotated Screenshot?
            if s.annotation_is_visible:
                image = s.img_blend
            else:
                image = s.img_movie

            # Convert to Pixmap
            try:
                qgraph, qpixmap = numpy_to_qt_image(image)
            except Exception as e:
                print("An Error Occured, Save and Restart. An Error occured in the Screenshot")
                # self.main_window.print_message("An Error Occured, Save and Restart. An Error occured in the Screenshot "
                #                                "Manager, I suggest you restart the application" + str(e), "Orange")
                continue

            item_image = ScreenshotManagerPixmapItems(qpixmap, self, s)
            self.scene.addItem(item_image)

            self.images_plain.append(item_image)
            current_sm_object.segm_images.append(item_image)

        self.images_segmentation.append(current_sm_object)

        self.clear_selection_frames()
        self.arrange_images()

    def clear_manager(self):
        for img in self.images_plain:
            self.scene.removeItem(img)
        for cap in self.captions:
            self.scene.removeItem(cap)

        self.images_plain = []
        self.captions = []
        self.images_segmentation = []

    def arrange_images(self):
        self.clear_captions()

        y = self.border_height
        if len(self.images_plain) > 0:
            img_width = self.images_plain[0].pixmap().width()
            img_height = self.images_plain[0].pixmap().height()
            x_offset = int(img_width / 7)
            y_offset = int(img_height / 7)
            y_offset = x_offset
            caption_width = int(img_width / 1.5)


            self.scene.setSceneRect(self.sceneRect().x(), self.sceneRect().y(), self.n_per_row * (img_width + x_offset), self.sceneRect().width())
        else:
            return

        if self.scaling_mode == SCALING_MODE_WIDTH:
            viewport_size = self.mapToScene(QPoint(self.width(), self.height())) - self.mapToScene(QPoint(0, 0))
            viewport_width = viewport_size.x()
            image_scale = round(img_width / (viewport_size.x()), 4)
            self.n_per_row = np.clip(int(np.ceil(viewport_width/ (img_width + x_offset))), 1, None)

        for segm in self.images_segmentation:
            self.add_line(y)
            self.add_caption(100, y + 100, segm.segm_name)
            self.add_caption(100, y + 250, segm.segm_id)

            x_counter = 0
            x = caption_width - (x_offset + img_width)
            for i, img in enumerate(segm.segm_images):
                if x_counter == self.n_per_row - 1:
                    x = caption_width
                    x_counter = 1
                    y += (y_offset + img_height)
                else:
                    x_counter += 1
                    x += (x_offset + img_width)

                img.setPos(x, y + int(img_height/5))
                img.selection_rect = QtCore.QRect(x, y + int(img_height/5), img_width, img_height)

            y += (2 * img_height)


        self.scene.setSceneRect(self.sceneRect().x(), self.sceneRect().y(), self.n_per_row * (img_width + x_offset), y)

        # Drawing the New Selection Frames
        self.draw_selection_frames()

        self.img_height = img_height
        self.img_width = img_width

    def add_line(self, y):
        p1 = QtCore.QPointF(0, y)
        p2 = QtCore.QPointF(self.scene.sceneRect().width(), y)

        pen = QtGui.QPen()
        pen.setColor(QtGui.QColor(200, 200, 200))
        pen.setWidth(5)
        line = self.scene.addLine(QtCore.QLineF(p1, p2), pen)
        self.captions.append(line)
        return line

    def add_caption(self, x, y, text):
        caption = self.scene.addText(str(text), self.font)
        caption.setDefaultTextColor(QColor(255, 255, 255))
        caption.setPos(QtCore.QPointF(x, y))
        self.captions.append(caption)
        return caption

    def clear_selection_frames(self):
        for s in self.selection_frames:
            self.scene.removeItem(s)
        self.selection_frames = []

    def clear_captions(self):
        for cap in self.captions:
            self.scene.removeItem(cap)
        self.captions = []

    def select_image(self, images, dispatch = True):
        self.selected = images

        # Drawing the New Selection Frames
        self.draw_selection_frames()

        if dispatch:
            sel = []
            for i in self.selected:
                sel.append(i.screenshot_obj)
            self.project.set_selected(self, sel)

    def draw_selection_frames(self):
        self.clear_selection_frames()
        if len(self.selected) > 0:
            for i in self.selected:
                pen = QtGui.QPen()
                pen.setColor(QtGui.QColor(255, 160, 74))
                pen.setWidth(25)
                item = QtWidgets.QGraphicsRectItem(QtCore.QRectF(i.selection_rect))
                item.setPen(pen)
                # rect = QtCore.QRectF(i.selection_rect)
                self.selection_frames.append(item)
                self.scene.addItem(item)

    def center_images(self):
        self.fitInView(self.sceneRect(), QtCore.Qt.KeepAspectRatio)

    def frame_image(self, image):
        rect = image.sceneBoundingRect()
        self.fitInView(rect, Qt.KeepAspectRatio)
        self.curr_scale = self.sceneRect().width() / rect.width()

    def frame_segment(self, segment_index):
        if self.follow_time:
            x = self.scene.sceneRect().width()
            y = self.scene.sceneRect().height()
            width = 0
            height = 0

            # # Segments that are empty are not represented in self.images_segmentation
            # if segment_index >= len(self.images_segmentation):
            #     return

            index = 0
            for i, s in enumerate(self.images_segmentation):
                if s.segm_id == segment_index + 1:
                    index = i

            # Determining the Bounding Box
            for img in self.images_segmentation[index].segm_images:
                if img.scenePos().x() < x:
                    x = img.scenePos().x()
                if img.scenePos().y() < y:
                    y = img.scenePos().y()
                if img.scenePos().y() + img.pixmap().width() > width:
                    width = img.scenePos().x() + img.pixmap().width()
                if img.scenePos().y() + img.pixmap().height() > height:
                    height = img.scenePos().y() + img.pixmap().height()

            self.fitInView(0, y, self.sceneRect().width(), height - y, Qt.KeepAspectRatio)

            if self.current_segment_frame is not None:
                self.scene.removeItem(self.current_segment_frame)

            pen = QtGui.QPen()
            pen.setColor(QtGui.QColor(251, 95, 2, 200))
            pen.setWidth(20)
            self.current_segment_frame = self.scene.addRect(0, y-int(self.img_height/5) - 10, self.sceneRect().width(), height - y + int(self.img_height / 7) + self.img_height - 100, pen)
        else:
            if self.current_segment_frame is not None:
                self.scene.removeItem(self.current_segment_frame)
                self.current_segment_frame = None
    def on_loaded(self, project):
        self.project = project
        self.update_manager()

    def on_changed(self, project, item):
        self.update_manager()
        self.on_selected(None, project.get_selected())

    def on_selected(self, sender, selected):
        if not sender is self:
            sel = []
            for i in self.images_plain:
                    for s in selected:
                        if isinstance(s, Screenshot):
                            if i.screenshot_obj is s:
                                sel.append(i)
            self.select_image(sel, dispatch=False)

    def rubber_band_selection(self, QRect, Union, QPointF=None, QPoint=None):
        self.rubberband_rect = self.mapToScene(QRect).boundingRect()

    def export_screenshots(self, path, visibility=None, image_type=None, quality=None, naming=None, smooth=False):
        screenshots = []

        # If there are selected Screenshots, only export those,
        # Else export all
        if len(self.selected_images) == 0:
            for item in self.images_plain:
                screenshots.append(item.screenshot_obj)
            self.main_window.print_message("No Screenshots selected, exporting all Screenshots", "red")
        else:
            for item in self.selected_images:
                screenshots.append(item.screenshot_obj)

        try:
            if not os.path.isdir(path):
                os.mkdir(path)

            exporter = ScreenshotsExporter(self.main_window.settings, self.main_window.project, naming)
            exporter.export(screenshots, path, visibility, image_type, quality, smooth)
        except OSError as e:
            QMessageBox.warning(self.main_window, "Failed to Create Directory", "Please choose a valid path\n\n" + path)
            self.main_window.print_message("Failed to Create Directory: " + path, "Red")

    def wheelEvent(self, event):
        if self.ctrl_is_pressed:
            self.setTransformationAnchor(QtWidgets.QGraphicsView.NoAnchor)
            self.setResizeAnchor(QtWidgets.QGraphicsView.NoAnchor)

            old_pos = self.mapToScene(event.pos())
            if self.main_window.is_darwin:
                h_factor = 1.1
                l_factor = 0.9
            else:
                h_factor = 1.1
                l_factor = 0.9

            viewport_size = self.mapToScene(QPoint(self.width(), self.height())) - self.mapToScene(QPoint(0, 0))
            self.curr_scale = round(self.img_width / (viewport_size.x()), 4)

            if event.angleDelta().y() > 0.0 and self.curr_scale < 100:
                self.scale(h_factor, h_factor)
                self.curr_scale *= h_factor

            elif event.angleDelta().y() < 0.0 and self.curr_scale > 0.01:
                self.curr_scale *= l_factor
                self.scale(l_factor, l_factor)

            cursor_pos = self.mapToScene(event.pos()) - old_pos

            if self.scaling_mode == SCALING_MODE_WIDTH:
                self.arrange_images()
            self.translate(cursor_pos.x(), cursor_pos.y())

        else:
            super(ScreenshotsManagerWidget, self).wheelEvent(event)
            # self.verticalScrollBar().setValue(self.verticalScrollBar().value() - (500 * (float(event.angleDelta().y()) / 360)))

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Control:
            self.viewport().setCursor(QtGui.QCursor(QtCore.Qt.UpArrowCursor))
            self.ctrl_is_pressed = True
        elif event.key() == QtCore.Qt.Key_Shift:
            self.shift_is_pressed = True

    def keyReleaseEvent(self, event):
        if event.key() == QtCore.Qt.Key_Control:
            self.viewport().setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
            self.ctrl_is_pressed = False
        elif event.key() == QtCore.Qt.Key_Shift:
            self.shift_is_pressed = False

    def mouseReleaseEvent(self, QMouseEvent):
        selected = []
        if self.rubberband_rect.width() > 20 and self.rubberband_rect.height() > 20:
            for i in self.images_plain:
                i_rect = QtCore.QRectF(i.pos().x(), i.pos().y(),i.boundingRect().width(), i.boundingRect().height())
                if self.rubberband_rect.intersects(QtCore.QRectF(i_rect)):
                    selected.append(i)
            self.select_image(selected)

            self.rubberband_rect = QtCore.QRectF(0.0, 0.0, 0.0, 0.0)
            super(ScreenshotsManagerWidget, self).mouseReleaseEvent(QMouseEvent)

    def mouseDoubleClickEvent(self, *args, **kwargs):
        if len(self.selected) > 0:
            self.frame_image(self.selected[0])
        else:
            self.center_images()


class ScreenshotsManagerScene(QGraphicsScene):
    def __init__(self, graphicsViewer):
        super(ScreenshotsManagerScene, self).__init__()
        self.graphicsViewer = graphicsViewer


class ScreenshotManagerPixmapItems(QGraphicsPixmapItem):
    def __init__(self, qpixmap, manager, obj, selection_rect = QtCore.QRect(0,0,0,0)):
        super(ScreenshotManagerPixmapItems, self).__init__(qpixmap)
        self.manager = manager
        self.screenshot_obj = obj
        self.selection_rect = selection_rect

    def mousePressEvent(self, *args, **kwargs):
        self.setSelected(True)

        if self.manager.shift_is_pressed:
            selected = self.manager.selected
            if self in selected:
                selected.remove(self)
            else:
                selected.append(self)
        else:
            selected = [self]

        self.manager.select_image(selected)
        # self.manager.main_window.screenshots_editor.set_current_screenshot(self.screenshot_obj)

