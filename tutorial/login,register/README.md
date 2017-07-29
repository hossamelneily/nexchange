**User login and register workflows**

* *Description:* workflow for email 1.login and 2.registration. 1 happens when email is already registered, 2 when email is new. User cannot see any difference between 1 and 2.


* *Backend Description:* Each site user must have User(`django.contrib.models.User`) and Profile(`accounts.models.Profile`) instances.
These instances have one2one releation (`profile = user.profile, user = profile.user`).

* *Cards Description:* Card is a reference to third party resource i.e. ETH card is a credit card(currency ETH) on [Uphold](https://uphold.com). Address is a crypto currency address on that card. Each user must have card(`core.models.AddressReserve`) and address(`core.models.Address`) for every crypto currency. i.e. If you are operating the system with BTC, ETH, LTC and RNS user must have 4 cards and 4 addresses. Cards and address are attributed via *allocate_wallets*(`core.signals.allocate_wallets.allocate_wallets`) signal which is called righ after saving new User.

* *Periodic Tasks Description(all tasks initiated on nexchange/settings.py):*
  * `renew_cards_reserve` creates new unassigned(`AddressReserve.user=None`) Cards. Therefore `user.create()` flow is faster because system does not have to send requests to third party sources.
  * `check_cards_uphold_invoke` checks validity of user card on [Uphold](https://uphold.com). If for some reason user has no cards or `AddressReserve.card_id` cannot be found on systems' Uphold account new cards are created for this user(old disabled).
