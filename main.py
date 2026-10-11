import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端，避免plt.show()阻塞程序

import ssl
import requests
import pandas as pd
from urllib.parse import urlencode, quote
import warnings
import re
from time import sleep
from lxml import etree
import time
import sys
import numpy as np
import Connect_qwen
import emotion_annalyse
import Scraper
import add_new_data
import stock_predict
# 导入新闻分析和情绪分析模块
from news_analysis.newscraper import create_scraper
from news_analysis.selfmademain import analyze_csv, combine_risk_with_sentiment
# 关闭所有警告
warnings.filterwarnings("ignore")
# 全局SSL配置+请求重试
ssl._create_default_https_context = ssl._create_unverified_context
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime, timedelta
yesterday_time = datetime.today().date()-timedelta(days=1)
yesterday = yesterday_time.strftime("%Y%m%d")
session = requests.Session()
retry = Retry(connect=3, backoff_factor=1)
adapter = HTTPAdapter(max_retries=retry)
session.mount('http://', adapter)
session.mount('https://', adapter)


def get_stock_daily_data(stock_code):
    """东方财富历史日线数据（格式整洁，无空格）"""
    try:
        secid = f"1.{stock_code}" if stock_code.startswith(('60', '68')) else f"0.{stock_code}"
        params = {
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f116",
            "ut": "7eea3edcaed734bea9cbfc24409ed989",
            "klt": "101", "fqt": "1",
            "secid": secid,
            "beg": "20251001", "end": yesterday
        }
        url = f"https://push2his.eastmoney.com/api/qt/stock/kline/get?{urlencode(params)}"

        response = session.get(url, timeout=30, verify=False)
        response.raise_for_status()
        data = response.json()

        if data.get("rc") != 0:
            raise Exception(f"接口错误：{data.get('msg', '未知错误')}")

        kline_list = data["data"]["klines"]
        kline_data = []
        for line in kline_list:
            parts = line.split(',')
            kline_data.append([
                parts[0], abs(float(parts[1])), abs(float(parts[2])),
                abs(float(parts[3])), abs(float(parts[4])), int(parts[5]),
                round(float(parts[6])/10000, 2)
            ])

        df = pd.DataFrame(
            kline_data,
            columns=["日期", "开盘价(元)", "收盘价(元)", "最高价(元)", "最低价(元)", "成交量(手)", "成交额(万元)"]
        )
        # 用日期当索引，消除表头空格，格式更整洁
        # df = df.set_index("日期")
        print(f"\n【{stock_code} 历史日线数据】（最近5条）：")
        print(df.tail(5).round(2))
        return df

    except Exception as e:
        print(f"获取日线数据失败：{str(e)[:60]}...")
        return None


def get_stock_realtime_data(stock_code):

    market_type = 'sh_a' if stock_code.startswith(('60', '68')) else 'sz_a'

    # 整页爬取时的分页范围
    for page in range(0, 21):  # 扩大查询页数，确保覆盖目标股票所在页面
        url = f'http://vip.stock.finance.sina.com.cn/q/go.php/vInvestConsult/kind/qgqp/index.phtml?t={market_type}&p={page}'
        # print(f"正在第{page}页查找 {stock_code} ...")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.5845.97 Safari/537.36 Core/1.116.537.400 QQBrowser/19.4.6561.400"
        }

        try:
            response = requests.get(url, headers=headers)
            response.encoding = 'gbk'
            html_str = response.text

            etree_element = etree.HTML(html_str)
            tr_list = etree_element.xpath('//table[@id="dataTable"]/tr')[1:]  # 跳过表头，和整页爬取一致

            for tr in tr_list:
                try:
                    # XPath
                    current_code = tr.xpath('./td[1]/span/a/text()')[0]

                    # 去除可能的空格或特殊字符，确保精确匹配
                    current_code_clean = current_code.strip()
                    target_code_clean = stock_code.strip()

                    if current_code_clean == target_code_clean:
                        name = tr.xpath('./td[2]/span/a/text()')[0]
                        comment = tr.xpath('./td[3]/a/text()')[0]
                        latest_price = tr.xpath('./td[4]/text()')[0]
                        rise_and_fall_amount = tr.xpath('./td[5]/text()')[0]
                        chg = tr.xpath('./td[6]/text()')[0]
                        yesterday_closing = tr.xpath('./td[7]/text()')[0]
                        today_open = tr.xpath('./td[8]/text()')[0]
                        highest = tr.xpath('./td[9]/text()')[0]
                        minimum = tr.xpath('./td[10]/text()')[0]
                        turnover = tr.xpath('./td[11]/text()')[0]
                        transaction_volume = tr.xpath('./td[12]/text()')[0]

                        stock_data = {
                            '代码': current_code_clean,
                            '名称': name,
                            '千股千评': comment,
                            '最新价': latest_price,
                            '涨跌额': rise_and_fall_amount,
                            '涨跌幅': chg,
                            '昨日收盘': yesterday_closing,
                            '今日开盘': today_open,
                            '最高': highest,
                            '最低': minimum,
                            '成交量(万股)': turnover,
                            '成交额(万元)': transaction_volume
                        }

                        print(f"\n【找到 {stock_code} 数据】（第{page}页）：")
                        for key, value in stock_data.items():
                            print(f"{key}: {value}")
                        return stock_data
                except IndexError:
                    continue  # 跳过异常行

        except Exception as e:
            print(f"第{page}页请求失败：{str(e)[:30]}")
            continue

        time.sleep(1)  # 读完一页延迟1秒免得被反爬

    print(f"\n未在页面中找到 {stock_code}（已检查前20页）")
    return None


