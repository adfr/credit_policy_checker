from flask import Blueprint, request, jsonify, render_template, redirect, url_for
from app.services.policy_analyzer import PolicyAnalyzer
from app.services.compliance_checker import ComplianceChecker
from app.services.document_processor import DocumentProcessor
from agents.agent_factory import AgentFactory
import os
from werkzeug.utils import secure_filename

policy_checker = Blueprint('policy_checker', __name__)

# Configure upload settings
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'doc', 'xlsx', 'xls', 'csv', 'png', 'jpg', 'jpeg', 'tiff', 'bmp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Main workflow route - all paths redirect here
@policy_checker.route('/')
@policy_checker.route('/workflow')
@policy_checker.route('/dashboard')
@policy_checker.route('/upload')
@policy_checker.route('/text-analysis')
@policy_checker.route('/compliance')
def workflow():
    """Single unified workflow for policy compliance checking"""
    return render_template('workflow.html')

# API Routes
@policy_checker.route('/api')
def api_info():
    """API information endpoint"""
    return jsonify({
        'message': 'Policy Checker API',
        'description': 'AI-powered policy analysis and compliance checking system',
        'status': 'active',
        'version': '1.0.0',
        'endpoints': {
            'policy_analysis': {
                'analyze_policy': {
                    'url': '/analyze-policy',
                    'method': 'POST',
                    'description': 'Analyze policy text and extract compliance checks',
                    'parameters': ['policy_text', 'domain_hint (optional)']
                },
                'domains': {
                    'url': '/domains',
                    'method': 'GET',
                    'description': 'Get information about supported domains'
                }
            },
            'compliance_checking': {
                'check_compliance': {
                    'url': '/check-compliance',
                    'method': 'POST',
                    'description': 'Check compliance against policy requirements',
                    'parameters': ['policy_checks', 'data']
                },
                'preview_agents': {
                    'url': '/preview-agents',
                    'method': 'POST',
                    'description': 'Preview what agents would be created for a policy',
                    'parameters': ['policy_checks']
                },
                'validate_data': {
                    'url': '/validate-data',
                    'method': 'POST',
                    'description': 'Validate if provided data is sufficient for policy checks',
                    'parameters': ['policy_checks', 'data']
                }
            },
            'document_processing': {
                'upload_document': {
                    'url': '/upload-document',
                    'method': 'POST',
                    'description': 'Upload and process document files',
                    'parameters': ['file', 'domain_hint (optional)']
                },
                'analyze_document_policy': {
                    'url': '/analyze-document-policy',
                    'method': 'POST',
                    'description': 'Complete workflow: upload document → extract policies → create agents preview',
                    'parameters': ['file', 'domain_hint (optional)']
                },
                'supported_formats': {
                    'url': '/supported-formats',
                    'method': 'GET',
                    'description': 'Get information about supported document formats'
                }
            }
        },
        'usage': {
            'example_curl': 'curl -X GET http://localhost:5000/domains',
            'content_type': 'application/json',
            'cors_enabled': True
        }
    })

@policy_checker.route('/analyze-policy', methods=['POST'])
def analyze_policy():
    """Analyze any type of policy and extract checks"""
    data = request.get_json()
    policy_text = data.get('policy_text')
    domain_hint = data.get('domain_hint')  # Optional domain hint
    
    if not policy_text:
        return jsonify({'error': 'Policy text is required'}), 400
    
    analyzer = PolicyAnalyzer()
    
    # First analyze complexity
    complexity_analysis = analyzer.analyze_policy_complexity(policy_text)
    
    # Extract checks
    checks = analyzer.extract_checks(policy_text, domain_hint)
    
    # Rewrite policy
    rewritten_policy = analyzer.rewrite_policy(policy_text, domain_hint)
    
    return jsonify({
        'checks': checks,
        'rewritten_policy': rewritten_policy,
        'complexity_analysis': complexity_analysis,
        'total_checks_extracted': len(checks)
    })

@policy_checker.route('/domains', methods=['GET'])
def get_domains():
    """Get information about supported domains"""
    factory = AgentFactory()
    return jsonify({
        'supported_domains': factory.get_domain_capabilities(),
        'complexity_types': {
            'simple': 'Single-step analysis with straightforward criteria',
            'quantitative': 'Mathematical calculations, ratios, statistical analysis',
            'comparative': 'Comparison against benchmarks, peers, or standards',
            'multi_step': 'Complex workflow requiring multiple analysis steps'
        }
    })

@policy_checker.route('/check-compliance', methods=['POST'])
def check_compliance():
    """Check compliance against any type of policy requirements"""
    data = request.get_json()
    policy_checks = data.get('policy_checks')
    compliance_data = data.get('data')  # More generic than 'credit_data'
    
    if not policy_checks or not compliance_data:
        return jsonify({'error': 'Policy checks and data are required'}), 400
    
    checker = ComplianceChecker()
    results = checker.check_compliance(policy_checks, compliance_data)
    agent_summary = checker.get_agent_summary(policy_checks)
    analysis = checker.analyze_compliance_results(results)
    
    return jsonify({
        'compliance_results': results,
        'analysis': analysis,
        'agents_created': agent_summary
    })

