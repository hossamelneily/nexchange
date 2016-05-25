
$(document).ready(function() {
    $('.withdraw_address').editable({
        success: function(response, newValue) {
            if(response.status == 'ERR') {
                return response.msg; //msg will be shown in editable form
            }
        },

        error: function(response, newValue) {
            if(response.status === 500) {
                return HTTP_500_MSG;
            } else {
                return response.responseText;
            }
        },
    });
});

