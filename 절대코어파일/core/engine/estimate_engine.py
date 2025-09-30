#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# === estimate_engine.py — 한국산업 견적 엔진 v2.0 완전 수정판 ===

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

# 로거 설정
logger = logging.getLogger(__name__)

# ====================================================
# 상수 테이블 정의 (기존 파일에서 로드하던 내용들)
# ====================================================

# 메인 상부 전선 공간 A(mm)
MAIN_TOP_CLEARANCE = {
    "30AF": 130, "50AF": 130, "60AF": 130, "100AF": 170, "125AF": 170,
    "200AF": 200, "250AF": 200, "400AF": 400, "600AF": 500, "800AF": 600,
}

# 메인차단기 높이 B(mm)
MAIN_BODY_HEIGHT = {
    "30AF": 120, "50AF": 120, "60AF": 120, "100AF": 120, "125AF": 140,
    "200AF": 160, "250AF": 160, "400AF": 220, "600AF": 280, "800AF": 280,
}

# 최고 스펙별 폭 테이블
WIDTH_BY_MAX_SPEC = {
    "none": 300, "30": 350, "50_60_100": 400, "125": 450,
    "200_250": 500, "400": 600, "600_800": 700
}

# AF와 분기수에 따른 깊이 테이블 (간소화)
DEPTH_BY_AF_COUNT = {
    ("30AF", 5): 200, ("50AF", 10): 250, ("100AF", 15): 300,
    ("125AF", 10): 280, ("200AF", 15): 320, ("250AF", 20): 350,
    ("400AF", 15): 400, ("600AF", 20): 450, ("800AF", 25): 500
}

# 재료 단가 (kg당)
MATERIAL_PRICE_PER_KG = {
    "CU": 8500,  # 구리
    "AL": 3200   # 알루미늄
}

# ====================================================
# 핵심 함수들
# ====================================================

def map_amp_to_af(amp: int) -> str:
    """차단기 용량(A) → AF(프레임) 매핑"""
    if amp <= 30: return "30AF"
    elif amp <= 50: return "50AF"
    elif amp <= 60: return "60AF"
    elif amp <= 100: return "100AF"
    elif amp <= 125: return "125AF"
    elif amp <= 200: return "200AF"
    elif amp <= 250: return "250AF"
    elif amp <= 400: return "400AF"
    elif amp <= 600: return "600AF"
    else: return "800AF"

def expand_branch_units(branches: List[Dict], style: str = "표준형") -> List[Dict]:
    """분기 목록을 개별 단위로 확장"""
    units = []
    for branch in branches:
        try:
            quantity = int(branch.get("수량", 1))
            capacity = branch.get("용량", "30A")
            amp = int(capacity.rstrip('A'))
            af = map_amp_to_af(amp)
            
            # 높이 계산
            poles = branch.get("극수", "4P")
            if poles == "2P":
                row_height = 35
            elif poles == "3P":
                row_height = 75
            else:  # 4P
                row_height = 100
            
            for _ in range(quantity):
                units.append({
                    "af": af,
                    "capacity": amp,
                    "poles": poles,
                    "row_height": row_height,
                    "quantity": 1
                })
        except (ValueError, KeyError):
            # 오류 시 기본값
            units.append({
                "af": "30AF",
                "capacity": 30,
                "poles": "4P", 
                "row_height": 100,
                "quantity": 1
            })
    return units

def max_branch_class(branches: List[Dict], style: str = "표준형") -> str:
    """분기 중 최고 스펙 클래스 반환"""
    units = expand_branch_units(branches, style)
    rank = "none"
    
    def upgrade_rank(current: str, new: str) -> str:
        order = ["none", "30", "50_60_100", "125", "200_250", "400", "600_800"]
        current_idx = order.index(current) if current in order else 0
        new_idx = order.index(new) if new in order else 0
        return order[max(current_idx, new_idx)]
    
    for unit in units:
        af = unit["af"]
        if af == "30AF":
            rank = upgrade_rank(rank, "30")
        elif af in {"50AF", "60AF", "100AF"}:
            rank = upgrade_rank(rank, "50_60_100")
        elif af == "125AF":
            rank = upgrade_rank(rank, "125")
        elif af in {"200AF", "250AF"}:
            rank = upgrade_rank(rank, "200_250")
        elif af == "400AF":
            rank = upgrade_rank(rank, "400")
        elif af in {"600AF", "800AF"}:
            rank = upgrade_rank(rank, "600_800")
    
    return rank

