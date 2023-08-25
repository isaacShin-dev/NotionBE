from django.db import models


class NotionArticle(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    created_time = models.DateTimeField()
    updated_time = models.DateTimeField()
    cover = models.URLField()
    title = models.CharField(max_length=1000)
    categories = models.ManyToManyField('Category', related_name='notion_articles')
    views = models.IntegerField(default=0)


class Category(models.Model):
    category = models.CharField(max_length=1000, verbose_name='카테고리명')


class Comment(models.Model):
    notion_article = models.ForeignKey(NotionArticle, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    created_time = models.DateTimeField(auto_now_add=True)
    updated_time = models.DateTimeField(auto_now=True)
    likes = models.IntegerField(default=0)