def get_stock_financial_indicators(stock_code):
    """和讯财经财务指标（已正常，保留）"""
    try:
        market_prefix = "sh" if stock_code.startswith(('60', '68')) else "sz"
        url = f"http://stockdata.stock.hexun.com/{market_prefix}{stock_code}_finance.shtml"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": f"http://quote.stock.hexun.com/{market_prefix}{stock_code}.shtml"
        }

        sleep(1)
        response = session.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        content = response.text

        # 提取股票名称
        name_match = re.search(r'<title>(.*?)_财务数据', content)
        stock_name = name_match.group(1) if name_match else "贵州茅台"

        # 提取财务指标
        financial_data = {
            "基本每股收益(元)": 0.0,
            "每股净资产(元)": 0.0,
            "市盈率TTM": 0.0,
            "市净率": 0.0
        }

        # 基本每股收益
        eps_match = re.search(r'基本每股收益</th>.*?<td>(.*?)</td>', content, re.DOTALL)
        if eps_match and eps_match.group(1).replace('.', '').isdigit():
            financial_data["基本每股收益(元)"] = float(eps_match.group(1))

        # 每股净资产
        bvps_match = re.search(r'每股净资产</th>.*?<td>(.*?)</td>', content, re.DOTALL)
        if bvps_match and bvps_match.group(1).replace('.', '').isdigit():
            financial_data["每股净资产(元)"] = float(bvps_match.group(1))

        # 市盈率TTM
        pe_match = re.search(r'市盈率\(TTM\)</th>.*?<td>(.*?)</td>', content, re.DOTALL)
        if pe_match and pe_match.group(1).replace('.', '').isdigit():
            financial_data["市盈率TTM"] = float(pe_match.group(1))

        # 市净率
        pb_match = re.search(r'市净率</th>.*?<td>(.*?)</td>', content, re.DOTALL)
        if pb_match and pb_match.group(1).replace('.', '').isdigit():
            financial_data["市净率"] = float(pb_match.group(1))

        # 显示数据
        print(f"\n【{stock_code} 核心财务指标】（和讯财经）：")
        print(f"股票名称: {stock_name}")
        for key, value in financial_data.items():
            if value != 0:
                print(f"{key}: {round(value, 2)}")
        return financial_data

    except requests.Timeout:
        print(f"获取财务指标失败：请求超时（已重试3次）")
        return None
    except Exception as e:
        print(f"获取财务指标失败：{str(e)[:60]}...")
        return None


