from flask import Flask, request, jsonify
from PIL import Image
import io
import json
import torch
import logging
import numpy as np

from typing import TypedDict, List, Dict, Any

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from transformers import (
    LlavaOnevisionProcessor,
    LlavaOnevisionForConditionalGeneration,
    AutoTokenizer,
    AutoModelForCausalLM,
)

from peft import PeftModel
from langgraph.graph import StateGraph, START, END


logging.getLogger("transformers").setLevel(logging.ERROR)


RAG_DATA_PATH = "puzzle_docs.json"

LLAVA_MODEL_ID = "llava-hf/llava-onevision-qwen2-0.5b-ov-hf"
GEMMA_MODEL_ID = "google/gemma-4-E2B-it"

# 사건 일지 JSON 생성용 LoRA
LORA_PATH = "gemma_journal_lora"

RETRIEVAL_MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"

device = "cuda" if torch.cuda.is_available() else "cpu"
dtype = torch.float16 if torch.cuda.is_available() else torch.float32

app = Flask(__name__)

# 시연 환경이 느리면 False로 바꾸면 검증 단계를 건너뜁니다.
USE_JOURNAL_VALIDATION = True


# RAG 문서 로드 및 검색용 데이터 정규화
def load_rag_data(path):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read().strip()

    if not text:
        raise ValueError("RAG data is empty.")

    data = json.loads(text)
    normalized = []

    for idx, item in enumerate(data, start=1):
        required_keys = ["scene_type", "facts", "hint_examples"]

        for key in required_keys:
            if key not in item:
                raise ValueError(f"RAG data missing key '{key}' at item {idx}")

        facts = item.get("facts", [])
        hint_examples = item.get("hint_examples", [])

        search_scenes = item.get("search_scenes")

        if not search_scenes:
            single = item.get("search_scene", "")
            search_scenes = [single] if single else []

        if not search_scenes:
            raise ValueError(f"RAG data missing search_scene/search_scenes at item {idx}")

        rag_text = " ".join(facts)

        reference_answer = (
            hint_examples[0]
            if hint_examples
            else "지금 보이는 것만으로는 확실한 단서를 찾기 어렵다."
        )

        answer = (
            hint_examples[1]
            if len(hint_examples) > 1
            else reference_answer
        )

        for search_scene in search_scenes:
            normalized.append({
                "id": item.get("id", ""),
                "area_id": item.get("area_id", ""),
                "scene_type": item["scene_type"],
                "spoiler_level": item.get("spoiler_level", 1),
                "scene": search_scene,
                "rag": rag_text,
                "reference_answer": reference_answer,
                "answer": answer,
                "reasoning_policy": item.get("reasoning_policy", ""),
                "hint_by_level": item.get("hint_by_level", {}),
                "director_tags": item.get("director_tags", []),
                "director_action": item.get("director_action", {}),
                "journal": item.get("journal", {}),
            })

    if not normalized:
        raise ValueError("RAG data is empty.")

    return normalized


rag_data = load_rag_data(RAG_DATA_PATH)


print("Loading LLaVA...")
llava_processor = LlavaOnevisionProcessor.from_pretrained(LLAVA_MODEL_ID)
llava_model = LlavaOnevisionForConditionalGeneration.from_pretrained(
    LLAVA_MODEL_ID,
    dtype=dtype,
    device_map="auto",
)
llava_model.eval()


print("Loading Retrieval Embedding Model...")
retrieval_model = SentenceTransformer(RETRIEVAL_MODEL_ID)


print("Loading Gemma Base...")
tokenizer = AutoTokenizer.from_pretrained(GEMMA_MODEL_ID)

if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

base_model = AutoModelForCausalLM.from_pretrained(
    GEMMA_MODEL_ID,
    dtype=dtype,
    device_map="auto",
)


print("Loading Gemma Journal LoRA...")
gemma_model = PeftModel.from_pretrained(base_model, LORA_PATH)
gemma_model.eval()


