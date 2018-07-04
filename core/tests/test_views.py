from django.core.urlresolvers import reverse

from core.tests.base import UserBaseTestCase


class SimpleViewsTestCase(UserBaseTestCase):

    def test_renders_main_view_redirect_code(self):
        response = self.client.get(reverse('main'))
        self.assertEqual(302, response.status_code)

    def test_renders_main_view_redirected(self):
        with self.assertTemplateUsed('referrals/index_referrals.html'):
            response = self.client.get(reverse('main'),
                                       follow=True)
            last_url, last_status_code = \
                response.redirect_chain[-1]
            self.assertEquals(last_url, '/en/referrals/')
            self.assertEquals(last_status_code, 302)
            self.assertEqual(200, response.status_code)
