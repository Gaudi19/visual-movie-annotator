from PyQt6.QtWidgets import QFileDialog,QDialog, QComboBox, QFrame, QFormLayout, QHBoxLayout, QMessageBox, QPushButton, QLabel
from PyQt6 import uic
from vian.core.gui.ewidgetbase import EDialogWidget
# from vian.core.data.exporters import ExperimentExporter
import os
import json

class ExportTemplateDialog(EDialogWidget):
    def __init__(self, main_window):
        super(ExportTemplateDialog, self).__init__(main_window, main_window)
        path = os.path.abspath("qt_ui/DialogExportTemplate.ui")
        uic.loadUi(path, self)
        self.settings = main_window.settings

        self.btn_Export.clicked.connect(self.on_export)
        self.btn_Cancel.clicked.connect(self.close)


    def on_export(self):
        name = self.lineEdit_Name.text()

        path = QFileDialog.getSaveFileName(caption="Select Path", directory=os.path.join(self.settings.DIR_TEMPLATES, name + ".viant"), filter="*.viant")[0]

        #
        segmentation = self.cB_Segmentation.isChecked()
        vocabulary = self.cB_Vocabulary.isChecked()
        annotation_layers = self.cB_AnnotationLayers.isChecked()
        node_scripts = self.cB_NodeScripts.isChecked()
        experiments = self.cB_Experiments.isChecked()

        template = self.main_window.project.get_template(segmentation, vocabulary,
                                                         annotation_layers, node_scripts,
                                                         experiments)
        # path = self.settings.DIR_TEMPLATES + name + ".viant"
        try:
            with open(path, "w") as f:
                json.dump(template, f)
            QMessageBox.information(self.main_window, "Template Exported", "The template has been exported to {f}".format(f=path))
        except Exception as e:
            self.main_window.print_message("Template Export Failed:", "Red")
            self.main_window.print_message(e, "Red")

        self.close()





