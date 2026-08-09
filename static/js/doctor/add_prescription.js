/* ==========================================================================
   ADD PRESCRIPTION PAGE (add_prescription.html) - PAGE SPECIFIC JAVASCRIPT
   Features:
   1. Add / Remove Medicine Rows
   2. Patient Info Sidebar (static lookup by selected patient)
   ========================================================================== */

document.addEventListener('DOMContentLoaded', function () {

    /* ----------------------------------------------------------------------
       1. Add / Remove Medicine Rows
    ---------------------------------------------------------------------- */
    var medicineRows = document.getElementById('medicineRows');
    var addMedicineBtn = document.getElementById('addMedicineBtn');

    function renumberRows() {
        var rows = medicineRows.querySelectorAll('.medicine-row');
        rows.forEach(function (row, index) {
            row.querySelector('.medicine-row-index').textContent = '#' + (index + 1);
            row.querySelector('.remove-medicine-btn').disabled = rows.length === 1;
        });
    }

    function buildMedicineRow() {
        var template = medicineRows.querySelector('.medicine-row');
        var newRow = template.cloneNode(true);

        newRow.querySelectorAll('input, select, textarea').forEach(function (field) {
            field.value = '';
        });

        return newRow;
    }

    if (addMedicineBtn) {
        addMedicineBtn.addEventListener('click', function () {
            medicineRows.appendChild(buildMedicineRow());
            renumberRows();
        });
    }

    medicineRows.addEventListener('click', function (event) {
        var removeBtn = event.target.closest('.remove-medicine-btn');
        if (!removeBtn || removeBtn.disabled) return;

        var row = removeBtn.closest('.medicine-row');
        if (row) {
            row.remove();
            renumberRows();
        }
    });


    /* ----------------------------------------------------------------------
       2. Patient Info Sidebar
       Reads patient data from the selected <option>'s data-* attributes,
       which are rendered server-side from real Patient records.
    ---------------------------------------------------------------------- */
    var patientSelect = document.getElementById('patientSelect');
    var appointmentSelect = document.getElementById('appointmentSelect');
    var emptyState = document.getElementById('patientInfoEmpty');
    var content = document.getElementById('patientInfoContent');
    var avatarEl = document.getElementById('patientInfoAvatar');
    var nameEl = document.getElementById('patientInfoName');
    var metaEl = document.getElementById('patientInfoMeta');
    var bloodGroupEl = document.getElementById('patientInfoBloodGroup');
    var allergyAlert = document.getElementById('patientAllergyAlert');
    var allergyText = document.getElementById('patientAllergyText');
    var noAllergyNote = document.getElementById('patientNoAllergyNote');

    function showPatientInfo(option) {
        if (!option || !option.value) return;

        emptyState.classList.add('d-none');
        content.classList.remove('d-none');

        avatarEl.src = option.getAttribute('data-avatar');
        nameEl.textContent = option.textContent.trim();
        metaEl.textContent = (option.getAttribute('data-age') || '-') + ' old · ' + (option.getAttribute('data-gender') || '-');
        bloodGroupEl.textContent = option.getAttribute('data-blood-group') || '-';

        var allergies = option.getAttribute('data-allergies');
        if (allergies) {
            allergyText.textContent = allergies;
            allergyAlert.classList.remove('d-none');
            noAllergyNote.classList.add('d-none');
        } else {
            allergyAlert.classList.add('d-none');
            noAllergyNote.classList.remove('d-none');
        }
    }

    if (patientSelect) {
        patientSelect.addEventListener('change', function () {
            showPatientInfo(patientSelect.options[patientSelect.selectedIndex]);
        });

        var preselected = patientSelect.options[patientSelect.selectedIndex];
        if (preselected && preselected.value) {
            showPatientInfo(preselected);
        }
    }

    if (appointmentSelect) {
        appointmentSelect.addEventListener('change', function () {
            var option = appointmentSelect.options[appointmentSelect.selectedIndex];
            var patientId = option ? option.getAttribute('data-patient-id') : null;
            if (patientId && patientSelect) {
                patientSelect.value = patientId;
                showPatientInfo(patientSelect.options[patientSelect.selectedIndex]);
            }
        });
    }

});
