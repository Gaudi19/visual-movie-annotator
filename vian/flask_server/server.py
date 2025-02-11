import os
import sys
import cv2
from functools import partial
import json
import platform
import requests
import webbrowser

import numpy as np

from PyQt6.QtCore import QThread, QObject, pyqtSlot, pyqtSignal, QUrl
from PyQt6.QtWidgets import QLabel
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings, QWebEngineProfile, QWebEnginePage
from PyQt6 import QtGui
from flask import Flask, render_template, send_file, url_for, jsonify, request, make_response

from vian.core.data.interfaces import IAnalysisJob
from vian.core.data.log import log_error, log_info
from vian.core.gui.ewidgetbase import EDockWidget
from vian.core.container.project import VIANProject, Screenshot, Segment
from vian.core.analysis.analysis_import import ColorFeatureAnalysis, ColorPaletteAnalysis, get_palette_at_merge_depth
from vian.core.data.computation import lab_to_lch, lab_to_sat, ms2datetime

app = Flask(__name__)


if getattr(sys, 'frozen', False):
    app.root_path = os.path.dirname(sys.executable)
elif __file__:
    app.root_path = os.path.dirname(__file__)

# app.root_path = os.path.split(__file__)[0]
log_info("FLASK ROOT", app.root_path)
# app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

VIAN_PORT = 5352

import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

import mimetypes
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('application/json', '.json')

from threading import Lock
UPDATE_LOCK = Lock()


class ScreenshotData:
    def __init__(self):
        self.a = []
        self.b = []
        self.urls = []
        self.saturation = []
        self.luminance = []
        self.chroma = []
        self.hue = []
        self.time = []
        self.uuids = []

        self.palettes = []

        self.selected_but_not_analyzed_uuids_ColorFeatureAnalysis = []
        self.selected_but_not_analyzed_uuids_ColorPaletteAnalysis = []
        self.segment_starts = []
        self.segment_ends = []


