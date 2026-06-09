"""Removed account-recovery and client state-import surfaces stay unavailable."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import auth
from app import app


def test_password_recovery_function_removed():
    assert not hasattr(auth, "recover_usernames_by_password")


def test_unsafe_routes_removed():
    routes = {(route.path, method) for route in app.routes for method in getattr(route, "methods", set())}
    assert ("/api/auth/recover_username", "POST") not in routes
    assert ("/api/cloud/state", "POST") not in routes
    assert ("/api/cloud/import_local", "POST") not in routes
    assert ("/api/import_state", "POST") not in routes
