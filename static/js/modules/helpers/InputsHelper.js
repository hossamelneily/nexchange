export default class InputsHelper {
    static stripSpaces() {
        let val = $(this).val().split(' ').join('');
        $(this).val(val);
    }
}