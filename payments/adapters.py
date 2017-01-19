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


def okpay_adapter(request):
    output = {
        'sum': request.GET.get('ok_item_1_gross'),
        'order_id': [request.GET.get('ok_item_1_name')]
    }
    return output


def leupay_adapter(request):
    return {}
