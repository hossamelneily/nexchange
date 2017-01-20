from django.conf import settings
from pytz import country_timezones


def analytics(request):
    """
    Use the variables returned in this function to
    render your Google Analytics tracking code template.
    """
    return {
        'GOOGLE_ANALYTICS_PROPERTY_ID':
            getattr(settings, 'GOOGLE_ANALYTICS_PROPERTY_ID'),
        'GOOGLE_ANALYTICS_DOMAIN':
            getattr(settings, 'GOOGLE_ANALYTICS_DOMAIN'),
        'YANDEX_METRICA_ID':
            getattr(settings, 'YANDEX_METRICA_ID')
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
