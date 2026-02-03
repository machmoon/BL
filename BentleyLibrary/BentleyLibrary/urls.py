from django.contrib import admin
from django.urls import path
from core.views import (
    index, search_results, book_page, resource_view, 
    checkout, checkin, AdvancedSearchResults
)

urlpatterns = [
    path('', index, name='index'),
    path("admin/", admin.site.urls),
    path('search/', search_results, name='search_results'),
    path('book/<int:book_id>/', book_page, name='book_page'),
    path('resource.html', resource_view, name='resource'),
    path('checkout/<str:isbn>/', checkout, name='checkout'),
    path('checkin/', checkin, name='checkin'),
    path('advanced_search_results/', AdvancedSearchResults.as_view(), name='advanced_search_results'),
]