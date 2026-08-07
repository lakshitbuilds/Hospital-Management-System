from accounts.models import User
from doctor.models import Doctor

user = User.objects.create_user(
    username='dr.sarah@example.com',
    email='dr.sarah@example.com',
    password='DoctorPass123',
    first_name='Sarah',
    last_name='Mitchell',
    role='doctor'
)

Doctor.objects.create(
    user=user,
    department='cardiology',
    specialization='Cardiologist'
)

print('Doctor created:', user.email)