/* ==========================================================================
   APPOINTMENT LIST PAGE (appointment_list.html) - PAGE SPECIFIC JAVASCRIPT
   Features:
   1. Search by Patient Name
   2. Filter by Status
   3. Cancel Confirmation Modal
   ========================================================================== */

document.addEventListener('DOMContentLoaded', function () {

    var searchInput = document.getElementById('patientSearchInput');
    var filterButtons = document.querySelectorAll('.apt-filter-btn');
    var tableBody = document.getElementById('appointmentTableBody');
    var emptyState = document.getElementById('tableEmptyState');
    var currentFilter = 'all';
    var currentSearch = '';

    function getRows() {
        return tableBody.querySelectorAll('tr');
    }

    function applyFilters() {
        var visibleCount = 0;

        getRows().forEach(function (row) {
            var matchesStatus = currentFilter === 'all' || row.getAttribute('data-status') === currentFilter;
            var matchesSearch = !currentSearch || row.getAttribute('data-patient').indexOf(currentSearch) !== -1;
            var visible = matchesStatus && matchesSearch;

            row.classList.toggle('d-none', !visible);
            if (visible) visibleCount++;
        });

        if (emptyState) {
            emptyState.classList.toggle('d-none', visibleCount > 0);
        }
        tableBody.closest('.table-responsive').classList.toggle('d-none', visibleCount === 0);
    }


    /* ----------------------------------------------------------------------
       1. Search by Patient Name
    ---------------------------------------------------------------------- */
    if (searchInput) {
        searchInput.addEventListener('input', function () {
            currentSearch = searchInput.value.trim().toLowerCase();
            applyFilters();
        });
    }


    /* ----------------------------------------------------------------------
       2. Filter by Status
    ---------------------------------------------------------------------- */
    filterButtons.forEach(function (button) {
        button.addEventListener('click', function () {
            currentFilter = button.getAttribute('data-filter');

            filterButtons.forEach(function (btn) {
                btn.classList.remove('active');
            });
            button.classList.add('active');

            applyFilters();
        });
    });


    /* ----------------------------------------------------------------------
       3. Cancel Confirmation Modal
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
