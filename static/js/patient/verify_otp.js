/* ==========================================================================
   VERIFY OTP PAGE (verify_otp.html) - PAGE SPECIFIC JAVASCRIPT
   Features:
   1. Digit Box Input (auto-advance, backspace, paste, auto-submit)
   2. Expiry Countdown Timer
   3. Resend Cooldown
   ========================================================================== */

document.addEventListener('DOMContentLoaded', function () {

    /* ----------------------------------------------------------------------
       1. Digit Box Input
    ---------------------------------------------------------------------- */
    var boxes = Array.prototype.slice.call(document.querySelectorAll('.otp-box'));
    var hiddenInput = document.getElementById('otpCodeHidden');
    var form = document.getElementById('verifyOtpForm');

    function syncHiddenValue() {
        var code = boxes.map(function (box) { return box.value; }).join('');
        hiddenInput.value = code;
        return code;
    }

    function focusBox(index) {
        if (index >= 0 && index < boxes.length) {
            boxes[index].focus();
            boxes[index].select();
        }
    }

    boxes.forEach(function (box, index) {
        box.addEventListener('input', function () {
            box.value = box.value.replace(/[^0-9]/g, '').slice(0, 1);

            if (box.value) {
                focusBox(index + 1);
            }

            var code = syncHiddenValue();
            if (code.length === boxes.length) {
                form.requestSubmit ? form.requestSubmit() : form.submit();
            }
        });

        box.addEventListener('keydown', function (event) {
            if (event.key === 'Backspace' && !box.value) {
                focusBox(index - 1);
            } else if (event.key === 'ArrowLeft') {
                focusBox(index - 1);
            } else if (event.key === 'ArrowRight') {
                focusBox(index + 1);
            }
        });

        box.addEventListener('paste', function (event) {
            var pasted = (event.clipboardData || window.clipboardData).getData('text').replace(/[^0-9]/g, '');
            if (!pasted) return;
            event.preventDefault();

            for (var i = 0; i < pasted.length && index + i < boxes.length; i++) {
                boxes[index + i].value = pasted[i];
            }

            var code = syncHiddenValue();
            focusBox(Math.min(index + pasted.length, boxes.length - 1));
            if (code.length === boxes.length) {
                form.requestSubmit ? form.requestSubmit() : form.submit();
            }
        });
    });

    if (boxes.length) {
        focusBox(0);
    }


    /* ----------------------------------------------------------------------
       2. Expiry Countdown Timer
    ---------------------------------------------------------------------- */
    var timerRow = document.getElementById('otpTimerRow');
    var timerActive = document.getElementById('otpTimerActive');
    var timerExpired = document.getElementById('otpTimerExpired');
    var timerValue = document.getElementById('otpTimerValue');

    if (timerRow) {
        var secondsRemaining = parseInt(timerRow.getAttribute('data-seconds-remaining'), 10) || 0;

        function renderTimer() {
            if (secondsRemaining <= 0) {
                timerActive.classList.add('d-none');
                timerExpired.classList.remove('d-none');
                return;
            }
            var minutes = Math.floor(secondsRemaining / 60);
            var seconds = secondsRemaining % 60;
            timerValue.textContent = minutes + ':' + (seconds < 10 ? '0' : '') + seconds;
        }

        renderTimer();

        var timerInterval = setInterval(function () {
            secondsRemaining--;
            renderTimer();
            if (secondsRemaining <= 0) {
                clearInterval(timerInterval);
            }
        }, 1000);
    }


    /* ----------------------------------------------------------------------
       3. Resend Cooldown
    ---------------------------------------------------------------------- */
    var resendBtn = document.getElementById('resendOtpBtn');

    if (resendBtn) {
        var cooldownRemaining = parseInt(resendBtn.getAttribute('data-cooldown-seconds'), 10) || 0;
        var originalLabel = resendBtn.textContent;

        function renderCooldown() {
            if (cooldownRemaining <= 0) {
                resendBtn.disabled = false;
                resendBtn.textContent = originalLabel;
                return;
            }
            resendBtn.disabled = true;
            resendBtn.textContent = 'Resend code (' + cooldownRemaining + 's)';
        }

        renderCooldown();

        var cooldownInterval = setInterval(function () {
            cooldownRemaining--;
            renderCooldown();
            if (cooldownRemaining <= 0) {
                clearInterval(cooldownInterval);
            }
        }, 1000);
    }

});
