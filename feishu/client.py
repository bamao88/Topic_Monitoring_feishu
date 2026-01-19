"""飞书 API 客户端"""
import sys
from typing import Dict, List, Any, Optional
from pathlib import Path

# 确保项目根目录优先于 MediaCrawler
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import lark_oapi as lark
from lark_oapi.api.bitable.v1 import *
from lark_oapi.api.docx.v1 import *
from lark_oapi.api.drive.v1 import *
from utils.logger import logger

from config.feishu_config import (
    FEISHU_APP_ID,
    FEISHU_APP_SECRET,
    FEISHU_APP_TOKEN,
    TABLE_IDS,
    FIELD_DEFINITIONS,
)


class FeishuClient:
    """飞书多维表格客户端"""

    def __init__(self):
        self.app_id = FEISHU_APP_ID
        self.app_secret = FEISHU_APP_SECRET
        self.app_token = FEISHU_APP_TOKEN
        self.table_ids = TABLE_IDS

        if not self.app_id or not self.app_secret:
            raise ValueError("请配置飞书 APP_ID 和 APP_SECRET")

        self.client = lark.Client.builder() \
            .app_id(self.app_id) \
            .app_secret(self.app_secret) \
            .log_level(lark.LogLevel.WARNING) \
            .build()

    def _get_table_id(self, table_name: str) -> str:
        """获取表格ID"""
        table_id = self.table_ids.get(table_name)
        if not table_id:
            raise ValueError(f"未配置表格ID: {table_name}")
        return table_id

    def create_records(self, table_name: str, records: List[Dict[str, Any]]) -> List[str]:
        """批量创建记录

        Args:
            table_name: 表格名称 (bloggers/notes/comments)
            records: 记录列表，每个记录是字段名到值的映射

        Returns:
            创建成功的记录ID列表
        """
        if not records:
            return []

        table_id = self._get_table_id(table_name)

        # 构建请求体
        app_table_records = []
        for record in records:
            fields = {}
            for key, value in record.items():
                if value is not None:
                    fields[key] = value
            app_table_records.append(
                AppTableRecord.builder().fields(fields).build()
            )

        request = BatchCreateAppTableRecordRequest.builder() \
            .app_token(self.app_token) \
            .table_id(table_id) \
            .request_body(
                BatchCreateAppTableRecordRequestBody.builder()
                .records(app_table_records)
                .build()
            ) \
            .build()

        response = self.client.bitable.v1.app_table_record.batch_create(request)

        if not response.success():
            logger.error(f"创建记录失败: {response.code} - {response.msg}")
            raise Exception(f"创建记录失败: {response.msg}")

        record_ids = [r.record_id for r in response.data.records]
        logger.info(f"成功创建 {len(record_ids)} 条记录到表 {table_name}")
        return record_ids

    def update_records(self, table_name: str, records: List[Dict[str, Any]]) -> int:
        """批量更新记录

        Args:
            table_name: 表格名称
            records: 记录列表，每个记录必须包含 record_id 字段

        Returns:
            更新成功的记录数
        """
        if not records:
            return 0

        table_id = self._get_table_id(table_name)

        app_table_records = []
        for record in records:
            record_id = record.pop("record_id", None)
            if not record_id:
                continue
            fields = {k: v for k, v in record.items() if v is not None}
            app_table_records.append(
                AppTableRecord.builder()
                .record_id(record_id)
                .fields(fields)
                .build()
            )

        if not app_table_records:
            return 0

        request = BatchUpdateAppTableRecordRequest.builder() \
            .app_token(self.app_token) \
            .table_id(table_id) \
            .request_body(
                BatchUpdateAppTableRecordRequestBody.builder()
                .records(app_table_records)
                .build()
            ) \
            .build()

        response = self.client.bitable.v1.app_table_record.batch_update(request)

        if not response.success():
            logger.error(f"更新记录失败: {response.code} - {response.msg}")
            raise Exception(f"更新记录失败: {response.msg}")

        count = len(response.data.records)
        logger.info(f"成功更新 {count} 条记录")
        return count

    def search_records(
        self,
        table_name: str,
        filter_expr: Optional[str] = None,
        page_size: int = 100,
    ) -> List[Dict[str, Any]]:
        """搜索记录

        Args:
            table_name: 表格名称
            filter_expr: 过滤表达式，如 'CurrentValue.[note_id]="xxx"'
            page_size: 每页记录数

        Returns:
            记录列表
        """
        table_id = self._get_table_id(table_name)
        all_records = []
        page_token = None

        while True:
            request_builder = SearchAppTableRecordRequest.builder() \
                .app_token(self.app_token) \
                .table_id(table_id)

            body_builder = SearchAppTableRecordRequestBody.builder() \
                .page_size(page_size)

            if filter_expr:
                body_builder.filter(
                    FilterInfo.builder()
                    .conjunction("and")
                    .conditions([
                        Condition.builder()
                        .field_name(filter_expr.split("=")[0].strip())
                        .operator("is")
                        .value([filter_expr.split("=")[1].strip().strip('"')])
                        .build()
                    ])
                    .build()
                )

            if page_token:
                request_builder.page_token(page_token)

            request = request_builder \
                .request_body(body_builder.build()) \
                .build()

            response = self.client.bitable.v1.app_table_record.search(request)

            if not response.success():
                logger.error(f"搜索记录失败: {response.code} - {response.msg}")
                break

            if response.data.items:
                for item in response.data.items:
                    record = {"record_id": item.record_id}
                    record.update(item.fields)
                    all_records.append(record)

            if not response.data.has_more:
                break

            page_token = response.data.page_token

        return all_records

    def get_all_records(self, table_name: str) -> List[Dict[str, Any]]:
        """获取表格所有记录

        Args:
            table_name: 表格名称

        Returns:
            记录列表
        """
        table_id = self._get_table_id(table_name)
        all_records = []
        page_token = None

        while True:
            request_builder = ListAppTableRecordRequest.builder() \
                .app_token(self.app_token) \
                .table_id(table_id) \
                .page_size(100)

            if page_token:
                request_builder.page_token(page_token)

            request = request_builder.build()
            response = self.client.bitable.v1.app_table_record.list(request)

            if not response.success():
                logger.error(f"获取记录失败: {response.code} - {response.msg}")
                break

            if response.data.items:
                for item in response.data.items:
                    record = {"record_id": item.record_id}
                    if item.fields:
                        record.update(item.fields)
                    all_records.append(record)

            if not response.data.has_more:
                break

            page_token = response.data.page_token

        logger.info(f"从表 {table_name} 获取到 {len(all_records)} 条记录")
        return all_records

    def find_record_by_field(
        self, table_name: str, field_name: str, field_value: str
    ) -> Optional[Dict[str, Any]]:
        """根据字段值查找记录

        Args:
            table_name: 表格名称
            field_name: 字段名
            field_value: 字段值

        Returns:
            找到的记录，没有则返回 None
        """
        records = self.get_all_records(table_name)
        for record in records:
            if record.get(field_name) == field_value:
                return record
        return None

    def list_tables(self) -> List[Dict[str, Any]]:
        """列出多维表格中的所有数据表

        Returns:
            数据表列表
        """
        request = ListAppTableRequest.builder() \
            .app_token(self.app_token) \
            .build()

        response = self.client.bitable.v1.app_table.list(request)

        if not response.success():
            logger.error(f"获取表格列表失败: {response.code} - {response.msg}")
            return []

        tables = []
        if response.data and response.data.items:
            for item in response.data.items:
                tables.append({
                    "table_id": item.table_id,
                    "name": item.name,
                    "revision": item.revision,
                })
        return tables

    def create_table(self, table_name: str, fields: List[Dict]) -> Optional[str]:
        """创建数据表

        Args:
            table_name: 表格名称
            fields: 字段定义列表

        Returns:
            创建成功的表格ID
        """
        # 构建字段列表
        table_fields = []
        for field in fields:
            table_fields.append(
                AppTableCreateHeader.builder()
                .field_name(field["field_name"])
                .type(field["type"])
                .build()
            )

        request = CreateAppTableRequest.builder() \
            .app_token(self.app_token) \
            .request_body(
                CreateAppTableRequestBody.builder()
                .table(
                    ReqTable.builder()
                    .name(table_name)
                    .fields(table_fields)
                    .build()
                )
                .build()
            ) \
            .build()

        response = self.client.bitable.v1.app_table.create(request)

        if not response.success():
            logger.error(f"创建表格失败: {response.code} - {response.msg}")
            return None

        table_id = response.data.table_id
        logger.info(f"成功创建表格 {table_name}, table_id: {table_id}")
        return table_id

    def test_connection(self) -> bool:
        """测试飞书连接

        Returns:
            连接是否成功
        """
        try:
            # 尝试获取表格列表来测试连接
            if not self.app_token:
                logger.warning("未配置 app_token，无法测试多维表格连接")
                # 可以尝试其他 API 来验证凭证
                logger.info("飞书凭证已配置，等待配置 app_token")
                return True

            tables = self.list_tables()
            logger.info(f"飞书连接成功，找到 {len(tables)} 个数据表")
            return True
        except Exception as e:
            logger.error(f"飞书连接失败: {e}")
            return False

    def upsert_record(
        self, table_name: str, key_field: str, record: Dict[str, Any]
    ) -> str:
        """插入或更新记录 (根据 key_field 判断)

        Args:
            table_name: 表格名称
            key_field: 用于判断记录是否存在的字段名
            record: 记录数据

        Returns:
            记录ID
        """
        key_value = record.get(key_field)
        if not key_value:
            raise ValueError(f"记录缺少 {key_field} 字段")

        # 查找现有记录
        existing = self.find_record_by_field(table_name, key_field, key_value)

        if existing:
            # 更新现有记录
            record["record_id"] = existing["record_id"]
            self.update_records(table_name, [record])
            return existing["record_id"]
        else:
            # 创建新记录
            record_ids = self.create_records(table_name, [record])
            return record_ids[0] if record_ids else ""

    def batch_upsert_records(
        self, table_name: str, key_field: str, records: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """批量插入或更新记录

        Args:
            table_name: 表格名称
            key_field: 用于判断记录是否存在的字段名
            records: 记录列表

        Returns:
            {"created": 创建数量, "updated": 更新数量}
        """
        if not records:
            return {"created": 0, "updated": 0}

        # 获取所有现有记录
        existing_records = self.get_all_records(table_name)
        existing_map = {r.get(key_field): r for r in existing_records if r.get(key_field)}

        to_create = []
        to_update = []

        for record in records:
            key_value = record.get(key_field)
            if not key_value:
                continue

            if key_value in existing_map:
                record["record_id"] = existing_map[key_value]["record_id"]
                to_update.append(record)
            else:
                to_create.append(record)

        created = 0
        updated = 0

        if to_create:
            self.create_records(table_name, to_create)
            created = len(to_create)

        if to_update:
            self.update_records(table_name, to_update)
            updated = len(to_update)

        return {"created": created, "updated": updated}

    # ==================== 文档相关 API ====================

    def create_document(
        self,
        title: str,
        folder_token: Optional[str] = None,
    ) -> Optional[Dict[str, str]]:
        """创建飞书文档

        Args:
            title: 文档标题
            folder_token: 文件夹 token（可选，不填则创建在根目录）

        Returns:
            {"document_id": "xxx", "url": "xxx"} 或 None
        """
        request_body_builder = CreateDocumentRequestBody.builder().title(title)

        if folder_token:
            request_body_builder.folder_token(folder_token)

        request = CreateDocumentRequest.builder() \
            .request_body(request_body_builder.build()) \
            .build()

        response = self.client.docx.v1.document.create(request)

        if not response.success():
            logger.error(f"创建文档失败: {response.code} - {response.msg}")
            return None

        document = response.data.document
        result = {
            "document_id": document.document_id,
            "title": document.title,
        }

        # 构建文档 URL
        result["url"] = f"https://bytedance.larkoffice.com/docx/{document.document_id}"

        logger.info(f"成功创建文档: {title}, document_id: {document.document_id}")
        return result

    def add_document_blocks(
        self,
        document_id: str,
        blocks: List[Dict[str, Any]],
        index: int = 0,
    ) -> bool:
        """向文档添加内容块

        Args:
            document_id: 文档ID
            blocks: 内容块列表
            index: 插入位置（默认在开头）

        Returns:
            是否成功
        """
        # 构建 Block 对象列表
        block_objects = []
        for i, block in enumerate(blocks):
            try:
                block_obj = self._build_block(block)
                if block_obj:
                    block_objects.append(block_obj)
            except Exception as e:
                logger.warning(f"构建第 {i} 个块失败: {block.get('type')} - {e}")
                continue

        if not block_objects:
            logger.warning("没有有效的内容块")
            return False

        # 分批添加（每批最多 50 个块）
        batch_size = 50
        total_added = 0
        current_index = index

        for batch_start in range(0, len(block_objects), batch_size):
            batch = block_objects[batch_start:batch_start + batch_size]

            request = CreateDocumentBlockChildrenRequest.builder() \
                .document_id(document_id) \
                .block_id(document_id) \
                .document_revision_id(-1) \
                .request_body(
                    CreateDocumentBlockChildrenRequestBody.builder()
                    .children(batch)
                    .index(current_index)
                    .build()
                ) \
                .build()

            response = self.client.docx.v1.document_block_children.create(request)

            if not response.success():
                logger.error(f"添加内容块失败 (批次 {batch_start // batch_size + 1}): {response.code} - {response.msg}")
                # 继续尝试下一批
                continue

            total_added += len(batch)
            current_index += len(batch)

        if total_added > 0:
            logger.info(f"成功添加 {total_added}/{len(block_objects)} 个内容块")
            return True
        else:
            logger.error("所有内容块添加失败")
            return False

    def _build_text_elements(self, content: str) -> list:
        """构建文本元素列表"""
        from lark_oapi.api.docx.v1.model import TextElement, TextRun
        return [
            TextElement.builder()
            .text_run(
                TextRun.builder()
                .content(content)
                .build()
            )
            .build()
        ]

    def _build_text(self, content: str):
        """构建 Text 对象"""
        from lark_oapi.api.docx.v1.model import Text
        return Text.builder().elements(self._build_text_elements(content)).build()

    def _build_block(self, block: Dict[str, Any]):
        """构建 Block 对象

        Args:
            block: 块定义，包含 type 和内容

        Returns:
            Block 对象
        """
        from lark_oapi.api.docx.v1.model import Block, Text, Divider, Callout

        block_type = block.get("type")
        content = block.get("content", "")

        if block_type == "heading1":
            return Block.builder() \
                .block_type(3) \
                .heading1(self._build_text(content)) \
                .build()

        elif block_type == "heading2":
            return Block.builder() \
                .block_type(4) \
                .heading2(self._build_text(content)) \
                .build()

        elif block_type == "heading3":
            return Block.builder() \
                .block_type(5) \
                .heading3(self._build_text(content)) \
                .build()

        elif block_type == "paragraph" or block_type == "text":
            return Block.builder() \
                .block_type(2) \
                .text(self._build_text(content)) \
                .build()

        elif block_type == "divider":
            return Block.builder() \
                .block_type(22) \
                .divider(Divider.builder().build()) \
                .build()

        elif block_type == "code":
            # code 块使用 Text 对象
            return Block.builder() \
                .block_type(14) \
                .code(self._build_text(content)) \
                .build()

        elif block_type == "quote":
            # 引用块简化为普通段落（前面加 > 符号）
            return Block.builder() \
                .block_type(2) \
                .text(self._build_text(f"> {content}")) \
                .build()

        else:
            logger.warning(f"未知的块类型: {block_type}")
            return None

    def markdown_to_blocks(self, markdown_content: str) -> List[Dict[str, Any]]:
        """将 Markdown 内容转换为飞书文档块

        Args:
            markdown_content: Markdown 内容

        Returns:
            块列表
        """
        import re

        blocks = []
        lines = markdown_content.split("\n")
        i = 0

        while i < len(lines):
            line = lines[i]

            # 跳过空行
            if not line.strip():
                i += 1
                continue

            # 标题
            if line.startswith("# "):
                blocks.append({"type": "heading1", "content": line[2:].strip()})
            elif line.startswith("## "):
                blocks.append({"type": "heading2", "content": line[3:].strip()})
            elif line.startswith("### "):
                blocks.append({"type": "heading3", "content": line[4:].strip()})

            # 分割线
            elif line.strip() in ["---", "***", "___"]:
                blocks.append({"type": "divider"})

            # 引用
            elif line.startswith("> "):
                quote_content = line[2:].strip()
                # 合并多行引用
                while i + 1 < len(lines) and lines[i + 1].startswith("> "):
                    i += 1
                    quote_content += "\n" + lines[i][2:].strip()
                blocks.append({"type": "quote", "content": quote_content})

            # 代码块
            elif line.startswith("```"):
                language = line[3:].strip() or "text"
                code_content = []
                i += 1
                while i < len(lines) and not lines[i].startswith("```"):
                    code_content.append(lines[i])
                    i += 1
                blocks.append({
                    "type": "code",
                    "content": "\n".join(code_content),
                    "language": self._get_language_code(language)
                })

            # 普通段落
            else:
                # 合并连续的非空行
                paragraph = line.strip()
                while i + 1 < len(lines) and lines[i + 1].strip() and \
                      not lines[i + 1].startswith(("#", ">", "```", "---", "***", "___", "|")):
                    i += 1
                    paragraph += "\n" + lines[i].strip()
                blocks.append({"type": "paragraph", "content": paragraph})

            i += 1

        return blocks

    def _get_language_code(self, language: str) -> int:
        """获取代码语言编号"""
        language_map = {
            "text": 1, "python": 2, "javascript": 3, "java": 4,
            "go": 5, "cpp": 6, "c": 7, "csharp": 8, "php": 9,
            "ruby": 10, "swift": 11, "kotlin": 12, "rust": 13,
            "sql": 14, "shell": 15, "bash": 15, "json": 16,
            "yaml": 17, "xml": 18, "html": 19, "css": 20,
            "markdown": 21, "typescript": 22,
        }
        return language_map.get(language.lower(), 1)

    def create_document_from_markdown(
        self,
        title: str,
        markdown_content: str,
        folder_token: Optional[str] = None,
    ) -> Optional[Dict[str, str]]:
        """从 Markdown 内容创建飞书文档

        Args:
            title: 文档标题
            markdown_content: Markdown 内容
            folder_token: 文件夹 token（可选）

        Returns:
            {"document_id": "xxx", "url": "xxx"} 或 None
        """
        # 创建空文档
        doc_info = self.create_document(title, folder_token)
        if not doc_info:
            return None

        document_id = doc_info["document_id"]

        # 转换 Markdown 为块
        blocks = self.markdown_to_blocks(markdown_content)

        if not blocks:
            logger.warning("Markdown 内容为空")
            return doc_info

        # 添加内容块
        success = self.add_document_blocks(document_id, blocks)

        if not success:
            logger.warning("添加内容块失败，但文档已创建")

        return doc_info

    def list_folder_files(self, folder_token: str) -> List[Dict[str, Any]]:
        """列出文件夹下的文件

        Args:
            folder_token: 文件夹 token

        Returns:
            文件列表
        """
        request = ListFileRequest.builder() \
            .folder_token(folder_token) \
            .page_size(50) \
            .build()

        response = self.client.drive.v1.file.list(request)

        if not response.success():
            logger.error(f"获取文件列表失败: {response.code} - {response.msg}")
            return []

        files = []
        if response.data and response.data.files:
            for f in response.data.files:
                files.append({
                    "token": f.token,
                    "name": f.name,
                    "type": f.type,
                    "url": f.url,
                })

        return files

    def get_root_folder_token(self) -> Optional[str]:
        """获取根文件夹 token

        Returns:
            根文件夹 token
        """
        request = GetDriveRootFolderMetaRequest.builder().build()
        response = self.client.drive.v1.drive_root_folder_meta.get(request)

        if not response.success():
            logger.error(f"获取根文件夹失败: {response.code} - {response.msg}")
            return None

        return response.data.token

    def get_file_meta(self, file_token: str, file_type: str = "docx") -> Optional[Dict[str, Any]]:
        """获取文件元信息

        Args:
            file_token: 文件 token
            file_type: 文件类型 (docx, sheet, bitable, folder 等)

        Returns:
            文件元信息
        """
        # 使用 BatchQueryMeta API 获取文件元信息
        request = BatchQueryMetaRequest.builder() \
            .request_body(
                MetaRequest.builder()
                .request_docs([
                    RequestDoc.builder()
                    .doc_token(file_token)
                    .doc_type(file_type)
                    .build()
                ])
                .build()
            ) \
            .build()

        response = self.client.drive.v1.meta.batch_query(request)

        if not response.success():
            logger.error(f"获取文件元信息失败: {response.code} - {response.msg}")
            return None

        metas = response.data.metas
        if not metas or len(metas) == 0:
            logger.error("未找到文件元信息")
            return None

        meta = metas[0]
        return {
            "token": meta.doc_token,
            "name": meta.title,
            "type": meta.doc_type,
            "parent_token": getattr(meta, 'parent_token', None),
            "url": meta.url,
            "owner_id": meta.owner_id,
        }

    def get_parent_folder_token(self, document_token: str) -> Optional[str]:
        """获取文档的父文件夹 token

        Args:
            document_token: 文档 token

        Returns:
            父文件夹 token
        """
        meta = self.get_file_meta(document_token, "docx")
        if meta:
            return meta.get("parent_token")
        return None

    def upload_analysis_report(
        self,
        blogger_id: str,
        blogger_name: str,
        markdown_content: str,
        folder_token: Optional[str] = None,
    ) -> Optional[Dict[str, str]]:
        """上传分析报告到飞书，并更新博主记录

        Args:
            blogger_id: 博主ID
            blogger_name: 博主名称（用作文档标题）
            markdown_content: Markdown 格式的报告内容
            folder_token: 目标文件夹 token（可选，默认使用配置中的）

        Returns:
            {"document_id": "xxx", "url": "xxx"} 或 None
        """
        from datetime import datetime
        from config.feishu_config import FEISHU_REPORT_FOLDER_TOKEN, FEISHU_DOMAIN

        # 使用配置中的文件夹或传入的文件夹
        target_folder = folder_token or FEISHU_REPORT_FOLDER_TOKEN

        if not target_folder:
            logger.warning("未配置报告存储文件夹，将创建到根目录")

        # 创建文档，标题格式：博主名称：年月日
        date_str = datetime.now().strftime("%Y%m%d")
        doc_title = f"{blogger_name}：{date_str}"
        doc_info = self.create_document_from_markdown(
            title=doc_title,
            markdown_content=markdown_content,
            folder_token=target_folder if target_folder else None,
        )

        if not doc_info:
            logger.error("创建分析报告文档失败")
            return None

        # 更新文档 URL（使用正确的域名）
        doc_info["url"] = f"https://{FEISHU_DOMAIN}/docx/{doc_info['document_id']}"

        # 更新博主记录中的分析文档链接
        try:
            blogger_record = self.find_record_by_field("bloggers", "blogger_id", blogger_id)
            if blogger_record:
                update_data = {
                    "record_id": blogger_record["record_id"],
                    "analysis_doc_url": {
                        "link": doc_info["url"],
                        "text": doc_title,
                    }
                }
                self.update_records("bloggers", [update_data])
                logger.info(f"已更新博主 {blogger_name} 的分析文档链接")
            else:
                logger.warning(f"未找到博主 {blogger_id} 的记录，无法更新链接")
        except Exception as e:
            logger.warning(f"更新博主分析文档链接失败: {e}")

        return doc_info
