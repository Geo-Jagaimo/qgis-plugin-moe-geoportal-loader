"""
HTTP requests through the QGIS network stack.

Unlike urllib, this applies the proxy, SSL and timeout settings configured in
QGIS, and aborts the request when the processing feedback is canceled.
"""

import json

from qgis.core import QgsBlockingNetworkRequest, QgsNetworkAccessManager
from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtNetwork import QNetworkReply, QNetworkRequest


def get_json(url, feedback=None):
    """GET url and decode its JSON body; raises OSError on network errors."""
    request = QNetworkRequest(QUrl(url))
    # Feature pages are large and never reused, so keep them out of the QGIS cache
    request.setAttribute(QNetworkRequest.Attribute.CacheSaveControlAttribute, False)

    blocking_request = QgsBlockingNetworkRequest()
    error = blocking_request.get(request, True, feedback)
    reply = blocking_request.reply()

    # Aborted requests (canceled, or timed out by QGIS) report NoError with an
    # empty body, so check for them explicitly
    if feedback is not None and feedback.isCanceled():
        raise OSError("Request canceled")
    if (
        error == QgsBlockingNetworkRequest.ErrorCode.TimeoutError
        or reply.error() == QNetworkReply.NetworkError.OperationCanceledError
    ):
        raise OSError(
            f"Request timed out after {QgsNetworkAccessManager.timeout() / 1000:g} s "
            "(see the network timeout in the QGIS options)"
        )
    if error != QgsBlockingNetworkRequest.ErrorCode.NoError:
        raise OSError(blocking_request.errorMessage())
    return json.loads(bytes(reply.content()).decode())
