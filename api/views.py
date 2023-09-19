import json
import requests
from bs4 import BeautifulSoup
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
    # check for update
    update_check_response = requests.get(f'{base_url}pages/{article_id}', headers=headers)
    update_check_res_to_json = json.loads(update_check_response.text)
    updated_time = datetime.strptime(update_check_res_to_json.get('last_edited_time'), '%Y-%m-%dT%H:%M:%S.%fZ')

    article = NotionArticle.objects.get(id=article_id)
    if article.updated_time != updated_time:
        article.updated_time = updated_time
        article.cover = update_check_res_to_json.get('cover').get('external').get('url')
        article.title = update_check_res_to_json.get('properties').get('이름').get('title')[0].get('plain_text')
        article.categories.clear()
        for i in range(len(update_check_res_to_json.get('properties').get('주제').get('multi_select'))):
            category, created = Category.objects.get_or_create(
                category=update_check_res_to_json.get('properties').get('주제').get('multi_select')[i].get('name'))
            article.categories.add(category)
        article.save()

    response = requests.get(f'{base_url}blocks/{article_id}/children', headers=headers)
    res_to_json = json.loads(response.text)
    results = res_to_json.get('results')

    content_body = build_html_from_notion(results)

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
        'content': content_body
    }

    return JsonResponse(data=result, status=status.HTTP_200_OK)


def build_html_from_notion(results):
    html_content = ""

    for result in results:
        block_type = result.get('type')

        if block_type == 'heading_1':
            h1_plain_text = result["heading_1"]["rich_text"][0]["plain_text"]
            html_content += f"<h1 class='main--header'>{h1_plain_text}</h1>"
        elif block_type == 'heading_2':
            h2_plain_text = result["heading_2"]["rich_text"][0]["plain_text"]
            html_content += f"<h2>{h2_plain_text}</h2>"
        elif block_type == 'heading_3':
            h3_plain_text = result["heading_3"]["rich_text"][0]["plain_text"]
            html_content += f"<h3>{h3_plain_text}</h3>"
        elif block_type == 'numbered_list_item':
            html_content += '<ol><li>'
            for text in result["numbered_list_item"]["rich_text"]:
                html_content += process_text(text)
            if result.get('has_children'):
                child_results = get_child_results(result)
                html_content += build_html_from_notion(child_results)
            html_content += '</li></ol>'
        elif block_type == 'paragraph':
            html_content += '<p>'
            for text in result["paragraph"]["rich_text"]:
                html_content += process_text(text)
            if result.get('has_children'):
                child_results = get_child_results(result)
                html_content += build_html_from_notion(child_results)
            html_content += '</p>'
        elif block_type == 'divider':
            html_content += '<hr>'
        elif block_type == 'callout':
            html_content += '<div class="callout">'
            if result['callout'].get('icon'):
                html_content += result['callout']['icon']['emoji']
            for text in result["callout"]["rich_text"]:
                html_content += process_text(text)
            html_content += '</div>'
        elif block_type == 'code':
            code_text = result['code']['rich_text'][0]['plain_text']
            code_type = result['code']['language'] if result['code'].get('language') else 'text'
            if code_type == 'python':
                code_type = 'py'
            html_content += f'<pre class="prettyprint lang-{code_type}">{code_text}</pre>'
        elif block_type == 'quote':
            html_content += '<blockquote>'
            for text in result["quote"]["rich_text"]:
                html_content += process_text(text)
            html_content += '</blockquote>'
        elif block_type == 'bulleted_list_item':
            html_content += '<ul><li>'
            for text in result["bulleted_list_item"]["rich_text"]:
                html_content += process_text(text)
            if result.get('has_children'):
                child_results = get_child_results(result)
                html_content += build_html_from_notion(child_results)
            html_content += '</li></ul>'
        elif block_type == 'image':
            image_url = result.get('image', {}).get('external', {}).get('url') or result.get('image', {}).get('file',
                                                                                                              {}).get(
                'url')
            caption = result['image'].get('caption')
            image_class = "body--image" if caption else ""
            text_align = 'style="text-align: center;"' if caption else ""
            html_content += f'<div {text_align}><img class="{image_class}" src="{image_url}" alt="image"></div>'

        elif block_type == 'bookmark':
            bookmark_url = result['bookmark']['url']
            html_content += build_bookmark_html(bookmark_url)
    return html_content


def get_html(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error fetching HTML: {e}")
        return None


def extract_meta(url):
    html = get_html(url)
    try:
        soup = BeautifulSoup(html, 'html.parser')

        # 메타 데이터 추출
        title = soup.find('meta', property='og:title') or soup.find('title')
        description = soup.find('meta', property='og:description') or soup.find('meta', {'name': 'description'})
        image = soup.find('meta', property='og:image')

        title_text = title['content'] if title else "No title found"
        description_text = description['content'] if description else "No description found"
        image_url = image['content'] if image else "No image found"

        return {
            'title': title_text,
            'description': description_text,
            'image': image_url
        }
    except Exception as e:
        print(f"Error extracting metadata: {e}")
        return None


def build_bookmark_html(url):
    meta = extract_meta(url)
    html_content = f"""
            <div class="bookmark">
                <a href="{url}" target="_blank">
                    <div class="bookmark--image" style="background-image: url('{meta['image']}')"></div>
                    <div class="bookmark--content">
                        <div class="bookmark--title">{meta['title']}</div>
                        <div class="bookmark--description">{meta['description']}</div>
                    </div>
                </a>
            </div>
        """
    return html_content


def process_text(text):
    plain_text = text['plain_text']
    annotations = text['annotations']
    if annotations.get('code'):
        return f'<code class="inline--code--block">{plain_text}</code>'
    if annotations.get('bold'):
        plain_text = f'<strong>{plain_text}</strong>'
    if annotations.get('italic'):
        plain_text = f'<em>{plain_text}</em>'
    if annotations.get('strikethrough'):
        plain_text = f'<del>{plain_text}</del>'
    if annotations.get('underline'):
        plain_text = f'<u>{plain_text}</u>'
    if annotations.get('color'):
        plain_text = f'<span style="color:{annotations["color"]}">{plain_text}</span>'
    if text.get('href'):
        plain_text = f'<a href="{text["href"]}">{plain_text}</a>'
    return plain_text


def get_child_results(result):
    p_id = result['id']
    res = requests.get(f'{base_url}/blocks/{p_id}/children', headers=headers)
    return json.loads(res.text).get('results')


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
    categories = Category.objects.all().distinct()  # id 값이 중복되는 것을 제거,
    serializer = CategorySerializer(categories, many=True)
    return JsonResponse(data=serializer.data, status=status.HTTP_200_OK, safe=False)

@api_view(['POST'])
def delete_article(request, article_id):
    article = NotionArticle.objects.get(id=article_id)
    article.delete()
    return JsonResponse(data={'message': 'successfully deleted'}, status=status.HTTP_200_OK)