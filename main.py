from datetime import date, datetime, timedelta
from enum import Enum
from typing import Literal

from pydantic import BaseModel
from reportlab.lib.colors import black, lightgrey
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

pdfmetrics.registerFont(TTFont("Yrsa", "fonts/yrsa/Yrsa-Light.ttf"))
pdfmetrics.registerFont(TTFont("YrsaBold", "fonts/yrsa/Yrsa-SemiBold.ttf"))
pdfmetrics.registerFont(TTFont("YrsaItalic", "fonts/yrsa/Yrsa-LightItalic.ttf"))
pdfmetrics.registerFont(TTFont("YrsaBoldItalic", "fonts/yrsa/Yrsa-SemiBoldItalic.ttf"))


class FontStyle(Enum):
    BASE = "base"
    BOLD = "bold"
    ITALIC = "italic"
    BOLD_ITALIC = "bold_italic"


MONTH_TO_FRENCH = {
    1: "janvier",
    2: "février",
    3: "mars",
    4: "avril",
    5: "mai",
    6: "juin",
    7: "juillet",
    8: "août",
    9: "septembre",
    10: "octobre",
    11: "novembre",
    12: "décembre",
}


class Alignment(Enum):
    LEFT = "left"
    RIGHT = "right"
    CENTER = "center"
    JUSTIFY = "justify"


class Client(BaseModel):
    name: str
    gender: Literal["M", "F"]
    city: str
    zip_code: str
    adress: str


class LawFirm(BaseModel):
    principal_lawyer: str
    collaborators: list[str]
    zip_code: str
    city: str
    adress: str
    phone: str
    toque_adress: str
    mail: str
    website: str
    vat_number: str
    siret_number: str


class Time(BaseModel):
    description: str
    duration: timedelta
    date: date


class Fees(BaseModel):
    times: list[Time]
    price: float


