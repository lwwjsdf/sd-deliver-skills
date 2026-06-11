#!/usr/bin/env python3
"""
draw.io 架构图快速生成器
用法：python3 gen_diagrams.py --config client_config.json --output /path/to/output/

config.json 格式见下方 EXAMPLE_CONFIG。
"""

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent

# 模板文件列表
TEMPLATES = [
    "Logical_Architecture_TEMPLATE.drawio",
    "Data_Flow_TEMPLATE.drawio",
    "System_Flow_EndUser_TEMPLATE.drawio",
    "System_Flow_Employee_TEMPLATE.drawio",
    "System_Flow_Maintenance_TEMPLATE.drawio",
    "Functional_Architecture_TEMPLATE.drawio",
]

# 输出文件名（去掉 _TEMPLATE）
def output_name(template: str, client: str) -> str:
    base = template.replace("_TEMPLATE", f"_{client}")
    return base

EXAMPLE_CONFIG = {
    "CLIENT": "NewClient",
    "CLIENT_SYSTEMS": "NewClient Systems",
    "BUSINESS_USER": "NewClient Employee",
    "EMAIL_SERVICE": "SendCloud",
    "FRONTEND_1": "Mini-Program",
    "FRONTEND_2": "Website",
    "FRONTEND_3": "Mobile App",
    "FRONTEND_4": "Other Channels",
    "SOCIAL_MEDIA": "Social Media",
    "SYSTEM_1": "CRM System",
    "SYSTEM_2": "Business Data",
    "SYSTEM_3": "CRM",
    "SYSTEM_4": "RSVP",
    "SYSTEM_5": "Retail System",
    "SYSTEM_6": "POS",
    "SYSTEM_7": "Other System 1",
    "SYSTEM_8": "Other System 2",
}


def apply_config(content: str, config: dict) -> str:
    for key, value in config.items():
        content = content.replace(f"{{{{{key}}}}}", value)
    return content


def generate(config_path: str, output_dir: str):
    # 读取配置
    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)

    client = config.get("CLIENT", "Client")
    os.makedirs(output_dir, exist_ok=True)

    generated = []
    for template_name in TEMPLATES:
        template_path = SCRIPT_DIR / template_name
        if not template_path.exists():
            print(f"⚠️  模板不存在，跳过：{template_name}", file=sys.stderr)
            continue

        with open(template_path, encoding="utf-8") as f:
            content = f.read()

        content = apply_config(content, config)

        # 检查是否还有未替换的占位符
        import re
        remaining = re.findall(r'\{\{[A-Z_0-9]+\}\}', content)
        if remaining:
            print(f"⚠️  {template_name} 中有未替换的占位符：{sorted(set(remaining))}")

        out_name = output_name(template_name, client)
        out_path = os.path.join(output_dir, out_name)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)

        generated.append(out_name)
        print(f"✓ {out_name}")

    print(f"\n共生成 {len(generated)} 个文件，输出目录：{output_dir}")
    print("\n下一步：")
    print("  1. 用 draw.io 打开各文件，检查占位符是否全部替换")
    print("  2. 根据客户实际情况删除不需要的 Future 节点")
    print("  3. 调整连线标签（数据字段名、协议、频率）")
    print("  4. 导出为 PNG/SVG 嵌入 LLD PPT")


def main():
    parser = argparse.ArgumentParser(description="draw.io 架构图快速生成器")
    parser.add_argument("--config", required=True, help="客户配置 JSON 文件路径")
    parser.add_argument("--output", required=True, help="输出目录")
    parser.add_argument("--example", action="store_true", help="输出示例配置文件")
    args = parser.parse_args()

    if args.example:
        print(json.dumps(EXAMPLE_CONFIG, ensure_ascii=False, indent=2))
        return

    generate(args.config, args.output)


if __name__ == "__main__":
    main()
