import graphene
from blog.schema import Query as YourAppQuery


class Query(YourAppQuery, graphene.ObjectType):
    pass


schema = graphene.Schema(query=Query)
