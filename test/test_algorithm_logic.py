import json
import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsCoordinateTransformContext,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsProcessingContext,
    QgsProcessingException,
    QgsProcessingOutputLayerDefinition,
    QgsProject,
    QgsVectorLayer,
)
from qgis.PyQt.QtGui import QColor
from qgis.testing import start_app

from data_loader.algorithm import MOELoaderAlgorithm, _StylePostProcessor
from data_loader.settings_prefecture import PREFECTURES

# Check if PROJ database is available for CRS tests
_CRS_AVAILABLE = QgsCoordinateReferenceSystem.fromEpsgId(4326).isValid()


class TestExtractOutputPath(unittest.TestCase):
    """Tests for MOELoaderAlgorithm._extract_output_path"""

    def setUp(self):
        self.alg = MOELoaderAlgorithm()

    def test_simple_file_path(self):
        result = self.alg._extract_output_path("/tmp/output.gpkg")
        self.assertEqual(result, "/tmp/output.gpkg")

    def test_path_with_pipe_separator(self):
        result = self.alg._extract_output_path("/tmp/output.gpkg|layername=foo")
        self.assertEqual(result, "/tmp/output.gpkg")

    def test_ogr_dbname_with_quotes(self):
        result = self.alg._extract_output_path(
            "ogr:dbname='/tmp/out.gpkg' table='layer'"
        )
        self.assertEqual(result, "/tmp/out.gpkg")

    def test_ogr_dbname_without_quotes(self):
        result = self.alg._extract_output_path("ogr:dbname=/tmp/out.gpkg table='layer'")
        self.assertEqual(result, "/tmp/out.gpkg")

    def test_none_input(self):
        result = self.alg._extract_output_path(None)
        self.assertEqual(result, "")

    def test_empty_string(self):
        result = self.alg._extract_output_path("")
        self.assertEqual(result, "")

    def test_memory_output(self):
        result = self.alg._extract_output_path("memory:")
        self.assertEqual(result, "memory:")

    def test_pipe_at_start(self):
        result = self.alg._extract_output_path("|layername=foo")
        self.assertEqual(result, "")


class TestBuildLayerName(unittest.TestCase):
    """Tests for MOELoaderAlgorithm._build_layer_name"""

    def setUp(self):
        self.alg = MOELoaderAlgorithm()

    def test_no_prefecture(self):
        dataset = {"name": "サンゴ礁調査"}
        result = self.alg._build_layer_name(dataset, False, None)
        self.assertEqual(result, "サンゴ礁調査")

    def test_with_prefecture_hokkaido(self):
        dataset = {"name": "植生図 - 都道府県別"}
        result = self.alg._build_layer_name(dataset, True, 0)
        expected_pref = list(PREFECTURES.values())[0]  # 北海道
        self.assertEqual(result, f"{expected_pref}_植生図")

    def test_with_prefecture_tokyo(self):
        dataset = {"name": "自然度 - 都道府県別"}
        tokyo_idx = list(PREFECTURES.keys()).index("13")
        result = self.alg._build_layer_name(dataset, True, tokyo_idx)
        self.assertEqual(result, "東京都_自然度")

    def test_strip_prefecture_suffix_no_prefecture_flag(self):
        dataset = {"name": "自然度 - 都道府県別"}
        result = self.alg._build_layer_name(dataset, False, None)
        self.assertEqual(result, "自然度")

    def test_name_without_suffix(self):
        dataset = {"name": "全国クマ類分布"}
        result = self.alg._build_layer_name(dataset, False, None)
        self.assertEqual(result, "全国クマ類分布")

    def test_has_prefecture_but_pref_idx_none(self):
        dataset = {"name": "植生図 - 都道府県別"}
        result = self.alg._build_layer_name(dataset, True, None)
        self.assertEqual(result, "植生図")

    def test_last_prefecture_okinawa(self):
        dataset = {"name": "植生図 - 都道府県別"}
        okinawa_idx = list(PREFECTURES.keys()).index("47")
        result = self.alg._build_layer_name(dataset, True, okinawa_idx)
        self.assertEqual(result, "沖縄県_植生図")


