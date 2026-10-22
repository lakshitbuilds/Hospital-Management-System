/* Password visibility and secure generation for account creation forms. */
document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.password-toggle-btn').forEach(function (button) {
        button.addEventListener('click', function () {
            var input = document.getElementById(button.getAttribute('data-target'));
            if (!input) return;

            var showPassword = input.type === 'password';
            input.type = showPassword ? 'text' : 'password';
            button.setAttribute('aria-label', showPassword ? 'Hide password' : 'Show password');
            button.setAttribute('aria-pressed', String(showPassword));
            var icon = button.querySelector('i');
            icon.classList.toggle('bi-eye', !showPassword);
            icon.classList.toggle('bi-eye-slash', showPassword);
        });
    });

    var form = document.querySelector('form');
    var password = document.getElementById('password');
    var confirmPassword = document.getElementById('confirmPassword');

    if (!form || !password || !confirmPassword) return;

    var generateButton = document.getElementById('generatePassword');
    var generationStatus = document.getElementById('passwordGenerationStatus');

    if (generateButton) {
        generateButton.addEventListener('click', function () {
            if (!window.crypto || !window.crypto.getRandomValues) {
                generationStatus.textContent = 'Password generation is unavailable. Please enter a password manually.';
                return;
            }

            // Rejection sampling avoids bias when selecting random characters.
            function randomIndex(limit) {
                var random = new Uint32Array(1);
                var cutoff = Math.floor(4294967296 / limit) * limit;
                do {
                    window.crypto.getRandomValues(random);
                } while (random[0] >= cutoff);
                return random[0] % limit;
            }

            var groups = ['ABCDEFGHJKLMNPQRSTUVWXYZ', 'abcdefghijkmnopqrstuvwxyz', '23456789', '!@#$%^&*'];
            var alphabet = groups.join('');
            var characters = groups.map(function (group) {
                return group[randomIndex(group.length)];
            });
            while (characters.length < 16) {
                characters.push(alphabet[randomIndex(alphabet.length)]);
            }
            for (var i = characters.length - 1; i > 0; i--) {
                var j = randomIndex(i + 1);
                var character = characters[i];
                characters[i] = characters[j];
                characters[j] = character;
            }

            password.value = characters.join('');
            confirmPassword.value = password.value;
            confirmPassword.setCustomValidity('');
            password.dispatchEvent(new Event('input', { bubbles: true }));
            confirmPassword.dispatchEvent(new Event('input', { bubbles: true }));
            generationStatus.textContent = 'Generated a 16-character password and filled both fields. Use the eye button to view it.';
        });
    }

});
