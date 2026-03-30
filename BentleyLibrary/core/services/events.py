import logging

from core.models import ProductEvent

logger = logging.getLogger(__name__)


def log_product_event(event_type, request=None, **payload):
    try:
        user = getattr(request, "user", None) if request else None
        role = ""
        if user and user.is_authenticated:
            role = getattr(getattr(user, "library_profile", None), "role", "")

        ProductEvent.objects.create(
            event_type=event_type,
            user=user if user and user.is_authenticated else None,
            role=role,
            query_text=payload.pop("query_text", ""),
            book_id=payload.pop("book_id", None),
            reading_goal=payload.pop("reading_goal", ""),
            metadata=payload,
        )
    except Exception:
        logger.exception("Failed to log product event '%s'", event_type)
