from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ietf_language_tags', '0003_auto_20200506_1245'),
    ]

    operations = [
        migrations.AlterField(
            model_name='languagetagtranslation',
            name='name_t',
            field=models.CharField(max_length=255, verbose_name='Name for translation'),
        ),
    ]
