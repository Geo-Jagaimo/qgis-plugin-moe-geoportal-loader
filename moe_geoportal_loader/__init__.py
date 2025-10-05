from qgis.gui import QgisInterface


def classFactory(iface: QgisInterface):
    from .plugin import MOEGeoportalLoader

    return MOEGeoportalLoader(iface)
