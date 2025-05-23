# Universal Policy Checker

A comprehensive document policy checker that uses AI-powered agents to analyze and verify compliance against any type of policy document. The system supports multimodal content extraction from PDFs, Word documents, Excel files, and images, then creates specialized agents dynamically to check compliance across any domain (ESG, financial, regulatory, operational, etc.).

## Features

🚀 **Universal Policy Analysis** - Handles any type of policy across all domains  
📄 **Multimodal Document Processing** - Extracts from text, tables, charts, and images  
🤖 **Dynamic Agent Creation** - Creates specialized agents on-the-fly based on policy requirements  
🔍 **Advanced OCR & Chart Analysis** - Powered by Docling for superior document understanding  
📊 **Comprehensive Compliance Checking** - Multi-step, quantitative, comparative, and simple analysis modes  
🌐 **RESTful API** - Easy integration with existing systems  

## Quick Start

### Prerequisites

- Python 3.8 or higher
- OpenAI API key

### Installation

1. **Clone the repository:**
```bash
git clone <repository-url>
cd integrate_policy_checker
```

2. **Create and activate virtual environment:**

**On Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**On macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Using conda (alternative):**
```bash
conda create -n policy-checker python=3.9
conda activate policy-checker
```

3. **Install dependencies:**
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**Note:** If you encounter issues with Docling installation, try:
```bash
pip install docling docling-core docling-ibm-models docling-parse --no-cache-dir
```

4. **Set up environment variables:**
```bash
cp .env.example .env
```

Edit `.env` and add your API keys:
```env
OPENAI_API_KEY=your_openai_api_key_here
SECRET_KEY=your_flask_secret_key_here
```

**Important Notes:**
- `OPENAI_API_KEY`: Your OpenAI API key (required for AI-powered policy analysis)
- `SECRET_KEY`: Flask secret key for session security (generate a strong random string)

**Generate a secure SECRET_KEY:**
```bash
# Option 1: Using Python
python -c "import secrets; print(secrets.token_hex(32))"

# Option 2: Using openssl (if available)
openssl rand -hex 32

# Option 3: Online generator or use any strong random string
```

**Example `.env` file:**
```env
OPENAI_API_KEY=sk-proj-abcdef123456789...
SECRET_KEY=a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456
```

5. **Verify installation:**
```bash
python -c "import docling; print('Docling installed successfully')"
python -c "import openai; print('OpenAI installed successfully')"
```

### Running the Application

1. **Start the development server:**
```bash
python app.py
```

The application will be available at `http://localhost:5000`

2. **Verify installation:**
```bash
curl http://localhost:5000/domains
```

## API Usage

### 1. Analyze Text-Based Policy

Extract policy requirements from plain text:

```bash
curl -X POST http://localhost:5000/analyze-policy \
  -H "Content-Type: application/json" \
  -d '{
    "policy_text": "All employees must maintain ESG compliance with carbon emissions below 50 tons CO2/year and diversity metrics above industry average.",
    "domain_hint": "esg"
  }'
```

### 2. Upload and Analyze Documents

Process any document format (PDF, Word, Excel, Images):

```bash
curl -X POST http://localhost:5000/analyze-document-policy \
  -F "file=@your_policy_document.pdf" \
  -F "domain_hint=financial"
```

### 3. Check Compliance

Verify data against extracted policy requirements:

```bash
curl -X POST http://localhost:5000/check-compliance \
  -H "Content-Type: application/json" \
  -d '{
    "policy_checks": [
      {
        "check_type": "carbon_emission_threshold",
        "description": "Carbon emissions must be below 50 tons CO2/year",
        "criteria": "< 50 tons CO2/year",
        "data_fields": ["carbon_emissions"],
        "domain": "esg",
        "complexity": "simple"
      }
    ],
    "data": {
      "carbon_emissions": 45.2,
      "diversity_score": 78
    }
  }'
```

### 4. Preview Agents

See what agents would be created before running compliance checks:

