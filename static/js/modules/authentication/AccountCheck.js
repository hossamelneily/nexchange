export default class AccountCheck {
    canProceedtoRegister(objectName) {
        let payMeth = $('#payment_method_id').val(),
            userAcc = $('#user_address_id').val(),
            userAccId = $('#new_user_account').val();

        if (!((objectName == 'menu2' || objectName == 'btn-register') &&
                payMeth === '' &&
                userAcc === '' &&
                userAccId === '')) {
            return true;
        }
        return false;
    }
}