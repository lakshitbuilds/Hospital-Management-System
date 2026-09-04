"""
Shared list-view pagination helper. Used by every hospital-wide/staff list
view across all four portals (previously none of them paginated at all --
each rendered its entire, ever-growing queryset on every request).

Centralized here rather than repeated in each view because every call site
needs the exact same two things: a Page object built from the request's
`?page=` parameter, and a compact "elided" page-range (e.g. 1 2 3 ... 8 9)
for rendering page-number links without listing every single page once a
list grows into the hundreds of pages.
"""
from django.core.paginator import Paginator

PAGE_SIZE = 20


def paginate(request, queryset, per_page=PAGE_SIZE):
    """
    Paginates `queryset` per the request's `?page=` parameter.

    Returns (page_obj, elided_page_range). `page_obj` is also directly
    iterable in templates (it yields just that page's rows). Invalid page
    numbers (non-numeric, out of range) are clamped to the nearest valid
    page by Paginator.get_page() rather than raising, so a malformed
    `?page=` value can't crash the view.

    `elided_page_range` is a list of page numbers and Paginator.ELLIPSIS
    ("…") markers ready to loop over in a template's pagination controls.
    """
    paginator = Paginator(queryset, per_page)
    page_obj = paginator.get_page(request.GET.get('page'))
    elided_page_range = list(paginator.get_elided_page_range(page_obj.number, on_each_side=1, on_ends=1))
    return page_obj, elided_page_range
