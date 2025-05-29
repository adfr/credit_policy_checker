from typing import Dict, List, Optional
from agents.base_agent import GeneralAgent
import json
import tiktoken

class PolicyAgentExtractor:
    """Extracts policy information from documents and generates compliance agents"""
    
    def __init__(self):
        self.agent = GeneralAgent("policy_agent_extractor")
        self.max_tokens = 6000  # Leave buffer for response
        self.encoding = tiktoken.encoding_for_model("gpt-4")
    
    def _count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        return len(self.encoding.encode(text))
    
    def _chunk_document(self, text: str, max_chunk_tokens: int = 4000) -> List[str]:
        """Split document into chunks that fit within token limits"""
        # Split by paragraphs first
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            # Check if adding this paragraph exceeds the limit
            test_chunk = current_chunk + "\n\n" + paragraph if current_chunk else paragraph
            
            if self._count_tokens(test_chunk) <= max_chunk_tokens:
                current_chunk = test_chunk
            else:
                # Save current chunk if it's not empty
                if current_chunk:
                    chunks.append(current_chunk)
                
                # Check if single paragraph is too large
                if self._count_tokens(paragraph) > max_chunk_tokens:
                    # Split paragraph by sentences
                    sentences = paragraph.split('. ')
                    temp_chunk = ""
                    for sentence in sentences:
                        test_sentence = temp_chunk + ". " + sentence if temp_chunk else sentence
                        if self._count_tokens(test_sentence) <= max_chunk_tokens:
                            temp_chunk = test_sentence
                        else:
                            if temp_chunk:
                                chunks.append(temp_chunk)
                            temp_chunk = sentence
                    if temp_chunk:
                        current_chunk = temp_chunk
                else:
                    current_chunk = paragraph
        
        # Add the last chunk
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
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
        
        # Check if document needs chunking
        doc_tokens = self._count_tokens(policy_document)
        print(f"Document has {doc_tokens} tokens, max allowed: {self.max_tokens}")
        
        if doc_tokens > self.max_tokens:
            # Process document in chunks
            print(f"Document too large ({doc_tokens} tokens), splitting into chunks...")
            chunks = self._chunk_document(policy_document)
            print(f"Split into {len(chunks)} chunks")
            
            agent_results = []
            for i, chunk in enumerate(chunks):
                print(f"Processing chunk {i+1}/{len(chunks)}...")
                chunk_result = self._extract_from_chunk(chunk, domain_hint, i+1, len(chunks))
                if chunk_result and 'error' not in chunk_result:
                    agent_results.append(chunk_result)
                else:
                    print(f"Warning: Chunk {i+1} failed to process: {chunk_result.get('error', 'Unknown error')}")
            
            if not agent_results:
                return {
                    "error": "Failed to extract agents from any document chunks",
                    "chunks_processed": len(chunks),
                    "document_tokens": doc_tokens
                }
            
            # Merge results from all chunks
            return self._merge_extracted_agents(agent_results)
        else:
            # Process entire document at once
            return self._extract_from_chunk(policy_document, domain_hint)
    
    def _extract_from_chunk(self, text_chunk: str, domain_hint: Optional[str] = None, chunk_num: int = 1, total_chunks: int = 1) -> Dict:
        """Extract agents from a single text chunk"""
        
        chunk_context = f" (Chunk {chunk_num} of {total_chunks})" if total_chunks > 1 else ""
        
        prompt = f"""
        You are a policy analysis expert. Extract key policy requirements from this document{chunk_context} and create compliance agents.
        
        Domain Context: {domain_hint or "Auto-detect from content"}
        
        Policy Document{chunk_context}:
        {text_chunk}
        
        Extract ALL policy requirements and categorize them into these agent types:
        
        1. **THRESHOLD AGENTS**: Specific numeric limits, ratios, percentages, amounts
           - Examples: "LTV must be ≤ 80%", "FICO score ≥ 620", "DTI ratio < 43%"
        
        2. **CRITERIA AGENTS**: Specific conditions that must be met (yes/no, categorical)
           - Examples: "Must have 2 years employment history", "Property must be owner-occupied", "No bankruptcies in last 7 years"
        
        3. **SCORE AGENTS**: Scoring systems, ratings, calculations
           - Examples: "Risk score calculation", "Credit grade assignment", "Pricing tier determination"
        
        4. **QUALITATIVE AGENTS**: Subjective assessments requiring human judgment
           - Examples: "Character assessment", "Compensating factors evaluation", "Special circumstances review"
        
        For EACH requirement found, extract:
        - agent_id: unique identifier (use format TH{chunk_num:02d}01, CR{chunk_num:02d}01, etc. - increment 01,02,03 for each agent)
        - agent_name: descriptive name
        - description: what needs to be checked
        - requirement: exact policy requirement
        - data_fields: list of data fields needed from applicant
        - priority: critical/high/medium/low
        - applicable_products: which loan products this applies to
        - exceptions: any noted exceptions or special cases
        
        Return JSON in this exact format:
        {{
            "policy_metadata": {{
                "document_title": "extracted title",
                "domain": "detected domain",
                "effective_date": "if mentioned",
                "chunk_info": "chunk {chunk_num} of {total_chunks}",
                "total_agents": "count of all agents in this chunk"
            }},
            "threshold_agents": [
                {{
                    "agent_id": "TH{chunk_num:02d}01",
                    "agent_name": "LTV Ratio Limit",
                    "description": "Verify loan-to-value ratio meets policy limits",
                    "requirement": "LTV must not exceed 80% for conventional loans",
                    "threshold_value": 80,
                    "threshold_type": "maximum",
                    "unit": "percentage",
                    "data_fields": ["loan_amount", "property_value"],
                    "calculation": "loan_amount / property_value * 100",
                    "priority": "critical",
                    "applicable_products": ["conventional"],
                    "exceptions": ["VA loans may exceed with approval"]
                }}
            ],
            "criteria_agents": [
                {{
                    "agent_id": "CR{chunk_num:02d}01", 
                    "agent_name": "Employment History",
                    "description": "Verify employment history meets minimum requirements",
                    "requirement": "Must have 2+ years continuous employment",
                    "criteria_type": "duration",
                    "expected_value": "2+ years",
                    "data_fields": ["employment_history", "employment_start_date"],
                    "verification_method": "documentation_review",
                    "priority": "high",
                    "applicable_products": ["all"],
                    "exceptions": ["Recent graduates with job offer"]
                }}
            ],
            "score_agents": [
                {{
                    "agent_id": "SC{chunk_num:02d}01",
                    "agent_name": "Credit Risk Score",
                    "description": "Calculate overall credit risk score",
                    "requirement": "Risk score must be calculated using specified factors",
                    "scoring_factors": ["fico_score", "dti_ratio", "ltv_ratio"],
                    "scoring_weights": {{"fico_score": 0.4, "dti_ratio": 0.3, "ltv_ratio": 0.3}},
                    "score_range": [0, 1000],
                    "data_fields": ["fico_score", "dti_ratio", "ltv_ratio"],
                    "priority": "critical",
                    "applicable_products": ["all"],
                    "exceptions": []
                }}
            ],
            "qualitative_agents": [
                {{
                    "agent_id": "QL{chunk_num:02d}01",
                    "agent_name": "Character Assessment",
                    "description": "Evaluate borrower character and reliability",
                    "requirement": "Assess borrower character based on payment history and references",
                    "assessment_criteria": ["payment_history", "references", "explanation_letters"],
                    "evaluation_guidelines": "Look for patterns of responsibility and reliability",
                    "data_fields": ["credit_report", "references", "borrower_statements"],
                    "priority": "medium",
                    "applicable_products": ["all"],
                    "exceptions": []
                }}
            ]
        }}
        
        IMPORTANT: Extract EVERY numeric value, percentage, ratio, and requirement from this text chunk.
        Each should be a separate agent. Be comprehensive and thorough.
        
        Return only valid JSON, no other text.
        """
        
        try:
            response = self.agent.process(prompt)
            return json.loads(response)
        except json.JSONDecodeError as e:
            return {
                "error": f"Failed to parse LLM response: {str(e)}",
                "raw_response": response[:500] if 'response' in locals() else "No response"
            }
        except Exception as e:
            return {
                "error": f"Failed to extract policy agents: {str(e)}"
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
                
                # Check required fields
                required_fields = ["agent_id", "agent_name", "description", "requirement", "data_fields", "priority"]
                for field in required_fields:
                    if not agent.get(field):
                        validation_results["errors"].append(f"Agent {agent_id} missing required field: {field}")
                        validation_results["is_valid"] = False
                
                # Type-specific validations
                if agent_type == "threshold_agents":
                    if not agent.get("threshold_value") and not agent.get("calculation"):
                        validation_results["warnings"].append(f"Threshold agent {agent_id} should have threshold_value or calculation")
                
                elif agent_type == "score_agents":
                    if not agent.get("scoring_factors"):
                        validation_results["warnings"].append(f"Score agent {agent_id} should have scoring_factors")
        
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
        if total_agents < 5:
            validation_results["suggestions"].append("Consider if more policy requirements could be extracted")
        
        if validation_results["agent_counts"]["threshold"] == 0:
            validation_results["suggestions"].append("No threshold agents found - check for numeric limits in the policy")
        
        return validation_results 