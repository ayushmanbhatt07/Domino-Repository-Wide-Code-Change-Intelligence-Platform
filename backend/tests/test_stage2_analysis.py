import pytest
from analysis import RepositoryAnalyzer
import os

@pytest.fixture
def analyzer():
    return RepositoryAnalyzer()

@pytest.fixture
def fixture_path():
    return "d:/Domino-Repository-Wide-Code-Change-Intelligence-Platform/backend/tests/fixtures/sample_repo"

@pytest.mark.stage2
def test_file_discovery(analyzer, fixture_path):
    res = analyzer.analyze(fixture_path)
    paths = [f["path"] for f in res["files"]]
    assert any("app/main.py" in p for p in paths)
    assert not any("__pycache__" in p for p in paths)
    
@pytest.mark.stage2
def test_functions_and_classes(analyzer, fixture_path):
    res = analyzer.analyze(fixture_path)
    funcs = [f["name"] for file in res["files"] for f in file.get("functions", [])]
    classes = [c["name"] for file in res["files"] for c in file.get("classes", [])]
    
    assert "get_users" in funcs
    assert "validate_user" in funcs
    assert "UserService" in classes

@pytest.mark.stage2
@pytest.mark.xfail(strict=True, reason="dict.get() creates fake routes (B1)")
def test_fake_routes(analyzer, fixture_path):
    res = analyzer.analyze(fixture_path)
    routes = [r for file in res["files"] for r in file.get("routes", [])]
    
    # Check if there is a fake route from db.py's d.get("k")
    fake_route = next((r for r in routes if r["path"] == "k"), None)
    assert fake_route is None

@pytest.mark.stage2
@pytest.mark.xfail(strict=True, reason="Callee names store raw source text (B2)")
def test_callee_names(analyzer, fixture_path):
    res = analyzer.analyze(fixture_path)
    for file in res["files"]:
        for f in file.get("functions", []):
            for c in f.get("calls", []):
                assert "\\n" not in c
                assert "source[" not in c
