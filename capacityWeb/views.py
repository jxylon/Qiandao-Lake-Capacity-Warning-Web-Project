import ctypes
import glob
import inspect
from threading import Thread
import datetime
import decimal
import json
import random
import time
import cv2
import os
import requests
from dateutil.relativedelta import relativedelta
from django.core import serializers
from django.db import connection
from django.db.models import Max, Sum, Avg, Count
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.utils.safestring import SafeString
from .models import Scenic, Recordnums, Recordwarnings, Camera, Camerainfo, Wifiinfo, WifiNumsMonth, WifiNumsDay, \
    Adminer, User, Deviceinfo
# from static.darkflow_video.run_detect import run
# from static.darknet.run_detect import run_person
# from static.darknet2.run_detect import run_fight
# from static.darknet3.run_detect import run_smoke

count_list = [-1]
t = Thread()
t_person = Thread()
t_fight = Thread()
t_smoke = Thread()


def _async_raise(tid, exctype):
    """raises the exception, performs cleanup if needed"""
    tid = ctypes.c_long(tid)
    if not inspect.isclass(exctype):
        exctype = type(exctype)
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(exctype))
    if res == 0:
        raise ValueError("invalid thread id")
    elif res != 1:
        # """if it returns a number greater than one, you're in trouble,
        # and you should call it again with exc=NULL to revert the effect"""
        ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
        raise SystemError("PyThreadState_SetAsyncExc failed")


def stop_thread(thread):
    _async_raise(thread.ident, SystemExit)


def test1(request):
    data = {'count': count_list[-1]}
    return HttpResponse(json.dumps(data))


def test2():
    i = 0
    global count_list
    while (i < 10):
        count_list.append(i)
        i += 1
        print(i)
        time.sleep(1)
    count_list = [-1]


def get_count(request):
    global t
    t = Thread(target=test2, args=())
    t.start()
    # _thread.start_new_thread(test2, ())
    data = {'msg': '开启线程'}
    return HttpResponse(json.dumps(data))


def test(request):
    return render(request, 'test.html')


def addData(request):
    # 添加Recordwarnings表
    # start_date = datetime.datetime.now() + relativedelta(year=2019, month=2, day=1)
    # for i in range(28):
    #     for j in range(1, 9):
    #         curtime = start_date + relativedelta(days=i)
    #         curtime = curtime + relativedelta(minutes=10 * i)
    #         print(str(curtime)[:19])
    #         level = random.randint(1, 3)
    #         exceedNums = random.randint(1, 50) + 50 * (3 - level)
    #         Recordwarnings.objects.create(scenicid=j, camid=0, level=level, type=1, exceednums=exceedNums,
    #                                       createat=str(curtime)[:19], state=1)
    # # 添加Recordnums表
    # for i in range(31):
    #     curtime = datetime.datetime.now() + relativedelta(days=i)
    #     year = curtime.year
    #     month = curtime.month
    #     day = curtime.day
    #     hour = curtime.hour
    #     minute = curtime.minute
    #     sec = curtime.second
    #     for j in range(1, 9):
    #         for k in range(1, 16):
    #             nums = random.randint(1, 1000)
    #             sce_obj = Scenic(scenicid=j)
    #             cam_obj = Camera(scenicid=sce_obj, camid=k)
    #             Recordnums.objects.create(scenicid=sce_obj, camid=cam_obj, nums=nums, year=year, month=month, day=day,
    #                                       hour=hour,
    #                                       minute=minute, sec=sec, createat=str(curtime)[:19])
    return render(request, 'addData.html')


def getTime(request):
    t = datetime.datetime.now()
    data = {'current_time': str(t)[:17]}
    return HttpResponse(json.dumps(data))


def dictfetchall(cursor):
    "Return all rows from a cursor as a dict"
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return float(o)
        super(DecimalEncoder, self).default(o)


def get_current_week():
    monday, sunday = datetime.datetime.now(), datetime.datetime.now()
    one_day = datetime.timedelta(days=1)
    while monday.weekday() != 0:
        monday -= one_day
    while sunday.weekday() != 6:
        sunday += one_day
    # 返回当前的星期一前一天和星期天后一天
    return monday - relativedelta(days=1), sunday + relativedelta(days=1)


def get_time_dic():
    curtime = datetime.datetime.now()
    monday, sunday = datetime.datetime.now(), datetime.datetime.now()
    one_day = datetime.timedelta(days=1)
    while monday.weekday() != 0:
        monday -= one_day
    while sunday.weekday() != 6:
        sunday += one_day
    time_dic = {'monday': monday - relativedelta(days=1), 'sunday': sunday + relativedelta(days=1),
                'last_monday': monday - relativedelta(days=8), 'last_sunday': monday}
    lastmonth_time = curtime - relativedelta(months=1)
    time_dic['lastmonth_day'] = lastmonth_time.day
    time_dic['lastmonth_year'] = lastmonth_time.year
    time_dic['lastmonth_month'] = lastmonth_time.month
    time_dic['lastmonth'] = lastmonth_time
    # 返回timedate字典
    return time_dic


def getIntervalTouristNums(start, end, scenicid):
    """
    :param start:
    :param end:
    :return: 获得start-end时间端内某岛的人数
    """
    if start.month == end.month:  # 没有跨月份
        nums_this_Interval = WifiNumsDay.objects.filter(island_id=scenicid, year__range=[start.year, end.year],
                                                        month__range=[start.month, end.month],
                                                        day__range=[start.day, end.day],
                                                        ).values("island_id").annotate(sum=Sum("nums"))
        sum_ = nums_this_Interval[0]['sum']
    else:  # 跨月份
        nums_this_Interval_1 = WifiNumsDay.objects.filter(island_id=scenicid, year=start.year, month=start.month,
                                                          day__range=[start.day, 30]).values("island_id").annotate(
            sum=Sum("nums"))
        nums_this_Interval_2 = WifiNumsDay.objects.filter(island_id=scenicid, year=end.year, month=end.month,
                                                          day__range=[0, end.day]).values("island_id").annotate(
            sum=Sum("nums"))
        sum_ = nums_this_Interval_1[0]['sum'] + nums_this_Interval_2[0]['sum']

    return sum_


def getIntervalWarnNums(start, end, scenicid):
    """

    :param start:
    :param end:
    :param scenicid:
    :return: 获得某岛的一段时间内的预警次数
    """
    start_str = str(start)[:10]
    # end = end + relativedelta(days=1)  # 因为是半闭合区间
    end_str = str(end)[:19]

    sum_ = 0
    result = Recordwarnings.objects.filter(scenicid=scenicid, createat__gte=start_str, createat__lte=end_str)
    for r in result:
        sum_ += 1

    return sum_


def getYouNeedInterval():
    """

    :return:获得本周起始时间，上一周起始时间，去年的本周起始时间，
            本月份起始时间，上一个月起始时间，去年本月起始时间
    """
    current_time = datetime.datetime.now()
    month_today = current_time
    month_start = current_time - relativedelta(days=current_time.day - 1)

    month_start_lastyear, month_today_lastyear = month_start - relativedelta(years=1), month_today - relativedelta(
        years=1)
    month_start_lastmonth, month_today_lastmonth = month_start - relativedelta(months=1), month_today - relativedelta(
        months=1)
    # 获得本月的起始时间，去年的本月起始时间，上个月的起始时间

    monday, sunday = get_current_week()
    sunday = current_time
    monday_lastyear, sunday_lastyear = monday - relativedelta(years=1), sunday - relativedelta(years=1)
    monday_lastweek, sunday_lastweek = monday - relativedelta(days=7), sunday - relativedelta(days=7)

    # 获得本周的起始时间，去年的本周起始时间，上周起始时间

    return monday, sunday, monday_lastweek, sunday_lastweek, monday_lastyear, sunday_lastyear, \
           month_start, month_today, month_start_lastmonth, month_today_lastmonth, month_start_lastyear, \
           month_today_lastyear


def getYearOverYearRate(nowDate, prevDate):
    """

    :param nowDate:
    :param prevDate:
    :return:返回同比增长率
    """
    return (nowDate - prevDate) / (nowDate + 1) * 100


def getMonthOverMonthRate(nowDate, prevDate):
    """

    :param nowDate:
    :param prevDate:
    :return: 返回环比增长率
    """
    return (nowDate - prevDate) / (prevDate + 1) * 100


def getScenicTouristNums(scenicid):
    """

    :param scenicid:
    :return: 得到某岛旅客人数
    """
    contexts = {}

    monday, sunday, monday_lastweek, sunday_lastweek, monday_lastyear, sunday_lastyear, \
    month_start, month_today, month_start_lastmonth, month_today_lastmonth, month_start_lastyear, \
    month_today_lastyear = getYouNeedInterval()

    # 获得本周的起始时间，去年的本周起始时间，上周起始时间
    # 本月份起始时间，上一个月起始时间，去年本月起始时间
    num_this_month = getIntervalTouristNums(month_start, month_today, scenicid)
    num_this_month_lastyear = getIntervalTouristNums(month_start_lastyear, month_today_lastyear, scenicid)
    num_this_month_lastmonth = getIntervalTouristNums(month_start_lastmonth, month_today_lastmonth, scenicid)
    # 通过getIntervalTouristNums获得本月份，去年本月份，上个月的游客人数

    month_yearOveryear_rate = getYearOverYearRate(num_this_month, num_this_month_lastyear)
    month_monthOvermonth_rate = getMonthOverMonthRate(num_this_month, num_this_month_lastmonth)
    contexts['month_yearOveryear_rate'] = month_yearOveryear_rate
    contexts['month_monthOvermonth_rate'] = month_monthOvermonth_rate
    contexts['num_this_month'] = num_this_month
    # 计算出月同比和环比增长率和环比率比保存到contexts中

    num_this_week = int(getIntervalTouristNums(monday, sunday, scenicid) * 1.5)
    num_this_week_lastyear = int(getIntervalTouristNums(monday_lastyear, sunday_lastyear, scenicid) * 1.5)
    num_this_week_lastweek = int(getIntervalTouristNums(monday_lastweek, sunday_lastweek, scenicid) * 1.5)
    # 通过getIntervalTouristNums获得本周，去年本周，上周的游客人数

    week_yearOveryear_rate = getYearOverYearRate(num_this_week, num_this_week_lastyear)
    week_weekOverweek_rate = getMonthOverMonthRate(num_this_week, num_this_week_lastweek)
    contexts['week_yearOveryear_rate'] = week_yearOveryear_rate
    contexts['week_weekOverweek_rate'] = week_weekOverweek_rate
    contexts['num_this_week'] = num_this_week
    # 计算出周的同比增长率和环比增长率并保存到contexts字典中

    return contexts


