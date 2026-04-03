"""Agent Tools System - Abstracts services into callable tools for agents."""
from typing import Dict, Any, Callable, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import logging
import json

logger = logging.getLogger(__name__)


class ToolInputType(str, Enum):
    """Tool input parameter types."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


@dataclass
class ToolParameter:
    """Parameter definition for a tool."""
    name: str
    type: ToolInputType
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[List[str]] = None


@dataclass
class ToolInputSchema:
    """Input schema for a tool."""
    parameters: List[ToolParameter] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON schema format."""
        return {
            "type": "object",
            "properties": {
                p.name: {
                    "type": p.type.value,
                    "description": p.description,
                    **({"enum": p.enum} if p.enum else {}),
                }
                for p in self.parameters
            },
            "required": [p.name for p in self.parameters if p.required],
        }


@dataclass
class ToolResult:
    """Result from executing a tool."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
        }


class AgentTool:
    """Base class for agent tools."""
    
    def __init__(
        self,
        name: str,
        description: str,
        input_schema: ToolInputSchema,
        execute_fn: Callable,
        category: str = "general",
    ):
        """Initialize agent tool.
        
        Args:
            name: Unique tool name (snake_case)
            description: Human-readable description
            input_schema: Input parameters schema
            execute_fn: Async function that executes the tool
            category: Tool category (search, scoring, generation, etc.)
        """
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.execute_fn = execute_fn
        self.category = category
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given arguments.
        
        Args:
            **kwargs: Tool input parameters
            
        Returns:
            ToolResult with execution details
        """
        import time
        start_time = time.time()
        
        try:
            # Validate inputs
            self._validate_inputs(kwargs)
            
            logger.info(f"Executing tool: {self.name} with inputs: {list(kwargs.keys())}")
            
            # Execute
            result = await self.execute_fn(**kwargs)
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            return ToolResult(
                success=True,
                data=result,
                execution_time_ms=execution_time_ms,
            )
            
        except ValueError as e:
            logger.error(f"Validation error in tool {self.name}: {str(e)}")
            return ToolResult(
                success=False,
                error=f"Validation error: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000,
            )
        except Exception as e:
            logger.error(f"Execution error in tool {self.name}: {str(e)}")
            return ToolResult(
                success=False,
                error=f"Execution error: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000,
            )
    
    def _validate_inputs(self, kwargs: Dict[str, Any]) -> None:
        """Validate input parameters against schema.
        
        Args:
            kwargs: Input parameters
            
        Raises:
            ValueError: If validation fails
        """
        required_params = {p.name for p in self.input_schema.parameters if p.required}
        provided_params = set(kwargs.keys())
        
        missing = required_params - provided_params
        if missing:
            raise ValueError(f"Missing required parameters: {missing}")
        
        # Type checking (basic)
        for param in self.input_schema.parameters:
            if param.name in kwargs:
                value = kwargs[param.name]
                # Basic type validation
                if param.type == ToolInputType.STRING and not isinstance(value, str):
                    raise ValueError(f"Parameter '{param.name}' must be string")
                elif param.type == ToolInputType.INTEGER and not isinstance(value, int):
                    raise ValueError(f"Parameter '{param.name}' must be integer")
                elif param.type == ToolInputType.FLOAT and not isinstance(value, (int, float)):
                    raise ValueError(f"Parameter '{param.name}' must be float")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert tool to dictionary for LLM consumption.
        
        Returns:
            Tool definition as dictionary
        """
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "input_schema": self.input_schema.to_dict(),
        }


class ToolRegistry:
    """Registry for managing available tools."""
    
    def __init__(self):
        """Initialize tool registry."""
        self.tools: Dict[str, AgentTool] = {}
        self.tools_by_category: Dict[str, List[str]] = {}
    
    def register(self, tool: AgentTool) -> None:
        """Register a tool.
        
        Args:
            tool: AgentTool instance
        """
        self.tools[tool.name] = tool
        
        if tool.category not in self.tools_by_category:
            self.tools_by_category[tool.category] = []
        self.tools_by_category[tool.category].append(tool.name)
        
        logger.info(f"Registered tool: {tool.name} (category: {tool.category})")
    
    def get_tool(self, name: str) -> Optional[AgentTool]:
        """Get tool by name.
        
        Args:
            name: Tool name
            
        Returns:
            AgentTool or None if not found
        """
        return self.tools.get(name)
    
    def get_tools_by_category(self, category: str) -> List[AgentTool]:
        """Get all tools in a category.
        
        Args:
            category: Tool category
            
        Returns:
            List of AgentTool instances
        """
        tool_names = self.tools_by_category.get(category, [])
        return [self.tools[name] for name in tool_names]
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """List all available tools.
        
        Returns:
            List of tool definitions
        """
        return [tool.to_dict() for tool in self.tools.values()]
    
    def get_tools_prompt(self) -> str:
        """Get formatted tool list for LLM prompt.
        
        Returns:
            Formatted string of all tools
        """
        tools_dict = {}
        for tool in self.tools.values():
            tools_dict[tool.name] = {
                "description": tool.description,
                "input_schema": tool.input_schema.to_dict(),
            }
        return json.dumps(tools_dict, indent=2)


# Global tool registry instance
_tool_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get or create global tool registry.
    
    Returns:
        ToolRegistry instance
    """
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
    return _tool_registry


