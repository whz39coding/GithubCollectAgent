import sys
import time

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI

from backend.core.config import get_settings


def main() -> int:
    settings = get_settings()
    if not settings.llm_api_key:
        print("LLM_API_KEY is not configured.")
        return 2

    print("Testing LLM configuration:")
    print(f"  base_url: {settings.llm_base_url}")
    print(f"  model: {settings.llm_model}")
    print(f"  api_key: configured ({len(settings.llm_api_key)} characters)")

    client = OpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        timeout=45.0,
        max_retries=0,
    )

    started_at = time.monotonic()
    try:
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {
                    "role": "user",
                    "content": "Reply with exactly: LLM configuration works",
                }
            ],
            temperature=0,
        )
    except APITimeoutError:
        print("FAILED: request timed out after 45 seconds.")
        return 1
    except APIConnectionError as exc:
        print(f"FAILED: could not connect to the LLM endpoint: {exc}")
        return 1
    except APIStatusError as exc:
        print(f"FAILED: API returned HTTP {exc.status_code}: {exc.message}")
        return 1
    except Exception as exc:
        print(f"FAILED: unexpected error: {type(exc).__name__}: {exc}")
        return 1

    elapsed = time.monotonic() - started_at
    content = response.choices[0].message.content or ""
    print(f"SUCCESS in {elapsed:.1f}s")
    print(f"Response: {content.strip()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
