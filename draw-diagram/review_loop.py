#!/usr/bin/env python3
"""
draw-diagram Review Loop
用法：
  python3 review_loop.py --arch arch.yaml --output diagram.drawio [--view view.yaml] [--max-rounds 5]

循环：生成图 → review → 自动修复 → 重新生成，直到通过或达到最大轮次。
"""
import argparse, sys, yaml
from pathlib import Path

# 路径设置
BUILDER_DIR = Path(__file__).parent / "builder"
REVIEW_DIR  = Path(__file__).parent / "review"
SHARED_DIR  = Path(__file__).parents[1] / "shared" / "review"
sys.path.insert(0, str(BUILDER_DIR))
sys.path.insert(0, str(SHARED_DIR))
sys.path.insert(0, str(REVIEW_DIR))

from render import render
from protocol import ReviewLoop
from checkers import (
    OverlapChecker, OrphanChecker, PiiColorChecker,
    ContainerChecker, EdgeLabelChecker, NodeTypeChecker,
)
from fixers import OverlapFixer, PiiColorFixer


def main():
    p = argparse.ArgumentParser(description="draw-diagram Review Loop")
    p.add_argument("--arch",       required=True, help="arch.yaml 路径")
    p.add_argument("--output",     required=True, help="输出 .drawio 路径")
    p.add_argument("--view",       default=None,  help="view.yaml 路径（可选）")
    p.add_argument("--max-rounds", type=int, default=5)
    p.add_argument("--verbose",    action="store_true")
    args = p.parse_args()

    arch_path = args.arch
    out_path  = args.output
    view_path = args.view

    with open(arch_path) as f:
        arch = yaml.safe_load(f)
    view = None
    if view_path and Path(view_path).exists():
        with open(view_path) as f:
            view = yaml.safe_load(f)

    context = {
        "arch":       arch,
        "arch_path":  arch_path,
        "drawio_path": out_path,
        "view_path":  view_path,
    }

    # generate_fn：重新渲染（每轮调用）
    def generate():
        with open(arch_path) as f:
            context["arch"] = yaml.safe_load(f)
        v = None
        if view_path and Path(view_path).exists():
            with open(view_path) as f:
                v = yaml.safe_load(f)
        render(context["arch"], out_path, view=v)
        context["drawio_path"] = out_path

    loop = ReviewLoop(
        checkers=[
            OverlapChecker(),
            OrphanChecker(),
            PiiColorChecker(),
            ContainerChecker(),
            EdgeLabelChecker(),
            NodeTypeChecker(),
        ],
        fixers={
            "overlap_checker":   OverlapFixer(),
            "pii_color_checker": PiiColorFixer(),
        },
        max_rounds=args.max_rounds,
        stop_on_pass=True,
        require_human_for_semantic=True,
    )

    final = loop.run(generate_fn=generate, context=context, verbose=args.verbose)

    print(f"\n最终结果：{'通过 ✅' if final.passed else '未通过 ❌'}")
    print(f"共 {len(loop.history)} 轮，"
          f"FAIL: {final.total_fail}，WARN: {final.total_warn}")
    return 0 if final.passed else 1


if __name__ == "__main__":
    sys.exit(main())
