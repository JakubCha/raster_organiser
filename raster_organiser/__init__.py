import os

from qgis.gui import QgisInterface

from raster_organiser.qgis_plugin_tools.infrastructure.debugging import setup_debugpy  # noqa F401
from raster_organiser.qgis_plugin_tools.infrastructure.debugging import setup_ptvsd  # noqa F401
from raster_organiser.qgis_plugin_tools.infrastructure.debugging import setup_pydevd  # noqa F401

DEBUG = True

debugger = os.environ.get("QGIS_PLUGIN_USE_DEBUGGER", "").lower()
if debugger in {"debugpy", "ptvsd", "pydevd"}:
    locals()["setup_" + debugger]()


def classFactory(iface: QgisInterface):  # noqa N802
    if DEBUG:
            import sys
            sys.path.append('C:\\Users\\Kuba_MASZYNA\\.vscode\\extensions\\ms-python.python-2023.20.0\\pythonFiles\\lib\\python')

            import debugpy
            import shutil
            debugpy.configure(python=shutil.which("python"))
            try:
                debugpy.listen(("localhost", 5678))
            except:
                debugpy.connect(("localhost", 5678))
    
    from raster_organiser.raster_organiser import Organizer

    return Organizer(iface)
