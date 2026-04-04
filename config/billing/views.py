import uuid

from django.db import transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Invoice, InvoiceLineItem
from .serializers import (
    InvoiceSerializer,
    CreateInvoiceSerializer,
    AddLineItemSerializer,
    FinalizeInvoiceSerializer,
    VoidInvoiceSerializer,
)
from clinic.models import Visit
from lab.models import LabTest, TestOrder
from users.permissions import HasPermission
from core.querysets import PaginatedListMixin
from audit.mixins import AuditLogMixin


def _parse_uuid(value, field_name):
    try:
        return uuid.UUID(str(value)), None
    except (ValueError, AttributeError):
        return None, Response(
            {field_name: 'Must be a valid UUID.'},
            status=status.HTTP_400_BAD_REQUEST,
        )


def _recompute_invoice_totals(invoice, discount_amount=None):
    """Recompute subtotal and total_amount from current line items. Save in place."""
    subtotal = (
        InvoiceLineItem.objects.filter(invoice_id=invoice.id)
        .aggregate(total=Sum('subtotal'))['total'] or 0
    )
    if discount_amount is None:
        discount_amount = invoice.discount_amount
    total = max(subtotal - discount_amount, 0)
    invoice.subtotal = subtotal
    invoice.discount_amount = discount_amount
    invoice.total_amount = total
    invoice.save(update_fields=['subtotal', 'discount_amount', 'total_amount'])


class InvoiceListView(AuditLogMixin, PaginatedListMixin, APIView):
    """
    GET  /api/billing/invoices/   — all authenticated staff, scoped to clinic
                                     ?visit_id=  ?status=  ?patient_id=
    POST /api/billing/invoices/   — receptionist, admin
    """

    def get_permissions(self):
        if self.request.method == 'POST':
            return [HasPermission.for_permission('manage_billing')()]
        return super().get_permissions()

    def get(self, request):
        qs = Invoice.objects.for_clinic(request.user.clinic_id)
        visit_id   = request.query_params.get('visit_id')
        patient_id = request.query_params.get('patient_id')
        status_f   = request.query_params.get('status')
        if visit_id:
            qs = qs.filter(visit_id=visit_id)
        if patient_id:
            qs = qs.filter(patient_id=patient_id)
        if status_f:
            qs = qs.filter(status=status_f)
        return self.paginate(qs, InvoiceSerializer, request)

    def post(self, request):
        serializer = CreateInvoiceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        visit_id_parsed, err = _parse_uuid(data['visit_id'], 'visit_id')
        if err:
            return err

        visit = get_object_or_404(
            Visit.objects.for_clinic(request.user.clinic_id), id=visit_id_parsed
        )

        invoice = Invoice.objects.create(
            clinic_id=request.user.clinic_id,
            visit_id=visit.id,
            patient_id=visit.patient_id,
            issued_by=request.user.id,
            notes=data.get('notes', ''),
        )
        self.log_action(request, 'create', 'invoice', invoice.id)
        return Response(InvoiceSerializer(invoice).data, status=status.HTTP_201_CREATED)


class InvoiceDetailView(APIView):
    """GET /api/billing/invoices/<id>/  — all authenticated staff"""

    def _get_invoice(self, request, invoice_id):
        return get_object_or_404(
            Invoice.objects.for_clinic(request.user.clinic_id), id=invoice_id
        )

    def get(self, request, invoice_id):
        return Response(InvoiceSerializer(self._get_invoice(request, invoice_id)).data)


