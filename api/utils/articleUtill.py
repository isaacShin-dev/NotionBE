import json
import requests
from .contentBuilders import content_builder


class NotionArticleParser:
    base_url = "https://api.notion.com/v1/"

    def __init__(self, api_key, database_id):
        self.api_key = api_key
        self.database_id = database_id
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }

    def get_article_list(self, body=None):
        if body:
            body = json.dumps(body)
        try:
            response = requests.post(
                f"{self.base_url}databases/{self.database_id}/query",
                headers=self.headers,
                data=body,
            )
            response.raise_for_status()
            return response.json().get("results")
        except requests.RequestException as e:
            print(f"An error occurred: {e}")
            return None

    def create_article(self, result, article_id):
        response = requests.get(
            f"{self.base_url}blocks/{article_id}/children", headers=self.headers
        )
        res_to_json = json.loads(response.text)
        results = res_to_json.get("results")

        content_body = content_builder(results, self.api_key)

        return content_body