def getTouristNums():
    """
    游客人数模块，得到历史游客人数
    :return: context
    """
    context = {}
    # 当前时间
    current_time = datetime.datetime.now()
    # 所需时间
    time_dic = get_time_dic()
    query_time = str(current_time)[:10]
    query_time_yesterday = str(current_time - relativedelta(days=1))[:10]
    query_time_monday = str(time_dic['monday'])[:10]
    query_time_monday_lastweek = str(time_dic['last_monday'])[:10]
    monday_lastyear = time_dic['monday'] - relativedelta(years=1)
    query_time_monday_lastyear = str(monday_lastyear)[:10]
    # 去年同日期
    query_time_lastyear = str(current_time - relativedelta(years=1))[:10]
    with connection.cursor() as cursor:
        # 本日 数据来源：recordnums表
        query = "SELECT scenicName as scenic,SUM(nums) DIV 20 as nums FROM recordnums,scenic WHERE recordnums.scenicId = scenic.scenicId AND createAt LIKE %s AND createAt <= %s GROUP BY scenic.scenicId ORDER BY nums DESC"
        cursor.execute(query, [str(current_time)[:10] + '%', str(current_time)[:19]])
        scenicrank_data = json.loads(json.dumps(dictfetchall(cursor), cls=DecimalEncoder))
        rn_sum_day_new = int(sum([x['nums'] for x in scenicrank_data]))

        # 本日 数据来源：mobile表
        # 查询本日游客人数
        query = "SELECT todayDividual as rn_sum_day FROM mobile WHERE ticketDate = %s"
        cursor.execute(query, [query_time])
        rn_sum_day = int(dictfetchall(cursor)[0]['rn_sum_day'])
        # 查询昨天游客人数
        query = "SELECT todayDividual as rn_sum_day_yesterday FROM mobile WHERE ticketDate = %s"
        cursor.execute(query, [query_time_yesterday])
        rn_sum_day_yesterday = int(dictfetchall(cursor)[0]['rn_sum_day_yesterday'])
        # 查询上一年本日游客人数
        query = "SELECT todayDividual as rn_sum_day_lastyear FROM mobile WHERE ticketDate = %s"
        cursor.execute(query, [query_time_lastyear])
        rn_sum_day_lastyear = int(dictfetchall(cursor)[0]['rn_sum_day_lastyear'])

        # 本周
        # 查询本周游客人数
        query = "select SUM(todayTotal) as rn_sum_week FROM mobile WHERE ticketDate >= %s AND ticketDate <= %s"
        cursor.execute(query, [query_time_monday, query_time])
        rn_sum_week = int(dictfetchall(cursor)[0]['rn_sum_week'])
        # 查询上一周游客人数
        query = "SELECT SUM(todayTotal) as rn_sum_week_lastweek FROM mobile WHERE ticketDate >= %s AND ticketDate <= %s"
        query_time_lastweek = str(current_time - relativedelta(weeks=1))[:10]
        cursor.execute(query, [query_time_monday_lastweek, query_time_lastweek])
        rn_sum_week_lastweek = int(dictfetchall(cursor)[0]['rn_sum_week_lastweek'])
        # 查询上一年本周游客人数
        query = "SELECT SUM(todayTotal) as rn_sum_week_lastyear FROM mobile WHERE ticketDate >= %s AND ticketDate <= %s"
        cursor.execute(query, [query_time_monday_lastyear, query_time_lastyear])
        rn_sum_week_lastyear = int(dictfetchall(cursor)[0]['rn_sum_week_lastyear'])

        # 本月
        # 查询本月游客人数
        query = "SELECT SUM(todayTotal) as rn_sum_month FROM mobile WHERE `year`=%s AND `month`=%s AND `day`<=%s"
        cursor.execute(query, [current_time.year, current_time.month, current_time.day])
        # cursor.execute(query, [2020, 1, 6])
        rn_sum_month = int(dictfetchall(cursor)[0]['rn_sum_month'])
        # 查询上一月游客人数
        query = "SELECT SUM(todayTotal) as rn_sum_month_lastmonth FROM mobile WHERE `year`=%s AND `month`=%s AND `day`<=%s"
        cursor.execute(query, [time_dic['lastmonth_year'], time_dic['lastmonth_month'], time_dic['lastmonth_day']])
        # cursor.execute(query, [2019, 12, 6])
        rn_sum_month_lastmonth = int(dictfetchall(cursor)[0]['rn_sum_month_lastmonth'])
        # 查询上一年本月游客人数
        query = "SELECT SUM(todayTotal) as rn_sum_month_lastyear FROM mobile WHERE `year`=%s AND `month`=%s AND `day`<=%s"
        cursor.execute(query, [current_time.year - 1, current_time.month, current_time.day])
        # cursor.execute(query, [2019, 1, 6])
        rn_sum_month_lastyear = int(dictfetchall(cursor)[0]['rn_sum_month_lastyear'])

        context['rn_sum_day'] = rn_sum_day_new
        context['rn_sum_day_dod'] = (rn_sum_day - rn_sum_day_yesterday) / (rn_sum_day_yesterday + 1) * 100
        context['rn_sum_day_yoy'] = (rn_sum_day - rn_sum_day_lastyear) / (rn_sum_day_lastyear + 1) * 100
        context['rn_sum_week'] = rn_sum_week * 8
        context['rn_sum_week_wow'] = (rn_sum_week - rn_sum_week_lastweek) / (rn_sum_week_lastweek + 1) * 100
        context['rn_sum_week_yoy'] = (rn_sum_week - rn_sum_week_lastyear) / (rn_sum_week_lastyear + 1) * 100
        context['rn_sum_month'] = rn_sum_month * 4
        context['rn_sum_month_mom'] = (rn_sum_month - rn_sum_month_lastmonth) / (rn_sum_month_lastmonth + 1) * 100
        context['rn_sum_month_yoy'] = (rn_sum_month - rn_sum_month_lastyear) / (rn_sum_month_lastyear + 1) * 100
    return context


def getScenicWarntNums(scenicid):
    contexts = {}

    monday, sunday, monday_lastweek, sunday_lastweek, monday_lastyear, sunday_lastyear, \
    month_start, month_today, month_start_lastmonth, month_today_lastmonth, month_start_lastyear, \
    month_today_lastyear = getYouNeedInterval()
    # 获得本周的起始时间，去年的本周起始时间，上周起始时间
    # 本月份起始时间，上一个月起始时间，去年本月起始时间

    num_this_month = getIntervalWarnNums(month_start, month_today, scenicid)
    num_this_month_lastyear = getIntervalWarnNums(month_start_lastyear, month_today_lastyear, scenicid)
    num_this_month_lastmonth = getIntervalWarnNums(month_start_lastmonth, month_today_lastmonth, scenicid)
    # 通过getIntervalWarnNums获得本月份，去年本月份，上个月的预警次数

    month_yearOveryear_rate_warn = getYearOverYearRate(num_this_month, num_this_month_lastyear)
    month_monthOvermonth_rate_warn = getMonthOverMonthRate(num_this_month, num_this_month_lastmonth)
    contexts['month_yearOveryear_rate_warn'] = month_yearOveryear_rate_warn
    contexts['month_monthOvermonth_rate_warn'] = month_monthOvermonth_rate_warn
    contexts['num_this_month_warn'] = num_this_month
    # 计算出月同比和环比增长率和环比率比保存到contexts中

    num_this_week = getIntervalWarnNums(monday, sunday, scenicid)
    num_this_week_lastyear = getIntervalWarnNums(monday_lastyear, sunday_lastyear, scenicid)
    num_this_week_lastweek = getIntervalWarnNums(monday_lastweek, sunday_lastweek, scenicid)
    # 通过getIntervalWarnNums获得本周，去年本周，上周的游客人数

    week_yearOveryear_rate_warn = getYearOverYearRate(num_this_week, num_this_week_lastyear)
    week_weekOverweek_rate_warn = getMonthOverMonthRate(num_this_week, num_this_week_lastweek)
    contexts['week_yearOveryear_rate_warn'] = week_yearOveryear_rate_warn
    contexts['week_weekOverweek_rate_warn'] = week_weekOverweek_rate_warn
    contexts['num_this_week_warn'] = num_this_week
    # 计算出周的同比增长率和环比增长率并保存到contexts字典中

    return contexts


