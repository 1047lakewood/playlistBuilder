import json
import os
import csv
from datetime import datetime
from typing import List, Dict, Optional
import logging

# Logger will be set in __init__ based on station_id

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    # Logger will be available in instances


class AdReportGenerator:
    """Generate professional advertiser reports for verification and invoicing."""

    def __init__(self, ad_logger, station_id):
        """
        Initialize the report generator.

        Args:
            ad_logger: AdPlayLogger instance to access play statistics
            station_id: Station identifier (e.g., 'station_1047' or 'station_887')
        """
        self.ad_logger = ad_logger
        self.station_id = station_id

        # Set up logger based on station_id
        logger_name = f'AdReportGenerator_{station_id.split("_")[1]}'  # e.g., 'AdReportGenerator_1047'
        self.logger = logging.getLogger(logger_name)

    def generate_csv_report(self, ad_name: str, start_date: str, end_date: str, 
                           output_file: str) -> bool:
        """
        Generate a CSV report for a specific ad.

        Args:
            ad_name: Name of the ad to generate report for
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            output_file: Path to save the CSV file

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get detailed statistics
            detailed_stats = self.ad_logger.get_detailed_stats(start_date, end_date)
            if "error" in detailed_stats:
                self.logger.error(f"Error getting stats: {detailed_stats['error']}")
                return False

            daily_plays = detailed_stats.get("daily_plays", {})

            # Collect all play records for this ad
            play_records = []
            for date_str, ad_plays in daily_plays.items():
                if ad_name in ad_plays:
                    play_count = ad_plays[ad_name]
                    play_records.append({
                        "date": date_str,
                        "plays": play_count
                    })

            # Sort by date
            play_records.sort(key=lambda x: x["date"])

            # Calculate totals
            total_plays = sum(record["plays"] for record in play_records)

            # Write CSV
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)

                # Header section
                writer.writerow(["Advertiser Report"])
                writer.writerow([])
                writer.writerow(["Ad Name:", ad_name])
                writer.writerow(["Report Period:", f"{start_date} to {end_date}"])
                writer.writerow(["Generated:", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
                writer.writerow(["Total Plays:", total_plays])
                writer.writerow([])

                # Play details
                writer.writerow(["Date", "Number of Plays"])
                writer.writerow(["=" * 15, "=" * 15])

                for record in play_records:
                    writer.writerow([record["date"], record["plays"]])

                writer.writerow([])
                writer.writerow(["TOTAL", total_plays])

            self.logger.info(f"CSV report generated: {output_file}")
            return True

        except Exception as e:
            self.logger.error(f"Error generating CSV report: {e}")
            return False

    def generate_pdf_report(self, ad_name: str, start_date: str, end_date: str,
                           output_file: str, advertiser_name: Optional[str] = None,
                           company_name: Optional[str] = None) -> bool:
        """
        Generate a professional PDF report for a specific ad.

        Args:
            ad_name: Name of the ad to generate report for
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            output_file: Path to save the PDF file
            advertiser_name: Optional advertiser contact name
            company_name: Optional company name for header

        Returns:
            bool: True if successful, False otherwise
        """
        if not REPORTLAB_AVAILABLE:
            self.logger.error("reportlab not available - cannot generate PDF")
            return False

        try:
            # Get detailed statistics
            detailed_stats = self.ad_logger.get_detailed_stats(start_date, end_date)
            if "error" in detailed_stats:
                self.logger.error(f"Error getting stats: {detailed_stats['error']}")
                return False

            daily_plays = detailed_stats.get("daily_plays", {})

            # Collect all play records for this ad
            play_records = []
            for date_str, ad_plays in daily_plays.items():
                if ad_name in ad_plays:
                    play_count = ad_plays[ad_name]
                    play_records.append({
                        "date": date_str,
                        "plays": play_count
                    })

            # Sort by date
            play_records.sort(key=lambda x: x["date"])

            # Calculate totals
            total_plays = sum(record["plays"] for record in play_records)
            total_days = len(play_records)
            avg_plays_per_day = total_plays / total_days if total_days > 0 else 0

            # Create PDF
            doc = SimpleDocTemplate(output_file, pagesize=letter)
            story = []
            styles = getSampleStyleSheet()

            # Custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#1a1a1a'),
                spaceAfter=30,
                alignment=TA_CENTER
            )

            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=14,
                textColor=colors.HexColor('#333333'),
                spaceAfter=12,
                spaceBefore=12
            )

            # Title
            if company_name:
                story.append(Paragraph(company_name, title_style))
            story.append(Paragraph("Advertisement Airplay Report", title_style))
            story.append(Spacer(1, 0.3 * inch))

            # Report info section
            info_data = [
                ["Ad Name:", ad_name],
                ["Report Period:", f"{start_date} to {end_date}"],
                ["Generated:", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
            ]

            if advertiser_name:
                info_data.insert(0, ["Advertiser:", advertiser_name])

            info_table = Table(info_data, colWidths=[2*inch, 4*inch])
            info_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#333333')),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(info_table)
            story.append(Spacer(1, 0.3 * inch))

            # Summary section
            story.append(Paragraph("Summary", heading_style))

            summary_data = [
                ["Total Plays", str(total_plays)],
                ["Days with Airplay", str(total_days)],
                ["Average Plays per Day", f"{avg_plays_per_day:.1f}"],
            ]

            summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
            summary_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 12),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1a1a1a')),
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f0f0f0')),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#cccccc')),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ]))
            story.append(summary_table)
            story.append(Spacer(1, 0.3 * inch))

            # Detailed plays section
            story.append(Paragraph("Daily Airplay Details", heading_style))

            # Create table data
            table_data = [["Date", "Number of Plays"]]
            for record in play_records:
                table_data.append([record["date"], str(record["plays"])])

            # Add total row
            table_data.append(["TOTAL", str(total_plays)])

            # Create table
            detail_table = Table(table_data, colWidths=[3*inch, 2*inch])
            detail_table.setStyle(TableStyle([
                # Header row
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),

                # Data rows
                ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -2), 10),
                ('ALIGN', (0, 1), (0, -2), 'LEFT'),
                ('ALIGN', (1, 1), (1, -2), 'RIGHT'),

                # Total row
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, -1), (-1, -1), 11),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#d9d9d9')),
                ('ALIGN', (0, -1), (0, -1), 'LEFT'),
                ('ALIGN', (1, -1), (1, -1), 'RIGHT'),

                # All cells
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#cccccc')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),

                # Alternating row colors (except header and total)
                ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f9f9f9')]),
            ]))
            story.append(detail_table)
            story.append(Spacer(1, 0.5 * inch))

            # Footer note
            footer_style = ParagraphStyle(
                'Footer',
                parent=styles['Normal'],
                fontSize=9,
                textColor=colors.HexColor('#666666'),
                alignment=TA_CENTER
            )
            story.append(Paragraph(
                "This report certifies that the above advertisement was broadcast during the specified period.",
                footer_style
            ))

            # Build PDF
            doc.build(story)

            self.logger.info(f"PDF report generated: {output_file}")
            return True

        except Exception as e:
            self.logger.error(f"Error generating PDF report: {e}")
            import traceback
            traceback.print_exc()
            return False

    def generate_report(self, start_date=None, end_date=None, advertiser_name=None, company_name=None):
        """
        Generate both CSV and PDF reports for all ads.

        Args:
            start_date: Start date in YYYY-MM-DD format (optional)
            end_date: End date in YYYY-MM-DD format (optional)
            advertiser_name: Optional advertiser contact name
            company_name: Optional company name for header

        Returns:
            tuple: (csv_file_path, pdf_file_path) if successful, (None, None) otherwise
        """
        try:
            # Get all ads that have plays in the date range
            detailed_stats = self.ad_logger.get_detailed_stats(start_date, end_date)
            if "error" in detailed_stats:
                self.logger.error(f"Error getting stats for report generation: {detailed_stats['error']}")
                return None, None

            daily_plays = detailed_stats.get("daily_plays", {})
            ad_totals = detailed_stats.get("ad_totals", {})

            # Get ads that have plays in the period
            played_ads = [ad_name for ad_name, total in ad_totals.items() if total > 0]

            if not played_ads:
                self.logger.warning("No ads with plays found for the selected period")
                return None, None

            # Generate timestamp for filenames
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Generate CSV report for each ad
            csv_files = []
            for ad_name in played_ads:
                csv_filename = f"REAL_REPORT_{ad_name.replace(' ', '_').replace('/', '_')}_{timestamp}.csv"
                csv_path = os.path.join(os.getcwd(), csv_filename)

                if self.generate_csv_report(ad_name, start_date or "2020-01-01", end_date or datetime.now().strftime("%Y-%m-%d"), csv_path):
                    csv_files.append(csv_path)

            # Generate PDF report for each ad
            pdf_files = []
            for ad_name in played_ads:
                pdf_filename = f"REAL_REPORT_{ad_name.replace(' ', '_').replace('/', '_')}_{timestamp}.pdf"
                pdf_path = os.path.join(os.getcwd(), pdf_filename)

                if self.generate_pdf_report(ad_name, start_date or "2020-01-01", end_date or datetime.now().strftime("%Y-%m-%d"), pdf_path, advertiser_name, company_name):
                    pdf_files.append(pdf_path)

            # Return the first CSV and PDF files (for compatibility with existing UI)
            csv_result = csv_files[0] if csv_files else None
            pdf_result = pdf_files[0] if pdf_files else None

            if csv_result and pdf_result:
                self.logger.info(f"Generated reports: CSV={csv_result}, PDF={pdf_result}")
            else:
                self.logger.error(f"Failed to generate reports. CSV: {csv_result}, PDF: {pdf_result}")

            return csv_result, pdf_result

        except Exception as e:
            self.logger.error(f"Error generating reports: {e}")
            import traceback
            traceback.print_exc()
            return None, None

    def generate_multi_ad_report(self, ad_names: List[str], start_date: str,
                                end_date: str, output_file: str,
                                format: str = "csv") -> bool:
        """
        Generate a report covering multiple ads.

        Args:
            ad_names: List of ad names to include
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            output_file: Path to save the report
            format: 'csv' or 'pdf'

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if format.lower() == "csv":
                return self._generate_multi_ad_csv(ad_names, start_date, end_date, output_file)
            elif format.lower() == "pdf":
                return self._generate_multi_ad_pdf(ad_names, start_date, end_date, output_file)
            else:
                self.logger.error(f"Unsupported format: {format}")
                return False

        except Exception as e:
            self.logger.error(f"Error generating multi-ad report: {e}")
            return False

    def _generate_multi_ad_csv(self, ad_names: List[str], start_date: str,
                               end_date: str, output_file: str) -> bool:
        """Generate a CSV report for multiple ads."""
        try:
            detailed_stats = self.ad_logger.get_detailed_stats(start_date, end_date)
            if "error" in detailed_stats:
                return False

            daily_plays = detailed_stats.get("daily_plays", {})

            # Collect all dates
            all_dates = sorted(daily_plays.keys())

            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)

                # Header
                writer.writerow(["Multi-Ad Report"])
                writer.writerow([])
                writer.writerow(["Report Period:", f"{start_date} to {end_date}"])
                writer.writerow(["Generated:", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
                writer.writerow([])

                # Table header
                header = ["Date"] + ad_names + ["Total"]
                writer.writerow(header)
                writer.writerow(["=" * 15] * len(header))

                # Daily breakdown
                for date_str in all_dates:
                    row = [date_str]
                    ad_plays = daily_plays.get(date_str, {})
                    daily_total = 0

                    for ad_name in ad_names:
                        plays = ad_plays.get(ad_name, 0)
                        row.append(plays)
                        daily_total += plays

                    row.append(daily_total)
                    writer.writerow(row)

                # Totals row
                totals_row = ["TOTAL"]
                grand_total = 0
                for ad_name in ad_names:
                    ad_total = sum(daily_plays.get(date_str, {}).get(ad_name, 0) 
                                 for date_str in all_dates)
                    totals_row.append(ad_total)
                    grand_total += ad_total
                totals_row.append(grand_total)
                writer.writerow([])
                writer.writerow(totals_row)

            self.logger.info(f"Multi-ad CSV report generated: {output_file}")
            return True

        except Exception as e:
            self.logger.error(f"Error generating multi-ad CSV: {e}")
            return False

    def _generate_multi_ad_pdf(self, ad_names: List[str], start_date: str,
                               end_date: str, output_file: str) -> bool:
        """Generate a PDF report for multiple ads."""
        if not REPORTLAB_AVAILABLE:
            self.logger.error("reportlab not available - cannot generate PDF")
            return False

        try:
            detailed_stats = self.ad_logger.get_detailed_stats(start_date, end_date)
            if "error" in detailed_stats:
                return False

            daily_plays = detailed_stats.get("daily_plays", {})
            all_dates = sorted(daily_plays.keys())

            # Create PDF
            doc = SimpleDocTemplate(output_file, pagesize=letter)
            story = []
            styles = getSampleStyleSheet()

            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=20,
                textColor=colors.HexColor('#1a1a1a'),
                spaceAfter=20,
                alignment=TA_CENTER
            )

            # Title
            story.append(Paragraph("Multi-Ad Airplay Report", title_style))
            story.append(Spacer(1, 0.2 * inch))

            # Info
            info_data = [
                ["Report Period:", f"{start_date} to {end_date}"],
                ["Generated:", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                ["Ads Included:", ", ".join(ad_names)]
            ]

            info_table = Table(info_data, colWidths=[2*inch, 4.5*inch])
            info_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(info_table)
            story.append(Spacer(1, 0.3 * inch))

            # Build table data
            col_width = 1.2 * inch
            table_data = [["Date"] + ad_names + ["Total"]]

            for date_str in all_dates:
                row = [date_str]
                ad_plays = daily_plays.get(date_str, {})
                daily_total = 0

                for ad_name in ad_names:
                    plays = ad_plays.get(ad_name, 0)
                    row.append(str(plays))
                    daily_total += plays

                row.append(str(daily_total))
                table_data.append(row)

            # Totals
            totals_row = ["TOTAL"]
            grand_total = 0
            for ad_name in ad_names:
                ad_total = sum(daily_plays.get(date_str, {}).get(ad_name, 0)
                             for date_str in all_dates)
                totals_row.append(str(ad_total))
                grand_total += ad_total
            totals_row.append(str(grand_total))
            table_data.append(totals_row)

            # Create table
            detail_table = Table(table_data)
            detail_table.setStyle(TableStyle([
                # Header
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),

                # Total row
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#d9d9d9')),

                # All cells
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#cccccc')),
                ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f9f9f9')]),
            ]))

            story.append(detail_table)
            doc.build(story)

            self.logger.info(f"Multi-ad PDF report generated: {output_file}")
            return True

        except Exception as e:
            self.logger.error(f"Error generating multi-ad PDF: {e}")
            return False

