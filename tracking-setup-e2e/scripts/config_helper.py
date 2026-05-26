#!/usr/bin/env python3
"""
config_helper.py — 公共配置获取模块

支持优先级：命令行参数 > 环境变量 > 交互式提示 > 报错
"""

import getpass
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv

    # .env 查找顺序：当前目录 → 父目录 → 祖父目录 → 脚本所在目录的父目录
    for _p in [
        Path.cwd(),
        Path.cwd().parent,
        Path.cwd().parent.parent,
        Path(__file__).parent.parent,
    ]:
        if (_p / ".env").exists():
            load_dotenv(_p / ".env")
            break
except ImportError:
    pass


CONFIG_SCHEMA = {
    "cdp_url": {
        "env_key": "SA_HOST",
        "prompt": "CDP 地址",
        "example": "https://demo.sensorsdata.cn",
        "help": "神策 CDP 控制台地址，登录后在浏览器地址栏看到",
    },
    "project": {
        "env_key": "SA_PROJECT",
        "prompt": "项目 ID",
        "example": "default",
        "help": "登录神策后 URL 中 project= 后面的值",
    },
    "api_key": {
        "env_key": "API_KEY",
        "prompt": "Open API 密钥",
        "example": "#K-jHllJkcPOMeRke3Vi5Nokeuc1MDlRZls",
        "help": "神策后台 → 系统管理 → API 密钥 → 创建密钥",
        "secret": True,
    },
    "data_url": {
        "env_key": "SA_TRACK_URL",
        "prompt": "数据接收地址",
        "example": "https://demo.sensorsdata.cn/sa?project=default",
        "help": "神策后台 → 数据接入 → HTTP API → 复制接入地址",
    },
    "tracking_plan": {
        "env_key": "TRACKING_PLAN_PATH",
        "prompt": "埋点方案路径",
        "example": "./references/tracking-plan.xlsx",
        "help": "埋点方案 Excel 文件的路径",
    },
}


def get_config(key: str, args_value: str = "", interactive: bool = True) -> str:
    """获取配置值，优先级：命令行参数 > 环境变量 > 交互式提示 > 报错"""
    schema = CONFIG_SCHEMA[key]

    if args_value:
        return args_value

    env_value = os.getenv(schema["env_key"], "")
    if env_value:
        return env_value

    if interactive and sys.stdin.isatty():
        print(f"\n{schema['prompt']}:")
        print(f"  示例: {schema['example']}")
        print(f"  获取: {schema['help']}")

        if schema.get("secret"):
            value = getpass.getpass("  请输入: ").strip()
        else:
            value = input("  请输入: ").strip()

        if value:
            return value

    print(f"\n❌ 错误：缺少 {schema['prompt']}")
    print(f"  请通过以下方式之一提供：")
    print(f"  1. 命令行参数: --{key.replace('_', '-')} <值>")
    print(f"  2. 环境变量: {schema['env_key']}=<值>")
    print(f"  3. .env 文件: {schema['env_key']}=<值>")
    print(f"  4. 交互式提示（直接运行脚本）")
    print(f"\n  示例值: {schema['example']}")
    print(f"  获取方式: {schema['help']}")
    sys.exit(1)
