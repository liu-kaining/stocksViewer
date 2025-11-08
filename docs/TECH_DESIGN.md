stocksViewer MVP – Technical Design
==================================

1. System Overview
------------------

stocksViewer 使用 Flask 作为后端框架，整合 Alpha Vantage 数据 API，SQLite 作为持久化层，并通过前端 ECharts 组件提供行情与指标可视化。架构需满足数据缓存、配置管理与未来 AI 服务扩展需求。

2. Architecture
---------------

```
┌───────────────────────────┐
│        Presentation        │
│  Flask (Jinja Templates)   │
│  Static Assets (JS/CSS)     │
│  ECharts Visualization      │
└─────────────┬──────────────┘
              │
┌─────────────▼──────────────┐
│        Application          │
│  Flask Blueprints           │
│  services/alphavantage.py   │
│  services/cache.py          │
│  services/ai.py             │
└─────────────┬──────────────┘
              │
┌─────────────▼──────────────┐
│        Data Layer           │
│  SQLite (sqlite3 / ORM)     │
│  app_config / historical    │
│  indicator / recent_quotes  │
└─────────────┬──────────────┘
              │
┌─────────────▼──────────────┐
│    External Integrations    │
│  Alpha Vantage REST APIs    │
│  (future) DeepSeek / Qwen   │
└────────────────────────────┘
```

3. Project Structure
--------------------

```
stocksViewer/
├── app/
│   ├── __init__.py
│   ├── config/
│   │   └── defaults.py        # 默认配置 schema
│   ├── db/
│   │   ├── __init__.py        # 数据库连接 & 初始化
│   │   └── models.py          # 数据表访问封装
│   ├── routes/
│   │   ├── views.py           # 页面路由
│   │   └── api.py             # JSON API
│   ├── services/
│   │   ├── alphavantage.py    # API 客户端 & 节流
│   │   ├── cache.py           # 缓存读写逻辑
│   │   └── ai.py              # DeepSeek/Qwen 封装
│   ├── templates/
│   │   ├── index.html
│   │   └── settings.html
│   └── static/
│       ├── css/
│       └── js/
├── docs/
│   ├── PRD.md
│   └── TECH_DESIGN.md
├── migrations/                # 如选择 Alembic，可在后续引入
├── tests/
├── run.py
└── requirements.txt
```

4. Configuration Schema
-----------------------

`app/config/defaults.py` 返回统一配置结构：

```python
DEFAULT_CONFIG = {
    "alphavantage": {
        "api_key": "",
        "default_range": "1M",
        "default_interval": "daily",
        "auto_refresh_sec": 60
    },
    "cache": {
        "history_ttl_days": 365,
        "quote_ttl_sec": 60,
        "indicator_ttl_sec": 300
    },
    "ai": {
        "deepseek": {
            "enabled": False,
            "api_key": "",
            "endpoint": "",
            "model": ""
        },
        "qwen": {
            "enabled": False,
            "api_key": "",
            "endpoint": "",
            "model": ""
        },
        "insight_prompt": ""
    },
    "ui": {
        "theme": "light",
        "show_ai_panel": False
    }
}
```

- SQLite `app_config` 表按一级 key 存储 JSON 字符串，系统启动时加载并与默认配置深度合并。
- 提供 `get_config()` 和 `update_config(payload)` 接口供业务层使用。

5. Database Design
------------------

### 5.1 Tables

1. `app_config`
   - `id` INTEGER PRIMARY KEY
   - `key` TEXT UNIQUE
   - `value` TEXT (JSON)
   - `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP

2. `historical_data`
   - `id` INTEGER PRIMARY KEY
   - `symbol` TEXT NOT NULL
   - `interval` TEXT NOT NULL
   - `range` TEXT NOT NULL
   - `adjusted` INTEGER DEFAULT 1
   - `as_of_date` DATE
   - `data` TEXT NOT NULL
   - `fetched_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   - UNIQUE (`symbol`, `interval`, `range`, `adjusted`)

3. `indicator_data`
   - `id` INTEGER PRIMARY KEY
   - `symbol` TEXT NOT NULL
   - `indicator` TEXT NOT NULL
   - `params` TEXT NOT NULL       # JSON 字符串
   - `interval` TEXT NOT NULL
  - `data` TEXT NOT NULL
   - `as_of_date` DATE
   - `fetched_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   - UNIQUE (`symbol`, `indicator`, `interval`, `params`)

4. `recent_quotes`
   - `id` INTEGER PRIMARY KEY
   - `symbol` TEXT UNIQUE NOT NULL
   - `data` TEXT NOT NULL
   - `fetched_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP

### 5.2 Access Layer

- 使用 sqlite3 + 自定义 DAO，或 SQLAlchemy Core/ORM 均可。
- 在 `app/db/models.py` 中封装 CRUD，避免业务层直接编写 SQL。
- 提供迁移脚本（初期可直接执行初始化 SQL）。

6. Services
-----------

### 6.1 Alpha Vantage Client (`services/alphavantage.py`)

- 统一构造 API 请求参数、签名与错误处理。
- 实现限流控制：维护时间戳队列，确保 <= 5 次/分钟（免费额度）。
- 提供方法：
  - `fetch_quote(symbol)`
  - `fetch_overview(symbol)`
  - `fetch_time_series(symbol, interval, outputsize="compact", adjusted=True, range=None)`
  - `fetch_indicator(symbol, indicator, interval, params)`

