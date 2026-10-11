import requests
import time
import csv  # 导入csv模块用于操作表格文件
from bs4 import BeautifulSoup


# 移除原有的MySQL相关导入：from con_mysql import *


class StockCommentScraper:
    def __init__(self, stock_code, start_page=925, end_page=14000, save_file="stock_comments.csv"):
        self.start_page = start_page
        self.stock_code = stock_code  # 股票代码
        self.end_page = end_page
        self.base_url = f'https://gubaf10.eastmoney.com/list,{stock_code}_{{}}.html'
        # self.base_url = 'https://gubaf10.eastmoney.com/list,zssh000001_{}.html'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.save_file = save_file  # 本地表格文件路径（CSV格式）
        # 初始化时创建CSV文件并写入表头（若文件已存在会覆盖，避免重复表头）
        self._init_csv()

    def _init_csv(self):
        """初始化CSV文件，写入表头"""
        try:
            with open(self.save_file, 'w', encoding='utf-8-sig', newline='') as f:
                # 表头与解析的数据字段对应
                fieldnames = ['read_nums', 'comment_nums', 'title', 'author', 'time']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()  # 写入表头
            print(f"已初始化本地表格文件：{self.save_file}")
        except Exception as e:
            print(f"初始化CSV文件失败: {e}")

    def get_html(self, page_num):
        """获取网页内容（逻辑不变）"""
        try:
            url = self.base_url.format(page_num)
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()  # 若状态码非200，抛出异常
            response.encoding = response.apparent_encoding  # 自动识别编码
            return response.text
        except requests.exceptions.RequestException as e:
            print(f"第{page_num}页请求失败: {e}")
            return None

    def parse_page(self, html):
        """解析页面数据（逻辑不变）"""
        if not html:
            return []

        parsed_data = []
        try:
            soup = BeautifulSoup(html, 'html.parser')
            post_list = soup.find_all('div', class_="articleh normal_post")

            for post in post_list:
                try:
                    data = {
                        'read_nums': int(post.find('span', class_='l1 a1').get_text(strip=True)),  # 阅读数
                        'comment_nums': int(post.find('span', class_='l2 a2').get_text(strip=True)),  # 评论数
                        'title': post.find('span', class_='l3 a3').get_text(strip=True),  # 标题
                        'author': post.find('span', class_='l4 a4').get_text(strip=True),  # 作者
                        'time': post.find('span', class_='l5 a5').get_text(strip=True)  # 更新时间
                    }
                    parsed_data.append(data)
                    # 可选：注释掉单条数据打印，避免控制台冗余
                    # print(f"解析数据: {data}")
                except Exception as e:
                    print(f"单条数据解析失败: {e}")
                    continue
            return parsed_data
        except Exception as e:
            print(f"页面解析失败: {e}")
            return []

    def save_data(self, data_list):
        """修改：保存数据到本地CSV文件（替代原数据库保存）"""
        if not data_list:
            print("没有数据需要保存")
            return

        try:
            # 以追加模式（a）写入数据，避免覆盖已有内容
            with open(self.save_file, 'a', encoding='utf-8-sig', newline='') as f:
                fieldnames = ['read_nums', 'comment_nums', 'title', 'author', 'time']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                # 批量写入当前页数据（比逐条写入更高效）
                writer.writerows(data_list)
            print(f"成功保存 {len(data_list)} 条数据到 {self.save_file}")
        except Exception as e:
            print(f"数据保存到CSV失败: {e}")

    def run(self):
        """执行完整爬取流程（调整请求频率，修复原打印错误）"""
        # 修复原打印错误：将"GDP数据爬取"改为"股票评论数据爬取"
        print("开始执行股票评论数据爬取...")
        print(f"开始爬取第{self.start_page}页到第{self.end_page}页...")

        for page in range(self.start_page, self.end_page + 1):
            html = self.get_html(page)
            page_data = self.parse_page(html)

            # 每爬取一页就保存一页数据（避免一次性存储大量数据占用内存）
            if page_data:
                self.save_data(page_data)

            # 关键修改：延长休眠时间（原0.002秒过短，极易被反爬封禁）
            sleep_time = 1.5  # 固定1.5秒，也可改为随机：random.uniform(1, 3)
            time.sleep(sleep_time)
            print(f"已完成第{page}页爬取（休眠{sleep_time}秒）")

        print(f"爬取任务完成！所有数据已保存至本地表格：{self.save_file}")


def scrape_stock_comments(stock_code, start_page=5, end_page=10, save_file="stock_comments.csv"):
    """
    封装股票评论爬取逻辑，根据股票代码爬取对应股吧评论

    参数:
        stock_code (str): 股票代码（如"600519"）
        start_page (int): 爬取起始页码，默认5
        end_page (int): 爬取结束页码，默认10
        save_file (str): 结果保存路径，默认"stock_comments.csv"
    """
    # 创建爬虫实例并执行爬取
    scraper = StockCommentScraper(
        stock_code=stock_code,
        start_page=start_page,
        end_page=end_page,
        save_file=save_file
    )
    scraper.run()

if __name__ == "__main__":
    # 可修改参数：起始页、结束页、保存文件名
    stock_code = input("请输入要爬取的股票代码：").strip()
    scraper = StockCommentScraper(
        stock_code=stock_code,
        start_page=1,
        end_page=5,  # 测试时先爬5页（925-930），确认正常后再改14000
        save_file="stock_comments.csv"  # 保存到当前目录，也可指定路径如"D:/stock.csv"
    )
    scraper.run()