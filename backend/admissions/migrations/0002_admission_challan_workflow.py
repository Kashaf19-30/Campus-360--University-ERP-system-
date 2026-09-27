# Generated migration for admission challan workflow

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admissions', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='admissionapplication',
            name='admission_challan_amount',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='admissionapplication',
            name='admission_challan_number',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name='admissionapplication',
            name='challan_paid',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='admissionapplication',
            name='rejection_message',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='admissionapplication',
            name='status',
            field=models.CharField(
                choices=[
                    ('draft', 'Draft'),
                    ('pending', 'Pending'),
                    ('challan_pending', 'Challan Pending'),
                    ('under_review', 'Under Review'),
                    ('documents_pending', 'Documents Pending'),
                    ('approved', 'Approved'),
                    ('rejected', 'Rejected'),
                    ('waitlist', 'Waitlist'),
                    ('registered', 'Registered'),
                ],
                default='pending',
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='applicantdocument',
            name='document_type',
            field=models.CharField(
                choices=[
                    ('cnic_front', 'CNIC Front'),
                    ('cnic_back', 'CNIC Back'),
                    ('domicile', 'Domicile'),
                    ('photograph', 'Photograph'),
                    ('matric_marksheet', 'Matric Marksheet'),
                    ('matric_certificate', 'Matric Certificate'),
                    ('inter_marksheet', 'Inter Marksheet'),
                    ('inter_certificate', 'Inter Certificate'),
                    ('paid_challan', 'Paid Admission Challan'),
                ],
                max_length=50,
            ),
        ),
    ]
