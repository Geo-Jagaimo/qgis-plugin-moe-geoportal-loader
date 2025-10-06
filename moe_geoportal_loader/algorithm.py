from qgis.core import (
    QgsFeatureSink,
    QgsField,
    QgsFields,
    QgsProcessingAlgorithm,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSink,
    QgsProject,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QCoreApplication

from .datasets import DATASETS
from .prefecture import PREFECTURES


class MOELoaderAlgorithm(QgsProcessingAlgorithm):
    DATASET = "DATASET"
    CATEGORY = "CATEGORY"
    PREFECTURE = "PREFECTURE"
    OUTPUT_TYPE = "OUTPUT_TYPE"
    OUTPUT = "OUTPUT"

    def initAlgorithm(self, config=None):
        self._dataset_mapping = []
        dataset_options = []

        for dataset_key, dataset in DATASETS.items():
            self._dataset_mapping.append(
                (
                    dataset_key,
                    dataset["has_prefecture"],
                )
            )
            dataset_options.append(dataset["name"])

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

        # select output type
        self.addParameter(
            QgsProcessingParameterEnum(
                self.OUTPUT_TYPE,
                self.tr("出力形式"),
                options=[
                    self.tr("スタイル付きレイヤ"),
                    self.tr("ファイルに保存"),
                    self.tr("どちらも"),
                ],
                defaultValue=0,
                optional=False,
            )
        )
        self.parameterDefinition(self.OUTPUT_TYPE).setMetadata(
            {
                "widget_wrapper": {
                    "useCheckBoxes": True,
                    "columns": 3,
                }
            }
        )

        # optional file output (skip by default)
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr("出力先"),
                optional=True,
                createByDefault=False,
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        dataset_idx = self.parameterAsEnum(parameters, self.CATEGORY, context)
        dataset_key, has_prefecture = self._dataset_mapping[dataset_idx]

        dataset = DATASETS[dataset_key]
        url = dataset["url"]

        # validation for data that requires prefecture specification
        if has_prefecture:
            pref_idx = self.parameterAsEnum(parameters, self.PREFECTURE, context)
            if pref_idx is None or pref_idx == 0:
                feedback.reportError(self.tr("都道府県を選択してください"))
                return {"OUTPUT": None}

            pref_code = list(PREFECTURES.keys())[pref_idx]

            # Handle specific URL for Hokkaido
            if dataset_key == "vg_50000" and pref_code == "01":
                pref_code = f"{pref_code}_0420"

            url = url.format(pref_code=pref_code)

        feedback.pushInfo(f"Loading from: {url}")

        # Get output type selection
        output_type = self.parameterAsEnum(parameters, self.OUTPUT_TYPE, context)
        # 0: スタイル付きレイヤ, 1: ファイルに保存, 2: どちらも

        layer_id = None
        file_output = None

        # Load styled layer if requested (0 or 2)
        if output_type == 0 or output_type == 2:
            layer_id = self._load_as_arcgis_layer(
                url,
                dataset,
                has_prefecture,
                pref_idx if has_prefecture else None,
                feedback,
            )

        if output_type == 1 or output_type == 2:
            if not parameters.get(self.OUTPUT):
                feedback.reportError(
                    self.tr("ファイルに保存を選択した場合は出力先を指定してください")
                )
                return {"OUTPUT": None}
            file_output = self._save_to_file(url, parameters, context, feedback)

        return {"OUTPUT": file_output if file_output else layer_id}

    def _load_as_arcgis_layer(self, url, dataset, has_prefecture, pref_idx, feedback):
        """Load layer directly as ArcGIS Feature Server layer with styling"""
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

            # Build layer name from dataset name and prefecture
            layer_name = dataset["name"].replace("- 都道府県別", "").strip()
            if has_prefecture and pref_idx is not None:
                prefecture_name = list(PREFECTURES.values())[pref_idx]
                layer_name = f"{layer_name}_{prefecture_name}"

            layer_url = f"{url}/{layer_id}"
            uri = f"url='{layer_url}'"

            vector_layer = QgsVectorLayer(uri, layer_name, "arcgisfeatureserver")

            if not vector_layer.isValid():
                feedback.reportError(f"Failed to load layer (ID: {layer_id})")
                return None

            # Add layer to project with styling preserved
            QgsProject.instance().addMapLayer(vector_layer)

            feedback.pushInfo(f"Successfully loaded layer: {layer_name}")
            feedback.pushInfo(f"CRS: {vector_layer.crs().authid()}")

            return vector_layer.id()

        except Exception as e:
            feedback.reportError(f"Error loading layer: {str(e)}")
            import traceback

            feedback.reportError(traceback.format_exc())
            return None

    def _save_to_file(self, url, parameters, context, feedback):
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

            layer_url = f"{url}/{layer_id}"

            uri = f"url='{layer_url}'"

            vector_layer = QgsVectorLayer(uri, "temp", "arcgisfeatureserver")

            if not vector_layer.isValid():
                feedback.reportError(f"Failed to load layer (ID: {layer_id})")
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
                feedback.reportError(self.tr("出力レイヤの作成に失敗しました"))
                return None

            feedback.pushInfo(f"Output CRS: {output_crs.authid()}")

            total = vector_layer.featureCount()
            feedback.pushInfo(f"Writing {total} features to output...")

            processed = 0
            for feature in vector_layer.getFeatures():
                if feedback.isCanceled():
                    break

                sink.addFeature(feature, QgsFeatureSink.FastInsert)
                processed += 1

                if total > 0:
                    feedback.setProgress(int((processed / total) * 100))

            feedback.pushInfo(f"Successfully wrote {processed} features")

            return dest_id

        except Exception as e:
            feedback.reportError(f"Error loading layers: {str(e)}")
            import traceback

            feedback.reportError(traceback.format_exc())
            return None

    def name(self):
        return "moe_geoportal_loader"

    def displayName(self):
        return self.tr("環境ジオポータルのデータを読み込む")

    def group(self):
        return None

    def groupId(self):
        return None

    def tr(self, string):
        return QCoreApplication.translate("Processing", string)

    def createInstance(self):
        return MOELoaderAlgorithm()