def getWarnNums():
    """
    预警次数模块，得到历史预警次数
    :return: context
    """
    context = {}
    # 当前时间
    current_time = datetime.datetime.now()
    # 所需时间
    time_dic = get_time_dic()
    # query_time = '2019-11-15'
    # query_time_yesterday = '2019-11-14'
    query_time = str(current_time)[:19]
    query_time2 = str(current_time)[:10]
    query_time_yesterday = str(current_time - relativedelta(days=1))[:19]
    query_time_yesterday2 = str(current_time - relativedelta(days=1))[:10]
    # 去年同日期
    # query_time_lastyear = '2018-11-15'
    query_time_lastyear = str(current_time - relativedelta(years=1))[:19]
    query_time_lastyear2 = str(current_time - relativedelta(years=1))[:10]
    # 周
    query_time_monday = str(time_dic['monday'])[:10]
    query_time_monday_lastweek = str(time_dic['last_monday'])[:10]
    monday_lastyear = time_dic['monday'] - relativedelta(years=1)
    query_time_monday_lastyear = str(monday_lastyear)[:10]
    with connection.cursor() as cursor:
        # # 查询本日预警次数
        # query = "SELECT COUNT(warningId) as rw_count_day FROM recordwarnings WHERE createAt <= %s AND createAt >= %s;"
        # cursor.execute(query, [query_time, query_time2])
        # rw_count_day = dictfetchall(cursor)[0]['rw_count_day']
        # # 查询昨天预警次数
        # query = "SELECT COUNT(warningId) as rw_count_day_lastday FROM recordwarnings WHERE createAt <= %s AND createAt >= %s;"
        # cursor.execute(query, [query_time_yesterday, query_time_yesterday2])
        # rw_count_day_lastday = dictfetchall(cursor)[0]['rw_count_day_lastday']
        # # 查询上一年本日预警次数
        # query = "SELECT COUNT(warningId) as rw_count_day_lastyear FROM recordwarnings WHERE createAt <= %s AND createAt >= %s;"
        # cursor.execute(query, [query_time_lastyear, query_time_lastyear2])
        # rw_count_day_lastyear = dictfetchall(cursor)[0]['rw_count_day_lastyear']

        # 查询本周预警次数
        query = "SELECT COUNT(warningId) as rw_count_week FROM recordwarnings WHERE createAt >= %s AND createAt <= %s;"
        cursor.execute(query, [query_time_monday, query_time])
        rw_count_week = dictfetchall(cursor)[0]['rw_count_week']
        # 查询上一周预警次数
        query = "SELECT COUNT(warningId) as rw_count_week_lastweek FROM recordwarnings WHERE createAt >= %s AND createAt <= %s;"
        query_time_lastweek = str(current_time - relativedelta(weeks=1))[:19]
        cursor.execute(query, [query_time_monday_lastweek, query_time_lastweek])
        rw_count_week_lastweek = dictfetchall(cursor)[0]['rw_count_week_lastweek']
        # 查询去年本周预警次数
        query = "SELECT COUNT(warningId) as rw_count_week_lastyear FROM recordwarnings WHERE createAt >= %s AND createAt <= %s;"
        query_time_lastyear = str(current_time - relativedelta(years=1))[:19]
        cursor.execute(query, [query_time_monday_lastyear, query_time_lastyear])
        rw_count_week_lastyear = dictfetchall(cursor)[0]['rw_count_week_lastyear']

        # 查询本月预警次数
        query = "SELECT COUNT(warningId) as rw_count_month FROM recordwarnings WHERE createAt LIKE %s AND createAt <= %s;"
        cursor.execute(query, [str(current_time)[:7] + '%', query_time])
        rw_count_month = dictfetchall(cursor)[0]['rw_count_month']
        # 查询上一月预警次数
        query = "SELECT COUNT(warningId) as rw_count_month_lastmonth FROM recordwarnings WHERE createAt LIKE %s AND createAt <= %s;"
        cursor.execute(query, [str(time_dic['lastmonth'])[:7] + '%', query_time])
        rw_count_month_lastmonth = dictfetchall(cursor)[0]['rw_count_month_lastmonth']
        # 查询本月预警次数
        query = "SELECT COUNT(warningId) as rw_count_month_lastyear FROM recordwarnings WHERE createAt LIKE %s AND createAt <= %s;"
        cursor.execute(query, [str(current_time - relativedelta(years=1))[:7] + '%', query_time])
        rw_count_month_lastyear = dictfetchall(cursor)[0]['rw_count_month_lastyear']

        # context['rw_count_day'] = rw_count_day
        # context['rw_count_day_dod'] = (rw_count_day - rw_count_day_lastday) / (rw_count_day_lastday + 1) * 100
        # context['rw_count_day_yoy'] = (rw_count_day - rw_count_day_lastyear) / (rw_count_day_lastyear + 1) * 100
        context['rw_count_week'] = rw_count_week
        context['rw_count_week_wow'] = (rw_count_week - rw_count_week_lastweek) / (rw_count_week_lastweek + 1) * 100
        context['rw_count_week_yoy'] = (rw_count_week - rw_count_week_lastyear) / (rw_count_week_lastyear + 1) * 100
        context['rw_count_month'] = rw_count_month
        context['rw_count_month_mom'] = (rw_count_month - rw_count_month_lastmonth) / (
                rw_count_month_lastmonth + 1) * 100
        context['rw_count_month_yoy'] = (rw_count_month - rw_count_month_lastyear) / (rw_count_month_lastyear + 1) * 100
    return context


def getScenicPlaceRank_week(scenicid_):
    """

    :param scenicid:
    :return: 获得某一个岛屿本周人数排行
    """
    current_time = datetime.datetime.now()
    monday, sunday = get_current_week()
    week_end = current_time + relativedelta(days=1)
    week_end_str = str(week_end)[:10]
    week_start_str = str(monday)[:10]
    # 获得本月起始时间与当前时间的字符串形式

    result = Recordnums.objects.filter(scenicid=scenicid_, createat__gt=week_start_str,
                                       createat__lt=week_end_str).values('camid').annotate(
        sun_num=Sum("nums")).order_by('sun_num')
    # 获得代号为scenicid_岛的各个摄像头的本月人流量

    tourist_num = []
    places = []
    for r in result:
        tourist_num.append(r['sun_num'])
        place = Camera.objects.filter(scenicid=scenicid_, camid=r['camid']).values('camplace')[0]['camplace']
        places.append(place)
    # 因为利用直方图来显示的时候需要categories和date，所以将其分别放入places和tourist_num
    scenicplacerankweek_context = {'place_week_rank': places, 'nums_week_rank': tourist_num}
    return scenicplacerankweek_context


def getScenicPlaceRank(scenicid_):
    """
    得到某一个岛的本月从月初到现在的游客人数排行榜
    :param scenicid_:
    :return: {'data':[data]},{'places':[placename]}
    """
    current_time = datetime.datetime.now()
    month_start = current_time - relativedelta(days=current_time.day - 1)
    month_end = current_time + relativedelta(days=1)
    month_end_str = str(month_end)[:10]
    month_start_str = str(month_start)[:10]
    # 获得本月起始时间与当前时间的字符串形式

    result = Recordnums.objects.filter(scenicid=scenicid_, createat__gt=month_start_str,
                                       createat__lt=month_end_str).values('camid').annotate(
        sun_num=Sum("nums")).order_by('sun_num')
    # 获得代号为scenicid_岛的各个摄像头的本月人流量

    tourist_num = []
    places = []
    for r in result:
        tourist_num.append(r['sun_num'])
        place = Camera.objects.filter(scenicid=scenicid_, camid=r['camid']).values('camplace')[0]['camplace']
        places.append(place)
    # 因为利用直方图来显示的时候需要categories和date，所以将其分别放入places和tourist_num
    scenicplacerank_context = {'place_month_rank': places, 'nums_month_rank': tourist_num}
    return scenicplacerank_context


def getScenicRank():
    """
    景区人数排行模块
    :return: context:{'scenicrank_data':[{'scenic':'景区1','nums':人数2},...]}
    """
    context = {}
    # 当前时间
    current_time = datetime.datetime.now()
    with connection.cursor() as cursor:
        query = "SELECT scenicName as scenic,SUM(nums) DIV 20 as nums FROM recordnums,scenic WHERE recordnums.scenicId = scenic.scenicId AND createAt LIKE %s AND createAt <= %s GROUP BY scenic.scenicId ORDER BY nums DESC"
        cursor.execute(query, [str(current_time)[:10] + '%', str(current_time)[:19]])
        scenicrank_data = json.loads(json.dumps(dictfetchall(cursor), cls=DecimalEncoder))
        context['scenicrank_data'] = SafeString(scenicrank_data)
    return context


# def getScenicRank():
#     """
#     景区人数排行模块
#     :return: context:{'scenicrank_data':[{'scenic':'景区1','nums':人数2},...]}
#     """
#     context = {}
#     # 当前时间
#     current_time = datetime.datetime.now()
#     rank_data = []
#     with connection.cursor() as cursor:
#         query = "SELECT centerDividual,eastsouthDividual,forestBar,lionCity FROM mobile WHERE ticketDate = %s;"
#         cursor.execute(query, [str(current_time)[:10]])
#         scenicrank_data = json.loads(json.dumps(dictfetchall(cursor), cls=DecimalEncoder))
#         scenic_dic = scenicrank_data[0]
#         scenic_dic = sorted(scenic_dic.items(), key=lambda x: x[1], reverse=True)
#         for scenic in scenic_dic:
#             if scenic[0] == 'centerDividual':
#                 scenic_name = '千岛湖中心湖区'
#             elif scenic[0] == 'eastsouthDividual':
#                 scenic_name = '千岛湖东南湖区'
#             elif scenic[0] == 'lionCity':
#                 scenic_name = '文渊狮城'
#             elif scenic[0] == 'forestBar':
#                 scenic_name = '森林氧吧'
#             rank_data.append({'scenic': scenic_name, 'nums': int(scenic[1]) * 8})
#         rank_data.sort(key=lambda x: x['nums'], reverse=True)
#         context['scenicrank_data'] = SafeString(rank_data)
#     return context


def getScenicRankByScenic():
    """
    景区人数排行模块
    :return: context:{'scenicrank_data':[{'scenic':'景区1','nums':人数2},...]}
    """
    context = {}
    # 当前时间
    current_time = datetime.datetime.now()
    with connection.cursor() as cursor:
        # 查询本月游客人数
        query = "SELECT scenicName as scenic,SUM(nums) as nums FROM recordnums,scenic WHERE recordnums.scenicId = scenic.scenicId AND createAt LIKE %s GROUP BY scenic.scenicId ORDER BY scenic"
        cursor.execute(query, [str(current_time)[:10] + '%'])
        scenicrank_data = json.loads(json.dumps(dictfetchall(cursor), cls=DecimalEncoder))
        context['scenicrank_bysce_data'] = SafeString(scenicrank_data)
    return context


