from pathlib import Path

import pytest
from polylith.libs import lock_files

test_path = Path("./test/test_data")
project_data = {"path": test_path}

expected_libraries = {
    "annotated-types": "0.7.0",
    "anyio": "4.4.0",
    "click": "8.1.7",
    "fastapi": "0.109.2",
    "h11": "0.14.0",
    "idna": "3.7",
    "pydantic": "2.7.4",
    "pydantic-core": "2.18.4",
    "sniffio": "1.3.1",
    "starlette": "0.36.3",
    "typing-extensions": "4.12.2",
    "uvicorn": "0.25.0",
}

pdm_lock_file = "pdm"
piptools_lock_file = "piptools"
pixi_lock_file = "pixi"
rye_lock_file = "rye"
uv_lock_file = "uv"
uv_workspace_lock_file = "uv_workspaces"

test_lock_files = {
    pdm_lock_file: "toml",
    piptools_lock_file: "text",
    pixi_lock_file: "yaml",
    rye_lock_file: "text",
    uv_lock_file: "toml",
    uv_workspace_lock_file: "toml",
}


@pytest.fixture
def setup(monkeypatch):
    monkeypatch.setattr(lock_files, "patterns", test_lock_files)


def test_find_lock_files(setup):
    res = lock_files.find_lock_files(project_data["path"])

    assert res == test_lock_files


def test_pick_lock_file(setup):
    res = lock_files.pick_lock_file(project_data["path"])

    assert res.get("filename")
    assert res.get("filetype")


def test_parse_contents_of_rye_lock_file(setup):
    names = lock_files.extract_libs(project_data, rye_lock_file, "text")

    assert names == expected_libraries


def test_parse_contents_of_pdm_lock_file(setup):
    names = lock_files.extract_libs(project_data, pdm_lock_file, "toml")

    assert names == expected_libraries


def test_parse_contents_of_pip_tools_lock_file(setup):
    names = lock_files.extract_libs(project_data, piptools_lock_file, "text")

    assert names == expected_libraries


def test_parse_contents_of_pixi_tools_lock_file(setup):
    names = lock_files.extract_libs(project_data, pixi_lock_file, "yaml")

    assert names == expected_libraries


def test_parse_contents_of_uv_lock_file(setup):
    names = lock_files.extract_libs(project_data, uv_lock_file, "toml")

    assert names == expected_libraries


def _extract_workspace_member_libs(name: str) -> dict:
    data = lock_files.get_workspace_enabled_lock_file_data(
        test_path, uv_workspace_lock_file, "toml"
    )

    extended_project_data = {**project_data, **{"name": name}}

    return lock_files.extract_workspace_member_libs(
        data,
        extended_project_data,
    )


def test_parse_contents_of_uv_workspaces_aware_lock_file(setup):
    expected_gcp_libs = {
        "functions-framework": "3.5.0",
        "click": "8.1.7",
        "colorama": "0.4.6",
        "cloudevents": "1.11.0",
        "deprecation": "2.1.0",
        "packaging": "24.1",
        "flask": "3.0.3",
        "blinker": "1.8.2",
        "importlib-metadata": "8.2.0",
        "zipp": "3.20.0",
        "itsdangerous": "2.2.0",
        "jinja2": "3.1.4",
        "markupsafe": "2.1.5",
        "werkzeug": "3.0.3",
        "gunicorn": "23.0.0",
        "watchdog": "4.0.2",
    }

    expected_consumer_libs = {"confluent-kafka": "2.3.0"}
    expected_cli_libs_with_recursive_deps = {
        "rich": "13.8.0",
        "tomlkit": "0.13.2",
        "typer": "0.12.5",
        "markdown-it-py": "3.0.0",
        "pygments": "2.18.0",
        "mdurl": "0.1.2",
        "mdit-py-plugins": "0.4.2",
        "click": "8.1.7",
        "colorama": "0.4.6",
        "shellingham": "1.5.4",
        "typing-extensions": "4.12.2",
    }

    gcp_libs = _extract_workspace_member_libs("my-gcp-function-project")
    consumer_libs = _extract_workspace_member_libs("consumer-project")
    aws_lambda_libs = _extract_workspace_member_libs("my-aws-lambda-project")
    non_existing = _extract_workspace_member_libs("this-workspace-member-doesnt-exist")

    gcp_libs_from_normalized_name = _extract_workspace_member_libs(
        "my_gcp_Function-project"
    )

    cli_libs = _extract_workspace_member_libs("polylith-cli")

    assert gcp_libs == expected_gcp_libs
    assert consumer_libs == expected_consumer_libs
    assert aws_lambda_libs == {}
    assert non_existing == {}

    assert gcp_libs_from_normalized_name == expected_gcp_libs

    assert cli_libs == expected_cli_libs_with_recursive_deps


def test_parse_contents_of_uv_workspaces_aware_lock_file_with_optional_dependencies(
    setup,
):
    expected_regular = {
        "fastapi": "0.106.0",
        "anyio": "3.7.1",
        "exceptiongroup": "1.2.2",
        "idna": "3.7",
        "sniffio": "1.3.1",
        "pydantic": "2.8.2",
        "annotated-types": "0.7.0",
        "pydantic-core": "2.20.1",
        "typing-extensions": "4.12.2",
        "starlette": "0.27.0",
        "uvicorn": "0.25.0",
        "click": "8.1.7",
        "colorama": "0.4.6",
        "h11": "0.14.0",
    }

    expected_optionals = {
        "requests": "2.32.3",
        "certifi": "2024.12.14",
        "charset-normalizer": "3.4.1",
        "urllib3": "2.3.0",
    }
    expected = {**expected_regular, **expected_optionals}

    my_fastapi_libs = _extract_workspace_member_libs("my-fastapi-project")

    assert my_fastapi_libs == expected
