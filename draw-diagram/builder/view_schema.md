# view.yaml Schema

## 职责

view.yaml 记录"在哪里"和"例外视觉"：
- 每个节点的绝对坐标（x/y/w/h）
- 每条连线的路径控制点（可选）
- 偏离语义规则的例外视觉属性（可选）

view.yaml **不记录**：
- 颜色（由 render.py 规则表从 type 推导）
- 线型虚实（由 render.py 规则表从 rel/has_pii 推导）
- 节点标签（在 arch.yaml 中）

## 格式

```yaml
meta:
  arch: arch.yaml          # 关联的 arch.yaml 文件名
  version: "1.0"
  last_modified: "2026-06-02"

nodes:
  cdp:                     # 与 arch.yaml 中的 node.id 对应
    x: 230
    y: 190
    w: 420
    h: 360

  mae:
    x: 750
    y: 252
    w: 460
    h: 290

  # 例外视觉 override（可选，仅在需要偏离标准规则时填写）
  system_a:
    x: 100
    y: 300
    w: 200
    h: 80
    override:
      stroke_color: "#FF6600"   # 橙色边框强调新增节点
      stroke_width: 3

groups:
  client_systems:
    x: -420
    y: 50
    w: 280
    h: 340

edges:
  # 大多数连线不需要记录（渲染器自动连接两端节点中心）
  # 只在需要控制连线路径时记录
  crm_to_system_a:           # from_to 格式
    waypoints:               # 中间控制点（可选）
      - {x: 150, y: 200}
    label_x: 120             # 连线标签位置偏移（可选）
    label_y: -10

canvas:
  width: 1900
  height: 1050
  grid: true
  grid_size: 10
