/* ==========================================================================
   PROFILE PAGE (profile.html) - PAGE SPECIFIC JAVASCRIPT
   Features:
   1. Tab Switching (sidebar nav -> content panels)
   2. Avatar Upload Preview
   3. Change Password Match Validation
   4. Save Success Feedback (per form)
   ========================================================================== */

document.addEventListener('DOMContentLoaded', function () {

    /* ----------------------------------------------------------------------
       1. Tab Switching
       Also activates a tab on load from the URL hash (e.g. "#change-password"),
       so a redirect back from a form on another tab (like changePasswordForm,
       which posts to a separate view) can reopen on the right tab instead of
       silently landing back on Personal Info.
    ---------------------------------------------------------------------- */
    var navLinks = document.querySelectorAll('.profile-nav-link[data-tab]');
    var panels = document.querySelectorAll('.profile-tab-panel');

    function activateTab(targetId) {
        var matchingLink = null;
        navLinks.forEach(function (link) {
            if (link.getAttribute('data-tab') === targetId) matchingLink = link;
        });
        if (!matchingLink) return;

        navLinks.forEach(function (btn) {
            btn.classList.remove('active');
        });
        matchingLink.classList.add('active');

        panels.forEach(function (panel) {
            panel.classList.toggle('active', panel.id === targetId);
        });
    }

    navLinks.forEach(function (link) {
        link.addEventListener('click', function (event) {
            event.preventDefault();
            activateTab(link.getAttribute('data-tab'));
        });
    });

    if (window.location.hash) {
        activateTab(window.location.hash.slice(1));
    }


    /* ----------------------------------------------------------------------
       2. Avatar Upload Preview
    ---------------------------------------------------------------------- */
    var avatarEditBtn = document.getElementById('avatarEditBtn');
    var avatarInput = document.getElementById('avatarInput');
    var avatarPreview = document.getElementById('avatarPreview');

    if (avatarEditBtn && avatarInput) {
        avatarEditBtn.addEventListener('click', function () {
            avatarInput.click();
        });

        avatarInput.addEventListener('change', function () {
            var file = avatarInput.files && avatarInput.files[0];
            if (!file) return;

            var reader = new FileReader();
            reader.onload = function (e) {
                avatarPreview.src = e.target.result;
            };
            reader.readAsDataURL(file);
        });
    }


    /* ----------------------------------------------------------------------
       3. Change Password Match Validation
    ---------------------------------------------------------------------- */
    var newPassword = document.getElementById('newPassword');
    var confirmNewPassword = document.getElementById('confirmNewPassword');

    function validateNewPasswordMatch() {
        if (!newPassword || !confirmNewPassword) return;
        confirmNewPassword.setCustomValidity(
            confirmNewPassword.value !== newPassword.value ? 'mismatch' : ''
        );
    }

    if (newPassword && confirmNewPassword) {
        newPassword.addEventListener('input', validateNewPasswordMatch);
        confirmNewPassword.addEventListener('input', validateNewPasswordMatch);
    }

    var changePasswordForm = document.getElementById('changePasswordForm');
    if (changePasswordForm) {
        changePasswordForm.addEventListener('submit', function (event) {
            validateNewPasswordMatch();

            if (!changePasswordForm.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            changePasswordForm.classList.add('was-validated');
        });
    }


    /* ----------------------------------------------------------------------
       4. Save Success Feedback
       Generic handler: any .profile-form shows its matching .save-success
       message for a few seconds after a valid submit (no backend wired
       yet, so this only simulates the confirmation state).
    ---------------------------------------------------------------------- */
    var forms = document.querySelectorAll('.profile-form');

    forms.forEach(function (form) {
        // A form with a real view behind it (e.g. personalInfoForm) no
        // longer has a `.save-success` element - leave it alone so it
        // submits to the server normally. Only intercept forms that
        // still have one (still backend-less demo forms).
        var successEl = form.querySelector('.save-success');
        if (!successEl) return;

        form.addEventListener('submit', function (event) {
            event.preventDefault();

            if (form.checkValidity && !form.checkValidity()) {
                form.classList.add('was-validated');
                return;
            }

            successEl.classList.remove('d-none');
            setTimeout(function () {
                successEl.classList.add('d-none');
            }, 3000);
        });
    });

});

const form = document.getElementById("personalInfoForm");

if (form) {
    form.addEventListener("submit", function () {
        console.log("FORM SUBMITTED");
    });
}


console.log("profile.js loaded"); 