from django.urls import path
from .views import VerifyPanView, VerifyAadhaarView, LoanApplicationView, CheckCibilView

urlpatterns = [
    path('verify-pan/', VerifyPanView.as_view(), name='verify-pan'),
    path('verify-aadhaar/', VerifyAadhaarView.as_view(), name='verify-aadhaar'),
    path('check-cibil/', CheckCibilView.as_view(), name='check-cibil'),
    path('apply-loan/', LoanApplicationView.as_view(), name='apply-loan'),
]
