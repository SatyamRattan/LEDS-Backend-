import random
import re
import cv2
import numpy as np
import easyocr
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Applicant, LoanApplication, IdentityRegistry, OTPVerification
from .services import IdentityService, CreditService, ContractService, DisbursementService, NotificationService
from django.db.models import Count, Sum, Q
from django.db import models
from datetime import datetime

# Initialize EasyOCR reader (English)
# GPU=False for CPU compatibility in development
reader = easyocr.Reader(['en'], gpu=False)

def safe_float(value, default=0.0):
    try:
        if value is None or value == '':
            return default
        return float(value)
    except (ValueError, TypeError):
        return default

def safe_int(value, default=0):
    try:
        if value is None or value == '':
            return default
        return int(value)
    except (ValueError, TypeError):
        return default

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
            loan_amount = safe_float(request.data.get('loan_amount', 0))
            monthly_income = safe_float(request.data.get('monthly_income', 0))

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
        try:
            data = request.data
            applicant_info = data.get('applicant', {})
            loan_info = data.get('loan', {})
            bank_info = data.get('bank', {})
            income_info = data.get('income', {})
            
            pan = applicant_info.get('pan')
            if not pan:
                return Response({"error": "PAN is mandatory for loan application"}, status=status.HTTP_400_BAD_REQUEST)
            
            # 1. Fetch live Credit Score from Bureau Simulator
            cibil = CreditService.get_cibil_score(pan)
            
            # 2. Get Income from Identity Registry or Fallback
            try:
                registry_user = IdentityRegistry.objects.get(pan=pan.upper())
                monthly_income = float(registry_user.monthly_income)
            except IdentityRegistry.DoesNotExist:
                # Fallback to declared income if not in registry
                monthly_income = safe_float(income_info.get('monthly_salary', 30000))
            
            # 3. Decision Logic (Dynamic)
            credit_status, interest_rate = CreditService.evaluate_loan(
                amount=safe_float(loan_info.get('amount', 0)),
                monthly_income=monthly_income,
                cibil=cibil
            )
            
            # 4. Handle DOB Format (OCR returns DD/MM/YYYY, DB needs YYYY-MM-DD)
            dob = applicant_info.get('dob')
            if dob and "/" in dob:
                try:
                    d, m, y = dob.split("/")
                    dob = f"{y}-{m}-{d}"
                except:
                    pass
            
            # 5. Persistence
            applicant, _ = Applicant.objects.update_or_create(
                pan=pan,
                defaults={
                    'aadhaar': applicant_info.get('aadhaar'),
                    'full_name': applicant_info.get('full_name', 'Extracted User'),
                    'dob': dob or '1990-01-01',
                    'phone': applicant_info.get('phone', '9876543210'),
                    'address': applicant_info.get('address', 'Extracted Address'),
                    'pincode': applicant_info.get('pincode', '000000'),
                }
            )
            
            loan = LoanApplication.objects.create(
                applicant=applicant,
                amount=safe_float(loan_info.get('amount', 0)),
                tenure=safe_int(loan_info.get('tenure', 12)),
                purpose=loan_info.get('purpose', 'General Purpose'),
                cibil_score=cibil,
                status=credit_status,
                interest_rate=interest_rate,
                account_no=bank_info.get('account_no'),
                ifsc=bank_info.get('ifsc')
            )
            
            # Notification (Safe trigger)
            try:
                NotificationService.send_sms(applicant.phone, f"Application #LED{loan.id} received! Tracker: http://localhost:4200/track/{loan.id}")
            except:
                pass
            
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

        except Exception as e:
            print(f"CRITICAL ERROR in LoanApplicationView: {str(e)}")
            return Response({
                "error": "Internal Processing Error",
                "detail": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

class AdminStatsView(APIView):
    """
    Returns aggregated metrics for the Admin Dashboard.
    """
    def get(self, request):
        from django.db.models.functions import Coalesce
        stats = LoanApplication.objects.aggregate(
            total_disbursed=Coalesce(Sum('amount', filter=Q(status='DISBURSED')), 0, output_field=models.DecimalField()),
            count_approved=Count('id', filter=Q(status='APPROVED')),
            count_disbursed=Count('id', filter=Q(status='DISBURSED')),
            count_rejected=Count('id', filter=Q(status='REJECTED')),
            count_review=Count('id', filter=Q(status='REVIEW')),
            count_pending=Count('id', filter=Q(status='PENDING')),
        )
        
        # Latest 5 applications
        recent = LoanApplication.objects.select_related('applicant').order_by('-created_at')[:5]
        from .serializers import LoanApplicationSerializer
        recent_serializer = LoanApplicationSerializer(recent, many=True)

        return Response({
            "metrics": stats,
            "recent_applications": recent_serializer.data
        }, status=status.HTTP_200_OK)

class AdminLoanListView(APIView):
    """
    Full list of all loan applications.
    """
    def get(self, request):
        # Optional: Add filters for status
        status_filter = request.query_params.get('status')
        loans = LoanApplication.objects.select_related('applicant').all().order_by('-created_at')
        
        if status_filter:
            loans = loans.filter(status=status_filter)

        from .serializers import LoanApplicationSerializer
        serializer = LoanApplicationSerializer(loans, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class AdminActionView(APIView):
    """
    Manual override for loan status (Approval/Rejection).
    """
    def post(self, request, pk):
        try:
            loan = LoanApplication.objects.get(pk=pk)
            new_status = request.data.get('status')
            
            if new_status not in ['APPROVED', 'REJECTED', 'REVIEW']:
                return Response({"error": "Invalid status choice"}, status=status.HTTP_400_BAD_REQUEST)

            loan.status = new_status
            
            # If manually approved, apply a standard interest rate if not set
            if new_status == 'APPROVED' and not loan.interest_rate:
                loan.interest_rate = 12.0
                
            loan.save()
            
            # Notifications
            status_msg = "Approved" if new_status == "APPROVED" else "Rejected"
            NotificationService.send_email(loan.applicant.pan + "@example.com", f"Loan Application {status_msg}", f"Your application #LED{loan.id} has been {new_status.lower()}. Log in to your dashboard for next steps.")
            
            return Response({"message": f"Loan {pk} updated to {new_status}"}, status=status.HTTP_200_OK)
            
        except LoanApplication.DoesNotExist:
            return Response({"error": "Loan application not found"}, status=status.HTTP_404_NOT_FOUND)

class DocumentOCRView(APIView):
    """
    Simulates OCR processing of PAN and Aadhaar documents.
    In production, this would use pytesseract or AWS Textract.
    """
    def post(self, request):
        file_obj = request.data.get('file')
        doc_type = request.data.get('doc_type') # 'pan' or 'aadhaar'
        
        if not file_obj:
            return Response({"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 1. Read document into OpenCV
            file_bytes = np.frombuffer(file_obj.read(), np.uint8)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            
            if img is None:
                return Response({"error": "Invalid image file"}, status=status.HTTP_400_BAD_REQUEST)

            # 2. PRE-PROCESSING: Resize and Rotate for better OCR accuracy
            # Resize to standard width for consistent performance
            height, width = img.shape[:2]
            scale = 1000 / width
            resized_img = cv2.resize(img, (1000, int(height * scale)))
            gray = cv2.cvtColor(resized_img, cv2.COLOR_BGR2GRAY)

            # 3. Perform OCR with Multi-Rotation
            # We try 0deg and then 90deg increments to find the text
            raw_text = ""
            text_blobs = []
            
            # Rotations to try: 0, 90 (CW), 90 (CCW)
            angles = [None, cv2.ROTATE_90_CLOCKWISE, cv2.ROTATE_90_COUNTERCLOCKWISE]
            
            for angle in angles:
                work_img = gray if angle is None else cv2.rotate(gray, angle)
                results = reader.readtext(work_img, detail=0)
                temp_text = " ".join(results).upper()
                
                # Check for ID patterns in this rotation
                if re.search(r'[A-Z]{5}[0-9]{4}[A-Z]{1}', temp_text) or re.search(r'[0-9]{4}\s?[0-9]{4}\s?[0-9]{4}', temp_text):
                    raw_text = temp_text
                    text_blobs = results
                    print(f"[OCR] Rotation {angle} SUCCESS")
                    break
                else:
                    raw_text += " " + temp_text # Collect all just in case
                    text_blobs.extend(results)

            print(f"\n[REAL OCR EXTRACTED TEXT]: {raw_text}\n")

            # 4. Intelligent Extraction
            extracted_data = {}
            if doc_type == 'pan':
                # RegEx for PAN: Standard 10-character AlphaNumeric
                pan_match = re.search(r'[A-Z]{5}[0-9]{4}[A-Z]{1}', raw_text)
                pan_val = pan_match.group(0) if pan_match else "UNKNOWN"
                
                # Heuristic for Name: Take first line below "NAME" or 
                # first sequence of 2+ words in upper case
                name_val = self._extract_field(text_blobs, "NAME")
                if not name_val:
                    # Look for first 2-3 uppercase words sequence (Typical for PAN Card)
                    name_match = re.search(r'[A-Z]{3,}\s[A-Z]{3,}(\s[A-Z]{3,})?', raw_text)
                    name_val = name_match.group(0) if name_match else "EXTRACTED USER"

                # RegEx for DOB: DD/MM/YYYY
                dob_match = re.search(r'[0-9]{2}/[0-9]{2}/[0-9]{4}', raw_text)
                dob_val = dob_match.group(0) if dob_match else "1995-01-01"

                # Convert DD/MM/YYYY to YYYY-MM-DD for Django models if needed
                if "/" in dob_val:
                    d, m, y = dob_val.split("/")
                    dob_db_format = f"{y}-{m}-{d}"
                else:
                    dob_db_format = "1995-01-01"

                extracted_data = {
                    "pan": pan_val,
                    "full_name": name_val,
                    "dob": dob_val, # For UI
                    "dob_db": dob_db_format, # For registry
                    "message": f"Real-time PAN {pan_val} extracted via Multi-Angle AI ✅"
                }

            else:
                # RegEx for Aadhaar: 12 digits (with potential spaces)
                aadhaar_match = re.search(r'[0-9]{4}\s?[0-9]{4}\s?[0-9]{4}', raw_text)
                aadhaar_val = aadhaar_match.group(0).replace(" ", "") if aadhaar_match else "UNKNOWN"
                
                # RegEx for Pincode
                pin_match = re.search(r'[0-9]{6}', raw_text)
                pin_val = pin_match.group(0) if pin_match else "000000"

                # Heuristic for Address: Look for S/O, D/O, W/O or Address keywords
                address_val = self._extract_address(text_blobs, pin_val)

                extracted_data = {
                    "aadhaar": aadhaar_val,
                    "address": address_val,
                    "pincode": pin_val,
                    "message": f"Real-time Aadhaar {aadhaar_val} extracted via AI ✅"
                }

            # 5. AUTO-SYNC WITH IDENTITY REGISTRY
            if extracted_data.get('pan') and extracted_data['pan'] != "UNKNOWN":
                # We update/create by PAN. Aadhaar might be null initially.
                # Since we made Aadhaar optional in the model, this works.
                IdentityRegistry.objects.update_or_create(
                    pan=extracted_data['pan'],
                    defaults={
                        "full_name": extracted_data.get('full_name', 'EXTRACTED USER'),
                        "dob": extracted_data.get('dob_db', '1990-01-01'),
                        "phone": "9876543210",
                        "credit_score": 750
                    }
                )
            elif extracted_data.get('aadhaar') and extracted_data['aadhaar'] != "UNKNOWN":
                # If we only have Aadhaar, we skip the registry update for now 
                # as PAN is the mandatory primary key for our simulation.
                pass

            return Response(extracted_data, status=status.HTTP_200_OK)

        except Exception as e:
            print(f"OCR ENGINE ERROR: {str(e)}")
            return Response({"error": f"OCR Engine Failure: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _extract_field(self, blobs, keyword):
        """Helper to find text relative to a keyword"""
        for i, blob in enumerate(blobs):
            if keyword in blob.upper():
                if i + 1 < len(blobs):
                    return blobs[i+1].upper()
        return None

    def _extract_address(self, blobs, pincode):
        """Heuristic for Indian Aadhaar Address extraction"""
        # Added SIO/S.O. as common OCR misinterpretations of S/O
        keywords = ["S/O", "SIO", "D/O", "W/O", "ADDRESS", "C/O", "S.O.", "SON OF"]
        start_idx = -1
        
        # Clean blobs to remove single character noise
        clean_blobs = [b for b in blobs if len(b) > 2]

        for i, blob in enumerate(clean_blobs):
            upper_blob = blob.upper()
            if any(k in upper_blob for k in keywords):
                start_idx = i
                break
        
        if start_idx != -1:
            addr_parts = []
            # We skip the very first blob (which contains S/O: Name) to keep the address clean
            # as requested by the user.
            for j in range(start_idx + 1, min(start_idx + 8, len(clean_blobs))):
                blob = clean_blobs[j]
                if pincode in blob:
                    # Capture the text BEFORE the pincode if any
                    last_part = blob.split(pincode)[0].strip(", ")
                    if last_part: addr_parts.append(last_part)
                    break
                addr_parts.append(blob)
            
            return ", ".join(addr_parts)
            
        return "Address Found in Scan"

class SendOTPView(APIView):
    """
    Generates and 'sends' an OTP to the user's phone number from Registry.
    """
    def post(self, request):
        pan = request.data.get('pan')
        try:
            registry_user = IdentityRegistry.objects.get(pan=pan)
            phone = registry_user.phone
            
            # Generate 6-digit OTP
            otp = f"{random.randint(100000, 999999)}"
            
            # Save to DB
            OTPVerification.objects.create(phone=phone, otp=otp)
            
            # SIMULATED SENDING (Log to console)
            print(f"\n[MFA SERVICE] Sending OTP {otp} to {phone} for PAN {pan}\n")
            
            # Return masked phone for UI
            masked_phone = f"+91 ******{phone[-4:]}"
            return Response({"message": "OTP sent successfully", "phone": masked_phone}, status=status.HTTP_200_OK)
            
        except IdentityRegistry.DoesNotExist:
            return Response({"error": "No identity found for this PAN. Unable to send OTP."}, status=status.HTTP_404_NOT_FOUND)

class VerifyOTPView(APIView):
    """
    Verifies the OTP provided by the user.
    """
    def post(self, request):
        phone_last_4 = request.data.get('phone_last_4') # To find the correct OTP record
        otp = request.data.get('otp')
        
        # Find the latest unverified OTP for this roughly matched phone
        otp_record = OTPVerification.objects.filter(
            phone__endswith=phone_last_4, 
            is_verified=False
        ).order_by('-created_at').first()
        
        if not otp_record:
            return Response({"error": "No pending OTP found"}, status=status.HTTP_404_NOT_FOUND)
            
        if otp_record.is_expired():
            return Response({"error": "OTP has expired. Please request a new one."}, status=status.HTTP_400_BAD_REQUEST)
            
        # UNIVERSAL TEST OTP (Bypass for development)
        if otp == '123456':
            otp_record.is_verified = True
            otp_record.save()
            return Response({"message": "Identity Verified (Test Mode) ✅"}, status=status.HTTP_200_OK)

        if otp_record.otp == otp:
            otp_record.is_verified = True
            otp_record.save()
            return Response({"message": "Identity Verified ✅"}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Invalid OTP. Please try again."}, status=status.HTTP_400_BAD_REQUEST)

class FaceMatchView(APIView):
    """
    Simulates AI Face Matching between VKYC frame and Aadhaar photo.
    """
    def post(self, request):
        # In production, we would receive an image file here
        # and compare it using face_recognition or Rekognition.
        return Response({
            "match_score": 0.98,
            "status": "MATCHED",
            "message": "Face matching successful. Identity confirmed."
        }, status=status.HTTP_200_OK)

class GenerateAgreementView(APIView):
    """
    Generates and returns a PDF loan agreement for a specific application.
    """
    def get(self, request, pk):
        try:
            loan = LoanApplication.objects.select_related('applicant').get(pk=pk)
            
            # Generate PDF using service
            pdf_buffer = ContractService.generate_agreement_pdf(loan)
            
            # Return as File Response
            response = HttpResponse(pdf_buffer, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="Loan_Agreement_{pk}.pdf"'
            return response
            
        except LoanApplication.DoesNotExist:
            return Response({"error": "Loan application not found"}, status=status.HTTP_404_NOT_FOUND)

class AdminDisburseView(APIView):
    """
    Enables bank managers to release funds to the applicant's account.
    """
    def post(self, request, pk):
        try:
            loan = LoanApplication.objects.select_related('applicant').get(pk=pk)
            
            if loan.status != 'APPROVED':
                return Response({"error": f"Loan must be APPROVED before disbursement. Current status: {loan.status}"}, status=status.HTTP_400_BAD_REQUEST)
                
            # Disburse funds
            try:
                txn_id = DisbursementService.disburse_funds(loan)
                
                # Send advice
                NotificationService.send_email(loan.applicant.pan + "@example.com", "Funds Disbursed! ✅", f"Amount INR {loan.amount:,.2f} has been released to your account {loan.account_no}. TXN ID: {txn_id}")
                
                return Response({
                    "message": "Funds disbursed successfully",
                    "transaction_id": txn_id,
                    "disbursed_at": loan.disbursed_at
                }, status=status.HTTP_200_OK)
            except ValueError as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
                
        except LoanApplication.DoesNotExist:
            return Response({"error": "Loan application not found"}, status=status.HTTP_404_NOT_FOUND)
