/* ==========================================================================
   DOCTORS PAGE (doctors.html) - PAGE SPECIFIC JAVASCRIPT
   Features:
   1. Filter Doctors by Department
   ========================================================================== */

document.addEventListener('DOMContentLoaded', function () {

    var filterButtons = document.querySelectorAll('.filter-btn');
    var doctorItems = document.querySelectorAll('.doctor-item');
    var noResultsEl = document.querySelector('.no-results');

    filterButtons.forEach(function (button) {
        button.addEventListener('click', function () {
            var filter = button.getAttribute('data-filter');
            var visibleCount = 0;

            // Update active tab state
            filterButtons.forEach(function (btn) {
                btn.classList.remove('active');
            });
            button.classList.add('active');

            // Show/hide doctor cards based on selected department
            doctorItems.forEach(function (item) {
                var matches = filter === 'all' || item.getAttribute('data-category') === filter;
                item.classList.toggle('d-none', !matches);
                if (matches) visibleCount++;
            });

            if (noResultsEl) {
                noResultsEl.classList.toggle('d-none', visibleCount > 0);
            }
        });
    });

});
