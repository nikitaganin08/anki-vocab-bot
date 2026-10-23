#!/usr/bin/env python3
"""Keep the Telegram bot profile (name, descriptions, command menu) in sync.

Telegram rate-limits profile edits (HTTP 429), so only the values that differ from what the bot
currently has are written; a deploy with nothing to change makes no write calls. Run by the
deploy workflow with TELEGRAM_BOT_TOKEN set.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any, Callable

DESIRED: dict[str, Any] = {
    "name": "Wordloop",
    "short_description": (
        "English words in context: instant cards and FSRS review right in Telegram."
    ),
    "description": (
        "Send a word, phrasal verb or idiom, in English or Russian. Wordloop makes a card: "
        'translation, transcription and natural usages like "give up smoking". Then it reminds '
        "you to review when the word starts to fade.\n\n"
        "/review — review words\n"
        "/find — find a word by description\n\n"
        "The Wordloop button next to the message field opens the app."
    ),
    "commands": [
        {"command": "review", "description": "Review words"},
        {"command": "find", "description": "Find a word by description"},
    ],
}
PRIVATE_SCOPE = {"scope": {"type": "all_private_chats"}}

Call = Callable[[str, dict[str, Any] | None], Any]


def plan(call: Call, desired: dict[str, Any] = DESIRED) -> list[tuple[str, dict[str, Any]]]:
    """Return the (method, payload) writes needed to reach `desired`."""
    updates: list[tuple[str, dict[str, Any]]] = []
    if call("getMyName", None)["name"].strip() != desired["name"]:
        updates.append(("setMyName", {"name": desired["name"]}))
    short = call("getMyShortDescription", None)["short_description"]
    if short.strip() != desired["short_description"]:
        updates.append(
            ("setMyShortDescription", {"short_description": desired["short_description"]})
        )
    if call("getMyDescription", None)["description"].strip() != desired["description"]:
        updates.append(("setMyDescription", {"description": desired["description"]}))
    # A leftover private-chat list would shadow the default menu in private chats.
    if call("getMyCommands", PRIVATE_SCOPE):
        updates.append(("deleteMyCommands", PRIVATE_SCOPE))
    if call("getMyCommands", None) != desired["commands"]:
        updates.append(("setMyCommands", {"commands": desired["commands"]}))
    # The menu button opens the Mini App in one tap; a command can only offer a button first.
    webapp_url = desired.get("webapp_url")
    if webapp_url:
        button = {"type": "web_app", "text": "Wordloop", "web_app": {"url": webapp_url}}
        current = call("getChatMenuButton", None)
        if (current.get("type"), current.get("text"), current.get("web_app")) != (
            "web_app",
            button["text"],
            button["web_app"],
        ):
            updates.append(("setChatMenuButton", {"menu_button": button}))
    return updates


def webapp_url_from_env() -> str | None:
    explicit = os.environ.get("TELEGRAM_WEBAPP_URL")
    if explicit:
        return explicit
    webhook = os.environ.get("TELEGRAM_WEBHOOK_URL", "").rstrip("/")
    return f"{webhook[: -len('/webhook')]}/webapp" if webhook.endswith("/webhook") else None


def telegram_call(token: str) -> Call:
    def call(method: str, payload: dict[str, Any] | None) -> Any:
        request = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/{method}",
            data=json.dumps(payload or {}).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                body = json.load(response)
        except urllib.error.HTTPError as exc:
            detail = json.loads(exc.read().decode() or "{}")
            retry = detail.get("parameters", {}).get("retry_after")
            raise SystemExit(
                f"{method}: HTTP {exc.code}" + (f", retry after {retry}s" if retry else "")
            )
        if not body.get("ok"):
            raise SystemExit(f"{method}: {body}")
        return body["result"]

    return call


def main() -> None:
    call = telegram_call(os.environ["TELEGRAM_BOT_TOKEN"])
    updates = plan(call, {**DESIRED, "webapp_url": webapp_url_from_env()})
    for method, payload in updates:
        call(method, payload)
        print(f"{method}: done")
    print("bot profile in sync" if not updates else f"{len(updates)} update(s) applied")


if __name__ == "__main__":
    sys.exit(main())
