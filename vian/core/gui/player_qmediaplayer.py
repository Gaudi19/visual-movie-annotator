import sys, os
from functools import partial
import cv2
from PyQt6 import QtCore, QtWidgets
from PyQt6.QtWidgets import QFrame, QMenu
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import *
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

from vian.core.gui.ewidgetbase import EDockWidget
from vian.core.data.computation import is_vian_light
from vian.core.data.interfaces import IProjectChangeNotify
from vian.core.data.log import log_error, log_info, log_debug

class PlayerDockWidget(EDockWidget):
    onSpacialFrequencyChanged = pyqtSignal(bool, str)
    onFaceRecognitionChanged = pyqtSignal(bool)
    onCurrentSpatialDatasetSelected = pyqtSignal(str)

    def __init__(self, main_window):
        super(PlayerDockWidget, self).__init__(main_window=main_window, limit_size=False)
        self.setWindowTitle("Player")
        self.video_player = None
        self.setMinimumWidth(100)
        self.setMinimumHeight(100)

        if is_vian_light():
            self.inner.menuBar().hide()

        self.vis_menu = self.inner.menuBar().addMenu("Visualization")
        self.spatial_frequency_menu = QMenu("Spatial Frequency")
        self.vis_menu.addMenu(self.spatial_frequency_menu)

        self.menu_spatial = self.vis_menu.addMenu("Spatial Datasets")

        self.a_spacial_frequency = self.spatial_frequency_menu.addAction("Edge Mean")
        self.a_spacial_frequency.setCheckable(True)
        self.a_spacial_frequency.triggered.connect(partial(self.on_spacial_frequency_changed, "edge-mean"))

        self.a_spacial_frequency_col_var = self.spatial_frequency_menu.addAction("Color Variance")
        self.a_spacial_frequency_col_var.setCheckable(True)
        self.a_spacial_frequency_col_var.triggered.connect(partial(self.on_spacial_frequency_changed, "color-var"))

        self.a_spacial_frequency_hue_var = self.spatial_frequency_menu.addAction("Hue Variance")
        self.a_spacial_frequency_hue_var.setCheckable(True)
        self.a_spacial_frequency_hue_var.triggered.connect(partial(self.on_spacial_frequency_changed, "hue-var"))

        self.a_spacial_frequency_lum_var = self.spatial_frequency_menu.addAction("Luminance Variance")
        self.a_spacial_frequency_lum_var.setCheckable(True)
        self.a_spacial_frequency_lum_var.triggered.connect(partial(self.on_spacial_frequency_changed, "luminance-var"))

        self.setFeatures(EDockWidget.DockWidgetFeature.NoDockWidgetFeatures | EDockWidget.DockWidgetFeature.DockWidgetClosable)

    @pyqtSlot(object)
    def on_spatial_datasets_changed(self, datasets):
        self.menu_spatial.clear()
        a = self.menu_spatial.addAction("None")
        a.triggered.connect(partial(self.onCurrentSpatialDatasetSelected.emit, "None"))

        for d in datasets:
            a = self.menu_spatial.addAction(d)
            a.triggered.connect(partial(self.onCurrentSpatialDatasetSelected.emit, d))

    def on_spacial_frequency_changed(self, method):
        state = self.sender().isChecked()
        self.a_spacial_frequency.setChecked(False)
        self.a_spacial_frequency_col_var.setChecked(False)
        self.a_spacial_frequency_lum_var.setChecked(False)
        self.a_spacial_frequency_hue_var.setChecked(False)
        self.sender().setChecked(True)
        self.onSpacialFrequencyChanged.emit(state, method)


    def on_face_rec_changed(self):
        self.onFaceRecognitionChanged.emit(self.a_face_rec.isChecked())

    def set_player(self, video_player):
        self.setWidget(video_player)
        self.video_player = video_player
        self.video_player.show()

    def resizeEvent(self, *args, **kwargs):
        super(PlayerDockWidget, self).resizeEvent(*args, **kwargs)
        self.main_window.drawing_overlay.update()

    # def dockLocationChanged(self, Qt_DockWidgetArea):
    #     super(PlayerDockWidget, self).dockLocationChanged(Qt_DockWidgetArea)
    #     self.main_window.drawing_overlay.raise_()


