from accounts.models import User
from doctor.models import Doctor

DOCTORS = [
    ('dr.arjun@example.com', 'Arjun', 'Rao', 'cardiology', 'Interventional Cardiologist', 1000),
    ('dr.james@example.com', 'James', 'Carter', 'neurology', 'Neurologist', 1100),
    ('dr.meera@example.com', 'Meera', 'Iyer', 'neurology', 'Neurosurgeon', 1500),
    ('dr.michael@example.com', 'Michael', 'Reyes', 'orthopedics', 'Orthopedic Surgeon', 900),
    ('dr.karan@example.com', 'Karan', 'Malhotra', 'orthopedics', 'Joint Replacement Surgeon', 1300),
    ('dr.emily@example.com', 'Emily', 'Chen', 'pediatrics', 'Pediatrician', 700),
    ('dr.laura@example.com', 'Laura', 'Simmons', 'dermatology', 'Dermatologist', 800),
    ('dr.neha@example.com', 'Neha', 'Kapoor', 'general', 'General Physician', 500),
    ('dr.rohan@example.com', 'Rohan', 'Verma', 'general', 'Family Medicine Specialist', 500),
]

created_count = 0

for email, first_name, last_name, department, specialization, consultation_fee in DOCTORS:
    if User.objects.filter(email=email).exists():
        print('Skipped (already exists):', email)
        continue

    user = User.objects.create_user(
        username=email,
        email=email,
        password='DoctorPass123',
        first_name=first_name,
        last_name=last_name,
        role='doctor'
    )

    Doctor.objects.create(
        user=user,
        department=department,
        specialization=specialization,
        consultation_fee=consultation_fee,
    )

    created_count += 1
    print('Doctor created:', email)

print(f'--- {created_count} new doctors created ---')
