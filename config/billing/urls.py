from django.urls import path
from .views import (
    InvoiceListView,
    InvoiceDetailView,
    InvoiceLineItemsView,
    InvoiceLineItemDetailView,
    InvoiceFinalizeView,
    InvoiceVoidView,
)

urlpatterns = [
    path('invoices/',                                   InvoiceListView.as_view(),           name='invoice-list'),
    path('invoices/<uuid:invoice_id>/',                 InvoiceDetailView.as_view(),         name='invoice-detail'),
    path('invoices/<uuid:invoice_id>/items/',           InvoiceLineItemsView.as_view(),      name='invoice-items'),
    path('invoices/<uuid:invoice_id>/items/<uuid:item_id>/', InvoiceLineItemDetailView.as_view(), name='invoice-item-detail'),
    path('invoices/<uuid:invoice_id>/finalize/',        InvoiceFinalizeView.as_view(),       name='invoice-finalize'),
    path('invoices/<uuid:invoice_id>/void/',            InvoiceVoidView.as_view(),           name='invoice-void'),
]
