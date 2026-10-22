/* Print only selected HTML content through the browser's native preview. */
(function () {
    var root = document.getElementById('documentPrintContent');
    var busy = false;
    if (!root) return;

    function cleanup() {
        document.body.classList.remove('printing-document');
        root.replaceChildren();
        busy = false;
    }
    window.addEventListener('afterprint', cleanup);
    document.addEventListener('click', async function (event) {
        var trigger = event.target.closest('[data-print-document]');
        if (!trigger) return;
        event.preventDefault();
        if (busy) return;
        var selector = trigger.getAttribute('data-print-target');
        var source = selector && document.querySelector(selector);
        if (!source) return;
        busy = true;
        trigger.setAttribute('aria-busy', 'true');
        try {
            var copy = source.cloneNode(true);
            copy.removeAttribute('hidden');
            copy.removeAttribute('id');
            copy.querySelectorAll('[id]').forEach(function (node) { node.removeAttribute('id'); });
            copy.querySelectorAll('button, .btn, form, .back-link, .table-actions, .list-pagination, .report-actions, .filter-chip, [data-print-document], .print-hide').forEach(function (node) { node.remove(); });
            root.replaceChildren(copy);
            // Fonts and images must settle before the browser computes print pages.
            await Promise.all(Array.from(root.querySelectorAll('img')).map(function (img) {
                return img.decode ? img.decode().catch(function () {}) : Promise.resolve();
            }));
            if (document.fonts) await document.fonts.ready;
            document.body.classList.add('printing-document');
            await new Promise(function (resolve) { requestAnimationFrame(function () { requestAnimationFrame(resolve); }); });
            window.print();
        } catch (error) {
            cleanup();
            console.error('Unable to prepare print preview.', error);
        } finally {
            trigger.removeAttribute('aria-busy');
        }
    });
})();
