from django.conf import settings
from django.http.response import Http404, HttpResponse
from django.template.loader import get_template
from django.utils.translation import ugettext_lazy as _

from articles.models import CmsPage


def cms_page(request, page_name):
    template = get_template('articles/cms_default.html')
    page = None
    try:
        page = CmsPage.objects.get(
            name=page_name,
            locale=request.LANGUAGE_CODE
        )
    except CmsPage.DoesNotExist:
        if not settings.DEBUG:
            raise Http404(_("Page not found"))

    cms_menu = []
    all_cms = [sf for sf in settings.CMSPAGES.values()]

    for a in all_cms:
        cms_menu = [sf for sf in a if page_name in sf]
        if len(cms_menu) > 0:
            cms_menu = a
            break

    context = {
        'page': page,
        'cmsmenu': cms_menu,
    }

    return HttpResponse(template.render(context, request))
