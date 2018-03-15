!(function(window ,$) {
  "use strict";
    var isVerified = false;

  var verifyRecatpchaCallback = function(response) {
          //console.log( 'g-recaptcha-response: ' + response );
      var phone = $('.phone.val');
      if (phone.length > 0) {
          if (phone.val().length > 10) {
              $('.create-acc')
                  .not('.resend')
                  .removeClass('disabled');
          }

          isVerified = true;
      }
  };
  
  var getIsVerefied = function () {
      return isVerified;
  };

module.exports = {
    verifyRecatpchaCallback:verifyRecatpchaCallback,
    isVerified: getIsVerefied
};

}(window, window.jQuery)); //jshint ignore:line
