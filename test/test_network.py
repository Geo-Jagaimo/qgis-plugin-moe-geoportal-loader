import http.server
import json
import os
import threading
import time
import unittest
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qsl

from qgis.core import (
    Qgis,
    QgsFeedback,
    QgsFields,
    QgsNetworkAccessManager,
    QgsProcessingException,
    QgsRectangle,
)
from qgis.PyQt.QtCore import QThreadPool
from qgis.testing import start_app

from data_loader import feature_downloader
from data_loader.algorithm import MOELoaderAlgorithm
from data_loader.feature_downloader import FeatureDownloader
from data_loader.network import get_json


class _Handler(http.server.BaseHTTPRequestHandler):
    RESPONSES = {
        "/ok": (200, b'{"layers": [{"id": 0}]}'),
        "/not-json": (200, b"not json"),
        "/layer/ids": (200, b'{"objectIdFieldName": "oid", "objectIds": [1]}'),
        "/layer/query": (200, b'{"features": []}'),
    }

    def do_GET(self):
        path, _, query = self.path.partition("?")
        if path == "/layer/query" and "returnIdsOnly=true" in query:
            path = "/layer/ids"
        elif path in ("/slow", "/layer/query"):
            # Not time.sleep(), which some tests patch out
            threading.Event().wait(5)
        status, body = self.RESPONSES.get(path, (404, b"missing"))
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class _QuietServer(http.server.ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):
        # Aborted requests make the slow handler write to a closed socket
        pass


class TestGetJson(unittest.TestCase):
    """get_json must go through the QGIS network stack, checked against a local server."""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        start_app()
        cls.server = _QuietServer(("127.0.0.1", 0), _Handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_returns_decoded_json(self):
        self.assertEqual(get_json(f"{self.base}/ok?f=json"), {"layers": [{"id": 0}]})

    def test_http_error_raises_oserror(self):
        with self.assertRaises(OSError):
            get_json(f"{self.base}/missing")

    def test_invalid_json_raises_valueerror(self):
        with self.assertRaises(ValueError):
            get_json(f"{self.base}/not-json")

    def test_qgis_network_timeout_applies(self):
        original = QgsNetworkAccessManager.timeout()
        QgsNetworkAccessManager.setTimeout(1000)
        self.addCleanup(QgsNetworkAccessManager.setTimeout, original)

        started = time.monotonic()
        with self.assertRaises(OSError) as raised:
            get_json(f"{self.base}/slow")
        self.assertIn("timed out", str(raised.exception))
        self.assertLess(time.monotonic() - started, 4)

    def test_qgis_network_timeout_applies_to_download_workers(self):
        original = QgsNetworkAccessManager.timeout()
        QgsNetworkAccessManager.setTimeout(1000)
        self.addCleanup(QgsNetworkAccessManager.setTimeout, original)
        downloader = FeatureDownloader(
            f"{self.base}/layer", QgsFields(), Qgis.WkbType.Point, QgsFeedback()
        )

        # Each attempt gives up after 1 s: about 3 s in total, versus 15 s if
        # the timeout did not reach the worker threads
        started = time.monotonic()
        with patch.object(feature_downloader.time, "sleep"):
            with self.assertRaises(QgsProcessingException):
                list(downloader)
        self.assertLess(time.monotonic() - started, 8)

    def test_canceling_aborts_a_running_request(self):
        # Like processAlgorithm: the request runs on a worker QThread and the
        # user cancels from the main thread
        feedback = QgsFeedback()
        outcome = {}

        def request():
            try:
                get_json(f"{self.base}/slow", feedback)
            except OSError as e:
                outcome["error"] = e

        pool = QThreadPool()
        started = time.monotonic()
        pool.start(request)
        time.sleep(0.5)
        feedback.cancel()

        self.assertTrue(pool.waitForDone(10000))
        self.assertIn("error", outcome)
        self.assertLess(time.monotonic() - started, 4)


class _LayerHandler(http.server.BaseHTTPRequestHandler):
    """An ArcGIS point layer whose features 1 to 3 lie at (1, 1), (2, 2) and (3, 3)."""

    LAYER = {
        "name": "layer",
        "type": "Feature Layer",
        "geometryType": "esriGeometryPoint",
        "capabilities": "Query",
        "extent": {
            "xmin": 1,
            "ymin": 1,
            "xmax": 3,
            "ymax": 3,
            # JGD2000, like the vegetation maps
            "spatialReference": {"wkid": 4612},
        },
        "fields": [{"name": "oid", "type": "esriFieldTypeOID", "alias": "oid"}],
    }

    def do_GET(self):
        path, _, query = self.path.partition("?")
        params = dict(parse_qsl(query))
        if path == "/layer":
            body = self.LAYER
        elif path == "/layer/query" and params.get("returnIdsOnly") == "true":
            self.server.id_queries.append(params)
            ids = [1, 2, 3]
            if "geometry" in params:
                xmin, ymin, xmax, ymax = map(float, params["geometry"].split(","))
                ids = [i for i in ids if xmin <= i <= xmax and ymin <= i <= ymax]
            body = {"objectIdFieldName": "oid", "objectIds": ids}
        else:
            self.send_error(404)
            return
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


class TestArcGisLayerExtent(unittest.TestCase):
    """The ArcGIS provider of QGIS must request only the features in the extent."""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        start_app()
        cls.server = _QuietServer(("127.0.0.1", 0), _LayerHandler)
        cls.server.id_queries = []
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.layer_url = f"http://127.0.0.1:{cls.server.server_address[1]}/layer"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def _feature_count(self, extent=None):
        self.server.id_queries.clear()
        layer = MOELoaderAlgorithm()._create_arcgis_vector_layer(
            self.layer_url, "layer", MagicMock(), extent=extent
        )
        # QGIS 4 requests the IDs only once it needs them
        count = layer.featureCount()
        self.assertEqual(len(self.server.id_queries), 1)
        return count, self.server.id_queries[0]

    def test_layer_has_only_the_features_in_the_extent(self):
        count, query = self._feature_count(QgsRectangle(1.5, 1.5, 3.5, 3.5))

        # QGIS formats the numbers its own way, such as 1.500000
        envelope = [float(value) for value in query["geometry"].split(",")]
        self.assertEqual(envelope, [1.5, 1.5, 3.5, 3.5])
        self.assertEqual(query["geometryType"], "esriGeometryEnvelope")
        self.assertEqual(count, 2)

    def test_layer_without_extent_has_every_feature(self):
        count, query = self._feature_count()

        self.assertNotIn("geometry", query)
        self.assertEqual(count, 3)


if __name__ == "__main__":
    unittest.main()
