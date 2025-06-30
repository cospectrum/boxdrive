from boxdrive import MemoryStore, create_app

store = MemoryStore()
app = create_app(store)
