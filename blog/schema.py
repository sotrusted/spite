from django.core.cache import cache
import graphene
from graphene_django import DjangoObjectType
import requests
from bs4 import BeautifulSoup

class LinkPreviewType(graphene.ObjectType):
    url = graphene.String()
    title = graphene.String()
    description = graphene.String()
    image = graphene.String()

class Query(graphene.ObjectType):
    link_preview = graphene.Field(LinkPreviewType, url=graphene.String(required=True))

    def resolve_link_preview(self, info, url):
        cached_data = cache.get(url)
        if cached_data:
            return cached_data

        # Fetch metadata (same as before)
        response = requests.get(url, timeout=5)
        soup = BeautifulSoup(response.content, "html.parser")
        title = soup.find("meta", property="og:title") or soup.find("title")
        description = soup.find("meta", property="og:description")
        image = soup.find("meta", property="og:image")

        data = LinkPreviewType(
            url=url,
            title=title["content"] if title else None,
            description=description["content"] if description else None,
            image=image["content"] if image else None,
        )
        cache.set(url, data, timeout=3600)  # Cache for 1 hour
        return data
