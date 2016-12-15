from django.conf import settings


def cms(request):
    c = {
        'lang': request.LANGUAGE_CODE,
        'social': settings.SOCIAL
    }
    return c