def getWarnRank1():
    """
    预警次数排行模块
    :return: context:{'warnrank_data':[{'景区1':次数1,'景区2':次数2},...]}
    """
    context = {}
    # 当前时间
    current_time = datetime.datetime.now()
    # current_time = '2019-11-15'
    with connection.cursor() as cursor:
        query = "SELECT scenicName AS scenic,COUNT(recordwarnings.scenicId) as times FROM recordwarnings,scenic WHERE recordwarnings.scenicId = scenic.scenicId AND `level` = '1' AND createAt LIKE %s AND createAt <= %s GROUP BY scenic.scenicId ORDER BY times DESC"
        cursor.execute(query, [str(current_time)[:10] + '%', str(current_time)[:19]])
        warnrank_data = json.loads(json.dumps(dictfetchall(cursor), cls=DecimalEncoder))
        context['warnrank1_data'] = SafeString(warnrank_data)
    return context


def getWarnRank2():
    """
    预警次数排行模块
    :return: context:{'warnrank_data':[{'景区1':次数1,'景区2':次数2},...]}
    """
    context = {}
    # 当前时间
    current_time = datetime.datetime.now()
    # current_time = '2019-11-15'
    with connection.cursor() as cursor:
        query = "SELECT scenicName AS scenic,COUNT(recordwarnings.scenicId) as times FROM recordwarnings,scenic WHERE recordwarnings.scenicId = scenic.scenicId AND `level` = '2' AND createAt LIKE %s AND createAt <= %s GROUP BY scenic.scenicId ORDER BY times DESC"
        cursor.execute(query, [str(current_time)[:10] + '%', str(current_time)[:19]])
        warnrank_data = json.loads(json.dumps(dictfetchall(cursor), cls=DecimalEncoder))
        context['warnrank2_data'] = SafeString(warnrank_data)
    return context


def getWarnRank3():
    """
    预警次数排行模块
    :return: context:{'warnrank_data':[{'景区1':次数1,'景区2':次数2},...]}
    """
    context = {}
    # 当前时间
    current_time = datetime.datetime.now()
    # current_time = '2019-11-15'
    with connection.cursor() as cursor:
        query = "SELECT scenicName AS scenic,COUNT(recordwarnings.scenicId) as times FROM recordwarnings,scenic WHERE recordwarnings.scenicId = scenic.scenicId AND `level` = '3' AND createAt LIKE %s AND createAt <= %s GROUP BY scenic.scenicId ORDER BY times DESC"
        cursor.execute(query, [str(current_time)[:10] + '%', str(current_time)[:19]])
        warnrank_data = json.loads(json.dumps(dictfetchall(cursor), cls=DecimalEncoder))
        context['warnrank3_data'] = SafeString(warnrank_data)
    return context


def getWarnRankByScenic():
    """
    预警次数排行模块
    :return: context:{'warnrank_data':[{'景区1':次数1,'景区2':次数2},...]}
    """
    context = {}
    # 当前时间
    current_time = datetime.datetime.now()
    with connection.cursor() as cursor:
        # 查询本月游客人数
        query = "SELECT scenicName AS scenic,COUNT(recordwarnings.scenicId) as times FROM recordwarnings,scenic WHERE recordwarnings.scenicId = scenic.scenicId AND createAt LIKE %s GROUP BY scenic.scenicId ORDER BY scenic"
        cursor.execute(query, [str(current_time)[:7] + '%'])
        warnrank_data = json.loads(json.dumps(dictfetchall(cursor), cls=DecimalEncoder))
        context['warnrank_bysce_data'] = SafeString(warnrank_data)
    return context


def getNumBarByMonth():
    """
    景区人数变化模块

    """
    context = {}
    # 当前时间
    current_time = datetime.datetime.now()
    with connection.cursor() as cursor:
        # 查询本月游客人数
        query = "SELECT CONCAT(CONCAT(`year`,'-'),`month`) as 'date',SUM(nums) as nums FROM recordnums WHERE `year`=%s GROUP BY `year`,`month` ORDER BY `year` DESC,`month` DESC LIMIT 8"
        cursor.execute(query, [str(current_time.year)])
        numbar_data = json.loads(json.dumps(dictfetchall(cursor), cls=DecimalEncoder))
        query = "SELECT CONCAT(CONCAT(`year`,'-'),`month`) as 'date',SUM(nums) as nums_lastyear FROM recordnums WHERE `year`=%s GROUP BY `year`,`month` ORDER BY `year` DESC,`month` DESC LIMIT 8"
        cursor.execute(query, [str(current_time.year - 1)])
        numbar_data_lastyear = json.loads(json.dumps(dictfetchall(cursor), cls=DecimalEncoder))
        for i in range(len(numbar_data)):
            numbar_data[i]['nums_lastyear'] = numbar_data_lastyear[i]['nums_lastyear']
        context['numbar_data_bymonth'] = SafeString(numbar_data)
    return context


def getNumBarByDay():
    """
    景区人数变化模块

    """
    context = {}
    # 当前时间
    current_time = datetime.datetime.now()
    with connection.cursor() as cursor:
        query = "SELECT CONCAT(`year`,'-',`month`,'-',`day`) as 'date',SUM(nums) as nums FROM recordnums WHERE `year` = %s GROUP BY `year`,`month`,`day` HAVING STR_TO_DATE(date,'%%Y-%%m-%%d')<= STR_TO_DATE(%s,'%%Y-%%m-%%d') ORDER BY STR_TO_DATE(date,'%%Y-%%m-%%d') DESC LIMIT 8"
        cursor.execute(query, [str(current_time.year), str(current_time)[:10]])
        numbar_data = json.loads(json.dumps(dictfetchall(cursor), cls=DecimalEncoder))
        query = "SELECT CONCAT(`year`,'-',`month`,'-',`day`) as 'date',SUM(nums) as nums_lastyear FROM recordnums WHERE `year` = %s GROUP BY `year`,`month`,`day` HAVING STR_TO_DATE(date,'%%Y-%%m-%%d')<= STR_TO_DATE(%s,'%%Y-%%m-%%d') ORDER BY STR_TO_DATE(date,'%%Y-%%m-%%d') DESC LIMIT 8"
        cursor.execute(query, [str(current_time.year - 1), str(current_time - relativedelta(years=1))[:10]])
        numbar_data_lastyear = json.loads(json.dumps(dictfetchall(cursor), cls=DecimalEncoder))
        for i in range(len(numbar_data)):
            numbar_data[i]['nums_lastyear'] = numbar_data_lastyear[i]['nums_lastyear']
        context['numbar_data_byday'] = SafeString(numbar_data)
    return context


def adjustTime(time_str):
    """
    str: 2019-11-20 16:23
    return: 2019-11-20 16:20
    """
    minute = int(time_str[-2:])
    minute = minute - minute % 10
    return time_str[:-2] + str(minute)


def getNumBarByMin():
    """
    景区人数变化模块

    """
    context = {}
    # 当前时间
    current_time = datetime.datetime.now()
    with connection.cursor() as cursor:
        query = "SELECT scenicName as scenic,SUM(nums) as nums,scenic.limitNums FROM recordnums,scenic WHERE recordnums.scenicId = scenic.scenicId AND createAt LIKE %s GROUP BY recordnums.scenicId ORDER BY limitNums DESC"
        cursor.execute(query, [adjustTime(str(current_time)[:16]) + '%'])
        numbar_data = json.loads(json.dumps(dictfetchall(cursor), cls=DecimalEncoder))
        for i in range(len(numbar_data)):
            numbar_data[i]['ratio'] = round(numbar_data[i]['nums'] / numbar_data[i]['limitNums'], 2)
        context['numbar_data_bymin'] = numbar_data
    return context


def updateNumbar(request):
    context = getNumBarByMin()
    numbar_data = json.dumps(context, ensure_ascii=False)
    return HttpResponse(numbar_data)


def getCurrentWarn():
    """
    当前预警信息模块

    """
    context = {}
    # 当前时间
    current_time = datetime.datetime.now()
    # current_time = '2019-11-15 10:30'
    with connection.cursor() as cursor:
        query = "SELECT * FROM (SELECT scenic.scenicId,warningId,scenicName,camera.camId,`level`,`type`,exceedNums,substring(createAt,12,5) as createAtMin,createAt,recordwarnings.state FROM scenic,recordwarnings,camera WHERE recordwarnings.scenicId = scenic.scenicId AND recordwarnings.scenicId = camera.scenicId AND recordwarnings.camId = camera.camId AND createAt <= %s AND createAt >= %s ORDER BY createAt DESC LIMIT 7) temp ORDER BY temp.`level`"
        cursor.execute(query, [str(current_time)[:19], str(current_time)[:10]])
        curwarn_data = json.loads(json.dumps(dictfetchall(cursor), cls=DecimalEncoder))
        context['curwarn'] = curwarn_data
    return context


def updateCurrentWarn(request):
    context = getCurrentWarn()
    curwarn = json.dumps(context, ensure_ascii=False)
    return HttpResponse(curwarn)


def getHeatMapNums(request):
    # 封装json
    res_json = [{}]
    # 景区信息表
    scenic_data = Scenic.objects.all()
    scenic_data_seri = serializers.serialize("json", scenic_data)
    scenic_data = json.loads(scenic_data_seri)
    res_json[0]['scenic_data'] = scenic_data
    # 人数记录表
    query_time = str(datetime.datetime.now())[0:16]
    # query_time = '2019-11-15 10:30'

    with connection.cursor() as cursor:
        query = "SELECT recordnums.scenicId,recordnums.camId,SUM(nums) AS all_nums,camLng,camLat FROM recordnums,camera WHERE recordnums.camId = camera.camId AND recordnums.scenicId = camera.scenicId AND recordnums.createAt LIKE %s GROUP BY recordnums.scenicId,recordnums.camId"
        cursor.execute(query, [adjustTime(query_time) + '%'])
        rn_data = json.loads(json.dumps(dictfetchall(cursor), cls=DecimalEncoder))
        res_json[0]['rn_data'] = rn_data
    res_json_seri = json.dumps(res_json)
    return HttpResponse(res_json_seri)


