# 부자재 및 액세서리 규칙

## 출처
`C:\Users\PC\Desktop\절대코어파일\핵심파일풀\KIS\Knowledge\packs/`

## 파일 목록
- `accessories.json` / `accessories_v1.0.0.json`: 부자재 카탈로그
- `accessory_layout_rules.json`: 부자재 배치 규칙
- `accessory_rules.json`: 부자재 선택 규칙

## 부자재 카테고리 (추정)
1. **퓨즈 홀더** (FUSE_HOLDER): 4,500원
2. **단자대** (TERM_BLOCK): 800원
3. **PVC 덕트** (PVC_DUCT): 6,000원
4. **전선 세트** (WIRE_SET): 12,000원
5. **푸시버튼** (PBL_ONOFF): 3,500원

## 배치 규칙
- 양 어레이 활성화: 400AF 이상
- 최소 간격: 25mm
- 측면 여유: 50mm
- 대면 배치 중심 간격: 150mm
- 유지보수 여유: 75mm

## 적용 우선순위
1. 브레이커 AF 기준 부자재 선택
2. 외함 크기에 따른 PVC 덕트 필요량
3. 배치 규칙에 따른 간격 조정
4. 발열량 기준 냉각 부자재 추가

## 통합 필요
현재 프로젝트의 자재 카탈로그 API와 통합 필요:
- `/v1/catalog`: 자재 카탈로그 조회
- 부자재 자동 선택 로직
- BOM 생성 시 부자재 포함
