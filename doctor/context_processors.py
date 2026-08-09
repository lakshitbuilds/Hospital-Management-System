from patient.models import Notification


def notifications(request):
    if request.user.is_authenticated and getattr(request.user, 'role', None) == 'doctor':
        count = Notification.objects.filter(user=request.user, is_read=False).count()
        return {'doctor_unread_count': count}
    return {'doctor_unread_count': 0}