def search_stock_code(stock_name, excel_file='code-name.xlsx'):
    """输入股票名称，返回对应的股票代码（修复数值类型问题）"""
    try:
        # 读取Excel数据时，根据网页检索要求将"代码"列强制转为字符串类型
        df = pd.read_excel(excel_file, dtype={'代码': str})

        # 检查必要的列
        if '代码' not in df.columns or '名称' not in df.columns:
            return None  # 格式错误返回None

        # 模糊匹配（忽略大小写）
        pattern = re.compile(re.escape(stock_name), re.IGNORECASE)
        matches = df[df['名称'].apply(lambda x: bool(pattern.search(str(x))))]

        # 若有匹配结果，返回第一个股票代码；否则返回None
        return str(matches.iloc[0]['代码']) if not matches.empty else None

    except Exception:
        return None  # 任何错误都返回None


def extract_numbers(response):
    """从LLM输出中提取数字（支持单个数字或用、分隔的数字）"""
    # 正则表达式匹配数字（包括1、4这样的格式）
    pattern = r'\b\d+\b'
    # 查找所有匹配的数字
    numbers = re.findall(pattern, response)
    # 转换为整数类型（或保留字符串类型，根据需求选择）
    numbers = [int(num) for num in numbers]  # 转为整数列表
    # 若需保留字符串类型，用：numbers = [num for num in numbers]
    return numbers


def extract_stock_names(response):
    """从LLM返回的结果中提取【】中的股票名称"""
    # 正则表达式匹配【】中的内容（非贪婪匹配，支持多个）
    pattern = r'【(.*?)】'
    # 查找所有匹配项
    stock_names = re.findall(pattern, response)
    # 去除空字符串（如果有）
    stock_names = [name.strip() for name in stock_names if name.strip()]
    return stock_names


