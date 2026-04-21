from __future__ import annotations


def build_prompt(template: str, *, dataset_description: str = "", current_caption: str = "") -> str:
    return (
        template.replace("{dataset_description}", dataset_description)
        .replace("{current_caption}", current_caption)
    )
