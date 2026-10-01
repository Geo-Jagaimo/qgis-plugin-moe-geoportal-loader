import unittest
from unittest.mock import MagicMock, patch

from qgis.core import (
    Qgis,
    QgsArcGisRestUtils,
    QgsField,
    QgsFields,
    QgsProcessingException,
)
from qgis.PyQt.QtCore import QMetaType

from data_loader import feature_downloader
from data_loader.feature_downloader import FeatureDownloader

LAYER_URL = "https://example.com/FeatureServer/0"
EPOCH_MS = 1700000000000


class FakeService:
    """Answers FeatureDownloader queries the way an ArcGIS feature layer does."""

    def __init__(self, object_ids, transfer_limit=None):
        self.object_ids = object_ids
        self.transfer_limit = transfer_limit
        self.where_clauses = []

    def __call__(self, url, params):
        if params.get("returnIdsOnly") == "true":
            return {"objectIdFieldName": "oid", "objectIds": list(self.object_ids)}

        self.where_clauses.append(params["where"])
        low, high = (int(part.split("=")[1]) for part in params["where"].split(" AND "))
        ids = [i for i in sorted(self.object_ids) if low <= i <= high]
        features = [
            {
                "attributes": {"oid": i, "name": f"n{i}", "date": EPOCH_MS},
                "geometry": {"x": float(i), "y": i + 0.5},
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

    def _download(self, service, page_size=2):
        with patch.object(feature_downloader, "_get_json", side_effect=service):
            downloader = FeatureDownloader(
                LAYER_URL,
                self.fields,
                Qgis.WkbType.Point,
                self.feedback,
                page_size=page_size,
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

    def test_raises_after_repeated_errors(self):
        failing = MagicMock(return_value={"error": {"code": 500, "message": "oops"}})
        with patch.object(feature_downloader, "_get_json", failing):
            with patch.object(feature_downloader.time, "sleep"):
                with self.assertRaises(QgsProcessingException):
                    FeatureDownloader(
                        LAYER_URL, self.fields, Qgis.WkbType.Point, self.feedback
                    )
        self.assertEqual(failing.call_count, feature_downloader.RETRIES)

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
