from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager

# Create your models here.
JUDGE_A = 0
JUDGE_B = 1
JUDGE_C = 2
JUDGE_CATEGORIES = (
    (JUDGE_A, 'A'),
    (JUDGE_B, 'B'),
    (JUDGE_C, 'C'),
)

class User(AbstractUser):
    category = models.IntegerField(choices=JUDGE_CATEGORIES, default=JUDGE_A)