class VideoPlayer(QtWidgets.QFrame, IProjectChangeNotify):
    """
    Implements IProjectChangeNotify
    """
    #SIGNALS
    movieOpened = pyqtSignal()
    started = pyqtSignal()
    stopped = pyqtSignal()
    timeChanged = pyqtSignal(int)

    def __init__(self, main_window):
        super(VideoPlayer, self).__init__(main_window)
        self.main_window = main_window
        self.media_descriptor = None
        # These Variables are initialized to be sure they exist in Classes inheriting from VideoPlayer
        self.movie_path = ""
        self.offset = 0
        self.start_time = 0
        self.stop_time = 0
        self.duration = 100
        self.orig_aspect_ratio = 0
        self.aspect_ratio = 0
        self.movie_size = (720,480)
        self.millis_per_sample = 0
        self.fps = 24
        self.mute = False

        self.use_user_fps = False
        self.user_fps = 29.9999999


        self.videoframe = QFrame(self)

    # *** EXTENSION METHODS *** #
    def get_frame(self):
        log_debug(NotImplementedError("Method <get_frame> not implemented"))

    def init_ui(self):
        log_debug(NotImplementedError("Method <init_ui> not implemented"))

    def get_size(self):
        log_debug(NotImplementedError("Method <get_size> not implemented"))

    def set_initial_values(self):
        log_debug(NotImplementedError("Method <set_initial_values> not implemented"))

    def play_pause(self):
        log_debug(NotImplementedError("Method <play_pause> not implemented"))
    # *** ELAN INTERFACE METHODS *** #

    def open_movie(self, path):
        log_debug(NotImplementedError("Method <open_movie> not implemented"))

    def play(self):
        log_debug(NotImplementedError("Method <play> not implemented"))

    def pause(self):
        log_debug(NotImplementedError("Method <pause> not implemented"))

    def stop(self):
        log_debug(NotImplementedError("Method <stop> not implemented"))

    def is_playing(self):
        """
        :return: bool
        """
        log_debug(NotImplementedError("Method <is_playing> not implemented"))

    def play_interval(self, start_ms, stop_ms):
        log_debug(NotImplementedError("Method <play_interval> not implemented"))

    def set_offset(self):
        """
        
        :return: Long
        """
        log_debug(NotImplementedError("Method <set_offset> not implemented"))

    def get_offset(self):
        log_debug(NotImplementedError("Method <get_offset> not implemented"))

    def set_stop_time(self, time):
        log_debug(NotImplementedError("Method <set_stop_time> not implemented"))

    def next_frame(self):
        log_debug(NotImplementedError("Method <next_frame> not implemented"))

    def previous_frame(self):
        log_debug(NotImplementedError("Method <previous_frame> not implemented"))

    def set_frame_steps_to_frame_begin(self, bool):
        log_debug(NotImplementedError("Method <set_frame_steps_to_frame_begin> not implemented"))

    def set_media_time(self, time):
        log_debug(NotImplementedError("Method <set_media_time> not implemented"))

    def get_media_time(self):
        log_debug(NotImplementedError("Method <get_media_time> not implemented"))

    def set_rate(self, rate):
        log_debug(NotImplementedError("Method <set_rate> not implemented"))

    def get_rate(self):
        log_debug(NotImplementedError("Method <get_rate> not implemented"))

    def is_frame_rate_auto_detected(self):
        log_debug(NotImplementedError("Method <is_frame_rate_auto_detected> not implemented"))

    def get_media_duration(self):
        log_debug(NotImplementedError("Method <get_media_duration> not implemented"))

    def set_volume(self, volume):
        log_debug(NotImplementedError("Method <set_volume> not implemented"))

    def get_volume(self):
        log_debug(NotImplementedError("Method <get_volume> not implemented"))

    def set_sub_volume(self, volume):
        log_debug(NotImplementedError("Method <set_sub_volume> not implemented"))

    def get_sub_volume(self):
        log_debug(NotImplementedError("Method <get_sub_colume> not implemented"))

    def set_mute(self, mute):
        log_debug(NotImplementedError("Method <set_mute> not implemented"))

    def get_mute(self):
        log_debug(NotImplementedError("Method <get_mute> not implemented"))

    def get_source_width(self):
        log_debug(NotImplementedError("Method <get_source_width> not implemented"))

    def get_source_height(self):
        log_debug(NotImplementedError("Method <get_source_height> not implemented"))

    def get_aspect_ratio(self):
        log_debug(NotImplementedError("Method <get_aspect_ratio> not implemented"))

    def set_aspect_ratio(self, ratio):
        log_debug(NotImplementedError("Method <set_aspect_ratio> not implemented"))

    def get_miliseconds_per_sample(self):
        log_debug(NotImplementedError("Method <get_miliseconds_per_sample> not implemented"))

    def set_miliseconds_per_sample(self, ms):
        log_debug(NotImplementedError("Method <set_miliseconds_per_sample> not implemented"))

    def on_loaded(self, project):
        pass

    def on_changed(self, project, item):
        pass


