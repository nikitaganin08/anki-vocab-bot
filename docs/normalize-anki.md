# Unify the local vocabulary cards

`backend/app/scripts/normalize_anki.py` runs inside Anki's Python console using
Anki's own collection API. No extra package installation or backend credentials
are needed. It does not edit SQLite directly or call the LLM.

Only `English::Inbox` is supported. Grammar and pronunciation decks are untouched.
Legacy `Front / Back / Sound` become `Translation / Word / PronunciationAudio`
in `VocabularyCard`. Missing explanations, examples and transcriptions stay empty.
Existing note IDs, card IDs, review history and scheduling survive conversion.
It does not repair incorrect examples or import legacy entries into the backend.

## Preview

Sync Anki first. Open its debug console and run (adjust the repository path):

```python
import runpy
migration = runpy.run_path('/Users/nganin/ganin/projects/own/anki-vocab-bot/backend/app/scripts/normalize_anki.py')
report = migration['run'](mw.col, report_path='/tmp/anki-preview.json')
print(report)
```

The report lists every conversion and exact-word duplicate group, including
translations, examples, review counts and note IDs. Case, HTML and whitespace are
ignored for matching; expressions, inflections and synonyms are not collapsed.
Equal words do not necessarily mean equal senses: review each pair.
The preview does not change the collection. Use a fresh report filename each run.

## Apply

Pass only the old duplicate IDs whose meanings you have reviewed:

```python
report = migration['run'](mw.col, report_path='/tmp/anki-applied.json', apply=True, archive_note_ids=[123, 456])
mw.reset()
```

Replace the example IDs with actual `archive_candidates` from the preview.
Omit `archive_note_ids` to convert formats only. Selected old duplicates are moved
to `English::Duplicate archive` and suspended. The modern note remains in Inbox,
keeping its backend ID and tags. Nothing is deleted and review histories are not
merged. Translations and audio on archived notes remain available for comparison.
Afterwards, archived notes also use VocabularyCard. To restore one to study, move
it back into Inbox and unsuspend it in Anki's browser.

Before the first mutation, a native `.colpkg` backup (without media) is created
in a new directory beside the report. Media files are never changed by this script.
The script refuses to apply if no backup file was produced. Operations are not
one transaction: if an error occurs after conversion, inspect the collection and
restore the backup before retrying with the old selection. A completed rerun
has no legacy notes left to convert; archived notes are outside the search scope.

Inspect the result before syncing. A note-type change may require a full sync;
use the modified desktop collection as the source when propagating the change.

## Verify locally

The integration tests need Anki's Python package and matching Python version.
They skip in the normal backend environment if Anki is absent. On this Mac:

```sh
PYTHONPATH="$HOME/Library/Application Support/AnkiProgramFiles/.venv/lib/python3.13/site-packages:$PWD/backend" backend/.venv/bin/python -m pytest backend/tests/test_normalize_anki.py -q
```

Use the runtime matching your installed Anki version. Test against a temporary
collection or a SQLite backup of your collection; never use the live profile as
a test fixture.
