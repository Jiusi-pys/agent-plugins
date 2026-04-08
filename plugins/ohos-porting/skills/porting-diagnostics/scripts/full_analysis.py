#!/usr/bin/env python3
"""
full_analysis.py - OHOS 移植完整诊断分析
用法: python3 full_analysis.py /path/to/source [--output report.json]
"""

import os
import re
import json
import argparse
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass, asdict
from typing import List, Dict, Set

# API 分类
RED_APIS = {
    'io_uring': 'io_uring 异步 I/O，OHOS 不支持',
    'clone.*CLONE_NEW': 'Linux namespace，OHOS 不支持',
    'unshare': 'Linux namespace，OHOS 不支持',
    'setns': 'Linux namespace，OHOS 不支持',
    'perf_event_open': 'Linux perf，OHOS 不支持',
    'bpf': 'eBPF，OHOS 不支持',
    'mount.*MS_': 'mount flags，受限',
    'pivot_root': '根文件系统切换，不支持',
}

YELLOW_APIS = {
    'epoll_create': 'epoll → poll() 或 select()',
    'epoll_ctl': 'epoll → poll() 或 select()',
    'epoll_wait': 'epoll → poll() 或 select()',
    'inotify_init': 'inotify → OHOS FileWatcher',
    'inotify_add_watch': 'inotify → OHOS FileWatcher',
    'eventfd': 'eventfd → pipe()',
    'signalfd': 'signalfd → signal() handler',
    'timerfd_create': 'timerfd → timer_create()',
    'timerfd_settime': 'timerfd → timer_settime()',
    'getauxval': 'getauxval → 手动读取或条件编译',
    'prctl': 'prctl → 部分支持，需验证',
    'sched_setaffinity': 'CPU 亲和性 → 部分支持',
}

GREEN_APIS = {
    'pthread_', 'socket', 'bind', 'listen', 'accept', 'connect',
    'open', 'read', 'write', 'close', 'lseek', 'fstat',
    'malloc', 'free', 'realloc', 'calloc',
    'memcpy', 'memset', 'strcmp', 'strlen',
    'printf', 'fprintf', 'sprintf', 'snprintf',
}

@dataclass
class APIUsage:
    name: str
    category: str  # red, yellow, green
    count: int
    files: List[str]
    suggestion: str

@dataclass
class Dependency:
    name: str
    required: bool
    ohos_available: str  # yes, no, unknown

@dataclass
class DiagnosticReport:
    project_path: str
    file_stats: Dict[str, int]
    api_usages: List[APIUsage]
    dependencies: List[Dependency]
    proc_sys_usage: List[str]
    grade: str
    estimated_effort: str
    risks: List[str]
    recommendations: List[str]

def scan_directory(path: Path) -> Dict[str, int]:
    """统计源文件"""
    stats = {'c': 0, 'cpp': 0, 'h': 0, 'total_lines': 0}
    for ext, key in [('.c', 'c'), ('.cpp', 'cpp'), ('.cc', 'cpp'), 
                      ('.cxx', 'cpp'), ('.h', 'h'), ('.hpp', 'h')]:
        for f in path.rglob(f'*{ext}'):
            stats[key] += 1
            try:
                stats['total_lines'] += len(f.read_text(errors='ignore').splitlines())
            except:
                pass
    return stats

def scan_api_usage(path: Path) -> List[APIUsage]:
    """扫描 API 使用"""
    usages = []
    api_files = defaultdict(set)
    api_counts = defaultdict(int)
    
    source_files = list(path.rglob('*.c')) + list(path.rglob('*.cpp')) + \
                   list(path.rglob('*.cc')) + list(path.rglob('*.h'))
    
    for src in source_files:
        try:
            content = src.read_text(errors='ignore')
        except:
            continue
        
        # Red APIs
        for api, desc in RED_APIS.items():
            matches = re.findall(api, content)
            if matches:
                api_counts[('red', api, desc)] += len(matches)
                api_files[('red', api, desc)].add(str(src.relative_to(path)))
        
        # Yellow APIs
        for api, desc in YELLOW_APIS.items():
            pattern = re.escape(api) if not api.endswith('_') else api
            matches = re.findall(pattern, content)
            if matches:
                api_counts[('yellow', api, desc)] += len(matches)
                api_files[('yellow', api, desc)].add(str(src.relative_to(path)))
    
    for (cat, api, desc), count in api_counts.items():
        usages.append(APIUsage(
            name=api,
            category=cat,
            count=count,
            files=list(api_files[(cat, api, desc)])[:10],
            suggestion=desc
        ))
    
    return sorted(usages, key=lambda x: (x.category != 'red', -x.count))

def scan_dependencies(path: Path) -> List[Dependency]:
    """扫描依赖库"""
    deps = []
    cmake = path / 'CMakeLists.txt'
    
    # OHOS 已知可用库
    ohos_available = {
        'pthread', 'dl', 'rt', 'm', 'z', 'ssl', 'crypto',
        'curl', 'sqlite3', 'jpeg', 'png', 'xml2',
    }
    
    if cmake.exists():
        content = cmake.read_text(errors='ignore')
        
        # find_package
        for match in re.findall(r'find_package\((\w+)', content):
            deps.append(Dependency(
                name=match,
                required=True,
                ohos_available='unknown'
            ))
        
        # pkg_check_modules
        for match in re.findall(r'pkg_check_modules\([^)]*\s+(\w+)', content):
            available = 'yes' if match.lower() in ohos_available else 'unknown'
            deps.append(Dependency(
                name=match,
                required=True,
                ohos_available=available
            ))
        
        # target_link_libraries
        for match in re.findall(r'target_link_libraries\([^)]+\)', content):
            for lib in re.findall(r'-l(\w+)|(\w+)(?:\s|$)', match):
                lib_name = lib[0] or lib[1]
                if lib_name and lib_name not in ['PUBLIC', 'PRIVATE', 'INTERFACE']:
                    available = 'yes' if lib_name.lower() in ohos_available else 'unknown'
                    deps.append(Dependency(
                        name=lib_name,
                        required=False,
                        ohos_available=available
                    ))
    
    # 去重
    seen = set()
    unique_deps = []
    for d in deps:
        if d.name not in seen:
            seen.add(d.name)
            unique_deps.append(d)
    
    return unique_deps

