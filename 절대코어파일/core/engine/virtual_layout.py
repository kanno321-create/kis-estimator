# virtual_layout.py
# 목적: 부품 실제 크기(mm) 기반 가상 배치 → 최소 외함(W,H,D) 산출 + SVG 시각화
# 정책 불변: 공식(W/H/D)은 estimate_engine 쪽 그대로 유지하고, 여기는 "증거용(Proof)" 산출만 수행
# 사용법:
#   py virtual_layout.py
# 결과:
#   - out/layout.svg : 배치 미니맵
#   - out/layout.json: 좌표/치수/메타
#   - 콘솔: 최소 W/H/D 및 배치 로그

from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from pathlib import Path
import json
import math
import os

# === 파라미터(기본 여유/통로) ===================================================
SIDE_MARGIN_L = 40       # 좌측 여유
SIDE_MARGIN_R = 40       # 우측 여유
TOP_MARGIN     = 60      # 상부 여유 (개폐/버스바)
BOTTOM_MARGIN  = 80      # 하부 여유 (케이블 인입/계량기 하부 취부 고려)
DUCT_WIDTH_L   = 60      # 좌측 세로덕트 폭 (필요 시 0)
DUCT_WIDTH_R   = 60      # 우측 세로덕트 폭 (필요 시 0)
ROW_GAP        = 20      # 선반(행) 사이 간격
ITEM_GAP_X     = 12      # 아이템 간 가로 간격
ITEM_GAP_Y     = 10      # 아이템 간 세로 간격
BUSBAR_CORRIDOR= 80      # 상단 모선 통로 높이(Top 안쪽에 확보)
PANEL_DEPTH    = 600     # 기본 깊이(정면 배선 기준), 필요시 입력으로 대체 가능
METER_CELL_W   = 130     # 계량기 하부 취부 1셀 폭
METER_CELL_H   = 200     # 계량기 하부 취부 1셀 높이

# === 데이터 구조 =================================================================
@dataclass
class Footprint:
    """단일 부품 외형(직사각형) 정의"""
    name: str
    w: int
    h: int
    qty: int = 1
    rotatable: bool = True      # 회전 허용 여부(90도)
    layer: str = "front"        # "front" (전면), "bottom" (하부), "back" 등 향후 확장
    kind: str = "GEN"           # MCCB/ELB/SPD/METER/DIN/DUCT 등 분류

@dataclass
class PlacedItem:
    name: str
    x: int
    y: int
    w: int
    h: int
    rotated: bool
    kind: str

