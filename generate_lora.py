import json
import random

OUTPUT_PATH = "lora_journal_hint_reasoning_policy.jsonl"
RANDOM_SEED = 42

random.seed(RANDOM_SEED)

scene_types = {
    "spawn_corpse": {
        "area_id": "TutorialZone",
        "scenes": [
            "A single body is lying on the floor in a dark room.",
            "One person is lying motionless on the ground.",
            "Only one body is visible near a staircase."
        ],
        "rag": "방 안에 한 명의 시체가 쓰러져 있다. 주변에는 핏자국이 남아 있다. 단순히 넘어진 것이 아니라 공격받은 흔적으로 보인다.",
        "reference": "저 사람... 그냥 쓰러진 건 아닌 것 같다.",
        "reasoning_policy": "장면에 보이는 사람은 한 명이다. 여러 명이 쓰러져 있다고 말하지 않는다.",
        "titles": ["의문의 시체", "쓰러진 사람"],
        "observations": [
            "바닥에 한 명의 사람이 쓰러져 있고 주변에는 핏자국이 남아 있다.",
            "어두운 방 안에 움직임 없는 사람이 보인다."
        ],
        "reasonings": [
            "단순히 넘어진 것이 아니라 누군가에게 공격받은 흔적처럼 보인다.",
            "주변의 핏자국을 보면 사고보다는 외부 공격 가능성이 있어 보인다."
        ],
        "conclusions": [
            "저 사람은 그냥 쓰러진 게 아닌 것 같다.",
            "이곳에서 이미 위험한 일이 벌어진 것 같다."
        ],
        "hints": [
            "저 사람... 그냥 쓰러진 건 아닌 것 같다.",
            "피가 주변에 튄 걸 보면... 공격받은 흔적처럼 보인다."
        ]
    },

    "locked_private_door": {
        "area_id": "TutorialZone",
        "scenes": [
            "A black door labeled PRIVATE is visible.",
            "A secured door with a keypad or access device is visible.",
            "A locked-looking door with an access panel is visible."
        ],
        "rag": "문에는 PRIVATE 표시가 있다. 문 옆에는 키패드 같은 장치가 있다. 문은 잠긴 상태일 가능성이 높다.",
        "reference": "PRIVATE라... 그냥 열 수 있는 문은 아닌 것 같다.",
        "reasoning_policy": "PRIVATE 표시와 문 옆 장치를 근거로 추론한다. 행동 지시를 하지 않는다.",
        "titles": ["PRIVATE 문", "잠긴 문"],
        "observations": [
            "문에는 PRIVATE 표시가 있고 옆에는 인증 장치처럼 보이는 장치가 있다.",
            "문 옆에 출입을 확인하는 장치처럼 보이는 물체가 붙어 있다."
        ],
        "reasonings": [
            "이 문은 일반적인 방식으로 열리는 문이 아니라 출입 권한을 요구하는 구조처럼 보인다.",
            "PRIVATE 표시와 장치를 보면 제한된 구역으로 연결된 문일 가능성이 높다."
        ],
        "conclusions": [
            "이 문은 그냥 열 수 있는 문이 아닌 것 같다.",
            "출입 권한 없이는 지나가기 어려워 보인다."
        ],
        "hints": [
            "PRIVATE라... 그냥 열 수 있는 문은 아닌 것 같다.",
            "문 옆 장치를 보면 인증이 필요한 것 같다."
        ]
    },

    "rest_area": {
        "area_id": "TutorialZone",
        "scenes": [
            "A room contains beds and furniture.",
            "A rest area contains beds and personal furniture.",
            "A room looks like a place where people used to rest."
        ],
        "rag": "침대와 가구가 있는 방은 직원 휴게 공간처럼 보인다. 이 방 안에는 단서가 남아 있을 수 있다.",
        "reference": "여긴 누군가 머물던 공간 같다.",
        "reasoning_policy": "침대와 가구를 근거로 누군가 머물던 공간이라고 추론한다.",
        "titles": ["직원 휴게 공간", "버려진 휴게실"],
        "observations": [
            "방 안에는 침대와 가구가 있고 누군가 생활하던 흔적이 남아 있다.",
            "침대와 의자 같은 물건들이 보여 휴식 공간처럼 보인다."
        ],
        "reasonings": [
            "이곳은 직원들이 쉬거나 머물던 공간일 가능성이 있다.",
            "누군가 사용하던 방이라면 작은 단서나 물건이 남아 있을 수 있다."
        ],
        "conclusions": [
            "여긴 누군가 쓰던 공간 같다.",
            "그냥 지나칠 만한 방은 아닌 것 같다."
        ],
        "hints": [
            "침대와 가구를 보면... 사람들이 머물던 공간 같다.",
            "여긴 누군가 쉬던 곳 같다... 그냥 비어 있는 방은 아닌 것 같다."
        ]
    },

    "mainhall_locked_door": {
        "area_id": "MainHall",
        "scenes": [
            "A locked door is visible on the right side of a hall.",
            "A door with an access device is visible in a bright hall.",
            "A closed door with a small device next to it is visible."
        ],
        "rag": "메인 홀 오른쪽에는 잠긴 문이 있다. 문은 그냥 열리지 않는 상태로 보인다.",
        "reference": "오른쪽 문은 잠긴 것 같다... 그냥 지나갈 수는 없어 보인다.",
        "reasoning_policy": "잠긴 문과 장치를 근거로 추론한다. 키카드를 확정적으로 말하지 않는다.",
        "titles": ["메인 홀의 잠긴 문", "오른쪽 출입문"],
        "observations": [
            "메인 홀 오른쪽에 닫힌 문이 있고 주변에 출입 장치처럼 보이는 물체가 있다.",
            "문은 일반적으로 열리는 구조처럼 보이지 않고 잠긴 상태처럼 보인다."
        ],
        "reasonings": [
            "이 문은 별도의 출입 수단이나 인증 절차가 필요한 구조일 가능성이 있다.",
            "주변 장치와 문 상태를 보면 그냥 통과하기는 어려워 보인다."
        ],
        "conclusions": [
            "이 문은 그냥 열릴 것 같지 않다.",
            "출입 수단이 없으면 열리지 않을 가능성이 높다."
        ],
        "hints": [
            "오른쪽 문은 그냥 열릴 것 같지 않다.",
            "문이 잠겨 있다면 이 홀 어딘가에 단서가 남아 있을지도 모른다."
        ]
    },

    "mainhall_keycard_on_chair": {
        "area_id": "MainHall",
        "scenes": [
            "A small card is lying on a chair.",
            "A keycard is visible on one of the chairs.",
            "An access card is placed on a chair near a machine."
        ],
        "rag": "기계 근처 의자 중 하나에는 키카드가 놓여 있다. 키카드는 메인 홀의 잠긴 문과 관련될 수 있다.",
        "reference": "의자 위에 카드가 있다... 출입증 같은 건가?",
        "reasoning_policy": "의자 위의 작은 카드나 출입증을 근거로 추론한다.",
        "titles": ["의자 위의 키카드", "남겨진 출입 카드"],
        "observations": [
            "기계 근처 의자 위에 작은 카드가 놓여 있다.",
            "의자 위의 카드가 출입증이나 키카드처럼 보인다."
        ],
        "reasonings": [
            "이 카드는 출입 제한 문과 관련된 물건일 가능성이 있다.",
            "잠긴 문이 있는 공간에서 발견된 카드라면 출입 수단일 가능성이 높다."
        ],
        "conclusions": [
            "이 카드는 잠긴 문과 관련 있을지도 모른다.",
            "의자 위의 작은 카드가 중요한 물건처럼 보인다."
        ],
        "hints": [
            "의자 위의 작은 카드가 눈에 띈다.",
            "저 카드라면 잠긴 문과 관련된 출입 수단일지도 모른다."
        ]
    },

    "labzone_spare_fuse": {
        "area_id": "LabZone",
        "scenes": [
            "A spare fuse is visible near a fuse box.",
            "A small fuse is placed inside a bathroom.",
            "An extra fuse is lying near an electrical panel."
        ],
        "rag": "화장실에는 여분의 퓨즈가 있다. 다른 퓨즈 박스에는 퓨즈가 부족하다.",
        "reference": "여분의 퓨즈가 남아 있다... 다른 곳에 필요할지도 모른다.",
        "reasoning_policy": "여분의 퓨즈를 근거로 추론한다. 어디에 꽂으라고 직접 말하지 않는다.",
        "titles": ["남겨진 퓨즈", "전원 문제의 단서"],
        "observations": [
            "화장실 안에 여분으로 보이는 퓨즈가 남아 있다.",
            "열린 퓨즈 박스 근처에 작은 전기 부품이 놓여 있다."
        ],
        "reasonings": [
            "여분의 퓨즈가 남아 있다는 것은 다른 곳에 부족한 전원 부품이 있을 가능성을 암시한다.",
            "이 퓨즈는 어두운 복도나 다른 퓨즈 박스와 연결될 수 있다."
        ],
        "conclusions": [
            "이 퓨즈는 다른 곳에서 필요할지도 모른다.",
            "전원 문제와 연결된 물건으로 보인다."
        ],
        "hints": [
            "이 퓨즈는 그냥 남겨진 물건처럼 보이지 않는다.",
            "여분의 퓨즈라면 다른 곳의 전원을 되살리는 데 쓰일지도 모른다."
        ]
    },

    "labzone_research_room_overview": {
        "area_id": "LabZone",
        "scenes": [
            "A dark laboratory room contains tables and chairs.",
            "A research room with several tables and chairs is visible.",
            "A laboratory contains desks, chairs, and scattered objects."
        ],
        "rag": "연구실 안에는 여러 테이블과 의자가 있다. 연구실에는 흩어진 물건과 어두운 얼룩이 보인다.",
        "reference": "연구실 안에 물건들이 흩어져 있다... 중요한 단서가 남아 있을지도 모른다.",
        "reasoning_policy": "연구실의 테이블, 의자, 흩어진 물건을 근거로 추론한다.",
        "titles": ["흩어진 연구실", "버려진 실험 공간"],
        "observations": [
            "연구실 안에는 여러 테이블과 의자가 있고 물건들이 흩어져 있다.",
            "실험 공간처럼 보이는 방 안에 장비와 가구가 남아 있다."
        ],
        "reasonings": [
            "이곳은 단순한 방이 아니라 연구나 실험이 이루어지던 공간으로 보인다.",
            "흩어진 물건들 사이에 사건을 설명할 단서가 남아 있을 가능성이 있다."
        ],
        "conclusions": [
            "연구실 안에는 중요한 단서가 남아 있을 것 같다.",
            "이 공간은 사건의 원인을 이해하는 데 중요한 장소처럼 보인다."
        ],
        "hints": [
            "연구실 안은 물건들이 흩어져 있어 뭔가 남아 있을 것 같다.",
            "테이블과 의자 주변에 중요한 단서가 남아 있을 가능성이 있다."
        ]
    },

    "labzone_monster_file": {
        "area_id": "LabZone",
        "scenes": [
            "A file or document is visible on a lab table.",
            "A monster information file is visible in the laboratory.",
            "A research file is lying on a table in the lab."
        ],
        "rag": "연구실 안에는 몬스터에 대한 정보 파일이 있다. 파일은 연구실에서 벌어진 실험이나 사건과 관련될 수 있다.",
        "reference": "저 파일... 이곳에서 무슨 실험이 있었는지 적혀 있을지도 모른다.",
        "reasoning_policy": "연구실 안의 파일과 문서를 근거로 추론한다. 파일 내용을 지어내지 않는다.",
        "titles": ["몬스터 정보 파일", "연구 기록"],
        "observations": [
            "연구실 테이블 위에 문서나 파일이 놓여 있다.",
            "실험 공간 안에 무언가를 기록한 파일이 남아 있다."
        ],
        "reasonings": [
            "이 파일은 연구실에서 벌어진 실험이나 사건과 관련된 기록일 가능성이 있다.",
            "문서 내용은 이 구역의 위험이나 몬스터의 정체를 이해하는 단서가 될 수 있다."
        ],
        "conclusions": [
            "이 파일은 연구실 사건을 이해하는 핵심 단서일지도 모른다.",
            "몬스터와 관련된 기록이라면 그냥 넘길 수 없다."
        ],
        "hints": [
            "연구실 안의 파일이 신경 쓰인다.",
            "저 파일에는 이곳에서 무슨 실험이 있었는지 적혀 있을지도 모른다."
        ]
    }
}


data = []

for scene_type, info in scene_types.items():
    for scene in info["scenes"]:
        for _ in range(25):
            data.append({
                "area_id": info["area_id"],
                "scene_type": scene_type,
                "scene": scene,
                "rag": info["rag"],
                "reference_answer": info["reference"],
                "reasoning_policy": info["reasoning_policy"],
                "title": random.choice(info["titles"]),
                "observation": random.choice(info["observations"]),
                "reasoning": random.choice(info["reasonings"]),
                "conclusion": random.choice(info["conclusions"]),
                "hint": random.choice(info["hints"])
            })

augmented_data = []

for item in data:
    augmented_data.append(item)
    augmented_data.append({
        **item,
        "scene": "The current image shows " + item["scene"]
    })

random.shuffle(augmented_data)

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    for d in augmented_data:
        f.write(json.dumps(d, ensure_ascii=False) + "\n")

print(f"Saved: {OUTPUT_PATH}")
print(f"Count: {len(augmented_data)}")