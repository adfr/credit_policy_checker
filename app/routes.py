from flask import Blueprint, request, jsonify, render_template, redirect, url_for
from app.services.document_processor import DocumentProcessor
from app.services.policy_agent_extractor import PolicyAgentExtractor
from app.services.agent_compliance_checker import AgentComplianceChecker
import os
import json
from werkzeug.utils import secure_filename

policy_checker = Blueprint('policy_checker', __name__)

# Configure upload settings
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'doc', 'xlsx', 'xls', 'csv', 'png', 'jpg', 'jpeg', 'tiff', 'bmp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Main route - redirect to restart workflow
@policy_checker.route('/')
@policy_checker.route('/restart')
def restart_workflow_page():
    """Serve the restart workflow page as the main interface"""
    return render_template('restart_workflow.html')

# NEW AGENT-BASED API ROUTES

@policy_checker.route('/api/extract-policy-agents', methods=['POST'])
def extract_policy_agents():
    """Extract policy agents from a policy document using LLM"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed'}), 400
        
        # Get optional domain hint
        domain_hint = request.form.get('domain_hint', None)
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        
        # Extract policy agents using the new agentic approach
        document_processor = DocumentProcessor()
        result = document_processor.extract_policy_agents(file_path, domain_hint)
        
        if 'error' in result:
            return jsonify(result), 500
        
        # Add file information to result
        result['file_info'] = {
            'filename': filename,
            'file_path': file_path,
            'domain_hint': domain_hint
        }
        
        return jsonify({
            'success': True,
            'extracted_agents': result['extracted_agents'],
            'validation': result['validation'],
            'document_summary': result['document_summary'],
            'file_info': result['file_info'],
            'agent_counts': result['validation']['agent_counts']
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to extract policy agents: {str(e)}'}), 500

@policy_checker.route('/api/refine-agents', methods=['POST'])
def refine_agents():
    """Refine extracted agents based on user feedback"""
    try:
        data = request.get_json()
        extracted_agents = data.get('extracted_agents', {})
        user_feedback = data.get('user_feedback', {})
        
        if not extracted_agents:
            return jsonify({'error': 'No extracted agents provided'}), 400
        
        # Refine agents using user feedback
        document_processor = DocumentProcessor()
        refined_agents = document_processor.refine_extracted_agents(extracted_agents, user_feedback)
        
        if 'error' in refined_agents:
            return jsonify(refined_agents), 500
        
        # Re-validate refined agents
        agent_extractor = PolicyAgentExtractor()
        validation = agent_extractor.validate_agents(refined_agents)
        
        return jsonify({
            'success': True,
            'refined_agents': refined_agents,
            'validation': validation,
            'agent_counts': validation['agent_counts']
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to refine agents: {str(e)}'}), 500

@policy_checker.route('/api/check-compliance-with-agents', methods=['POST'])
def check_compliance_with_agents():
    """Check document compliance using selected policy agents"""
    try:
        # Get the document file info
        if 'file' not in request.files:
            return jsonify({'error': 'No document file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed'}), 400
        
        # Get selected agents and optional applicant data from form data
        selected_agents_json = request.form.get('selected_agents', '[]')
        applicant_data_json = request.form.get('applicant_data', '{}')
        
        try:
            selected_agents = json.loads(selected_agents_json)
            applicant_data = json.loads(applicant_data_json) if applicant_data_json != '{}' else None
        except json.JSONDecodeError:
            return jsonify({'error': 'Invalid JSON in selected_agents or applicant_data'}), 400
        
        if not selected_agents:
            return jsonify({'error': 'No agents selected for compliance checking'}), 400
        
        # Save uploaded document file
        filename = secure_filename(file.filename)
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        
        # Run compliance check using selected agents
        document_processor = DocumentProcessor()
        result = document_processor.check_document_compliance(file_path, selected_agents, applicant_data)
        
        if 'error' in result:
            return jsonify(result), 500
        
        # Add file information to result
        result['file_info'] = {
            'filename': filename,
            'selected_agents_count': len(selected_agents),
            'applicant_data_provided': bool(applicant_data)
        }
        
        return jsonify({
            'success': True,
            'compliance_results': result['compliance_results'],
            'document_summary': result['document_summary'],
            'selected_agents_summary': result['selected_agents_summary'],
            'file_info': result['file_info']
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to check compliance: {str(e)}'}), 500

@policy_checker.route('/api/get-agent-data-requirements', methods=['POST'])
def get_agent_data_requirements():
    """Get data requirements for selected agents"""
    try:
        data = request.get_json()
        selected_agents = data.get('selected_agents', [])
        
        if not selected_agents:
            return jsonify({'error': 'No agents selected'}), 400
        
        # Get data requirements summary
        document_processor = DocumentProcessor()
        requirements = document_processor.get_agent_data_requirements(selected_agents)
        
        return jsonify({
            'success': True,
            'data_requirements': requirements
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to get data requirements: {str(e)}'}), 500

# EXISTING LEGACY API ROUTES (for backward compatibility)

@policy_checker.route('/api/restart-workflow', methods=['GET'])
def restart_workflow():
    """Reset and restart the compliance checking workflow"""
    return jsonify({
        'message': 'Workflow restarted',
        'status': 'ready',
        'steps': {
            'step1': 'Upload Policy Document',
            'step2': 'Review and Select Agents',
            'step3': 'Upload Assessment Document', 
            'step4': 'Run Compliance Assessment'
        },
        'new_agent_workflow': {
            'step1': 'Extract Policy Agents from Document',
            'step2': 'Review and Select Relevant Agents',
            'step3': 'Check Document Compliance with Selected Agents'
        }
    })