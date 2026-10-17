# Import every model module so its table is registered on Base.metadata.
from app.models import app_settings, card, review_log  # noqa: F401
