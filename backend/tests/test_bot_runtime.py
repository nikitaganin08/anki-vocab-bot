import app.models.anki_sync_attempt as anki_sync_attempt_model
import app.models.card as card_model
from app.bot.runtime import MODEL_MODULES


def test_runtime_eagerly_imports_model_modules() -> None:
    assert anki_sync_attempt_model in MODEL_MODULES
    assert card_model in MODEL_MODULES
