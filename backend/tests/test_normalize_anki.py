import pytest

from app.scripts.normalize_anki import ARCHIVE, DECK, NEW_MODEL, OLD_MODEL, run

# Integration checks use Anki's runtime (see docs/normalize-anki.md).
anki = pytest.importorskip("anki.collection")


@pytest.fixture
def collection(tmp_path):
    col = anki.Collection(str(tmp_path / "collection.anki2"))
    for name, fields, front in [
        (OLD_MODEL, ["Front", "Back", "Sound"], "Front"),
        (
            NEW_MODEL,
            [
                "Word",
                "Translation",
                "Example",
                "Explanation",
                "PronunciationAudio",
                "Transcription",
            ],
            "Translation",
        ),
    ]:
        model = col.models.new(name)
        for field in fields:
            col.models.add_field(model, col.models.new_field(field))
        template = col.models.new_template("Card")
        template["qfmt"] = "{{" + front + "}}"
        template["afmt"] = "{{FrontSide}}"
        col.models.add_template(model, template)
        col.models.add(model)
    yield col
    col.close()


def add(col, model, word, translation):
    note = col.new_note(col.models.by_name(model))
    note["Back" if model == OLD_MODEL else "Word"] = word
    note["Front" if model == OLD_MODEL else "Translation"] = translation
    if model == OLD_MODEL:
        note["Sound"] = "[sound:test.mp3]"
    else:
        note.tags = ["avb-card-7"]
    col.add_note(note, col.decks.id(DECK))
    return note


def test_preview_then_conversion_and_archive_preserve_ids_and_schedule(collection, tmp_path):
    col = collection
    old = add(col, OLD_MODEL, " <b>Recall</b> ", "вспоминать")
    modern = add(col, NEW_MODEL, "recall", "отзывать")
    single = add(col, OLD_MODEL, "unique", "уникальный")
    card = old.cards()[0]
    card.reps, card.ivl, card.due, card.type, card.queue = 15, 20, 100, 2, 2
    col.update_card(card)
    before = (card.id, card.reps, card.ivl, card.due)
    report = run(col, report_path=str(tmp_path / "preview.json"))
    assert report["duplicates"][0]["archive_candidates"] == [old.id]
    assert col.get_note(old.id).note_type()["name"] == OLD_MODEL
    run(col, report_path=str(tmp_path / "apply.json"), apply=True, archive_note_ids=[old.id])
    assert list((tmp_path / "apply.backup").glob("*.colpkg"))
    converted = col.get_note(old.id)
    assert converted["Word"] == " <b>Recall</b> "
    assert converted["Translation"] == "вспоминать"
    assert converted["PronunciationAudio"] == "[sound:test.mp3]"
    assert converted["Example"] == ""
    card = converted.cards()[0]
    assert (card.id, card.reps, card.ivl, card.due) == before
    assert card.queue == -1
    assert col.decks.get(card.did)["name"] == ARCHIVE
    assert col.get_note(single.id).note_type()["name"] == NEW_MODEL
    assert col.get_note(modern.id).tags == ["avb-card-7"]
    assert col.get_note(modern.id)["Translation"] == "отзывать"
    again = run(col, report_path=str(tmp_path / "again.json"), apply=True)
    assert again["convert_note_ids"] == []
    assert again["duplicates"] == []


def test_cannot_archive_linked_note_or_unrelated_id(collection, tmp_path):
    old = add(collection, OLD_MODEL, "recall", "вспоминать")
    old.tags = ["avb-card-99"]
    collection.update_note(old)
    add(collection, NEW_MODEL, "recall", "вспоминать")
    for nid in (old.id, 123):
        with pytest.raises(ValueError, match="Not eligible"):
            run(
                collection,
                report_path=str(tmp_path / "invalid.json"),
                apply=True,
                archive_note_ids=[nid],
            )
    assert collection.get_note(old.id).note_type()["name"] == OLD_MODEL


def test_backup_failure_prevents_conversion(collection, tmp_path, monkeypatch):
    old = add(collection, OLD_MODEL, "recall", "вспоминать")
    monkeypatch.setattr(collection, "create_backup", lambda **kwargs: False)
    with pytest.raises(RuntimeError, match="No backup"):
        run(collection, report_path=str(tmp_path / "failed.json"), apply=True)
    assert collection.get_note(old.id).note_type()["name"] == OLD_MODEL


def test_can_archive_after_separate_format_conversion(collection, tmp_path):
    old = add(collection, OLD_MODEL, "recall", "вспоминать")
    modern = add(collection, NEW_MODEL, "recall", "вспоминать")
    run(collection, report_path=str(tmp_path / "format.json"), apply=True)
    report = run(
        collection,
        report_path=str(tmp_path / "archive.json"),
        apply=True,
        archive_note_ids=[old.id],
    )
    assert report["convert_note_ids"] == []
    assert collection.get_note(old.id).cards()[0].queue == -1
    assert collection.get_note(modern.id).cards()[0].queue != -1
