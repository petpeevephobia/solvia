"""
Enhanced RAG (Retrieval-Augmented Generation) System for Intelligent SEO Issue Analysis
Implements advanced chunking, semantic search, and confidence scoring based on 2024 best practices
"""
import json
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass, asdict, field
from enum import Enum
from collections import defaultdict
import hashlib

import openai
from app.config import settings
from app.database.supabase_db import SupabaseAuthDB

logger = logging.getLogger(__name__)

class IssueSeverity(str, Enum):
    """Issue severity levels with business impact"""
    CRITICAL = "critical"  # >50% traffic loss or complete failure
    HIGH = "high"         # 20-50% performance impact
    MEDIUM = "medium"     # 10-20% performance impact
    LOW = "low"          # <10% performance impact

class ChunkingStrategy(str, Enum):
    """Chunking strategies for different data types"""
    FIXED_SIZE = "fixed_size"      # Traditional fixed-size chunks
    SEMANTIC = "semantic"          # Group by meaning/context
    TEMPORAL = "temporal"          # Group by time periods
    METRIC_BASED = "metric_based"  # Group by metric thresholds

@dataclass
class DataChunk:
    """Represents a chunk of data for RAG processing"""
    id: str
    content: Dict[str, Any]
    metadata: Dict[str, Any]
    chunk_type: ChunkingStrategy
    embeddings: Optional[List[float]] = None
    relevance_score: float = 0.0
    
    def get_hash(self) -> str:
        """Generate unique hash for chunk"""
        content_str = json.dumps(self.content, sort_keys=True)
        return hashlib.md5(content_str.encode()).hexdigest()

@dataclass
class SEOPattern:
    """Represents a detected SEO pattern in the data"""
    pattern_type: str
    confidence: float
    affected_metrics: List[str]
    time_range: Tuple[datetime, datetime]
    severity: IssueSeverity
    evidence: List[Dict[str, Any]]
    
@dataclass
class EnhancedSEOIssue:
    """Enhanced data structure for SEO issues with confidence and evidence"""
    title: str
    description: str
    severity: IssueSeverity
    impact: str
    recommendation: str
    category: str
    data_points: Dict[str, Any]
    confidence_score: float
    evidence_chunks: List[DataChunk] = field(default_factory=list)
    patterns_detected: List[SEOPattern] = field(default_factory=list)
    temporal_context: Optional[Dict[str, Any]] = None
    similar_sites_comparison: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "title": self.title,
            "description": self.description,
            "severity": self.severity,
            "impact": self.impact,
            "recommendation": self.recommendation,
            "category": self.category,
            "data_points": self.data_points,
            "confidence_score": self.confidence_score,
            "evidence_count": len(self.evidence_chunks),
            "patterns_count": len(self.patterns_detected),
            "temporal_context": self.temporal_context,
            "similar_sites_comparison": self.similar_sites_comparison
        }

