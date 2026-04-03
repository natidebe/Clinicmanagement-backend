from rest_framework import serializers
from .models import Patient, Visit, Consultation


class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = ['id', 'clinic_id', 'full_name', 'gender', 'date_of_birth', 'phone', 'created_at']
        read_only_fields = ['id', 'clinic_id', 'created_at']


class VisitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Visit
        fields = ['id', 'clinic_id', 'patient_id', 'created_by', 'assigned_doctor_id', 'status', 'created_at']
        read_only_fields = ['id', 'clinic_id', 'created_by', 'created_at']


class ConsultationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Consultation
        fields = ['id', 'visit_id', 'doctor_id', 'symptoms', 'diagnosis', 'notes', 'created_at']
        read_only_fields = ['id', 'doctor_id', 'created_at']
