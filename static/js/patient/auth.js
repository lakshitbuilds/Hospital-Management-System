/* ==========================================================================
   AUTH PAGES (login.html / register.html) - SHARED JAVASCRIPT
   Features:
   1. Password Visibility Toggle
   2. Login Form Validation
   3. Register Form Validation (incl. password match check)
   ========================================================================== */
document.addEventListener('DOMContentLoaded', function () {

    /* ----------------------------------------------------------------------
       1. Password Visibility Toggle
       Works for any `.password-toggle` button paired with an input via
       its `data-target` attribute (supports multiple fields per page).
    ---------------------------------------------------------------------- */
    var toggleButtons = document.querySelectorAll('.password-toggle');

    toggleButtons.forEach(function (button) {
        button.addEventListener('click', function () {
            var targetId = button.getAttribute('data-target');
            var input = document.getElementById(targetId);
            var icon = button.querySelector('i');

            if (!input) return;

            var isPassword = input.getAttribute('type') === 'password';
            input.setAttribute('type', isPassword ? 'text' : 'password');

            if (icon) {
                icon.classList.toggle('bi-eye', !isPassword);
                icon.classList.toggle('bi-eye-slash', isPassword);
            }

            button.setAttribute('aria-label', isPassword ? 'Hide password' : 'Show password');
        });
    });


    /* ----------------------------------------------------------------------
       2. Login Form Validation
    ---------------------------------------------------------------------- */
    var loginForm = document.getElementById('loginForm');

    if (loginForm) {
        loginForm.addEventListener('submit', function (event) {
            if (!loginForm.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            loginForm.classList.add('was-validated');
        });
    }


    /* ----------------------------------------------------------------------
       3. Register Form Validation
       Adds a custom check so "Confirm Password" must match "Password"
       before the form is allowed to submit.
    ---------------------------------------------------------------------- */
    var registerForm = document.getElementById('registerForm');
    var passwordInput = document.getElementById('registerPassword');
    var confirmInput = document.getElementById('confirmPassword');

    function validatePasswordMatch() {
        if (!passwordInput || !confirmInput) return;

        if (confirmInput.value !== passwordInput.value) {
            confirmInput.setCustomValidity('mismatch');
        } else {
            confirmInput.setCustomValidity('');
        }
    }

    if (registerForm) {
        passwordInput.addEventListener('input', validatePasswordMatch);
        confirmInput.addEventListener('input', validatePasswordMatch);

        registerForm.addEventListener('submit', function (event) {
            validatePasswordMatch();

            if (!registerForm.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            registerForm.classList.add('was-validated');
        });
    }

});
