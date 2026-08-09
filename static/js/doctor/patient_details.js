/* ==========================================================================
   PATIENT DETAILS PAGE (patient_details.html) - PAGE SPECIFIC JAVASCRIPT
   Features:
   1. Print Patient Summary
   ========================================================================== */

document.addEventListener('DOMContentLoaded', function () {

    var printBtn = document.getElementById('printPatientBtn');

    if (printBtn) {
        printBtn.addEventListener('click', function () {
            window.print();
        });
    }

});
