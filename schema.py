import graphene
import json
from python_graphql_client import GraphqlClient


class Room(graphene.ObjectType):
    id = graphene.ID()
    location = graphene.String()
    price = graphene.Int()
    description = graphene.String()
    expirationDate = graphene.String()
    uuid = graphene.String()


class Query(graphene.ObjectType):
    rooms = graphene.List(Room, first=graphene.Int())

    def resolve_rooms(self, info, first):
        return [
            Room(id="1", location="location", price=20, description="desc", expirationDate="1/19/2020"),
            Room(id="2", location="location", price=10, description="desc", expirationDate="1/19/2020")
        ][:first]


class CreateRoom(graphene.Mutation):
    class Arguments:
        location = graphene.String()
        price = graphene.Int()
        description = graphene.String()
        expirationDate = graphene.String()
        uuid = graphene.String()

    room = graphene.Field(Room)

    def mutate(self, info, location, price, description, expirationDate, uuid):
        room = Room(location=location, price=price, description=description, expirationDate=expirationDate, uuid=uuid)
        return CreateRoom(room=room)


class Mutations(graphene.ObjectType):
    create_room: CreateRoom.Field()


schema = graphene.Schema(query=Query, mutation=Mutations)

client = GraphqlClient('http://localhost:8081/graphql')

result = schema.execute(
    '''
    mutation createRoom{
        createRoom()
    }
    '''
)

rooms = dict(result.data.items())
print(json.dumps(rooms, indent=4))
