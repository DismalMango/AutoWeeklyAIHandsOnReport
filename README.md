# Auto Weekly AI Feedback

一个基于 LangChain 的 CLI agent：自动联网发现近期热门 AI native product，并生成中文 Markdown 使用报告。

## 安装

```bash
source .venv/bin/activate
pip install -e ".[dev]"
```

## 配置

复制 `.env.example` 为 `.env`，填写 OpenAI 兼容接口和 Tavily key：

```bash
cp .env.example .env
```

必填变量：

- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `MODEL_NAME`
- `TAVILY_API_KEY`

## 运行

```bash
ai-product-report run
```

常用参数：

```bash
ai-product-report run --days 30 --max-candidates 8 --output reports --topic general
```

报告会保存到：

```text
reports/YYYY-MM-DD/<product-slug>.md
```

第一版报告基于公开网页、文档、演示和第三方评价，不会自动注册、登录或真实操作第三方产品。
