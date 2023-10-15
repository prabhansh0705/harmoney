"""
    Employer Group Schema
"""
import graphene

from group.resolvers import GroupResolvers
from group.types import GroupType


class GroupQuery(graphene.ObjectType):
    """
        Employer group queries
    """
    group = graphene.Field(GroupType, group_id=graphene.ID(required=True))

    def resolve_group(self, info, group_id):
        """
        resolve group query
        """
        return GroupResolvers.resolve_group(group_id)
