from core.models import Currency

from selenium.webdriver.support.select import Select
from core.models import Pair
from core.tests.test_ui.base import BaseTestUI


class TestUIDisplay(BaseTestUI):

    def test_currency_selection_by_url(self):
        self.workflow = 'CURRENCY_SELECT'
        self.screenpath2 = 'MAIN SCREENS'
        enabled_pairs = Pair.objects.filter(disabled=False)
        pair_names = [pair.name for pair in enabled_pairs]
        # lots of pairs so test only every nth pair
        nth = len(Currency.objects.filter(is_crypto=False))
        picked_names = [pair_names[i] for i in range(0, len(pair_names), nth)]
        for pair_name in picked_names:
            self.screenshot_no = 1
            self.get_currency_pair_main_screen(pair_name)
            self.do_screenshot('main_{}'.format(pair_name))
            c_from = Select(self.driver.find_element_by_xpath(
                '//select[@name="currency_from"]'))
            c_to = Select(self.driver.find_element_by_xpath(
                '//select[@name="currency_to"]'))
            from_text = c_to.first_selected_option.text
            to_text = c_from.first_selected_option.text
            self.assertEqual(pair_name, from_text + to_text)
