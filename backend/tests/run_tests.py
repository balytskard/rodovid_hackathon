#!/usr/bin/env python
"""
🧪 Rodovid Test Runner
======================

Запуск всіх тестів з красивим звітом.

Використання:
    python run_tests.py              # Всі тести
    python run_tests.py --critical   # Тільки критичні
    python run_tests.py --security   # Тільки security
    python run_tests.py --quick      # Швидкі unit тести
"""

import sys
import os
import subprocess
import argparse
from datetime import datetime

# Додаємо backend до шляху
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def print_banner():
    """Виводимо красивий банер"""
    print("""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   🌳 РОДОВІД - AUTOMATED TEST SUITE                          ║
║                                                               ║
║   Zero-Knowledge Family Tree Security Tests                   ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
    """)


def run_pytest(markers=None, extra_args=None):
    """Запуск pytest з параметрами"""
    cmd = ["python", "-m", "pytest", ".", "-v"]
    
    if markers:
        cmd.extend(["-m", markers])
    
    if extra_args:
        cmd.extend(extra_args)
    
    # Запускаємо
    result = subprocess.run(cmd, cwd=os.path.dirname(__file__))
    return result.returncode


def run_all_tests():
    """Запуск всіх тестів"""
    print("\n🧪 Running ALL tests...\n")
    return run_pytest()


def run_critical_tests():
    """Тільки критичні тести"""
    print("\n🔴 Running CRITICAL tests...\n")
    return run_pytest("critical")


def run_security_tests():
    """Тільки security тести"""
    print("\n🔐 Running SECURITY tests...\n")
    return run_pytest("security")


def run_quick_tests():
    """Швидкі unit тести"""
    print("\n⚡ Running QUICK (unit) tests...\n")
    return run_pytest("unit")


def run_integration_tests():
    """Integration тести (потребують Neo4j)"""
    print("\n🔗 Running INTEGRATION tests...\n")
    return run_pytest("integration")


def run_performance_tests():
    """Performance тести"""
    print("\n📊 Running PERFORMANCE tests...\n")
    return run_pytest("performance")


def generate_report():
    """Генерація HTML звіту"""
    print("\n📄 Generating HTML report...\n")
    return run_pytest(extra_args=["--html=report.html", "--self-contained-html"])


def main():
    parser = argparse.ArgumentParser(description="Rodovid Test Runner")
    
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--all", action="store_true", help="Run all tests")
    group.add_argument("--critical", action="store_true", help="Run only critical tests")
    group.add_argument("--security", action="store_true", help="Run security tests")
    group.add_argument("--quick", action="store_true", help="Run quick unit tests")
    group.add_argument("--integration", action="store_true", help="Run integration tests")
    group.add_argument("--performance", action="store_true", help="Run performance tests")
    group.add_argument("--report", action="store_true", help="Generate HTML report")
    
    args = parser.parse_args()
    
    print_banner()
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if args.critical:
        exit_code = run_critical_tests()
    elif args.security:
        exit_code = run_security_tests()
    elif args.quick:
        exit_code = run_quick_tests()
    elif args.integration:
        exit_code = run_integration_tests()
    elif args.performance:
        exit_code = run_performance_tests()
    elif args.report:
        exit_code = generate_report()
    else:
        exit_code = run_all_tests()
    
    # Фінальний звіт
    print("\n" + "="*60)
    if exit_code == 0:
        print("✅ ALL TESTS PASSED!")
    else:
        print("❌ SOME TESTS FAILED!")
    print("="*60 + "\n")
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

