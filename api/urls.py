from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path(
        "fetch_new_data/", views.data_list_fetch_to_save, name="data_list_fetch_to_save"
    ),
    path("list/", views.fetch_published_list, name="list"),
    path("article/<str:article_id>/", views.fetch_article, name="article"),
    path("category/<str:category>/", views.fetch_by_category, name="category"),
    path("rank/", views.fetch_by_views, name="rank"),
    path("tags/", views.fetch_all_tags, name="tags"),
    # path("delete/<str:article_id>/", views.delete_article, name="delete"),
]
