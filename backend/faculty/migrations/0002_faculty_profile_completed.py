from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('faculty', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='faculty',
            name='profile_completed',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='employeeprofile',
            name='cnic',
            field=models.CharField(blank=True, default='', max_length=15, unique=True),
        ),
        migrations.AlterField(
            model_name='employeeprofile',
            name='current_address',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='employeeprofile',
            name='date_of_birth',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='employeeprofile',
            name='emergency_contact_name',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AlterField(
            model_name='employeeprofile',
            name='emergency_contact_phone',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
        migrations.AlterField(
            model_name='employeeprofile',
            name='emergency_contact_relation',
            field=models.CharField(blank=True, default='', max_length=50),
        ),
        migrations.AlterField(
            model_name='employeeprofile',
            name='phone_number',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
    ]
