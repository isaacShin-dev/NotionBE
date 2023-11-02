from .models import NotionArticle, Category, Tags
from rest_framework import serializers


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"


class NotionArticleSerializer(serializers.ModelSerializer):
    categories_data = CategorySerializer(source="categories", many=True, read_only=True)

    class Meta:
        model = NotionArticle
        fields = (
            "id",
            "created_time",
            "updated_time",
            "cover",
            "title",
            "categories_data",
            "views",
            "html_content",
        )


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tags
        fields = "__all__"
