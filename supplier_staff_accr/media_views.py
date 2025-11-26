# media_views.py
import os
from django.conf import settings
from django.http import HttpResponse

def list_photos(request):
    photos_path = os.path.join(settings.MEDIA_ROOT, "photos")
    files = os.listdir(photos_path)

    links = [
        f'<li><a href="/media/photos/{f}">{f}</a></li>'
        for f in files
    ]

    return HttpResponse("<h2>Photos</h2><ul>" + "\n".join(links) + "</ul>")
