from django.conf import settings


def event_branding(request):
    """Expose audience-facing event branding to every template.

    Sourced from settings (env-overridable) so rebranding for a new event
    needs no template edits. See ``EVENT_TITLE`` / ``EVENT_SUBTITLE`` in
    ``ushu/settings.py``.
    """
    return {
        'EVENT_TITLE': settings.EVENT_TITLE,
        'EVENT_SUBTITLE': settings.EVENT_SUBTITLE,
    }
