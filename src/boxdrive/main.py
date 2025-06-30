from boxdrive import create_app
from boxdrive.stores import MemoryStore

store = MemoryStore()
app = create_app(store)