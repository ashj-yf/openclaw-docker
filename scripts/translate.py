#!/usr/bin/env python3
"""
使用阿里云机器翻译 API 翻译文本

环境变量:
    ALIYUN_ACCESS_KEY_ID: 阿里云 AccessKey ID
    ALIYUN_ACCESS_KEY_SECRET: 阿里云 AccessKey Secret

用法:
    python3 translate.py <text> [source_language] [target_language]
"""

import base64
import hashlib
import hmac
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import json
from datetime import datetime, timezone


def percent_encode(s: str) -> str:
    """URL 编码（阿里云规范）"""
    return urllib.parse.quote(s, safe='~')


def sign(params: dict, access_key_secret: str) -> str:
    """生成阿里云 API 签名"""
    sorted_params = sorted(params.items())
    canonicalized_query = '&'.join([
        f'{percent_encode(k)}={percent_encode(v)}'
        for k, v in sorted_params
    ])
    string_to_sign = f'GET&%2F&{percent_encode(canonicalized_query)}'
    key = f'{access_key_secret}&'.encode('utf-8')
    signature = hmac.new(key, string_to_sign.encode('utf-8'), hashlib.sha1).digest()
    signature_base64 = base64.b64encode(signature).decode('utf-8')
    return signature_base64


def translate(text: str, source_lang: str = 'en', target_lang: str = 'zh') -> str:
    """调用阿里云机器翻译 API"""

    access_key_id = os.environ.get('ALIYUN_ACCESS_KEY_ID')
    access_key_secret = os.environ.get('ALIYUN_ACCESS_KEY_SECRET')

    if not access_key_id or not access_key_secret:
        raise ValueError('ALIYUN_ACCESS_KEY_ID and ALIYUN_ACCESS_KEY_SECRET must be set')

    params = {
        'Action': 'TranslateGeneral',
        'Version': '2018-10-12',
        'Format': 'JSON',
        'AccessKeyId': access_key_id,
        'SignatureMethod': 'HMAC-SHA1',
        'SignatureVersion': '1.0',
        'SignatureNonce': str(hashlib.md5(str(time.time()).encode()).hexdigest()),
        'Timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'FormatType': 'text',
        'SourceLanguage': source_lang,
        'TargetLanguage': target_lang,
        'Scene': 'general',
        'SourceText': text,
    }

    params['Signature'] = sign(params, access_key_secret)

    endpoint = os.environ.get('ALIYUN_MT_ENDPOINT', 'mt.cn-hangzhou.aliyuncs.com')
    query_string = '&'.join([f'{k}={urllib.parse.quote(v, safe="")}' for k, v in params.items()])
    url = f'https://{endpoint}/?{query_string}'

    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        raise Exception(f"HTTP Error {e.code}: {error_body}")
    except Exception as e:
        raise Exception(f"Request failed: {e}")

    if str(result.get('Code')) == '200':
        return result['Data']['Translated']
    else:
        raise Exception(f"Translation failed (Code: {result.get('Code')}): {result.get('Message', result)}")


def fix_markdown_format(text: str) -> str:
    """
    修复翻译后的 Markdown 格式
    阿里云翻译有时会破坏 markdown 格式，需要修复
    """
    lines = text.split('\n')
    fixed_lines = []

    for line in lines:
        # 修复列表项格式: "-文字" -> "- 文字"
        line = re.sub(r'^-(\S)', r'- \1', line)
        line = re.sub(r'^\*-(\S)', r'*- \1', line)  # 修复 "- Markdown: text"

        # 修复数字列表: "1.文字" -> "1. 文字"
        line = re.sub(r'^(\d+)\.(\S)', r'\1. \2', line)

        fixed_lines.append(line)

    return '\n'.join(fixed_lines)


def translate_long_text(text: str, source_lang: str = 'en', target_lang: str = 'zh',
                       max_chunk_size: int = 4500) -> str:
    """
    翻译长文本（分段处理）
    阿里云 API 单次请求上限 5000 字符
    """
    if len(text) <= max_chunk_size:
        result = translate(text, source_lang, target_lang)
        return fix_markdown_format(result)

    # 按段落分割
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 <= max_chunk_size:
            current_chunk += ('\n\n' if current_chunk else '') + para
        else:
            if current_chunk:
                chunks.append(current_chunk)
            if len(para) > max_chunk_size:
                sentences = para.replace('. ', '.\n').split('\n')
                for sentence in sentences:
                    if len(sentence) > max_chunk_size:
                        for i in range(0, len(sentence), max_chunk_size):
                            chunks.append(sentence[i:i+max_chunk_size])
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
        print(f'Translating chunk {i+1}/{len(chunks)}...', file=sys.stderr)
        translated = translate(chunk, source_lang, target_lang)
        translated_chunks.append(translated)
        time.sleep(0.5)

    result = '\n\n'.join(translated_chunks)
    return fix_markdown_format(result)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    text = sys.argv[1]
    source_lang = sys.argv[2] if len(sys.argv) > 2 else 'en'
    target_lang = sys.argv[3] if len(sys.argv) > 3 else 'zh'

    try:
        result = translate_long_text(text, source_lang, target_lang)
        print(result)
    except Exception as e:
        print(f'Error: {e}', file=sys.stderr)
        sys.exit(1)