# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Status

This is a newly initialized project directory. The codebase structure and development commands will be documented here as the project evolves.

## Development Setup

- Python Flask web application with universal agent system
- Uses OpenAI o3 model for AI-powered policy analysis and compliance checking
- Environment variables required: OPENAI_API_KEY, SECRET_KEY

## Architecture

Universal document policy checker for ANY type of compliance assessment (ESG, financial, regulatory, risk, operational, etc.):

**Core Components:**
- `PolicyAnalyzer`: Universal policy analysis that extracts checks from any domain (ESG, financial, regulatory, etc.)
- `ComplianceChecker`: Orchestrates compliance checking with intelligent result analysis
- `AgentFactory`: Creates universal agents dynamically based on domain detection and complexity analysis
- `UniversalAgent`: Handles any type of check with domain expertise and multiple analysis approaches

**Agent System:**
- `BaseAgent`: Abstract base with o3 model integration
- `UniversalAgent`: Adapts to any domain/complexity with 4 analysis modes:
  - Simple: Single-step straightforward analysis
  - Quantitative: Mathematical calculations, ratios, statistical analysis
  - Comparative: Benchmarking against industry standards/peers
  - Multi-step: Complex workflows with sequential analysis steps

**Supported Domains:**
Financial, ESG, Regulatory, Risk, Operational, Market, Strategic, HR, Technology, Supply Chain, General

**API Endpoints:**
- `/analyze-policy`: Analyzes text-based policies and extracts domain-specific checks
- `/upload-document`: Processes any document format (PDF, Word, Excel, Images) with multimodal content extraction
- `/analyze-document-policy`: Complete workflow from document upload to policy extraction to agent preview
- `/check-compliance`: Universal compliance checking across all domains
- `/preview-agents`: Shows what agents would be created before execution
- `/validate-data`: Validates if available data is sufficient for policy checks
- `/domains`: Lists supported domains and complexity types
- `/supported-formats`: Lists supported document formats and capabilities

**Document Processing Capabilities (Powered by Docling):**
- **PDF**: Advanced text extraction, precise table structure recognition, image extraction with OCR, chart analysis, document structure detection
- **Word (DOCX)**: Text extraction, table extraction, image handling, document structure analysis
- **Excel/CSV**: Data extraction, table analysis, metric identification, threshold detection, statistical analysis
- **Images**: Superior OCR capabilities, chart/graph detection, visual element analysis, multimodal understanding
- **Multimodal**: Combines text, tables, images, and charts for comprehensive policy extraction

**Data Flow:**
1. **Text Input**: Policy text → PolicyAnalyzer → Domain detection → Structured checks extraction
2. **Document Input**: Any file format → DocumentParser → Multimodal content extraction → PolicyProcessor → Universal policy extraction
3. **Compliance Check**: Data + Policy checks → ComplianceChecker → Universal agents creation → Domain-specific validation → Comprehensive analysis

**Multimodal Processing (Docling-Enhanced):**
- Superior text extraction with document structure understanding
- Advanced table structure recognition with cell-level analysis
- Intelligent image and chart processing with context awareness
- High-accuracy OCR for scanned and mixed-content documents
- Automatic figure and chart classification
- Policy-aware content extraction across all media types
- Document layout analysis for better content understanding

## Common Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your API keys

# Run development server
python app.py

# Run tests
pytest tests/

# Code formatting
black .

# Linting
flake8 .
```