from django.urls import path

from . import views

urlpatterns = [

    # ===== Dashboard =====
    path('', views.receptionist_dashboard, name='receptionist_dashboard'),

    # ===== Patients =====
    path('patients/', views.patient_list, name='receptionist_patient_list'),
    path('patients/register/', views.register_patient, name='receptionist_register_patient'),
    path('patients/<int:patient_id>/', views.patient_detail, name='receptionist_patient_detail'),

    # ===== Appointments =====
    path('appointments/today/', views.today_appointments, name='receptionist_today_appointments'),
    path('appointments/book/', views.book_appointment, name='receptionist_book_appointment'),
    path('appointments/<int:appointment_id>/confirm/', views.confirm_appointment, name='receptionist_confirm_appointment'),
    path('appointments/<int:appointment_id>/cancel/', views.cancel_appointment, name='receptionist_cancel_appointment'),
    path('appointments/', views.appointment_list, name='receptionist_appointment_list'),

    # ===== Doctors =====
    path('doctors/', views.doctor_list, name='receptionist_doctor_list'),

    # ===== Notifications =====
    path('notifications/', views.notifications_view, name='receptionist_notifications'),
    path('notifications/mark-all-read/', views.mark_all_read, name='receptionist_mark_all_read'),
    path('notifications/<int:notification_id>/dismiss/', views.dismiss_notification, name='receptionist_dismiss_notification'),

    # ===== Profile =====
    path('profile/', views.receptionist_profile, name='receptionist_profile'),
    path('profile/edit/', views.edit_profile, name='receptionist_edit_profile'),
    path('profile/change-password/', views.change_password, name='receptionist_change_password'),

]
