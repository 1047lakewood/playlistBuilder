# Ad Report Generation Feature

## Overview

The Ad Report Generation system allows you to create professional reports for advertisers to verify that their ads were played during a specified period. This is essential for transparency and billing purposes.

## Features

### 1. **Single Ad Reports**
Generate detailed reports for individual ads showing:
- Total number of plays
- Daily breakdown of plays
- Date range covered
- Optional advertiser and company name (PDF only)

### 2. **Multi-Ad Reports**
Generate comparative reports covering multiple ads:
- Side-by-side comparison of play counts
- Daily breakdown for all selected ads
- Total plays per ad and per day

### 3. **Export Formats**

#### PDF Reports (Recommended for Advertisers)
- Professional, formatted layout
- Perfect for emailing to clients
- Includes company branding options
- Suitable for invoicing and proof of airplay
- Features:
  - Summary statistics (total plays, average per day)
  - Daily breakdown table with alternating row colors
  - Header with advertiser/company information
  - Professional formatting with colors and spacing

#### CSV Reports (For Data Analysis)
- Spreadsheet-compatible format
- Easy to import into Excel or Google Sheets
- Good for internal analysis
- Simple, clean tabular format

## How to Use

### Via the User Interface

1. **Open the Ad Statistics Window**
   - Launch your main application
   - Navigate to the Ad Statistics section

2. **Click "Generate Report"**
   - This opens the Report Generator dialog

3. **Configure Your Report**
   - **Report Type**: Choose Single Ad or Multi-Ad
   - **Ad Selection**: 
     - For single ad: Select from dropdown
     - For multi-ad: Check all ads you want to include
   - **Date Range**: Enter start and end dates (YYYY-MM-DD format)
     - Example: 2025-09-01 to 2025-09-30
   - **Output Format**: Choose PDF or CSV
   - **Optional (PDF only)**:
     - Advertiser Name: Contact name for the advertiser
     - Company Name: Your radio station or company name

4. **Generate and Save**
   - Click "Generate Report"
   - Choose save location
   - Option to open the report immediately

### Programmatically

```python
from config_manager import ConfigManager
from ad_play_logger import AdPlayLogger
from ad_report_generator import AdReportGenerator

# Initialize
config_manager = ConfigManager()
ad_logger = AdPlayLogger(config_manager)
report_generator = AdReportGenerator(ad_logger)

# Generate single ad PDF report
report_generator.generate_pdf_report(
    ad_name="My Ad Campaign",
    start_date="2025-09-01",
    end_date="2025-09-30",
    output_file="advertiser_report.pdf",
    advertiser_name="John Smith",
    company_name="WXYZ Radio Station"
)

# Generate CSV report
report_generator.generate_csv_report(
    ad_name="My Ad Campaign",
    start_date="2025-09-01",
    end_date="2025-09-30",
    output_file="advertiser_report.csv"
)

# Generate multi-ad report
report_generator.generate_multi_ad_report(
    ad_names=["Ad 1", "Ad 2", "Ad 3"],
    start_date="2025-09-01",
    end_date="2025-09-30",
    output_file="multi_ad_report.pdf",
    format="pdf"
)
```

## Dependencies

The report generation system requires:
- **Python 3.6+**
- **reportlab** (for PDF generation): `pip install reportlab`
  - If reportlab is not installed, only CSV reports will be available

## Report Contents

### Single Ad Report (PDF)

**Header Section:**
- Company name (if provided)
- Report title
- Advertiser name (if provided)
- Ad name
- Report period
- Generation timestamp

**Summary Section:**
- Total plays during the period
- Number of days with airplay
- Average plays per day

**Daily Breakdown:**
- Table showing each day and play count
- Alternating row colors for readability
- Bold total row at bottom

**Footer:**
- Certification statement

### Multi-Ad Report

**Header:**
- Report period
- List of included ads
- Generation timestamp

**Daily Breakdown Table:**
- Rows: Each day in the date range
- Columns: Each ad + total column
- Shows play counts for each ad on each day
- Total row at bottom

## Best Practices

1. **Regular Reporting**
   - Generate monthly reports for each advertiser
   - Keep copies for your records

2. **Professional Delivery**
   - Use PDF format for client-facing reports
   - Include your company name for branding
   - Add the advertiser's name for personalization

3. **Data Verification**
   - Cross-reference reports with your broadcast logs
   - Verify dates before sending to clients

4. **Archival**
   - Save reports with descriptive filenames
   - Example: `2025-09_ABC_Corp_Ad_Report.pdf`
   - Keep organized by advertiser and month

## Troubleshooting

### "reportlab not available" Error
- Install reportlab: `pip install reportlab`
- Or use CSV format instead

### No Data in Report
- Verify the ad was played during the date range
- Check that ad logging is enabled
- Ensure the date range is correct (YYYY-MM-DD)

### Date Format Errors
- Use YYYY-MM-DD format only
- Examples: 2025-01-15, 2025-12-31
- Start date must be before or equal to end date

## File Locations

- **Report Generator Module**: `src/ad_report_generator.py`
- **Ad Logger**: `src/ad_play_logger.py`
- **UI Integration**: `src/ui_ad_statistics_window.py`
- **Test Script**: `test_ad_report_generation.py`

## Testing

Run the test script to verify functionality:

```bash
python test_ad_report_generation.py
```

This will:
- Generate sample CSV and PDF reports
- Test single and multi-ad reports
- Verify all report generation functions

## Future Enhancements

Potential improvements for future versions:
- Email delivery integration
- Automated monthly report generation
- Additional report formats (Excel, HTML)
- Charts and graphs in PDF reports
- Hourly breakdown option
- Custom date range presets (last month, last quarter, etc.)

