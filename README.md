# Policy Compliance Checker

A sophisticated AI-powered system for analyzing policy documents and checking compliance against them using intelligent document processing and specialized compliance agents.

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

## Technical Implementation: Agent Generation

### 1. Agent Architecture

The system uses a sophisticated agent-based architecture for policy compliance checking:

#### Base Agent Framework
- **BaseAgent** (abstract class): Foundation for all compliance agents
  - Integrates OpenAI API for LLM-powered reasoning
  - Defines standard interface with abstract `check()` method
  - Handles error responses and JSON formatting
  - Provides consistent structure for all agent types

#### Agent Factory Pattern
- **AgentFactory**: Intelligent agent creation based on policy requirements
  - **Domain Detection**: Automatically identifies domain (financial, ESG, regulatory, etc.) from 11 supported categories
  - **Complexity Assessment**: Determines analysis complexity (simple, quantitative, comparative, multi-step)
  - **Agent Selection**: Chooses between specialized agents, universal agents, or hybrid graph+LLM agents
  - **Keyword-Based Routing**: Uses domain-specific keywords for accurate agent assignment

### 2. Agent Types

#### Domain-Specific Policy Agents
1. **ThresholdAgent**: Numeric limit verification
   - Handles ratios, percentages, and numeric thresholds (e.g., LTV ≤ 80%, FICO ≥ 620)
   - Supports minimum, maximum, exact, and range comparisons
   - Performs calculations with unit conversions

2. **CriteriaAgent**: Categorical requirement checking
   - Verifies yes/no conditions (e.g., 2 years employment history)
   - Validates documentation requirements
   - Handles exceptions and alternative evidence

3. **ScoreAgent**: Scoring model implementation
   - Calculates weighted scores based on multiple factors
   - Normalizes values across different scales
   - Provides detailed score breakdowns

4. **QualitativeAgent**: Subjective assessment handling
   - Performs judgment-based evaluations
   - Considers compensating factors
   - Flags items for human review

#### Universal Agent
- Adapts to any policy type across all domains
- Self-determines analysis approach based on requirement complexity
- Generates analysis steps dynamically for complex multi-step checks

#### Hybrid Agents
- Combines Neo4j graph database with LLM reasoning
- Retrieves structured requirements from knowledge graph
- Uses graph for authoritative rules, LLM for edge cases and interpretation
- Particularly effective for credit and financial domains

### 3. Agent Generation Process

#### Step 1: Policy Document Analysis
```python
# PolicyAgentExtractor extracts agents from policy documents
1. Smart Document Chunking:
   - Token-aware splitting (target: 400 tokens per chunk)
   - Preserves logical boundaries and context
   - Handles multi-section policy documents

2. LLM-Powered Extraction:
   - Analyzes each chunk to identify compliance requirements
   - Categorizes into appropriate agent types
   - Extracts structured metadata for each agent
```

#### Step 2: Agent Configuration
Each generated agent includes:
```json
{
    "agent_id": "unique_identifier",
    "agent_name": "descriptive_name",
    "description": "what needs to be checked",
    "requirement": "exact policy requirement text",
    "data_fields": ["required", "data", "fields"],
    "priority": "critical/high/medium/low",
    "applicable_products": ["relevant products"],
    "exceptions": ["documented exceptions"]
}
```

Additional type-specific fields:
- **Threshold**: `threshold_value`, `threshold_type`, `unit`, `calculation`
- **Criteria**: `criteria_type`, `expected_value`, `verification_method`
- **Score**: `scoring_factors`, `scoring_weights`, `score_range`
- **Qualitative**: `assessment_criteria`, `evaluation_guidelines`

#### Step 3: Agent Instantiation
```python
# AgentFactory creates appropriate agent instances
agent = AgentFactory.create_agent(
    agent_config=extracted_config,
    domain=detected_domain,
    complexity=assessed_complexity
)
```

### 4. Compliance Checking Workflow

1. **Parallel Processing**: Agents run concurrently using ThreadPoolExecutor
2. **Data Extraction**: Each agent extracts required fields from documents
3. **Analysis Execution**: Agents perform their specific checks
4. **Result Aggregation**: Individual results combined into comprehensive assessment
5. **Decision Generation**: Overall compliance determination with reasoning

### 5. Key Design Patterns

- **Factory Pattern**: Centralized agent creation logic
- **Template Method**: Base class defines structure, subclasses implement specifics
- **Strategy Pattern**: Different analysis strategies based on complexity
- **Adapter Pattern**: Hybrid agents bridge graph database and LLM capabilities
- **Observer Pattern**: Progress tracking and result notification

### 6. Extensibility

The system is designed for easy extension:

```python
# Add new agent type
class CustomAgent(BaseAgent):
    def check(self, data, requirement):
        # Implement custom checking logic
        pass

# Register with factory
AgentFactory.register_agent_type('custom', CustomAgent)

# Add new domain
DOMAIN_KEYWORDS['new_domain'] = ['keyword1', 'keyword2']
```

### 7. Performance Optimizations

- **Concurrent Processing**: Multiple agents run in parallel
- **Smart Chunking**: Optimal document splitting for LLM processing
- **Caching**: Results cached for repeated checks
- **Batch Processing**: Multiple documents processed efficiently
- **Resource Management**: Automatic scaling based on workload

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