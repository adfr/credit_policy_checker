from typing import Dict, List, Optional
from agents.base_agent import GeneralAgent
from .agent_storage_service import AgentStorageService
import json
import tiktoken
import logging
import os
import re

# Set up logging for policy agent extraction
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)

# Configure logging to both file and console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'{log_dir}/policy_extraction.log'),
        logging.StreamHandler()  # Console output
    ]
)
logger = logging.getLogger(__name__)

class PolicyAgentExtractor:
    """Extracts policy information from documents and generates compliance agents"""
    
    def __init__(self):
        self.agent = GeneralAgent("policy_agent_extractor")
        self.max_tokens = 500  # Reduced for smaller, more focused chunks
        self.min_chunk_tokens = 200  # Minimum meaningful chunk size
        self.encoding = tiktoken.encoding_for_model("gpt-4")
        self.storage_service = AgentStorageService()
    
    def _count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        return len(self.encoding.encode(text))
    
    def _smart_chunk_document(self, text: str, target_chunk_tokens: int = 400) -> List[str]:
        """
        Split document into smaller, smarter chunks based on content structure
        Focuses on policy sections, requirements, and logical breaks
        """
        logger.info(f"Starting smart chunking with target size: {target_chunk_tokens} tokens")
        
        # First, try to identify major sections
        sections = self._identify_policy_sections(text)
        
        if sections:
            logger.info(f"Identified {len(sections)} major policy sections")
            chunks = []
            
            for i, section in enumerate(sections):
                section_tokens = self._count_tokens(section)
                logger.info(f"Section {i+1}: {section_tokens} tokens")
                
                if section_tokens <= target_chunk_tokens:
                    # Section fits in one chunk
                    chunks.append(section)
                else:
                    # Break section into smaller chunks
                    sub_chunks = self._chunk_by_content_breaks(section, target_chunk_tokens)
                    chunks.extend(sub_chunks)
                    logger.info(f"Section {i+1} split into {len(sub_chunks)} sub-chunks")
        else:
            # Fallback to content-based chunking
            logger.info("No clear sections found, using content-based chunking")
            chunks = self._chunk_by_content_breaks(text, target_chunk_tokens)
        
        # Filter out very small chunks and merge them
        final_chunks = self._merge_small_chunks(chunks)
        
        logger.info(f"Final chunking result: {len(final_chunks)} chunks")
        for i, chunk in enumerate(final_chunks):
            chunk_tokens = self._count_tokens(chunk)
            logger.info(f"Chunk {i+1}: {chunk_tokens} tokens")
        
        return final_chunks
    
    def _identify_policy_sections(self, text: str) -> List[str]:
        """
        Identify major policy sections based on headers, numbering, and content patterns
        """
        import re
        
        # Common policy section patterns
        section_patterns = [
            r'\n\s*(\d+\.|\d+\)\s|\([a-z]\)|\([0-9]+\))\s*[A-Z][^.\n]+',  # Numbered sections
            r'\n\s*[A-Z][A-Z\s]+:',  # ALL CAPS headers with colon
            r'\n\s*[A-Z][a-zA-Z\s]+ Requirements?:?',  # Requirements sections
            r'\n\s*[A-Z][a-zA-Z\s]+ Policy:?',  # Policy sections
            r'\n\s*[A-Z][a-zA-Z\s]+ Guidelines?:?',  # Guidelines sections
            r'\n\s*Approval\s+Limits?:?',  # Approval limits
            r'\n\s*Credit\s+Requirements?:?',  # Credit requirements
            r'\n\s*Documentation\s+Requirements?:?',  # Documentation
        ]
        
        # Find all section breaks
        breaks = [0]  # Start of document
        
        for pattern in section_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                breaks.append(match.start())
        
        # Add end of document
        breaks.append(len(text))
        breaks = sorted(set(breaks))  # Remove duplicates and sort
        
        if len(breaks) <= 2:  # Only start and end found
            return []
        
        # Create sections
        sections = []
        for i in range(len(breaks) - 1):
            section = text[breaks[i]:breaks[i+1]].strip()
            if len(section) > 100:  # Ignore very small sections
                sections.append(section)
        
        return sections
    
    def _chunk_by_content_breaks(self, text: str, target_tokens: int) -> List[str]:
        """
        Chunk text by natural content breaks (paragraphs, sentences, lists)
        """
        chunks = []
        
        # Split by double line breaks (paragraphs)
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        current_chunk = ""
        
        for paragraph in paragraphs:
            # Check if adding this paragraph exceeds target
            test_chunk = current_chunk + "\n\n" + paragraph if current_chunk else paragraph
            test_tokens = self._count_tokens(test_chunk)
            
            if test_tokens <= target_tokens:
                current_chunk = test_chunk
            else:
                # Save current chunk if it has meaningful content
                if current_chunk and self._count_tokens(current_chunk) >= self.min_chunk_tokens:
                    chunks.append(current_chunk)
                
                # Check if single paragraph is too large
                para_tokens = self._count_tokens(paragraph)
                if para_tokens > target_tokens:
                    # Split paragraph by sentences or logical breaks
                    sub_chunks = self._split_large_paragraph(paragraph, target_tokens)
                    chunks.extend(sub_chunks)
                    current_chunk = ""
                else:
                    current_chunk = paragraph
        
        # Add final chunk
        if current_chunk and self._count_tokens(current_chunk) >= self.min_chunk_tokens:
            chunks.append(current_chunk)
        
        return chunks
    
    def _split_large_paragraph(self, paragraph: str, target_tokens: int) -> List[str]:
        """
        Split a large paragraph by sentences, bullet points, or other logical breaks
        """
        chunks = []
        
        # Try splitting by bullet points or numbered lists first
        if '•' in paragraph or '- ' in paragraph or re.search(r'\d+\.', paragraph):
            # Split by list items
            items = re.split(r'(?=\s*[•\-]|\s*\d+\.)', paragraph)
            current_chunk = ""
            
            for item in items:
                if not item.strip():
                    continue
                    
                test_chunk = current_chunk + "\n" + item if current_chunk else item
                if self._count_tokens(test_chunk) <= target_tokens:
                    current_chunk = test_chunk
                else:
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = item
            
            if current_chunk:
                chunks.append(current_chunk)
        else:
            # Split by sentences
            sentences = [s.strip() + '.' for s in paragraph.split('.') if s.strip()]
            current_chunk = ""
            
            for sentence in sentences:
                test_chunk = current_chunk + " " + sentence if current_chunk else sentence
                if self._count_tokens(test_chunk) <= target_tokens:
                    current_chunk = test_chunk
                else:
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = sentence
            
            if current_chunk:
                chunks.append(current_chunk)
        
        return chunks
    
    def _merge_small_chunks(self, chunks: List[str]) -> List[str]:
        """
        Merge very small chunks with adjacent ones to ensure meaningful content
        """
        if not chunks:
            return chunks
        
        merged = []
        current_chunk = ""
        
        for chunk in chunks:
            chunk_tokens = self._count_tokens(chunk)
            
            if chunk_tokens < self.min_chunk_tokens:
                # Try to merge with current or previous
                if current_chunk:
                    test_merge = current_chunk + "\n\n" + chunk
                    if self._count_tokens(test_merge) <= self.max_tokens:
                        current_chunk = test_merge
                        continue
                    else:
                        # Save current and start new
                        merged.append(current_chunk)
                        current_chunk = chunk
                else:
                    current_chunk = chunk
            else:
                # Chunk is good size
                if current_chunk:
                    merged.append(current_chunk)
                merged.append(chunk)
                current_chunk = ""
        
        # Add final chunk
        if current_chunk:
            merged.append(current_chunk)
        
        return merged
    
    def _merge_extracted_agents(self, agent_results: List[Dict]) -> Dict:
        """Merge agent results from multiple document chunks"""
        merged = {
            "policy_metadata": {},
            "threshold_agents": [],
            "criteria_agents": [],
            "score_agents": [],
            "qualitative_agents": []
        }
        
        for result in agent_results:
            if 'error' in result:
                continue
                
            # Merge metadata (use first non-empty)
            if not merged["policy_metadata"] and result.get("policy_metadata"):
                merged["policy_metadata"] = result["policy_metadata"]
            
            # Combine all agents
            for agent_type in ["threshold_agents", "criteria_agents", "score_agents", "qualitative_agents"]:
                if agent_type in result:
                    merged[agent_type].extend(result[agent_type])
        
        # Remove duplicates based on agent_id
        for agent_type in ["threshold_agents", "criteria_agents", "score_agents", "qualitative_agents"]:
            seen_ids = set()
            unique_agents = []
            for agent in merged[agent_type]:
                agent_id = agent.get('agent_id', '')
                if agent_id not in seen_ids:
                    seen_ids.add(agent_id)
                    unique_agents.append(agent)
            merged[agent_type] = unique_agents
        
        # Update total count
        total_agents = sum(len(merged[agent_type]) for agent_type in ["threshold_agents", "criteria_agents", "score_agents", "qualitative_agents"])
        merged["policy_metadata"]["total_agents"] = total_agents
        
        return merged
    
    def extract_policy_agents(self, policy_document: str, domain_hint: Optional[str] = None) -> Dict:
        """
        Extract key policy information and generate different types of agents
        
        Args:
            policy_document: The full text content of the policy document
            domain_hint: Optional domain context (e.g., "credit", "lending", "compliance")
            
        Returns:
            Dict containing extracted agents organized by type
        """
        
        logger.info(f"Starting policy agent extraction with domain hint: {domain_hint}")
        
        # Check if document needs chunking
        doc_tokens = self._count_tokens(policy_document)
        logger.info(f"Document has {doc_tokens} tokens, max allowed: {self.max_tokens}")
        
        if doc_tokens > self.max_tokens:
            # Process document in chunks
            logger.info(f"Document too large ({doc_tokens} tokens), splitting into chunks...")
            chunks = self._smart_chunk_document(policy_document)
            logger.info(f"Split into {len(chunks)} chunks")
            
            agent_results = []
            for i, chunk in enumerate(chunks):
                logger.info(f"Processing chunk {i+1}/{len(chunks)}...")
                
                # Log chunk content summary
                chunk_preview = chunk[:200] + "..." if len(chunk) > 200 else chunk
                logger.info(f"Chunk {i+1} content preview: {chunk_preview}")
                logger.info(f"Chunk {i+1} length: {len(chunk)} characters, {self._count_tokens(chunk)} tokens")
                
                chunk_result = self._extract_from_chunk(chunk, domain_hint, i+1, len(chunks))
                if chunk_result and 'error' not in chunk_result:
                    # Log extraction results for this chunk
                    chunk_agents = {
                        'threshold': len(chunk_result.get('threshold_agents', [])),
                        'criteria': len(chunk_result.get('criteria_agents', [])),
                        'score': len(chunk_result.get('score_agents', [])),
                        'qualitative': len(chunk_result.get('qualitative_agents', []))
                    }
                    total_chunk_agents = sum(chunk_agents.values())
                    logger.info(f"Chunk {i+1} extracted {total_chunk_agents} agents: {chunk_agents}")
                    
                    agent_results.append(chunk_result)
                else:
                    error_msg = chunk_result.get('error', 'Unknown error') if chunk_result else 'No result returned'
                    logger.error(f"Chunk {i+1} failed to process: {error_msg}")
            
            if not agent_results:
                logger.error("Failed to extract agents from any document chunks")
                return {
                    "error": "Failed to extract agents from any document chunks",
                    "chunks_processed": len(chunks),
                    "document_tokens": doc_tokens
                }
            
            # Merge results from all chunks
            merged_result = self._merge_extracted_agents(agent_results)
            final_counts = {
                'threshold': len(merged_result.get('threshold_agents', [])),
                'criteria': len(merged_result.get('criteria_agents', [])),
                'score': len(merged_result.get('score_agents', [])),
                'qualitative': len(merged_result.get('qualitative_agents', []))
            }
            total_final_agents = sum(final_counts.values())
            logger.info(f"Final merged result: {total_final_agents} agents: {final_counts}")
            
            return merged_result
        else:
            # Process entire document at once
            logger.info("Processing entire document in single chunk")
            doc_preview = policy_document[:200] + "..." if len(policy_document) > 200 else policy_document
            logger.info(f"Document content preview: {doc_preview}")
            
            result = self._extract_from_chunk(policy_document, domain_hint)
            
            if result and 'error' not in result:
                final_counts = {
                    'threshold': len(result.get('threshold_agents', [])),
                    'criteria': len(result.get('criteria_agents', [])),
                    'score': len(result.get('score_agents', [])),
                    'qualitative': len(result.get('qualitative_agents', []))
                }
                total_agents = sum(final_counts.values())
                logger.info(f"Single chunk extracted {total_agents} agents: {final_counts}")
            
            return result
    
    def _extract_from_chunk(self, text_chunk: str, domain_hint: Optional[str] = None, chunk_num: int = 1, total_chunks: int = 1) -> Dict:
        """Extract agents from a single text chunk"""
        
        chunk_context = f" (Chunk {chunk_num} of {total_chunks})" if total_chunks > 1 else ""
        logger.info(f"Extracting agents from chunk {chunk_num}{chunk_context}")
        
        prompt = f"""
        You are a policy analysis expert. Extract key policy requirements from this document{chunk_context} and create compliance agents.
        
        Domain Context: {domain_hint or "Auto-detect from content"}
        
        Policy Document{chunk_context}:
        {text_chunk}
        
        Extract ALL policy requirements and categorize them into these agent types:
        
        1. **THRESHOLD AGENTS**: Specific numeric limits, ratios, percentages, amounts, approval limits
           - Examples: "LTV must be ≤ 80%", "FICO score ≥ 620", "DTI ratio < 43%", "Max loan amount $500K"
           - Look for: dollar amounts, percentages, ratios, minimums, maximums, approval limits, concentration limits
           - Include: lending limits, exposure limits, collateral requirements, reserve requirements
        
        2. **CRITERIA AGENTS**: Specific conditions that must be met (yes/no, categorical, documentation)
           - Examples: "Must have 2 years employment history", "Property must be owner-occupied", "No bankruptcies in last 7 years"
           - Look for: documentation requirements, eligibility criteria, prohibited conditions, required conditions
           - Include: occupancy requirements, employment criteria, citizenship status, property types
        
        3. **SCORE AGENTS**: Scoring systems, ratings, calculations, risk assessments, pricing
           - Examples: "Risk score calculation", "Credit grade assignment", "Pricing tier determination", "DTI calculation"
           - Look for: mathematical calculations, scoring models, risk assessments, pricing matrices
           - Include: credit scoring, risk rating, pricing adjustments, fee calculations
        
        4. **QUALITATIVE AGENTS**: Subjective assessments requiring human judgment
           - Examples: "Character assessment", "Compensating factors evaluation", "Special circumstances review"
           - Look for: manual reviews, subjective assessments, exception handling, judgment calls
           - Include: underwriter discretion, manual overrides, case-by-case reviews
        
        COMPREHENSIVE SCANNING INSTRUCTIONS:
        - Scan for ALL numeric values (dollars, percentages, ratios, counts, time periods)
        - Look for approval authority limits (who can approve what amounts)
        - Find concentration limits and portfolio restrictions
        - Extract documentation and verification requirements
        - Identify prohibited activities or restricted conditions
        - Look for exception processes and manual review triggers
        - Find pricing and fee structures
        - Extract regulatory compliance requirements
        - Identify monitoring and reporting requirements
        
        For EACH requirement found, extract with these simple fields:
        - agent_id: unique identifier (format: TH{chunk_num:02d}01, CR{chunk_num:02d}01, SC{chunk_num:02d}01, QL{chunk_num:02d}01)
        - agent_name: short descriptive name
        - description: what needs to be checked (1-2 sentences)
        - requirement: exact policy requirement text
        - data_fields: list of data fields needed (e.g., ["credit_score", "income", "employment_history"])
        - priority: critical/high/medium/low
        - applicable_products: which products this applies to (e.g., ["all"], ["conventional"], ["FHA"])
        - exceptions: any noted exceptions (can be empty list)
        
        Return JSON in this simplified format:
        {{
            "policy_metadata": {{
                "document_title": "extracted title",
                "domain": "detected domain",
                "total_agents": "count of all agents in this chunk"
            }},
            "threshold_agents": [
                {{
                    "agent_id": "TH{chunk_num:02d}01",
                    "agent_name": "LTV Ratio Limit",
                    "description": "Verify loan-to-value ratio meets policy limits",
                    "requirement": "LTV must not exceed 80% for conventional loans",
                    "data_fields": ["loan_amount", "property_value"],
                    "priority": "critical",
                    "applicable_products": ["conventional"],
                    "exceptions": ["VA loans may exceed with approval"]
                }},
                {{
                    "agent_id": "TH{chunk_num:02d}02",
                    "agent_name": "Loan Amount Limit",
                    "description": "Check loan amount against approval limits",
                    "requirement": "Loan amount must not exceed $500,000 for conventional loans",
                    "data_fields": ["loan_amount", "loan_type"],
                    "priority": "critical",
                    "applicable_products": ["conventional"],
                    "exceptions": ["Jumbo loans with additional approval"]
                }},
                {{
                    "agent_id": "TH{chunk_num:02d}03",
                    "agent_name": "Approval Authority Limit",
                    "description": "Check if loan amount exceeds approval authority",
                    "requirement": "Loans over $1M require senior management approval",
                    "data_fields": ["loan_amount", "approver_level"],
                    "priority": "critical",
                    "applicable_products": ["all"],
                    "exceptions": []
                }}
            ],
            "criteria_agents": [
                {{
                    "agent_id": "CR{chunk_num:02d}01", 
                    "agent_name": "Employment History",
                    "description": "Verify employment history meets minimum requirements",
                    "requirement": "Must have 2+ years continuous employment",
                    "data_fields": ["employment_history", "employment_length"],
                    "priority": "high",
                    "applicable_products": ["all"],
                    "exceptions": ["Recent graduates with job offer"]
                }},
                {{
                    "agent_id": "CR{chunk_num:02d}02",
                    "agent_name": "Income Documentation",
                    "description": "Verify required income documentation is provided",
                    "requirement": "Must provide 2 years tax returns and recent pay stubs",
                    "data_fields": ["tax_returns", "pay_stubs", "income_documentation"],
                    "priority": "high",
                    "applicable_products": ["all"],
                    "exceptions": ["Bank statement programs"]
                }}
            ],
            "score_agents": [
                {{
                    "agent_id": "SC{chunk_num:02d}01",
                    "agent_name": "DTI Calculation",
                    "description": "Calculate debt-to-income ratio",
                    "requirement": "DTI ratio must be calculated and assessed",
                    "data_fields": ["monthly_income", "monthly_debts", "proposed_payment"],
                    "priority": "critical",
                    "applicable_products": ["all"],
                    "exceptions": []
                }},
                {{
                    "agent_id": "SC{chunk_num:02d}02",
                    "agent_name": "Risk Score Assessment",
                    "description": "Calculate overall borrower risk score",
                    "requirement": "Risk score must be calculated using credit, income, and collateral factors",
                    "data_fields": ["credit_score", "income", "ltv_ratio", "dti_ratio"],
                    "priority": "critical",
                    "applicable_products": ["all"],
                    "exceptions": []
                }}
            ],
            "qualitative_agents": [
                {{
                    "agent_id": "QL{chunk_num:02d}01",
                    "agent_name": "Credit History Review",
                    "description": "Review overall credit history and patterns",
                    "requirement": "Assess borrower creditworthiness and payment patterns",
                    "data_fields": ["credit_report", "payment_history"],
                    "priority": "medium",
                    "applicable_products": ["all"],
                    "exceptions": []
                }},
                {{
                    "agent_id": "QL{chunk_num:02d}02",
                    "agent_name": "Compensating Factors",
                    "description": "Evaluate compensating factors for marginal applications",
                    "requirement": "Consider compensating factors for applications that don't meet standard criteria",
                    "data_fields": ["assets", "employment_stability", "payment_history"],
                    "priority": "medium",
                    "applicable_products": ["all"],
                    "exceptions": []
                }}
            ]
        }}
        
        EXTRACTION REQUIREMENTS:
        1. Be EXTREMELY COMPREHENSIVE - extract EVERY numeric limit, requirement, condition, and policy rule
        2. Look specifically for: approval limits, dollar amounts, percentages, time periods, ratios, scores, grades
        3. Create separate agents for each distinct requirement - don't combine multiple rules
        4. Pay special attention to: lending limits, concentration limits, approval authority, documentation requirements
        5. Include quantitative thresholds even if they seem minor
        6. Look for fee structures, pricing rules, and calculation methods
        7. Extract ALL requirements found - no minimum or maximum limits
        
        Return only valid JSON, no other text.
        """
        
        try:
            logger.info(f"Sending chunk {chunk_num} to LLM for agent extraction...")
            response = self.agent.process(prompt)
            
            # Parse the response
            result = json.loads(response)
            
            # Log the extracted agents in detail
            if 'threshold_agents' in result:
                logger.info(f"Chunk {chunk_num} - Threshold agents extracted:")
                for agent in result['threshold_agents']:
                    logger.info(f"  - {agent.get('agent_name', 'Unknown')}: {agent.get('requirement', 'No requirement')}")
            
            if 'criteria_agents' in result:
                logger.info(f"Chunk {chunk_num} - Criteria agents extracted:")
                for agent in result['criteria_agents']:
                    logger.info(f"  - {agent.get('agent_name', 'Unknown')}: {agent.get('requirement', 'No requirement')}")
            
            if 'score_agents' in result:
                logger.info(f"Chunk {chunk_num} - Score agents extracted:")
                for agent in result['score_agents']:
                    logger.info(f"  - {agent.get('agent_name', 'Unknown')}: {agent.get('requirement', 'No requirement')}")
            
            if 'qualitative_agents' in result:
                logger.info(f"Chunk {chunk_num} - Qualitative agents extracted:")
                for agent in result['qualitative_agents']:
                    logger.info(f"  - {agent.get('agent_name', 'Unknown')}: {agent.get('requirement', 'No requirement')}")
            
            return result
            
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse LLM response: {str(e)}"
            logger.error(f"Chunk {chunk_num} - {error_msg}")
            logger.error(f"Chunk {chunk_num} - Raw response (first 500 chars): {response[:500] if 'response' in locals() else 'No response'}")
            return {
                "error": error_msg,
                "raw_response": response[:500] if 'response' in locals() else "No response"
            }
        except Exception as e:
            error_msg = f"Failed to extract policy agents: {str(e)}"
            logger.error(f"Chunk {chunk_num} - {error_msg}")
            return {
                "error": error_msg
            }
    
    def refine_agents(self, extracted_agents: Dict, user_feedback: Dict) -> Dict:
        """
        Refine extracted agents based on user feedback
        
        Args:
            extracted_agents: Initially extracted agents
            user_feedback: User corrections and modifications
            
        Returns:
            Refined agents dictionary
        """
        
        prompt = f"""
        Refine these extracted policy agents based on user feedback:
        
        Original Agents:
        {json.dumps(extracted_agents, indent=2)}
        
        User Feedback:
        {json.dumps(user_feedback, indent=2)}
        
        Apply the user feedback to improve the agents:
        1. Fix any incorrect extractions
        2. Add missing requirements the user identified
        3. Modify thresholds or criteria as specified
        4. Adjust priorities and applicability
        5. Correct data field requirements
        
        Return the refined agents in the same JSON format as the original.
        Ensure the response is valid JSON starting with {{ and ending with }}.
        """
        
        try:
            response = self.agent.process(prompt)
            
            # Handle case where response is already a JSON error string
            if isinstance(response, str) and response.strip().startswith('{"passed": false'):
                # This is an error response from the base agent
                return {
                    "error": "LLM service error occurred during agent refinement",
                    "original": extracted_agents,
                    "details": "OpenAI API may be unavailable or rate limited"
                }
            
            # Handle empty or None response
            if not response or not response.strip():
                return {
                    "error": "Empty response from LLM during agent refinement", 
                    "original": extracted_agents
                }
            
            # Try to parse the response
            parsed_response = json.loads(response)
            
            # Validate that the response has the expected structure
            expected_keys = ["threshold_agents", "criteria_agents", "score_agents", "qualitative_agents"]
            if not all(key in parsed_response for key in expected_keys):
                # If structure is invalid, return original with minor modifications
                refined = extracted_agents.copy()
                
                # Apply simple feedback if provided
                if user_feedback.get("add_requirements"):
                    # Add the feedback as metadata
                    if "policy_metadata" not in refined:
                        refined["policy_metadata"] = {}
                    refined["policy_metadata"]["user_feedback"] = user_feedback.get("add_requirements")
                
                return refined
            
            return parsed_response
            
        except json.JSONDecodeError as e:
            return {
                "error": f"Failed to parse refinement response: {str(e)}",
                "original": extracted_agents,
                "fallback_applied": True
            }
        except Exception as e:
            return {
                "error": f"Unexpected error during agent refinement: {str(e)}",
                "original": extracted_agents
            }
    
    def validate_agents(self, agents: Dict) -> Dict:
        """
        Validate the extracted agents for completeness and consistency
        
        Args:
            agents: Dictionary of extracted agents
            
        Returns:
            Validation results with suggestions for improvement
        """
        
        validation_results = {
            "is_valid": True,
            "warnings": [],
            "errors": [],
            "suggestions": [],
            "agent_counts": {
                "threshold": len(agents.get("threshold_agents", [])),
                "criteria": len(agents.get("criteria_agents", [])), 
                "score": len(agents.get("score_agents", [])),
                "qualitative": len(agents.get("qualitative_agents", []))
            }
        }
        
        # Check for required fields in each agent type
        for agent_type in ["threshold_agents", "criteria_agents", "score_agents", "qualitative_agents"]:
            agents_list = agents.get(agent_type, [])
            
            for i, agent in enumerate(agents_list):
                agent_id = agent.get("agent_id", f"{agent_type}_{i}")
                
                # Check required fields (simplified structure)
                required_fields = ["agent_id", "agent_name", "description", "requirement", "data_fields", "priority"]
                for field in required_fields:
                    if not agent.get(field):
                        validation_results["errors"].append(f"Agent {agent_id} missing required field: {field}")
                        validation_results["is_valid"] = False
                
                # Basic validations for data quality
                if isinstance(agent.get("data_fields"), list) and len(agent.get("data_fields", [])) == 0:
                    validation_results["warnings"].append(f"Agent {agent_id} has empty data_fields list")
                
                if agent.get("priority") not in ["critical", "high", "medium", "low"]:
                    validation_results["warnings"].append(f"Agent {agent_id} has invalid priority: {agent.get('priority')}")
        
        # Check for duplicate agent IDs
        all_ids = []
        for agent_type in ["threshold_agents", "criteria_agents", "score_agents", "qualitative_agents"]:
            for agent in agents.get(agent_type, []):
                agent_id = agent.get("agent_id")
                if agent_id in all_ids:
                    validation_results["errors"].append(f"Duplicate agent ID found: {agent_id}")
                    validation_results["is_valid"] = False
                all_ids.append(agent_id)
        
        # Suggestions for improvement
        total_agents = sum(validation_results["agent_counts"].values())
        if total_agents < 8:
            validation_results["suggestions"].append("Low agent count - consider extracting more policy requirements")
        
        if validation_results["agent_counts"]["threshold"] == 0:
            validation_results["suggestions"].append("No threshold agents found - check for numeric limits, percentages, or ratios")
        
        if validation_results["agent_counts"]["criteria"] == 0:
            validation_results["suggestions"].append("No criteria agents found - check for yes/no conditions or categorical requirements")
        
        if total_agents > 50:
            validation_results["suggestions"].append("High agent count - consider consolidating similar requirements")
        
        return validation_results
    
    def save_extracted_agents(self, policy_name: str, agents: Dict, metadata: Optional[Dict] = None) -> Dict:
        """
        Save extracted agents to JSON file storage
        
        Args:
            policy_name: Name of the policy document
            agents: Dictionary containing extracted agents
            metadata: Optional metadata about the policy
            
        Returns:
            Dictionary with save results
        """
        try:
            # Prepare metadata with additional info
            save_metadata = {
                "extraction_method": "LLM-based policy agent extraction",
                "extractor_version": "1.0",
                "total_agents": sum(len(agents.get(agent_type, [])) for agent_type in ["threshold_agents", "criteria_agents", "score_agents", "qualitative_agents"])
            }
            
            # Merge with provided metadata
            if metadata:
                save_metadata.update(metadata)
            
            # Save using storage service
            result = self.storage_service.save_agents(policy_name, agents, save_metadata)
            
            if result.get("success"):
                logger.info(f"Successfully saved {result['agent_counts']['total']} agents for policy '{policy_name}' with ID {result['policy_id']}")
            else:
                logger.error(f"Failed to save agents for policy '{policy_name}': {result.get('error', 'Unknown error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Exception while saving agents for policy '{policy_name}': {str(e)}")
            return {"success": False, "error": str(e)}
    
    def load_saved_agents(self, policy_id: str) -> Optional[Dict]:
        """
        Load saved agents from storage
        
        Args:
            policy_id: Unique policy identifier
            
        Returns:
            Dictionary containing agent data or None if not found
        """
        return self.storage_service.load_agents(policy_id)
    
    def list_saved_policies(self) -> List[Dict]:
        """
        List all saved policies
        
        Returns:
            List of policy summaries
        """
        return self.storage_service.list_policies()
    
    def delete_saved_policy(self, policy_id: str) -> bool:
        """
        Delete a saved policy
        
        Args:
            policy_id: Unique policy identifier
            
        Returns:
            True if successful, False otherwise
        """
        return self.storage_service.delete_policy(policy_id)
    
    def search_saved_agents(self, query: str, agent_type: Optional[str] = None) -> List[Dict]:
        """
        Search for agents across all saved policies
        
        Args:
            query: Search query
            agent_type: Optional filter by agent type
            
        Returns:
            List of matching agents with policy information
        """
        return self.storage_service.search_agents(query, agent_type)