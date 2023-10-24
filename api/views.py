import json
import requests

from django.http import JsonResponse
from rest_framework.decorators import api_view
from .models import NotionArticle, Category, Tags
from .serializers import NotionArticleSerializer, TagSerializer, CategorySerializer
from rest_framework.pagination import PageNumberPagination
from rest_framework import status
from datetime import datetime

# TODO: 기능 추가 구현
"""
#  1. 노션 데이터베이스 리스트 가져와서, 저장 처리하는 기능. DONE
#  2. 이미 배포 및 저장된(데이터베이스에 저장된 리스트 가져오는 기능) DONE
#  3. 카테고리별로 가져오는 기능
#  4. 조회수 별로 가져오는 기능
#  5. 좋아요 별로 가져오는 기능
#  6. 댓글 별로 가져오는 기능
#  7. page id -> 상세 페이지 가져오는 기능
    #  7-1. 페이지에 존재하는 모든 childeren 가져오는 기능 
    #  7-2. childeren 을 하나의 객체로 묶어서 화면단으로 보내줄 리스트 만드는 기능
"""

base_url = "https://api.notion.com/v1/"
database_id = "4751b6458ce2435cb2dbc4ddea1042c5"
headers = {
    'Authorization': 'Bearer secret_Dkn3N3vg2vrK2tu3PRdqYReqPvum5JbWTc1pYBafKOO',
    'Notion-Version': '2022-06-28',
    'Content-Type': 'application/json'
}


def create_article(result):
    article_id = result.get('id')

    response = requests.get(f'{base_url}blocks/{article_id}/children', headers=headers)
    res_to_json = json.loads(response.text)
    results = res_to_json.get('results')

    content_body = content_builder(results)

    created_time = datetime.strptime(result.get('created_time'), '%Y-%m-%dT%H:%M:%S.%fZ')
    updated_time = datetime.strptime(result.get('last_edited_time'), '%Y-%m-%dT%H:%M:%S.%fZ')
    article = NotionArticle(
        id=article_id,
        created_time=created_time,
        updated_time=updated_time,
        cover=result.get('cover').get('external').get('url'),
        title=result.get('properties').get('이름').get('title')[0].get('plain_text'),
        html_content=content_body
    )
    article.save()

    for i in range(len(result.get('properties').get('주제').get('multi_select'))):
        category, created = Category.objects.get_or_create(
            category=result.get('properties').get('주제').get('multi_select')[i].get('name'))
        Tags.objects.create(category=category, notion_article=article)


@api_view(['GET'])
def data_list_fetch_to_save(request):
    body = {
        "filter": {
            "property": "Done",
            "checkbox": {
                "equals": True
            }
        },
        "sorts": [
            {
                "property": "release_date",
                "direction": "descending"
            }
        ]
    }
    body_json = json.dumps(body)
    response = requests.post(f'{base_url}databases/{database_id}/query', headers=headers, data=body_json)
    res_to_json = json.loads(response.text)
    new_data_cnt = 0
    for result in res_to_json.get('results'):
        try:
            article = NotionArticle.objects.get(id=result.get('id'))
        except NotionArticle.DoesNotExist:
            create_article(result)
            new_data_cnt += 1

    return JsonResponse(data={'message': 'successfully saved', 'count': new_data_cnt}, status=status.HTTP_200_OK)


class listPagination(PageNumberPagination):
    page_size = 8
    page_size_query_param = None
    max_page_size = 8


@api_view(['GET'])
def fetch_published_list(request):
    tag = request.query_params.get('tag')
    if tag:
        # 태그의 아이디 값을 받아, 해당 태그를 가지고 있는 article 을 가져온다.
        articles = NotionArticle.objects.filter(categories=tag).order_by('-created_time')
    else:
        articles = NotionArticle.objects.prefetch_related('categories').order_by('-created_time')

    paginator = listPagination()
    paginated_list = paginator.paginate_queryset(articles, request)
    serializer = NotionArticleSerializer(paginated_list, many=True)

    return paginator.get_paginated_response(serializer.data)


@api_view(['GET'])
def fetch_article(request, article_id):
    article = NotionArticle.objects.get(id=article_id)

    article.views += 1
    article.save()

    category_list = NotionArticle.objects.get(id=article_id).categories.all()

    print([category.category for category in category_list])
    result = {
        'title': article.title,
        'categories': [category.category for category in category_list],
        'cover': article.cover,
        'created_at': article.created_time,
        'views': article.views,
        'content': article.html_content,
    }

    return JsonResponse(data=result, status=status.HTTP_200_OK)


def process_rich_text_element(text):
    tmp = text.get('plain_text')
    if text.get('annotations').get('code'):
        tmp = f'<code class="inline--code--block">{tmp}</code>'
    if text.get('annotations').get('bold'):
        tmp = f'<strong>{tmp}</strong>'
    if text.get('annotations').get('italic'):
        tmp = f'<em>{tmp}</em>'
    if text.get('annotations').get('strikethrough'):
        tmp = f'<del>{tmp}</del>'
    if text.get('annotations').get('underline'):
        tmp = f'<u>{tmp}</u>'
    if text.get('annotations').get('color'):
        tmp = f'<span style="color:{text.get("annotations").get("color")}">{tmp}</span>'
    if text.get('href'):
        tmp = f'<a href="{text.get("href")}">{tmp}</a>'
    return tmp


