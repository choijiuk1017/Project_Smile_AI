import json
import random

OUTPUT_PATH = "lora_tutorial_hint_reasoning_policy.jsonl"

scene_types = {
    # =========================
    # TutorialZone
    # =========================
    "spawn_corpse": {
        "area_id": "TutorialZone",
        "scenes": [
            "A single body is lying on the floor in a dark room.",
            "One person is lying motionless on the ground.",
            "A single humanoid figure is collapsed on the floor.",
            "Only one body is visible near a staircase.",
            "One injured person is lying on a tiled floor.",
            "A single figure is lying on the floor with blood nearby."
        ],
        "rag": "방 안에 한 명의 시체가 쓰러져 있다. 주변에는 핏자국이 남아 있다. 단순히 넘어진 것이 아니라 공격받은 흔적으로 보인다.",
        "reference": "저 시체는 뭐지? 무언가한테 공격받은 것 같은데...",
        "reasoning_policy": "장면에 보이는 사람은 한 명이다. 여러 명이 쓰러져 있다고 말하지 않는다. 복도 전체의 사건으로 확대하지 않는다. 한 명의 시체와 주변 핏자국만 바탕으로 추론한다.",
        "answers": [
            "저 사람... 그냥 쓰러진 건 아닌 것 같다.",
            "피가 주변에 튄 걸 보면... 저 사람은 공격받은 건가?",
            "움직임이 없다... 단순히 넘어진 건 아닌 것 같다.",
            "저 상태라면 무언가에게 당한 흔적처럼 보인다.",
            "한 사람이 저렇게 쓰러져 있다... 여기서 무슨 일이 있었던 거지?"
        ]
    },
    "hallway_corpses": {
        "area_id": "TutorialZone",
        "scenes": [
            "Multiple bodies are lying on the floor in a hallway.",
            "Several human figures are lying across a corridor.",
            "Two or more bodies are scattered across a corridor floor.",
            "A hallway contains many motionless people.",
            "Several bodies are visible in a long corridor.",
            "A corridor floor is covered with multiple bodies."
        ],
        "rag": "복도에는 여러 명의 사람이 쓰러져 있다. 복도 전체에 핏자국과 쓰러진 사람들이 보인다. 여러 사람이 동시에 피해를 입은 사건처럼 보인다.",
        "reference": "끔찍하군... 대체 무슨 일이 있었던 거야?",
        "reasoning_policy": "장면에는 여러 명이 쓰러져 있다. 한 명만 있다고 축소하지 않는다. 복도나 통로 전체에서 벌어진 사건처럼 추론한다.",
        "answers": [
            "복도에 쓰러진 사람이 한둘이 아니다... 여기서 무슨 일이 있었던 거지?",
            "이 정도로 여러 사람이 쓰러져 있다면 단순한 사고는 아닌 것 같다.",
            "복도 전체가 사건 현장처럼 보인다... 누가 이런 짓을 한 거지?",
            "사람들이 이렇게까지 쓰러져 있다니... 무언가 큰일이 벌어진 것 같다.",
            "여러 사람이 한꺼번에 당한 흔적처럼 보인다... 우연은 아닌 것 같다."
        ]
    },
    "locked_private_door": {
        "area_id": "TutorialZone",
        "scenes": [
            "A black door labeled PRIVATE is visible.",
            "A door with the word PRIVATE written on it is shown.",
            "A PRIVATE door is visible in a dimly lit room.",
            "A secured door with a keypad or access device is visible.",
            "A door labeled PRIVATE has a small wall device next to it.",
            "A locked-looking door with an access panel is visible."
        ],
        "rag": "문에는 PRIVATE 표시가 있다. 문 옆에는 키패드 같은 장치가 있다. 문은 잠긴 상태일 가능성이 높다. 키패드 같은 장치는 키카드나 출입증이 필요할 수 있음을 암시한다.",
        "reference": "문이 잠긴 것 같은데... 옆에 키패드를 보면 키카드 같은 것이 필요하겠어...",
        "reasoning_policy": "PRIVATE 표시와 문 옆 장치를 근거로 추론한다. 키카드가 확정적으로 있다고 말하지 않고 필요할 가능성으로만 말한다. 행동 지시를 하지 않는다.",
        "answers": [
            "PRIVATE라... 그냥 열 수 있는 문은 아닌 것 같다.",
            "문 옆 장치를 보면 출입을 확인하는 무언가가 필요한 것 같다.",
            "PRIVATE 표시와 장치를 보면 인증 없이는 열리지 않을 것 같다.",
            "이 문은 평범한 문이 아니다... 뭔가 조건이 필요한 것 같다.",
            "옆에 붙은 장치가 신경 쓰인다... 출입증 같은 것이 필요할지도 모른다."
        ]
    },
    "rest_area": {
        "area_id": "TutorialZone",
        "scenes": [
            "A room contains beds and furniture.",
            "A dilapidated room contains beds, chairs, and a television.",
            "A room with a bed, chair, table, and television is visible.",
            "A rest area contains beds and personal furniture.",
            "A room looks like a place where people used to rest.",
            "A room contains beds and scattered debris."
        ],
        "rag": "침대와 가구가 있는 방은 직원 휴게 공간처럼 보인다. 이 방 안에는 문을 여는 데 필요한 물건이 있을 수 있다. 플레이어는 방 안을 살펴볼 수 있다.",
        "reference": "이곳은 직원들 휴게 공간인가 보군... 여기 어딘가에 필요한 물건이 있을지도 몰라.",
        "reasoning_policy": "침대와 가구를 근거로 누군가 머물던 공간이라고 추론한다. 특정 물건이 있다고 단정하지 않는다. 행동 지시를 하지 않는다.",
        "answers": [
            "침대와 가구를 보면... 사람들이 머물던 공간 같다.",
            "여긴 누군가 쉬던 곳 같다... 그냥 비어 있는 방은 아닌 것 같다.",
            "직원들이 쓰던 공간이라면 뭔가 남아 있을지도 모른다.",
            "이 공간은 누군가 사용하던 흔적이 있다... 그냥 지나치긴 어렵다.",
            "침대와 가구가 남아 있다... 필요한 단서가 숨어 있을지도 모른다."
        ]
    },
    "office_desk": {
        "area_id": "TutorialZone",
        "scenes": [
            "A room contains a desk and a chair.",
            "A desk with a computer monitor is visible.",
            "A room has a desk, chair, and computer monitor.",
            "A desk with scattered objects is visible in a dim room.",
            "A table with a cup and a small object is visible.",
            "A room contains a table, sink, cup, and scattered objects."
        ],
        "rag": "책상과 컴퓨터가 있는 사무 공간이다. 책상 주변에는 단서가 남아 있을 수 있다. 흩어진 물건들은 조사 대상이 될 수 있다.",
        "reference": "책상 주변에 단서가 남아 있을지도 모른다.",
        "reasoning_policy": "책상, 컴퓨터, 흩어진 물건을 근거로 추론한다. 특정 아이템을 만들어내지 않는다. 행동 지시를 하지 않는다.",
        "answers": [
            "책상 주변에 물건들이 흩어져 있다... 뭔가 남아 있을지도 모른다.",
            "컴퓨터와 책상이 있는 걸 보면... 기록이 남아 있을 가능성이 있다.",
            "이건 작업 공간 같다... 단서가 남아 있을지도 모른다.",
            "누군가 여기서 일하다 떠난 흔적 같다... 그냥 넘기긴 어렵다.",
            "흩어진 물건들을 보면... 이 주변에 뭔가 남아 있을 것 같다."
        ]
    },
    "blood_stains_only": {
        "area_id": "TutorialZone",
        "scenes": [
            "A room has blood stains but no visible body.",
            "Dark stains are scattered across the floor with no person visible.",
            "The floor and walls have splatters but no body is visible.",
            "A dim room contains stains and splatters but no clear object.",
            "Blood-like marks are visible on the floor without any person nearby.",
            "A corridor has dark stains but no visible bodies."
        ],
        "rag": "핏자국이나 얼룩은 보이지만 시체나 중요한 물체는 보이지 않는다. 이 흔적만으로는 튜토리얼 퍼즐과 직접 관련된 단서라고 보기 어렵다.",
        "reference": "핏자국은 보이지만, 이것만으로는 확실히 알 수 없다.",
        "reasoning_policy": "핏자국만 근거로 추론한다. 시체, 키카드, 문 같은 보이지 않는 물체를 추가하지 않는다. 확실하지 않다는 방향으로 말한다.",
        "answers": [
            "핏자국은 보이지만, 이것만으로는 확실히 알 수 없다.",
            "흔적은 남아 있는데... 이걸로 판단하긴 어렵다.",
            "피가 보이긴 하지만 주변에 분명한 단서는 없는 것 같다.",
            "여기서 무언가 있었던 건 맞지만... 아직 확신하긴 어렵다.",
            "핏자국만으로는 무슨 일이 있었는지 단정할 수 없다."
        ]
    },
    "tutorial_keycard": {
        "area_id": "TutorialZone",
        "scenes": [
            "A small card is visible on a desk.",
            "An access card is lying on a table.",
            "A keycard-like object is visible near a computer.",
            "A small rectangular card is placed on a surface.",
            "A card or ID badge is visible in the room.",
            "A small card is lying among scattered objects."
        ],
        "rag": "키카드는 출입증처럼 보인다. 키카드는 잠긴 문 옆 장치와 관련될 수 있다. 플레이어는 이 물건을 확인할 수 있다.",
        "reference": "저건 키카드 같은데... 저게 출입증인가?",
        "reasoning_policy": "작은 카드나 출입증처럼 보이는 물체를 근거로 추론한다. 잠긴 문과 관련될 가능성은 말할 수 있지만, 정답처럼 단정하지 않는다.",
        "answers": [
            "저건 키카드 같은데... 출입증으로 쓰는 물건인가?",
            "책상 위의 작은 카드가 그냥 놓인 물건처럼 보이진 않는다.",
            "저 카드라면 출입이 제한된 문과 관련이 있을지도 모른다.",
            "작은 카드가 눈에 띈다... 뭔가를 여는 데 쓰는 물건일지도 모른다.",
            "이 카드라면 아까 본 장치와 연결될 가능성이 있다."
        ]
    },
    "tutorial_no_clue": {
        "area_id": "TutorialZone",
        "scenes": [
            "An empty dark room with no clear important object.",
            "Only walls, floor, and lighting are visible.",
            "A plain room is visible with no clear clue.",
            "A dark corner or empty wall is visible.",
            "No person, card, door label, desk, or bed is clearly visible.",
            "The scene contains no obvious interactable object."
        ],
        "rag": "현재 장면에서는 튜토리얼 퍼즐과 직접 관련된 단서가 확인되지 않는다.",
        "reference": "지금 보이는 것만으로는 확실한 단서를 찾기 어렵다.",
        "reasoning_policy": "명확한 단서가 보이지 않는다고 말한다. 보이지 않는 물체나 해결 방법을 만들지 않는다.",
        "answers": [
            "지금 보이는 것만으로는 확실한 단서를 찾기 어렵다.",
            "확실한 단서는 보이지 않는다.",
            "이 장면만으로는 판단할 정보가 부족하다.",
            "여기서는 당장 의미 있는 단서를 찾기 어려워 보인다.",
            "지금 시야에는 눈에 띄는 단서가 없다."
        ]
    },

    # =========================
    # MainHall
    # =========================
    "mainhall_bright_hall": {
        "area_id": "MainHall",
        "scenes": [
            "A bright large hall is visible.",
            "A spacious hall with bright lighting is visible.",
            "A clean bright lobby or hall is shown.",
            "A large open hall is visible with lights on.",
            "The player is looking at a bright main hall.",
            "A wide illuminated hall is visible."
        ],
        "rag": "메인 홀은 비교적 밝고 넓은 공간이다. 이 공간은 다른 방이나 잠긴 문으로 이어질 수 있다. 처음 들어왔을 때 주변 구조를 파악해야 하는 구역이다.",
        "reference": "갑자기 밝은 홀이 나오니 더 낯설다... 주변을 살펴봐야 할 것 같다.",
        "reasoning_policy": "밝고 넓은 홀의 구조를 근거로 추론한다. 아직 키카드나 노트를 직접 언급하지 않는다. 주변에 이어진 문이나 장치를 의식하는 정도로만 말한다.",
        "answers": [
            "갑자기 밝은 홀이 나오니 더 낯설다... 이곳 구조부터 파악해야 할 것 같다.",
            "이 홀은 단순한 통로 같지는 않다... 주변에 이어진 곳이 더 있을 것 같다.",
            "밝은 공간이라 더 불안하다... 어딘가로 이어지는 문이 있을지도 모른다.",
            "홀 자체보다 주변에 놓인 문이나 장치가 더 신경 쓰인다.",
            "이 넓은 공간은 그냥 지나가는 곳만은 아닌 것 같다."
        ]
    },
    "mainhall_locked_door": {
        "area_id": "MainHall",
        "scenes": [
            "A locked door is visible on the right side of a hall.",
            "A door with an access device is visible in a bright hall.",
            "A secured door is visible near the main hall.",
            "A door that looks locked is visible on the side of the hall.",
            "A door with a panel or reader is visible in the hall.",
            "A closed door with a small device next to it is visible."
        ],
        "rag": "메인 홀 오른쪽에는 잠긴 문이 있다. 문은 그냥 열리지 않는 상태로 보인다. 이 문을 열려면 키카드 같은 출입 수단이 필요할 수 있다.",
        "reference": "오른쪽 문은 잠긴 것 같다... 그냥 지나갈 수는 없어 보인다.",
        "reasoning_policy": "오른쪽의 잠긴 문과 장치를 근거로 추론한다. 키카드가 확정적으로 있다고 말하지 않고 출입 수단이 필요할 가능성으로만 말한다.",
        "answers": [
            "오른쪽 문은 그냥 열릴 것 같지 않다.",
            "저 문도 출입을 막아둔 것 같다... 뭔가 조건이 필요한 건가?",
            "문이 잠겨 있다면 이 홀 어딘가에 단서가 남아 있을지도 모른다.",
            "옆에 장치가 있다면 그냥 손으로 열 수 있는 문은 아닌 것 같다.",
            "이 문은 키카드 같은 출입 수단과 연결되어 있을 가능성이 높다."
        ]
    },
    "mainhall_machine_area": {
        "area_id": "MainHall",
        "scenes": [
            "A machine or terminal is visible in front of the hall.",
            "A large device or machine is visible with chairs nearby.",
            "A machine-like object is visible near two chairs.",
            "A terminal or mechanical device is visible in the hall.",
            "Two chairs are placed near a machine or console.",
            "A device with two chairs nearby is visible."
        ],
        "rag": "메인 홀 앞쪽에는 기계처럼 보이는 장치가 있다. 기계 주변에는 의자 두 개가 놓여 있다. 의자 주변에는 노트와 키카드가 놓여 있을 수 있다.",
        "reference": "저 기계 주변이 신경 쓰인다... 누군가 앉아 있던 흔적 같기도 하다.",
        "reasoning_policy": "기계와 의자 주변을 근거로 추론한다. 키카드와 노트를 바로 단정하지 않고, 주변에 무언가 남아 있을 가능성으로 말한다.",
        "answers": [
            "앞쪽의 기계와 의자들이 그냥 배치된 것 같지는 않다.",
            "저 기계 주변은 누군가 사용하던 자리처럼 보인다.",
            "기계 주변 의자에 무언가 남아 있을 가능성이 있다.",
            "의자들이 기계 앞에 놓여 있다... 여긴 그냥 장식은 아닌 것 같다.",
            "잠긴 문을 열 단서는 기계 주변 의자 쪽에 있을지도 모른다."
        ]
    },
    "mainhall_note_on_chair": {
        "area_id": "MainHall",
        "scenes": [
            "A note is lying on a chair.",
            "A piece of paper is visible on one of the chairs.",
            "A chair has a note or paper placed on it.",
            "A written note is visible near a machine.",
            "A small paper note is placed on a chair.",
            "One chair has a paper note on it."
        ],
        "rag": "기계 근처 의자 중 하나에는 노트가 놓여 있다. 노트에는 메인 홀의 잠긴 문이나 키카드와 관련된 내용이 적혀 있을 수 있다. 노트는 주변 상황을 이해하는 단서가 될 수 있다.",
        "reference": "의자 위에 뭔가 적힌 종이가 있다... 그냥 지나칠 수는 없겠군.",
        "reasoning_policy": "의자 위의 노트를 근거로 추론한다. 노트의 내용을 직접 지어내지 않는다. 잠긴 문과 관련될 가능성은 말할 수 있다.",
        "answers": [
            "의자 위의 종이가 그냥 버려진 것 같지는 않다.",
            "저 노트에는 이 홀에서 무슨 일이 있었는지 적혀 있을지도 모른다.",
            "기계 옆 의자에 노트가 놓여 있다... 단서일 가능성이 높다.",
            "종이가 일부러 남겨진 것처럼 보인다... 뭔가 알려주려는 건가?",
            "잠긴 문을 이해하는 단서가 저 노트에 있을지도 모른다."
        ]
    },
    "mainhall_keycard_on_chair": {
        "area_id": "MainHall",
        "scenes": [
            "A small card is lying on a chair.",
            "A keycard is visible on one of the chairs.",
            "An access card is placed on a chair near a machine.",
            "A small rectangular card is visible on a chair.",
            "A card or ID badge is lying on a chair.",
            "One chair has a keycard-like object on it."
        ],
        "rag": "기계 근처 의자 중 하나에는 키카드가 놓여 있다. 키카드는 메인 홀의 잠긴 문과 관련될 수 있다. 키카드는 출입 수단처럼 보인다.",
        "reference": "의자 위에 카드가 있다... 출입증 같은 건가?",
        "reasoning_policy": "의자 위의 작은 카드나 출입증을 근거로 추론한다. 메인 홀의 잠긴 문과 연결될 가능성을 말할 수 있지만, 정답처럼 명령하지 않는다.",
        "answers": [
            "의자 위의 작은 카드가 눈에 띈다.",
            "저건 키카드 같은데... 출입증으로 쓰는 물건인가?",
            "저 카드라면 잠긴 문과 관련된 출입 수단일지도 모른다.",
            "기계 옆 의자에 카드가 놓여 있다... 그냥 버려진 물건은 아닌 것 같다.",
            "이 카드라면 오른쪽의 잠긴 문과 연결될 가능성이 있다."
        ]
    },
    "mainhall_two_chairs": {
        "area_id": "MainHall",
        "scenes": [
            "Two chairs are visible near a machine.",
            "Two chairs are placed side by side in the hall.",
            "A pair of chairs is visible near a device.",
            "There are two chairs in front of a machine.",
            "Two seats are visible near a terminal.",
            "The scene shows two chairs beside a machine-like object."
        ],
        "rag": "기계 근처에는 의자 두 개가 놓여 있다. 두 의자 중 하나에는 노트가 있고 다른 하나에는 키카드가 있을 수 있다. 의자 주변은 메인 홀 퍼즐의 핵심 단서 위치다.",
        "reference": "기계 옆 의자들이 그냥 놓인 것 같지는 않다.",
        "reasoning_policy": "두 의자와 기계를 근거로 추론한다. 노트와 키카드를 확정적으로 보았다고 말하지 않고, 주변에 물건이 남아 있을 가능성으로 말한다.",
        "answers": [
            "기계 옆 의자들이 묘하게 신경 쓰인다.",
            "두 의자 주변에 뭔가 남겨진 물건이 있을지도 모른다.",
            "의자들이 기계 앞에 놓여 있다... 누군가 사용하던 자리처럼 보인다.",
            "저 의자 근처가 이 홀에서 가장 수상해 보인다.",
            "잠긴 문과 관련된 단서는 기계 근처 의자 쪽에 있을 가능성이 높다."
        ]
    },
    "mainhall_no_clue": {
        "area_id": "MainHall",
        "scenes": [
            "A bright hall is visible with no clear important object.",
            "Only walls, floor, and lighting are visible in the hall.",
            "A plain hall is visible with no clear clue.",
            "A bright corner or empty wall is visible.",
            "No card, note, door, chair, or machine is clearly visible.",
            "The scene contains no obvious interactable object in the hall."
        ],
        "rag": "현재 메인 홀 장면에서는 직접적인 단서가 확인되지 않는다. 메인 홀에서는 잠긴 문, 기계 주변, 의자 위 물건들이 주요 단서가 될 수 있다.",
        "reference": "지금 보이는 것만으로는 확실한 단서를 찾기 어렵다.",
        "reasoning_policy": "명확한 단서가 보이지 않는다고 말한다. 보이지 않는 키카드나 노트를 단정하지 않는다. 다만 메인 홀에서는 문이나 기계 주변을 의식할 수 있다.",
        "answers": [
            "지금 보이는 것만으로는 확실한 단서를 찾기 어렵다.",
            "이 홀에는 단서가 있을 것 같지만, 지금 시야에는 뚜렷하게 보이지 않는다.",
            "지금 장면만으로는 판단할 정보가 부족하다.",
            "벽과 바닥만 봐서는 알 수 있는 게 거의 없다.",
            "더 분명한 문이나 장치가 보여야 판단할 수 있을 것 같다."
        ]
    }
}

data = []

for scene_type, info in scene_types.items():
    for scene in info["scenes"]:
        for answer in info["answers"]:
            data.append({
                "area_id": info["area_id"],
                "scene_type": scene_type,
                "scene": scene,
                "rag": info["rag"],
                "reference_answer": info["reference"],
                "reasoning_policy": info["reasoning_policy"],
                "answer": answer
            })

augmented_data = []

for item in data:
    augmented_data.append(item)

    augmented_data.append({
        **item,
        "scene": "The current image shows " + item["scene"]
    })

    augmented_data.append({
        **item,
        "scene": "In the scene, " + item["scene"]
    })

random.shuffle(augmented_data)

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    for d in augmented_data:
        f.write(json.dumps(d, ensure_ascii=False) + "\n")

print(f"Saved: {OUTPUT_PATH}")
print(f"Count: {len(augmented_data)}")