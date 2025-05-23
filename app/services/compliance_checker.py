from typing import List, Dict
from agents.agent_factory import AgentFactory
from app.services.document_classifier import DocumentClassifier

class ComplianceChecker:
    """Universal compliance checker for any type of policy requirements"""
    
    def __init__(self):
        self.agent_factory = AgentFactory()
    
    def check_compliance(self, policy_checks: List[Dict], data: Dict, filter_by_relevance: bool = True) -> List[Dict]:
        """Check compliance for all policy requirements across any domain"""
        results = []
        
        # Classify document if filtering is enabled
        if filter_by_relevance:
            classifier = DocumentClassifier()
            document_classification = classifier.classify_document(data)
            applicable_checks, skipped_checks = classifier.determine_applicable_agents(
                document_classification, policy_checks
            )
            
            # Add classification info to results
            classification_info = {
                'document_type': document_classification.get('primary_loan_type', 'unknown'),
                'classification_confidence': document_classification.get('confidence', 0),
                'total_checks': len(policy_checks),
                'applicable_checks': len(applicable_checks),
                'skipped_checks': len(skipped_checks)
            }
        else:
            applicable_checks = policy_checks
            skipped_checks = []
            classification_info = {
                'filtering_disabled': True,
                'total_checks': len(policy_checks)
            }
        
        # Process applicable checks
        for i, check in enumerate(applicable_checks):
            # Create universal agent based on check definition
            agent = self.agent_factory.create_agent(
                check['check_type'], 
                check_definition=check
            )
            
            result = agent.check(check, data)
            
            # Add metadata about the check
            result.update({
                'check_id': f"{check['check_type']}_{i}",
                'check_index': i,
                'priority': check.get('priority', 'medium'),
                'data_fields_used': check.get('data_fields', []),
                'relevance_score': check.get('relevance_score', 1.0),
                'status': 'executed'
            })
            
            results.append(result)
        
        # Add skipped checks to results with appropriate status
        for i, check in enumerate(skipped_checks):
            skipped_result = {
                'check_type': check.get('check_type'),
                'description': check.get('description'),
                'check_id': f"{check['check_type']}_skipped_{i}",
                'status': 'skipped',
                'skip_reason': check.get('skip_reason', 'Not applicable to document type'),
                'relevance_score': check.get('relevance_score', 0),
                'priority': check.get('priority', 'medium'),
                'passed': None,  # Not executed
                'domain': check.get('domain', 'unknown')
            }
            results.append(skipped_result)
        
        # Store classification info for reporting
        self.last_classification = classification_info
        
        return results
    
    def get_agent_summary(self, policy_checks: List[Dict]) -> Dict:
        """Return summary of agents that would be created"""
        agent_summary = {}
        domain_breakdown = {}
        complexity_breakdown = {}
        
        for check in policy_checks:
            check_type = check['check_type']
            domain = check.get('domain', 'general')
            complexity = check.get('complexity', 'simple')
            
            # Count by check type
            if check_type in agent_summary:
                agent_summary[check_type]['count'] += 1
            else:
                agent_summary[check_type] = {
                    'count': 1,
                    'domain': domain,
                    'complexity': complexity,
                    'description': check.get('description', 'No description'),
                    'priority': check.get('priority', 'medium')
                }
            
            # Count by domain
            domain_breakdown[domain] = domain_breakdown.get(domain, 0) + 1
            
            # Count by complexity
            complexity_breakdown[complexity] = complexity_breakdown.get(complexity, 0) + 1
        
        return {
            'by_check_type': agent_summary,
            'by_domain': domain_breakdown,
            'by_complexity': complexity_breakdown,
            'total_checks': len(policy_checks),
            'unique_check_types': len(agent_summary)
        }
    
    def analyze_compliance_results(self, results: List[Dict]) -> Dict:
        """Analyze overall compliance results"""
        if not results:
            return {'status': 'no_checks', 'message': 'No checks performed'}
        
        # Separate executed and skipped checks
        executed_results = [r for r in results if r.get('status') != 'skipped']
        skipped_results = [r for r in results if r.get('status') == 'skipped']
        
        total_checks = len(results)
        executed_checks = len(executed_results)
        skipped_checks = len(skipped_results)
        
        # Only count passes/fails from executed checks
        passed_checks = sum(1 for r in executed_results if r.get('passed', False))
        failed_checks = executed_checks - passed_checks
        
        # Analyze by priority (only executed checks)
        critical_failures = [r for r in executed_results if not r.get('passed', False) and r.get('priority') == 'critical']
        high_failures = [r for r in executed_results if not r.get('passed', False) and r.get('priority') == 'high']
        
        # Analyze by domain
        domain_results = {}
        for result in results:
            domain = result.get('domain', 'general')
            if domain not in domain_results:
                domain_results[domain] = {'total': 0, 'passed': 0, 'failed': 0}
            domain_results[domain]['total'] += 1
            if result.get('passed', False):
                domain_results[domain]['passed'] += 1
            else:
                domain_results[domain]['failed'] += 1
        
        # Determine overall status (based on executed checks only)
        if executed_checks == 0:
            overall_status = 'no_applicable_checks'
        elif critical_failures:
            overall_status = 'critical_failure'
        elif high_failures and len(high_failures) > executed_checks * 0.3:  # More than 30% high priority failures
            overall_status = 'high_risk'
        elif failed_checks > executed_checks * 0.5:  # More than 50% failures
            overall_status = 'non_compliant'
        elif failed_checks == 0:
            overall_status = 'fully_compliant'
        else:
            overall_status = 'partially_compliant'
        
        # Add classification info if available
        classification_info = getattr(self, 'last_classification', {})
        
        return {
            'overall_status': overall_status,
            'document_classification': classification_info,
            'summary': {
                'total_checks': total_checks,
                'executed_checks': executed_checks,
                'skipped_checks': skipped_checks,
                'passed': passed_checks,
                'failed': failed_checks,
                'pass_rate': passed_checks / executed_checks if executed_checks > 0 else 0,
                'execution_rate': executed_checks / total_checks if total_checks > 0 else 0
            },
            'critical_failures': len(critical_failures),
            'high_priority_failures': len(high_failures),
            'domain_breakdown': domain_results,
            'skipped_reasons': self._summarize_skip_reasons(skipped_results),
            'recommendations': self._generate_recommendations(executed_results, overall_status)
        }
    
    def _generate_recommendations(self, results: List[Dict], overall_status: str) -> List[str]:
        """Generate recommendations based on compliance results"""
        recommendations = []
        
        failed_results = [r for r in results if not r.get('passed', False)]
        
        if overall_status == 'critical_failure':
            recommendations.append("Immediate action required: Address critical compliance failures before proceeding")
        
        if failed_results:
            # Group failures by domain
            domain_failures = {}
            for result in failed_results:
                domain = result.get('domain', 'general')
                if domain not in domain_failures:
                    domain_failures[domain] = []
                domain_failures[domain].append(result)
            
            for domain, failures in domain_failures.items():
                if len(failures) > 1:
                    recommendations.append(f"Review {domain} processes - multiple failures detected")
                else:
                    recommendations.append(f"Address {domain} compliance issue: {failures[0].get('description', 'Unknown issue')}")
        
        if overall_status == 'fully_compliant':
            recommendations.append("All compliance checks passed - continue with current processes")
        
        return recommendations
    
    def _summarize_skip_reasons(self, skipped_results: List[Dict]) -> Dict[str, int]:
        """Summarize reasons for skipping checks"""
        skip_reasons = {}
        for result in skipped_results:
            reason = result.get('skip_reason', 'Unknown reason')
            skip_reasons[reason] = skip_reasons.get(reason, 0) + 1
        return skip_reasons