"""
神策 CDP & MAE 架构图标准组件库
每个组件定义：样式、默认尺寸、语义类型
"""

# ── 颜色常量 ─────────────────────────────────────────────────────────────────
COLORS = {
    "sd_product":    {"fill": "#d5e8d4", "stroke": "#82b366"},   # 绿：神策产品
    "client_system": {"fill": "#e1d5e7", "stroke": "#9673a6"},   # 紫：客户系统
    "external_saas": {"fill": "#dae8fc", "stroke": "#6c8ebf"},   # 蓝：外部SaaS
    "module":        {"fill": "#fffde7", "stroke": "#d6b656"},   # 黄：内部模块
    "future":        {"fill": "#f5f5f5", "stroke": "#bdbdbd", "dashed": True},  # 灰：Future
    "container":     {"fill": "none",    "stroke": "#82b366", "dashed": True},  # 无填充容器
    "person":        {"fill": "#FFCE9F", "stroke": "#d79b00"},   # 人形图标
    "internet":      {"fill": "none",    "stroke": "#6c8ebf", "dashed": True},  # 互联网区域
}

# ── 连线颜色常量 ─────────────────────────────────────────────────────────────
EDGE_COLORS = {
    "pii_realtime":  "#FF0000",   # 红实线：含PII实时流
    "pii_batch":     "#FF0000",   # 红虚线：含PII批量流
    "internal":      "#82b366",   # 绿实线：内部数据流
    "kafka_async":   "#6c8ebf",   # 蓝虚线：Kafka异步
    "config":        "#666666",   # 灰实线：配置/系统数据
    "future":        "#bdbdbd",   # 灰虚线：Future连线
}

# ── 组件定义 ─────────────────────────────────────────────────────────────────
# 格式：id → {label, type, color_key, w, h, shape}
STANDARD_COMPONENTS = {

    # ── 神策核心产品 ────────────────────────────────────────────────────────
    "cdp": {
        "label": "CDP",
        "type": "container",
        "color_key": "sd_product",
        "w": 420, "h": 360,
        "font_size": 36,
        "description": "神策 CDP 主容器，包含数据接入/身份解析/分群/分析等模块",
    },
    "mae": {
        "label": "MAE",
        "type": "container",
        "color_key": "sd_product",
        "w": 460, "h": 290,
        "font_size": 36,
        "description": "神策 MAE 主容器，包含活动规划/旅程编排/渠道管理等模块",
    },
    "etl": {
        "label": "ETL",
        "type": "node",
        "color_key": "sd_product",
        "w": 120, "h": 50,
        "description": "ETL 批量数据处理节点",
    },
    "sftp": {
        "label": "SFTP Server",
        "type": "node",
        "color_key": "sd_product",
        "w": 140, "h": 50,
        "description": "SFTP 文件传输服务器",
    },

    # ── CDP 内部模块 ─────────────────────────────────────────────────────────
    "cdp_ingest": {
        "label": "📥 Data Ingestion & ETL",
        "type": "module",
        "color_key": "module",
        "w": 360, "h": 50,
        "description": "数据接入与批量处理",
    },
    "cdp_identity": {
        "label": "🔗 Identity Resolution",
        "type": "module",
        "color_key": "module",
        "w": 360, "h": 50,
        "description": "跨渠道身份解析与 ID Mapping",
    },
    "cdp_segment": {
        "label": "🎯 Segmentation & Tagging",
        "type": "module",
        "color_key": "module",
        "w": 360, "h": 50,
        "description": "用户分群与标签",
    },
    "cdp_analytics": {
        "label": "📊 Analytics & Dashboard",
        "type": "module",
        "color_key": "module",
        "w": 360, "h": 50,
        "description": "分析与仪表盘",
    },

    # ── MAE 内部模块 ─────────────────────────────────────────────────────────
    "mae_campaign": {
        "label": "📅 Campaign Planning",
        "type": "module",
        "color_key": "module",
        "w": 400, "h": 50,
        "description": "活动规划（时间触发/事件触发）",
    },
    "mae_journey": {
        "label": "🗺 Journey Orchestration",
        "type": "module",
        "color_key": "module",
        "w": 400, "h": 50,
        "description": "旅程编排（多步骤/分支/等待/退出）",
    },
    "mae_channel": {
        "label": "📡 Channel Management",
        "type": "module",
        "color_key": "module",
        "w": 400, "h": 50,
        "description": "渠道管理（eDM/Push/SMS/Webhook）",
    },

    # ── 客户系统 ─────────────────────────────────────────────────────────────
    "crm": {
        "label": "CRM",
        "type": "node",
        "color_key": "client_system",
        "w": 120, "h": 40,
        "description": "客户关系管理系统",
    },
    "ticketing": {
        "label": "Ticketing System",
        "type": "node",
        "color_key": "client_system",
        "w": 160, "h": 40,
        "description": "票务系统",
    },
    "erp": {
        "label": "ERP",
        "type": "node",
        "color_key": "client_system",
        "w": 120, "h": 40,
        "description": "企业资源规划系统",
    },
    "pos": {
        "label": "POS",
        "type": "node",
        "color_key": "client_system",
        "w": 100, "h": 40,
        "description": "销售终端系统",
        "future": True,
    },

    # ── 前端渠道 ─────────────────────────────────────────────────────────────
    "miniprogram": {
        "label": "Mini-Program",
        "type": "node",
        "color_key": "client_system",
        "w": 140, "h": 40,
        "description": "微信小程序",
    },
    "website": {
        "label": "Website",
        "type": "node",
        "color_key": "client_system",
        "w": 120, "h": 40,
        "description": "网站",
    },
    "app": {
        "label": "Mobile App",
        "type": "node",
        "color_key": "client_system",
        "w": 120, "h": 40,
        "description": "移动应用",
    },

    # ── 外部 SaaS ────────────────────────────────────────────────────────────
    "sendcloud": {
        "label": "SendCloud",
        "type": "node",
        "color_key": "external_saas",
        "w": 140, "h": 50,
        "description": "邮件投递服务商（SendCloud）",
    },
    "email_service": {
        "label": "Email Service",
        "type": "node",
        "color_key": "external_saas",
        "w": 140, "h": 50,
        "description": "邮件服务商（通用）",
    },

    # ── 用户角色 ─────────────────────────────────────────────────────────────
    "end_user": {
        "label": "End User",
        "type": "person",
        "color_key": "person",
        "w": 60, "h": 80,
        "shape": "mxgraph.basic.person2",
        "description": "最终用户/客户",
    },
    "business_user": {
        "label": "Business User",
        "type": "person",
        "color_key": "person",
        "w": 60, "h": 80,
        "shape": "mxgraph.basic.person2",
        "description": "业务用户（营销人员/分析师）",
    },
    "ops_user": {
        "label": "Maintenance User",
        "type": "person",
        "color_key": "person",
        "w": 60, "h": 80,
        "shape": "mxgraph.basic.person2",
        "description": "运维/维护用户",
    },

    # ── 通用自定义节点 ───────────────────────────────────────────────────────
    "custom_sd": {
        "label": "Custom (SD Product)",
        "type": "node",
        "color_key": "sd_product",
        "w": 160, "h": 50,
        "description": "自定义神策产品节点，修改 label 使用",
    },
    "custom_client": {
        "label": "Custom (Client System)",
        "type": "node",
        "color_key": "client_system",
        "w": 160, "h": 50,
        "description": "自定义客户系统节点，修改 label 使用",
    },
    "custom_external": {
        "label": "Custom (External)",
        "type": "node",
        "color_key": "external_saas",
        "w": 160, "h": 50,
        "description": "自定义外部系统节点，修改 label 使用",
    },
}

