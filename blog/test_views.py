from django.shortcuts import render
from .models import Post
from django.http import HttpResponse
from blog.views import simple_password_required

@simple_password_required
def editor(request):
    if request.method == "POST":
        content = request.POST.get("content", "")
        return HttpResponse(f"<h2>Submitted Content:</h2><div>{content}</div>")

    return render(request, "test/editor.html")
