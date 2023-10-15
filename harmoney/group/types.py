"""
    Custom Django types related to Employer groups
"""
from graphene_django.types import DjangoObjectType

from group.models import Group, EocInformation


class GroupType(DjangoObjectType):
    """
        Group Type
    """
    class Meta:
        """
            Group Model
        """
        model = Group


class EocInformationType(DjangoObjectType):
    """
        EOC Information Type
    """
    class Meta:
        """
            EOC Information model
        """
        model = EocInformation