# ── 标准连线模式 ─────────────────────────────────────────────────────────────
STANDARD_EDGES = {
    "sdk_realtime": {
        "style": "pii_realtime",
        "dashed": False,
        "label_template": "SDK / HTTPS (real-time)\n{data_fields}",
        "description": "SDK 实时数据上报，含 PII",
    },
    "sftp_batch": {
        "style": "pii_batch",
        "dashed": True,
        "label_template": "SFTP Batch (daily, T+1)\n{data_fields}",
        "description": "SFTP 批量文件传输，含 PII",
    },
    "api_realtime": {
        "style": "pii_realtime",
        "dashed": False,
        "label_template": "HTTPS API (real-time)\n{data_fields}",
        "description": "HTTPS API 实时调用",
    },
    "kafka_async": {
        "style": "kafka_async",
        "dashed": True,
        "label_template": "Kafka Topic Sub (async)\n{data_fields}",
        "description": "Kafka 异步消费",
    },
    "internal_flow": {
        "style": "internal",
        "dashed": False,
        "label_template": "{data_fields}",
        "description": "系统内部数据流（非 PII）",
    },
    "config_flow": {
        "style": "config",
        "dashed": False,
        "label_template": "{data_fields}",
        "description": "配置/系统数据流",
    },
}

def list_components():
    """打印所有可用组件"""
    print("=== 神策标准组件库 ===\n")
    categories = {
        "神策产品": ["cdp", "mae", "etl", "sftp"],
        "CDP 内部模块": ["cdp_ingest", "cdp_identity", "cdp_segment", "cdp_analytics"],
        "MAE 内部模块": ["mae_campaign", "mae_journey", "mae_channel"],
        "客户系统": ["crm", "ticketing", "erp", "pos"],
        "前端渠道": ["miniprogram", "website", "app"],
        "外部 SaaS": ["sendcloud", "email_service"],
        "用户角色": ["end_user", "business_user", "ops_user"],
        "自定义": ["custom_sd", "custom_client", "custom_external"],
    }
    for cat, ids in categories.items():
        print(f"【{cat}】")
        for cid in ids:
            c = STANDARD_COMPONENTS.get(cid, {})
            future = " [Future]" if c.get("future") else ""
            print(f"  {cid:<20} {c.get('description','')}{future}")
        print()

if __name__ == "__main__":
    list_components()
