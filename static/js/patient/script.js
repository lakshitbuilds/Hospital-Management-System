/* ==========================================================================
   MEDICARE HOSPITAL - MAIN JAVASCRIPT
   Features:
   1. Sticky Navbar Shadow on Scroll
   2. Back To Top Button
   3. Active Navigation Highlight
   4. Smooth Scroll for In-Page Anchor Links
   5. Auto-Close Mobile Menu on Link Click
   ========================================================================== */

document.addEventListener('DOMContentLoaded', function () {

    /* ----------------------------------------------------------------------
       1. Sticky Navbar Shadow on Scroll
       Adds a `.scrolled` class once the page scrolls past a threshold so
       the navbar gains a shadow/tighter padding (handled in style.css).
    ---------------------------------------------------------------------- */
    var navbar = document.getElementById('mainNavbar');
    var SCROLL_THRESHOLD = 40;

    function handleNavbarScroll() {
        if (!navbar) return;
        if (window.scrollY > SCROLL_THRESHOLD) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }
    }

    handleNavbarScroll();
    window.addEventListener('scroll', handleNavbarScroll);


    /* ----------------------------------------------------------------------
       2. Back To Top Button
       Shows the button after scrolling down and smooth-scrolls to top
       when clicked.
    ---------------------------------------------------------------------- */
    var backToTopBtn = document.getElementById('backToTop');
    var BACK_TO_TOP_THRESHOLD = 300;

    function handleBackToTopVisibility() {
        if (!backToTopBtn) return;
        if (window.scrollY > BACK_TO_TOP_THRESHOLD) {
            backToTopBtn.classList.add('show');
        } else {
            backToTopBtn.classList.remove('show');
        }
    }

    handleBackToTopVisibility();
    window.addEventListener('scroll', handleBackToTopVisibility);

    if (backToTopBtn) {
        backToTopBtn.addEventListener('click', function () {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }


    /* ----------------------------------------------------------------------
       3. Active Navigation Highlight
       Compares each nav link's pathname against the current page path
       and marks the matching link as `.active`.
    ---------------------------------------------------------------------- */
    var navLinks = document.querySelectorAll('.nav-center .nav-link');
    var currentPath = window.location.pathname.replace(/\/$/, '') || '/';

    navLinks.forEach(function (link) {
        var linkPath = link.pathname.replace(/\/$/, '') || '/';
        if (linkPath === currentPath) {
            link.classList.add('active');
            link.setAttribute('aria-current', 'page');
        } else {
            link.classList.remove('active');
        }
    });


    /* ----------------------------------------------------------------------
       4. Smooth Scroll for In-Page Anchor Links
       Any link pointing to a `#section-id` on the same page scrolls
       smoothly instead of jumping (native CSS smooth-scroll handles most
       cases, this adds an offset for the sticky navbar).
    ---------------------------------------------------------------------- */
    var anchorLinks = document.querySelectorAll('a[href^="#"]:not([href="#"])');

    anchorLinks.forEach(function (anchor) {
        anchor.addEventListener('click', function (e) {
            var targetId = this.getAttribute('href');
            var targetEl = document.querySelector(targetId);

            if (targetEl) {
                e.preventDefault();
                var navbarHeight = navbar ? navbar.offsetHeight : 0;
                var targetPosition = targetEl.getBoundingClientRect().top + window.pageYOffset - navbarHeight - 16;

                window.scrollTo({
                    top: targetPosition,
                    behavior: 'smooth'
                });
            }
        });
    });


    /* ----------------------------------------------------------------------
       5. Auto-Close Mobile Menu on Link Click
       Collapses the Bootstrap navbar automatically after a nav link is
       tapped on mobile, so users don't have to manually close it.
    ---------------------------------------------------------------------- */
    var navbarCollapse = document.getElementById('navbarMain');
    var mobileNavLinks = document.querySelectorAll('#navbarMain .nav-link, #navbarMain .dropdown-item');

    if (navbarCollapse) {
        mobileNavLinks.forEach(function (link) {
            link.addEventListener('click', function () {
                if (window.innerWidth < 992 && navbarCollapse.classList.contains('show')) {
                    var bsCollapse = bootstrap.Collapse.getOrCreateInstance(navbarCollapse);
                    bsCollapse.hide();
                }
            });
        });
    }


    /* ----------------------------------------------------------------------
       Footer: Current Year
    ---------------------------------------------------------------------- */
    var yearEl = document.getElementById('currentYear');
    if (yearEl) {
        yearEl.textContent = new Date().getFullYear();
    }

});
