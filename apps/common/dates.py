import calendar
import datetime


def add_one_month(value):
    year = value.year + (1 if value.month == 12 else 0)
    month = 1 if value.month == 12 else value.month + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return datetime.date(year, month, day)


def _start_of_month(value):
    return value.replace(day=1)


def _end_of_month(value):
    return value.replace(day=calendar.monthrange(value.year, value.month)[1])
