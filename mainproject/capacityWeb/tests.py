import random

import numpy as np
import pandas as pd
import requests
import datetime
from dateutil.relativedelta import relativedelta
import MySQLdb

file_path = "D:/Documents/HDU421/"


def getLakeNumbers():
    """
    统计本月连接中国移动wifi的游客人数
    """
    url = 'http://115.29.3.3:8080/qdhdc/ydrk/getLakeNumber'
    db = MySQLdb.connect(host="localhost", user="root", password="qq2009", port=3306, db="capacity", charset='utf8')
    cursor = db.cursor()
    table = 'mobile'
    today = datetime.datetime.now() - relativedelta(days=10)
    first_day = datetime.datetime.now() + relativedelta(day=1)
    last_day = first_day + relativedelta(months=1) - relativedelta(days=1)
    while today.day <= last_day.day and today.month == last_day.month:
        date = str(today)[:10]
        result = requests.get(url, 'date=' + date).json()[0]
        today = today + relativedelta(days=1)
        try:
            data = {
                'todayDividual': result['todayDividual'],
                'todayTeam': result['todayTeam'],
                'todayTotal': result['todayTotal'],
                'centerDividual': result['result']['centerDividual'],
                'centerTeam': result['result']['centerTeam'],
                'centerIn': result['result']['centerIn'],
                'eastsouthDividual': result['result']['eastsouthDividual'],
                'eastsouthTeam': result['result']['eastsouthTeam'],
                'eastSouthIn': result['result']['eastSouthIn'],
                'year': date.split('-')[0],
                'month': date.split('-')[1],
                'day': date.split('-')[2],
                'ticketDate': date
            }
            keys = ', '.join(data.keys())
            values = ', '.join(['%s'] * len(data))
            sql = "INSERT INTO {table}({keys}) VALUES ({values})".format(table=table, keys=keys, values=values)
            cursor.execute(sql, tuple(data.values()))
            print(date + ' INSERT Successful')
            db.commit()
        except:
            print(date + ' INSERT Failed')
            continue
    cursor.close()
    db.close()


def saveToWifi(cursor, db, table, line):
    unknow = lambda x: '未知' if pd.isna(x) else x
    data = {
        'scenicId': random.randint(1, 8),
        'camId': random.randint(1, 15),
        'apcn': line['APCN'],
        'staMac': line['STA_MAC'],
        'terType': unknow(line['TER_TYPE']),
        'vendorCn': unknow(line['VENDOR_CN']),
        'staRxbytes': line['STA_RXBYTES'],
        'staTxbytes': line['STA_TXBYTES'],
        'year': line['SAMPLEYEAR'],
        'month': line['SAMPLEMON'],
        'day': line['SAMPLEDAY'],
        'hour': line['SAMPLEHOUR'],
        'minute': line['SAMPLEMIN'],
        'createAt': str(line['SAMPLEDATE'])[:16],
    }
    keys = ', '.join(data.keys())
    values = ', '.join(['%s'] * len(data))
    sql = "INSERT INTO {table}({keys}) VALUES ({values})".format(table=table, keys=keys, values=values)
    print(line['SAMPLEYEAR'], end=' ')
    cursor.execute(sql, tuple(data.values()))
    db.commit()
    print('- finish')


