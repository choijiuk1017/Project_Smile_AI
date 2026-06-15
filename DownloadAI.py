from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    LlavaOnevisionProcessor,
    LlavaOnevisionForConditionalGeneration
)
from sentence_transformers import SentenceTransformer

LlavaOnevisionProcessor.from_pretrained(
    "llava-hf/llava-onevision-qwen2-0.5b-ov-hf"
)

LlavaOnevisionForConditionalGeneration.from_pretrained(
    "llava-hf/llava-onevision-qwen2-0.5b-ov-hf"
)

AutoTokenizer.from_pretrained(
    "google/gemma-4-E2B-it"
)

AutoModelForCausalLM.from_pretrained(
    "google/gemma-4-E2B-it"
)

SentenceTransformer(
    "sentence-transformers/all-MiniLM-L6-v2"
)

print("다운로드 완료")