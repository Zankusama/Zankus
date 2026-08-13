#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
usage: python3 check_standards.py [standards.json 路径]
默认路径: ~/.workbuddy/oxhorse-polisher/standards.json（可用参数覆盖）
功能: 校验 oxhorse-polisher 标准文件 schema（v2.1）
  - schema_version 字段存在
  - task_standards 为数组
  - 每项含 task_type（匹配键，必须唯一）
  - 新标准字段（why/done/proof）存在性建议级提示（旧数据迁移允许缺失）
退出码: 0=通过 / 1=校验失败（可机器化验收用）
"""
import json
import sys
import os

DEFAULT = os.path.expanduser("~/.workbuddy/oxhorse-polisher/standards.json")


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    if not os.path.exists(path):
        print(f"❌ 标准文件不存在: {path}")
        return 1
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析失败: {e}")
        return 1

    errors = []
    warns = []

    if "schema_version" not in data:
        errors.append("缺 schema_version 字段（应 >= 2.1）")
    elif data.get("schema_version") != "2.1":
        warns.append(f"schema_version={data.get('schema_version')}（预期 2.1）")

    items = data.get("task_standards")
    if not isinstance(items, list):
        errors.append("task_standards 不是数组")
        return 1

    seen = {}
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"第{i+1}条不是对象")
            continue
        tt = item.get("task_type")
        if not tt:
            errors.append(f"第{i+1}条缺 task_type（匹配键）")
        elif tt in seen:
            errors.append(f"task_type 重复: {tt}（同一类型应只保留最新一条）")
        else:
            seen[tt] = i
        if not item.get("created_at"):
            warns.append(f"第{i+1}条缺 created_at")
        for field in ("why", "done", "proof"):
            if field not in item:
                warns.append(f"第{i+1}条({tt})缺新标准字段 {field}（旧数据迁移可暂缺）")

    if errors:
        for e in errors:
            print(f"❌ {e}")
        print("校验失败: 退出码 1")
        return 1
    for w in warns:
        print(f"⚠️ {w}")
    print(f"✅ standards.json schema 校验通过（{len(items)} 条标准，task_type 唯一）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
