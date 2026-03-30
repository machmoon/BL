from django.contrib import admin
from django.conf import settings
from django.urls import include, path
from core.views import (
    AdvancedSearchResults,
    BentleyLoginView,
    account_overview,
    ai_concierge,
    auth0_callback,
    auth0_login,
    book_page,
    checkin,
    checkout,
    isbn_lookup,
    index,
    logout_view,
    place_hold,
    resource_view,
    search_results,
)

urlpatterns = [
    path('', index, name='index'),
    path("admin/", admin.site.urls),
    path("accounts/login/", BentleyLoginView.as_view(), name="login"),
    path("accounts/logout/", logout_view, name="logout"),
    path("accounts/auth0/login/", auth0_login, name="auth0_login"),
    path("accounts/auth0/callback/", auth0_callback, name="auth0_callback"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("account/", account_overview, name="account_overview"),
    path('search/', search_results, name='search_results'),
    path('book/<int:book_id>/', book_page, name='book_page'),
    path('book/<int:book_id>/hold/', place_hold, name='place_hold'),
    path('resources/', resource_view, name='resource'),
    path('resource.html', resource_view),
    path("api/isbn-lookup/", isbn_lookup, name="isbn_lookup"),
    path("api/ai-concierge/", ai_concierge, name="ai_concierge"),
    path('checkout/<str:isbn>/', checkout, name='checkout'),
    path('checkin/', checkin, name='checkin'),
    path('advanced-search/', AdvancedSearchResults.as_view(), name='advanced_search_results'),
    path('advanced_search_results/', AdvancedSearchResults.as_view()),
]
