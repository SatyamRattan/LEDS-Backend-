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
