# Appointment cancellation reasons

Cancellation requires one of six predefined radio choices and explicit confirmation. Other additionally requires a nonblank explanation. Switching away from Other hides and clears the explanation. The shared Bootstrap modal shows patient, doctor, and appointment date/time. It submits with CSRF protection using fetch; validation, HTTP, and network failures keep the modal and its entered reason on the current page. Drafts remain in memory while switching appointments. No reason is stored in browser storage.

Patients can cancel only their own appointments, doctors only their own, and receptionists/admins retain their existing system-wide permissions. Only pending and confirmed appointments can be cancelled. A conditional, authorized database update prevents repeated cancellation; status, reason, and notification are committed atomically. Email is sent after commit. Failed saves leave the appointment unchanged.

The admin status dropdown also asks for a reason before selecting Cancelled. Other status corrections retain their existing behavior. Existing cancelled appointments keep an empty reason; future cancellations require one. Reasons are escaped in appointment history and patient details.

## Database

Appointment.cancellation_reason stores the selected label. Appointment.cancellation_explanation stores the optional Other explanation. Non-Other choices always save an empty explanation. Migration patient.0017_cancellation_reason_options adds the explanation field and declares the six model choices. It was applied successfully to the configured local database. Existing free-text cancellation reasons are preserved; no data is rewritten.

For another environment:

```powershell
venv/Scripts/python.exe manage.py migrate
```

No URL changes or dependencies are required.

## Files added

- patient/cancellation.py — shared authorized validation, atomic save, JSON errors and HTML fallback.
- patient/migrations/0016_appointment_cancellation_reason.py — schema migration.
- patient/test_cancellation.py — cancellation regression tests.
- templates/includes/cancellation_modal.html — shared responsive reason modal.
- templates/includes/cancellation_error.html — non-JavaScript error response preserving the reason.
- static/js/shared/cancel_appointment.js — modal details, required reason, drafts, AJAX failures, and admin dropdown handling.
- project_documentation/Cancellation_Reason_Implementation.md — these implementation/deployment notes.

## Files updated

- patient/models.py — new cancellation reason field.
- patient/views.py, doctor/views.py, receptionist/views.py, adminpanel/views.py — route cancellation requests through the authorized shared workflow.
- templates/patient/base.html, templates/doctor/base.html, templates/receptionist/base.html, templates/adminpanel/base.html — load the shared modal and script.
- templates/patient/my_appointments.html — reason modal trigger and stored reason in history.
- static/js/patient/my_appointments.js — remove obsolete direct cancellation handler; preserve filters and details behavior.
- templates/doctor/appointment_list.html — shared modal trigger, reason in history, remove obsolete cancellation modal/script inclusion.
- templates/receptionist/appointment_list.html — shared modal trigger, reason in history, remove obsolete cancellation modal/script inclusion.
- templates/receptionist/today_appointments.html — replace immediate cancellation POST with confirmation/reason modal.
- templates/adminpanel/appointment_list.html — require reason for Cancelled status and show saved reason.
- templates/doctor/patient_details.html, templates/receptionist/patient_detail.html — show cancellation reason in appointment history.
- receptionist/tests.py — supply a reason in existing successful cancellation scenarios.

## Verification

53 Django tests passed, including empty/whitespace/valid reasons, ownership and roles, completed/no-show/repeated cancellation protection, rollback on notification database failure, HTML fallback escaping, history display, and post-commit email.

JavaScript checks verified no request on opening the modal, whitespace validation, retained reasons and no reload on HTTP/network failures, draft restoration, and refresh only after successful cancellation. Native browser UI was not visually exercised.

```powershell
venv/Scripts/python.exe manage.py test --noinput
venv/Scripts/python.exe manage.py makemigrations --check --dry-run
```


## Radio-choice update: modified files

- patient/models.py: six canonical reason choices and cancellation_explanation field.
- patient/cancellation.py: allowlisted single-choice validation, required Other explanation, ignore stale explanations for other choices, atomic persistence.
- patient/migrations/0017_cancellation_reason_options.py: new explanation column and model choices; already applied locally.
- patient/templatetags/__init__.py and patient/templatetags/cancellation_tags.py: expose the model's canonical choices to all portal templates.
- templates/includes/cancellation_reason_fields.html: reusable radio group and conditional Other textarea.
- templates/includes/cancellation_modal.html and templates/includes/cancellation_error.html: use the shared fields, retaining selections/explanations on errors.
- static/js/shared/cancel_appointment.js: conditional visibility and required state, clear text when leaving Other, restore failed-submission drafts, preserve existing confirmation/AJAX flow.
- templates/patient/base.html, templates/doctor/base.html, templates/receptionist/base.html, templates/adminpanel/base.html: update script version so browsers load the new handler.
- templates/patient/my_appointments.html, templates/doctor/appointment_list.html, templates/doctor/patient_details.html, templates/receptionist/appointment_list.html, templates/receptionist/patient_detail.html, templates/receptionist/today_appointments.html, templates/adminpanel/appointment_list.html: show the selected reason and additional explanation in history/details.
- patient/test_cancellation.py: every option across all four portals, Other validation, unknown/multiple choices, history display, persistence and existing safety tests.
- receptionist/tests.py: use valid predefined reasons in existing workflow tests.
- project_documentation/Cancellation_Reason_Implementation.md: current migration and implementation notes.

The six choices are Patient is unavailable, Doctor is unavailable, Patient requested rescheduling, Appointment booked by mistake, Health issue or emergency, and Other.

Additional JavaScript checks covered all radio options, Other visibility/required/disabled states, clearing explanation on a different selection, whitespace validation, retaining draft values after an error, and success-only cancellation.