LLAVA_PROMPT = (
    "Describe only what is visibly present in the image. "
    "Do not infer gameplay, objectives, solutions, story, danger, or player actions. "
    "Do not say 'the player must', 'suggesting', 'trapped', or 'navigate'. "
    "Do not guess that an object is a keycard unless it is clearly visible as a card. "
    "Mention only visible objects, colors, positions, and scene elements. "
    "Write one short English sentence."
)


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
"""


DEFAULT_REASONING_POLICY = """RAG 정보의 의미를 유지한다.
새 물체, 해결 방법, 행동 지시를 추가하지 않는다.
관찰, 추론, 결론, 힌트를 서로 다른 역할로 작성한다."""


# 이미지 크기 축소
def resize_image(image, max_size=384):
    image.thumbnail((max_size, max_size))
    return image


# LLaVA를 이용한 상황 분석
def analyze_image_with_llava(image_bytes):
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    image = resize_image(image)

    conversation = [
        {
            "role": "user",
            "content": [
                {"type": "image"},
                {"type": "text", "text": LLAVA_PROMPT},
            ],
        }
    ]

    prompt = llava_processor.apply_chat_template(
        conversation,
        add_generation_prompt=True,
    )

    inputs = llava_processor(
        images=image,
        text=prompt,
        return_tensors="pt",
    ).to(llava_model.device)

    with torch.no_grad():
        output = llava_model.generate(
            **inputs,
            max_new_tokens=80,
            do_sample=False,
        )

    generated = output[0][inputs["input_ids"].shape[-1]:]

    scene = llava_processor.decode(
        generated,
        skip_special_tokens=True,
    ).strip()

    return scene


# 현재 구역에 맞는 RAG 문서만 검색
def retrieve_best_rag(scene_text, area_id=None, top_k=3):
    candidate_indices = []

    for idx, item in enumerate(rag_data):
        if area_id is None or area_id == "Unknown":
            candidate_indices.append(idx)
        elif item.get("area_id", "") == area_id:
            candidate_indices.append(idx)

    if not candidate_indices:
        candidate_indices = list(range(len(rag_data)))

    candidate_texts = [rag_data[idx]["scene"] for idx in candidate_indices]

    candidate_embeddings = retrieval_model.encode(
        candidate_texts,
        normalize_embeddings=True,
    )

    query_embedding = retrieval_model.encode(
        [scene_text],
        normalize_embeddings=True,
    )

    scores = cosine_similarity(query_embedding, candidate_embeddings)[0]

    top_local_indices = np.argsort(scores)[::-1][:top_k]

    results = []

    for local_idx in top_local_indices:
        rag_idx = candidate_indices[local_idx]
        item = rag_data[rag_idx]
        score = float(scores[local_idx])

        results.append({
            "score": score,
            "id": item.get("id", ""),
            "area_id": item.get("area_id", ""),
            "scene_type": item.get("scene_type", "unknown"),
            "scene": item["scene"],
            "rag": item["rag"],
            "reference_answer": item["reference_answer"],
            "answer": item.get("answer", item["reference_answer"]),
            "reasoning_policy": item.get(
                "reasoning_policy",
                DEFAULT_REASONING_POLICY,
            ) or DEFAULT_REASONING_POLICY,
            "hint_by_level": item.get("hint_by_level", {}),
            "director_tags": item.get("director_tags", []),
            "director_action": item.get("director_action", {}),
            "journal": item.get("journal", {}),
        })

    return results


# RAG 검색 결과 중 최종 사용할 문서 선택
def select_primary_rag(rag_results, threshold=0.55):
    if not rag_results:
        return {
            "score": 0.0,
            "scene_type": "unknown",
            "scene": "",
            "rag": "단서 없음",
            "reference_answer": "지금 보이는 것만으로는 확실한 단서를 찾기 어렵다.",
            "answer": "지금 보이는 것만으로는 확실한 단서를 찾기 어렵다.",
            "reasoning_policy": DEFAULT_REASONING_POLICY,
            "hint_by_level": {},
            "journal": {},
        }

    primary = rag_results[0]

    if primary["score"] < threshold:
        return {
            "score": primary["score"],
            "scene_type": "no_clue",
            "scene": primary["scene"],
            "rag": "현재 장면에서는 직접적인 단서가 확인되지 않는다.",
            "reference_answer": "지금 보이는 것만으로는 확실한 단서를 찾기 어렵다.",
            "answer": "지금 보이는 것만으로는 확실한 단서를 찾기 어렵다.",
            "reasoning_policy": DEFAULT_REASONING_POLICY,
            "hint_by_level": {
                "1": "지금 보이는 것만으로는 확실한 단서를 찾기 어렵다.",
                "2": "이 장면만으로는 판단할 정보가 부족하다.",
                "3": "현재 시야에는 직접적인 단서가 없으니 다른 대상을 기준으로 판단해야 할 것 같다.",
            },
            "journal": {},
        }

    return primary


# 검색 후보를 로그 및 디버깅용 문자열로 정리
def build_rag_context(rag_results):
    lines = []

    for idx, item in enumerate(rag_results, start=1):
        lines.append(f"[검색 후보 {idx}]")
        lines.append(f"score: {item['score']:.4f}")
        lines.append(f"scene_type: {item.get('scene_type', 'unknown')}")
        lines.append(f"reference_scene: {item['scene']}")
        lines.append(f"rag: {item['rag']}")
        lines.append(f"reference_answer: {item['reference_answer']}")
        lines.append("")

    return "\n".join(lines).strip()


# AI Director가 힌트 강도 결정
def decide_hint_level(hint_count, area_stay_time):
    if hint_count >= 10:
        return 3

    if hint_count >= 5:
        return 2

    return 1


# Gemma 사건 일지 생성 프롬프트 생성
def build_journal_prompt(scene, rag, reference_answer, reasoning_policy=None, hint_count=1):
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

[힌트 요청 횟수]
{hint_count}

현재 장면을 바탕으로 사건 일지를 JSON 형식으로 출력하라.<end_of_turn>
<start_of_turn>model
"""


