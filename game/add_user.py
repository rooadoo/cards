import django.contrib.auth
import string
from secrets import SystemRandom

# chars to use for password, replace ambiguous letters
CHARS = string.ascii_letters.replace("O", "").replace("l", "") + string.digits

def add_user(username, superuser=False):
    password = "".join(SystemRandom().choices(CHARS, k=10))

    User = django.contrib.auth.get_user_model()
    user = User.objects.create_user(username, password=password)
    user.is_superuser = superuser
    user.is_staff = False
    user.save()

    print(f"User {username} created with password {password}")
