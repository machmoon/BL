from django.shortcuts import render, get_object_or_404, redirect
from .models import Bookinventory, Log
from django.db.models import Q
import datetime
from django.utils import timezone
from django.contrib import messages

def checkout(request, isbn):
    if request.method == 'POST':
        # Get data from the form
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        email = request.POST['email']
        
        # Find the book in the inventory based on the provided ISBN
        try:
            book = Bookinventory.objects.get(isbn=isbn)
        except Bookinventory.DoesNotExist:
            return render(request, 'checkout.html', {'error_message': 'Book not found in inventory.'})
        
        # Check if there are available copies
        if book.available_quantity <= 0:
            return render(request, 'checkout.html', {'error_message': 'No copies available to check out.'})
        
        # Create a log entry
        log_entry = Log(
            book=book,
            title=book.title,
            author=book.author,
            publisher=book.publisher,
            publication_date=book.published_date,
            isbn=book.isbn,
            borrower_first_name=first_name,
            borrower_last_name=last_name,
            borrower_email=email,
            borrowed_date=timezone.now().date(),
            borrowed_time=timezone.now().time()
        )
        log_entry.save()
        
        # Update the book's available quantity
        book.available_quantity -= 1
        book.save()
        
        # Set a success message
        messages.success(request, 'Thanks for checking out the book.')

        # Redirect to the home page
        return redirect('index')  # Assuming 'index' is the name of your home page URL pattern

    return render(request, 'checkout.html')

def checkin(request):
    if request.method == 'POST':
        isbn = request.POST['isbn']
        
        try:
            book = Bookinventory.objects.get(isbn=isbn)
        except Bookinventory.DoesNotExist:
            return render(request, 'checkin.html', {'error_message': 'Book not found in inventory.'})
        
        # Check if the book is already checked in
        if book.available_quantity >= book.quantity:
            return render(request, 'checkin.html', {'error_message': 'This book is not checked out.'})
        
        # Find the most recent log entry for the book and mark it as returned
        try:
            log_entry = Log.objects.filter(isbn=isbn).latest('borrowed_date', 'borrowed_time')
        except Log.DoesNotExist:
            return render(request, 'checkin.html', {'error_message': 'No check-out record found for this book.'})
        
        log_entry.returned_date = timezone.now().date()
        log_entry.returned_time = timezone.now().time()
        log_entry.save()
        
        # Update the book's available quantity
        book.available_quantity += 1
        book.save()
        
        messages.success(request, 'Book checked in successfully.')
        return redirect('index')  # Redirect to the check-in page

    return render(request, 'checkin.html')

from django.db.models import Q
from django.views.generic import ListView

class advanced_search_results(ListView):
    model = Bookinventory  # Specify your model here
    template_name = 'advanced_search_results.html'
    context_object_name = 'results'
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Extract search criteria from the form
        search_type = self.request.GET.get('search_type')
        field = self.request.GET.getlist('field[]')
        operator = self.request.GET.getlist('operator[]')
        search_term = self.request.GET.getlist('search_term[]')
        logical_operator = self.request.GET.getlist('logical_operator[]')
        
        # Initialize an empty Q object to build dynamic queries
        filter_query = Q()

        if search_type in ['everything', 'catalog']:
            for i in range(len(field)):
                if field[i] == 'any_field':
                    # Search all relevant fields
                    sub_query = (
                        Q(title__icontains=search_term[i]) |
                        Q(author__icontains=search_term[i]) |
                        Q(publisher__icontains=search_term[i]) |
                        Q(isbn__icontains=search_term[i]) |
                        Q(description__icontains=search_term[i])  # Include description field
                    )
                    filter_query |= sub_query
                else:
                    # Search a specific field using the selected operator
                    sub_query = Q(**{f"{field[i]}__{operator[i]}": search_term[i]})
                    filter_query |= sub_query

        # Apply logical operators
        if logical_operator:
            for i in range(len(logical_operator)):
                if logical_operator[i] == 'AND':
                    filter_query &= Q()  # Apply AND logical operator
                elif logical_operator[i] == 'OR':
                    filter_query |= Q()  # Apply OR logical operator
                elif logical_operator[i] == 'NOT':
                    filter_query &= ~Q()  # Apply NOT logical operator

        # Get published date filters
        published_date_start_filter = self.request.GET.get('published_date_start', '')
        published_date_end_filter = self.request.GET.get('published_date_end', '')

        # Apply published date filters
        if published_date_start_filter:
            filter_query &= Q(published_date__gte=published_date_start_filter)

        if published_date_end_filter:
            filter_query &= Q(published_date__lte=published_date_end_filter)

        # Check if any search parameters are provided
        if any([search_type, field, operator, search_term, logical_operator, published_date_start_filter, published_date_end_filter]):
            # Apply the final filter_query to the queryset
            queryset = queryset.filter(filter_query)
        else:
            # No search parameters provided, return an empty queryset
            queryset = queryset.none()

        return queryset