class TestCrsFromEsriSpatialRefLogic(unittest.TestCase):
    """Tests for _crs_from_esri_spatial_ref logic (WKID mapping, fallback chain).

    Uses mocks so tests pass regardless of PROJ database availability.
    """

    def setUp(self):
        self.alg = MOELoaderAlgorithm()
        self.feedback = MagicMock()

    def test_none_input(self):
        crs = self.alg._crs_from_esri_spatial_ref(None, self.feedback)
        self.assertIsNone(crs)

    def test_empty_dict(self):
        crs = self.alg._crs_from_esri_spatial_ref({}, self.feedback)
        self.assertIsNone(crs)

    def test_invalid_wkid_string(self):
        crs = self.alg._crs_from_esri_spatial_ref({"wkid": "abc"}, self.feedback)
        self.assertIsNone(crs)
        self.feedback.reportError.assert_called()

    def test_esri_102100_mapped_to_3857(self):
        mock_crs = MagicMock()
        mock_crs.isValid.return_value = True
        mock_crs.authid.return_value = "EPSG:3857"
        with patch(
            "qgis.core.QgsCoordinateReferenceSystem.fromEpsgId",
            return_value=mock_crs,
        ) as mock_from:
            crs = self.alg._crs_from_esri_spatial_ref({"wkid": 102100}, self.feedback)
            mock_from.assert_called_with(3857)
            self.assertIsNotNone(crs)

    def test_esri_102113_mapped_to_3857(self):
        mock_crs = MagicMock()
        mock_crs.isValid.return_value = True
        with patch(
            "qgis.core.QgsCoordinateReferenceSystem.fromEpsgId",
            return_value=mock_crs,
        ) as mock_from:
            self.alg._crs_from_esri_spatial_ref({"wkid": 102113}, self.feedback)
            mock_from.assert_called_with(3857)

    def test_standard_wkid_passed_directly(self):
        mock_crs = MagicMock()
        mock_crs.isValid.return_value = True
        with patch(
            "qgis.core.QgsCoordinateReferenceSystem.fromEpsgId",
            return_value=mock_crs,
        ) as mock_from:
            self.alg._crs_from_esri_spatial_ref({"wkid": 4326}, self.feedback)
            mock_from.assert_called_with(4326)

    def test_latest_wkid_takes_priority_over_wkid(self):
        mock_crs = MagicMock()
        mock_crs.isValid.return_value = True
        with patch(
            "qgis.core.QgsCoordinateReferenceSystem.fromEpsgId",
            return_value=mock_crs,
        ) as mock_from:
            self.alg._crs_from_esri_spatial_ref(
                {"latestWkid": 4326, "wkid": 102100}, self.feedback
            )
            # latestWkid=4326 is used, not wkid=102100 mapped to 3857
            mock_from.assert_called_with(4326)

    def test_wkt_fallback_when_no_wkid(self):
        wkt = (
            'GEOGCS["GCS_WGS_1984",'
            'DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],'
            'PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]]'
        )
        mock_crs = MagicMock()
        mock_crs.createFromWkt.return_value = True
        with patch(
            "data_loader.algorithm.QgsCoordinateReferenceSystem",
            return_value=mock_crs,
        ):
            crs = self.alg._crs_from_esri_spatial_ref({"wkt": wkt}, self.feedback)
            mock_crs.createFromWkt.assert_called_once_with(wkt)
            self.assertIsNotNone(crs)

    def test_latest_wkt_used_when_wkt_absent(self):
        wkt = 'GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]]'
        mock_crs = MagicMock()
        mock_crs.createFromWkt.return_value = True
        with patch(
            "data_loader.algorithm.QgsCoordinateReferenceSystem",
            return_value=mock_crs,
        ):
            crs = self.alg._crs_from_esri_spatial_ref({"latestWkt": wkt}, self.feedback)
            mock_crs.createFromWkt.assert_called_once_with(wkt)
            self.assertIsNotNone(crs)

    def test_returns_none_when_wkid_invalid_and_no_wkt(self):
        invalid_crs = MagicMock()
        invalid_crs.isValid.return_value = False
        with patch(
            "qgis.core.QgsCoordinateReferenceSystem.fromEpsgId",
            return_value=invalid_crs,
        ):
            crs = self.alg._crs_from_esri_spatial_ref({"wkid": 999999}, self.feedback)
            self.assertIsNone(crs)