class VirtualLayout:
    def __init__(self,
                 side_margin_l=SIDE_MARGIN_L,
                 side_margin_r=SIDE_MARGIN_R,
                 top_margin=TOP_MARGIN,
                 bottom_margin=BOTTOM_MARGIN,
                 duct_w_l=DUCT_WIDTH_L,
                 duct_w_r=DUCT_WIDTH_R,
                 row_gap=ROW_GAP,
                 item_gap_x=ITEM_GAP_X,
                 item_gap_y=ITEM_GAP_Y,
                 busbar_corridor=BUSBAR_CORRIDOR,
                 panel_depth=PANEL_DEPTH):
        self.side_margin_l = side_margin_l
        self.side_margin_r = side_margin_r
        self.top_margin    = top_margin
        self.bottom_margin = bottom_margin
        self.duct_w_l      = duct_w_l
        self.duct_w_r      = duct_w_r
        self.row_gap       = row_gap
        self.item_gap_x    = item_gap_x
        self.item_gap_y    = item_gap_y
        self.busbar_corridor = busbar_corridor
        self.panel_depth   = panel_depth

        self.items: List[Footprint] = []
        self.placed: List[PlacedItem] = []
        self.rows: List[Dict] = []  # 각 row의 y, height, x_cursor 추적

    def add_items(self, fps: List[Footprint]):
        self.items.extend(fps)

    # === 핵심: Shelf(선반) 배치 + 보조 Guillotine =================================
    def _start_first_row(self, x0: int, y0: int):
        self.rows.append({
            "y": y0,
            "height": 0,
            "x_cursor": x0
        })

    def _start_new_row(self, x0: int):
        last = self.rows[-1]
        new_y = last["y"] + last["height"] + self.row_gap
        self.rows.append({
            "y": new_y,
            "height": 0,
            "x_cursor": x0
        })

    def _place_in_current_row(self, fp: Footprint, max_width: int) -> Optional[PlacedItem]:
        """현재 row에 배치 가능한지 시도 → 가능하면 배치, 아니면 None"""
        row = self.rows[-1]
        x = row["x_cursor"]
        y = row["y"]
        w, h = fp.w, fp.h
        rotated = False

        # 회전 허용이면, row 높이 이득이 큰 방향으로 선택
        if fp.rotatable and h > w:
            w, h = h, w
            rotated = True

        # 가로 공간 체크
        if x + w <= max_width:
            # 배치
            pi = PlacedItem(fp.name, x, y, w, h, rotated, fp.kind)
            self.placed.append(pi)
            # row 상태 업데이트
            row["x_cursor"] = x + w + self.item_gap_x
            row["height"] = max(row["height"], h)
            return pi
        return None

    def _guillotine_pack_rest(self, remain: List[Footprint], max_width: int):
        """간단한 직교 분할: 행 생성하면서 잔여 아이템도 순차 배치"""
        while remain:
            self._start_new_row(self.side_margin_l + self.duct_w_l)
            row = self.rows[-1]
            for fp in list(remain):
                pi = self._place_in_current_row(fp, max_width)
                if pi:
                    remain.remove(fp)

    def _expand_items_by_qty(self, fps: List[Footprint]) -> List[Footprint]:
        expanded = []
        for fp in fps:
            for i in range(fp.qty):
                expanded.append(Footprint(
                    name=f"{fp.name}#{i+1}" if fp.qty>1 else fp.name,
                    w=fp.w, h=fp.h, qty=1, rotatable=fp.rotatable, layer=fp.layer, kind=fp.kind
                ))
        return expanded

    def _meter_bottom_block(self, meter_count: int, meter_cols: int) -> Tuple[int,int]:
        """계량기 하부 취부가 필요한 경우(2EA+) 하단 블록 크기 계산"""
        if meter_count < 2:
            return (0,0)
        cols = max(2, meter_cols or 2)
        # 행은 올림으로
        rows = math.ceil(meter_count / cols)
        w = cols * METER_CELL_W
        h = rows * METER_CELL_H
        return (w,h)

    def pack(self,
             base_width_hint: int,
             components: List[Footprint],
             meter_count: int = 0,
             meter_columns: Optional[int] = None) -> Dict:
        """
        base_width_hint: 정책상 최소 폭 감(모선/덕트/여유 감안), 여기에 따라 선반 가로폭 결정
        components: 전면 배치 대상(차단기/FB/SPD/릴레이 등)
        meter_count: 2EA+면 하부 블록 필요
        """
        self.items.clear()
        self.placed.clear()
        self.rows.clear()

        # 1) 아이템 수량 확장 + 우선순위(큰 것 먼저) 정렬
        items = self._expand_items_by_qty(components)
        items.sort(key=lambda f: max(f.w,f.h)*min(f.w,f.h), reverse=True)

        # 2) 전체 유효 가로 폭
        max_width = (self.side_margin_l + self.duct_w_l
                     + base_width_hint
                     + self.duct_w_r + self.side_margin_r)

        # 3) 첫 row 시작 (상부 모선 통로 고려 → 첫 row y 오프셋)
        y0 = self.top_margin + self.busbar_corridor
        x0 = self.side_margin_l + self.duct_w_l
        self._start_first_row(x0, y0)

        # 4) 1차: Shelf로 꽉 채우기
        remain = []
        for fp in items:
            pi = self._place_in_current_row(fp, max_width)
            if not pi:
                remain.append(fp)
        # 5) 2차: 남은 것 Guillotine식으로 새 행에 배치
        if remain:
            self._guillotine_pack_rest(remain, max_width)

        # 6) 하부 계량기 블록 필요 시 추가 행 예약
        meter_w, meter_h = self._meter_bottom_block(meter_count, meter_columns)
        meter_block = None
        if meter_w > 0:
            self._start_new_row(self.side_margin_l + self.duct_w_l)
            row = self.rows[-1]
            # 하부 블록은 좌측 정렬로 고정(안전)
            meter_block = PlacedItem("METER_BLOCK", row["x_cursor"], row["y"], meter_w, meter_h, False, "METER")
            self.placed.append(meter_block)
            row["x_cursor"] += meter_w + self.item_gap_x
            row["height"] = max(row["height"], meter_h)

        # 7) 외함 치수 산출
        used_width = 0
        used_height = 0
        for row in self.rows:
            used_width = max(used_width, row["x_cursor"])
        used_width -= self.item_gap_x  # 마지막 여백 제거

        # 행들의 바닥선 + 하부 여유 포함
        if self.rows:
            last_row = self.rows[-1]
            base_y = last_row["y"] + last_row["height"]
        else:
            base_y = y0

        used_height = base_y + self.bottom_margin

        # 8) 최종 W/H/D
        final_W = max_width
        final_H = used_height
        final_D = self.panel_depth

        layout = {
            "W": int(final_W),
            "H": int(final_H),
            "D": int(final_D),
            "params": {
                "side_margin_l": self.side_margin_l,
                "side_margin_r": self.side_margin_r,
                "top_margin": self.top_margin,
                "bottom_margin": self.bottom_margin,
                "duct_w_l": self.duct_w_l,
                "duct_w_r": self.duct_w_r,
                "busbar_corridor": self.busbar_corridor,
                "row_gap": self.row_gap,
                "item_gap_x": self.item_gap_x,
                "item_gap_y": self.item_gap_y
            },
            "placed": [pi.__dict__ for pi in self.placed],
            "meter_block": meter_block.__dict__ if meter_block else None
        }
        return layout

    # === SVG 내보내기 ===============================================================
    def export_svg(self, layout: Dict, out_path: str):
        W, H = layout["W"], layout["H"]
        placed = layout["placed"]
        meter = layout["meter_block"]

        # SVG 헤더
        svg = []
        svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}">')
        # 배경
        svg.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="#fafafa" stroke="#333" stroke-width="1"/>')

        # 덕트 음영
        if self.duct_w_l:
            svg.append(f'<rect x="{self.side_margin_l}" y="{self.top_margin}" width="{self.duct_w_l}" '
                       f'height="{H - self.top_margin - self.bottom_margin}" fill="#e9f0ff" stroke="#aac" />')
        if self.duct_w_r:
            x = W - self.side_margin_r - self.duct_w_r
            svg.append(f'<rect x="{x}" y="{self.top_margin}" width="{self.duct_w_r}" '
                       f'height="{H - self.top_margin - self.bottom_margin}" fill="#e9f0ff" stroke="#aac" />')

        # 상단 모선 통로
        svg.append(f'<rect x="{self.side_margin_l + self.duct_w_l}" y="{self.top_margin}" '
                   f'width="{W - (self.side_margin_l + self.duct_w_l + self.side_margin_r + self.duct_w_r)}" '
                   f'height="{self.busbar_corridor}" fill="#fff6e6" stroke="#d9b" />')

        # 아이템들
        for pi in placed:
            svg.append(f'<rect x="{pi["x"]}" y="{pi["y"]}" width="{pi["w"]}" height="{pi["h"]}" '
                       f'fill="#fff" stroke="#444"/>')
            svg.append(f'<text x="{pi["x"] + 4}" y="{pi["y"] + 14}" font-size="12" fill="#222">{pi["name"]}</text>')

        # 치수 라벨
        svg.append(f'<text x="{W/2 - 60}" y="{15}" font-size="14" fill="#111">W={W}mm, H={H}mm, D={self.panel_depth}mm</text>')
        svg.append('</svg>')

        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_text("\n".join(svg), encoding="utf-8")

