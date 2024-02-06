from pathlib import Path
import os

from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import (QWidget, QVBoxLayout, QLabel, QDialog,
                                 QHBoxLayout, QPushButton, QFileDialog)
from qgis.PyQt import QtWidgets

from qgis.gui import QgsMapLayerComboBox
from qgis.core import QgsMapLayerProxyModel, QgsVectorLayer

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'dialog_settings.ui'))

class SettingsDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, parent=None, iface=None, project=None):
        super(SettingsDialog, self).__init__(parent)
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        self.parent = parent
        self.iface = iface
        self.project = project
        
        self.current_layer = None
        
        self.mlcb.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.file_selection_button.clicked.connect(self.getFile)
        self.dialogBox.clicked.connect(self.set_currentLayer)
        
    def getFile(self):
        file_name = QFileDialog.getOpenFileName(None, 'Select file', '', filter='*.shp; *.gpkg')
        if file_name:
            self.mlcb.setAdditionalItems([file_name[0]])
            self.mlcb.setCurrentIndex(self.mlcb.model().rowCount()-1)
    
    def set_currentLayer(self):
        self.current_layer = self.mlcb.currentLayer()
        if self.current_layer is not None:
            return self.current_layer
        else:
            path = self.mlcb.currentText()
            name = Path(path).stem
            layer = QgsVectorLayer(path, name, 'ogr')
            if layer.isValid():
                self.project.addMapLayer(layer)
                self.current_layer = layer
                return self.current_layer
        return None
    