import json
import torch

from datasets import load_dataset

from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    TrainingArguments,
    Trainer,
)

from peft import LoraConfig, get_peft_model


MODEL_ID = "google/gemma-4-E2B-it"
DATA_PATH = "lora_hint.jsonl"
OUTPUT_DIR = "gemma_journal_lora"

MAX_LENGTH = 512

SYSTEM_PROMPT = """너는 공포 퍼즐 게임의 AI 사건 기록 시스템이다.

반드시 지켜라:
- 현재 장면과 RAG 정보만 근거로 사건 일지를 작성한다.
- RAG에 없는 물체, 위치, 해결 방법을 만들지 않는다.
- 행동 지시를 하지 않는다.
- 관찰은 화면에서 보이는 사실 중심으로 쓴다.
- 추론은 관찰을 바탕으로 한 가능성으로 쓴다.
- 결론은 플레이어가 기록한 짧은 판단처럼 쓴다.
- hint는 인게임에 바로 출력할 짧은 주인공 독백 한 문장으로 쓴다.
- 반드시 JSON만 출력한다.
- JSON 키는 title, observation, reasoning, conclusion, hint만 사용한다.

좋은 출력:
{
  "title": "의문의 시체",
  "observation": "바닥에 한 명의 사람이 쓰러져 있고 주변에 핏자국이 남아 있다.",
  "reasoning": "단순히 넘어진 것이 아니라 누군가에게 공격받은 흔적처럼 보인다.",
  "conclusion": "이곳에서 이미 위험한 일이 벌어진 것 같다.",
  "hint": "저 사람... 그냥 쓰러진 건 아닌 것 같다."
}

나쁜 출력:
책상을 조사해보자.
키카드를 찾아야 한다.
RAG에 없는 괴물이 근처에 있다.
"""


DEFAULT_REASONING_POLICY = (
    "RAG 정보의 의미를 유지한다. "
    "새 물체, 해결 방법, 행동 지시를 추가하지 않는다. "
    "관찰, 추론, 결론, 힌트를 서로 다른 역할로 작성한다."
)


def build_prompt(scene, rag, reference_answer, reasoning_policy=None):
    if reasoning_policy is None or str(reasoning_policy).strip() == "":
        reasoning_policy = DEFAULT_REASONING_POLICY

    return f"""<start_of_turn>user
{SYSTEM_PROMPT}

[장면]
{scene}

[RAG 정보]
{rag}

[기준 힌트]
{reference_answer}

[추론 규칙]
{reasoning_policy}

현재 장면을 바탕으로 사건 일지를 JSON 형식으로 출력하라.<end_of_turn>
<start_of_turn>model
"""


class CausalLMCollator:
    def __init__(self, tokenizer):
        self.tokenizer = tokenizer

    def __call__(self, features):
        max_len = max(len(f["input_ids"]) for f in features)

        input_ids_list = []
        attention_mask_list = []
        labels_list = []

        for f in features:
            pad_len = max_len - len(f["input_ids"])

            input_ids_list.append(
                f["input_ids"] + [self.tokenizer.pad_token_id] * pad_len
            )
            attention_mask_list.append(
                f["attention_mask"] + [0] * pad_len
            )
            labels_list.append(
                f["labels"] + [-100] * pad_len
            )

        return {
            "input_ids": torch.tensor(input_ids_list, dtype=torch.long),
            "attention_mask": torch.tensor(attention_mask_list, dtype=torch.long),
            "labels": torch.tensor(labels_list, dtype=torch.long),
        }


def build_language_model_targets():
    targets = []

    for i in range(35):
        base = f"language_model.layers.{i}"

        targets.append(f"{base}.self_attn.q_proj")
        targets.append(f"{base}.self_attn.v_proj")
        targets.append(f"{base}.self_attn.o_proj")

    return targets


def main():
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    tokenizer.padding_side = "right"

    dtype = (
        torch.bfloat16
        if torch.cuda.is_available() and torch.cuda.is_bf16_supported()
        else torch.float16
    )

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        dtype=dtype,
        device_map="auto",
        low_cpu_mem_usage=True,
    )

    model.config.use_cache = False

    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=build_language_model_targets(),
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )

    model = get_peft_model(model, lora_config)

    model.train()
    model.enable_input_require_grads()
    model.print_trainable_parameters()

    def tokenize(example):
        prompt = build_prompt(
            scene=example["scene"],
            rag=example["rag"],
            reference_answer=example["reference_answer"],
            reasoning_policy=example.get("reasoning_policy", DEFAULT_REASONING_POLICY),
        )

        answer_obj = {
            "title": example["title"],
            "observation": example["observation"],
            "reasoning": example["reasoning"],
            "conclusion": example["conclusion"],
            "hint": example["hint"],
        }

        answer = json.dumps(answer_obj, ensure_ascii=False) + tokenizer.eos_token

        prompt_ids = tokenizer(
            prompt,
            add_special_tokens=False,
        )["input_ids"]

        answer_ids = tokenizer(
            answer,
            add_special_tokens=False,
        )["input_ids"]

        input_ids = prompt_ids + answer_ids
        labels = [-100] * len(prompt_ids) + answer_ids
        attention_mask = [1] * len(input_ids)

        input_ids = input_ids[:MAX_LENGTH]
        labels = labels[:MAX_LENGTH]
        attention_mask = attention_mask[:MAX_LENGTH]

        return {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "labels": labels,
        }

    dataset = load_dataset(
        "json",
        data_files=DATA_PATH,
        split="train",
    )

    dataset = dataset.map(
        tokenize,
        remove_columns=dataset.column_names,
    )

    collator = CausalLMCollator(tokenizer)

    test_batch = collator([dataset[0]])
    test_batch = {
        k: v.to(model.device)
        for k, v in test_batch.items()
    }

    output = model(**test_batch)
    print("LOSS:", output.loss.item())
    print("LOSS REQUIRES GRAD:", output.loss.requires_grad)

    output.loss.backward()

    found_grad = False

    for name, param in model.named_parameters():
        if param.requires_grad:
            grad_sum = 0.0 if param.grad is None else param.grad.abs().sum().item()

            if grad_sum > 0:
                print("GRAD CHECK OK:", name, grad_sum)
                found_grad = True
                break

    if not found_grad:
        raise RuntimeError("LoRA gradient가 0입니다.")

    model.zero_grad(set_to_none=True)

    args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=8,
        learning_rate=6e-5,
        num_train_epochs=2,
        logging_steps=1,
        save_strategy="epoch",
        save_total_limit=1,
        fp16=(dtype == torch.float16),
        bf16=(dtype == torch.bfloat16),
        optim="adamw_torch",
        report_to="none",
        remove_unused_columns=False,
        max_grad_norm=1.0,
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=dataset,
        data_collator=collator,
    )

    trainer.train()

    model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)

    print(f"LoRA saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()