# === 샘플 실행 ====================================================================
def sample_components() -> List[Footprint]:
    """현장 감으로 잡은 대표 크기(예시). 실제로는 차단기설명.txt/부속자재.txt에서 로드 권장.
       크기는 mm, 전면 장착 기준 폭×높이."""
    return [
        Footprint("MAIN_MCCB_4P_150A", 160, 240, 1, True, "front", "MCCB"),
        Footprint("BR_2P_20A", 18*6, 90, 6, True, "front", "BR"),    # 6EA 묶음 가정
        Footprint("ELB_2P_30A", 36*2, 120, 2, True, "front", "ELB"),
        Footprint("SPD", 72, 120, 1, True, "front", "SPD"),
        Footprint("CONTACTOR_25A", 45, 90, 3, True, "front", "MAG"),
        Footprint("MCB_AUX", 18*3, 90, 1, True, "front", "AUX"),
    ]

def main():
    # 1) 컴포넌트(예시) 구성
    comps = sample_components()

    # 2) 정책상 base 폭 힌트: 분기 수/덕트/버스바 고려하여 대략 480~720 이상 권장
    base_width_hint = 720

    # 3) 계량기 규칙: 1EA=사이드(폭/높이 증가 없음), 2EA+=하부취부(셀 폭*열, 셀 높이*행)
    meter_count = 2
    meter_cols  = 2

    # 4) 배치 실행
    vl = VirtualLayout()
    layout = vl.pack(base_width_hint, comps, meter_count, meter_cols)

    # 5) 출력
    out_dir = Path("out")
    out_dir.mkdir(exist_ok=True, parents=True)
    (out_dir / "layout.json").write_text(json.dumps(layout, ensure_ascii=False, indent=2), encoding="utf-8")
    vl.export_svg(layout, str(out_dir / "layout.svg"))

    print("=== VIRTUAL LAYOUT RESULT ===")
    print(f'W={layout["W"]}mm, H={layout["H"]}mm, D={layout["D"]}mm')
    print(f'placed: {len(layout["placed"])} items')
    print(f'SVG: {out_dir / "layout.svg"}')

if __name__ == "__main__":
    main()
