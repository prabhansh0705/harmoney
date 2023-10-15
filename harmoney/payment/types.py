from graphene_django.types import DjangoObjectType
from payment.models import Member, Balance, CreditCard, BankAccount, Premium, Ref
from payment.models import RecurringPayment, Invoice, ApplicationConfig, OneTimePayment
from payment.models import PaymentHistory, StatusReturn, RecurringPaymentReturn, PaymentMethodRequest
from payment.constants import IgnoredFields

#Nested Object Types:
class RefType(DjangoObjectType):
    class Meta:
        model = Ref
        exclude_fields = IgnoredFields.extra_ref_fields.value

class PaymentMethodType(DjangoObjectType):
    class Meta:
        model = PaymentMethodRequest
        exclude_fields = IgnoredFields.extra_payment_method_fields.value


class StatusReturnType(DjangoObjectType):
    class Meta:
        model = StatusReturn
        exclude_fields = ('id',)

class MemberType(DjangoObjectType):
    class Meta:
        model = Member


class BalanceType(DjangoObjectType):
    class Meta:
        model = Balance
        exclude_fields = ('id', 'member')


class PremiumType(DjangoObjectType):
    class Meta:
        model = Premium
        exclude_fields = ('member', 'id')


class BankAccountType(DjangoObjectType):
    class Meta:
        model = BankAccount
        exclude_fields = ('member', 'id')


class CreditCardType(DjangoObjectType):
    class Meta:
        model = CreditCard
        exclude_fields = ('member', 'id')


class RecurringPaymentType(DjangoObjectType):
    class Meta:
        model = RecurringPayment
        exclude_fields = ('id',)

class RecurringPaymentReturnType(DjangoObjectType):
    class Meta:
        model = RecurringPaymentReturn
        exclude_fields = ('id',)

class InvoiceType(DjangoObjectType):
    class Meta:
        model = Invoice
        exclude_fields = ('member', 'id')


class ApplicationConfigType(DjangoObjectType):
    class Meta:
        model = ApplicationConfig
        exclude_fields = ('member', 'id')


class PaymentHistoryType(DjangoObjectType):
    class Meta:
        model = PaymentHistory
        exclude_fields = ('member', 'id')

class OneTimePaymentType(DjangoObjectType):
    class Meta:
        model = OneTimePayment
        exclude_fields = ('id',)

