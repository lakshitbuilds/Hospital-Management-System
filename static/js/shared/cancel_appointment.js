/* Shared cancellation choices and conditional explanation, across all portals. */
(function () {
    function reasonFields(form) {
        var radios = Array.from(form.querySelectorAll('input[name="cancellation_reason"]'));
        var explanation = form.querySelector('[name="cancellation_explanation"]');
        var other = form.querySelector('[data-cancellation-other]');
        function selected() {
            var checked = radios.find(function (radio) { return radio.checked; });
            return checked ? checked.value : '';
        }
        function sync(clear) {
            var isOther = selected() === 'Other';
            other.hidden = !isOther;
            explanation.required = isOther;
            explanation.disabled = !isOther;
            explanation.setCustomValidity('');
            if (!isOther && clear) explanation.value = '';
        }
        radios.forEach(function (radio) {
            radio.addEventListener('change', function () { sync(true); });
        });
        explanation.addEventListener('input', function () { explanation.setCustomValidity(''); });
        sync(true);
        return { radios: radios, explanation: explanation, selected: selected, sync: sync };
    }
    var controls = new Map();
    document.querySelectorAll('[data-cancellation-form]').forEach(function (form) {
        var fields = reasonFields(form);
        controls.set(form, fields);
        if (form.id !== 'appointmentCancellationForm') {
            form.addEventListener('submit', function (event) {
                if (fields.selected() === 'Other' && !fields.explanation.value.trim()) {
                    event.preventDefault();
                    fields.explanation.setCustomValidity('Please specify the cancellation reason when selecting Other.');
                    fields.explanation.reportValidity();
                }
            });
        }
    });
    var modal = document.getElementById('appointmentCancellationModal');
    if (!modal) return;
    var form = document.getElementById('appointmentCancellationForm');
    var fields = controls.get(form);
    var error = document.getElementById('appointmentCancellationError');
    var confirm = document.getElementById('appointmentCancellationConfirm');
    var activeUrl = '';
    var drafts = new Map();
    document.addEventListener('change', function (event) {
        var select = event.target.closest('[data-cancellation-select]');
        if (!select) return;
        if (select.value === 'cancelled') {
            select.value = select.getAttribute('data-original-status');
            bootstrap.Modal.getOrCreateInstance(modal).show(select);
        } else {
            select.form.requestSubmit();
        }
    });
    function showError(message) {
        error.textContent = message;
        error.hidden = false;
    }
    function saveDraft() {
        drafts.set(activeUrl, { reason: fields.selected(), explanation: fields.explanation.value });
        error.hidden = true;
    }
    form.addEventListener('change', saveDraft);
    form.addEventListener('input', saveDraft);
    fields.radios.forEach(function (radio) {
        radio.addEventListener('invalid', function () { showError('Please select a cancellation reason.'); });
    });
    fields.explanation.addEventListener('invalid', function () { showError('Please specify the cancellation reason when selecting Other.'); });
    modal.addEventListener('show.bs.modal', function (event) {
        var trigger = event.relatedTarget;
        if (!trigger) return;
        activeUrl = trigger.getAttribute('data-cancel-url');
        form.action = activeUrl;
        var draft = drafts.get(activeUrl) || { reason: '', explanation: '' };
        fields.radios.forEach(function (radio) { radio.checked = radio.value === draft.reason; });
        fields.explanation.value = draft.explanation;
        fields.sync(true);
        error.hidden = true;
        document.getElementById('appointmentCancellationDetails').textContent = trigger.getAttribute('data-cancel-details') || '';
    });
    modal.addEventListener('shown.bs.modal', function () {
        var checked = fields.radios.find(function (radio) { return radio.checked; });
        (checked || fields.radios[0]).focus();
    });
    form.addEventListener('submit', async function (event) {
        event.preventDefault();
        if (confirm.disabled) return;
        saveDraft();
        if (!fields.selected()) {
            showError('Please select a cancellation reason.');
            fields.radios[0].focus();
            return;
        }
        if (fields.selected() === 'Other' && !fields.explanation.value.trim()) {
            showError('Please specify the cancellation reason when selecting Other.');
            fields.explanation.focus();
            return;
        }
        if (!activeUrl || !form.reportValidity()) return;
        confirm.disabled = true;
        error.hidden = true;
        try {
            var response = await fetch(activeUrl, { method: 'POST', body: new FormData(form), credentials: 'same-origin', headers: { 'Accept': 'application/json' } });
            var data = await response.json();
            if (!response.ok || !data.success) {
                showError(data.error || 'Cancellation failed. Please try again.');
                return;
            }
            drafts.delete(activeUrl);
            window.location.reload();
        } catch (failure) {
            showError('The request could not be completed. Your selections have been kept. Please try again.');
        } finally {
            confirm.disabled = false;
        }
    });
})();
