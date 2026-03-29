import json
import os
import unittest
from unittest.mock import MagicMock, patch

from qgis.core import QgsCoordinateReferenceSystem

from data_loader.algorithm import MOELoaderAlgorithm
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
        result = self.alg._fetch_json("ftp://example.com/data", self.feedback, "test")
        self.assertIsNone(result)
        self.feedback.reportError.assert_called_once()

    def test_rejects_file_scheme(self):
        result = self.alg._fetch_json("file:///etc/passwd", self.feedback, "test")
        self.assertIsNone(result)
        self.feedback.reportError.assert_called_once()

    def test_rejects_javascript_scheme(self):
        result = self.alg._fetch_json("javascript:alert(1)", self.feedback, "test")
        self.assertIsNone(result)
        self.feedback.reportError.assert_called_once()

    @patch("data_loader.algorithm.urlopen")
    def test_network_error(self, mock_urlopen):
        mock_urlopen.side_effect = ConnectionError("Connection refused")
        result = self.alg._fetch_json(
            "https://example.com/api", self.feedback, "test error"
        )
        self.assertIsNone(result)
        self.feedback.reportError.assert_called_once()
        self.assertIn("test error", self.feedback.reportError.call_args[0][0])

    @patch("data_loader.algorithm.urlopen")
    def test_invalid_json_response(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = b"not json"
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = self.alg._fetch_json(
            "https://example.com/api", self.feedback, "parse error"
        )
        self.assertIsNone(result)
        self.feedback.reportError.assert_called_once()

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

    def test_no_layers_returns_none(self):
        service_meta = {"layers": []}
        with patch.object(self.alg, "_fetch_json", return_value=service_meta):
            result = self.alg._resolve_layer_url_and_meta(
                "https://example.com/FeatureServer", self.feedback
            )
            self.assertIsNone(result)
            self.feedback.reportError.assert_called()

    def test_missing_layers_key_returns_none(self):
        service_meta = {"services": []}
        with patch.object(self.alg, "_fetch_json", return_value=service_meta):
            result = self.alg._resolve_layer_url_and_meta(
                "https://example.com/FeatureServer", self.feedback
            )
            self.assertIsNone(result)

    def test_service_fetch_failure_returns_none(self):
        with patch.object(self.alg, "_fetch_json", return_value=None):
            result = self.alg._resolve_layer_url_and_meta(
                "https://example.com/FeatureServer", self.feedback
            )
            self.assertIsNone(result)

    def test_layer_meta_fetch_failure_returns_empty_dict(self):
        service_meta = {"layers": [{"id": 0}]}
        with patch.object(self.alg, "_fetch_json", side_effect=[service_meta, None]):
            result = self.alg._resolve_layer_url_and_meta(
                "https://example.com/FeatureServer", self.feedback
            )
            self.assertIsNotNone(result)
            _, _, lyr = result  # type: ignore
            self.assertEqual(lyr, {})


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


class TestReportException(unittest.TestCase):
    """Tests for MOELoaderAlgorithm._report_exception"""

    def setUp(self):
        self.alg = MOELoaderAlgorithm()
        self.feedback = MagicMock()

    def test_reports_error_and_traceback(self):
        try:
            raise ValueError("test error")
        except ValueError as e:
            self.alg._report_exception(self.feedback, "Something failed", e)
        self.assertEqual(self.feedback.reportError.call_count, 2)
        first_call = self.feedback.reportError.call_args_list[0][0][0]
        self.assertIn("Something failed", first_call)
        self.assertIn("test error", first_call)


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
    def test_returns_none_when_invalid(self, mock_layer_cls):
        mock_layer = MagicMock()
        mock_layer.isValid.return_value = False
        mock_layer_cls.return_value = mock_layer

        result = self.alg._create_arcgis_vector_layer(
            "https://example.com/FeatureServer/0", "test_layer", self.feedback
        )
        self.assertIsNone(result)
        self.feedback.reportError.assert_called_once()


if __name__ == "__main__":
    unittest.main()
