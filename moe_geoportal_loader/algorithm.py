from qgis.core import (
    QgsFeatureSink,
    QgsField,
    QgsFields,
    QgsProcessingAlgorithm,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSink,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QCoreApplication

from .datasets import DATASETS
from .prefecture import PREFECTURES


class MOELoaderAlgorithm(QgsProcessingAlgorithm):
    DATASET = "DATASET"
    CATEGORY = "CATEGORY"
    PREFECTURE = "PREFECTURE"
    OUTPUT = "OUTPUT"

    def initAlgorithm(self, config=None):
        self._dataset_mapping = []
        dataset_options = []

        for dataset_key, dataset in DATASETS.items():
            display_name = dataset["name"]
            self._dataset_mapping.append(
                (
                    dataset_key,
                    display_name,
                    dataset["has_prefecture"],
                )
            )
            dataset_options.append(display_name)

        # select dataset
        self.addParameter(
            QgsProcessingParameterEnum(
                self.CATEGORY,
                self.tr("データセット"),
                options=dataset_options,
                defaultValue=0,
            )
        )

        # select prefecture
        prefecture_names = [name for name in PREFECTURES.values()]
        self.addParameter(
            QgsProcessingParameterEnum(
                self.PREFECTURE,
                self.tr("都道府県"),
                options=prefecture_names,
                defaultValue=0,
            )
        )

        # output layer
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr("出力レイヤ"),
                optional=False,
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        dataset_idx = self.parameterAsEnum(parameters, self.CATEGORY, context)
        dataset_key, display_name, has_prefecture = self._dataset_mapping[dataset_idx]

        dataset = DATASETS[dataset_key]
        url = dataset["url"]
        layer_name = display_name

        # validation for data that requires prefecture specification
        if has_prefecture:
            pref_idx = self.parameterAsEnum(parameters, self.PREFECTURE, context)
            if pref_idx is None or pref_idx == 0:
                feedback.reportError("都道府県を選択してください")
                return {"OUTPUT": None}

            pref_code = list(PREFECTURES.keys())[pref_idx]
            url = url.format(pref_code=pref_code)
            layer_name = f"{layer_name} ({PREFECTURES[pref_code]})"

        feedback.pushInfo(f"Loading from: {url}")

        result = self._load_and_write_layers(
            url, layer_name, parameters, context, feedback
        )

        return {"OUTPUT": result}

    def _load_and_write_layers(self, url, layer_name, parameters, context, feedback):
        try:
            import json
            from urllib.error import URLError
            from urllib.request import urlopen

            try:
                with urlopen(f"{url}?f=json") as response:
                    data = json.loads(response.read().decode())
            except URLError as e:
                feedback.reportError(
                    f"Failed to fetch FeatureServer metadata: {str(e)}"
                )
                return None

            layers = data.get("layers", [])

            if not layers:
                feedback.reportError(f"No layers found in FeatureServer: {url}")
                return None

            first_layer = layers[0]
            layer_id = first_layer.get("id")
            layer_title = first_layer.get("name", f"Layer {layer_id}")

            layer_url = f"{url}/{layer_id}"

            uri = f"crs='EPSG:4612' url='{layer_url}'"
            full_layer_name = f"{layer_name} - {layer_title}"

            vector_layer = QgsVectorLayer(uri, full_layer_name, "arcgisfeatureserver")

            if not vector_layer.isValid():
                feedback.reportError(
                    f"Failed to load layer: {full_layer_name} (ID: {layer_id})"
                )
                return None

            cleaned_fields = QgsFields()
            for field in vector_layer.fields():
                # create new fields
                new_field = QgsField(field)
                new_field.setAlias("")
                new_field.setComment("")
                cleaned_fields.append(new_field)

            output_crs = vector_layer.crs()

            (sink, dest_id) = self.parameterAsSink(
                parameters,
                self.OUTPUT,
                context,
                cleaned_fields,
                vector_layer.wkbType(),
                output_crs,
                QgsFeatureSink.SinkFlags(),
            )

            if sink is None:
                feedback.reportError("Failed to create output sink")
                return None

            feedback.pushInfo(f"Output CRS: {output_crs.authid()}")

            total = vector_layer.featureCount()
            feedback.pushInfo(f"Writing {total} features to output...")

            # Batch processing settings
            BATCH_SIZE = 2000
            features_batch = []
            processed = 0

            for feature in vector_layer.getFeatures():
                if feedback.isCanceled():
                    break

                features_batch.append(feature)

                if len(features_batch) >= BATCH_SIZE:
                    sink.addFeatures(features_batch, QgsFeatureSink.FastInsert)
                    processed += len(features_batch)
                    features_batch = []

                    if total > 0:
                        feedback.setProgress(int((processed / total) * 100))

            if features_batch:
                sink.addFeatures(features_batch, QgsFeatureSink.FastInsert)
                processed += len(features_batch)

            feedback.pushInfo(f"Successfully wrote {processed} features")

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
        return "環境ジオポータルのデータを読み込む"

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