### 6.2 Cache Service (`services/cache.py`)

- 负责缓存读写策略：
  - `get_quote(symbol)`：优先从 `recent_quotes` 读，过期则调用 API + 更新。
  - `get_historical(symbol, interval, range, adjusted)`：
    - 查询 `historical_data`。
    - 若缺失或需要补全，则调用 Alpha Vantage，写回数据库。
  - `save_historical(...)`、`clear_historical()`
  - `get_indicator(...)`、`save_indicator(...)`
- 返回数据时补充 `source` 字段（cache / fetched）。

### 6.3 AI Service (`services/ai.py`)

- 管理 DeepSeek & Qwen 的配置读取与连接测试。
- 提供占位函数：
  - `test_provider(provider_name)`
  - `generate_insight(symbol, context)`（当前可返回 “未启用” 状态）。

7. API Design
-------------

| Endpoint | Method | Description | Request Params | Response |
|----------|--------|-------------|----------------|----------|
| `/api/quote` | GET | 获取实时概览 | `symbol` | `symbol`, `price`, `change`, `change_percent`, `volume`, `timestamp`, `company_overview`, `source` |
| `/api/history` | GET | 历史行情数据 | `symbol`, `interval`, `range`, `adjusted` | `series`, `as_of_date`, `fetched_at`, `source` |
| `/api/indicator` | GET | 指标数据 | `symbol`, `indicator`, `interval`, 指标参数 | `series`, `as_of_date`, `fetched_at`, `source` |
| `/api/settings` | GET | 获取配置 | - | 合并后的配置 JSON |
| `/api/settings` | POST | 更新配置 | JSON body | 更新后的配置 |
| `/api/settings/test` | POST | 测试数据源/AI 连通性 | JSON body `{ provider: "alphavantage"/"deepseek"/"qwen" }` | 测试结果 |
| `/api/cache/clear_history` | POST | 清空历史数据缓存 | - | 操作状态 |

- 所有返回值采用统一包装：`{ "success": true/false, "data": ..., "error": ... }`。
- 错误处理：调用失败时返回 `success=false`，并附带 `error.code` 和 `error.message`。

8. Frontend Implementation
--------------------------

### 8.1 首页脚本 (`static/js/home.js`)

- 初始化：加载默认配置（范围、主题），请求 `/api/quote` 与 `/api/history`。
- 搜索框监听输入，触发数据重载。
- ECharts：
  - 主图：K 线 / 折线切换。
  - 子图：成交量、技术指标（可多 series）。
  - 响应式适配，支持 legend 控制。
- 指标面板：
  - 复选框控制指标启用。
  - 参数输入变更触发 `debounce` 请求。
- 提示条：统一调用 `showToast(message, type)`。

### 8.2 配置页脚本 (`static/js/settings.js`)

- 页面加载时请求 `/api/settings`，填充表单。
- 保存：提交差异字段到后端，局部刷新状态提示。
- 测试按钮：调用 `/api/settings/test`，展示结果。
- 清空历史数据：弹窗确认后调用 `/api/cache/clear_history`。

### 8.3 样式

- 使用简洁的 CSS（可结合 Tailwind 或自定义），保证布局响应式。
- 提供明暗主题样式变量。

9. Caching & Data Strategy
--------------------------

- **实时行情**：缓存 60 秒，防止超限；若缓存存在且未过期直接返回。
- **历史数据**：任何成功的历史数据请求均写入 `historical_data`；后续相同范围直接命中。对自定义范围，需要判断是否完全覆盖：
  - 若部分覆盖，补齐缺失区间并更新缓存。
  - `history_ttl_days` 到期后执行定期清理任务（可在应用启动时触发一轮清理）。
- **指标**：缓存 300 秒，减少重复计算/请求。

10. Error Handling & Logging
----------------------------

- 统一日志记录：请求 Alpha Vantage 失败、限流、解析异常都写入日志（后续可引入标准 logger 配置）。
- API 返回层面提供友好错误消息，并提示用户操作（例如“稍后重试”、“检查 API Key”）。
- 对关键操作（更新配置、清空缓存）进行审计日志记录（可写入单独表或日志文件）。

11. Testing Strategy
--------------------

- 单元测试：
  - 配置加载与合并逻辑。
  - 缓存命中与过期流程。
  - Alpha Vantage 客户端参数生成、节流逻辑（可通过 mock 时间）。
- 集成测试：
  - `/api/history` 对缓存/补全逻辑的整体行为。
  - `/api/settings` 更新与读取。
- 前端测试：
  - 利用 Jest + jsdom 或 Cypress/Playwright 进行基础 UI 行为验证（后续迭代）。

12. Deployment Considerations
-----------------------------

- 配置通过环境变量覆盖（例如 Flask `FLASK_ENV`、数据库路径、API Key）。
- 提供 `Dockerfile`（后续迭代）以便部署。
- 静态资源可由 Flask 或 CDN 提供，确保缓存策略合理。

13. Future Work Hooks
---------------------

- AI 分析模块：`services/ai.py` 保留 `generate_insight` 接口，供后续在首页或独立页面调用。
- 自选股表结构与 API 预留。
- 计划引入后台任务（如 APScheduler）以定时刷新关键数据。
- 错误监控与性能监控接入（Sentry 等）。