def getWifiInfo():
    file_names = ['wasu_wifi_ap_sta_info_2018.xls', 'wasu_wifi_ap_sta_info_201712.xls']
    data_df = pd.read_excel(file_path + file_names[0])
    data_df['SAMPLEMIN'] = 0
    data_df['adminId'] = 10000
    data_df['adminName'] = '张三'
    grouped = data_df.groupby(['SAMPLEDATE', 'SAMPLEHOUR'])
    record_len = {}
    print("处理原始数据")
    for name, group in grouped:
        SAMPLEDATE = name[0]
        SAMPLEHOUR = name[1]
        record_len[(SAMPLEDATE, SAMPLEHOUR)] = len(group)
    for key, value in record_len.items():
        index = data_df.loc[(data_df['SAMPLEDATE'] == key[0]) & (data_df['SAMPLEHOUR'] == key[1])].index
        data_df.loc[index, 'SAMPLEMIN'] = np.linspace(0.0, 59.9, num=value)
    data_df[['SAMPLEMIN']] = data_df[['SAMPLEMIN']].astype(int)
    data_df['SAMPLEYEAR'] = data_df.apply(lambda x: int(x['SAMPLEDATE'].split('-')[0]) + 2, axis=1)
    data_df['SAMPLEMON'] = data_df.apply(lambda x: x['SAMPLEDATE'].split('-')[1], axis=1).astype(int)
    data_df['SAMPLEDAY'] = data_df.apply(lambda x: x['SAMPLEDATE'].split('-')[2], axis=1).astype(int)
    data_df['SAMPLEDATE'] = data_df.apply(
        lambda x: str(x['SAMPLEDATE']) + ' ' + str(x['SAMPLEHOUR']) + ':' + str(x['SAMPLEMIN']),
        axis=1)
    data_df['SAMPLEDATE'] = data_df.apply(lambda x: datetime.datetime.strptime(x['SAMPLEDATE'], "%Y-%m-%d %H:%M"),
                                          axis=1)
    print('复制数据')
    temp_df = data_df.copy()
    while max(temp_df['SAMPLEYEAR']) != 2019:
        temp_df['SAMPLEDATE'] = temp_df[['SAMPLEDATE']].applymap(lambda x: x + relativedelta(days=5))
        temp_df['SAMPLEYEAR'] = temp_df[['SAMPLEDATE']].applymap(lambda x: x.year)
        temp_df['SAMPLEMON'] = temp_df[['SAMPLEDATE']].applymap(lambda x: x.month)
        temp_df['SAMPLEDAY'] = temp_df[['SAMPLEDATE']].applymap(lambda x: x.day)
        data_df = pd.concat([data_df, temp_df], ignore_index=True)
        print(max(temp_df['SAMPLEDATE']))
    data_df.drop(data_df.loc[data_df['SAMPLEYEAR'] == 2019].index, inplace=True)
    data_df.drop(['PERIOD'], axis=1, inplace=True)
    data_df['SAMPLEDATE'] = data_df[['SAMPLEDATE']].applymap(lambda x: str(x)[:16])
    data_df['scenicId'] = np.random.randint(1, 9, len(data_df))
    data_df['camId'] = np.random.randint(1, 16, len(data_df))
    unknow = lambda x: 'unknow' if pd.isna(x) else x
    data_df['TER_TYPE'] = data_df[['TER_TYPE']].applymap(lambda x: unknow(x))
    data_df['VENDOR_CN'] = data_df[['VENDOR_CN']].applymap(lambda x: unknow(x))
    data_df['state'] = np.array([1] * len(data_df))
    admin = {'10000': '张三', '10001': '李四', '10002': '王五'}
    data_df['adminId'] = np.random.randint(10000, 10003, len(data_df)).astype(str)
    data_df['adminName'] = data_df[['adminId']].applymap(lambda x: admin[x])
    print('保存csv文件')
    data_df.rename(columns={'APCN': 'apcn', 'STA_MAC': 'staMac', 'TER_TYPE': 'terType', 'VENDOR_CN': 'vendorCn',
                            'STA_RXBYTES': 'staRxbytes', 'STA_TXBYTES': 'staTxbytes', 'SAMPLEYEAR': 'year',
                            'SAMPLEMON': 'month', 'SAMPLEDAY': 'day', 'SAMPLEMIN': 'minute', 'SAMPLEHOUR': 'hour',
                            'SAMPLEDATE': 'createAt', }, inplace=True)
    data_df.to_csv(file_path + 'wasu_wifi_ap_sta_info_2018.csv', encoding='utf-8')


def addTodayDataRN():
    """
    添加Recordnums

    """
    data = []
    for i in range(1, 37):
        curtime = datetime.datetime.now() + relativedelta(hour=7, minute=0, second=0) + relativedelta(days=i)
        next_day = curtime + relativedelta(days=1)
        print(str(curtime))
        while curtime.day != next_day.day:
            year = curtime.year
            month = curtime.month
            day = curtime.day
            hour = curtime.hour
            minute = curtime.minute
            sec = curtime.second
            for j in range(1, 9):
                for k in range(1, 10):
                    if hour < 19:
                        nums = random.randint(1, 100)
                    else:
                        nums = 0
                    data.append([j, k, nums, year, month, day, hour, minute, sec, str(curtime)[:19]])
            curtime = curtime + relativedelta(minutes=10)
    data_df = pd.DataFrame(data=data,
                           columns=['scenicId', 'camId', 'nums', 'year', 'month', 'day', 'hour', 'minute', 'sec',
                                    'createAt'])
    data_df.to_csv(file_path + 'recordNumsData.csv', encoding='utf-8')


def addTodayDataRW():
    """
    添加Recordwarnings表

    """
    data = []
    for i in range(1, 37):
        curtime = datetime.datetime.now() + relativedelta(hour=7, minute=0, second=0) + relativedelta(days=i)
        print(str(curtime))
        while curtime.hour != 19:
            alert = random.randint(1, 10)
            if alert != 5:
                continue
            j = random.randint(1, 8)
            level = random.randint(1, 3)
            exceedNums = random.randint(1, 50) + 50 * (3 - level)
            data.append([j, 0, level, 1, exceedNums, str(curtime)[:19]])
            curtime = curtime + relativedelta(minutes=10)
    data_df = pd.DataFrame(data=data, columns=['scenicId', 'camId', 'level', 'type', 'exceedNums', 'createAt'])
    data_df.to_csv(file_path + 'recordWarningData.csv', encoding='utf-8')


if __name__ == '__main__':
    getLakeNumbers()
