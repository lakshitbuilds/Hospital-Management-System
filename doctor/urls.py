from django.urls import path
from . import views

urlpatterns = [

    # ===== Dashboard =====
    path('', views.doctor_home, name='doctor_home'),

    # ===== Appointments =====
    path('appointments/today/', views.today_appointments, name='today_appointments'),
    path('appointments/today/<int:appointment_id>/complete/', views.mark_appointment_complete, name='mark_appointment_complete'),
    path('appointments/', views.appointment_list, name='appointment_list'),
    path('appointments/<int:appointment_id>/cancel/', views.doctor_cancel_appointment, name='doctor_cancel_appointment'),

    # ===== Patients =====
    path('patients/<int:patient_id>/', views.patient_details, name='patient_details'),

    # ===== Prescriptions =====
    path('prescriptions/add/', views.add_prescription, name='add_prescription'),
    path('prescriptions/history/', views.prescription_history, name='prescription_history'),

    # ===== Availability =====
    path('availability/', views.availability, name='availability'),

    # ===== Notifications =====
    path('notifications/', views.notifications_view, name='doctor_notifications'),
    path('notifications/mark-all-read/', views.mark_all_read, name='doctor_mark_all_read'),
    path('notifications/<int:notification_id>/dismiss/', views.dismiss_notification, name='doctor_dismiss_notification'),

    # ===== Profile =====
    path('profile/', views.doctor_profile, name='doctor_profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/change-password/', views.change_password, name='change_password'),

]
