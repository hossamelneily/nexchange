
$(document).ready(function() {

    /**
     * Handles withdrawl address definition
     */
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


    /**
     * Handles the payment confirmation
     */
    $('.checkbox-inline input').change(function() {
        var pk = $(this).data('pk');
        var spin = $("#spin_confirming_" + pk );
        var container = $(this).closest('.checkbox-inline');
        var toggle = this;
        var withdraw_address = $(".withdraw_address[data-pk=" + pk + "]"); // withdraw_address for this orders

        var treatError = function(msg) {
            // Sets the toggle back and notifies the user about the error
            if ( $(toggle).prop('checked') ){
                $(toggle).data('bs.toggle').off(true);
            } else {
                $(toggle).data('bs.toggle').on(true);
            }

            $(spin).hide();
            $(container).show();

            window.alert(msg);
        }

        $.post( $(this).data('url'), {'paid': $(this).prop('checked')}, function( data ) {

            if (data.status === 'OK') {
                
                
                if (data.frozen) {
                    // so user wont change any payment confirmation
                    $(toggle).bootstrapToggle('disable');

                    // so user cannot edit withdraw_address
                    $("#td-withdraw-" + pk).hide(); 
                    $("#td-frozen-withdraw-" + pk).html($(withdraw_address).html()).show();                    
                } 

                $(spin).hide();
                $(container).show();
                
            } else {
                treatError(UNKNOW_ERROR);
            }

            
        }).fail(function(jqXHR){
            if (jqXHR.status == 403) {
                treatError(jqXHR.responseText);
            } else {
                treatError(UNKNOW_ERROR);
            }
        });

        
        
    })

});

