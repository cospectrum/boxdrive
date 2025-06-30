#!/usr/bin/env python3
"""Example usage of BoxDrive with in-memory store for FastAPI CLI."""

from boxdrive import MemoryStore, create_app

store = MemoryStore()
app = create_app(store)
