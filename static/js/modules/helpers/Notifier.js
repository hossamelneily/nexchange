export default class Notifier {
    static lockoutResponse(data) {
        toastr.error(window.getLockOutText(data));
    }

    static failureResponse(data, defaultMsg) {
        let message = gettext(defaultMsg);

        if (data != null)
        	message = data.responseJSON.message || defaultMsg;

        toastr.error(message);
    }
}