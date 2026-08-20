/* ==========================================================================
   BOOK APPOINTMENT PAGE (book_appointment.html) - PAGE SPECIFIC JAVASCRIPT
   Features:
   1. Live Booking Summary (Department / Doctor / Date / Time)
   2. Filter Doctor List by Selected Department
   3. Minimum Selectable Date = Today
   4. Form Validation + Success Banner
   5. Load real available time slots from the backend (doctor's weekly
      availability, blocked/holiday dates, and existing bookings)
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
       5. Load real available time slots from the backend
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
        var date = dateInput ? dateInput.value : '';

        if (!slotsUrl || !doctorId || !date) {
            renderSlotMessage('Choose a doctor and date above to see available times.');
            updateSummary();
            return;
        }

        renderSlotMessage('Loading available times…');

        fetch(slotsUrl + '?doctor=' + encodeURIComponent(doctorId) + '&date=' + encodeURIComponent(date))
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
            })
            .finally(function () {
                updateSummary();
            });
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
       4. Form Validation + Success Banner
    ---------------------------------------------------------------------- */
    if (form) {
        form.addEventListener('submit', function (event) {
            event.preventDefault();

            var timeSelected = document.querySelector('.time-slot-input:checked');

            if (!form.checkValidity() || !timeSelected) {
                form.classList.add('was-validated');
                return;
            }

            form.classList.remove('was-validated');
            form.submit();   // <-- actually send the form to Django
        });
    }

    // Initialize summary and time slots on page load
    filterDoctorsByDepartment(document.querySelector('.department-input:checked').value);
    loadTimeSlots();

});
