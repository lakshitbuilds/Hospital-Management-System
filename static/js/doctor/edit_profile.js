/* ==========================================================================
   EDIT PROFILE PAGE (edit_profile.html) - PAGE SPECIFIC JAVASCRIPT
   Features:
   1. Avatar Upload Preview
   2. Submit Validation (blocks invalid only - see profile.js lesson)
   ========================================================================== */

document.addEventListener('DOMContentLoaded', function () {

    /* ----------------------------------------------------------------------
       1. Avatar Upload Preview
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
       2. Submit Validation
       Only blocks the submit when the native form validity check fails.
       A valid submission is left alone and posts to the real Django
       view - no fake success message here (see the profile.js bug from
       the patient-side edit form for why that matters).
    ---------------------------------------------------------------------- */
    var form = document.getElementById('editProfileForm');

    if (form) {
        form.addEventListener('submit', function (event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                form.reportValidity();
            }
        });
    }

});