# Gemma 출력에서 JSON만 추출
def extract_json_object(text):
    text = text.strip()

    decoder = json.JSONDecoder()

    start = text.find("{")
    if start == -1:
        raise ValueError("JSON object not found in model output.")

    obj, end = decoder.raw_decode(text[start:])

    if not isinstance(obj, dict):
        raise ValueError("Decoded JSON is not an object.")

    return obj


# 빈 값 방지용 fallback 사건 일지
def make_fallback_journal(area_id, primary_rag, hint, hint_level, scene_text):
    scene_type = primary_rag.get("scene_type", "unknown")
    rag = primary_rag.get("rag", "현재 장면에서는 직접적인 단서가 확인되지 않는다.")

    title_map = {
        "spawn_corpse": "의문의 시체",
        "hallway_corpses": "복도의 시체들",
        "locked_private_door": "잠긴 PRIVATE 문",
        "rest_area": "직원 휴게 공간",
        "office_desk": "사무 공간",
        "blood_stains_only": "핏자국",
        "keycard": "수상한 출입 카드",
        "bright_hall": "중앙 로비",
        "locked_door": "잠긴 문",
        "machine_area": "기계 주변의 흔적",
        "note_on_chair": "의자 위의 노트",
        "keycard_on_chair": "의자 위의 키카드",
        "two_chairs": "기계 옆 의자",
        "spare_fuse": "남겨진 퓨즈",
        "dark_corridor_switch_fusebox": "어두운 복도와 퓨즈 박스",
        "research_room_overview": "흩어진 연구실",
        "monster_file": "몬스터 정보 파일",
        "no_clue": "불확실한 장면",
    }

    title = title_map.get(scene_type, scene_type)

    return {
        "title": title,
        "area": area_id,
        "scene_type": scene_type,
        "observation": rag,
        "reasoning": hint,
        "conclusion": hint,
        "hint": hint,
        "hint_level": hint_level,
        "matched_score": primary_rag.get("score", 0.0),
        "scene": scene_text,
    }


