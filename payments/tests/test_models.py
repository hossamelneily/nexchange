from core.tests.base import UserBaseTestCase
from payments.models import UserCards


class UserCardsTest(UserBaseTestCase):

    def create_card(self):

        self.data = {
            'card_id': 'ade869d8-7913-4f67-bb4d-72719f0a2be0',
            'address_id': '145ZeN94MAtTmEgvhXEch3rRgrs7BdD2cY',
            'currency': 'BTC',
            'user': self.user,
        }
        usercards = UserCards.objects.create(**self.data)
        return usercards

    def test_usercards_creation(self):
        c = self.create_card()
        self.assertTrue(isinstance(c, UserCards))
        self.assertEqual(c.__str__(), c.card_id)
