from accounts.models import User
from patient.models import Patient

PATIENTS = [
    ('anita.sharma@example.com', 'Anita', 'Sharma', '1994-06-12', 'Female', 'O+', '+91 98765 43210', 'Penicillin'),
    ('rohit.verma@example.com', 'Rohit', 'Verma', '1981-03-22', 'Male', 'B+', '+91 98765 11223', ''),
    ('priya.nair@example.com', 'Priya', 'Nair', '2018-09-05', 'Female', 'A+', '+91 98765 33445', 'Peanuts'),
    ('karan.malhotra@example.com', 'Karan', 'Malhotra', '1975-01-30', 'Male', 'AB-', '+91 98765 55667', ''),
    ('sneha.gupta@example.com', 'Sneha', 'Gupta', '1990-11-18', 'Female', 'B-', '+91 98765 77889', 'Dust'),
    ('vikram.singh@example.com', 'Vikram', 'Singh', '1988-07-09', 'Male', 'O-', '+91 98765 99001', ''),
    ('meera.pillai@example.com', 'Meera', 'Pillai', '1999-04-27', 'Female', 'AB+', '+91 98765 22334', ''),
    ('arjun.desai@example.com', 'Arjun', 'Desai', '1965-12-14', 'Male', 'A-', '+91 98765 44556', 'Sulfa drugs'),
    ('divya.reddy@example.com', 'Divya', 'Reddy', '2005-02-08', 'Female', 'B+', '+91 98765 66778', ''),
    ('rahul.kapoor@example.com', 'Rahul', 'Kapoor', '1997-08-19', 'Male', 'O+', '+91 98765 88990', 'Latex'),
]

created_count = 0

for email, first_name, last_name, dob, gender, blood_group, phone, allergies in PATIENTS:
    if User.objects.filter(email=email).exists():
        print('Skipped (already exists):', email)
        continue

    user = User.objects.create_user(
        username=email,
        email=email,
        password='PatientPass123',
        first_name=first_name,
        last_name=last_name,
        role='patient'
    )

    Patient.objects.create(
        user=user,
        phone=phone,
        date_of_birth=dob,
        gender=gender,
        blood_group=blood_group,
        allergies=allergies,
        city='New Delhi',
        state='Delhi',
        country='India',
    )

    created_count += 1
    print('Patient created:', email)

print(f'--- {created_count} new patients created ---')
