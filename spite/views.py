from django.conf import settings
from django.http import FileResponse, HttpRequest, HttpResponse

def favicon(request: HttpRequest) -> HttpResponse:
    file = (settings.BASE_DIR / "static" / "favicon.ico").open("rb")
    return FileResponse(file)
    
