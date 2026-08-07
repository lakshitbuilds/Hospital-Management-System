from .models import Notification

def notifications(request):
    if request.user.is_authenticated:
        qs = Notification.objects.filter(user=request.user)
        return {
            'nav_notifications': qs[:5],
            'unread_notifications_count': qs.filter(is_read=False).count(),
        }
    return {'nav_notifications': [], 'unread_notifications_count': 0}