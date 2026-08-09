from patient.models import Notification


def notifications(request):
    if request.user.is_authenticated and getattr(request.user, 'role', None) == 'admin':
        qs = Notification.objects.filter(user=request.user)
        return {
            'admin_nav_notifications': qs[:5],
            'admin_unread_count': qs.filter(is_read=False).count(),
        }
    return {'admin_nav_notifications': [], 'admin_unread_count': 0}
