from types import SimpleNamespace

import pytest


class Scanner:
    def __init__(self, clean, reason=None):
        self.result = SimpleNamespace(clean=clean, reason=reason)

    def scan(self, object_key):
        return self.result


class Metadata:
    def __init__(self):
        self.completed = []
        self.rejected = []

    def record_completed(self, upload_id, object_key):
        self.completed.append(upload_id)

    def record_rejected(self, upload_id, reason):
        self.rejected.append(upload_id)


class Events:
    def __init__(self):
        self.names = []

    def publish(self, name, payload):
        self.names.append(name)


@pytest.fixture
def fakes():
    return SimpleNamespace(
        upload=SimpleNamespace(id="upload-1", object_key="quarantine/upload-1"),
        clean_scanner=Scanner(clean=True),
        infected_scanner=Scanner(clean=False, reason="malware"),
        metadata=Metadata(),
        events=Events(),
    )
