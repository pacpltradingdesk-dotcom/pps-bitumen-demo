---
description: Initialize and run the Bitumen Sales Dashboard project
---

# Project Initialization Workflow

## Prerequisites
- Python 3.8+ installed and in PATH
- pip package manager

## Initialization Steps

### 1. Install Dependencies
```bash
pip install pandas openpyxl pyarrow streamlit numpy fpdf
```

### 2. Convert/Prepare Data (if needed)
If `logistics_data.parquet` doesn't exist:
```bash
python convert_data.py
```

### 3. Run the Dashboard
```bash
python -m streamlit run dashboard.py
```

Or use the batch launcher:
```bash
run_dashboard.bat
```

## Project Structure
- `dashboard.py` - Main Streamlit application (Logistics Pricing AI)
- `optimizer.py` - Cost optimization engine
- `pdf_generator.py` - Quote PDF generation
- `sales_calendar.py` - Sales calendar with holidays/festivals
- `distance_matrix.py` - Logistics distance calculations
- `feasibility_engine.py` - Feasibility assessment
- `party_master.py` - Party management system
- `source_master.py` - Source directory management
- `mock_data.py` - Sample data generation
- `company_config.py` - Company configuration

## Quick Start
// turbo-all
Run `run_dashboard.bat` to auto-install dependencies and launch the dashboard.
