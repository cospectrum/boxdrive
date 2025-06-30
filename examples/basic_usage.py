from boxdrive import create_app
from boxdrive.stores import InMemoryStore

store = InMemoryStore()
app = create_app(store)
