from django.conf import settings
from pytz import country_timezones


def analytics(request):
    """
    Use the variables returned in this function to
    render your Google Analytics tracking code template.
    """
    domain = request.META['HTTP_HOST']
    ga_ru = getattr(settings, 'GOOGLE_ANALYTICS_PROPERTY_ID_RU')
    ga_uk = getattr(settings, 'GOOGLE_ANALYTICS_PROPERTY_UK')
    ym_ru = getattr(settings, 'YANDEX_METRICA_ID_RU')
    ym_uk = getattr(settings, 'YANDEX_METRICA_ID_UK')

    return {
        'GOOGLE_ANALYTICS_PROPERTY_ID':
            ga_ru if domain.endWith('ru') else ga_uk,
        'YANDEX_METRICA_ID':
            ym_ru if domain.endWith('ru') else ym_uk,
    }


def recaptcha(request):
    """ Adds recaptcha sitekey to context.
    https://developers.google.com/recaptcha/docs/display
    """
    return {
        'RECAPTCHA_SITEKEY':
            getattr(settings, 'RECAPTCHA_SITEKEY')
    }


def country_code(request):
    try:
        country_code = timezone_country()[request.COOKIES['USER_TZ']]
        return {'COUNTRY_CODE': country_code}
    except KeyError:
        return {'COUNTRY_CODE': 'US'}


def timezone_country():
    timezone_country = {}
    for country_code in country_timezones:
        timezones = country_timezones[country_code]
        for timezone in timezones:
            timezone_country[timezone] = country_code
    return timezone_country
