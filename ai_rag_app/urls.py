from django.urls import path

from . import views, api

urlpatterns = [
    path("", views.index, name="index"),

    # REST API
    path('api/ask_question', api.ask_question),
]
