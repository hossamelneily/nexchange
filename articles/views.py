from django.template.loader import get_template
from articles.models import CmsPage
from django.http.response import Http404, HttpResponse
from django.conf import settings
from django.utils.translation import ugettext_lazy as _


def cms_page(request, page_name):
    template = get_template('articles/cms_default.html')
    page = head = body = written_by = None

    try:
        page = CmsPage.objects.get(
            name=page_name,
            locale=request.LANGUAGE_CODE
        )
    except CmsPage.DoesNotExist:
        if not settings.DEBUG:
            raise Http404(_("Page not found"))

    if page:
        head = page.head
        body = page.body
        written_by = page.written_by

    cms_menu = []
    all_cms = [sf for sf in settings.CMSPAGES.values()]

    for a in all_cms:
        cms_menu = [sf for sf in a if page_name in sf]
        if len(cms_menu) > 0:
            cms_menu = a
            break

    context = {
        'cmsmenu': cms_menu,
        'head': head,
        'body': body,
        'written_by': written_by, }

    return HttpResponse(template.render(context, request))
