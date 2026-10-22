/* ==========================================================================
   MY APPOINTMENTS PAGE (my_appointments.html) - PAGE SPECIFIC JAVASCRIPT
   Features:
   1. Filter Tabs (All / Upcoming / Completed / Cancelled)
   2. Cancel Confirmation Modal
   3. Empty State Toggle
   ========================================================================== */

document.addEventListener('DOMContentLoaded', function () {

    var filterButtons = document.querySelectorAll('.apt-filter-btn');
    var appointmentList = document.getElementById('appointmentList');
    var emptyState = document.getElementById('aptEmptyState');
    var currentFilter = 'all';

    function getCards() {
        return appointmentList.querySelectorAll('.appointment-card');
    }


    /* ----------------------------------------------------------------------
       1. Filter Tabs
    ---------------------------------------------------------------------- */
    function applyFilter() {
        var visibleCount = 0;

        getCards().forEach(function (card) {
            var matches = currentFilter === 'all' || card.getAttribute('data-status') === currentFilter;
            card.classList.toggle('d-none', !matches);
            if (matches) visibleCount++;
        });

        if (emptyState) {
            emptyState.classList.toggle('d-none', visibleCount > 0);
        }
        if (appointmentList) {
            appointmentList.classList.toggle('d-none', visibleCount === 0);
        }
    }

    filterButtons.forEach(function (button) {
        button.addEventListener('click', function () {
            currentFilter = button.getAttribute('data-filter');

            filterButtons.forEach(function (btn) {
                btn.classList.remove('active');
            });
            button.classList.add('active');

            applyFilter();
        });
    });



});

var viewDetailsModalEl = document.getElementById('viewDetailsModal');
if (viewDetailsModalEl) {
    viewDetailsModalEl.addEventListener('show.bs.modal', function (event) {
        var triggerBtn = event.relatedTarget;
        if (!triggerBtn) return;

        document.getElementById('detailDoctor').textContent = triggerBtn.getAttribute('data-doctor');
        document.getElementById('detailDepartment').textContent = triggerBtn.getAttribute('data-department');
        document.getElementById('detailDate').textContent = triggerBtn.getAttribute('data-date');
        document.getElementById('detailTime').textContent = triggerBtn.getAttribute('data-time');
        document.getElementById('detailVisitType').textContent = triggerBtn.getAttribute('data-visit-type');
        document.getElementById('detailStatus').textContent = triggerBtn.getAttribute('data-status');
        document.getElementById('detailReason').textContent = triggerBtn.getAttribute('data-reason');
    });
}