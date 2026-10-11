# -*- coding: utf-8 -*-
import os
import json
import requests


def call_qianwen_api(user_input):
    """调用阿里云千问API"""
    api_key = os.getenv("DASHSCOPE_API_KEY")
    api_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"

    # 构建请求头
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json; charset=UTF-8",
        "Accept": "application/json"
    }

    # 构建请求体
    request_body = {
        "model": "qwen-turbo",  # 模型名称
        "input": {
            "messages": [
                {
                    "role": "user",
                    "content": user_input  # 用户输入内容
                }
            ]
        },
        "parameters": {
            "result_format": "text"  # 返回纯文本格式
        }
    }

    # print("发送的请求体:")
    # print(json.dumps(request_body, indent=2, ensure_ascii=False))  # 打印格式化的请求体

    try:
        # 发送POST请求
        response = requests.post(
            url=api_url,
            headers=headers,
            data=json.dumps(request_body, ensure_ascii=False).encode("utf-8"),
            timeout=30
        )
        response.raise_for_status()  # 抛出HTTP错误状态码
        result = response.text
        print("API返回原始内容:")
        print(result)

        # 解析响应
        if result.strip().startswith("{"):
            json_resp = json.loads(result)
            # 处理错误响应
            if "code" in json_resp:
                return f"API调用失败 [{json_resp['code']}]: {json_resp.get('message', '未知错误')}"
            # 处理成功响应
            elif "output" in json_resp:
                return json_resp["output"].get("text", "无返回内容")
            else:
                return f"API响应格式异常: {result}"
        else:
            return f"API返回非JSON内容: {result}"

    except requests.exceptions.RequestException as e:
        return f"调用出错: {str(e)}（类型：{type(e).__name__}）"


def main():
    # 检查API_KEY是否存在
    api_key = os.getenv("DASHSCOPE_API_KEY")
    print(f"API_KEY是否存在: {'是' if api_key else '否'}")
    if not api_key or api_key.strip() == "":
        print("错误: 未设置DASHSCOPE_API_KEY环境变量")
        return

    # 获取用户输入
    print("输入问题：")
    user_input = input().strip()  # 读取用户输入

    # 构建提示词
    prompt = """”，你是金融专家，判断用户问题意图是否为：1、风险分析 2、舆情分析 3、股票预测 4、查询数字数据 中的一或多项（有可能不是，一定要判断），若都不是则不输出序号直接仅回答用户问题，若用户意图为查询背景信息就给出其需要的信息；若是则不解释仅输出这个意图的序号(仅序号不用文字)，若有多个序号则用、分隔，同时在【】中输出这个股票的主体，可能有多个主体。输出示例：1、4【贵州茅台】【中天科技】易错点：1、查询往年股价不算在已有意图里，需要你主动查询这段时间中的信息输出而非输出序号 2、若出现关键词：“前年”、“去年”等表示以往时间的关键词的不算股票预测"""

    # 拼接完整输入
    full_input = f"用户问题:“{user_input}{prompt}"

    # 调用API并输出结果
    try:
        response = call_qianwen_api(full_input)
        print("API 响应：")
        print(response)
    except Exception as e:
        print(f"程序异常: {str(e)}")


def front(user_input=None):
    if user_input is None:
        print("输入问题：")
        user_input = input().strip()  # 读取用户输入（对应Java的Scanner）

    # 构建提示词
    prompt = """”，你是金融专家，判断用户问题意图是否为：1、风险分析 2、舆情分析 3、股票预测 4、查询数字数据 中的一或多项（有可能不是，一定要判断），若都不是则不输出序号直接仅回答用户问题，若用户意图为查询背景信息就给出其需要的信息；若是则不解释仅输出这个意图的序号(仅序号不用文字)，若有多个序号则用、分隔，同时在【】中输出这个股票的主体，可能有多个主体。输出示例：1、4【贵州茅台】【中天科技】易错点：1、查询往年股价不算在已有意图里，需要你主动查询这段时间中的信息输出而非输出序号 2、若出现关键词：“前年”、“去年”等表示以往时间的关键词的不算股票预测"""

    # 拼接完整输入
    full_input = f"用户问题:“{user_input}{prompt}"

    # 调用API并输出结果
    try:
        final_response = call_qianwen_api(full_input)
    except Exception as e:
        print(f"程序异常: {str(e)}")
        final_response = ""
    return final_response


if __name__ == "__main__":
    main()