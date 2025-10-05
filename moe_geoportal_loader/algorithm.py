from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingParameterEnum,
    QgsProject,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QCoreApplication

from .datasets import DATASETS, PREFECTURES


class MOELoaderAlgorithm(QgsProcessingAlgorithm):
    DATASET = "DATASET"
    PREFECTURE = "PREFECTURE"

    def initAlgorithm(self, config=None):
        """
        URL指定のためのパラメータ（データセット/都道府県）
        """
        # dataset
        dataset_names = [ds["name"] for ds in DATASETS.values()]
        self.addParameter(
            QgsProcessingParameterEnum(
                self.DATASET,
                self.tr("データセット"),
                options=dataset_names,
                defaultValue=0,
            )
        )

        # 都道府県
        prefecture_names = [f"{code}: {name}" for code, name in PREFECTURES.items()]
        self.addParameter(
            QgsProcessingParameterEnum(
                self.PREFECTURE,
                self.tr("都道府県"),
                options=prefecture_names,
                defaultValue=0,
                optional=True,
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """
        ArcGIS REST FeatureServerからレイヤを追加
        """
        # 選択されたデータセットを取得
        dataset_idx = self.parameterAsEnum(parameters, self.DATASET, context)
        dataset_key = list(DATASETS.keys())[dataset_idx]
        dataset = DATASETS[dataset_key]

        # URLを構築
        url = dataset["url_template"]

        # 都道府県別データの場合、都道府県コードを置換
        if dataset["has_prefecture"]:
            pref_idx = self.parameterAsEnum(parameters, self.PREFECTURE, context)
            pref_code = list(PREFECTURES.keys())[pref_idx]
            url = url.format(pref_code=pref_code)
            layer_name = f"{dataset['name']} ({PREFECTURES[pref_code]})"
        else:
            url = url.format(pref_code="")
            layer_name = dataset["name"]

        feedback.pushInfo(f"Loading from: {url}")

        # ArcGIS FeatureServerレイヤを追加
        result = self._add_arcgis_layer(url, layer_name, feedback)

        return {"OUTPUT": result}

    def _add_arcgis_layer(self, url, layer_name, feedback):
        """
        ArcGIS REST FeatureServerレイヤをQGISプロジェクトに追加
        """
        try:
            # FeatureServerの全レイヤ情報を取得して、各レイヤを追加
            import json
            from urllib.error import URLError
            from urllib.request import urlopen

            # FeatureServerのメタデータを取得
            try:
                with urlopen(f"{url}?f=json") as response:
                    data = json.loads(response.read().decode())
            except URLError as e:
                feedback.reportError(
                    f"Failed to fetch FeatureServer metadata: {str(e)}"
                )
                return False

            # レイヤリストを取得
            layers = data.get("layers", [])

            if not layers:
                feedback.reportError(f"No layers found in FeatureServer: {url}")
                return False

            # 各レイヤを追加
            added_count = 0
            for layer_info in layers:
                layer_id = layer_info.get("id")
                layer_title = layer_info.get("name", f"Layer {layer_id}")

                # レイヤURLを構築（レイヤIDを含む）
                layer_url = f"{url}/{layer_id}"

                # ArcGIS FeatureServerレイヤを作成
                # crs=authid形式でURL構築
                uri = f"crs='EPSG:4612' url='{layer_url}'"
                full_layer_name = f"{layer_name} - {layer_title}"

                vector_layer = QgsVectorLayer(
                    uri, full_layer_name, "arcgisfeatureserver"
                )

                if not vector_layer.isValid():
                    feedback.pushWarning(
                        f"Failed to load layer: {full_layer_name} (ID: {layer_id})"
                    )
                    continue

                # プロジェクトにレイヤを追加
                QgsProject.instance().addMapLayer(vector_layer)
                feedback.pushInfo(
                    f"Successfully added layer: {full_layer_name} (ID: {layer_id})"
                )
                added_count += 1

            if added_count == 0:
                feedback.reportError("No layers were successfully added")
                return False

            feedback.pushInfo(f"Total layers added: {added_count}")
            return True

        except Exception as e:
            feedback.reportError(f"Error adding layer: {str(e)}")
            import traceback

            feedback.reportError(traceback.format_exc())
            return False

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return "MOEGeoportalLoader"

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr(self.name())

    def group(self):
        """
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        """
        return self.tr(self.groupId())

    def groupId(self):
        """
        Returns the unique ID of the group this algorithm belongs to. This
        string should be fixed for the algorithm, and must not be localised.
        The group id should be unique within each provider. Group id should
        contain lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return ""

    def tr(self, string):
        return QCoreApplication.translate("Processing", string)

    def createInstance(self):
        return MOELoaderAlgorithm()