async def initialize_tools(
    rag_service,
    recruitment_ai_service,
    orchestration_service,
) -> ToolRegistry:
    """Initialize all available tools from existing services.
    
    Args:
        rag_service: RAGService instance
        recruitment_ai_service: RecruitmentAIService instance
        orchestration_service: RequestOrchestrationService instance
        
    Returns:
        Initialized ToolRegistry with all tools
    """
    registry = get_tool_registry()
    
    # Tool 1: Search Documents
    registry.register(AgentTool(
        name="search_documents",
        description="Search for documents matching a query using semantic similarity",
        input_schema=ToolInputSchema(parameters=[
            ToolParameter("query", ToolInputType.STRING, "Search query text"),
            ToolParameter("user_id", ToolInputType.INTEGER, "User ID for filtering"),
            ToolParameter("top_k", ToolInputType.INTEGER, "Number of results to return", required=False, default=5),
            ToolParameter("similarity_threshold", ToolInputType.FLOAT, "Minimum similarity score", required=False, default=0.1),
        ]),
        execute_fn=lambda query, user_id, top_k=5, similarity_threshold=0.1: 
            rag_service.retrieve_documents(
                query=query,
                user_id=user_id,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
            ),
        category="search",
    ))
    
    # Tool 2: Score Resume Against JD
    registry.register(AgentTool(
        name="score_resume",
        description="Score a resume against job description requirements",
        input_schema=ToolInputSchema(parameters=[
            ToolParameter("jd_parsed", ToolInputType.OBJECT, "Parsed job description"),
            ToolParameter("resume_parsed", ToolInputType.OBJECT, "Parsed resume"),
            ToolParameter("resume_text", ToolInputType.STRING, "Full resume text"),
            ToolParameter("jd_text", ToolInputType.STRING, "Full JD text"),
        ]),
        execute_fn=lambda jd_parsed, resume_parsed, resume_text, jd_text:
            recruitment_ai_service.score_candidate(
                jd_parsed=jd_parsed,
                resume_parsed=resume_parsed,
                resume_text=resume_text,
                jd_text=jd_text,
            ),
        category="scoring",
    ))
    
    # Tool 3: Generate Email
    registry.register(AgentTool(
        name="generate_email",
        description="Generate recruitment email (outreach, interview, rejection)",
        input_schema=ToolInputSchema(parameters=[
            ToolParameter("candidate", ToolInputType.OBJECT, "Candidate information"),
            ToolParameter("jd", ToolInputType.OBJECT, "Job description"),
            ToolParameter("email_type", ToolInputType.STRING, "Email type: outreach, interview, rejection", 
                         enum=["outreach", "interview", "rejection"]),
            ToolParameter("custom_note", ToolInputType.STRING, "Additional context", required=False),
        ]),
        execute_fn=lambda candidate, jd, email_type, custom_note=None:
            recruitment_ai_service.generate_outreach_email(
                candidate=candidate,
                jd=jd,
                email_type=email_type,
                custom_note=custom_note,
            ),
        category="generation",
    ))
    
    # Tool 4: Generate Insights
    registry.register(AgentTool(
        name="generate_insights",
        description="Generate actionable insights from query, answer, and context",
        input_schema=ToolInputSchema(parameters=[
            ToolParameter("query", ToolInputType.STRING, "Original user query"),
            ToolParameter("answer", ToolInputType.STRING, "Generated answer"),
            ToolParameter("context", ToolInputType.STRING, "Retrieved context"),
        ]),
        execute_fn=lambda query, answer, context:
            orchestration_service.generate_insights(
                query=query,
                answer=answer,
                context=context,
                llm_service=orchestration_service.llm_service if hasattr(orchestration_service, 'llm_service') else None,
            ),
        category="analysis",
    ))
    
    # Tool 5: Analyze Resume Truth
    registry.register(AgentTool(
        name="analyze_resume_truth",
        description="Analyze resume authenticity and depth without rejecting candidates",
        input_schema=ToolInputSchema(parameters=[
            ToolParameter("resume_text", ToolInputType.STRING, "Full resume text"),
            ToolParameter("jd_text", ToolInputType.STRING, "Job description text"),
        ]),
        execute_fn=lambda resume_text, jd_text:
            recruitment_ai_service.analyze_resume_truth(
                resume_text=resume_text,
                jd_text=jd_text,
            ),
        category="analysis",
    ))
    
    logger.info(f"Tool registry initialized with {len(registry.tools)} tools")
    return registry
