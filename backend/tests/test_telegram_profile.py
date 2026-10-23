from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

PATH = Path(__file__).resolve().parents[2] / "deploy" / "telegram" / "profile.py"
spec = importlib.util.spec_from_file_location("telegram_profile", PATH)
assert spec is not None and spec.loader is not None
profile = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profile)


def fake_call(**overrides: Any):
    state: dict[str, Any] = {
        "getMyName": {"name": profile.DESIRED["name"]},
        "getMyShortDescription": {"short_description": profile.DESIRED["short_description"]},
        "getMyDescription": {"description": profile.DESIRED["description"]},
        "private": [],
        "default": profile.DESIRED["commands"],
    }
    state.update(overrides)

    def call(method: str, payload: dict[str, Any] | None) -> Any:
        if method == "getMyCommands":
            return state["private"] if payload else state["default"]
        return state[method]

    return call


def test_nothing_to_write_when_in_sync() -> None:
    assert profile.plan(fake_call()) == []


def test_description_comparison_ignores_surrounding_whitespace() -> None:
    padded = {"description": f"  {profile.DESIRED['description']}\n"}

    assert profile.plan(fake_call(getMyDescription=padded)) == []


def test_only_differing_values_are_written() -> None:
    call = fake_call(
        getMyName={"name": "Anki"},
        default=[{"command": "find", "description": "old"}],
    )

    methods = [method for method, _ in profile.plan(call)]

    assert methods == ["setMyName", "setMyCommands"]


def test_stale_private_chat_menu_is_deleted_before_setting_commands() -> None:
    call = fake_call(private=[{"command": "admin", "description": "old"}], default=[])

    methods = [method for method, _ in profile.plan(call)]

    assert methods == ["deleteMyCommands", "setMyCommands"]


def test_admin_command_is_not_listed() -> None:
    assert "admin" not in [c["command"] for c in profile.DESIRED["commands"]]
