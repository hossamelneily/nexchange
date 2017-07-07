import './css/old.css';
import './css/style.css';
import '../node_modules/select2/dist/css/select2.css';
import '../node_modules/font-awesome/css/font-awesome.css';
import '../node_modules/nprogress/nprogress.css';
import '../node_modules/intl-tel-input/build/css/intlTelInput.css';
import '../node_modules/bootstrap-toggle/css/bootstrap-toggle.min.css';
import '../node_modules/toastr/build/toastr.css';
import '../node_modules/bootstrap-social/bootstrap-social.css';

window.countryCode = document.getElementsByTagName("html")[0].getAttribute("lang");

window.getLockOutText = function(data) {
    if (!data.responseJSON.cooloff_time) {
        return false;
    }
    var refreshTimtout = 5,
        countDownUnit = 1;

    setTimeout(
        function() {
            window.location.reload();
        }, refreshTimtout * 1000
    )

    setInterval(function() {
        var countDown = $("#refresh_count"),
            current = parseInt(countDown.text());
        countDown.text(current - 1)
        countDown.val()
    }, countDownUnit * 1000);

    var formattedTime = data
        .responseJSON
        .cooloff_time
        .replace("PT", "")
        .replace("H", ":")
        .replace("M", "")
        .replace("S", ""),
        errorMsg = gettext('You were locked out, please try again in '),
        refreshMsg = 'Refreshing in <span id="refresh_count">' + 5 + '</span>',
        completeMsg = errorMsg +
        formattedTime + ' ' +
        gettext('minutes') + '<br>' +
        refreshMsg;
    return completeMsg;
};

toastr.options = {
    "closeButton": false,
    "debug": false,
    "newestOnTop": false,
    "progressBar": false,
    "positionClass": "toast-bottom-right",
    "preventDuplicates": false,
    "onclick": null,
    "showDuration": "300",
    "hideDuration": "1000",
    "timeOut": "5000",
    "extendedTimeOut": "1000",
    "showEasing": "swing",
    "hideEasing": "linear",
    "showMethod": "fadeIn",
    "hideMethod": "fadeOut"
};

$(document).ready(function() {
    Cookies.set("USER_TZ", moment.tz.guess());
    var userLang = Cookies.get("django_language");
    if (!userLang) {
        userLang = navigator.language || navigator.userLanguage;
        Cookies.set("django_language", userLang.substring(0, 2).toLowerCase());
    }
});
