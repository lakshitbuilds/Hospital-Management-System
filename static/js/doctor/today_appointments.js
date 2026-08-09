/* ==========================================================================
   TODAY'S APPOINTMENTS PAGE (today_appointments.html) - PAGE SPECIFIC JS
   Features:
   1. Mark Appointment as Completed
   ========================================================================== */

document.addEventListener('DOMContentLoaded', function () {

    var timeline = document.getElementById('todayTimeline');
    if (!timeline) return;

    timeline.addEventListener('click', function (event) {
        var markBtn = event.target.closest('[data-mark-complete]');
        if (!markBtn) return;

        var slot = markBtn.closest('.timeline-slot');
        if (!slot) return;

        slot.classList.add('is-done');
        slot.setAttribute('data-status', 'completed');

        var badge = slot.querySelector('.status-badge');
        if (badge) {
            badge.className = 'status-badge status-completed';
            badge.textContent = 'Completed';
        }

        markBtn.remove();
    });

});
