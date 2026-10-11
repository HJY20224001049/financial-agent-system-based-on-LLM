import warnings
import ssl
import requests
import pandas as pd
import os
from urllib.parse import urlencode
from datetime import datetime, timedelta
import time

# 基础配置
warnings.filterwarnings("ignore")
ssl._create_default_https_context = ssl._create_unverified_context
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

session = requests.Session()
retry = Retry(connect=3, backoff_factor=1)
adapter = HTTPAdapter(max_retries=retry)
session.mount('http://', adapter)
session.mount('https://', adapter)

# 日期范围（过去30天）
yesterday_time = datetime.today().date() - timedelta(days=1)
start_time = yesterday_time - timedelta(days=60)
yesterday = yesterday_time.strftime("%Y%m%d")
start_date = start_time.strftime("%Y%m%d")

# 替换起始行（第6111行，索引6110）
REPLACE_START_INDEX = 6109


def get_stock_daily_data(stock_code):
    """根据网站表头解析数据，映射到stock_data.csv格式"""
    try:
        # 东方财富接口参数（确保与网站数据对应）
        secid = f"1.{stock_code}" if stock_code.startswith(('60', '68')) else f"0.{stock_code}"
        params = {
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f116",
            "ut": "7eea3edcaed734bea9cbfc24409ed989",
            "klt": "101", "fqt": "1",
            "secid": secid,
            "beg": start_date, "end": yesterday
        }
        url = f"https://push2his.eastmoney.com/api/qt/stock/kline/get?{urlencode(params)}"
        time.sleep(0.5)

        response = session.get(url, timeout=30, verify=False)
        response.raise_for_status()
        data = response.json()

        if data.get("rc") != 0:
            raise Exception(f"接口错误：{data.get('msg', '未知错误')}")

        kline_list = data["data"]["klines"]
        if not kline_list:
            print(f"未获取到{stock_code}的历史数据")
            return None

        kline_data = []
        for line in kline_list:
            parts = line.split(',')
            # 打印第一行数据用于验证（需要时取消注释）
            # if not kline_data:
            #     print("原始数据行验证:", parts)

            # 根据最新原始数据解析字段（严格对应索引）
            stock_info = {
                "代码": stock_code,
                "名称": "",  # 接口未返回名称
                "千股千评": "",
                "最新价": float(parts[4]),  # parts[4] = 收盘价（最新价）
                "涨跌额": float(parts[9]),  # parts[9] = 涨跌额（直接使用接口值，如-4.99）
                "涨跌幅": float(parts[8])/100  ,  # parts[8] = 涨跌幅（%，如-0.34）
                "昨收": float(parts[2]),  # parts[2] = 昨日收盘价
                "今开": float(parts[1]),  # parts[1] = 今日开盘价
                "最高": float(parts[3]),  # parts[3] = 当日最高价
                "最低": float(parts[4]),  # parts[4] = 当日最低价（根据原始数据，此处应为最低值，修正之前的错误假设）
                # 成交量：parts[5]为“手”，转换为“万股”（1手=100股 → 万股=手×100÷10000）
                "成交量(万股)": round(int(parts[5]) * 100 / 10000, 2),
                # 成交额：parts[6]为“元”，转换为“万元”（÷10000）
                "成交额(元)": round(float(parts[6]), 2)
            }

            # 映射到stock_data.csv表头（确保与CSV格式一致）
            kline_data.append([
                stock_info["代码"],  # index_code
                pd.to_datetime(parts[0]).strftime("%Y-%m-%d"),  # date
                stock_info["今开"],  # open（开盘价）
                stock_info["最新价"],  # close（收盘价）
                stock_info["最低"],  # low（最低价）
                stock_info["最高"],  # high（最高价）
                int(stock_info["成交量(万股)"] * 10000),  # volume（万股→股，原始单位）
                stock_info["成交额(元)"],  # money（元）
                stock_info["涨跌幅"]  # change（涨跌幅%）
            ])

        # 生成DataFrame
        df = pd.DataFrame(
            kline_data,
            columns=["index_code", "date", "open", "close", "low", "high", "volume", "money", "change"]
        )
        print(f"\n【{stock_code} 过去30天数据】（最近5条）：")
        print(df.tail(5).round(2))
        return df

    except Exception as e:
        print(f"获取{stock_code}数据失败：{str(e)}")
        return None


def replace_csv_from_line(new_df, csv_path="./data/stock_data.csv"):
    """替换CSV中指定行开始的内容"""
    if new_df is None or new_df.empty:
        print("无数据可替换")
        return

    if not os.path.exists(csv_path):
        print(f"错误：原文件 {csv_path} 不存在")
        return

    original_df = pd.read_csv(csv_path)
    original_rows = len(original_df)
    print(f"原CSV共有 {original_rows} 行数据")

    if REPLACE_START_INDEX >= original_rows:
        print(f"替换起始行超出范围，将追加数据")
        updated_df = pd.concat([original_df, new_df], ignore_index=True)
    else:
        updated_df = pd.concat(
            [original_df.iloc[:REPLACE_START_INDEX], new_df],
            ignore_index=True
        )

    updated_df.to_csv(csv_path, index=False, encoding="utf-8")
    print(f"已完成替换，更新后共 {len(updated_df)} 行")


if __name__ == "__main__":
    stock_code = "600519"
    new_data = get_stock_daily_data(stock_code)
    replace_csv_from_line(new_data)