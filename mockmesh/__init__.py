# /Users/aman/mockmesh/mockmesh/__init__.py
from contextlib import contextmanager
from .hook import interceptor_engine
from .state import state_engine
from .server import start_server, stop_server

def enable():
    """Activates the in-process RAM hooks globally"""
    interceptor_engine.patch()

def disable():
    """Deactivates hooks and restores real network adapters"""
    interceptor_engine.unpatch()

def clean():
    """Wipes the physical disk cache folder completely clean"""
    state_engine.purge_disk_cache()

@contextmanager
def mockmesh():
    """Allows safe inline mocking blocks: with mockmesh():"""
    enable()
    try:
        yield
    finally:
        disable()
