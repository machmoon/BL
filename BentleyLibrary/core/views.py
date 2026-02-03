import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from django.db import transaction
from django.utils import timezone
from django.contrib import messages
from django.views.generic import ListView
from .models import Bookinventory, Log

logger = logging.getLogger(__name__)


def checkout(request, isbn):
    """Handle book checkout with race condition protection."""
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        
        if not all([first_name, last_name, email]):
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'checkout.html', {'error_message': 'Please fill in all required fields.'})
        
        if '@' not in email or '.' not in email.split('@')[-1]:
            messages.error(request, 'Please enter a valid email address.')
            return render(request, 'checkout.html', {'error_message': 'Please enter a valid email address.'})
        
        try:
            with transaction.atomic():
                book = Bookinventory.objects.select_for_update().get(isbn=isbn)
                
                if book.available_quantity <= 0:
                    messages.error(request, 'No copies available to check out.')
                    return render(request, 'checkout.html', {'error_message': 'No copies available to check out.'})
                
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
                
                book.available_quantity -= 1
                book.save()
                
                logger.info(f"Book {isbn} checked out by {email}")
                messages.success(request, 'Thanks for checking out the book.')
                return redirect('index')
                
        except Bookinventory.DoesNotExist:
            logger.warning(f"Checkout attempted for non-existent ISBN: {isbn}")
            messages.error(request, 'Book not found in inventory.')
            return render(request, 'checkout.html', {'error_message': 'Book not found in inventory.'})
        except Exception as e:
            logger.error(f"Error during checkout: {str(e)}")
            messages.error(request, 'An error occurred during checkout. Please try again.')
            return render(request, 'checkout.html', {'error_message': 'An error occurred during checkout. Please try again.'})
    
    return render(request, 'checkout.html')


def checkin(request):
    """Handle book checkin with error handling."""
    if request.method == 'POST':
        isbn = request.POST.get('isbn', '').strip()
        
        if not isbn:
            messages.error(request, 'Please provide an ISBN.')
            return render(request, 'checkin.html', {'error_message': 'Please provide an ISBN.'})
        
        try:
            with transaction.atomic():
                book = Bookinventory.objects.select_for_update().get(isbn=isbn)
                
                if book.available_quantity >= book.quantity:
                    messages.error(request, 'This book is not checked out.')
                    return render(request, 'checkin.html', {'error_message': 'This book is not checked out.'})
                
                log_entry = Log.objects.filter(
                    book=book,
                    returned_date__isnull=True
                ).order_by('-borrowed_date', '-borrowed_time').first()
                
                if not log_entry:
                    messages.error(request, 'No check-out record found for this book.')
                    return render(request, 'checkin.html', {'error_message': 'No check-out record found for this book.'})
                
                log_entry.returned_date = timezone.now().date()
                log_entry.returned_time = timezone.now().time()
                log_entry.save()
                
                book.available_quantity += 1
                book.save()
                
                logger.info(f"Book {isbn} checked in")
                messages.success(request, 'Book checked in successfully.')
                return redirect('index')
                
        except Bookinventory.DoesNotExist:
            logger.warning(f"Checkin attempted for non-existent ISBN: {isbn}")
            messages.error(request, 'Book not found in inventory.')
            return render(request, 'checkin.html', {'error_message': 'Book not found in inventory.'})
        except Exception as e:
            logger.error(f"Error during checkin: {str(e)}")
            messages.error(request, 'An error occurred during checkin. Please try again.')
            return render(request, 'checkin.html', {'error_message': 'An error occurred during checkin. Please try again.'})
    
    return render(request, 'checkin.html')


