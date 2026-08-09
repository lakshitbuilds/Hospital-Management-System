from accounts.models import User
from doctor.models import Doctor

DOCTORS = [
    ('dr.arjun@example.com', 'Arjun', 'Rao', 'cardiology', 'Interventional Cardiologist'),
    ('dr.james@example.com', 'James', 'Carter', 'neurology', 'Neurologist'),
    ('dr.meera@example.com', 'Meera', 'Iyer', 'neurology', 'Neurosurgeon'),
    ('dr.michael@example.com', 'Michael', 'Reyes', 'orthopedics', 'Orthopedic Surgeon'),
    ('dr.karan@example.com', 'Karan', 'Malhotra', 'orthopedics', 'Joint Replacement Surgeon'),
    ('dr.emily@example.com', 'Emily', 'Chen', 'pediatrics', 'Pediatrician'),
    ('dr.laura@example.com', 'Laura', 'Simmons', 'dermatology', 'Dermatologist'),
    ('dr.neha@example.com', 'Neha', 'Kapoor', 'general', 'General Physician'),
    ('dr.rohan@example.com', 'Rohan', 'Verma', 'general', 'Family Medicine Specialist'),
]

created_count = 0

for email, first_name, last_name, department, specialization in DOCTORS:
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
        specialization=specialization
    )

    created_count += 1
    print('Doctor created:', email)

print(f'--- {created_count} new doctors created ---')
