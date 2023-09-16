from django.db import models


class Model1(models.Model):
    name = models.CharField(max_length=50)
    description = models.CharField(max_length=100)
    decimal = models.DecimalField(max_digits=10, decimal_places=2)


class TestModel(models.Model):
    a = models.CharField(max_length=20)
    b = models.CharField(max_length=20)
    c = models.CharField(max_length=20)
    d = models.CharField(max_length=20)
