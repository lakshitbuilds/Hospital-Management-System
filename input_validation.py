"""
Shared, lightweight format checks for a couple of free-text fields that
several account-creation views split/store as-is with no validation beyond
"is it present" -- e.g. a full name containing digits or HTML markup was
previously accepted everywhere (harmless from a security standpoint, since
template auto-escaping neutralizes it on display, but still bad data
hygiene). Not a full validation framework -- just the one check that's
actually worth having at account-creation time, kept as a plain module
(matching image_validation.py / pagination.py / safe_redirect.py) since
this project has no shared/common app any of the four portals import from.
"""
import re

# Letters (incl. accented), spaces, hyphens, and apostrophes -- covers
# real-world names ("Mary-Jane O'Brien") without being overly strict about
# what counts as a valid name.
_NAME_RE = re.compile(r"^[A-Za-zÀ-ſ' -]+$")


def is_valid_name(value):
    """True if `value` looks like a real person's name, not e.g. digits or markup."""
    return bool(value) and bool(_NAME_RE.match(value.strip()))
