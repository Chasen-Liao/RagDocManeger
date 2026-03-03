"""Text chunking strategies for document processing."""

from typing import List, Dict, Any, Optional
import logging
import re

from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)


class ChunkingStrategy:
    """Implements text chunking strategies for document processing."""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: List[str] = None,
    ):
        """
        Initialize chunking strategy.

        Args:
            chunk_size: Size of each chunk in characters
            chunk_overlap: Number of overlapping characters between chunks
            separators: List of separators to use for splitting
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", " ", ""]

    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into chunks using recursive character splitting.

        Args:
            text: Text to chunk

        Returns:
            List of text chunks

        Raises:
            ValueError: If text is empty or invalid
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        try:
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                separators=self.separators,
                length_function=len,
            )

            chunks = splitter.split_text(text)

            if not chunks:
                raise ValueError("No chunks could be created from text")

            logger.info(
                f"Text chunked into {len(chunks)} chunks "
                f"(size: {self.chunk_size}, overlap: {self.chunk_overlap})"
            )

            return chunks
        except Exception as e:
            logger.error(f"Error chunking text: {str(e)}")
            raise

    def chunk_text_with_metadata(
        self, text: str, metadata: dict = None
    ) -> List[dict]:
        """
        Split text into chunks with metadata.

        Args:
            text: Text to chunk
            metadata: Optional metadata to attach to each chunk

        Returns:
            List of dicts with 'content' and 'metadata' keys
        """
        chunks = self.chunk_text(text)
        metadata = metadata or {}

        return [
            {
                "content": chunk,
                "metadata": {**metadata, "chunk_index": i},
            }
            for i, chunk in enumerate(chunks)
        ]


class MarkdownHeadingChunkingStrategy:
    """按 Markdown 标题层级切分文档的策略。

    特点：
    - 识别 # 到 ###### 共 6 级标题
    - 按标题将文档切分成语义完整的章节
    - 支持在章节过大时进行二次切分
    - 保留标题层级信息作为元数据
    """

    # Markdown 标题正则表达式（匹配 # 到 ######）
    HEADING_PATTERN = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)

    def __init__(
        self,
        max_chunk_size: int = 2000,
        chunk_overlap: int = 200,
        min_section_size: int = 50,
    ):
        """
        初始化 Markdown 标题切分策略。

        Args:
            max_chunk_size: 单个 chunk 最大字符数，超过时会进行二次切分
            chunk_overlap: 二次切分时的重叠字符数
            min_section_size: 最小章节大小，小于此值的章节会合并到相邻章节
        """
        self.max_chunk_size = max_chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_section_size = min_section_size
        self._recursive_splitter = RecursiveCharacterTextSplitter(
            chunk_size=max_chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", " ", ""],
            length_function=len,
        )

    def _parse_headings(self, text: str) -> List[Dict[str, Any]]:
        """
        解析文本中的标题结构。

        Args:
            text: Markdown 文本

        Returns:
            标题结构列表，每个元素包含标题信息和内容
        """
        sections = []
        lines = text.split('\n')

        current_section = {
            'heading': None,
            'level': 0,
            'content': [],
            'heading_text': None,
        }

        for line in lines:
            match = self.HEADING_PATTERN.match(line)
            if match:
                # 保存之前的章节
                if current_section['heading'] is not None:
                    sections.append(current_section)

                # 开始新章节
                heading_marks = match.group(1)
                heading_text = match.group(2)
                current_section = {
                    'heading': f"{'#' * len(heading_marks)} {heading_text}",
                    'level': len(heading_marks),
                    'content': [],
                    'heading_text': heading_text,
                }
            else:
                current_section['content'].append(line)

        # 添加最后一个章节
        if current_section['heading'] is not None or current_section['content']:
            sections.append(current_section)

        return sections

    def _build_section_path(
        self,
        sections: List[Dict[str, Any]],
        index: int
    ) -> str:
        """
        构建章节的完整路径（如：第一章 > 1.1 节 > 1.1.1 小节）。

        Args:
            sections: 所有章节列表
            index: 当前章节索引

        Returns:
            章节路径字符串
        """
        current_level = sections[index]['level']
        path_parts = []

        # 向前查找所有父级标题
        for i in range(index - 1, -1, -1):
            if sections[i]['level'] < current_level:
                path_parts.insert(0, sections[i]['heading_text'])
                current_level = sections[i]['level']

        # 添加当前标题
        if sections[index]['heading_text']:
            path_parts.append(sections[index]['heading_text'])

        return ' > '.join(path_parts) if path_parts else '无标题'

    def _split_large_section(
        self,
        content: str,
        heading: Optional[str],
        section_path: str,
        section_index: int
    ) -> List[Dict[str, Any]]:
        """
        对过大的章节进行二次切分。

        Args:
            content: 章节内容
            heading: 章节标题
            section_path: 章节完整路径
            section_index: 章节索引

        Returns:
            切分后的 chunk 列表
        """
        chunks = self._recursive_splitter.split_text(content)
        result = []

        for i, chunk in enumerate(chunks):
            chunk_metadata = {
                'section_path': section_path,
                'heading': heading,
                'section_index': section_index,
                'sub_chunk_index': i if len(chunks) > 1 else None,
                'total_sub_chunks': len(chunks) if len(chunks) > 1 else 1,
                'structure_type': 'markdown_heading',
            }
            result.append({
                'content': chunk,
                'metadata': chunk_metadata,
            })

        return result

    def chunk_text(self, text: str) -> List[Dict[str, Any]]:
        """
        按 Markdown 标题切分文本。

        Args:
            text: Markdown 文本

        Returns:
            包含内容和元数据的 chunk 列表

        Raises:
            ValueError: 如果文本为空
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        try:
            sections = self._parse_headings(text)
            chunks = []

            # 合并过小的章节
            merged_sections = self._merge_small_sections(sections)

            for idx, section in enumerate(merged_sections):
                content = '\n'.join(section['content']).strip()

                if not content:
                    continue

                section_path = self._build_section_path(merged_sections, idx)

                # 如果章节过大，进行二次切分
                if len(content) > self.max_chunk_size:
                    section_chunks = self._split_large_section(
                        content=content,
                        heading=section['heading'],
                        section_path=section_path,
                        section_index=idx,
                    )
                    chunks.extend(section_chunks)
                else:
                    metadata = {
                        'section_path': section_path,
                        'heading': section['heading'],
                        'section_index': idx,
                        'sub_chunk_index': None,
                        'total_sub_chunks': 1,
                        'structure_type': 'markdown_heading',
                    }
                    chunks.append({
                        'content': content,
                        'metadata': metadata,
                    })

            logger.info(
                f"Markdown text chunked into {len(chunks)} chunks "
                f"based on heading structure"
            )

            return chunks

        except Exception as e:
            logger.error(f"Error chunking markdown text: {str(e)}")
            raise

    def _merge_small_sections(
        self,
        sections: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        合并过小的章节到相邻章节。

        Args:
            sections: 原始章节列表

        Returns:
            合并后的章节列表
        """
        if not sections:
            return sections

        merged = []
        buffer = None

        for section in sections:
            content_size = sum(len(c) for c in section['content'])

            if content_size < self.min_section_size:
                # 章节太小，加入缓冲区
                if buffer is None:
                    buffer = section.copy()
                    buffer['content'] = section['content'].copy()
                else:
                    # 合并内容
                    if section['heading']:
                        buffer['content'].append(f"\n{section['heading']}")
                    buffer['content'].extend(section['content'])
            else:
                # 章节足够大，添加到结果
                if buffer is not None:
                    merged.append(buffer)
                    buffer = None
                merged.append(section)

        # 处理剩余的缓冲区
        if buffer is not None:
            merged.append(buffer)

        return merged
