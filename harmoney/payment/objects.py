from datetime import datetime


class TimeSpan:
    def __init__(self, effective_date, end_date):
        if (isinstance(effective_date, datetime)
                and isinstance(end_date, datetime)):
            self.effective_date = effective_date
            self.end_date = end_date
        else:
            print('invalid time object')


class PlatformMember:
    def __init__(self, abs_person_id: str, abs_subscriber_id: str, amisys_id: str, business_line: str, business_unit: str, business_unitcode: str):
        self.abs_person_id = abs_person_id
        self.abs_subscriber_id = abs_subscriber_id
        self.amisys_id = amisys_id
        self.business_line = business_line
        self.business_unit = business_unit
        self.business_unitcode = business_unitcode