def scan_proc_sys(path: Path) -> List[str]:
    """扫描 /proc /sys 使用"""
    usages = []
    for src in list(path.rglob('*.c')) + list(path.rglob('*.cpp')):
        try:
            content = src.read_text(errors='ignore')
            for match in re.finditer(r'["\']/(proc|sys)/[^"\']+["\']', content):
                usages.append(f"{src.relative_to(path)}: {match.group(0)}")
        except:
            pass
    return usages[:20]

def calculate_grade(api_usages: List[APIUsage], proc_count: int) -> tuple:
    """计算移植难度等级"""
    red_count = sum(u.count for u in api_usages if u.category == 'red')
    yellow_count = sum(u.count for u in api_usages if u.category == 'yellow')
    
    if red_count > 5 or proc_count > 20:
        return 'D', '不建议移植', ['深度依赖 Linux 特性']
    elif red_count > 0 or proc_count > 10:
        return 'C', '1-2 周', ['需要重构核心逻辑']
    elif yellow_count > 20:
        return 'C', '1-2 周', ['大量 API 需要适配']
    elif yellow_count > 5:
        return 'B', '1-3 天', ['中等改动量']
    else:
        return 'A', '< 1 天', ['简单移植']

def generate_report(path: str) -> DiagnosticReport:
    """生成完整诊断报告"""
    p = Path(path)
    
    file_stats = scan_directory(p)
    api_usages = scan_api_usage(p)
    dependencies = scan_dependencies(p)
    proc_sys = scan_proc_sys(p)
    grade, effort, risks = calculate_grade(api_usages, len(proc_sys))
    
    recommendations = []
    if grade in ['C', 'D']:
        recommendations.append('评估替代库')
        recommendations.append('与团队确认移植必要性')
    if any(u.category == 'red' for u in api_usages):
        recommendations.append('隔离 Linux 特定代码到独立模块')
    if len([d for d in dependencies if d.ohos_available == 'unknown']) > 0:
        recommendations.append('验证依赖库 OHOS 可用性')
    
    return DiagnosticReport(
        project_path=str(p.absolute()),
        file_stats=file_stats,
        api_usages=api_usages,
        dependencies=dependencies,
        proc_sys_usage=proc_sys,
        grade=grade,
        estimated_effort=effort,
        risks=risks,
        recommendations=recommendations
    )

def print_report(report: DiagnosticReport):
    """打印报告"""
    print("╔" + "═" * 60 + "╗")
    print("║" + "OHOS 移植可行性诊断报告".center(56) + "║")
    print("╠" + "═" * 60 + "╣")
    print(f"║ 评级: {report.grade}".ljust(61) + "║")
    print(f"║ 预估工时: {report.estimated_effort}".ljust(61) + "║")
    print("╚" + "═" * 60 + "╝")
    print()
    
    print("【文件统计】")
    print(f"  C 文件: {report.file_stats['c']}")
    print(f"  C++ 文件: {report.file_stats['cpp']}")
    print(f"  头文件: {report.file_stats['h']}")
    print(f"  总行数: {report.file_stats['total_lines']}")
    print()
    
    red_apis = [u for u in report.api_usages if u.category == 'red']
    yellow_apis = [u for u in report.api_usages if u.category == 'yellow']
    
    if red_apis:
        print("【红灯 API (不可移植)】")
        for u in red_apis:
            print(f"  {u.name}: {u.count} 处")
            print(f"    建议: {u.suggestion}")
        print()
    
    if yellow_apis:
        print("【黄灯 API (需要适配)】")
        for u in yellow_apis[:10]:
            print(f"  {u.name}: {u.count} 处 → {u.suggestion}")
        if len(yellow_apis) > 10:
            print(f"  ... 还有 {len(yellow_apis) - 10} 项")
        print()
    
    if report.dependencies:
        print("【依赖库】")
        for d in report.dependencies[:10]:
            status = {'yes': '✓', 'no': '✗', 'unknown': '?'}[d.ohos_available]
            print(f"  {status} {d.name}")
        print()
    
    if report.proc_sys_usage:
        print("【/proc /sys 使用】")
        for usage in report.proc_sys_usage[:5]:
            print(f"  {usage}")
        print()
    
    print("【风险】")
    for risk in report.risks:
        print(f"  ⚠ {risk}")
    print()
    
    print("【建议】")
    for rec in report.recommendations:
        print(f"  → {rec}")

def main():
    parser = argparse.ArgumentParser(description='OHOS 移植可行性诊断')
    parser.add_argument('path', help='源码目录路径')
    parser.add_argument('--output', '-o', help='输出 JSON 文件')
    args = parser.parse_args()
    
    report = generate_report(args.path)
    print_report(report)
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(asdict(report), f, indent=2, ensure_ascii=False)
        print(f"\n报告已保存到: {args.output}")

if __name__ == '__main__':
    main()
