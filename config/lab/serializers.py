from rest_framework import serializers
from .models import LabTest, TestOrder, TestResult, TEST_ORDER_STATUS_CHOICES


class LabTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabTest
        fields = ['id', 'clinic_id', 'name', 'description', 'price', 'is_active', 'created_by', 'created_at']
        read_only_fields = ['id', 'clinic_id', 'created_by', 'created_at']


class TestOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestOrder
        fields = [
            'id', 'visit_id', 'consultation_id', 'test_id', 'ordered_by',
            'assigned_to', 'status', 'is_billable', 'price_at_order_time',
            'billed_invoice_id', 'created_at',
        ]
        read_only_fields = ['id', 'ordered_by', 'price_at_order_time', 'billed_invoice_id', 'created_at']


class TestOrderUpdateSerializer(serializers.Serializer):
    status      = serializers.ChoiceField(choices=TEST_ORDER_STATUS_CHOICES, required=False)
    assigned_to = serializers.UUIDField(required=False)
    is_billable = serializers.BooleanField(required=False)


class TestResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestResult
        fields = ['id', 'test_order_id', 'technician_id', 'result_data', 'remarks', 'created_at']
        read_only_fields = ['id', 'technician_id', 'created_at']
