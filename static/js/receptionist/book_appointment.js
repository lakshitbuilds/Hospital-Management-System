/* ==========================================================================
   BOOK APPOINTMENT PAGE (book_appointment.html) - PAGE SPECIFIC JAVASCRIPT
   Features:
   1. Live Booking Summary Sidebar
   ========================================================================== */

document.addEventListener('DOMContentLoaded', function () {

    var patientSelect = document.getElementById('patientSelect');
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

    if (patientSelect && summaryPatient) {
        patientSelect.addEventListener('change', function () {
            summaryPatient.textContent = selectedText(patientSelect);
        });
    }

    if (doctorSelect && summaryDoctor) {
        doctorSelect.addEventListener('change', function () {
            summaryDoctor.textContent = selectedText(doctorSelect);
        });
    }

    if (dateInput && summaryDate) {
        dateInput.addEventListener('change', function () {
            summaryDate.textContent = dateInput.value || 'Not selected';
        });
    }

    if (timeSlotGrid && summaryTime) {
        timeSlotGrid.addEventListener('change', function (event) {
            if (event.target.name === 'time_slot') {
                summaryTime.textContent = event.target.value;
            }
        });
    }

});