def getHeatMapScenic(request):
    # 封装json
    res_json = [{}]
    query_time = str(datetime.datetime.now())[0:16]
    # query_time = '2019-11-15 11:10'
    with connection.cursor() as cursor:
        query = "SELECT scenic.scenicId,scenic.scenicName,SUM(nums) as nums,warning1Nums,warning2Nums,warning3Nums,lng,lat FROM scenic,recordnums " \
                "WHERE scenic.scenicId = recordnums.scenicId AND createAt LIKE %s GROUP BY scenicId"
        cursor.execute(query, [adjustTime(query_time) + '%'])
        rn_data = json.loads(json.dumps(dictfetchall(cursor), cls=DecimalEncoder))
        res_json[0]['rn_data'] = rn_data
    res_json_seri = json.dumps(res_json)
    return HttpResponse(res_json_seri)


def getHeatMapCamera(request):
    # 封装json
    res_json = [{}]
    with connection.cursor() as cursor:
        query = "SELECT * FROM camera WHERE camId!=0"
        cursor.execute(query)
        camera_data = json.loads(json.dumps(dictfetchall(cursor), cls=DecimalEncoder))
        res_json[0]['camera_data'] = camera_data
    res_json_seri = json.dumps(res_json)
    return HttpResponse(res_json_seri)


def index(request):
    """
    跳转至 index.html

    """
    username = request.session.get('username', '')
    if not username:
        return redirect('/login/')
    # 参数
    context = {}
    # 游客人数模块
    print('游客人数模块')
    tourist_context = getTouristNums()
    context.update(tourist_context)
    # 预警次数模块
    print('预警次数模块')
    warnnums_context = getWarnNums()
    context.update(warnnums_context)
    # 人数排行模块
    print('景区人数排行模块')
    scenicrank_context = getScenicRank()
    context.update(scenicrank_context)
    # 预警排行模块
    print('预警排行模块')
    warnrank1_context = getWarnRank1()
    context.update(warnrank1_context)
    warnrank2_context = getWarnRank2()
    context.update(warnrank2_context)
    warnrank3_context = getWarnRank3()
    context.update(warnrank3_context)
    warnrank_bysce_context = getWarnRankByScenic()
    context.update(warnrank_bysce_context)
    # 景区人数变化模块
    print('景区人数变化模块')
    # numbar_context_month = getNumBarByMonth()
    # context.update(numbar_context_month)
    # numbar_context_day = getNumBarByDay()
    # context.update(numbar_context_day)
    # numbar_context_min = getNumBarByMin()
    # context.update(numbar_context_min)
    # 当前预警信息模块
    print('当前预警信息模块')
    curwarn_context = getCurrentWarn()
    context.update(curwarn_context)
    # 今天日期
    context['today2day'] = str(datetime.datetime.now())[:10]
    context['today2min'] = str(datetime.datetime.now())[:16]
    return render(request, 'index.html', context=context)


def meifeng(request):
    """
    :param request:
    :return: 返回梅峰岛景区信息
    """
    username = request.session.get('username', '')
    if not username:
        return redirect('/login/')
    context = getScenicContext(1)
    return render(request, 'mf_scenic.html', context=context)


def huangshanjian(request):
    """

    :param request:
    :return: 返回黄山尖景区信息
    """
    username = request.session.get('username', '')
    if not username:
        return redirect('/login/')
    context = getScenicContext(2)
    return render(request, 'hs_scenic.html', context=context)


def tianchi(request):
    """

    :param request:
    :return: 返回天池岛景区信息
    """
    username = request.session.get('username', '')
    if not username:
        return redirect('/login/')
    context = getScenicContext(3)
    return render(request, 'tc_scenic.html', context=context)


def yueguang(request):
    """

    :param request:
    :return: 返回月光岛景区信息
    """
    username = request.session.get('username', '')
    if not username:
        return redirect('/login/')
    context = getScenicContext(4)
    return render(request, 'yg_scenic.html', context=context)


def longshan(request):
    """

    :param request:
    :return: 返回龙山岛景区信息
    """
    username = request.session.get('username', '')
    if not username:
        return redirect('/login/')
    context = getScenicContext(5)
    return render(request, 'longshan_scenic.html', context=context)


def yule(request):
    """

    :param request:
    :return: 返回渔乐岛景区信息
    """
    username = request.session.get('username', '')
    if not username:
        return redirect('/login/')
    context = getScenicContext(6)
    return render(request, 'yl_scenic.html', context=context)


def guihua(request):
    """

    :param request:
    :return: 返回桂花岛景区信息
    """
    username = request.session.get('username', '')
    if not username:
        return redirect('/login/')
    context = getScenicContext(7)
    return render(request, 'gh_scenic.html', context=context)


def mishan(request):
    """

    :param request:
    :return: 返回蜜山岛信息
    """
    username = request.session.get('username', '')
    if not username:
        return redirect('/login/')
    context = getScenicContext(8)
    return render(request, 'ms_scenic.html', context=context)


def getScenicContext(scenicid_):
    context = {}

    # 岛屿参数
    info_context = getScenicInfo(scenicid_)
    context.update(info_context)
    # 游客人数模块
    tourist_context = getScenicTouristNums(scenicid_)
    context.update(tourist_context)
    # 预警次数模块
    warnnums_context = getScenicWarntNums(scenicid_)
    context.update(warnnums_context)
    # 本月人数排行模块
    scenicplacerank_context = getScenicPlaceRank(scenicid_)
    context.update(scenicplacerank_context)
    # 本周人数排行模块
    scenicplacerankweek_context = getScenicPlaceRank_week(scenicid_)
    context.update(scenicplacerankweek_context)
    # 景区人数变化模块
    numbar_context = todayTouristNumChangeStart(scenicid_)
    context.update(numbar_context)
    # 当前预警信息模块
    print('当前预警信息模块')
    curwarn_context = getCurrentWarn()
    context.update(curwarn_context)
    # 今天日期
    context['today2day'] = str(datetime.datetime.now())[:10]
    context['today2min'] = str(datetime.datetime.now())[:16]
    # 游客人数分布模块
    distribute_context = getTouristDistribute(scenicid_)
    context.update(distribute_context)

    return context


def getScenicHeartMapData(request):
    """

    :param request:
    :return:根据request中的scenicid返回对应岛屿的热度图
    """
    _scenicid = request.GET['_scenicid']  # 后台发送json请求时，附带上岛屿的编号
    _scenicid = int(_scenicid)
    result = Recordnums.objects.values("scenicid", "camid").annotate(latest=Max("id")).filter(scenicid=_scenicid)
    # select scenicid,camid,Max('id') as latest from recordnums where scenucud=1 group by scenicid,camid
    # 因为最新插入的数据id是肯定比之前的大的，所有我们先找到指定岛指定摄像头的数据的最大id

    result_latest = []
    # 存储某一个岛所有摄像头的最新数据
    for i in result:
        # i表示某一个摄像头的数据
        latest_id = i['latest']
        # latest_id 表示i这个摄像头的最新数据的id
        # 字典的访问是i['latest']不是i.latest
        select_latest_nums = Recordnums.objects.filter(id=latest_id).values("scenicid", "id", "camid",
                                                                            "nums")
        # 根据最新数据的id来查询Recordnums表，获得人数
        select_latest_nums = select_latest_nums[0]
        # 查询结果是一个list，即使结果只有一个，所以需要[0]
        num = select_latest_nums['nums']
        sceid = select_latest_nums['scenicid']
        cid = select_latest_nums['camid']
        # 获得最新数据的人数num，岛屿id，摄像头id以便查询该摄像头的经纬度
        select_latest_point = Camera.objects.filter(scenicid=sceid, camid=cid).values("camlng", "camlat")
        # 查询Camera表获得经纬度
        result_send = {}
        result_send["count"] = num
        result_send["lng"] = select_latest_point[0]['camlng']
        result_send["lat"] = select_latest_point[0]['camlat']
        # 按照热力图需要的数据格式存入字典
        result_latest.append(result_send)
        # 将各个摄像头的数据存入result_latest

    return JsonResponse(result_latest, safe=False, json_dumps_params={'ensure_ascii': False})


def todayTouristNumChangeStart(scenicid):
    start_data = getTodayIntervalTouristNums(scenicid)
    start_data_week = getThisWeekTouristNums(scenicid)
    start_data_month = getThisMonthTouristNums(scenicid)
    context = {'start_data': start_data, 'start_data_week': start_data_week, 'start_data_month': start_data_month,
               'start_data_len': len(start_data), 'start_data_week_len': len(start_data_week),
               'start_data_month_len': len(start_data_month)}
    return context


def getThisWeekTouristNums(scencicid=1):
    """

    :param scencicid:
    :return: 返回本周内人数
    """
    monday, sunday = get_current_week()
    monday = monday + relativedelta(days=1)
    today = datetime.datetime.now()

    result = Recordnums.objects.filter(scenicid=scencicid, day__gte=monday.day, day__lte=today.day \
                                       , year__gte=monday.year, year__lte=today.year, \
                                       month__gte=monday.month, month__lte=today.month).values('year', 'month',
                                                                                               'day').annotate(
        weeknums=Sum('nums')).order_by('-year', '-month', '-day')
    result_send = []
    for i, r in enumerate(result):
        nums = r['weeknums'] // 20
        timeArray = time.strptime(str(r['year']) + '-' + str(r['month']) + '-' + str(r['day']), '%Y-%m-%d')
        timeStamp = int(time.mktime(timeArray)) * 1000
        result_item = [timeStamp, nums]
        result_send.append(result_item)
    return result_send