class EnhancedSEOKnowledgeBase:
    """
    Enhanced SEO knowledge base with 2024 best practices and semantic understanding
    """
    
    @staticmethod
    def get_advanced_seo_context() -> str:
        """Get comprehensive SEO context based on 2024 best practices"""
        return """
        Advanced SEO Analysis Framework (2024 Standards):
        
        1. CORE WEB VITALS & USER EXPERIENCE:
        - LCP (Largest Contentful Paint): Should be < 2.5s for good UX
        - FID (First Input Delay): Should be < 100ms
        - CLS (Cumulative Layout Shift): Should be < 0.1
        - INP (Interaction to Next Paint): New metric replacing FID in 2024
        
        2. E-E-A-T (Experience, Expertise, Authoritativeness, Trustworthiness):
        - Author credentials and expertise signals
        - Site reputation and brand authority
        - Content accuracy and fact-checking
        - User reviews and testimonials
        
        3. SEMANTIC SEO & ENTITY RECOGNITION:
        - Topic clusters and content hubs
        - Entity relationships and knowledge graph
        - Semantic keyword variations
        - Search intent matching (informational, transactional, navigational)
        
        4. AI & SGE (Search Generative Experience) OPTIMIZATION:
        - Structured data markup (JSON-LD preferred)
        - FAQ and Q&A schema implementation
        - Featured snippet optimization
        - Zero-click search optimization
        
        5. MOBILE-FIRST INDEXING:
        - Mobile page speed (3G/4G performance)
        - Touch target size (minimum 48x48 pixels)
        - Viewport configuration
        - Mobile-specific content parity
        
        6. TRAFFIC ANOMALY PATTERNS:
        - Algorithm updates typically show 20-40% traffic changes
        - Seasonal patterns vary by industry (e-commerce: +200% holiday)
        - Technical issues cause immediate drops (>50% in 24h)
        - Content decay shows gradual decline (5-10% monthly)
        
        7. CTR BENCHMARKS BY POSITION (2024):
        - Position 1: 27.6% CTR
        - Position 2: 15.8% CTR
        - Position 3: 11.0% CTR
        - Position 4-10: 2-8% CTR
        - Below Position 10: <2% CTR
        
        8. RECOVERY TIMEFRAMES:
        - Technical fixes: 1-2 weeks
        - Content improvements: 2-8 weeks
        - Penalty recovery: 3-6 months
        - Brand building: 6-12 months
        """
    
    @staticmethod
    def get_pattern_detection_rules() -> Dict[str, Dict[str, Any]]:
        """Get rules for detecting SEO patterns"""
        return {
            "algorithm_update": {
                "indicators": ["sudden_traffic_drop", "position_volatility", "serp_reshuffling"],
                "threshold": 0.3,  # 30% change
                "timeframe": 3,     # days
                "confidence_factors": ["industry_wide_impact", "no_technical_changes"]
            },
            "technical_issue": {
                "indicators": ["crawl_errors", "indexing_drop", "server_errors"],
                "threshold": 0.5,  # 50% error rate
                "timeframe": 1,     # day
                "confidence_factors": ["sudden_onset", "specific_pages_affected"]
            },
            "content_decay": {
                "indicators": ["gradual_traffic_decline", "position_erosion", "decreased_ctr"],
                "threshold": 0.1,  # 10% monthly decline
                "timeframe": 90,    # days
                "confidence_factors": ["competitor_improvements", "outdated_content"]
            },
            "seasonal_trend": {
                "indicators": ["yearly_pattern", "month_correlation", "industry_events"],
                "threshold": 0.2,  # 20% variation
                "timeframe": 365,   # days
                "confidence_factors": ["historical_match", "industry_benchmarks"]
            },
            "competitor_surge": {
                "indicators": ["position_loss", "impression_share_decline", "serp_features_loss"],
                "threshold": 0.15,  # 15% share loss
                "timeframe": 30,    # days
                "confidence_factors": ["new_competitor_content", "backlink_growth"]
            }
        }
    
    @staticmethod
    def get_industry_benchmarks() -> Dict[str, Dict[str, float]]:
        """Get industry-specific benchmarks for comparison"""
        return {
            "e-commerce": {
                "avg_ctr": 2.69,
                "avg_position": 15.2,
                "conversion_rate": 2.86,
                "bounce_rate": 45.0,
                "page_session": 3.2
            },
            "saas": {
                "avg_ctr": 3.12,
                "avg_position": 12.8,
                "conversion_rate": 7.0,
                "bounce_rate": 55.0,
                "page_session": 2.8
            },
            "blog": {
                "avg_ctr": 2.35,
                "avg_position": 18.5,
                "conversion_rate": 1.5,
                "bounce_rate": 65.0,
                "page_session": 1.9
            },
            "local_business": {
                "avg_ctr": 4.21,
                "avg_position": 8.3,
                "conversion_rate": 5.0,
                "bounce_rate": 40.0,
                "page_session": 2.5
            },
            "default": {
                "avg_ctr": 2.5,
                "avg_position": 15.0,
                "conversion_rate": 3.0,
                "bounce_rate": 50.0,
                "page_session": 2.5
            }
        }

