from patient.models import Notification


def notifications(request):
    if request.user.is_authenticated and getattr(request.user, 'role', None) == 'receptionist':
        qs = Notification.objects.filter(user=request.user)
        return {
            'receptionist_nav_notifications': qs[:5],
            'receptionist_unread_count': qs.filter(is_read=False).count(),
        }
    return {'receptionist_nav_notifications': [], 'receptionist_unread_count': 0}