class ServerData:
    def __init__(self):
        self.project = None #type: VIANProject

        self._recompute_screenshot_cache = False
        self._screenshot_cache = dict(revision = 0, data=ScreenshotData())

        self._project_closed = False
        self.selected_uuids = None
        self.settings = None

    def get_screenshot_data(self, revision = 0):
        if self._recompute_screenshot_cache:
            self._recompute_screenshot_cache = False
            self.update_screenshot_data()
            self._screenshot_cache['revision'] += 1

        if revision != self._screenshot_cache['revision']:
            return dict(update=True,
                        revision = self._screenshot_cache['revision'],
                        data=self._screenshot_cache['data'].__dict__)
        else:
            return dict(update=False,
                        revision = self._screenshot_cache['revision'],
                        data=dict())

    def update_screenshot_data(self):
        a = []
        b = []
        chroma = []
        luminance = []
        saturation = []
        time = []
        hue = []

        palettes = []

        uuids = []

        segment_starts = []
        segment_ends = []
        segment_ids = []

        selected_but_not_analyzed_uuids_ColorFeatureAnalysis = []
        selected_but_not_analyzed_uuids_ColorPaletteAnalysis = []
        #print("selected screenshots", self.selected_uuids)

        for i, s in enumerate(self.project.screenshots):
            if self.selected_uuids is not None and s.unique_id not in self.selected_uuids:
                continue

            t = s.get_connected_analysis(ColorFeatureAnalysis)
            if len(t) > 0:
                try:
                    arr = t[0].get_adata()['color_lab']
                except Exception as e:
                    log_error(e)
                    continue
                d = arr.tolist()
                a.append(d[1])
                b.append(d[2])
                uuids.append(s.unique_id)
                time.append(ms2datetime(s.get_start()))
                lch = lab_to_lch(arr, human_readable=True)
                luminance.append(float(arr[0]))
                chroma.append(float(lch[1]))
                hue.append(float(lch[2]))
                saturation.append(float(lab_to_sat(arr)))
            else:
                selected_but_not_analyzed_uuids_ColorFeatureAnalysis.append(s.unique_id)

            t2 = s.get_connected_analysis(ColorPaletteAnalysis)
            if len(t2) > 0:
                try:
                    arr = t2[0].get_adata()
                except Exception as e:
                    log_error(e)
                    continue
                pal = get_palette_at_merge_depth(arr, depth=15)
                if pal is not None:
                    palettes.extend(pal)
            else:
                selected_but_not_analyzed_uuids_ColorPaletteAnalysis.append(s.unique_id)

        if self.project.get_main_segmentation() is not None:
            for s in self.project.get_main_segmentation().segments:
                segment_starts.append(int(s.get_start()))
                segment_ends.append(int(s.get_end()))
                segment_ids.append(s.ID)

        data = ScreenshotData()
        data.a = np.nan_to_num(a).tolist()
        data.b = np.nan_to_num(b).tolist()
        data.chroma = np.nan_to_num(chroma).tolist()
        data.luminance = np.nan_to_num(luminance).tolist()
        data.saturation = np.nan_to_num(saturation).tolist()
        data.hue = np.nan_to_num(hue).tolist()
        data.time = np.nan_to_num(time).tolist()

        data.uuids = uuids
        data.palettes = palettes

        data.selected_but_not_analyzed_uuids_ColorFeatureAnalysis = selected_but_not_analyzed_uuids_ColorFeatureAnalysis
        data.selected_but_not_analyzed_uuids_ColorPaletteAnalysis = selected_but_not_analyzed_uuids_ColorPaletteAnalysis

        data.segment_starts = segment_starts
        data.segment_ends = segment_ends
        data.segment_ids = segment_ids

        self._screenshot_cache['has_changed'] = True
        self._screenshot_cache['data'] = data
        self.export_screenshots()

    def set_project(self, project:VIANProject, onAnalyseColorFeatureSignal, onAnalyseColorPaletteSignal):
        self.project = project
        self.onAnalyseColorFeatureSignal = onAnalyseColorFeatureSignal
        self.onAnalyseColorPaletteSignal = onAnalyseColorPaletteSignal

        self._screenshot_cache = dict(revision = 0, data=ScreenshotData())

        self.project.onScreenshotAdded.connect(self.on_screenshot_added)
        self.project.onAnalysisAdded.connect(partial(self.queue_update))
        self.project.onSelectionChanged.connect(partial(self.queue_update))
        self.project.onProjectChanged.connect(partial(self.queue_update))

        for s in self.project.screenshots:
            s.onScreenshotChanged.connect(partial(self.queue_update))

        self._screenshot_cache['revision'] += 1
        self.update_screenshot_data()

    def queue_update(self):
        self._recompute_screenshot_cache = True

    def update(self):
        if self._project_closed:
            self._clear()
            return False

        if self.project is not None:
            self.update_screenshot_data()
            return True
        else:
            return False

    def on_screenshot_added(self, s:Screenshot):
        s.onScreenshotChanged.connect(partial(self.update_screenshot_data))

    def screenshot_url(self, s:Screenshot = None, uuid = None):
        if self.project is None:
            return None

        if uuid is None:
            file = os.path.join(os.path.join(self.project.export_dir, "screenshot_thumbnails"), str(s.unique_id) + ".jpg")
        else:
            file = os.path.join(os.path.join(self.project.export_dir, "screenshot_thumbnails"), str(uuid) + ".jpg")
        if os.path.isfile(file):
            return file
        else:
            return None

    def export_screenshots(self):
        ps = []
        rdir = os.path.join(self.project.export_dir, "screenshot_thumbnails")
        if not os.path.isdir(rdir):
            os.mkdir(rdir)

        for s in self.project.screenshots:
            if s.img_movie is None:
                continue

            if s.img_movie.shape[0] > 100:
                p = os.path.join(rdir, str(s.unique_id) + ".jpg")
                if not os.path.isfile(p):
                    cv2.imwrite(p, s.img_movie)
                ps.append(p)
        return ps

    def set_settings(self, settings):
        self.settings = settings

    def get_settings(self):
        return self.settings

    def clear(self):
        self._project_closed = True

    def _clear(self):
        self.project = None  # type: VIANProject
        self._screenshot_cache = dict(revision = 0, data=ScreenshotData())


_server_data = ServerData()


class FlaskServer(QObject):
    onAnalyseColorFeature = pyqtSignal(list)
    onAnalyseColorPalette = pyqtSignal(list)
    def __init__(self, parent):
        super(FlaskServer, self).__init__(parent)

    @pyqtSlot()
    def run_server(self):
        app.run(host='127.0.0.1', port=VIAN_PORT)

    def on_loaded(self, project):
        global _server_data
        _server_data.set_project(project, self.onAnalyseColorFeature, self.onAnalyseColorPalette)

    def on_closed(self):
        global _server_data
        _server_data.clear()

    def on_changed(self, project, item):
        pass

    def get_project(self):
        return None

    def on_selected(self, sender, selected):
        selected = list(selected)
        if sender is _server_data:
            return

        q = None
        for t in selected:
            if isinstance(t, VIANProject):
                q = t
        if q is not None:
            selected.remove(q)

        if _server_data.project is not None:
            # TODO this fails with corpus selection
            if len(selected) > 0:
                for s in selected:
                    if isinstance(s, Segment):
                        selected.extend(_server_data.project.get_screenshots_of_segment(s))
                selected = list(set(selected))
                _server_data.selected_uuids = [s.unique_id for s in selected]
            else:
                _server_data.selected_uuids = None
            _server_data.queue_update()
        pass


class WebPage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level: 'QWebEnginePage.JavaScriptConsoleMessageLevel', message: str, lineNumber: int, sourceID: str) -> None:
        print(message)