```bash
curl -X POST http://localhost:5000/preview-agents \
  -H "Content-Type: application/json" \
  -d '{
    "policy_checks": [...]
  }'
```

## Supported File Formats

| Format | Extensions | Capabilities |
|--------|------------|-------------|
| **PDF** | `.pdf` | Advanced text extraction, table structure recognition, image extraction with OCR, chart analysis |
| **Word** | `.docx` | Text extraction, table extraction, image handling, document structure |
| **Excel** | `.xlsx`, `.xls` | Data analysis, metric identification, threshold detection, statistical analysis |
| **CSV** | `.csv` | Data extraction, table analysis, metric identification |
| **Images** | `.png`, `.jpg`, `.jpeg`, `.tiff`, `.bmp` | Superior OCR, chart/graph detection, visual element analysis |

## Usage Examples

### Example 1: ESG Policy Compliance

1. **Upload ESG policy document:**
```bash
curl -X POST http://localhost:5000/analyze-document-policy \
  -F "file=@esg_policy.pdf" \
  -F "domain_hint=esg"
```

2. **Check company ESG data:**
```bash
curl -X POST http://localhost:5000/check-compliance \
  -H "Content-Type: application/json" \
  -d '{
    "policy_checks": [...], 
    "data": {
      "carbon_emissions": 42.5,
      "renewable_energy_percentage": 65,
      "diversity_score": 82,
      "governance_rating": "A"
    }
  }'
```

### Example 2: Financial Risk Assessment

1. **Analyze financial policy:**
```bash
curl -X POST http://localhost:5000/analyze-policy \
  -H "Content-Type: application/json" \
  -d '{
    "policy_text": "Credit applications require: debt-to-income ratio < 40%, credit score >= 650, liquid assets >= 6 months expenses",
    "domain_hint": "financial"
  }'
```

2. **Check loan application:**
```bash
curl -X POST http://localhost:5000/check-compliance \
  -H "Content-Type: application/json" \
  -d '{
    "policy_checks": [...],
    "data": {
      "debt_to_income_ratio": 35.5,
      "credit_score": 720,
      "liquid_assets_months": 8.2,
      "annual_income": 85000
    }
  }'
```

### Example 3: Operational KPI Monitoring

1. **Upload operational dashboard (Excel):**
```bash
curl -X POST http://localhost:5000/upload-document \
  -F "file=@operational_kpis.xlsx" \
  -F "domain_hint=operational"
```

2. **Extract visual metrics from charts:**
The system automatically extracts thresholds and targets from charts and tables.

## Advanced Features

### Multi-Step Analysis

For complex policies requiring sequential analysis:

```json
{
  "check_type": "comprehensive_risk_assessment",
  "complexity": "multi_step",
  "analysis_steps": [
    "Analyze financial metrics",
    "Assess market conditions", 
    "Evaluate operational risks",
    "Generate final recommendation"
  ]
}
```

### Comparative Analysis

For benchmarking against industry standards:

```json
{
  "check_type": "industry_benchmark_comparison",
  "complexity": "comparative",
  "benchmarks": "Industry average for similar companies"
}
```

### Visual Chart Analysis

The system automatically:
- Detects charts and graphs in documents
- Extracts data points and thresholds
- Identifies trend patterns
- Creates compliance agents for visual metrics

## API Endpoints Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/analyze-policy` | POST | Analyze text-based policy and extract checks |
| `/upload-document` | POST | Process document files with multimodal extraction |
| `/analyze-document-policy` | POST | Complete workflow: upload → extract → preview agents |
| `/check-compliance` | POST | Run compliance checks against policy requirements |
| `/preview-agents` | POST | Preview agents that would be created |
| `/validate-data` | POST | Validate if data is sufficient for policy checks |
| `/domains` | GET | List supported domains and complexity types |
| `/supported-formats` | GET | List supported file formats and capabilities |

## Supported Domains

