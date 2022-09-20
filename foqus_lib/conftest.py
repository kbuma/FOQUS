import contextlib
import os
from pathlib import Path
import shutil
import zipfile
import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--qtbot-slowdown-wait-ms",
        action="store",
        default=100,
        help="Slow down the qtbot by waiting for this amount of time (in  ms) before performing each action.",
    )
    parser.addoption(
        "--qtbot-artifacts",
        action="store",
        default="qtbot-artifacts",
        help=(
            "Choose how to handle artifacts (screenshots, widget search logs, etc) generated by the qtbot."
            " If set to a non-empty string (default), artifacts will be saved to a subdirectory with that name"
            " under the pytest base temporary directory (set automatically, or customizable with the built-in --basetemp option)."
            " If set to an empty string, artifacts collection will be disabled."
        ),
    )
    parser.addoption(
        "--main-window-size",
        action="store",
        default="800x600",
        help="Size of the main window specified as a <width>x<height> string",
    )
    parser.addoption("--main-window-title", action="store", default="FOQUS")


@pytest.fixture(scope="session")
def _repo_root():
    this_file = Path(__file__).resolve()  # FOQUS/foqus_lib/conftest.py
    repo_root = this_file.parent.parent
    assert (repo_root / ".git").is_dir()
    return repo_root


@pytest.fixture(scope="session")
def foqus_examples_dir(_repo_root):
    _examples_dir = _repo_root / "examples"
    assert _examples_dir.exists()
    return _examples_dir


@pytest.fixture(scope="session")
def psuade_path():
    _psuade_path = shutil.which("psuade")
    assert _psuade_path is not None
    return Path(_psuade_path).resolve()


@pytest.fixture(
    scope="session",
)
def foqus_working_dir(
    request, tmp_path_factory, name: str = "foqus-working-dir"
) -> Path:
    d = tmp_path_factory.mktemp(name, numbered=False)

    yield d


@pytest.fixture(scope="session")
def foqus_ml_ai_models_dir(
    foqus_working_dir: Path,
) -> Path:
    # skip this test if tensorflow is not available
    pytest.importorskip("tensorflow", reason="tensorflow not installed")

    return foqus_working_dir / "user_ml_ai_models"


@pytest.fixture(
    scope="session",
    autouse=True,
)
def install_ml_ai_model_files(
    foqus_examples_dir: Path, foqus_ml_ai_models_dir: Path
) -> Path:
    """
    This is a session-level fixture with autouse b/c it needs to be created
    before the main window is instantiated.
    """
    # skip this test if tensorflow is not available
    pytest.importorskip("tensorflow", reason="tensorflow not installed")

    print("installing ml_ai model files")
    models_dir = foqus_ml_ai_models_dir

    base_path = foqus_examples_dir / "other_files" / "ML_AI_Plugin"
    ts_models_base_path = base_path / "TensorFlow_2-7_Models"

    models_dir.mkdir(exist_ok=True, parents=False)

    for path in [
        base_path / "mea_column_model.py",
        ts_models_base_path / "mea_column_model.h5",
        ts_models_base_path / "AR_nocustomlayer.h5",
        base_path / "mea_column_model_customnormform.py",
        ts_models_base_path / "mea_column_model_customnormform.h5",
        base_path / "mea_column_model_customnormform_savedmodel.py",
        ts_models_base_path / "mea_column_model_customnormform_savedmodel.zip",
        base_path / "mea_column_model_customnormform_json.py",
        ts_models_base_path / "mea_column_model_customnormform_json.json",
        ts_models_base_path / "mea_column_model_customnormform_json_weights.h5",
    ]:
        shutil.copy2(path, models_dir)
    # unzip the zip file (could be generalized later to more files if needed)
    with zipfile.ZipFile(
        models_dir / "mea_column_model_customnormform_savedmodel.zip", "r"
    ) as zip_ref:
        zip_ref.extractall(models_dir)

    yield models_dir


@contextlib.contextmanager
def setting_working_dir(dest: Path) -> Path:
    from foqus_lib.service.flowsheet import _set_working_dir

    assert dest.is_dir()
    initial_working_dir = Path(os.getcwd())
    try:
        _set_working_dir(dest)
        yield dest
    finally:
        _set_working_dir(initial_working_dir)


@pytest.fixture(scope="session")
def foqus_session(
    foqus_working_dir: Path,
    psuade_path: Path,
):
    "Base FOQUS session object, initialized once per (pytest) session."
    print("starting foqus session")
    from foqus_lib.framework.session import session

    with setting_working_dir(foqus_working_dir) as wdir:
        session.makeWorkingDirStruct()
        session.makeWorkingDirFiles()

        dat = session.session(useCurrentWorkingDir=True)
        dat.foqusSettings.psuade_path = str(psuade_path)
        yield dat
    # TODO is there any cleanup to be done, considering that the directory will be changed?


def pytest_report_header(config):
    return f"pytest temporary directory: {config.option.basetemp}"


def pytest_terminal_summary(terminalreporter, config):
    tr = terminalreporter
    basetemp = config.option.basetemp

    tr.section("FOQUS information")

    tr.write_line(f"pytest temporary directory:\n\t{basetemp}")
    tr.write_line(f"subdirectories:")
    for path in Path(basetemp).rglob("*"):
        if path.is_dir():
            tr.write_line(f"\t{path}")
