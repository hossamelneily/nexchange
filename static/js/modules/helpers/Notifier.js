export default class Notifier {
    static lockoutResponse(data) {
        toastr.error(window.getLockOutText(data));
    }

    static failureResponse(data, defaultMsg) {
        let _defaultMsg = gettext(defaultMsg),
            message = data.responseJSON.message || _defaultMsg;
        toastr.error(message);
    }
}