from django.contrib import admin
from django.urls import path
from myapp.views import *

urlpatterns = [
    path("1", View1.as_view(), name="view1"),
    path("2", View2.as_view(), name="view2"),
]
