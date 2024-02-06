from typing import Callable, List, Optional
import os
import shutil

from qgis.PyQt.QtCore import QCoreApplication, QTranslator
from qgis.PyQt.QtGui import QIcon, QCursor, QPixmap
from qgis.PyQt.QtWidgets import QAction, QWidget
from qgis.utils import iface
from qgis.core import (QgsVectorLayer, QgsProject,
                       QgsRasterLayer, QgsGeometry, 
                       QgsFeature, QgsCoordinateReferenceSystem,
                       QgsCoordinateTransform, QgsFeatureRequest,
                       QgsCsException, QgsPointXY,
                       QgsSpatialIndex, QgsRectangle)
from qgis.core.additions.edit import edit
from qgis.gui import QgsMapToolEmitPoint

from raster_organiser.qgis_plugin_tools.tools.custom_logging import (
    setup_logger,
    teardown_logger,
)
from raster_organiser.qgis_plugin_tools.tools.i18n import setup_translation
from raster_organiser.qgis_plugin_tools.tools.resources import (plugin_name, resources_path, )

from raster_organiser.user_communication import UserCommunication
from .resources import *
from raster_organiser.settings_dialog import SettingsDialog

class Organizer:
    """QGIS Plugin Implementation."""

    name = plugin_name()

    def __init__(self, iface) -> None:
        setup_logger(Organizer.name)

        # initialize locale
        locale, file_path = setup_translation()
        if file_path:
            self.translator = QTranslator()
            self.translator.load(file_path)
            # noinspection PyCallByClass
            QCoreApplication.installTranslator(self.translator)
        else:
            pass
        
        self.iface = iface
        self.canvas = self.iface.mapCanvas()
        self.project = QgsProject.instance()
        self.uc = UserCommunication(iface, 'Raster Organiser')
        self.toolbar = None
        self.menu = None
        self.crs_transform = None
        self.mode = None
        # TODO: Change to dynamic path
        self.target_rasters_path = r'N:\PSE\test_project\raster_organiser\test_data\target_path'
        self.mpzp_extents_layer = None

        self.actions: List[QAction] = []
        
        # Map tools
        self.load_tool = QgsMapToolEmitPoint(self.canvas)
        self.load_tool.setObjectName("OrganizerLoadRasterTool")
        self.load_tool.setCursor(QCursor(QIcon(resources_path('icons' , "cursor_load_raster.svg")).pixmap(32,32), hotX=0, hotY=0))
        self.load_tool.canvasClicked.connect(self.point_clicked)
        
        self.map_tool_btn = dict()
        self.canvas.mapToolSet.connect(self.check_active_tool)

    def add_action(
        self,
        icon_path: str,
        text: str,
        callback: Callable,
        enabled_flag: bool = True,
        add_to_menu: bool = True,
        add_to_toolbar: bool = True,
        status_tip: Optional[str] = None,
        whats_this: Optional[str] = None,
        parent: Optional[QWidget] = None,
        checkable: bool = False,
        checked: bool = False
    ) -> QAction:
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.

        :param text: Text that should be shown in menu items for this action.

        :param callback: Function to be called when the action is triggered.

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.

        :param parent: Parent widget for the new action. Defaults None.

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(resources_path('icons' , icon_path))
        action = QAction(icon, text, parent)
        # noinspection PyUnresolvedReferences
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)
        action.setCheckable(checkable)
        action.setChecked(checked)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            # iface.addToolBarIcon(action)
            # Adds plugin icon to desired toolbar
            add_to_toolbar.addAction(action)

        if add_to_menu:
            iface.addPluginToMenu(self.menu, action)

        self.actions.append(action)

        return action

    def initGui(self) -> None:  # noqa N802
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        # Add the toolbar
        self.toolbar = self.iface.addToolBar('Raster Organiser Main Toolbar')
        self.toolbar.setObjectName('Raster Organiser Main Toolbar')
        self.toolbar.setToolTip('Raster Organiser Main Toolbar')
        
        self.menu = Organizer.name
        
        self.add_raster_btn = self.add_action(
            "save_raster.svg",
            text="Save raster",
            callback=self.add_raster,
            add_to_toolbar=self.toolbar,
        )
        
        self.load_rasters_btn = self.add_action(
            "load_raster.svg",
            text="Load rasters by point",
            callback=self.load_rasters,
            add_to_toolbar=self.toolbar,
            checkable=True
        )
        self.map_tool_btn[self.load_rasters_btn] = self.load_rasters_btn
        
        self.settings_btn = self.add_action(
            "settings.svg",
            text="Configure plugin settings",
            callback=self.edit_settings,
            add_to_toolbar=self.toolbar,
            parent=self.iface.mainWindow()
        )
        
        self.add_action(
            "",
            text=Organizer.name,
            callback=self.run_menu,
            parent=iface.mainWindow(),
            add_to_toolbar=False,
        )
                

    def onClosePlugin(self) -> None:  # noqa N802
        """Cleanup necessary items here when plugin dockwidget is closed"""
        pass

    def unload(self) -> None:
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            iface.removePluginMenu(Organizer.name, action)
            iface.removeToolBarIcon(action)
        del self.toolbar
        teardown_logger(Organizer.name)

    def run_menu(self) -> None:
        """Run method that performs all the real work"""
        active_layer = self.iface.activeLayer()
        print(active_layer.extent())
        print(active_layer.dataProvider().dataSourceUri())
        print("Hello QGIS plugin again")
        
    def add_raster(self) -> None:
        if self.mpzp_extents_layer is None:
            self.uc.show_warn("There is no active vector layer. Set it first!")
            return
        
        print(self.mpzp_extents_layer.name())
        active_raster = self.iface.activeLayer()
        # check if any layer is selected at all
        if active_raster is None:
            self.uc.show_info("No active layer selected")
            return
        
        active_raster_name = active_raster.name()
        active_raster_path = active_raster.dataProvider().dataSourceUri()
        raster_target_path = os.path.join(self.target_rasters_path, os.path.basename(active_raster_path))
        
        # check if selected layer is Raster layer
        if not isinstance(active_raster, QgsRasterLayer):
            self.uc.bar_warn(f"Selected layer {active_raster_name} is not Raster!")
            return
        # check if raster name is already in mpzp raster
        expression = f"raster_name = '{active_raster_name}'"
        request = QgsFeatureRequest().setFilterExpression(expression)
        if any(self.mpzp_extents_layer.getFeatures(request)):
            self.uc.show_warn(f"Raster with name: {active_raster_name} already exists in {self.mpzp_extents_layer.name()}")     
            return
        # check if raster with such name already exists in target path
        if os.path.isfile(raster_target_path):
            self.uc.show_warn(f"Raster with name: {os.path.basename(active_raster_path)} already exists in {self.target_rasters_path}")
            return
        
        # Append raster extent to selected target Vector layer
        raster_layer_extent = active_raster.extent()
        raster_extent_geometry = QgsGeometry.fromRect(raster_layer_extent)
        raster_extent_feature = QgsFeature(self.mpzp_extents_layer.fields())
        # transform geometry if needed
        if active_raster.crs() != self.mpzp_extents_layer.crs():
            tr = QgsCoordinateTransform(active_raster.crs(), self.mpzp_extents_layer.crs(), self.project)
            raster_extent_geometry.transform(tr)
        raster_extent_feature.setGeometry(raster_extent_geometry)
        raster_extent_feature.setAttributes([None, active_raster_name, raster_target_path])
        
        self.mpzp_extents_layer.dataProvider().addFeatures([raster_extent_feature])

        self.canvas.refresh()
        
        # copy raster to target path
        shutil.copy2(active_raster_path, raster_target_path)
        
        print("save!")
        
    def load_rasters(self) -> None:
        self.mode = 'load_raster'
        self.canvas.setMapTool(self.load_tool)
        print("load!")
    
    def uncheck_all_btns(self):
        self.load_rasters_btn.setChecked(False)
        
    def check_active_tool(self, cur_tool):
        self.uncheck_all_btns()
        if cur_tool in self.map_tool_btn:
            self.map_tool_btn[cur_tool].setChecked(True)
            
    def point_clicked(self, point=None, button=None):
        if self.mpzp_extents_layer is None:
            self.uc.show_warn("There is no active vector layer. Set it first!")
            return
        
        print(f"Clicked point in canvas CRS: {point if point else self.last_point}")
        
        if point is None:
            ptxy_in_src_crs = self.last_point
        else:
            if self.crs_transform:
                try:
                    ptxy_in_src_crs = self.crs_transform.transform(point)
                except QgsCsException as err:
                    self.uc.show_warn(
                        "Point coordinates transformation failed! Check the target layer projection:\n\n{}".format(repr(err)))
                    return
            else:
                ptxy_in_src_crs = QgsPointXY(point.x(), point.y())
                
        print(f"Clicked point in raster CRS: {ptxy_in_src_crs}")
        self.last_point = ptxy_in_src_crs
        
        if self.mode == 'load_raster':
            self.mpzp_extents_layer.removeSelection()
            index = QgsSpatialIndex(self.mpzp_extents_layer.getFeatures())
            
            dxy = 0.001
            pt_x, pt_y = self.last_point.x(), self.last_point.y()
            cell = QgsRectangle(pt_x, pt_y, pt_x + dxy, pt_y + dxy)
            
            matches_ids = index.intersects(cell)
            self.mpzp_extents_layer.selectByIds(matches_ids)
            selection = self.mpzp_extents_layer.selectedFeatures()
            
            if len(selection) == 0:
                self.uc.bar_info("There is no data in chosen point", dur=2)
            for feature in selection:
                print(feature['raster_path'])
                # load raster layer
                self.iface.addRasterLayer(feature['raster_path'], baseName=feature["raster_name"])
            
                self.mpzp_extents_layer.removeSelection()
                self.uc.bar_info(f"Loaded raster {feature['raster_name']}", dur=1)
            
    def edit_settings(self):
        """Open dialog with plugin settings"""
        settings_dialog = SettingsDialog(iface=self.iface, project=self.project)
        
        settings_dialog.show()
        result = settings_dialog.exec_()
        if result:
            self.mpzp_extents_layer = settings_dialog.current_layer
            self.crs_transform = None if self.project.crs() == self.mpzp_extents_layer.crs() else \
                QgsCoordinateTransform(self.project.crs(), self.mpzp_extents_layer.crs(), self.project)
        
    