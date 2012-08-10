import datetime
import pytz

from django import template
from django.utils.translation import ugettext, ungettext

register = template.Library()


@register.filter(name='timesince_human')
def humanize_timesince(date):
    delta = datetime.datetime.now(pytz.utc) - date

    num_years = delta.days / 365
    if (num_years > 0):
        return ungettext(u"%d year ago", u"%d years ago", num_years) % num_years

    num_weeks = delta.days / 7
    if (num_weeks > 0):
        return ungettext(u"%d week ago", u"%d weeks ago", num_weeks) % num_weeks

    if (delta.days > 0):
        return ungettext(u"%d day ago", u"%d days ago", delta.days) % delta.days

    num_hours = delta.seconds / 3600
    if (num_hours > 0):
        return ungettext(u"%d hr ago", u"%d hrs ago", num_hours) % num_hours

    num_minutes = delta.seconds / 60
    if (num_minutes > 0):
        return ungettext(u"%d min ago", u"%d mins ago", num_minutes) % num_minutes

    return ugettext(u"seconds ago")