def getThisMonthTouristNums(scencicid=1):
    """

    :param scencicid:
    :return: 返回本月份内人数
    """

    today = datetime.datetime.now()
    start = today - relativedelta(days=today.day - 1)
    result = Recordnums.objects.filter(scenicid=scencicid, day__gte=start.day, day__lte=today.day \
                                       , year__gte=start.year, year__lte=today.year, month__gte=start.month,
                                       month__lte=today.month).values('year', 'month', 'day').annotate(
        weeknums=Sum('nums')).order_by('-year', '-month', '-day')
    result_send = []
    for r in result:
        nums = r['weeknums'] // 20
        timeArray = time.strptime(str(r['year']) + '-' + str(r['month']) + '-' + str(r['day']), '%Y-%m-%d')
        timeStamp = int(time.mktime(timeArray)) * 1000
        result_item = [timeStamp, nums]
        result_send.append(result_item)
    return result_send


def getTodayIntervalTouristNums(scenicid_=1):
    """

    :return: 返回当前时间到1小时前的间隔内的数据
    """
    today_now = datetime.datetime.now()
    # 在展示demo的时候我们只展示9-28的数据。部署的时候再来具体更改
    today_start = today_now - relativedelta(minutes=60)
    today_start_str = str(today_start)[:19]
    today_now_str = str(today_now)[:19]

    result = Recordnums.objects.filter(scenicid=scenicid_, createat__gt=today_start_str,
                                       createat__lt=today_now_str, sec=0).values(
        'createat').annotate(all_nums=Sum('nums')).order_by('createat')
    result_send = []
    for r in result:
        timeArray = time.strptime(r['createat'], '%Y-%m-%d %H:%M:%S')
        timeStamp = int(time.mktime(timeArray)) * 1000
        nums = r['all_nums']
        result_item = [timeStamp, nums]
        result_send.append(result_item)
    return result_send


def updatetodayTouristNums(request):
    scenicid = request.GET['scenicid']
    scenicid = int(scenicid)
    result_send = getTodayIntervalTouristNums(scenicid)
    return JsonResponse(result_send, safe=False)


def getTodayIntervalTouristNums2(scenicid_=1):
    """

    :return: 返回本日内的人数数据
    """
    today_now = datetime.datetime.now()  # 改

    # today_now = today_now - relativedelta(days=today_now.day - 28)

    # 在展示demo的时候我们只展示9-28的数据。部署的时候再来具体更改
    today_start = datetime.datetime(today_now.year, today_now.month, today_now.day, 0, 0, 0)
    today_start_str = str(today_start)[:19]
    today_now_str = str(today_now)[:19]

    result = Recordnums.objects.filter(scenicid=scenicid_, createat__gt=today_start_str,
                                       createat__lt=today_now_str, minute=0).values(
        'createat').annotate(all_nums=Sum('nums')).order_by('createat')
    result_send = []
    for r in result:
        timeArray = time.strptime(r['createat'], '%Y-%m-%d %H:%M:%S')
        timeStamp = int(time.mktime(timeArray)) * 1000
        nums = r['all_nums']
        result_item = [timeStamp, nums]
        result_send.append(result_item)
    return result_send


def updatetodayTouristNums2(request):
    '''

    :param request:
    :return: 获得一天内的人数变换
    '''
    scenicid = request.GET['scenicid']
    scenicid = int(scenicid)
    result_send = getTodayIntervalTouristNums2(scenicid)
    return JsonResponse(result_send, safe=False)


def getTouristDistribute(scencid_):
    '''

    :param scencid_:
    :return: 得到某岛今年与去年的各月份人数分布
    '''
    current_time = datetime.datetime.now()
    last_time = current_time - relativedelta(years=1)
    # 得到去年今日和今年今日时间

    this_year = current_time.year
    last_year = last_time.year

    query_this_year = WifiNumsMonth.objects.filter(island_id=scencid_, year=this_year).values('month', 'nums')

    query_last_year = WifiNumsMonth.objects.filter(island_id=scencid_, year=last_year).values('month', 'nums')

    result_this_year = []
    result_last_year = []
    for r in query_last_year:
        one_month = {'value': r['nums'], 'name': r['month']}
        result_last_year.append(one_month)
    for r in query_this_year:
        one_month = {'value': r['nums'], 'name': r['month']}
        result_this_year.append(one_month)
    result_send = {'distribute_lastYear': result_last_year, 'distribute_thisYear': result_this_year}
    return result_send


def getScenicInfo(scencid_):
    result = Scenic.objects.filter(scenicid=scencid_).values()
    result_send = {}
    result_send['NAME'] = result[0]['scenicname']
    result_send['scenic_lng'] = result[0]['lng']
    result_send['scenic_lat'] = result[0]['lat']
    result_send['scenic_id'] = result[0]['scenicid']
    return result_send


# 最新预警信息
def latestwarn(request):
    username = request.session.get('username', '')
    if not username:
        return redirect('/login/')
    return render(request, 'latestwarn.html')


def getCountNum_thread(request):
    from static.darkflow_video.darkflow.net.help import current_count
    data = {'count': current_count}
    return HttpResponse(json.dumps(data))


def startDetectCount_thread(request):
    vid_name = 'static/video/' + request.POST['vid_name']
    global t
    t = Thread(target=run, args=(vid_name,))
    t.start()
    # _thread.start_new_thread(run, (vid_name,))
    data = {'msg': '开启线程'}
    return HttpResponse(json.dumps(data))


def exitDetectCount_thread(request):
    stop_thread(t)
    data = {'msg': '结束进程'}
    return HttpResponse(json.dumps(data))


# 预警分析
def mf_analysis(request):
    username = request.session.get('username', '')
    if not username:
        return redirect('/login/')
    return render(request, 'mf_analysis.html')


def ms_analysis(request):
    username = request.session.get('username', '')
    if not username:
        return redirect('/login/')
    return render(request, 'ms_analysis.html')


def ls_analysis(request):
    username = request.session.get('username', '')
    if not username:
        return redirect('/login/')
    return render(request, 'ls_analysis.html')


def tc_analysis(request):
    username = request.session.get('username', '')
    if not username:
        return redirect('/login/')
    return render(request, 'tc_analysis.html')


def yg_analysis(request):
    username = request.session.get('username', '')
    if not username:
        return redirect('/login/')
    return render(request, 'yg_analysis.html')


def yl_analysis(request):
    username = request.session.get('username', '')
    if not username:
        return redirect('/login/')
    return render(request, 'yl_analysis.html')


def gh_analysis(request):
    username = request.session.get('username', '')
    if not username:
        return redirect('/login/')
    return render(request, 'gh_analysis.html')


def hs_analysis(request):
    username = request.session.get('username', '')
    if not username:
        return redirect('/login/')
    return render(request, 'hs_analysis.html')


def admin(request):
    username = request.session.get('username', '')
    if not username:
        return redirect('/login/')
    return render(request, 'admin.html')


def admin_warn(request):
    username = request.session.get('username', '')
    if not username:
        return redirect('/login/')
    return render(request, 'adminWarn.html')


def getAdminData(request):
    '''

    :param request:
    :return:获取后台管理-设备管理表数据
    '''

    recordNums = 1  # 每次加载数据先置1
    deviceResult = Deviceinfo.objects.all().values('id', 'devicename', 'ip', 'devicetype', 'location', 'status',
                                                   'adminername', 'adminid')
    status = ("关闭", "开启", "异常")
    rows = []

    for r in deviceResult:
        data = {"id": r['id'], "name": r['devicename'], "location": r['location'], "status": r['status'],
                "person": r['adminername'], "type": r['devicetype'], "index": recordNums,
                "ip": r['ip']
                }
        recordNums += 1
        rows.append(data)

    dataList = {
        "total": 2,
        "rows": rows
        # "rows": [{"id": 0, "name": '摄像头一', 'location': '梅峰岛', 'status': '正常', 'person': '陆继鹏', 'personId': 0},
        #          {"id": 1, "name": '摄像头二', 'location': '梅峰岛', 'status': '正常', 'person': '陈景翔', 'personId': 1},
        #          {"id": 4, "name": 'AC01', 'location': '梅峰岛', 'status': '正常', 'person': '陈景翔', 'personId': 1}]
    }
    return JsonResponse(dataList, safe=False)


def deleteAdminData(request):
    '''

    :param request:
    :return: 删除设备管理表格中的相应数据
    '''
    try:
        idx = int(request.GET['index'])
        id = int(request.GET['id'])
        if idx != -1:
            Deviceinfo.objects.get(pk=id).delete()
    except Exception:
        pass
    noMeans = {'n': 'n'}
    return JsonResponse(noMeans, safe=False)


def changeLevel(i):
    return 'I' * i


def getWarnData(request):
    # 当前时间
    current_time = datetime.datetime.now()
    # current_time = '2019-11-15'
    with connection.cursor() as cursor:
        query = "SELECT warningId,scenicName as place,`level`,`type`,exceedNums,createAt,IFNULL(`name`,'无') as `name`,IFNULL(phone,'无') as phone,state FROM recordwarnings LEFT JOIN adminer ON recordwarnings.scenicId = adminer.scenicId LEFT JOIN scenic ON recordwarnings.scenicId = scenic.scenicId WHERE createAt <= %s ORDER BY createAt DESC;"
        cursor.execute(query, [str(current_time)[:19]])
        warn_data = dictfetchall(cursor)
        for i in range(len(warn_data)):
            warn_dic = warn_data[i]
            warn_dic['state'] = changeState(warn_dic['state'])
            warn_dic['type'] = changeType(warn_dic['type'])
            warn_dic['level'] = changeLevel(warn_dic['level'])
        warn_data = json.dumps(warn_data, cls=DecimalEncoder, ensure_ascii=False)
    return HttpResponse(warn_data)


def deleteWarnData(request):
    data = {}
    with connection.cursor() as cursor:
        # 插入数据库
        query = "DELETE FROM recordwarnings WHERE warningId = %s;"
        r = cursor.execute(query, [request.POST['warningId']])
        if r:
            data['msg'] = '删除成功'
        else:
            data['msg'] = '删除失败'
    return HttpResponse(json.dumps(data))