class PDFInvoiceWriter:
    font_base = "Yrsa"
    font_bold = "YrsaBold"
    font_italic = "YrsaItalic"
    font_bold_italic = "YrsaBoldItalic"

    def __init__(self, output_path: str, client: Client, lawfirm: LawFirm, fees: Fees):
        self.output_path = output_path
        self.client = client
        self.lawfirm = lawfirm
        self.fees = fees
        self.doc = SimpleDocTemplate(output_path, pagesize=letter)
        self.styles = getSampleStyleSheet()

        # Generates an empty story
        self.contents = []

    def font_from_style(self, style: FontStyle):
        match style:
            case FontStyle.BASE:
                return self.font_base
            case FontStyle.BOLD:
                return self.font_bold
            case FontStyle.ITALIC:
                return self.font_italic
            case FontStyle.BOLD_ITALIC:
                return self.font_bold_italic
            case _:
                raise ValueError(f"Invalid font style: {style}")

    def _draw_footer(self, canvas, doc):
        """Draws the footer on each page."""
        canvas.saveState()

        footer_style = self.style(font_size=9, alignment=Alignment.CENTER)
        y_position = doc.bottomMargin / 2  # Center vertically in the bottom margin

        # Line 1: Address, City, Zip
        line1_text = (
            f"{self.lawfirm.adress} {self.lawfirm.zip_code} {self.lawfirm.city}"
        )
        p1 = Paragraph(line1_text, footer_style)
        w1, h1 = p1.wrap(doc.width, doc.bottomMargin)
        p1.drawOn(canvas, doc.leftMargin, y_position + h1 * 1.5)  # Position lines

        # Line 2: Phone, Mail, Website
        line2_text = f"Tel : {self.lawfirm.phone} - Mail : {self.lawfirm.mail} - Site : {self.lawfirm.website}"
        p2 = Paragraph(line2_text, footer_style)
        w2, h2 = p2.wrap(doc.width, doc.bottomMargin)
        p2.drawOn(
            canvas, doc.leftMargin, y_position + h1 * 0.5
        )  # Position below line 1

        # Line 3: VAT, SIRET
        line3_text = f"TVA Intracommunautaire : {self.lawfirm.vat_number} - SIRET : {self.lawfirm.siret_number}"
        p3 = Paragraph(line3_text, footer_style)
        w3, h3 = p3.wrap(doc.width, doc.bottomMargin)
        p3.drawOn(
            canvas, doc.leftMargin, y_position - h2 * 0.5
        )  # Position below line 2

        canvas.restoreState()

    def build(self):
        self.lawyer_title(self.lawfirm.principal_lawyer)
        self.spacer(1.5)
        if self.lawfirm.collaborators:
            self.collaborator_title(self.lawfirm.collaborators)
            self.spacer(1)
        self.client_address(self.client)
        self.spacer(3)
        self.place_and_date("Paris", datetime.now())
        self.spacer(0.5)
        self.invoice_number_rectangle("2025-121")
        self.spacer(2)
        self.detail_fees()
        self.spacer(2)
        self.final()

        # Build the document using the footer drawing callback
        self.doc.build(
            self.contents, onFirstPage=self._draw_footer, onLaterPages=self._draw_footer
        )
        print(f"ReportLab PDF '{self.output_path}' generated successfully.")

    def spacer(self, height: float, base_height: float = 12):
        """Adds a spacer to the document."""
        self.contents.append(Spacer(1, base_height * height))

    def style(
        self,
        alignment: Alignment = Alignment.LEFT,
        font_style: FontStyle = FontStyle.BASE,
        font_size: float = 12,
    ) -> ParagraphStyle:
        style_name = f"{alignment.value}_{font_style.value}"

        # If not in cache, create, store, and return
        style = ParagraphStyle(style_name, parent=self.styles["Normal"])
        # Convert Alignment enum to ReportLab constant for alignment
        if alignment == Alignment.LEFT:
            style.alignment = TA_LEFT
        elif alignment == Alignment.RIGHT:
            style.alignment = TA_RIGHT
        elif alignment == Alignment.CENTER:
            style.alignment = TA_CENTER
        elif alignment == Alignment.JUSTIFY:
            style.alignment = TA_JUSTIFY

        style.fontName = self.font_from_style(font_style)
        style.fontSize = font_size
        return style

    def lawyer_title(self, name):
        """Adds a centered paragraph with the main's lawyer name"""
        # Create a copy of the style to avoid modifying the original
        self.contents.append(
            Paragraph(name, self.style(Alignment.CENTER, FontStyle.BOLD, font_size=16))
        )
        self.spacer(0.3)
        self.contents.append(
            Paragraph("Avocate à la Cour", self.style(Alignment.CENTER, font_size=16))
        )

    def collaborator_title(self, names: list[str]):
        """Adds a left-aligned paragraph with the lawyer's collaborators"""
        self.contents.append(
            Paragraph(
                "En collaboration avec :", self.style(Alignment.LEFT, FontStyle.ITALIC)
            )
        )

        for name in names:
            self.contents.append(Paragraph(name, self.style(Alignment.LEFT)))

        self.contents.append(
            Paragraph(
                "Avocate{} à la Cour".format("s" if len(names) > 1 else ""),
                self.style(Alignment.LEFT),
            )
        )

    def client_address(self, client: Client):
        # Use bold style for the name line
        style = self.style(Alignment.RIGHT, FontStyle.BOLD)
        title = "Monsieur" if client.gender == "M" else "Madame"

        self.contents.append(Paragraph(f"{title} {client.name}", style))
        self.contents.append(Paragraph(f"{client.adress}", style))
        self.contents.append(Paragraph(f"{client.zip_code} {client.city}", style))

    def invoice_number_rectangle(self, number: str):
        """Shows the invoice number in a rectangle of the width of the page."""

        text = f"FACTURE N°{number}"
        p = Paragraph(text, self.style(Alignment.CENTER, FontStyle.BOLD))

        available_width = letter[0] - 2 * inch
        data = [[p]]
        table = Table(data, colWidths=[available_width], rowHeights=[0.5 * inch])
        ts = TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 1, black),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
        table.setStyle(ts)

        self.contents.append(table)

    def place_and_date(self, place: str, date: datetime):
        """Adds a date to the document."""
        self.contents.append(
            Paragraph(
                f"{place}, le {date.day} {MONTH_TO_FRENCH[date.month]} {date.year}",
                self.style(Alignment.RIGHT),
            )
        )

    def list_fee_table(self):
        """Shows the list of individual fees"""
        data = []
        for time in self.fees.times:
            price = time.duration.total_seconds() / 3600 * self.fees.price
            hours = time.duration.total_seconds() // 3600
            minutes = (time.duration.total_seconds() % 3600) // 60

            data.append(
                [
                    Paragraph(f"", self.style()),
                    Paragraph(
                        f"{time.description} ({time.date.strftime('%d/%m/%Y')})",
                        self.style(Alignment.LEFT, FontStyle.BOLD),
                    ),
                    Paragraph(
                        f"{hours:02.0f}:{minutes:02.0f}",
                        self.style(Alignment.RIGHT, FontStyle.BOLD),
                    ),
                    Paragraph(
                        f"{price:.2f} €", self.style(Alignment.RIGHT, FontStyle.BOLD)
                    ),
                ]
            )

        available_width = letter[0] - 2 * inch

        before_width = available_width * 0.15
        description_width = available_width * 0.55
        time_width = available_width * 0.15
        price_width = available_width * 0.15

        table = Table(
            data,
            colWidths=[before_width, description_width, time_width, price_width],
            rowHeights=[12] * len(data),  # Reduce row height to 12 points
        )
        ts = TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 0),  # Reduce top padding
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),  # Reduce bottom padding
            ]
        )
        table.setStyle(ts)

        self.contents.append(table)

    def show_total(self):
        """Shows the total of the fees in a 4-row table."""
        ht_price = sum(
            time.duration.total_seconds() / 3600 * self.fees.price
            for time in self.fees.times
        )
        total_time_seconds = sum(
            time.duration.total_seconds() for time in self.fees.times
        )
        hours = total_time_seconds // 3600
        minutes = (total_time_seconds % 3600) // 60
        vat = ht_price * 0.20
        ttc_price = ht_price + vat

        # Define styles for the total table
        label_style = self.style(Alignment.LEFT, FontStyle.BOLD)
        value_style = self.style(Alignment.RIGHT, FontStyle.BOLD)
        empty_style = self.style()  # For the empty first column cell

        data = [
            [
                Paragraph("", empty_style),  # Empty first cell
                Paragraph(
                    f"<u>Soit un total de {hours:02.0f}h{minutes:02.0f}</u>",
                    label_style,
                ),
                Paragraph("", value_style),
            ],
            [
                Paragraph("", empty_style),  # Empty first cell
                Paragraph("Honoraires H.T.", label_style),
                Paragraph(f"{ht_price:.2f} €", value_style),
            ],
            [
                Paragraph("", empty_style),  # Empty first cell
                Paragraph("TVA 20%", label_style),
                Paragraph(f"{vat:.2f} €", value_style),
            ],
            [
                Paragraph("", empty_style),  # Empty first cell
                Paragraph("TOTAL T.T.C. DU", label_style),
                Paragraph(f"{ttc_price:.2f} €", value_style),
            ],
        ]

        # Calculate available width and split for the three columns
        available_width = letter[0] - 2 * inch
        col0_width = available_width * 0.10  # Empty first column
        remaining_width = available_width * 0.90
        col1_width = remaining_width * 0.70  # Label column (70% of remaining)
        col2_width = remaining_width * 0.30  # Value column (30% of remaining)

        total_table = Table(data, colWidths=[col0_width, col1_width, col2_width])

        # Basic style: no grid lines, vertical alignment
        ts = TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BACKGROUND", (0, -1), (2, -1), lightgrey),
            ]
        )
        total_table.setStyle(ts)

        self.contents.append(total_table)

    def detail_fees(self):
        fees_style = self.style(font_style=FontStyle.BOLD)
        self.contents.append(Paragraph(f"<u>Honoraires</u>", fees_style))
        self.spacer(1)

        hourly_price_txt = f"Facturation horaire : {self.fees.price} euros HT de l'heure (selon l'article 2.1 du contrat de mission)"
        self.contents.append(Paragraph(hourly_price_txt, fees_style))
        self.spacer(1)

        self.contents.append(Paragraph("Diligences effectuées :", fees_style))
        self.spacer(1)

        self.list_fee_table()

        self.spacer(5)
        self.show_total()

    def final(self):
        self.contents.append(
            Paragraph("TVA Applicable -", self.style(font_style=FontStyle.ITALIC))
        )
        self.contents.append(
            Paragraph(
                "En votre aimable règlement", self.style(font_style=FontStyle.BOLD)
            )
        )
        self.spacer(1)

        self.contents.append(
            Paragraph(
                "<u>Conformément à nos usages de professions libérales, la présente est payable dès réception</u>",
                self.style(),
            )
        )


