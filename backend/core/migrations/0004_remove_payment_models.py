from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0003_apikey_key_hash'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Token',
        ),
        migrations.DeleteModel(
            name='Transaction',
        ),
        migrations.AlterField(
            model_name='conversationstate',
            name='current_step',
            field=models.CharField(
                choices=[
                    ('inquiry', 'Inquiry'),
                    ('property_selection', 'Property Selection'),
                    ('booking_confirmation', 'Booking Confirmation'),
                    ('additional_info', 'Additional Info'),
                    ('completed', 'Completed'),
                ],
                default='inquiry',
                max_length=50,
            ),
        ),
    ]
