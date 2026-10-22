"""Keep the project's hand-written forms bound when a submission fails.

No submitted values are stored in sessions or browser storage. Error redirects
are rendered in the same request, using the view's existing GET context.
"""
import logging
from collections import defaultdict
from contextlib import nullcontext
from functools import wraps
from html import escape
from html.parser import HTMLParser

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import DatabaseError, transaction
from django.urls import resolve, reverse

logger = logging.getLogger(__name__)


class BoundHTML(HTMLParser):
    """Bind named controls without rewriting unrelated page HTML or scripts."""
    def __init__(self, data):
        super().__init__(convert_charrefs=False)
        self.data = data
        self.output = []
        self.in_form = False
        self.select = None
        self.textarea = False
        self.indices = defaultdict(int)

    def tag(self, tag, attrs):
        self.output.append('<' + tag + ''.join(
            f' {key}' if value is None else f' {key}="{escape(str(value), quote=True)}"'
            for key, value in attrs.items()) + '>')

    def value(self, name):
        values = self.data.getlist(name)
        index = self.indices[name]
        self.indices[name] += 1
        return values[index] if index < len(values) else ''

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        name = attributes.get('name')
        if tag == 'form':
            self.in_form = attributes.get('method', 'get').lower() == 'post'
        if self.in_form and tag == 'input' and name and name != 'csrfmiddlewaretoken':
            kind = attributes.get('type', 'text').lower()
            if kind in ('checkbox', 'radio'):
                attributes.pop('checked', None)
                if attributes.get('value', 'on') in self.data.getlist(name):
                    attributes['checked'] = None
            elif kind not in ('file', 'submit', 'button', 'reset', 'image') and name in self.data:
                attributes['value'] = self.value(name)
            self.tag(tag, attributes)
        elif self.in_form and tag == 'select' and name:
            self.select = self.data.getlist(name) if 'multiple' in attributes else [self.value(name)]
            self.output.append(self.get_starttag_text())
        elif self.select is not None and tag == 'option':
            attributes.pop('selected', None)
            if attributes.get('value', '') in self.select:
                attributes['selected'] = None
            self.tag(tag, attributes)
        elif self.in_form and tag == 'textarea' and name in self.data:
            self.output.append(self.get_starttag_text())
            self.output.append(escape(self.value(name)))
            self.textarea = True
        elif not self.textarea:
            self.output.append(self.get_starttag_text())

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag == 'textarea':
            self.textarea = False
        if not self.textarea:
            self.output.append(f'</{tag}>')
        if tag == 'select':
            self.select = None
        if tag == 'form':
            self.in_form = False

    def handle_data(self, data):
        if not self.textarea:
            self.output.append(data)

    def handle_entityref(self, name):
        self.handle_data(f'&{name};')

    def handle_charref(self, name):
        self.handle_data(f'&#{name};')

    def handle_comment(self, data):
        self.handle_data(f'<!--{data}-->')

    def handle_decl(self, decl):
        self.handle_data(f'<!{decl}>')


class InvalidSubmission(Exception):
    pass


def preserve_form(view=None, *, error_view=None, atomic=True):
    def decorate(func):
        @wraps(func)
        def wrapped(request, *args, **kwargs):
            request.form_medicine_rows = range(max(1, len(request.POST.getlist('medicine_name[]'))))
            if request.method != 'POST':
                return func(request, *args, **kwargs)
            storage = messages.get_messages(request)
            previous = len(list(storage))
            storage.used = False
            response = None
            try:
                # Roll back all related writes on validation or database failure.
                with transaction.atomic() if atomic else nullcontext():
                    response = func(request, *args, **kwargs)
                    messages_were_used = storage.used
                    current = list(storage)
                    storage.used = messages_were_used
                    if any(note.level >= messages.ERROR for note in current[previous:]):
                        raise InvalidSubmission
            except (InvalidSubmission, DatabaseError, ValidationError) as exc:
                if isinstance(exc, DatabaseError):
                    logger.exception('Unable to save form at %s', request.path)
                    messages.error(request, 'Your changes could not be saved. Please try again. Your entries have been kept.')
                elif isinstance(exc, ValidationError):
                    for message in exc.messages:
                        messages.error(request, message)
                if request.FILES:
                    messages.warning(request, 'Please select your upload again before retrying. Other entries have been kept.')
                if error_view == 'patient_profile':
                    request.form_error_tab = 'change-password'
                # Rerun only the GET branch to rebuild choices/context, never POST.
                if response is None or response.status_code in (301, 302, 303, 307, 308):
                    request.method = 'GET'
                    try:
                        callback = resolve(reverse(error_view)).func if error_view else func
                        response = callback(request, *args, **kwargs)
                    finally:
                        request.method = 'POST'
                if response.status_code == 200 and response.get('Content-Type', '').startswith('text/html'):
                    binder = BoundHTML(request.POST)
                    binder.feed(response.content.decode(response.charset))
                    response.content = ''.join(binder.output).encode(response.charset)
                    response['Cache-Control'] = 'private, no-store'
                return response
            return response
        return wrapped
    return decorate(view) if view else decorate
