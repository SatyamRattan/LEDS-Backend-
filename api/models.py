from django.db import models
import random

class IdentityRegistry(models.Model):
    """
    Simulation of External NSDL/UIDAI/Credit Bureau Database.
    Admin can add 'Real' users here to be 'fetched' and 'checked' by the system.
    """
    pan = models.CharField(max_length=10, unique=True)
    aadhaar = models.CharField(max_length=12, unique=True)
    full_name = models.CharField(max_length=255)
    dob = models.DateField()
    phone = models.CharField(max_length=15)
    address = models.TextField()
    pincode = models.CharField(max_length=6)
    
    monthly_income = models.DecimalField(max_digits=12, decimal_places=2, default=50000)
    credit_score = models.IntegerField(default=750)

    def __str__(self):
        return f"REGISTRY: {self.full_name} ({self.pan})"

class Applicant(models.Model):
    pan = models.CharField(max_length=10, unique=True)
    aadhaar = models.CharField(max_length=12, unique=True)
    full_name = models.CharField(max_length=255)
    dob = models.DateField()
    phone = models.CharField(max_length=15)
    address = models.TextField()
    pincode = models.CharField(max_length=6)

    def __str__(self):
        return f"{self.full_name} ({self.pan})"

class LoanApplication(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('REVIEW', 'Manual Review'),
    ]

    applicant = models.ForeignKey(Applicant, on_delete=models.CASCADE, related_name='loans')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    tenure = models.IntegerField(help_text="Tenure in months")
    purpose = models.TextField()
    
    cibil_score = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    account_no = models.CharField(max_length=20, null=True, blank=True)
    ifsc = models.CharField(max_length=11, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Loan {self.id} - {self.applicant.full_name} ({self.status})"