@unittest.skipUnless(_CRS_AVAILABLE, "PROJ database not available")
class TestCrsFromEsriSpatialRefIntegration(unittest.TestCase):
    """Integration tests using real CRS creation (requires PROJ database)."""

    def setUp(self):
        self.alg = MOELoaderAlgorithm()
        self.feedback = MagicMock()

    def test_real_crs_4326(self):
        crs = self.alg._crs_from_esri_spatial_ref({"wkid": 4326}, self.feedback)
        self.assertIsNotNone(crs)
        self.assertTrue(crs.isValid())  # type: ignore
        self.assertEqual(crs.authid(), "EPSG:4326")  # type: ignore

    def test_real_crs_102100_to_3857(self):
        crs = self.alg._crs_from_esri_spatial_ref({"wkid": 102100}, self.feedback)
        self.assertIsNotNone(crs)
        self.assertEqual(crs.authid(), "EPSG:3857")  # type: ignore

    def test_real_crs_jgd2011(self):
        crs = self.alg._crs_from_esri_spatial_ref({"wkid": 6690}, self.feedback)
        self.assertIsNotNone(crs)
        self.assertTrue(crs.isValid())  # type: ignore


class TestFetchJson(unittest.TestCase):
    """Tests for MOELoaderAlgorithm._fetch_json"""

    def setUp(self):
        self.alg = MOELoaderAlgorithm()
        self.feedback = MagicMock()

    @patch("data_loader.algorithm.urlopen")
    def test_valid_json_response(self, mock_urlopen):
        expected = {"layers": [{"id": 0}]}
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(expected).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = self.alg._fetch_json(
            "https://example.com/api?f=json", self.feedback, "test"
        )
        self.assertEqual(result, expected)

    def test_rejects_ftp_scheme(self):
        with self.assertRaises(QgsProcessingException):
            self.alg._fetch_json("ftp://example.com/data", self.feedback, "test")

    def test_rejects_file_scheme(self):
        with self.assertRaises(QgsProcessingException):
            self.alg._fetch_json("file:///etc/passwd", self.feedback, "test")

    def test_rejects_javascript_scheme(self):
        with self.assertRaises(QgsProcessingException):
            self.alg._fetch_json("javascript:alert(1)", self.feedback, "test")

    @patch("data_loader.algorithm.urlopen")
    def test_network_error(self, mock_urlopen):
        mock_urlopen.side_effect = ConnectionError("Connection refused")
        with self.assertRaises(QgsProcessingException) as raised:
            self.alg._fetch_json("https://example.com/api", self.feedback, "test error")
        self.assertIn("test error", str(raised.exception))

    @patch("data_loader.algorithm.urlopen")
    def test_invalid_json_response(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = b"not json"
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        with self.assertRaises(QgsProcessingException):
            self.alg._fetch_json("https://example.com/api", self.feedback, "parse")

    def test_accepts_http_scheme(self):
        with patch("data_loader.algorithm.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = b'{"ok": true}'
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_response

            result = self.alg._fetch_json(
                "http://example.com/api", self.feedback, "test"
            )
            self.assertEqual(result, {"ok": True})

    @patch("data_loader.algorithm.urlopen")
    def test_arcgis_error_response_raises(self, mock_urlopen):
        body = {"error": {"code": 499, "message": "Token Required"}}
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(body).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        with self.assertRaises(QgsProcessingException) as raised:
            self.alg._fetch_json(
                "https://example.com/api", self.feedback, "error context"
            )
        self.assertIn("error context: 499 Token Required", str(raised.exception))


class TestResolveLayerUrlAndMeta(unittest.TestCase):
    """Tests for MOELoaderAlgorithm._resolve_layer_url_and_meta"""

    def setUp(self):
        self.alg = MOELoaderAlgorithm()
        self.feedback = MagicMock()

    def test_success_returns_tuple(self):
        service_meta = {"layers": [{"id": 0}], "spatialReference": {}}
        layer_meta = {"extent": {}, "spatialReference": {}}

        with patch.object(
            self.alg, "_fetch_json", side_effect=[service_meta, layer_meta]
        ):
            result = self.alg._resolve_layer_url_and_meta(
                "https://example.com/FeatureServer", self.feedback
            )
            self.assertIsNotNone(result)
            layer_url, svc, lyr = result  # type: ignore
            self.assertEqual(layer_url, "https://example.com/FeatureServer/0")
            self.assertEqual(svc, service_meta)
            self.assertEqual(lyr, layer_meta)

    def test_uses_first_layer_id(self):
        service_meta = {"layers": [{"id": 5}, {"id": 10}]}
        layer_meta = {}

        with patch.object(
            self.alg, "_fetch_json", side_effect=[service_meta, layer_meta]
        ):
            result = self.alg._resolve_layer_url_and_meta(
                "https://example.com/FeatureServer", self.feedback
            )
            layer_url, _, _ = result  # type: ignore
            self.assertEqual(layer_url, "https://example.com/FeatureServer/5")

    def test_no_layers_raises(self):
        service_meta = {"layers": []}
        with patch.object(self.alg, "_fetch_json", return_value=service_meta):
            with self.assertRaises(QgsProcessingException):
                self.alg._resolve_layer_url_and_meta(
                    "https://example.com/FeatureServer", self.feedback
                )

    def test_missing_layers_key_raises(self):
        service_meta = {"services": []}
        with patch.object(self.alg, "_fetch_json", return_value=service_meta):
            with self.assertRaises(QgsProcessingException):
                self.alg._resolve_layer_url_and_meta(
                    "https://example.com/FeatureServer", self.feedback
                )

    def test_service_fetch_failure_raises(self):
        error = QgsProcessingException("Failed to fetch FeatureServer metadata")
        with patch.object(self.alg, "_fetch_json", side_effect=error):
            with self.assertRaises(QgsProcessingException):
                self.alg._resolve_layer_url_and_meta(
                    "https://example.com/FeatureServer", self.feedback
                )

    def test_layer_meta_fetch_failure_returns_empty_dict(self):
        service_meta = {"layers": [{"id": 0}]}
        error = QgsProcessingException("Failed to fetch layer metadata")
        with patch.object(self.alg, "_fetch_json", side_effect=[service_meta, error]):
            result = self.alg._resolve_layer_url_and_meta(
                "https://example.com/FeatureServer", self.feedback
            )
            _, _, lyr = result
            self.assertEqual(lyr, {})
            self.feedback.pushWarning.assert_called_once()


class TestCheckParameterValues(unittest.TestCase):
    """Tests for MOELoaderAlgorithm.checkParameterValues"""

    def setUp(self):
        self.alg = MOELoaderAlgorithm()
        self.context = MagicMock()
        # Manually set up _dataset_mapping to avoid calling initAlgorithm
        self.alg._dataset_mapping = [
            ("vg_50000", True),  # index 0: prefecture-aware
            ("coral_survey", False),  # index 1: no prefecture
        ]

    def test_prefecture_required_but_missing_none(self):
        parameters = {"CATEGORY": 0, "PREFECTURE": None}
        with patch.object(self.alg, "parameterAsEnum", return_value=0):
            ok, msg = self.alg.checkParameterValues(parameters, self.context)
            self.assertFalse(ok)

    def test_prefecture_required_but_missing_empty(self):
        parameters = {"CATEGORY": 0, "PREFECTURE": ""}
        with patch.object(self.alg, "parameterAsEnum", return_value=0):
            ok, msg = self.alg.checkParameterValues(parameters, self.context)
            self.assertFalse(ok)

    def test_prefecture_required_and_provided(self):
        parameters = {"CATEGORY": 0, "PREFECTURE": 0}
        with patch.object(self.alg, "parameterAsEnum", return_value=0):
            with patch(
                "qgis.core.QgsProcessingAlgorithm.checkParameterValues",
                return_value=(True, ""),
            ):
                ok, msg = self.alg.checkParameterValues(parameters, self.context)
                self.assertTrue(ok)

    def test_no_prefecture_required(self):
        parameters = {"CATEGORY": 1, "PREFECTURE": None}
        with patch.object(self.alg, "parameterAsEnum", return_value=1):
            with patch(
                "qgis.core.QgsProcessingAlgorithm.checkParameterValues",
                return_value=(True, ""),
            ):
                ok, msg = self.alg.checkParameterValues(parameters, self.context)
                self.assertTrue(ok)


class TestAlgorithmIdentity(unittest.TestCase):
    """Tests for algorithm identity methods"""

    def setUp(self):
        self.alg = MOELoaderAlgorithm()

    def test_name(self):
        self.assertEqual(self.alg.name(), "moe_geoportal_loader")

    def test_display_name(self):
        self.assertIsInstance(self.alg.displayName(), str)
        self.assertGreater(len(self.alg.displayName()), 0)

    def test_group_is_none(self):
        self.assertIsNone(self.alg.group())

    def test_group_id_is_none(self):
        self.assertIsNone(self.alg.groupId())

    def test_create_instance(self):
        instance = self.alg.createInstance()
        self.assertIsInstance(instance, MOELoaderAlgorithm)
        self.assertIsNot(instance, self.alg)

    def test_short_help_string(self):
        help_str = self.alg.shortHelpString()
        self.assertIsInstance(help_str, str)
        self.assertIn("geoportal", help_str.lower())


class TestGetBundledQml(unittest.TestCase):
    """Tests for MOELoaderAlgorithm._get_bundled_qml"""

    def setUp(self):
        self.alg = MOELoaderAlgorithm()

    def test_returns_none_for_nonexistent_key(self):
        result = self.alg._get_bundled_qml("nonexistent_dataset_key_xyz")
        self.assertIsNone(result)

    def test_returns_path_for_existing_style(self):
        styles_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "data_loader", "styles"
        )
        if os.path.isdir(styles_dir):
            qml_files = [f for f in os.listdir(styles_dir) if f.endswith(".qml")]
            if qml_files:
                key = qml_files[0].replace(".qml", "")
                result = self.alg._get_bundled_qml(key)
                self.assertIsNotNone(result)
                self.assertTrue(os.path.exists(result))  # type: ignore

    def test_returns_none_for_none_key(self):
        result = self.alg._get_bundled_qml(None)
        self.assertIsNone(result)


class TestSaveStyleQml(unittest.TestCase):
    """_save_style_qml must notice when QGIS could not write the style."""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        start_app()

    def setUp(self):
        self.alg = MOELoaderAlgorithm()
        self.layer = QgsVectorLayer("Point?crs=EPSG:4326", "layer", "memory")
        self.feedback = MagicMock()

    def test_saves_style_next_to_file_output(self):
        out_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, out_dir)

        qml_path = self.alg._save_style_qml(
            self.layer, os.path.join(out_dir, "out.gpkg"), None, True, self.feedback
        )
        self.assertEqual(qml_path, os.path.join(out_dir, "out.qml"))
        self.assertTrue(os.path.exists(qml_path))
        self.feedback.reportError.assert_not_called()

    def test_reports_style_that_could_not_be_saved(self):
        output_path = os.path.join(tempfile.gettempdir(), "no_such_dir_xyz", "out.gpkg")

        qml_path = self.alg._save_style_qml(
            self.layer, output_path, None, True, self.feedback
        )
        self.assertIsNone(qml_path)
        self.feedback.reportError.assert_called_once()

    def test_removes_temporary_file_when_saving_fails(self):
        layer = MagicMock()
        layer.saveNamedStyle.return_value = ("ERROR: Failed to save", False)

        qml_path = self.alg._save_style_qml(layer, "", None, False, self.feedback)
        self.assertIsNone(qml_path)
        self.assertFalse(os.path.exists(layer.saveNamedStyle.call_args[0][0]))


