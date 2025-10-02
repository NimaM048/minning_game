from django.db import migrations

def create_initial_plans(apps, schema_editor):
    Plan = apps.get_model('plans', 'Plan')
    Token = apps.get_model('token_app', 'Token')

    token = Token.objects.first()
    if not token:
        raise Exception("No token found. Please create a Token before running this migration.")

    base_price = 5000
    base_power = 1

    for level in range(1, 22):  # Plan 1 to 21
        price = base_price * (2 ** (level - 1))  # دو برابر شونده
        power = base_power * (2 ** (level - 1))  # MH/s هم دو برابر

        Plan.objects.create(
            name=f"Plan {level}",
            level=level,
            price=price,
            power=power,
            token=token,
        )

def delete_initial_plans(apps, schema_editor):
    Plan = apps.get_model('plans', 'Plan')
    Plan.objects.filter(level__lte=21).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('plans', '0001_initial'),  # مطمئن شو این شماره با آخرین فایل توی plans/migrations یکی باشه
    ]

    operations = [
        migrations.RunPython(create_initial_plans, delete_initial_plans),
    ]