class Player_QMediaPlayer(VideoPlayer):
    def __init__(self, main_window):
        super(Player_QMediaPlayer, self).__init__(main_window)

        self.media_player = QMediaPlayer()
        self.video = QVideoWidget()
        self.media_player.setVideoOutput(self.video)
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)

        self.media_player.positionChanged.connect(self.positionChanged)
        self.media_player.playbackStateChanged.connect(self.playbackStateChanged)
        self.media_player.mediaStatusChanged.connect(self.mediaChanged)

        self.time_update_interval = 100
        self.update_timer = QtCore.QTimer()
        self.update_timer.setInterval(self.time_update_interval)
        self.update_timer.timeout.connect(self.signal_timestep_update)

        self.vboxlayout = QtWidgets.QVBoxLayout()
        self.setLayout(self.vboxlayout)
        self.vboxlayout.addWidget(self.video)


    def mediaChanged(self):
        if self.media_player.mediaStatus() is QMediaPlayer.MediaStatus.EndOfMedia:
            self.media_player.setPosition(0)

        if self.media_player.mediaStatus() is QMediaPlayer.MediaStatus.BufferedMedia or \
                self.media_player.mediaStatus() is QMediaPlayer.MediaStatus.BufferingMedia:
            self.set_initial_values()

    def positionChanged(self):
        self.timeChanged.emit(self.media_player.position())

    def signal_timestep_update(self):
        self.timeChanged.emit(self.media_player.position())

    def playbackStateChanged(self):
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState and not self.update_timer.isActive():
            self.update_timer.start()
        elif self.update_timer.isActive():
            self.update_timer.stop()
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.StoppedState:
            self.stopped.emit()

    # *** EXTENSION METHODS *** #
    def release_player(self):
        if self.media_player is not None:
            self.media_player.setSource(QUrl("none")) #remove moviefile
            self.stop()
            self.videoframe.hide()

    def get_frame(self):
        # fps = self.media_player.get_fps()
        pos = float(self.get_media_time()) / 1000 * self.fps
        vid = cv2.VideoCapture(self.movie_path)
        vid.set(cv2.CAP_PROP_POS_FRAMES, pos)
        ret, frame = vid.read()

        return frame

    def get_size(self):
        if self.media_player is not None:
            return self.media_player.video_get_size()
        else:
            return [1,1]

    def set_initial_values(self):
        self.offset = 0
        self.start_time = 0
        self.stop_time = self.media_player.duration()
        self.duration = self.stop_time
        self.millis_per_sample = 40

        capture = cv2.VideoCapture(self.movie_path)
        self.fps = capture.get(cv2.CAP_PROP_FPS)
        self.movie_size = (capture.get(cv2.CAP_PROP_FRAME_WIDTH), capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.media_descriptor.set_duration(self.duration)
        self.user_fps = self.fps

    def get_subtitles(self):
        subs = self.media_player.subtitleTracks()
        return subs

    def set_subtitle(self, index):
        self.media_player.setActiveSubtitleTrack(index)

    def open_movie(self, path, from_server = False):
        # create the media

        self.movie_path = path
        self.media_player.setSource(QUrl.fromLocalFile(self.movie_path))


        if from_server:
            self.new_movie_loaded = True

        self.set_media_time(0)

        log_info("Opened Movie", self.movie_path)
        self.movieOpened.emit()
        self.resize(self.size() + QtCore.QSize(1,1))

    def play_pause(self):
        if not self.is_playing():
            self.play()
        else:
            self.pause()
        return self.is_playing()

    def play(self):
        if self.media_player is None:
            return
        self.media_player.play()
        self.started.emit()

    def pause(self):
        if self.media_player is None:
            return
        self.media_player.pause()
        self.stopped.emit()

    def stop(self):
        if self.media_player is None:
            return
        self.media_player.stop()
        self.stopped.emit()

    def is_playing(self):
        """
        :return: bool
        """
        return self.media_player.playbackState() == self.media_player.PlaybackState.PlayingState

    def play_interval(self, start_ms, stop_ms):
        log_debug(NotImplementedError("Method <play_interval> not implemented"))

    def set_offset(self):
        """

        :return: Long
        """
        log_debug(NotImplementedError("Method <set_offset> not implemented"))

    def get_offset(self):
        log_debug(NotImplementedError("Method <get_offset> not implemented"))

    def set_stop_time(self, time):
        log_debug(NotImplementedError("Method <set_stop_time> not implemented"))

    def next_frame(self):
        return
        if self.media_player is None:
            return
        self.media_player.next_frame()

    def previous_frame(self):
        pass

    def set_frame_steps_to_frame_begin(self, bool):
        log_debug(NotImplementedError("Method <set_frame_steps_to_frame_begin> not implemented"))

    def set_media_time(self, time):
        if time > self.duration - 1:
            time = self.duration - 1
        if self.media_player is None:
            return

        self.media_player.setPosition(int(time))
        self.timeChanged.emit(time)

        self.last_set_frame = time

    def get_media_time(self):
        if self.media_player is None:
            return 0

        return self.media_player.position()

    def set_rate(self, rate):
        if self.media_player is None:
            return
        self.media_player.setPlaybackRate(float(rate))

    def get_rate(self):
        if self.media_player is None:
            return 1.0
        return self.media_player.playbackRate()

    def is_frame_rate_auto_detected(self):
        return
        if self.get_rate() != 0.0:
            return True
        return False

    def get_media_duration(self):
        return
        if self.media_player is None:
            return 0
        return self.media.get_duration()

    def set_volume(self, volume):
        if self.audio_output is None:
            return
        self.audio_output.setVolume(volume/100.0)

    def get_volume(self):
        if self.audio_output is None:
            return 0
        return self.audio_output.getVolume()*100

    def set_sub_volume(self, volume):
        return
        if self.media_player is None:
            return
        return self.media_player.audio_set_volume(volume)

    def get_sub_volume(self):
        return
        return self.get_volume()

    def set_mute(self, mute):
        if self.audio_output is None:
            return
        self.audio_output.setMuted(bool(mute))

    def get_mute(self):
        if self.audio_output is None:
            return 0
        return self.audio_output.isMuted()

    def get_source_width(self):
        return
        if self.media_player is None:
            return 0
        return self.media_player.video_get_size()[0]

    def get_source_height(self):
        return
        if self.media_player is None:
            return 0
        return self.media_player.video_get_size()[1]

    def get_aspect_ratio(self):
        log_debug(NotImplementedError("Method <get_aspect_ratio> not implemented"))
        return
        '''
        if self.media_player is None:
            return 4/3

        t = self.media_player.video_get_aspect_ratio()
        if t is None:
            return float(4)/3
        return t
        '''

    def set_aspect_ratio(self, ratio):
        log_debug(NotImplementedError("Method <set_aspect_ratio> not implemented"))

    def get_miliseconds_per_sample(self):
        return 0

    def set_miliseconds_per_sample(self, ms):
        log_debug(NotImplementedError("Method <set_miliseconds_per_sample> not implemented"))

    def get_fps(self):
        if self.use_user_fps:
            return self.user_fps
        else:
            return self.fps

    def on_loaded(self, project):
        path = project.movie_descriptor.get_movie_path()
        self.media_descriptor = project.movie_descriptor

        if os.path.isfile(path):
            self.open_movie(path)
        else:
            raise FileNotFoundError("No Movie Selected")

    def on_changed(self, project, item):
        pass

    def get_frame_pos_by_time(self, time):
        fps = self.get_fps()
        # pos = round(round(float(time) / 1000, 0) * fps, 0)
        pos = round(float(time) * fps / 1000, 0)
        return int(pos)

    def frame_step(self, backward = False):
        if backward:
            self.set_media_time(self.media_player.position() - (1000 / self.fps))
        else:
            self.set_media_time(self.media_player.position() + (1000 / self.fps))

    def on_closed(self):
        self.release_player()


    def on_selected(self,sender, selected):
        pass

#endregion
