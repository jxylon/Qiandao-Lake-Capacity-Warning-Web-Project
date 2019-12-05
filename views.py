import ctypes
import inspect
from threading import Thread
import datetime
import decimal
import json
import random
import time
from dateutil.relativedelta import relativedelta
from django.core import serializers
from django.db import connection
from django.db.models import Max, Sum, Avg
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils.safestring import SafeString
from .models import Scenic, Recordnums, Recordwarnings, Camera, Camerainfo, Wifiinfo, WifiNumsMonth, WifiNumsDay, \
    Adminer
from static.darkflow_video.run_detect import run

count_list = [-1]
t = Thread()


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


def addTodayData(request):
    # 添加Recordnums
    for i in range(60):
        curtime = datetime.datetime.now() + relativedelta(hour=0, minute=0, second=0) - relativedelta(days=i)
        print(str(curtime))
        next_day = curtime.day + 1
        while curtime.day != next_day:
            year = curtime.year
            month = curtime.month
            day = curtime.day
            hour = curtime.hour
            minute = curtime.minute
            sec = curtime.second
            for j in range(1, 9):
                for k in range(1, 16):
                    nums = random.randint(1, 100)
                    sce_obj = Scenic(scenicid=j)
                    cam_obj = Camera(scenicid=sce_obj, camid=k)
                    Recordnums.objects.create(scenicid=sce_obj, camid=cam_obj, nums=nums, year=year, month=month,
                                              day=day,
                                              hour=hour,
                                              minute=minute, sec=sec, createat=str(curtime)[:19])
            curtime = curtime + relativedelta(minutes=10)
    return render(request, 'addTodayData.html')


def addData(request):
    # 添加Recordwarnings表
    for i in range(31):
        curtime = datetime.datetime.now() + relativedelta(days=i)
        for j in range(1, 9):
            level = random.randint(1, 3)
            exceedNums = random.randint(1, 50) + 50 * (3 - level)
            Recordwarnings.objects.create(scenicid=j, camid=0, level=level, type=1, exceednums=exceedNums,
                                          createat=str(curtime)[:19])
    # 添加Recordnums表
    for i in range(31):
        curtime = datetime.datetime.now() + relativedelta(days=i)
        year = curtime.year
        month = curtime.month
        day = curtime.day
        hour = curtime.hour
        minute = curtime.minute
        sec = curtime.second
        for j in range(1, 9):
            for k in range(1, 16):
                nums = random.randint(1, 1000)
                sce_obj = Scenic(scenicid=j)
                cam_obj = Camera(scenicid=sce_obj, camid=k)
                Recordnums.objects.create(scenicid=sce_obj, camid=cam_obj, nums=nums, year=year, month=month, day=day,
                                          hour=hour,
                                          minute=minute, sec=sec, createat=str(curtime)[:19])
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
    nums_this_Interval = WifiNumsDay.objects.filter(island_id=scenicid, year__range=[start.year, end.year],
                                                    month__range=[start.month, end.month],
                                                    day__range=[start.day, end.day],
                                                    ).values("island_id").annotate(sum=Sum("nums"))
    sum_ = nums_this_Interval[0]['sum']

    return sum_


