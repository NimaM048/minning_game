from django.db import migrations

def create_initial_miners(apps, schema_editor):
    Miner = apps.get_model('miners', 'Miner')
    Plan = apps.get_model('plans', 'Plan')
    Token = apps.get_model('token_app', 'Token')

    token = Token.objects.first()
    if not token:
        raise Exception("No token found. Please create a Token before running this migration.")

    for level in range(1, 22):  # Plan 1 to 21
        plan = Plan.objects.filter(level=level).first()
        if not plan:
            raise Exception(f"Plan with level {level} not found. Run plan creation migration first.")

        Miner.objects.create(
            plan=plan,
            token=token,
            name=f"Miner {level}",
            power=plan.power,
            is_online=True  # یا False اگر می‌خوای خاموش باشن اولش
        )

def delete_initial_miners(apps, schema_editor):
    Miner = apps.get_model('miners', 'Miner')
    Miner.objects.filter(name__startswith="Miner ").delete()

class Migration(migrations.Migration):

    dependencies = [
        ('miners', '0001_initial'),  # آخرین فایل مایگریشن miners
        ('plans', '0005_auto_20250711_0330'),  # جایی که ۲۱ پلن ساخته شدن
    ]

    operations = [
        migrations.RunPython(create_initial_miners, delete_initial_miners),
    ]
