from django.conf import settings


def site(request):
    return {
        "SITE_URL": settings.SITE_URL,
        "GA_MEASUREMENT_ID": settings.GA_MEASUREMENT_ID,
    }
