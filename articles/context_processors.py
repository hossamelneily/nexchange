from django.conf import settings


def cms(request):
    c = {
        'lang': request.LANGUAGE_CODE,
        'contact': settings.CONTACT,
    }
    return c