def getIntervalWarnNums(start, end, scenicid):
    """

    :param start:
    :param end:
    :param scenicid:
    :return: 获得某岛的一段时间内的预警次数
    """
    start_str = str(start)[:10]
    end = end + relativedelta(days=1)  # 因为是半闭合区间
    end_str = str(end)[:10]

    sum_ = 0
    result = Recordwarnings.objects.filter(scenicid=scenicid, createat__gt=start_str, createat__lt=end_str)
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

    num_this_week = getIntervalTouristNums(monday, sunday, scenicid)
    num_this_week_lastyear = getIntervalTouristNums(monday_lastyear, sunday_lastyear, scenicid)
    num_this_week_lastweek = getIntervalTouristNums(monday_lastweek, sunday_lastweek, scenicid)
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
    # query_time = str(current_time)[:10]
    # query_time_yesterday = str(current_time - relativedelta(days=1))[:10]
    query_time = '2019-11-15'
    query_time_yesterday = '2019-11-14'
    # 去年同日期
    query_time_lastyear = '2018-11-15'
    # query_time_lastyear = str(current_time - relativedelta(years=1))[:10]
    with connection.cursor() as cursor:
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
        # 查询本月游客人数
        query = "SELECT SUM(todayTotal) as rn_sum_month FROM mobile WHERE `year`=%s AND `month`=%s"
        # cursor.execute(query, [current_time.year, current_time.month])
        cursor.execute(query, [2019, 11])
        rn_sum_month = int(dictfetchall(cursor)[0]['rn_sum_month'])
        # 查询上一月游客人数
        query = "SELECT SUM(todayTotal) as rn_sum_month_lastmonth FROM mobile WHERE `year`=%s AND `month`=%s"
        # cursor.execute(query, [time_dic['lastmonth_year'], time_dic['lastmonth_month']])
        cursor.execute(query, [2019, 10])
        rn_sum_month_lastmonth = int(dictfetchall(cursor)[0]['rn_sum_month_lastmonth'])
        # 查询上一年本月游客人数
        query = "SELECT SUM(todayTotal) as rn_sum_month_lastyear FROM mobile WHERE `year`=%s AND `month`=%s"
        # cursor.execute(query, [current_time.year - 1, current_time.month])
        cursor.execute(query, [2018, 11])
        rn_sum_month_lastyear = int(dictfetchall(cursor)[0]['rn_sum_month_lastyear'])

        context['rn_sum_day'] = rn_sum_day * 4
        context['rn_sum_day_dod'] = (rn_sum_day - rn_sum_day_yesterday) / (rn_sum_day_yesterday + 1) * 100
        context['rn_sum_day_yoy'] = (rn_sum_day - rn_sum_day_lastyear) / (rn_sum_day_lastyear + 1) * 100
        context['rn_sum_month'] = rn_sum_month * 3
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
    query_time = str(current_time)[:10]
    query_time_yesterday = str(current_time - relativedelta(days=1))[:10]
    # 去年同日期
    # query_time_lastyear = '2018-11-15'
    query_time_lastyear = str(current_time - relativedelta(years=1))[:10]
    with connection.cursor() as cursor:
        # 查询本日游客人数
        query = "SELECT COUNT(warningId) as rw_count_week FROM recordwarnings WHERE createAt LIKE %s"
        cursor.execute(query, [query_time + '%'])
        rw_count_week = dictfetchall(cursor)[0]['rw_count_week']
        # 查询昨天游客人数
        query = "SELECT COUNT(warningId) as rw_count_week_lastweek FROM recordwarnings WHERE createAt LIKE %s"
        cursor.execute(query, [query_time_yesterday + '%'])
        rw_count_week_lastweek = dictfetchall(cursor)[0]['rw_count_week_lastweek']
        # 查询上一年本日游客人数
        query = "SELECT COUNT(warningId) as rw_count_week_lastyear FROM recordwarnings WHERE createAt LIKE %s"
        cursor.execute(query, [query_time_lastyear + '%'])
        rw_count_week_lastyear = dictfetchall(cursor)[0]['rw_count_week_lastyear']
        # 查询本月游客人数
        query = "SELECT COUNT(warningId) as rw_count_month FROM recordwarnings WHERE createAt LIKE %s"
        cursor.execute(query, [str(current_time)[:7] + '%'])
        rw_count_month = dictfetchall(cursor)[0]['rw_count_month']
        # 查询上一月游客人数
        query = "SELECT COUNT(warningId) as rw_count_month_lastmonth FROM recordwarnings WHERE createAt LIKE %s"
        cursor.execute(query, [str(time_dic['lastmonth'])[:7] + '%'])
        rw_count_month_lastmonth = dictfetchall(cursor)[0]['rw_count_month_lastmonth']
        # 查询本月游客人数
        query = "SELECT COUNT(warningId) as rw_count_month_lastyear FROM recordwarnings WHERE createAt LIKE %s"
        cursor.execute(query, [str(current_time - relativedelta(years=1))[:7] + '%'])
        rw_count_month_lastyear = dictfetchall(cursor)[0]['rw_count_month_lastyear']

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
        query = "SELECT scenicName as scenic,SUM(nums) DIV 9 as nums FROM recordnums,scenic WHERE recordnums.scenicId = scenic.scenicId AND createAt LIKE %s GROUP BY scenic.scenicId ORDER BY nums DESC"
        cursor.execute(query, [str(current_time)[:10] + '%'])
        scenicrank_data = json.loads(json.dumps(dictfetchall(cursor), cls=DecimalEncoder))
        context['scenicrank_data'] = SafeString(scenicrank_data)
    return context


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
        query = "SELECT scenicName AS scenic,COUNT(recordwarnings.scenicId) as times FROM recordwarnings,scenic WHERE recordwarnings.scenicId = scenic.scenicId AND `level` = '1' AND createAt LIKE %s GROUP BY scenic.scenicId ORDER BY times DESC"
        cursor.execute(query, [str(current_time)[:10] + '%'])
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
        query = "SELECT scenicName AS scenic,COUNT(recordwarnings.scenicId) as times FROM recordwarnings,scenic WHERE recordwarnings.scenicId = scenic.scenicId AND `level` = '2' AND createAt LIKE %s GROUP BY scenic.scenicId ORDER BY times DESC"
        cursor.execute(query, [str(current_time)[:10] + '%'])
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
        query = "SELECT scenicName AS scenic,COUNT(recordwarnings.scenicId) as times FROM recordwarnings,scenic WHERE recordwarnings.scenicId = scenic.scenicId AND `level` = '3' AND createAt LIKE %s GROUP BY scenic.scenicId ORDER BY times DESC"
        cursor.execute(query, [str(current_time)[:10] + '%'])
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
        query = "SELECT * FROM (SELECT scenic.scenicId,scenicName,camera.camId,`level`,`type`,exceedNums,substring(createAt,12,5) as createAtMin,createAt,recordwarnings.state FROM scenic,recordwarnings,camera WHERE recordwarnings.scenicId = scenic.scenicId AND recordwarnings.scenicId = camera.scenicId AND recordwarnings.camId = camera.camId AND createAt <= %s AND createAt >= %s ORDER BY createAt DESC LIMIT 7) temp ORDER BY temp.`level`"
        cursor.execute(query, [adjustTime(str(current_time)[:16]) + ':00', str(current_time)[:10]])
        curwarn_data = json.loads(json.dumps(dictfetchall(cursor), cls=DecimalEncoder))
        context['curwarn'] = curwarn_data
    return context


