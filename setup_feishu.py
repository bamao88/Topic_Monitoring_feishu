#!/usr/bin/env python3
"""
飞书多维表格设置脚本

使用方法:
    python setup_feishu.py

功能:
1. 测试飞书连接
2. 创建博主/笔记/评论三张数据表
3. 输出配置信息供后续使用
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from loguru import logger
from feishu.client import FeishuClient
from config.feishu_config import (
    FEISHU_APP_ID,
    FEISHU_APP_TOKEN,
    TABLE_IDS,
    FIELD_DEFINITIONS,
)


def main():
    print("=" * 60)
    print("飞书多维表格设置")
    print("=" * 60)

    # 检查配置
    print(f"\n[配置检查]")
    print(f"APP_ID: {FEISHU_APP_ID[:10]}..." if FEISHU_APP_ID else "APP_ID: 未配置")
    print(f"APP_TOKEN: {FEISHU_APP_TOKEN[:10]}..." if FEISHU_APP_TOKEN else "APP_TOKEN: 未配置")

    if not FEISHU_APP_ID:
        print("\n错误: 请先在 config/feishu_config.py 中配置 FEISHU_APP_ID")
        return

    if not FEISHU_APP_TOKEN:
        print("\n" + "=" * 60)
        print("下一步: 创建飞书多维表格")
        print("=" * 60)
        print("""
请按以下步骤操作:

1. 打开飞书，创建一个新的多维表格 (Base)
   - 可以在飞书文档中点击 "+" -> "多维表格"

2. 从 URL 中获取 app_token
   - URL 格式: https://xxx.feishu.cn/base/xxxxAPP_TOKENxxxx?table=tblXXX
   - app_token 是 /base/ 后面的那串字符

3. 将 app_token 填入 config/feishu_config.py:
   FEISHU_APP_TOKEN = "你的app_token"

4. 给飞书应用授权访问该多维表格:
   - 在多维表格右上角点击 "..." -> "更多" -> "添加文档应用"
   - 搜索并添加你的飞书应用

5. 重新运行此脚本: python setup_feishu.py
""")
        return

    # 初始化客户端
    try:
        client = FeishuClient()
        print("\n飞书客户端初始化成功")
    except Exception as e:
        print(f"\n飞书客户端初始化失败: {e}")
        return

    # 测试连接
    print("\n[测试连接]")
    if not client.test_connection():
        print("连接失败，请检查配置")
        return

    # 获取现有表格
    print("\n[现有数据表]")
    tables = client.list_tables()
    if tables:
        for t in tables:
            print(f"  - {t['name']}: {t['table_id']}")
    else:
        print("  (无)")

    # 检查需要创建的表格
    print("\n[表格配置]")
    tables_to_create = []
    existing_names = {t["name"] for t in tables}

    table_configs = [
        ("bloggers", "博主表"),
        ("notes", "笔记表"),
        ("comments", "评论表"),
    ]

    for key, name in table_configs:
        table_id = TABLE_IDS.get(key)
        if table_id:
            print(f"  {name}: 已配置 ({table_id})")
        elif name in existing_names:
            # 找到已存在的表格 ID
            for t in tables:
                if t["name"] == name:
                    print(f"  {name}: 已存在 ({t['table_id']}) - 请更新配置")
        else:
            print(f"  {name}: 需要创建")
            tables_to_create.append((key, name))

    # 创建缺失的表格
    if tables_to_create:
        print("\n[创建数据表]")
        created_tables = {}

        for key, name in tables_to_create:
            fields = FIELD_DEFINITIONS.get(key, [])
            if not fields:
                print(f"  跳过 {name}: 无字段定义")
                continue

            print(f"  创建 {name}...")
            table_id = client.create_table(name, fields)
            if table_id:
                created_tables[key] = table_id
                print(f"    成功: {table_id}")
            else:
                print(f"    失败")

        if created_tables:
            print("\n" + "=" * 60)
            print("请将以下配置更新到 config/feishu_config.py:")
            print("=" * 60)
            print("\nTABLE_IDS = {")
            for key, table_id in {**TABLE_IDS, **created_tables}.items():
                if table_id:
                    print(f'    "{key}": "{table_id}",')
            print("}")
    else:
        all_configured = all(TABLE_IDS.get(key) for key, _ in table_configs)
        if all_configured:
            print("\n" + "=" * 60)
            print("所有表格已配置完成!")
            print("=" * 60)
            print("\n可以运行数据同步: python main.py")
        else:
            print("\n请更新 TABLE_IDS 配置后重新运行")


if __name__ == "__main__":
    main()
