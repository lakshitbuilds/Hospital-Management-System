/* ==========================================================================
   BOOK APPOINTMENT PAGE (book_appointment.html) - PAGE SPECIFIC JAVASCRIPT
   Features:
   1. Live Booking Summary Sidebar
   2. Load real available time slots from the backend (doctor's weekly
      availability, blocked/holiday dates, and existing bookings)
   ========================================================================== */

document.addEventListener('DOMContentLoaded', function () {

    var patientSelect = document.getElementById('patientSelect');
    var patientSearchInput = document.getElementById('patientSearchInput');
    var patientSearchResults = document.getElementById('patientSearchResults');
    var doctorSelect = document.getElementById('doctorSelect');
    var dateInput = document.getElementById('appointmentDate');
    var timeSlotGrid = document.getElementById('timeSlotGrid');

    var summaryPatient = document.getElementById('summaryPatient');
    var summaryDoctor = document.getElementById('summaryDoctor');
    var summaryDate = document.getElementById('summaryDate');
    var summaryTime = document.getElementById('summaryTime');

    function selectedText(select) {
        var option = select.options[select.selectedIndex];
        return option && option.value ? option.textContent.trim() : 'Not selected';
    }

    /* ----------------------------------------------------------------------
       Patient search-as-you-type (replaces a plain <select> listing every
       patient in the system, which stopped scaling as the patient count grew)
    ---------------------------------------------------------------------- */
    if (patientSearchInput && patientSelect && patientSearchResults) {
        var searchDebounce = null;

        function pickPatient(id, label) {
            patientSelect.value = id;
            patientSearchInput.value = label;
            if (summaryPatient) summaryPatient.textContent = label;
            patientSearchResults.hidden = true;
            patientSearchResults.innerHTML = '';
        }

        var patientSearchUrl = patientSearchInput.getAttribute('data-search-url');

        function runSearch(query) {
            fetch(patientSearchUrl + '?q=' + encodeURIComponent(query))
                .then(function (resp) { return resp.json(); })
                .then(function (data) {
                    patientSearchResults.innerHTML = '';
                    if (!data.results.length) {
                        patientSearchResults.innerHTML = '<div class="patient-search-empty">No matching patients</div>';
                        patientSearchResults.hidden = false;
                        return;
                    }
                    data.results.forEach(function (p) {
                        var label = p.name + ' · ' + p.patient_id;
                        var item = document.createElement('button');
                        item.type = 'button';
                        item.className = 'patient-search-item';
                        item.textContent = label;
                        item.addEventListener('click', function () {
                            pickPatient(p.id, label);
                        });
                        patientSearchResults.appendChild(item);
                    });
                    patientSearchResults.hidden = false;
                });
        }

        patientSearchInput.addEventListener('input', function () {
            // Typing again invalidates whatever was previously selected,
            // so the form can't silently submit a stale patient id that no
            // longer matches the visible search text.
            patientSelect.value = '';
            var query = patientSearchInput.value.trim();
            clearTimeout(searchDebounce);
            searchDebounce = setTimeout(function () { runSearch(query); }, 200);
        });

        patientSearchInput.addEventListener('focus', function () {
            if (patientSearchInput.value.trim()) {
                runSearch(patientSearchInput.value.trim());
            }
        });

        document.addEventListener('click', function (event) {
            if (event.target !== patientSearchInput && !patientSearchResults.contains(event.target)) {
                patientSearchResults.hidden = true;
            }
        });
    }

    if (doctorSelect && summaryDoctor) {
        doctorSelect.addEventListener('change', function () {
            summaryDoctor.textContent = selectedText(doctorSelect);
            loadTimeSlots();
        });
    }

    if (dateInput && summaryDate) {
        dateInput.addEventListener('change', function () {
            summaryDate.textContent = dateInput.value || 'Not selected';
            loadTimeSlots();
        });
    }

    if (timeSlotGrid && summaryTime) {
        timeSlotGrid.addEventListener('change', function (event) {
            if (event.target.name === 'time_slot') {
                summaryTime.textContent = event.target.value;
            }
        });
    }


    /* ----------------------------------------------------------------------
       2. Load real available time slots from the backend
    ---------------------------------------------------------------------- */
    function renderSlotMessage(text) {
        timeSlotGrid.innerHTML = '';
        var msg = document.createElement('p');
        msg.className = 'time-slot-empty';
        msg.textContent = text;
        timeSlotGrid.appendChild(msg);
    }

    function renderSlots(slots) {
        timeSlotGrid.innerHTML = '';
        slots.forEach(function (slot, index) {
            var id = 'slot_' + index;

            var input = document.createElement('input');
            input.type = 'radio';
            input.name = 'time_slot';
            input.id = id;
            input.value = slot.time;
            input.className = 'time-slot-input';
            if (slot.booked) input.disabled = true;

            var label = document.createElement('label');
            label.setAttribute('for', id);
            label.className = 'time-slot-option' + (slot.booked ? ' is-booked' : '');
            label.textContent = slot.time;

            timeSlotGrid.appendChild(input);
            timeSlotGrid.appendChild(label);
        });
    }

    function loadTimeSlots() {
        if (!timeSlotGrid) return;

        var slotsUrl = timeSlotGrid.getAttribute('data-slots-url');
        var doctorId = doctorSelect ? doctorSelect.value : '';
        var dateValue = dateInput ? dateInput.value : '';

        if (!slotsUrl || !doctorId || !dateValue) {
            renderSlotMessage('Choose a doctor and date above to see available times.');
            return;
        }

        renderSlotMessage('Loading available times…');

        fetch(slotsUrl + '?doctor=' + encodeURIComponent(doctorId) + '&date=' + encodeURIComponent(dateValue))
            .then(function (response) { return response.json(); })
            .then(function (data) {
                if (!data.available) {
                    renderSlotMessage(data.reason || 'Doctor is unavailable on this date.');
                    return;
                }
                if (!data.slots || !data.slots.length) {
                    renderSlotMessage('No time slots configured for this doctor on this date.');
                    return;
                }
                renderSlots(data.slots);
            })
            .catch(function () {
                renderSlotMessage('Could not load time slots. Please try again.');
            });
    }

    // Initialize on page load (in case doctor/date are pre-filled)
    loadTimeSlots();

});