if __name__ == "__main__":
    # 首先获取用户原始问题
    print("输入问题：")
    user_input = input().strip()

    # 调用LLM判断意图和股票
    LLM_response = Connect_qwen.front(user_input)  # 使用已获取的用户输入

    # 保存用户原始问题
    original_question = user_input

    action_list = extract_numbers(LLM_response)
    stock_name_list = extract_stock_names(LLM_response)
    print(f"DEBUG: action_list = {action_list}")
    print(f"DEBUG: stock_name_list = {stock_name_list}")
    # 清洗股票名称列表中的特殊符号（如【】、引号等）
    cleaned_stock_names = []
    for name in stock_name_list:
        # 去除前后的【】、()、[]、""、''等符号
        cleaned_name = name.strip('【】()[]""\'\'').strip()
        if cleaned_name:  # 确保清洗后不为空
            cleaned_stock_names.append(cleaned_name)
    stock_name_list = cleaned_stock_names  # 替换为清洗后的列表

    # 初始化结果收集字典
    results = {
        1: [],  # 风险分析
        2: [],  # 舆情分析
        3: [],  # 股票预测
        4: []   # 查询数字数据
    }

    if len(action_list) != 0:
        for action in action_list:
            if action == 4:
                for name in stock_name_list:
                    if not name:  # 此时已清洗，直接判断是否为空
                        print("股票名称无效")
                        continue  # 跳过空名称，不退出程序
                    stock_code = search_stock_code(name)
                    if stock_code is None:
                        print(f"未找到股票名称「{name}」对应的代码，跳过后续操作")
                        continue
                    print("股票代码：", stock_code)

                    try:
                        # 获取日线数据
                        daily_data = get_stock_daily_data(stock_code)
                        # 获取实时数据
                        realtime_data = get_stock_realtime_data(stock_code)

                        # 收集结果
                        result_text = f"【查询数字数据 - {name} ({stock_code})】\n"
                        if daily_data is not None:
                            result_text += f"历史日线数据（最近5条）：\n{daily_data.tail(5).round(2).to_string()}\n"
                        if realtime_data is not None:
                            result_text += f"实时数据：\n"
                            for key, value in realtime_data.items():
                                result_text += f"  {key}: {value}\n"
                        result_text += "-" * 50 + "\n"
                        results[4].append(result_text)
                    except Exception as e:
                        print(f"  查询股票[{name}]数据时出错：{str(e)}")
                        # 即使出错也生成结果文本
                        result_text = f"【查询数字数据 - {name} ({stock_code})】\n"
                        result_text += f"股票名称：{name}（代码：{stock_code}）\n"
                        result_text += f"  数据查询过程中出错：{str(e)[:100]}\n"
                        result_text += "-" * 50 + "\n"
                        results[4].append(result_text)

            elif action == 1:
                print("风险分析")
                for name in stock_name_list:
                    if not name:  # 此时已清洗，直接判断是否为空
                        print("股票名称无效")
                        continue  # 跳过空名称，不退出程序
                    stock_code = search_stock_code(name)
                    if stock_code is None:
                        print(f"未找到股票名称「{name}」对应的代码，跳过后续操作")
                        continue
                    else:
                        print(f"股票[{name}]的风险分析，代码为{stock_code}：")

                    # 新闻搜索
                    try:
                        # 创建爬虫实例（使用东方财富）
                        scraper = create_scraper('eastmoney')
                        # 使用股票名称作为关键词进行搜索
                        # 对关键词进行URL编码
                        encoded_keyword = quote(name)
                        url = f'https://so.eastmoney.com/news/s?keyword={encoded_keyword}'
                        print(f"  搜索URL: {url}")
                        news_items = scraper.scrape(url, max_pages=3)
                        # 按关键词过滤新闻（二次过滤确保相关性）
                        if news_items:
                            news_items = scraper.filter_news_by_keyword(news_items, name)
                        else:
                            news_items = []

                        if not news_items:
                            print(f"  未找到关于「{name}」的新闻")
                            # 仍然生成一个空的CSV文件以便后续分析
                            csv_file = f"stock_news_{name}.csv"
                            pd.DataFrame(columns=['title', 'date', 'source', 'url']).to_csv(csv_file, index=False, encoding='utf-8-sig')
                        else:
                            print(f"  找到{len(news_items)}条相关新闻")
                            # 保存到CSV文件
                            csv_file = f"stock_news_{name}.csv"
                            scraper.save_to_csv(news_items, csv_file)

                        # 情绪分析
                        print(f"  开始情绪分析...")
                        df = analyze_csv(csv_file, text_col="title", output_csv=None)

                        # 总结情绪分析结果
                        if df is not None and not df.empty:
                            # 计算平均情感分数
                            avg_score = df['sentiment_score'].mean()
                            # 统计情感标签分布
                            sentiment_counts = df['sentiment_label'].value_counts().to_dict()
                            pos_count = sentiment_counts.get('积极', 0)
                            neg_count = sentiment_counts.get('消极', 0)
                            neu_count = sentiment_counts.get('中性', 0)
                            total_news = len(df)

                            result_text = f"【风险分析 - {name} ({stock_code})】\n"
                            result_text += f"股票名称：{name}（代码：{stock_code}）\n"
                            result_text += f"  新闻数量：{total_news}\n"
                            result_text += f"  积极新闻：{pos_count}条，消极新闻：{neg_count}条，中性新闻：{neu_count}条\n"
                            result_text += f"  平均情感分数：{avg_score:.3f}\n"
                            # 根据平均分数给出风险提示
                            if avg_score > 0.6:
                                risk = "较低风险（积极情绪主导）"
                            elif avg_score < 0.4:
                                risk = "较高风险（消极情绪主导）"
                            else:
                                risk = "中等风险（情绪中性）"
                            result_text += f"  风险提示：{risk}\n"
                            result_text += "-" * 50 + "\n"
                        else:
                            result_text = f"【风险分析 - {name} ({stock_code})】\n"
                            result_text += f"股票名称：{name}（代码：{stock_code}）\n"
                            result_text += f"  未找到可分析的新闻数据\n"
                            result_text += "-" * 50 + "\n"

                        # 将结果保存到riskanalysis.txt
                        with open('riskanalysis.txt', 'a', encoding='utf-8-sig') as f:
                            f.write(result_text)
                        print(f"  结果已保存到riskanalysis.txt")

                        # 收集结果
                        results[1].append(result_text)

                        # 清理临时CSV文件（可选）
                        import os
                        if os.path.exists(csv_file):
                            os.remove(csv_file)
                            print(f"  临时文件{csv_file}已删除")

                    except Exception as e:
                        print(f"  处理股票[{name}]时出错：{str(e)}")
                        import traceback
                        traceback.print_exc()
                        # 即使出错也生成结果文本
                        result_text = f"【风险分析 - {name} ({stock_code})】\n"
                        result_text += f"股票名称：{name}（代码：{stock_code}）\n"
                        result_text += f"  风险分析过程中出错：{str(e)[:100]}\n"
                        result_text += "-" * 50 + "\n"
                        results[1].append(result_text)
                        continue  # 出错后继续处理下一只股票
            elif action == 2:# 舆情分析
                for name in stock_name_list:
                    if not name:  # 此时已清洗，直接判断是否为空
                        print("股票名称无效")
                        continue  # 跳过空名称，不退出程序
                    stock_code = search_stock_code(name)
                    if stock_code is None:
                        print(f"未找到股票名称「{name}」对应的代码，跳过后续操作")
                        continue
                    else:
                        print(f"股票[{name}]的舆情分析，代码为{stock_code}：  ")

                    # 执行舆情分析，添加异常处理
                    try:
                        Scraper.scrape_stock_comments(stock_code)
                        emotion_annalyse.classify_csv_comments(threshold=0.4)
                        print(f"舆情分析完成：已爬取评论并完成情感分析")
                    except Exception as e:
                        print(f"舆情分析过程出错：{e}")
                        import traceback
                        traceback.print_exc()
                        # 即使分析过程出错，也生成结果文本
                        result_text = f"【舆情分析 - {name} ({stock_code})】\n"
                        result_text += f"股票名称：{name}（代码：{stock_code}）\n"
                        result_text += f"  舆情分析过程中出错：{str(e)[:100]}\n"
                        result_text += "-" * 50 + "\n"
                        results[2].append(result_text)
                        continue  # 继续处理下一只股票

                    # 读取舆情分析结果
                    try:
                        import pandas as pd
                        import os
                        input_file = 'stock_comments.csv'
                        sentiment_file = 'stock_comments_with_sentiment.csv'

                        # 检查输入文件是否存在
                        if not os.path.exists(input_file):
                            print(f"  警告：输入文件 {input_file} 不存在，可能爬虫未成功抓取评论")
                            result_text = f"【舆情分析 - {name} ({stock_code})】\n"
                            result_text += f"股票名称：{name}（代码：{stock_code}）\n"
                            result_text += f"  错误：未找到评论数据文件 {input_file}\n"
                            result_text += f"  可能原因：爬虫未成功抓取到评论数据\n"
                            result_text += "-" * 50 + "\n"
                            results[2].append(result_text)
                            continue

                        # 检查输出文件是否存在
                        if not os.path.exists(sentiment_file):
                            print(f"  警告：输出文件 {sentiment_file} 不存在，情感分析可能失败")
                            result_text = f"【舆情分析 - {name} ({stock_code})】\n"
                            result_text += f"股票名称：{name}（代码：{stock_code}）\n"
                            result_text += f"  错误：情感分析结果文件 {sentiment_file} 未生成\n"
                            result_text += f"  可能原因：情感分析模型处理失败\n"
                            result_text += "-" * 50 + "\n"
                            results[2].append(result_text)
                            continue

                        # 尝试读取输出文件
                        try:
                            df = pd.read_csv(sentiment_file, encoding='utf-8-sig')
                        except UnicodeDecodeError:
                            # 尝试其他编码
                            try:
                                df = pd.read_csv(sentiment_file, encoding='utf_8_sig')
                            except UnicodeDecodeError:
                                df = pd.read_csv(sentiment_file, encoding='gbk')
                        except Exception as e:
                            print(f"  读取文件 {sentiment_file} 失败：{e}")
                            raise

                        # 检查必要的列是否存在
                        if 'sentiment' not in df.columns:
                            print(f"  警告：输出文件缺少 'sentiment' 列")
                            result_text = f"【舆情分析 - {name} ({stock_code})】\n"
                            result_text += f"股票名称：{name}（代码：{stock_code}）\n"
                            result_text += f"  错误：情感分析结果文件格式不正确\n"
                            result_text += f"  文件列名：{list(df.columns)}\n"
                            result_text += "-" * 50 + "\n"
                            results[2].append(result_text)
                            continue

                        pos_cnt = len(df[df['sentiment'] == '积极'])
                        neg_cnt = len(df[df['sentiment'] == '消极'])
                        total_cnt = len(df)

                        result_text = f"【舆情分析 - {name} ({stock_code})】\n"
                        result_text += f"股票名称：{name}（代码：{stock_code}）\n"
                        result_text += f"  总评论数：{total_cnt}条\n"
                        result_text += f"  积极评论：{pos_cnt}条 ({pos_cnt/total_cnt:.1%})\n"
                        result_text += f"  消极评论：{neg_cnt}条 ({neg_cnt/total_cnt:.1%})\n"
                        if total_cnt > 0:
                            if pos_cnt > neg_cnt:
                                sentiment_summary = "整体情绪偏积极"
                            elif neg_cnt > pos_cnt:
                                sentiment_summary = "整体情绪偏消极"
                            else:
                                sentiment_summary = "情绪中性"
                            result_text += f"  舆情总结：{sentiment_summary}\n"

                            # 添加样本评论示例
                            if total_cnt > 5:
                                sample_pos = df[df['sentiment'] == '积极'].head(2)
                                sample_neg = df[df['sentiment'] == '消极'].head(2)
                                result_text += f"\n  评论示例：\n"
                                if not sample_pos.empty:
                                    for idx, row in sample_pos.iterrows():
                                        title = row.get('title', '')[:50] + "..." if len(str(row.get('title', ''))) > 50 else str(row.get('title', ''))
                                        result_text += f"    - [积极] {title}\n"
                                if not sample_neg.empty:
                                    for idx, row in sample_neg.iterrows():
                                        title = row.get('title', '')[:50] + "..." if len(str(row.get('title', ''))) > 50 else str(row.get('title', ''))
                                        result_text += f"    - [消极] {title}\n"
                        result_text += "-" * 50 + "\n"
                        results[2].append(result_text)

                    except Exception as e:
                        print(f"读取舆情分析结果失败：{e}")
                        import traceback
                        traceback.print_exc()
                        result_text = f"【舆情分析 - {name} ({stock_code})】\n"
                        result_text += f"股票名称：{name}（代码：{stock_code}）\n"
                        result_text += f"  舆情分析完成，但读取结果时出错：{str(e)[:100]}\n"
                        result_text += f"  详细错误：请检查 stock_comments.csv 和 stock_comments_with_sentiment.csv 文件是否正常生成\n"
                        result_text += "-" * 50 + "\n"
                        results[2].append(result_text)

            elif action == 3:
                print("股票预测")
                for name in stock_name_list:
                    if not name:  # 此时已清洗，直接判断是否为空
                        print("股票名称无效")
                        continue  # 跳过空名称，不退出程序
                    stock_code = search_stock_code(name)
                    if stock_code is None:
                        print(f"未找到股票名称「{name}」对应的代码，跳过后续操作")
                        continue
                    else:
                        print(f"股票[{name}]的预测，代码为{stock_code}：  ")
                        # 更新数据
                        new_data = add_new_data.get_stock_daily_data(stock_code)
                        add_new_data.replace_csv_from_line(new_data)  # 替换/追加数据到CSV

                        # 初始化配置
                        config = stock_predict.Config()
                        # 关键：开启训练模式（增量训练）
                        config.do_train = False
                        config.do_predict = True  # 训练后执行预测
                        config.add_train = True  # 启用增量训练（加载已有模型")
                        # 保存图表而不显示，避免阻塞程序
                        config.do_figure_save = True

                        # 置信区间参数调整（如果置信区间太宽，可以调整以下参数）
                        # config.confidence_level = 0.90  # 置信水平: 0.80(80%), 0.85(85%), 0.90(90%), 0.95(95%), 0.99(99%)
                        # config.use_standard_error = True  # 使用标准误差(True: 置信区间更窄, False: 使用原始标准差)
                        # config.confidence_interval_scale = 0.5  # 置信区间宽度缩放因子，小于1缩小，大于1放大
                        # config.smooth_errors = True  # 对误差进行平滑处理，减少波动
                        # config.smooth_window = 10  # 平滑窗口大小

                        try:
                            # 步骤1：备份原始模型为a和b
                            stock_predict.backup_model(config)

                            # 步骤2：修改模型名为副本a，用于增量训练
                            config.model_name = f"model_a{config.model_postfix[config.used_frame]}"

                            # 加载数据和日志
                            logger = stock_predict.load_logger(config)
                            data = stock_predict.Data(config)

                            # 获取训练/验证数据（四元组：train_X, valid_X, train_Y, valid_Y）
                            train_X, valid_X, train_Y, valid_Y = data.get_train_and_valid_data()

                            # 检查数据维度（核心：确保样本数一致）
                            assert train_X.shape[0] == train_Y.shape[0], \
                                f"训练数据维度不匹配：train_X样本数{train_X.shape[0]}，train_Y样本数{train_Y.shape[0]}"
                            assert valid_X.shape[0] == valid_Y.shape[0], \
                                f"验证数据维度不匹配：valid_X样本数{valid_X.shape[0]}，valid_Y样本数{valid_Y.shape[0]}"

                            # 执行增量训练（传递正确的四元组数据）
                            np.random.seed(config.random_seed)
                            stock_predict.train(config, logger, [train_X, train_Y, valid_X, valid_Y])
                            test_X, test_Y = data.get_test_data(return_label_data=True)  # 获取测试数据
                            pred_result = stock_predict.predict(config, test_X)  # 基于模型a预测
                            stock_predict.draw(config, data, logger, pred_result)  # 输出预测结果（含日志）

                            # 步骤3：训练后用副本b恢复原始模型
                            # 恢复原模型名（与Config中默认命名一致："model_pytorch.pth"）
                            config.model_name = f"model_{config.continue_flag}{config.used_frame}{config.model_postfix[config.used_frame]}"
                            stock_predict.restore_model(config)

                            # 收集结果 - 从预测结果中提取关键信息
                            # 计算实际预测价格（反归一化）
                            predict_data = pred_result * data.std[config.label_in_feature_index] + data.mean[config.label_in_feature_index]

                            # 获取标签列名
                            label_name = [data.data_column_name[i] for i in config.label_in_feature_index]

                            result_text = f"【股票预测 - {name} ({stock_code})】\n"
                            result_text += f"股票名称：{name}（代码：{stock_code}）\n"
                            result_text += f"  已使用增量训练更新预测模型\n"
                            result_text += f"  预测未来 {config.predict_day} 天价格：\n"

                            # 显示每个预测指标的预测值
                            for i in range(len(label_name)):
                                # 获取最后predict_day天的预测值
                                predicted_values = predict_data[-config.predict_day:, i]
                                if config.predict_day == 1:
                                    result_text += f"  {label_name[i]}：{predicted_values[0]:.2f}\n"
                                else:
                                    for day_idx, value in enumerate(predicted_values, 1):
                                        result_text += f"  第{day_idx}天 {label_name[i]}：{value:.2f}\n"

                            # 如果有历史数据对比，可以显示最近的实际值
                            if hasattr(data, 'data') and data.data is not None:
                                # 获取最近的实际价格
                                recent_actual = data.data[-5:, config.label_in_feature_index]  # 最近5天的实际值
                                result_text += f"\n  最近实际价格（供参考）：\n"
                                for i in range(len(label_name)):
                                    actual_values = recent_actual[:, i]
                                    result_text += f"  {label_name[i]}：{', '.join([f'{v:.2f}' for v in actual_values])}\n"

                            result_text += f"  预测图表已生成，可查看详细走势\n"
                            result_text += "-" * 50 + "\n"
                            results[3].append(result_text)
                            print(f"DEBUG: 已添加股票预测结果到 results[3]，当前长度：{len(results[3])}")

                        except Exception as e:
                            print(f"处理股票[{name}]时出错：{str(e)}")
                            # 即使出错也记录结果
                            result_text = f"【股票预测 - {name} ({stock_code})】\n"
                            result_text += f"股票名称：{name}（代码：{stock_code}）\n"
                            result_text += f"  预测过程中出错：{str(e)[:100]}\n"
                            result_text += "-" * 50 + "\n"
                            results[3].append(result_text)
                            continue  # 出错后继续处理下一只股票

        # ===== 若同时调用了风险分析（1）和舆情分析（2），进行综合风险评估 =====
        if 1 in action_list and 2 in action_list:
            print("\n" + "="*60)
            print("检测到同时调用了风险分析与舆情分析，正在生成综合风险评估...")
            print("="*60)
            combined_risk_results = []
            for risk_text in results[1]:
                # 调用风险分析模块的融合函数，将舆情分析结果融入风险分析
                combined_text = combine_risk_with_sentiment(
                    risk_text, results[2],
                    stock_name=None, stock_code=None
                )
                combined_risk_results.append(combined_text)

            if combined_risk_results:
                # 用综合风险评估替换原有的风险分析结果
                results[1] = combined_risk_results
                # 更新 riskanalysis.txt：追加综合评估结果
                try:
                    with open('riskanalysis.txt', 'a', encoding='utf-8-sig') as f:
                        f.write("\n" + "【以下为综合风险评估（融合舆情分析结果）】\n")
                        for text in combined_risk_results:
                            f.write(text)
                    print("综合风险评估结果已追加到 riskanalysis.txt")
                except Exception as e:
                    print(f"保存综合风险评估到文件失败：{e}")

        # 所有action执行完毕后，汇总结果并调用LLM分析
        print("\n" + "="*60)
        print("所有分析完成，开始汇总结果并生成最终建议...")
        print("="*60)

        # 构建汇总文本
        summary = f"原始用户问题：{original_question}\n\n"
        summary += "="*60 + "\n"

        # 添加各action结果
        action_names = {
            1: "风险分析结果",
            2: "舆情分析结果",
            3: "股票预测结果",
            4: "查询数字数据结果"
        }

        total_results = 0
        print(f"DEBUG: 开始汇总结果，action_list = {action_list}")
        for action in action_list:
            print(f"DEBUG: 处理 action {action}, results[{action}] 长度 = {len(results[action]) if action in results else 'key not found'}")
            if action in results and len(results[action]) > 0:
                summary += f"\n【{action_names[action]}】\n"
                for result in results[action]:
                    summary += result
                total_results += len(results[action])

        if total_results > 0:
            # 调用LLM进行综合分析
            print(f"\n汇总了{total_results}个分析结果，正在生成最终建议...")

            # 构建LLM提示词
            llm_prompt = f"""你是一位专业的金融分析师。以下是根据用户问题"{original_question}"执行股票分析工具得到的结果汇总：

{summary}

请根据以上分析结果和用户问题，回答用户的问题，为用户提供专业的投资建议和综合分析。请包括：
1. 总体评估：基于所有分析维度的综合评估
2. 关键发现：从各分析维度中发现的重要信息
3. 后续建议：建议进一步关注的方向或指标

请以专业、客观的语气提供分析，并确保建议基于上述数据并围绕用户问题。"""

            try:
                # 调用LLM API
                final_analysis = Connect_qwen.call_qianwen_api(llm_prompt)
                print("\n" + "="*60)
                print("最终分析建议：")
                print("="*60)
                print(final_analysis)
            except Exception as e:
                print(f"调用LLM生成最终建议失败：{e}")
                final_analysis = "LLM分析失败，请查看以下分析结果汇总。"
                print("以下是分析结果汇总：")
                print(summary)

            # 将结果保存到文件（无论LLM是否成功）
            try:
                with open('final_analyse.txt', 'w', encoding='utf-8-sig') as f:
                    f.write(f"原始问题：{original_question}\n\n")
                    f.write("分析结果汇总：\n")
                    f.write(summary)
                    f.write("\n" + "="*60 + "\n")
                    f.write("最终分析建议：\n")
                    f.write("="*60 + "\n")
                    f.write(final_analysis)
                print(f"\n分析结果已保存到 final_analyse.txt")
                # 调试输出：检查results字典
                print(f"DEBUG: results 字典内容:")
                for action_key in sorted(results.keys()):
                    print(f"  results[{action_key}] 长度 = {len(results[action_key])}")
                    if len(results[action_key]) > 0:
                        print(f"    第一个结果前100字符: {results[action_key][0][:100]}")
            except Exception as e:
                print(f"保存结果到文件失败：{e}")
        else:
            print("没有收集到任何分析结果。")

    else:
        print(LLM_response)
