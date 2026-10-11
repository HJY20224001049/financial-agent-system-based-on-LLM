#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
股票新闻爬虫
用于爬取股票相关新闻标题，供selfmademain.py进行情感分析
支持新浪财经、东方财富等常见新闻网站
"""

import os
import sys
import csv
import time
import logging
import argparse
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup
import pandas as pd
from lxml import etree

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 尝试导入Selenium相关模块（可选）
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.chrome.service import Service as ChromeService
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
    logger.debug("Selenium模块导入成功")
except ImportError:
    SELENIUM_AVAILABLE = False
    logger.info("Selenium不可用，如需处理动态页面请安装: pip install selenium webdriver-manager")

# 默认请求头，模拟浏览器访问
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

def parse_date_string(date_str: str) -> Optional[datetime]:
    """
    解析各种格式的日期字符串
    支持格式: YYYY-MM-DD, YYYY年MM月DD日, MM-DD, 今天, 昨天, X小时前, X分钟前等
    """
    if not date_str:
        return None

    date_str = date_str.strip()
    today = datetime.now()

    # 处理相对时间
    if '今天' in date_str:
        return today.replace(hour=0, minute=0, second=0, microsecond=0)
    elif '昨天' in date_str:
        return (today - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    elif '小时前' in date_str:
        try:
            hours = int(''.join(filter(str.isdigit, date_str)))
            return today - timedelta(hours=hours)
        except:
            return today
    elif '分钟前' in date_str:
        try:
            minutes = int(''.join(filter(str.isdigit, date_str)))
            return today - timedelta(minutes=minutes)
        except:
            return today

    # 处理标准格式
    try:
        # YYYY-MM-DD
        if '-' in date_str and len(date_str.split('-')) == 3:
            return datetime.strptime(date_str, '%Y-%m-%d')
        # YYYY年MM月DD日
        elif '年' in date_str and '月' in date_str and '日' in date_str:
            date_str = date_str.replace('年', '-').replace('月', '-').replace('日', '')
            return datetime.strptime(date_str, '%Y-%m-%d')
        # MM-DD (假设是今年)
        elif '-' in date_str and len(date_str.split('-')) == 2:
            return datetime.strptime(f"{today.year}-{date_str}", '%Y-%m-%d')
    except Exception as e:
        logger.debug(f"日期解析失败: {date_str} - {str(e)}")

    # 默认返回今天
    return today.replace(hour=0, minute=0, second=0, microsecond=0)


class NewsScraper:
    """股票新闻爬虫基类"""

    def __init__(self, headers: Dict = None, timeout: int = 30):
        """
        初始化爬虫
        :param headers: HTTP请求头
        :param timeout: 请求超时时间（秒）
        """
        self.headers = headers or DEFAULT_HEADERS
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def fetch_page(self, url: str) -> Optional[str]:
        """
        获取页面内容
        :param url: 页面URL
        :return: 页面HTML内容
        """
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            response.encoding = response.apparent_encoding or 'utf-8'
            return response.text
        except requests.exceptions.RequestException as e:
            logger.error(f"请求页面失败: {url} - {str(e)}")
            return None

    def parse_news_list(self, html: str) -> List[Dict]:
        """
        解析新闻列表页，提取新闻信息
        子类需要重写此方法
        :param html: 页面HTML
        :return: 新闻信息列表，每个元素为字典，包含title、url、date等字段
        """
        raise NotImplementedError("子类必须实现parse_news_list方法")

    def scrape(self, url: str, max_pages: int = 1) -> List[Dict]:
        """
        爬取新闻
        :param url: 起始URL
        :param max_pages: 最大爬取页数
        :return: 新闻信息列表
        """
        all_news = []
        prev_titles = set()  # 上一页的标题集合，用于检测分页是否有效

        for page in range(1, max_pages + 1):
            logger.info(f"正在爬取第 {page} 页: {url}")

            # 处理分页URL
            page_url = self._get_page_url(url, page)
            logger.info(f"生成的分页URL: {page_url}")
            html = self.fetch_page(page_url)

            if not html:
                logger.warning(f"第 {page} 页获取失败，跳过")
                continue

            news_items = self.parse_news_list(html)
            if not news_items:
                logger.warning(f"第 {page} 页未解析到新闻，可能页面结构已变化")
                break

            # 检测分页有效性：比较当前页与上一页的新闻标题重叠度
            current_titles = {item.get('title', '') for item in news_items if item.get('title', '')}
            if prev_titles and current_titles:
                overlap = len(prev_titles.intersection(current_titles))
                overlap_ratio = overlap / len(current_titles) if len(current_titles) > 0 else 0
                if overlap_ratio > 0.7:  # 如果超过70%重复，可能分页无效
                    logger.warning(
                        f"第 {page} 页与上一页新闻重叠度高达 {overlap_ratio:.1%} "
                        f"({overlap}/{len(current_titles)})，分页可能无效。"
                        f"尝试检查分页参数或网站分页机制。"
                    )
                    # 调用钩子方法，子类可以实现特定处理逻辑
                    self._on_pagination_suspected(page, overlap_ratio)

            prev_titles = current_titles

            all_news.extend(news_items)
            logger.info(f"第 {page} 页爬取到 {len(news_items)} 条新闻")

            # 避免请求过快
            time.sleep(1)

        logger.info(f"总共爬取到 {len(all_news)} 条新闻")
        return all_news

    def _get_page_url(self, base_url: str, page: int) -> str:
        """
        根据基础URL和页码生成分页URL
        子类可重写此方法以适应不同的分页规则
        :param base_url: 基础URL
        :param page: 页码
        :return: 分页URL
        """
        # 默认分页规则：在URL末尾添加 ?page= 或 /page/
        if '?' in base_url:
            return f"{base_url}&page={page}"
        else:
            return f"{base_url}?page={page}"

    def filter_news_by_keyword(self, news_items: List[Dict], keyword: str,
                                case_sensitive: bool = False,
                                match_whole_word: bool = False) -> List[Dict]:
        """
        根据关键词筛选新闻
        :param news_items: 新闻信息列表
        :param keyword: 筛选关键词
        :param case_sensitive: 是否区分大小写（默认不区分）
        :param match_whole_word: 是否匹配完整单词（默认部分匹配）
        :return: 筛选后的新闻列表
        """
        if not keyword or not news_items:
            return news_items

        filtered_items = []
        keyword_lower = keyword if case_sensitive else keyword.lower()

        for item in news_items:
            title = item.get('title', '')
            if not title:
                continue

            title_to_check = title if case_sensitive else title.lower()

            if match_whole_word:
                # 匹配完整单词（单词边界）
                words = title_to_check.split()
                if keyword_lower in words:
                    filtered_items.append(item)
            else:
                # 部分匹配（子字符串）
                if keyword_lower in title_to_check:
                    filtered_items.append(item)

        logger.info(f"关键词筛选: 从 {len(news_items)} 条新闻中筛选出包含关键词 '{keyword}' 的 {len(filtered_items)} 条新闻")
        return filtered_items

    def _on_pagination_suspected(self, page: int, overlap_ratio: float):
        """
        当检测到分页可能无效时的回调方法
        子类可以重写此方法以采取特定行动（如切换分页参数）
        :param page: 当前页码
        :param overlap_ratio: 与上一页的重叠比例
        """
        # 基类默认不采取任何行动
        pass

    def save_to_csv(self, news_items: List[Dict], output_file: str):
        """
        将新闻保存到CSV文件
        :param news_items: 新闻信息列表
        :param output_file: 输出CSV文件路径
        """
        if not news_items:
            logger.warning("没有新闻数据可保存")
            return

        # 确保输出目录存在
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 转换为DataFrame
        df = pd.DataFrame(news_items)

        # 如果数据中没有'title'列，则使用其他可能的列名
        if 'title' not in df.columns:
            # 尝试常见的中文列名
            possible_title_columns = ['标题', '新闻标题', 'title', '新闻']
            for col in possible_title_columns:
                if col in df.columns:
                    df.rename(columns={col: 'title'}, inplace=True)
                    break

        # 确保有'title'列（selfmademain.py需要的列）
        if 'title' not in df.columns and len(df) > 0:
            logger.warning("数据中没有找到标题列，将创建空标题列")
            df['title'] = ''

        # 保存到CSV
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        logger.info(f"新闻数据已保存到: {output_file}，共 {len(df)} 条记录")


class SinaFinanceScraper(NewsScraper):
    """新浪财经股票新闻爬虫"""

    def parse_news_list(self, html: str) -> List[Dict]:
        """
        解析新浪财经股票新闻列表页
        示例URL: https://finance.sina.com.cn/stock/
        """
        soup = BeautifulSoup(html, 'lxml')
        news_items = []

        # 判断是否为搜索结果页面
        is_search_page = 'search' in html.lower() or '搜索结果' in html

        if is_search_page:
            # 搜索结果页面选择器
            logger.info("检测到搜索结果页面，使用搜索选择器")
            selectors = [
                '.result .title a',  # 搜索结果标题
                '.search-result-item h3 a',
                '.box-result .tit a',
                '.list-blk li a',
                'h3 a',  # 通用h3链接
                'a[href*=".shtml"]',  # 包含.shtml的链接
                '.content h2 a',
            ]
        else:
            # 普通新闻列表页选择器 - 优先选择新闻链接
            selectors = [
                # 首先尝试新闻特定的选择器
                'a[href*=".shtml"]',  # 包含.shtml的链接（很可能是新闻）
                'a[href*="/202"][href*=".shtml"]',  # 包含日期和.shtml的链接（很可能是新闻文章）
                'a[href*="/stock/"][href*=".shtml"]',  # 包含stock且以.shtml结尾的链接
                'a[href*="article"]',  # 包含article的链接（通常是新闻文章）
                '.news-item h2 a',  # 常见选择器
                '.news-title a',    # 新闻标题
                '.tit a',           # 标题选择器
                '.list_009 li a',   # 另一种选择器
                '.blk_12 li a',
                '.m-content li a',  # 主内容区链接
                '.listBlk li a',    # 列表区块链接
                '.bd li a',         # 主体列表链接
                'a[href*="/stock/"]',  # 包含stock的链接（最后尝试）
            ]

        for selector in selectors:
            links = soup.select(selector)
            if links:
                logger.info(f"使用选择器 '{selector}' 找到 {len(links)} 个链接")
                for link in links:
                    try:
                        title = link.get_text(strip=True)
                        url = link.get('href', '')

                        # 过滤太短的标题（可能是导航或按钮）
                        if len(title) < 8:
                            continue

                        # 过滤常见的导航文本
                        if title in ['要闻公告', '实时数据', '复盘数据', '基本面', '特色', '财经首页', '股票首页', '返回首页']:
                            continue

                        # 确保URL是完整URL
                        if url and not url.startswith('http'):
                            url = f"https://finance.sina.com.cn{url}" if url.startswith('/') else f"https://finance.sina.com.cn/{url}"

                        # 提取时间（尝试从父元素或附近元素查找）
                        time_element = link.find_parent().find(class_='time') or link.find_next_sibling(class_='time')
                        date_str = time_element.get_text(strip=True) if time_element else datetime.now().strftime('%Y-%m-%d')

                        news_items.append({
                            'title': title,
                            'url': url,
                            'date': date_str,
                            'source': '新浪财经'
                        })

                    except Exception as e:
                        logger.debug(f"解析链接时出错: {str(e)}")
                        continue

                if news_items:
                    break  # 找到新闻后停止尝试其他选择器

        return news_items

    def _get_page_url(self, base_url: str, page: int) -> str:
        """新浪财经分页规则"""
        if page == 1:
            return base_url

        # 检查是否为搜索URL
        if 'search/index.php' in base_url or 'q=' in base_url:
            # 搜索URL分页：添加或更新page参数
            if 'page=' in base_url:
                # 替换现有的page参数
                import re
                return re.sub(r'page=\d+', f'page={page}', base_url)
            else:
                # 添加page参数
                if '?' in base_url:
                    return f"{base_url}&page={page}"
                else:
                    return f"{base_url}?page={page}"

        # 普通新闻列表页分页
        # 如果URL以.shtml结尾，使用 _页码.shtml 格式
        if base_url.endswith('.shtml'):
            base = base_url.replace('.shtml', '')
            return f"{base}_{page}.shtml"
        elif base_url.endswith('/'):
            # 如果URL以/结尾，可能是目录，使用 index_页码.shtml 格式
            return f"{base_url}index_{page}.shtml"
        else:
            # 否则使用查询参数 ?page=页码 格式
            if '?' in base_url:
                return f"{base_url}&page={page}"
            else:
                return f"{base_url}?page={page}"


class EastMoneyScraper(NewsScraper):
    """东方财富股票新闻爬虫"""

    def __init__(self, headers: Dict = None, timeout: int = 30):
        super().__init__(headers, timeout)
        # 分页参数列表，按优先级尝试
        self._pagination_params = ['page', 'p', 'pageindex', 'pn']
        self._current_pagination_index = 0  # 当前使用的参数索引

    def _on_pagination_suspected(self, page: int, overlap_ratio: float):
        """
        检测到分页可能无效时，尝试切换分页参数
        """
        if self._current_pagination_index < len(self._pagination_params) - 1:
            self._current_pagination_index += 1
            new_param = self._pagination_params[self._current_pagination_index]
            logger.warning(f"分页可能无效，切换到分页参数: '{new_param}'")
        else:
            logger.warning("已尝试所有分页参数，分页可能仍然无效。请检查网站分页机制。")

    def scrape(self, url: str, max_pages: int = 1, use_selenium_pagination: bool = True) -> List[Dict]:
        """
        重写scrape方法，对东方财富搜索页面使用Selenium模拟点击分页

        :param url: 起始URL
        :param max_pages: 最大爬取页数
        :param use_selenium_pagination: 是否使用Selenium模拟点击分页（仅对搜索页面有效）
        :return: 新闻信息列表
        """
        # 检查是否为搜索页面且Selenium可用且允许使用Selenium分页
        is_search_page = 'so.eastmoney.com' in url or 'keyword=' in url

        if is_search_page and SELENIUM_AVAILABLE and use_selenium_pagination:
            logger.info(f"检测到东方财富搜索页面，使用Selenium模拟点击分页: {url}")
            return self._scrape_with_selenium_pagination(url, max_pages)
        else:
            # 使用父类逻辑（普通分页）
            return super().scrape(url, max_pages)

    def _scrape_with_selenium_pagination(self, url: str, max_pages: int) -> List[Dict]:
        """
        使用Selenium模拟点击分页按钮来爬取多页内容
        """
        all_news = []
        driver = None

        try:
            # 启动Selenium浏览器
            driver = self._create_selenium_driver()
            if driver is None:
                logger.error("无法创建Selenium WebDriver，回退到普通爬取")
                # 回退到父类方法，但禁用Selenium分页以避免递归
                return super().scrape(url, max_pages)

            logger.info(f"Selenium正在加载页面: {url}")
            driver.get(url)

            # 等待页面加载完成
            self._wait_for_news_elements(driver)

            prev_titles = set()
            for page in range(1, max_pages + 1):
                logger.info(f"正在处理第 {page} 页")

                # 获取当前页面HTML并解析新闻
                html = driver.page_source
                news_items = self.parse_news_list(html)

                # 检测分页有效性：比较当前页与上一页的新闻标题重叠度
                current_titles = {item.get('title', '') for item in news_items if item.get('title', '')}
                if prev_titles and current_titles:
                    overlap = len(prev_titles.intersection(current_titles))
                    overlap_ratio = overlap / len(current_titles) if len(current_titles) > 0 else 0
                    if overlap_ratio > 0.7:  # 如果超过70%重复，可能分页无效
                        logger.warning(
                            f"第 {page} 页与上一页新闻重叠度高达 {overlap_ratio:.1%} "
                            f"({overlap}/{len(current_titles)})，分页可能无效。"
                            f"页面可能没有正确翻页。"
                        )
                        # 调用钩子方法
                        self._on_pagination_suspected(page, overlap_ratio)

                prev_titles = current_titles

                all_news.extend(news_items)
                logger.info(f"第 {page} 页爬取到 {len(news_items)} 条新闻")

                # 如果不是最后一页，尝试点击下一页按钮
                if page < max_pages:
                    if not self._click_next_page(driver, page + 1):
                        logger.warning(f"无法切换到第 {page + 1} 页，停止分页")
                        break

                    # 等待新页面加载
                    logger.info("等待新页面加载...")
                    time.sleep(3)  # 增加等待时间，确保页面加载
                    self._wait_for_news_elements(driver)

                    # 额外的等待，确保页面稳定
                    time.sleep(1)

            logger.info(f"Selenium分页爬取完成，总共爬取到 {len(all_news)} 条新闻")

        except Exception as e:
            logger.error(f"Selenium分页爬取失败: {str(e)}")
            import traceback
            traceback.print_exc()
            # 发生异常时，返回已收集的新闻（如果有）
        finally:
            if driver:
                driver.quit()

        return all_news

    def _create_selenium_driver(self):
        """创建Selenium WebDriver实例"""
        if not SELENIUM_AVAILABLE:
            raise RuntimeError("Selenium不可用")

        # 动态导入Selenium模块
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options as ChromeOptions
            from selenium.webdriver.chrome.service import Service as ChromeService
            from webdriver_manager.chrome import ChromeDriverManager
        except ImportError as e:
            logger.warning(f"Selenium模块导入失败: {str(e)}")
            return None

        # 创建Chrome选项
        chrome_options = ChromeOptions()
        chrome_options.add_argument('--headless')  # 无头模式
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')

        # 使用webdriver_manager自动管理ChromeDriver
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        return driver

    def _wait_for_news_elements(self, driver, timeout: int = 10):
        """等待新闻元素加载完成"""
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.common.exceptions import TimeoutException

            wait = WebDriverWait(driver, timeout)
            # 等待至少一个新闻元素出现
            wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, '.news-item, .article-item, .search-result-item, a[href*=".html"], a[href*=".shtml"]')
                )
            )
        except TimeoutException:
            logger.warning("等待新闻元素超时，继续使用当前页面内容")
        except Exception as e:
            logger.debug(f"等待新闻元素时出错: {str(e)}")

    def _click_next_page(self, driver, target_page: int) -> bool:
        """
        点击分页按钮切换到目标页面
        返回True表示成功，False表示失败
        """
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.common.action_chains import ActionChains

            # 方法1：尝试通过data-pi属性查找分页按钮
            logger.info(f"尝试查找第 {target_page} 页的分页按钮")

            # 查找所有分页按钮
            pagination_selectors = [
                # 通过data-pi属性查找 (CSS选择器)
                f'a[data-pi="{target_page}"]',
                # 通过文本内容查找 (XPath)
                f'//a[text()="{target_page}"]',
                f'//a[contains(text(), "{target_page}")]',
                # 用户提供的XPath模式（动态生成）
                f'/html/body/div[1]/div[3]/div[1]/div[4]/div/a[{target_page + 1}]',  # 假设第一个按钮可能是"上一页"
                # 通用的分页按钮选择器
                '.pagination a',
                '.page a',
                '.page-item a',
                '.pager a',
                '.page-nav a',
                # 更通用的选择器
                'a[href="#"]',  # 可能是分页按钮（href="#"）
            ]

            for selector in pagination_selectors:
                logger.info(f"尝试分页选择器: {selector}")
                try:
                    if selector.startswith('//') or selector.startswith('/'):  # XPath
                        elements = driver.find_elements(By.XPATH, selector)
                    else:  # CSS选择器
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    logger.info(f"选择器 '{selector}' 找到 {len(elements)} 个元素")

                    if elements:
                        # 尝试所有找到的元素
                        for element in elements:
                            try:
                                # 确保元素可见且可点击
                                if element.is_displayed() and element.is_enabled():
                                    # 获取元素文本，确认是页码按钮
                                    text = element.text.strip()
                                    element_class = element.get_attribute('class') or ''
                                    data_pi = element.get_attribute('data-pi') or ''

                                    # 检查是否看起来像页码按钮
                                    is_page_button = (
                                        text == str(target_page) or
                                        data_pi == str(target_page) or
                                        'page' in element_class.lower() or
                                        'pager' in element_class.lower() or
                                        'pagination' in element_class.lower()
                                    )

                                    if is_page_button:
                                        logger.info(f"找到分页按钮: {selector} (文本: '{text}', data-pi: '{data_pi}', class: '{element_class}')")

                                        # 滚动到元素
                                        driver.execute_script("arguments[0].scrollIntoView(true);", element)
                                        time.sleep(0.5)

                                        # 使用ActionChains进行更稳定的点击
                                        actions = ActionChains(driver)
                                        actions.move_to_element(element).click().perform()

                                        logger.info(f"成功点击第 {target_page} 页按钮")
                                        return True
                            except Exception as e:
                                logger.debug(f"尝试点击元素时出错: {str(e)}")
                                continue
                except Exception as e:
                    logger.debug(f"尝试选择器 '{selector}' 时出错: {str(e)}")
                    continue

            logger.warning(f"未找到第 {target_page} 页的分页按钮")

            # 作为最后手段，尝试点击"下一页"按钮
            return self._click_next_button(driver)

        except Exception as e:
            logger.error(f"点击分页按钮时出错: {str(e)}")
            return False

    def _click_next_button(self, driver) -> bool:
        """尝试点击"下一页"按钮"""
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.common.action_chains import ActionChains

            next_button_selectors = [
                # XPath按文本查找
                '//a[contains(text(), "下一页")]',
                '//a[@title="下一页"]',  # 通过title属性查找
                '//a[contains(text(), "next") or contains(text(), "Next")]',
                '//button[contains(text(), "下一页")]',
                # 用户提供的特定XPath（下一页按钮固定位置）
                '/html/body/div[1]/div[3]/div[1]/div[4]/div/a[7]',
                # CSS选择器
                '.next-page',
                '.next',
                '.pagination-next',
                '[class*="next"]',
            ]

            for selector in next_button_selectors:
                logger.info(f"尝试下一页按钮选择器: {selector}")
                try:
                    if selector.startswith('//'):  # XPath
                        elements = driver.find_elements(By.XPATH, selector)
                    else:  # CSS选择器
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    logger.info(f"选择器 '{selector}' 找到 {len(elements)} 个元素")

                    if elements:
                        element = elements[0]
                        if element.is_displayed() and element.is_enabled():
                            # 记录元素详细信息以便调试
                            element_html = element.get_attribute('outerHTML')
                            element_text = element.text
                            element_title = element.get_attribute('title')
                            element_data_pi = element.get_attribute('data-pi')
                            element_class = element.get_attribute('class')
                            logger.info(f"找到下一页按钮: {selector}")
                            logger.info(f"按钮详细信息: text='{element_text}', title='{element_title}', data-pi='{element_data_pi}', class='{element_class}'")
                            logger.info(f"按钮HTML: {element_html[:200]}...")

                            # 滚动到元素
                            driver.execute_script("arguments[0].scrollIntoView(true);", element)
                            time.sleep(0.5)

                            # 使用ActionChains进行更稳定的点击
                            actions = ActionChains(driver)
                            actions.move_to_element(element).click().perform()

                            logger.info("成功点击下一页按钮")
                            return True
                except Exception as e:
                    logger.debug(f"尝试选择器 '{selector}' 时出错: {str(e)}")
                    continue

            logger.warning("未找到下一页按钮")
            return False

        except Exception as e:
            logger.error(f"点击下一页按钮时出错: {str(e)}")
            return False

    def parse_news_list(self, html: str) -> List[Dict]:
        """
        解析东方财富股票新闻列表页
        示例URL: http://finance.eastmoney.com/a/cgsgd.html
        """
        soup = BeautifulSoup(html, 'lxml')
        news_items = []

        # 判断是否为搜索结果页面
        is_search_page = 'so.eastmoney.com' in html or '搜索结果' in html or 'keyword=' in html

        # 新增：如果看起来是动态加载的页面，尝试直接提取所有链接然后过滤
        is_likely_dynamic = '<div id="app"></div>' in html and is_search_page

        if is_search_page:
            # 首先尝试动态页面提取策略
            if is_likely_dynamic:
                logger.info("检测到动态加载页面，使用直接链接提取策略")
                dynamic_news = self._extract_news_from_dynamic_page(html, soup)
                if dynamic_news:
                    logger.info(f"动态页面提取策略找到 {len(dynamic_news)} 条新闻")
                    return dynamic_news
                else:
                    logger.info("动态页面提取策略未找到新闻，回退到选择器策略")

            # 东方财富搜索结果页面选择器
            logger.info("检测到搜索结果页面，使用搜索选择器")
            selectors = [
                # 先尝试更具体的搜索结果选择器
                'div.news-item a',
                'div.article-item a',
                '.newslist_item a',
                '.search-result-item a',
                '.search-item a',
                '.result-item a',
                # 通用新闻链接选择器
                'a[href*="/news/"]',
                'a[href*="/a/"]',
                'a[href*="article"]',
                'a[href*=".html"]',
                'a[href*=".shtml"]',
                # 标题类选择器
                'h3.title a',
                'h3 a',
                'h4.title a',
                'h4 a',
                '.title a',
                '.tit a',
                '.text-ellipsis a',
                # 更通用的选择器
                'div[class*="news"] a',
                'div[class*="article"] a',
                'li[class*="news"] a',
                'li[class*="article"] a',
                'div[class*="item"] a',
                'div[class*="list"] a',
                'li[class*="item"] a',
                'div a[href*=".html"]',
                'div a[href*=".shtml"]',
                # 最后尝试：所有链接，但严格过滤
                'a',
            ]
        else:
            # 普通新闻列表页选择器
            selectors = [
                '.newslist li a',  # 常见选择器
                '.article-item a',
                '.text .title a',
                '.news-title a',   # 新闻标题
                '.title a',        # 标题
                'li a[href*=".html"]',  # 链接到html页面的列表项
                'a[href*="/a/"]',
                'a[href*="news"]',  # 包含news的链接
            ]

        # 对于搜索结果页面，尝试所有选择器并去重
        # 对于普通页面，保持原有逻辑（找到第一个可用的选择器就停止）
        seen_urls = set()  # 用于去重的URL集合

        for selector in selectors:
            links = soup.select(selector)
            if links:
                logger.info(f"使用选择器 '{selector}' 找到 {len(links)} 个链接")
                selector_news_count = 0

                for link in links:
                    try:
                        title = link.get_text(strip=True)
                        url = link.get('href', '')

                        # 确保URL是完整URL
                        if url and not url.startswith('http'):
                            url = f"http://finance.eastmoney.com{url}" if url.startswith('/') else f"http://finance.eastmoney.com/{url}"

                        # 去重：如果URL已处理过，跳过
                        if url in seen_urls:
                            continue

                        # 在搜索页面模式下，过滤非新闻链接
                        if is_search_page:
                            # 检查URL是否可能是新闻链接 - 放宽条件
                            # 东方财富搜索结果可能使用多种URL格式
                            url_lower = url.lower()
                            is_news_url = (
                                'news' in url_lower or
                                'article' in url_lower or
                                '/a/' in url_lower or
                                '.html' in url_lower or
                                '.shtml' in url_lower or
                                'detail' in url_lower or
                                'content' in url_lower or
                                '/n/' in url_lower or  # 可能的形式
                                'news.' in url_lower or
                                'article.' in url_lower
                            )

                            # 检查标题有效性
                            is_valid_title = len(title) >= 8 and not title.startswith('http')

                            # 排除常见导航文本
                            common_nav_texts = ['首页', '股票', '基金', '财经', '行情', '数据', '交易', '登录', '注册', '更多', '查看更多']
                            is_nav_text = any(nav_text in title for nav_text in common_nav_texts)

                            # 新闻链接通常有较长的标题，且不是导航文本
                            # 放宽条件：如果标题足够长且不是导航文本，即使URL不符合新闻模式也接受
                            title_is_long_enough = len(title) >= 15
                            looks_like_news_title = title_is_long_enough and not is_nav_text

                            # 最终判断：接受新闻URL或看起来像新闻的标题
                            if not (is_news_url or looks_like_news_title) or not is_valid_title:
                                # 调试日志：记录为什么链接被过滤（只在前几个链接记录）
                                if len(news_items) < 5:  # 如果还没有收集到足够新闻
                                    reason = []
                                    if not is_news_url and not looks_like_news_title:
                                        reason.append(f"URL不匹配且标题不像新闻: {url[:60]}")
                                    if not is_valid_title:
                                        reason.append(f"标题无效: '{title[:40]}' (长度: {len(title)})")
                                    if is_nav_text:
                                        reason.append(f"导航文本: '{title[:30]}'")
                                    if reason:
                                        logger.info(f"过滤链接: {'; '.join(reason)}")
                                continue

                        # 提取时间
                        time_element = link.find_parent().find(class_='time') or link.find_next_sibling(class_='time')
                        date_str = time_element.get_text(strip=True) if time_element else datetime.now().strftime('%Y-%m-%d')

                        # 记录成功提取的新闻
                        logger.info(f"Extracted news: '{title[:100]}' | URL: {url[:80]}")

                        news_items.append({
                            'title': title,
                            'url': url,
                            'date': date_str,
                            'source': '东方财富'
                        })

                        seen_urls.add(url)
                        selector_news_count += 1

                    except Exception as e:
                        logger.debug(f"解析链接时出错: {str(e)}")
                        continue

                logger.info(f"选择器 '{selector}' 成功提取 {selector_news_count} 条新闻")

                # 如果不是搜索结果页面，找到新闻后可以提前退出
                if not is_search_page and news_items:
                    logger.info(f"普通页面模式，找到新闻后停止尝试其他选择器")
                    break

        logger.info(f"总共提取到 {len(news_items)} 条新闻")
        return news_items

    def fetch_page(self, url: str) -> Optional[str]:
        """
        重写fetch_page方法，对东方财富搜索页面使用Selenium
        """
        # 检查是否为需要Selenium的搜索页面
        is_search_page = 'so.eastmoney.com' in url or 'keyword=' in url

        if is_search_page and SELENIUM_AVAILABLE:
            logger.info(f"检测到搜索页面，使用Selenium获取动态内容: {url}")
            try:
                return self._fetch_with_selenium(url)
            except Exception as e:
                logger.warning(f"Selenium获取失败，回退到普通请求: {str(e)}")
                # 回退到父类方法
                return super().fetch_page(url)
        else:
            # 使用父类方法（普通requests）
            return super().fetch_page(url)

    def _fetch_with_selenium(self, url: str) -> Optional[str]:
        """
        使用Selenium获取页面内容（支持JavaScript动态加载）
        """
        if not SELENIUM_AVAILABLE:
            logger.warning("Selenium不可用，无法获取动态页面")
            return None

        # 动态导入Selenium模块（避免全局导入失败）
        try:
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.common.exceptions import TimeoutException, WebDriverException
            from selenium.webdriver.chrome.options import Options as ChromeOptions
            from selenium.webdriver.chrome.service import Service as ChromeService
            from webdriver_manager.chrome import ChromeDriverManager
        except ImportError as e:
            logger.warning(f"Selenium模块导入失败: {str(e)}")
            return None

        driver = None
        try:
            # 创建Chrome选项
            chrome_options = ChromeOptions()
            chrome_options.add_argument('--headless')  # 无头模式
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')

            # 使用webdriver_manager自动管理ChromeDriver
            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)

            logger.info(f"Selenium正在加载页面: {url}")
            driver.get(url)

            # 等待页面加载完成
            # 等待至少一个新闻元素出现
            try:
                wait = WebDriverWait(driver, 10)
                # 尝试等待常见新闻元素
                wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, '.news-item, .article-item, .search-result-item, a[href*=".html"], a[href*=".shtml"]')
                    )
                )
            except TimeoutException:
                logger.warning("等待新闻元素超时，继续使用当前页面内容")

            # 获取页面源代码
            html = driver.page_source
            logger.info(f"Selenium获取页面成功，长度: {len(html)} 字符")

            # 检查是否包含动态内容
            if '<div id="app"></div>' in html and '新闻' not in html:
                logger.warning("页面可能仍是动态加载状态，新闻内容未完全渲染")

            return html

        except Exception as e:
            logger.error(f"Selenium获取页面失败: {str(e)}")
            return None
        finally:
            if driver:
                driver.quit()

    def _try_extract_with_selenium(self, soup: BeautifulSoup) -> Optional[List[Dict]]:
        """
        尝试使用Selenium获取动态加载内容
        注意：此方法需要URL来重新获取页面，但当前只有soup，因此无法使用Selenium
        返回None表示失败，让其他方法继续尝试
        """
        # 由于没有URL，无法使用Selenium重新获取页面
        # 可以尝试从soup中提取，但soup已经来自不完整的HTML
        # 因此直接返回None，让其他方法处理
        logger.debug("_try_extract_with_selenium: 无URL可用，跳过Selenium提取")
        return None

    def _extract_news_from_dynamic_page(self, html: str, soup: BeautifulSoup) -> List[Dict]:
        """
        从动态加载的页面提取新闻
        针对东方财富搜索结果页面（包含<div id="app"></div>的页面）
        """
        news_items = []
        seen_urls = set()

        # 方法0：首先尝试使用Selenium获取动态加载内容
        selenium_result = self._try_extract_with_selenium(soup)
        if selenium_result:
            logger.info(f"Selenium成功提取 {len(selenium_result)} 条新闻")
            return selenium_result

        # 方法1：尝试使用XPath提取新闻链接
        logger.info("尝试使用XPath提取新闻链接")
        try:
            # 使用lxml解析HTML
            tree = etree.HTML(html)

            # 尝试多种XPath模式来查找新闻链接
            xpath_patterns = [
                # 用户提供的模式：/html/body/div[1]/div[3]/div[1]/div[3]/div[5]/div[1]/a
                # 通用化：查找深层div结构中的a标签
                "//div[count(div) > 3]//a[@href]",
                "//div[contains(@class, 'item') or contains(@class, 'news') or contains(@class, 'article')]//a[@href]",
                "//a[contains(@href, '.html') or contains(@href, '.shtml')]",
                "//a[contains(@href, '/a/') or contains(@href, '/news/')]",
                # 更通用的模式：查找所有a标签，然后过滤
                "//a[@href]",
            ]

            for xpath in xpath_patterns:
                try:
                    elements = tree.xpath(xpath)
                    if not elements:
                        continue

                    logger.info(f"XPath '{xpath}' 找到 {len(elements)} 个元素")

                    for elem in elements:
                        try:
                            title = elem.text
                            url = elem.get('href', '')

                            if not title or not url:
                                # 尝试获取子元素文本
                                title = ''.join(elem.itertext()).strip()

                            if not title or len(title) < 8:
                                continue

                            # 确保URL是完整URL
                            if url and not url.startswith('http'):
                                if url.startswith('/'):
                                    url = f"http://finance.eastmoney.com{url}"
                                else:
                                    url = f"http://finance.eastmoney.com/{url}"

                            # 检查是否是新闻URL
                            url_lower = url.lower()
                            is_news_url = (
                                '/a/' in url_lower or
                                '/news/' in url_lower or
                                'article' in url_lower or
                                '.html' in url_lower or
                                '.shtml' in url_lower
                            )

                            if not is_news_url:
                                continue

                            # 去重
                            if url in seen_urls:
                                continue

                            # 排除导航文本
                            common_nav_texts = ['首页', '股票', '基金', '财经', '行情', '数据', '交易', '登录', '注册', '更多', '查看更多']
                            if any(nav_text in title for nav_text in common_nav_texts):
                                continue

                            # 提取日期
                            date_match = re.search(r'/(\d{8})/', url)
                            if date_match:
                                date_str = f"{date_match.group(1)[:4]}-{date_match.group(1)[4:6]}-{date_match.group(1)[6:8]}"
                            else:
                                date_str = datetime.now().strftime('%Y-%m-%d')

                            news_items.append({
                                'title': title,
                                'url': url,
                                'date': date_str,
                                'source': '东方财富'
                            })

                            seen_urls.add(url)
                            logger.debug(f"XPath提取: '{title[:60]}...' | URL: {url[:80]}")

                        except Exception as e:
                            logger.debug(f"处理XPath元素时出错: {str(e)}")
                            continue

                    if news_items:
                        logger.info(f"XPath策略成功提取 {len(news_items)} 条新闻")
                        return news_items

                except Exception as e:
                    logger.debug(f"执行XPath '{xpath}' 时出错: {str(e)}")
                    continue

        except Exception as e:
            logger.warning(f"XPath提取失败，尝试其他方法: {str(e)}")

        # 如果XPath失败，回退到原有方法

        # 方法2：查找所有包含特定URL模式的链接
        # 东方财富新闻URL常见模式：/a/数字.html, /news/..., article数字.html等
        url_patterns = [
            r'https?://finance\.eastmoney\.com/a/\d+\.html',
            r'https?://finance\.eastmoney\.com/news/\d+,\d+\.html',
            r'https?://\w+\.eastmoney\.com/\w+/\d+\.html',
            r'https?://\w+\.eastmoney\.com/\w+/\d+\.shtml',
            r'/a/\d+\.html',
            r'/news/\d+,\d+\.html',
        ]

        # 首先尝试：使用正则表达式直接从HTML中提取链接和标题
        # 匹配 <a href="URL" target="_blank">标题</a> 格式
        link_pattern = r'<a\s+href="([^"]+)"[^>]*target="_blank"[^>]*>([^<]+)</a>'
        matches = re.findall(link_pattern, html, re.IGNORECASE)

        logger.info(f"正则表达式找到 {len(matches)} 个 target='_blank' 链接")

        for url, title in matches:
            try:
                title = title.strip()
                if not title or len(title) < 8:
                    continue

                # 确保URL是完整URL
                if url and not url.startswith('http'):
                    if url.startswith('/'):
                        url = f"http://finance.eastmoney.com{url}"
                    else:
                        url = f"http://finance.eastmoney.com/{url}"

                # 检查URL是否匹配新闻模式
                is_news_url = any(re.search(pattern, url) for pattern in url_patterns)

                # 或者URL包含常见新闻关键词
                url_lower = url.lower()
                is_news_url = is_news_url or any(keyword in url_lower for keyword in ['/a/', '/news/', 'article', '.html', '.shtml'])

                if not is_news_url:
                    continue

                # 去重
                if url in seen_urls:
                    continue

                # 排除导航链接
                common_nav_texts = ['首页', '股票', '基金', '财经', '行情', '数据', '交易', '登录', '注册', '更多', '查看更多']
                if any(nav_text in title for nav_text in common_nav_texts):
                    continue

                # 尝试提取日期 - 从URL中提取或使用默认值
                date_match = re.search(r'/(\d{8})/', url)
                if date_match:
                    date_str = f"{date_match.group(1)[:4]}-{date_match.group(1)[4:6]}-{date_match.group(1)[6:8]}"
                else:
                    date_str = datetime.now().strftime('%Y-%m-%d')

                news_items.append({
                    'title': title,
                    'url': url,
                    'date': date_str,
                    'source': '东方财富'
                })

                seen_urls.add(url)
                logger.debug(f"动态提取: '{title[:60]}...' | URL: {url[:80]}")

            except Exception as e:
                logger.debug(f"解析动态链接时出错: {str(e)}")
                continue

        # 方法2：如果没有找到新闻，尝试更宽松的提取 - 所有a标签
        if not news_items:
            logger.info("尝试方法2: 提取所有a标签并过滤")
            all_links = soup.find_all('a', href=True)
            logger.info(f"找到 {len(all_links)} 个链接")

            for link in all_links:
                try:
                    title = link.get_text(strip=True)
                    url = link.get('href', '')

                    if not title or len(title) < 8:
                        continue

                    # 确保URL是完整URL
                    if url and not url.startswith('http'):
                        if url.startswith('/'):
                            url = f"http://finance.eastmoney.com{url}"
                        else:
                            url = f"http://finance.eastmoney.com/{url}"

                    # 检查URL是否可能是新闻
                    url_lower = url.lower()
                    is_news_url = (
                        '/a/' in url_lower or
                        '/news/' in url_lower or
                        'article' in url_lower or
                        '.html' in url_lower or
                        '.shtml' in url_lower
                    )

                    if not is_news_url:
                        continue

                    # 去重
                    if url in seen_urls:
                        continue

                    # 排除导航文本
                    common_nav_texts = ['首页', '股票', '基金', '财经', '行情', '数据', '交易', '登录', '注册', '更多', '查看更多']
                    if any(nav_text in title for nav_text in common_nav_texts):
                        continue

                    # 提取日期
                    date_match = re.search(r'/(\d{8})/', url)
                    if date_match:
                        date_str = f"{date_match.group(1)[:4]}-{date_match.group(1)[4:6]}-{date_match.group(1)[6:8]}"
                    else:
                        date_str = datetime.now().strftime('%Y-%m-%d')

                    news_items.append({
                        'title': title,
                        'url': url,
                        'date': date_str,
                        'source': '东方财富'
                    })

                    seen_urls.add(url)

                except Exception as e:
                    logger.debug(f"解析a标签时出错: {str(e)}")
                    continue

        logger.info(f"动态页面提取总共找到 {len(news_items)} 条新闻")
        return news_items

    def _get_page_url(self, base_url: str, page: int) -> str:
        """东方财富分页规则"""
        # 检查是否为搜索URL
        if 'so.eastmoney.com' in base_url or 'keyword=' in base_url:
            # 搜索URL分页：使用当前分页参数名
            param = self._pagination_params[self._current_pagination_index]
            # 检查URL中是否已包含当前参数
            import re
            pattern = f'{param}=\\d+'
            if re.search(pattern, base_url):
                # 替换现有的参数
                return re.sub(pattern, f'{param}={page}', base_url)
            else:
                # 添加参数
                if '?' in base_url:
                    return f"{base_url}&{param}={page}"
                else:
                    return f"{base_url}?{param}={page}"

        if page == 1:
            return base_url

        # 东方财富常见分页格式: _2.html, _2.shtml, /index_2.html
        if base_url.endswith('.html'):
            base = base_url.replace('.html', '')
            return f"{base}_{page}.html"
        elif base_url.endswith('.shtml'):
            base = base_url.replace('.shtml', '')
            return f"{base}_{page}.shtml"
        elif '/a/' in base_url:
            # 形如 http://finance.eastmoney.com/a/cgsgd.html
            if '?' in base_url:
                return f"{base_url}&page={page}"
            else:
                return f"{base_url}?page={page}"
        else:
            # 默认添加 ?page= 参数
            if '?' in base_url:
                return f"{base_url}&page={page}"
            else:
                return f"{base_url}?page={page}"


def create_scraper(source: str) -> NewsScraper:
    """创建指定来源的爬虫实例"""
    scrapers = {
        'sina': SinaFinanceScraper,
        'eastmoney': EastMoneyScraper,
    }

    scraper_class = scrapers.get(source.lower())
    if not scraper_class:
        raise ValueError(f"不支持的新闻来源: {source}，支持: {list(scrapers.keys())}")

    return scraper_class()


def main():
    """主函数：解析命令行参数并运行爬虫"""
    parser = argparse.ArgumentParser(description='股票新闻爬虫')
    parser.add_argument('--source', '-s', default='sina',
                       choices=['sina', 'eastmoney'],
                       help='新闻来源（默认：sina）')
    parser.add_argument('--url', '-u',
                       default=None,
                       help='新闻列表页URL（默认根据来源自动选择）')
    parser.add_argument('--keyword', '-k',
                       default=None,
                       help='搜索关键词，如"茅台"。如果提供，将搜索相关新闻而不是爬取固定列表')
    parser.add_argument('--days', '-d', type=int, default=15,
                       help='搜索最近多少天的新闻（默认：7天）')
    parser.add_argument('--output', '-o',
                       default='stock_news.csv',
                       help='输出CSV文件路径（默认：stock_news.csv）')
    parser.add_argument('--pages', '-p', type=int, default=6,
                       help='爬取页数（默认：3）')
    parser.add_argument('--update-existing', action='store_true',
                       help='如果输出文件已存在，则追加新数据（默认覆盖）')

    args = parser.parse_args()

    # 设置默认URL（如果未提供）
    if args.url is None:
        if args.keyword:
            # 对关键词进行URL编码
            encoded_keyword = quote(args.keyword)
            # 根据关键词生成搜索URL
            if args.source == 'sina':
                # 新浪财经搜索URL不可用，使用默认股票新闻URL，后续本地过滤关键词
                logger.info(f"新浪财经搜索功能暂不可用，将爬取股票新闻并本地过滤关键词'{args.keyword}'")
                # 使用新浪财经股票页面，这是已知可访问的页面
                args.url = 'https://finance.sina.com.cn/stock/'
            elif args.source == 'eastmoney':
                # 东方财富搜索URL（需要Selenium处理动态加载）
                args.url = f'https://so.eastmoney.com/news/s?keyword={encoded_keyword}'
                logger.info(f"东方财富搜索URL: {args.url} (将使用Selenium处理动态加载)")
            else:
                args.url = 'https://finance.sina.com.cn/stock/'
        else:
            # 没有关键词，使用默认新闻列表URL
            if args.source == 'sina':
                # 使用新浪财经股票页面
                args.url = 'https://finance.sina.com.cn/stock/'
            elif args.source == 'eastmoney':
                args.url = 'http://finance.eastmoney.com/a/cgnjj.html'  # 国内经济新闻
            else:
                args.url = 'https://finance.sina.com.cn/stock/'

    try:
        # 创建爬虫实例
        scraper = create_scraper(args.source)

        # 爬取新闻
        news_items = scraper.scrape(args.url, max_pages=args.pages)

        # 按日期过滤新闻
        if args.days > 0:
            cutoff_date = datetime.now() - timedelta(days=args.days)
            filtered_items = []
            for item in news_items:
                date_str = item.get('date', '')
                if not date_str:
                    # 没有日期信息，保留
                    filtered_items.append(item)
                    continue
                item_date = parse_date_string(date_str)
                if item_date and item_date >= cutoff_date:
                    filtered_items.append(item)

            logger.info(f"日期过滤: 从 {len(news_items)} 条新闻中保留最近 {args.days} 天的 {len(filtered_items)} 条新闻")
            news_items = filtered_items

        # 按关键词过滤新闻
        if args.keyword:
            news_items = scraper.filter_news_by_keyword(news_items, args.keyword)

        if not news_items:
            logger.error("未爬取到任何新闻，请检查URL或选择器")
            return 1

        # 处理输出文件
        output_file = args.output

        if args.update_existing and os.path.exists(output_file):
            # 读取现有数据
            try:
                existing_df = pd.read_csv(output_file, encoding='utf-8-sig')
                existing_items = existing_df.to_dict('records')

                # 合并数据（基于标题去重）
                existing_titles = {item.get('title', '') for item in existing_items}
                new_items = [item for item in news_items if item.get('title', '') not in existing_titles]

                if new_items:
                    all_items = existing_items + new_items
                    logger.info(f"在现有 {len(existing_items)} 条记录基础上添加 {len(new_items)} 条新记录")
                else:
                    all_items = existing_items
                    logger.info("没有新记录可添加")

                news_items = all_items

            except Exception as e:
                logger.warning(f"读取现有文件失败，将覆盖文件: {str(e)}")

        # 保存到CSV
        scraper.save_to_csv(news_items, output_file)

        logger.info(f"爬虫任务完成，数据已保存到: {output_file}")
        return 0

    except Exception as e:
        logger.error(f"爬虫运行失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


def install_dependencies():
    """安装必要依赖"""
    global SELENIUM_AVAILABLE

    required_packages = [
        'requests',
        'beautifulsoup4',
        'pandas',
        'lxml',
        'selenium',
        'webdriver-manager'
    ]

    # 检查已安装的包
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        logger.info(f"正在安装缺失依赖: {', '.join(missing_packages)}")
        install_cmd = f"{sys.executable} -m pip install {' '.join(missing_packages)}"
        logger.info(f"执行命令: {install_cmd}")
        os.system(install_cmd)
        logger.info("依赖安装完成")

        # 重新检查Selenium是否可用
        try:
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.common.exceptions import TimeoutException, WebDriverException
            from selenium.webdriver.chrome.options import Options as ChromeOptions
            from selenium.webdriver.chrome.service import Service as ChromeService
            from webdriver_manager.chrome import ChromeDriverManager
            SELENIUM_AVAILABLE = True
            logger.info("Selenium已成功安装并可用")
        except ImportError:
            SELENIUM_AVAILABLE = False
            logger.warning("Selenium安装后仍不可用")

if __name__ == "__main__":
    # 安装必要依赖（首次运行自动安装）
    install_dependencies()

    # 重新导入必要的模块
    import requests
    from bs4 import BeautifulSoup
    import pandas as pd

    sys.exit(main())