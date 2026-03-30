from django.conf import settings
from django.db import models
from django.utils import timezone


class LibraryRole(models.TextChoices):
    PATRON = "patron", "Patron"
    LIBRARIAN = "librarian", "Librarian"
    CURATOR = "curator", "Curator"
    ADMIN = "admin", "Admin"


class CopyStatus(models.TextChoices):
    AVAILABLE = "available", "Available"
    ON_LOAN = "on_loan", "On Loan"
    ON_HOLD = "on_hold", "On Hold"
    MAINTENANCE = "maintenance", "Maintenance"
    LOST = "lost", "Lost"


class LoanStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    RETURNED = "returned", "Returned"
    OVERDUE = "overdue", "Overdue"


class HoldStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    READY = "ready", "Ready for Pickup"
    FULFILLED = "fulfilled", "Fulfilled"
    CANCELLED = "cancelled", "Cancelled"
    EXPIRED = "expired", "Expired"


class Bookinventory(models.Model):
    title = models.CharField(max_length=255, db_index=True)
    subtitle = models.CharField(max_length=255, blank=True, default="")
    author = models.CharField(max_length=255, db_index=True)
    isbn = models.CharField(max_length=13, db_index=True)
    published_date = models.DateField(db_index=True)
    publisher = models.CharField(max_length=255, db_index=True)
    genre = models.CharField(max_length=120, blank=True, default="", db_index=True)
    language = models.CharField(max_length=64, blank=True, default="English", db_index=True)
    audience = models.CharField(max_length=64, blank=True, default="General", db_index=True)
    shelf_location = models.CharField(max_length=64, blank=True, default="", db_index=True)
    quantity = models.PositiveIntegerField()
    available_quantity = models.PositiveIntegerField(db_index=True)
    description = models.TextField(blank=True, default="")
    summary = models.TextField(blank=True, default="")
    image_url = models.URLField(max_length=500, blank=True, default="")
    metadata = models.JSONField(blank=True, default=dict)
    search_document = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "bookinventory"
        indexes = [
            models.Index(fields=["title"], name="book_title_idx"),
            models.Index(fields=["author"], name="book_author_idx"),
            models.Index(fields=["publisher"], name="book_publisher_idx"),
            models.Index(fields=["isbn"], name="book_isbn_idx"),
            models.Index(fields=["published_date"], name="book_pubdate_idx"),
            models.Index(fields=["available_quantity"], name="book_available_idx"),
            models.Index(fields=["genre", "audience"], name="book_genre_aud_idx"),
        ]

    def __str__(self):
        return self.title

    def build_search_document(self):
        parts = [
            self.title,
            self.subtitle,
            self.author,
            self.publisher,
            self.isbn,
            self.genre,
            self.language,
            self.audience,
            self.description,
            self.summary,
            self.metadata.get("subjects", "") if isinstance(self.metadata, dict) else "",
        ]
        return " ".join(str(part).strip() for part in parts if part).strip()

    def save(self, *args, **kwargs):
        self.search_document = self.build_search_document()
        super().save(*args, **kwargs)

    @property
    def active_loan_count(self):
        return self.loans.filter(status__in=[LoanStatus.ACTIVE, LoanStatus.OVERDUE]).count()


class LibraryProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="library_profile",
    )
    role = models.CharField(
        max_length=32,
        choices=LibraryRole.choices,
        default=LibraryRole.PATRON,
        db_index=True,
    )
    card_number = models.CharField(max_length=32, unique=True)
    department = models.CharField(max_length=120, blank=True, default="")
    max_active_loans = models.PositiveIntegerField(default=5)
    is_email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["user__username"]

    def __str__(self):
        return f"{self.user.username} ({self.role})"


class BookCopy(models.Model):
    inventory = models.ForeignKey(
        Bookinventory,
        on_delete=models.CASCADE,
        related_name="copies",
    )
    barcode = models.CharField(max_length=64, unique=True)
    status = models.CharField(
        max_length=32,
        choices=CopyStatus.choices,
        default=CopyStatus.AVAILABLE,
        db_index=True,
    )
    acquisition_date = models.DateField(default=timezone.now)
    condition_notes = models.TextField(blank=True, default="")
    due_back_date = models.DateField(blank=True, null=True, db_index=True)
    last_circulated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["barcode"]
        indexes = [
            models.Index(fields=["inventory", "status"], name="copy_inventory_status_idx"),
            models.Index(fields=["status", "due_back_date"], name="copy_status_due_idx"),
        ]
        permissions = [
            ("manage_inventory", "Can manage inventory and copies"),
        ]

    def __str__(self):
        return self.barcode


