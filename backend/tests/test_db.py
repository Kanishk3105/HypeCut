from __future__ import annotations

from pathlib import Path

import pytest

from hypecut import db as dbmod


def make_conn(tmp_path: Path):
    conn = dbmod.connect(tmp_path / "test.db")
    dbmod.init_db(conn)
    return conn


def test_project_roundtrip(tmp_path: Path) -> None:
    conn = make_conn(tmp_path)
    project = dbmod.create_project(conn, "My stream", "youtube", "https://youtu.be/abc123")
    assert project["name"] == "My stream"
    assert project["source_type"] == "youtube"
    assert project["status"] == "created"
    assert project["id"]

    fetched = dbmod.get_project(conn, project["id"])
    assert fetched == project

    updated = dbmod.update_project(conn, project["id"], name="Renamed", status="ingested")
    assert updated["name"] == "Renamed"
    assert updated["status"] == "ingested"

    assert dbmod.list_projects(conn) == [updated]

    assert dbmod.delete_project(conn, project["id"]) is True
    assert dbmod.get_project(conn, project["id"]) is None
    assert dbmod.delete_project(conn, project["id"]) is False


def test_project_rejects_bad_source_type(tmp_path: Path) -> None:
    conn = make_conn(tmp_path)
    with pytest.raises(ValueError):
        dbmod.create_project(conn, "x", "ftp", "ftp://example.com")


def test_update_missing_project_returns_none(tmp_path: Path) -> None:
    conn = make_conn(tmp_path)
    assert dbmod.update_project(conn, "nope", name="x") is None


def test_settings_roundtrip(tmp_path: Path) -> None:
    conn = make_conn(tmp_path)
    assert dbmod.get_setting(conn, "missing") is None
    dbmod.set_setting(conn, "model", "base")
    dbmod.set_setting(conn, "model", "small")
    assert dbmod.get_setting(conn, "model") == "small"


def test_persistence_across_connections(tmp_path: Path) -> None:
    path = tmp_path / "persist.db"
    conn1 = dbmod.connect(path)
    dbmod.init_db(conn1)
    project = dbmod.create_project(conn1, "persist", "local", "C:/videos/a.mp4")
    conn1.close()

    conn2 = dbmod.connect(path)
    dbmod.init_db(conn2)
    assert dbmod.get_project(conn2, project["id"]) is not None
