/* Open the browser print preview for a document PDF, never the portal page. */
document.addEventListener('click', function (event) {
    var link = event.target.closest('a[data-print-document]');
    if (!link || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    if (!link.getAttribute('href')) return;

    event.preventDefault();
    if (link.getAttribute('aria-busy') === 'true') return;
    link.setAttribute('aria-busy', 'true');

    var previousFrame = document.getElementById('documentPrintFrame');
    if (previousFrame) previousFrame.remove();

    var frame = document.createElement('iframe');
    frame.id = 'documentPrintFrame';
    frame.title = 'Document print preview';
    // Keep the PDF loaded and rendered without covering the current page.
    frame.style.cssText = 'position:fixed;right:0;bottom:0;width:1px;height:1px;border:0;opacity:0;pointer-events:none;';
    frame.setAttribute('aria-hidden', 'true');
    frame.onload = function () {
        link.removeAttribute('aria-busy');
        try {
            frame.contentWindow.focus();
            frame.contentWindow.print();
        } catch (error) {
            // The PDF viewer remains available if a browser blocks embedded printing.
            window.open(link.href, '_blank', 'noopener');
        }
    };
    frame.onerror = function () {
        link.removeAttribute('aria-busy');
        frame.remove();
        window.open(link.href, '_blank', 'noopener');
    };
    frame.src = link.href;
    document.body.appendChild(frame);
});