# Gemma-LoRA를 이용한 사건 일지 + 힌트 생성
def generate_journal(scene_text, rag_results, hint_level=1, hint_count=1):
    primary_rag = select_primary_rag(rag_results)
    rag_context = build_rag_context(rag_results)

    hint_by_level = primary_rag.get("hint_by_level", {})
    level_key = str(hint_level)

    selected_reference_answer = primary_rag.get(
        "reference_answer",
        "지금 보이는 것만으로는 확실한 단서를 찾기 어렵다."
    )

    if hint_by_level and level_key in hint_by_level:
        selected_reference_answer = hint_by_level[level_key]

    # no_clue는 모델 생성이 이상해질 수 있어서 fallback 중심
    if primary_rag.get("scene_type") == "no_clue":
        hint = selected_reference_answer

        journal_file = make_fallback_journal(
            area_id=primary_rag.get("area_id", ""),
            primary_rag=primary_rag,
            hint=hint,
            hint_level=hint_level,
            scene_text=scene_text,
        )

        journal_file["validation_passed"] = True
        journal_file["validation_result"] = "NO_CLUE_FALLBACK"

        return hint, journal_file, primary_rag, rag_context

    prompt = build_journal_prompt(
        scene=scene_text,
        rag=primary_rag["rag"],
        reference_answer=selected_reference_answer,
        reasoning_policy=primary_rag.get("reasoning_policy", DEFAULT_REASONING_POLICY),
        hint_count=hint_count,
    )

    inputs = tokenizer(
        prompt,
        return_tensors="pt",
        add_special_tokens=False,
    ).to(gemma_model.device)

    with torch.no_grad():
        output = gemma_model.generate(
            **inputs,
            max_new_tokens=120,
            do_sample=False,
            repetition_penalty=1.05,
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )

    generated_ids = output[0][inputs["input_ids"].shape[-1]:]

    result = tokenizer.decode(
        generated_ids,
        skip_special_tokens=True,
    ).strip()

    try:
        journal_json = extract_json_object(result)

        title = str(journal_json.get("title", "")).strip()
        observation = str(journal_json.get("observation", "")).strip()
        reasoning = str(journal_json.get("reasoning", "")).strip()
        conclusion = str(journal_json.get("conclusion", "")).strip()
        hint = str(journal_json.get("hint", "")).strip()

        if not title:
            title = primary_rag.get("scene_type", "unknown")

        if not observation:
            observation = primary_rag.get("rag", "")

        if not reasoning:
            reasoning = selected_reference_answer

        if not conclusion:
            conclusion = selected_reference_answer

        if not hint:
            hint = selected_reference_answer

        investigation_file = {
            "title": title,
            "area": primary_rag.get("area_id", ""),
            "scene_type": primary_rag.get("scene_type", "unknown"),
            "observation": observation,
            "reasoning": reasoning,
            "conclusion": conclusion,
            "hint": hint,
            "hint_level": hint_level,
            "matched_score": primary_rag.get("score", 0.0),
            "scene": scene_text,
        }

        if USE_JOURNAL_VALIDATION:
            passed, validation_result = validate_journal_with_ai(
                scene_text=scene_text,
                rag=primary_rag.get("rag", ""),
                investigation_file=investigation_file,
            )
        else:
            passed, validation_result = True, "SKIPPED"

        investigation_file["validation_passed"] = passed
        investigation_file["validation_result"] = validation_result

        if not passed:
            print("JOURNAL VALIDATION FAILED:", validation_result)

            fallback_hint = selected_reference_answer

            fallback_file = make_fallback_journal(
                area_id=primary_rag.get("area_id", ""),
                primary_rag=primary_rag,
                hint=fallback_hint,
                hint_level=hint_level,
                scene_text=scene_text,
            )

            fallback_file["validation_passed"] = False
            fallback_file["validation_result"] = validation_result

            return fallback_hint, fallback_file, primary_rag, rag_context

        return hint, investigation_file, primary_rag, rag_context

    except Exception as e:
        print("JOURNAL JSON PARSE FAILED:", str(e))
        print("RAW OUTPUT:", result)

        fallback_hint = selected_reference_answer

        investigation_file = make_fallback_journal(
            area_id=primary_rag.get("area_id", ""),
            primary_rag=primary_rag,
            hint=fallback_hint,
            hint_level=hint_level,
            scene_text=scene_text,
        )

        investigation_file["validation_passed"] = False
        investigation_file["validation_result"] = "JSON_PARSE_FAILED"

        return fallback_hint, investigation_file, primary_rag, rag_context


