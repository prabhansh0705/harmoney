from django.db import models
from dataclasses import dataclass
from enum import Enum


##NESTED OBJECTS##
class Ref(models.Model):
    refId = models.CharField(max_length=50, blank=True, null=True)
    source = models.CharField(max_length=20)

class ApplicationConfig(models.Model):
    member = models.OneToOneField(
        'Member',
        on_delete=models.CASCADE,
        related_name="applicationConfig",
        null=True
    )
    creditCardTokenizationURL = models.CharField(max_length=100)
    bankAccountTokenizationURL = models.CharField(max_length=100)
    paymentClientId = models.CharField(max_length=50)

class BillingAddress(models.Model):
    address1 = models.CharField(blank=False, max_length=50)
    address2 = models.CharField(blank=False, max_length=50)
    city = models.CharField(blank=False, max_length=50)
    state = models.CharField(blank=False, max_length=3)
    zipCode = models.CharField(blank=False, max_length=15)


class PaymentMethodRequest(models.Model):
    token = models.CharField(blank=False, max_length=50)
    type = models.CharField(blank=False, max_length=50)
    source = models.CharField(blank=False, max_length=50)
    amount = models.FloatField(null=True)
    runDayOfMonth = models.IntegerField()
    scheduleType = models.CharField(blank=False, max_length=50)

class CardState(Enum):
    Authorized = "Authorized"
    Invalid = "Invalid"


class CardType(Enum):
    Visa = "Visa"
    MasterCard = "MasterCard"
    Amex = "Amex"
    Discover = "Discover"

class AccountState(Enum):
    Authorized = "Authorized"
    Disabled = "Disabled"
    New = "New"
    Pending = "Pending"
    Invalid = "Invalid"

###MAIN OBJECTS###
class StatusReturn(models.Model):
    status = models.IntegerField()
    error = models.CharField(blank=True, max_length=150)

class Balance(models.Model):
    member = models.ForeignKey(
        'Member',
        on_delete=models.CASCADE,
        related_name='balance',
        null=True
    )
    totalAmountDue = models.FloatField()
    premiumAmountDue = models.FloatField()
    currentAmountDue = models.FloatField()
    financeStatus = models.CharField(max_length=50, null=True)
    status = models.CharField(max_length=50)


class Premium(models.Model):
    member = models.ForeignKey(
        'Member',
        on_delete=models.CASCADE,
        related_name='premium',
        null=True
    )
    claimsPaidThroughDate = models.CharField(max_length=50)
    premiumPaidThroughDate = models.CharField(max_length=50)
    premiumDueDate = models.CharField(max_length=50)
    startDate = models.CharField(blank=False, max_length=50)
    endDate = models.CharField(blank=False, max_length=50)
    premiumAmountTotal = models.CharField(blank=True, max_length=50)
    totalAmountDue = models.CharField(blank=True, max_length=50)
    pastDueAmount = models.CharField(blank=True, max_length=50)
    taxCredit = models.CharField(blank=True, max_length=50)
    otherPayerAmounts = models.CharField(blank=True, max_length=50)
    autoPay = models.BooleanField(null=True)
    subscriberResponsibility = models.CharField(blank=True, max_length=50)
    isChanged = models.BooleanField()
    changedDate = models.CharField(max_length=50)


class CreditCard(models.Model):
    member = models.ForeignKey(
        'Member',
        on_delete=models.CASCADE,
        related_name="creditCards",
        null=True
    )
    memberId = models.CharField(blank=False, null=True, max_length=50)
    token = models.CharField(blank=False, max_length=50)
    cardHolderName = models.CharField(blank=False, max_length=50)
    cardState = models.CharField(
        max_length=20,
        choices=[(e.value, e.name) for e in CardState],
        default=CardState.Invalid.value
    )
    cardType = models.CharField(
        max_length=20,
        choices=[(e.value, e.name) for e in CardType],
    )
    expirationMonth = models.CharField(blank=False, max_length=50)
    expirationYear = models.CharField(blank=False, max_length=50)
    ref = models.ForeignKey(
        Ref,
        on_delete=models.CASCADE,
        null=True
    )
    email = models.CharField(blank=False, max_length=50)
    createdAt = models.CharField(max_length=50)
    modifiedOn = models.CharField(max_length=50)
    maskedCardNumber = models.CharField(blank=False, max_length=50)
    isDefault = models.BooleanField()


class OneTimePayment(models.Model):
    accountId = models.IntegerField()
    paymentAmount = models.IntegerField()
    description = models.CharField(max_length=50)
    referenceId = models.CharField(max_length=50)
    confirmationNumber = models.CharField(max_length=20)
    _id = models.IntegerField()
    source = models.CharField(max_length=15)
    createdDate = models.CharField(max_length=50)
    modifiedDate = models.CharField(max_length=50)    
    paymentDate = models.CharField(max_length=30)
    paymentMethod = models.ForeignKey(PaymentMethodRequest, on_delete=models.CASCADE)