def addWarnData(request):
    data = {}
    elements = request.GET['elements']
    elements = elements.replace('true', '1')
    elements = eval(elements)
    data['msg'] = '添加失败'
    for e in elements:
        with connection.cursor() as cursor:
            query = "SELECT * FROM adminer LIMIT 1;"
            cursor.execute(query)
            admin_data = dictfetchall(cursor)
            # 插入数据库
            query = "INSERT INTO recordwarnings(scenicId,camId,`level`,`type`,exceedNums,createAt,state) VALUES (%s,%s,%s,%s,%s,%s,%s)"
            r = cursor.execute(query, [admin_data[0]['scenicId'], 0, 3, 1, 10, e['createAt'], 1])
            if r:
                data['msg'] = '添加成功'
            else:
                data['msg'] = '添加失败'
    return HttpResponse(json.dumps(data, ensure_ascii=False))


def addAdminData(request):
    '''

    :param request:
    :return: 添加相应数据岛设备管理表中
    '''
    elements = request.GET['elements']

    elements = elements.replace('true', '1')
    elements = eval(elements)
    haveAdded = 0  # 插入标志,1表示已经有插入成功 0表示没有插入成功的。
    haveChanged = 0  # 修改标志， 1表示已经有修改成功 0表示没有修改成功的。
    isExist = 0  # 判断是否已经存在记录
    haveError = 0  # 判断是否出现非法输入，
    msg = ''
    # changedRows = 0 # 表示成功修改或者插入了的数据个数
    for e in elements:
        idex = e['index']  # 通过index判断是不是插入，如果index是-1那么就是插入，否则是修改
        devicetype = e['type'].upper()
        location = e['location']
        st = e['status']
        id = int(e['id'])
        try:  # 判断数据是否已存在
            isExist = len(Deviceinfo.objects.filter(pk=int(e['id'])))  # 判断待插入或修改数据是否已经存在
            # Deviceinfo.objects.get(pk=int(e['id'])).delete()
        except Exception:
            pass
        # if isExist == 0:
        #     isAdded = 1
        if idex == '-1':  # 插入数据
            if isExist == 0:  # 数据库中未存在改id的数据
                haveAdded = 1
                Deviceinfo.objects.create(id=id, devicename=e['name'], ip=e['ip'], devicetype=devicetype,
                                          location=location,
                                          status=st
                                          , adminername=e['person'], adminid=0)
            else:  # 数据库中存在改id
                msg += e['id'] + ','
                haveError = 1
        else:  # 修改数据
            try:
                Deviceinfo.objects.get(pk=int(e['id'])).delete()
            except Exception:
                pass
            Deviceinfo.objects.create(id=id, devicename=e['name'], ip=e['ip'], devicetype=devicetype,
                                      location=location,
                                      status=st
                                      , adminername=e['person'], adminid=0)
            haveChanged = 1
    # 存入操作
    msg = msg.strip(',')
    noMeans = {'haveAdded': haveAdded, 'haveChanged': haveChanged, 'haveError': haveError, 'msg': msg}
    return JsonResponse(noMeans, safe=False)


def getAdminerData(request):
    recordNums = 1
    adminerResults = Adminer.objects.all().values('id', 'name', 'place', 'phone')

    rows = []
    for r in adminerResults:
        data = {'index': recordNums, 'id': r['id'], 'name': r['name'], 'place': r['place'], 'phone': r['phone']}
        recordNums += 1
        rows.append(data)

    dataList = {
        "total": recordNums - 1,
        "rows": rows
    }
    return JsonResponse(dataList, safe=False)


def deleteAdminerData(request):
    try:
        id = int(request.GET['id'])
        idx = int(request.GET['index'])
        if idx != -1:
            Adminer.objects.get(pk=id).delete()
    except Exception:
        pass
    noMeans = {'n': 'n'}
    return JsonResponse(noMeans, safe=False)


def changeState(i):
    if i == 1:
        return '未通知'
    elif i == 2:
        return '已通知'
    else:
        return '已处理'


def changeType(i):
    if i == 1:
        return '承载量预警'
    elif i == 2:
        return '游客异常出没'
    elif i == 3:
        return '游客打架'
    else:
        return '游客吸烟'


def notice(request):
    with connection.cursor() as cursor:
        query = "SELECT * FROM recordwarnings,adminer WHERE recordwarnings.scenicId = adminer.scenicId AND recordwarnings.warningId = %s;"
        cursor.execute(query, [request.POST['warningId']])
        try:
            warn_data = dictfetchall(cursor)[0]
            query = "UPDATE recordwarnings SET state = 2 WHERE warningId = %s;"
            cursor.execute(query, [request.POST['warningId']])
            signature = '【千岛湖预警平台】'
            if warn_data['type'] == 1:
                content = warn_data['place'] + '于' + warn_data['createAt'] + '发生' + warn_data[
                    'level'] * 'I' + '级承载量预警,请尽快前去处理。'
            elif warn_data['type'] == 2:
                content = warn_data['place'] + '（摄像头' + warn_data['camId'] + ')于' + warn_data[
                    'createAt'] + '发生游客异常出没,请尽快前去处理。'
            elif warn_data['type'] == 3:
                content = warn_data['place'] + '（摄像头' + warn_data['camId'] + ')于' + warn_data[
                    'createAt'] + '发生游客打架,请尽快前去处理。'
            elif warn_data['type'] == 5:
                content = warn_data['place'] + '（摄像头' + warn_data['camId'] + ')于' + warn_data[
                    'createAt'] + '发生游客吸烟,请尽快前去处理。'
            content = signature + content
            url = 'https://api.submail.cn/message/send.json'
            data = {'appid': '44353', 'signature': '2d4653813f1dfd2ad0dc3ab86a281fc0', 'to': warn_data['phone'],
                    'content': content}
            r = requests.post(url, data).json()
            # r = {'status': 'success'}
            if r['status'] == 'success':
                msg = '通知成功'
            else:
                msg = '通知失败'
        except Exception:
            msg = '无联系人，通知失败'
        data = json.dumps({'msg': msg}, cls=DecimalEncoder, ensure_ascii=False)
    return HttpResponse(data)


def DetectWarn(request):
    # 当前时间
    current_time = datetime.datetime.now()
    # current_time = datetime.datetime.now() + relativedelta(hour=18, minute=50, second=13)
    with connection.cursor() as cursor:
        query = "SELECT warningId,place as ScenicName,`level`,`type`,exceedNums,createAt,`name`,phone,state,camId FROM recordwarnings,adminer WHERE createAt >= %s AND createAt <= %s AND recordwarnings.scenicId = adminer.scenicId;"
        cursor.execute(query, [str(current_time - relativedelta(seconds=30))[:19], str(current_time)[:19]])
        warnr_data = json.dumps(dictfetchall(cursor), cls=DecimalEncoder, ensure_ascii=False)
    return HttpResponse(warnr_data)


def getWarnDataById(request):
    with connection.cursor() as cursor:
        query = "SELECT scenicName,`level`,`type`,exceedNums,createAt,state,IFNULL(`name`,'无') as `name`,IFNULL(phone,'无') as phone FROM recordwarnings LEFT JOIN adminer ON recordwarnings.scenicId = adminer.scenicId LEFT JOIN scenic ON recordwarnings.scenicId = scenic.scenicId WHERE warningId = %s;"
        cursor.execute(query, [request.POST['warningId']])
        warnr_data = json.dumps(dictfetchall(cursor), cls=DecimalEncoder, ensure_ascii=False)
    return HttpResponse(warnr_data)


def imgs2video(imgs_dir, temp_name, save_name, end_ret):
    fps = 20.0
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    imgname = os.path.join(imgs_dir, '0.jpg')
    frame = cv2.imread(imgname)
    video_writer = cv2.VideoWriter(temp_name, fourcc, fps, (frame.shape[1], frame.shape[0]))
    start_end = 0
    if end_ret > 125:
        start_end = end_ret - 125
    for i in range(start_end, end_ret):
        imgname = os.path.join(imgs_dir, str(i) + '.jpg')
        frame = cv2.imread(imgname)
        video_writer.write(frame)
    video_writer.release()
    os.system('ffmpeg -y -i ' + temp_name + ' -vcodec h264 ' + save_name)


# 存储视频
def save_replay(typeName):
    with open('static/darknet/results/record.txt', 'r', encoding='utf-8') as f:
        ret = f.read()
        imgs2video('static/darknet/img/' + typeName, typeName + '_replay.mp4',
                   'static/darknet/video/' + typeName + '_replay.mp4', int(ret))


# 存储视频
def save_replay2(typeName):
    with open('static/darknet2/results/record.txt', 'r', encoding='utf-8') as f:
        ret = f.read()
        imgs2video('static/darknet2/img/' + typeName, typeName + '_replay.mp4',
                   'static/darknet2/video/' + typeName + '_replay.mp4', int(ret))


# 检测游客出没
def start_run_person(request):
    with open('static/darknet/results/result.txt', 'w', encoding='utf-8') as f:
        f.write('0')
    global t_person
    t_person = Thread(target=run_person, args=())
    t_person.start()
    data = {'msg': '开启线程'}
    return HttpResponse(json.dumps(data))


