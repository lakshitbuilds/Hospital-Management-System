// Demo-only card checkout: formats inputs and mirrors them onto the fake
// card preview. Nothing here validates or transmits real card data.
document.addEventListener('DOMContentLoaded', function () {
    const nameInput = document.getElementById('cardName');
    const numberInput = document.getElementById('cardNumber');
    const expiryInput = document.getElementById('cardExpiry');

    const previewName = document.getElementById('previewCardName');
    const previewNumber = document.getElementById('previewCardNumber');
    const previewExpiry = document.getElementById('previewCardExpiry');

    if (nameInput && previewName) {
        nameInput.addEventListener('input', function () {
            previewName.textContent = nameInput.value.trim() ? nameInput.value : 'YOUR NAME';
        });
    }

    if (numberInput && previewNumber) {
        numberInput.addEventListener('input', function () {
            const digits = numberInput.value.replace(/\D/g, '').slice(0, 16);
            const grouped = digits.replace(/(.{4})/g, '$1 ').trim();
            numberInput.value = grouped;

            const padded = digits.padEnd(16, '•');
            previewNumber.textContent = padded.replace(/(.{4})/g, '$1 ').trim();
        });
    }

    if (expiryInput && previewExpiry) {
        expiryInput.addEventListener('input', function () {
            let digits = expiryInput.value.replace(/\D/g, '').slice(0, 4);
            if (digits.length >= 3) {
                digits = digits.slice(0, 2) + '/' + digits.slice(2);
            }
            expiryInput.value = digits;
            previewExpiry.textContent = digits || 'MM/YY';
        });
    }

    const form = document.getElementById('cardPaymentForm');
    const submitBtn = form ? form.querySelector('button[type="submit"]') : null;
    if (form && submitBtn) {
        form.addEventListener('submit', function (event) {
            event.preventDefault();

            if (!form.checkValidity()) {
                form.classList.add('was-validated');
                return;
            }

            form.classList.remove('was-validated');
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="btn-spinner"></span>Processing payment&hellip;';
            form.submit();
        });
    }
});
