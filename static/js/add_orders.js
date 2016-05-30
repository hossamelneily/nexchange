$(function(){
    // TODO: get api root via DI
     var apiRoot = '/en/api/v1',
         createAccEndpoint = apiRoot + '/phone';
 $('.btn-circle').on('click',function(){
   $('.btn-circle.btn-info').removeClass('btn-info').addClass('btn-default');
   $(this).addClass('btn-info').removeClass('btn-default').blur();
 });

 $('.next-step, .prev-step').on('click', changeState);

    $('.create-acc').on('click', function() {
        var payload = {
            phone: $('#phone').val()
        };
        $.post(createAccEndpoint, payload, function (data) {
            $('.step1').addClass('hidden');
            $('.step2').removeClass('hidden');
        })
    });

    $('.verify-acc').on('click', function () {

    });

    $.post( "/profile/verifyPhone/", {'token': $("#verification_code").val()}, function( data ) {

        if (data.status === 'OK') {
            ; //TODO: Ajax update screen..
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

});

function setButtonDefaultState () {
    $('.btn-circle.btn-info')
        .removeClass('btn-info')
        .addClass('btn-default');
}

function changeState () {
    var paneClass = '.tab-pane',
        tab = $('.tab-pane.active'),
        action = $(this).hasClass('next-step') ? 'next' :'prev',
        nextStateId = tab[action](paneClass).attr('id'),
        nextState = $('[href="#'+ nextStateId +'"]');

    setButtonDefaultState();
    nextState
        .addClass('btn-info')
        .removeClass('btn-default')
        .tab('show');
}