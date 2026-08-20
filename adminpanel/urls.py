from django.urls import path

from . import views

urlpatterns = [

    # ===== Dashboard =====
    path('', views.admin_dashboard, name='admin_dashboard'),

    # ===== Doctors =====
    path('doctors/', views.doctor_list, name='admin_doctor_list'),
    path('doctors/add/', views.add_doctor, name='admin_add_doctor'),
    path('doctors/<int:doctor_id>/', views.doctor_detail, name='admin_doctor_detail'),

    # ===== Receptionists =====
    path('receptionists/', views.receptionist_list, name='admin_receptionist_list'),
    path('receptionists/add/', views.add_receptionist, name='admin_add_receptionist'),
    path('receptionists/<int:receptionist_id>/update-shift/', views.update_receptionist_shift, name='admin_update_receptionist_shift'),

    # ===== Patients =====
    path('patients/', views.patient_list, name='admin_patient_list'),
    path('patients/<int:patient_id>/', views.patient_detail, name='admin_patient_detail'),

    # ===== Appointments =====
    path('appointments/', views.appointment_list, name='admin_appointment_list'),

    # ===== Billing =====
    path('billing/', views.billing_list, name='admin_billing_list'),
    path('billing/<int:bill_id>/mark-paid/', views.mark_bill_paid, name='admin_mark_bill_paid'),

    # ===== Security Settings =====
    path('security-settings/', views.security_settings, name='admin_security_settings'),

    # ===== Account Status =====
    path('users/<int:user_id>/toggle-status/', views.toggle_user_status, name='admin_toggle_user_status'),

    # ===== Notifications =====
    path('notifications/', views.notifications_view, name='admin_notifications'),
    path('notifications/mark-all-read/', views.mark_all_read, name='admin_mark_all_read'),
    path('notifications/<int:notification_id>/dismiss/', views.dismiss_notification, name='admin_dismiss_notification'),

    # ===== Profile =====
    path('profile/', views.admin_profile, name='admin_profile'),
    path('profile/edit/', views.edit_profile, name='admin_edit_profile'),
    path('profile/change-password/', views.change_password, name='admin_change_password'),

]
