import unittest
from unittest.mock import MagicMock, patch

from qgis.core import (
    Qgis,
    QgsArcGisRestUtils,
    QgsField,
    QgsFields,
    QgsProcessingException,
    QgsRectangle,
)
from qgis.PyQt.QtCore import QMetaType

from data_loader import feature_downloader
from data_loader.feature_downloader import FeatureDownloader, envelope

LAYER_URL = "https://example.com/FeatureServer/0"
EPOCH_MS = 1700000000000


class FakeService:
    """Answers FeatureDownloader queries the way an ArcGIS feature layer does."""

    def __init__(self, object_ids, transfer_limit=None, positions=None):
        self.object_ids = object_ids
        self.transfer_limit = transfer_limit
        # Where each feature is; by default on a diagonal
        self.positions = positions or {i: (float(i), i + 0.5) for i in object_ids}
        self.queries = []
        self.where_clauses = []

    def _matches(self, object_id, params):
        if "geometry" not in params:
            return True
        xmin, ymin, xmax, ymax = (float(v) for v in params["geometry"].split(","))
        x, y = self.positions[object_id]
        return xmin <= x <= xmax and ymin <= y <= ymax

    def __call__(self, url, params, feedback):
        self.queries.append(params)
        if params.get("returnIdsOnly") == "true":
            ids = [i for i in self.object_ids if self._matches(i, params)]
            return {"objectIdFieldName": "oid", "objectIds": ids}

        self.where_clauses.append(params["where"])
        low, high = (int(part.split("=")[1]) for part in params["where"].split(" AND "))
        ids = [
            i
            for i in sorted(self.object_ids)
            if low <= i <= high and self._matches(i, params)
        ]
        features = [
            {
                "attributes": {"oid": i, "name": f"n{i}", "date": EPOCH_MS},
                "geometry": dict(zip("xy", self.positions[i])),
            }
            for i in ids
        ]
        page = {"geometryType": "esriGeometryPoint", "features": features}
        if self.transfer_limit and len(ids) > self.transfer_limit:
            page["features"] = features[: self.transfer_limit]
            page["exceededTransferLimit"] = True
        return page


class TestFeatureDownloader(unittest.TestCase):
    def setUp(self):
        self.fields = QgsFields()
        self.fields.append(QgsField("oid", QMetaType.Type.Int))
        self.fields.append(QgsField("name", QMetaType.Type.QString))
        self.fields.append(QgsField("date", QMetaType.Type.QDateTime))
        self.feedback = MagicMock()
        self.feedback.isCanceled.return_value = False

    def _download(self, service, page_size=2, extent=None):
        with patch.object(feature_downloader, "_get_json", side_effect=service):
            downloader = FeatureDownloader(
                LAYER_URL,
                self.fields,
                Qgis.WkbType.Point,
                self.feedback,
                page_size=page_size,
                extent=extent,
            )
            return downloader, list(downloader)

    def test_downloads_pages_in_object_id_order(self):
        service = FakeService([5, 1, 3, 2, 4])
        downloader, features = self._download(service)

        self.assertEqual(len(downloader), 5)
        self.assertEqual([f["oid"] for f in features], [1, 2, 3, 4, 5])
        self.assertEqual(
            sorted(service.where_clauses),
            ["oid>=1 AND oid<=2", "oid>=3 AND oid<=4", "oid>=5 AND oid<=5"],
        )
        self.assertEqual(features[0]["name"], "n1")
        point = features[2].geometry().asPoint()
        self.assertEqual((point.x(), point.y()), (3.0, 3.5))

    def test_converts_dates_like_the_provider(self):
        _, features = self._download(FakeService([1]))

        expected = QgsArcGisRestUtils.convertDateTime(EPOCH_MS)
        self.assertEqual(features[0]["date"], expected)

    def test_splits_pages_when_transfer_limit_is_exceeded(self):
        service = FakeService([1, 2, 3, 4], transfer_limit=1)
        _, features = self._download(service, page_size=4)

        self.assertEqual([f["oid"] for f in features], [1, 2, 3, 4])

    def test_downloads_only_the_features_in_the_extent(self):
        # The page of 2 and 4 also spans 3, which is outside the extent
        inside, outside = (5.0, 5.0), (0.0, 0.0)
        positions = {1: outside, 2: inside, 3: outside, 4: inside, 5: outside}
        service = FakeService([1, 2, 3, 4, 5], positions=positions)
        downloader, features = self._download(service, extent=QgsRectangle(4, 4, 6, 6))

        self.assertEqual(len(downloader), 2)
        self.assertEqual([f["oid"] for f in features], [2, 4])
        self.assertEqual(service.where_clauses, ["oid>=2 AND oid<=4"])

    def test_sends_the_extent_with_every_query(self):
        service = FakeService([1, 2, 3, 4], transfer_limit=1)
        self._download(service, page_size=4, extent=QgsRectangle(0, 0, 10, 10))

        # The ID query, then the page and its halves
        self.assertGreater(len(service.queries), 2)
        for params in service.queries:
            self.assertEqual(params["geometry"], "0.0,0.0,10.0,10.0")
            self.assertEqual(params["geometryType"], "esriGeometryEnvelope")
            self.assertEqual(params["spatialRel"], "esriSpatialRelIntersects")
            # The service then reads the extent in the CRS of the layer
            self.assertNotIn("inSR", params)

    def test_no_extent_downloads_every_feature(self):
        service = FakeService([1, 2, 3])
        _, features = self._download(service)

        self.assertEqual([f["oid"] for f in features], [1, 2, 3])
        for params in service.queries:
            self.assertNotIn("geometry", params)

    def test_envelope_keeps_every_digit(self):
        extent = QgsRectangle(139.123456789, -0.5, 15550219.75, 35.987654321)
        self.assertEqual(
            envelope(extent), "139.123456789,-0.5,15550219.75,35.987654321"
        )

    def test_raises_after_repeated_errors(self):
        failing = MagicMock(return_value={"error": {"code": 500, "message": "oops"}})
        with patch.object(feature_downloader, "_get_json", failing):
            with patch.object(feature_downloader.time, "sleep"):
                with self.assertRaises(QgsProcessingException):
                    FeatureDownloader(
                        LAYER_URL, self.fields, Qgis.WkbType.Point, self.feedback
                    )
        self.assertEqual(failing.call_count, feature_downloader.RETRIES)

    def test_canceled_request_is_not_retried(self):
        def abort(url, params, feedback):
            self.feedback.isCanceled.return_value = True
            raise OSError("Operation canceled")

        with patch.object(feature_downloader, "_get_json", side_effect=abort) as get:
            with patch.object(feature_downloader.time, "sleep") as sleep:
                downloader = FeatureDownloader(
                    LAYER_URL, self.fields, Qgis.WkbType.Point, self.feedback
                )
        self.assertEqual(len(downloader), 0)
        self.assertEqual(get.call_count, 1)
        sleep.assert_not_called()

    def test_stops_when_canceled(self):
        self.feedback.isCanceled.side_effect = [False, True, True, True]
        _, features = self._download(FakeService([1, 2, 3, 4, 5]))

        self.assertEqual([f["oid"] for f in features], [1, 2])

    def test_rejects_non_http_urls(self):
        with self.assertRaises(ValueError):
            FeatureDownloader(
                "file:///etc/passwd", self.fields, Qgis.WkbType.Point, self.feedback
            )


if __name__ == "__main__":
    unittest.main()
