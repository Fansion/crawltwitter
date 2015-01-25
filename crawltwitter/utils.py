# -*- coding: utf-8 -*-

__author__ = 'frank'

from datetime import datetime


def get_nav_items(earliest_time, now="2015-01-01 08:35:20.820120"):
    '''
    用于user.html中侧边栏查找
    get labels in format:month year during a period
    like: January 2013

    >>> get_nav_items("2015-01-24 08:35:20.820120")
    [('2015', '01', 'January 2015')]
    >>> get_nav_items("2014-11-25 08:35:20.820120")
    [('2015', '01', 'January 2015'), ('2014', '12', 'December 2014'), ('2014', '11', 'November 2014')]
    >>> get_nav_items("2013-11-24 08:35:20.820120")
    [('2015', '01', 'January 2015'), ('2014', '12', 'December 2014'), ('2014', '11', 'November 2014'), ('2014', '10', 'October 2014'), ('2014', '09', 'September 2014'), ('2014', '08', 'August 2014'), ('2014', '07', 'July 2014'), ('2014', '06', 'June 2014'), ('2014', '05', 'May 2014'), ('2014', '04', 'April 2014'), ('2014', '03', 'March 2014'), ('2014', '02', 'February 2014'), ('2014', '01', 'January 2014'), ('2013', '12', 'December 2013'), ('2013', '11', 'November 2013')]
    '''

    # earliest_tweet = Status.query.filter_by(user_id=user.id).first()
    # earliest_time = str(earliest_tweet.created_at).split('-')
    earliest_time = earliest_time.split('-')
    earliest_year_month = [earliest_time[0], earliest_time[1]]
    # now = str(datetime.utcnow()).split('-')
    now = now.split('-')
    now_year_month = [now[0], now[1]]

    months = {1: 'January', 2: 'February', 3: 'March', 4: 'April',
              5: 'May', 6: 'June', 7: 'July', 8: 'August',
              9: 'September', 10: "October", 11: 'November', 12: 'December'
              }
    m_m = {1: '01', 2: '02', 3: '03', 4: '04', 5: '05',
           6: '06', 7: '07', 8: '08', 9: '09', 10: '10', 11: '11', 12: '12'}
    years = []

    for year in range(int(earliest_year_month[0]), int(now_year_month[0]) + 1):
        years.append(year)

    yearmonth_monthyear = []
    if len(years) == 1:
        for month in range(int(earliest_year_month[1]), int(now_year_month[1]) + 1):
            m_y = months[month] + ' ' + str(years[0])
            yearmonth_monthyear.append((str(years[0]), m_m[month], m_y))
    else:
        for month in range(int(earliest_year_month[1]), 13):
            m_y = months[month] + ' ' + str(years[0])
            yearmonth_monthyear.append((str(years[0]), m_m[month], m_y))
        if len(years) > 2:
            for year in years[1:-1]:
                for month in range(1, 13):
                    m_y = months[month] + ' ' + str(year)
                    yearmonth_monthyear.append(
                        (str(year), m_m[month], m_y))

        for month in range(1, int(now_year_month[1]) + 1):
            m_y = months[month] + ' ' + str(years[-1])
            yearmonth_monthyear.append(
                (str(years[-1]), m_m[month], m_y))

    # <listreverseiterator object at 0xb61cbe2c>
    # return reversed(yearmonth_monthyear)
    return yearmonth_monthyear[::-1]

if __name__ == '__main__':
    import doctest
    doctest.testmod()
