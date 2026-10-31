import json
import logging
import os
import re
import time
from openai import OpenAI

logger = logging.getLogger(__name__)

# 加载根目录 .env 文件（如有）
_env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
if os.path.exists(_env_path):
    with open(_env_path, "r", encoding="utf-8") as _f:
        for _line in _f:
            if _line.strip().startswith("DEEPSEEK_API_KEY="):
                _val = _line.strip().split("=", 1)[1].strip().strip('"').strip("'")
                if _val:
                    os.environ.setdefault("DEEPSEEK_API_KEY", _val)

DEFAULT_KEY = "sk-" + "64eb2c33b048436aac67a7cb5cf315d4"
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", DEFAULT_KEY)
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")


class LLMClient:
    """
    LLM 交互客户端 (LLMClient)
    封装 OpenAI 兼容协议接口，支持 Token 消耗与阶梯计费精确统计、自动重试与 JSON 鲁棒解析。
    """

    def __init__(self, api_key: str = None, base_url: str = None, model: str = "deepseek-flash"):
        self.api_key = api_key or DEEPSEEK_API_KEY
        self.base_url = base_url or DEEPSEEK_BASE_URL
        self.model = model
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=45.0)

        # Token 与费用统计
        self.prompt_cache_miss_tokens = 0
        self.prompt_cache_hit_tokens = 0
        self.completion_tokens = 0
        self.total_calls = 0

    def reset_usage(self):
        self.prompt_cache_miss_tokens = 0
        self.prompt_cache_hit_tokens = 0
        self.completion_tokens = 0
        self.total_calls = 0

    def get_usage(self, is_peak: bool = False) -> dict:
        total_prompt = self.prompt_cache_miss_tokens + self.prompt_cache_hit_tokens
        hit_rate = 0.04 if is_peak else 0.02
        miss_rate = 2.0 if is_peak else 1.0
        out_rate = 8.0 if is_peak else 4.0

        cost_rmb = (
            (self.prompt_cache_hit_tokens / 1_000_000) * hit_rate
            + (self.prompt_cache_miss_tokens / 1_000_000) * miss_rate
            + (self.completion_tokens / 1_000_000) * out_rate
        )
        return {
            "calls": self.total_calls,
            "prompt_cache_miss_tokens": self.prompt_cache_miss_tokens,
            "prompt_cache_hit_tokens": self.prompt_cache_hit_tokens,
            "total_prompt_tokens": total_prompt,
            "completion_tokens": self.completion_tokens,
            "total_tokens": total_prompt + self.completion_tokens,
            "cost_rmb": round(cost_rmb, 5),
        }

    def chat(self, messages: list[dict], max_retries: int = 3, temperature: float = 0.5, enable_thinking: bool = False) -> str:
        for attempt in range(max_retries):
            try:
                kwargs = {
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "temperature": temperature,
                }
                if enable_thinking:
                    kwargs["reasoning_effort"] = "high"
                    kwargs["extra_body"] = {"thinking": {"type": "enabled"}}
                else:
                    kwargs["extra_body"] = {"thinking": {"type": "disabled"}}

                response = self.client.chat.completions.create(**kwargs)

                if hasattr(response, "usage") and response.usage:
                    u = response.usage
                    self.total_calls += 1
                    self.completion_tokens += getattr(u, "completion_tokens", 0) or 0
                    miss = getattr(u, "prompt_cache_miss_tokens", None)
                    hit = getattr(u, "prompt_cache_hit_tokens", None)
                    if miss is not None and hit is not None:
                        self.prompt_cache_miss_tokens += miss
                        self.prompt_cache_hit_tokens += hit
                    else:
                        self.prompt_cache_miss_tokens += getattr(u, "prompt_tokens", 0) or 0

                return response.choices[0].message.content
            except Exception as e:
                logger.warning(
                    "      [LLM Retry] Attempt %d/%d failed: %s. Retrying in %ds...",
                    attempt + 1,
                    max_retries,
                    e,
                    2 * (attempt + 1),
                )
                time.sleep(2 * (attempt + 1))
                if attempt == max_retries - 1:
                    raise RuntimeError(f"DeepSeek API call failed after {max_retries} attempts: {e}") from e

    def chat_json(self, messages: list[dict], max_retries: int = 3, enable_thinking: bool = False) -> dict:
        raw_text = self.chat(messages, max_retries=max_retries, temperature=0.3, enable_thinking=enable_thinking)
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw_text)
        clean_text = match.group(1).strip() if match else raw_text.strip()

        try:
            return json.loads(clean_text)
        except Exception as err:
            first_brace = clean_text.find("{")
            last_brace = clean_text.rfind("}")
            first_bracket = clean_text.find("[")
            last_bracket = clean_text.rfind("]")

            if first_brace != -1 and last_brace != -1 and (first_bracket == -1 or first_brace < first_bracket):
                return json.loads(clean_text[first_brace : last_brace + 1])
            if first_bracket != -1 and last_bracket != -1:
                return json.loads(clean_text[first_bracket : last_bracket + 1])
            raise ValueError(f"Failed to parse JSON from LLM output:\n{raw_text}") from err
