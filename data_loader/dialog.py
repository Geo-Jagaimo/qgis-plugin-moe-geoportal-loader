"""
The algorithm dialog, which enables the prefecture only for the datasets
published per prefecture.
"""

# The dialog comes from the Processing plugin, not from the QGIS API, and QGIS
# 4.2 renamed it when it made the dialog dockable
try:
    from processing.gui.algorithm_widget import AlgorithmWidget as AlgorithmDialog
except ImportError:  # QGIS 3.44 to 4.0
    from processing.gui.AlgorithmDialog import AlgorithmDialog


class MOELoaderDialog(AlgorithmDialog):
    def __init__(self, alg, parent=None):
        super().__init__(alg, parent=parent)
        self._dataset_mapping = alg._dataset_mapping
        wrappers = self.mainWidget().wrappers
        self._dataset = wrappers[alg.CATEGORY]
        self._prefecture = wrappers[alg.PREFECTURE]

        self._dataset.widgetValueHasChanged.connect(self._update_prefecture)
        self._update_prefecture()

    def _update_prefecture(self):
        _, has_prefecture = self._dataset_mapping[self._dataset.parameterValue()]
        # The prefecture keeps its value while disabled, for when the user
        # selects such a dataset again; the algorithm ignores it meanwhile
        self._prefecture.wrappedWidget().setEnabled(has_prefecture)
        self._prefecture.wrappedLabel().setEnabled(has_prefecture)
