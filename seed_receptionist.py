from accounts.models import User
from receptionist.models import Receptionist

email = 'reception@example.com'

if User.objects.filter(email=email).exists():
    print('Skipped (already exists):', email)
else:
    user = User.objects.create_user(
        username=email,
        email=email,
        password='ReceptionPass123',
        first_name='Priya',
        last_name='Nair',
        role='receptionist',
    )

    receptionist = Receptionist.objects.create(user=user, phone='+91 98765 00011', shift='morning')

    print('Receptionist created:', user.email, '-', receptionist.employee_id)
