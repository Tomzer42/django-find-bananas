from django.conf import settings


def site(request):
    return {
        "SITE_URL": settings.SITE_URL,
        "GA_MEASUREMENT_ID": settings.GA_MEASUREMENT_ID,
        # Names as written in settings (each in its own language), not
        # translated like {% get_available_languages %} would.
        "SITE_LANGUAGES": settings.LANGUAGES,
        "NOINDEX": settings.NOINDEX,
        "GOOGLE_LOGIN": bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET),
    }
