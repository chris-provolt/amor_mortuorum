from pathlib import Path
import sys

from tools.ci.build_binary import (
    find_spec_file,
    parse_pyproject_entrypoint,
    resolve_module_file,
    detect_entrypoint,
    platform_tag,
)


def test_find_spec_file(tmp_path: Path):
    (tmp_path / "pyinstaller").mkdir()
    spec = tmp_path / "pyinstaller" / "app.spec"
    spec.write_text("# spec content", encoding="utf-8")
    assert find_spec_file(tmp_path) == spec


def test_parse_pyproject_entrypoint(tmp_path: Path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
        [project]
        name = "demo"
        version = "0.1.0"

        [project.scripts]
        demo = "pkg.cli:main"
        """,
        encoding="utf-8",
    )
    ep = parse_pyproject_entrypoint(pyproject)
    assert ep == "pkg.cli:main"


def test_resolve_module_file_and_detect_entrypoint(tmp_path: Path, monkeypatch):
    # Create a minimal package with a script module
    src = tmp_path / "src"
    pkg = src / "pkg"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("__all__ = []\n", encoding="utf-8")
    (pkg / "cli.py").write_text("def main():\n    pass\n", encoding="utf-8")

    # Ensure import works
    monkeypatch.syspath_prepend(str(src))

    # Module path
    mod_file = resolve_module_file("pkg.cli:main")
    assert mod_file is not None
    assert mod_file.name == "cli.py"

    # Fallback detect from src/**/__main__.py when no scripts
    (pkg / "__main__.py").write_text("print('ok')\n", encoding="utf-8")
    ep = detect_entrypoint(tmp_path)
    assert ep is not None
    assert ep.name == "__main__.py"


def test_platform_tag_has_os_and_arch():
    tag = platform_tag()
    assert any(tag.startswith(os) for os in ("linux-", "windows-", "macos-"))
    assert any(tag.endswith(arch) for arch in ("x86_64", "arm64"))
