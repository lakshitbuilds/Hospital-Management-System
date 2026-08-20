from django.urls import path
from . import views

urlpatterns = [

    # ===== Public Pages =====
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('services/', views.services, name='services'),
    path('departments/', views.department, name='department'),
    path('doctors/', views.doctors, name='doctors'),
    path('contact/', views.contact, name='contact'),

    # ===== Auth =====
    path('login/', views.login, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('resend-otp/', views.resend_otp, name='resend_otp'),

    # ===== Patient Profile =====
    path('patient-profile/', views.patient_profile, name='patient_profile'),

    # ===== Appointments =====
    path('book-appointment/', views.book_appointment, name='book_appointment'),
    path('book-appointment/available-slots/', views.get_doctor_slots, name='get_doctor_slots'),
    path('book-appointment/billing/', views.confirm_appointment_billing, name='confirm_appointment_billing'),
    path('book-appointment/billing/cancel/', views.cancel_pending_appointment, name='cancel_pending_appointment'),
    path('my-appointments/', views.my_appointments, name='my_appointments'),
    path('appointments/<int:appointment_id>/cancel/', views.cancel_appointment, name='cancel_appointment'),
    path('my-billing/', views.my_billing, name='my_billing'),

    # ===== Notifications =====
    path('notifications/', views.notifications_view, name='notifications'),
    path('notifications/mark-all-read/', views.mark_all_read, name='mark_all_read'),
    path('notifications/<int:notification_id>/dismiss/', views.dismiss_notification, name='dismiss_notification'),

]