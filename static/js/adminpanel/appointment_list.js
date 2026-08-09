/* ==========================================================================
   APPOINTMENT LIST PAGE (appointment_list.html) - PAGE SPECIFIC JAVASCRIPT
   Features:
   1. Search by Patient or Doctor Name
   2. Filter by Status
   ========================================================================== */

document.addEventListener('DOMContentLoaded', function () {

    var searchInput = document.getElementById('searchInput');
    var filterButtons = document.querySelectorAll('.apt-filter-btn');
    var table = document.getElementById('appointmentTable');
    var emptyState = document.getElementById('tableEmptyState');
    var currentFilter = 'all';
    var currentSearch = '';

    if (!table) return;
    var tableBody = table.querySelector('tbody');

    function applyFilters() {
        var visibleCount = 0;

        tableBody.querySelectorAll('tr').forEach(function (row) {
            if (!row.hasAttribute('data-status')) return;

            var matchesStatus = currentFilter === 'all' || row.getAttribute('data-status') === currentFilter;
            var haystack = (row.getAttribute('data-patient') || '') + ' ' + (row.getAttribute('data-doctor') || '');
            var matchesSearch = !currentSearch || haystack.indexOf(currentSearch) !== -1;
            var visible = matchesStatus && matchesSearch;

            row.classList.toggle('d-none', !visible);
            if (visible) visibleCount++;
        });

        if (emptyState) emptyState.classList.toggle('d-none', visibleCount > 0);
        table.closest('.table-responsive').classList.toggle('d-none', visibleCount === 0);
    }

    if (searchInput) {
        searchInput.addEventListener('input', function () {
            currentSearch = searchInput.value.trim().toLowerCase();
            applyFilters();
        });
    }

    filterButtons.forEach(function (button) {
        button.addEventListener('click', function () {
            currentFilter = button.getAttribute('data-filter');
            filterButtons.forEach(function (btn) { btn.classList.remove('active'); });
            button.classList.add('active');
            applyFilters();
        });
    });

});
