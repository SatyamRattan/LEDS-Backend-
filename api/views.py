from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Applicant, LoanApplication, IdentityRegistry
from .services import IdentityService, CreditService

class VerifyPanView(APIView):
    """
    Simulates calling an External Identity Registry (DPI simulation).
    Fetches user data dynamically if it exists in the simulator registry.
    """
    def post(self, request):
        pan = request.data.get('pan', '').upper()
        if not pan or len(pan) != 10:
            return Response({"error": "Invalid PAN format"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Discover user from External Identity Registry
        registry_user = IdentityService.discover_identity(pan)
        
        if not registry_user:
            return Response({
                "error": "PAN Not Found in Registry",
                "detail": "Please add this user to the Identity Registry in Django Admin first."
            }, status=status.HTTP_404_NOT_FOUND)
        
        return Response({
            "pan": registry_user.pan,
            "full_name": registry_user.full_name,
            "dob": registry_user.dob,
            "phone": registry_user.phone
        }, status=status.HTTP_200_OK)

class VerifyAadhaarView(APIView):
    """
    Simulates KYC process via Aadhaar discovery.
    """
    def post(self, request):
        aadhaar = request.data.get('aadhaar', '')
        if not aadhaar or len(aadhaar) != 12:
            return Response({"error": "Invalid Aadhaar format"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Discover address from External KYC Registry
        registry_user = IdentityService.verify_kyc(aadhaar)
        
        if not registry_user:
            return Response({
                "error": "Aadhaar Not Found in Registry",
                "detail": "Ensure Aadhaar matches the PAN in Identity Registry."
            }, status=status.HTTP_404_NOT_FOUND)
        
        return Response({
            "aadhaar": registry_user.aadhaar,
            "address": registry_user.address,
            "pincode": registry_user.pincode
        }, status=status.HTTP_200_OK)

class CheckCibilView(APIView):
    """
    Fetches CIBIL score from the Credit Bureau Simulator.
    Called after the user provides PAN, Aadhaar, income details, and loan amount.
    """
    def post(self, request):
        try:
            print(f"DEBUG: Receiving CIBIL request: {request.data}")
            pan = request.data.get('pan', '').upper()
            loan_amount = float(request.data.get('loan_amount', 0) or 0)
            monthly_income = float(request.data.get('monthly_income', 0) or 0)

            if not pan:
                return Response({"error": "PAN is required"}, status=status.HTTP_400_BAD_REQUEST)

            try:
                registry_user = IdentityRegistry.objects.get(pan=pan)
            except IdentityRegistry.DoesNotExist:
                return Response({"error": f"PAN {pan} not found in bureau database. Please add it via admin panels."}, status=status.HTTP_404_NOT_FOUND)

            cibil = registry_user.credit_score
            estimated_emi = (loan_amount * 1.12) / 12
            emi_ratio = round((estimated_emi / monthly_income * 100), 1) if monthly_income > 0 else 100

            if cibil >= 750:
                verdict = 'EXCELLENT'
                verdict_color = 'green'
                eligible = True
                message = 'Your CIBIL score is excellent. You qualify for the best interest rates!'
            else:
                verdict = 'POOR'
                verdict_color = 'red'
                eligible = False
                message = f'Your CIBIL score ({cibil}) is below our minimum threshold of 750. We are unable to process this loan.'

            response_data = {
                "cibil_score": cibil,
                "verdict": verdict,
                "verdict_color": verdict_color,
                "eligible": eligible,
                "message": message,
                "emi_ratio": emi_ratio,
            }
            print(f"DEBUG: CIBIL check successful for {pan}: {response_data}")
            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            print(f"CRITICAL ERROR in CheckCibilView: {str(e)}")
            return Response({"error": f"System error while fetching credit score: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LoanApplicationView(APIView):
    """
    Dynamic Credit Decision and Application Submission.
    """
    def post(self, request):
        data = request.data
        applicant_info = data.get('applicant', {})
        loan_info = data.get('loan', {})
        bank_info = data.get('bank', {})
        
        pan = applicant_info.get('pan')
        
        # 1. Fetch live Credit Score from Bureau Simulator
        cibil = CreditService.get_cibil_score(pan)
        
        # 2. Get Income from Identity Registry
        registry_user = IdentityRegistry.objects.get(pan=pan)
        monthly_income = float(registry_user.monthly_income)
        
        # 3. Decision Logic (Dynamic)
        credit_status, interest_rate = CreditService.evaluate_loan(
            amount=float(loan_info.get('amount', 0)),
            monthly_income=monthly_income,
            cibil=cibil
        )
        
        # 4. Persistence
        applicant, _ = Applicant.objects.update_or_create(
            pan=pan,
            defaults={
                'aadhaar': applicant_info.get('aadhaar'),
                'full_name': applicant_info.get('full_name'),
                'dob': applicant_info.get('dob'),
                'phone': applicant_info.get('phone'),
                'address': applicant_info.get('address'),
                'pincode': applicant_info.get('pincode'),
            }
        )
        
        loan = LoanApplication.objects.create(
            applicant=applicant,
            amount=loan_info.get('amount'),
            tenure=loan_info.get('tenure'),
            purpose=loan_info.get('purpose'),
            cibil_score=cibil,
            status=credit_status,
            interest_rate=interest_rate,
            account_no=bank_info.get('account_no'),
            ifsc=bank_info.get('ifsc')
        )
        
        return Response({
            "message": "Application processed via Dynamic Credit Engine",
            "loan_id": loan.id,
            "status": loan.status,
            "cibil": loan.cibil_score,
            "interest_rate": loan.interest_rate,
            "amount": loan.amount,
            "tenure": loan.tenure,
            "account_no": loan.account_no,
            "income_profile": "Standard" if monthly_income < 100000 else "Premium"
        }, status=status.HTTP_201_CREATED)
