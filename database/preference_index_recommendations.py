"""
Database Index Recommendations for Preference Queries
Provides analysis and recommendations for optimizing preference-related database queries
through strategic index creation.
"""

import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from database.connection import db_manager
import structlog

logger = logging.getLogger(__name__)
index_logger = structlog.get_logger("preference_index_recommendations")

@dataclass
class IndexRecommendation:
    """Recommendation for creating a database index"""
    table_name: str
    index_name: str
    columns: List[str]
    index_type: str = "btree"  # btree, hash, gin, gist, etc.
    unique: bool = False
    partial_condition: Optional[str] = None
    priority: str = "medium"  # high, medium, low
    estimated_benefit: str = ""
    create_statement: str = ""
    rationale: str = ""
    
    def __post_init__(self):
        """Generate create statement after initialization"""
        if not self.create_statement:
            self.create_statement = self._generate_create_statement()
    
    def _generate_create_statement(self) -> str:
        """Generate SQL CREATE INDEX statement"""
        unique_clause = "UNIQUE " if self.unique else ""
        columns_clause = ", ".join(self.columns)
        
        statement = f"CREATE {unique_clause}INDEX CONCURRENTLY {self.index_name} ON {self.table_name}"
        
        if self.index_type != "btree":
            statement += f" USING {self.index_type}"
        
        statement += f" ({columns_clause})"
        
        if self.partial_condition:
            statement += f" WHERE {self.partial_condition}"
        
        statement += ";"
        
        return statement

@dataclass
class QueryAnalysis:
    """Analysis of a specific query pattern"""
    query_name: str
    table_name: str
    where_conditions: List[str]
    join_conditions: List[str]
    order_by_columns: List[str]
    estimated_rows_scanned: int
    execution_frequency: str  # high, medium, low
    current_performance: str  # slow, medium, fast

