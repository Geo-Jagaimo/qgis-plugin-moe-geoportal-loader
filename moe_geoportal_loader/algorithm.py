from qgis.core import (
    QgsFeatureSink,
    QgsProcessingAlgorithm,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSink,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QCoreApplication

from .datasets import DATASETS, PREFECTURES


class MOELoaderAlgorithm(QgsProcessingAlgorithm):
    DATASET = "DATASET"
    PREFECTURE = "PREFECTURE"
    OUTPUT = "OUTPUT"

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

        # 出力レイヤ
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr("出力レイヤ"),
                optional=False,
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """
        ArcGIS REST FeatureServerからレイヤをロードしてFeatureSinkに出力
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

        # ArcGIS FeatureServerからレイヤをロードしてsinkに出力
        result = self._load_and_write_layers(
            url, layer_name, parameters, context, feedback
        )

        return {"OUTPUT": result}

    def _load_and_write_layers(self, url, layer_name, parameters, context, feedback):
        """
        ArcGIS REST FeatureServerからレイヤをロードし、FeatureSinkに書き込む
        """
        try:
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
                return None

            # レイヤリストを取得
            layers = data.get("layers", [])

            if not layers:
                feedback.reportError(f"No layers found in FeatureServer: {url}")
                return None

            # 最初のレイヤのみを処理（複数レイヤの場合は最初のものを使用）
            # 複数レイヤ対応は今後の拡張として残す
            first_layer = layers[0]
            layer_id = first_layer.get("id")
            layer_title = first_layer.get("name", f"Layer {layer_id}")

            # レイヤURLを構築（レイヤIDを含む）
            layer_url = f"{url}/{layer_id}"

            # ArcGIS FeatureServerレイヤを作成
            uri = f"crs='EPSG:4612' url='{layer_url}'"
            full_layer_name = f"{layer_name} - {layer_title}"

            vector_layer = QgsVectorLayer(uri, full_layer_name, "arcgisfeatureserver")

            if not vector_layer.isValid():
                feedback.reportError(
                    f"Failed to load layer: {full_layer_name} (ID: {layer_id})"
                )
                return None

            # FeatureSinkを作成
            (sink, dest_id) = self.parameterAsSink(
                parameters,
                self.OUTPUT,
                context,
                vector_layer.fields(),
                vector_layer.wkbType(),
                vector_layer.crs(),
            )

            if sink is None:
                feedback.reportError("Failed to create output sink")
                return None

            # フィーチャをsinkに書き込む
            total = vector_layer.featureCount()
            feedback.pushInfo(f"Writing {total} features to output...")

            for current, feature in enumerate(vector_layer.getFeatures()):
                if feedback.isCanceled():
                    break

                sink.addFeature(feature, QgsFeatureSink.FastInsert)

                if total > 0:
                    feedback.setProgress(int((current / total) * 100))

            feedback.pushInfo(f"Successfully wrote layer: {full_layer_name}")

            return dest_id

        except Exception as e:
            feedback.reportError(f"Error loading layers: {str(e)}")
            import traceback

            feedback.reportError(traceback.format_exc())
            return None

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
