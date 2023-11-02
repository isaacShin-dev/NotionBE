import urllib.request as req
from pathlib import Path
from django.conf import settings

if settings.DEBUG:
    base_url = "http://127.0.0.1:8000/media/"
else:
    base_url = "https://eclipseaddict.com/media/"

base_directory = Path(__file__).resolve().parent.parent.parent / "media"


def download_img(url):
    img_name = url.split("/")[-2] + url.split("/")[-1]
    if len(img_name) > 20:
        img_name = img_name[-10:]
    img_path = base_directory / img_name
    req.urlretrieve(url, img_path)

    return base_url + img_name
