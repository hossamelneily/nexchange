# flake8: noqa

response = '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">' \
           '<soap:Body>' \
           '<ns2:sendMoneyResponse xmlns:ns2="http://wsm.advcash/">' \
           '<return>{tx_id}</return>' \
           '</ns2:sendMoneyResponse>' \
           '</soap:Body>' \
           '</soap:Envelope>'