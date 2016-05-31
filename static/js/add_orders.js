$(function() {
    // TODO: get api root via DI
    var apiRoot = '/en/api/v1',
        createAccEndpoint = apiRoot + '/phone',
        validatePhoneEndpoint = '/profile/verifyPhone/';
    $('.btn-circle').on('click', function () {
        $('.btn-circle.btn-info').removeClass('btn-info').addClass('btn-default');
        $(this).addClass('btn-info').removeClass('btn-default').blur();
    });

    $('.next-step, .prev-step').on('click', changeState);

    $('.create-acc').on('click', function () {
        var payload = {
            phone: $('#phone').val()
        };
        $.ajax({
            type: "POST",
            url: createAccEndpoint,
            data: payload,
            success: function (data) {
                $('.step2').removeClass('hidden');
                $('.verify-acc').removeClass('hidden');
                $(".create-acc").addClass('hidden');
                $("#phone").attr("disabled", "disabled")
            },
            error: function (jqXHR, textStatus, errorThrown) {
                alert('Invalid phone number');
            }
        });
    });

    $('.verify-acc').on('click', function () {
        var payload = {
            'token': $("#verification_code").val(),
            'phone': $("#phone").val()
        };
        $.ajax({
            type: "POST",
            url: validatePhoneEndpoint,
            data: payload,
            success: function (data) {
                if (data.status === 'OK') {
                    changeState('next');
                } else if (data.status === 'NOT_MATCH') {
                    window.alert("The code you sent was incorrect. Please, try again.")
                }
            },
            error: function () {
                window.alert("Something went wrong. Please, try again.")
            }
        });

    });
});
function setButtonDefaultState (tabId) {
    if (tabId == 'menu2') {
        var modifier = action === ACTION_SELL ? 'btn-danger' : 'btn-success';
        $('.next-step').removeClass('btn-info').addClass(modifier);
    } else {
        $('.next-step').removeClass('btn-success').removeClass('btn-danger').addClass('btn-info');
    }
    $('.btn-circle.btn-info')
        .removeClass('btn-info')
        .addClass('btn-default');
}

function changeState (action) {
    var paneClass = '.tab-pane',
        tab = $('.tab-pane.active'),
        action = action || (this).hasClass('next-step') ? 'next' :'prev',
        nextStateId = tab[action](paneClass).attr('id'),
        nextState = $('[href="#'+ nextStateId +'"]');

    setButtonDefaultState(nextStateId);
    nextState
        .addClass('btn-info')
        .removeClass('btn-default')
        .tab('show');
}