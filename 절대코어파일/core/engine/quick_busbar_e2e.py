# quick_busbar_e2e.py
from estimate_engine import (
    main_busbar_kg_factor, busbar_kg_factor_by_main,
    busbar_spec_by_main_amp, busbar_spec_by_branch_amp,
    MAIN_BUSBAR_UNIT_PRICE, BRANCH_BUSBAR_UNIT_PRICE
)

def round_to_2(x):
    try: return round(float(x), 2)
    except: return 0.0

def build_busbar_lines(W, H, main_amp_int, start_no=1):
    lines = []
    no = start_no

    # MAIN
    main_bus_spec = busbar_spec_by_main_amp(main_amp_int)
    main_bus_kg   = round_to_2((W * H) * main_busbar_kg_factor(main_amp_int))
    main_bus_amt  = round_to_2(main_bus_kg * MAIN_BUSBAR_UNIT_PRICE)
    lines.append({"no": no, "품명": "MAIN BUS-BAR", "규격": main_bus_spec, "단위": "KG",
                  "수량": main_bus_kg, "단가": MAIN_BUSBAR_UNIT_PRICE, "금액": main_bus_amt}); no += 1

    # BRANCH
    bus_spec = busbar_spec_by_branch_amp(main_amp_int)
    bus_kg   = round_to_2((W * H) * busbar_kg_factor_by_main(main_amp_int))
    bus_amt  = round_to_2(bus_kg * BRANCH_BUSBAR_UNIT_PRICE)
    lines.append({"no": no, "품명": "BUS-BAR", "규격": bus_spec, "단위": "KG",
                  "수량": bus_kg, "단가": BRANCH_BUSBAR_UNIT_PRICE, "금액": bus_amt}); no += 1

    subtotal = round(sum(float(r.get("금액") or 0) for r in lines), 0)
    lines.append({"no": no, "품명": "소계", "규격": "", "단위": "", "수량": "", "단가": "", "금액": subtotal}); no += 1
    return lines

if __name__ == "__main__":
    W, H, amp = 800, 1200, 250
    rows = build_busbar_lines(W, H, amp)
    for r in rows:
        print(r)
