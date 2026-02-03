"""
Test models for unit testing.
These models are managed by Django and can be used in tests.
"""
from django.db import models


class TestBookinventory(models.Model):
    """Test version of Bookinventory model that Django can manage."""
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    isbn = models.CharField(max_length=13, unique=True)
    published_date = models.DateField()
    publisher = models.CharField(max_length=255)
    quantity = models.IntegerField()
    available_quantity = models.IntegerField()
    description = models.TextField(blank=True, null=True)
    image_url = models.CharField(max_length=255)

    class Meta:
        db_table = 'test_bookinventory'

    def __str__(self):
        return self.title


class TestLog(models.Model):
    """Test version of Log model that Django can manage."""
    book = models.ForeignKey(TestBookinventory, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    publisher = models.CharField(max_length=255)
    publication_date = models.DateField()
    isbn = models.CharField(max_length=13)
    borrower_first_name = models.CharField(max_length=255)
    borrower_last_name = models.CharField(max_length=255)
    borrower_email = models.CharField(max_length=255)
    borrowed_date = models.DateField()
    borrowed_time = models.TimeField()
    returned_date = models.DateField(blank=True, null=True)
    returned_time = models.TimeField(blank=True, null=True)

    class Meta:
        db_table = 'test_log'

    def __str__(self):
        return self.title