from django.db.models import Q
from datetime import datetime
from django.shortcuts import render
from .models import Bookinventory

def advanced_search(request):
    # Get search query from the form
    query = request.GET.get('q', '')

    # Start with an empty filter query
    filter_query = Q()

    if query:
        # Apply search query to title, publisher, author, description, and ISBN
        filter_query |= (Q(title__icontains=query) |
                         Q(publisher__icontains=query) |
                         Q(author__icontains=query) |
                         Q(description__icontains=query) |
                         Q(isbn__icontains=query))

    # Get the selected search type (e.g., "everything," "catalog," etc.)
    search_type = request.GET.get('search_type', 'everything')

    if search_type == 'everything':
        # Apply advanced search parameters for "Everything" search
        title = request.GET.get('title', '')
        author = request.GET.get('author', '')
        publisher = request.GET.get('publisher', '')
        isbn = request.GET.get('ISBN', '')

        if title:
            filter_query &= Q(title__icontains=title)

        if author:
            filter_query &= Q(author__icontains=author)

        if publisher:
            filter_query &= Q(publisher__icontains=publisher)

        if isbn:
            filter_query &= Q(isbn__icontains=isbn)

    # Get published date filters
    published_date_start_filter = request.GET.get('published_date_start', '')
    published_date_end_filter = request.GET.get('published_date_end', '')

    # Apply published date filters
    if published_date_start_filter:
        filter_query &= Q(published_date__gte=published_date_start_filter)

    if published_date_end_filter:
        filter_query &= Q(published_date__lte=published_date_end_filter)

    # ... Additional logic for other advanced search parameters ...

    # Filter the results based on the combined query
    results = Bookinventory.objects.filter(filter_query)

    # ... Additional logic for filtering by other advanced search parameters ...

    # Prepare the context for rendering the results
    context = {
        'results': results,
        'query': query,
        'search_type': search_type,
        'start_day': start_day,
        'start_month': start_month,
        'start_year': start_year,
        'end_day': end_day,
        'end_month': end_month,
        'end_year': end_year,
        'author': author,
        'publisher': publisher,
        'isbn': isbn,
    }

    return render(request, 'advanced_search_results.html', context)


def resource_view(request):

    return render(request, 'resource.html')