# Gemma를 이용한 사건 일지 검증
def validate_journal_with_ai(scene_text, rag, investigation_file):
    validation_prompt = f"""<start_of_turn>user
너는 공포 퍼즐 게임의 AI 사건 일지 검수자다.
다음 사건 일지가 출력해도 되는지 판단하라.

[장면]
{scene_text}

[RAG 정보]
{rag}

[사건 일지]
{json.dumps(investigation_file, ensure_ascii=False)}

PASS 기준:
- 사건 일지가 RAG 정보와 의미상 맞으면 PASS
- 관찰, 추론, 결론, 힌트가 서로 역할이 나뉘어 있으면 PASS
- RAG의 내용을 다른 표현으로 말한 정도면 PASS
- 공포 퍼즐 게임의 사건 기록처럼 자연스러우면 PASS

FAIL 기준:
- RAG에 없는 물체, 위치, 해결 방법을 새로 만들면 FAIL
- RAG에 없는 몬스터, 괴물, 실험체를 단정하면 FAIL
- '~하자', '~해야 한다', '~찾아야 한다', '~확인해야 한다' 같은 행동 지시가 있으면 FAIL
- observation, reasoning, conclusion, hint가 거의 같은 문장이면 FAIL
- JSON 필드가 비어 있으면 FAIL
- 문장이 한국어로 어색해서 의미가 이상하면 FAIL

주의:
- 너무 엄격하게 판단하지 마라.
- 애매하면 PASS로 판단하라.
- 출력은 반드시 PASS 또는 FAIL 한 단어만 써라.<end_of_turn>
<start_of_turn>model
"""

    inputs = tokenizer(
        validation_prompt,
        return_tensors="pt",
        add_special_tokens=False,
    ).to(gemma_model.device)

    with torch.no_grad():
        output = gemma_model.generate(
            **inputs,
            max_new_tokens=8,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )

    generated_ids = output[0][inputs["input_ids"].shape[-1]:]

    result = tokenizer.decode(
        generated_ids,
        skip_special_tokens=True,
    ).strip().upper()

    if "FAIL" in result:
        return False, result

    return True, result


class HintGraphState(TypedDict):
    area_id: str
    image_bytes: bytes
    scene: str
    rag_results: List[Dict[str, Any]]
    hint: str
    investigation_file: Dict[str, Any]
    primary_rag: Dict[str, Any]
    rag_context: str
    hint_count: int
    play_time: float
    area_stay_time: float
    objective_id: str
    last_interaction: str
    hint_level: int


# LangGraph 노드: 이미지 분석
def node_analyze_image(state: HintGraphState) -> dict:
    print("[LangGraph] node_analyze_image 실행")

    scene = analyze_image_with_llava(state["image_bytes"])

    return {
        "scene": scene,
    }


# LangGraph 노드: RAG 검색
def node_retrieve_rag(state: HintGraphState) -> dict:
    print("[LangGraph] node_retrieve_rag 실행")

    rag_results = retrieve_best_rag(
        scene_text=state["scene"],
        area_id=state["area_id"],
        top_k=3,
    )

    return {
        "rag_results": rag_results,
    }


