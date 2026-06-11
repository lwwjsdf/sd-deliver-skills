# Document Control Page Template

## Purpose

The document control page provides metadata about the document, including version, author, status, and approval chain.

## Markdown Template

```markdown
## Document Control

| Field | Details |
|:------|:--------|
| **Document Name** | [Full Document Title] |
| **Document Code** | [Project]-[Type]-[Version] |
| **Version** | 1.0 |
| **Release Date** | YYYY-MM-DD |
| **Author** | [Name], [Role] |
| **Reviewer** | [Name], [Role] |
| **Approver** | [Name], [Role] |
| **Department** | [Department Name] |
| **Status** | Draft / In Review / Approved / Archived |
| **Classification** | Public / Internal / Confidential / Restricted |
| **Distribution** | [List of recipients or "Internal Use Only"] |
| **Next Review Date** | YYYY-MM-DD |
```

## Word Table Formatting

1. Insert table: 2 columns, 12 rows
2. Column width: Left 30%, Right 70%
3. Header formatting:
   - First column: Bold, 11pt
   - Second column: Regular, 11pt
4. Table style: "Light Grid Accent 1" or custom
5. Header row background: RGB(68, 114, 196) or Gray
6. Borders: 0.5pt solid
7. Alignment: Left align both columns
8. Vertical alignment: Center

## Style Specifications

```
Table Properties:
- Width: 100% of page width
- Alignment: Center
- Cell margins: Top/Bottom 6pt, Left/Right 8pt
- Border: 0.5pt solid black

First Column (Labels):
- Font: Calibri, 11pt, Bold
- Background: RGB(242, 242, 242) or theme color
- Width: 4cm

Second Column (Values):
- Font: Calibri, 11pt, Regular
- Background: White
- Width: 12cm
```

## Example

| Field | Details |
|:------|:--------|
| **Document Name** | System Non-Functional Requirements Specification |
| **Document Code** | BEA-NFR-001 |
| **Version** | 1.0 |
| **Release Date** | 2024-06-05 |
| **Author** | John Smith, Senior Architect |
| **Reviewer** | Jane Doe, Technical Lead |
| **Approver** | Bob Johnson, VP Engineering |
| **Department** | Delivery & Architecture |
| **Status** | Approved |
| **Classification** | Confidential |
| **Distribution** | BEA Project Team, Internal Only |
| **Next Review Date** | 2024-12-05 |
