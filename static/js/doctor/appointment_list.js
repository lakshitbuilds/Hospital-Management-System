/* ==========================================================================
   APPOINTMENT LIST PAGE (appointment_list.html) - PAGE SPECIFIC JAVASCRIPT
   Features:
   1. Cancel Confirmation Modal

   Search and status filtering used to be done here client-side, but that
   only ever worked over whatever rows were already in the DOM -- now that
   the list is paginated, both are handled server-side (see
   doctor.views.appointment_list) via the search form and the
   status-filter links on the page.
   ========================================================================== */

document.addEventListener('DOMContentLoaded', function () {

    /* ----------------------------------------------------------------------
       1. Cancel Confirmation Modal
    ---------------------------------------------------------------------- */
    var cancelModalEl = document.getElementById('cancelAptModal');
    var cancelPatientName = document.getElementById('cancelAptPatientName');
    var confirmCancelBtn = document.getElementById('confirmCancelAptBtn');
    var cancelForm = document.getElementById('cancelAptForm');
    var pendingAppointmentId = null;

    if (cancelModalEl) {
        cancelModalEl.addEventListener('show.bs.modal', function (event) {
            var triggerBtn = event.relatedTarget;
            if (!triggerBtn) return;

            pendingAppointmentId = triggerBtn.getAttribute('data-appointment-id');

            var patientName = triggerBtn.getAttribute('data-patient-name');
            if (cancelPatientName && patientName) {
                cancelPatientName.textContent = patientName;
            }
        });
    }

    if (confirmCancelBtn) {
        confirmCancelBtn.addEventListener('click', function () {
            if (pendingAppointmentId && cancelForm) {
                cancelForm.action = '/doctor/appointments/' + pendingAppointmentId + '/cancel/';
                cancelForm.submit();
            }
        });
    }

});