class DataChunker:
    """Intelligent data chunking for optimal RAG performance"""
    
    def __init__(self, strategy: ChunkingStrategy = ChunkingStrategy.SEMANTIC):
        self.strategy = strategy
        self.chunk_size = 512  # Optimal for most embedding models
        
    def chunk_gsc_data(self, data: Dict[str, Any]) -> List[DataChunk]:
        """Chunk GSC data based on selected strategy"""
        if self.strategy == ChunkingStrategy.SEMANTIC:
            return self._semantic_chunking(data)
        elif self.strategy == ChunkingStrategy.TEMPORAL:
            return self._temporal_chunking(data)
        elif self.strategy == ChunkingStrategy.METRIC_BASED:
            return self._metric_based_chunking(data)
        else:
            return self._fixed_size_chunking(data)
    
    def _semantic_chunking(self, data: Dict[str, Any]) -> List[DataChunk]:
        """Group data by semantic meaning (pages, queries, topics)"""
        chunks = []
        
        # Chunk by top pages
        if "top_pages" in data:
            for page in data["top_pages"][:10]:
                chunk = DataChunk(
                    id=f"page_{hashlib.md5(page['page'].encode()).hexdigest()[:8]}",
                    content={
                        "type": "page_performance",
                        "url": page["page"],
                        "clicks": page["clicks"],
                        "impressions": page["impressions"],
                        "ctr": page["ctr"],
                        "position": page["position"]
                    },
                    metadata={
                        "category": "page",
                        "importance": "high" if page["clicks"] > 100 else "medium"
                    },
                    chunk_type=ChunkingStrategy.SEMANTIC
                )
                chunks.append(chunk)
        
        # Chunk by query groups
        if "top_queries" in data:
            query_groups = self._group_queries_by_intent(data["top_queries"])
            for intent, queries in query_groups.items():
                chunk = DataChunk(
                    id=f"queries_{intent}_{len(queries)}",
                    content={
                        "type": "query_group",
                        "intent": intent,
                        "queries": queries[:5],  # Top 5 per intent
                        "total_clicks": sum(q["clicks"] for q in queries),
                        "avg_position": np.mean([q["position"] for q in queries])
                    },
                    metadata={
                        "category": "queries",
                        "intent": intent,
                        "count": len(queries)
                    },
                    chunk_type=ChunkingStrategy.SEMANTIC
                )
                chunks.append(chunk)
        
        return chunks
    
    def _temporal_chunking(self, data: Dict[str, Any]) -> List[DataChunk]:
        """Group data by time periods for trend analysis"""
        chunks = []
        
        # Weekly performance chunks
        if "timeline_data" in data:
            timeline = data["timeline_data"]
            weekly_data = self._aggregate_by_week(timeline)
            
            for week_str, week_data in weekly_data.items():
                chunk = DataChunk(
                    id=f"week_{week_str}",
                    content={
                        "type": "weekly_performance",
                        "week": week_str,
                        "metrics": week_data,
                        "trend": self._calculate_trend(week_data)
                    },
                    metadata={
                        "category": "temporal",
                        "period": "week",
                        "date": week_str
                    },
                    chunk_type=ChunkingStrategy.TEMPORAL
                )
                chunks.append(chunk)
        
        return chunks
    
    def _metric_based_chunking(self, data: Dict[str, Any]) -> List[DataChunk]:
        """Group data by metric thresholds and anomalies"""
        chunks = []
        
        # High-performance content
        if "top_pages" in data:
            high_performers = [p for p in data["top_pages"] if p["ctr"] > 5.0]
            if high_performers:
                chunk = DataChunk(
                    id="high_ctr_pages",
                    content={
                        "type": "high_performers",
                        "pages": high_performers,
                        "avg_ctr": np.mean([p["ctr"] for p in high_performers])
                    },
                    metadata={
                        "category": "performance",
                        "threshold": "high_ctr"
                    },
                    chunk_type=ChunkingStrategy.METRIC_BASED
                )
                chunks.append(chunk)
        
        # Underperforming content
        if "top_pages" in data:
            low_performers = [p for p in data["top_pages"] if p["position"] > 20]
            if low_performers:
                chunk = DataChunk(
                    id="low_ranking_pages",
                    content={
                        "type": "low_performers",
                        "pages": low_performers,
                        "avg_position": np.mean([p["position"] for p in low_performers])
                    },
                    metadata={
                        "category": "performance",
                        "threshold": "poor_ranking"
                    },
                    chunk_type=ChunkingStrategy.METRIC_BASED
                )
                chunks.append(chunk)
        
        return chunks
    
    def _fixed_size_chunking(self, data: Dict[str, Any]) -> List[DataChunk]:
        """Traditional fixed-size chunking as fallback"""
        chunks = []
        data_str = json.dumps(data)
        
        for i in range(0, len(data_str), self.chunk_size):
            chunk_content = data_str[i:i+self.chunk_size]
            chunk = DataChunk(
                id=f"fixed_{i}",
                content={"raw": chunk_content},
                metadata={"category": "fixed", "offset": i},
                chunk_type=ChunkingStrategy.FIXED_SIZE
            )
            chunks.append(chunk)
        
        return chunks
    
    def _group_queries_by_intent(self, queries: List[Dict]) -> Dict[str, List[Dict]]:
        """Group queries by search intent"""
        intent_groups = defaultdict(list)
        
        for query in queries:
            intent = self._detect_query_intent(query["query"])
            intent_groups[intent].append(query)
        
        return dict(intent_groups)
    
    def _detect_query_intent(self, query: str) -> str:
        """Detect search intent from query"""
        query_lower = query.lower()
        
        # Transactional
        if any(word in query_lower for word in ["buy", "price", "cheap", "deal", "discount"]):
            return "transactional"
        
        # Informational
        elif any(word in query_lower for word in ["how", "what", "why", "guide", "tutorial"]):
            return "informational"
        
        # Navigational
        elif any(word in query_lower for word in ["login", "sign in", "homepage"]):
            return "navigational"
        
        # Commercial
        elif any(word in query_lower for word in ["best", "top", "review", "compare"]):
            return "commercial"
        
        return "general"
    
    def _aggregate_by_week(self, timeline: List[Dict]) -> Dict[str, Dict]:
        """Aggregate timeline data by week"""
        weekly = defaultdict(lambda: {"clicks": 0, "impressions": 0, "days": 0})
        
        for day_data in timeline:
            week_key = day_data["date"][:10]  # Simple week key
            weekly[week_key]["clicks"] += day_data.get("clicks", 0)
            weekly[week_key]["impressions"] += day_data.get("impressions", 0)
            weekly[week_key]["days"] += 1
        
        return dict(weekly)
    
    def _calculate_trend(self, data: Dict) -> str:
        """Calculate trend from data"""
        # Simplified trend calculation
        if data.get("clicks", 0) > 100:
            return "growing"
        elif data.get("clicks", 0) < 50:
            return "declining"
        return "stable"

