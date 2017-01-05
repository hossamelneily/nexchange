from django.conf import settings

from pytz import country_timezones


def google_analytics(request):
    """
    Use the variables returned in this function to
    render your Google Analytics tracking code template.
    """
    ga_prop_id = getattr(settings, 'GOOGLE_ANALYTICS_PROPERTY_ID', False)
    ga_domain = getattr(settings, 'GOOGLE_ANALYTICS_DOMAIN', False)
    # production
    # if not settings.DEBUG and ga_prop_id and ga_domain:
    # dev
    if ga_prop_id and ga_domain:
        return {
            'GOOGLE_ANALYTICS_PROPERTY_ID': ga_prop_id,
            'GOOGLE_ANALYTICS_DOMAIN': ga_domain,
        }
    return {}

def country_code(request):
    try:
        country_code = timezone_country()[request.COOKIES['USER_TZ']]
        return {'COUNTRY_CODE': country_code}
    except KeyError:
        return {'COUNTRY_CODE': 'asdfasdf'}

def timezone_country():
    timezone_country = {}
    for country_code in country_timezones:
       timezones = country_timezones[country_code]
       for timezone in timezones:
           timezone_country[timezone] = country_code
    return timezone_country
