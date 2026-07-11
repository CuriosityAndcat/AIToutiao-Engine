# specs/acceptance.md — 内容质量验收标准

> 权威源：`lib/toutiao-auto-publisher/backend/evaluation.py`
> 本文是将代码中的验收逻辑「文档化」为正式标准，**禁止在别处另立验收**。
> 流水线与状态契约见 `pipeline.md`。

---

## 1. 权威函数

```python
evaluate_content(content: str, title: str, style: str, research_context: str = "") -> dict
```

- 调用方式：经 `AIWriter._call_ai`（DeepSeek），`temperature=0.1`，`max_tokens=500`
- 纯逻辑、无 UI 依赖（仅写 stderr）

---

## 2. 五个验收维度（每项满分 100）

| 维度 | 含义 | 校验要点 |
|---|---|---|
| 事实准确 | 与已知事实一致，无明显编造 | 结合 `research_context` 比对 |
| 信息完整 | 覆盖人物 / 事件 / 原因 / 影响 | 关键点无遗漏 |
| 结构清晰 | 段落分明、逻辑连贯、易读 | — |
| 风格一致 | 符合指定写作风格 | 对比 `style` 参数（`ContentStyle` 中文标签） |
| 去AI味 | 像真人写作，无机器腔 | — |

---

## 3. 通过算法（代码即标准）

1. 综合分 `score` = 5 项维度分的平均值（整数）
2. **通过条件（必须全部满足）**：
   - `score >= QUALITY_PASS_THRESHOLD`（= **75**）
   - 且 5 个维度中**任意一个不低于 50**
3. 否则 `passed = False`（触发重写 / 迭代）

> 源码常量：`evaluation.py:9` → `QUALITY_PASS_THRESHOLD = 75`
> 单维下限：`evaluation.py:133` → `if any(v < 50 for v in dimensions.values()): passed = False`

---

## 4. 输出契约（返回值 dict）

| 字段 | 类型 | 说明 |
|---|---|---|
| `score` | int | 综合分 0-100 |
| `feedback` | str | 一句话优劣总结与改进建议 |
| `passed` | bool | 是否通过 |
| `dimensions` | dict | `{"事实准确","信息完整","结构清晰","风格一致","去AI味": int}` |

---

## 5. 解析降级策略（健壮性）

评估输出优先 XML 标签解析；失败按以下顺序降级：

1. **XML 解析**：`<evaluation>` / `<score>` / `<dimensions>` / `<feedback>`
2. **JSON 解析**：兼容旧格式
3. **规则判断**：无反馈时 `content > 100` 字判 `PASS`，否则 `FAIL`，`score = 50`
4. **模块异常**：返回 `passed=True, score=75, 维度全 70`（跳过评估，记 stderr）

---

## 6. 与风格系统的关系

- `style` 参数来自 `state.content_style`，经 `models.style_label()` 转为中文标签
- 「风格一致」维度针对该标签校验；**新增风格须在 `models.ContentStyle` 登记**

---

## 7. 使用约束

1. 验收以**本文件 + `evaluation.py`** 为唯一权威，禁止在业务代码中硬编码另一套阈值。
2. 阈值 **75**、单维下限 **50** 的修改必须经评审，并同步更新本文件。
3. 写作循环（`write_stage.research_and_write`）以 `passed` 作为迭代停止条件，直到 `PASS` 或达到 `MAX_RESEARCH_ITERATIONS = 3`。
