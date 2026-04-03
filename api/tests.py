from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import IdentityRegistry, Applicant, LoanApplication

class LEDS_APITests(APITestCase):
    def setUp(self):
        # Create simulator data in the Identity Registry
        self.perfect_pan = "ABCDE1234F"
        self.mid_pan = "GHIJK5678L"
        self.poor_pan = "MNOPQ9012R"
        
        IdentityRegistry.objects.create(
            pan=self.perfect_pan,
            aadhaar="123456789012",
            full_name="John Doe",
            dob="1990-01-01",
            phone="9876543210",
            address="123 Green Lane, Bangalore",
            pincode="560001",
            monthly_income=120000, # High income
            credit_score=800       # Excellent score
        )
        
        IdentityRegistry.objects.create(
            pan=self.mid_pan,
            aadhaar="098765432109",
            full_name="Jane Smith",
            dob="1992-05-15",
            phone="9123456780",
            address="456 Orange Street, Mumbai",
            pincode="400001",
            monthly_income=60000,  # Mid income
            credit_score=680       # Fair score
        )

        IdentityRegistry.objects.create(
            pan=self.poor_pan,
            aadhaar="111122223333",
            full_name="Alice Brown",
            dob="1985-08-20",
            phone="8888777766",
            address="789 Red Road, Delhi",
            pincode="110001",
            monthly_income=30000,  # Low income
            credit_score=400       # Poor score
        )

    # --- IDENTITY VERIFICATION TESTS ---

    def test_verify_pan_success(self):
        url = reverse('verify-pan')
        data = {'pan': self.perfect_pan}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['full_name'], "John Doe")

    def test_verify_pan_not_found(self):
        url = reverse('verify-pan')
        data = {'pan': "UNKNOWN99P"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_verify_aadhaar_success(self):
        url = reverse('verify-aadhaar')
        data = {'aadhaar': "123456789012"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Bangalore", response.data['address'])

    # --- CREDIT BUREAU SIMULATION TESTS ---

    def test_check_cibil_excellent(self):
        url = reverse('check-cibil')
        data = {
            'pan': self.perfect_pan,
            'loan_amount': 500000,
            'monthly_income': 120000
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['verdict'], 'EXCELLENT')
        self.assertTrue(response.data['eligible'])

    def test_check_cibil_poor(self):
        url = reverse('check-cibil')
        data = {
            'pan': self.poor_pan,
            'loan_amount': 100000,
            'monthly_income': 30000
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['verdict'], 'POOR')
        self.assertFalse(response.data['eligible'])

    # --- LOAN DECISION ENGINE TESTS ---

    def test_loan_application_auto_approval(self):
        url = reverse('apply-loan')
        data = {
            "applicant": {
                "pan": self.perfect_pan,
                "aadhaar": "123456789012",
                "full_name": "John Doe",
                "dob": "1990-01-01",
                "phone": "9876543210",
                "address": "123 Green Lane, Bangalore",
                "pincode": "560001"
            },
            "loan": {
                "amount": 200000,
                "tenure": 24,
                "purpose": "Home Improvement"
            },
            "bank": {
                "account_no": "9988776655",
                "ifsc": "HDFC0001234"
            }
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'APPROVED')
        self.assertEqual(float(response.data['amount']), 200000.0)

    def test_loan_application_manual_rejection_mid_range(self):
        url = reverse('apply-loan')
        data = {
            "applicant": {
                "pan": self.mid_pan, # CIBIL 680
                "aadhaar": "098765432109",
                "full_name": "Jane Smith",
                "dob": "1992-05-15",
                "phone": "9123456780",
                "address": "456 Orange Street, Mumbai",
                "pincode": "400001"
            },
            "loan": {
                "amount": 300000,
                "tenure": 12,
                "purpose": "Medical Emergency"
            },
            "bank": {
                "account_no": "1122334455",
                "ifsc": "ICIC0005678"
            }
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'REJECTED')

    def test_loan_application_rejection(self):
        url = reverse('apply-loan')
        data = {
            "applicant": {
                "pan": self.poor_pan,
                "aadhaar": "111122223333",
                "full_name": "Alice Brown",
                "dob": "1985-08-20",
                "phone": "8888777766",
                "address": "789 Red Road, Delhi",
                "pincode": "110001"
            },
            "loan": {
                "amount": 50000,
                "tenure": 6,
                "purpose": "Personal Use"
            },
            "bank": {
                "account_no": "5544332211",
                "ifsc": "SBIN0001234"
            }
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'REJECTED')
