from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsFeatureSink,
    QgsField,
    QgsFields,
    QgsProcessingAlgorithm,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSink,
    QgsProject,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QCoreApplication

from .settings_datasets import DATASETS
from .settings_prefecture import PREFECTURES


class MOELoaderAlgorithm(QgsProcessingAlgorithm):
    DATASET = "DATASET"
    CATEGORY = "CATEGORY"
    PREFECTURE = "PREFECTURE"
    ADD_AS_ARCGIS_LAYER = "ADD_AS_ARCGIS_LAYER"
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

        self.addParameter(
            QgsProcessingParameterEnum(
                self.CATEGORY,
                self.tr("データセット"),
                options=dataset_options,
                defaultValue=0,
            )
        )

        prefecture_names = [name for name in PREFECTURES.values()]
        self.addParameter(
            QgsProcessingParameterEnum(
                self.PREFECTURE,
                self.tr("都道府県"),
                options=prefecture_names,
                defaultValue=0,
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.ADD_AS_ARCGIS_LAYER,
                self.tr("ArcGIS REST Server layerとして追加"),
                defaultValue=False,
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr("出力レイヤ"),
                createByDefault=False,
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        dataset_idx = self.parameterAsEnum(parameters, self.CATEGORY, context)
        dataset_key, has_prefecture = self._dataset_mapping[dataset_idx]

        dataset = DATASETS[dataset_key]
        url = dataset["url"]

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

        add_as_arcgis_layer = self.parameterAsBool(
            parameters, self.ADD_AS_ARCGIS_LAYER, context
        )

        if add_as_arcgis_layer:
            layer_id = self._load_as_arcgis_layer(
                url,
                dataset,
                has_prefecture,
                pref_idx if has_prefecture else None,
                feedback,
            )
            return {"OUTPUT": layer_id}

        if not parameters.get(self.OUTPUT):
            feedback.reportError(self.tr("出力レイヤの保存先を指定してください"))
            return {"OUTPUT": None}

        file_output = self._save_to_file(url, parameters, context, feedback)
        return {"OUTPUT": file_output}

    def _fetch_json(self, url, feedback, error_context):
        try:
            import json
            from urllib.request import urlopen

            with urlopen(url) as response:
                return json.loads(response.read().decode())
        except Exception as e:
            feedback.reportError(f"{error_context}: {str(e)}")
            return None

    def _resolve_layer_url_and_meta(self, url, feedback):
        service_meta = self._fetch_json(
            f"{url}?f=json", feedback, "Failed to fetch FeatureServer metadata"
        )
        if not service_meta:
            return None

        layers = service_meta.get("layers", [])
        if not layers:
            feedback.reportError(f"No layers found in FeatureServer: {url}")
            return None

        first_layer = layers[0]
        layer_id = first_layer.get("id")
        layer_url = f"{url}/{layer_id}"

        layer_meta = (
            self._fetch_json(
                f"{layer_url}?f=json", feedback, "Failed to fetch layer metadata"
            )
            or {}
        )

        return (layer_url, service_meta, layer_meta)

    def _build_layer_name(self, dataset, has_prefecture, pref_idx):
        layer_name = dataset["name"].replace("- 都道府県別", "").strip()
        if has_prefecture and pref_idx is not None:
            prefecture_name = list(PREFECTURES.values())[pref_idx]
            layer_name = f"{prefecture_name}_{layer_name}"
        return layer_name

    def _create_arcgis_vector_layer(self, layer_url, layer_name, feedback):
        uri = f"url='{layer_url}'"
        vector_layer = QgsVectorLayer(uri, layer_name, "arcgisfeatureserver")
        if not vector_layer.isValid():
            feedback.reportError(f"Failed to load layer (URL: {layer_url})")
            return None
        return vector_layer

    def _set_vector_layer_crs(self, vector_layer, service_meta, layer_meta, feedback):
        spatial_ref = (
            (layer_meta.get("extent") or {}).get("spatialReference")
            or layer_meta.get("spatialReference")
            or service_meta.get("spatialReference", {})
        )
        layer_crs = self._crs_from_esri_spatial_ref(spatial_ref, feedback)
        if layer_crs and layer_crs.isValid():
            vector_layer.setCrs(layer_crs)
            feedback.pushInfo(f"Layer CRS set to: {layer_crs.authid()}")
        else:
            feedback.pushInfo(f"Layer CRS: {vector_layer.crs().authid()}")

    def _load_as_arcgis_layer(self, url, dataset, has_prefecture, pref_idx, feedback):
        try:
            resolved = self._resolve_layer_url_and_meta(url, feedback)
            if not resolved:
                return None
            layer_url, service_meta, layer_meta = resolved

            layer_name = self._build_layer_name(dataset, has_prefecture, pref_idx)
            vector_layer = self._create_arcgis_vector_layer(
                layer_url, layer_name, feedback
            )
            if vector_layer is None:
                return None

            self._set_vector_layer_crs(
                vector_layer,
                service_meta,
                layer_meta,
                feedback,
            )
            project = QgsProject.instance()
            project.setCrs(project.crs())

            QgsProject.instance().addMapLayer(vector_layer)
            feedback.pushInfo(f"Successfully loaded layer: {layer_name}")
            return vector_layer.id()

        except Exception as e:
            feedback.reportError(f"Error loading layer: {str(e)}")
            import traceback

            feedback.reportError(traceback.format_exc())
            return None

    def _save_to_file(self, url, parameters, context, feedback):
        try:
            import os
            import re

            resolved = self._resolve_layer_url_and_meta(url, feedback)
            if not resolved:
                return None
            layer_url, service_meta, layer_meta = resolved

            vector_layer = self._create_arcgis_vector_layer(layer_url, "temp", feedback)
            if vector_layer is None:
                return None

            self._set_vector_layer_crs(
                vector_layer,
                service_meta,
                layer_meta,
                feedback,
            )

            cleaned_fields = QgsFields()
            for field in vector_layer.fields():
                new_field = QgsField(field)
                new_field.setAlias("")
                new_field.setComment("")
                cleaned_fields.append(new_field)

            final_output_crs = vector_layer.crs()

            (sink, dest_id) = self.parameterAsSink(
                parameters,
                self.OUTPUT,
                context,
                cleaned_fields,
                vector_layer.wkbType(),
                final_output_crs,
                QgsFeatureSink.SinkFlags(),
            )

            if sink is None:
                feedback.reportError(self.tr("出力レイヤの作成に失敗しました"))
                return None

            feedback.pushInfo(
                f"Output CRS: {final_output_crs.authid() if final_output_crs.isValid() else 'Unknown'}"
            )

            total = vector_layer.featureCount()
            feedback.pushInfo(f"Writing {total} features to output...")

            processed = 0
            needs_transform = final_output_crs.isValid() and (
                final_output_crs.authid() != vector_layer.crs().authid()
            )
            if needs_transform:
                feedback.pushInfo(
                    f"Reprojecting on save: {vector_layer.crs().authid()} → {final_output_crs.authid()}"
                )
                transform = QgsCoordinateTransform(
                    vector_layer.crs(),
                    final_output_crs,
                    QgsProject.instance().transformContext(),
                )
            else:
                transform = None

            for feature in vector_layer.getFeatures():
                if feedback.isCanceled():
                    break
                new_f = QgsFeature(feature)
                if transform and new_f.hasGeometry():
                    try:
                        geom = new_f.geometry()
                        if not geom.isEmpty():
                            geom.transform(transform)
                            new_f.setGeometry(geom)
                    except Exception as e:
                        feedback.pushInfo(
                            f"Skipping feature due to transform error: {str(e)}"
                        )
                        continue
                sink.addFeature(new_f, QgsFeatureSink.FastInsert)
                processed += 1
                if total > 0:
                    feedback.setProgress(int((processed / total) * 100))

            feedback.pushInfo(f"Successfully wrote {processed} features")

            dest_str = dest_id or ""
            output_path = dest_str.split("|", 1)[0] if "|" in dest_str else dest_str

            if output_path and output_path.startswith("ogr:"):
                m = re.search(r"dbname='?([^' ]+)'?", output_path)
                if m:
                    output_path = m.group(1)

            if output_path and output_path not in ("memory:", ""):
                base, _ = os.path.splitext(output_path)
                qml_path = base + ".qml"
                res, err = vector_layer.saveNamedStyle(qml_path)
                if res:
                    feedback.pushInfo(f"Saved style file: {qml_path}")
                else:
                    feedback.reportError(f"Failed to save style to {qml_path}: {err}")
            else:
                feedback.pushInfo(
                    "Could not determine output file path; skipped writing .qml style."
                )

            return dest_id

        except Exception as e:
            feedback.reportError(f"Error saving layer: {str(e)}")
            import traceback

            feedback.reportError(traceback.format_exc())
            return None

    def _crs_from_esri_spatial_ref(self, spatial_ref, feedback):
        if not spatial_ref:
            return None

        try:
            wkid = spatial_ref.get("latestWkid") or spatial_ref.get("wkid")

            esri_to_epsg = {
                102100: 3857,
                102113: 3857,
            }
            if wkid in esri_to_epsg:
                wkid = esri_to_epsg[wkid]

            if wkid:
                wkid_int = int(wkid)
                crs = QgsCoordinateReferenceSystem.fromEpsgId(wkid_int)
                if crs.isValid():
                    return crs

            wkt = spatial_ref.get("wkt") or spatial_ref.get("latestWkt")
            if wkt:
                crs = QgsCoordinateReferenceSystem()
                if crs.createFromWkt(wkt):
                    return crs
        except Exception as e:
            feedback.reportError(f"CRS parse error: {str(e)}")

        return None

    def shortHelpString(self):
        return self.tr(
            "環境省が提供する地理空間情報ポータルサイト「環境ジオポータル」のデータをQGISに直接読み込むためのプラグインです。\n"
            "データセットを選択すると、ArcGIS Feature Serviceレイヤとして、設定されたスタイル付きで読み込まれます。\n"
            "必要に応じてファイル保存も同時に行うことができ、保存時にはスタイルも自動的に保存されます。"
        )

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
