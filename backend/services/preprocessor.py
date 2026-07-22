import re

from loguru import logger


class ReadmePreprocessor:
    def __init__(self, max_length: int) -> None:
        self.max_length = max_length

    def clean(self, content: str) -> str:
        original_length = len(content)
        content = self._remove_html_images(content)
        content = self._remove_markdown_badges(content)
        content = self._trim_long_code_blocks(content)
        content = self._collapse_blank_lines(content)
        content = self._smart_truncate(content)
        logger.info("README 预处理完成: {} -> {} 字符", original_length, len(content))
        return content

    def _remove_html_images(self, content: str) -> str:
        content = re.sub(r"<img\b[^>]*>", "", content, flags=re.IGNORECASE)
        return re.sub(r"<picture\b.*?</picture>", "", content, flags=re.IGNORECASE | re.DOTALL)

    def _remove_markdown_badges(self, content: str) -> str:
        badge_patterns = [
            r"!\[[^\]]*(?:badge|build|status|coverage|version|license)[^\]]*\]\([^)]+\)",
            r"\[!\[[^\]]+\]\([^)]+\)\]\([^)]+\)",
        ]
        for pattern in badge_patterns:
            content = re.sub(pattern, "", content, flags=re.IGNORECASE)
        return content

    def _trim_long_code_blocks(self, content: str) -> str:
        def replace_block(match: re.Match) -> str:
            block = match.group(0)
            line_count = block.count("\n")
            if line_count <= 50:
                return block
            first_line = block.splitlines()[0] if block.splitlines() else "```"
            return f"{first_line}\n...长代码块已省略...\n```"

        return re.sub(r"```[\s\S]*?```", replace_block, content)

    def _collapse_blank_lines(self, content: str) -> str:
        content = re.sub(r"[ \t]+", " ", content)
        return re.sub(r"\n{3,}", "\n\n", content).strip()

    def _smart_truncate(self, content: str) -> str:
        if len(content) <= self.max_length:
            return content

        head_length = int(self.max_length * 0.8)
        tail_length = self.max_length - head_length
        return (
            content[:head_length]
            + "\n\n...中间冗长内容已省略...\n\n"
            + content[-tail_length:]
        )