if __name__ == "__main__":
    client = Client(
        name="John DOE",
        gender="M",
        city="Paris",
        zip_code="75000",
        adress="123 Rue de la Paix",
    )
    lawfirm = LawFirm(
        principal_lawyer="Jean-Pierre Machin",
        collaborators=["Gerard LOULOU", "Francesca MARTINI"],
        zip_code="75000",
        city="Paris",
        adress="123 Rue de la Paix",
        phone="01.23.45.67.89",
        toque_adress="Somewhere AX8786",
        mail="cabinet.avocate@gmail.com",
        website="cabinet-avocat.fr",
        vat_number="FR1234567890",
        siret_number="1234567890",
    )

    fees = Fees(
        times=[
            Time(
                description="Courriel Mme : Projet LO",
                duration=timedelta(minutes=11),
                date=date(2025, 3, 24),
            ),
            Time(
                description="Courriel Mme",
                duration=timedelta(minutes=6),
                date=date(2025, 3, 25),
            ),
            Time(
                description="Renvoi audience",
                duration=timedelta(hours=1),
                date=date(2025, 4, 2),
            ),
            Time(
                description="An element done in 3 hours and 12 minutes",
                duration=timedelta(hours=3, minutes=12),
                date=date(2025, 5, 3),
            ),
        ],
        price=300,
    )
    writer = PDFInvoiceWriter(
        output_path="invoice.pdf", client=client, lawfirm=lawfirm, fees=fees
    )
    writer.build()
