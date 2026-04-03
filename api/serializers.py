from rest_framework import serializers
from .models import Applicant, LoanApplication

class ApplicantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Applicant
        fields = '__all__'

class LoanApplicationSerializer(serializers.ModelSerializer):
    applicant_details = ApplicantSerializer(source='applicant', read_only=True)
    
    class Meta:
        model = LoanApplication
        fields = '__all__'