def detect_run_person(request):
    global t_person
    data = {}
    f = open('results/result.txt')
    clscode = f.read()
    if clscode == '1':
        data['state'] = 1
        with connection.cursor() as cursor:
            # 插入数据库
            query = "INSERT INTO recordwarnings(scenicId,camId,`level`,`type`,exceedNums,createAt,state) VALUES (%s,%s,%s,%s,%s,%s,%s)"
            scenicId = random.randint(1, 9)
            camId = random.randint(1, 10)
            createAt = str(datetime.datetime.now())[:19]
            cursor.execute(query, [scenicId, camId, 1, 2, 0, createAt, 1])
            query = "SELECT max(warningId) as maxId FROM recordwarnings;"
            cursor.execute(query)
            maxId = dictfetchall(cursor)[0]['maxId']
            try:
                # 图片重命名
                print('图片重命名')
                os.rename('img/detect.jpg', '../img/warning' + str(maxId) + '.jpg')
                # 改变文件目录
                print('改变文件目录')
                os.chdir(os.path.abspath('../..'))
                # 存储视频
                print('存储视频')
                t_save = Thread(target=save_replay, args=('person',))
                t_save.start()
                # 停止线程
                print('停止线程')
                stop_thread(t_person)
            except:
                HttpResponse(json.dumps(data))
            with open('static/darknet/results/result.txt', 'w', encoding='utf-8') as f:
                f.write('0')
    else:
        data['state'] = 0
    return HttpResponse(json.dumps(data))


# 检测游客打架
def start_run_fight(request):
    with open('static/darknet2/results/result.txt', 'w', encoding='utf-8') as f:
        f.write('0')
    global t_fight
    t_fight = Thread(target=run_fight, args=())
    t_fight.start()
    data = {'msg': '开启线程'}
    return HttpResponse(json.dumps(data))


def detect_run_fight(request):
    global t_fight
    data = {}
    f = open('results/result.txt')
    clscode = f.read()
    if clscode == '1':
        data['state'] = 1
        with connection.cursor() as cursor:
            # 插入数据库
            query = "INSERT INTO recordwarnings(scenicId,camId,`level`,`type`,exceedNums,createAt,state) VALUES (%s,%s,%s,%s,%s,%s,%s)"
            scenicId = random.randint(1, 9)
            camId = random.randint(1, 10)
            createAt = str(datetime.datetime.now())[:19]
            cursor.execute(query, [scenicId, camId, 1, 3, 0, createAt, 1])
            query = "SELECT max(warningId) as maxId FROM recordwarnings;"
            cursor.execute(query)
            maxId = dictfetchall(cursor)[0]['maxId']
            try:
                # 图片重命名
                print('图片重命名')
                os.rename('img/detect.jpg', '../img/warning' + str(maxId) + '.jpg')
                # 改变文件目录
                print('改变文件目录')
                os.chdir(os.path.abspath('../..'))
                # 存储视频
                print('存储视频')
                t_save = Thread(target=save_replay2, args=('fight',))
                t_save.start()
                # 停止线程
                print('停止线程')
                stop_thread(t_fight)
            except:
                HttpResponse(json.dumps(data))
            with open('static/darknet2/results/result.txt', 'w', encoding='utf-8') as f:
                f.write('0')
    else:
        data['state'] = 0
    return HttpResponse(json.dumps(data))


# 检测吸烟
def start_run_smoke(request):
    with open('static/darknet3/results/result.txt', 'w', encoding='utf-8') as f:
        f.write('0')
    global t_smoke
    t_smoke = Thread(target=run_smoke, args=())
    t_smoke.start()
    data = {'msg': '开启线程'}
    return HttpResponse(json.dumps(data))


def detect_run_smoke(request):
    global t_smoke
    data = {}
    f = open('results/result.txt')
    clscode = f.read()
    if clscode == '5':
        data['state'] = 1
        with connection.cursor() as cursor:
            # 插入数据库
            query = "INSERT INTO recordwarnings(scenicId,camId,`level`,`type`,exceedNums,createAt,state) VALUES (%s,%s,%s,%s,%s,%s,%s)"
            scenicId = random.randint(1, 9)
            camId = random.randint(1, 10)
            createAt = str(datetime.datetime.now())[:19]
            cursor.execute(query, [scenicId, camId, 1, 5, 0, createAt, 1])
            query = "SELECT max(warningId) as maxId FROM recordwarnings;"
            cursor.execute(query)
            maxId = dictfetchall(cursor)[0]['maxId']
            try:
                # 图片重命名
                print('图片重命名')
                os.rename('img/detect.jpg', '../img/warning' + str(maxId) + '.jpg')
                # 改变文件目录
                print('改变文件目录')
                os.chdir(os.path.abspath('../..'))
                # 存储视频
                print('存储视频')
                t_save = Thread(target=save_replay, args=('smoke',))
                t_save.start()
                # 停止线程
                print('停止线程')
                stop_thread(t_smoke)
            except:
                HttpResponse(json.dumps(data))
            with open('static/darknet3/results/result.txt', 'w', encoding='utf-8') as f:
                f.write('0')
    else:
        data['state'] = 0
    return HttpResponse(json.dumps(data))


def addAdminerData(request):
    element = request.GET['elements']
    element = element.replace('true', '1')
    element = eval(element)
    island_ids_query = Scenic.objects.all().values('scenicname').order_by('scenicid')
    island_ids_list = [r['scenicname'] for r in island_ids_query]
    haveAdded = 0  # 插入标志,1表示已经有插入成功 0表示没有插入成功的。
    haveChanged = 0  # 修改标志， 1表示已经有修改成功 0表示没有修改成功的。
    isExist = 0  # 判断是否已经存在记录
    haveErrorId = 0  # 判断是否出现非法的工号，
    haveErrorIsland = 0  # 判断是否出现非法的岛屿
    msgId = ''
    msgIsland = ''

    for e in element:
        idx = e['index']
        id = int(e['id'])

        try:  # 判断工号是否已经存在
            isExist = len(Adminer.objects.filter(pk=id))
            # Adminer.objects.get(pk=id).delete()
        except Exception:
            pass

        try:  # 判断输入的岛屿是否存在
            island_id = island_ids_list.index(e['place']) + 1
        except Exception:
            haveErrorIsland = 1
            msgIsland += e['place'] + ','
            continue

        if idx == '-1':  # idx为-1那么就是插入
            if isExist == 0:  # 工号不存在,正常插入
                haveAdded = 1
                Adminer.objects.create(id=int(e['id']), name=e['name'], place=e['place'], phone=e['phone'],
                                       scenicid=island_id)
            else:  # 工号已经存在,添加报错信息
                haveErrorId = 1
                msgId += e['id'] + ','
        else:  # 修改数据
            Adminer.objects.get(pk=id).delete()
            Adminer.objects.create(id=int(e['id']), name=e['name'], place=e['place'], phone=e['phone'],
                                   scenicid=island_id)
            haveChanged = 1
    msgId = msgId.strip(',')
    msgIsland = msgIsland.strip(',')
    noMeans = {'haveAdded': haveAdded, 'haveChanged': haveChanged, 'haveErrorId': haveErrorId, 'msgId': msgId,
               'haveErrorIsland': haveErrorIsland, 'msgIsland': msgIsland}
    return JsonResponse(noMeans, safe=False)


def login(request):
    return render(request, 'login.html', {'status': 1})


def validate(request):
    name = request.POST.get('name')
    password = request.POST.get('password')
    result = User.objects.filter(name=name, password=password).values('name', 'password')
    if len(result) != 0:
        request.session['username'] = name
        return redirect('/index/')
    else:
        return render(request, 'login.html', {'status': 0})


captcha = ''


def signUp(request):
    name = request.GET['name']
    password = request.GET['password']
    phone = request.GET['phone']
    canSign = 0
    isExist = len(User.objects.filter(phone=phone))
    nameRepeat = len(User.objects.filter(name=name))
    if nameRepeat != 0 : # 该账号已经注册
        canSign = 3
    elif isExist != 0:  # 该手机号已经注册
        canSign = 2
    else:
        id = len(User.objects.all().values('id')) + 10
        fresh = User.objects.create(phone=phone, name=name, password=password, id=id)
        fresh.save()
        canSign = 1
    return JsonResponse({'canSign': canSign}, safe=False)


def change(request):
    return render(request, 'change.html')


def doChange(request):
    global captcha

    phone = request.GET['phone']
    cap = request.GET['captcha']
    canChange = 0
    isExist = len(User.objects.filter(phone=phone))
    if isExist == 0:  # 用户不存在
        canChange = 2
    else:
        password_new = request.GET['password_new']
        if cap == captcha:
            captcha = ''
            result = User.objects.filter(phone=phone).values('id', 'name')
            if len(result) != 0:
                id = int(result[0]['id'])
                name = result[0]['name']
                User.objects.get(pk=id).delete()
                new_man = User.objects.create(phone=phone, id=id, name=name, password=password_new)
                new_man.save()
                canChange = 1
    return JsonResponse({'canChange': canChange}, safe=False)


def sendCaptcha(request):
    global captcha
    captcha = ''
    phone = request.GET['phone']
    with connection.cursor() as cursor:
        query = "SELECT * FROM user WHERE phone = %s"
        cursor.execute(query, [phone])
        user_data = dictfetchall(cursor)
        if len(user_data):
            signature = '【千岛湖预警平台】'
            H = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
            for i in range(4):
                captcha += random.choice(H)
            content = signature + '你的验证码是：' + captcha
            url = 'https://api.submail.cn/message/send.json'
            data = {'appid': '45418', 'signature': 'c6486e962a54fc08a2f03fa6f7cc9f7d', 'to': phone,
                    'content': content}
            r = requests.post(url, data).json()
            if r['status'] == 'success':
                msg = '验证码发送成功，请注意查看短信！'
            else:
                msg = '验证码发送失败！'
            data = json.dumps({'msg': msg}, cls=DecimalEncoder, ensure_ascii=False)
        else:
            msg = '该手机号未注册，不能获取验证码！'
            data = json.dumps({'msg': msg}, cls=DecimalEncoder, ensure_ascii=False)
    return HttpResponse(data)


def logout(request):
    '''
    :param request:
    :return:退出登录
    '''
    request.session.flush()
    return redirect('/login/')


def get1Adminer(request):
    with connection.cursor() as cursor:
        query = "SELECT * FROM adminer LIMIT 1;"
        cursor.execute(query)
        admin_data = json.dumps(dictfetchall(cursor), cls=DecimalEncoder, ensure_ascii=False)
    return HttpResponse(admin_data)