class FlaskWebWidget(EDockWidget):
    def __init__(self, main_window):
        super(FlaskWebWidget, self).__init__(main_window, limit_size=False)
        self.setWindowTitle("Bokeh Visualizations")


        self.view = QWebEngineView(self)
        self.view.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, False)
        self.view.setPage(WebPage())
        self.view.reload()
        self.view.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        self.setWidget(self.view)

        self.a_open_browser = self.inner.menuBar().addAction("Open in Browser")
        self.a_open_browser.triggered.connect(self.on_browser)

        self.url = None
        self.getSettingsURL = None
        self.setSettingsURL = None


    def on_browser(self):
        if sys.platform == 'darwin':
            os.system(f"open \"\" {self.url}")
        else:
            webbrowser.open(self.url)

    def set_url(self, url):
        self.url = url

        QWebEngineProfile.defaultProfile().clearAllVisitedLinks()
        QWebEngineProfile.defaultProfile().clearHttpCache()
        self.view.setUrl(QUrl(url))
        self.view.reload()

    def set_settingsURL(self, getSettingsURL, setSettingsURL):
        self.getSettingsURL = getSettingsURL
        self.setSettingsURL = setSettingsURL

    def showEvent(self, a0: QtGui.QShowEvent) -> None:
        self.reload()
        super(FlaskWebWidget, self).showEvent(a0)

    def reload(self):
        self.view.reload()

    def get_settings(self):
        if self.getSettingsURL == None:
            return None
        response = requests.get(self.getSettingsURL)
        if response.status_code == 204:
            return None
        return response.json()

    def apply_settings(self, settings):
        r = requests.post(self.setSettingsURL, json=settings)
        print(r)



@app.route("/")
def index():
    return render_template("color_dt.tmpl.html")


@app.route("/screenshot_vis/")
def screenshot_vis():
    return render_template("screenshot_vis.tmpl.html")


@app.route("/screenshot/<string:uuid>")
def screenshot(uuid):
    file = _server_data.screenshot_url(uuid=uuid)
    if file is None:
        print("Not Found", file)
        return make_response("Not found", 404)
    else:
        return send_file(file)


@app.route("/screenshot-data/<int:revision>")
def screenshot_data(revision):
    if _server_data.project is None:
        return json.dumps(_server_data.get_screenshot_data(revision))
    else:
        ret = _server_data.get_screenshot_data(revision)
        if 'uuids' in ret['data']:
            ret['data']['urls'] = [url_for("screenshot", uuid=u) for u in ret['data']['uuids']]
        return json.dumps(_server_data.get_screenshot_data(revision))


@app.route("/set-selection/", methods=['POST'])
def set_selection():
    if _server_data.project is None:
        return make_response(dict(screenshots_changed=False, uuids=[]))
    d = request.json
    selected_uuids = d['uuids']
    selected = [_server_data.project.get_by_id(uuids) for uuids in selected_uuids]

    selected = list(set(selected))
    if None in selected:
        selected.remove(None)

    _server_data.project.set_selected(_server_data, selected)
    return make_response("OK")

@app.route("/run-ColorFeatureAnalysis/", methods=['POST'])
def run_colorFeatureAnalysis():
    if _server_data.project is None:
        return make_response("Project is not set.")
    d = request.json
    uuid_submitted = d['uuids']
    if len(uuid_submitted) == 0: # means: analyse all
        for s in _server_data.project.screenshots:
            analyses = s.get_connected_analysis(ColorFeatureAnalysis)
            if len(analyses) == 0:
                uuid_submitted.append(s.unique_id)
    _server_data.onAnalyseColorFeatureSignal.emit(uuid_submitted)
    return make_response("OK")

@app.route("/run-ColorPaletteAnalysis/", methods=['POST'])
def run_colorPaletteAnalysis():
    if _server_data.project is None:
        return make_response("Project is not set.")
    d = request.json
    uuid_submitted = d['uuids']
    if len(uuid_submitted) == 0: # means: analyse all
        for s in _server_data.project.screenshots:
            analyses = s.get_connected_analysis(ColorPaletteAnalysis)
            if len(analyses) == 0:
                uuid_submitted.append(s.unique_id)
    _server_data.onAnalyseColorPaletteSignal.emit(uuid_submitted)
    return make_response("OK")

@app.route("/post-settings/", methods=['POST'])
def post_settings():
    d = request.json
    if d == None:
        return make_response("nothing set, submitted settings are None")
    _server_data.set_settings(d)
    return make_response("OK")

@app.route("/get-settings/")
def get_settings():
    if _server_data.project is None or _server_data.get_settings() is None:
        return '', 204
    return json.dumps(_server_data.get_settings())



@app.route("/summary/")
def summary():
    from vian.core.visualization.bokeh_timeline import generate_plot
    html, script = generate_plot(_server_data.project, return_mode="components")
    return render_template("template_inject.tmpl.html",script=html + script)
    # return render_template("summary.tmpl.html")


if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0', port=VIAN_PORT)
