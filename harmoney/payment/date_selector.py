from harmoney.exceptions import InvalidFieldForObject


class DateSelector:
    def __init__(self, modifier, date):
        valid_modifiers = [
            'current',
            'previous',
            'next',
            'latestNonExpired',
            'currentOrFuture']
        if modifier not in valid_modifiers:
            print('not a valid modifier type')
            return
        self.mod = modifier
        self.date = date

    def date_filter(self, mapping):
        span = mapping.get('TimeSpan')
        if self.mod == "current":
            return span.effective_date <= self.date <= span.end_date

        elif self.mod == "previous":
            return span.end_date < self.date

        elif self.mod == "next":
            return span.effective_date > self.date

        elif self.mod == "latestNonExpired":
            return span.end_date > self.date

        elif self.mod == "currentOrFuture":
            return span.end_date >= self.date

        else:
            print('Invalid Modifier passed in.')
            return []

    def date_sorter(self, mapping):
        span = mapping.get('TimeSpan')
        if (self.mod == 'currentOrFuture' or self.mod == 'latestNotExpired'
                or self.mod == 'next' or self.mod == 'current'):
            return span.effective_date

        elif self.mod == "previous":
            return span.end_date
        else:
            print('Invalid Modifier passed in.')
            return {}

    def reversed_or_not(self):
        if self.mod in ("previous", "latestNotExpired", "current"):
            return True
        elif self.mod in ("next", "currentOrFuture"):
            return False
        else:
            raise InvalidFieldForObject
