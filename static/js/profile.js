!(function (window, $) {
    "use strict";

    var get_msg = function (data) {
        var defaultMsg = gettext('The code you sent was incorrect. Please, try again.'),
            message = data.responseJSON.message || window.getLockOutText(data) || defaultMsg;

        return message;
    };

    var requestNewSMSToken = function() {
        var url = $("#resend_sms_button").data('url');

        $("#resend_sms_button").html(
            '<i class="fa fa-spinner fa-spin"></i>&nbsp;Sending you the token again...'
        );

        $.post( url , function( data ) {
            $("#resend_sms_button").html(
                '<i class="fa fa-repeat" aria-hidden="true"></i>&nbsp;Send-me the token again'
            );
            var message = gettext("SMS token sent. Fill in the verification form field and click on 'Verify phone now'.");
            toastr.info(message);
        }).
        fail(function(data){
            $("#resend_sms_button").html(
                '<i class="fa fa-repeat" aria-hidden="true"></i>&nbsp;Send-me the verification token again'
            );

            toastr.error(get_msg(data));
        });
    };


    $("#resend_sms_button").on("click", requestNewSMSToken);

    var verifyPhone = function() {
        var url = $("#verify_phone_now").data('url');
        var token = $("#verification_code").val();
        $("#alert_phone_not_verified").hide();
        $("#alert_verifying_phone").show();
         $.post( url , {'token': token}, function( data ) {
             if (data.status.toUpperCase() === 'OK') {
                 location.reload(); //TODO: Ajax update screen..
             }
         })
         .fail(function (data) {
            $("#alert_verifying_phone").hide();
            $("#alert_phone_not_verified").show();
            toastr.error(get_msg(data));
         });
    };
    $("#verify_phone_now").on("click", verifyPhone);

    function getParameterByName(name, url) {
        if (!url) url = window.location.href;
            name = name.replace(/[\[\]]/g, "\\$&");
        var regex = new RegExp("[?&]" + name + "(=([^&#]*)|&|#|$)"),
            results = regex.exec(url);
        if (!results) return null;
        if (!results[2]) return '';
        return decodeURIComponent(results[2].replace(/\+/g, " "));
}

    window.openProfileTab = function(evt, tabId) {
        // Declare all variables
        var i, tabcontent, tablinks;

        // Get all elements with class="tabcontent" and hide them
        tabcontent = document.getElementsByClassName("tabcontent");
        for (i = 0; i < tabcontent.length; i++) {
            tabcontent[i].style.display = "none";
        }

        // Get all elements with class="tablinks" and remove the class "active"
        tablinks = document.getElementsByClassName("tablinks");
        for (i = 0; i < tablinks.length; i++) {
            tablinks[i].className = tablinks[i].className.replace(" active", "");
        }

        // Show the current tab, and add an "active" class to the button that opened the tab
        document.getElementById(tabId).style.display = "block";
        if (evt === null) {
            $('#' + tabId + "_button").addClass('active');
        } else {
            evt.currentTarget.className += " active";
        }

    };
    $(document).ready(function() {
        var tabName = getParameterByName('tab');
        if (tabName !== null) {
            window.openProfileTab(null, tabName);
        }
    });

    window.verifyPhone = verifyPhone; //hack to allow tests to run
}(window, window.jQuery)); //jshint ignore:line
