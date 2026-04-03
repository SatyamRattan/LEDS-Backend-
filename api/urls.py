from django.urls import path
from .views import (
    VerifyPanView, VerifyAadhaarView, LoanApplicationView, 
    CheckCibilView, AdminStatsView, AdminLoanListView, AdminActionView,
    DocumentOCRView, SendOTPView, VerifyOTPView, FaceMatchView,
    GenerateAgreementView, AdminDisburseView
)

urlpatterns = [
    path('verify-pan/', VerifyPanView.as_view(), name='verify-pan'),
    path('verify-aadhaar/', VerifyAadhaarView.as_view(), name='verify-aadhaar'),
    path('check-cibil/', CheckCibilView.as_view(), name='check-cibil'),
    path('apply-loan/', LoanApplicationView.as_view(), name='apply-loan'),
    
    # Admin Panel Endpoints
    path('admin/stats/', AdminStatsView.as_view(), name='admin-stats'),
    path('admin/applications/', AdminLoanListView.as_view(), name='admin-applications'),
    path('admin/action/<int:pk>/', AdminActionView.as_view(), name='admin-action'),
    path('admin/disburse/<int:pk>/', AdminDisburseView.as_view(), name='admin-disburse'),

    # Document AI / OCR
    path('ocr/', DocumentOCRView.as_view(), name='document-ocr'),

    # MFA & Security
    path('mfa/send-otp/', SendOTPView.as_view(), name='send-otp'),
    path('mfa/verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('face-match/', FaceMatchView.as_view(), name='face-match'),

    # Contract / E-Sign
    path('agreement/download/<int:pk>/', GenerateAgreementView.as_view(), name='download-agreement'),
]
