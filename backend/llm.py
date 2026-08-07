import os
from dotenv import load_dotenv
import requests

load_dotenv()

API_KEY = os.getenv("DASHSCOPE_API_KEY")
URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"


def call_qwen(prompt, model="qwen-plus", temperature=0.7):
    """通用 Qwen API 调用接口"""
    if not API_KEY:
        print("❌ 错误：未设置 DASHSCOPE_API_KEY，请检查 .env 文件")
        return None

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,
        "input": {"prompt": prompt},
        "parameters": {"temperature": temperature}
    }

    try:
        response = requests.post(URL, headers=headers, json=data, timeout=30)
        if response.status_code != 200:
            print(f"❌ 请求失败！状态码: {response.status_code}")
            print(f"返回内容: {response.text}")
            return None
        return response.json()["output"]["text"]
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return None


if __name__ == "__main__":
    result = call_qwen("你好，我是参赛选手，请鼓励我一下。")
    if result:
        print("✅ 大模型回复：")
        print(result)