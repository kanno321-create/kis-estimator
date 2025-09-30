# estimate_policy.py
# 견적 정책/기본값 로더 (RAG 번들에서 정책을 읽고, 없으면 안전한 기본값 사용)

import os, json

DEFAULTS = {
    "h_strategy": "A+B+C+D+E",
    "meter_bottom_slot": {
        "h_mm": 200,                 # 1칸 높이 = 130(본체)+70(배선) = 200mm
        "w_per_column_mm": 130,      # 컬럼(가로) 폭 = 130mm
        "single_meter_no_change_if_side_space": True  # 계량기 1EA는 메인 좌/우 여유로 처리 가능하면 함 변화 없음
    },
    "magnet_labor_per_unit_krw": 20000,  # 마그네트 인건비
    "accessory_share": {"magnet": 0.60}, # 부속자재 비중 참고(추천/정렬용)
    "consumables_cap_krw": 42000,        # 잡자재비 상한

    # UI/엔진 기본값(원하면 나중에 바꿔도 됨)
    "E_ratio_default": 0.25,             # 부속 여유(E) 비율 기본 25% (20/25/30 중)
    "meter_columns_default": 2           # 계량기 하부 컬럼 기본 2칸(= W + 260mm)
}

def _load_bundle(path: str):
    """RAG 통합 번들에서 policies 섹션을 읽어 DEFAULTS에 덮어쓴다."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            bundle = json.load(f)
        pol = bundle.get("policies", {})
        out = DEFAULTS.copy()
        out.update(pol)
        return out, bundle
    except Exception:
        return DEFAULTS.copy(), {}

def load_policies(base_dir=None):
    """
    data/rag/estimate_rag_bundle_v1.0.0.json 을 찾아 정책을 로드한다.
    로컬 개발/테스트를 위해 /mnt/data 경로도 함께 확인한다.
    반환: (policies_dict, bundle_dict)
    """
    base_dir = base_dir or os.path.dirname(__file__)
    data_dir = os.path.join(base_dir, "data", "rag")

    candidates = [
        os.path.join(data_dir, "estimate_rag_bundle_v1.0.0.json"),
        "/mnt/data/rag/estimate_rag_bundle_v1.0.0.json"
    ]
    for p in candidates:
        if os.path.exists(p):
            return _load_bundle(p)

    # 번들이 없어도 안전하게 동작
    return DEFAULTS.copy(), {}
