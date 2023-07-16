from django.db import models


class Movie(models.Model):

    title = models.CharField(max_length=1000, null=True, blank=True)
    budget = models.IntegerField(null=True)
    homepage = models.CharField(max_length=1000, null=True, blank=True)
    overview = models.CharField(max_length=1000, null=True, blank=True)
    popularity = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    release_date = models.DateField(null=True)
    revenue = models.BigIntegerField(null=True)
    runtime = models.IntegerField(null=True)
    movie_status = models.CharField(max_length=50, null=True, blank=True)
    tagline = models.CharField(max_length=1000, null=True, blank=True)
    vote_average = models.DecimalField(max_digits=4, decimal_places=2, null=True)
    vote_count = models.IntegerField(null=True)