def getAdminInfo(request):
    """
    当前管理员信息

    """
    with connection.cursor() as cursor:
        query = "SELECT * FROM adminer WHERE scenicId = %s"
        cursor.execute(query, [request.POST['scenicId']])
        admin_data = json.dumps(dictfetchall(cursor), cls=DecimalEncoder, ensure_ascii=False)
    return HttpResponse(admin_data)


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
    context = getScenicContext(1)
    return render(request, 'mf_scenic.html', context=context)


def huangshanjian(request):
    """

    :param request:
    :return: 返回黄山尖景区信息
    """
    context = getScenicContext(2)
    return render(request, 'hs_scenic.html', context=context)


def tianchi(request):
    """

    :param request:
    :return: 返回天池岛景区信息
    """
    context = getScenicContext(3)
    return render(request, 'tc_scenic.html', context=context)


def yueguang(request):
    """

    :param request:
    :return: 返回月光岛景区信息
    """
    context = getScenicContext(4)
    return render(request, 'yg_scenic.html', context=context)


def longshan(request):
    """

    :param request:
    :return: 返回龙山岛景区信息
    """
    context = getScenicContext(5)
    return render(request, 'longshan_scenic.html', context=context)


def yule(request):
    """

    :param request:
    :return: 返回渔乐岛景区信息
    """
    context = getScenicContext(6)
    return render(request, 'yl_scenic.html', context=context)


def guihua(request):
    """

    :param request:
    :return: 返回桂花岛景区信息
    """

    context = getScenicContext(7)
    return render(request, 'gh_scenic.html', context=context)


def mishan(request):
    """

    :param request:
    :return: 返回蜜山岛信息
    """
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
    context = {'start_data': start_data, 'start_data_week': start_data_week, 'start_data_month': start_data_month}
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
        nums = r['weeknums']
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
        nums = r['weeknums']
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
    # today_now = datetime.datetime.now()  # 改
    today_now = datetime.datetime(2019, 9, 28, 5, 25, 30)  # for display
    # today_now = today_now - relativedelta(days=today_now.day - 28)

    # 在展示demo的时候我们只展示9-28的数据。部署的时候再来具体更改
    today_start = datetime.datetime(today_now.year, today_now.month, today_now.day, 0, 0, 0)
    today_start_str = str(today_start)[:19]
    today_now_str = str(today_now)[:19]

    result = Recordnums.objects.filter(scenicid=scenicid_, createat__gt=today_start_str,
                                       createat__lt=today_now_str).values(
        'hour').annotate(all_nums=Avg('nums')).order_by('hour')
    result_send = []
    for r in result:
        showTime = '{0}-{1}-{2} {3}:{4}:{5}'.format(today_now.year, today_now.month, today_now.day, r['hour'], 0, 0)
        timeArray = time.strptime(showTime, '%Y-%m-%d %H:%M:%S')
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
    return render(request, 'mf_analysis.html')


def ms_analysis(request):
    return render(request, 'ms_analysis.html')


def ls_analysis(request):
    return render(request, 'ls_analysis.html')


def tc_analysis(request):
    return render(request, 'tc_analysis.html')


def yg_analysis(request):
    return render(request, 'yg_analysis.html')


def yl_analysis(request):
    return render(request, 'yl_analysis.html')


def gh_analysis(request):
    return render(request, 'gh_analysis.html')


def hs_analysis(request):
    return render(request, 'hs_analysis.html')


def admin(request):
    return render(request, 'admin.html')


def admin_warn(request):
    return render(request, 'adminWarn.html')


