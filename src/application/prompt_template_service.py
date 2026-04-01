"""Prompt template management service."""
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class PromptTemplateService:
    """Service for managing prompt templates."""
    
    def __init__(self):
        """Initialize prompt template service."""
        self.templates = {}
        self._load_default_templates()
    
    def _load_default_templates(self):
        """Load default system templates."""
        self.templates["default_rag"] = {
            "name": "default_rag",
            "template": """Based on the following context, answer the question concisely.

Context:
{context}

Question: {query}

Answer:""",
            "variables": ["context", "query"],
            "category": "system",
            "description": "Default RAG prompt template",
        }
        
        self.templates["detailed_rag"] = {
            "name": "detailed_rag",
            "template": """You are a helpful assistant. Using the provided context, give a detailed and comprehensive answer.

Context:
{context}

Question: {query}

Please provide a detailed answer with examples where applicable.
Answer:""",
            "variables": ["context", "query"],
            "category": "system",
            "description": "Detailed RAG response template",
        }
        
        self.templates["qa_format"] = {
            "name": "qa_format",
            "template": """Answer the following question based on the provided context.
Provide your answer in Q&A format.

Context:
{context}

Question: {query}

Q&A Format Answer:""",
            "variables": ["context", "query"],
            "category": "system",
            "description": "Q&A format template",
        }
    
    async def create_template(
        self,
        name: str,
        template: str,
        variables: List[str],
        category: str = "user_defined",
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create new prompt template.
        
        Args:
            name: Template name
            template: Template string with {variable} placeholders
            variables: List of variable names
            category: Template category
            description: Template description
            
        Returns:
            Created template
        """
        try:
            # Validate template
            self._validate_template(template, variables)
            
            template_data = {
                "name": name,
                "template": template,
                "variables": variables,
                "category": category,
                "description": description or "",
                "version": 1,
            }
            
            self.templates[name] = template_data
            logger.info(f"Created template: {name}")
            return template_data
            
        except Exception as e:
            logger.error(f"Error creating template: {str(e)}")
            raise
    
    async def get_template(self, name: str) -> Optional[Dict[str, Any]]:
        """Get template by name.
        
        Args:
            name: Template name
            
        Returns:
            Template data or None
        """
        return self.templates.get(name)
    
    async def list_templates(
        self,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List all templates.
        
        Args:
            category: Filter by category
            
        Returns:
            List of templates
        """
        templates = list(self.templates.values())
        
        if category:
            templates = [t for t in templates if t["category"] == category]
        
        return templates
    
    async def update_template(
        self,
        name: str,
        template: Optional[str] = None,
        variables: Optional[List[str]] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update existing template.
        
        Args:
            name: Template name
            template: New template string
            variables: New variables list
            description: New description
            
        Returns:
            Updated template
        """
        try:
            if name not in self.templates:
                raise ValueError(f"Template '{name}' not found")
            
            existing = self.templates[name]
            
            if template:
                self._validate_template(template, variables or existing["variables"])
                existing["template"] = template
            
            if variables:
                existing["variables"] = variables
            
            if description is not None:
                existing["description"] = description
            
            existing["version"] = existing.get("version", 0) + 1
            
            logger.info(f"Updated template: {name}")
            return existing
            
        except Exception as e:
            logger.error(f"Error updating template: {str(e)}")
            raise
    
    async def delete_template(self, name: str) -> bool:
        """Delete template.
        
        Args:
            name: Template name
            
        Returns:
            True if deleted
        """
        try:
            # Prevent deletion of system templates
            if self.templates.get(name, {}).get("category") == "system":
                raise ValueError("Cannot delete system templates")
            
            if name in self.templates:
                del self.templates[name]
                logger.info(f"Deleted template: {name}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error deleting template: {str(e)}")
            raise
    
    def render_template(
        self,
        template_name: str,
        **kwargs
    ) -> str:
        """Render template with variables.
        
        Args:
            template_name: Name of template
            **kwargs: Template variables
            
        Returns:
            Rendered template string
        """
        try:
            template_data = self.templates.get(template_name)
            if not template_data:
                raise ValueError(f"Template '{template_name}' not found")
            
            template_str = template_data["template"]
            return template_str.format(**kwargs)
            
        except Exception as e:
            logger.error(f"Error rendering template: {str(e)}")
            raise
    
    def _validate_template(self, template: str, variables: List[str]):
        """Validate template has correct variable placeholders.
        
        Args:
            template: Template string
            variables: Expected variables
            
        Raises:
            ValueError if template is invalid
        """
        for var in variables:
            if f"{{{var}}}" not in template:
                raise ValueError(f"Template missing variable: {{{var}}}")
