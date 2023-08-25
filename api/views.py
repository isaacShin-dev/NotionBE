import json
import requests

from django.http import JsonResponse
from rest_framework.decorators import api_view
from .models import NotionArticle, Category
from .serializers import NotionArticleSerializer
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
    created_time = datetime.strptime(result.get('created_time'), '%Y-%m-%dT%H:%M:%S.%fZ')
    updated_time = datetime.strptime(result.get('last_edited_time'), '%Y-%m-%dT%H:%M:%S.%fZ')
    article = NotionArticle(
        id=result.get('id'),
        created_time=created_time,
        updated_time=updated_time,
        cover=result.get('cover').get('external').get('url'),
        title=result.get('properties').get('이름').get('title')[0].get('plain_text'),
    )
    article.save()

    for i in range(len(result.get('properties').get('주제').get('multi_select'))):
        category, created = Category.objects.get_or_create(
            category=result.get('properties').get('주제').get('multi_select')[i].get('name'))
        article.categories.add(category)


@api_view(['POST'])
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

    for result in res_to_json.get('results'):
        try:
            article = NotionArticle.objects.get(id=result.get('id'))
        except NotionArticle.DoesNotExist:
            create_article(result)

    return JsonResponse(data={'message': 'successfully saved'}, status=status.HTTP_200_OK)


class listPagination(PageNumberPagination):
    page_size = 8
    page_size_query_param = None
    max_page_size = 8


@api_view(['GET'])
def fetch_published_list(request):
    articles = NotionArticle.objects.prefetch_related('categories').order_by('-created_time')

    paginator = listPagination()
    paginated_list = paginator.paginate_queryset(articles, request)
    serializer = NotionArticleSerializer(paginated_list, many=True)

    return paginator.get_paginated_response(serializer.data)


@api_view(['GET'])
def fetch_article(request, article_id):
    response = requests.get(f'{base_url}blocks/{article_id}/children', headers=headers)
    res_to_json = json.loads(response.text)
    results = res_to_json.get('results')

    content_body = ""
    content_markdown = ""
    for result in results:
        if result.get('type') == 'heading_1':
            h1_plain_text = result.get('heading_1').get('rich_text')[0].get('plain_text')
            # content_markdown += f'# {h1_plain_text} \n'
            content_body += f'<h1 class="main--header">{h1_plain_text}</h1>'

        elif result.get('type') == 'heading_2':
            h2_plain_text = result.get('heading_2').get('rich_text')[0].get('plain_text')
            content_body += f'<h2>{h2_plain_text}</h2>'
            # content_markdown += f'## {h2_plain_text} \n'

        elif result.get('type') == 'heading_3':
            h3_plain_text = result.get('heading_3').get('rich_text')[0].get('plain_text')
            content_body += f'<h3>{h3_plain_text}</h3>'
            # content_markdown += f'### {h3_plain_text} \n\n'

        elif result.get('type') == 'paragraph':
            # for text in result.get('paragraph').get('rich_text'):
            #     if text.get('annotations').get('code'):
            #         content_markdown += f'`{text.get("plain_text")}`'
            #     else:
            #         content_markdown += text.get('plain_text')
            # content_markdown += f' \n'
            content_body += f'<p>'
            for text in result.get('paragraph').get('rich_text'):
                content_body += text.get('plain_text')
            content_body += f'</p>'

        elif result.get('type') == 'divider':
            content_body += f'<hr>'
            # content_markdown += f'--- \n'

        elif result.get('type') == 'callout':
            # if result.get('callout').get('icon'):
            #     content_markdown += f'{result.get("callout").get("icon").get("emoji")}'
            # for text in result.get('callout').get('rich_text'):
            #     if text.get('annotations').get('code'):
            #         content_markdown += f'`{text.get("plain_text")}`'
            #     else:
            #         content_markdown += text.get('plain_text')
            # content_markdown += f' \n'
            content_body += f'<div class="callout">'
            if result.get('callout').get('icon'):
                content_body += f'{result.get("callout").get("icon").get("emoji")}'
            for text in result.get('callout').get('rich_text'):
                if text.get('annotations').get('code'):
                    content_body += f'<code class="inline--code--block">{text.get("plain_text")}</code>'
                else:
                    content_body += text.get('plain_text')
            content_body += f'</div>'

        elif result.get('type') == 'code':
            code_text = result.get('code').get('rich_text')[0].get('plain_text')
            code_type = result.get('code').get('language')
            if code_type == 'python':
                code_type = 'py'
            # content_markdown += f'``` {code_type} {code_text} ``` \n'
            content_body += f'<pre class="prettyprint lang-{code_type}">{code_text}</pre>'

        elif result.get('type') == 'quote':
            quatation_text = result.get('quote').get('rich_text')[0].get('plain_text')
            content_body += f'<blockquote>{quatation_text}</blockquote>'
            # content_markdown += f'> {result.get("quote").get("rich_text")[0].get("plain_text")} \n'

        elif result.get('type') == 'bulleted_list_item':
            content_body += f'<ul><li>'
            for text in result.get('bulleted_list_item').get('rich_text'):
                if text.get('annotations').get('code'):
                    # content_markdown += f'`{text.get("plain_text")}` \n'
                    content_body += f'<code class="inline--code--block">{text.get("plain_text")}</code>'
                else:
                    content_markdown += text.get('plain_text') + ' \n'
                    content_body += text.get('plain_text')
            #         content_body += text.get('plain_text')
            content_body += f'</li></ul>'





    print(content_body)
    result = {
        'content': content_body
    }

    return JsonResponse(data=result, status=status.HTTP_200_OK)
