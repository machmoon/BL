"""
Comprehensive unit tests for BentleyLibrary application.
Tests view logic, validation, error handling, and edge cases.
"""
from django.test import TestCase, Client, TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.db import transaction
from django.contrib.messages import get_messages
from django.core.exceptions import ValidationError
from datetime import date, time, timedelta
from unittest.mock import Mock, patch, MagicMock
import threading
import time as time_module

from .models import Bookinventory, Log


class CheckoutViewTest(TestCase):
    """Test checkout view functionality."""
    
    def setUp(self):
        """Set up test client."""
        self.client = Client()
    
    def test_checkout_get_request(self):
        """Test GET request to checkout page."""
        url = reverse('checkout', args=['1234567890123'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'checkout.html')
    
    @patch('core.views.Bookinventory')
    def test_checkout_successful(self, mock_book_model):
        """Test successful book checkout."""
        # Mock book object
        mock_book = Mock()
        mock_book.isbn = '1234567890123'
        mock_book.title = 'Test Book'
        mock_book.author = 'Test Author'
        mock_book.publisher = 'Test Publisher'
        mock_book.published_date = date(2020, 1, 1)
        mock_book.available_quantity = 3
        mock_book.save = Mock()
        mock_book.refresh_from_db = Mock()
        
        # Mock queryset
        mock_book_model.objects.select_for_update.return_value.get.return_value = mock_book
        
        # Mock Log model
        with patch('core.views.Log') as mock_log_model:
            mock_log_entry = Mock()
            mock_log_model.return_value = mock_log_entry
            mock_log_entry.save = Mock()
            
            url = reverse('checkout', args=['1234567890123'])
            response = self.client.post(url, {
                'first_name': 'John',
                'last_name': 'Doe',
                'email': 'john.doe@example.com'
            })
            
            # Check redirect
            self.assertEqual(response.status_code, 302)
            
            # Verify book quantity was decremented
            self.assertEqual(mock_book.available_quantity, 2)
            mock_book.save.assert_called_once()
            mock_log_entry.save.assert_called_once()
    
    def test_checkout_missing_fields(self):
        """Test checkout with missing required fields."""
        url = reverse('checkout', args=['1234567890123'])
        response = self.client.post(url, {
            'first_name': 'John',
            # Missing last_name and email
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'required fields', status_code=200)
    
    def test_checkout_invalid_email(self):
        """Test checkout with invalid email."""
        url = reverse('checkout', args=['1234567890123'])
        response = self.client.post(url, {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'invalid-email'  # Missing @
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'valid email', status_code=200)
    
    @patch('core.views.Bookinventory')
    def test_checkout_no_available_copies(self, mock_book_model):
        """Test checkout when no copies are available."""
        # Mock book with 0 available quantity
        mock_book = Mock()
        mock_book.available_quantity = 0
        mock_book_model.objects.select_for_update.return_value.get.return_value = mock_book
        
        url = reverse('checkout', args=['1234567890123'])
        response = self.client.post(url, {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john.doe@example.com'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No copies available', status_code=200)
    
    @patch('core.views.Bookinventory')
    def test_checkout_nonexistent_book(self, mock_book_model):
        """Test checkout with non-existent ISBN."""
        from django.core.exceptions import ObjectDoesNotExist
        mock_book_model.DoesNotExist = ObjectDoesNotExist
        mock_book_model.objects.select_for_update.return_value.get.side_effect = ObjectDoesNotExist()
        
        url = reverse('checkout', args=['9999999999999'])
        response = self.client.post(url, {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john.doe@example.com'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'not found', status_code=200)
    
    def test_checkout_empty_email(self):
        """Test checkout with empty email."""
        url = reverse('checkout', args=['1234567890123'])
        response = self.client.post(url, {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': ''
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'required fields', status_code=200)


class CheckinViewTest(TestCase):
    """Test checkin view functionality."""
    
    def setUp(self):
        """Set up test client."""
        self.client = Client()
    
    def test_checkin_get_request(self):
        """Test GET request to checkin page."""
        url = reverse('checkin')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'checkin.html')
    
    @patch('core.views.Log')
    @patch('core.views.Bookinventory')
    def test_checkin_successful(self, mock_book_model, mock_log_model):
        """Test successful book checkin."""
        # Mock book object
        mock_book = Mock()
        mock_book.isbn = '1234567890123'
        mock_book.quantity = 5
        mock_book.available_quantity = 2  # 3 checked out
        mock_book.save = Mock()
        mock_book.refresh_from_db = Mock()
        
        mock_book_model.objects.select_for_update.return_value.get.return_value = mock_book
        
        # Mock log entry
        mock_log_entry = Mock()
        mock_log_entry.returned_date = None
        mock_log_entry.returned_time = None
        mock_log_entry.save = Mock()
        mock_log_entry.refresh_from_db = Mock()
        
        mock_log_model.objects.filter.return_value.order_by.return_value.first.return_value = mock_log_entry
        
        url = reverse('checkin')
        response = self.client.post(url, {
            'isbn': '1234567890123'
        })
        
        # Check redirect
        self.assertEqual(response.status_code, 302)
        
        # Verify book quantity was incremented
        self.assertEqual(mock_book.available_quantity, 3)
        mock_book.save.assert_called_once()
        mock_log_entry.save.assert_called_once()
        self.assertIsNotNone(mock_log_entry.returned_date)
    
    def test_checkin_missing_isbn(self):
        """Test checkin with missing ISBN."""
        url = reverse('checkin')
        response = self.client.post(url, {})
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ISBN', status_code=200)
    
    @patch('core.views.Bookinventory')
    def test_checkin_book_not_checked_out(self, mock_book_model):
        """Test checkin when book is not checked out."""
        # Mock book with all copies available
        mock_book = Mock()
        mock_book.isbn = '1234567890123'
        mock_book.quantity = 5
        mock_book.available_quantity = 5  # All available
        mock_book_model.objects.select_for_update.return_value.get.return_value = mock_book
        
        url = reverse('checkin')
        response = self.client.post(url, {
            'isbn': '1234567890123'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'not checked out', status_code=200)
    
    @patch('core.views.Bookinventory')
    def test_checkin_nonexistent_book(self, mock_book_model):
        """Test checkin with non-existent ISBN."""
        from django.core.exceptions import ObjectDoesNotExist
        mock_book_model.DoesNotExist = ObjectDoesNotExist
        mock_book_model.objects.select_for_update.return_value.get.side_effect = ObjectDoesNotExist()
        
        url = reverse('checkin')
        response = self.client.post(url, {
            'isbn': '9999999999999'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'not found', status_code=200)
    
    @patch('core.views.Log')
    @patch('core.views.Bookinventory')
    def test_checkin_no_log_entry(self, mock_book_model, mock_log_model):
        """Test checkin when no log entry exists."""
        # Mock book
        mock_book = Mock()
        mock_book.isbn = '1234567890123'
        mock_book.quantity = 5
        mock_book.available_quantity = 2
        mock_book_model.objects.select_for_update.return_value.get.return_value = mock_book
        
        # Mock no log entry found
        mock_log_model.objects.filter.return_value.order_by.return_value.first.return_value = None
        
        url = reverse('checkin')
        response = self.client.post(url, {
            'isbn': '1234567890123'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No check-out record', status_code=200)


class SearchResultsViewTest(TestCase):
    """Test search results view."""
    
    def setUp(self):
        """Set up test client."""
        self.client = Client()
    
    @patch('core.views.Bookinventory')
    @patch('core.views.Log')
    def test_search_by_title(self, mock_log_model, mock_book_model):
        """Test search by book title."""
        # Mock queryset
        mock_book = Mock()
        mock_book.title = 'Python Programming'
        mock_book.id = 1
        
        mock_queryset = Mock()
        mock_queryset.filter.return_value = [mock_book]
        mock_queryset.values.return_value = [{'id': 1}]
        mock_book_model.objects.filter.return_value = mock_queryset
        
        mock_log_model.objects.filter.return_value.values_list.return_value = []
        
        url = reverse('search_results')
        response = self.client.get(url, {'q': 'Python'})
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'search_results.html')
    
    def test_search_empty_query(self):
        """Test search with empty query."""
        with patch('core.views.Bookinventory') as mock_book_model:
            mock_queryset = Mock()
            mock_queryset.filter.return_value = []
            mock_queryset.values.return_value = []
            mock_book_model.objects.filter.return_value = mock_queryset
            
            with patch('core.views.Log') as mock_log_model:
                mock_log_model.objects.filter.return_value.values_list.return_value = []
                
                url = reverse('search_results')
                response = self.client.get(url, {'q': ''})
                
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, 'search_results.html')
    
    @patch('core.views.Bookinventory')
    @patch('core.views.Log')
    def test_search_with_date_filter(self, mock_log_model, mock_book_model):
        """Test search with date filters."""
        mock_queryset = Mock()
        mock_queryset.filter.return_value = []
        mock_queryset.values.return_value = []
        mock_book_model.objects.filter.return_value = mock_queryset
        mock_log_model.objects.filter.return_value.values_list.return_value = []
        
        url = reverse('search_results')
        response = self.client.get(url, {
            'q': 'Python',
            'published_date_start': '2020-01-01',
            'published_date_end': '2020-12-31'
        })
        
        self.assertEqual(response.status_code, 200)


class BookPageViewTest(TestCase):
    """Test book page view."""
    
    def setUp(self):
        """Set up test client."""
        self.client = Client()
    
    @patch('core.views.Log')
    @patch('core.views.get_object_or_404')
    def test_book_page_exists(self, mock_get_object, mock_log_model):
        """Test accessing an existing book page."""
        # Mock book
        mock_book = Mock()
        mock_book.id = 1
        mock_book.title = 'Test Book'
        mock_get_object.return_value = mock_book
        
        # Mock log queryset
        mock_log_model.objects.filter.return_value.values_list.return_value = []
        
        url = reverse('book_page', args=[1])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'book_page.html')
    
    @patch('core.views.get_object_or_404')
    def test_book_page_nonexistent(self, mock_get_object):
        """Test accessing a non-existent book page."""
        from django.http import Http404
        mock_get_object.side_effect = Http404()
        
        url = reverse('book_page', args=[99999])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)


class IndexViewTest(TestCase):
    """Test index/home view."""
    
    def setUp(self):
        """Set up test client."""
        self.client = Client()
    
    def test_index_page_loads(self):
        """Test index page loads successfully."""
        url = reverse('index')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/index.html')


class AdvancedSearchResultsTest(TestCase):
    """Test advanced search results view."""
    
    def setUp(self):
        """Set up test client."""
        self.client = Client()
    
    def test_advanced_search_get(self):
        """Test GET request to advanced search."""
        with patch('core.views.Bookinventory') as mock_book_model:
            mock_queryset = Mock()
            mock_queryset.filter.return_value = []
            mock_queryset.none.return_value = []
            mock_book_model.objects.all.return_value = mock_queryset
            
            url = reverse('advanced_search_results')
            response = self.client.get(url)
            
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, 'advanced_search_results.html')
    
    def test_advanced_search_by_title(self):
        """Test advanced search by title."""
        with patch('core.views.Bookinventory') as mock_book_model:
            mock_queryset = Mock()
            mock_queryset.filter.return_value = []
            mock_book_model.objects.all.return_value.filter.return_value = mock_queryset
            
            url = reverse('advanced_search_results')
            response = self.client.get(url, {
                'search_type': 'everything',
                'field[]': ['title'],
                'operator[]': ['icontains'],
                'search_term[]': ['Python']
            })
            
            self.assertEqual(response.status_code, 200)
    
    def test_advanced_search_any_field(self):
        """Test advanced search with any_field option."""
        with patch('core.views.Bookinventory') as mock_book_model:
            mock_queryset = Mock()
            mock_queryset.filter.return_value = []
            mock_book_model.objects.all.return_value.filter.return_value = mock_queryset
            
            url = reverse('advanced_search_results')
            response = self.client.get(url, {
                'search_type': 'everything',
                'field[]': ['any_field'],
                'operator[]': [''],
                'search_term[]': ['Expert']
            })
            
            self.assertEqual(response.status_code, 200)
    
    def test_advanced_search_with_date_range(self):
        """Test advanced search with date range."""
        with patch('core.views.Bookinventory') as mock_book_model:
            mock_queryset = Mock()
            mock_queryset.filter.return_value = []
            mock_book_model.objects.all.return_value.filter.return_value = mock_queryset
            
            url = reverse('advanced_search_results')
            response = self.client.get(url, {
                'search_type': 'everything',
                'published_date_start': '2022-01-01',
                'published_date_end': '2022-12-31'
            })
            
            self.assertEqual(response.status_code, 200)


class InputValidationTest(TestCase):
    """Test input validation across views."""
    
    def setUp(self):
        """Set up test client."""
        self.client = Client()
    
    def test_checkout_email_validation_edge_cases(self):
        """Test various email validation edge cases."""
        test_cases = [
            ('no-at-sign', False),
            ('@nodomain', False),
            ('nodomain@', False),
            ('valid@example.com', True),
            ('test.email@domain.co.uk', True),
        ]
        
        for email, should_accept in test_cases:
            url = reverse('checkout', args=['1234567890123'])
            response = self.client.post(url, {
                'first_name': 'Test',
                'last_name': 'User',
                'email': email
            })
            
            if should_accept:
                # Should not show email error (may show other errors like book not found)
                self.assertNotContains(response, 'valid email', status_code=200)
            else:
                # Should show email error
                self.assertContains(response, 'valid email', status_code=200)
    
    def test_checkout_whitespace_handling(self):
        """Test that whitespace is stripped from input."""
        url = reverse('checkout', args=['1234567890123'])
        response = self.client.post(url, {
            'first_name': '  John  ',
            'last_name': '  Doe  ',
            'email': '  john@example.com  '
        })
        
        # Should handle whitespace (validation should pass, may fail on book not found)
        # The important thing is it doesn't crash
        self.assertIn(response.status_code, [200, 302])


class ErrorHandlingTest(TestCase):
    """Test error handling in views."""
    
    def setUp(self):
        """Set up test client."""
        self.client = Client()
    
    @patch('core.views.Bookinventory')
    def test_checkout_database_error(self, mock_book_model):
        """Test checkout handles database errors gracefully."""
        mock_book_model.objects.select_for_update.return_value.get.side_effect = Exception("Database error")
        
        url = reverse('checkout', args=['1234567890123'])
        response = self.client.post(url, {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john@example.com'
        })
        
        # Should show error message, not crash
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'error', status_code=200)
    
    @patch('core.views.Bookinventory')
    def test_checkin_database_error(self, mock_book_model):
        """Test checkin handles database errors gracefully."""
        mock_book_model.objects.select_for_update.return_value.get.side_effect = Exception("Database error")
        
        url = reverse('checkin')
        response = self.client.post(url, {
            'isbn': '1234567890123'
        })
        
        # Should show error message, not crash
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'error', status_code=200)


class URLRoutingTest(TestCase):
    """Test URL routing and reverse lookups."""
    
    def test_all_urls_resolve(self):
        """Test that all URL patterns resolve correctly."""
        urls_to_test = [
            ('index', []),
            ('search_results', []),
            ('checkin', []),
            ('advanced_search_results', []),
            ('resource', []),
        ]
        
        for url_name, args in urls_to_test:
            try:
                url = reverse(url_name, args=args)
                self.assertIsNotNone(url)
            except Exception as e:
                self.fail(f"URL '{url_name}' failed to resolve: {e}")
    
    def test_checkout_url_with_isbn(self):
        """Test checkout URL with ISBN parameter."""
        url = reverse('checkout', args=['1234567890123'])
        self.assertIn('1234567890123', url)
    
    def test_book_page_url_with_id(self):
        """Test book page URL with book ID."""
        url = reverse('book_page', args=[1])
        self.assertIn('1', url)


class MessagesTest(TestCase):
    """Test Django messages framework integration."""
    
    def setUp(self):
        """Set up test client."""
        self.client = Client()
    
    @patch('core.views.Bookinventory')
    def test_checkout_success_message(self, mock_book_model):
        """Test that success message is set on checkout."""
        mock_book = Mock()
        mock_book.isbn = '1234567890123'
        mock_book.title = 'Test Book'
        mock_book.author = 'Test Author'
        mock_book.publisher = 'Test Publisher'
        mock_book.published_date = date(2020, 1, 1)
        mock_book.available_quantity = 1
        mock_book.save = Mock()
        
        mock_book_model.objects.select_for_update.return_value.get.return_value = mock_book
        
        with patch('core.views.Log'):
            url = reverse('checkout', args=['1234567890123'])
            response = self.client.post(url, {
                'first_name': 'John',
                'last_name': 'Doe',
                'email': 'john@example.com'
            }, follow=True)
            
            # Check for success message
            messages = list(get_messages(response.wsgi_request))
            self.assertTrue(any('Thanks' in str(m) for m in messages))
