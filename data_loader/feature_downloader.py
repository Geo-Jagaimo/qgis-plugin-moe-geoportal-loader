"""
Fast download of ArcGIS Feature Service layers.

The QGIS ArcGIS provider requests 100 features at a time, one request after
another. This module requests pages of up to maxRecordCount features, several
pages in parallel, and converts them with the same functions as the provider.
"""

from __future__ import annotations

import time
from collections import deque
from concurrent.futures import Future
from itertools import islice
from urllib.parse import urlencode

from qgis.core import (
    QgsArcGisRestUtils,
    QgsFeature,
    QgsGeometry,
    QgsProcessingException,
    QgsWkbTypes,
)
from qgis.PyQt.QtCore import QMetaType, QThreadPool

from .network import get_json

DEFAULT_PAGE_SIZE = 1000
MAX_PAGE_SIZE = 2000
WORKERS = 4
RETRIES = 3


class _QThreadPoolExecutor:
    """Runs jobs on QThreads, where Qt timers work, so the QGIS network timeout
    also applies to them (it does not in threads started by Python)."""

    def __init__(self, max_workers):
        self._pool = QThreadPool()
        self._pool.setMaxThreadCount(max_workers)

    def submit(self, fn, *args):
        future = Future()

        def run():
            if not future.set_running_or_notify_cancel():
                return
            try:
                future.set_result(fn(*args))
            except Exception as e:
                future.set_exception(e)

        self._pool.start(run)
        return future

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self._pool.clear()
        self._pool.waitForDone()


def _get_json(url: str, params: dict, feedback) -> dict:
    return get_json(f"{url}?{urlencode(params)}", feedback)


def _query(layer_url: str, params: dict, feedback) -> dict:
    error = ""
    for attempt in range(RETRIES):
        try:
            data = _get_json(f"{layer_url}/query", params, feedback)
        except (OSError, ValueError) as e:
            error = str(e)
        else:
            if "error" not in data:
                return data
            error = f"{data['error'].get('code')} {data['error'].get('message')}"
        if feedback.isCanceled():
            # The request was aborted on purpose; retrying would only delay the stop
            return {}
        if attempt < RETRIES - 1:
            time.sleep(2**attempt)
    raise QgsProcessingException(
        f"Failed to download features from {layer_url}: {error}"
    )


class FeatureDownloader:
    """Iterates over all features of an ArcGIS feature service layer in object ID order."""

    def __init__(self, layer_url, fields, wkb_type, feedback, page_size=None):
        if not layer_url.startswith(("https://", "http://")):
            raise ValueError(f"Unsupported URL scheme: {layer_url}")
        self.layer_url = layer_url
        self.fields = fields
        self.feedback = feedback
        self.page_size = min(page_size or DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE)
        self.has_m = QgsWkbTypes.hasM(wkb_type)
        self.has_z = QgsWkbTypes.hasZ(wkb_type)
        self.has_curves = QgsWkbTypes.isCurvedType(wkb_type)
        self.date_fields = [
            i
            for i, field in enumerate(fields)
            if field.type() in (QMetaType.Type.QDateTime, QMetaType.Type.QDate)
        ]

        ids = _query(
            layer_url,
            {"where": "1=1", "returnIdsOnly": "true", "f": "json"},
            feedback,
        )
        self.oid_field = ids.get("objectIdFieldName")
        self.object_ids = sorted(ids.get("objectIds") or [])

    def __len__(self):
        return len(self.object_ids)

    def __iter__(self):
        batches = (
            self.object_ids[i : i + self.page_size]
            for i in range(0, len(self.object_ids), self.page_size)
        )
        with _QThreadPoolExecutor(WORKERS) as executor:
            # Keep a bounded number of pages in flight so memory stays flat
            pending = deque(
                executor.submit(self._fetch, batch)
                for batch in islice(batches, WORKERS * 2)
            )
            while pending:
                if self.feedback.isCanceled():
                    for future in pending:
                        future.cancel()
                    return
                features, geometry_type = pending.popleft().result()
                batch = next(batches, None)
                if batch is not None:
                    pending.append(executor.submit(self._fetch, batch))
                yield from self._convert(features, geometry_type)

    def _fetch(self, object_ids):
        # object_ids is a sorted run of the layer's IDs, so this range matches exactly them
        page = _query(
            self.layer_url,
            {
                "f": "json",
                "where": f"{self.oid_field}>={object_ids[0]} AND {self.oid_field}<={object_ids[-1]}",
                "outFields": "*",
                "returnGeometry": "true",
                "returnM": "true" if self.has_m else "false",
                "returnZ": "true" if self.has_z else "false",
            },
            self.feedback,
        )
        if page.get("exceededTransferLimit") and len(object_ids) > 1:
            half = len(object_ids) // 2
            first, geometry_type = self._fetch(object_ids[:half])
            second, _ = self._fetch(object_ids[half:])
            return first + second, geometry_type
        return page.get("features") or [], page.get("geometryType")

    def _convert(self, features, geometry_type):
        names = self.fields.names()
        for data in features:
            attributes = data.get("attributes") or {}
            values = [attributes.get(name) for name in names]
            for i in self.date_fields:
                if values[i] is not None:
                    values[i] = QgsArcGisRestUtils.convertDateTime(values[i])

            feature = QgsFeature(self.fields)
            feature.setAttributes(values)
            if data.get("geometry"):
                geometry, _ = QgsArcGisRestUtils.convertGeometry(
                    data["geometry"],
                    geometry_type,
                    self.has_m,
                    self.has_z,
                    self.has_curves,
                )
                if geometry:
                    feature.setGeometry(QgsGeometry(geometry))
            yield feature
