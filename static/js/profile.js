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
        if (!url) {url = window.location.href;}
        name = name.replace(/[\[\]]/g, "\\$&");
        var regex = new RegExp("[?&]" + name + "(=([^&#]*)|&|#|$)"),
            results = regex.exec(url);
        if (!results) {return null;}
        if (!results[2]) {return '';}
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

    $("#new-referral-code").on("click", function() {
        $("#new-referral-code-modal").modal('show');
    });

    $(document).on('submit', '#new-referral-code-form', function (event) {
            event.preventDefault();
            var verifyPayload = $(this).serialize();

            $.ajax({
                type: 'POST',
                url: '/en/referrals/code/new/',
                dataType: 'text',
                data: verifyPayload,
                contentType: 'application/x-www-form-urlencoded; charset=UTF-8',
                success: function success(data) {
                    //if the transaction is Buy
                    var status = JSON.parse(data).status,
                        message = JSON.parse(data).msg;
                    if (status == 'OK') {
                        window.location.href = JSON.parse(data).redirect;
                        toastr.success(message);
                    } else {
                        toastr.error(message);
                    }
                },
                error: function error(jqXHR) {
                    var message = gettext('Something went wrong. Please, try again.');
                    toastr.error(message);
                }
            });
        });

    $(document).on('submit', '#login-anonymous-form', function (event) {
            event.preventDefault();
            var verifyPayload = $(this).serialize();

            $.ajax({
                type: 'POST',
                url: '/en/accounts/login_anonymous/',
                dataType: 'json',
                data: verifyPayload,
                statusCode: {
                    200: function (data) {
                        var message = gettext(data.message);
                        if (data.status === 'OK'){
                            toastr.success(message);
                            window.location.href = data.redirect;
                        } else {
                            toastr.error(message);
                        }
                    }
                }
            });
        });

    window.verifyPhone = verifyPhone; //hack to allow tests to run
}(window, window.jQuery)); //jshint ignore:line
