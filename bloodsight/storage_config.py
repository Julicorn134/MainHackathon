"""Server-only storage settings. Selecting cloud storage never falls back to local data."""
import base64
import json
import os
from urllib.parse import urlsplit

import ai_config


class StorageUnavailable(ValueError):
    """Safe, user-visible storage error; never include a response body or credentials."""


def settings() -> dict:
    try:
        local = ai_config.read_secrets()
    except ValueError as exc:
        raise StorageUnavailable(str(exc)) from None

    def get(key, default=""):
        return str(os.environ.get(key) or local.get(key) or default).strip()

    backend = get("BLOODSIGHT_DATA_BACKEND", "sqlite").lower()
    if backend not in ("sqlite", "supabase"):
        raise StorageUnavailable("Choose sqlite or supabase for BLOODSIGHT_DATA_BACKEND in server settings.")
    return {"backend": backend, "url": get("SUPABASE_URL").rstrip("/"),
            "key": get("SUPABASE_SECRET_KEY") or get("SUPABASE_SERVICE_ROLE_KEY")}


def cloud_settings() -> dict:
    config = settings()
    try:
        parsed = urlsplit(config["url"])
        valid = (parsed.scheme == "https" and parsed.hostname and parsed.hostname.endswith(".supabase.co")
                 and not any((parsed.username, parsed.password, parsed.port, parsed.path, parsed.query, parsed.fragment)))
    except ValueError:
        valid = False
    if not valid:
        raise StorageUnavailable("Set SUPABASE_URL to the project's https://PROJECT.supabase.co address in server settings.")
    key = config["key"]
    if key.startswith("sb_secret_"):
        return config
    # Check legacy key type before sending it; this is not JWT authentication.
    try:
        payload = key.split(".")[1]
        role = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))).get("role")
    except (ValueError, IndexError, AttributeError, TypeError):
        role = None
    if role != "service_role":
        raise StorageUnavailable("Add a Supabase secret key (or legacy service_role key) to server settings. "
                                 "A public/publishable key cannot access these staff records.")
    return config
