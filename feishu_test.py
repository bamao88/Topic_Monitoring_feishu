#!/usr/bin/env python3
"""
飞书文档 API 测试工具

所需权限（在飞书开发者后台开启）:
1. docx:document 或 docx:document:create - 用于创建文档
2. drive:drive 或 drive:drive.metadata:readonly - 用于获取文件元信息

权限开启地址: https://open.feishu.cn/app/cli_a9805d1addbed00e/auth
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from feishu.client import FeishuClient

# 文档 token（从 URL 中获取）
DOCUMENT_TOKEN = "Pr3idW7SFo5Np0x7hlqcdtzAnJf"

def test_get_meta():
    """测试获取文档元信息"""
    client = FeishuClient()

    print(f"获取文档元信息: {DOCUMENT_TOKEN}")
    meta = client.get_file_meta(DOCUMENT_TOKEN, "docx")

    if meta:
        print(f"文档名称: {meta.get('name')}")
        print(f"文档类型: {meta.get('type')}")
        print(f"父文件夹 token: {meta.get('parent_token')}")
        print(f"文档 URL: {meta.get('url')}")

        parent_token = meta.get('parent_token')
        if parent_token:
            print("\n" + "=" * 50)
            print("请将以下内容添加到 .env 文件中:")
            print(f"FEISHU_REPORT_FOLDER_TOKEN={parent_token}")
            print("=" * 50)
    else:
        print("获取文档元信息失败")
        print("\n提示: 需要在飞书开发者后台开启 drive:drive 或 drive:drive.metadata:readonly 权限")
        print("请访问: https://open.feishu.cn/app/cli_a9805d1addbed00e/auth")


def test_create_doc():
    """测试创建文档（不指定文件夹）"""
    client = FeishuClient()

    print("测试创建文档...")
    doc_info = client.create_document("测试文档-自动生成")

    if doc_info:
        print(f"文档创建成功!")
        print(f"文档ID: {doc_info.get('document_id')}")
        print(f"文档URL: {doc_info.get('url')}")
    else:
        print("文档创建失败")


def test_create_doc_with_content():
    """测试创建带内容的文档"""
    client = FeishuClient()

    print("测试创建带内容的文档...")
    markdown_content = """# 测试标题

这是一个测试文档。

## 小节

- 列表项 1
- 列表项 2

> 这是一段引用

**粗体** 和 *斜体*
"""

    doc_info = client.create_document_from_markdown(
        title="测试文档-带内容",
        markdown_content=markdown_content,
    )

    if doc_info:
        print(f"文档创建成功!")
        print(f"文档ID: {doc_info.get('document_id')}")
        print(f"文档URL: {doc_info.get('url')}")
    else:
        print("文档创建失败")


def show_permissions():
    """显示所需权限说明"""
    print("=" * 60)
    print("飞书应用所需权限")
    print("=" * 60)
    print()
    print("请在飞书开发者后台为应用开启以下权限：")
    print()
    print("1. 文档创建权限（二选一）:")
    print("   - docx:document")
    print("   - docx:document:create")
    print()
    print("2. 云文档元信息读取权限（二选一）:")
    print("   - drive:drive")
    print("   - drive:drive.metadata:readonly")
    print()
    print("权限开启步骤:")
    print("1. 访问飞书开发者后台: https://open.feishu.cn/")
    print("2. 进入你的应用")
    print("3. 点击「权限管理」->「云文档」")
    print("4. 勾选上述权限并发布应用")
    print()
    print("快捷链接:")
    print("https://open.feishu.cn/app/cli_a9805d1addbed00e/auth")
    print("=" * 60)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="飞书文档测试工具")
    parser.add_argument("--meta", action="store_true", help="获取文档元信息")
    parser.add_argument("--create", action="store_true", help="测试创建空文档")
    parser.add_argument("--create-content", action="store_true", help="测试创建带内容的文档")
    parser.add_argument("--permissions", action="store_true", help="显示所需权限说明")

    args = parser.parse_args()

    if args.permissions:
        show_permissions()
    elif args.meta:
        test_get_meta()
    elif args.create:
        test_create_doc()
    elif args.create_content:
        test_create_doc_with_content()
    else:
        # 默认显示权限说明
        show_permissions()


if __name__ == "__main__":
    main()