@policy_checker.route('/preview-agents', methods=['POST'])
def preview_agents():
    """Preview what agents would be created for a policy"""
    data = request.get_json()
    policy_checks = data.get('policy_checks')
    
    if not policy_checks:
        return jsonify({'error': 'Policy checks are required'}), 400
    
    checker = ComplianceChecker()
    agent_summary = checker.get_agent_summary(policy_checks)
    
    return jsonify({
        'agents_preview': agent_summary,
        'execution_strategy': {
            'total_agents': agent_summary['total_checks'],
            'unique_types': agent_summary['unique_check_types'],
            'estimated_complexity': 'high' if agent_summary['by_complexity'].get('multi_step', 0) > 3 else 'medium' if agent_summary['by_complexity'].get('quantitative', 0) > 5 else 'low'
        }
    })

@policy_checker.route('/validate-data', methods=['POST'])
def validate_data():
    """Validate if provided data is sufficient for policy checks"""
    data = request.get_json()
    policy_checks = data.get('policy_checks')
    available_data = data.get('data')
    
    if not policy_checks or not available_data:
        return jsonify({'error': 'Policy checks and data are required'}), 400
    
    validation_results = []
    missing_fields = []
    
    for check in policy_checks:
        required_fields = check.get('data_fields', [])
        check_missing = []
        
        for field in required_fields:
            if field not in available_data:
                check_missing.append(field)
                if field not in missing_fields:
                    missing_fields.append(field)
        
        validation_results.append({
            'check_type': check.get('check_type'),
            'description': check.get('description'),
            'required_fields': required_fields,
            'missing_fields': check_missing,
            'can_execute': len(check_missing) == 0
        })
    
    executable_checks = [v for v in validation_results if v['can_execute']]
    
    return jsonify({
        'validation_results': validation_results,
        'summary': {
            'total_checks': len(policy_checks),
            'executable_checks': len(executable_checks),
            'blocked_checks': len(policy_checks) - len(executable_checks),
            'missing_fields': missing_fields,
            'readiness_score': len(executable_checks) / len(policy_checks) if policy_checks else 0
        },
        'recommendations': [
            f"Provide data for field: {field}" for field in missing_fields
        ] if missing_fields else ["All required data is available"]
    })

@policy_checker.route('/upload-document', methods=['POST'])
def upload_document():
    """Upload and process document files (PDF, Word, Excel, Images)"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    domain_hint = request.form.get('domain_hint')
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': f'File type not supported. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'}), 400
    
    try:
        # Create uploads directory if it doesn't exist
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        
        # Save file
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        
        # Process document
        processor = DocumentProcessor()
        result = processor.process_document(file_path, domain_hint)
        
        # Clean up uploaded file
        os.remove(file_path)
        
        if result.get('processing_status') == 'success':
            return jsonify({
                'document_analysis': result,
                'extracted_policies': result.get('policy_extraction', {}).get('extracted_policies', []),
                'document_insights': result.get('policy_extraction', {}).get('document_insights', {}),
                'visual_metrics': processor.extract_visual_metrics(result.get('parsed_content', {}))
            })
        else:
            return jsonify({'error': 'Document processing failed', 'details': result}), 500
    
    except Exception as e:
        return jsonify({'error': f'Document processing error: {str(e)}'}), 500

@policy_checker.route('/analyze-document-policy', methods=['POST'])
def analyze_document_policy():
    """Complete workflow: upload document → extract policies → create agents preview"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    domain_hint = request.form.get('domain_hint')
    
    if not allowed_file(file.filename):
        return jsonify({'error': f'File type not supported. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'}), 400
    
    try:
        # Create uploads directory if it doesn't exist
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        
        # Save and process file
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        
        # Process document
        processor = DocumentProcessor()
        doc_result = processor.process_document(file_path, domain_hint)
        
        # Clean up uploaded file
        os.remove(file_path)
        
        if doc_result.get('processing_status') != 'success':
            return jsonify({'error': 'Document processing failed', 'details': doc_result}), 500
        
        # Extract policy checks from document
        extracted_policies = doc_result.get('policy_extraction', {}).get('extracted_policies', [])
        
        if not extracted_policies:
            return jsonify({
                'warning': 'No policies extracted from document',
                'document_analysis': doc_result,
                'suggestions': [
                    'Document may not contain clear policy requirements',
                    'Try providing a domain hint',
                    'Ensure document contains compliance criteria or thresholds'
                ]
            })
        
        # Preview agents that would be created
        checker = ComplianceChecker()
        agent_summary = checker.get_agent_summary(extracted_policies)
        
        # Validate document completeness
        validation = processor.validate_document_completeness(doc_result.get('parsed_content', {}))
        
        return jsonify({
            'document_analysis': doc_result.get('document_summary', {}),
            'extracted_policies': extracted_policies,
            'policy_count': len(extracted_policies),
            'agents_preview': agent_summary,
            'document_validation': validation,
            'ready_for_compliance_check': validation.get('is_complete', False)
        })
    
    except Exception as e:
        return jsonify({'error': f'Document analysis error: {str(e)}'}), 500

