import random
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from io import BytesIO
from .models import IdentityRegistry, Applicant, LoanApplication

class IdentityService:
    """
    Simulates calling an external Fintech data provider (e.g., NSDL or UIDAI).
    In a production system, this would use `requests.get(EXTERNAL_API_URL)`.
    """
    
    @staticmethod
    def discover_identity(pan: str):
        try:
            return IdentityRegistry.objects.get(pan=pan.upper())
        except IdentityRegistry.DoesNotExist:
            return None

    @staticmethod
    def verify_kyc(aadhaar: str):
        try:
            return IdentityRegistry.objects.get(aadhaar=aadhaar)
        except IdentityRegistry.DoesNotExist:
            return None

class CreditService:
    """
    Simulates a Credit Bureau (CIBIL) evaluation engine.
    """
    
    @staticmethod
    def get_cibil_score(pan: str):
        # Fetch actual score from registry simulation
        try:
            registry_entry = IdentityRegistry.objects.get(pan=pan.upper())
            return registry_entry.credit_score
        except IdentityRegistry.DoesNotExist:
            return 300 # Default poor score if unknown

    @staticmethod
    def evaluate_loan(amount: float, monthly_income: float, cibil: int):
        """
        Decision Logic:
        - If CIBIL > 750 AND EMI < 50% of income -> Green ✅
        - Else -> Red ❌
        """
        # Simple EMI estimation (12% interest, 1 year)
        estimated_emi = (amount * 1.12) / 12
        
        if cibil >= 750 and estimated_emi < (monthly_income * 0.5):
            return 'APPROVED', 10.5
        else:
            return 'REJECTED', 0.0

class ContractService:
    """
    Generates PDF Loan Agreement using ReportLab.
    """
    @staticmethod
    def generate_agreement_pdf(loan_app):
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        
        # Header
        p.setFont("Helvetica-Bold", 18)
        p.drawCentredString(300, 800, "LOAN AGREEMENT & DISCLOSURE")
        p.setLineWidth(1)
        p.line(100, 790, 500, 790)

        # Basic Info
        p.setFont("Helvetica", 10)
        p.drawString(100, 770, f"Agreement ID: #LED-AG-{loan_app.id}")
        p.drawString(100, 755, f"Date generated: {loan_app.created_at.strftime('%Y-%m-%d %H:%M')}")

        # Section 1: Borrower Details
        p.setFont("Helvetica-Bold", 12)
        p.drawString(100, 725, "1. BORROWER DETAILS")
        p.setFont("Helvetica", 10)
        p.drawString(120, 705, f"Full Name: {loan_app.applicant.full_name}")
        p.drawString(120, 690, f"PAN Number: {loan_app.applicant.pan}")
        p.drawString(120, 675, f"Aadhaar Number: {loan_app.applicant.aadhaar}")
        p.drawString(120, 660, f"Permanent Address: {loan_app.applicant.address}")

        # Section 2: Loan Terms
        p.setFont("Helvetica-Bold", 12)
        p.drawString(100, 630, "2. LOAN TERMS")
        p.setFont("Helvetica", 10)
        p.drawString(120, 610, f"Principal Amount: INR {loan_app.amount:,.2f}")
        p.drawString(120, 595, f"Repayment Tenure: {loan_app.tenure} Months")
        p.drawString(120, 580, f"Annual Interest Rate: {loan_app.interest_rate}% p.a. (Fixed)")
        p.drawString(120, 565, f"Purpose of Loan: {loan_app.purpose}")

        # Section 3: Terms and Conditions
        p.setFont("Helvetica-Bold", 12)
        p.drawString(100, 530, "3. TERMS AND CONDITIONS")
        p.setFont("Helvetica", 9)
        
        # Wrapped text simulation
        text_lines = [
            "I, the undersigned Borrower, hereby acknowledge and agree to the terms of this Loan Agreement. I confirm that all information",
            "provided during the application process is true and correct to the best of my knowledge. I understand that the loan",
            "disbursement is subject to final verification and Video KYC completion.",
            "",
            "The Borrower agrees to repay the Principal Amount along with the accrued interest through the bank account specified in",
            "the disbursement step. Any default in repayment may lead to legal action and reporting to Credit Bureaus (CIBIL, etc.).",
            "",
            "ELECTRONIC SIGNATURE: By proceeding with the electronic application, I am providing my legally binding electronic signature",
            "to this agreement, equivalent to a physical signature under the Information Technology Act."
        ]
        
        y_pos = 510
        for line in text_lines:
            p.drawString(100, y_pos, line)
            y_pos -= 15

        # Signatures
        p.setDash(1, 4)
        p.line(100, 250, 250, 250)
        p.setFont("Helvetica-Oblique", 9)
        p.drawString(100, 235, "Borrower's Signature (E-Signed)")
        
        p.line(350, 250, 550, 250)
        p.drawString(350, 235, "Authorized Signatory (Antigravity LEDS)")
        
        p.setFont("Helvetica", 8)
        p.drawCentredString(300, 50, f"Document Generated dynamically by LEDS System on {loan_app.created_at.strftime('%Y-%m-%d')}")
        
        p.showPage()
        p.save()
        
        buffer.seek(0)
        return buffer

class DisbursementService:
    """
    Simulates fund transfer to a bank account.
    """
    @staticmethod
    def disburse_funds(loan_app):
        import uuid
        from django.utils import timezone
        
        # Simulate local bank validation
        if len(loan_app.account_no) < 10:
            raise ValueError("Invalid Account Number")
            
        txn_id = f"TXN-{uuid.uuid4().hex[:12].upper()}"
        loan_app.status = 'DISBURSED'
        loan_app.disbursed_at = timezone.now()
        loan_app.transaction_id = txn_id
        loan_app.save()
        
        return txn_id

class NotificationService:
    """
    Central engine for SMS and Email notifications.
    Mocked to console for development.
    """
    @staticmethod
    def send_sms(phone, message):
        print(f"\n[SMS SENT to {phone}]: {message}\n")

    @staticmethod
    def send_email(email, subject, body):
        print(f"\n[EMAIL SENT to {email}]\nSubject: {subject}\nBody: {body}\n")
