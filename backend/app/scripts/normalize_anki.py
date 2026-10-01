"""Run with an open Anki Collection; see docs/normalize-anki.md."""

from __future__ import annotations

import html
import json
import re
from collections import defaultdict
from pathlib import Path

OLD_MODEL = "Простая (с вводом ответа)(тестовое)"
NEW_MODEL = "VocabularyCard"
DECK = "English::Inbox"
ARCHIVE = "English::Duplicate archive"
FIELD_MAP = {"Front": "Translation", "Back": "Word", "Sound": "PronunciationAudio"}
NEW_FIELDS = {
    "Word",
    "Translation",
    "PronunciationAudio",
    "Transcription",
    "Explanation",
    "Example",
}


def normalized_word(value: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]*>", "", value)).split()).casefold()


def inspect_collection(col) -> dict:
    """Read only: exact words are candidates, not proof of identical meanings."""
    target = col.models.by_name(NEW_MODEL)
    if target is None or {f["name"] for f in target["flds"]} != NEW_FIELDS:
        raise ValueError("VocabularyCard must have the six expected fields")
    if target["type"] != 0 or len(target["tmpls"]) != 1:
        raise ValueError("VocabularyCard must have exactly one ordinary card template")
    groups = defaultdict(list)
    convert = []
    for nid in col.find_notes(f'deck:"{DECK}"'):
        note = col.get_note(nid)
        model = note.note_type()
        if model["name"] not in (OLD_MODEL, NEW_MODEL):
            continue
        old = model["name"] == OLD_MODEL
        if old and (
            {f["name"] for f in model["flds"]} != set(FIELD_MAP)
            or model["type"] != 0
            or len(model["tmpls"]) != 1
        ):
            raise ValueError("Legacy model must have Front, Back, Sound and one template")
        cards = note.cards()
        if len(cards) != 1 or cards[0].ord != 0 or cards[0].odid:
            raise ValueError(f"Note {nid}: expected one card outside a filtered deck")
        if col.decks.get(cards[0].did)["name"] != DECK:
            raise ValueError(f"Note {nid}: subdecks are not supported; move it to {DECK}")
        word = note["Back" if old else "Word"]
        key = normalized_word(word)
        if not key:
            raise ValueError(f"Note {nid} has an empty word")
        if old:
            convert.append(nid)
        groups[key].append(
            {
                "note_id": nid,
                "model": model["name"],
                "word": word,
                "translation": note["Front" if old else "Translation"],
                "example": "" if old else note["Example"],
                "reps": cards[0].reps,
                "tags": note.tags,
            }
        )
    duplicates = []
    for word, notes in sorted(groups.items()):
        if len(notes) < 2:
            continue
        # Keep backend-linked IDs intact; never guess how to merge backend records.
        modern = [n for n in notes if n["model"] == NEW_MODEL]
        linked = [n for n in notes if any(t.startswith("avb-card-") for t in n["tags"])]
        keep = linked if len(linked) == 1 else modern if not linked else []
        candidates = [
            n["note_id"]
            for n in notes
            if n not in keep and not any(t.startswith("avb-card-") for t in n["tags"])
        ]
        duplicates.append(
            {
                "word": word,
                "notes": notes,
                "archive_candidates": candidates if len(keep) == 1 else [],
            }
        )
    return {"convert_note_ids": sorted(convert), "duplicates": duplicates}


def run(col, *, report_path: str, apply: bool = False, archive_note_ids=()) -> dict:
    """Convert in place and archive ONLY explicitly selected duplicate note IDs."""
    report = inspect_collection(col)
    selected = set(archive_note_ids)
    allowed = {nid for group in report["duplicates"] for nid in group["archive_candidates"]}
    if not selected <= allowed:
        raise ValueError(f"Not eligible duplicate IDs: {sorted(selected - allowed)}")
    report["archive_note_ids"] = sorted(selected)
    path = Path(report_path).expanduser().resolve()
    # Never overwrite an earlier report or its associated backup.
    with path.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    if not apply or not (report["convert_note_ids"] or selected):
        return report
    backup_dir = path.with_suffix(".backup")
    backup_dir.mkdir()
    col.create_backup(backup_folder=str(backup_dir), force=True, wait_for_completion=True)
    if not list(backup_dir.glob("*.colpkg")):
        raise RuntimeError("No backup produced; collection has not been modified")
    if report["convert_note_ids"]:
        old = col.models.by_name(OLD_MODEL)
        new = col.models.by_name(NEW_MODEL)
        request = col.models.change_notetype_info(
            old_notetype_id=old["id"], new_notetype_id=new["id"]
        ).input
        old_fields = {f["name"]: i for i, f in enumerate(old["flds"])}
        reverse = {dest: src for src, dest in FIELD_MAP.items()}
        request.new_fields[:] = [
            old_fields[reverse[f["name"]]] if f["name"] in reverse else -1 for f in new["flds"]
        ]
        request.new_templates[:] = [0]
        request.note_ids[:] = report["convert_note_ids"]
        col.models.change_notetype_of_notes(request)
    if selected:
        card_ids = [card.id for nid in sorted(selected) for card in col.get_note(nid).cards()]
        col.set_deck(card_ids, col.decks.id(ARCHIVE))
        col.sched.suspend_cards(card_ids)
    return report
