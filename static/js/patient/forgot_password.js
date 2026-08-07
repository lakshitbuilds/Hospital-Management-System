/* ==========================================================================
   FORGOT PASSWORD PAGE (forgot_password.html) - PAGE SPECIFIC JAVASCRIPT
   Features:
   1. Switch from Request Form to Success State on Submit
   2. Resend Email Button Feedback
   ========================================================================== */

document.addEventListener('DOMContentLoaded', function () {

    var form = document.getElementById('forgotPasswordForm');
    var emailInput = document.getElementById('resetEmail');
    var requestState = document.getElementById('resetRequestState');
    var successState = document.getElementById('resetSuccessState');
    var sentEmailEl = document.getElementById('sentEmailAddress');
    var resendBtn = document.getElementById('resendResetBtn');

    if (form) {
        form.addEventListener('submit', function (event) {
            event.preventDefault();

            if (!form.checkValidity()) {
                form.classList.add('was-validated');
                return;
            }

            if (sentEmailEl && emailInput) {
                sentEmailEl.textContent = emailInput.value;
            }

            requestState.classList.add('d-none');
            successState.classList.remove('d-none');
        });
    }

    if (resendBtn) {
        resendBtn.addEventListener('click', function () {
            var originalHTML = resendBtn.innerHTML;
            resendBtn.disabled = true;
            resendBtn.innerHTML = '<i class="bi bi-check2 me-2"></i>Email Sent Again';

            setTimeout(function () {
                resendBtn.disabled = false;
                resendBtn.innerHTML = originalHTML;
            }, 3000);
        });
    }

});
