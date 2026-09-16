from dataclasses import dataclass

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.card import Card
from app.schemas.llm import WordFamilyItem
from app.scripts.backfill_word_family import backfill_cards


@dataclass
class FakeWordFamilyGenerator:
    word_family: list[WordFamilyItem]

    def generate_word_family(
        self,
        canonical_text: str,
        *,
        explanation: str,
        translation_variants: list[str],
    ) -> list[WordFamilyItem]:
        return self.word_family


def make_card(*, card_id: int, backfilled: bool) -> Card:
    return Card(
        id=card_id,
        source_text=f"word-{card_id}",
        source_language="en",
        entry_type="word",
        canonical_text="accommodate",
        canonical_text_normalized=f"accommodate-{card_id}",
        transcription=None,
        translation_variants_json=["размещать", "приспосабливать"],
        word_family_json=[],
        word_family_backfilled=backfilled,
        explanation="To provide space or adjust to a situation.",
        examples_json=["The hotel can accommodate guests.", "The room accommodates two people."],
        frequency=5,
        frequency_note=None,
        eligible_for_anki=True,
        llm_model="test-model",
    )


def test_backfill_updates_only_unprocessed_cards() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all(
            [
                make_card(card_id=1, backfilled=False),
                make_card(card_id=2, backfilled=True),
            ]
        )
        session.commit()

        summary = backfill_cards(
            session,
            FakeWordFamilyGenerator(
                word_family=[
                    WordFamilyItem(
                        word="accommodation",
                        part_of_speech="noun",
                        translation="размещение",
                    )
                ]
            ),
            limit=10,
        )

        updated = session.get(Card, 1)
        skipped = session.get(Card, 2)

    assert summary.selected == 1
    assert summary.updated == 1
    assert summary.failed == 0
    assert updated is not None
    assert updated.word_family_backfilled is True
    assert updated.word_family_json[0]["word"] == "accommodation"
    assert skipped is not None
    assert skipped.word_family_json == []
