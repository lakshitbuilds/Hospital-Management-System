/* ==========================================================================
   PRESCRIPTION HISTORY PAGE (prescription_history.html) - PAGE SPECIFIC JS
   Features:
   1. Search by Patient / Diagnosis
   2. Sort by Date (Newest / Oldest)
   3. View Prescription Modal (static lookup by rx id)
   ========================================================================== */

document.addEventListener('DOMContentLoaded', function () {

    /* ----------------------------------------------------------------------
       1. Search by Patient / Diagnosis
    ---------------------------------------------------------------------- */
    var searchInput = document.getElementById('rxSearchInput');
    var sortSelect = document.getElementById('rxSortSelect');
    var tableBody = document.getElementById('rxTableBody');
    var emptyState = document.getElementById('rxEmptyState');

    function applySearch() {
        var term = searchInput.value.trim().toLowerCase();
        var visibleCount = 0;

        tableBody.querySelectorAll('tr').forEach(function (row) {
            var matches = !term || row.getAttribute('data-search').indexOf(term) !== -1;
            row.classList.toggle('d-none', !matches);
            if (matches) visibleCount++;
        });

        if (emptyState) {
            emptyState.classList.toggle('d-none', visibleCount > 0);
        }
        tableBody.closest('.table-responsive').classList.toggle('d-none', visibleCount === 0);
    }

    if (searchInput) {
        searchInput.addEventListener('input', applySearch);
    }


    /* ----------------------------------------------------------------------
       2. Sort by Date (Newest / Oldest)
    ---------------------------------------------------------------------- */
    if (sortSelect) {
        sortSelect.addEventListener('change', function () {
            var rows = Array.from(tableBody.querySelectorAll('tr'));
            var direction = sortSelect.value === 'oldest' ? 1 : -1;

            rows.sort(function (a, b) {
                var aTime = parseInt(a.getAttribute('data-timestamp'), 10);
                var bTime = parseInt(b.getAttribute('data-timestamp'), 10);
                return (aTime - bTime) * direction;
            });

            rows.forEach(function (row) {
                tableBody.appendChild(row);
            });
        });
    }


    /* ----------------------------------------------------------------------
       3. View Prescription Modal
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
