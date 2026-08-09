/* ==========================================================================
   ACCOUNT STATUS TOGGLE - SHARED JAVASCRIPT
   Used by doctor_list.html, receptionist_list.html, patient_list.html.
   Wires a confirmation modal to the toggle-status form action.
   ========================================================================== */

document.addEventListener('DOMContentLoaded', function () {

    var modalEl = document.getElementById('statusToggleModal');
    if (!modalEl) return;

    var nameEl = document.getElementById('statusToggleName');
    var actionEl = document.getElementById('statusToggleAction');
    var confirmBtn = document.getElementById('confirmStatusToggleBtn');
    var form = document.getElementById('statusToggleForm');
    var pendingUserId = null;

    modalEl.addEventListener('show.bs.modal', function (event) {
        var triggerBtn = event.relatedTarget;
        if (!triggerBtn) return;

        pendingUserId = triggerBtn.getAttribute('data-user-id');
        var name = triggerBtn.getAttribute('data-user-name');
        var isActive = triggerBtn.getAttribute('data-is-active') === 'true';

        if (nameEl && name) nameEl.textContent = name;
        if (actionEl) actionEl.textContent = isActive ? 'deactivate' : 'activate';
        if (confirmBtn) confirmBtn.className = 'btn btn-lg ' + (isActive ? 'btn-danger' : 'btn-success');
    });

    if (confirmBtn) {
        confirmBtn.addEventListener('click', function () {
            if (pendingUserId && form) {
                form.action = '/adminpanel/users/' + pendingUserId + '/toggle-status/';
                form.submit();
            }
        });
    }

});
