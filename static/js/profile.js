
var requestNewSMSToken = function() {
    
    $("#resend_sms_button").html(
        '<i class="fa fa-spinner fa-spin"></i>&nbsp;Sending you the token again...'
    );

    $.post( "/profile/resendSMS/", function( data ) {
        $("#resend_sms_button").html(
            '<i class="fa fa-repeat" aria-hidden="true"></i>&nbsp;Send-me the token again'
        );
        window.alert("SMS token sent. Fill in the verification form field and click on 'Verify phone now'.")
    }).fail(function(){
        
        $("#resend_sms_button").html(
            '<i class="fa fa-repeat" aria-hidden="true"></i>&nbsp;Send-me the verification token again'
        );
        window.alert("Something went wrong. Please, try again.")
    });
};


$("#resend_sms_button").on("click", requestNewSMSToken);

var verifyPhone = function() {
    $("#alert_phone_not_verified").hide();
    $("#alert_verifying_phone").show();

     $.post( "/profile/verifyPhone/", {'token': $("#verification_code").val()}, function( data ) {

        if (data.status === 'OK') {
            window.location.reload(); //TODO: Ajax update screen..
        } else if (data.status === 'NOT_MATCH') {
            $("#alert_verifying_phone").hide();
            $("#alert_phone_not_verified").show();
            window.alert("The code you sent was incorrect. Please, try again.")
        }

        
    }).fail(function(){
        $("#alert_verifying_phone").hide();
        $("#alert_phone_not_verified").show();
        window.alert("Something went wrong. Please, try again.")
    });
   
};

$("#verify_phone_now").on("click", verifyPhone);
