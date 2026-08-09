from accounts.models import User

email = 'admin@example.com'

if User.objects.filter(email=email).exists():
    print('Skipped (already exists):', email)
else:
    user = User.objects.create_user(
        username=email,
        email=email,
        password='AdminPass123',
        first_name='Vikrant',
        last_name='Mehta',
        role='admin',
    )
    print('Admin created:', user.email)
