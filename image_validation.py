"""
Shared profile-picture upload validation, used by patient/doctor/receptionist
edit-profile views. Needed because this project has no forms.py: an uploaded
file assigned straight to an ImageField and saved via model.save() bypasses
Django's normal ModelForm-driven Pillow content check entirely, so without
this, any file (e.g. a renamed .html file with a <script> tag) is accepted
and stored as-is.
"""
from PIL import Image

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
ALLOWED_PIL_FORMATS = {'JPEG', 'PNG', 'WEBP'}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024


def validate_uploaded_image(uploaded_file):
    """
    Returns an error message string if `uploaded_file` isn't a genuine,
    reasonably-sized image of an allowed type, or None if it's fine to save.
    Must be called before assigning the file to a model field.
    """
    name = uploaded_file.name or ''
    ext = name.rsplit('.', 1)[-1].lower() if '.' in name else ''
    if ext not in ALLOWED_EXTENSIONS:
        return 'Please upload a JPG, PNG, or WEBP image.'

    if uploaded_file.size > MAX_UPLOAD_BYTES:
        return 'Image must be smaller than 5MB.'

    try:
        image = Image.open(uploaded_file)
        image_format = image.format
        image.verify()
    except Exception:
        return 'That file is not a valid image.'
    finally:
        # Image.open()/verify() read through the file; the field's storage
        # backend still needs to read it from the start to actually save it.
        uploaded_file.seek(0)

    if image_format not in ALLOWED_PIL_FORMATS:
        return 'Please upload a JPG, PNG, or WEBP image.'

    return None