class TestCreateArcgisVectorLayer(unittest.TestCase):
    """Tests for MOELoaderAlgorithm._create_arcgis_vector_layer"""

    def setUp(self):
        self.alg = MOELoaderAlgorithm()
        self.feedback = MagicMock()

    @patch("data_loader.algorithm.QgsVectorLayer")
    def test_returns_layer_when_valid(self, mock_layer_cls):
        mock_layer = MagicMock()
        mock_layer.isValid.return_value = True
        mock_layer_cls.return_value = mock_layer

        result = self.alg._create_arcgis_vector_layer(
            "https://example.com/FeatureServer/0", "test_layer", self.feedback
        )
        self.assertIsNotNone(result)
        mock_layer_cls.assert_called_once_with(
            "url='https://example.com/FeatureServer/0'",
            "test_layer",
            "arcgisfeatureserver",
        )

    @patch("data_loader.algorithm.QgsVectorLayer")
    def test_raises_when_invalid(self, mock_layer_cls):
        mock_layer = MagicMock()
        mock_layer.isValid.return_value = False
        mock_layer_cls.return_value = mock_layer

        with self.assertRaises(QgsProcessingException):
            self.alg._create_arcgis_vector_layer(
                "https://example.com/FeatureServer/0", "test_layer", self.feedback
            )


