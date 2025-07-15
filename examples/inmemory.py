import os

from boxdrive import create_app
from boxdrive.stores import InMemoryStore

otel_exporter_http_endpoint = os.getenv("OTEL_EXPORTER_HTTP_ENDPOINT")

store = InMemoryStore()
app = create_app(
    store,
    otel_exporter_http_endpoint=otel_exporter_http_endpoint,
)