class PaymentHistory(models.Model):
    member = models.ForeignKey(
        'Member',
        on_delete=models.CASCADE,
        related_name="paymentHistories",
        null=True
    )
    buCode = models.IntegerField(null=True)
    memberId = models.CharField(max_length=50, null=True, blank=False)
    paymentId = models.CharField(max_length=50)
    submitter = models.CharField(max_length=50)
    transmissionDate = models.CharField(max_length=50)
    tradingPartner = models.CharField(max_length=50)
    paymentMethod = models.CharField(max_length=50)
    transactionId = models.CharField(max_length=50)
    paymentType = models.CharField(max_length=50)
    product = models.CharField(max_length=50)
    paymentDate = models.CharField(max_length=50)
    paymentClass = models.CharField(max_length=50)
    paymentSource = models.CharField(max_length=50)
    sourceSystem = models.CharField(max_length=50)
    paymentAmount = models.FloatField(null=True)
    receiptNumber = models.CharField(max_length=50)
    stateCode = models.CharField(max_length=50)
    businessUnit = models.CharField(max_length=50)
    caseId = models.CharField(max_length=50, null=True)
    externalVendorClientId = models.CharField(max_length=50, null=True)
    dataSourcePointer = models.CharField(max_length=50, null=True)
    checkNumber = models.CharField(max_length=50)
    lockBoxId = models.CharField(max_length=50)
    lockBoxBatchId = models.CharField(max_length=50, null=True)
    createdDate = models.CharField(max_length=50)


class Invoice(models.Model):
    member = models.ForeignKey(
        'Member',
        on_delete=models.CASCADE,
        related_name="invoices"
    )
    documentId = models.CharField(max_length=50, null=True)
    memberId = models.CharField(null=True, max_length=50)
    invoiceNumber = models.CharField(max_length=50)
    invoiceDate = models.CharField(max_length=50)
    periodStart = models.CharField(max_length=50)
    periodEnd = models.CharField(max_length=50)
    invoiceDueDate = models.CharField(max_length=50)
    premiumAmount = models.FloatField()
    memberAmountDue = models.FloatField()
    aptcAmount = models.FloatField()
    buCode = models.CharField(max_length=50)
    stateCode = models.CharField(max_length=50)
    product = models.CharField(max_length=50)
    businessUnit = models.CharField(max_length=50)
    sourceSystem = models.CharField(max_length=50)
    policyPremiumAmount = models.FloatField()
    totalAmountDue = models.FloatField(null=True)
    balanceForwardAmount = models.FloatField(null=True)



class RecurringPayment(models.Model):
    """
    Recurring Payment Model

    Related models (Class_name = related_name):
    * Schedule  = schedule
    * PaymentMethod = method
    """
    status = models.CharField(blank=False, max_length=50)
    createdAt = models.CharField(blank=False, max_length=50)
    ref = models.ForeignKey(
        Ref,
        on_delete=models.CASCADE,
        null=True
    )
    paymentMethod = models.ForeignKey(
        PaymentMethodRequest,
        on_delete=models.CASCADE,
        null=True
    )
    accountNickname = models.CharField(blank=False, max_length=50)
    lastDayProcessed = models.CharField(blank=False, max_length=50)
    signUpDate = models.CharField(blank=False, max_length=50)
    ownerId = models.CharField(max_length=50, null=True)
    folderId = models.CharField(max_length=50, null=True)
    source  = models.CharField(max_length=50, null=True)


class RecurringPaymentReturn(models.Model):
    status = models.CharField(blank=False, max_length=50)
    createdAt = models.CharField(blank=False, max_length=50)
    ref = models.ForeignKey(
        Ref,
        on_delete=models.CASCADE,
        null=True
    )
    paymentMethod = models.ForeignKey(
        PaymentMethodRequest,
        on_delete=models.CASCADE,
        null=True
    )
    accountNickname = models.CharField(blank=False, max_length=50)
    lastDayProcessed = models.CharField(blank=False, max_length=50)
    paymentClientId = models.CharField(blank=False, max_length=30)
    signUpDate = models.CharField(blank=False, max_length=50)
    ownerId = models.CharField(max_length=50, null=True)
    folderId = models.CharField(max_length=50, null=True)
    source  = models.CharField(max_length=50, null=True)


class BankAccount(models.Model):
    member = models.ForeignKey(
        'Member',
        on_delete=models.CASCADE,
        related_name='bankAccounts',
        null=True
    )
    memberId = models.CharField(blank=False, null=True, max_length=50)
    token = models.CharField(blank=False, null=True, max_length=50)
    accountHolderName = models.CharField(blank=False, max_length=50)
    accountState = models.CharField(
        max_length=20,
        choices=[(e.value, e.name) for e in AccountState],
        default=CardState.Invalid.value
    )
    accountType = models.CharField(blank=False, max_length=50)
    nickName = models.CharField(max_length=50)
    routingNumber = models.CharField(blank=False, max_length=50)
    accountNumber = models.CharField(blank=False, max_length=50)
    ref = models.ForeignKey(
        Ref,
        on_delete=models.SET_NULL,
        related_name="BankAccountRef",
        null=True
    )
    email = models.CharField(blank=False, max_length=50)
    createdAt = models.CharField(blank=False, null=True, max_length=50)
    modifiedOn = models.CharField(blank=False, null=True, max_length=50)
    isDefault = models.BooleanField(null=True)


class Member(models.Model):
    """
    Schema for Centene members

    Related models (Class_name = related_name):
    * ApplicationConfig = applicationConfig
    * Balance = balance
    * Premium = premium
    * [CreditCard] = creditCards
    * [PaymentHistory] = paymentHistories
    * [Invoice] = invoices
    * [RecurringPayment] = recurringPayments
    * [BankAcount] = bankAccounts
    """
    id = models.CharField(primary_key=True, max_length=50)
    amisysId = models.CharField(blank=False, max_length=50)
    firstName = models.CharField(blank=False, max_length=50)
    middleName = models.CharField(max_length=50)
    lastName = models.CharField(blank=False, max_length=50)
    fullName = models.CharField(null=True, max_length=150)
    dateOfBirth = models.DateTimeField()

