"""
URL configuration for BentleyLibrary project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from core.views import index
from core.views import search_results, book_page, resource_view, checkout, checkin, advanced_search, advanced_search_results


urlpatterns = [
    path('', index, name='index'),
    path("admin/", admin.site.urls),
    path('search/', search_results, name='search_results'),
    path('book/<int:book_id>/', book_page, name='book_page'),
    path('resource.html', resource_view, name='resource'),
    path('checkout/<str:isbn>/', checkout, name='checkout'),
    path('checkin/', checkin, name='checkin'),
    # path('advanced_search/', advanced_search, name='advanced_search'),
    path('advanced_search_results/', advanced_search_results.as_view(), name='advanced_search_results'),

    # path('checkin.html', checkin, name='checkin'),

    # path('book_inventory/', book_inventory, name='book_inventory'),
    # path('my-url/', my_view, name='my_view'),

]