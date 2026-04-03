import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()
from api.models import IdentityRegistry
from datetime import date

users = [
    {"pan": "ABCD1234E", "aadhaar": "123456789012", "full_name": "Satyam (Insta-Approved)", "dob": date(1995, 5, 20), "phone": "9876543210", "address": "Tech Park, Bangalore", "pincode": "560001", "monthly_income": 250000.00, "credit_score": 850},
    {"pan": "WXYZ9876Q", "aadhaar": "987654321098", "full_name": "Rohan (Rejected poor CIBIL)", "dob": date(1998, 8, 15), "phone": "9998887770", "address": "New Market, Kolkata", "pincode": "700001", "monthly_income": 35000.00, "credit_score": 550},
    {"pan": "TEST5678M", "aadhaar": "555566667777", "full_name": "Priya (Manual Review)", "dob": date(1992, 12, 1), "phone": "8887776665", "address": "Marine Drive, Mumbai", "pincode": "400001", "monthly_income": 65000.00, "credit_score": 680}
]

for u in users:
    IdentityRegistry.objects.get_or_create(pan=u['pan'], defaults=u)

print("Identities seeded perfectly into PostgreSQL!")