class PatternDetector:
    """Detects patterns and anomalies in SEO data"""
    
    def __init__(self):
        self.knowledge_base = EnhancedSEOKnowledgeBase()
        
    def detect_patterns(
        self, 
        chunks: List[DataChunk],
        historical_data: Optional[Dict] = None
    ) -> List[SEOPattern]:
        """Detect patterns across data chunks"""
        patterns = []
        rules = self.knowledge_base.get_pattern_detection_rules()
        
        # Analyze temporal patterns
        temporal_chunks = [c for c in chunks if c.chunk_type == ChunkingStrategy.TEMPORAL]
        if temporal_chunks:
            patterns.extend(self._detect_temporal_patterns(temporal_chunks, rules))
        
        # Analyze metric-based patterns
        metric_chunks = [c for c in chunks if c.chunk_type == ChunkingStrategy.METRIC_BASED]
        if metric_chunks:
            patterns.extend(self._detect_metric_patterns(metric_chunks, rules))
        
        # Cross-chunk pattern analysis
        if len(chunks) > 3:
            patterns.extend(self._detect_cross_chunk_patterns(chunks, rules))
        
        return patterns
    
    def _detect_temporal_patterns(
        self, 
        chunks: List[DataChunk], 
        rules: Dict
    ) -> List[SEOPattern]:
        """Detect patterns in temporal data"""
        patterns = []
        
        # Check for traffic drops
        for i in range(1, len(chunks)):
            curr_chunk = chunks[i].content
            prev_chunk = chunks[i-1].content
            
            if "metrics" in curr_chunk and "metrics" in prev_chunk:
                curr_clicks = curr_chunk["metrics"].get("clicks", 0)
                prev_clicks = prev_chunk["metrics"].get("clicks", 0)
                
                if prev_clicks > 0:
                    change_rate = (curr_clicks - prev_clicks) / prev_clicks
                    
                    if change_rate < -0.3:  # 30% drop
                        pattern = SEOPattern(
                            pattern_type="traffic_drop",
                            confidence=min(0.9, abs(change_rate) * 2),
                            affected_metrics=["clicks", "impressions"],
                            time_range=(
                                datetime.now() - timedelta(days=7),
                                datetime.now()
                            ),
                            severity=IssueSeverity.HIGH if change_rate < -0.5 else IssueSeverity.MEDIUM,
                            evidence=[curr_chunk, prev_chunk]
                        )
                        patterns.append(pattern)
        
        return patterns
    
    def _detect_metric_patterns(
        self, 
        chunks: List[DataChunk], 
        rules: Dict
    ) -> List[SEOPattern]:
        """Detect patterns in metric-based data"""
        patterns = []
        
        for chunk in chunks:
            content = chunk.content
            
            # Detect underperformance pattern
            if content.get("type") == "low_performers":
                avg_position = content.get("avg_position", 0)
                if avg_position > 30:
                    pattern = SEOPattern(
                        pattern_type="severe_ranking_issues",
                        confidence=0.85,
                        affected_metrics=["position", "visibility"],
                        time_range=(
                            datetime.now() - timedelta(days=30),
                            datetime.now()
                        ),
                        severity=IssueSeverity.CRITICAL,
                        evidence=[content]
                    )
                    patterns.append(pattern)
        
        return patterns
    
    def _detect_cross_chunk_patterns(
        self, 
        chunks: List[DataChunk], 
        rules: Dict
    ) -> List[SEOPattern]:
        """Detect patterns across multiple chunks"""
        patterns = []
        
        # Collect all metrics
        all_metrics = defaultdict(list)
        for chunk in chunks:
            if "metrics" in chunk.content:
                for key, value in chunk.content["metrics"].items():
                    all_metrics[key].append(value)
        
        # Check for consistency issues
        for metric, values in all_metrics.items():
            if len(values) > 3:
                std_dev = np.std(values)
                mean_val = np.mean(values)
                
                if mean_val > 0 and std_dev / mean_val > 0.5:  # High variance
                    pattern = SEOPattern(
                        pattern_type="high_volatility",
                        confidence=0.7,
                        affected_metrics=[metric],
                        time_range=(
                            datetime.now() - timedelta(days=30),
                            datetime.now()
                        ),
                        severity=IssueSeverity.MEDIUM,
                        evidence=values[:5]
                    )
                    patterns.append(pattern)
        
        return patterns

