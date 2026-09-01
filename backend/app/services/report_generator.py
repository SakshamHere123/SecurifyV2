from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle


def _build_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="TableCell", fontName="Helvetica", fontSize=8, leading=10,
    ))
    styles.add(ParagraphStyle(
        name="CodeUnchanged", fontName="Courier", fontSize=8, leading=10, textColor=colors.black,
    ))
    styles.add(ParagraphStyle(
        name="CodeAdded", fontName="Courier", fontSize=8, leading=10,
        textColor=colors.HexColor("#15803D"), backColor=colors.HexColor("#DCFCE7"),
    ))
    styles.add(ParagraphStyle(
        name="CodeRemoved", fontName="Courier", fontSize=8, leading=10,
        textColor=colors.HexColor("#B91C1C"), backColor=colors.HexColor("#FEE2E2"),
    ))
    return styles


def generate_report_pdf(output_path: str, scan: dict, findings: list[dict], diffs: list[dict]) -> None:
    """Builds the final PDF report: scan summary, the full findings table
    (with resolved/unresolved status and which policy each one broke), and a
    color-coded diff per changed resource.

    This is the artifact from the original pitch: 'a report artifact you
    could hand to someone unfamiliar with the project.' It has to be
    readable on its own -- no Terraform knowledge required to see what was
    wrong and what changed.
    """
    styles = _build_styles()
    doc = SimpleDocTemplate(output_path, pagesize=letter, topMargin=0.6 * inch, bottomMargin=0.6 * inch)
    story = []

    story.append(Paragraph("Securify Security Report", styles["Title"]))
    story.append(Spacer(1, 12))

    resolved_count = sum(1 for f in findings if f["resolved"])
    total = len(findings)
    story.append(Paragraph(
        f"Scan ID: {escape(str(scan['scan_id']))}<br/>"
        f"Status: {escape(str(scan['status']))}<br/>"
        f"Remediation attempts: {scan['retry_count']}<br/>"
        f"Violations found: {total}<br/>"
        f"Violations resolved: {resolved_count}/{total}",
        styles["Normal"],
    ))
    story.append(Spacer(1, 20))

    story.append(Paragraph("Findings", styles["Heading2"]))
    if findings:
        table_data = [["Resource", "Severity", "Issue", "Policy Reference", "Status"]]
        for f in findings:
            status = "Resolved" if f["resolved"] else "Unresolved"
            table_data.append([
                Paragraph(escape(f["resource"]), styles["TableCell"]),
                Paragraph(escape(f["severity"].upper()), styles["TableCell"]),
                Paragraph(escape(f["issue"]), styles["TableCell"]),
                Paragraph(escape(f.get("policy_reference") or "-"), styles["TableCell"]),
                Paragraph(status, styles["TableCell"]),
            ])
        table = Table(table_data, colWidths=[1.5 * inch, 0.65 * inch, 1.65 * inch, 1.7 * inch, 0.75 * inch])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(table)
    else:
        story.append(Paragraph("No violations found.", styles["Normal"]))

    story.append(Spacer(1, 20))
    story.append(Paragraph("Before / After Diff", styles["Heading2"]))

    if diffs:
        for resource_diff in diffs:
            story.append(Paragraph(escape(resource_diff["resource"]), styles["Heading3"]))
            for line in resource_diff["lines"]:
                if line["type"] == "added":
                    style, prefix = styles["CodeAdded"], "+ "
                elif line["type"] == "removed":
                    style, prefix = styles["CodeRemoved"], "- "
                else:
                    style, prefix = styles["CodeUnchanged"], "  "
                content = escape(prefix + line["content"]).replace(" ", "&nbsp;")
                story.append(Paragraph(content, style))
            story.append(Spacer(1, 12))
    else:
        story.append(Paragraph("No changes were made.", styles["Normal"]))

    doc.build(story)