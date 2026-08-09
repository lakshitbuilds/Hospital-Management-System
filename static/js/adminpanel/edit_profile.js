/* ==========================================================================
   EDIT PROFILE PAGE (edit_profile.html) - PAGE SPECIFIC JAVASCRIPT
   Features:
   1. Submit Validation (blocks invalid only)
   ========================================================================== */

document.addEventListener('DOMContentLoaded', function () {

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
