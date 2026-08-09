/* ==========================================================================
   ADMIN NOTIFICATIONS PAGE (notifications.html) - PAGE SPECIFIC JS
   Features:
   1. Filter Tabs (All / Unread)
   Note: Mark-all-read and dismiss are real form submits handled server-side.
   ========================================================================== */

document.addEventListener('DOMContentLoaded', function () {

    var filterButtons = document.querySelectorAll('.notif-filter-btn');
    var notificationList = document.getElementById('notificationList');
    var emptyState = document.getElementById('notifEmptyState');
    var currentFilter = 'all';

    function getItems() {
        return notificationList.querySelectorAll('.notification-item');
    }

    function applyFilter() {
        var visibleCount = 0;

        getItems().forEach(function (item) {
            var matches = currentFilter === 'all' || item.getAttribute('data-status') === currentFilter;
            item.classList.toggle('d-none', !matches);
            if (matches) visibleCount++;
        });

        if (emptyState) emptyState.classList.toggle('d-none', visibleCount > 0);
        if (notificationList) notificationList.classList.toggle('d-none', visibleCount === 0);
    }

    filterButtons.forEach(function (button) {
        button.addEventListener('click', function () {
            currentFilter = button.getAttribute('data-filter');
            filterButtons.forEach(function (btn) { btn.classList.remove('active'); });
            button.classList.add('active');
            applyFilter();
        });
    });

});
