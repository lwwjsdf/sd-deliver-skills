# Business Document Formatting Skill

Professional formatting standards and tools for generating enterprise-quality business documents from Markdown or programmatic content.

## Features

- **Cover Page**: Professional cover with logo, title, version, and classification
- **Document Control**: Version control table with metadata
- **Table of Contents**: Auto-generated TOC placeholder
- **Heading Hierarchy**: Multi-level headings with proper spacing and formatting
- **Professional Tables**: Styled tables with header colors, alternating rows
- **Headers & Footers**: Document title in header, page numbers and classification in footer
- **Page Layout**: Standard A4 with binding margins
- **Typography**: Calibri font family, consistent sizing and spacing

## Installation

```bash
pip install python-docx
```

## Usage

### 1. Command Line

```bash
python generate_business_doc.py \
  --input input.md \
  --output output.docx \
  --title "Document Title" \
  --subtitle "Project Subtitle" \
  --version "1.0" \
  --author "Your Name" \
  --classification "Confidential"
```

### 2. Python API

```python
from generate_business_doc import BusinessDocumentFormatter

# Initialize formatter
formatter = BusinessDocumentFormatter(
    document_title="System NFR Specification",
    subtitle="BEA CDP + SF Project",
    version="1.0",
    author="SensorsData Delivery Team",
    classification="Confidential"
)

# Add front matter
formatter.add_cover_page()
formatter.add_document_control()
formatter.add_toc_placeholder()

# Add content
formatter.add_heading("1. Introduction", level=1)
formatter.add_paragraph("Your content here...")

formatter.add_heading("1.1 Background", level=2)
formatter.add_paragraph("More content...")

# Add header/footer
formatter.add_header_footer()

# Save
formatter.save("output.docx")
```

### 3. From Markdown

```python
from generate_business_doc import generate_from_markdown

with open('input.md', 'r') as f:
    content = f.read()

generate_from_markdown(
    content, 
    'output.docx',
    document_title='My Document',
    version='1.0'
)
```

## Document Standards

### Page Layout
- Paper: A4 (210mm x 297mm)
- Margins: Top/Bottom 2.54cm, Left 3.17cm (binding), Right 2.54cm
- Orientation: Portrait

### Typography
- Font: Calibri (English), 微软雅黑 (Chinese)
- Body: 11pt, 1.15 line spacing
- Headings: H1 16pt, H2 14pt, H3 12pt
- Tables: 10.5pt
- Captions: 10pt italic

### Colors
- Header row: RGB(68, 114, 196) with white text
- Alternating rows: RGB(242, 242, 242)
- Classification: RGB(192, 0, 0) red

## Templates

- `templates/cover_page.md` - Cover page layout guide
- `templates/document_control.md` - Document control table template
- `templates/toc_guide.md` - Table of contents setup instructions

## File Structure

```
business-doc-formatting/
├── SKILL.md                      # Main skill documentation
├── generate_business_doc.py      # Python generator script
├── templates/
│   ├── cover_page.md            # Cover page template
│   ├── document_control.md      # Document control template
│   └── toc_guide.md             # TOC setup guide
└── README.md                     # This file
```

## Standards Compliance

This skill implements industry best practices for:
- Technical specification documents
- Business proposals and SOWs
- Non-functional requirement documents
- Commercial deliverables
- Client-facing documentation

## Integration

### With Pandoc
```bash
pandoc input.md -o output.docx \
  --reference-doc=templates/reference.docx \
  --toc --toc-depth=3
```

### With CI/CD
```yaml
- name: Generate Document
  run: |
    python generate_business_doc.py \
      --input spec.md \
      --output deliverable.docx \
      --title "Technical Specification" \
      --version "${{ github.ref_name }}"
```

## License

Internal use only - SensorsData Delivery Team
