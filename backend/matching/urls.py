from django.urls import path
from . import views

app_name = 'matching'

urlpatterns = [
    path('', views.matching_index, name='matching_index'),
    path('search/', views.search_properties, name='search_properties'),
    path('match/', views.match_properties, name='match_properties'),
    path('properties/', views.list_properties, name='list_properties'),
]