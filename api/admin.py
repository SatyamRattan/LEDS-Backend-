from django.contrib import admin
from .models import Applicant, LoanApplication, IdentityRegistry

@admin.register(IdentityRegistry)
class IdentityRegistryAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'pan', 'aadhaar', 'monthly_income', 'credit_score')
    search_fields = ('pan', 'aadhaar', 'full_name')

@admin.register(Applicant)
class ApplicantAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'pan', 'phone')

@admin.register(LoanApplication)
class LoanApplicationAdmin(admin.ModelAdmin):
    list_display = ('applicant', 'amount', 'status', 'cibil_score')
    list_filter = ('status',)
