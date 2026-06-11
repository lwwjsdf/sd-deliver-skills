# Business Document Formatting Skill

Professional formatting standards for business documents, technical specifications, and commercial deliverables.

## When to Use

Use this skill when:
- Generating Word/PDF documents from Markdown or structured data
- Creating professional business proposals, specifications, or reports
- Formatting technical documentation for client delivery
- Ensuring consistent document quality across team deliverables
- Converting plain text/Markdown into publication-ready documents

## Quick Start

### Generate Document from Markdown

```python
from business_doc_formatting import BusinessDocumentFormatter

formatter = BusinessDocumentFormatter(
    document_title="System NFR Specification",
    subtitle="BEA CDP + SF Project",
    version="1.0",
    author="SensorsData Delivery Team",
    classification="Confidential"
)

formatter.add_cover_page()
formatter.add_document_control()
formatter.add_toc_placeholder()

# Add your content
formatter.add_heading("1. Introduction", level=1)
formatter.add_paragraph("Your content here...")

formatter.add_header_footer()
formatter.save("output.docx")
```

### Using Command Line

```bash
python generate_business_doc.py \
  --input input.md \
  --output output.docx \
  --title "Document Title" \
  --version "1.0" \
  --author "Your Name" \
  --classification "Confidential" \
  --template consulting
```

### Available Templates

| Template | Font | Heading Color | Table Header | Margins | Best For |
|----------|------|---------------|--------------|---------|----------|
| **consulting** | Calibri 11pt | #0F4761 (Deep Blue) | #156082 | 2.54cm all | Consulting reports, proposals |
| **investment_research** | Arial 11pt | #000000 (Black) | #333333 | 2.0cm all | Investment research, analysis |
| **technical_spec** | Arial 11pt | #000000 (Black) | #4472C4 | Left 3.17cm | Technical specifications |
| **default** | Calibri 11pt | #000000 (Black) | #4472C4 | Left 3.17cm | General business documents |

**Template Selection Guidelines:**
- Use **consulting** for client-facing proposals, SOWs, and strategy documents
- Use **investment_research** for data-heavy reports requiring maximum content density
- Use **technical_spec** for system architecture, API docs, and technical requirements
- Use **default** when no specific industry standard applies

## Document Structure Standards

### 1. Cover Page (首页)

**Required Elements:**
- Company logo (top center, 2-3cm from top edge)
- Document title (centered, 18-22pt, bold)
- Subtitle or project name (centered, 14-16pt, regular)
- Version number and date (centered, 11-12pt)
- Classification label (bottom center): "Confidential" / "Internal Use" / "Restricted"
- Page border: 0.5pt single line, 1cm from page edge (optional)

**Spacing:**
- Title to subtitle: 24pt
- Subtitle to version: 36pt
- Version to classification: 48pt
- Use vertical centering for main content block

### 2. Document Control Page (版本控制页)

**Table Format:**
| Field | Value |
|-------|-------|
| Document Name | [Title] |
| Version | x.y (e.g., 1.0) |
| Date | YYYY-MM-DD |
| Author | [Name] |
| Reviewer | [Name] |
| Approver | [Name] |
| Status | Draft / Review / Approved |
| Classification | Internal / Confidential / Restricted |

**Format:**
- Table width: 80% of page width, centered
- Header row: shaded (RGB: 217,217,217 or theme color)
- Borders: 0.5pt solid black
- Font: 10-11pt

### 3. Revision History (修订历史)

**Table Format:**
| Version | Date | Author | Changes | Approver |
|---------|------|--------|---------|----------|
| 1.0 | 2024-01-15 | [Name] | Initial release | [Name] |
| 1.1 | 2024-02-01 | [Name] | Updated Section 3 | [Name] |

**Rules:**
- Always include, even for first version
- Sort: newest first (descending by date)
- Changes column: brief bullet points or summary

### 4. Table of Contents (目录)

**Format:**
- Title: "Table of Contents" (centered, 16pt, bold)
- Auto-generated with page numbers
- Include: Heading 1, Heading 2 (optional: Heading 3)
- Leader dots: "........" connecting title to page number
- Indentation: Heading 2 indented 1cm, Heading 3 indented 2cm
- Update before final delivery (F9 in Word)

