# -*- coding: utf-8 -*-

__author__ = 'frank'


import re


uselessurl = re.compile(" ?([0-9a-zA-Z:/.]+…)$")
url = re.compile(" ?(http://t.co/[0-9a-zA-Z]+) ?")


def clean(text):
    """clean url ends with ... and replace url with <tag></tag>"""
    text = uselessurl.sub(r'', text)
    text = url.sub(r' <a href="\1">\1</a> ', text)
    return text


def filter_emoji(text):
    """filter emoji characters from input so can save input in mysql"""
    try:
        # UCS-4
        highpoints = re.compile(u'[\U00010000-\U0010ffff]')
    except Exception, e:
        # UCS-2
        highpoints = re.compile(u'[\uD800-\uDBFF][\uDC00-\uDFFF]')

    return highpoints.sub(u'\u25FD', text)
