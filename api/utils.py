import datetime


def timestamp():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M%S%f")
