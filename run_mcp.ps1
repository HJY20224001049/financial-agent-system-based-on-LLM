# MCP股票分析快速开始 PowerShell脚本
$env:PYTHONIOENCODING='utf-8'

Write-Host "正在启动 MCP 股票分析快速开始..." -ForegroundColor Green
Write-Host ""

# 检查Python是否可用
try {
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "使用Python版本: $pythonVersion" -ForegroundColor Cyan
        Write-Host ""
    } else {
        Write-Host "警告: Python版本检查失败，尝试继续运行..." -ForegroundColor Yellow
    }
} catch {
    Write-Host "错误: Python未找到" -ForegroundColor Red
    Write-Host "请确保Python已安装并添加到PATH" -ForegroundColor Yellow
    Write-Host "或者使用完整路径: E:\python3.9\python.exe quick_start_mcp.py" -ForegroundColor Yellow
    Read-Host "按Enter退出"
    exit 1
}

# 运行主脚本
Write-Host "开始运行 quick_start_mcp.py..." -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

python quick_start_mcp.py

Write-Host ""
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "完成!" -ForegroundColor Green
if ($host.Name -eq 'ConsoleHost') {
    Read-Host "按Enter退出"
}