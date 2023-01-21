from django.db import models
from django.utils import timezone

class Bananas(models.Model):
  timestamp = models.DateTimeField(default=timezone.now)
  nb_bananas_1 = models.IntegerField()
  nb_bananas_2 = models.IntegerField()
  nb_bananas_3 = models.IntegerField()
  image_1 = models.ImageField()
  image_2 = models.ImageField()
  image_3 = models.ImageField()


