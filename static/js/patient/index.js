/* ==========================================================================
   HOME PAGE (index.html) - PAGE SPECIFIC JAVASCRIPT
   Features:
   1. Animated Stat Counters (triggered on scroll into view)
   2. Testimonial Carousel Pause-on-Hover
   ========================================================================== */

document.addEventListener('DOMContentLoaded', function () {

    /* ----------------------------------------------------------------------
       1. Animated Stat Counters
       Counts each `.counter` element up from 0 to its `data-target` value
       once the stats section scrolls into the viewport. Uses
       IntersectionObserver so the animation only fires once, when visible.
    ---------------------------------------------------------------------- */
    var counters = document.querySelectorAll('.counter');
    var COUNT_DURATION = 1500; // ms

    function animateCounter(el) {
        var target = parseInt(el.getAttribute('data-target'), 10) || 0;
        var startTime = null;

        function step(timestamp) {
            if (!startTime) startTime = timestamp;
            var progress = Math.min((timestamp - startTime) / COUNT_DURATION, 1);
            var value = Math.floor(progress * target);
            el.textContent = value.toLocaleString();

            if (progress < 1) {
                requestAnimationFrame(step);
            } else {
                el.textContent = target.toLocaleString();
            }
        }

        requestAnimationFrame(step);
    }

    if (counters.length && 'IntersectionObserver' in window) {
        var counterObserver = new IntersectionObserver(function (entries, observer) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    animateCounter(entry.target);
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.5 });

        counters.forEach(function (counter) {
            counterObserver.observe(counter);
        });
    } else {
        // Fallback for browsers without IntersectionObserver support
        counters.forEach(animateCounter);
    }


    /* ----------------------------------------------------------------------
       2. Testimonial Carousel Pause-on-Hover
       Bootstrap's carousel auto-cycles via data-bs-ride; this pauses it
       while a visitor is reading/hovering and resumes on mouse leave.
    ---------------------------------------------------------------------- */
    var testimonialCarouselEl = document.getElementById('testimonialCarousel');

    if (testimonialCarouselEl && window.bootstrap) {
        var carouselInstance = bootstrap.Carousel.getOrCreateInstance(testimonialCarouselEl, {
            interval: 5000,
            pause: false
        });

        testimonialCarouselEl.addEventListener('mouseenter', function () {
            carouselInstance.pause();
        });

        testimonialCarouselEl.addEventListener('mouseleave', function () {
            carouselInstance.cycle();
        });
    }

});
