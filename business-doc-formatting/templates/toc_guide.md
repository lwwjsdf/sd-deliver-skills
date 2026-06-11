# Table of Contents Setup Guide

## Automatic TOC in Microsoft Word

### Step 1: Apply Heading Styles

Before generating TOC, ensure all headings use Word styles:

1. Select heading text
2. Home → Styles → Heading 1 / Heading 2 / Heading 3
3. Or press Ctrl+Alt+1 (H1), Ctrl+Alt+2 (H2), Ctrl+Alt+3 (H3)

### Step 2: Insert TOC

1. Place cursor where TOC should appear (usually after cover page)
2. References → Table of Contents → Custom Table of Contents
3. Settings:
   - Show levels: 3 (or 2 for simple documents)
   - Formats: From template
   - Show page numbers: ✓
   - Right align page numbers: ✓
   - Use hyperlinks: ✓ (for digital documents)
   - Tab leader: ........ (dots)

### Step 3: Format TOC Styles

1. References → Table of Contents → Custom Table of Contents → Modify
2. Modify each TOC level:

**TOC 1 (Heading 1):**
- Font: Calibri, 12pt, Bold
- Indent: 0cm

**TOC 2 (Heading 2):**
- Font: Calibri, 11pt, Regular
- Indent: 0.8cm

**TOC 3 (Heading 3):**
- Font: Calibri, 10.5pt, Regular
- Indent: 1.6cm

### Step 4: Update TOC

**Manual update:**
- Right-click TOC → Update Field → Update entire table
- Or: Select TOC → F9 → Update entire table

**Before final delivery:**
- Always update TOC
- Verify page numbers match actual content
- Check that all headings are included

## TOC in Markdown (for Pandoc)

### YAML Front Matter

```yaml
---
title: "Document Title"
subtitle: "Project Name"
author: "Author Name"
date: "2024-06-05"
toc: true
toc-depth: 3
number-sections: true
---
```

### Pandoc Command with TOC

```bash
pandoc input.md -o output.docx \
  --reference-doc=template.docx \
  --toc \
  --toc-depth=3 \
  --number-sections
```

### Manual TOC in Markdown

```markdown
## Table of Contents

- [1. Introduction](#1-introduction)
  - [1.1 Background](#11-background)
  - [1.2 Scope](#12-scope)
- [2. Requirements](#2-requirements)
  - [2.1 Functional Requirements](#21-functional-requirements)
  - [2.2 Non-Functional Requirements](#22-non-functional-requirements)
- [Appendix A: Glossary](#appendix-a-glossary)
```

## TOC Formatting Checklist

- [ ] TOC appears after cover page and document control
- [ ] Page numbers are right-aligned with leader dots
- [ ] Heading levels are visually distinct (indentation, bold)
- [ ] Hyperlinks work in digital version (Ctrl+Click)
- [ ] Page numbers are correct (update before delivery)
- [ ] No headings from cover page or document control included
- [ ] Consistent font and spacing throughout TOC
- [ ] Maximum 3 levels shown (adjust based on document complexity)

## Advanced: Multi-level Numbering in Word

### Setup Multi-level List

1. Home → Multilevel List → Define New Multilevel List
2. Link each level to heading style:
   - Level 1 → Heading 1 (1, 2, 3...)
   - Level 2 → Heading 2 (1.1, 1.2...)
   - Level 3 → Heading 3 (1.1.1, 1.1.2...)
3. Format: "1." not "1.1." (no trailing dot on last number)
4. Position: Align at 0cm, indent at 0.8cm per level

### Numbering Format Examples

```
1. Introduction
   1.1 Background
      1.1.1 Project Overview
      1.1.2 Current State
   1.2 Scope
      1.2.1 In Scope
      1.2.2 Out of Scope
2. Requirements
   2.1 Functional Requirements
```

## Troubleshooting

**Issue: TOC not updating**
→ Solution: Select all (Ctrl+A) → F9 → Update entire table

**Issue: Wrong page numbers**
→ Solution: Update TOC. If persists, check for section breaks causing restart.

**Issue: Cover page headings appear in TOC**
→ Solution: Apply "Title" style (not Heading 1) to cover text, or set TOC to exclude Heading 1 from specific pages.

**Issue: Heading 4+ not showing**
→ Solution: References → Table of Contents → Custom → Show levels: 4 (or more)

**Issue: Formatting lost after update**
→ Solution: Modify TOC styles (TOC 1, TOC 2, etc.) directly, don't format TOC text manually.
