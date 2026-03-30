import csv

from django.contrib import admin
from django.http import HttpResponse

from .models import BookCopy, Bookinventory, HoldRequest, LibraryProfile, Loan, Log


def export_as_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{queryset.model._meta.model_name}.csv"'
    writer = csv.writer(response)
    writer.writerow([field.name for field in queryset.model._meta.fields])
    for instance in queryset:
        writer.writerow([getattr(instance, field.name) for field in queryset.model._meta.fields])
    return response


export_as_csv.short_description = "Export selected rows as CSV"


class ExportCsvAdmin(admin.ModelAdmin):
    actions = [export_as_csv]


@admin.register(Bookinventory)
class BookInventoryAdmin(ExportCsvAdmin):
    list_display = (
        "title",
        "author",
        "isbn",
        "genre",
        "audience",
        "quantity",
        "available_quantity",
    )
    list_filter = ("genre", "audience", "language", "publisher")
    search_fields = ("title", "author", "isbn", "publisher", "description", "summary")


@admin.register(BookCopy)
class BookCopyAdmin(ExportCsvAdmin):
    list_display = ("barcode", "inventory", "status", "due_back_date", "last_circulated_at")
    list_filter = ("status",)
    search_fields = ("barcode", "inventory__title", "inventory__isbn")


@admin.register(Loan)
class LoanAdmin(ExportCsvAdmin):
    list_display = ("inventory", "copy", "borrower", "borrower_email_snapshot", "status", "due_at")
    list_filter = ("status",)
    search_fields = ("inventory__title", "borrower__username", "borrower_email_snapshot", "copy__barcode")


@admin.register(HoldRequest)
class HoldRequestAdmin(ExportCsvAdmin):
    list_display = ("inventory", "requester", "status", "requested_at", "expires_at")
    list_filter = ("status",)
    search_fields = ("inventory__title", "requester__username")


@admin.register(LibraryProfile)
class LibraryProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "card_number", "max_active_loans", "is_email_verified")
    list_filter = ("role", "is_email_verified")
    search_fields = ("user__username", "user__email", "card_number")


@admin.register(Log)
class LogAdmin(ExportCsvAdmin):
    list_display = ("title", "borrower_email", "borrowed_date", "returned_date")
    search_fields = ("title", "isbn", "borrower_email")