class PreferenceIndexAnalyzer:
    """Analyzes preference queries and provides index recommendations"""
    
    def __init__(self):
        self.recommendations: List[IndexRecommendation] = []
        self.query_analyses: List[QueryAnalysis] = []
    
    async def analyze_preference_queries(self) -> List[IndexRecommendation]:
        """Analyze all preference queries and generate index recommendations"""
        index_logger.info("Starting preference query analysis for index recommendations")
        
        # Analyze each preference query pattern
        await self._analyze_image_preference_stats_query()
        await self._analyze_preference_data_query()
        await self._analyze_preference_jobs_query()
        await self._analyze_supporting_queries()
        
        # Check existing indexes
        await self._check_existing_indexes()
        
        # Generate final recommendations
        self._prioritize_recommendations()
        
        index_logger.info(
            "Preference query analysis completed",
            total_recommendations=len(self.recommendations),
            high_priority=len([r for r in self.recommendations if r.priority == "high"]),
            medium_priority=len([r for r in self.recommendations if r.priority == "medium"]),
            low_priority=len([r for r in self.recommendations if r.priority == "low"])
        )
        
        return self.recommendations
    
    async def _analyze_image_preference_stats_query(self):
        """Analyze imagePreferenceStatsQuery performance"""
        # Query: SELECT rv_imgtcnt, rv_imgrcnt, rv_imgresrate FROM mwd_resval WHERE anp_seq = ?
        
        analysis = QueryAnalysis(
            query_name="imagePreferenceStatsQuery",
            table_name="mwd_resval",
            where_conditions=["anp_seq = ?"],
            join_conditions=[],
            order_by_columns=[],
            estimated_rows_scanned=1,  # Should return exactly 1 row
            execution_frequency="high",  # Called for every preference analysis
            current_performance="medium"
        )
        self.query_analyses.append(analysis)
        
        # Recommendation: Index on anp_seq for mwd_resval
        recommendation = IndexRecommendation(
            table_name="mwd_resval",
            index_name="idx_mwd_resval_anp_seq",
            columns=["anp_seq"],
            priority="high",
            estimated_benefit="Significant improvement for preference stats lookup",
            rationale="Primary key lookup for user preference statistics. Critical for all preference analysis operations."
        )
        self.recommendations.append(recommendation)
    
    async def _analyze_preference_data_query(self):
        """Analyze preferenceDataQuery performance"""
        # Complex query with joins on mwd_score1, mwd_question_attr, mwd_question_explain
        
        analysis = QueryAnalysis(
            query_name="preferenceDataQuery",
            table_name="mwd_score1",
            where_conditions=["anp_seq = ?", "sc1_step = 'img'", "sc1_rank <= 3"],
            join_conditions=[
                "mwd_question_attr ON qa.qua_code = sc1.qua_code",
                "mwd_question_explain ON qe.qua_code = qa.qua_code AND qe.que_switch = 1"
            ],
            order_by_columns=["sc1_rank"],
            estimated_rows_scanned=3,  # Top 3 preferences
            execution_frequency="high",
            current_performance="slow"
        )
        self.query_analyses.append(analysis)
        
        # Primary recommendation: Composite index on mwd_score1
        recommendation1 = IndexRecommendation(
            table_name="mwd_score1",
            index_name="idx_mwd_score1_preference_lookup",
            columns=["anp_seq", "sc1_step", "sc1_rank"],
            priority="high",
            estimated_benefit="Major improvement for preference data retrieval",
            rationale="Composite index covering all WHERE conditions and ORDER BY for preference data query. Eliminates table scan."
        )
        self.recommendations.append(recommendation1)
        
        # Supporting recommendation: Index on mwd_question_explain
        recommendation2 = IndexRecommendation(
            table_name="mwd_question_explain",
            index_name="idx_mwd_question_explain_lookup",
            columns=["qua_code", "que_switch"],
            priority="medium",
            estimated_benefit="Faster joins for question explanations",
            rationale="Optimizes join condition for question explanations in preference queries."
        )
        self.recommendations.append(recommendation2)
    
    async def _analyze_preference_jobs_query(self):
        """Analyze preferenceJobsQuery performance"""
        # Complex query with multiple joins: mwd_resjob, mwd_job, mwd_job_major_map, mwd_major, mwd_question_attr
        
        analysis = QueryAnalysis(
            query_name="preferenceJobsQuery",
            table_name="mwd_resjob",
            where_conditions=[
                "anp_seq = ?",
                "rej_kind IN ('rimg1', 'rimg2', 'rimg3')",
                "rej_rank <= 5"
            ],
            join_conditions=[
                "mwd_job ON jo.jo_code = rj.rej_code",
                "mwd_job_major_map ON jmm.jo_code = jo.jo_code",
                "mwd_major ON ma.ma_code = jmm.ma_code",
                "mwd_question_attr ON qa.qua_code = rj.rej_quacode"
            ],
            order_by_columns=["rej_kind", "rej_rank"],
            estimated_rows_scanned=15,  # 3 types * 5 jobs each
            execution_frequency="high",
            current_performance="slow"
        )
        self.query_analyses.append(analysis)
        
        # Primary recommendation: Composite index on mwd_resjob
        recommendation1 = IndexRecommendation(
            table_name="mwd_resjob",
            index_name="idx_mwd_resjob_preference_jobs",
            columns=["anp_seq", "rej_kind", "rej_rank"],
            priority="high",
            estimated_benefit="Significant improvement for preference job retrieval",
            rationale="Composite index covering all WHERE conditions and ORDER BY for preference jobs query."
        )
        self.recommendations.append(recommendation1)
        
        # Supporting recommendation: Index on mwd_job_major_map
        recommendation2 = IndexRecommendation(
            table_name="mwd_job_major_map",
            index_name="idx_mwd_job_major_map_jo_code",
            columns=["jo_code"],
            priority="medium",
            estimated_benefit="Faster joins for job-major relationships",
            rationale="Optimizes join performance for job-major mapping in preference queries."
        )
        self.recommendations.append(recommendation2)
        
        # Additional recommendation: Partial index for preference job types
        recommendation3 = IndexRecommendation(
            table_name="mwd_resjob",
            index_name="idx_mwd_resjob_preference_types",
            columns=["rej_kind", "rej_rank"],
            partial_condition="rej_kind IN ('rimg1', 'rimg2', 'rimg3')",
            priority="medium",
            estimated_benefit="Optimized filtering for preference job types",
            rationale="Partial index specifically for preference-related job recommendations."
        )
        self.recommendations.append(recommendation3)
    
    async def _analyze_supporting_queries(self):
        """Analyze supporting queries used in preference analysis"""
        
        # mwd_score1 general performance (used in multiple queries)
        recommendation1 = IndexRecommendation(
            table_name="mwd_score1",
            index_name="idx_mwd_score1_general",
            columns=["anp_seq", "sc1_step"],
            priority="high",
            estimated_benefit="Improves all score-based queries",
            rationale="General index for all score queries by user and step type."
        )
        self.recommendations.append(recommendation1)
        
        # mwd_question_attr performance
        recommendation2 = IndexRecommendation(
            table_name="mwd_question_attr",
            index_name="idx_mwd_question_attr_qua_code",
            columns=["qua_code"],
            priority="medium",
            estimated_benefit="Faster question attribute lookups",
            rationale="Primary key index for question attribute joins."
        )
        self.recommendations.append(recommendation2)
        
        # mwd_answer_progress for user lookups
        recommendation3 = IndexRecommendation(
            table_name="mwd_answer_progress",
            index_name="idx_mwd_answer_progress_anp_seq",
            columns=["anp_seq"],
            priority="high",
            estimated_benefit="Critical for user session lookups",
            rationale="Primary key index for answer progress, used in most user queries."
        )
        self.recommendations.append(recommendation3)
    
    async def _check_existing_indexes(self):
        """Check which recommended indexes already exist"""
        try:
            async with db_manager.get_async_session() as session:
                # Query to get existing indexes
                query = text("""
                    SELECT 
                        schemaname,
                        tablename,
                        indexname,
                        indexdef
                    FROM pg_indexes 
                    WHERE schemaname = 'public'
                    AND tablename IN ('mwd_resval', 'mwd_score1', 'mwd_resjob', 'mwd_job_major_map', 
                                     'mwd_question_attr', 'mwd_question_explain', 'mwd_answer_progress')
                    ORDER BY tablename, indexname
                """)
                
                result = await session.execute(query)
                existing_indexes = result.fetchall()
                
                existing_index_names = {row.indexname for row in existing_indexes}
                
                # Filter out recommendations for indexes that already exist
                filtered_recommendations = []
                for rec in self.recommendations:
                    if rec.index_name not in existing_index_names:
                        filtered_recommendations.append(rec)
                    else:
                        index_logger.info(
                            "Index already exists, skipping recommendation",
                            index_name=rec.index_name,
                            table_name=rec.table_name
                        )
                
                self.recommendations = filtered_recommendations
                
                index_logger.info(
                    "Existing index check completed",
                    total_existing=len(existing_indexes),
                    recommendations_filtered=len(self.recommendations)
                )
                
        except Exception as e:
            index_logger.error(
                "Failed to check existing indexes",
                error=str(e)
            )
    
    def _prioritize_recommendations(self):
        """Prioritize recommendations based on impact and frequency"""
        # Sort by priority (high -> medium -> low) and estimated benefit
        priority_order = {"high": 0, "medium": 1, "low": 2}
        
        self.recommendations.sort(
            key=lambda x: (priority_order.get(x.priority, 3), x.table_name, x.index_name)
        )
        
        # Update rationale with priority reasoning
        for i, rec in enumerate(self.recommendations):
            if rec.priority == "high":
                rec.rationale += " [HIGH PRIORITY: Critical for performance]"
            elif rec.priority == "medium":
                rec.rationale += " [MEDIUM PRIORITY: Moderate performance improvement]"
            else:
                rec.rationale += " [LOW PRIORITY: Minor performance improvement]"
    
    async def create_recommended_indexes(
        self, 
        recommendations: Optional[List[IndexRecommendation]] = None,
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """Create recommended indexes"""
        if recommendations is None:
            recommendations = self.recommendations
        
        results = {
            "created": [],
            "failed": [],
            "skipped": [],
            "dry_run": dry_run
        }
        
        if dry_run:
            index_logger.info(
                "DRY RUN: Would create the following indexes",
                count=len(recommendations)
            )
            for rec in recommendations:
                index_logger.info(
                    "DRY RUN: Index creation",
                    index_name=rec.index_name,
                    table_name=rec.table_name,
                    statement=rec.create_statement
                )
                results["skipped"].append({
                    "index_name": rec.index_name,
                    "table_name": rec.table_name,
                    "reason": "dry_run"
                })
            return results
        
        async with db_manager.get_async_session() as session:
            for rec in recommendations:
                try:
                    index_logger.info(
                        "Creating index",
                        index_name=rec.index_name,
                        table_name=rec.table_name,
                        priority=rec.priority
                    )
                    
                    await session.execute(text(rec.create_statement))
                    await session.commit()
                    
                    results["created"].append({
                        "index_name": rec.index_name,
                        "table_name": rec.table_name,
                        "priority": rec.priority
                    })
                    
                    index_logger.info(
                        "Index created successfully",
                        index_name=rec.index_name,
                        table_name=rec.table_name
                    )
                    
                except Exception as e:
                    await session.rollback()
                    
                    results["failed"].append({
                        "index_name": rec.index_name,
                        "table_name": rec.table_name,
                        "error": str(e)
                    })
                    
                    index_logger.error(
                        "Failed to create index",
                        index_name=rec.index_name,
                        table_name=rec.table_name,
                        error=str(e)
                    )
        
        index_logger.info(
            "Index creation completed",
            created=len(results["created"]),
            failed=len(results["failed"]),
            skipped=len(results["skipped"])
        )
        
        return results
    
    def generate_index_report(self) -> Dict[str, Any]:
        """Generate comprehensive index recommendation report"""
        return {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_recommendations": len(self.recommendations),
                "high_priority": len([r for r in self.recommendations if r.priority == "high"]),
                "medium_priority": len([r for r in self.recommendations if r.priority == "medium"]),
                "low_priority": len([r for r in self.recommendations if r.priority == "low"])
            },
            "recommendations": [
                {
                    "index_name": rec.index_name,
                    "table_name": rec.table_name,
                    "columns": rec.columns,
                    "index_type": rec.index_type,
                    "unique": rec.unique,
                    "partial_condition": rec.partial_condition,
                    "priority": rec.priority,
                    "estimated_benefit": rec.estimated_benefit,
                    "rationale": rec.rationale,
                    "create_statement": rec.create_statement
                }
                for rec in self.recommendations
            ],
            "query_analyses": [
                {
                    "query_name": qa.query_name,
                    "table_name": qa.table_name,
                    "where_conditions": qa.where_conditions,
                    "join_conditions": qa.join_conditions,
                    "order_by_columns": qa.order_by_columns,
                    "estimated_rows_scanned": qa.estimated_rows_scanned,
                    "execution_frequency": qa.execution_frequency,
                    "current_performance": qa.current_performance
                }
                for qa in self.query_analyses
            ]
        }

async def analyze_and_recommend_indexes() -> List[IndexRecommendation]:
    """Convenience function to analyze preference queries and get recommendations"""
    analyzer = PreferenceIndexAnalyzer()
    return await analyzer.analyze_preference_queries()

async def create_preference_indexes(dry_run: bool = True) -> Dict[str, Any]:
    """Convenience function to create all recommended preference indexes"""
    analyzer = PreferenceIndexAnalyzer()
    recommendations = await analyzer.analyze_preference_queries()
    return await analyzer.create_recommended_indexes(recommendations, dry_run=dry_run)