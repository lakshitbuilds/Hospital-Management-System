/* ==========================================================================
   PRESCRIPTION HISTORY PAGE (prescription_history.html) - PAGE SPECIFIC JS
   Features:
   1. View Prescription Modal (static lookup by rx id)

   Search and sort used to be done here client-side (a substring filter and
   a DOM row re-sort), but both only ever worked over whatever rows were
   already in the DOM -- now that the list is paginated, both are handled
   server-side (see doctor.views.prescription_history) via the search/sort
   form on the page.
   ========================================================================== */

document.addEventListener('DOMContentLoaded', function () {

    /* ----------------------------------------------------------------------
       1. View Prescription Modal
    ---------------------------------------------------------------------- */
    var viewModalEl = document.getElementById('viewRxModal');
    var modalAvatar = document.getElementById('rxModalAvatar');
    var modalPatientName = document.getElementById('rxModalPatientName');
    var modalDate = document.getElementById('rxModalDate');
    var modalDiagnosis = document.getElementById('rxModalDiagnosis');
    var modalMedicineBody = document.getElementById('rxModalMedicineBody');
    var modalAdvice = document.getElementById('rxModalAdvice');
    var modalFollowUpSection = document.getElementById('rxModalFollowUpSection');
    var modalFollowUp = document.getElementById('rxModalFollowUp');

    if (viewModalEl) {
        viewModalEl.addEventListener('show.bs.modal', function (event) {
            var triggerBtn = event.relatedTarget;
            if (!triggerBtn) return;

            var medicines = [];
            try {
                medicines = JSON.parse(triggerBtn.getAttribute('data-medicines') || '[]');
            } catch (e) {
                medicines = [];
            }

            modalAvatar.src = triggerBtn.getAttribute('data-patient-avatar');
            modalPatientName.textContent = triggerBtn.getAttribute('data-patient-name');
            modalDate.textContent = triggerBtn.getAttribute('data-date');
            modalDiagnosis.textContent = triggerBtn.getAttribute('data-diagnosis');
            modalAdvice.textContent = triggerBtn.getAttribute('data-advice') || '-';

            modalMedicineBody.innerHTML = medicines.map(function (med) {
                return '<tr>' +
                    '<td>' + med.name + '</td>' +
                    '<td>' + med.dosage + '</td>' +
                    '<td>' + med.frequency + '</td>' +
                    '<td>' + med.duration + '</td>' +
                    '<td>' + (med.instructions || '-') + '</td>' +
                    '</tr>';
            }).join('');

            var followUp = triggerBtn.getAttribute('data-follow-up');
            if (followUp) {
                modalFollowUp.textContent = followUp;
                modalFollowUpSection.classList.remove('d-none');
            } else {
                modalFollowUpSection.classList.add('d-none');
            }
        });
    }

});