class Loan(models.Model):
    inventory = models.ForeignKey(
        Bookinventory,
        on_delete=models.CASCADE,
        related_name="loans",
    )
    copy = models.ForeignKey(
        BookCopy,
        on_delete=models.CASCADE,
        related_name="loans",
    )
    borrower = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="loans",
        blank=True,
        null=True,
    )
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="processed_loans",
        blank=True,
        null=True,
    )
    borrower_email_snapshot = models.EmailField(max_length=255)
    checked_out_at = models.DateTimeField(default=timezone.now, db_index=True)
    due_at = models.DateTimeField(db_index=True)
    returned_at = models.DateTimeField(blank=True, null=True, db_index=True)
    status = models.CharField(
        max_length=32,
        choices=LoanStatus.choices,
        default=LoanStatus.ACTIVE,
        db_index=True,
    )

    class Meta:
        ordering = ["-checked_out_at"]
        indexes = [
            models.Index(fields=["inventory", "status"], name="loan_inventory_status_idx"),
            models.Index(fields=["borrower", "status"], name="loan_borrower_status_idx"),
            models.Index(fields=["due_at", "status"], name="loan_due_status_idx"),
        ]
        permissions = [
            ("manage_loans", "Can check books in and out"),
        ]

    def __str__(self):
        borrower = self.borrower.username if self.borrower else self.borrower_email_snapshot
        return f"{self.inventory.title} -> {borrower}"


class HoldRequest(models.Model):
    inventory = models.ForeignKey(
        Bookinventory,
        on_delete=models.CASCADE,
        related_name="holds",
    )
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="hold_requests",
    )
    status = models.CharField(
        max_length=32,
        choices=HoldStatus.choices,
        default=HoldStatus.PENDING,
        db_index=True,
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(blank=True, null=True, db_index=True)
    fulfilled_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["requested_at"]
        indexes = [
            models.Index(fields=["inventory", "status"], name="hold_inventory_status_idx"),
            models.Index(fields=["requester", "status"], name="hold_requester_status_idx"),
        ]
        permissions = [
            ("approve_holds", "Can approve and fulfill holds"),
        ]

    def __str__(self):
        return f"{self.requester.username} waiting for {self.inventory.title}"


class Log(models.Model):
    book = models.ForeignKey(
        Bookinventory,
        on_delete=models.CASCADE,
        related_name="logs",
        blank=True,
        null=True,
    )
    loan = models.ForeignKey(
        Loan,
        on_delete=models.SET_NULL,
        related_name="legacy_logs",
        blank=True,
        null=True,
    )
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    publisher = models.CharField(max_length=255)
    publication_date = models.DateField()
    isbn = models.CharField(max_length=13, db_index=True)
    borrower_first_name = models.CharField(max_length=255)
    borrower_last_name = models.CharField(max_length=255)
    borrower_email = models.EmailField(max_length=255, db_index=True)
    borrowed_date = models.DateField(db_index=True)
    borrowed_time = models.TimeField()
    returned_date = models.DateField(blank=True, null=True, db_index=True)
    returned_time = models.TimeField(blank=True, null=True)

    class Meta:
        db_table = "log"
        indexes = [
            models.Index(fields=["isbn", "returned_date"], name="log_isbn_returned_idx"),
            models.Index(fields=["borrower_email", "borrowed_date"], name="log_borrower_date_idx"),
        ]

    def __str__(self):
        return f"{self.title} ({self.borrower_email})"


class ProductEvent(models.Model):
    event_type = models.CharField(max_length=64, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="product_events",
        blank=True,
        null=True,
    )
    role = models.CharField(max_length=32, blank=True, default="", db_index=True)
    query_text = models.CharField(max_length=255, blank=True, default="")
    book_id = models.PositiveIntegerField(blank=True, null=True, db_index=True)
    reading_goal = models.CharField(max_length=32, blank=True, default="")
    metadata = models.JSONField(blank=True, default=dict)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["event_type", "created_at"], name="event_type_created_idx"),
            models.Index(fields=["role", "created_at"], name="event_role_created_idx"),
        ]

    def __str__(self):
        return f"{self.event_type} @ {self.created_at.isoformat()}"
