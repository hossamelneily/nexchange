!(function(window ,$) {
  "use strict"; 

  var verifyRecatpchaCallback = function(response) {

          //console.log( 'g-recaptcha-response: ' + response );
            $('.btn-primary.create-acc').removeClass('hidden');

  };

  var doRender = function() {
          grecaptcha.render( 'grecaptcha', {
            'sitekey' : '6LfPaAoUAAAAAOmpl6ZwPIk2Zs-30TErK48dPhcS',  // required
            'theme' : 'light',  // optional
            'callback': verifyRecatpchaCallback  // optional
          });
  };

    module.exports = {
        verifyRecatpchaCallback:verifyRecatpchaCallback,
        doRender: doRender,        
    };

}(window, window.jQuery)); //jshint ignore:line