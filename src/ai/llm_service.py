"""LLM Service for language model operations using Ollama."""
from typing import Dict, Any, Optional
import logging
import httpx

logger = logging.getLogger(__name__)


class LLMService:
    """Service for LLM operations using Ollama."""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "mistral", fine_tuned_model: Optional[str] = None):
        """Initialize LLM service.
        
        Args:
            base_url: Ollama server base URL
            model: Base model name to use (mistral, neural-chat, dolphin-mixtral, etc.)
            fine_tuned_model: Optional fine-tuned model to use instead of base model
        """
        self.base_url = base_url
        self.base_model = model
        self.fine_tuned_model = fine_tuned_model
        self.client = httpx.AsyncClient(timeout=300.0)
    
    @property
    def model_name(self) -> str:
        """Get active model name (fine-tuned if available, else base)."""
        return self.fine_tuned_model or self.base_model
    
    def use_finetuned_model(self, model_name: str) -> None:
        """Switch to using a fine-tuned model.
        
        Args:
            model_name: Name of the fine-tuned model
        """
        self.fine_tuned_model = model_name
        logger.info(f"Switched to fine-tuned model: {model_name}")
    
    def use_base_model(self) -> None:
        """Switch back to using the base model."""
        self.fine_tuned_model = None
        logger.info(f"Switched back to base model: {self.base_model}")
    
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        use_finetuned: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate text using Ollama.
        
        Args:
            prompt: Input prompt
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            use_finetuned: Whether to use fine-tuned model if available
            **kwargs: Additional parameters
            
        Returns:
            Dictionary with generated text and metadata
        """
        try:
            # Select model based on preference and availability
            active_model = self.model_name if use_finetuned else self.base_model
            
            # Prepare request payload
            payload = {
                "model": active_model,
                "prompt": prompt,
                "stream": False,
                "temperature": temperature,
            }
            
            if max_tokens:
                payload["num_predict"] = max_tokens
            
            # Call Ollama API
            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json=payload,
            )
            response.raise_for_status()
            
            result_data = response.json()
            
            result = {
                "text": result_data.get("response", "").strip(),
                "tokens_used": result_data.get("eval_count", 0),
                "processing_time_ms": result_data.get("total_duration", 0) // 1_000_000,
                "model": active_model,
                "is_finetuned": use_finetuned and self.fine_tuned_model is not None,
                "finish_reason": "stop",
            }
            
            logger.info(f"Generated text using {active_model}")
            return result
            
        except Exception as e:
            logger.error(f"Error generating text: {str(e)}")
            raise
    
    async def summarize(
        self,
        text: str,
        max_length: int = 150,
        use_finetuned: bool = True,
    ) -> str:
        """Summarize text.
        
        Args:
            text: Text to summarize
            max_length: Maximum length of summary
            use_finetuned: Whether to use fine-tuned model if available
            
        Returns:
            Summary text
        """
        try:
            prompt = f"""Summarize the following text in approximately {max_length} words:

{text}

Summary:"""
            
            result = await self.generate(
                prompt=prompt,
                max_tokens=max_length // 4,  # Rough conversion
                use_finetuned=use_finetuned,
            )
            
            return result["text"]
            
        except Exception as e:
            logger.error(f"Error summarizing text: {str(e)}")
            raise
    
    async def extract_entities(self, text: str, use_finetuned: bool = True) -> Dict[str, Any]:
        """Extract named entities from text.
        
        Args:
            text: Text to extract entities from
            use_finetuned: Whether to use fine-tuned model if available
            
        Returns:
            Dictionary of extracted entities
        """
        try:
            prompt = f"""Extract named entities from the following text. 
Return as JSON with keys: persons, organizations, locations, dates, other.

Text: {text}

Entities (JSON):"""
            
            result = await self.generate(
                prompt=prompt,
                use_finetuned=use_finetuned,
            )
            
            # TODO: Parse JSON response
            return {"entities": result["text"]}
            
        except Exception as e:
            logger.error(f"Error extracting entities: {str(e)}")
            raise
    
    async def classify(
        self,
        text: str,
        categories: list,
        use_finetuned: bool = True,
    ) -> Dict[str, float]:
        """Classify text into categories.
        
        Args:
            text: Text to classify
            categories: List of categories
            use_finetuned: Whether to use fine-tuned model if available
            
        Returns:
            Dictionary with category scores
        """
        try:
            categories_str = ", ".join(categories)
            prompt = f"""Classify the following text into one of these categories: {categories_str}

Text: {text}

