"""
Loan Type Detection Service
Analyzes credit memos and documents to automatically detect loan types and characteristics
"""

from typing import Dict, List, Optional
from agents.base_agent import GeneralAgent
import json
import logging

logger = logging.getLogger(__name__)

class LoanTypeDetector:
    """Detects loan type and characteristics from credit memo content"""

    def __init__(self):
        self.agent = GeneralAgent("loan_type_detector")

    def detect_loan_type(self, document_content: str) -> Dict:
        """
        Analyze document content to detect loan type and characteristics

        Args:
            document_content: Text content of the credit memo/application

        Returns:
            Dictionary with loan type information
        """

        prompt = f"""
        Analyze this credit memo/loan application document and identify the loan type and characteristics.

        Document Content:
        {document_content[:3000]}  # Limit to first 3000 chars for analysis

        Based on the content, determine:

        1. **Primary Loan Type** (choose one):
           - mortgage (any type of home loan)
           - auto (vehicle financing)
           - personal (personal loan/line of credit)
           - credit_card (credit card application)
           - home_equity (HELOC/home equity loan)
           - commercial (business/commercial loan)
           - student (student loan)
           - other

        2. **Mortgage Sub-Type** (if applicable):
           - conventional (traditional mortgage)
           - FHA (FHA-insured loan)
           - VA (VA-guaranteed loan)
           - USDA (USDA rural development)
           - jumbo (high-balance loan)
           - portfolio (bank portfolio loan)
           - unknown

        3. **Property Type** (if real estate related):
           - primary_residence (primary home)
           - investment (rental/investment property)
           - second_home (vacation/second home)
           - commercial_property (commercial real estate)
           - unknown

        4. **Loan Purpose** (if identifiable):
           - purchase (buying property/asset)
           - refinance (refinancing existing loan)
           - cash_out_refinance (cash-out refi)
           - renovation (home improvement)
           - debt_consolidation
           - other
           - unknown

        5. **Special Characteristics** (multiple possible):
           - first_time_buyer
           - jumbo_loan (>$766,550 in most areas)
           - low_down_payment (<10%)
           - high_ltv (>80%)
           - non_qm (non-qualified mortgage)
           - construction_loan
           - bridge_loan
           - none

        6. **Risk Indicators** (multiple possible):
           - high_dti (>43%)
           - low_credit_score (<620)
           - limited_documentation
           - self_employed_borrower
           - multiple_properties
           - recent_credit_events
           - none

        Look for specific keywords and phrases like:
        - Loan type mentions (mortgage, auto loan, personal loan, etc.)
        - Property descriptions (single family, condo, investment, etc.)
        - Program types (FHA, VA, conventional, etc.)
        - Loan amounts and property values
        - Borrower characteristics and employment
        - Credit and income information

        Return ONLY a JSON object in this exact format:
        {{
            "primary_loan_type": "mortgage",
            "mortgage_subtype": "conventional",
            "property_type": "primary_residence",
            "loan_purpose": "purchase",
            "special_characteristics": ["first_time_buyer", "low_down_payment"],
            "risk_indicators": ["high_dti"],
            "confidence": 0.85,
            "reasoning": "Brief explanation of key indicators found",
            "detected_keywords": ["keyword1", "keyword2", "keyword3"]
        }}

        Ensure confidence is between 0.0 and 1.0 based on clarity of indicators.
        """

        try:
            logger.info("Sending loan type detection request to LLM...")
            response = self.agent.process(prompt)

            # Parse the JSON response
            result = json.loads(response)

            # Validate required fields
            required_fields = ['primary_loan_type', 'confidence']
            for field in required_fields:
                if field not in result:
                    result[field] = 'unknown' if field != 'confidence' else 0.5

            # Ensure confidence is valid
            if not isinstance(result.get('confidence'), (int, float)):
                result['confidence'] = 0.5
            else:
                result['confidence'] = max(0.0, min(1.0, float(result['confidence'])))

            logger.info(f"Detected loan type: {result.get('primary_loan_type')} with confidence {result.get('confidence')}")

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse loan type detection response: {str(e)}")
            return self._get_fallback_detection()

        except Exception as e:
            logger.error(f"Error in loan type detection: {str(e)}")
            return self._get_fallback_detection()

    def _get_fallback_detection(self) -> Dict:
        """Return a fallback detection result when analysis fails"""
        return {
            "primary_loan_type": "unknown",
            "mortgage_subtype": "unknown",
            "property_type": "unknown",
            "loan_purpose": "unknown",
            "special_characteristics": [],
            "risk_indicators": [],
            "confidence": 0.3,
            "reasoning": "Automatic detection failed, manual classification recommended",
            "detected_keywords": []
        }

    def get_applicable_product_filters(self, loan_detection: Dict) -> List[str]:
        """
        Convert loan type detection to applicable_products filter list

        Args:
            loan_detection: Result from detect_loan_type()

        Returns:
            List of applicable_products to filter agents
        """
        filters = []

        # Always include universal agents
        filters.extend(["all", "universal"])

        # Add primary loan type
        primary_type = loan_detection.get('primary_loan_type', 'unknown')
        if primary_type != 'unknown':
            filters.append(primary_type)

        # Add mortgage-specific filters
        if primary_type == 'mortgage':
            mortgage_subtype = loan_detection.get('mortgage_subtype', 'unknown')
            if mortgage_subtype != 'unknown':
                filters.append(mortgage_subtype)

            # Add property type filters for mortgages
            property_type = loan_detection.get('property_type', 'unknown')
            if property_type != 'unknown':
                filters.append(property_type)

        # Add special characteristic filters
        special_chars = loan_detection.get('special_characteristics', [])
        filters.extend(special_chars)

        logger.info(f"Generated applicable product filters: {filters}")
        return filters

    def get_relevance_score(self, agent: Dict, loan_detection: Dict) -> float:
        """
        Calculate relevance score for an agent based on loan detection

        Args:
            agent: Agent configuration dictionary
            loan_detection: Result from detect_loan_type()

        Returns:
            Relevance score between 0.0 and 1.0
        """
        score = 0.0

        agent_products = agent.get('applicable_products', [])
        detection_filters = self.get_applicable_product_filters(loan_detection)

        # Base score for universal agents
        if any(prod in ['all', 'universal'] for prod in agent_products):
            score += 0.3

        # Score for matching primary loan type
        primary_type = loan_detection.get('primary_loan_type', 'unknown')
        if primary_type in agent_products:
            score += 0.4

        # Score for matching mortgage subtype
        if primary_type == 'mortgage':
            mortgage_subtype = loan_detection.get('mortgage_subtype', 'unknown')
            if mortgage_subtype in agent_products:
                score += 0.3

        # Score for property type match
        property_type = loan_detection.get('property_type', 'unknown')
        if property_type in agent_products:
            score += 0.2

        # Score for special characteristics
        special_chars = loan_detection.get('special_characteristics', [])
        for char in special_chars:
            if char in agent_products:
                score += 0.1

        # Priority boost
        priority_boost = {
            'critical': 0.2,
            'high': 0.1,
            'medium': 0.05,
            'low': 0.0
        }
        agent_priority = agent.get('priority', 'medium')
        score += priority_boost.get(agent_priority, 0.0)

        # Cap at 1.0
        return min(1.0, score)