from django.db import models


class User(models.Model):
    telegram_id = models.BigIntegerField(unique=True)
    username = models.CharField(max_length=150, blank=True, null=True)

    def __str__(self):
        return self.username or str(self.telegram_id)


class Word(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='words')
    english_word = models.CharField(max_length=255)
    russian_word = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.english_word} -> {self.russian_word}"