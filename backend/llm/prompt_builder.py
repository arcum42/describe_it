from __future__ import annotations


def build_prompt(template: str, *, dataset_description: str = "", current_caption: str = "") -> str:
    return (
        template.replace("{dataset_description}", dataset_description)
        .replace("{current_caption}", current_caption)
    )


def build_caption_prompt(
    *,
    filename: str,
    dataset_description: str,
    current_caption: str,
    caption_mode: str = "description",
    extra_instructions: str = "",
) -> str:
    if caption_mode == "tags":
        instruction = (
            "Write one comma-separated tag list for this image suitable for training tags. "
            "Use short, concrete visual tags and no prose sentence. "
            "Return only the tags with no surrounding explanation."
        )
    else:
        instruction = (
            "Write one concise training caption for this image. "
            "Focus on clear visual attributes and avoid mentioning camera metadata. "
            "Return only the caption text with no surrounding explanation."
        )

    base = (
        f"{instruction}\n\n"
        f"Dataset description: {dataset_description or '(none provided)'}\n"
        f"Filename: {filename}\n"
        f"Current caption: {current_caption or '(none)'}"
    )
    if extra_instructions.strip():
        base += f"\nAdditional instructions: {extra_instructions.strip()}"
    return base
