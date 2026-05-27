import re
import json
import httpx
from urllib.parse import urlparse

from backend.core.logger import setup_logger

logger = setup_logger("tool.jd_fetcher")

_HTML_RE = re.compile(r"<[^>]+>")
_MIN_MEANINGFUL_LENGTH = 80


# ═══════════════════════════════════════════════════════════════════════
# Main entry point
# ═══════════════════════════════════════════════════════════════════════

def fetch_jd_from_url(url: str, timeout: int = 15) -> str:
    """Fetch job description text from a URL."""
    logger.info("Fetching JD from URL: %s", url)
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(
                url,
                headers=_default_headers(),
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise ValueError(
            f"链接访问失败: HTTP {e.response.status_code}\n\n"
            f"该链接可能已失效、需要登录、或仅限内部访问。\n"
            f"解决方法：从浏览器直接复制职位描述文本，粘贴到 JD 输入框中。"
        ) from e
    except httpx.RequestError as e:
        raise ValueError(
            f"无法连接到链接: {e}\n\n请检查链接是否正确，网络是否正常。"
        ) from e

    content_type = response.headers.get("content-type", "")
    html = response.text

    if "text/html" not in content_type:
        logger.info("非 HTML 内容，直接返回 (%d 字符)", len(html))
        return html

    # ── 尝试提取内嵌数据 ──
    embedded = _extract_embedded_data(html)
    if embedded and len(embedded) > _MIN_MEANINGFUL_LENGTH:
        logger.info("从内嵌数据提取 %d 字符", len(embedded))
        return embedded

    # ── 纯 HTML 提取 ──
    text = _strip_html(html)
    logger.info("HTML 清洗后 %d 字符", len(text))

    if len(text) < _MIN_MEANINGFUL_LENGTH:
        # ── 最后手段：无头浏览器渲染 ──
        browser_text = _fetch_with_browser(url, timeout)
        if browser_text and len(browser_text) > _MIN_MEANINGFUL_LENGTH:
            logger.info("浏览器渲染成功，%d 字符", len(browser_text))
            return browser_text

        site = _guess_site_name(url)
        raise ValueError(
            f"无法从链接提取有效内容（仅 {len(text)} 字符）。\n\n"
            f"{site} 页面是 JS 动态渲染的，普通 HTTP 请求无法获取实际内容。\n\n"
            f"解决方法 1（推荐）：从浏览器打开链接，复制职位描述全文，粘贴到 JD 输入框。\n"
            f"解决方法 2：安装 Playwright 实现自动渲染——"
            f"运行 pip install playwright && playwright install chromium"
        )

    return text


# ═══════════════════════════════════════════════════════════════════════
# 通用抓取
# ═══════════════════════════════════════════════════════════════════════

def _default_headers() -> dict:
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }


def _guess_site_name(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
        for name, label in [
            ("zhipin", "Boss直聘"), ("boss", "Boss直聘"),
            ("lagou", "拉勾"), ("51job", "前程无忧"),
            ("liepin", "猎聘"), ("linkedin", "LinkedIn"),
        ]:
            if name in host:
                return label
        return host
    except Exception:
        return "该"


def _extract_embedded_data(html: str) -> str:
    """从 HTML <script> 标签提取内嵌的结构化数据。"""
    parts: list[str] = []

    # JSON-LD
    ld_re = re.compile(
        r'<script[^>]*type="application/ld\+json"[^>]*>([\s\S]*?)</script>', re.I
    )
    for m in ld_re.finditer(html):
        try:
            data = json.loads(m.group(1))
            text = _flatten_jsonld(data)
            if text:
                parts.append(text)
        except json.JSONDecodeError:
            pass

    # 常见 SPA 状态变量
    patterns = [
        r'__NEXT_DATA__\s*=\s*({[\s\S]*?});',
        r'__NUXT__\s*=\s*({[\s\S]*?});',
        r'window\.__INITIAL_STATE__\s*=\s*({[\s\S]*?});',
        r'window\.__PRELOADED_STATE__\s*=\s*({[\s\S]*?});',
        r'"jobInfo"\s*:\s*({[\s\S]*?})\s*[,}\]]',
        r'"jobDetail"\s*:\s*({[\s\S]*?})\s*[,}\]]',
        r'"jdContent"\s*:\s*"([\s\S]*?)"',
        r'"description"\s*:\s*"([\s\S]{100,}?)"',
        r'"jobDescription"\s*:\s*"([\s\S]{100,}?)"',
    ]
    for pattern in patterns:
        for m in re.finditer(pattern, html):
            try:
                payload = m.group(1)
                try:
                    data = json.loads(payload)
                    text = _deep_extract_text(data)
                    if text and len(text) > _MIN_MEANINGFUL_LENGTH:
                        parts.append(text)
                except json.JSONDecodeError:
                    if len(payload) > _MIN_MEANINGFUL_LENGTH:
                        parts.append(_clean_text(payload))
            except Exception:
                pass

    return "\n\n".join(parts)


def _flatten_jsonld(data) -> str:
    if isinstance(data, list):
        return "\n\n".join(t for item in data if (t := _flatten_jsonld(item)))
    if not isinstance(data, dict):
        return ""
    if "@graph" in data:
        return _flatten_jsonld(data["@graph"])

    fields = []
    kmap = {
        "title": "职位", "name": "名称", "description": "描述",
        "responsibilities": "职责", "qualifications": "要求",
        "skills": "技能", "experienceRequirements": "经验要求",
        "educationRequirements": "学历要求", "jobLocation": "地点",
        "hiringOrganization": "公司", "employmentType": "类型",
        "baseSalary": "薪资", "industry": "行业",
    }
    for key, label in kmap.items():
        val = data.get(key)
        if isinstance(val, str) and len(val) > 1:
            fields.append(f"{label}: {_clean_text(val)}")
        elif isinstance(val, dict):
            inner = _flatten_jsonld(val)
            if inner:
                fields.append(f"{label}: {inner}")
        elif isinstance(val, list):
            items = []
            for v in val:
                if isinstance(v, str):
                    items.append(f"- {_clean_text(v)}")
                elif isinstance(v, dict):
                    for k, vv in v.items():
                        items.append(f"- {k}: {_clean_text(str(vv))}")
            if items:
                fields.append(f"{label}:\n" + "\n".join(items))
    return "\n".join(fields)


def _deep_extract_text(data, max_depth: int = 5) -> str:
    if max_depth <= 0:
        return ""
    if isinstance(data, str):
        return _clean_text(data) if len(data) > 20 else ""
    if isinstance(data, (int, float, bool)):
        return ""
    if isinstance(data, list):
        texts = []
        for item in data[:20]:
            t = _deep_extract_text(item, max_depth - 1)
            if t:
                texts.append(t)
        return "\n".join(texts)
    if isinstance(data, dict):
        texts = []
        priority = [
            "description", "jobDetail", "jobDesc", "jdContent", "jobDescription",
            "responsibility", "requirement", "qualification", "postDescription",
            "title", "jobName", "positionName", "companyName", "brandName",
            "skill", "keyword", "tag", "detail", "content", "text", "summary",
        ]
        for key in priority:
            val = data.get(key) or data.get(key.lower(), "")
            t = _deep_extract_text(val, max_depth - 1)
            if t:
                texts.append(f"{key}: {t}")
        for key, val in data.items():
            if key in priority:
                continue
            t = _deep_extract_text(val, max_depth - 1)
            if t and len(t) > 30:
                texts.append(t)
        return "\n".join(texts)
    return ""


def _clean_text(text: str) -> str:
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&quot;", '"').replace("&#x27;", "'").replace("&#39;", "'")
    text = text.replace("&nbsp;", " ").replace(" ", " ")
    text = re.sub(r"\\n", "\n", text)
    text = re.sub(r"\\t", " ", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\n\s*\n", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


# ═══════════════════════════════════════════════════════════════════════
# 无头浏览器兜底（Playwright，可选）
# ═══════════════════════════════════════════════════════════════════════

def _fetch_with_browser(url: str, timeout: int = 30) -> str | None:
    """使用 Playwright 无头浏览器渲染 JS 页面，提取可见文本。

    需要安装: pip install playwright && playwright install chromium
    如未安装则静默跳过，返回 None。
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.info("Playwright 未安装，跳过浏览器渲染")
        return None

    logger.info("启动无头浏览器渲染: %s", url)
    try:
        with sync_playwright() as p:
            # 优先用完整 Chromium（headless shell 可能没装）
            import os as _os
            chromium_path = None
            for possible in [
                _os.path.expandvars(r"%LOCALAPPDATA%\ms-playwright\chromium-1223\chrome-win64\chrome.exe"),
                _os.path.expandvars(r"%USERPROFILE%\AppData\Local\ms-playwright\chromium-1223\chrome-win64\chrome.exe"),
            ]:
                if _os.path.exists(possible):
                    chromium_path = possible
                    break

            if chromium_path:
                browser = p.chromium.launch(
                    headless=True,
                    executable_path=chromium_path,
                    args=["--no-sandbox", "--disable-setuid-sandbox"],
                )
            else:
                browser = p.chromium.launch(headless=True)

            page = browser.new_page()
            page.goto(url, timeout=timeout * 1000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            text = page.inner_text("body")
            browser.close()
            return _clean_text(text)
    except Exception as e:
        logger.warning("浏览器渲染失败: %s", e)
        return None


def _strip_html(html: str) -> str:
    html = re.sub(r"<(script|style|noscript)[^>]*>[\s\S]*?</\1>", "", html, flags=re.I)
    html = re.sub(
        r"</?(div|p|br|h[1-6]|li|tr|article|section|header|footer|main|nav)[^>]*>",
        "\n", html, flags=re.I,
    )
    text = _HTML_RE.sub("", html)
    text = _clean_text(text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()
