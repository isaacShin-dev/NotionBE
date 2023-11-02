import os
from datetime import datetime
from django.http import JsonResponse
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.pagination import PageNumberPagination
from .models import NotionArticle, Category, Tags
from .serializers import NotionArticleSerializer, CategorySerializer
from pathlib import Path
from .utils.articleUtill import NotionArticleParser
from .utils.common import download_img
import os, json
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
secret_file = os.path.join(BASE_DIR, "secrets.json")

with open(secret_file) as file:
    secrets = json.loads(file.read())


def get_secret(setting):
    try:
        return secrets[setting]
    except KeyError:
        error_msg = "No such key : {} ".format(setting)
        raise ImproperlyConfigured(error_msg)


api_key = get_secret("API_KEY")
database_id = get_secret("DATABASE_ID")


notion_parser = NotionArticleParser(api_key, database_id)


@api_view(["GET"])
def data_list_fetch_to_save(request):
    body = {
        "filter": {"property": "Done", "checkbox": {"equals": True}},
        "sorts": [{"property": "release_date", "direction": "descending"}],
    }
    results = notion_parser.get_article_list(body)
    new_data_cnt = 0

    for result in results:
        try:
            NotionArticle.objects.get(id=result.get("id"))
        except NotionArticle.DoesNotExist:
            article_id = result.get("id")
            # content_body = notion_parser.create_article(result, article_id)
            content_body = ""
            new_data_cnt += 1

            created_time = datetime.strptime(
                result.get("created_time"), "%Y-%m-%dT%H:%M:%S.%fZ"
            )
            updated_time = datetime.strptime(
                result.get("last_edited_time"), "%Y-%m-%dT%H:%M:%S.%fZ"
            )
            article = NotionArticle(
                id=article_id,
                created_time=created_time,
                updated_time=updated_time,
                cover=result.get("cover").get("external").get("url"),
                title=result.get("properties")
                .get("이름")
                .get("title")[0]
                .get("plain_text"),
                html_content=content_body,
            )
            article.save()

            for i in range(len(result.get("properties").get("주제").get("multi_select"))):
                category, created = Category.objects.get_or_create(
                    category=result.get("properties")
                    .get("주제")
                    .get("multi_select")[i]
                    .get("name")
                )
                Tags.objects.create(category=category, notion_article=article)

    return JsonResponse(
        data={"message": "successfully saved", "count": new_data_cnt},
        status=status.HTTP_200_OK,
    )


class listPagination(PageNumberPagination):
    page_size = 8
    page_size_query_param = None
    max_page_size = 8


@api_view(["GET"])
def fetch_published_list(request):
    tag = request.query_params.get("tag")
    if tag:
        # 태그의 아이디 값을 받아, 해당 태그를 가지고 있는 article 을 가져온다.
        articles = NotionArticle.objects.filter(categories=tag).order_by(
            "-created_time"
        )
    else:
        articles = NotionArticle.objects.prefetch_related("categories").order_by(
            "-created_time"
        )

    paginator = listPagination()
    paginated_list = paginator.paginate_queryset(articles, request)
    serializer = NotionArticleSerializer(paginated_list, many=True)

    return paginator.get_paginated_response(serializer.data)


@api_view(["GET"])
def fetch_article(request, article_id):
    article = NotionArticle.objects.get(id=article_id)

    article.views += 1
    article.save()

    category_list = NotionArticle.objects.get(id=article_id).categories.all()
    content = notion_parser.create_article(article_id)
    result = {
        "title": article.title,
        "categories": [category.category for category in category_list],
        "cover": article.cover,
        "created_at": article.created_time,
        "views": article.views,
        "content": content,
    }

    return JsonResponse(data=result, status=status.HTTP_200_OK)


@api_view(["GET"])
def fetch_by_category(request, category):
    articles = NotionArticle.objects.filter(categories__category=category).order_by(
        "-created_time"
    )

    paginator = listPagination()
    paginated_list = paginator.paginate_queryset(articles, request)
    serializer = NotionArticleSerializer(paginated_list, many=True)

    return paginator.get_paginated_response(serializer.data)


@api_view(["GET"])
def fetch_by_views(request):
    articles = NotionArticle.objects.order_by("-views")[0:5]

    paginator = listPagination()
    paginated_list = paginator.paginate_queryset(articles, request)
    serializer = NotionArticleSerializer(paginated_list, many=True)

    return paginator.get_paginated_response(serializer.data)


# @api_view(['GET'])
def fetch_all_tags(request):
    categories = Category.objects.all().distinct()[:20]  # id 값이 중복되는 것을 제거,
    serializer = CategorySerializer(categories, many=True)
    return JsonResponse(data=serializer.data, status=status.HTTP_200_OK, safe=False)
