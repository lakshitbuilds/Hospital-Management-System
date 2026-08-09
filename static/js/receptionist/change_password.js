/* ==========================================================================
   CHANGE PASSWORD PAGE (change_password.html) - PAGE SPECIFIC JAVASCRIPT
   Features:
   1. Show/Hide Password Toggles
   2. Live Requirement Checklist + Strength Meter
   3. Confirm Password Match Check
   4. Submit Validation (blocks invalid, lets valid submits reach the server)
   ========================================================================== */

document.addEventListener('DOMContentLoaded', function () {

    /* ----------------------------------------------------------------------
       1. Show/Hide Password Toggles
    ---------------------------------------------------------------------- */
    document.querySelectorAll('.password-toggle-btn').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var targetInput = document.getElementById(btn.getAttribute('data-target'));
            if (!targetInput) return;

            var icon = btn.querySelector('i');
            var showing = targetInput.type === 'text';

            targetInput.type = showing ? 'password' : 'text';
            icon.classList.toggle('bi-eye', showing);
            icon.classList.toggle('bi-eye-slash', !showing);
        });
    });


    /* ----------------------------------------------------------------------
       2. Live Requirement Checklist + Strength Meter
    ---------------------------------------------------------------------- */
    var newPasswordInput = document.getElementById('newPassword');
    var strengthBar = document.getElementById('strengthBar');
    var strengthLabel = document.getElementById('strengthLabel');
    var requirementItems = document.querySelectorAll('#passwordRequirements li');

    var RULES = {
        length: function (value) { return value.length >= 8; },
        uppercase: function (value) { return /[A-Z]/.test(value); },
        number: function (value) { return /[0-9]/.test(value); },
        special: function (value) { return /[!@#$%^&*]/.test(value); }
    };

    var STRENGTH_LEVELS = [
        { label: 'Enter a new password', color: 'var(--rec-border-color)', width: '0%' },
        { label: 'Weak', color: 'var(--rec-danger)', width: '25%' },
        { label: 'Fair', color: 'var(--rec-warning)', width: '50%' },
        { label: 'Good', color: '#3b82f6', width: '75%' },
        { label: 'Strong', color: 'var(--rec-success)', width: '100%' }
    ];

    function updatePasswordFeedback() {
        var value = newPasswordInput.value;
        var metCount = 0;

        requirementItems.forEach(function (item) {
            var rule = item.getAttribute('data-rule');
            var passed = RULES[rule](value);
            var icon = item.querySelector('i');

            item.classList.toggle('met', passed);
            icon.classList.toggle('bi-circle', !passed);
            icon.classList.toggle('bi-check-circle-fill', passed);

            if (passed) metCount++;
        });

        var level = value.length === 0 ? STRENGTH_LEVELS[0] : STRENGTH_LEVELS[metCount] || STRENGTH_LEVELS[STRENGTH_LEVELS.length - 1];
        strengthBar.style.width = level.width;
        strengthBar.style.backgroundColor = level.color;
        strengthLabel.textContent = level.label;

        return metCount === Object.keys(RULES).length;
    }

    if (newPasswordInput) {
        newPasswordInput.addEventListener('input', updatePasswordFeedback);
    }


    /* ----------------------------------------------------------------------
       3. Confirm Password Match Check
    ---------------------------------------------------------------------- */
    var confirmInput = document.getElementById('confirmNewPassword');
    var confirmError = document.getElementById('confirmPasswordError');

    function passwordsMatch() {
        return newPasswordInput.value.length > 0 && newPasswordInput.value === confirmInput.value;
    }

    function updateConfirmFeedback() {
        var mismatch = confirmInput.value.length > 0 && !passwordsMatch();
        confirmInput.closest('.password-input-group').classList.toggle('has-error', mismatch);
        confirmError.classList.toggle('d-none', !mismatch);
        return !mismatch;
    }

    if (confirmInput) {
        confirmInput.addEventListener('input', updateConfirmFeedback);
        newPasswordInput.addEventListener('input', updateConfirmFeedback);
    }


    /* ----------------------------------------------------------------------
       4. Submit Validation
       Only blocks the submit when something is actually invalid.
    ---------------------------------------------------------------------- */
    var form = document.getElementById('changePasswordForm');
    var currentPasswordInput = document.getElementById('currentPassword');
    var currentPasswordError = document.getElementById('currentPasswordError');

    if (form) {
        form.addEventListener('submit', function (event) {
            var isStrong = updatePasswordFeedback();
            var isMatching = updateConfirmFeedback();
            var hasCurrentPassword = currentPasswordInput.value.trim().length > 0;

            currentPasswordInput.closest('.password-input-group').classList.toggle('has-error', !hasCurrentPassword);
            currentPasswordError.classList.toggle('d-none', hasCurrentPassword);

            if (!hasCurrentPassword || !isStrong || !isMatching) {
                event.preventDefault();
            }
        });
    }

});
