/* ==========================================================================
   RECEPTIONIST PORTAL - SHARED LAYOUT JAVASCRIPT
   Features:
   1. Mobile Sidebar Toggle (+ overlay)
   2. Active Sidebar Link by Current Path
   3. Dark / Light Mode Toggle
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


    /* ----------------------------------------------------------------------
       3. Dark / Light Mode Toggle
       Theme itself is applied pre-paint by an inline script in base.html;
       this just wires up the button, syncs the icon, and persists the choice.
    ---------------------------------------------------------------------- */
    var themeToggleBtn = document.getElementById('themeToggleBtn');
    var themeToggleIcon = document.getElementById('themeToggleIcon');

    function syncThemeIcon() {
        var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        if (themeToggleIcon) {
            themeToggleIcon.classList.toggle('bi-moon-stars-fill', !isDark);
            themeToggleIcon.classList.toggle('bi-sun-fill', isDark);
        }
    }

    syncThemeIcon();

    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', function () {
            var next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', next);
            localStorage.setItem('hms-theme', next);
            syncThemeIcon();
        });
    }

});