class InvoiceLineItemsView(AuditLogMixin, APIView):
    """
    POST   /api/billing/invoices/<id>/items/   — add line item to draft (receptionist, admin)
    """
    permission_classes = [HasPermission.for_permission('manage_billing')]

    def _get_draft_invoice(self, request, invoice_id):
        invoice = get_object_or_404(
            Invoice.objects.for_clinic(request.user.clinic_id), id=invoice_id
        )
        if invoice.status != 'draft':
            return invoice, Response(
                {'detail': 'Line items can only be modified on draft invoices.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return invoice, None

    def post(self, request, invoice_id):
        invoice, err = self._get_draft_invoice(request, invoice_id)
        if err:
            return err

        serializer = AddLineItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        test_order_id = data.get('test_order_id')

        if test_order_id:
            # Validate the test order belongs to this clinic
            visit_ids = Visit.objects.for_clinic(request.user.clinic_id).values_list('id', flat=True)
            test_order = get_object_or_404(TestOrder, id=test_order_id, visit_id__in=visit_ids)

            if not test_order.is_billable:
                return Response(
                    {'detail': 'This test order is marked as non-billable.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if test_order.status == 'canceled':
                return Response(
                    {'detail': 'Cannot bill a canceled test order.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if test_order.billed_invoice_id is not None:
                return Response(
                    {'detail': 'This test order has already been billed on another invoice.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if InvoiceLineItem.objects.filter(
                invoice_id=invoice.id, test_order_id=test_order_id
            ).exists():
                return Response(
                    {'detail': 'This test order is already on this invoice.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Resolve snapshot values from the order (never from live lab_test.price)
            lab_test = get_object_or_404(
                LabTest.objects.for_clinic(request.user.clinic_id), id=test_order.test_id
            )
            test_name  = lab_test.name
            unit_price = test_order.price_at_order_time
        else:
            # Ad-hoc line item (consultation fee, admin charge, etc.)
            test_name  = data['test_name']
            unit_price = data['unit_price']
            test_order_id = None

        quantity = data.get('quantity', 1)
        subtotal = unit_price * quantity

        with transaction.atomic():
            line_item = InvoiceLineItem.objects.create(
                invoice_id=invoice.id,
                test_order_id=test_order_id,
                test_name=test_name,
                unit_price=unit_price,
                quantity=quantity,
                subtotal=subtotal,
                notes=data.get('notes', ''),
            )
            _recompute_invoice_totals(invoice)

        self.log_action(request, 'update', 'invoice', invoice.id)
        from .serializers import InvoiceLineItemSerializer
        return Response(InvoiceLineItemSerializer(line_item).data, status=status.HTTP_201_CREATED)


class InvoiceLineItemDetailView(AuditLogMixin, APIView):
    """
    DELETE /api/billing/invoices/<id>/items/<item_id>/  — remove line item from draft
    """
    permission_classes = [HasPermission.for_permission('manage_billing')]

    def delete(self, request, invoice_id, item_id):
        invoice = get_object_or_404(
            Invoice.objects.for_clinic(request.user.clinic_id), id=invoice_id
        )
        if invoice.status != 'draft':
            return Response(
                {'detail': 'Line items can only be modified on draft invoices.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        line_item = get_object_or_404(InvoiceLineItem, id=item_id, invoice_id=invoice.id)

        with transaction.atomic():
            line_item.delete()
            _recompute_invoice_totals(invoice)

        self.log_action(request, 'update', 'invoice', invoice.id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class InvoiceFinalizeView(AuditLogMixin, APIView):
    """
    POST /api/billing/invoices/<id>/finalize/  — lock invoice and stamp test orders
    """
    permission_classes = [HasPermission.for_permission('manage_billing')]

    def post(self, request, invoice_id):
        invoice = get_object_or_404(
            Invoice.objects.for_clinic(request.user.clinic_id), id=invoice_id
        )

        if invoice.status != 'draft':
            return Response(
                {'detail': 'Only draft invoices can be finalized.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        line_items = list(InvoiceLineItem.objects.filter(invoice_id=invoice.id))
        if not line_items:
            return Response(
                {'detail': 'Invoice must have at least one line item before finalization.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = FinalizeInvoiceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        discount = data.get('discount_amount', 0)

        # Guard: no test order already billed on a different invoice
        order_ids = [li.test_order_id for li in line_items if li.test_order_id]
        if order_ids:
            conflicting = list(
                TestOrder.objects.filter(id__in=order_ids)
                .exclude(billed_invoice_id__isnull=True)
                .values_list('id', flat=True)
            )
            if conflicting:
                return Response(
                    {
                        'detail': 'One or more test orders are already billed on another invoice.',
                        'conflicting_orders': [str(oid) for oid in conflicting],
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        subtotal     = sum(li.subtotal for li in line_items)
        total_amount = max(subtotal - discount, 0)

        with transaction.atomic():
            invoice.status          = 'finalized'
            invoice.subtotal        = subtotal
            invoice.discount_amount = discount
            invoice.total_amount    = total_amount
            invoice.finalized_by    = request.user.id
            invoice.finalized_at    = timezone.now()
            if data.get('notes'):
                invoice.notes = data['notes']
            invoice.save()

            # Stamp every billed test order so they can't be double-billed
            if order_ids:
                TestOrder.objects.filter(id__in=order_ids).update(
                    billed_invoice_id=invoice.id
                )

        self.log_action(request, 'update', 'invoice', invoice.id)
        return Response(InvoiceSerializer(invoice).data)


class InvoiceVoidView(AuditLogMixin, APIView):
    """
    POST /api/billing/invoices/<id>/void/  — void a finalized invoice (admin only)
    Releases all stamped test orders so they can be re-billed.
    """
    permission_classes = [HasPermission.for_permission('void_invoice')]

    def post(self, request, invoice_id):
        invoice = get_object_or_404(
            Invoice.objects.for_clinic(request.user.clinic_id), id=invoice_id
        )

        if invoice.status != 'finalized':
            return Response(
                {'detail': 'Only finalized invoices can be voided.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = VoidInvoiceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order_ids = list(
            InvoiceLineItem.objects.filter(invoice_id=invoice.id)
            .exclude(test_order_id__isnull=True)
            .values_list('test_order_id', flat=True)
        )

        with transaction.atomic():
            # Release test orders so they can be re-billed on a new invoice
            if order_ids:
                TestOrder.objects.filter(
                    id__in=order_ids, billed_invoice_id=invoice.id
                ).update(billed_invoice_id=None)

            invoice.status      = 'void'
            invoice.voided_by   = request.user.id
            invoice.voided_at   = timezone.now()
            invoice.void_reason = serializer.validated_data['void_reason']
            invoice.save()

        self.log_action(request, 'update', 'invoice', invoice.id)
        return Response(InvoiceSerializer(invoice).data)
