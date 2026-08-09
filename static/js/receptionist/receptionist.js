/* ==========================================================================
   RECEPTIONIST PORTAL - SHARED LAYOUT JAVASCRIPT
   Features:
   1. Mobile Sidebar Toggle (+ overlay)
   2. Active Sidebar Link by Current Path
   ========================================================================== */

document.addEventListener('DOMContentLoaded', function () {

    /* ----------------------------------------------------------------------
       1. Mobile Sidebar Toggle
    ---------------------------------------------------------------------- */
    var sidebar = document.getElementById('receptionistSidebar');
    var toggleBtn = document.getElementById('sidebarToggleBtn');
    var overlay = document.getElementById('sidebarOverlay');

    function openSidebar() {
        sidebar.classList.add('show');
        overlay.classList.add('show');
    }

    function closeSidebar() {
        sidebar.classList.remove('show');
        overlay.classList.remove('show');
    }

    if (toggleBtn) {
        toggleBtn.addEventListener('click', function () {
            sidebar.classList.contains('show') ? closeSidebar() : openSidebar();
        });
    }

    if (overlay) {
        overlay.addEventListener('click', closeSidebar);
    }


    /* ----------------------------------------------------------------------
       2. Active Sidebar Link by Current Path
    ---------------------------------------------------------------------- */
    var sidebarLinks = document.querySelectorAll('.sidebar-link');
    var currentPath = window.location.pathname.replace(/\/$/, '') || '/';

    sidebarLinks.forEach(function (link) {
        var linkPath = link.pathname.replace(/\/$/, '') || '/';
        link.classList.toggle('active', linkPath === currentPath && linkPath !== '/');
    });

});
