# 神策 CDP API 封装
# 所有 skill 脚本通过此模块与神策系统交互，不直接调用 browse

import json
import os
import subprocess
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

SA_HOST = os.getenv("SA_HOST", "").rstrip("/")
SA_PROJECT = os.getenv("SA_PROJECT", "")
SA_TOKEN = os.getenv("SA_TOKEN", "")

BROWSE_BIN = Path.home() / ".claude/skills/gstack/browse/dist/browse"


def validate_env(required: list[str]):
    """检查必要的环境变量是否已配置"""
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        print(f"错误：缺少必要配置，请在 .env 中设置：{', '.join(missing)}")
        raise SystemExit(1)


def _browse(cmd: list[str]) -> str:
    result = subprocess.run(
        [str(BROWSE_BIN)] + cmd,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def ensure_session():
    """确保 browse 已有登录态，自动通过 cookie picker 导入"""
    if not BROWSE_BIN.exists():
        print("错误：未找到 gstack/browse，请确认已安装")
        raise SystemExit(1)

    # 启动 cookie-import-browser
    proc = subprocess.Popen(
        [str(BROWSE_BIN), "cookie-import-browser", "Chrome"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    picker_url = None
    for line in proc.stdout:
        if "cookie-picker" in line:
            picker_url = line.strip().split()[-1]
            break

    if not picker_url:
        return  # 已有 session，无需导入

    # 在 browse 内部打开 picker 并自动选择目标域名
    time.sleep(0.5)
    hostname = SA_HOST.replace("https://", "").replace("http://", "").split("/")[0]
    _browse(["goto", picker_url])
    time.sleep(0.5)
    _browse(["fill", "[placeholder='Search domains...']", hostname])
    time.sleep(0.5)

    # 验证导入结果
    text = _browse(["text"])
    if hostname in text:
        print(f"  ✓ 登录态导入成功（{hostname}）")
    else:
        print(f"  警告：登录态导入状态未知，继续尝试")

    # 导航到目标站点激活 session
    _browse(["goto", f"{SA_HOST}/report/?project={SA_PROJECT}"])
    time.sleep(2)


def fetch(path: str, method: str = "GET", body: dict = None) -> dict:
    """通过 browse 发起 API 请求（复用已登录的 session）"""
    url = f"{SA_HOST}{path}"
    if body:
        js = (
            f"fetch('{url}', {{"
            f"method:'{method}',"
            f"credentials:'include',"
            f"headers:{{'Content-Type':'application/json'}},"
            f"body:JSON.stringify({json.dumps(body, ensure_ascii=False)})"
            f"}}).then(r=>r.json()).then(d=>JSON.stringify(d))"
        )
    else:
        js = f"fetch('{url}',{{credentials:'include'}}).then(r=>r.json()).then(d=>JSON.stringify(d))"

    raw = _browse(["js", js])
    try:
        return json.loads(raw)
    except Exception:
        return {"_raw": raw}


def check_connection() -> bool:
    """验证连接和登录态是否正常"""
    resp = fetch(f"/api/v2/horizon/v1/web/config/get?project={SA_PROJECT}")
    if "error_type" in resp and "UNAUTHORIZED" in str(resp):
        return False
    if "_raw" in resp:
        return False
    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="验证连接")
    args = parser.parse_args()

    if args.check:
        validate_env(["SA_HOST", "SA_PROJECT"])
        print(f"目标：{SA_HOST}  项目：{SA_PROJECT}")
        ensure_session()
        if check_connection():
            print("✓ 连接正常，登录态有效")
        else:
            print("✗ 连接失败，请检查 SA_HOST、SA_PROJECT 配置或重新登录")
