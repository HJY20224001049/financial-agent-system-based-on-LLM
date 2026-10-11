# MCP股票分析集成

基于 [mcp-stock-analysis-server](https://www.scnet.cn/ui/aihub/mcp/renchang1016/stock-mcp) 的Python客户端，用于实时查询股票数据、技术指标和新闻情感分析。

## 文件说明

- `mcp_stock_client.py` - 主客户端类，实现与MCP服务器的通信
- `use_mcp_example.py` - 使用示例和集成演示
- `quick_start_mcp.py` - 快速开始脚本，检查依赖并测试功能

## 快速开始

### 1. 安装依赖

需要先安装Node.js和npm：

1. 下载并安装 [Node.js](https://nodejs.org/)（包含npm）
2. 验证安装：
   ```bash
   node --version
   npx --version
   ```

### 2. 测试MCP服务器

运行快速开始脚本：
```bash
python quick_start_mcp.py
```

脚本会自动检查依赖并测试MCP服务器。

### 3. 简单使用示例

```python
from mcp_stock_client import quick_start

# 获取股票报价
quote = quick_start("AAPL")
if quote:
    print(f"AAPL当前价格: {quote.get('price')}")
```

### 4. 完整使用示例

```python
from mcp_stock_client import MCPStockClient

# 创建客户端（可设置环境变量）
client = MCPStockClient(env={
    "NEWS_API_KEY": "your_news_api_key"  # 可选，用于新闻分析
})

try:
    # 启动服务器
    client.start()

    # 获取实时报价
    quote = client.get_stock_quote("600519.SS")  # 贵州茅台
    print(f"贵州茅台: {quote}")

    # 获取历史数据
    historical = client.get_historical_data("AAPL", "daily")
    print(f"AAPL历史数据: {historical}")

    # 分析趋势（需要NEWS_API_KEY）
    trend = client.analyze_trend("AAPL", period=30)
    print(f"趋势分析: {trend}")

finally:
    # 停止服务器
    client.stop()
```

## 功能列表

### 可用工具（根据MCP服务器文档）

1. **实时报价**
   - `getStockQuote(symbol)` - 获取股票实时报价
   - 返回：价格、涨跌幅、市值等

2. **历史数据**
   - `getHistoricalData(symbol, interval, startDate, endDate)`
   - 间隔：daily, weekly, monthly
   - 返回：OHLCV数据（开盘、最高、最低、收盘、成交量）

3. **技术分析**
   - `getTechnicalIndicators(symbol, indicator)`
   - 指标：RSI, MACD, BOLL, EMA, SAR等
   - 返回：技术指标数值

4. **趋势分析**
   - `analyzeTrend(symbol, period, includeNews)`
   - 结合技术指标和新闻情感分析
   - 返回：趋势预测和置信度

5. **新闻情感分析**（需要NEWS_API_KEY）
   - 分析股票相关新闻的情感倾向
   - 返回：情感分数和置信度

## 配置说明

### Claude Desktop 集成

在Claude Desktop配置文件中添加：

```json
{
  "mcpServers": {
    "mcp-stock-analysis-server": {
      "command": "npx",
      "args": ["-y", "mcp-stock-analysis-server"],
      "env": {
        "NEWS_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

配置后，Claude AI助手可以直接通过MCP协议访问股票数据。

### API密钥

- **News API Key**（可选）：用于新闻情感分析
  - 注册地址：https://newsapi.org/
  - 免费版有限制，但足够个人使用
  - 设置环境变量：`NEWS_API_KEY=your_key`

## 股票代码格式

- **美股**：AAPL, GOOGL, MSFT, TSLA
- **A股（上证）**：600519.SS, 601318.SS
- **A股（深证）**：000001.SZ, 000858.SZ
- **港股**：0700.HK, 0939.HK
- **指数**：^GSPC（标普500）, ^IXIC（纳斯达克）, ^HSI（恒生）

## 与现有项目集成

### 替代现有数据源

现有项目使用东方财富API获取历史数据，可以增强为：

```python
# 原有代码
from add_new_data import get_stock_daily_data

# 增强：添加实时数据
from mcp_stock_client import MCPStockClient

def get_enhanced_stock_data(stock_code):
    """获取增强的股票数据（历史+实时+分析）"""
    # 1. 获取历史数据（原有）
    historical = get_stock_daily_data(stock_code)

    # 2. 获取实时数据（新增）
    client = MCPStockClient()
    client.start()
    try:
        realtime = client.get_stock_quote(f"{stock_code}.SS")
        analysis = client.analyze_trend(f"{stock_code}.SS")
    finally:
        client.stop()

    return {
        "historical": historical,
        "realtime": realtime,
        "analysis": analysis
    }
```

### 增强预测模型

将实时数据和技术指标作为特征输入到预测模型：

```python
def prepare_features_with_mcp(stock_code):
    """准备包含MCP数据的特征"""
    client = MCPStockClient()
    client.start()

    try:
        # 获取技术指标
        indicators = client.get_technical_indicators(f"{stock_code}.SS", "all")

        # 获取新闻情感
        trend = client.analyze_trend(f"{stock_code}.SS", include_news=True)

        # 提取特征
        features = {
            "rsi": indicators.get("rsi", 50),
            "macd": indicators.get("macd", 0),
            "news_sentiment": trend.get("newsSentiment", {}).get("score", 0),
            # ... 其他特征
        }

        return features
    finally:
        client.stop()
```

## 故障排除

### 常见问题

1. **Node.js/npx未安装**
   ```
   Error: Node.js is not installed
   ```
   解决方案：安装 [Node.js](https://nodejs.org/)

2. **MCP服务器启动失败**
   ```
   Failed to start MCP server
   ```
   解决方案：手动测试 `npx mcp-stock-analysis-server --help`

3. **网络连接问题**
   ```
   Timeout waiting for response
   ```
   解决方案：检查网络连接，确保可以访问Yahoo Finance

4. **NEWS_API_KEY缺失**
   ```
   News sentiment analysis unavailable
   ```
   解决方案：注册News API并设置环境变量，或忽略新闻功能

### 手动测试

```bash
# 测试Node.js
node --version

# 测试npx
npx --version

# 测试MCP服务器（可能无响应，按Ctrl+C退出）
npx -y mcp-stock-analysis-server --help

# 设置环境变量（Windows）
set NEWS_API_KEY=your_key_here

# 设置环境变量（Linux/Mac）
export NEWS_API_KEY=your_key_here
```

## 性能注意事项

1. **启动时间**：MCP服务器启动需要2-5秒
2. **请求频率**：避免高频请求，Yahoo Finance API有限制
3. **并发限制**：建议单实例使用，多实例可能导致端口冲突
4. **资源占用**：Node.js进程会占用内存，使用后及时停止

## 扩展开发

### 添加新工具

如果MCP服务器支持新工具，可以在`MCPStockClient`类中添加相应方法：

```python
def get_new_feature(self, symbol, param):
    """调用新的MCP工具"""
    return self._call_tool("newToolName", {
        "symbol": symbol,
        "param": param
    })
```

### 支持其他MCP服务器

修改`server_command`参数可以支持其他MCP服务器：

```python
# Alpha Vantage MCP服务器
client = MCPStockClient(
    server_command=["npx", "@gviper/alphavantage-mcp"],
    env={"ALPHAVANTAGE_API_KEY": "your_key"}
)

# 自定义MCP服务器
client = MCPStockClient(
    server_command=["node", "/path/to/custom-mcp-server.js"]
)
```

## 许可证

本项目代码基于MIT许可证。MCP服务器`mcp-stock-analysis-server`有其自己的许可证（可能是Apache 2.0）。

## 更多资源

- [MCP协议官方文档](https://modelcontextprotocol.io/)
- [Claude Desktop MCP配置](https://docs.anthropic.com/claude/docs/model-context-protocol)
- [Yahoo Finance API](https://finance.yahoo.com/)
- [News API文档](https://newsapi.org/docs)

## 更新日志

- 2026-03-30：初始版本，实现基本MCP客户端功能
- 2026-03-30：添加示例和快速开始脚本
- 2026-03-30：完善文档和故障排除指南