class AdvancedSearchResults(ListView):
    """Advanced search results with dynamic query building."""
    model = Bookinventory
    template_name = 'advanced_search_results.html'
    context_object_name = 'results'
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search_type = self.request.GET.get('search_type')
        field = self.request.GET.getlist('field[]')
        operator = self.request.GET.getlist('operator[]')
        search_term = self.request.GET.getlist('search_term[]')
        logical_operator = self.request.GET.getlist('logical_operator[]')
        filter_query = Q()

        if search_type in ['everything', 'catalog'] and field:
            queries = []
            for i in range(len(field)):
                if i >= len(search_term) or not search_term[i]:
                    continue
                    
                if field[i] == 'any_field':
                    sub_query = (
                        Q(title__icontains=search_term[i]) |
                        Q(author__icontains=search_term[i]) |
                        Q(publisher__icontains=search_term[i]) |
                        Q(isbn__icontains=search_term[i]) |
                        Q(description__icontains=search_term[i])
                    )
                    queries.append(sub_query)
                else:
                    if i < len(operator) and operator[i]:
                        try:
                            sub_query = Q(**{f"{field[i]}__{operator[i]}": search_term[i]})
                            queries.append(sub_query)
                        except (ValueError, TypeError):
                            sub_query = Q(**{f"{field[i]}__icontains": search_term[i]})
                            queries.append(sub_query)
            
            if queries:
                if logical_operator and len(logical_operator) > 0:
                    filter_query = queries[0]
                    for i in range(1, len(queries)):
                        if i-1 < len(logical_operator):
                            if logical_operator[i-1] == 'AND':
                                filter_query &= queries[i]
                            elif logical_operator[i-1] == 'OR':
                                filter_query |= queries[i]
                            elif logical_operator[i-1] == 'NOT':
                                filter_query &= ~queries[i]
                        else:
                            filter_query |= queries[i]
                else:
                    for query in queries:
                        filter_query |= query

        published_date_start_filter = self.request.GET.get('published_date_start', '')
        published_date_end_filter = self.request.GET.get('published_date_end', '')

        if published_date_start_filter:
            try:
                filter_query &= Q(published_date__gte=published_date_start_filter)
            except (ValueError, TypeError):
                pass

        if published_date_end_filter:
            try:
                filter_query &= Q(published_date__lte=published_date_end_filter)
            except (ValueError, TypeError):
                pass

        if any([search_type, field, operator, search_term, logical_operator, published_date_start_filter, published_date_end_filter]):
            queryset = queryset.filter(filter_query)
        else:
            queryset = queryset.none()

        return queryset


def advanced_search(request):
    """Advanced search view (unused, kept for future use)."""
    query = request.GET.get('q', '')
    filter_query = Q()

    if query:
        filter_query |= (Q(title__icontains=query) |
                         Q(publisher__icontains=query) |
                         Q(author__icontains=query) |
                         Q(description__icontains=query) |
                         Q(isbn__icontains=query))

    search_type = request.GET.get('search_type', 'everything')

    if search_type == 'everything':
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

    published_date_start_filter = request.GET.get('published_date_start', '')
    published_date_end_filter = request.GET.get('published_date_end', '')

    if published_date_start_filter:
        filter_query &= Q(published_date__gte=published_date_start_filter)
    if published_date_end_filter:
        filter_query &= Q(published_date__lte=published_date_end_filter)

    results = Bookinventory.objects.filter(filter_query)

    context = {
        'results': results,
        'query': query,
        'search_type': search_type,
        'author': author if 'author' in locals() else '',
        'publisher': publisher if 'publisher' in locals() else '',
        'isbn': isbn if 'isbn' in locals() else '',
    }

    return render(request, 'advanced_search_results.html', context)


def resource_view(request):
    """Resource view."""
    return render(request, 'resource.html')


def search_results(request):
    """Search results with query handling."""
    query = request.GET.get('q', '')
    filter_query = Q()

    if query:
        filter_query |= (Q(title__icontains=query) |
                         Q(publisher__icontains=query) |
                         Q(author__icontains=query) |
                         Q(description__icontains=query) |
                         Q(isbn__icontains=query))

    published_date_start_filter = request.GET.get('published_date_start', '')
    published_date_end_filter = request.GET.get('published_date_end', '')

    if published_date_start_filter:
        filter_query &= Q(published_date__gte=published_date_start_filter)
    if published_date_end_filter:
        filter_query &= Q(published_date__lte=published_date_end_filter)

    available_quantity_filter = request.GET.get('available_quantity', '')
    if available_quantity_filter:
        try:
            filter_query &= Q(available_quantity=int(available_quantity_filter))
        except (ValueError, TypeError):
            pass

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

    results = Bookinventory.objects.filter(filter_query)
    borrowed_books = Log.objects.filter(
        book_id__in=results.values('id'),
        returned_date__isnull=True
    )
    borrower_emails = borrowed_books.values_list('borrower_email', flat=True)
    borrowed_book_ids = borrowed_books.values_list('book_id', flat=True)

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
    """Display individual book page with borrowing information."""
    book = get_object_or_404(Bookinventory, id=book_id)
    borrowed_books = Log.objects.filter(book_id=book_id, returned_date__isnull=True)
    borrower_emails = borrowed_books.values_list('borrower_email', flat=True)
    borrowed_book_ids = borrowed_books.values_list('book_id', flat=True)

    context = {
        'book': book,
        'borrowed_books': borrowed_books,
        'borrower_emails': borrower_emails,
        'borrowed_book_ids': borrowed_book_ids
    }
    return render(request, 'book_page.html', context)


def index(request):
    """Home page view."""
    success_messages = messages.get_messages(request)
    return render(request, 'core/index.html', {'success_messages': success_messages})
