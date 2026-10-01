"""
Fast download of ArcGIS Feature Service layers.

The QGIS ArcGIS provider requests 100 features at a time, one request after
another. This module requests pages of up to maxRecordCount features, several
pages in parallel, and converts them with the same functions as the provider.
"""

from __future__ import annotations

import http.client
import json
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from itertools import islice
from urllib.parse import urlencode
from urllib.request import urlopen

from qgis.core import (
    QgsArcGisRestUtils,
    QgsFeature,
    QgsGeometry,
    QgsProcessingException,
    QgsWkbTypes,
)
from qgis.PyQt.QtCore import QMetaType

DEFAULT_PAGE_SIZE = 1000
MAX_PAGE_SIZE = 2000
WORKERS = 4
TIMEOUT = 120
RETRIES = 3


def _get_json(url: str, params: dict) -> dict:
    with urlopen(f"{url}?{urlencode(params)}", timeout=TIMEOUT) as response:  # noqa: S310  # nosec B310  # scheme validated by FeatureDownloader
        return json.loads(response.read().decode())


def _query(layer_url: str, params: dict) -> dict:
    error = ""
    for attempt in range(RETRIES):
        try:
            data = _get_json(f"{layer_url}/query", params)
        except (OSError, ValueError, http.client.HTTPException) as e:
            error = str(e)
        else:
            if "error" not in data:
                return data
            error = f"{data['error'].get('code')} {data['error'].get('message')}"
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

        ids = _query(layer_url, {"where": "1=1", "returnIdsOnly": "true", "f": "json"})
        self.oid_field = ids["objectIdFieldName"]
        self.object_ids = sorted(ids.get("objectIds") or [])

    def __len__(self):
        return len(self.object_ids)

    def __iter__(self):
        batches = (
            self.object_ids[i : i + self.page_size]
            for i in range(0, len(self.object_ids), self.page_size)
        )
        with ThreadPoolExecutor(WORKERS) as executor:
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
