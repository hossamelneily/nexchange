**Phone Login via Login view**


![Phone` Login via Login view](https://github.com/onitsoft/nexchange/blob/feature/tutorial/tutorial/login,register/phone_login_view(login,register)/phone_login.gif?raw=true)

* *Sources:*
  * *py:* `accounts.views.user_get_or_create` sends OTP(One Time Password). `accounts.views.verify_user` checks that password(`accounts.models.SmsToken`)
  * *js:* generic functions on `static/js/modules/register.js`. Button clicks on `static/js/main.js`.
