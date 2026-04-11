#!/usr/bin/env python3
"""
使用阿里云百炼（DashScope）大模型翻译文本

支持模型：
- qwen-turbo（推荐，性价比高）
- qwen-plus
- qwen-max

环境变量:
    DASHSCOPE_API_KEY: 阿里云百炼 API Key

用法:
    python3 translate_with_bailian.py <text> [source_language] [target_language]
    python3 translate_with_bailian.py release_notes.txt en zh
"""

import os
import sys
import re
import time
import json
import urllib.request
import urllib.parse


def translate_with_dashscope(
    text: str,
    source_lang: str = 'en',
    target_lang: str = 'zh',
    model: str = 'qwen-turbo',
    temperature: float = 0.3
) -> str:
    """
    调用阿里云百炼 DashScope API 进行翻译

    Args:
        text: 待翻译的文本
        source_lang: 源语言 (en/zh/ja/ko 等)
        target_lang: 目标语言
        model: 使用的模型 (qwen-turbo/qwen-plus/qwen-max)
        temperature: 生成温度，越低越稳定

    Returns:
        翻译后的文本
    """
    api_key = os.environ.get('DASHSCOPE_API_KEY')
    if not api_key:
        raise ValueError('DASHSCOPE_API_KEY 环境变量未设置')

    # 构建翻译提示词
    lang_name_map = {
        'en': '英语',
        'zh': '中文',
        'ja': '日语',
        'ko': '韩语',
        'fr': '法语',
        'de': '德语',
        'es': '西班牙语',
        'ru': '俄语',
    }
    source_lang_name = lang_name_map.get(source_lang, source_lang)
    target_lang_name = lang_name_map.get(target_lang, target_lang)

    system_prompt = f"""你是一位专业的技术文档翻译专家。请将以下内容从{source_lang_name}翻译成{target_lang_name}。

翻译要求：
1. 保持专业性和准确性，特别是技术术语
2. 保持原文的 Markdown 格式（标题、列表、代码块、链接等）
3. 代码块内的内容不要翻译
4. 专有名词（如产品名、API 名称）保持原文
5. 译文要通顺自然，符合{target_lang_name}表达习惯
6. 不要添加任何原文没有的内容
7. 直接输出翻译结果，不要添加解释"""

    user_prompt = f"""{system_prompt}

请翻译以下内容：

{text}"""

    # 构建请求体（百炼 API 只支持 user/assistant role）
    request_body = {
        "model": model,
        "input": {
            "messages": [
                {"role": "user", "content": user_prompt}
            ]
        },
        "parameters": {
            "temperature": temperature,
            "max_tokens": 4096
        }
    }

    # 调用 API
    req = urllib.request.Request(
        'https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation',
        data=json.dumps(request_body).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}',
            'X-DashScope-SSE': 'disable'  # 禁用流式输出
        },
        method='POST'
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        raise Exception(f"HTTP 错误 {e.code}: {error_body}")
    except Exception as e:
        raise Exception(f"请求失败：{e}")

    # 解析响应
    if result.get('status_code') == 200:
        return result['output']['choices'][0]['message']['content']
    else:
        code = result.get('code', 'Unknown')
        message = result.get('message', result)
        raise Exception(f"翻译失败 (Code: {code}): {message}")


def fix_markdown_format(text: str) -> str:
    """
    修复翻译后的 Markdown 格式
    """
    lines = text.split('\n')
    fixed_lines = []

    for line in lines:
        # 修复列表项格式
        line = re.sub(r'^-(\S)', r'- \1', line)
        line = re.sub(r'^\*-(\S)', r'*- \1', line)

        # 修复数字列表
        line = re.sub(r'^(\d+)\.(\S)', r'\1. \2', line)

        fixed_lines.append(line)

    return '\n'.join(fixed_lines)


def translate_long_text(
    text: str,
    source_lang: str = 'en',
    target_lang: str = 'zh',
    model: str = 'qwen-turbo',
    max_chunk_size: int = 4000
) -> str:
    """
    翻译长文本（分段处理）
    大模型有 token 限制，需要分段处理
    """
    if len(text) <= max_chunk_size:
        result = translate_with_dashscope(text, source_lang, target_lang, model)
        return fix_markdown_format(result)

    # 按段落分割
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        if not para or not para.strip():
            continue
        if len(current_chunk) + len(para) + 2 <= max_chunk_size:
            current_chunk += ('\n\n' if current_chunk else '') + para
        else:
            if current_chunk:
                chunks.append(current_chunk)
            if len(para) > max_chunk_size:
                # 超长段落按句子分割
                sentences = para.replace('. ', '.\n').split('\n')
                for sentence in sentences:
                    if not sentence or not sentence.strip():
                        continue
                    if len(sentence) > max_chunk_size:
                        for i in range(0, len(sentence), max_chunk_size):
                            chunk_part = sentence[i:i+max_chunk_size]
                            if chunk_part.strip():
                                chunks.append(chunk_part)
                    else:
                        chunks.append(sentence)
            else:
                chunks.append(para)
            current_chunk = ""

    if current_chunk:
        chunks.append(current_chunk)

    # 翻译每个分段
    translated_chunks = []
    for i, chunk in enumerate(chunks):
        if not chunk or not chunk.strip():
            print(f'跳过空分段 {i+1}/{len(chunks)}...', file=sys.stderr)
            continue
        print(f'翻译分段 {i+1}/{len(chunks)}...', file=sys.stderr)
        translated = translate_with_dashscope(chunk, source_lang, target_lang, model)
        translated_chunks.append(translated)
        translated_chunks.append('')
        time.sleep(0.5)  # 避免 API 限流

    result = '\n\n'.join(translated_chunks)
    return fix_markdown_format(result)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    input_arg = sys.argv[1]

    # 支持文件路径作为输入
    if os.path.isfile(input_arg):
        with open(input_arg, 'r', encoding='utf-8') as f:
            text = f.read()
    else:
        text = input_arg

    source_lang = sys.argv[2] if len(sys.argv) > 2 else 'en'
    target_lang = sys.argv[3] if len(sys.argv) > 3 else 'zh'
    model = os.environ.get('DASHSCOPE_MODEL', 'qwen-turbo')

    try:
        result = translate_long_text(text, source_lang, target_lang, model)
        print(result)
    except Exception as e:
        print(f'错误：{e}', file=sys.stderr)
        sys.exit(1)