def process_rich_text(rich_texts):
    return ''.join([process_rich_text_element(text) for text in rich_texts])


def get_child_content(p_id):
    res = requests.get(f'{base_url}blocks/{p_id}/children', headers=headers)
    return content_builder(json.loads(res.text).get('results'))


def content_builder(results):
    content_body = ""

    for result in results:
        if result.get('type') in ['heading_1', 'heading_2', 'heading_3']:
            tag = f"h{result.get('type')[-1]}"
            class_name = "main--header" if tag == 'h1' else ""
            content_body += f'<{tag} class="{class_name}">{process_rich_text(result.get(result.get("type")).get("rich_text"))}</{tag}>'
        elif result.get('type') in ['numbered_list_item', 'bulleted_list_item']:
            tag = 'ol' if result.get('type') == 'numbered_list_item' else 'ul'
            content_body += f'<{tag}><li>{process_rich_text(result.get(result.get("type")).get("rich_text"))}'
            if result.get('has_children'):
                content_body += get_child_content(result.get('id'))
            content_body += f'</li></{tag}>'
        elif result.get('type') == 'paragraph':
            if not result.get('paragraph').get('rich_text'):
                content_body += f'<br>'
            else:
                content_body += f'<p>{process_rich_text(result.get("paragraph").get("rich_text"))}'
            if result.get('has_children'):
                content_body += get_child_content(result.get('id'))
            content_body += '</p>'
        elif result.get('type') == 'divider':
            content_body += f'<hr>'

        elif result.get('type') == 'callout':
            content_body += f'<div class="callout">'
            if result.get('callout').get('icon'):
                content_body += f'{result.get("callout").get("icon").get("emoji")}'
            content_body += process_rich_text(result.get('callout').get('rich_text'))
            content_body += f'</div>'

        elif result.get('type') == 'code':
            code_text = process_rich_text(result.get('code').get('rich_text'))
            code_type = result.get('code').get('language')
            if code_type == 'python':
                code_type = 'py'
            content_body += f'<pre class="prettyprint lang-{code_type}">{code_text}</pre>'

        elif result.get('type') == 'quote':
            content_body += f'<blockquote>'
            content_body += process_rich_text(result.get('quote').get('rich_text'))
            content_body += f'</blockquote>'

        elif result.get('type') == 'image':
            image_url = result.get('image').get('external', {}).get('url', '') or result.get('image').get('file',
                                                                                                          {}).get('url',
                                                                                                                  '')
            if result.get('image').get('caption'):
                if result.get('image').get('caption')[0].get("plain_text") == "img-box-shadow":
                    content_body += f'<div style="text-align: center;"><img max-width="270" class="body--image img--w90 img--shadow" src="{image_url}" alt="image"></div>'
                else:
                    content_body += f'<div style="text-align: center;"><img max-width="270" class="body--image" src="{image_url}" alt="image"></div>'
            else:
                content_body += f'<div><img class="body--image img--w90" max-width="270" src="{image_url}" alt="image"></div>'

        elif result.get('type') == 'bookmark':
            bookmark_url = result.get('bookmark').get('url')
            extract_title = bookmark_url[bookmark_url.find('title='):]
            bookmark_caption = result.get('bookmark').get('caption')[0].get('plain_text')
            content_body += f'<a href="{bookmark_url}" target="_blank"><div class="bookmark--wrapper">' \
                            f'<div class="bookmark--left">' \
                            f'<img class="bookmark-image" src="/share-banner.png"></img>' \
                            f'</div>' \
                            f'<div class="bookmark--title">' \
                            f'<span class="title--span">{bookmark_caption} | {extract_title}</span>' \
                            f'<hr/>' \
                            f'<span class="title--span--subtitle">{bookmark_url}</span>' \
                            f'</div>' \
                            f'</div>' \
                            f'</a>'

    return content_body


@api_view(['GET'])
def fetch_by_category(request, category):
    articles = NotionArticle.objects.filter(categories__category=category).order_by('-created_time')

    paginator = listPagination()
    paginated_list = paginator.paginate_queryset(articles, request)
    serializer = NotionArticleSerializer(paginated_list, many=True)

    return paginator.get_paginated_response(serializer.data)


@api_view(['GET'])
def fetch_by_views(request):
    articles = NotionArticle.objects.order_by('-views')[0:5]

    paginator = listPagination()
    paginated_list = paginator.paginate_queryset(articles, request)
    serializer = NotionArticleSerializer(paginated_list, many=True)

    return paginator.get_paginated_response(serializer.data)


# @api_view(['GET'])
def fetch_all_tags(request):
    categories = Category.objects.all().distinct()[:20]  # id 값이 중복되는 것을 제거,
    serializer = CategorySerializer(categories, many=True)
    return JsonResponse(data=serializer.data, status=status.HTTP_200_OK, safe=False)


@api_view(['GET'])
def related_articles(request, tags):
    articles = NotionArticle.objects.filter(categories__category=tags).order_by('-created_time')[0:3]
    serializer = NotionArticleSerializer(articles, many=True)
    return JsonResponse(data=serializer.data, status=status.HTTP_200_OK, safe=False)