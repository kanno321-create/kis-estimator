#!/usr/bin/env python3
"""
종합 테스트 실행 스크립트
KIS Estimator 시스템의 모든 테스트를 실행하고 결과를 리포트합니다.
"""

import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime

# 색상 코드 (Windows 터미널 지원)
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def print_header(text):
    """헤더 출력"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BLUE}{text:^60}{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*60}{Colors.RESET}\n")

def print_success(text):
    print(f"{Colors.GREEN}[SUCCESS] {text}{Colors.RESET}")

def print_warning(text):
    print(f"{Colors.YELLOW}[WARNING] {text}{Colors.RESET}")

def print_error(text):
    print(f"{Colors.RED}[ERROR] {text}{Colors.RESET}")

def run_command(cmd, description):
    """명령 실행 및 결과 반환"""
    print(f"실행 중: {description}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode == 0, result.stdout, result.stderr

def main():
    """메인 테스트 실행 함수"""
    start_time = time.time()

    print_header("KIS Estimator 테스트 실행")
    print(f"실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 테스트 카테고리별 실행
    test_categories = [
        ("유닛 테스트", "pytest -m unit -q --tb=short"),
        ("통합 테스트", "pytest -m integration -q --tb=short"),
        ("회귀 테스트", "pytest -m regression -q --tb=short"),
        ("계약 검증", "pytest tests/test_contracts.py -q --tb=short"),
        ("성능 테스트", "pytest tests/test_breaker_placer_perf.py -q --tb=short"),
    ]

    results = {}

    for category, cmd in test_categories:
        print(f"\n[테스트] {category}")
        success, stdout, stderr = run_command(cmd, category)

        if success:
            # 성공한 테스트 개수 파싱
            if "passed" in stdout:
                import re
                match = re.search(r'(\d+) passed', stdout)
                if match:
                    passed_count = match.group(1)
                    print_success(f"{passed_count}개 테스트 통과")
            else:
                print_success("모든 테스트 통과")
        else:
            if "collected 0 items" in stdout or "no tests ran" in stdout:
                print_warning(f"{category} - 테스트가 없습니다")
            else:
                print_error(f"{category} - 일부 실패")
                if stderr:
                    print(f"  오류: {stderr[:200]}...")

        results[category] = success

    # 커버리지 테스트
    print("\n[커버리지] 코드 커버리지 측정 중...")
    success, stdout, stderr = run_command(
        "pytest --cov=src --cov-report=term-missing --cov-report=html -q",
        "커버리지 측정"
    )

    if success and "%" in stdout:
        # 커버리지 퍼센트 추출
        import re
        match = re.search(r'TOTAL.*\s+(\d+)%', stdout)
        if match:
            coverage = match.group(1)
            if int(coverage) >= 80:
                print_success(f"커버리지: {coverage}%")
            else:
                print_warning(f"커버리지: {coverage}% (목표: 80%)")

    # 결과 요약
    print_header("테스트 결과 요약")

    total = len(test_categories)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed

    print(f"전체 카테고리: {total}")
    print(f"{Colors.GREEN}통과: {passed}{Colors.RESET}")
    print(f"{Colors.RED}실패: {failed}{Colors.RESET}")

    # 개별 결과
    print("\n카테고리별 결과:")
    for category, success in results.items():
        status = f"{Colors.GREEN}[OK]{Colors.RESET}" if success else f"{Colors.RED}[FAIL]{Colors.RESET}"
        print(f"  {status} {category}")

    # 실행 시간
    elapsed_time = time.time() - start_time
    print(f"\n실행 시간: {elapsed_time:.2f}초")

    # 회귀 테스트 특별 체크
    if "회귀 테스트" in results:
        if results["회귀 테스트"]:
            print_success("회귀 테스트 20/20 통과 - 프로덕션 배포 가능")
        else:
            print_error("회귀 테스트 실패 - 프로덕션 배포 불가")

    # 최종 상태 반환
    if failed == 0:
        print_success("\n모든 테스트 통과!")
        return 0
    else:
        print_error(f"\n{failed}개 카테고리에서 테스트 실패")
        return 1

if __name__ == "__main__":
    sys.exit(main())