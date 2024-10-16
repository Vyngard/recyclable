# Generated by Django 4.2.7 on 2024-08-20 20:28

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Container',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('barcode', models.CharField(max_length=255, unique=True)),
                ('brand', models.CharField(default='', max_length=255)),
                ('product_name', models.CharField(default='', max_length=255)),
                ('material_type', models.CharField(choices=[('alu', 'Aluminum'), ('bimetal', 'Bimetal'), ('cardboard', 'Cardboard'), ('FOIL_LAMINATE', 'Foil Laminate'), ('glass', 'Glass'), ('paper', 'Paper'), ('organic', 'Organic'), ('plastic', 'Plastic'), ('other', 'Other'), ('unknown', 'Unknown')], max_length=31)),
                ('plastic_code', models.CharField(choices=[('1_pet', '1-PET'), ('2_hdpe', '2-HDPE'), ('3_pvc', '3-PVC'), ('4_ldpe', '4-LDPE'), ('5_pp', '5-PP'), ('6_ps', '6-PS'), ('7_o', '7-OTHER'), ('NA', 'NA'), ('unknown', 'Unknown')], max_length=31)),
                ('liquid_volume', models.FloatField()),
                ('liquid_volume_unit', models.CharField(choices=[('OZ', 'fl oz'), ('ML', 'mL'), ('LITER', 'L'), ('NA', 'NA')], max_length=31)),
                ('mass_gram', models.FloatField(default=0.0)),
                ('ca', models.BooleanField(default=False)),
                ('ct', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='Image',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('aws_entity_tag', models.CharField(max_length=511, unique=True)),
                ('s3_bucket_name', models.CharField(max_length=63)),
                ('aws_region_name', models.CharField(max_length=63)),
                ('s3_object_key', models.CharField(max_length=511, unique=True)),
                ('crush_degree', models.IntegerField()),
                ('valid_orientation', models.BooleanField()),
                ('container', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='recyclable.container')),
            ],
        ),
    ]
