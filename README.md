# Auto Weekly AI Feedback

一个基于 LangGraph 的 CLI workflow：自动联网发现近期热门 AI native product，先产出候选和推荐，再生成中文 Markdown 评测报告。

当前图结构：

```text
search_candidates -> select_product -> resolve_selection -> write_editorial_review
```

## 安装

```bash
source .venv/bin/activate
pip install -e ".[dev]"
```

## 配置

项目直接从环境变量读取配置，也支持通过本地 `.env` 文件加载。

最少需要：

- `OPENAI_API_KEY` 或 `DEEPSEEK_API_KEY`
- `MODEL_NAME`
- `TAVILY_API_KEY`

如果你使用 OpenAI 兼容网关，再额外配置：

- `OPENAI_BASE_URL`

示例：

```bash
export DEEPSEEK_API_KEY="your-api-key"
export MODEL_NAME="deepseek-v4-pro"
export TAVILY_API_KEY="your-tavily-key"
export OPENAI_BASE_URL="https://api.deepseek.com"
```

也可以在仓库根目录创建 `.env`，内容与上面相同。

## 运行

自动模式会直接采用模型推荐的候选：

```bash
ai-product-report run
```

常用参数：

```bash
ai-product-report run --days 30 --max-candidates 8 --output reports --topic general --selection-mode auto
```

如果你希望先看候选再人工选择：

```bash
ai-product-report run --days 30 --max-candidates 8 --topic general --selection-mode user
```

报告会保存到：

```text
reports/YYYY-MM-DD/<product-slug>.md
```

## 行为说明

- `search_candidates`：搜索近期 AI product 候选并整理多来源证据
- `select_product`：对候选打分并给出推荐
- `resolve_selection`：自动定案或等待用户选择
- `write_editorial_review`：生成编辑型中文评测

报告基于公开网页、文档、演示和第三方评价生成，不会自动注册、登录或真实操作第三方产品。
