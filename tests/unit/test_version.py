import pathlib
import tomllib

import boxdrive

root_dir = pathlib.Path(__file__).parent.parent.parent


def test_pyproject_version():
    pyproject_path = root_dir / "pyproject.toml"

    data = tomllib.loads(pyproject_path.read_text())
    pyproject_version = data["project"]["version"]

    assert pyproject_version == boxdrive.__version__
