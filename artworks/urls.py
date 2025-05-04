# portfolio/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.portfolio, name='portfolio'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('portfolio/<slug:slug>/', views.portfolio_by_category, name='portfolio_by_category'),
    path('artwork/<slug:slug>/', views.artwork_detail, name='artwork_detail'),
    path('hx_get_artwork/<slug:slug>/', views.hx_get_artwork_detail, name='hx_get_artwork_detail'),
]