/* ==========================================================================
   NOTIFICATIONS PAGE (notifications.html) - PAGE SPECIFIC JAVASCRIPT
   Features:
   1. Filter Tabs (All / Unread)
   2. Mark All As Read
   3. Dismiss Individual Notification
   4. Empty State Toggle
   ========================================================================== */

document.addEventListener('DOMContentLoaded', function () {

    var filterButtons = document.querySelectorAll('.notif-filter-btn');
    var markAllReadBtn = document.getElementById('markAllReadBtn');
    var unreadCountBadge = document.getElementById('unreadCountBadge');
    var notificationList = document.getElementById('notificationList');
    var emptyState = document.getElementById('notifEmptyState');
    var currentFilter = 'all';

    function getItems() {
        return notificationList.querySelectorAll('.notification-item');
    }

    function updateUnreadCount() {
        var unreadCount = notificationList.querySelectorAll('.notification-item.is-unread').length;

        if (unreadCountBadge) {
            unreadCountBadge.textContent = unreadCount;
        }

        if (markAllReadBtn) {
            markAllReadBtn.disabled = unreadCount === 0;
        }
    }

    function applyFilter() {
        var visibleCount = 0;

        getItems().forEach(function (item) {
            var matches = currentFilter === 'all' || item.getAttribute('data-status') === currentFilter;
            item.classList.toggle('d-none', !matches);
            if (matches) visibleCount++;
        });

        if (emptyState) {
            emptyState.classList.toggle('d-none', visibleCount > 0);
        }
        if (notificationList) {
            notificationList.classList.toggle('d-none', visibleCount === 0);
        }
    }


    /* ----------------------------------------------------------------------
       1. Filter Tabs
    ---------------------------------------------------------------------- */
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


    /* ----------------------------------------------------------------------
       2. Mark All As Read
    ---------------------------------------------------------------------- */
    if (markAllReadBtn) {
        markAllReadBtn.addEventListener('click', function () {
            getItems().forEach(function (item) {
                item.classList.remove('is-unread');
                item.setAttribute('data-status', 'read');
            });

            updateUnreadCount();
            applyFilter();
        });
    }


    /* ----------------------------------------------------------------------
       3. Dismiss Individual Notification
    ---------------------------------------------------------------------- */
    notificationList.addEventListener('click', function (event) {
        var dismissBtn = event.target.closest('.notif-dismiss');
        if (!dismissBtn) return;

        var item = dismissBtn.closest('.notification-item');
        if (!item) return;

        item.classList.add('is-removing');
        setTimeout(function () {
            item.remove();
            updateUnreadCount();
            applyFilter();
        }, 200);
    });


    // Initialize
    updateUnreadCount();

});