# LangGraph 노드: 플레이어 상태 기반 힌트 단계 결정
def node_decide_hint_level(state: HintGraphState) -> dict:
    print("[LangGraph] node_decide_hint_level 실행")

    hint_level = decide_hint_level(
        hint_count=state["hint_count"],
        area_stay_time=state["area_stay_time"],
    )

    return {
        "hint_level": hint_level,
    }


# LangGraph 노드: 사건 일지와 힌트 생성
def node_generate_journal(state: HintGraphState) -> dict:
    print("[LangGraph] node_generate_journal 실행")

    hint, investigation_file, primary_rag, rag_context = generate_journal(
        scene_text=state["scene"],
        rag_results=state["rag_results"],
        hint_level=state["hint_level"],
        hint_count=state["hint_count"],
    )

    return {
        "hint": hint,
        "investigation_file": investigation_file,
        "primary_rag": primary_rag,
        "rag_context": rag_context,
    }


# LangGraph 워크플로우 구성
def build_hint_graph():
    graph = StateGraph(HintGraphState)

    graph.add_node("analyze_image", node_analyze_image)
    graph.add_node("retrieve_rag", node_retrieve_rag)
    graph.add_node("decide_hint_level", node_decide_hint_level)
    graph.add_node("generate_journal", node_generate_journal)

    graph.add_edge(START, "analyze_image")
    graph.add_edge("analyze_image", "retrieve_rag")
    graph.add_edge("retrieve_rag", "decide_hint_level")
    graph.add_edge("decide_hint_level", "generate_journal")
    graph.add_edge("generate_journal", END)

    return graph.compile()


hint_graph = build_hint_graph()


# Unreal에서 이미지와 플레이어 상태를 받아 힌트와 사건 일지 반환
@app.route("/predict", methods=["POST"])
def predict():
    try:
        print("REQUEST RECEIVED")

        area_id = request.headers.get("X-Area-Id", "Unknown")
        objective_id = request.headers.get("X-Objective-Id", "Unknown")
        last_interaction = request.headers.get("X-Last-Interaction", "None")

        hint_count = int(request.headers.get("X-Hint-Count", "1"))
        play_time = float(request.headers.get("X-Play-Time", "0"))
        area_stay_time = float(request.headers.get("X-Area-Stay-Time", "0"))

        image_bytes = request.data

        if not image_bytes:
            return jsonify({"error": "이미지 없음"}), 400

        graph_result = hint_graph.invoke({
            "area_id": area_id,
            "image_bytes": image_bytes,
            "scene": "",
            "rag_results": [],
            "hint": "",
            "investigation_file": {},
            "primary_rag": {},
            "rag_context": "",
            "hint_count": hint_count,
            "play_time": play_time,
            "area_stay_time": area_stay_time,
            "objective_id": objective_id,
            "last_interaction": last_interaction,
            "hint_level": 1,
        })

        scene = graph_result["scene"]
        rag_results = graph_result["rag_results"]
        hint = graph_result["hint"]
        investigation_file = graph_result["investigation_file"]
        primary_rag = graph_result["primary_rag"]
        hint_level = graph_result["hint_level"]

        print("AREA:", area_id)
        print("OBJECTIVE:", objective_id)
        print("LAST_INTERACTION:", last_interaction)
        print("HINT_COUNT:", hint_count)
        print("PLAY_TIME:", play_time)
        print("AREA_STAY_TIME:", area_stay_time)
        print("HINT_LEVEL:", hint_level)

        print("SCENE:", scene)
        print("MATCHED_SCENE_TYPE:", primary_rag.get("scene_type", "unknown"))
        print("MATCHED_SCORE:", primary_rag.get("score", 0.0))
        print("MATCHED_REFERENCE_SCENE:", primary_rag.get("scene", ""))
        print("RAG:", primary_rag.get("rag", ""))
        print("REFERENCE_ANSWER:", primary_rag.get("reference_answer", ""))
        print("HINT:", hint)
        print("INVESTIGATION_FILE:", investigation_file)

        return jsonify({
            "area": area_id,
            "objective": objective_id,
            "last_interaction": last_interaction,
            "hint_count": hint_count,
            "play_time": play_time,
            "area_stay_time": area_stay_time,
            "hint_level": hint_level,
            "scene": scene,
            "matched_scene_type": primary_rag.get("scene_type", "unknown"),
            "matched_score": primary_rag.get("score", 0.0),
            "matched_reference_scene": primary_rag.get("scene", ""),
            "rag": primary_rag.get("rag", ""),
            "reference_answer": primary_rag.get("reference_answer", ""),
            "hint": hint,
            "investigation_file": investigation_file,
            "rag_candidates": rag_results,
            "langgraph_flow": [
                "analyze_image",
                "retrieve_rag",
                "decide_hint_level",
                "generate_journal",
            ],
        })

    except Exception as e:
        print("ERROR:", str(e))
        return jsonify({"error": str(e)}), 500


