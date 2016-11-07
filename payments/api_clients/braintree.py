from django.conf import settings
import braintree
import uuid
import OpenSSL


class Braintree_API():
    def __init__(self):
        mode = settings.BRAINTREE_API_MODE

        if mode == 'SANDBOX':
            braintreecfg = settings.BRAINTREE_API['SANDBOX']
            braintree.Configuration.configure(
                braintree.Environment.Sandbox,
                merchant_id=braintreecfg['merchant_id'],
                public_key=braintreecfg['public_key'],
                private_key=braintreecfg['private_key'],
                timeout=braintreecfg['timeout'])
            self.merchant_accounts = braintreecfg['merchant_accounts']
            self.braintree_vault = braintreecfg['vault']
        else:
            braintreecfg = settings.BRAINTREE_API['PRODUCTION']
            braintree.Configuration.configure(
                braintree.Environment.Production,
                merchant_id=braintreecfg['merchant_id'],
                public_key=braintreecfg['public_key'],
                private_key=braintreecfg['private_key'],
                timeout=braintreecfg['timeout'])
            self.merchant_accounts = braintreecfg['merchant_accounts']
            self.braintree_vault = braintreecfg['vault']

    def get_client_token(self, customerpk):
        if self.braintree_vault:
            try:
                result = braintree.ClientToken.generate({
                    "customer_id": customerpk
                })
            except:
                result = braintree.ClientToken.generate()
        else:
            result = braintree.ClientToken.generate()
        return result

    def get_client_token_history(self, profile):
        if profile.sig_key == '' or profile.sig_key is None:
            profile.sig_key = self.get_usersigkey()
            profile.save()
        customer = self.Customer_Find(profile.sig_key)
        user = profile.user
        if not customer:
            result = self.Customer_Create(user, profile.sig_key)
            if result.is_success:
                resultcc = True
            else:
                resultcc = False
        else:
            resultcc = True

        if resultcc:
            result = braintree.ClientToken.generate({
                "customer_id": profile.sig_key
            })
        else:
            result = None
        return result

    def get_usersigkey(self):
        key = str(uuid.UUID(bytes=OpenSSL.rand.bytes(16)))
        key = key.split("-")
        key = "".join(key)
        return key

    def Customer_Find(self, key):
        try:
            customer = braintree.Customer.find(key)
        except:
            customer = None
        return customer

    def Customer_Create(self, user, sig_key):
        if user.first_name != '':
            first_name = user.first_name
        else:
            first_name = user.username

        if user.last_name != '':
            last_name = user.last_name
        else:
            last_name = ''

        result = braintree.Customer.create({'id': sig_key,
                                            "first_name": first_name,
                                            "last_name": last_name})
        return result

    def PaymentMethod_Create(self, sig_key, payment_method_nonce):
        result = braintree.PaymentMethod.create({
            "customer_id": sig_key,
            "payment_method_nonce": payment_method_nonce,
            "options": {
                "verify_card": True,
                "fail_on_duplicate_payment_method": False
                #                "fail_on_duplicate_payment_method": True
            }
        })

        return result

    def Make_Default(self, paymentmethod):
        if paymentmethod.type == 'PayPal':
            result = braintree.PayPalAccount.update(paymentmethod.token, {
                "options": {"make_default": True}
            })
        elif paymentmethod.type == 'Card':
            result = braintree.PaymentMethod.update(paymentmethod.token, {
                "options": {
                    "make_default": True
                }
            })
        else:
            result = None

        return result

    def Delete_PaymentMethod(self, paymentmethod):
        result = braintree.PaymentMethod.delete(paymentmethod.token)
        return result

    def Send_Payment(self, paymentmethod, amount, currency=None):
        if not currency and currency not in self.merchant_accounts:
            raise ValueError("Payment not using the correct currency")

        result = braintree.Transaction.sale(
            {"payment_method_token": paymentmethod.token,
             "amount": amount,
             "merchant_account_id": self.merchant_accounts[currency],
             "options": {"submit_for_settlement": True}
             })
        return result

braintreeAPI = Braintree_API()
