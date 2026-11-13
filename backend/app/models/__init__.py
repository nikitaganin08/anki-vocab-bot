# Import every model module so its table is registered on Base.metadata.
from app.models import app_settings, card, daily_progress, review_log, speaking  # noqa: F401
