import json
import requests


def process_rich_text_element(text):
    tmp = text.get("plain_text")
    if text.get("annotations").get("code"):
        tmp = f'<code class="inline--code--block">{tmp}</code>'
    if text.get("annotations").get("bold"):
        tmp = f"<strong>{tmp}</strong>"
    if text.get("annotations").get("italic"):
        tmp = f"<em>{tmp}</em>"
    if text.get("annotations").get("strikethrough"):
        tmp = f"<del>{tmp}</del>"
    if text.get("annotations").get("underline"):
        tmp = f"<u>{tmp}</u>"
    if text.get("annotations").get("color"):
        tmp = f'<span style="color:{text.get("annotations").get("color")}">{tmp}</span>'
    if text.get("href"):
        tmp = f'<a href="{text.get("href")}">{tmp}</a>'
    return tmp


def process_rich_text(rich_texts):
    return "".join([process_rich_text_element(text) for text in rich_texts])


def get_child_content(p_id, api_key):
    base_url = "https://api.notion.com/v1/"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    res = requests.get(f"{base_url}blocks/{p_id}/children", headers=headers)
    return content_builder(json.loads(res.text).get("results"), api_key)


def content_builder(results, api_key):
    content_body = ""

    for result in results:
        if result.get("type") in ["heading_1", "heading_2", "heading_3"]:
            tag = f"h{result.get('type')[-1]}"
            class_name = "main--header" if tag == "h1" else ""
            content_body += f'<{tag} class="{class_name}">{process_rich_text(result.get(result.get("type")).get("rich_text"))}</{tag}>'
        elif result.get("type") in ["numbered_list_item", "bulleted_list_item"]:
            tag = "ol" if result.get("type") == "numbered_list_item" else "ul"
            content_body += f'<{tag}><li>{process_rich_text(result.get(result.get("type")).get("rich_text"))}'
            if result.get("has_children"):
                content_body += get_child_content(result.get("id"), api_key)
            content_body += f"</li></{tag}>"
        elif result.get("type") == "paragraph":
            if not result.get("paragraph").get("rich_text"):
                content_body += f"<br>"
            else:
                content_body += (
                    f'<p>{process_rich_text(result.get("paragraph").get("rich_text"))}'
                )
            if result.get("has_children"):
                content_body += get_child_content(result.get("id"), api_key)
            content_body += "</p>"
        elif result.get("type") == "divider":
            content_body += f"<hr>"

        elif result.get("type") == "callout":
            content_body += f'<div class="callout">'
            if result.get("callout").get("icon"):
                content_body += f'{result.get("callout").get("icon").get("emoji")}'
            content_body += process_rich_text(result.get("callout").get("rich_text"))
            content_body += f"</div>"

        elif result.get("type") == "code":
            code_text = process_rich_text(result.get("code").get("rich_text"))
            code_type = result.get("code").get("language")
            if code_type == "python":
                code_type = "py"
            content_body += (
                f'<pre class="prettyprint lang-{code_type}">{code_text}</pre>'
            )

        elif result.get("type") == "quote":
            content_body += f"<blockquote>"
            content_body += process_rich_text(result.get("quote").get("rich_text"))
            content_body += f"</blockquote>"

        elif result.get("type") == "image":
            image_url = result.get("image").get("external", {}).get(
                "url", ""
            ) or result.get("image").get("file", {}).get("url", "")
            if result.get("image").get("caption"):
                if (
                    result.get("image").get("caption")[0].get("plain_text")
                    == "img-box-shadow"
                ):
                    content_body += f'<div style="text-align: center;"><img max-width="270" class="body--image img--w90 img--shadow" src="{image_url}" alt="image"></div>'
                else:
                    content_body += f'<div style="text-align: center;"><img max-width="270" class="body--image" src="{image_url}" alt="image"></div>'
            else:
                content_body += f'<div><img class="body--image img--w90" max-width="270" src="{image_url}" alt="image"></div>'

        elif result.get("type") == "bookmark":
            bookmark_url = result.get("bookmark").get("url")
            extract_title = bookmark_url[bookmark_url.find("title=") :]
            bookmark_caption = (
                result.get("bookmark").get("caption")[0].get("plain_text")
            )
            content_body += (
                f'<a href="{bookmark_url}" target="_blank"><div class="bookmark--wrapper">'
                f'<div class="bookmark--left">'
                f'<img class="bookmark-image" src="/share-banner.png"></img>'
                f"</div>"
                f'<div class="bookmark--title">'
                f'<span class="title--span">{bookmark_caption} | {extract_title}</span>'
                f"<hr/>"
                f'<span class="title--span--subtitle">{bookmark_url}</span>'
                f"</div>"
                f"</div>"
                f"</a>"
            )

    return content_body
