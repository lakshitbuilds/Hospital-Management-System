/* ==========================================================================
   CONTACT PAGE (contact.html) - PAGE SPECIFIC JAVASCRIPT
   Features:
   1. Client-Side Form Validation (Bootstrap-style)
   ========================================================================== */

document.addEventListener('DOMContentLoaded', function () {

    var form = document.getElementById('contactForm');
    var successMessage = document.getElementById('formSuccess');

    if (!form) return;

        form.addEventListener('submit', function (event) {
        event.preventDefault();
        event.stopPropagation();

        if (form.checkValidity()) {
            form.classList.remove('was-validated');
            form.submit();   // <-- actually send to Django
        } else {
            form.classList.add('was-validated');
            if (successMessage) {
                successMessage.classList.add('d-none');
            }
        }
    });

});
