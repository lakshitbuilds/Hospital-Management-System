"""
Shared helper for safely redirecting to a `next` value read out of a POST
body. Several staff-portal views (adminpanel/doctor/receptionist) accept an
optional `next` field so a form can redirect back to whatever page it was
submitted from, e.g. `redirect(request.POST.get('next') or 'some_fallback')`.
Passed straight to `redirect()`, an attacker-controlled `next` value (e.g.
`next=https://evil.example`) would redirect the user off-site after a
legitimate action on this app -- low risk here since every one of these
call sites is a CSRF-protected POST-only endpoint, but worth closing as
defense-in-depth rather than leaving it open.
"""
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import NoReverseMatch, reverse
from django.utils.http import url_has_allowed_host_and_scheme


def safe_next_redirect(request, fallback):
    """
    Accept a named route or a safe, absolute-path/same-site URL in `next`.
    Invalid names and relative paths fall back to the supplied URL name.
    """
    next_url = request.POST.get('next', '').strip()
    if next_url:
        # Forms may submit a named route rather than a literal URL.
        try:
            next_url = reverse(next_url)
        except NoReverseMatch:
            pass
    if next_url and next_url.startswith(('/', 'http://', 'https://')) and url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return HttpResponseRedirect(next_url)
    return redirect(fallback)
