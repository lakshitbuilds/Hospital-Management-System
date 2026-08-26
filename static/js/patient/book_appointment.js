/* ==========================================================================
   BOOK APPOINTMENT PAGE (book_appointment.html) - PAGE SPECIFIC JAVASCRIPT
   Features:
   1. Live Booking Summary (Department / Doctor / Date / Time)
   2. Filter Doctor List by Selected Department
   3. Minimum Selectable Date = Today
   4. Form Validation + Success Banner + Submit Loading State
   5. Load real available time slots from the backend (doctor's weekly
      availability, blocked/holiday dates, and existing bookings), kept
      fresh with background polling so a slot taken by another patient
      closes automatically, and one freed up by a cancellation reopens
   ========================================================================== */

document.addEventListener('DOMContentLoaded', function () {

    var departmentInputs = document.querySelectorAll('.department-input');
    var doctorSelect = document.getElementById('doctorSelect');
    var dateInput = document.getElementById('appointmentDate');
    var timeSlotGrid = document.getElementById('timeSlotGrid');
    var form = document.getElementById('bookAppointmentForm');
    var successBanner = document.getElementById('bookingSuccess');

    var summaryDepartment = document.getElementById('summaryDepartment');
    var summaryDoctor = document.getElementById('summaryDoctor');
    var summaryDate = document.getElementById('summaryDate');
    var summaryTime = document.getElementById('summaryTime');


    /* ----------------------------------------------------------------------
       2. Filter Doctor List by Selected Department
       Hides doctors that don't belong to the chosen department and
       auto-selects the first remaining match.
    ---------------------------------------------------------------------- */
    function filterDoctorsByDepartment(department) {
        if (!doctorSelect) return;

        var options = doctorSelect.querySelectorAll('option[data-department]');
        var firstVisible = null;

        options.forEach(function (option) {
            var matches = option.getAttribute('data-department') === department;
            option.hidden = !matches;
            if (matches && !firstVisible) {
                firstVisible = option;
            }
        });

        if (firstVisible) {
            doctorSelect.value = firstVisible.value;
        }

        updateSummary();
    }


    /* ----------------------------------------------------------------------
       1. Live Booking Summary
    ---------------------------------------------------------------------- */
    function formatDate(value) {
        if (!value) return 'Not selected';
        var parts = value.split('-');
        var dateObj = new Date(parts[0], parts[1] - 1, parts[2]);
        return dateObj.toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric' });
    }

    function updateSummary() {
        var checkedDept = document.querySelector('.department-input:checked');
        if (checkedDept && summaryDepartment) {
            summaryDepartment.textContent = checkedDept.getAttribute('data-label');
        }

        if (doctorSelect && summaryDoctor) {
            var selectedOption = doctorSelect.options[doctorSelect.selectedIndex];
            summaryDoctor.textContent = selectedOption ? (selectedOption.getAttribute('data-label') || selectedOption.textContent) : 'Not selected';
        }

        if (dateInput && summaryDate) {
            summaryDate.textContent = formatDate(dateInput.value);
        }

        var checkedSlot = document.querySelector('.time-slot-input:checked');
        if (summaryTime) {
            summaryTime.textContent = checkedSlot ? checkedSlot.value : 'Not selected';
        }
    }

    departmentInputs.forEach(function (input) {
        input.addEventListener('change', function () {
            filterDoctorsByDepartment(input.value);
            loadTimeSlots();
        });
    });

    if (doctorSelect) {
        doctorSelect.addEventListener('change', function () {
            updateSummary();
            loadTimeSlots();
        });
    }

    if (dateInput) {
        dateInput.addEventListener('change', function () {
            updateSummary();
            loadTimeSlots();
        });
    }

    // Time slots are re-rendered on every doctor/date change, so listen via
    // delegation on the grid container rather than binding each input.
    if (timeSlotGrid) {
        timeSlotGrid.addEventListener('change', function (event) {
            if (event.target.classList.contains('time-slot-input')) {
                updateSummary();
            }
        });
    }


    /* ----------------------------------------------------------------------
       5. Load real available time slots from the backend, kept fresh via
          background polling (see startSlotPolling below)
    ---------------------------------------------------------------------- */
    var slotNotice = document.getElementById('slotNotice');
    var slotPollTimer = null;
    var SLOT_POLL_INTERVAL_MS = 8000;

    function renderSlotMessage(text) {
        timeSlotGrid.innerHTML = '';
        var msg = document.createElement('p');
        msg.className = 'time-slot-empty';
        msg.textContent = text;
        timeSlotGrid.appendChild(msg);
    }

    function renderSlotLoader() {
        timeSlotGrid.innerHTML = '';
        var loader = document.createElement('div');
        loader.className = 'slot-loader';
        var spinner = document.createElement('span');
        spinner.className = 'slot-loader-spinner';
        var text = document.createElement('span');
        text.className = 'slot-loader-text';
        text.textContent = 'Loading available times…';
        loader.appendChild(spinner);
        loader.appendChild(text);
        timeSlotGrid.appendChild(loader);
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

    function showSlotNotice(text) {
        if (!slotNotice) return;
        slotNotice.textContent = text;
        slotNotice.classList.remove('d-none');
        clearTimeout(slotNotice._hideTimer);
        slotNotice._hideTimer = setTimeout(function () {
            slotNotice.classList.add('d-none');
        }, 6000);
    }

    // Applied on background polls: syncs each already-rendered slot's
    // booked/free state against fresh server data in place, instead of
    // wiping and rebuilding the grid, so the patient's current selection
    // survives a refresh -- unless that exact slot just got taken by
    // someone else, in which case it's unchecked, disabled ("closed"),
    // and the patient is told. A slot someone else cancelled re-enables
    // ("opens") the same way, with no notice needed since nothing of
    // the patient's own was affected.
    function syncSlotsInPlace(slots) {
        var currentInputs = timeSlotGrid.querySelectorAll('.time-slot-input');
        if (currentInputs.length !== slots.length) {
            // Slot layout itself changed (e.g. doctor's availability was
            // edited) -- safest to just do a full re-render.
            renderSlots(slots);
            return;
        }

        var lostSelection = false;
        for (var index = 0; index < slots.length; index++) {
            var slot = slots[index];
            var input = currentInputs[index];
            if (!input || input.value !== slot.time) {
                // Same layout mismatch as the length check above, just
                // caught mid-loop -- bail out to a full re-render instead
                // of continuing to compare against the wrong slots.
                renderSlots(slots);
                return;
            }
            var label = timeSlotGrid.querySelector('label[for="' + input.id + '"]');
            var wasChecked = input.checked;
            input.disabled = slot.booked;
            if (label) label.classList.toggle('is-booked', slot.booked);
            if (slot.booked && wasChecked) {
                input.checked = false;
                lostSelection = true;
            }
        }

        if (lostSelection) {
            updateSummary();
            showSlotNotice('That time slot was just booked by another patient — please choose a different time.');
        }
    }

    function loadTimeSlots(options) {
        if (!timeSlotGrid) return;
        var background = options && options.background;

        var slotsUrl = timeSlotGrid.getAttribute('data-slots-url');
        var doctorId = doctorSelect ? doctorSelect.value : '';
        var date = dateInput ? dateInput.value : '';

        if (!slotsUrl || !doctorId || !date) {
            stopSlotPolling();
            renderSlotMessage('Choose a doctor and date above to see available times.');
            updateSummary();
            return;
        }

        if (!background) {
            renderSlotLoader();
        }

        fetch(slotsUrl + '?doctor=' + encodeURIComponent(doctorId) + '&date=' + encodeURIComponent(date))
            .then(function (response) { return response.json(); })
            .then(function (data) {
                if (!data.available) {
                    stopSlotPolling();
                    renderSlotMessage(data.reason || 'Doctor is unavailable on this date.');
                    return;
                }
                if (!data.slots || !data.slots.length) {
                    stopSlotPolling();
                    renderSlotMessage('No time slots configured for this doctor on this date.');
                    return;
                }
                if (background) {
                    syncSlotsInPlace(data.slots);
                } else {
                    renderSlots(data.slots);
                    startSlotPolling();
                }
            })
            .catch(function () {
                if (!background) {
                    renderSlotMessage('Could not load time slots. Please try again.');
                }
            })
            .finally(function () {
                updateSummary();
            });
    }

    function startSlotPolling() {
        stopSlotPolling();
        slotPollTimer = setInterval(function () {
            loadTimeSlots({ background: true });
        }, SLOT_POLL_INTERVAL_MS);
    }

    function stopSlotPolling() {
        if (slotPollTimer) {
            clearInterval(slotPollTimer);
            slotPollTimer = null;
        }
    }


    /* ----------------------------------------------------------------------
       3. Minimum Selectable Date = Today
    ---------------------------------------------------------------------- */
    if (dateInput) {
        var today = new Date();
        var yyyy = today.getFullYear();
        var mm = String(today.getMonth() + 1).padStart(2, '0');
        var dd = String(today.getDate()).padStart(2, '0');
        dateInput.setAttribute('min', yyyy + '-' + mm + '-' + dd);
    }


    /* ----------------------------------------------------------------------
       4. Form Validation + Success Banner + Submit Loading State
    ---------------------------------------------------------------------- */
    var submitBtn = form ? form.querySelector('button[type="submit"]') : null;

    if (form) {
        form.addEventListener('submit', function (event) {
            event.preventDefault();

            var timeSelected = document.querySelector('.time-slot-input:checked');

            if (!form.checkValidity() || !timeSelected) {
                form.classList.add('was-validated');
                return;
            }

            form.classList.remove('was-validated');
            stopSlotPolling();
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span class="btn-spinner"></span>Booking&hellip;';
            }
            form.submit();   // <-- actually send the form to Django
        });
    }

    // Initialize summary and time slots on page load
    filterDoctorsByDepartment(document.querySelector('.department-input:checked').value);
    loadTimeSlots();

});
