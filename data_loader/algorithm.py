import contextlib
import os
import re
import tempfile

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsFeatureSink,
    QgsField,
    QgsFields,
    QgsProcessingAlgorithm,
    QgsProcessingContext,
    QgsProcessingException,
    QgsProcessingLayerPostProcessorInterface,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterCrs,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSink,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QCoreApplication

from .feature_downloader import FeatureDownloader
from .network import get_json
from .settings_datasets import DATASETS
from .settings_prefecture import PREFECTURE_NAMES_EN, PREFECTURES


class _StylePostProcessor(QgsProcessingLayerPostProcessorInterface):
    _instance = None

    def __init__(self, qml_path, remove_after=False):
        super().__init__()
        self.qml_path = qml_path
        self.remove_after = remove_after
        _StylePostProcessor._instance = self

    def postProcessLayer(self, layer, context, feedback):
        if not self.qml_path or not os.path.exists(self.qml_path):
            return
        message, ok = layer.loadNamedStyle(self.qml_path)
        if ok:
            layer.triggerRepaint()
            feedback.pushInfo(f"Applied style to layer: {layer.name()}")
        else:
            feedback.pushWarning(f"Failed to apply style: {message}")
        if self.remove_after:
            with contextlib.suppress(OSError):
                os.remove(self.qml_path)


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

    def createCustomParametersWidget(self, parent=None):
        # Imported only when needed: qgis_process, which also loads this
        # module, has no GUI
        try:
            from .dialog import MOELoaderDialog
        except ImportError:
            # The Processing plugin may rename its dialog again (see dialog.py):
            # QGIS then opens its own dialog, where the prefecture is always enabled
            return None
        return MOELoaderDialog(self, parent=parent)

    def processAlgorithm(self, parameters, context, feedback):
        dataset_idx = self.parameterAsEnum(parameters, self.CATEGORY, context)
        dataset_key, has_prefecture = self._dataset_mapping[dataset_idx]

        dataset = DATASETS[dataset_key]
        url = dataset["url"]

        if has_prefecture:
            pref_idx = self.parameterAsEnum(parameters, self.PREFECTURE, context)
            pref_code = list(PREFECTURES.keys())[pref_idx]
            pref_name = PREFECTURE_NAMES_EN[pref_code]
            url = url.format(pref_code=pref_code, pref_name=pref_name)

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
            raise QgsProcessingException(
                self.tr("Please specify the save location for the output layer.")
            )

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
            # Qt can also open file:// URLs, so only allow HTTP(S)
            if not url.startswith(("https://", "http://")):
                raise ValueError(f"Unsupported URL scheme: {url}")
            data = get_json(url, feedback)
        except (OSError, ValueError) as e:
            raise QgsProcessingException(f"{error_context}: {e}") from e

        # ArcGIS reports errors such as "499 Token Required" in the JSON body
        error = data.get("error") if isinstance(data, dict) else None
        if error:
            raise QgsProcessingException(
                f"{error_context}: {error.get('code')} {error.get('message')}"
            )
        return data

    def _resolve_layer_url_and_meta(self, url, feedback):
        service_meta = self._fetch_json(
            f"{url}?f=json", feedback, "Failed to fetch FeatureServer metadata"
        )
        layers = service_meta.get("layers", [])
        if not layers:
            raise QgsProcessingException(f"No layers found in FeatureServer: {url}")

        first_layer = layers[0]
        layer_id = first_layer.get("id")
        layer_url = f"{url}/{layer_id}"

        try:
            layer_meta = self._fetch_json(
                f"{layer_url}?f=json", feedback, "Failed to fetch layer metadata"
            )
        except QgsProcessingException as e:
            # Only used for the CRS and page size; the layer itself still loads
            feedback.pushWarning(str(e))
            layer_meta = {}

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
            raise QgsProcessingException(f"Failed to load layer (URL: {layer_url})")
        return vector_layer

    def _open_feature_stream(self, layer_url, vector_layer, layer_meta, feedback):
        # Much faster than vector_layer.getFeatures(), which fetches 100 at a time
        return FeatureDownloader(
            layer_url,
            vector_layer.fields(),
            vector_layer.wkbType(),
            feedback,
            page_size=layer_meta.get("maxRecordCount"),
        )

    def _set_vector_layer_crs(self, vector_layer, service_meta, layer_meta, feedback):
        extent_ref = (layer_meta.get("extent") or {}).get("spatialReference")
        layer_ref = layer_meta.get("spatialReference")
        service_ref = service_meta.get("spatialReference", {})
        spatial_ref = extent_ref or layer_ref or service_ref

        esri_crs = self._crs_from_esri_spatial_ref(spatial_ref, feedback)

        # Only the CRS the service data is in: setCrs() relabels coordinates
        # without reprojecting them, so the user-specified CRS must not go here.
        if esri_crs and esri_crs.isValid():
            layer_crs = esri_crs
            feedback.pushInfo(f"Using ESRI-defined CRS: {layer_crs.authid()}")
        else:
            feedback.pushInfo(
                f"No valid CRS found, using layer default: {vector_layer.crs().authid()}"
            )
            return

        vector_layer.setCrs(layer_crs)

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
        layer_url, service_meta, layer_meta = self._resolve_layer_url_and_meta(
            url, feedback
        )
        layer_name = self._build_layer_name(dataset, has_prefecture, pref_idx)
        vector_layer = self._create_arcgis_vector_layer(layer_url, layer_name, feedback)

        self._set_vector_layer_crs(vector_layer, service_meta, layer_meta, feedback)

        param_crs = self.parameterAsCrs(parameters, self.CRS, context)
        if param_crs.isValid() and param_crs != vector_layer.crs():
            feedback.pushWarning(
                f"Output CRS {param_crs.authid()} is not applied to ArcGIS "
                "layers; QGIS reprojects them on the fly."
            )

        # processAlgorithm runs in a background thread, so hand the layer to
        # QGIS, which adds it to the project on the main thread afterwards
        context.temporaryLayerStore().addMapLayer(vector_layer)
        context.addLayerToLoadOnCompletion(
            vector_layer.id(),
            QgsProcessingContext.LayerDetails(
                layer_name, context.project(), self.OUTPUT
            ),
        )
        feedback.pushInfo(f"Successfully loaded layer: {layer_name}")
        return vector_layer.id()

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
        layer_url, service_meta, layer_meta = self._resolve_layer_url_and_meta(
            url, feedback
        )
        vector_layer = self._create_arcgis_vector_layer(layer_url, "temp", feedback)

        self._set_vector_layer_crs(vector_layer, service_meta, layer_meta, feedback)

        source_crs = vector_layer.crs()
        param_crs = self.parameterAsCrs(parameters, self.CRS, context)
        if param_crs.isValid() and param_crs != source_crs:
            if not source_crs.isValid():
                raise QgsProcessingException(
                    "Cannot reproject to the output CRS: the source CRS is unknown."
                )
            final_output_crs = param_crs
            feedback.pushInfo(
                f"Reprojecting on save: {source_crs.authid()} → {final_output_crs.authid()}"
            )
            transform = QgsCoordinateTransform(
                source_crs, final_output_crs, context.transformContext()
            )
        else:
            final_output_crs = source_crs
            transform = None

        cleaned_fields = QgsFields()
        for field in vector_layer.fields():
            new_field = QgsField(field)
            new_field.setAlias("")
            new_field.setComment("")
            cleaned_fields.append(new_field)

        (sink, dest_id) = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context,
            cleaned_fields,
            vector_layer.wkbType(),
            final_output_crs,
        )

        if sink is None:
            raise QgsProcessingException(self.tr("Failed to create output layer."))

        feedback.pushInfo(
            f"Output CRS: {final_output_crs.authid() if final_output_crs.isValid() else 'Unknown'}"
        )

        features = self._open_feature_stream(
            layer_url, vector_layer, layer_meta, feedback
        )
        total = len(features)
        feedback.pushInfo(f"Writing {total} features to output...")

        processed = 0
        for feature in features:
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
                    feedback.pushWarning(
                        f"Skipping feature due to transform error: {str(e)}"
                    )
                    continue
            sink.addFeature(new_f, QgsFeatureSink.Flag.FastInsert)
            processed += 1
            if total > 0:
                feedback.setProgress(int((processed / total) * 100))

        feedback.pushInfo(f"Successfully wrote {processed} features")

        del sink

        output_path = self._extract_output_path(dest_id)
        is_file_output = bool(output_path) and os.path.isabs(output_path)

        # QGIS registers the output when "Open output file after running
        # algorithm" is checked and loads it on the main thread afterwards
        will_load = context.willLoadLayerOnCompletion(dest_id)
        if not (is_file_output or will_load):
            return dest_id

        layer_name = self._build_layer_name(dataset, has_prefecture, pref_idx)
        # A .qml next to the output belongs to the whole file, so the tables of
        # one GeoPackage would overwrite each other's style: when the format
        # can, store the style in the table itself
        output_layer = (
            self._open_style_storing_output(dest_id) if is_file_output else None
        )
        next_to_output = is_file_output and output_layer is None
        qml_path = self._save_style_qml(
            vector_layer, output_path, dataset_key, next_to_output, feedback
        )
        if qml_path and output_layer is not None:
            self._save_style_in_output(output_layer, qml_path, layer_name, feedback)

        if will_load:
            details = context.layerToLoadOnCompletionDetails(dest_id)
            details.name = layer_name
            if qml_path:
                details.setPostProcessor(
                    _StylePostProcessor(qml_path, remove_after=not next_to_output)
                )
        elif qml_path and not next_to_output:
            with contextlib.suppress(OSError):
                os.remove(qml_path)
        return dest_id

    def _open_style_storing_output(self, dest_id):
        """The output layer if its format can store styles, as GeoPackage can."""
        options = QgsVectorLayer.LayerOptions()
        options.loadDefaultStyle = False
        output_layer = QgsVectorLayer(dest_id, "output", "ogr", options)
        if output_layer.isValid() and (
            output_layer.dataProvider().styleStorageCapabilities()
            & Qgis.ProviderStyleStorageCapability.SaveToDatabase
        ):
            return output_layer
        return None

    def _save_style_in_output(self, output_layer, qml_path, style_name, feedback):
        message, ok = output_layer.loadNamedStyle(qml_path)
        if ok:
            # Stored as the table's default style, which QGIS applies when opening it
            if hasattr(output_layer, "saveStyleToDatabaseV2"):
                _, message = output_layer.saveStyleToDatabaseV2(
                    style_name, "", True, ""
                )
            else:  # QGIS 3.44.0
                message = output_layer.saveStyleToDatabase(style_name, "", True, "")
            ok = not message

        if ok:
            feedback.pushInfo(f"Saved style in the output: {output_layer.source()}")
        else:
            feedback.reportError(
                f"Failed to save style in {output_layer.source()}: {message}"
            )

    def _save_style_qml(
        self, vector_layer, output_path, dataset_key, next_to_output, feedback
    ):
        if next_to_output:
            base, _ = os.path.splitext(output_path)
            qml_path = base + ".qml"
        else:
            fd, qml_path = tempfile.mkstemp(suffix=".qml")
            os.close(fd)

        # Use bundled QML if available
        bundled_qml = self._get_bundled_qml(dataset_key)
        if bundled_qml:
            import shutil

            shutil.copy2(bundled_qml, qml_path)
            feedback.pushInfo(f"Using bundled style: {bundled_qml}")
            from .style_converter import convert_rasterfill_qml

            if convert_rasterfill_qml(qml_path):
                feedback.pushInfo("Converted RasterFill to native symbols")
            return qml_path

        message, ok = vector_layer.saveNamedStyle(qml_path)
        if ok:
            feedback.pushInfo(f"Saved style file: {qml_path}")
            return qml_path

        feedback.reportError(f"Failed to save style to {qml_path}: {message}")
        if not next_to_output:
            with contextlib.suppress(OSError):
                os.remove(qml_path)
        return None

    def _get_bundled_qml(self, dataset_key):
        # The official style files keep their published names, so several
        # datasets can share one, like the eight blocks of the 2024 map
        style = DATASETS.get(dataset_key, {}).get("style")
        if not style:
            return None
        qml_path = os.path.join(os.path.dirname(__file__), "styles", style)
        if os.path.exists(qml_path):
            return qml_path
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
