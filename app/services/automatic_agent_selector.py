"""
Automatic Agent Selector Service
Automatically selects relevant agents based on loan type detection
"""

from typing import Dict, List, Optional, Tuple
from .loan_type_detector import LoanTypeDetector
import logging

logger = logging.getLogger(__name__)

class AutomaticAgentSelector:
    """Automatically selects relevant agents based on loan type and characteristics"""

    def __init__(self):
        self.loan_detector = LoanTypeDetector()

        # Minimum relevance score for auto-selection
        self.min_relevance_score = 0.3

        # Maximum number of agents to auto-select
        self.max_auto_selected = 20

    def select_agents_automatically(
        self,
        document_content: str,
        available_agents: Dict,
        min_score: Optional[float] = None,
        max_agents: Optional[int] = None
    ) -> Dict:
        """
        Automatically select relevant agents based on document content

        Args:
            document_content: Text content of the credit memo
            available_agents: Dictionary of all available agents from policy extraction
            min_score: Minimum relevance score (default: 0.3)
            max_agents: Maximum agents to select (default: 20)

        Returns:
            Dictionary with selected agents and selection metadata
        """

        min_score = min_score or self.min_relevance_score
        max_agents = max_agents or self.max_auto_selected

        logger.info("Starting automatic agent selection...")

        try:
            # Step 1: Detect loan type and characteristics
            loan_detection = self.loan_detector.detect_loan_type(document_content)
            logger.info(f"Loan detection completed: {loan_detection.get('primary_loan_type')} "
                       f"(confidence: {loan_detection.get('confidence', 0)})")

            # Step 2: Score and rank all agents
            scored_agents = self._score_all_agents(available_agents, loan_detection)

            # Step 3: Filter agents by minimum score
            relevant_agents = [
                (agent, score, reasoning) for agent, score, reasoning in scored_agents
                if score >= min_score
            ]

            # Step 4: Sort by score (highest first) and apply max limit
            relevant_agents.sort(key=lambda x: x[1], reverse=True)
            if len(relevant_agents) > max_agents:
                relevant_agents = relevant_agents[:max_agents]

            # Step 5: Prepare selected agents list
            selected_agents = [agent for agent, _, _ in relevant_agents]

            # Step 6: Generate selection summary
            selection_metadata = self._generate_selection_metadata(
                loan_detection, scored_agents, relevant_agents, selected_agents
            )

            logger.info(f"Automatic selection complete: {len(selected_agents)} agents selected")

            return {
                'selected_agents': selected_agents,
                'loan_detection': loan_detection,
                'selection_metadata': selection_metadata,
                'total_available': self._count_total_agents(available_agents),
                'total_selected': len(selected_agents),
                'selection_mode': 'automatic'
            }

        except Exception as e:
            logger.error(f"Error in automatic agent selection: {str(e)}")
            return self._get_fallback_selection(available_agents)

    def _score_all_agents(self, available_agents: Dict, loan_detection: Dict) -> List[Tuple]:
        """Score all available agents based on loan detection"""

        scored_agents = []

        for agent_type in ['threshold_agents', 'criteria_agents', 'score_agents', 'qualitative_agents']:
            agents = available_agents.get(agent_type, [])

            for agent in agents:
                score = self.loan_detector.get_relevance_score(agent, loan_detection)
                reasoning = self._generate_selection_reasoning(agent, loan_detection, score)

                scored_agents.append((agent, score, reasoning))

        return scored_agents

    def _generate_selection_reasoning(self, agent: Dict, loan_detection: Dict, score: float) -> str:
        """Generate human-readable reasoning for why an agent was selected"""

        reasons = []

        # Check applicable products match
        agent_products = agent.get('applicable_products', [])
        primary_type = loan_detection.get('primary_loan_type', 'unknown')

        if 'all' in agent_products or 'universal' in agent_products:
            reasons.append("applies to all loan types")

        if primary_type in agent_products:
            reasons.append(f"relevant to {primary_type} loans")

        if primary_type == 'mortgage':
            mortgage_subtype = loan_detection.get('mortgage_subtype', 'unknown')
            if mortgage_subtype in agent_products:
                reasons.append(f"specific to {mortgage_subtype} mortgages")

        # Check property type relevance
        property_type = loan_detection.get('property_type', 'unknown')
        if property_type in agent_products:
            reasons.append(f"applies to {property_type.replace('_', ' ')}")

        # Check special characteristics
        special_chars = loan_detection.get('special_characteristics', [])
        matching_chars = [char for char in special_chars if char in agent_products]
        if matching_chars:
            reasons.append(f"relevant to {', '.join(matching_chars)}")

        # Priority consideration
        priority = agent.get('priority', 'medium')
        if priority in ['critical', 'high']:
            reasons.append(f"{priority} priority requirement")

        if not reasons:
            return f"General applicability (score: {score:.2f})"

        return f"{', '.join(reasons)} (score: {score:.2f})"

    def _generate_selection_metadata(
        self,
        loan_detection: Dict,
        all_scored: List,
        selected: List,
        selected_agents: List
    ) -> Dict:
        """Generate metadata about the selection process"""

        # Calculate score distribution
        all_scores = [score for _, score, _ in all_scored]
        selected_scores = [score for _, score, _ in selected]

        # Count by agent type
        type_counts = {
            'threshold': 0,
            'criteria': 0,
            'score': 0,
            'qualitative': 0
        }

        for agent in selected_agents:
            agent_id = agent.get('agent_id', '')
            if agent_id.startswith('TH'):
                type_counts['threshold'] += 1
            elif agent_id.startswith('CR'):
                type_counts['criteria'] += 1
            elif agent_id.startswith('SC'):
                type_counts['score'] += 1
            elif agent_id.startswith('QL'):
                type_counts['qualitative'] += 1

        # Priority distribution
        priority_counts = {}
        for agent in selected_agents:
            priority = agent.get('priority', 'unknown')
            priority_counts[priority] = priority_counts.get(priority, 0) + 1

        return {
            'loan_type_summary': {
                'primary_type': loan_detection.get('primary_loan_type', 'unknown'),
                'subtype': loan_detection.get('mortgage_subtype', 'unknown'),
                'confidence': loan_detection.get('confidence', 0),
                'key_characteristics': loan_detection.get('special_characteristics', [])
            },
            'selection_stats': {
                'avg_relevance_score': sum(selected_scores) / len(selected_scores) if selected_scores else 0,
                'min_score': min(selected_scores) if selected_scores else 0,
                'max_score': max(selected_scores) if selected_scores else 0,
                'score_range': f"{min(selected_scores):.2f} - {max(selected_scores):.2f}" if selected_scores else "N/A"
            },
            'agent_type_distribution': type_counts,
            'priority_distribution': priority_counts,
            'selection_reasoning': loan_detection.get('reasoning', 'Automatic selection based on loan type analysis'),
            'detected_keywords': loan_detection.get('detected_keywords', [])
        }

    def _count_total_agents(self, available_agents: Dict) -> int:
        """Count total number of available agents"""
        total = 0
        for agent_type in ['threshold_agents', 'criteria_agents', 'score_agents', 'qualitative_agents']:
            total += len(available_agents.get(agent_type, []))
        return total

    def _get_fallback_selection(self, available_agents: Dict) -> Dict:
        """Return fallback selection when automatic detection fails"""

        logger.warning("Using fallback selection due to detection failure")

        # Select high-priority and universal agents as fallback
        fallback_agents = []

        for agent_type in ['threshold_agents', 'criteria_agents', 'score_agents', 'qualitative_agents']:
            agents = available_agents.get(agent_type, [])

            for agent in agents:
                # Include critical/high priority or universal agents
                priority = agent.get('priority', 'medium')
                products = agent.get('applicable_products', [])

                if (priority in ['critical', 'high'] or
                    any(prod in ['all', 'universal'] for prod in products)):
                    fallback_agents.append(agent)

        # Limit fallback selection
        if len(fallback_agents) > self.max_auto_selected:
            fallback_agents = fallback_agents[:self.max_auto_selected]

        return {
            'selected_agents': fallback_agents,
            'loan_detection': {
                'primary_loan_type': 'unknown',
                'confidence': 0.3,
                'reasoning': 'Automatic detection failed'
            },
            'selection_metadata': {
                'loan_type_summary': {
                    'primary_type': 'unknown',
                    'subtype': 'unknown',
                    'confidence': 0.3,
                    'key_characteristics': []
                },
                'selection_stats': {
                    'avg_relevance_score': 0.5,
                    'fallback_mode': True
                },
                'selection_reasoning': 'Fallback selection: high-priority and universal agents only'
            },
            'total_available': self._count_total_agents(available_agents),
            'total_selected': len(fallback_agents),
            'selection_mode': 'automatic_fallback'
        }

    def explain_selection(self, selection_result: Dict) -> str:
        """Generate human-readable explanation of the selection"""

        metadata = selection_result.get('selection_metadata', {})
        loan_summary = metadata.get('loan_type_summary', {})

        explanation = f"""
**Automatic Agent Selection Summary**

**Detected Loan Type:** {loan_summary.get('primary_type', 'unknown').replace('_', ' ').title()}
**Subtype:** {loan_summary.get('subtype', 'unknown').replace('_', ' ').title()}
**Detection Confidence:** {loan_summary.get('confidence', 0):.1%}

**Selected {selection_result.get('total_selected', 0)} out of {selection_result.get('total_available', 0)} available agents:**

**Agent Distribution:**
- Threshold Agents: {metadata.get('agent_type_distribution', {}).get('threshold', 0)}
- Criteria Agents: {metadata.get('agent_type_distribution', {}).get('criteria', 0)}
- Score Agents: {metadata.get('agent_type_distribution', {}).get('score', 0)}
- Qualitative Agents: {metadata.get('agent_type_distribution', {}).get('qualitative', 0)}

**Selection Reasoning:** {metadata.get('selection_reasoning', 'N/A')}

**Key Characteristics Detected:** {', '.join(loan_summary.get('key_characteristics', [])) or 'None'}
        """

        return explanation.strip()