**Levels:**
- Level 1: Main sections (bold, 12pt)
- Level 2: Subsections (regular, 11pt)
- Level 3: Detail sections (regular, 10.5pt, italic)

## Typography Standards (字体与排版)

### Font Selection

**English Documents:**
| Element | Font | Size | Weight |
|---------|------|------|--------|
| Cover Title | Calibri / Arial | 20pt | Bold |
| Heading 1 | Calibri / Arial | 16pt | Bold |
| Heading 2 | Calibri / Arial | 14pt | Bold |
| Heading 3 | Calibri / Arial | 12pt | Bold |
| Body Text | Calibri / Arial | 11pt | Regular |
| Table Text | Calibri / Arial | 10-11pt | Regular |
| Caption | Calibri / Arial | 10pt | Italic |
| Header/Footer | Calibri / Arial | 9pt | Regular |
| Footnote | Calibri / Arial | 9pt | Regular |

**Bilingual Documents (Chinese + English):**
| Element | Chinese Font | English Font | Size |
|---------|-------------|--------------|------|
| Cover Title | 微软雅黑 (Microsoft YaHei) | Arial | 18-22pt |
| Heading 1 | 微软雅黑 | Arial | 16pt |
| Heading 2 | 微软雅黑 | Arial | 14pt |
| Body Text | 宋体 (SimSun) | Times New Roman | 12pt |
| Table Text | 宋体 | Times New Roman | 10.5pt |

**Note:** Use consistent font family throughout document. Do not mix more than 2 font families.

### Text Formatting

**Alignment:**
- Cover page: Centered
- Headings: Left-aligned (or justified)
- Body text: Justified (两端对齐)
- Tables: Center column headers, left-align content (or center for numbers)
- Captions: Centered below tables/figures

**Line Spacing:**
- Cover page: 1.5x or Double
- Body text: 1.15x or 1.5x
- Tables: Single (1.0x) or 1.15x
- Before heading: 12-18pt space
- After heading: 6-12pt space
- Between paragraphs: 6-12pt

**Paragraph Spacing:**
```
Heading 1: Before 18pt, After 12pt
Heading 2: Before 14pt, After 8pt
Heading 3: Before 10pt, After 6pt
Body: Before 0pt, After 6pt
```

## Page Layout (页面设置)

### Margins

**Standard A4:**
- Top: 2.54cm (1 inch)
- Bottom: 2.54cm
- Left: 3.17cm (1.25 inch) - for binding
- Right: 2.54cm
- Gutter: 0cm (or 0.5cm if spiral binding)

**Narrow (for tables/figures):**
- Top/Bottom: 2cm
- Left/Right: 2cm

**Orientation:**
- Default: Portrait
- Wide tables: Landscape (rotate page)

### Paper Size
- Default: A4 (210mm x 297mm)
- US clients: Letter (8.5" x 11")

### Section Breaks
- Use "Next Page" section break before TOC, main content, appendices
- Different headers/footers per section
- Restart page numbering at main content (Page 1)

## Heading Hierarchy (标题层级)

### Structure
```
# Heading 1 - Major Section (e.g., 1. Introduction)
## Heading 2 - Subsection (e.g., 1.1 Background)
### Heading 3 - Detail (e.g., 1.1.1 Project Scope)
#### Heading 4 - Sub-detail (avoid if possible, use bullets instead)
```

### Numbering
- Use multi-level numbering: 1, 1.1, 1.1.1
- Format: "1. Title", "1.1 Title", "1.1.1 Title"
- No period after last number: "1.1 Title" not "1.1. Title"
- Appendix: "A.", "A.1", "A.1.1"

### Visual Distinction
| Level | Size | Color | Before | After | Border |
|-------|------|-------|--------|-------|--------|
| H1 | 16pt | Black | 18pt | 12pt | Bottom: 1pt solid |
| H2 | 14pt | Black | 14pt | 8pt | None |
| H3 | 12pt | Black | 10pt | 6pt | None |
| H4 | 11pt | Bold | 8pt | 4pt | None |

## Table Formatting (表格格式)

### Standard Business Table

**Borders:**
- Header row: 1pt bottom border (thick)
- Data rows: 0.5pt horizontal borders
- Vertical borders: Optional (minimal style: none)
- Outer border: 1pt (if using grid)