class EnhancedRAGAnalyzer:
    """
    Enhanced RAG analyzer with advanced chunking, pattern detection, and confidence scoring
    """
    
    def __init__(self):
        self.db = SupabaseAuthDB()
        self.knowledge_base = EnhancedSEOKnowledgeBase()
        self.chunker = DataChunker(ChunkingStrategy.SEMANTIC)
        self.pattern_detector = PatternDetector()
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        self.embeddings_cache = {}
    
    async def analyze_audit_data(
        self, 
        audit_data: Dict[str, Any],
        website_url: str,
        industry: str = "default"
    ) -> List[EnhancedSEOIssue]:
        """
        Analyze audit data with enhanced RAG capabilities
        
        Args:
            audit_data: Raw audit data from GSC and analysis
            website_url: The website being analyzed
            industry: Industry category for benchmarking
            
        Returns:
            List of enhanced SEO issues with evidence and confidence scores
        """
        # Step 1: Intelligent chunking of data
        chunks = self.chunker.chunk_gsc_data(audit_data)
        
        # Step 2: Generate embeddings for semantic search (if needed)
        chunks = await self._generate_embeddings(chunks)
        
        # Step 3: Detect patterns and anomalies
        patterns = self.pattern_detector.detect_patterns(chunks)
        
        # Step 4: Extract metrics and compare with benchmarks
        metrics = self._extract_enhanced_metrics(audit_data)
        benchmarks = self.knowledge_base.get_industry_benchmarks()[industry]
        comparison = self._compare_with_benchmarks(metrics, benchmarks)
        
        # Step 5: Detect issues with confidence scoring
        detected_issues = self._detect_enhanced_issues(
            metrics, 
            patterns, 
            comparison,
            chunks
        )
        
        # Step 6: Enhance with AI insights using advanced prompting
        enhanced_issues = await self._enhance_with_advanced_ai(
            detected_issues,
            metrics,
            patterns,
            chunks,
            website_url,
            industry
        )
        
        # Step 7: Rank by confidence and business impact
        enhanced_issues = self._rank_issues_by_impact(enhanced_issues)
        
        # Return top 3 most impactful issues
        return enhanced_issues[:3]
    
    async def _generate_embeddings(self, chunks: List[DataChunk]) -> List[DataChunk]:
        """Generate embeddings for chunks (placeholder for vector search)"""
        # In production, you would use OpenAI embeddings or similar
        # For now, we'll use a simple hash-based approach
        for chunk in chunks:
            chunk_hash = chunk.get_hash()
            if chunk_hash not in self.embeddings_cache:
                # Simulate embedding generation
                chunk.embeddings = [float(ord(c)) for c in chunk_hash[:10]]
                self.embeddings_cache[chunk_hash] = chunk.embeddings
            else:
                chunk.embeddings = self.embeddings_cache[chunk_hash]
        
        return chunks
    
    def _extract_enhanced_metrics(self, audit_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract comprehensive metrics from audit data"""
        metrics = {
            "seo_score": audit_data.get("seo_score", 0),
            "clicks": audit_data.get("organic_traffic", 0),
            "impressions": audit_data.get("impressions", 0),
            "ctr": audit_data.get("ctr", 0),
            "avg_position": audit_data.get("avg_position", 0),
            "clicks_change": audit_data.get("clicks_change", 0),
            "impressions_change": audit_data.get("impressions_change", 0),
            "position_change": audit_data.get("position_change", 0),
            "keywords": audit_data.get("keywords", 0),
            "top_pages_count": len(audit_data.get("top_pages", [])),
            "top_queries_count": len(audit_data.get("top_queries", [])),
        }
        
        # Calculate additional derived metrics
        if metrics["impressions"] > 0:
            metrics["visibility_score"] = min(100, (metrics["impressions"] / 1000) * 10)
        else:
            metrics["visibility_score"] = 0
        
        if metrics["clicks"] > 0:
            metrics["engagement_score"] = min(100, metrics["ctr"] * 20)
        else:
            metrics["engagement_score"] = 0
        
        return metrics
    
    def _compare_with_benchmarks(
        self, 
        metrics: Dict[str, Any], 
        benchmarks: Dict[str, float]
    ) -> Dict[str, Dict[str, Any]]:
        """Compare metrics with industry benchmarks"""
        comparison = {}
        
        for key in ["avg_ctr", "avg_position"]:
            if key in benchmarks:
                metric_key = key.replace("avg_", "")
                if metric_key == "ctr":
                    current_value = metrics.get("ctr", 0)
                else:
                    current_value = metrics.get("avg_position", 0)
                
                benchmark_value = benchmarks[key]
                
                if benchmark_value > 0:
                    performance_ratio = current_value / benchmark_value
                    
                    comparison[key] = {
                        "current": current_value,
                        "benchmark": benchmark_value,
                        "ratio": performance_ratio,
                        "status": "above" if performance_ratio > 1 else "below",
                        "gap": abs(current_value - benchmark_value)
                    }
        
        return comparison
    
    def _detect_enhanced_issues(
        self,
        metrics: Dict[str, Any],
        patterns: List[SEOPattern],
        comparison: Dict[str, Dict[str, Any]],
        chunks: List[DataChunk]
    ) -> List[Dict[str, Any]]:
        """Detect issues with confidence scoring based on evidence"""
        issues = []
        
        # Critical: No visibility
        if metrics["impressions"] == 0:
            issues.append({
                "title": "Zero Search Visibility",
                "severity": IssueSeverity.CRITICAL,
                "category": "visibility",
                "confidence": 1.0,  # 100% confident
                "evidence": self._find_relevant_chunks(chunks, ["impressions", "visibility"]),
                "data": {
                    "impressions": 0,
                    "expected_minimum": 100,
                    "days_affected": 30
                }
            })
        
        # High: Poor CTR compared to benchmark
        elif "avg_ctr" in comparison and comparison["avg_ctr"]["status"] == "below":
            confidence = min(0.95, comparison["avg_ctr"]["gap"] / comparison["avg_ctr"]["benchmark"])
            issues.append({
                "title": "Below Industry CTR Standards",
                "severity": IssueSeverity.HIGH,
                "category": "engagement",
                "confidence": confidence,
                "evidence": self._find_relevant_chunks(chunks, ["ctr", "clicks"]),
                "data": {
                    "current_ctr": metrics["ctr"],
                    "industry_benchmark": comparison["avg_ctr"]["benchmark"],
                    "gap": comparison["avg_ctr"]["gap"]
                }
            })
        
        # Pattern-based issues
        for pattern in patterns:
            if pattern.severity in [IssueSeverity.CRITICAL, IssueSeverity.HIGH]:
                issues.append({
                    "title": self._pattern_to_title(pattern.pattern_type),
                    "severity": pattern.severity,
                    "category": self._pattern_to_category(pattern.pattern_type),
                    "confidence": pattern.confidence,
                    "evidence": pattern.evidence,
                    "data": {
                        "pattern_type": pattern.pattern_type,
                        "affected_metrics": pattern.affected_metrics,
                        "time_range": str(pattern.time_range)
                    }
                })
        
        # Low traffic with evidence
        if metrics["clicks"] < 100:
            relevant_chunks = self._find_relevant_chunks(chunks, ["clicks", "traffic"])
            confidence = 0.9 if len(relevant_chunks) > 2 else 0.7
            
            issues.append({
                "title": "Critically Low Organic Traffic",
                "severity": IssueSeverity.CRITICAL,
                "category": "traffic",
                "confidence": confidence,
                "evidence": relevant_chunks,
                "data": {
                    "current_clicks": metrics["clicks"],
                    "minimum_healthy": 100,
                    "visibility_score": metrics["visibility_score"]
                }
            })
        
        return issues
    
    def _find_relevant_chunks(
        self, 
        chunks: List[DataChunk], 
        keywords: List[str]
    ) -> List[DataChunk]:
        """Find chunks relevant to given keywords"""
        relevant = []
        
        for chunk in chunks:
            chunk_str = json.dumps(chunk.content).lower()
            relevance_score = sum(1 for kw in keywords if kw.lower() in chunk_str)
            
            if relevance_score > 0:
                chunk.relevance_score = relevance_score / len(keywords)
                relevant.append(chunk)
        
        # Sort by relevance and return top 3
        relevant.sort(key=lambda x: x.relevance_score, reverse=True)
        return relevant[:3]
    
    async def _enhance_with_advanced_ai(
        self,
        issues: List[Dict[str, Any]],
        metrics: Dict[str, Any],
        patterns: List[SEOPattern],
        chunks: List[DataChunk],
        website_url: str,
        industry: str
    ) -> List[EnhancedSEOIssue]:
        """Enhanced AI analysis with better prompting and evidence"""
        if not issues:
            return []
        
        # Prepare comprehensive context
        context = self._prepare_advanced_context(
            issues, metrics, patterns, chunks, website_url, industry
        )
        
        try:
            # Use advanced prompting with few-shot examples
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self._get_advanced_system_prompt()},
                    {"role": "user", "content": context}
                ],
                temperature=0.3,  # Lower temperature for more consistent output
                max_tokens=1500
            )
            
            # Parse and validate AI response
            ai_insights = self._parse_validated_response(response.choices[0].message.content)
            
            # Create enhanced issues with all evidence
            enhanced_issues = []
            for idx, issue in enumerate(issues):
                insight = ai_insights.get(idx, {})
                
                enhanced_issue = EnhancedSEOIssue(
                    title=issue["title"],
                    description=insight.get("description", "Analysis pending"),
                    severity=issue["severity"],
                    impact=insight.get("impact", "May affect SEO performance"),
                    recommendation=insight.get("recommendation", "Review and optimize"),
                    category=issue["category"],
                    data_points=issue.get("data", {}),
                    confidence_score=issue.get("confidence", 0.5),
                    evidence_chunks=issue.get("evidence", []),
                    patterns_detected=[p for p in patterns if p.severity == issue["severity"]],
                    temporal_context={"timeframe": "last_30_days"},
                    similar_sites_comparison={"industry": industry, "performance": "below_average"}
                )
                enhanced_issues.append(enhanced_issue)
            
            return enhanced_issues
            
        except Exception as e:
            logger.error(f"Advanced AI enhancement failed: {e}")
            # Return basic enhanced issues
            return self._create_fallback_issues(issues)
    
    def _prepare_advanced_context(
        self,
        issues: List[Dict[str, Any]],
        metrics: Dict[str, Any],
        patterns: List[SEOPattern],
        chunks: List[DataChunk],
        website_url: str,
        industry: str
    ) -> str:
        """Prepare comprehensive context for AI with evidence"""
        
        # Summarize evidence chunks
        evidence_summary = []
        for chunk in chunks[:5]:  # Top 5 most relevant
            if chunk.relevance_score > 0:
                evidence_summary.append({
                    "type": chunk.content.get("type", "unknown"),
                    "relevance": chunk.relevance_score,
                    "key_data": {
                        k: v for k, v in chunk.content.items() 
                        if k in ["clicks", "impressions", "ctr", "position"]
                    }
                })
        
        # Pattern summary
        pattern_summary = [
            {
                "type": p.pattern_type,
                "confidence": p.confidence,
                "severity": p.severity
            }
            for p in patterns[:3]
        ]
        
        return f"""
        Analyze these SEO issues for {website_url} ({industry} industry):
        
        CURRENT PERFORMANCE:
        - SEO Score: {metrics['seo_score']}/100
        - Monthly Clicks: {metrics['clicks']} (Change: {metrics['clicks_change']:.1f}%)
        - Monthly Impressions: {metrics['impressions']} (Change: {metrics['impressions_change']:.1f}%)
        - CTR: {metrics['ctr']:.2f}%
        - Average Position: {metrics['avg_position']:.1f}
        - Visibility Score: {metrics['visibility_score']}/100
        - Engagement Score: {metrics['engagement_score']}/100
        
        DETECTED PATTERNS:
        {json.dumps(pattern_summary, indent=2)}
        
        EVIDENCE CHUNKS:
        {json.dumps(evidence_summary, indent=2)}
        
        ISSUES TO ANALYZE:
        {json.dumps([{
            "title": i["title"],
            "severity": i["severity"],
            "confidence": i.get("confidence", 0.5),
            "data": i.get("data", {})
        } for i in issues], indent=2)}
        
        For each issue, provide:
        1. A clear, non-technical description of the problem
        2. The specific business impact (lost revenue, missed customers, competitive disadvantage)
        3. An actionable recommendation with timeline (quick win, short-term, long-term)
        4. Expected outcome if fixed (% improvement, timeframe)
        
        Format as JSON array with objects containing: description, impact, recommendation, expected_outcome
        """
    
    def _get_advanced_system_prompt(self) -> str:
        """Get advanced system prompt with few-shot examples"""
        return f"""
        You are an elite SEO consultant with 15+ years of experience analyzing enterprise websites.
        
        {self.knowledge_base.get_advanced_seo_context()}
        
        Your analysis must be:
        1. DATA-DRIVEN: Base all insights on provided metrics and evidence
        2. BUSINESS-FOCUSED: Translate technical issues into business impact
        3. ACTIONABLE: Provide specific steps, not generic advice
        4. REALISTIC: Set achievable expectations with timeframes
        
        Example of good analysis:
        {{
            "description": "Your website receives 45 monthly clicks despite 2,300 impressions, indicating that users see your site but don't find the titles compelling enough to click.",
            "impact": "You're losing approximately 50-70 potential customers monthly who see your business but choose competitors instead. At a typical conversion rate, this represents $5,000-10,000 in lost revenue.",
            "recommendation": "Rewrite your top 10 page titles to include emotional triggers and clear value propositions. Use power words like 'Ultimate', 'Essential', or 'Complete'. A/B test titles using Google Search Console data.",
            "expected_outcome": "CTR improvement from 2% to 4-5% within 4 weeks, doubling organic traffic to 90-100 clicks/month"
        }}
        
        Avoid vague statements like "improve content" or "optimize for SEO". 
        Always provide specific, measurable recommendations with expected outcomes.
        
        Respond only with valid JSON array format.
        """
    
    def _parse_validated_response(self, response: str) -> Dict[int, Dict[str, str]]:
        """Parse and validate AI response with fallback handling"""
        try:
            # Clean response
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]
            
            # Parse JSON
            insights = json.loads(response)
            
            # Validate structure
            if isinstance(insights, list):
                validated = {}
                for i, item in enumerate(insights):
                    if isinstance(item, dict):
                        validated[i] = {
                            "description": str(item.get("description", ""))[:500],
                            "impact": str(item.get("impact", ""))[:300],
                            "recommendation": str(item.get("recommendation", ""))[:400],
                            "expected_outcome": str(item.get("expected_outcome", ""))[:200]
                        }
                return validated
            
        except Exception as e:
            logger.warning(f"Failed to parse AI response: {e}")
        
        # Fallback response
        return {
            0: {
                "description": "SEO analysis indicates optimization opportunities",
                "impact": "Current performance is below optimal levels",
                "recommendation": "Implement SEO best practices for improvement",
                "expected_outcome": "Performance improvements expected within 4-8 weeks"
            }
        }
    
    def _create_fallback_issues(self, issues: List[Dict[str, Any]]) -> List[EnhancedSEOIssue]:
        """Create fallback enhanced issues when AI fails"""
        enhanced = []
        
        for issue in issues:
            enhanced_issue = EnhancedSEOIssue(
                title=issue["title"],
                description=f"Detected {issue['category']} issue requiring attention",
                severity=issue["severity"],
                impact="This issue may be affecting your search visibility",
                recommendation="Review and optimize based on SEO best practices",
                category=issue["category"],
                data_points=issue.get("data", {}),
                confidence_score=issue.get("confidence", 0.5),
                evidence_chunks=issue.get("evidence", [])
            )
            enhanced.append(enhanced_issue)
        
        return enhanced
    
    def _rank_issues_by_impact(
        self, 
        issues: List[EnhancedSEOIssue]
    ) -> List[EnhancedSEOIssue]:
        """Rank issues by business impact and confidence"""
        
        def calculate_impact_score(issue: EnhancedSEOIssue) -> float:
            severity_weights = {
                IssueSeverity.CRITICAL: 4.0,
                IssueSeverity.HIGH: 3.0,
                IssueSeverity.MEDIUM: 2.0,
                IssueSeverity.LOW: 1.0
            }
            
            severity_score = severity_weights.get(issue.severity, 1.0)
            confidence_weight = issue.confidence_score
            evidence_weight = min(1.0, len(issue.evidence_chunks) / 3)
            pattern_weight = min(1.0, len(issue.patterns_detected) / 2)
            
            return severity_score * confidence_weight * (1 + evidence_weight + pattern_weight)
        
        # Calculate impact scores
        for issue in issues:
            issue.impact_score = calculate_impact_score(issue)
        
        # Sort by impact score
        issues.sort(key=lambda x: x.impact_score, reverse=True)
        
        return issues
    
    def _pattern_to_title(self, pattern_type: str) -> str:
        """Convert pattern type to readable title"""
        titles = {
            "traffic_drop": "Significant Traffic Decline Detected",
            "algorithm_update": "Possible Algorithm Impact",
            "technical_issue": "Technical SEO Problems",
            "content_decay": "Content Performance Decay",
            "seasonal_trend": "Seasonal Traffic Pattern",
            "competitor_surge": "Competitive Pressure Increasing",
            "high_volatility": "Unstable Performance Metrics",
            "severe_ranking_issues": "Critical Ranking Problems"
        }
        return titles.get(pattern_type, "Performance Issue Detected")
    
    def _pattern_to_category(self, pattern_type: str) -> str:
        """Convert pattern type to category"""
        categories = {
            "traffic_drop": "traffic",
            "algorithm_update": "algorithm",
            "technical_issue": "technical",
            "content_decay": "content",
            "seasonal_trend": "seasonal",
            "competitor_surge": "competition",
            "high_volatility": "stability",
            "severe_ranking_issues": "visibility"
        }
        return categories.get(pattern_type, "general")

# Create singleton instance
enhanced_rag_analyzer = EnhancedRAGAnalyzer()