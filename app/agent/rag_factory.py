"""
RAG Agent Factory
=================
Unified factory for creating RAG agents based on configuration.
Automatically switches between keyword-based and vector-based RAG.
"""

import os
import logging
from typing import Union
from supabase import Client

from .keyword_rag_agent import KeywordRAGAgent, KeywordRAGConfig
from .supabase_rag_agent import SupabaseRAGAgent, RAGConfig

logger = logging.getLogger(__name__)


class RAGFactory:
    """
    Factory for creating the appropriate RAG agent based on configuration.
    """
    
    @staticmethod
    def create_rag_agent(
        supabase_client: Client,
        openai_api_key: str,
        mode: str = None
    ) -> Union[KeywordRAGAgent, SupabaseRAGAgent]:
        """
        Create the appropriate RAG agent based on mode and capabilities.
        
        Args:
            supabase_client: Initialized Supabase client
            openai_api_key: OpenAI API key
            mode: 'keyword', 'vector', or 'auto' (default: from env)
            
        Returns:
            Configured RAG agent
        """
        # Determine mode
        if mode is None:
            mode = os.getenv('RAG_MODE', 'auto')
            
        # Auto-detect best mode if not specified
        if mode == 'auto':
            mode = RAGFactory._detect_best_mode(openai_api_key)
            
        logger.info(f"Creating RAG agent in {mode} mode")
        
        if mode == 'keyword':
            return KeywordRAGAgent(
                supabase_client=supabase_client,
                openai_api_key=openai_api_key,
                config=KeywordRAGConfig()
            )
        elif mode == 'vector':
            return SupabaseRAGAgent(
                supabase_client=supabase_client,
                openai_api_key=openai_api_key,
                config=RAGConfig()
            )
        else:
            raise ValueError(f"Unknown RAG mode: {mode}. Use 'keyword', 'vector', or 'auto'")
    
    @staticmethod
    def _detect_best_mode(openai_api_key: str) -> str:
        """
        Auto-detect the best RAG mode based on API capabilities.
        
        Args:
            openai_api_key: OpenAI API key to test
            
        Returns:
            'vector' if embeddings available, 'keyword' otherwise
        """
        try:
            import openai
            
            client = openai.OpenAI(api_key=openai_api_key)
            
            # Test embedding access - try multiple models
            embedding_models = ["text-embedding-3-small", "text-embedding-ada-002", "text-embedding-3-large"]
            
            for model in embedding_models:
                try:
                    response = client.embeddings.create(
                        model=model,
                        input=["test"]
                    )
                    logger.info(f"Embeddings API available with {model} - using vector mode")
                    return 'vector'
                except Exception as model_error:
                    logger.debug(f"Model {model} not available: {model_error}")
                    continue
            
            logger.info("No embedding models available - using keyword mode")
            return 'keyword'
            
        except Exception as e:
            logger.info(f"Embeddings test failed ({e}) - using keyword mode")
            return 'keyword'
    
    @staticmethod
    def get_supported_modes() -> list:
        """
        Get list of supported RAG modes.
        
        Returns:
            List of supported modes
        """
        return ['keyword', 'vector', 'auto']
    
    @staticmethod
    def test_rag_capabilities(openai_api_key: str) -> dict:
        """
        Test RAG capabilities and return status.
        
        Args:
            openai_api_key: OpenAI API key to test
            
        Returns:
            Dictionary with capability status
        """
        import openai
        
        capabilities = {
            'chat': False,
            'embeddings': False,
            'recommended_mode': 'keyword',
            'embedding_model': None
        }
        
        client = openai.OpenAI(api_key=openai_api_key)
        
        # Test chat
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            capabilities['chat'] = True
            logger.info("Chat API: Available")
        except Exception as e:
            logger.error(f"Chat API: Failed - {e}")
            
        # Test embeddings - try multiple models
        embedding_models = ["text-embedding-3-small", "text-embedding-ada-002", "text-embedding-3-large"]
        
        for model in embedding_models:
            try:
                response = client.embeddings.create(
                    model=model,
                    input=["test"]
                )
                capabilities['embeddings'] = True
                capabilities['recommended_mode'] = 'vector'
                capabilities['embedding_model'] = model
                logger.info(f"Embeddings API: Available with {model}")
                break
            except Exception as e:
                logger.debug(f"Embedding model {model}: Not available - {e}")
                continue
                
        if not capabilities['embeddings']:
            logger.warning("Embeddings API: No models available")
            
        return capabilities