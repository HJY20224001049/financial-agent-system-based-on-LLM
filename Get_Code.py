# -*- coding: utf-8 -*-
import requests
from lxml import etree
import pandas as pd
import time


def get_html(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.5845.97 Safari/537.36 Core/1.116.537.400 QQBrowser/19.4.6561.400"
    }
    response = requests.get(url, headers=headers)
    response.encoding = 'gbk'  # 新浪财经编码
    return response.text


def get_data(data_list, html_str):
    etree_element = etree.HTML(html_str)
    tr_list = etree_element.xpath('//table[@id="dataTable"]/tr')[1:]  # 跳过表头

    for tr in tr_list:
        try:
            # 只提取股票代码和名称
            code = tr.xpath('./td[1]/span/a/text()')[0].strip()  # 去除可能的空格
            name = tr.xpath('./td[2]/span/a/text()')[0].strip()

            print(f'代码: {code}, 名称: {name}')
            data_list.append({'代码': code, '名称': name})
        except IndexError:
            print("跳过异常行数据")
            continue


def save(data_list):
    """只保存股票代码和名称到Excel"""
    df = pd.DataFrame(data_list)
    df.drop_duplicates(subset=['代码'])  # 按代码去重
    df.to_excel('code-name.xlsx', index=False)


def main():
    page_num = 20  # 爬取的页数
    data_list = []

    for i in range(1, page_num + 1):
        url = f'http://vip.stock.finance.sina.com.cn/q/go.php/vInvestConsult/kind/qgqp/index.phtml?t=sh_a&p={i}'
        print(f"正在爬取第{i}页: {url}")

        html_str = get_html(url)
        get_data(data_list, html_str)
        time.sleep(2)  # 延迟2s避免被限制

    save(data_list)
    print(f"爬取完成，共获取{len(data_list)}条股票代码和名称，已保存至Excel")


if __name__ == '__main__':
    main()