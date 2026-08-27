from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from apps.treatments.models import Session, Treatment

TEAL = colors.HexColor("#0d9488")
TEAL_DARK = colors.HexColor("#0f766e")
SLATE = colors.HexColor("#334155")
LIGHT = colors.HexColor("#ccfbf1")

_STATUS_COLORS = {
    Session.Status.DONE: colors.HexColor("#047857"),
    Session.Status.PENDING: colors.HexColor("#b45309"),
    Session.Status.CANCELLED: colors.HexColor("#b91c1c"),
}


def _styles():
    base = getSampleStyleSheet()
    title = ParagraphStyle(
        "Title", parent=base["Title"], fontSize=20, textColor=TEAL_DARK,
        spaceAfter=2,
    )
    subtitle = ParagraphStyle(
        "Subtitle", parent=base["Normal"], fontSize=11, textColor=SLATE,
        spaceAfter=14,
    )
    h2 = ParagraphStyle(
        "H2", parent=base["Heading2"], fontSize=13, textColor=TEAL_DARK,
        spaceBefore=16, spaceAfter=8,
    )
    cell = ParagraphStyle(
        "Cell", parent=base["Normal"], fontSize=9.5, leading=13,
    )
    header = ParagraphStyle(
        "HeaderCell", parent=cell, textColor=colors.white, fontName="Helvetica-Bold",
    )
    block = ParagraphStyle(
        "Block", parent=base["Normal"],
        fontSize=10.5, leading=15, textColor=SLATE,
        spaceBefore=2, spaceAfter=14,
    )
    return title, subtitle, h2, cell, header, block


def _info_table(data):
    rows = [[Paragraph(k, _styles()[3]), Paragraph(v, _styles()[3])] for k, v in data]
    table = Table(rows, colWidths=[4.5 * cm, 11 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), LIGHT),
                ("TEXTCOLOR", (0, 0), (0, -1), TEAL_DARK),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9.5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
            ]
        )
    )
    return table


def build_treatment_pdf(treatment: Treatment) -> bytes:
    title, subtitle, h2, cell, header, block = _styles()
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=1.6 * cm,
        bottomMargin=1.8 * cm,
        title=f"Tratamiento — {treatment.diagnosis}",
        author="Kinewind",
    )

    def _footer(canvas, _doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8.5)
        canvas.setFillColor(SLATE)
        canvas.drawCentredString(A4[0] / 2, 1.1 * cm, f"Kinewind · {_doc.page}")
        canvas.restoreState()

    left_lines = [
        "<b>Cristian Garrido Soliño</b>",
        "N. Colegio: 12392",
        "DNI: 53175115N",
    ]
    right_lines = [
        "C/Barbate nº 2 (Centro de Belleza Susana Soliño)",
        "Cangas del Morrazo · 36940 Pontevedra",
        "Teléfono: +34 620 616 015",
        "hola@kinewindgalicia.es",
    ]
    header_left = [
        Paragraph(line, ParagraphStyle("hl", parent=cell, fontSize=10, leading=15))
        for line in left_lines
    ]
    header_right = [
        Paragraph(line, ParagraphStyle("hr", parent=cell, fontSize=10, leading=15))
        for line in right_lines
    ]
    letterhead = Table(
        [[header_left, header_right]],
        colWidths=[8 * cm, 8 * cm],
    )
    letterhead.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story = [letterhead, Spacer(1, 0.3 * cm)] + [
        Paragraph("Informe de tratamiento", subtitle),
        Spacer(1, 0.1 * cm),
    ]

    patient = treatment.patient
    story.append(Paragraph("Paciente", h2))
    story.append(
        _info_table(
            [
                ("Nombre", patient.full_name),
                ("DNI", patient.dni or "—"),
                ("Nacimiento", patient.birth_date.strftime("%d/%m/%Y") if patient.birth_date else "—"),
                ("Teléfono", patient.phone or "—"),
                ("Email", patient.email or "—"),
            ]
        )
    )

    story.append(Paragraph("Tratamiento", h2))
    story.append(
        _info_table(
            [
                ("Diagnóstico", treatment.diagnosis),
                ("Frecuencia", treatment.frequency or "—"),
                ("Inicio", treatment.start_date.strftime("%d/%m/%Y") if treatment.start_date else "—"),
                ("Fin", treatment.end_date.strftime("%d/%m/%Y") if treatment.end_date else "—"),
                ("Estado", treatment.get_status_display()),
                ("Sesiones", f"{treatment.sessions_done} / {treatment.total_sessions}"),
            ]
        )
    )
    if treatment.description:
        story.append(Paragraph("Descripción", h2))
        story.append(
            Paragraph(treatment.description.replace("\n", "<br/>"), block)
        )
    if treatment.notes:
        story.append(Paragraph("Observaciones", h2))
        story.append(Paragraph(treatment.notes.replace("\n", "<br/>"), block))

    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("Plan de sesiones", h2))
    sessions = list(treatment.sessions.order_by("number"))
    if sessions:
        rows = [
            [Paragraph(c, header) for c in ("Nº", "Fecha", "Estado", "Notas clínicas", "Evolución")]
        ]
        for session in sessions:
            color = _STATUS_COLORS.get(session.status, colors.black)
            rows.append(
                [
                    Paragraph(str(session.number), cell),
                    Paragraph(session.date.strftime("%d/%m/%Y"), cell),
                    Paragraph(
                        f'<font color="{color.hexval()}"><b>{session.get_status_display()}</b></font>',
                        cell,
                    ),
                    Paragraph(session.clinical_notes or "—", cell),
                    Paragraph(session.evolution or "—", cell),
                ]
            )
        table = Table(rows, colWidths=[1.2 * cm, 2.4 * cm, 2.6 * cm, 5.4 * cm, 5.4 * cm], repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), TEAL),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ]
            )
        )
        story.append(table)
    else:
        story.append(Paragraph("El tratamiento no tiene sesiones registradas.", cell))

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()
