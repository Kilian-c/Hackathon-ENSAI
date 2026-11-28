"""Version locale de secours : le moteur sert `frontend/dist` sur `/`, sans gêner l'API."""

from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import create_app, mount_frontend


def _dist(tmp_path: Path) -> Path:
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<!doctype html><title>Crash-Test</title>", encoding="utf-8")
    (tmp_path / "assets" / "app.js").write_text("console.log('ok')", encoding="utf-8")
    (tmp_path / "favicon.svg").write_text("<svg/>", encoding="utf-8")
    return tmp_path


def test_serves_the_interface_and_keeps_the_api_first(tmp_path: Path) -> None:
    client = TestClient(create_app(_dist(tmp_path)))
    page = client.get("/")
    assert page.status_code == 200 and "Crash-Test" in page.text
    assert "text/html" in page.headers["content-type"]
    assert client.get("/?exp=regression-lineaire&seed=42").status_code == 200  # la navigation passe par l'URL
    assert client.get("/assets/app.js").status_code == 200
    assert client.get("/favicon.svg").status_code == 200
    # l'API garde la priorité sur le dossier statique
    assert client.get("/api/health").json() == {"status": "ok"}
    experiments = client.get("/api/experiments")
    assert experiments.status_code == 200 and len(experiments.json()) >= 15
    run = client.post("/api/run", json={"experiment_id": "regression-lineaire", "state": {}})
    assert run.status_code == 200 and "measures" in run.json()


def test_unknown_files_and_api_paths_are_real_404s_not_the_html_page(tmp_path: Path) -> None:
    client = TestClient(create_app(_dist(tmp_path)))
    for path in ("/api/inconnue", "/assets/absent.js", "/nimporte/quoi"):
        response = client.get(path)
        assert response.status_code == 404 and "Crash-Test" not in response.text, path


def test_cannot_read_outside_the_dist_folder(tmp_path: Path) -> None:
    (tmp_path / "dist").mkdir()
    dist = _dist(tmp_path / "dist")
    (tmp_path / "secret.txt").write_text("secret", encoding="utf-8")  # à côté du dossier servi, pas dedans
    client = TestClient(create_app(dist))
    for path in ("/../secret.txt", "/%2e%2e/secret.txt", "/assets/../../secret.txt"):
        assert "secret" not in client.get(path).text, path


def test_without_a_build_nothing_changes(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path / "absent"))
    assert client.get("/").status_code == 404  # pas d'interface servie
    assert client.get("/api/health").status_code == 200
    empty = tmp_path / "vide"
    empty.mkdir()
    assert mount_frontend(create_app(empty), empty) is False  # un dossier sans index.html n'est pas servi


def test_experiments_are_loaded_at_startup_not_on_the_first_request(tmp_path: Path) -> None:
    from backend.api import registry

    registry.official.cache_clear()
    registry.content_digest.cache_clear()
    with TestClient(create_app(tmp_path / "absent")):  # le `with` exécute le démarrage du serveur
        assert registry.official.cache_info().currsize == 1
        assert registry.content_digest.cache_info().currsize == 1
