import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class AgentStorageService:
    """Service for storing and managing policy agents in JSON files"""
    
    def __init__(self, storage_dir: str = "stored_agents"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        
        # Create subdirectories for organization
        (self.storage_dir / "policies").mkdir(exist_ok=True)
        (self.storage_dir / "sessions").mkdir(exist_ok=True)
        
        # Metadata file for tracking stored agents
        self.metadata_file = self.storage_dir / "metadata.json"
        self._init_metadata()
    
    def _init_metadata(self):
        """Initialize metadata file if it doesn't exist"""
        if not self.metadata_file.exists():
            metadata = {
                "version": "1.0",
                "created_at": datetime.now().isoformat(),
                "total_policies": 0,
                "policies": {}
            }
            self._save_json(self.metadata_file, metadata)
    
    def _save_json(self, file_path: Path, data: Dict) -> bool:
        """Save data to JSON file with error handling"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Failed to save JSON to {file_path}: {str(e)}")
            return False
    
    def _load_json(self, file_path: Path) -> Optional[Dict]:
        """Load data from JSON file with error handling"""
        try:
            if not file_path.exists():
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load JSON from {file_path}: {str(e)}")
            return None
    
    def _generate_policy_id(self, policy_name: str) -> str:
        """Generate unique policy ID"""
        base_id = policy_name.lower().replace(' ', '_').replace('-', '_')
        # Remove special characters
        base_id = ''.join(c for c in base_id if c.isalnum() or c == '_')
        
        # Ensure uniqueness by adding timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{base_id}_{timestamp}"
    
    def save_agents(self, 
                   policy_name: str, 
                   agents: Dict, 
                   metadata: Optional[Dict] = None) -> Dict:
        """
        Save policy agents to JSON file
        
        Args:
            policy_name: Name of the policy
            agents: Dictionary containing extracted agents
            metadata: Optional metadata about the policy
            
        Returns:
            Dictionary with save results
        """
        try:
            # Generate unique policy ID
            policy_id = self._generate_policy_id(policy_name)
            
            # Prepare agent data for storage
            agent_data = {
                "policy_id": policy_id,
                "policy_name": policy_name,
                "created_at": datetime.now().isoformat(),
                "metadata": metadata or {},
                "agents": agents,
                "agent_counts": {
                    "threshold": len(agents.get("threshold_agents", [])),
                    "criteria": len(agents.get("criteria_agents", [])),
                    "score": len(agents.get("score_agents", [])),
                    "qualitative": len(agents.get("qualitative_agents", []))
                }
            }
            
            # Calculate total agents
            agent_data["agent_counts"]["total"] = sum(agent_data["agent_counts"].values())
            
            # Save to policy file
            policy_file = self.storage_dir / "policies" / f"{policy_id}.json"
            if not self._save_json(policy_file, agent_data):
                return {"success": False, "error": "Failed to save agent data"}
            
            # Update metadata
            self._update_metadata(policy_id, agent_data)
            
            logger.info(f"Successfully saved {agent_data['agent_counts']['total']} agents for policy '{policy_name}' with ID {policy_id}")
            
            return {
                "success": True,
                "policy_id": policy_id,
                "file_path": str(policy_file),
                "agent_counts": agent_data["agent_counts"]
            }
            
        except Exception as e:
            logger.error(f"Failed to save agents for policy '{policy_name}': {str(e)}")
            return {"success": False, "error": str(e)}
    
    def load_agents(self, policy_id: str) -> Optional[Dict]:
        """
        Load policy agents from JSON file
        
        Args:
            policy_id: Unique policy identifier
            
        Returns:
            Dictionary containing agent data or None if not found
        """
        try:
            policy_file = self.storage_dir / "policies" / f"{policy_id}.json"
            agent_data = self._load_json(policy_file)
            
            if agent_data is None:
                logger.warning(f"Policy {policy_id} not found")
                return None
            
            logger.info(f"Successfully loaded {agent_data.get('agent_counts', {}).get('total', 0)} agents for policy {policy_id}")
            return agent_data
            
        except Exception as e:
            logger.error(f"Failed to load agents for policy {policy_id}: {str(e)}")
            return None
    
    def list_policies(self) -> List[Dict]:
        """
        List all stored policies
        
        Returns:
            List of policy summaries
        """
        try:
            metadata = self._load_json(self.metadata_file)
            if not metadata:
                return []
            
            policies = []
            for policy_id, policy_info in metadata.get("policies", {}).items():
                policies.append({
                    "policy_id": policy_id,
                    "policy_name": policy_info.get("policy_name", "Unknown"),
                    "created_at": policy_info.get("created_at", "Unknown"),
                    "agent_counts": policy_info.get("agent_counts", {}),
                    "metadata": policy_info.get("metadata", {})
                })
            
            # Sort by creation date (newest first)
            policies.sort(key=lambda x: x["created_at"], reverse=True)
            
            return policies
            
        except Exception as e:
            logger.error(f"Failed to list policies: {str(e)}")
            return []
    
    def delete_policy(self, policy_id: str) -> bool:
        """
        Delete a stored policy
        
        Args:
            policy_id: Unique policy identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            policy_file = self.storage_dir / "policies" / f"{policy_id}.json"
            
            if not policy_file.exists():
                logger.warning(f"Policy {policy_id} not found for deletion")
                return False
            
            # Remove file
            policy_file.unlink()
            
            # Update metadata
            metadata = self._load_json(self.metadata_file)
            if metadata and "policies" in metadata and policy_id in metadata["policies"]:
                del metadata["policies"][policy_id]
                metadata["total_policies"] = len(metadata["policies"])
                self._save_json(self.metadata_file, metadata)
            
            logger.info(f"Successfully deleted policy {policy_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete policy {policy_id}: {str(e)}")
            return False
    
    def search_agents(self, query: str, agent_type: Optional[str] = None) -> List[Dict]:
        """
        Search for agents across all policies
        
        Args:
            query: Search query (matches in agent name, description, or requirement)
            agent_type: Optional filter by agent type
            
        Returns:
            List of matching agents with policy information
        """
        try:
            results = []
            query_lower = query.lower()
            
            for policy_file in (self.storage_dir / "policies").glob("*.json"):
                policy_data = self._load_json(policy_file)
                if not policy_data:
                    continue
                
                policy_id = policy_data.get("policy_id", "")
                policy_name = policy_data.get("policy_name", "")
                agents = policy_data.get("agents", {})
                
                # Search through all agent types
                for agent_type_key, agent_list in agents.items():
                    if agent_type and agent_type_key != agent_type:
                        continue
                    
                    # Ensure agent_list is actually a list
                    if not isinstance(agent_list, list):
                        continue
                    
                    for agent in agent_list:
                        # Check if query matches agent name, description, or requirement
                        matches = [
                            query_lower in agent.get("agent_name", "").lower(),
                            query_lower in agent.get("description", "").lower(),
                            query_lower in agent.get("requirement", "").lower()
                        ]
                        
                        if any(matches):
                            results.append({
                                "policy_id": policy_id,
                                "policy_name": policy_name,
                                "agent_type": agent_type_key,
                                "agent": agent
                            })
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to search agents: {str(e)}")
            return []
    
    def _update_metadata(self, policy_id: str, agent_data: Dict):
        """Update metadata file with new policy information"""
        try:
            metadata = self._load_json(self.metadata_file)
            if not metadata:
                metadata = {
                    "version": "1.0",
                    "created_at": datetime.now().isoformat(),
                    "total_policies": 0,
                    "policies": {}
                }
            
            # Add/update policy info
            metadata["policies"][policy_id] = {
                "policy_name": agent_data.get("policy_name", ""),
                "created_at": agent_data.get("created_at", ""),
                "agent_counts": agent_data.get("agent_counts", {}),
                "metadata": agent_data.get("metadata", {})
            }
            
            metadata["total_policies"] = len(metadata["policies"])
            metadata["last_updated"] = datetime.now().isoformat()
            
            self._save_json(self.metadata_file, metadata)
            
        except Exception as e:
            logger.error(f"Failed to update metadata: {str(e)}")
    
    def get_storage_stats(self) -> Dict:
        """Get storage statistics"""
        try:
            metadata = self._load_json(self.metadata_file)
            if not metadata:
                return {"total_policies": 0, "total_agents": 0}
            
            total_agents = 0
            for policy_info in metadata.get("policies", {}).values():
                total_agents += policy_info.get("agent_counts", {}).get("total", 0)
            
            return {
                "total_policies": metadata.get("total_policies", 0),
                "total_agents": total_agents,
                "storage_dir": str(self.storage_dir),
                "last_updated": metadata.get("last_updated", "Unknown")
            }
            
        except Exception as e:
            logger.error(f"Failed to get storage stats: {str(e)}")
            return {"total_policies": 0, "total_agents": 0, "error": str(e)}