**Colors:**
- Header background: RGB(68,114,196) or RGB(217,217,217)
- Header text: White (on dark) or Black (on light)
- Alternating rows: RGB(242,242,242) / White
- No cell shading for data cells (unless heat map)

**Alignment:**
- Header: Center, bold
- Text columns: Left-align
- Number columns: Right-align or center
- Date columns: Center
- Status columns: Center

**Spacing:**
- Cell padding: Top/Bottom 6pt, Left/Right 8pt
- Minimum row height: 0.8cm
- Column width: Auto-fit content or equal distribution

### Requirement/Specification Tables

**For NFR/SRS type documents:**
| Req ID | Requirement | Description | Priority | Owner |
|--------|-------------|-------------|----------|-------|
| R001 | System shall... | Details... | High | Team A |

**Format:**
- Req ID: Bold, monospace font (Consolas 10pt)
- Priority column: Color-coded (Red=High, Yellow=Medium, Green=Low)
- Owner column: Consistent abbreviation
- Wrap text enabled for Description column

## Header and Footer (页眉页脚)

### Header
- Content: Document title or abbreviated title
- Alignment: Left or Center
- Font: 9pt, gray color (RGB: 128,128,128)
- Border: 0.5pt bottom border (optional)
- Different first page: Yes (no header on cover)

### Footer
- Content: Page number (center or right)
- Format: "Page X of Y" or "- X -" or "X / Y"
- Font: 9pt, gray
- Additional: Confidentiality label (left side), Document version (right side)
- Different first page: Yes

### Page Numbering
- Cover: No number
- TOC: Roman numerals (i, ii, iii)
- Main content: Arabic numerals (1, 2, 3)
- Appendices: Continue Arabic or use "A-1", "A-2"

## Lists and Bullets (列表)

### Bullet Points
- Level 1: Solid circle (●) or dash (–)
- Level 2: Hollow circle (○) or arrow (→)
- Level 3: Square (■) or hyphen (-)
- Consistent indentation: 1cm per level

### Numbered Lists
- Level 1: 1, 2, 3
- Level 2: a, b, c (or 1.1, 1.2)
- Level 3: i, ii, iii
- Parenthesis style: (1), (a), (i)

### Spacing
- Before list: 6pt
- After list: 6pt
- Between items: 3pt
- Align with body text or indent 1cm

## Figures and Captions (图表)

### Figure Format
- Center alignment
- Maximum width: 90% of text width
- Border: None (or 0.5pt if screenshot)
- Caption: Below figure, centered, "Figure X: Description"
- Caption font: 10pt italic

### Table Caption
- Above table (preferred for business docs)
- Format: "Table X: Description"
- Bold, 10-11pt

## Special Elements

### Callout Boxes
**For important notes, warnings, or key decisions:**
- Border: 1pt solid, left border 3pt thick (color-coded)
- Background: Light tint (RGB: 255,255,204 for yellow)
- Padding: 8pt all sides
- Margin: 12pt before/after

**Color coding:**
- Blue (Info): RGB(219,238,244)
- Yellow (Warning): RGB(255,242,204)
- Red (Critical): RGB(252,228,214)
- Green (Success): RGB(226,239,218)

### Code Blocks
- Font: Consolas or Courier New, 9-10pt
- Background: RGB(245,245,245)
- Border: 0.5pt solid RGB(221,221,221)
- Padding: 8pt
- Line numbers: Optional (gray, right-aligned)

## Document Classification (密级标识)

**Placement:**
- Cover page: Bottom center, bold
- Header/Footer: Every page
- First page after cover: Top right corner

**Standard Labels:**
- **Public** - No restrictions
- **Internal Use** - Company employees only
- **Confidential** - Need-to-know basis
- **Restricted** - Named recipients only

**Format:**
- Font: 10pt bold, red color (RGB: 192,0,0)
- Box: 1pt border, padding 4pt

## Quality Checklist (质量检查)

Before delivering document, verify:

- [ ] Cover page complete with all required elements
- [ ] Version control page filled
- [ ] Revision history included
- [ ] Table of contents updated (press F9)
- [ ] Page numbers continuous and correct
- [ ] All headings follow hierarchy (no skipped levels)
- [ ] Tables have captions and are referenced in text
- [ ] Figures have captions and are referenced in text
- [ ] Cross-references updated (press Ctrl+A, F9)
- [ ] No widows/orphans (single lines at page break)
- [ ] Consistent font usage throughout
- [ ] Spacing uniform (no extra blank lines)
- [ ] Headers/footers consistent
- [ ] Classification label on every page
- [ ] File name follows naming convention: `[Project]_[DocType]_vX.Y_YYYYMMDD`
- [ ] Spell check completed
- [ ] Grammar check completed (Grammarly or similar)
- [ ] Reviewed by at least one peer
- [ ] Approved by designated authority

## File Naming Convention (文件命名)

**Format:**
```
[Project]_[DocumentType]_v[Version]_[YYYYMMDD].[ext]
```

**Examples:**
- `BEA_NFR_v1.0_20240605.docx`
- `ACME_TechSpec_v2.1_20240515.pdf`
- `ProjectX_SOW_v1.0_20240120.docx`

**Rules:**
- No spaces (use underscore)
- Version: v1.0, v1.1, v2.0
- Date: Document creation date, not project date
- Extension: .docx (editable), .pdf (final delivery)

## Integration with Tools

### Pandoc (Markdown to Word)

**Basic command:**
```bash
pandoc input.md -o output.docx --reference-doc=template.docx
```

**With TOC:**
```bash
pandoc input.md -o output.docx --reference-doc=template.docx \
  --toc --toc-depth=3
```

**Reference document setup:**
1. Create template.docx with desired styles
2. Modify styles in Word: Design → Paragraph Spacing → Custom
3. Save as .docx (not .dotx)
4. Use `--reference-doc` to apply styles

### Python-docx (Programmatic Generation)

**Key settings:**
```python
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.style import WD_STYLE_TYPE

# Page setup
section = doc.sections[0]
section.page_height = Cm(29.7)
section.page_width = Cm(21.0)
section.top_margin = Cm(2.54)
section.bottom_margin = Cm(2.54)
section.left_margin = Cm(3.17)
section.right_margin = Cm(2.54)

# Style modification
style = doc.styles['Normal']
font = style.font
font.name = 'Calibri'
font.size = Pt(11)
style.paragraph_format.line_spacing = 1.15
style.paragraph_format.space_after = Pt(6)

# Heading styles
for i, size in enumerate([16, 14, 12], 1):
    style = doc.styles[f'Heading {i}']
    style.font.name = 'Calibri'
    style.font.size = Pt(size)
    style.font.bold = True
    style.paragraph_format.space_before = Pt(18 if i == 1 else 14)
    style.paragraph_format.space_after = Pt(12 if i == 1 else 8)
```

### Microsoft Word Best Practices

**Styles (必须):**
- Always use Word styles, never direct formatting
- Modify styles via: Home → Styles → Right-click → Modify
- Create custom styles for special elements
- Use "Update [Style] to Match Selection" for quick updates

**Tables:**
- Use "Table Grid" style as base
- Modify: Design → Table Styles → Modify Table Style
- Save in template for reuse

**Quick Parts:**
- Save cover page as Quick Part (Insert → Quick Parts → Save Selection)
- Save headers/footers as Quick Parts
- Reuse across documents

**Template (.dotx):**
- Save finalized format as .dotx template
- Store in: `%APPDATA%\Microsoft\Templates`
- New documents: File → New → Personal → Select template

## Appendix: Common Mistakes to Avoid

1. **Mixing fonts** - Use max 2 font families per document
2. **Inconsistent spacing** - Use styles, not manual spacing
3. **Missing TOC update** - Always update TOC before delivery (F9)
4. **Wrong page numbering** - Set up sections properly
5. **Tables without captions** - Every table needs "Table X: ..."
6. **Orphan headings** - Keep with next paragraph
7. **Manual formatting** - Use styles for everything
8. **Forgotten classification** - Add confidentiality label
9. **Broken cross-references** - Update all fields (Ctrl+A, F9)
10. **Inconsistent date formats** - Use YYYY-MM-DD throughout

## Templates Provided

This skill includes:
- `templates/cover_page.md` - Cover page template
- `templates/document_control.md` - Version control template
- `templates/toc_guide.md` - TOC setup instructions
- `templates/reference.docx` - Word reference document with pre-defined styles

## Related Skills

- `sd-tech-design` - Technical design document generation
- `document-release` - Post-ship documentation updates
- `sd-faq` - FAQ and knowledge base formatting