# 텍스트 장면만 넣어서 RAG 검색 테스트
@app.route("/test_rag", methods=["POST"])
def test_rag():
    try:
        data = request.get_json()

        if not data or "scene" not in data:
            return jsonify({"error": "scene 값이 없습니다."}), 400

        scene = data["scene"]
        area_id = data.get("area_id", None)

        rag_results = retrieve_best_rag(
            scene_text=scene,
            area_id=area_id,
            top_k=3,
        )

        primary_rag = select_primary_rag(rag_results)

        return jsonify({
            "scene": scene,
            "matched_scene_type": primary_rag.get("scene_type", "unknown"),
            "matched_score": primary_rag.get("score", 0.0),
            "matched_reference_scene": primary_rag.get("scene", ""),
            "rag": primary_rag.get("rag", ""),
            "reference_answer": primary_rag.get("reference_answer", ""),
            "hint_by_level": primary_rag.get("hint_by_level", {}),
            "rag_candidates": rag_results,
        })

    except Exception as e:
        print("ERROR:", str(e))
        return jsonify({"error": str(e)}), 500


# 텍스트 장면으로 LangGraph 사건 일지 생성 테스트
@app.route("/test_graph", methods=["POST"])
def test_graph():
    try:
        data = request.get_json()

        if not data or "scene" not in data:
            return jsonify({"error": "scene 값이 없습니다."}), 400

        scene = data["scene"]
        hint_count = int(data.get("hint_count", 1))
        area_stay_time = float(data.get("area_stay_time", 0))
        area_id = data.get("area_id", None)

        rag_results = retrieve_best_rag(
            scene_text=scene,
            area_id=area_id,
            top_k=3,
        )

        hint_level = decide_hint_level(
            hint_count=hint_count,
            area_stay_time=area_stay_time,
        )

        hint, investigation_file, primary_rag, rag_context = generate_journal(
            scene_text=scene,
            rag_results=rag_results,
            hint_level=hint_level,
            hint_count=hint_count,
        )

        return jsonify({
            "scene": scene,
            "hint_count": hint_count,
            "area_stay_time": area_stay_time,
            "hint_level": hint_level,
            "matched_scene_type": primary_rag.get("scene_type", "unknown"),
            "matched_score": primary_rag.get("score", 0.0),
            "matched_reference_scene": primary_rag.get("scene", ""),
            "rag": primary_rag.get("rag", ""),
            "reference_answer": primary_rag.get("reference_answer", ""),
            "hint": hint,
            "investigation_file": investigation_file,
            "rag_candidates": rag_results,
            "langgraph_note": "이미지 분석 없이 RAG 검색과 사건 일지 생성을 테스트합니다.",
        })

    except Exception as e:
        print("ERROR:", str(e))
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print(f"Using device: {device}")
    print(f"Loaded RAG docs: {len(rag_data)}")
    print("LangGraph Flow: analyze_image -> retrieve_rag -> decide_hint_level -> generate_journal")
    print("Server Start")
    app.run(host="0.0.0.0", port=5000)