Classification:"""
            
            result = await self.generate(
                prompt=prompt,
                use_finetuned=use_finetuned,
            )
            
            # TODO: Parse classification response
            return {"classification": result["text"]}
            
        except Exception as e:
            logger.error(f"Error classifying text: {str(e)}")
            raise
    
    async def batch_generate(
        self,
        prompts: list,
        use_finetuned: bool = True,
        **kwargs
    ) -> list:
        """Generate text for multiple prompts.
        
        Args:
            prompts: List of prompts to generate for
            use_finetuned: Whether to use fine-tuned model if available
            **kwargs: Additional parameters
            
        Returns:
            List of generated results
        """
        try:
            results = []
            for prompt in prompts:
                result = await self.generate(
                    prompt=prompt,
                    use_finetuned=use_finetuned,
                    **kwargs
                )
                results.append(result)
            
            logger.info(f"Batch generated {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Error in batch generation: {str(e)}")
            raise
    
    async def get_model_info(self) -> Dict[str, Any]:
        """Get information about the active model.
        
        Returns:
            Model information
        """
        return {
            "base_model": self.base_model,
            "active_model": self.model_name,
            "is_finetuned": self.fine_tuned_model is not None,
            "fine_tuned_model": self.fine_tuned_model,
            "ollama_endpoint": self.base_url,
        }
    
    async def close(self) -> None:
        """Close the HTTP client connection."""
        await self.client.aclose()
    
    @property
    def model_name(self) -> str:
        """Get active model name (fine-tuned if available, else base)."""
        return self.fine_tuned_model or self.base_model
    
    def use_finetuned_model(self, model_name: str) -> None:
        """Switch to using a fine-tuned model.
        
        Args:
            model_name: Name of the fine-tuned model
        """
        self.fine_tuned_model = model_name
        logger.info(f"Switched to fine-tuned model: {model_name}")
    
    def use_base_model(self) -> None:
        """Switch back to using the base model."""
        self.fine_tuned_model = None
        logger.info(f"Switched back to base model: {self.base_model}")
    
    # async def generate(
    #     self,
    #     prompt: str,
    #     temperature: float = 0.7,
    #     max_tokens: Optional[int] = None,
    #     use_finetuned: bool = True,
    #     **kwargs
    # ) -> Dict[str, Any]:
    #     """Generate text using LLM.
        
    #     Args:
    #         prompt: Input prompt
    #         temperature: Sampling temperature
    #         max_tokens: Maximum tokens to generate
    #         use_finetuned: Whether to use fine-tuned model if available
    #         **kwargs: Additional parameters
            
    #     Returns:
    #         Dictionary with generated text and metadata
    #     """
    #     try:
    #         # Select model based on preference and availability
    #         active_model = self.model_name if use_finetuned else self.base_model
            
    #         # TODO: Implement actual LLM API call
    #         # This is a placeholder implementation
            
    #         result = {
    #             "text": "Generated response placeholder",
    #             "tokens_used": 100,
    #             "processing_time_ms": 1000,
    #             "model": active_model,
    #             "is_finetuned": use_finetuned and self.fine_tuned_model is not None,
    #             "finish_reason": "stop",
    #         }
            
    #         logger.info(f"Generated text using {active_model}")
    #         return result
            
    #     except Exception as e:
    #         logger.error(f"Error generating text: {str(e)}")
    #         raise
    
    async def summarize(
        self,
        text: str,
        max_length: int = 150,
        use_finetuned: bool = True,
    ) -> str:
        """Summarize text.
        
        Args:
            text: Text to summarize
            max_length: Maximum length of summary
            use_finetuned: Whether to use fine-tuned model if available
            
        Returns:
            Summary text
        """
        try:
            prompt = f"""Summarize the following text in {max_length} words:

{text}

Summary:"""
            
            result = await self.generate(
                prompt=prompt,
                max_tokens=max_length // 4,  # Rough conversion
                use_finetuned=use_finetuned,
            )
            
            return result["text"]
            
        except Exception as e:
            logger.error(f"Error summarizing text: {str(e)}")
            raise
    
    async def extract_entities(self, text: str, use_finetuned: bool = True) -> Dict[str, Any]:
        """Extract named entities from text.
        
        Args:
            text: Text to extract entities from
            use_finetuned: Whether to use fine-tuned model if available
            
        Returns:
            Dictionary of extracted entities
        """
        try:
            prompt = f"""Extract named entities from the following text. 
Return as JSON with keys: persons, organizations, locations, dates, other.

Text: {text}

Entities:"""
            
            result = await self.generate(
                prompt=prompt,
                use_finetuned=use_finetuned,
            )
            
            # TODO: Parse JSON response
            return {"entities": result["text"]}
            
        except Exception as e:
            logger.error(f"Error extracting entities: {str(e)}")
            raise
    
    async def classify(
        self,
        text: str,
        categories: list,
        use_finetuned: bool = True,
    ) -> Dict[str, float]:
        """Classify text into categories.
        
        Args:
            text: Text to classify
            categories: List of categories
            use_finetuned: Whether to use fine-tuned model if available
            
        Returns:
            Dictionary with category scores
        """
        try:
            categories_str = ", ".join(categories)
            prompt = f"""Classify the following text into one of these categories: {categories_str}

Text: {text}

Classification:"""
            
            result = await self.generate(
                prompt=prompt,
                use_finetuned=use_finetuned,
            )
            
            # TODO: Parse classification response
            return {"classification": result["text"]}
            
        except Exception as e:
            logger.error(f"Error classifying text: {str(e)}")
            raise
    
    async def batch_generate(
        self,
        prompts: list,
        use_finetuned: bool = True,
        **kwargs
    ) -> list:
        """Generate text for multiple prompts.
        
        Args:
            prompts: List of prompts to generate for
            use_finetuned: Whether to use fine-tuned model if available
            **kwargs: Additional parameters
            
        Returns:
            List of generated results
        """
        try:
            results = []
            for prompt in prompts:
                result = await self.generate(
                    prompt=prompt,
                    use_finetuned=use_finetuned,
                    **kwargs
                )
                results.append(result)
            
            logger.info(f"Batch generated {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Error in batch generation: {str(e)}")
            raise
    
    async def get_model_info(self) -> Dict[str, Any]:
        """Get information about the active model.
        
        Returns:
            Model information
        """
        return {
            "base_model": self.base_model,
            "active_model": self.model_name,
            "is_finetuned": self.fine_tuned_model is not None,
            "fine_tuned_model": self.fine_tuned_model,
        }

