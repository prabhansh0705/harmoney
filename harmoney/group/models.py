"""
    Custom Django models related to Employer Group
"""
from django.db import models


class EocInformation(models.Model):
    """
        EOC Information Model

        Related models (Class_name = related_name):
        * Coverage Code  = coverageCode
        * Effective Date = effectiveDate
        * EOC Id = eocId
        * Expiry Date = expiryDate
    """
    coverageCode = models.CharField(max_length=50)
    effectiveDate = models.DateTimeField
    eocId = models.CharField(max_length=50)
    expiryDate = models.DateTimeField


class Group(models.Model):
    """
        EOC Information Model

        Related models (Class_name = related_name):
        * Group Id  = groupId
        * Group Name = groupName
        * EOC Information = eocInformation
    """
    groupId = models.CharField(primary_key=True, max_length=50)
    groupName = models.CharField(max_length=50)
    eocInformation = models.CharField(max_length=50000)