- **Financial** - Credit assessment, financial ratios, risk analysis
- **ESG** - Environmental, Social, Governance compliance
- **Regulatory** - Legal compliance, audit requirements
- **Risk** - Risk assessment, exposure analysis, stress testing
- **Operational** - Process efficiency, performance metrics, KPIs
- **Market** - Market analysis, competitive positioning
- **Strategic** - Business planning, investment assessment
- **HR** - Human resources, talent management
- **Technology** - IT assessment, cybersecurity, digital transformation
- **Supply Chain** - Vendor assessment, procurement, logistics

## Development

### Code Structure

```
├── app/
│   ├── __init__.py
│   ├── routes.py                 # API endpoints
│   ├── services/
│   │   ├── policy_analyzer.py    # Universal policy analysis
│   │   ├── compliance_checker.py # Compliance orchestration
│   │   └── document_processor.py # Document processing workflow
│   └── parsers/
│       ├── document_parser.py    # Main parser interface
│       └── docling_parser.py     # Docling-powered parsing
├── agents/
│   ├── base_agent.py            # Abstract base agent
│   ├── universal_agent.py       # Universal compliance agent
│   └── agent_factory.py         # Dynamic agent creation
├── tests/
├── requirements.txt
├── app.py                       # Application entry point
└── CLAUDE.md                    # Development documentation
```

### Running Tests

```bash
pytest tests/
```

### Code Quality

```bash
# Format code
black .

# Lint code
flake8 .
```

## Troubleshooting

### Common Issues

1. **Virtual Environment Issues**
   ```bash
   # If virtual environment doesn't activate properly
   deactivate  # if currently in an environment
   rm -rf venv  # remove corrupted environment
   python3 -m venv venv  # recreate
   source venv/bin/activate  # reactivate
   ```

2. **Docling Installation Issues**
   ```bash
   # For dependency conflicts
   pip install --upgrade pip setuptools wheel
   pip install docling docling-core docling-ibm-models --no-cache-dir
   
   # For macOS Apple Silicon
   pip install docling --no-binary=:all: --force-reinstall
   
   # Alternative: Install with conda
   conda install -c conda-forge docling
   ```

3. **Python Version Compatibility**
   ```bash
   # Check Python version
   python --version
   
   # If using wrong Python version
   python3.9 -m venv venv  # specify exact version
   ```

4. **OpenAI API Errors**
   - Verify your API key is correct in `.env`
   - Check your OpenAI account has sufficient credits
   - Ensure you have access to the o3 model
   - Test with a simple request first

5. **Import Errors**
   ```bash
   # If getting module not found errors
   pip list  # check installed packages
   pip install -r requirements.txt --force-reinstall
   
   # For specific docling issues
   python -m pip install --upgrade docling
   ```

6. **File Upload Errors**
   - Check file size limits (adjust if needed)
   - Verify file format is supported
   - Ensure sufficient disk space for temporary files
   - Check file permissions

7. **Memory Issues with Large Documents**
   - Process documents in smaller sections
   - Increase available RAM
   - Use text extraction instead of full multimodal processing
   - Process one document at a time

### Performance Tips

- **Large PDFs**: Use domain hints to focus extraction
- **Complex Documents**: Process incrementally 
- **Batch Processing**: Use preview endpoints to optimize before full analysis
- **Memory Management**: Clear temporary files regularly

### Environment Management

**Deactivating the environment:**
```bash
deactivate
```

**Reactivating the environment later:**
```bash
# Navigate to project directory
cd integrate_policy_checker

# Activate environment
source venv/bin/activate  # macOS/Linux
# OR
venv\Scripts\activate     # Windows
```

**Updating dependencies:**
```bash
pip install -r requirements.txt --upgrade
```

**Exporting current environment:**
```bash
pip freeze > requirements-current.txt
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

[Add your license information here]

## Support

For issues and questions:
- Create an issue in the repository
- Check the troubleshooting section
- Review the API documentation

---

**Note**: This system uses AI models and requires an OpenAI API key. Ensure you have proper API access and understand associated costs before running extensive analyses.