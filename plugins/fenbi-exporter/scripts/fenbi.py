#!/usr/bin/env python3
"""Fenbi exporter command line; stdout contains summaries, never credentials."""
import argparse
import json
import sys
from pathlib import Path
from fenbi_exporter.browser import BrowserSession, AccessRequired
from fenbi_exporter.core import ExportStore


def parser():
    root = argparse.ArgumentParser(description='粉笔课程资料与做题记录本地导出')
    sub = root.add_subparsers(dest='command', required=True)
    for name in ('login', 'course', 'history', 'resume', 'verify'):
        p = sub.add_parser(name)
        p.add_argument('--output', type=Path, default=Path.home() / 'Documents' / 'FenbiExports')
        if name != 'verify':
            p.add_argument('--profile', type=Path)
            p.add_argument('--headless', action='store_true')
        if name in ('course', 'history', 'resume'):
            p.add_argument('--fresh-session', action='store_true', help='下载崩溃时使用临时会话，在内存中复用专用配置的登录状态')
        if name == 'login':
            p.add_argument('--timeout', type=int, default=600)
        if name == 'course':
            p.add_argument('course')
            p.add_argument('--limit', type=int, help='仅用于小范围验收：最多处理课时数')
            p.add_argument('--group', help='仅下载名称完全匹配的科目分组')
            p.add_argument('--lesson', help='仅下载名称完全匹配的课时')
        if name == 'history':
            p.add_argument('--subject', choices=['all', 'xingce', 'shenlun'], default='all')
            p.add_argument('--from', dest='start')
            p.add_argument('--to', dest='end')
            p.add_argument('--record-url', action='append', default=[])
            p.add_argument('--limit', type=int, help='仅用于小范围验收：最多处理记录数')
        if name == 'resume':
            p.add_argument('--run', required=True)
    return root


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    args = parser().parse_args()
    try:
        if args.command == 'verify':
            if not (args.output / 'index.json').exists():
                raise ValueError('导出目录内没有 index.json')
            result = ExportStore(args.output).verify()
        else:
            with BrowserSession(args.profile, args.headless, getattr(args, 'fresh_session', False)) as browser:
                if args.command == 'login':
                    browser.login(args.timeout)
                    result = {'status': 'complete', 'action': 'login'}
                else:
                    from fenbi_exporter.workflow import execute
                    result = execute(args, browser)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result['status'] == 'complete' else (3 if result['status'] in ('auth_required','user_action_required','blocked') else (1 if result['status']=='failed' else 2))
    except AccessRequired as exc:
        print(json.dumps({'status': exc.status, 'action': '请运行 login 并在浏览器中处理登录或验证'}, ensure_ascii=False))
        return 3
    except (ValueError, RuntimeError) as exc:
        # Our domain exceptions contain only fixed text or non-secret local identifiers.
        print(json.dumps({'status': 'failed', 'reason': str(exc)}, ensure_ascii=False))
        return 1
    except Exception as exc:
        print(json.dumps({'status': 'failed', 'reason': type(exc).__name__}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    sys.exit(main())
