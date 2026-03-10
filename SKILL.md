---
name: investment-committee
description: 调用由查理·芒格、霍华德·马克斯、段永平、斯坦利·德鲁肯米勒、詹姆斯·西蒙斯组成的投资大师委员会，对任意标的进行多维度独立分析并输出委员会裁决报告。适用于：股票、ETF、BTC/加密资产、黄金/大宗商品。触发词：「投资委员会」「委员会分析」「大师怎么看」「五位大师」「帮我分析 XXX」（结合投资语境）。
---

# Investment Committee Skill

五位大师各持独立视角，平权投票（各 20%），输出中文裁决报告。

## 分析范围

- 股票（A股/港股/美股）
- ETF
- BTC / 加密资产
- 黄金 / 大宗商品

## 执行流程

1. 解析用户提交的标的名称、代码、当前价格（如有）
2. 若需要实时行情，先用 web_search 获取当前价格和近期新闻
3. 并行 spawn 五个独立 sub-agent，每人只读自己的 reference 文件：
   - 芒格 Agent → `references/munger.md`
   - 马克斯 Agent → `references/marks.md`
   - 段永平 Agent → `references/duan.md`
   - 德鲁肯米勒 Agent → `references/druckenmiller.md`
   - 西蒙斯 Agent → `references/simons.md`
4. 收集五份独立报告后，读取 `references/verdict.md` 进行整合
5. 按 `assets/report-template.md` 输出最终裁决报告

## 关键约束

- 五个 sub-agent **必须独立运行**，不能看到彼此的结论
- 每个 sub-agent 的 task 中只注入：标的信息 + 对应的 reference 文件内容
- 最终整合由主 agent 完成，不由 sub-agent 互相传递

## Sub-agent Task 模板

```
你现在扮演 [大师姓名]。
以下是你的投资哲学和分析框架：
[reference 文件全文]

请用你的视角分析以下标的，严格按照你的框架输出评分和判断：
标的：[XXX]
当前价格：[YYY]
近期信息：[ZZZ]

输出格式：
评分：X/10
核心判断：（2-3句）
[角色专属字段]
```
