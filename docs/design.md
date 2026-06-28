# EventWeave 设计文档

> AI-assisted synthetic event streams from scenarios, rules, and timelines.
> Generate event flows, not just fake rows.

## 1. 项目概述

**EventWeave**，中文名 **流织**，是一个 AI 辅助的场景化事件流生成框架。

它用于将自然语言描述、YAML 场景文件、业务规则、实体关系和时间线定义，转化为真实、可控、可复现、可流式输出的模拟事件流。

EventWeave 的核心目标不是生成几行假数据，而是生成具备上下文、时间关系、实体关系和业务逻辑的 **事件流**。

适用场景包括：

* 系统测试
* 产品演示
* 日志平台压测
* 数据管道调试
* Agent 评测
* 安全运营模拟
* 电商订单流模拟
* SaaS 多租户行为模拟
* IoT 设备遥测模拟
* 医院运维业务事件模拟

---

## 2. 项目定位

EventWeave 的定位是：

> 一个 AI 辅助的、场景驱动的、规则感知的、时间感知的合成事件流生成框架。

英文定位：

> EventWeave is an AI-assisted synthetic event stream generator that turns scenarios, rules, and timelines into realistic event flows.

中文定位：

> EventWeave 是一个将场景、规则和时间线编织成真实模拟事件流的开源框架。

---

## 3. 为什么需要 EventWeave

常见 mock data 工具大多解决的是静态数据生成问题。

例如：

* 生成用户
* 生成订单
* 生成手机号
* 生成随机文本
* 生成数据库测试记录

但真实系统中的数据往往不是孤立记录，而是持续发生的事件流。

真实系统有：

* 实体
* 关系
* 状态变化
* 时间顺序
* 延迟
* 重试
* 批量补传
* 乱序到达
* 背景噪声
* 多数据源
* 多租户
* 业务规则
* 语义描述
* ground truth

EventWeave 要解决的问题是：

> 如何从一个场景出发，自动生成一组逻辑一致、时间合理、语义真实、可流式输出的事件数据。

---

## 4. 设计目标

### 4.1 场景驱动

用户通过 YAML 或自然语言描述场景，而不是手写每一条数据。

例如：

```text
模拟一个电商退款场景：
用户下单、支付、申请退款，客服创建工单，部分退款失败。
要求每秒 100 条订单事件，10% 触发退款，2% 产生客服投诉。
```

EventWeave 应该能够将这个场景转化为：

* 实体模型
* 事件模型
* 时间线
* 规则约束
* 语义任务
* runtime plan
* 输出数据流

---

### 4.2 规则感知

生成的数据必须符合业务逻辑。

例如：

* 订单必须先创建再支付
* 退款不能早于支付
* 退款金额不能大于支付金额
* 工单必须关联已存在的订单
* 告警必须关联已存在的资产
* 设备离线后不能继续产生正常心跳
* 用户不存在时不能产生登录行为

EventWeave 不追求“随机”，而追求“合理”。

---

### 4.3 时间感知

EventWeave 不只是随机修改时间戳，而是提供完整的时间模型。

支持：

* 实时事件流
* 延迟到达
* 乱序到达
* 批量回放
* 状态更新
* 周期事件
* 突发流量
* 背景噪声
* 设备时钟偏移

---

### 4.4 多源模拟

EventWeave 支持模拟多个 source。

例如：

```text
order-service
payment-service
ticket-service
firewall-001
edr-001
iot-gateway-001
hospital-terminal-001
```

每个 source 可以独立配置：

* 类型
* 角色
* QPS
* burst QPS
* jitter
* 输出目标
* 时间策略
* 语义注入比例

---

### 4.5 AI 辅助，但不依赖 AI

EventWeave 是 **AI-assisted**，不是 **AI-dependent**。

AI 适合做：

* 场景草稿生成
* 语义文本生成
* 工单描述生成
* 告警说明生成
* 用户评论生成
* 退款原因生成
* 规则建议
* Pack 草稿生成
* Agent 评测样本生成

AI 不应该直接进入高 QPS 运行时热路径。

运行时应该是：

* 可复现
* 可控制
* 可压测
* 可调试
* 可离线运行

---

### 4.6 可复现

同一个场景、同一个 seed，应生成一致的数据计划。

例如：

```bash
eventweave compile examples/ecommerce/refund.yaml --seed 20260628
```

这样便于：

* 测试回归
* 规则验证
* 演示复现
* Agent 评测
* bug 复盘

---

### 4.7 可扩展

EventWeave 通过 Pack 机制支持不同业务领域。

内置推荐 Pack：

```text
common       通用实体、用户、组织、设备、位置
ecommerce    商品、订单、支付、退款、客服
security     资产、告警、日志、IOC、事件、工单
saas         租户、用户、订阅、API、审计
iot          设备、网关、传感器、遥测
devops       服务、实例、部署、日志、指标、告警
hospital     终端、排队、支付、故障、运维工单
```

---

## 5. 非目标

EventWeave 不是：

1. 普通 Faker 封装。
2. 单纯数据库 seeding 工具。
3. 单纯压测工具。
4. 单纯 LLM 文本生成器。
5. 单纯日志回放工具。
6. 真实攻击模拟平台。
7. 生产数据同步平台。

EventWeave 的核心是：

> 生成具备场景、规则、时间线和语义上下文的合成事件流。

---

## 6. 核心概念

### 6.1 Scenario

场景，描述“发生了什么”。

例如：

* 电商退款
* 用户异常登录
* 医院自助机支付失败
* IoT 设备离线后批量补传
* SaaS 租户 API 调用超限
* 安全设备触发横向移动告警

---

### 6.2 Entity

实体，描述场景中的对象。

例如：

* user
* order
* product
* payment
* ticket
* device
* host
* alert
* tenant
* service
* patient
* terminal

---

### 6.3 Relation

实体关系，描述实体之间的关联。

例如：

```text
user -> order
order -> payment
order -> refund
ticket -> order
alert -> asset
device -> gateway
tenant -> user
service -> instance
```

---

### 6.4 Event

事件，描述某个时间点发生的行为或状态变化。

例如：

```text
order.created
order.paid
refund.requested
ticket.created
user.login
device.offline
alert.triggered
api.called
service.deployed
```

---

### 6.5 Timeline

时间线，描述事件之间的先后关系、间隔、概率和触发条件。

例如：

```yaml
timeline:
  - at: "00:00:00"
    event: order.created

  - after: order.created
    delay: "1m..5m"
    event: order.paid

  - after: order.paid
    delay: "5m..20m"
    probability: 0.2
    event: refund.requested
```

---

### 6.6 Rule

规则，保证数据逻辑正确。

规则可以分为：

* 字段规则
* 状态规则
* 时间规则
* 实体引用规则
* 业务约束规则
* Pack 专属规则

---

### 6.7 Semantic Pool

语义素材池，用于保存 AI 或模板生成的文本素材。

例如：

* 退款原因
* 工单描述
* 告警说明
* 用户评论
* 设备故障描述
* 处置建议
* 报告摘要
* Agent 评测提示

语义素材池中的内容经过校验后，由 runtime 注入事件流。

---

### 6.8 Source

模拟数据源实例。

例如：

```text
order-service
payment-service
ticket-service
firewall-001
edr-001
iot-gateway-001
```

每个 source 可以独立配置速率、输出和时间策略。

---

### 6.9 Sink

输出目标。

支持：

* stdout
* JSONL
* CSV
* Parquet
* HTTP
* Webhook
* Kafka
* Redis Stream
* Syslog
* ClickHouse
* Elasticsearch
* OpenSearch
* PostgreSQL

---

## 7. 总体架构

```text
┌──────────────────────────────────────────────────────────┐
│                      EventWeave                           │
│      AI-assisted synthetic event stream generator          │
└──────────────────────────────────────────────────────────┘

┌──────────────────────┐
│ Natural Language      │
│ Scenario Description  │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ AI Scenario Builder   │
│ - 场景草稿生成         │
│ - YAML 生成            │
│ - 规则建议             │
│ - Pack 草稿生成        │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Scenario DSL          │
│ YAML / JSON            │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Scenario Compiler     │
│ Python                │
│ - schema validation   │
│ - entity graph        │
│ - rule engine         │
│ - timeline planner    │
│ - semantic tasks      │
└──────────┬───────────┘
           │
           ├─────────────────────────────┐
           │                             │
           ▼                             ▼
┌──────────────────────┐       ┌──────────────────────┐
│ Runtime Plan          │       │ AI Semantic Sidecar   │
│ - entities            │       │ - descriptions        │
│ - relations           │       │ - reasons             │
│ - event plan          │       │ - summaries           │
│ - source config       │       │ - conversations       │
│ - ground truth        │       │ - suggestions         │
└──────────┬───────────┘       └──────────┬───────────┘
           │                              │
           │                              ▼
           │                    ┌──────────────────────┐
           │                    │ Semantic Pool         │
           │                    │ validated text assets │
           │                    └──────────┬───────────┘
           │                              │
           ▼                              ▼
┌──────────────────────────────────────────────────────────┐
│ Event Runtime                                             │
│ - multi-source simulation                                 │
│ - QPS / burst / jitter                                    │
│ - late arrival                                            │
│ - out-of-order events                                     │
│ - batch replay                                            │
│ - semantic injection                                      │
│ - metrics                                                 │
└──────────┬───────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────┐
│ Sinks & Evaluation                                        │
│ JSONL / HTTP / Kafka / Syslog / ClickHouse / Elastic       │
│ Ground Truth / Agent Evaluation / Quality Report           │
└──────────────────────────────────────────────────────────┘
```

---

## 8. 技术选型

### 8.1 Python 控制面

Python 负责：

* Scenario DSL 解析
* Schema 校验
* Rule Engine
* Entity Graph 构建
* Timeline Planner
* LLM Sidecar
* Semantic Pool
* 静态导出
* 本地低 QPS runtime

推荐依赖：

```text
pydantic
pyyaml
jinja2
orjson
faker
mimesis
factory_boy
networkx
typer
rich
httpx
```

---

### 8.2 Go 高性能运行时

Go 负责：

* 多 source 运行
* 高 QPS 输出
* 并发调度
* token bucket 限速
* burst 控制
* sink 写入
* backpressure
* metrics
* health check

Go runtime 适合后续作为独立二进制发布。

---

### 8.3 Rust 暂不作为主语言

Rust 可作为未来扩展：

* PCAP 生成
* 二进制协议模拟
* 极限性能流量生成
* WASM 插件
* 嵌入式边缘模拟器

第一阶段不建议引入 Rust，以降低开发复杂度。

---

## 9. 推荐仓库结构

```text
eventweave/
├── README.md
├── LICENSE
├── pyproject.toml
├── docs/
│   ├── design.md
│   ├── scenario-dsl.md
│   ├── pack-spec.md
│   ├── runtime-plan.md
│   ├── time-policy.md
│   └── agent-evaluation.md
│
├── eventweave/
│   ├── core/
│   │   ├── entity/
│   │   ├── event/
│   │   ├── relation/
│   │   ├── scenario/
│   │   ├── timeline/
│   │   ├── rules/
│   │   ├── semantic/
│   │   └── runtime_plan/
│   │
│   ├── compiler/
│   │   ├── loader.py
│   │   ├── validator.py
│   │   ├── planner.py
│   │   ├── entity_graph_builder.py
│   │   ├── event_plan_builder.py
│   │   └── semantic_task_builder.py
│   │
│   ├── ai/
│   │   ├── scenario_builder.py
│   │   ├── semantic_sidecar.py
│   │   ├── rule_critic.py
│   │   ├── pack_generator.py
│   │   ├── prompts/
│   │   └── providers/
│   │
│   ├── semantic/
│   │   ├── pool.py
│   │   ├── cache.py
│   │   └── validators.py
│   │
│   ├── exporters/
│   │   ├── jsonl/
│   │   ├── csv/
│   │   ├── parquet/
│   │   ├── http/
│   │   ├── kafka/
│   │   ├── clickhouse/
│   │   └── elastic/
│   │
│   ├── runtime/
│   │   └── local_python/
│   │
│   ├── evaluation/
│   │   ├── ground_truth.py
│   │   ├── agent_eval.py
│   │   └── report.py
│   │
│   └── cli/
│       └── main.py
│
├── packs/
│   ├── common/
│   ├── ecommerce/
│   ├── security/
│   ├── saas/
│   ├── iot/
│   ├── devops/
│   └── hospital/
│
├── runtime-go/
│   ├── cmd/
│   │   └── eventweave-runtime/
│   ├── internal/
│   │   ├── controller/
│   │   ├── source/
│   │   ├── scheduler/
│   │   ├── rate/
│   │   ├── encoder/
│   │   ├── sink/
│   │   ├── metrics/
│   │   └── config/
│   └── go.mod
│
├── examples/
│   ├── ecommerce/
│   ├── security/
│   ├── saas/
│   ├── iot/
│   ├── devops/
│   └── hospital/
│
└── tests/
```

---

## 10. 核心数据模型

### 10.1 Entity

```json
{
  "id": "user_001",
  "type": "user",
  "domain": "common",
  "attributes": {
    "name": "Zhang San",
    "email": "zhangsan@example.com",
    "department": "finance"
  },
  "tags": ["demo", "vip"],
  "created_at": "2026-06-28T10:00:00Z"
}
```

---

### 10.2 Relation

```json
{
  "from": "user_001",
  "to": "order_001",
  "type": "created",
  "attributes": {
    "confidence": 1.0
  }
}
```

---

### 10.3 Event

```json
{
  "event_id": "evt_001",
  "scenario_id": "ecommerce_refund_flow",
  "source_id": "order-service",
  "event_type": "order.created",
  "event_time": "2026-06-28T10:00:01Z",
  "generated_at": "2026-06-28T10:00:01Z",
  "emit_time": "2026-06-28T10:00:02Z",
  "ingest_time": null,
  "entity_refs": {
    "user": "user_001",
    "order": "order_001"
  },
  "attributes": {
    "order_amount": 299.0,
    "currency": "CNY",
    "status": "created"
  },
  "semantic_refs": [],
  "labels": ["normal", "scenario:ecommerce_refund_flow"],
  "ground_truth": {
    "is_key_event": true,
    "stage": "order_create"
  }
}
```

---

### 10.4 Source

```json
{
  "id": "order-service",
  "type": "service",
  "domain": "ecommerce",
  "role": "order_service",
  "rate": {
    "base_qps": 100,
    "burst_qps": 1000,
    "jitter": 0.15
  },
  "time_policy": {
    "mode": "realtime",
    "late_arrival_ratio": 0.02
  },
  "outputs": [
    {
      "type": "jsonl",
      "path": "./out/orders.jsonl"
    }
  ]
}
```

---

### 10.5 Semantic Asset

```json
{
  "id": "sem_001",
  "domain": "ecommerce",
  "type": "refund.reason",
  "text": "The customer reported that the product did not match the description and requested a refund.",
  "valid_for": ["refund.requested", "ticket.created"],
  "variables": ["user", "order", "product"],
  "created_by": "llm",
  "quality_score": 0.92,
  "review_status": "approved"
}
```

---

## 11. 时间模型

EventWeave 使用显式 Time Policy，而不是简单随机时间戳。

### 11.1 时间字段

```text
event_time       事件真实发生时间
generated_at     EventWeave 生成事件的时间
emit_time        runtime 发出事件的时间
ingest_time      下游系统接收事件的时间
modified_at      业务实体被修改的时间
delay_ms         模拟传输延迟
clock_skew       模拟源设备时钟偏移
```

---

### 11.2 时间行为

支持：

```text
realtime          实时流
delayed           延迟到达
out_of_order      乱序到达
batch_replay      批量回放
state_update      状态更新
scheduled         定时事件
burst             突发流量
background_noise  背景噪声
```

---

### 11.3 Time Policy 示例

```yaml
time_policy:
  event_time:
    mode: scenario_relative
    jitter: "0s..3s"

  emit_time:
    mode: realtime
    delay_distribution:
      type: lognormal
      min: "100ms"
      p95: "3s"
      max: "2m"

  late_arrival:
    enabled: true
    ratio: 0.05
    delay_range: "1m..30m"

  out_of_order:
    enabled: true
    ratio: 0.02
    max_skew: "5m"

  batch_replay:
    enabled: false
```

---

## 12. AI 辅助能力设计

### 12.1 AI Scenario Builder

用户可以用自然语言描述场景，由 AI 生成场景草稿。

输入：

```text
帮我模拟一个医院自助机故障场景：
自助机支付超时，患者重复支付失败，最终生成运维工单。
要求包含终端心跳、支付请求、支付失败、用户投诉、工单创建。
```

输出：

* entities
* sources
* timeline
* rules
* semantic tasks
* runtime plan 草稿

---

### 12.2 AI Semantic Sidecar

AI 生成语义素材，不进入 runtime 热路径。

适合生成：

* 退款原因
* 告警描述
* 工单内容
* 用户反馈
* 设备故障说明
* 处置建议
* 事件摘要
* 客服对话
* Agent 评测问题

流程：

```text
Scenario
  -> Semantic Tasks
  -> AI Semantic Sidecar
  -> Validation
  -> Semantic Pool
  -> Runtime Injection
```

---

### 12.3 AI Rule Critic

AI 帮用户检查场景是否存在逻辑漏洞。

例如：

```text
refund.requested 可能早于 order.paid，建议增加规则 order_must_be_paid_before_refund。
```

或者：

```text
当前安全场景缺少背景噪声，生成数据过于干净，不利于测试告警关联能力。
```

---

### 12.4 AI Pack Generator

AI 根据行业描述生成 Pack 草稿。

例如：

```text
生成一个 SaaS 多租户 Pack，包括租户、用户、订阅、API 调用、审计日志、用量超限事件。
```

输出：

```text
entities/
events/
rules/
semantic/
examples/
```

---

### 12.5 AI Agent Evaluation

EventWeave 可以生成带 ground truth 的事件流，用于评测 AI Agent。

流程：

```text
生成场景
输出事件流
保存 ground truth
让 Agent 分析
比对 Agent 输出
生成评测报告
```

适合评测：

* 告警研判 Agent
* 运维分析 Agent
* 数据分析 Agent
* 客服工单 Agent
* 异常检测 Agent
* 业务流程分析 Agent

---

## 13. Scenario DSL 示例

### 13.1 电商退款场景

```yaml
id: ecommerce_refund_flow
name: E-commerce refund flow
domain: ecommerce
duration: 30m
seed: 20260628

entities:
  customer:
    count: 100

  product:
    count: 20

  order:
    count: 200

sources:
  - id: order-service
    type: service
    role: order_service
    rate:
      base_qps: 100
      burst_qps: 800
      jitter: 0.1
    outputs:
      - type: jsonl
        path: ./out/orders.jsonl

  - id: ticket-service
    type: service
    role: ticket_service
    rate:
      base_qps: 20
      burst_qps: 100
      jitter: 0.2
    outputs:
      - type: jsonl
        path: ./out/tickets.jsonl

timeline:
  - at: "00:00:00"
    event: order.created
    source: order-service

  - after: order.created
    delay: "1m..5m"
    event: order.paid
    source: order-service

  - after: order.paid
    delay: "5m..20m"
    probability: 0.2
    event: refund.requested
    source: order-service
    semantic:
      type: refund.reason
      inject: true

  - after: refund.requested
    delay: "10s..1m"
    event: ticket.created
    source: ticket-service
    semantic:
      type: customer_service.description
      inject: true

rules:
  - order_must_be_paid_before_refund
  - refund_amount_must_not_exceed_payment_amount
  - ticket_must_reference_existing_order
```

---

### 13.2 安全运营场景

```yaml
id: security_lateral_movement
name: Lateral movement alert scenario
domain: security
duration: 45m
seed: 20260628

entities:
  user:
    type: employee
    count: 50

  host:
    type: endpoint
    count: 100

  ip:
    type: ip_address
    count: 150

sources:
  - id: edr-001
    type: security_device
    role: edr
    rate:
      base_qps: 300
      burst_qps: 3000
      jitter: 0.15
    outputs:
      - type: kafka
        topic: mock.security.edr

  - id: firewall-001
    type: security_device
    role: firewall
    rate:
      base_qps: 1000
      burst_qps: 8000
      jitter: 0.2
    outputs:
      - type: syslog
        protocol: udp
        address: 127.0.0.1:514

timeline:
  - at: "00:01:00"
    event: user.login.failed
    source: edr-001

  - at: "00:03:00"
    event: user.login.success
    source: edr-001

  - at: "00:10:00"
    event: process.suspicious_started
    source: edr-001
    semantic:
      type: alert.description
      inject: true

  - at: "00:12:00"
    event: network.lateral_connection
    source: firewall-001

  - at: "00:15:00"
    event: alert.triggered
    source: edr-001
    semantic:
      type: alert.explanation
      inject: true

rules:
  - login_success_after_failed_attempts
  - alert_must_reference_existing_host
  - lateral_connection_must_reference_two_hosts
```

---

## 14. Pack 机制

Pack 是 EventWeave 的领域扩展机制。

每个 Pack 可以包含：

```text
实体定义
事件定义
规则
状态机
字段 schema
语义模板
AI prompts
编码器
示例场景
测试用例
```

Pack 结构示例：

```text
packs/ecommerce/
├── pack.yaml
├── entities/
│   ├── customer.yaml
│   ├── product.yaml
│   └── order.yaml
├── events/
│   ├── order.yaml
│   ├── payment.yaml
│   └── refund.yaml
├── rules/
│   └── refund_rules.py
├── semantic/
│   ├── refund_reason.yaml
│   └── ticket_description.yaml
├── prompts/
│   └── scenario_builder.md
├── encoders/
│   └── json.py
└── examples/
    └── refund_flow.yaml
```

---

## 15. Runtime 设计

### 15.1 Local Runtime

Python Local Runtime 用于：

* 开发调试
* 小规模演示
* 静态导出
* 单机低 QPS 事件流

---

### 15.2 High-performance Runtime

Go Runtime 用于：

* 高 QPS 输出
* 多 source 模拟
* 长时间运行
* Kafka / HTTP / Syslog 输出
* 压测场景
* 性能指标采集

核心模块：

```text
controller       运行控制器
source           数据源实例
scheduler        时间线调度器
rate             QPS / burst / jitter 控制
encoder          格式转换
sink             输出目标
metrics          指标监控
health           健康检查
config           配置加载
```

---

## 16. 输出链路

EventWeave 输出链路采用：

```text
Canonical Event
  -> Encoder
  -> Sink
```

示例：

```text
Canonical Event -> JSON Encoder -> Kafka Sink
Canonical Event -> ECS Encoder -> Elasticsearch Sink
Canonical Event -> Syslog Encoder -> UDP Sink
Canonical Event -> ClickHouse Encoder -> ClickHouse Sink
```

---

## 17. CLI 设计

### 17.1 编译场景

```bash
eventweave compile examples/ecommerce/refund.yaml -o dist/refund
```

输出：

```text
dist/refund/
├── scenario.json
├── entities.json
├── relations.json
├── event_plan.jsonl
├── sources.json
├── semantic_tasks.json
├── runtime_plan.json
└── ground_truth.json
```

---

### 17.2 生成语义素材

```bash
eventweave semantic generate dist/refund
```

---

### 17.3 本地运行

```bash
eventweave run dist/refund --runtime local
```

---

### 17.4 高性能运行

```bash
eventweave-runtime run dist/refund/runtime_plan.json
```

---

### 17.5 静态导出

```bash
eventweave export dist/refund --format jsonl --output ./out
```

---

### 17.6 时间加速

```bash
eventweave-runtime run dist/security/runtime_plan.json --speed 10x
```

---

### 17.7 QPS 缩放

```bash
eventweave-runtime run dist/security/runtime_plan.json --scale 5
```

---

## 18. Agent Evaluation 设计

EventWeave 可以作为 Agent 评测数据生成器。

### 18.1 Ground Truth

每个场景可以生成 ground truth：

```json
{
  "scenario_id": "security_lateral_movement",
  "expected_findings": [
    {
      "type": "suspicious_login",
      "entities": ["user_001", "host_001"],
      "stage": "initial_access"
    },
    {
      "type": "lateral_movement",
      "entities": ["host_001", "host_002"],
      "stage": "lateral_movement"
    }
  ],
  "expected_summary": "The scenario simulates suspicious login followed by lateral movement and EDR alert generation."
}
```

---

### 18.2 Evaluation Flow

```text
EventWeave 生成事件流
Agent 分析事件流
Agent 输出结论
Evaluation Harness 读取 ground truth
计算准确率、召回率、阶段识别、实体识别、解释质量
生成评测报告
```

---

### 18.3 评测指标

```text
关键事件识别率
实体识别准确率
时间线还原准确率
根因判断准确率
误报率
漏报率
处置建议质量
解释一致性
```

---

## 19. 质量评估

### 19.1 结构质量

```text
Schema 通过率
字段完整率
枚举合法率
实体引用合法率
状态流转合法率
```

---

### 19.2 场景质量

```text
关键事件覆盖率
时间线合理性
实体关系一致性
背景噪声比例
异常事件比例
ground truth 完整性
```

---

### 19.3 语义质量

```text
文本可读性
业务一致性
字段引用正确性
重复率
敏感内容检查
人工审核状态
```

---

### 19.4 性能质量

```text
实际 QPS
P50 / P95 / P99 延迟
sink 写入成功率
丢弃事件数
backpressure 次数
CPU 占用
内存占用
```

---

## 20. 安全设计

### 20.1 LLM 安全

```text
不默认上传真实敏感数据
支持本地模型
支持 Prompt 审计
支持 Output 审计
支持敏感词过滤
支持语义素材人工审核
```

---

### 20.2 Runtime 安全

```text
限制 HTTP sink 目标地址
避免 SSRF
限制文件写入路径
限制命令执行能力
默认不启用危险协议
支持 dry-run
```

---

### 20.3 数据安全

```text
默认生成虚假数据
示例数据不包含真实个人信息
不内置真实密钥
不内置真实身份证
不内置真实手机号
支持脱敏规则
```

---

## 21. Roadmap

### v0.1：Scenario Compiler MVP

目标：先把场景编译和静态数据生成跑通。

范围：

```text
Scenario DSL
Entity Model
Event Model
Timeline Planner
Rule Engine
JSONL Exporter
CLI compile / export
ecommerce 示例
security 示例
```

验收：

```text
可以编译一个电商退款场景
可以编译一个安全告警场景
可以生成 entities.json
可以生成 event_plan.jsonl
可以生成 ground_truth.json
可以导出 JSONL
```

---

### v0.2：AI Semantic Sidecar

目标：实现 AI 旁路语义生成。

范围：

```text
Semantic Task
Prompt Template
LLM Provider 抽象
Semantic Pool
语义素材缓存
Schema 校验
人工审核状态
```

验收：

```text
可以为退款原因、工单内容、告警说明生成语义素材
LLM 不进入 runtime 热路径
语义素材可缓存、复用、审计
```

---

### v0.3：Python Local Runtime

目标：实现低 QPS 流式运行。

范围：

```text
source 实例
rate policy
time policy
semantic injection
stdout sink
file sink
HTTP sink
delayed arrival
out-of-order events
batch replay
```

验收：

```text
可以模拟多个 source
可以按 QPS 输出事件
可以注入语义素材
可以模拟延迟到达和乱序到达
```

---

### v0.4：Go Runtime

目标：实现高性能多实例运行。

范围：

```text
Go runtime
scheduler
token bucket
worker pool
Kafka sink
Syslog sink
HTTP sink
Prometheus metrics
pause / resume / stop
```

验收：

```text
单机可稳定高 QPS 输出
支持多 source 独立限速
支持暂停、恢复、停止
支持 metrics
```

---

### v0.5：Pack Ecosystem

目标：完善领域扩展能力。

范围：

```text
pack.yaml 规范
pack loader
domain rule registry
domain encoder registry
更多示例场景
贡献指南
```

内置 Pack：

```text
common
ecommerce
security
saas
iot
devops
hospital
```

---

### v0.6：Agent Evaluation Harness

目标：支持 Agent 评测。

范围：

```text
ground truth schema
agent output schema
评测指标
评测报告
安全场景评测
运维场景评测
电商场景评测
```

验收：

```text
可以生成带 ground truth 的事件流
可以读取 Agent 输出
可以生成评测报告
```

---

## 22. GitHub README 首页建议

```markdown
# EventWeave

> AI-assisted synthetic event streams from scenarios, rules, and timelines.

Generate event flows, not just fake rows.

EventWeave turns scenario files and natural language descriptions into realistic, rule-aware, time-aware synthetic event streams.

## What it can generate

- application logs
- API events
- audit records
- security telemetry
- user behavior
- order flows
- device telemetry
- workflow events
- operational alerts
- agent evaluation datasets

## Why EventWeave?

Most mock data tools generate static records.

EventWeave generates coherent event flows with:

- entities
- relationships
- timelines
- state changes
- background noise
- delayed events
- out-of-order events
- semantic context
- ground truth
```

---

## 23. 推荐 GitHub Topics

```text
synthetic-data
mock-data
event-stream
data-generator
scenario-testing
streaming-data
test-data-generator
simulation
ai-assisted
agent-evaluation
kafka
observability
security-testing
```

---

## 24. License 建议

推荐使用：

```text
Apache-2.0
```

原因：

* 对企业友好
* 适合基础设施类开源项目
* 方便后续商业化或企业内部使用
* 比 MIT 多了专利授权条款

---

## 25. 总结

EventWeave 的核心思想是：

```text
场景定义业务意图
实体图保证关系真实
规则引擎保证逻辑正确
时间模型保证流式可信
AI 旁路增强语义
Runtime 负责高并发输出
Pack 机制承载领域扩展
Ground Truth 支持 Agent 评测
```

EventWeave 要做的不是普通 mock data generator，而是：

> 一个可以将场景编织成事件流的 AI 辅助模拟框架。

最终目标：

```text
Define the scenario.
Weave the entities.
Validate the rules.
Plan the timeline.
Generate the semantics.
Stream the events.
Evaluate the agents.
```

Generate event flows, not just fake rows.
