$(document).ready(function() {

    function withdraw_address_error(msg) {
        $(".withdraw_address_err:visible").html(msg);
    }


    $('[data-toggle="popover"]').on('inserted.bs.popover', function () {

        var span = $(this);
        var popover = $(this).data("bs.popover");

        // Links that closes the popover
        $(".closepopover").click(function(event){
            span.trigger("click");
        });

        // Buttons to toggle between select/add address
        $(".toggle_widthdraw_address_form").click(function(){
            $(".set_withdraw_address").toggle();
            $(".insert_withdraw_address").toggle();
        });

        // if there is one address set, select it
        var select = $(".set_withdraw_address:visible:first select:visible:first");
        select.children("option").each(function(index, option){            
            if ( $.trim($(option).text()) === $.trim(span.html()) ) {
                select.prop('selectedIndex', index);
            }
        })
        
        /**
         * The form the handles 'select one of the existing addresses'
         */
        $(".set_withdraw_address:visible:first form:visible:first").submit(function(event) {            
            event.preventDefault();

            withdraw_address_error(''); // clean up

            var form = event.target;
            var selected = $(form).find("select:first option:selected").eq(0);
            
            if (selected.val() === "") {
                withdraw_address_error("You must select an address first.");
                return false;
            }

            var btn = $(form).find("button[type=submit]:first");
            btn.button('loading');

            var treatError = function(msg) {
                withdraw_address_error(msg);
            };

            $.post( span.data('url-update'), {'value': selected.val()}, function( data ) {
                if (data.status === 'OK') {                    
                    span.html(selected.text());
                    span.trigger("click");
                } else {
                    treatError(UNKNOW_ERROR);
                }

                btn.button('reset');
            }).fail(function(jqXHR){
                if (jqXHR.status == 403) {
                    treatError(jqXHR.responseText);
                } else {
                    treatError(UNKNOW_ERROR);
                }
                btn.button('reset');
            });

            
        });
    })

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
        };

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
        
    });

});