def search_results(request):
    # Get search query from the form
    query = request.GET.get('q', '')

    # Start with an empty filter query
    filter_query = Q()

    if query:
        # Apply search query to title, publisher, author, description, and ISBN
        filter_query |= (Q(title__icontains=query) |
                         Q(publisher__icontains=query) |
                         Q(author__icontains=query) |
                         Q(description__icontains=query) |
                         Q(isbn__icontains=query))

    # Get published date filters
    published_date_start_filter = request.GET.get('published_date_start', '')
    published_date_end_filter = request.GET.get('published_date_end', '')

    # Apply published date filters
    if published_date_start_filter:
        filter_query &= Q(published_date__gte=published_date_start_filter)

    if published_date_end_filter:
        filter_query &= Q(published_date__lte=published_date_end_filter)

    # Get available quantity filter
    available_quantity_filter = request.GET.get('available_quantity', '')

    # Apply available quantity filter
    if available_quantity_filter:
        filter_query &= Q(available_quantity=available_quantity_filter)

    # ... Additional logic for other advanced search parameters ...

    # Apply advanced search parameters
    title = request.GET.get('title', '')
    author = request.GET.get('author', '')
    publisher = request.GET.get('publisher', '')
    isbn = request.GET.get('ISBN', '')

    if title:
        filter_query &= Q(title__icontains=title)

    if author:
        filter_query &= Q(author__icontains=author)

    if publisher:
        filter_query &= Q(publisher__icontains=publisher)

    if isbn:
        filter_query &= Q(isbn__icontains=isbn)

    # Filter the results based on the combined query
    results = Bookinventory.objects.filter(filter_query)

    # ... Additional logic for filtering by other advanced search parameters ...

    # Get borrowed books and related data (if needed)
    book_ids = results.values_list('id', flat=True)
    borrowed_books = Log.objects.filter(book_id__in=book_ids, returned_date__isnull=True)
    borrower_emails = borrowed_books.values_list('borrower_email', flat=True)
    borrowed_book_ids = borrowed_books.values_list('book_id', flat=True)

    # Prepare the context for rendering the results
    context = {
        'results': results,
        'query': query,
        'published_date_start_filter': published_date_start_filter,
        'published_date_end_filter': published_date_end_filter,
        'available_quantity_filter': available_quantity_filter,
        'author': author,
        'publisher': publisher,
        'isbn': isbn,
        'borrowed_books': borrowed_books,
        'borrower_emails': borrower_emails,
        'borrowed_book_ids': borrowed_book_ids,
    }

    return render(request, 'search_results.html', context)

    
def book_page(request, book_id):
    book = get_object_or_404(Bookinventory, id=book_id)
    borrowed_books = Log.objects.filter(book_id=book_id, returned_date__isnull=True)
    borrower_emails = borrowed_books.values_list('borrower_email', flat=True)
    borrowed_book_ids = borrowed_books.values_list('book_id', flat=True)  # Get the borrowed book IDs

    context = {
        'book': book,
        'borrowed_books': borrowed_books,
        'borrower_emails': borrower_emails,
        'borrowed_book_ids': borrowed_book_ids
    }
    return render(request, 'book_page.html', context)

def index(request):
    # Your view logic goes here
    success_messages = messages.get_messages(request)
    return render(request, 'core/index.html', {'success_messages': success_messages})


# def checkout(request):

#     if request.method == 'POST':
#         # Retrieve form data
#         first_name = request.POST.get('first_name')
#         last_name = request.POST.get('last_name')
#         grade = request.POST.get('grade')
#     # book = get_object_or_404(Bookinventory, id=book_id)
#     # borrowed_books = Log.objects.filter(book_id=book_id, availablereturned_date__isnull=True)
#     # borrower_emails = borrowed_books.values_list('borrower_email', flat=True)
#     # borrowed_book_ids = borrowed_books.values_list('book_id', flat=True)  # Get the borrowed book IDs

#     # context = {
#     #     'book': book,
#     #     'borrowed_books': borrowed_books,
#     #     'borrower_emails': borrower_emails,
#     #     'borrowed_book_ids': borrowed_book_ids
#     # }
#     return render(request, 'checkout.html')
    
# def checkoin(request, book_id):
#     book = get_object_or_404(Bookinventory, id=book_id)
#     borrowed_books = Log.objects.filter(book_id=book_id, availablereturned_date__isnull=True)
#     borrower_emails = borrowed_books.values_list('borrower_email', flat=True)
#     borrowed_book_ids = borrowed_books.values_list('book_id', flat=True)  # Get the borrowed book IDs

#     context = {
#         'book': book,
#         'borrowed_books': borrowed_books,
#         'borrower_emails': borrower_emails,
#         'borrowed_book_ids': borrowed_book_ids
#     }
#     return render(request, 'book_page.html', context)

