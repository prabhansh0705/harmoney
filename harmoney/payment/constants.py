from enum import Enum


class Constants(Enum):
    STATE_ID_MAPPING = {
        'AR': 54,
        'AZ': 101,
        'CA': 104,
        'FL': 55,
        'GA': 56,
        'IL': 76,
        'IN': 57,
        'KS': 74,
        'KY': 221,
        'LA': 70,
        'MA': 58,
        'MD': '',
        'MI': 184,
        'MN': '',
        'MO': 75,
        'MS': 59,
        'NC': 136,
        'NE': 223,
        'NH': 69,
        'NJ': 222,
        'NM': 213,
        'NV': 124,
        'NY': '',
        'OH': 60,
        'OK': 224,
        'OR': '',
        'PA': 138,
        'SC': 71,
        'TN': 137,
        'TX': 61,
        'VT': '',
        'WA': 62,
        'WI': 72,
        # this is for wellcare NorthCarolina for completeness, though it will likely never be used.
        'WC': 220,
    }
    SOFTHEON_REMOTE_SCOPE = "remote"
    SOFTHEON_PAYMENT_SCOPE = "payment"


class FormattingStrings(Enum):
    DateTimeFormat = '%Y-%m-%dT%H:%M:%SZ'
    ErrorLogFormat = "%s, %s"


class HttpStatusCodes(Enum):
    FileNotFoundErr = 404
    UnauthorizedErr = 401
    BadRequestErr = 400
    DuplicateInstanceErr = 409

class ValidInputs(Enum):
    valid_sources = ["unknown", "online", "voice", "subscription", "scheduled", "lockbox", "pos"]
    valid_states = ["active", "inactive", "expired"]

APPLICATION_JSON_CONTENT_TYPE = "application/json"

class IgnoredFields(Enum):
    #Adding foreign keys will auto-gen these 'set' objects that will cause issues due to the fact we do not have a database
    extra_ref_fields = ('id', 'BankAccountRef', 'recurringpayment_set', 'recurringpaymentreturn_set', 'creditcard_set')
    extra_payment_method_fields = ('id', 'recurringpaymentreturn_set', 'recurringpayment_set', 'onetimepayment_set')
