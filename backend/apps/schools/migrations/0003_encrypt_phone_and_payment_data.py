"""Encrypt schools' contact phone numbers and payment providers' answers in the database."""

import json

from django.db import migrations

import apps.core.encryption


def encrypt_phones(apps, schema_editor):
    """Rows written before encryption hold the plain number: saving it again encrypts it."""
    School = apps.get_model("schools", "School")
    for pk, phone in list(School.objects.exclude(phone="").values_list("pk", "phone")):
        School.objects.filter(pk=pk).update(phone=phone)


def decrypt_phones(apps, schema_editor):
    School = apps.get_model("schools", "School")
    table = schema_editor.quote_name(School._meta.db_table)
    rows = list(School.objects.exclude(phone="").values_list("pk", "phone"))
    with schema_editor.connection.cursor() as cursor:
        for pk, phone in rows:
            cursor.execute(f"UPDATE {table} SET phone = %s WHERE id = %s", [phone[:40], pk])


def encrypt_payment_data(apps, schema_editor):
    """Plain JSON from before is read as it is and written back encrypted."""
    Payment = apps.get_model("schools", "Payment")
    for pk, data in list(Payment.objects.exclude(provider_data__isnull=True).values_list("pk", "provider_data")):
        Payment.objects.filter(pk=pk).update(provider_data=data)


def decrypt_payment_data(apps, schema_editor):
    Payment = apps.get_model("schools", "Payment")
    table = schema_editor.quote_name(Payment._meta.db_table)
    rows = list(Payment.objects.exclude(provider_data__isnull=True).values_list("pk", "provider_data"))
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        for pk, data in rows:
            key = Payment._meta.pk.get_db_prep_value(pk, connection)
            cursor.execute(f"UPDATE {table} SET provider_data = %s WHERE id = %s", [json.dumps(data), key])


class Migration(migrations.Migration):
    dependencies = [
        ("schools", "0002_payment_checked_at"),
    ]

    operations = [
        migrations.AlterField(
            model_name="school",
            name="phone",
            field=apps.core.encryption.EncryptedTextField(blank=True, max_length=40),
        ),
        migrations.RunPython(encrypt_phones, decrypt_phones),
        migrations.AlterField(
            model_name="payment",
            name="provider_data",
            field=apps.core.encryption.EncryptedJSONField(blank=True, default=dict),
        ),
        migrations.RunPython(encrypt_payment_data, decrypt_payment_data),
    ]
