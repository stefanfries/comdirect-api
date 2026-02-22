import datetime


def timestamp():
    return datetime.datetime.now(datetime.UTC).strftime("%Y%m%d%H%M%S%f")
