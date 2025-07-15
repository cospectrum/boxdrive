import os

from boxdrive import create_app
from boxdrive.stores import GitlabStore

repo_id = int(os.environ["REPO_ID"])
branch = os.environ.get("BRANCH", "main")
access_token = os.environ["ACCESS_TOKEN"]

otel_exporter_http_endpoint = os.getenv("OTEL_EXPORTER_HTTP_ENDPOINT")

store = GitlabStore(repo_id, branch, access_token=access_token)
app = create_app(
    store,
    otel_exporter_http_endpoint=otel_exporter_http_endpoint,
)
