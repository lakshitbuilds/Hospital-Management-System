/* ==========================================================================
   DOCTOR PROFILE PAGE (profile.html) - PAGE SPECIFIC JAVASCRIPT
   Features:
   1. Click-to-Copy Contact Fields
   ========================================================================== */

document.addEventListener('DOMContentLoaded', function () {

    document.querySelectorAll('.copyable').forEach(function (item) {
        item.addEventListener('click', function () {
            var value = item.getAttribute('data-copy-value');
            if (!value || !navigator.clipboard) return;

            navigator.clipboard.writeText(value).then(function () {
                item.classList.add('is-copied');
                setTimeout(function () {
                    item.classList.remove('is-copied');
                }, 1500);
            });
        });
    });

});
