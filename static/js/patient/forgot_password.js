/* ==========================================================================
   FORGOT PASSWORD PAGE (forgot_password.html) - PAGE SPECIFIC JAVASCRIPT
   Client-side required-field validation only -- the actual request/resend
   submit and which state (request form vs. "check your email") to show are
   both handled server-side by patient.views.forgot_password.
   ========================================================================== */

document.addEventListener('DOMContentLoaded', function () {

    var form = document.getElementById('forgotPasswordForm');

    if (form) {
        form.addEventListener('submit', function (event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    }

});
