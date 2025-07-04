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
            print(f"Error loading benchmarks: {e}")
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
            print(f"Error determining benchmark level for {metric_name}: {e}")
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
            print(f"Error calculating score for {metric_name}: {e}")
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
    
    async def generate_ai_insights(self, dashboard_metrics: Dict[str, Any], business_type: str = "general") -> Dict[str, Any]:
        """Generate AI-powered insights using OpenAI API."""
        if not self.openai_client:
            return self._generate_fallback_insights(dashboard_metrics)
        
        try:
            analysis_data = self.prepare_analysis_data(dashboard_metrics)
            
            # Prepare the prompt
            prompt = self._create_analysis_prompt(analysis_data, business_type)
            
            # Call OpenAI API
            response = await openai.ChatCompletion.acreate(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert SEO analyst specializing in data-driven insights and actionable recommendations."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            # Parse the response
            ai_response = response.choices[0].message.content
            try:
                # Try to parse as JSON
                insights = json.loads(ai_response)
                return insights
            except json.JSONDecodeError:
                # If not valid JSON, return fallback insights
                print(f"Invalid JSON response from OpenAI: {ai_response}")
                return self._generate_fallback_insights(dashboard_metrics)
                
        except Exception as e:
            print(f"Error generating AI insights: {e}")
            return self._generate_fallback_insights(dashboard_metrics)
    
    def _load_prompt_files(self) -> tuple[str, str]:
        """Load prompt instructions and JSON template from separate files."""
        # Load prompt instructions
        prompt_path = os.path.join(os.path.dirname(__file__), 'prompts', 'benchmark_analysis_prompt.txt')
        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt_instructions = f.read()
        
        # Load JSON template
        template_path = os.path.join(os.path.dirname(__file__), 'prompts', 'benchmark_response_template.txt')
        with open(template_path, 'r', encoding='utf-8') as f:
            json_template = f.read()
        
        return prompt_instructions, json_template
    


    def _create_analysis_prompt(self, analysis_data: Dict[str, Any], business_type: str) -> str:
        """Create the analysis prompt for OpenAI by loading and concatenating prompt files."""
        # Load prompt files
        prompt_instructions, json_template = self._load_prompt_files()
        
        # Create the complete prompt
        complete_prompt = f"""{prompt_instructions}

## INPUT DATA
Dashboard Metrics: {json.dumps(analysis_data['dashboard_metrics'], indent=2)}
Benchmark Data: {json.dumps(analysis_data['benchmark_data'], indent=2)}
Calculated Metrics: {json.dumps(analysis_data['calculated_metrics'], indent=2)}
Business Type: {business_type}

{json_template}"""
        
        return complete_prompt
    
    def _generate_fallback_insights(self, dashboard_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Generate fallback insights when AI is not available."""
        return {
            "analysis_timestamp": datetime.now().isoformat(),
            "overall_seo_health": {
                "score": 75,
                "grade": "good",
                "summary": "Your website shows good SEO performance with room for improvement.",
                "top_strength": "Performance metrics",
                "biggest_opportunity": "Metadata optimization"
            },
            "visibility_performance": {
                "overall_assessment": "Good visibility with opportunities for improvement",
                "metrics": {
                    "impressions": {
                        "current_value": dashboard_metrics.get('summary', {}).get('total_impressions', 0),
                        "benchmark_level": "good",
                        "score": 70,
                        "analysis": "Your search visibility is performing well within industry standards.",
                        "next_tier_target": "Focus on expanding keyword coverage and content creation",
                        "recommendations": [
                            "Create more content targeting relevant keywords",
                            "Improve internal linking structure"
                        ],
                        "priority": "medium",
                        "time_to_impact": "short-term"
                    }
                }
            },
            "performance_metrics": {
                "overall_assessment": "Good performance with optimization opportunities",
                "metrics": {
                    "performance_score": {
                        "current_value": dashboard_metrics.get('ux', {}).get('performance_score', 0),
                        "benchmark_level": "good",
                        "score": 75,
                        "analysis": "Your website performance is good but can be improved.",
                        "next_tier_target": "Optimize images and reduce server response time",
                        "recommendations": [
                            "Compress and optimize images",
                            "Implement browser caching"
                        ],
                        "priority": "high",
                        "time_to_impact": "immediate"
                    }
                }
            },
            "metadata_optimization": {
                "overall_assessment": "Metadata needs attention for better SEO performance",
                "metrics": {
                    "meta_titles": {
                        "current_value": dashboard_metrics.get('metadata', {}).get('meta_titles', 0),
                        "benchmark_level": "average",
                        "score": 60,
                        "analysis": "Meta titles need optimization for better search visibility.",
                        "next_tier_target": "Optimize titles on all pages",
                        "recommendations": [
                            "Rewrite meta titles to include primary keywords",
                            "Ensure titles are 50-60 characters long"
                        ],
                        "priority": "high",
                        "time_to_impact": "immediate"
                    }
                }
            },
            "action_plan": {
                "immediate_actions": [
                    "Optimize meta titles and descriptions",
                    "Compress website images"
                ],
                "short_term_goals": [
                    "Improve page loading speed",
                    "Create more content"
                ],
                "long_term_strategy": [
                    "Build quality backlinks",
                    "Develop comprehensive content strategy"
                ]
            },
            "competitive_context": {
                "industry_percentile": "top 50%",
                "peer_comparison": "You're performing well compared to similar websites",
                "market_opportunity": "Focus on content creation and technical optimization"
            }
        }

# Global instance
benchmark_analyzer = BenchmarkAnalyzer() 