@policy_checker.route('/supported-formats', methods=['GET'])
def get_supported_formats():
    """Get information about supported document formats"""
    return jsonify({
        'supported_formats': {
            'documents': ['pdf', 'docx'],
            'spreadsheets': ['xlsx', 'xls', 'csv'],
            'images': ['png', 'jpg', 'jpeg', 'tiff', 'bmp']
        },
        'capabilities': {
            'pdf': 'Text extraction, table detection, image extraction, OCR on embedded images',
            'docx': 'Text extraction, table extraction, image handling',
            'xlsx/xls': 'Data extraction, table analysis, metric identification',
            'csv': 'Data analysis, metric extraction',
            'images': 'OCR text extraction, chart/graph detection, visual element analysis'
        },
        'content_types_extracted': [
            'Text content and policy language',
            'Tables with compliance metrics',
            'Charts and graphs with thresholds',
            'Images with OCR text extraction',
            'Visual compliance indicators'
        ]
    })

# Simplified Workflow API Endpoints
@policy_checker.route('/api/workflow/upload-policy', methods=['POST'])
def workflow_upload_policy():
    """Step 1: Upload policy document and create agents"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    domain_hint = request.form.get('domain_hint')
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': f'File type not supported. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'}), 400
    
    try:
        # Create uploads directory if it doesn't exist
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        
        # Save file
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        
        # Process document to extract policies
        processor = DocumentProcessor()
        doc_result = processor.process_document(file_path, domain_hint)
        
        # Clean up uploaded file
        os.remove(file_path)
        
        if doc_result.get('processing_status') != 'success':
            return jsonify({'error': 'Document processing failed', 'details': doc_result}), 500
        
        # Extract policy checks from document
        extracted_policies = doc_result.get('policy_extraction', {}).get('extracted_policies', [])
        
        if not extracted_policies:
            return jsonify({
                'success': False,
                'error': 'No policies found in document',
                'suggestions': [
                    'Document may not contain clear policy requirements',
                    'Try providing a domain hint',
                    'Ensure document contains compliance criteria or thresholds'
                ]
            })
        
        # Preview agents that would be created
        checker = ComplianceChecker()
        agent_summary = checker.get_agent_summary(extracted_policies)
        
        return jsonify({
            'success': True,
            'policy_document': filename,
            'policies_extracted': len(extracted_policies),
            'agents_created': agent_summary,
            'policy_data': extracted_policies,
            'document_insights': doc_result.get('policy_extraction', {}).get('document_insights', {})
        })
    
    except Exception as e:
        return jsonify({'error': f'Policy processing error: {str(e)}'}), 500

@policy_checker.route('/api/workflow/check-compliance', methods=['POST'])
def workflow_check_compliance():
    """Step 2: Upload document to check and Step 3: Generate compliance report"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    policy_data = request.form.get('policy_data')
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': f'File type not supported. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'}), 400
    
    if not policy_data:
        return jsonify({'error': 'Policy data is required. Please upload a policy document first.'}), 400
    
    try:
        import json
        policy_checks = json.loads(policy_data)
        
        # Create uploads directory if it doesn't exist
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        
        # Save file
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        
        # Process document to extract data
        processor = DocumentProcessor()
        doc_result = processor.process_document(file_path)
        
        # Clean up uploaded file
        os.remove(file_path)
        
        if doc_result.get('processing_status') != 'success':
            return jsonify({'error': 'Document processing failed', 'details': doc_result}), 500
        
        # Extract data for compliance checking
        document_data = doc_result.get('parsed_content', {})
        
        # Run compliance check
        checker = ComplianceChecker()
        compliance_results = checker.check_compliance(policy_checks, document_data)
        analysis = checker.analyze_compliance_results(compliance_results)
        agent_summary = checker.get_agent_summary(policy_checks)
        
        # Calculate compliance metrics
        total_checks = len(compliance_results)
        passed_checks = sum(1 for result in compliance_results if result.get('status') == 'pass')
        compliance_score = (passed_checks / total_checks * 100) if total_checks > 0 else 0
        
        return jsonify({
            'success': True,
            'document_name': filename,
            'compliance_score': round(compliance_score, 1),
            'total_checks': total_checks,
            'passed_checks': passed_checks,
            'failed_checks': total_checks - passed_checks,
            'compliance_results': compliance_results,
            'analysis': analysis,
            'agents_used': agent_summary,
            'recommendations': analysis.get('recommendations', [])
        })
    
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid policy data format'}), 400
    except Exception as e:
        return jsonify({'error': f'Compliance checking error: {str(e)}'}), 500