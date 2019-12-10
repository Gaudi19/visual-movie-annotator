from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from core.data.interfaces import *
from core.gui.ewidgetbase import *
from core.analysis.informative import select_rows
from core.data.computation import ms_to_frames
from core.container.project import *
from core.concurrent.auto_segmentation import ApplySegmentationWindow

def auto_screenshot(project:VIANProject, method, distribution, n, segmentation, hdf5_manager):
        frame_ms = []

        if method == "Uniform Distribution":
            if distribution == "N - Per Segment":
                for s in segmentation.segments:
                    delta = (s.get_end() - s.get_start()) / n
                    k = s.get_start()
                    while k < s.get_end():
                        frame_ms.append(k)
                        k += delta

            elif distribution == "N - Complete":
                delta = project.movie_descriptor.duration / n
                k = 0
                while k < project.movie_descriptor.duration:
                    frame_ms.append(k)
                    k += delta

            elif distribution == "Every N-th Frame":
                k = 0
                while k < project.movie_descriptor.duration:
                    frame_ms.append(k)
                    k += frame2ms(n, project.movie_descriptor.fps)

        elif method == "Most Informative":
            for s in segmentation.segments:
                idx_start = int(ms_to_frames(s.get_start(), project.movie_descriptor.fps) / project.colormetry_analysis.resolution)
                idx_end = int(ms_to_frames(s.get_end(), project.movie_descriptor.fps) / project.colormetry_analysis.resolution)
                indices = range(idx_start, idx_end, 1)
                hists = hdf5_manager.col_histograms()[indices]
                hists = np.reshape(hists, newshape=(hists.shape[0], hists.shape[1]* hists.shape[2] * hists.shape[3]))
                hists /= np.sqrt(np.sum(hists ** 2, axis=1, keepdims=True))
                result = select_rows(hists, np.clip(n, 1, hists.shape[0]))

                frame_ms.extend([frame2ms((f + idx_start) * project.colormetry_analysis.resolution, project.movie_descriptor.fps) for f in result])

        frame_pos = []
        for f in frame_ms:
            frame_pos.append(ms_to_frames(f, project.movie_descriptor.fps))
        return frame_pos


class DialogAutoScreenshot(EDialogWidget):
    def __init__(self, parent, project):
        super(DialogAutoScreenshot, self).__init__(parent, parent, "https://www.vian.app/static/manual/step_by_step/segmentation/auto_segmentation.html")
        path = os.path.abspath("qt_ui/DialogAutoScreenshot.ui")
        uic.loadUi(path, self)

        self.project = project
        self.segmentations = []
        for s in self.project.segmentation:
            self.comboBox_Target.addItem(s.get_name())
            self.segmentations.append(s)

        # If there are no segmentations, remove this option
        if len(self.segmentations) == 0:
            self.comboBox_Target.setEnabled(False)
            self.comboBox_Distribution.removeItem(0)

        self.btn_Run.clicked.connect(self.on_ok)
        self.btn_Help.clicked.connect(self.on_help)
        self.btn_Cancel.clicked.connect(self.close)

    def on_ok(self):
        segmentation = None
        # if self.comboBox_Distribution.currentText() == "N - Per Segment":
        segmentation = self.segmentations[self.comboBox_Target.currentIndex()]
        job = AutoScreenshotJob(None, self.comboBox_Method.currentText(),
                          self.comboBox_Distribution.currentText(),
                            self.spinBox_N.value(), segmentation, self.project.hdf5_manager)
        self.main_window.run_job_concurrent(job)
        self.close()


class AutoScreenshotJob(IConcurrentJob):
    def __init__(self, args, method, distribution, n, segmentation, hdf5_manager):
        super(AutoScreenshotJob, self).__init__(args)
        self.method = method
        self.distribution = distribution
        self.n = n
        self.segmentation = segmentation
        self.hdf5_manager = hdf5_manager

    def prepare(self, project):
        self.args = [project.movie_descriptor.movie_path,
                     project]

    def run_concurrent(self, args, sign_progress):
        movie_path = args[0]
        project = args[1]
        frame_pos = auto_screenshot(project, self.method, self.distribution, self.n, self.segmentation, self.hdf5_manager)
        # frame_pos = args[1]

        cap = cv2.VideoCapture(movie_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        result = []

        for i, p in enumerate(frame_pos):
            p += 1
            sign_progress(i / len(frame_pos))
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(p))
            ret, frame = cap.read()
            if ret:
                result.append(dict(
                    name="Auto_Scr_" + str(i),
                    img = frame,
                    frame_pos = p,
                    ms_pos = frame2ms(p, fps)
                    )
                )
        return result

    def modify_project(self, project:VIANProject, result, sign_progress=None, main_window = None):
        if result is not None:
            scr_group = project.add_screenshot_group("Manual")
            scr_group.add_screenshots(project.screenshots)

            project.inhibit_dispatch = True

            shots = []
            for s in result:
                n = Screenshot(s['name'], image=s['img'], timestamp=s['ms_pos'], frame_pos=s['frame_pos'])
                project.add_screenshot(n)
                shots.append(n)
            project.inhibit_dispatch = False
            scr_group = project.add_screenshot_group("Automatic")
            scr_group.add_screenshots(shots)
            project.dispatch_changed()

    def get_widget(self, parent, result):
        return ApplySegmentationWindow(parent, result[0], result[1], result[2], result[3], result[4], result[5])

