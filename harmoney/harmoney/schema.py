import graphene
import payment.schema
import group.schema


class Query(payment.schema.MemberQuery, group.schema.GroupQuery):
    pass


class Mutation(payment.schema.MemberMutation):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation)