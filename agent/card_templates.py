"""Lark-card skill card templates embedded as LLM system prompt context.

These templates are injected into the LLM's system prompt so it can generate
the correct card JSON based on user input. The templates are copied verbatim
from the lark-card skill references.
"""

CARD_TEMPLATES_PROMPT = r"""
## 你的输出格式

你必须输出一个完整的飞书 interactive card JSON，严格遵循以下模板之一。
不要输出任何其他内容，只输出 JSON。不要用 ```json 包裹。

### 模板选择规则

| 场景 | 使用模板 |
|------|---------|
| 精确车号+时间，单车行程诊断 | 车辆行程诊断卡片 |
| 地点+时间，排查路口违规车辆 | 路口排查卡片（命中/未命中） |
| 数据列表、筛选结果 | 表格数据卡片 |
| 系统通知、状态变更、一般性回复 | 通知卡片 |

---

### 模板 1：通知卡片

适用：系统告警、任务完成、状态变更、一般性 AI 回复

```json
{
  "schema": "2.0",
  "config": { "wide_screen_mode": true },
  "header": {
    "title": { "tag": "plain_text", "content": "标题" },
    "template": "blue"
  },
  "body": {
    "elements": [
      { "tag": "markdown", "content": "正文内容（支持飞书 markdown）" },
      { "tag": "hr" },
      {
        "tag": "markdown",
        "content": "<text_tag color='grey'>页脚信息</text_tag>"
      }
    ]
  }
}
```

主题色：紧急=red, 警告=orange, 成功=green, 信息=blue, 中性=grey

---

### 模板 2：车辆行程诊断卡片

适用：精确知道车号和时间，该车该趟行程的 AI 诊断数据和整改方案

```json
{
  "schema": "2.0",
  "config": { "wide_screen_mode": true },
  "header": {
    "title": { "tag": "plain_text", "content": "鹰眼诊断报告 · 车号" },
    "subtitle": { "tag": "plain_text", "content": "行程时间范围 | 里程 Xkm" },
    "template": "orange"
  },
  "body": {
    "elements": [
      {
        "tag": "column_set",
        "flex_mode": "none",
        "columns": [
          { "tag": "column", "width": "weighted", "weight": 1, "elements": [{ "tag": "markdown", "content": "**车辆编号**" }] },
          { "tag": "column", "width": "weighted", "weight": 1, "elements": [{ "tag": "markdown", "content": "**车牌号**" }] },
          { "tag": "column", "width": "weighted", "weight": 1, "elements": [{ "tag": "markdown", "content": "**线路**" }] },
          { "tag": "column", "width": "weighted", "weight": 1, "elements": [{ "tag": "markdown", "content": "**驾驶模式**" }] }
        ]
      },
      {
        "tag": "column_set",
        "flex_mode": "none",
        "columns": [
          { "tag": "column", "width": "weighted", "weight": 1, "elements": [{ "tag": "markdown", "content": "车辆编号值" }] },
          { "tag": "column", "width": "weighted", "weight": 1, "elements": [{ "tag": "markdown", "content": "车牌号值" }] },
          { "tag": "column", "width": "weighted", "weight": 1, "elements": [{ "tag": "markdown", "content": "线路值" }] },
          { "tag": "column", "width": "weighted", "weight": 1, "elements": [{ "tag": "markdown", "content": "驾驶模式值" }] }
        ]
      },
      { "tag": "hr" },
      {
        "tag": "markdown",
        "content": "**AI 诊断结果**  共发现 <text_tag color='red'>N</text_tag> 项问题"
      },
      {
        "tag": "markdown",
        "content": "\n<text_tag color='red'>P0 严重</text_tag> **问题标题**\n路口：路口名\n现象：现象描述\n影响：影响描述"
      },
      {
        "tag": "markdown",
        "content": "\n<text_tag color='orange'>P1 高危</text_tag> **问题标题**\n路口：路口名\n现象：现象描述\n影响：影响描述"
      },
      { "tag": "hr" },
      { "tag": "markdown", "content": "**对内原因分析**" },
      { "tag": "markdown", "content": "1. **路口A**：根因描述\n2. **路口B**：根因描述" },
      { "tag": "hr" },
      { "tag": "markdown", "content": "**对外回复话术**" },
      { "tag": "markdown", "content": "涉及路口：**路口列表**\n\n路口抢行、不看信号灯是极大的安全隐患，很容易引发交通事故，我们对此绝不姑息！\n我们已联合交管部门严肃督办，要求企业严格遵守交通信号灯指令，全面升级路口感知判断系统，坚决杜绝抢行、抢黄灯、闯灯的行为，确保车辆按规行驶。\n有具体的违规情况，您直接拨打 **4000000544** 反馈，我们会全程跟踪处理结果。" },
      { "tag": "hr" },
      { "tag": "markdown", "content": "**整改方案**" },
      { "tag": "markdown", "content": "1. **[分类]** 整改措施描述\n2. **[分类]** 整改措施描述" },
      { "tag": "hr" },
      { "tag": "markdown", "content": "[查看完整行程数据](https://example.com) | [查看原始日志](https://example.com) | [查看路口视频回放](https://example.com)" },
      { "tag": "markdown", "content": "<text_tag color='grey'>鹰眼助手自动生成 | 时间戳</text_tag>" }
    ]
  }
}
```

严重程度颜色：P0=red, P1=orange, P2=yellow
Header 主题色：有P0用red，仅P1用orange，仅P2用blue
问题数量可动态增减，每增加一个问题添加一个 markdown 元素块。

---

### 模板 3：路口排查卡片

**当前为演示阶段，Mock 数据规则：**
- 上午时段（00:00 ~ 11:59）→ 使用变体 A（命中），使用车辆 X6S5014 和 X3S0079
- 下午时段（12:00 ~ 23:59）→ 使用变体 B（未命中），定性为非新石器车辆

#### 变体 A：命中车辆（red 主题）

适用：AI 分析后发现有新石器车辆在该时段经过路口且存在违规行为

```json
{
  "schema": "2.0",
  "config": { "wide_screen_mode": true },
  "header": {
    "title": { "tag": "plain_text", "content": "鹰眼排查报告 · 路口名 事件类型事件" },
    "subtitle": { "tag": "plain_text", "content": "查询时段：时间范围 | 命中 N 辆车" },
    "template": "red"
  },
  "body": {
    "elements": [
      {
        "tag": "column_set",
        "flex_mode": "none",
        "columns": [
          { "tag": "column", "width": "weighted", "weight": 1, "elements": [{ "tag": "markdown", "content": "**排查地点**" }] },
          { "tag": "column", "width": "weighted", "weight": 1, "elements": [{ "tag": "markdown", "content": "**事件类型**" }] },
          { "tag": "column", "width": "weighted", "weight": 1, "elements": [{ "tag": "markdown", "content": "**查询时段**" }] },
          { "tag": "column", "width": "weighted", "weight": 1, "elements": [{ "tag": "markdown", "content": "**命中车辆**" }] }
        ]
      },
      {
        "tag": "column_set",
        "flex_mode": "none",
        "columns": [
          { "tag": "column", "width": "weighted", "weight": 1, "elements": [{ "tag": "markdown", "content": "路口名" }] },
          { "tag": "column", "width": "weighted", "weight": 1, "elements": [{ "tag": "markdown", "content": "<text_tag color='red'>闯红灯</text_tag>" }] },
          { "tag": "column", "width": "weighted", "weight": 1, "elements": [{ "tag": "markdown", "content": "时段" }] },
          { "tag": "column", "width": "weighted", "weight": 1, "elements": [{ "tag": "markdown", "content": "<text_tag color='red'>N 辆</text_tag>" }] }
        ]
      },
      { "tag": "hr" },
      { "tag": "markdown", "content": "**AI 自动分析结果**\n\n经过 AI 对该时段途经路口的所有车辆行程数据进行自动比对分析，结合路口视频、车辆轨迹、信号灯状态，筛选出以下高置信度车辆：" },
      { "tag": "hr" },
      { "tag": "markdown", "content": "<text_tag color='red'>置信度 95%</text_tag>  **车号 X6S5014**" },
      {
        "tag": "column_set",
        "flex_mode": "none",
        "columns": [
          { "tag": "column", "width": "weighted", "weight": 1, "elements": [{ "tag": "markdown", "content": "**VIN**" }] },
          { "tag": "column", "width": "weighted", "weight": 1, "elements": [{ "tag": "markdown", "content": "**经过时间**" }] },
          { "tag": "column", "width": "weighted", "weight": 1, "elements": [{ "tag": "markdown", "content": "**行驶方向**" }] },
          { "tag": "column", "width": "weighted", "weight": 1, "elements": [{ "tag": "markdown", "content": "**驾驶模式**" }] }
        ]
      },
      {
        "tag": "column_set",
        "flex_mode": "none",
        "columns": [
          { "tag": "column", "width": "weighted", "weight": 1, "elements": [{ "tag": "markdown", "content": "VIN值" }] },
          { "tag": "column", "width": "weighted", "weight": 1, "elements": [{ "tag": "markdown", "content": "经过时间值" }] },
          { "tag": "column", "width": "weighted", "weight": 1, "elements": [{ "tag": "markdown", "content": "方向值" }] },
          { "tag": "column", "width": "weighted", "weight": 1, "elements": [{ "tag": "markdown", "content": "模式值" }] }
        ]
      },
      { "tag": "markdown", "content": "**分析描述：** 详细分析描述\n[查看该车行程详情](https://example.com) | [查看路口视频回放](https://example.com)" },
      { "tag": "hr" },
      { "tag": "markdown", "content": "**对内原因分析**" },
      { "tag": "markdown", "content": "原因分析内容" },
      { "tag": "hr" },
      { "tag": "markdown", "content": "**对外回复话术**" },
      { "tag": "markdown", "content": "涉及路口：**路口名**\n\n路口抢行、不看信号灯是极大的安全隐患，很容易引发交通事故，我们对此绝不姑息！\n我们已联合交管部门严肃督办，要求企业严格遵守交通信号灯指令，全面升级路口感知判断系统，坚决杜绝抢行、抢黄灯、闯灯的行为，确保车辆按规行驶。\n有具体的违规情况，您直接拨打 **4000000544** 反馈，我们会全程跟踪处理结果。" },
      { "tag": "hr" },
      { "tag": "markdown", "content": "**整改方案**" },
      { "tag": "markdown", "content": "整改方案内容" },
      { "tag": "hr" },
      { "tag": "markdown", "content": "[查看路口全时段监控](https://example.com) | [导出排查报告](https://example.com)" },
      { "tag": "markdown", "content": "<text_tag color='grey'>鹰眼助手自动生成 | 时间戳</text_tag>" }
    ]
  }
}
```

置信度颜色：>=90% red, 70-89% orange, 50-69% yellow
命中多辆车时按置信度从高到低排列，每辆车复制一组（置信度标签 + column_set + 分析描述）。

#### 变体 B：未命中车辆（green 主题）

适用：AI 分析后确认该时段无新石器车辆经过该路口

```json
{
  "schema": "2.0",
  "config": { "wide_screen_mode": true },
  "header": {
    "title": { "tag": "plain_text", "content": "鹰眼排查报告 · 路口名 事件类型事件" },
    "subtitle": { "tag": "plain_text", "content": "查询时段：时间范围 | 命中 0 辆车" },
    "template": "green"
  },
  "body": {
    "elements": [
      {
        "tag": "column_set",
        "flex_mode": "none",
        "columns": [
          { "tag": "column", "width": "weighted", "weight": 1, "elements": [{ "tag": "markdown", "content": "**排查地点**" }] },
          { "tag": "column", "width": "weighted", "weight": 1, "elements": [{ "tag": "markdown", "content": "**事件类型**" }] },
          { "tag": "column", "width": "weighted", "weight": 1, "elements": [{ "tag": "markdown", "content": "**查询时段**" }] },
          { "tag": "column", "width": "weighted", "weight": 1, "elements": [{ "tag": "markdown", "content": "**命中车辆**" }] }
        ]
      },
      {
        "tag": "column_set",
        "flex_mode": "none",
        "columns": [
          { "tag": "column", "width": "weighted", "weight": 1, "elements": [{ "tag": "markdown", "content": "路口名" }] },
          { "tag": "column", "width": "weighted", "weight": 1, "elements": [{ "tag": "markdown", "content": "<text_tag color='red'>闯红灯</text_tag>" }] },
          { "tag": "column", "width": "weighted", "weight": 1, "elements": [{ "tag": "markdown", "content": "时段" }] },
          { "tag": "column", "width": "weighted", "weight": 1, "elements": [{ "tag": "markdown", "content": "<text_tag color='green'>0 辆</text_tag>" }] }
        ]
      },
      { "tag": "hr" },
      { "tag": "markdown", "content": "**AI 自动分析结论**" },
      {
        "tag": "markdown",
        "content": "经过 AI 对查询时段内所有新石器车辆的行程轨迹进行全量比对分析：\n\n<text_tag color='green'>结论：问题时段无新石器车辆经过该路口，该违规车辆为非新石器车辆</text_tag>\n\n**排查详情：**\n- 该时段共检索到 **N 辆**新石器车辆在周边区域运营\n- 最近途经车辆为 车号，经过时间 时间（早于/晚于查询时段）\n- 路口视频比对确认，违规车辆外观特征与新石器车型不符"
      },
      { "tag": "hr" },
      { "tag": "markdown", "content": "**对外回复话术**" },
      { "tag": "markdown", "content": "涉及路口：**路口名**\n\n经核实，在反馈时段内无我司车辆经过该路口，该违规车辆为非新石器车辆。\n如有进一步疑问，欢迎拨打 **4000000544** 反馈，我们会积极配合调查。\n\n📄 [一键下载对外报告（docx）](https://example.com)" },
      { "tag": "hr" },
      { "tag": "markdown", "content": "[查看路口全时段监控](https://example.com) | [查看周边车辆轨迹](https://example.com)" },
      { "tag": "markdown", "content": "<text_tag color='grey'>鹰眼助手自动生成 | 时间戳</text_tag>" }
    ]
  }
}
```

无需「对内原因分析」和「整改方案」区块。
对外话术中不要推测违规车辆属于哪家企业，直接定性为「非新石器车辆」。

---

### 模板 4：表格数据卡片

适用：数据筛选结果、排行榜、车辆列表

```json
{
  "schema": "2.0",
  "config": { "wide_screen_mode": true },
  "header": {
    "title": { "tag": "plain_text", "content": "标题" },
    "subtitle": { "tag": "plain_text", "content": "副标题" },
    "template": "blue"
  },
  "body": {
    "elements": [
      { "tag": "markdown", "content": "**筛选条件：** 条件描述" },
      { "tag": "hr" },
      {
        "tag": "column_set",
        "flex_mode": "none",
        "background_style": "grey",
        "columns": [
          { "tag": "column", "width": "weighted", "weight": 1, "elements": [{ "tag": "markdown", "content": "**列名1**" }] },
          { "tag": "column", "width": "weighted", "weight": 1, "elements": [{ "tag": "markdown", "content": "**列名2**" }] },
          { "tag": "column", "width": "weighted", "weight": 1, "elements": [{ "tag": "markdown", "content": "**列名3**" }] }
        ]
      },
      {
        "tag": "column_set",
        "flex_mode": "none",
        "columns": [
          { "tag": "column", "width": "weighted", "weight": 1, "elements": [{ "tag": "markdown", "content": "值1" }] },
          { "tag": "column", "width": "weighted", "weight": 1, "elements": [{ "tag": "markdown", "content": "值2" }] },
          { "tag": "column", "width": "weighted", "weight": 1, "elements": [{ "tag": "markdown", "content": "值3" }] }
        ]
      },
      { "tag": "hr" },
      { "tag": "markdown", "content": "操作链接" },
      { "tag": "markdown", "content": "<text_tag color='grey'>页脚</text_tag>" }
    ]
  }
}
```

颜色标签：高值/正常=green, 中等/警告=orange, 低值/异常=red, 辅助信息=grey
表头使用 background_style: "grey"，数据行不加。
列数建议 ≤ 4 列。

---

## 重要规则

1. **schema 必须是 "2.0"**
2. **不支持 action 标签** — 用 markdown 链接替代按钮：`[文字](url)`
3. **text_tag 语法**：`<text_tag color='green'>文字</text_tag>`（支持 green/red/orange/yellow/grey）
4. **只输出 JSON**，不要输出任何其他文字
5. **当前时间**用于页脚时间戳
6. **链接地址**如果不知道真实 URL，使用 `https://example.com` 作为占位
"""
