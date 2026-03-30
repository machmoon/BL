from django.contrib import admin
from django.urls import include, path
from core.views import (
    AdvancedSearchResults,
    account_overview,
    book_page,
    checkin,
    checkout,
    index,
    place_hold,
    resource_view,
    search_results,
)

urlpatterns = [
    path('', index, name='index'),
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("account/", account_overview, name="account_overview"),
    path('search/', search_results, name='search_results'),
    path('book/<int:book_id>/', book_page, name='book_page'),
    path('book/<int:book_id>/hold/', place_hold, name='place_hold'),
    path('resources/', resource_view, name='resource'),
    path('resource.html', resource_view),
    path('checkout/<str:isbn>/', checkout, name='checkout'),
    path('checkin/', checkin, name='checkin'),
    path('advanced-search/', AdvancedSearchResults.as_view(), name='advanced_search_results'),
    path('advanced_search_results/', AdvancedSearchResults.as_view()),
]