def compute_enclosure_size(main_kind: str, main_poles_text: str, main_amp_text: str, 
                          branches: List[Dict], style: str = "표준형", 
                          meter_count: int = 0, single_meter_side_ok: bool = True) -> Dict[str, Any]:
    """외함 크기 계산 개선 버전"""
    try:
        # 1. 메인 차단기 정보 추출
        main_amp = int(main_amp_text.rstrip('A'))
        main_af = map_amp_to_af(main_amp)
        main_poles = int(main_poles_text.rstrip('P'))
        
        # 2. A_top 계산 (메인 상부 전선 공간)
        A_top = MAIN_TOP_CLEARANCE.get(main_af, 170)
        
        # 3. B_gap 계산 (메인 차단기 높이)
        B_gap = MAIN_BODY_HEIGHT.get(main_af, 120)
        
        # 4. C_branch_total 계산 (분기 전체 높이)
        branch_units = expand_branch_units(branches, style)
        C_branch_total = sum(unit.get("row_height", 40) for unit in branch_units)
        
        # 5. D_bottom 계산 (하부 공간)
        D_bottom = 100  # 표준 하부 공간
        
        # 6. E_accessory 계산 (계기 및 기타)
        E_accessory = 0
        if meter_count > 1:
            E_accessory = ((meter_count + 1) // 2) * 200  # 2열 배치 기준
        elif meter_count == 1 and not single_meter_side_ok:
            E_accessory = 200
            
        # 7. H 최종 계산
        H_raw = A_top + B_gap + C_branch_total + D_bottom + E_accessory
        H_final = ((H_raw + 99) // 100) * 100  # 100mm 단위 올림
        
        # 8. W 계산 (최고 스펙 기준)
        max_spec = max_branch_class(branches, style)
        W = WIDTH_BY_MAX_SPEC.get(max_spec, 400)
        
        # 9. D 계산 (AF×분기수 규칙)
        branch_count = len(branch_units)
        # 간단한 깊이 계산
        if main_af in ["30AF", "50AF"]:
            D = 200
        elif main_af in ["100AF", "125AF"]:
            D = 250
        elif main_af in ["200AF", "250AF"]:
            D = 300
        else:
            D = 350
            
        # 10. 설명 생성
        explain = {
            "A_top": A_top,
            "B_gap": B_gap, 
            "C_branch_total": C_branch_total,
            "D_bottom": D_bottom,
            "E_accessory": E_accessory,
            "H_raw": H_raw,
            "H_final": H_final,
            "max_spec_class": max_spec,
            "근거키": "외함크기산출공식.txt/기본계산식/H=A+B+C+D+E"
        }
        
        return {"W": W, "H": H_final, "D": D, "explain": explain}
        
    except Exception as e:
        logger.error(f"외함 크기 계산 오류: {e}")
        # 기본값 반환
        return {"W": 400, "H": 800, "D": 300, "explain": {"error": str(e)}}

def compute_busbar_capacity(main_amp: str, branches: List[Dict], 
                           material: str = "CU", J_density: float = 2.5) -> Dict[str, Any]:
    """부스바 용량 계산 개선 버전"""
    try:
        # 1. 요구전류 계산
        main_current = int(main_amp.rstrip('A'))
        I_req = main_current * 1.25  # 안전계수 적용
        
        # 2. 필요 단면적 계산 
        S_required = I_req / J_density  # mm²
        
        # 3. 표준 규격 선택
        busbar_specs = [
            {"spec": "3T*15", "area": 45, "weight_per_m": 0.12},
            {"spec": "5T*20", "area": 100, "weight_per_m": 0.27},
            {"spec": "6T*30", "area": 180, "weight_per_m": 0.49},
            {"spec": "8T*40", "area": 320, "weight_per_m": 0.86}
        ]
        
        selected_spec = None
        for spec in busbar_specs:
            if spec["area"] >= S_required:
                selected_spec = spec
                break
                
        if not selected_spec:
            selected_spec = busbar_specs[-1]  # 최대 규격 선택
            
        # 4. 무게 및 비용 계산
        estimated_length = 2.0  # 표준 길이 (m)
        total_weight = selected_spec["weight_per_m"] * estimated_length
        material_cost = total_weight * MATERIAL_PRICE_PER_KG.get(material, 8500)
        
        # 5. 가공비 계산
        processing_cost = {
            "절단": 5000,
            "천공": 3000 * 4,  # 4개 구멍 기준
            "굽힘": 2000
        }
        
        return {
            "spec": selected_spec["spec"],
            "area": selected_spec["area"], 
            "weight_kg": round(total_weight, 2),
            "material_cost": int(material_cost),
            "processing_cost": sum(processing_cost.values()),
            "total_cost": int(material_cost) + sum(processing_cost.values()),
            "근거키": "부스바 산출공식.txt/표준규격선택/S=I_req/J"
        }
        
    except Exception as e:
        logger.error(f"부스바 계산 오류: {e}")
        return {"error": f"부스바 계산 오류: {str(e)}"}

def calculate_labor_cost(W: int, H: int, D: int, branch_count: int, 
                        main_af: str, style: str = "표준형") -> Dict[str, Any]:
    """인건비 계산 개선 버전"""
    try:
        # 1. 조립 인건비 (티어 + H 증분)
        assembly_base = {
            "30AF": 50000, "50AF": 50000, "60AF": 50000, "100AF": 50000,
            "125AF": 70000, "200AF": 70000, "250AF": 70000,
            "400AF": 90000,
            "600AF": 120000, "800AF": 120000
        }
        
        base_cost = assembly_base.get(main_af, 70000)
            
        # H 증분 (100mm 단위당 가산)
        h_increment = ((H - 600) // 100) * 5000 if H > 600 else 0
        assembly_cost = base_cost + max(0, h_increment)
        
        # 2. E.T 인건비 (분기 12개당 1EA, 최소 1EA)
        et_count = max(1, (branch_count + 11) // 12)
        et_unit_cost = {
            "30AF": 15000, "50AF": 15000, "60AF": 15000, "100AF": 15000,
            "125AF": 18000, "200AF": 20000, "250AF": 20000,
            "400AF": 25000, "600AF": 30000, "800AF": 30000
        }
        et_cost = et_count * et_unit_cost.get(main_af, 20000)
        
        # 3. 마그네트 인건비 (1EA당 20,000원)
        magnet_cost = 20000  # 정책: 1EA 고정
        
        total_labor = assembly_cost + et_cost + magnet_cost
        
        return {
            "assembly_cost": assembly_cost,
            "et_cost": et_cost,
            "magnet_cost": magnet_cost,
            "total_labor": total_labor,
            "근거키": "인건비 및 기타사항 단가.txt/인건비계산/티어+H증분+ET+마그네트"
        }
        
    except Exception as e:
        logger.error(f"인건비 계산 오류: {e}")
        return {"error": f"인건비 계산 오류: {str(e)}"}

def calc_grand_total(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """통합 견적 계산 - Phase 2 핵심 함수"""
    try:
        # 1. 입력 데이터 정규화
        main = input_data.get("main", {})
        branches = input_data.get("branches", [])
        enclosure_info = input_data.get("enclosure", {})
        
        # 2. 외함 크기 계산
        enc_result = compute_enclosure_size(
            main.get("종류", "MCCB"),
            main.get("극수", "4P"), 
            main.get("용량", "100A"),
            branches,
            enclosure_info.get("함종류", "표준형"),
            enclosure_info.get("계기수", 0)
        )
        
        W, H, D = enc_result["W"], enc_result["H"], enc_result["D"]
        
        # 3. 부스바 계산
        busbar_result = compute_busbar_capacity(
            main.get("용량", "100A"),
            branches,
            input_data.get("busbar", {}).get("재질", "CU")
        )
        
        # 4. 인건비 계산
        branch_count = sum(b.get("수량", 1) for b in branches)
        main_af = map_amp_to_af(int(main.get("용량", "100A").rstrip('A')))
        labor_result = calculate_labor_cost(W, H, D, branch_count, main_af)
        
        # 5. 기타 자재비 계산
        other_materials = {
            "N.T": 3000,
            "N.P_3T": 4000,
            "코팅": 5000 if main_af in ["50AF", "100AF", "125AF", "200AF", "250AF"] else 10000,
            "지지대": branch_count * 500,
            "인슐레이터": 4 * (1100 if main_af in ["50AF", "100AF", "125AF", "200AF", "250AF"] else 4400)
        }
        
        # 6. 잡자재비 (CAP 적용)
        cap_base = 42000
        consumables = max(7000, (W * H // 100000) * 1000)  # 크기 기반 계산
        
        # 7. 총 원가 계산
        material_cost = busbar_result.get("total_cost", 0)
        labor_cost = labor_result.get("total_labor", 0) 
        other_cost = sum(other_materials.values())
        consumable_cost = min(consumables, cap_base)
        
        subtotal = material_cost + labor_cost + other_cost + consumable_cost
        
        # 8. 마진 및 VAT 적용 
        overhead = int(subtotal * 0.15)  # 15% 오버헤드
        margin = int((subtotal + overhead) * 0.20)  # 20% 이윤
        
        total_before_vat = subtotal + overhead + margin
        vat = int(total_before_vat * 0.10)  # 10% 부가세
        final_total = total_before_vat + vat
        
        # 9. 천원 절사
        final_total = (final_total // 1000) * 1000
        
        return {
            "enclosure": {"W": W, "H": H, "D": D},
            "busbar": busbar_result,
            "costs": {
                "material": material_cost,
                "labor": labor_cost, 
                "other": other_cost,
                "consumables": consumable_cost
            },
            "total": {
                "subtotal": subtotal,
                "overhead": overhead,
                "margin": margin,
                "before_vat": total_before_vat,
                "vat": vat,
                "final": final_total
            },
            "trace": {
                "enclosure_explain": enc_result.get("explain"),
                "근거키": "통합견적계산/전체플로우/재료+인건+기타+잡자재"
            }
        }
        
    except Exception as e:
        logger.error(f"통합 계산 오류: {e}")
        return {"error": f"통합 계산 오류: {str(e)}"}

# ====================================================
# 기존 호환성을 위한 클래스
# ====================================================

class EstimateEngine:
    """기존 호환성을 위한 클래스 래퍼"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def calculate_estimate(self, input_data: Dict) -> Dict:
        """기존 인터페이스 호환"""
        return calc_grand_total(input_data)

# ====================================================
# 테스트 실행 부분
# ====================================================

if __name__ == "__main__":
    # 간단한 테스트
    engine = EstimateEngine()
    
    sample_data = {
        "client": {"업체명": "테스트업체", "프로젝트": "샘플"},
        "main": {"종류": "MCCB", "극수": "4P", "용량": "150A"},
        "branches": [
            {"종류": "MCCB", "극수": "4P", "용량": "50A", "수량": 3},
            {"종류": "ELB", "극수": "2P", "용량": "20A", "수량": 4},
        ],
        "enclosure": {"함종류": "표준형", "계기수": 1},
        "busbar": {"재질": "CU"}
    }
    
    result = engine.calculate_estimate(sample_data)
    print(json.dumps(result, ensure_ascii=False, indent=2))