#! /usr/bin/env python3
import datetime


def now():
    return datetime.datetime.today().strftime("%Y-%d-%m %H:%M:%S")


