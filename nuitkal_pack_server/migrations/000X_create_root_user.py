# your_app/migrations/000X_create_root_user.py
from django.contrib.auth import get_user_model
from django.db import migrations


def create_root_user(apps, schema_editor):
    User = get_user_model()
    if not User.objects.filter(username="root").exists():
        User.objects.create_superuser(username="root", password="root")  # type: ignore


class Migration(migrations.Migration):
    dependencies = [
        ("nuitkal_pack_server", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_root_user),
    ]
