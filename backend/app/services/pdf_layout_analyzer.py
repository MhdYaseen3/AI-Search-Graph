"""PDF layout analysis for improved resume parsing.

Analyzes PyMuPDF extraction blocks to understand document structure:
- Detects columns and sections
- Preserves reading order
- Maintains spatial relationships

This enables the parser to handle multi-column, unusual layouts correctly.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BlockInfo:
    """Information about a text block in a PDF."""
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    page_num: int

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        return self.y1 - self.y0

    @property
    def area(self) -> float:
        return self.width * self.height


@dataclass(frozen=True)
class LayoutInfo:
    """Document layout information derived from blocks."""
    blocks: list[BlockInfo]
    page_count: int
    has_multiple_columns: bool
    column_count: int
    reading_order: list[int]  # indices into blocks, in reading order


class PDFLayoutAnalyzer:
    """Analyzes PDF document structure to enable robust layout-aware parsing."""

    # Thresholds for column detection
    COLUMN_THRESHOLD_RATIO = 0.25  # blocks with less than 25% overlap are separate columns
    MIN_COLUMN_WIDTH_RATIO = 0.3   # columns must be at least 30% of page width

    def __init__(self) -> None:
        pass

    def analyze_blocks(
        self,
        blocks: list[tuple[float, float, float, float, str, int, str]],
        page_width: float,
        page_height: float,
    ) -> LayoutInfo:
        """Analyze PyMuPDF blocks to understand document layout.

        Args:
            blocks: List of (x0, y0, x1, y1, text, block_num, block_type) from page.get_blocks("dict")
            page_width: Width of the page
            page_height: Height of the page

        Returns:
            LayoutInfo with structure analysis
        """
        # Filter and create BlockInfo objects
        block_list: list[BlockInfo] = []
        for idx, (x0, y0, x1, y1, text, block_num, block_type) in enumerate(blocks):
            if isinstance(text, str) and text.strip() and block_type == 0:  # type 0 is text
                block_list.append(BlockInfo(
                    text=text.strip(),
                    x0=float(x0),
                    y0=float(y0),
                    x1=float(x1),
                    y1=float(y1),
                    page_num=0,  # simplified for single-page analysis
                ))

        if not block_list:
            return LayoutInfo(
                blocks=[],
                page_count=1,
                has_multiple_columns=False,
                column_count=1,
                reading_order=[],
            )

        # Detect columns
        has_multiple_columns, column_count = self._detect_columns(block_list, page_width)

        # Determine reading order (top-to-bottom, left-to-right for columns)
        reading_order = self._determine_reading_order(block_list, has_multiple_columns)

        return LayoutInfo(
            blocks=block_list,
            page_count=1,
            has_multiple_columns=has_multiple_columns,
            column_count=column_count,
            reading_order=reading_order,
        )

    def _detect_columns(
        self,
        blocks: list[BlockInfo],
        page_width: float,
    ) -> tuple[bool, int]:
        """Detect if document uses multiple columns.

        Returns:
            (has_multiple_columns, column_count)
        """
        if len(blocks) < 3:
            return False, 1

        # Group blocks by y-position (same line)
        y_tolerance = 5
        line_groups: dict[float, list[BlockInfo]] = {}
        for block in blocks:
            # Find or create line group
            found_line = None
            for y_pos in line_groups:
                if abs(block.y0 - y_pos) < y_tolerance:
                    found_line = y_pos
                    break
            if found_line is None:
                found_line = block.y0
            line_groups.setdefault(found_line, []).append(block)

        # Check if any line has blocks that are clearly separated horizontally
        multi_column_lines = 0
        for blocks_in_line in line_groups.values():
            if len(blocks_in_line) < 2:
                continue

            # Sort by x position
            blocks_in_line.sort(key=lambda b: b.x0)

            # Check for gap (columns)
            for i in range(len(blocks_in_line) - 1):
                gap = blocks_in_line[i + 1].x0 - blocks_in_line[i].x1
                if gap > page_width * self.COLUMN_THRESHOLD_RATIO:
                    # Check if both sides are reasonable column widths
                    if (blocks_in_line[i].width > page_width * self.MIN_COLUMN_WIDTH_RATIO and
                        blocks_in_line[i + 1].width > page_width * self.MIN_COLUMN_WIDTH_RATIO):
                        multi_column_lines += 1
                        break

        # If multiple lines show column separation, treat as multi-column
        if multi_column_lines >= max(1, len(line_groups) // 3):
            # Try to determine column count (2, 3, or more)
            column_x_ranges: list[tuple[float, float]] = []
            for blocks_in_line in line_groups.values():
                if len(blocks_in_line) >= 2:
                    blocks_in_line.sort(key=lambda b: b.x0)
                    for i in range(len(blocks_in_line) - 1):
                        gap = blocks_in_line[i + 1].x0 - blocks_in_line[i].x1
                        if gap > page_width * self.COLUMN_THRESHOLD_RATIO:
                            # This is a column boundary
                            pass

            return True, min(len(line_groups), 3)  # Detect 2 or 3 columns

        return False, 1

    def _determine_reading_order(
        self,
        blocks: list[BlockInfo],
        has_multiple_columns: bool,
    ) -> list[int]:
        """Determine the reading order of blocks.

        For single column: top-to-bottom.
        For multi-column: top-to-bottom within each column, left-to-right between columns.

        Returns:
            Indices into blocks, in reading order
        """
        if not blocks:
            return []

        if not has_multiple_columns:
            # Simple top-to-bottom order
            indexed = [(i, block) for i, block in enumerate(blocks)]
            indexed.sort(key=lambda item: item[1].y0)
            return [idx for idx, _ in indexed]

        # Multi-column: group blocks by approximate x-position, then sort within each column by y
        # Find column boundaries
        x_positions = sorted(set(b.x0 for b in blocks))
        columns: dict[int, list[tuple[int, BlockInfo]]] = {}

        for i, block in enumerate(blocks):
            # Find which column this block belongs to
            # (assign to nearest left edge)
            col_idx = 0
            min_dist = abs(block.x0 - x_positions[0])
            for j, x_pos in enumerate(x_positions):
                dist = abs(block.x0 - x_pos)
                if dist < min_dist:
                    min_dist = dist
                    col_idx = j

            columns.setdefault(col_idx, []).append((i, block))

        # Sort within each column by y position, then concatenate in column order
        reading_order = []
        for col_idx in sorted(columns.keys()):
            col_blocks = columns[col_idx]
            col_blocks.sort(key=lambda item: item[1].y0)
            reading_order.extend([idx for idx, _ in col_blocks])

        return reading_order

    def reorder_blocks_by_reading_order(self, layout: LayoutInfo) -> str:
        """Reorder blocks according to reading order and return as text."""
        reordered_blocks = [layout.blocks[i] for i in layout.reading_order]
        return "\n".join(block.text for block in reordered_blocks)
