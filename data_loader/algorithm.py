import json
import os
import re
import tempfile
import traceback
from pathlib import Path
from urllib.request import urlopen

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsFeatureSink,
    QgsField,
    QgsFields,
    QgsProcessingAlgorithm,
    QgsProcessingContext,
    QgsProcessingLayerPostProcessorInterface,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterCrs,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSink,
    QgsProject,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QCoreApplication, QUrl

from .settings_datasets import DATASETS
from .settings_prefecture import PREFECTURES


class _StylePostProcessor(QgsProcessingLayerPostProcessorInterface):
    _instance = None

    def __init__(self, qml_path):
        super().__init__()
        self.qml_path = qml_path
        _StylePostProcessor._instance = self

    def postProcessLayer(self, layer, context, feedback):
        if self.qml_path and os.path.exists(self.qml_path):
            ok, err = layer.loadNamedStyle(self.qml_path)
            if ok:
                layer.triggerRepaint()
                feedback.pushInfo(f"Applied style to layer: {layer.name()}")
            else:
                feedback.pushInfo(f"Failed to apply style: {err}")


class MOELoaderAlgorithm(QgsProcessingAlgorithm):
    DATASET = "DATASET"
    CATEGORY = "CATEGORY"
    PREFECTURE = "PREFECTURE"
    CRS = "CRS"
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
                self.tr("Dataset"),
                options=dataset_options,
                defaultValue=0,
            )
        )

        prefecture_names = list(PREFECTURES.values())
        self.addParameter(
            QgsProcessingParameterEnum(
                self.PREFECTURE,
                self.tr("Prefectures"),
                options=prefecture_names,
                optional=True,
                defaultValue=None,
            )
        )

        self.addParameter(
            QgsProcessingParameterCrs(
                self.CRS,
                self.tr("Output coordinate system"),
                optional=True,
                defaultValue=None,
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.ADD_AS_ARCGIS_LAYER,
                self.tr("Add as ArcGIS REST Server layer"),
                optional=True,
                defaultValue=False,
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr("Output layer"),
                createByDefault=False,
            )
        )

    def checkParameterValues(self, parameters, context):
        dataset_idx = self.parameterAsEnum(parameters, self.CATEGORY, context)
        _, has_prefecture = self._dataset_mapping[dataset_idx]

        if has_prefecture:
            raw_value = parameters.get(self.PREFECTURE)
            if raw_value is None or raw_value == "":
                return False, self.tr("Please select a prefecture.")

        return super().checkParameterValues(parameters, context)

    def processAlgorithm(self, parameters, context, feedback):
        dataset_idx = self.parameterAsEnum(parameters, self.CATEGORY, context)
        dataset_key, has_prefecture = self._dataset_mapping[dataset_idx]

        dataset = DATASETS[dataset_key]
        url = dataset["url"]

        if has_prefecture:
            pref_idx = self.parameterAsEnum(parameters, self.PREFECTURE, context)
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
                parameters,
                context,
                feedback,
            )
            return {"OUTPUT": layer_id}

        if not parameters.get(self.OUTPUT):
            feedback.reportError(
                self.tr("Please specify the save location for the output layer.")
            )
            return {"OUTPUT": None}

        file_output = self._save_to_file(
            url,
            parameters,
            context,
            feedback,
            dataset=dataset,
            dataset_key=dataset_key,
            has_prefecture=has_prefecture,
            pref_idx=pref_idx if has_prefecture else None,
        )
        return {"OUTPUT": file_output}

    def _fetch_json(self, url, feedback, error_context):
        try:
            if not url.startswith(("https://", "http://")):
                raise ValueError(f"Unsupported URL scheme: {url}")
            with urlopen(url) as response:  # noqa: S310  # nosec B310 - scheme validated above
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

        # fmt: off
        layer_meta = self._fetch_json(
            f"{layer_url}?f=json", feedback, "Failed to fetch layer metadata"
        ) or {}
        # fmt: on

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

    def _set_vector_layer_crs(
        self, vector_layer, service_meta, layer_meta, parameters, context, feedback
    ):
        extent_ref = (layer_meta.get("extent") or {}).get("spatialReference")
        layer_ref = layer_meta.get("spatialReference")
        service_ref = service_meta.get("spatialReference", {})
        spatial_ref = extent_ref or layer_ref or service_ref

        esri_crs = self._crs_from_esri_spatial_ref(spatial_ref, feedback)

        # Prioritize the CRS specified by the user
        param_crs = self.parameterAsCrs(parameters, self.CRS, context)

        if param_crs and param_crs.isValid():
            layer_crs = param_crs
            feedback.pushInfo(f"Using user-specified CRS: {layer_crs.authid()}")
        elif esri_crs and esri_crs.isValid():
            layer_crs = esri_crs
            feedback.pushInfo(f"Using ESRI-defined CRS: {layer_crs.authid()}")
        else:
            feedback.pushInfo(
                f"No valid CRS found, using layer default: {vector_layer.crs().authid()}"
            )
            return

        vector_layer.setCrs(layer_crs)

    def _report_exception(self, feedback, message, exception):
        feedback.reportError(f"{message}: {str(exception)}")
        feedback.reportError(traceback.format_exc())

    def _extract_output_path(self, dest_id):
        dest_str = dest_id or ""
        output_path = dest_str.split("|", 1)[0] if "|" in dest_str else dest_str

        if output_path and output_path.startswith("ogr:"):
            m = re.search(r"dbname='?([^' ]+)'?", output_path)
            if m:
                output_path = m.group(1)

        return output_path

    def _load_as_arcgis_layer(
        self, url, dataset, has_prefecture, pref_idx, parameters, context, feedback
    ):
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
                parameters,
                context,
                feedback,
            )

            QgsProject.instance().addMapLayer(vector_layer)
            feedback.pushInfo(f"Successfully loaded layer: {layer_name}")
            return vector_layer.id()

        except Exception as e:
            self._report_exception(feedback, "Error loading layer", e)
            return None

    def _save_to_file(
        self,
        url,
        parameters,
        context,
        feedback,
        dataset=None,
        dataset_key=None,
        has_prefecture=False,
        pref_idx=None,
    ):
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
            parameters,
            context,
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
            feedback.reportError(self.tr("Failed to create output layer."))
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

        del sink

        output_path = self._extract_output_path(dest_id)

        # Build layer name
        layer_name = self._build_layer_name(dataset, has_prefecture, pref_idx)

        # Check if this is a real file path (absolute path)
        is_file_output = output_path and os.path.isabs(output_path)

        # Save style QML
        qml_path = self._save_style_qml(
            vector_layer, output_path, dataset_key, is_file_output, feedback
        )

        if is_file_output:
            # Load the saved layer and add it to the project with style
            try:
                saved_layer = QgsVectorLayer(output_path, layer_name, "ogr")
                if saved_layer.isValid():
                    QgsProject.instance().addMapLayer(saved_layer)
                    feedback.pushInfo(f"Added layer to project: {layer_name}")
                    context.addLayerToLoadOnCompletion(
                        saved_layer.id(),
                        QgsProcessingContext.LayerDetails(
                            layer_name, QgsProject.instance(), self.OUTPUT
                        ),
                    )
                else:
                    feedback.reportError(f"Could not load saved layer: {output_path}")
            except Exception as e:
                self._report_exception(feedback, "Error loading saved layer", e)
        else:
            # For memory layers: apply style via post-processor
            feedback.pushInfo(f"Setting layer name to: {layer_name}")
            details = QgsProcessingContext.LayerDetails(
                layer_name, QgsProject.instance(), self.OUTPUT
            )
            if qml_path:
                details.setPostProcessor(_StylePostProcessor(qml_path))
            context.addLayerToLoadOnCompletion(dest_id, details)

        return dest_id

    def _save_style_qml(
        self, vector_layer, output_path, dataset_key, is_file_output, feedback
    ):
        if is_file_output:
            base, _ = os.path.splitext(output_path)
            qml_path = base + ".qml"
        else:
            fd, qml_path = tempfile.mkstemp(suffix=".qml")
            os.close(fd)

        res, err = vector_layer.saveNamedStyle(qml_path)
        if res:
            feedback.pushInfo(f"Saved style file: {qml_path}")
            if dataset_key == "vg_50000":
                from .style_converter import convert_rasterfill_qml

                if convert_rasterfill_qml(qml_path):
                    feedback.pushInfo("Converted RasterFill to native symbols")
            return qml_path
        else:
            feedback.reportError(f"Failed to save style to {qml_path}: {err}")
            return None

    def _crs_from_esri_spatial_ref(self, spatial_ref, feedback):
        if not spatial_ref:
            return None

        wkid = spatial_ref.get("latestWkid") or spatial_ref.get("wkid")
        if wkid is not None:
            esri_to_epsg = {
                102100: 3857,
                102113: 3857,
            }
            wkid = esri_to_epsg.get(wkid, wkid)

            if wkid is not None:
                try:
                    wkid_int = int(wkid)
                    crs = QgsCoordinateReferenceSystem.fromEpsgId(wkid_int)
                    if crs.isValid():
                        return crs
                except (ValueError, TypeError) as e:
                    feedback.reportError(f"Invalid WKID format: {wkid} - {str(e)}")

        wkt = spatial_ref.get("wkt") or spatial_ref.get("latestWkt")
        if wkt:
            crs = QgsCoordinateReferenceSystem()
            if crs.createFromWkt(wkt):
                return crs

        return None

    def _file_path_from_source(self, layer):
        src = layer.source() or ""
        base = src.split("|", 1)[0]
        if base.startswith("file:"):
            base = QUrl(base).toLocalFile()
        return base

    def _apply_qml_if_exists(self, layer, feedback):
        path = self._file_path_from_source(layer)
        if not path:
            return
        p = Path(path)
        if not p.exists():
            return
        candidates = [p.with_suffix(".qml")]
        if p.suffix.lower() in [".gpkg", ".sqlite"]:
            candidates.append(p.parent / f"{p.stem}_{layer.name()}.qml")
        for qml in candidates:
            if qml.exists():
                ok, err = layer.loadNamedStyle(str(qml))
                if ok:
                    layer.triggerRepaint()
                    feedback.pushInfo(f"Applied QML style: {qml}")
                else:
                    feedback.pushInfo(f"Failed to apply QML style: {err}")
                break

    def shortHelpString(self):
        return self.tr(
            'This is a plugin to directly load data from the "<a href="https://geoportal.env.go.jp/">Environmental GeoPortal</a>," a geospatial information portal site provided by the Ministry of the Environment, into QGIS.\n'
            "When you select the dataset and output destination, the file and style settings are automatically saved.\n"
            "If necessary, it can be loaded as an ArcGIS Feature Service layer."
        )

    def name(self):
        return "moe_geoportal_loader"

    def displayName(self):
        return self.tr("Load the data from Environmental GeoPortal")

    def group(self):
        return None

    def groupId(self):
        return None

    def tr(self, string):
        return QCoreApplication.translate("MOELoaderAlgorithm", string)

    def createInstance(self):
        return MOELoaderAlgorithm()
