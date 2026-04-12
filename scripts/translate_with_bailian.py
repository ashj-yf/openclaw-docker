#!/usr/bin/env python3
"""
使用阿里云百炼（DashScope）大模型翻译文本

支持模型：
- qwen-turbo（推荐，性价比高）
- qwen-plus
- qwen-max

环境变量:
    DASHSCOPE_API_KEY: 阿里云百炼 API Key
    DASHSCOPE_MODEL: 使用的模型（默认 qwen-turbo）

用法:
    python3 translate_with_bailian.py <text_file> [source_lang] [target_lang]
    python3 translate_with_bailian.py release_notes.txt en zh
"""

import os
import sys
import re
import time
import json
import urllib.request
from typing import Optional


# =============================================================================
# 配置常量
# =============================================================================

DASHSCOPE_API_URL = 'https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation'

LANGUAGE_NAMES = {
    'en': '英语',
    'zh': '中文',
    'ja': '日语',
    'ko': '韩语',
    'fr': '法语',
    'de': '德语',
    'es': '西班牙语',
    'ru': '俄语',
}

# 分段策略配置
MAX_CHUNK_SIZE = 8000  # 单段最大字符数
API_RETRY_DELAY = 0.5  # API 请求间隔（秒）
API_TIMEOUT = 120      # API 超时时间（秒）


# =============================================================================
# API 调用函数
# =============================================================================

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
        source_lang: 源语言代码
        target_lang: 目标语言代码
        model: 使用的模型
        temperature: 生成温度

    Returns:
        翻译后的文本
    """
    api_key = os.environ.get('DASHSCOPE_API_KEY')
    if not api_key:
        raise ValueError('DASHSCOPE_API_KEY 环境变量未设置')

    source_lang_name = LANGUAGE_NAMES.get(source_lang, source_lang)
    target_lang_name = LANGUAGE_NAMES.get(target_lang, target_lang)

    # 构建系统提示词
    system_prompt = build_translation_prompt(source_lang_name, target_lang_name)

    # 构建用户消息
    user_content = f"{system_prompt}\n\n请翻译以下内容：\n\n{text}"

    # 构建请求体
    request_body = {
        "model": model,
        "input": {
            "messages": [{"role": "user", "content": user_content}]
        },
        "parameters": {
            "temperature": temperature,
            "max_tokens": 4096
        }
    }

    # 发送请求
    req = urllib.request.Request(
        DASHSCOPE_API_URL,
        data=json.dumps(request_body).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}',
            'X-DashScope-SSE': 'disable'
        },
        method='POST'
    )

    try:
        with urllib.request.urlopen(req, timeout=API_TIMEOUT) as response:
            result = json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        raise Exception(f"HTTP 错误 {e.code}: {error_body}")
    except Exception as e:
        raise Exception(f"请求失败：{e}")

    # 解析响应
    if result.get('output') and result['output'].get('choices'):
        return result['output']['choices'][0]['message']['content']
    else:
        code = result.get('code', 'Unknown')
        message = result.get('message', str(result))
        raise Exception(f"翻译失败 (Code: {code}): {message}")


def build_translation_prompt(source_lang: str, target_lang: str) -> str:
    """构建翻译系统提示词"""
    return f"""你是一位专业的技术文档翻译专家。请将以下内容从{source_lang}翻译成{target_lang}。

