import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()
from api.models import IdentityRegistry
from datetime import date

# Clear old invalid ones
IdentityRegistry.objects.all().delete()

# Seed corrected 10-character PANs matching the exact RegEx [A-Z]{5}[0-9]{4}[A-Z]{1}
users = [
    {"pan": "ABCDE1234F", "aadhaar": "123456789012", "full_name": "Satyam (Insta-Approved)", "dob": date(1995, 5, 20), "phone": "9876543210", "address": "Tech Park, Bangalore", "pincode": "560001", "monthly_income": 250000.00, "credit_score": 850},
    {"pan": "WXYZQ9876P", "aadhaar": "987654321098", "full_name": "Rohan (Rejected)", "dob": date(1998, 8, 15), "phone": "9998887770", "address": "New Market, Kolkata", "pincode": "700001", "monthly_income": 35000.00, "credit_score": 550},
    {"pan": "TESTM5678N", "aadhaar": "555566667777", "full_name": "Priya (Manual Review)", "dob": date(1992, 12, 1), "phone": "8887776665", "address": "Marine Drive, Mumbai", "pincode": "400001", "monthly_income": 65000.00, "credit_score": 680}
]

for u in users:
    IdentityRegistry.objects.get_or_create(pan=u['pan'], defaults=u)

print("Identities seeded perfectly into PostgreSQL!")
