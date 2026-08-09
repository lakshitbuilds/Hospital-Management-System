/* ==========================================================================
   REGISTER PATIENT PAGE (register_patient.html) - PAGE SPECIFIC JAVASCRIPT
   Features:
   1. Password Match Check
   2. Submit Validation (blocks invalid only)
   ========================================================================== */

document.addEventListener('DOMContentLoaded', function () {

    var form = document.querySelector('form');
    var password = document.getElementById('password');
    var confirmPassword = document.getElementById('confirmPassword');

    if (!form) return;

    form.addEventListener('submit', function (event) {
        var isValid = form.checkValidity();

        if (password.value !== confirmPassword.value) {
            confirmPassword.setCustomValidity('Passwords do not match.');
            isValid = false;
        } else {
            confirmPassword.setCustomValidity('');
        }

        if (!isValid) {
            event.preventDefault();
            form.reportValidity();
        }
    });

    confirmPassword.addEventListener('input', function () {
        confirmPassword.setCustomValidity('');
    });

});