翻译要求：
1. 保持专业性和准确性，特别是技术术语
2. 保持原文的 Markdown 格式（标题、列表、代码块、链接等）
3. 代码块内的内容不要翻译
4. 专有名词（如产品名、API 名称）保持原文
5. 译文要通顺自然，符合{target_lang}表达习惯
6. 不要添加任何原文没有的内容
7. 不要遗漏任何内容
8. 直接输出翻译结果，不要添加解释"""


# =============================================================================
# Markdown 处理函数
# =============================================================================

def fix_markdown_format(text: str) -> str:
    """
    修复翻译后的 Markdown 格式
    """
    lines = text.split('\n')
    fixed_lines = []

    for line in lines:
        # 修复列表项格式：-xxx → - xxx
        line = re.sub(r'^-(\S)', r'- \1', line)
        # 修复 * 列表格式
        line = re.sub(r'^\*(\S)', r'* \1', line)
        # 修复数字列表：1.xxx → 1. xxx
        line = re.sub(r'^(\d+)\.(\S)', r'\1. \2', line)
        fixed_lines.append(line)

    return '\n'.join(fixed_lines)


def split_by_markdown_headers(text: str) -> list[str]:
    """
    按 Markdown 三级标题 (###) 分割文本，保持结构完整

    Returns:
        分割后的章节列表
    """
    # 使用前瞻断言分割，保留 ### 标题
    sections = re.split(r'(?=^### )', text, flags=re.MULTILINE)
    # 过滤空章节
    return [s.strip() for s in sections if s and s.strip()]


def split_by_paragraphs(text: str, max_size: int = MAX_CHUNK_SIZE) -> list[str]:
    """
    按段落分割文本，确保每段不超过 max_size

    Args:
        text: 待分割的文本
        max_size: 单段最大字符数

    Returns:
        分割后的段落列表
    """
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        if not para or not para.strip():
            continue

        # 如果当前段落可以加入当前块
        if len(current_chunk) + len(para) + 2 <= max_size:
            current_chunk += ('\n\n' if current_chunk else '') + para
        else:
            # 保存当前块
            if current_chunk:
                chunks.append(current_chunk)

            # 处理超长段落
            if len(para) > max_size:
                # 按句子分割
                sentences = re.split(r'(?<=[.!?])\s+', para)
                for sentence in sentences:
                    if not sentence.strip():
                        continue
                    if len(sentence) > max_size:
                        # 极端情况：按字符分割
                        for i in range(0, len(sentence), max_size):
                            chunks.append(sentence[i:i+max_size])
                    else:
                        chunks.append(sentence)
            else:
                current_chunk = para

    # 保存最后一个块
    if current_chunk:
        chunks.append(current_chunk)

    return chunks


# =============================================================================
# 主翻译逻辑
# =============================================================================

def translate_text(
    text: str,
    source_lang: str = 'en',
    target_lang: str = 'zh',
    model: str = 'qwen-turbo'
) -> str:
    """
    智能翻译文本，自动选择分段策略

    Args:
        text: 待翻译的文本
        source_lang: 源语言
        target_lang: 目标语言
        model: 使用的模型

    Returns:
        翻译后的文本
    """
    text_length = len(text)
    print(f'待翻译文本长度：{text_length} 字符', file=sys.stderr)

    # 短文本：直接翻译
    if text_length <= MAX_CHUNK_SIZE:
        print('文本较短，直接翻译...', file=sys.stderr)
        result = translate_with_dashscope(text, source_lang, target_lang, model)
        return fix_markdown_format(result)

    # 尝试按标题分割
    sections = split_by_markdown_headers(text)
    print(f'按标题分割为 {len(sections)} 个章节', file=sys.stderr)

    # 如果章节数量合理（每个章节平均大小合适），按章节翻译
    if sections and len(sections) <= 10:
        avg_section_size = text_length / len(sections)
        if avg_section_size <= MAX_CHUNK_SIZE * 0.8:  # 留 20% 余量
            print('按章节翻译...', file=sys.stderr)
            translated_sections = []

            for i, section in enumerate(sections, 1):
                print(f'翻译章节 {i}/{len(sections)} ({len(section)} 字符)...', file=sys.stderr)
                # 如果单个章节过大，递归处理
                if len(section) > MAX_CHUNK_SIZE:
                    translated = translate_text(section, source_lang, target_lang, model)
                else:
                    translated = translate_with_dashscope(section, source_lang, target_lang, model)
                translated_sections.append(fix_markdown_format(translated))
                time.sleep(API_RETRY_DELAY)

            result = '\n\n'.join(translated_sections)
            print(f'翻译完成，结果长度：{len(result)} 字符', file=sys.stderr)
            return result

    # 回退到按段落分割
    print('回退到按段落分割...', file=sys.stderr)
    chunks = split_by_paragraphs(text, MAX_CHUNK_SIZE)
    print(f'分割为 {len(chunks)} 个段落', file=sys.stderr)

    translated_chunks = []
    for i, chunk in enumerate(chunks, 1):
        print(f'翻译段落 {i}/{len(chunks)} ({len(chunk)} 字符)...', file=sys.stderr)
        translated = translate_with_dashscope(chunk, source_lang, target_lang, model)
        translated_chunks.append(fix_markdown_format(translated))
        time.sleep(API_RETRY_DELAY)

    result = '\n\n'.join(translated_chunks)
    print(f'翻译完成，结果长度：{len(result)} 字符', file=sys.stderr)
    return result


# =============================================================================
# 命令行入口
# =============================================================================

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("参数说明:")
        print("  input: 输入文件或文本")
        print("  source_lang: 源语言代码（默认 en）")
        print("  target_lang: 目标语言代码（默认 zh）")
        sys.exit(1)

    input_arg = sys.argv[1]

    # 读取输入（文件或文本）
    if os.path.isfile(input_arg):
        with open(input_arg, 'r', encoding='utf-8') as f:
            text = f.read()
        print(f'从文件读取：{input_arg}', file=sys.stderr)
    else:
        text = input_arg

    # 解析参数
    source_lang = sys.argv[2] if len(sys.argv) > 2 else 'en'
    target_lang = sys.argv[3] if len(sys.argv) > 3 else 'zh'
    model = os.environ.get('DASHSCOPE_MODEL', 'qwen-turbo')

    print(f'翻译配置：{source_lang} → {target_lang}, 模型：{model}', file=sys.stderr)
    print(f'DASHSCOPE_API_KEY: {os.environ.get("DASHSCOPE_API_KEY", "")[:8]}...', file=sys.stderr)

    try:
        result = translate_text(text, source_lang, target_lang, model)
        print(result)
    except Exception as e:
        print(f'错误：{e}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
