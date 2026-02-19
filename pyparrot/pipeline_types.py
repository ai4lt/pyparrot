"""Central pipeline type definitions for PyParrot."""

from typing import Dict, List, Optional


PIPELINE_DEFINITIONS: Dict[str, Dict[str, object]] = {
    "end2end": {
        "templates": ["middleware", "asr"],
        "backend_components": ["stt"],
        "used_urls": ["stt"],
        "use_slt": True,
        "slide_support": False,
        "default_mt_backend_engine": None,
        "default_tts_backend_engine": None,
    },
    "cascaded": {
        "templates": ["middleware", "asr", "mt"],
        "backend_components": ["stt", "mt"],
        "used_urls": ["stt", "mt"],
        "use_slt": False,
        "slide_support": False,
        "default_mt_backend_engine": "vllm",
        "default_tts_backend_engine": None,
    },
    "LT.2025": {
        "templates": ["middleware", "asr", "mt", "tts", "dialog", "markup"],
        "backend_components": ["stt", "mt", "tts"],
        "used_urls": [
            "stt",
            "mt",
            "tts",
            "summarizer",
            "text_structurer_online",
            "text_structurer_offline",
            "llm",
        ],
        "use_slt": False,
        "slide_support": False,
        "default_mt_backend_engine": None,
        "default_tts_backend_engine": "tts-kokoro",
    },
    "dialog": {
        "templates": ["middleware", "asr", "tts", "dialog"],
        "backend_components": ["stt", "tts"],
        "used_urls": ["stt", "tts", "llm"],
        "use_slt": False,
        "slide_support": False,
        "default_mt_backend_engine": None,
        "default_tts_backend_engine": "tts-kokoro",
    },
    "BOOM-light": {
        "templates": ["middleware", "asr", "tts", "dialog", "markup", "boom"],
        "backend_components": ["stt", "tts"],
        "used_urls": [
            "stt",
            "mt",
            "tts",
            "summarizer",
            "text_structurer_online",
            "text_structurer_offline",
            "llm",
        ],
        "use_slt": True,
        "slide_support": True,
        "default_mt_backend_engine": None,
        "default_tts_backend_engine": "tts-kokoro",
    },
    "BOOM": {
        "templates": ["middleware", "asr", "tts", "dialog", "markup", "boom"],
        "backend_components": ["stt", "tts"],
        "used_urls": [
            "stt",
            "mt",
            "tts",
            "summarizer",
            "text_structurer_online",
            "text_structurer_offline",
            "llm",
        ],
        "use_slt": True,
        "slide_support": True,
        "default_mt_backend_engine": None,
        "default_tts_backend_engine": "tts-kokoro",
    },
}


def get_pipeline_types() -> List[str]:
    return list(PIPELINE_DEFINITIONS.keys())


def has_pipeline_type(pipeline_type: str) -> bool:
    return pipeline_type in PIPELINE_DEFINITIONS


def get_pipeline_templates(pipeline_type: str) -> List[str]:
    return list(PIPELINE_DEFINITIONS[pipeline_type]["templates"])


def get_backend_components(pipeline_type: str) -> List[str]:
    return list(PIPELINE_DEFINITIONS[pipeline_type]["backend_components"])


def uses_url(pipeline_type: str, url_key: str) -> bool:
    definition = PIPELINE_DEFINITIONS.get(pipeline_type)
    if not definition:
        return False
    return url_key in definition["used_urls"]


def uses_slt(pipeline_type: str) -> bool:
    definition = PIPELINE_DEFINITIONS.get(pipeline_type)
    return bool(definition and definition["use_slt"])


def slide_support_enabled(pipeline_type: str) -> bool:
    definition = PIPELINE_DEFINITIONS.get(pipeline_type)
    return bool(definition and definition["slide_support"])


def default_mt_backend_engine(pipeline_type: str) -> Optional[str]:
    definition = PIPELINE_DEFINITIONS.get(pipeline_type)
    if not definition:
        return None
    return definition["default_mt_backend_engine"]


def default_tts_backend_engine(pipeline_type: str) -> Optional[str]:
    definition = PIPELINE_DEFINITIONS.get(pipeline_type)
    if not definition:
        return None
    return definition["default_tts_backend_engine"]
