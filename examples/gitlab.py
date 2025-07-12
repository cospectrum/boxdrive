import os

from boxdrive import create_app
from boxdrive.stores import GitlabStore

repo_id = int(os.environ["REPO_ID"])
branch = os.environ.get("BRANCH", "main")
access_token = os.environ["ACCESS_TOKEN"]

store = GitlabStore(repo_id, branch, access_token=access_token)
app = create_app(store)
