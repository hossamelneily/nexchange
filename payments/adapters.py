from payments.utils import check_signature_robo


def unitpay_adapter(request):
    pass


def robokassa_adapter(request):
    output = {
        'sum': request.GET.get("OutSum"),
        'order_id': request.GET.get("InvId"),
        'sig': request.GET.get("SignatureValue")
    }

    output['valid'] = check_signature_robo(
        output['order_id'],
        output['sum'],
        output['sig']
    )

    return output

# FIXME: started for OKPAY IPN - finish or delete
def okpay_adapter(request):
    output = {
        'sum': request.GET.get('ok_item_1_gross'),
        'order_id': [request.GET.get('ok_item_1_name')]
    }
    #request.GET.get('ok_charset')
    #request.GET.get('ok_receiver')
    #request.GET.get('ok_receiver_id')
    #request.GET.get('ok_receiver_wallet')
    #request.GET.get('ok_txn_id')
    #request.GET.get('ok_txn_kind')
    #request.GET.get('ok_txn_payment_type')
    #request.GET.get('ok_txt_payment_method')
    #request.GET.get('ok_txn_gross')
    #request.GET.get('ok_txn_amount')
    #request.GET.get('ok_txn_net')
    #request.GET.get('ok_txn_fee')
    #request.GET.get('ok_txn_currency')
    #request.GET.get('ok_txn_datetime')
    #request.GET.get('ok_txn_status')
    #request.GET.get('ok_invoice')
    #request.GET.get('ok_payer_status')
    #request.GET.get('ok_payer_id')
    #request.GET.get('ok_payer_reputation')
    #request.GET.get('ok_payer_first_name')
    #request.GET.get('ok_payer_last_name')
    #request.GET.get('ok_payer_email')
    #request.GET.get('ok_items_count')
    #request.GET.get('ok_item_1_name')
    #request.GET.get('ok_item_1_type')
    #request.GET.get('ok_item_1_quantity')
    #request.GET.get('ok_item_1_gross')
    #request.GET.get('ok_item_1_price')
    return output


def leupay_adapter(request):
    return {}
