# Policy Compliance Checker

A sophisticated AI-powered system for analyzing policy documents and checking compliance against them using intelligent document processing and specialized compliance agents.

## Demo

![Policy Compliance Checker Demo](demogif.gif)

*Watch the complete workflow: Upload policy → Extract agents → Select checks → Upload document → Get compliance results*

## Features

### 🔄 **Restart Workflow System**
- **Step 1**: Upload and analyze policy documents to extract compliance checks
- **Step 2**: Review and select specific agents/checks for assessment  
- **Step 3**: Upload documents for compliance assessment with enhanced data extraction
- **Step 4**: Generate comprehensive compliance reports with recommendations

### 🤖 **Intelligent Agents**
- **Domain-specific agents** for different compliance areas (credit, employment, property, etc.)
- **Complexity-aware processing** (simple, quantitative, comparative, multi-step)
- **Confidence scoring** for all assessments and data extractions

### 📄 **Enhanced Document Processing**
- **Multi-format support**: PDF, DOCX, XLSX, images
- **Advanced data extraction**: Financial data, personal info, property details, employment history
- **Context-aware analysis** with confidence scoring
- **Visual element detection** in charts and tables

### ⚖️ **Compliance Assessment**
- **Automated compliance checking** against extracted policies
- **Detailed reasoning** for each assessment decision
- **Risk categorization** and priority scoring
- **Actionable recommendations** for compliance gaps

## Quick Start

### 1. Setup
```bash
# Clone and setup
git clone <repository>
cd integrate_policy_checker
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env and add your OpenAI API key:
# OPENAI_API_KEY=your-api-key-here
```

### 3. Run the Application
```bash
python app.py
```

### 4. Access the Interface
Open your browser and go to:
- **Main Interface**: http://localhost:5000
- **Restart Workflow**: http://localhost:5000/restart

## Usage

### Web Interface Workflow

1. **Upload Policy Document** 📄
   - Upload a PDF or DOCX policy document
   - System extracts compliance checks and creates intelligent agents
   - Review the extracted policies and agent capabilities

2. **Select Agents** 🤖
   - Choose which compliance checks to run
   - See agent capabilities and complexity ratings
   - Select all or specific agents based on your needs

3. **Upload Assessment Document** 📋
   - Upload the document to be assessed for compliance
   - Enhanced processor extracts relevant data with confidence scores
   - Review extracted data completeness

4. **Run Assessment** ⚖️
   - Execute compliance assessment using selected agents
   - Get detailed results with pass/fail status and reasoning
   - Receive actionable recommendations for improvements

### Demo Script

Test the system programmatically:
```bash
python demo_restart_workflow.py
```

## API Endpoints

### Restart Workflow API
- `GET /api/restart-workflow` - Initialize workflow
- `POST /api/upload-policy-document` - Upload and analyze policy
- `POST /api/select-agents` - Select agents for assessment
- `POST /api/upload-assessment-document` - Upload document for assessment
- `POST /api/run-compliance-assessment` - Execute compliance check

## Supported Document Types

### Input Formats
- **PDF**: Text extraction, table detection, OCR
- **DOCX**: Text and table extraction
- **XLSX/XLS**: Data analysis and metrics
- **Images**: OCR text extraction

### Content Types Processed
- Policy documents with compliance requirements
- Financial statements and credit applications
- Employment verification documents
- Property appraisals and valuations
- Any document with structured compliance data

## System Architecture

### Core Components
- **PolicyAnalyzer**: Extracts compliance checks from policy documents
- **EnhancedDocumentProcessor**: Advanced data extraction with confidence scoring
- **ComplianceChecker**: Coordinates agent-based compliance assessment
- **AgentFactory**: Creates domain-specific compliance agents
- **UniversalAgent**: Handles complex multi-domain assessments

### Data Flow
```
Policy Document → PolicyAnalyzer → Compliance Checks → Agent Selection
                                                              ↓
Assessment Document → EnhancedProcessor → Structured Data → ComplianceChecker
                                                              ↓
                                          Selected Agents → Assessment Results
```

## Example Use Cases

### 1. Credit Policy Compliance
- Upload bank credit policy
- Check loan applications against policy requirements
- Verify debt-to-income ratios, credit scores, employment history

### 2. Employment Policy Verification
- Upload HR policy document
- Assess employee records for compliance
- Check background verification, training requirements

### 3. Property Assessment Compliance
- Upload property valuation standards
- Review appraisal documents for compliance
- Verify methodology and comparable sales requirements

## Technical Requirements

- Python 3.8+
- OpenAI API key for AI-powered analysis
- Flask web framework
- Libraries: PyPDF2, python-docx, openpyxl, requests

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For questions, issues, or feature requests, please open an issue on the GitHub repository.