###GENERAL###
class DeletionOfNonExistantObjException(Exception):
    #Called when trying to delete an object that does not exist
    pass

class InvalidTypeException(Exception):
    #Called when an invalid object type is passed
    pass

class DisabledFieldException(Exception):
    # Called when a field within a return type is invalid
    pass

class MissingFieldException(Exception):
    # Called when a field within an object is not just invalid, but non-existant
    pass

class NoneReturnTypeException(Exception):
    # Called when an api call unexpectedly returns 'None'
    pass

class InvalidFieldForObject(Exception):
    #Called when a data structure does not have a valid field. (ie: an array of fruits contains an item 'book')
    pass

class DupicateObjectException(Exception):
    #Called when a user attempts to post an object that already exists in a situation were duplicates are not allowed
    pass

class InvalidFormatException(Exception):
    #Called when data is passed into a function with an invalid format
    pass

class InvalidTokenException(Exception):
    #Called when a user attempts to make a payment on a CC or ACH token that does not exist for the user.
    pass

###FIELD SPECIFIC###
class MemberNotFoundException(Exception):
    #Called when Member data can not be found
    pass

class MissingAuthTokenException(Exception):
    # Called when an auth token is missing when expected
    pass

class FailedClientCreationException(Exception):
    # Called when a connection to a client fails due to an invalid host, url, or other variable
    pass

class PaymentNotFoundException(Exception):
    # Called when a RTR payment and billing information can not be found
    pass

class PaymentDisabledException(Exception):
    # Called when a member payment functionality is disabled
    pass

class InvoiceNotFoundException(Exception):
    # called when invoice records cannot be found for marketplace members
    pass

class InvalidCreditCardTypeException(Exception):
    #Call when a user tries to use a credit card that does not have a cardType that we support
    pass