def getAdminData(request):
    recordNums = 1  # 每次加载数据先置1
    placeResult = Scenic.objects.all().values('scenicid', 'scenicname').order_by('scenicid')
    cameraResult = Camerainfo.objects.all().values('sciencid', 'cameraid', 'name', 'state', 'adminname',
                                                   'adminid', 'devicetype').order_by('sciencid', 'cameraid')
    wifiResult = Wifiinfo.objects.all().values('tvid', 'sciencid', 'name', 'state', 'adminid', 'adminname',
                                               'devicetype')
    status = ("关闭", "开启", "异常")
    rows = []

    for r in wifiResult:
        location = placeResult[int(r['sciencid']) - 1]['scenicname']
        data = {"id": r['tvid'], "name": r['name'], "location": location, "status": status[int(r['state'])],
                "person": r['adminname'], "personId": r['adminid'], "type": r['devicetype'], "index": recordNums,
                }
        recordNums += 1
        rows.append(data)

    for r in cameraResult:
        location = placeResult[int(r['sciencid']) - 1]['scenicname']
        data = {"id": r['cameraid'], "name": r['name'], "location": location, "status": status[int(r['state'])],
                "person": r['adminname'], "personId": r['adminid'], "type": r['devicetype'], "index": recordNums,
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
    try:
        id = int(request.GET['id'])
        type = int(request.GET['type'])
        willDelete = [Camerainfo, Wifiinfo]
        willDelete[type].objects.get(pk=id).delete()
    except Exception:
        pass
    noMeans = {'n': 'n'}
    return JsonResponse(noMeans, safe=False)


def addAdminData(request):
    print('asd')
    elements = request.GET['elements']

    elements = elements.replace('true', '1')
    elements = eval(elements)

    dbs = [Camerainfo, Wifiinfo]
    db_names = ['摄像头', 'WIFI']
    scenicResult = Scenic.objects.all().values('scenicname').order_by('scenicid')
    scenicNames = [r['scenicname'] for r in scenicResult]
    states = ['关闭', '开启', '异常']

    for e in elements:
        type = db_names.index(e['type'])
        sid = scenicNames.index(e['location']) + 1
        st = states.index(e['status'])
        try:
            dbs[type].objects.get(pk=int(e['id'])).delete()
        except Exception:
            pass

        if type == 0:  # 插入摄像头数据
            dbs[type].objects.create(sciencid=int(sid), cameraid=int(e['id']), name=e['name'], state=st,
                                     adminname=e['person'], adminid=e['personId'], devicetype='摄像头')
        elif type == 1:  # 插入WIFI数据
            dbs[type].objects.create(sciencid=int(sid), tvid=int(e['id']), name=e['name'], state=st,
                                     adminname=e['person'], adminid=e['personId'], devicetype='WIFI')

    # 存入操作
    noMeans = {'n': 'n'}
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
        Adminer.objects.get(pk=id).delete()
    except Exception:
        pass
    noMeans = {'n': 'n'}
    return JsonResponse(noMeans, safe=False)


def addAdminerData(request):
    element = request.GET['elements']
    element = element.replace('true', '1')
    element = eval(element)

    for e in element:
        id = int(e['id'])
        Adminer.objects.create(id=int(e['id']), name=e['name'], place=e['place'], phone=e['phone'])
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
        return '有人出没'
    else:
        return '吸烟'


def changeLevel(i):
    return 'I' * i


def getWarnData(request):
    # 当前时间
    current_time = datetime.datetime.now()
    # current_time = '2019-11-15'
    with connection.cursor() as cursor:
        query = "SELECT warningId,place,`level`,`type`,exceedNums,createAt,`name`,phone,state FROM recordwarnings,adminer WHERE recordwarnings.scenicId = adminer.scenicId AND createAt <= %s ORDER BY state,createAt DESC"
        cursor.execute(query, [str(current_time)[:16]])
        warnr_data = dictfetchall(cursor)
        for i in range(len(warnr_data)):
            warn_dic = warnr_data[i]
            warn_dic['state'] = changeState(warn_dic['state'])
            warn_dic['type'] = changeType(warn_dic['type'])
            warn_dic['level'] = changeLevel(warn_dic['level'])
        warnr_data = json.dumps(warnr_data, cls=DecimalEncoder, ensure_ascii=False)
    return HttpResponse(warnr_data)


def notice(request):
    context = {}
    with connection.cursor() as cursor:
        query = "UPDATE recordwarnings SET state = 2 WHERE warningId = %s"
        # request.POST['warningId']
        res = cursor.execute(query, [1450])
        if res:
            msg = '修改成功'
        else:
            msg = '修改失败'
        context['msg'] = msg
        data = json.dumps(context, cls=DecimalEncoder, ensure_ascii=False)
    return HttpResponse(data)
