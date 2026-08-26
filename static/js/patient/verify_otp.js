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


    /* ----------------------------------------------------------------------
       Verifying / Success / Locked Overlay
       Submits the code via fetch (instead of a plain form submit) so we
       can tell a correct code apart from a wrong one *before* navigating
       anywhere -- only a correct code gets the "Successful!" animation.
       A wrong-but-not-locked-out code never leaves this page on the
       server side either way (Django redirects back to the same
       verify-otp URL), so we just read the fresh attempts-remaining/error
       text out of that response and patch it into the current page
       in place -- no full reload, and no reliance on Django's one-shot
       flash-message cookie surviving a second round-trip. Only a genuine
       navigation away (success, or a lockout bounce to /login/) uses a
       real `window.location.href` -- deliberately not `document.write`,
       which turned out to silently drop the page's own flash message in
       testing (its script/style tags reload with the page mid-write,
       and by then the flash-message cookie has already been consumed by
       this same fetch's redirect-follow, before the write even starts).
    ---------------------------------------------------------------------- */
    var overlay = document.getElementById('otpOverlay');
    var overlaySpinner = document.getElementById('otpSpinner');
    var successIcon = document.getElementById('otpSuccessIcon');
    var lockedIcon = document.getElementById('otpLockedIcon');
    var overlayTitle = document.getElementById('otpOverlayTitle');
    var overlaySubtitle = document.getElementById('otpOverlaySubtitle');
    var inlineError = document.getElementById('otpInlineError');
    var attemptsNote = document.getElementById('otpAttemptsNote');

    function showOverlay() {
        if (overlaySpinner) overlaySpinner.classList.remove('d-none');
        if (successIcon) successIcon.classList.add('d-none');
        if (lockedIcon) lockedIcon.classList.add('d-none');
        if (overlayTitle) overlayTitle.textContent = 'Verifying…';
        if (overlaySubtitle) {
            overlaySubtitle.textContent = '';
            overlaySubtitle.classList.add('d-none');
        }
        if (overlay) overlay.classList.remove('d-none');
    }

    function hideOverlay() {
        if (overlay) overlay.classList.add('d-none');
    }

    function showSuccessState() {
        if (overlaySpinner) overlaySpinner.classList.add('d-none');
        if (successIcon) successIcon.classList.remove('d-none');
        if (overlayTitle) overlayTitle.textContent = 'Successful!';
        if (overlaySubtitle) {
            overlaySubtitle.textContent = "You're verified — taking you in…";
            overlaySubtitle.classList.remove('d-none');
        }
    }

    function showLockedState(message) {
        if (overlaySpinner) overlaySpinner.classList.add('d-none');
        if (lockedIcon) lockedIcon.classList.remove('d-none');
        if (overlayTitle) overlayTitle.textContent = 'Account Locked';
        if (overlaySubtitle) {
            overlaySubtitle.textContent = message || 'Too many incorrect attempts.';
            overlaySubtitle.classList.remove('d-none');
        }
    }

    // Pulls a bit of text out of an HTML string without touching the live
    // document -- used to read the fresh error/attempts-remaining text a
    // wrong-code response rendered, without a full-page reload.
    function extractText(html, selector) {
        var doc = new DOMParser().parseFromString(html, 'text/html');
        var el = doc.querySelector(selector);
        return el ? el.textContent.replace(/\s+/g, ' ').trim() : '';
    }

    function showInlineError(html) {
        hideOverlay();

        var message = extractText(html, '.alert');
        var freshAttemptsNote = extractText(html, '#otpAttemptsNote');

        if (inlineError && message) {
            inlineError.innerHTML = '<i class="bi bi-exclamation-circle-fill"></i>' + message;
            inlineError.classList.remove('d-none');
        }
        if (attemptsNote && freshAttemptsNote) {
            attemptsNote.textContent = freshAttemptsNote;
        }

        // Clear the boxes so the patient can try again.
        boxes.forEach(function (box) { box.value = ''; });
        hiddenInput.value = '';
        focusBox(0);
    }

    function submitOtpForCheck() {
        showOverlay();

        var formData = new FormData(form);
        fetch(form.action, {
            method: 'POST',
            body: formData,
            credentials: 'same-origin',
        })
            .then(function (response) {
                var destinationUrl = response.url;
                var landedOnVerifyPage = new URL(destinationUrl).pathname === window.location.pathname;

                if (landedOnVerifyPage) {
                    return response.text().then(showInlineError);
                }

                var isLockout = /\/login\/?$/.test(new URL(destinationUrl).pathname);
                if (isLockout) {
                    return response.text().then(function (html) {
                        showLockedState(extractText(html, '.alert'));
                        setTimeout(function () {
                            window.location.href = destinationUrl;
                        }, 1600);
                    });
                }

                // Correct code: the server already logged the patient in
                // and redirected to their destination -- just show the
                // moment, then follow it for real.
                showSuccessState();
                setTimeout(function () {
                    window.location.href = destinationUrl;
                }, 1400);
            })
            .catch(function () {
                // Network hiccup: fall back to a plain form submit rather
                // than leaving the user stuck behind the overlay.
                hideOverlay();
                form.submit();
            });
    }

    // Route every submission -- auto-fill, paste-fill, or a manual click
    // on "Verify & Login" -- through the same fetch-based check above.
    if (form) {
        form.addEventListener('submit', function (event) {
            event.preventDefault();
            submitOtpForCheck();
        });
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
                submitOtpForCheck();
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
                submitOtpForCheck();
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