class _MockedServiceTestCase(unittest.TestCase):
    """Runs the algorithm against a memory layer standing in for the ArcGIS service."""

    # so4 is served in JGD2000 geographic coordinates
    SOURCE_CRS = "EPSG:4612"
    SOURCE_X, SOURCE_Y = 139.871853, 33.170186

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        start_app()
        if not QgsCoordinateReferenceSystem("EPSG:6691").isValid():
            raise unittest.SkipTest("PROJ database not available")

    def setUp(self):
        self.alg = MOELoaderAlgorithm()
        self.alg.initAlgorithm()
        self.context = QgsProcessingContext()
        self.feedback = MagicMock()
        self.feedback.isCanceled.return_value = False

        self.source = QgsVectorLayer(
            f"Point?crs={self.SOURCE_CRS}&field=name:string", "source", "memory"
        )
        feature = QgsFeature(self.source.fields())
        feature.setAttributes(["a"])
        feature.setGeometry(
            QgsGeometry.fromPointXY(QgsPointXY(self.SOURCE_X, self.SOURCE_Y))
        )
        self.source.dataProvider().addFeatures([feature])

        meta = {"spatialReference": {"wkid": 4612}}
        patcher = patch.multiple(
            self.alg,
            _resolve_layer_url_and_meta=MagicMock(
                return_value=("https://example.com/FeatureServer/0", meta, meta)
            ),
            _create_arcgis_vector_layer=MagicMock(return_value=self.source),
            _open_feature_stream=MagicMock(
                return_value=list(self.source.getFeatures())
            ),
            _save_style_qml=MagicMock(return_value=None),
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def _save_to_file(self, parameters):
        return self.alg._save_to_file(
            "https://example.com/FeatureServer",
            parameters,
            self.context,
            self.feedback,
            dataset={"name": "test"},
            dataset_key="test",
        )

    def _load_as_arcgis_layer(self, parameters):
        return self.alg._load_as_arcgis_layer(
            "https://example.com/FeatureServer",
            {"name": "test"},
            False,
            None,
            parameters,
            self.context,
            self.feedback,
        )


class TestOutputCrs(_MockedServiceTestCase):
    """The CRS parameter must reproject saved features, never relabel them."""

    def _save(self, crs):
        dest_id = self._save_to_file({"CRS": crs, "OUTPUT": "TEMPORARY_OUTPUT"})
        return self.context.temporaryLayerStore().mapLayer(dest_id)

    @staticmethod
    def _first_point(layer):
        return next(layer.getFeatures()).geometry().asPoint()

    def test_output_crs_reprojects_features(self):
        output = self._save("EPSG:6691")

        expected = QgsCoordinateTransform(
            QgsCoordinateReferenceSystem(self.SOURCE_CRS),
            QgsCoordinateReferenceSystem("EPSG:6691"),
            QgsCoordinateTransformContext(),
        ).transform(QgsPointXY(self.SOURCE_X, self.SOURCE_Y))
        point = self._first_point(output)
        self.assertEqual(output.crs().authid(), "EPSG:6691")
        self.assertAlmostEqual(point.x(), expected.x(), places=3)
        self.assertAlmostEqual(point.y(), expected.y(), places=3)

    def test_no_output_crs_keeps_source_coordinates(self):
        output = self._save(None)

        point = self._first_point(output)
        self.assertEqual(output.crs().authid(), self.SOURCE_CRS)
        self.assertAlmostEqual(point.x(), self.SOURCE_X)
        self.assertAlmostEqual(point.y(), self.SOURCE_Y)

    def test_arcgis_layer_keeps_service_crs(self):
        self._load_as_arcgis_layer({"CRS": "EPSG:6691"})

        self.assertEqual(self.source.crs().authid(), self.SOURCE_CRS)
        self.feedback.pushWarning.assert_called_once()


class TestFailures(_MockedServiceTestCase):
    """Failures must fail the algorithm instead of ending as a success."""

    def test_unavailable_service_fails_the_algorithm(self):
        self.alg._resolve_layer_url_and_meta.side_effect = QgsProcessingException(
            "Failed to fetch FeatureServer metadata: 499 Token Required"
        )
        for mode in ({}, {"ADD_AS_ARCGIS_LAYER": True}):
            parameters = {"CATEGORY": 1, "OUTPUT": "TEMPORARY_OUTPUT", **mode}
            with self.subTest(mode=mode), self.assertRaises(QgsProcessingException):
                self.alg.processAlgorithm(parameters, self.context, self.feedback)

    def test_arcgis_layer_errors_are_not_swallowed(self):
        self.alg._create_arcgis_vector_layer.side_effect = QgsProcessingException(
            "Failed to load layer"
        )
        with self.assertRaises(QgsProcessingException):
            self._load_as_arcgis_layer({})

    def test_reprojecting_from_an_unknown_crs_fails(self):
        self.alg._resolve_layer_url_and_meta.return_value = (
            "https://example.com/FeatureServer/0",
            {},
            {},
        )
        self.source.setCrs(QgsCoordinateReferenceSystem())

        with self.assertRaises(QgsProcessingException):
            self._save_to_file({"CRS": "EPSG:6691", "OUTPUT": "TEMPORARY_OUTPUT"})


class TestLayerLoading(_MockedServiceTestCase):
    """processAlgorithm runs in a worker thread and must not touch the project."""

    def test_arcgis_layer_is_handed_to_the_context(self):
        layers_before = QgsProject.instance().count()
        layer_id = self._load_as_arcgis_layer({})

        self.assertEqual(QgsProject.instance().count(), layers_before)
        self.assertIs(
            self.context.temporaryLayerStore().mapLayer(layer_id), self.source
        )
        self.assertTrue(self.context.willLoadLayerOnCompletion(layer_id))
        details = self.context.layerToLoadOnCompletionDetails(layer_id)
        self.assertEqual(details.name, "test")

    def test_registered_output_gets_name_and_style(self):
        fd, qml_path = tempfile.mkstemp(suffix=".qml")
        os.close(fd)
        self.addCleanup(os.remove, qml_path)
        self.alg._save_style_qml.return_value = qml_path
        output = QgsProcessingOutputLayerDefinition(
            "TEMPORARY_OUTPUT", QgsProject.instance()
        )

        layers_before = QgsProject.instance().count()
        dest_id = self._save_to_file({"OUTPUT": output})

        self.assertEqual(QgsProject.instance().count(), layers_before)
        details = self.context.layerToLoadOnCompletionDetails(dest_id)
        self.assertEqual(details.name, "test")
        self.assertIsInstance(details.postProcessor(), _StylePostProcessor)
        self.assertEqual(details.postProcessor().qml_path, qml_path)

    def test_unregistered_output_is_not_loaded(self):
        dest_id = self._save_to_file({"OUTPUT": "TEMPORARY_OUTPUT"})

        self.assertFalse(self.context.willLoadLayerOnCompletion(dest_id))
        self.alg._save_style_qml.assert_not_called()


class TestStylePostProcessor(unittest.TestCase):
    """_StylePostProcessor must apply the QML and report the actual outcome."""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        start_app()

    def setUp(self):
        self.layer = QgsVectorLayer("Point?crs=EPSG:4326", "layer", "memory")
        self.feedback = MagicMock()
        fd, self.qml_path = tempfile.mkstemp(suffix=".qml")
        os.close(fd)
        self.addCleanup(
            lambda: os.path.exists(self.qml_path) and os.remove(self.qml_path)
        )

    def test_applies_style(self):
        styled = QgsVectorLayer("Point?crs=EPSG:4326", "styled", "memory")
        styled.renderer().symbol().setColor(QColor(12, 34, 56))
        styled.saveNamedStyle(self.qml_path)

        _StylePostProcessor(self.qml_path).postProcessLayer(
            self.layer, None, self.feedback
        )
        self.assertEqual(self.layer.renderer().symbol().color(), QColor(12, 34, 56))
        self.feedback.pushInfo.assert_called_once()
        self.feedback.pushWarning.assert_not_called()

    def test_reports_broken_style(self):
        with open(self.qml_path, "w", encoding="utf-8") as f:
            f.write("<qgis><renderer-v2")

        _StylePostProcessor(self.qml_path).postProcessLayer(
            self.layer, None, self.feedback
        )
        self.feedback.pushWarning.assert_called_once()

    def test_removes_temporary_style_after_use(self):
        self.layer.saveNamedStyle(self.qml_path)

        _StylePostProcessor(self.qml_path, remove_after=True).postProcessLayer(
            self.layer, None, self.feedback
        )
        self.assertFalse(os.path.exists(self.qml_path))


if __name__ == "__main__":
    unittest.main()
