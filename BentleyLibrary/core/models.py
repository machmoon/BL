from django.db import models

class Bookinventory(models.Model):
    title = models.CharField(max_length=255, db_collation='utf8mb3_unicode_ci')
    author = models.CharField(max_length=255, db_collation='utf8mb3_unicode_ci')
    isbn = models.CharField(max_length=13)
    published_date = models.DateField()
    publisher = models.CharField(max_length=255)
    quantity = models.IntegerField()
    available_quantity = models.IntegerField()
    description = models.TextField(blank=True, null=True)
    image_url = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'bookinventory'

    def __str__(self):
        return self.title

class Log(models.Model):
    book = models.ForeignKey(Bookinventory, on_delete=models.CASCADE)
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
        managed = False
        db_table = 'log'
        
    def __str__(self):
        return self.title