export default class MenuReloader {
    static reloadRoleRelatedElements() {
        $.get('/en/api/v1/menu', function(menu) {
            $(".menuContainer").html($(menu));
        });

        $(".process-step .btn")
            .removeClass('btn-info')
            .removeClass('disabled')
            .removeClass('disableClick')
            .addClass('btn-default');

        $(".step2 .btn")
            .addClass('btn-info')
            .addClass('disableClick');
    }
}