# def search_results(request):
    
#     books = Bookinventory.objects.all()
#     context = {
#         'books' : books
#     }
#     return render(request, 'search_results.html', context)
#     # query = request.GET.get('q')  # Update parameter name to 'q'
#     # if query:
#     #     results = BookInventory.objects.filter(
#     #         Q(title__icontains=query) |
#     #         Q(publisher__icontains=query) |
#     #         Q(author__icontains=query) |
#     #         Q(description__icontains=query)
#     #     )
#     # else:
#     #     results = []
#     # print("Query:", query)
#     # print("Results:", results)
#     # return render(request, 'search_results.html', {'results': results, 'query': query})


# def search_results(request):
#     query = request.GET.get('q', '')
#     published_date_start_filter = request.GET.get('published_date_start', '')
#     available_quantity_filter = request.GET.get('available_quantity', '')

#     # Start with all books
#     results = Bookinventory.objects.all()

#     # Apply filters
#     if query:
#         results = results.filter(
#             Q(title__icontains=query) |
#             Q(publisher__icontains=query) |
#             Q(author__icontains=query) |
#             Q(description__icontains=query) |
#             Q(isbn__icontains=query)
#         )

#     if published_date_start_filter:
#         results = results.filter(published_date__gte=published_date_start_filter)

#     if available_quantity_filter:
#         results = results.filter(available_quantity__gte=available_quantity_filter)

#     # Additional filter logic can be added here for other filters

#     # Retrieve a list of borrowed book IDs (if needed)
#     book_ids = results.values_list('id', flat=True)
#     borrowed_books = Log.objects.filter(book_id__in=book_ids, returned_date__isnull=True)
#     borrower_emails = borrowed_books.values_list('borrower_email', flat=True)
#     borrowed_book_ids = borrowed_books.values_list('book_id', flat=True)

#     context = {
#         'results': results,
#         'query': query,
#         'published_date_start_filter': published_date_start_filter,
#         'available_quantity_filter': available_quantity_filter,
#         'borrowed_books': borrowed_books,
#         'borrower_emails': borrower_emails,
#         'borrowed_book_ids': borrowed_book_ids
#     }

#     return render(request, 'search_results.html', context)

# def search_results(request):
#     query = request.GET.get('q', '')
#     published_date_start_filter = request.GET.get('published_date_start', '')
#     published_date_end_filter = request.GET.get('published_date_end', '')
#     available_quantity_filter = request.GET.get('available_quantity', '')

#     # Start with an empty filter query
#     filter_query = Q()

#     if query:
#         filter_query |= Q(title__icontains=query) | \
#                        Q(publisher__icontains=query) | \
#                        Q(author__icontains=query) | \
#                        Q(description__icontains=query) | \
#                        Q(isbn__icontains=query)

#     results = Bookinventory.objects.filter(filter_query)

#     if published_date_start_filter:
#         results = results.filter(published_date__gte=published_date_start_filter)

#     if published_date_end_filter:
#         results = results.filter(published_date__lte=published_date_end_filter)

#     if available_quantity_filter is not '':
#         results = results.filter(available_quantity=available_quantity_filter)

#     book_ids = results.values_list('id', flat=True)
#     borrowed_books = Log.objects.filter(book_id__in=book_ids, returned_date__isnull=True)
#     borrower_emails = borrowed_books.values_list('borrower_email', flat=True)
#     borrowed_book_ids = borrowed_books.values_list('book_id', flat=True)  # Get the borrowed book IDs

#     context = {
#         'results': results,
#         'query': query,
#         'published_date_start_filter': published_date_start_filter,
#         'published_date_end_filter': published_date_end_filter,
#         'available_quantity_filter': available_quantity_filter,
#         'borrowed_books': borrowed_books,
#         'borrower_emails': borrower_emails,
#         'borrowed_book_ids': borrowed_book_ids,
#     }

#     print(results.query)

#     return render(request, 'search_results.html', context)
