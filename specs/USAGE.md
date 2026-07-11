# specs/USAGE.md — 文档体系使用约定（SOP）

> 本文件说明「如何使用 AGENTS.md + specs/ 三件套」，是文档体系的入口与维护约定。
> 全部为约定与说明，**不涉及任何程序（代码）更改**。
> 配套文档：`AGENTS.md`（地图）、`specs/pipeline.md`（流水线契约）、`specs/acceptance.md`（验收标准）。

---

## 1. 文档地图与消费者

| 文档 | 定位 | 主要消费者 | 何时读 |
|---|---|---|---|
| `AGENTS.md` | 项目地图 | AI 协作 + 新成员 | 进入项目的**第一件事**（约定文件名，AI 工具应自动加载） |
| `specs/pipeline.md` | 流水线契约 | AI / 开发者改流水线代码时 | 改动 `research.py` / `write_stage.py` / `evaluation.py` / `engine_app.py` **前** |
| `specs/acceptance.md` | 验收标准 | AI / 开发者改验收时 | 改动 `evaluation.py` 或写作循环 **前** |
| `docs/WEB_REVIEW.md` | 网页评审基线 + 技能选型 | AI / 开发者改网页时 | 改动 `engine_app.py` UI 代码 **前** |
| `specs/USAGE.md` | 本文件 | 所有人 | 不确定该读哪个、或要更新文档时 |

---

## 2. AI 协作 SOP（自动路由）

给 AI 的标准前置指令（复制到任务开头即可）：

```
1. 先读 AGENTS.md，定位模块与职责。
2. 若任务涉及「流水线/阶段/状态传递」→ 查 specs/pipeline.md 的契约与函数签名。
3. 若任务涉及「质量验收/阈值/维度」→ 查 specs/acceptance.md，以 evaluation.py 为权威。
4. 改代码后，若契约事实变化，同步更新对应 specs 文档（行号、签名、字段）。
5. 涉及护栏接线或全局编排重构 → 标记为批次 B/C，不可顺手混入当前改动。
```

---

## 3. 人类开发者约定

- **改流水线模块** → 先看 `specs/pipeline.md`，改动后同步对应契约段。
- **改验收阈值/维度** → 先看 `specs/acceptance.md`；阈值 75、单维下限 50 的修改**必须评审**并同步本文件。
- **架构级决策**（护栏接线、通用编排是否接管写作循环）→ 走独立批次（C），不在日常 PR 里拍板。
- **新增模块** → 在 `AGENTS.md` 加一行职责 + 接入状态。

---

## 4. 防漂移：指针式协同原则

文档与代码是「镜像」而非「副本」，防止二者失同步：

1. **不复制代码逻辑**：文档只描述职责/契约/边界，逻辑以代码为准。
2. **行号引用随代码更新**：文档中的 `evaluation.py:9` 等行号，代码变动后低成本同步。
3. **单一权威源**：验收以 `evaluation.py` 为唯一权威，`acceptance.md` 是其可读镜像；禁止在别处另立阈值。
4. **状态契约单一**：模块间状态传递统一用 `state.outputs` + `state` 顶层字段（见 `pipeline.md` §2）。

---

## 5. 维护触发条件（何时更新文档）

| 触发事件 | 更新动作 |
|---|---|
| 新增 / 删除模块 | `AGENTS.md` 对应表加 / 删一行 |
| 改 `PipelineState` 字段 | `specs/pipeline.md` §2 更新 |
| 改写作循环签名或轮数 | `specs/pipeline.md` §4 更新 |
| 改验收维度 / 阈值 | `specs/acceptance.md` §3 同步，并评审 |
| 接/断 Harness 组件（如护栏上线） | `AGENTS.md` 「接入状态」表更新 |

---

## 6. 立即接入动作（零代码，今天可做）

1. **自动加载**：`AGENTS.md` 已是行业约定文件名（类比 `CLAUDE.md`），主流 AI 编码工具会自动读取——无需改代码即生效。
2. **README 指引**：在项目 `README.md` 顶部加一句「新成员 / AI 协作请先读 `AGENTS.md`」。
3. **纳入版本基线**：将 `AGENTS.md` + `specs/` 提交 git，作为协作基线。
4. **团队对齐**：在本文件 §3 约定的三类改动前，强制先查对应 specs。

---

## 7. 当前项目落地检查表

- [x] `AGENTS.md` 已生成（项目地图 + Harness 接入状态）
- [x] `specs/pipeline.md` 已生成（5 阶段 + 函数级契约）
- [x] `specs/acceptance.md` 已生成（5 维 + 阈值 75 + 单维下限 50）
- [x] `specs/USAGE.md` 已生成（本文件，使用约定）
- [x] `docs/WEB_REVIEW.md` 已有（网页评审 + §七选型结论已定稿）
- [x] `README.md` 顶部加一句指引（可选，零代码）
- [ ] 批次 B：护栏词表落地 + `write_stage` 接线点（低风险代码增强）
- [ ] 批次 C：`agent/graph.py` 通用编排是否接管写作循环（架构评审，独立立项）
- [ ] 批次 D：内容选题变现（独立）
