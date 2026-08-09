/* ==========================================================================
   AVAILABILITY PAGE (availability.html) - PAGE SPECIFIC JAVASCRIPT
   Features:
   1. Day Toggle Enables/Disables Time Inputs
   2. Copy Monday's Hours to All Weekdays
   3. Add / Remove Blocked Dates
   4. Save Feedback (no backend wired yet)
   ========================================================================== */

document.addEventListener('DOMContentLoaded', function () {

    /* ----------------------------------------------------------------------
       1. Day Toggle Enables/Disables Time Inputs
    ---------------------------------------------------------------------- */
    var dayToggles = document.querySelectorAll('.day-toggle');

    function syncRowState(toggle) {
        var row = toggle.closest('.schedule-row');
        var timeInputs = row.querySelectorAll('.schedule-time input');

        row.classList.toggle('is-unavailable', !toggle.checked);
        timeInputs.forEach(function (input) {
            input.disabled = !toggle.checked;
        });
    }

    dayToggles.forEach(function (toggle) {
        syncRowState(toggle);
        toggle.addEventListener('change', function () {
            syncRowState(toggle);
        });
    });


    /* ----------------------------------------------------------------------
       2. Copy Monday's Hours to All Weekdays
    ---------------------------------------------------------------------- */
    var copyBtn = document.querySelector('.copy-hours-btn');
    var WEEKDAYS = ['tuesday', 'wednesday', 'thursday', 'friday'];

    if (copyBtn) {
        copyBtn.addEventListener('click', function () {
            var mondayRow = document.querySelector('.schedule-row[data-day="monday"]');
            var mondayStart = mondayRow.querySelector('input[name="start_monday"]').value;
            var mondayEnd = mondayRow.querySelector('input[name="end_monday"]').value;
            var mondayAvailable = mondayRow.querySelector('.day-toggle').checked;

            WEEKDAYS.forEach(function (day) {
                var row = document.querySelector('.schedule-row[data-day="' + day + '"]');
                if (!row) return;

                var toggle = row.querySelector('.day-toggle');
                toggle.checked = mondayAvailable;
                row.querySelector('input[name="start_' + day + '"]').value = mondayStart;
                row.querySelector('input[name="end_' + day + '"]').value = mondayEnd;
                syncRowState(toggle);
            });
        });
    }


    /* ----------------------------------------------------------------------
       3. Add / Remove Blocked Dates
    ---------------------------------------------------------------------- */
    var blockedDateInput = document.getElementById('blockedDateInput');
    var blockedReasonInput = document.getElementById('blockedReasonInput');
    var addBlockedDateBtn = document.getElementById('addBlockedDateBtn');
    var blockedDateList = document.getElementById('blockedDateList');
    var blockedDateEmpty = document.getElementById('blockedDateEmpty');

    function formatDisplayDate(isoDate) {
        var parts = isoDate.split('-');
        var dateObj = new Date(parts[0], parts[1] - 1, parts[2]);
        return dateObj.toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric' });
    }

    function refreshBlockedEmptyState() {
        var hasItems = blockedDateList.querySelectorAll('li').length > 0;
        if (blockedDateEmpty) {
            blockedDateEmpty.classList.toggle('d-none', hasItems);
        }
    }

    function addBlockedDate(isoDate, reason) {
        var li = document.createElement('li');
        li.setAttribute('data-date', isoDate);
        li.innerHTML =
            '<div>' +
                '<h6>' + formatDisplayDate(isoDate) + '</h6>' +
                '<p>' + (reason || 'Unavailable') + '</p>' +
            '</div>' +
            '<button type="button" class="remove-blocked-date-btn" aria-label="Remove blocked date">' +
                '<i class="bi bi-trash3"></i>' +
            '</button>' +
            '<input type="hidden" name="blocked_date[]" value="' + isoDate + '">' +
            '<input type="hidden" name="blocked_reason[]" value="' + (reason || '') + '">';

        blockedDateList.appendChild(li);
        refreshBlockedEmptyState();
    }

    if (addBlockedDateBtn) {
        addBlockedDateBtn.addEventListener('click', function () {
            var isoDate = blockedDateInput.value;
            var reason = blockedReasonInput.value.trim();

            if (!isoDate) {
                blockedDateInput.focus();
                return;
            }

            addBlockedDate(isoDate, reason);
            blockedDateInput.value = '';
            blockedReasonInput.value = '';
            blockedDateInput.focus();
        });
    }

    if (blockedDateList) {
        blockedDateList.addEventListener('click', function (event) {
            var removeBtn = event.target.closest('.remove-blocked-date-btn');
            if (!removeBtn) return;

            removeBtn.closest('li').remove();
            refreshBlockedEmptyState();
        });
    }

    refreshBlockedEmptyState();


});
