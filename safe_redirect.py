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
from django.utils.http import url_has_allowed_host_and_scheme


def safe_next_redirect(request, fallback):
    """
    Redirects to `request.POST.get('next')` if it's a safe, same-site URL;
    otherwise falls back to `redirect(fallback)` (a URL name, as normally
    passed to Django's `redirect()`).
    """
    next_url = request.POST.get('next')
    if next_url and url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return HttpResponseRedirect(next_url)
    return redirect(fallback)
