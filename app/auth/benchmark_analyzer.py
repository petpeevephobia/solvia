"""
Benchmark Analyzer for Solvia SEO Dashboard
Provides AI-powered insights by comparing user metrics against industry benchmarks.
"""

import json
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
import openai
from app.config import settings
from core.modules.prompt_loader import load_prompt
import inspect

class BenchmarkAnalyzer:
    """Analyzes user metrics against SEO benchmarks and generates AI-powered insights."""
    
    def __init__(self):
        self.benchmarks = self._load_benchmarks()
        self.openai_client = None
        if hasattr(settings, 'OPENAI_API_KEY') and settings.OPENAI_API_KEY:
            self.openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
    
    def _load_benchmarks(self) -> Dict[str, Any]:
        """Load SEO benchmarks from JSON file."""
        try:
            benchmark_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'seo_benchmarks.json')
            with open(benchmark_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('seo_benchmarks', {})
        except Exception as e:
            return {}
    
    def get_benchmark_level(self, metric_name: str, value: float, category: str) -> str:
        """Determine performance level (excellent/good/average/poor) for a metric."""
        try:
            category_data = self.benchmarks.get(category, {})
            metric_data = category_data.get(metric_name, {})
            
            # Check thresholds in order: excellent, good, average, poor
            if 'excellent' in metric_data:
                excellent_threshold = metric_data['excellent']
                if 'min' in excellent_threshold and value >= excellent_threshold['min']:
                    return 'excellent'
                if 'max' in excellent_threshold and value <= excellent_threshold['max']:
                    return 'excellent'
            
            if 'good' in metric_data:
                good_threshold = metric_data['good']
                if 'min' in good_threshold and value >= good_threshold['min']:
                    return 'good'
                if 'max' in good_threshold and value <= good_threshold['max']:
                    return 'good'
            
            if 'average' in metric_data:
                average_threshold = metric_data['average']
                if 'min' in average_threshold and value >= average_threshold['min']:
                    return 'average'
                if 'max' in average_threshold and value <= average_threshold['max']:
                    return 'average'
            
            return 'poor'
        except Exception as e:
            return 'average'
    
    def calculate_metric_score(self, metric_name: str, value: float, category: str) -> int:
        """Calculate a score (0-100) for a metric based on benchmark thresholds."""
        try:
            category_data = self.benchmarks.get(category, {})
            metric_data = category_data.get(metric_name, {})
            
            # Get threshold values
            excellent_threshold = metric_data.get('excellent', {})
            poor_threshold = metric_data.get('poor', {})
            
            # Determine if higher or lower values are better
            higher_is_better = 'min' in excellent_threshold
            
            if higher_is_better:
                excellent_value = excellent_threshold.get('min', 100)
                poor_value = poor_threshold.get('max', 0)
                
                if value >= excellent_value:
                    return 100
                elif value <= poor_value:
                    return 0
                else:
                    return int(((value - poor_value) / (excellent_value - poor_value)) * 100)
            else:
                excellent_value = excellent_threshold.get('max', 0)
                poor_value = poor_threshold.get('min', 100)
                
                if value <= excellent_value:
                    return 100
                elif value >= poor_value:
                    return 0
                else:
                    return int(((poor_value - value) / (poor_value - excellent_value)) * 100)
        except Exception as e:
            return 50
    
    def prepare_analysis_data(self, dashboard_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare dashboard metrics and benchmarks for AI analysis."""
        analysis_data = {
            "dashboard_metrics": dashboard_metrics,
            "benchmark_data": self.benchmarks,
            "analysis_timestamp": datetime.now().isoformat()
        }
        
        # Add calculated benchmark levels and scores
        analysis_data["calculated_metrics"] = {}
        
        # Visibility Performance
        if 'summary' in dashboard_metrics:
            summary = dashboard_metrics['summary']
            analysis_data["calculated_metrics"]["visibility_performance"] = {
                "impressions": {
                    "value": summary.get('total_impressions', 0),
                    "level": self.get_benchmark_level("impressions", summary.get('total_impressions', 0), "visibility_performance"),
                    "score": self.calculate_metric_score("impressions", summary.get('total_impressions', 0), "visibility_performance")
                },
                "clicks": {
                    "value": summary.get('total_clicks', 0),
                    "level": self.get_benchmark_level("clicks", summary.get('total_clicks', 0), "visibility_performance"),
                    "score": self.calculate_metric_score("clicks", summary.get('total_clicks', 0), "visibility_performance")
                },
                "ctr": {
                    "value": summary.get('avg_ctr', 0) * 100,  # Convert to percentage
                    "level": self.get_benchmark_level("ctr", summary.get('avg_ctr', 0) * 100, "visibility_performance"),
                    "score": self.calculate_metric_score("ctr", summary.get('avg_ctr', 0) * 100, "visibility_performance")
                },
                "average_position": {
                    "value": summary.get('avg_position', 0),
                    "level": self.get_benchmark_level("average_position", summary.get('avg_position', 0), "visibility_performance"),
                    "score": self.calculate_metric_score("average_position", summary.get('avg_position', 0), "visibility_performance")
                }
            }
        
        # Performance Metrics
        if 'ux' in dashboard_metrics:
            ux = dashboard_metrics['ux']
            analysis_data["calculated_metrics"]["performance_metrics"] = {
                "performance_score": {
                    "value": ux.get('performance_score', 0),
                    "level": self.get_benchmark_level("performance_score", ux.get('performance_score', 0), "performance_metrics"),
                    "score": self.calculate_metric_score("performance_score", ux.get('performance_score', 0), "performance_metrics")
                },
                "lcp_seconds": {
                    "value": ux.get('lcp', 0),
                    "level": self.get_benchmark_level("lcp_seconds", ux.get('lcp', 0), "performance_metrics"),
                    "score": self.calculate_metric_score("lcp_seconds", ux.get('lcp', 0), "performance_metrics")
                },
                "fcp_seconds": {
                    "value": ux.get('fcp', 0),
                    "level": self.get_benchmark_level("fcp_seconds", ux.get('fcp', 0), "performance_metrics"),
                    "score": self.calculate_metric_score("fcp_seconds", ux.get('fcp', 0), "performance_metrics")
                },
                "cls_score": {
                    "value": ux.get('cls', 0),
                    "level": self.get_benchmark_level("cls_score", ux.get('cls', 0), "performance_metrics"),
                    "score": self.calculate_metric_score("cls_score", ux.get('cls', 0), "performance_metrics")
                }
            }
        
        # Metadata Optimization
        if 'metadata' in dashboard_metrics:
            metadata = dashboard_metrics['metadata']
            analysis_data["calculated_metrics"]["metadata_optimization"] = {
                "meta_titles": {
                    "value": metadata.get('meta_titles', 0),
                    "level": self.get_benchmark_level("meta_titles", metadata.get('meta_titles', 0), "metadata_optimization"),
                    "score": self.calculate_metric_score("meta_titles", metadata.get('meta_titles', 0), "metadata_optimization")
                },
                "meta_descriptions": {
                    "value": metadata.get('meta_descriptions', 0),
                    "level": self.get_benchmark_level("meta_descriptions", metadata.get('meta_descriptions', 0), "metadata_optimization"),
                    "score": self.calculate_metric_score("meta_descriptions", metadata.get('meta_descriptions', 0), "metadata_optimization")
                },
                "h1_tags": {
                    "value": metadata.get('h1_tags', 0),
                    "level": self.get_benchmark_level("h1_tags", metadata.get('h1_tags', 0), "metadata_optimization"),
                    "score": self.calculate_metric_score("h1_tags", metadata.get('h1_tags', 0), "metadata_optimization")
                },
                "image_alt_text": {
                    "value": metadata.get('image_alt_text', 0),
                    "level": self.get_benchmark_level("image_alt_text", metadata.get('image_alt_text', 0), "metadata_optimization"),
                    "score": self.calculate_metric_score("image_alt_text", metadata.get('image_alt_text', 0), "metadata_optimization")
                }
            }
        
        return analysis_data
    
    def generate_ai_insights(self, dashboard_metrics: Dict[str, Any], business_type: str = "general") -> Dict[str, Any]:
        caller = inspect.stack()[1]
        """Generate AI-powered insights using OpenAI API."""
        if not self.openai_client:
            raise Exception("OpenAI client not available. Cannot generate AI insights.")
        
        # Check if OpenAI API key is configured
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("[ERROR] OPENAI_API_KEY not found in environment variables")
            return self._get_fallback_insights()
        
        analysis_data = self.prepare_analysis_data(dashboard_metrics)
        prompt = self._create_analysis_prompt(analysis_data, business_type)
        
        
        try:
            # Use the new OpenAI client format
            client = openai.OpenAI(api_key=api_key)
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert SEO analyst specializing in data-driven insights and actionable recommendations. You must respond with valid JSON only, no markdown formatting."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            ai_response = response.choices[0].message.content
            
            # print(f"[DEBUG] OpenAI raw response:\t{ai_response}")
            
            if not ai_response or ai_response.strip() == "":
                print("[ERROR] OpenAI returned empty response")
                return self._get_fallback_insights()
            
            # Try to extract JSON from markdown code blocks first
            insights = None
            if "```json" in ai_response:
                json_start = ai_response.find("```json") + 7
                json_end = ai_response.find("```", json_start)
                if json_end > json_start:
                    json_content = ai_response[json_start:json_end].strip()
                    try:
                        insights = json.loads(json_content)
                    except json.JSONDecodeError as e:
                        print(f"[ERROR] Failed to parse JSON from code block: {e}")
                        print(f"[DEBUG] JSON content: {json_content[:200]}...")
            
            # If no code block found or parsing failed, try parsing the raw response
            if insights is None:
                try:
                    insights = json.loads(ai_response)
                except json.JSONDecodeError as e:
                    print(f"[ERROR] Failed to parse raw JSON response: {e}")
                    print(f"[DEBUG] Raw response: {ai_response[:200]}...")
                    return self._get_fallback_insights()
            
            # Ensure all expected keys are present
            required_keys = [
                "overall_seo_health",
                "visibility_performance",
                "performance_metrics",
                "metadata_optimization",
                "action_plan",
                "competitive_context"
            ]
            for key in required_keys:
                if key not in insights:
                    insights[key] = {}
            
            # Handle the actual response structure - check if insights are nested under "insights" key
            if "insights" in insights:
                insights_data = insights["insights"]
            elif "analysis" in insights:
                insights_data = insights["analysis"]
            else:
                insights_data = insights

            def extract_section(section):
                sec = insights_data.get(section, {})
                # If the section is already in the expected format, use it
                if "metrics" in sec and "overall_assessment" in sec:
                    overall = sec.get("overall_assessment", "Analysis not available")
                    metrics = sec.get("metrics", {})
                    # Patch: If overall_assessment is missing or 'Analysis not available', aggregate per-metric analyses
                    if not overall or overall == "Analysis not available":
                        analyses = [v.get("analysis") for v in metrics.values() if isinstance(v, dict) and v.get("analysis")]
                        if analyses:
                            overall = " ".join(analyses)
                    return {
                        "overall_assessment": overall,
                        "metrics": metrics
                    }
                # If the section is a flat dict of metrics, wrap it in 'metrics'
                if isinstance(sec, dict) and not ("metrics" in sec and "overall_assessment" in sec):
                    metrics = sec
                    overall = "Analysis not available"
                    # Patch: Aggregate per-metric analyses if possible
                    analyses = [v.get("analysis") for v in metrics.values() if isinstance(v, dict) and v.get("analysis")]
                    if analyses:
                        overall = " ".join(analyses)
                    return {
                        "overall_assessment": overall,
                        "metrics": metrics
                    }
                # Otherwise, just return the whole section as metrics
                return {
                    "overall_assessment": "Analysis not available",
                    "metrics": sec
                }

            ai_insights = {
                "visibility_performance": extract_section("visibility_performance"),
                "performance_metrics": extract_section("performance_metrics"),
                "metadata_optimization": extract_section("metadata_optimization"),
                "analysis": insights_data.get("overall_seo_health", {}),
                "recommendations": insights_data.get("action_plan", {})
            }
            return ai_insights
            
        except Exception as e:
            print(f"[ERROR] OpenAI API error: {e}")
            print(f"[ERROR] Error type: {type(e)}")
            return self._get_fallback_insights()
    
    def _get_fallback_insights(self) -> Dict[str, Any]:
        """Return fallback insights when OpenAI API fails."""
        return {
            "overall_seo_health": {
                "score": 0,
                "status": "Unable to analyze",
                "summary": "AI analysis temporarily unavailable"
            },
            "visibility_performance": {
                "score": 0,
                "status": "Unable to analyze",
                "summary": "Visibility analysis temporarily unavailable"
            },
            "performance_metrics": {
                "score": 0,
                "status": "Unable to analyze",
                "summary": "Performance analysis temporarily unavailable"
            },
            "metadata_optimization": {
                "score": 0,
                "status": "Unable to analyze",
                "summary": "Metadata analysis temporarily unavailable"
            },
            "action_plan": {
                "priority_actions": [],
                "quick_wins": [],
                "long_term_strategy": []
            },
            "competitive_context": {
                "industry_benchmarks": {},
                "competitive_analysis": "Analysis temporarily unavailable"
            }
        }
    
    def _load_prompt_files(self) -> tuple[str, str]:
        """Load prompt instructions and JSON template from a single file using prompt_loader."""
        # Load the complete prompt file using prompt_loader (which cleans the JSON template)
        complete_prompt = load_prompt('benchmark_analysis_prompt.txt')
        
        # Split the content at 'REQUIRED OUTPUT FORMAT (JSON):' to separate prompt and template
        if 'REQUIRED OUTPUT FORMAT (JSON):' in complete_prompt:
            parts = complete_prompt.split('REQUIRED OUTPUT FORMAT (JSON):')
            if len(parts) >= 2:
                prompt_instructions = parts[0].strip()
                json_template = parts[1].strip()
                return prompt_instructions, json_template
        
        # Fallback if splitting doesn't work
        return complete_prompt, ""
    
    def _create_analysis_prompt(self, analysis_data: Dict[str, Any], business_type: str) -> str:
        """Create the analysis prompt for OpenAI by loading and concatenating prompt files."""
        # Load prompt files
        prompt_instructions, json_template = self._load_prompt_files()
        
        # Create the complete prompt with input data
        complete_prompt = f"""{prompt_instructions}

## INPUT DATA
Dashboard Metrics: {json.dumps(analysis_data['dashboard_metrics'], indent=2)}
Benchmark Data: {json.dumps(analysis_data['benchmark_data'], indent=2)}
Calculated Metrics: {json.dumps(analysis_data['calculated_metrics'], indent=2)}
Business Type: {business_type}

Please analyze the above data and respond with a JSON object following the required format."""
        
        return complete_prompt
    
# Global instance
benchmark_analyzer = BenchmarkAnalyzer()