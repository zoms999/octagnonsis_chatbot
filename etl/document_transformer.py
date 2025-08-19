"""
Document Transformation Engine
Converts query results into thematic documents optimized for RAG system with semantic chunking
"""

import logging
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import json
from collections import defaultdict

from database.models import DocumentType
from monitoring.preference_metrics import get_preference_metrics_collector

logger = logging.getLogger(__name__)

class DocumentTransformationError(Exception):
    """Raised when document transformation fails"""
    def __init__(self, doc_type: str, error_message: str):
        self.doc_type = doc_type
        self.error_message = error_message
        super().__init__(f"Document transformation failed for {doc_type}: {error_message}")

@dataclass
class TransformedDocument:
    """Container for transformed document data"""
    doc_type: str
    content: Dict[str, Any]
    summary_text: str
    metadata: Dict[str, Any]
    embedding_vector: Optional[List[float]] = None  # 임베딩 단계에서 추가됨

class DocumentTransformer:
    """
    Transforms raw query results into semantic documents optimized for RAG with chunking strategy
    """
    
    def __init__(self):
        # Remove the old transformation_methods approach for better chunking flexibility
        pass
    
    def _safe_get(self, data: List[Dict[str, Any]], index: int = 0, default: Dict[str, Any] = None) -> Dict[str, Any]:
        if default is None:
            default = {}
        if not data or len(data) <= index:
            return default
        return data[index] if data[index] is not None else default
    
    def _safe_get_value(self, data: Dict[str, Any], key: str, default: Any = None) -> Any:
        return data.get(key, default) if data else default
    
    def _generate_hypothetical_questions(self, summary: str, doc_type: str, content: Dict[str, Any]) -> List[str]:
        """
        주어진 요약문을 바탕으로 LLM을 사용하여 가상 질문을 생성합니다.
        실제 구현에서는 LLM API 호출이 필요합니다.
        """
        # ----- 실제 구현 시 LLM 호출 예시 -----
        # from your_llm_library import generate_text
        # prompt = f"""
        # 아래 내용은 사용자의 검사 결과 데이터의 일부입니다.
        # 이 내용을 가장 잘 설명하고 요약하는 질문을 한국어로 3개만 생성해주세요.
        # 질문은 사용자가 챗봇에게 물어볼 법한 자연스러운 대화체여야 합니다.
        #
        # 내용: "{summary}"
        #
        # 질문 (3개):
        # 1.
        # 2.
        # 3.
        # """
        # generated_text = generate_text(prompt)
        # questions = [line.strip() for line in generated_text.split('\n') if line.strip()]
        # return questions
        # -----------------------------------------
        
        # 지금은 테스트를 위해 규칙 기반으로 예시 질문을 생성합니다.
        if "기본 정보" in summary:
            return ["내 나이랑 성별 알려줘", "내 기본 정보 요약해줘", "내가 누구인지 알려줘"]
        if "학력" in summary:
            return ["내 최종학력은 뭐야?", "내가 졸업한 학교랑 전공 알려줘", "학력 정보 보여줘"]
        if "직업 정보" in summary:
            return ["내 직업이 뭐야?", "지금 다니는 회사랑 직무 알려줘", "경력 정보 요약해줘"]
        if "주요 성향 분석" in summary:
            return ["내 성격 유형 알려줘", "나의 대표적인 성향은 뭐야?", "성격 검사 결과 요약해줘"]
        if "성향에 대한 상세 설명" in summary:
            tendency_name = content.get("name", "내 성향")
            return [f"{tendency_name} 성향은 어떤 특징이 있어?", f"{tendency_name}에 대해 자세히 설명해줘", f"내 성격 진단 결과 좀 더 알려줘"]
        if "주요 강점" in summary:
            return ["내 성격의 강점은 뭐야?", "내가 잘하는 건 뭐야?", "강점 분석 결과 보여줘"]
        if "개선 영역" in summary:
            return ["내 성격의 약점은 뭐야?", "내가 보완해야 할 점은?", "약점 분석 결과 알려줘"]
        if "사고력: 내 점수" in summary:
            skill_name = content.get("skill_name", "내 사고력")
            return [f"내 {skill_name} 점수는 몇 점이야?", f"나는 {skill_name}이 강한 편이야?", f"{skill_name} 분석 결과 알려줘"]
        if "성향 기반 추천 직업" in summary:
            return ["내 성향에 맞는 직업 추천해줘", "나한테 어울리는 직업이 뭐야?", "진로 추천 결과 알려줘"]
        if "역량 기반 추천 직업" in summary:
            return ["내 역량으로 갈 수 있는 직업은?", "내 강점을 살릴 수 있는 직업 추천해줘", "역량 기반 직업 추천 결과 보여줘"]
        
        # 더 구체적인 패턴 매칭 추가
        if "성향" in summary or "성격" in summary:
            return ["내성향알려줘", "내 성격은 어떤 타입이야?", "성향 분석 결과 보여줘"]
        if "사고력" in summary or "사고" in summary:
            return ["내 사고력은 어때?", "사고 능력 분석 결과 알려줘", "내가 어떤 사고를 잘해?"]
        if "직업" in summary or "진로" in summary:
            return ["추천 직업 알려줘", "나한테 맞는 직업이 뭐야?", "진로 추천해줘"]
        if "학습" in summary:
            return ["내 학습 스타일은?", "어떻게 공부하는 게 좋아?", "학습 방법 추천해줘"]
        if "역량" in summary or "능력" in summary:
            return ["내 강점은 뭐야?", "내가 잘하는 능력은?", "역량 분석 결과 알려줘"]
        
        return [summary]  # 매칭되는 규칙이 없으면 그냥 원본 요약문을 사용

    def _get_skill_level(self, percentile: float) -> str:
        """Determine skill level based on percentile"""
        if percentile >= 90: return "매우 우수 (상위 10%)"
        elif percentile >= 75: return "우수 (상위 25%)"
        elif percentile >= 50: return "보통 (상위 50%)"
        elif percentile >= 25: return "개선 필요"
        else: return "많은 개선 필요"

    # ==================== CHUNKING METHODS ====================
    # These methods create focused, topic-specific documents for better RAG performance
    
    def _generate_hypothetical_questions(self, summary: str, doc_type: str, content: Dict[str, Any]) -> List[str]:
        """주어진 요약문을 바탕으로 가상 질문을 생성합니다."""
        if "기본 정보" in summary:
            return ["내 기본 정보 요약해줘", "내 나이랑 직업 알려줘", "프로필 정보 보여줘"]
        if "학력" in summary:
            return ["내 학력 정보 알려줘", "어느 학교 다녔어?", "전공이 뭐야?"]
        if "직업 정보" in summary:
            return ["내 직업 정보 알려줘", "어디서 일해?", "무슨 일 해?"]
        if "성향 분석" in summary:
            primary = content.get("primary_tendency", {}).get("name", "내 성향")
            return [f"내 성격 유형 알려줘", f"나의 주요 성향은 뭐야?", f"{primary} 성향에 대해 설명해줘"]
        if "사고력" in summary:
            return ["내 사고력 점수 알려줘", "나는 어떤 사고를 잘해?", "사고력 분석 결과 요약해줘"]
        if "추천 직업" in summary or "직업" in summary:
            return ["나한테 맞는 직업 추천해줘", "내 성향에 어울리는 직업은?", "진로 추천 결과 알려줘"]
        if "학습 스타일" in summary:
            return ["나한테 맞는 공부 방법 알려줘", "내 학습 스타일은 어때?", "어떻게 공부해야 효율적일까?"]
        if "핵심 역량" in summary or "역량" in summary:
            return ["내가 가진 핵심 역량은 뭐야?", "나의 강점 역량 알려줘", "역량 분석 결과 보여줘"]
        if "선호도" in summary or "이미지" in summary:
            return ["내 선호도 분석 결과 알려줘", "이미지 선호도 검사 결과는?", "내가 선호하는 것들은 뭐야?"]
        # 기본 질문
        return [f"{summary}에 대해 알려줘", "결과를 자세히 설명해줘"]
    
    def _chunk_user_profile(self, query_results: Dict[str, List[Dict[str, Any]]]) -> List[TransformedDocument]:
        """Create focused user profile documents"""
        documents = []
        personal_info = self._safe_get(query_results.get("personalInfoQuery", []))
        institute_settings = self._safe_get(query_results.get("instituteSettingsQuery", []))
        
        if not personal_info or 'user_name' not in personal_info:
            # 개인정보 데이터가 없을 때 기본 문서 생성
            logger.warning("개인정보 데이터가 없어 기본 문서를 생성합니다.")
            documents.append(TransformedDocument(
                doc_type="USER_PROFILE",
                content={"message": "사용자 프로필 데이터가 아직 준비되지 않았습니다."},
                summary_text="사용자 프로필: 데이터 준비 중",
                metadata={"data_sources": [], "created_at": datetime.now().isoformat(), "sub_type": "unavailable"}
            ))
            return documents

        user_name = self._safe_get_value(personal_info, "user_name", "사용자")

        # 1. Basic Profile Document
        basic_content = {
            "user_name": user_name,
            "age": self._safe_get_value(personal_info, "age"),
            "gender": self._safe_get_value(personal_info, "gender"),
            "birth_date": self._safe_get_value(personal_info, "birth_date")
        }
        
        summary = f"{user_name}님의 기본 정보: {basic_content['age']}세, {basic_content['gender']}"
        documents.append(TransformedDocument(
            doc_type="USER_PROFILE",
            content=basic_content,
            summary_text=summary,
            metadata={"data_sources": ["personalInfoQuery"], "created_at": datetime.now().isoformat(), "sub_type": "basic_info"}
        ))

        # 2. Education Document
        education_info = {
            "education_level": self._safe_get_value(personal_info, "education_level"),
            "school_name": self._safe_get_value(personal_info, "school_name"),
            "school_year": self._safe_get_value(personal_info, "school_year"),
            "major": self._safe_get_value(personal_info, "major")
        }
        
        if education_info.get("school_name") or education_info.get("education_level"):
            edu_summary = f"{user_name}님의 학력: {education_info['education_level']}"
            if education_info.get("school_name"):
                edu_summary += f", {education_info['school_name']}"
            if education_info.get("major"):
                edu_summary += f"에서 {education_info['major']} 전공"
                
            documents.append(TransformedDocument(
                doc_type="USER_PROFILE",
                content=education_info,
                summary_text=edu_summary,
                metadata={"data_sources": ["personalInfoQuery"], "created_at": datetime.now().isoformat(), "sub_type": "education"}
            ))

        # 3. Career Document
        career_info = {
            "job_status": self._safe_get_value(personal_info, "job_status"),
            "company_name": self._safe_get_value(personal_info, "company_name"),
            "job_title": self._safe_get_value(personal_info, "job_title")
        }
        
        if career_info.get("job_status") or career_info.get("company_name"):
            career_summary = f"{user_name}님의 직업 정보: {career_info['job_status']}"
            if career_info.get("company_name"):
                career_summary += f", {career_info['company_name']}"
            if career_info.get("job_title"):
                career_summary += f"에서 {career_info['job_title']} 담당"
                
            documents.append(TransformedDocument(
                doc_type="USER_PROFILE",
                content=career_info,
                summary_text=career_summary,
                metadata={"data_sources": ["personalInfoQuery"], "created_at": datetime.now().isoformat(), "sub_type": "career"}
            ))

        return documents

    def _chunk_personality_analysis(self, query_results: Dict[str, List[Dict[str, Any]]]) -> List[TransformedDocument]:
        """Create detailed personality analysis documents"""
        documents = []
        
        # Main tendency summary
        tendency_data = self._safe_get(query_results.get("tendencyQuery", []))
        top_tendencies = query_results.get("topTendencyQuery", [])
        tendency_stats = query_results.get("tendencyStatsQuery", [])
        
        if tendency_data:
            primary = self._safe_get_value(tendency_data, "Tnd1")
            secondary = self._safe_get_value(tendency_data, "Tnd2")
            tertiary = self._safe_get_value(tendency_data, "Tnd3")
            
            # Find stats for each tendency
            primary_stats = next((s for s in tendency_stats if primary and s.get('tendency_name', '').startswith(primary)), {})
            secondary_stats = next((s for s in tendency_stats if secondary and s.get('tendency_name', '').startswith(secondary)), {})
            tertiary_stats = next((s for s in tendency_stats if tertiary and s.get('tendency_name', '').startswith(tertiary)), {})
            
            # 통계 데이터에서 각 성향의 비율 찾기
            stats_map = {}
            for stat in tendency_stats:
                tendency_name = stat.get('tendency_name', '').replace('형', '')
                stats_map[tendency_name] = stat.get('percentage', 0)
            
            content = {
                "primary_tendency": {"name": primary, "percentage": stats_map.get(primary, 0)},
                "secondary_tendency": {"name": secondary, "percentage": stats_map.get(secondary, 0)},
                "tertiary_tendency": {"name": tertiary, "percentage": stats_map.get(tertiary, 0)}
            }
            
            summary = f"주요 성향 분석: 1순위 {primary}({content['primary_tendency']['percentage']:.1f}%), 2순위 {secondary}({content['secondary_tendency']['percentage']:.1f}%)"
            if tertiary:
                summary += f", 3순위 {tertiary}({content['tertiary_tendency']['percentage']:.1f}%)"
                
            documents.append(TransformedDocument(
                doc_type="PERSONALITY_PROFILE",
                content=content,
                summary_text=summary,
                metadata={"data_sources": ["tendencyQuery", "tendencyStatsQuery"], "created_at": datetime.now().isoformat(), "sub_type": "main_tendencies"}
            ))
        else:
            # 성향 데이터가 없을 때는 빈 리스트 반환 (1단계에서 데이터 준비를 보장하므로)
            logger.warning("성향 분석 데이터가 없습니다.")
            return []

        # Individual tendency explanations
        tendency1_explain = self._safe_get(query_results.get("tendency1ExplainQuery", []))
        if tendency1_explain and tendency1_explain.get("explanation"):
            primary_name = self._safe_get_value(tendency_data, "Tnd1", "1순위 성향")
            documents.append(TransformedDocument(
                doc_type="PERSONALITY_PROFILE",
                content=tendency1_explain,
                summary_text=f"{primary_name} 성향에 대한 상세 설명: {tendency1_explain['explanation'][:100]}...",
                metadata={"data_sources": ["tendency1ExplainQuery"], "created_at": datetime.now().isoformat(), "sub_type": "tendency_1_explanation"}
            ))

        tendency2_explain = self._safe_get(query_results.get("tendency2ExplainQuery", []))
        if tendency2_explain and tendency2_explain.get("explanation"):
            secondary_name = self._safe_get_value(tendency_data, "Tnd2", "2순위 성향")
            documents.append(TransformedDocument(
                doc_type="PERSONALITY_PROFILE",
                content=tendency2_explain,
                summary_text=f"{secondary_name} 성향에 대한 상세 설명: {tendency2_explain['explanation'][:100]}...",
                metadata={"data_sources": ["tendency2ExplainQuery"], "created_at": datetime.now().isoformat(), "sub_type": "tendency_2_explanation"}
            ))

        # Top tendencies with detailed explanations
        top_tendency_explains = query_results.get("topTendencyExplainQuery", [])
        for i, explain_data in enumerate(top_tendency_explains[:5]):  # Top 5 only
            if explain_data.get("explanation"):
                documents.append(TransformedDocument(
                    doc_type="PERSONALITY_PROFILE",
                    content=explain_data,
                    summary_text=f"{explain_data.get('tendency_name', f'{i+1}순위 성향')} 상세 분석: {explain_data['explanation'][:100]}...",
                    metadata={"data_sources": ["topTendencyExplainQuery"], "created_at": datetime.now().isoformat(), "sub_type": f"top_tendency_detail_{i+1}"}
                ))

        # Top tendencies with detailed explanations
        top_tendency_explains = query_results.get("topTendencyExplainQuery", [])
        for i, explain_data in enumerate(top_tendency_explains[:5]):  # Top 5 only
            if explain_data.get("explanation"):
                documents.append(TransformedDocument(
                    doc_type="PERSONALITY_PROFILE",
                    content=explain_data,
                    summary_text=f"{explain_data.get('tendency_name', f'{i+1}순위 성향')} 상세 분석: {explain_data['explanation'][:100]}...",
                    metadata={"data_sources": ["topTendencyExplainQuery"], "created_at": datetime.now().isoformat(), "sub_type": f"top_tendency_detail_{i+1}"}
                ))

        # Strengths and weaknesses
        strengths_weaknesses = query_results.get("strengthsWeaknessesQuery", [])
        if strengths_weaknesses:
            strengths = [sw for sw in strengths_weaknesses if sw.get('type') == 'strength']
            weaknesses = [sw for sw in strengths_weaknesses if sw.get('type') == 'weakness']
            
            if strengths:
                strength_summary = f"주요 강점: {', '.join([s['description'][:50] for s in strengths[:3]])}"
                documents.append(TransformedDocument(
                    doc_type="PERSONALITY_PROFILE",
                    content={"strengths": strengths},
                    summary_text=strength_summary,
                    metadata={"data_sources": ["strengthsWeaknessesQuery"], "created_at": datetime.now().isoformat(), "sub_type": "strengths"}
                ))
            
            if weaknesses:
                weakness_summary = f"개선 영역: {', '.join([w['description'][:50] for w in weaknesses[:3]])}"
                documents.append(TransformedDocument(
                    doc_type="PERSONALITY_PROFILE",
                    content={"weaknesses": weaknesses},
                    summary_text=weakness_summary,
                    metadata={"data_sources": ["strengthsWeaknessesQuery"], "created_at": datetime.now().isoformat(), "sub_type": "weaknesses"}
                ))

        return documents

    def _chunk_thinking_skills(self, query_results: Dict[str, List[Dict[str, Any]]]) -> List[TransformedDocument]:
        """Create focused thinking skills documents"""
        documents = []
        
        # Main thinking skills summary
        thinking_main = self._safe_get(query_results.get("thinkingMainQuery", []))
        thinking_skills = query_results.get("thinkingSkillsQuery", [])
        
        if thinking_main:
            summary = f"주요 사고력: {thinking_main.get('main_thinking_skill')}, 부 사고력: {thinking_main.get('sub_thinking_skill')}, 총점: {thinking_main.get('total_score')}"
            documents.append(TransformedDocument(
                doc_type="THINKING_SKILLS",
                content=thinking_main,
                summary_text=summary,
                metadata={"data_sources": ["thinkingMainQuery"], "created_at": datetime.now().isoformat(), "sub_type": "summary"}
            ))
        elif thinking_skills:
            # thinkingSkillsQuery 데이터로 요약 생성
            skill_names = [skill.get('skill_name', '') for skill in thinking_skills[:3]]
            summary = f"사고력 분석: {', '.join(skill_names)} 등 {len(thinking_skills)}개 영역"
            documents.append(TransformedDocument(
                doc_type="THINKING_SKILLS",
                content={"skills": thinking_skills},
                summary_text=summary,
                metadata={"data_sources": ["thinkingSkillsQuery"], "created_at": datetime.now().isoformat(), "sub_type": "skills_overview"}
            ))

        # Detailed thinking skills comparison
        comparison_data = query_results.get("thinkingSkillComparisonQuery", [])
        if comparison_data:
            # Create individual documents for top skills
            sorted_skills = sorted(comparison_data, key=lambda x: x.get('my_score', 0), reverse=True)
            
            for i, skill in enumerate(sorted_skills[:5]):  # Top 5 skills
                skill_name = skill.get('skill_name')
                my_score = skill.get('my_score', 0)
                avg_score = skill.get('average_score', 0)
                
                summary = f"{skill_name} 사고력: 내 점수 {my_score}점, 평균 {avg_score}점"
                if my_score > avg_score:
                    summary += f" (평균보다 {my_score - avg_score}점 높음)"
                elif my_score < avg_score:
                    summary += f" (평균보다 {avg_score - my_score}점 낮음)"
                
                documents.append(TransformedDocument(
                    doc_type="THINKING_SKILLS",
                    content=skill,
                    summary_text=summary,
                    metadata={"data_sources": ["thinkingSkillComparisonQuery"], "created_at": datetime.now().isoformat(), "sub_type": f"skill_{i+1}", "skill_name": skill_name}
                ))

        # Detailed thinking explanations
        thinking_details = query_results.get("thinkingDetailQuery", [])
        for detail in thinking_details:
            if detail.get("explanation"):
                skill_name = detail.get('skill_name')
                documents.append(TransformedDocument(
                    doc_type="THINKING_SKILLS",
                    content=detail,
                    summary_text=f"{skill_name} 상세 분석: {detail['explanation'][:100]}...",
                    metadata={"data_sources": ["thinkingDetailQuery"], "created_at": datetime.now().isoformat(), "sub_type": "detail", "skill_name": skill_name}
                ))

        # Detailed thinking explanations
        thinking_details = query_results.get("thinkingDetailQuery", [])
        for detail in thinking_details:
            if detail.get("explanation"):
                skill_name = detail.get('skill_name')
                documents.append(TransformedDocument(
                    doc_type="THINKING_SKILLS",
                    content=detail,
                    summary_text=f"{skill_name} 상세 분석: {detail['explanation'][:100]}...",
                    metadata={"data_sources": ["thinkingDetailQuery"], "created_at": datetime.now().isoformat(), "sub_type": "detail", "skill_name": skill_name}
                ))

        return documents

    def _chunk_career_recommendations(self, query_results: Dict[str, List[Dict[str, Any]]]) -> List[TransformedDocument]:
        """Create separate documents for different types of career recommendations"""
        documents = []

        # Tendency-based job recommendations
        tendency_jobs = query_results.get("careerRecommendationQuery", [])
        if tendency_jobs:
            job_names = [job['job_name'] for job in tendency_jobs[:5]]
            summary = f"성향 기반 추천 직업: {', '.join(job_names)}"
            documents.append(TransformedDocument(
                doc_type="CAREER_RECOMMENDATIONS",
                content={"jobs": tendency_jobs, "recommendation_type": "tendency"},
                summary_text=summary,
                metadata={"data_sources": ["careerRecommendationQuery"], "created_at": datetime.now().isoformat(), "sub_type": "tendency_based"}
            ))

        # Competency-based job recommendations
        competency_jobs = query_results.get("competencyJobsQuery", [])
        if competency_jobs:
            job_names = [job['jo_name'] for job in competency_jobs[:5]]
            summary = f"역량 기반 추천 직업: {', '.join(job_names)}"
            documents.append(TransformedDocument(
                doc_type="CAREER_RECOMMENDATIONS",
                content={"jobs": competency_jobs, "recommendation_type": "competency"},
                summary_text=summary,
                metadata={"data_sources": ["competencyJobsQuery"], "created_at": datetime.now().isoformat(), "sub_type": "competency_based"}
            ))

        # Preference-based job recommendations
        preference_jobs = query_results.get("preferenceJobsQuery", [])
        if preference_jobs:
            # Group by preference type
            pref_groups = defaultdict(list)
            for job in preference_jobs:
                pref_groups[job.get('preference_type', 'unknown')].append(job)
            
            for pref_type, jobs in pref_groups.items():
                job_names = [job['jo_name'] for job in jobs[:3]]
                pref_name = jobs[0].get('preference_name', pref_type)
                summary = f"{pref_name} 선호도 기반 추천 직업: {', '.join(job_names)}"
                documents.append(TransformedDocument(
                    doc_type="CAREER_RECOMMENDATIONS",
                    content={"jobs": jobs, "preference_type": pref_type, "preference_name": pref_name},
                    summary_text=summary,
                    metadata={"data_sources": ["preferenceJobsQuery"], "created_at": datetime.now().isoformat(), "sub_type": f"preference_{pref_type}"}
                ))

        # Job majors recommendations
        job_majors = query_results.get("suitableJobMajorsQuery", [])
        if job_majors:
            summary = f"추천 직업별 관련 전공: {', '.join([jm['jo_name'] for jm in job_majors[:3]])}"
            documents.append(TransformedDocument(
                doc_type="CAREER_RECOMMENDATIONS",
                content={"job_majors": job_majors},
                summary_text=summary,
                metadata={"data_sources": ["suitableJobMajorsQuery"], "created_at": datetime.now().isoformat(), "sub_type": "related_majors"}
            ))

        # Duties recommendations
        duties = query_results.get("dutiesQuery", [])
        if duties:
            duty_names = [duty['du_name'] for duty in duties[:5]]
            summary = f"추천 직무: {', '.join(duty_names)}"
            documents.append(TransformedDocument(
                doc_type="CAREER_RECOMMENDATIONS",
                content={"duties": duties},
                summary_text=summary,
                metadata={"data_sources": ["dutiesQuery"], "created_at": datetime.now().isoformat(), "sub_type": "duties"}
            ))

        return documents

    def _chunk_competency_analysis(self, query_results: Dict[str, List[Dict[str, Any]]]) -> List[TransformedDocument]:
        """Create detailed competency analysis documents"""
        documents = []
        
        competencies = query_results.get("competencyAnalysisQuery", [])
        competency_subjects = query_results.get("competencySubjectsQuery", [])
        talent_list = self._safe_get(query_results.get("talentListQuery", []))

        # Overall competency summary
        if talent_list and talent_list.get("talent_summary"):
            documents.append(TransformedDocument(
                doc_type="COMPETENCY_ANALYSIS",
                content=talent_list,
                summary_text=f"핵심 역량 요약: {talent_list['talent_summary']}",
                metadata={"data_sources": ["talentListQuery"], "created_at": datetime.now().isoformat(), "sub_type": "summary"}
            ))
        elif competencies:
            # talentListQuery가 없어도 competencyAnalysisQuery가 있으면 요약 생성
            comp_names = [comp.get('competency_name', '') for comp in competencies[:5]]
            summary_text = f"핵심 역량 요약: {', '.join(comp_names)}"
            documents.append(TransformedDocument(
                doc_type="COMPETENCY_ANALYSIS",
                content={"competencies": competencies},
                summary_text=summary_text,
                metadata={"data_sources": ["competencyAnalysisQuery"], "created_at": datetime.now().isoformat(), "sub_type": "summary"}
            ))
        else:
            # 역량 데이터가 없을 때는 빈 리스트 반환
            logger.warning("역량 분석 데이터가 없습니다.")
            return []

        # Individual competency details
        subjects_by_competency = defaultdict(list)
        for sub in competency_subjects:
            subjects_by_competency[sub.get('competency_name', '')].append(sub)

        for comp in competencies:
            comp_name = comp.get('competency_name')
            if comp_name:
                related_subjects = subjects_by_competency.get(comp_name, [])
                content = {
                    "competency": comp,
                    "related_subjects": related_subjects
                }
                
                summary = f"{comp_name} 역량: {comp.get('score')}점 (상위 {comp.get('percentile')}%)"
                if related_subjects:
                    subject_names = [s['subject_name'] for s in related_subjects[:3]]
                    summary += f", 관련 과목: {', '.join(subject_names)}"
                
                documents.append(TransformedDocument(
                    doc_type="COMPETENCY_ANALYSIS",
                    content=content,
                    summary_text=summary,
                    metadata={"data_sources": ["competencyAnalysisQuery", "competencySubjectsQuery"], "created_at": datetime.now().isoformat(), "sub_type": f"competency_{comp.get('rank', 0)}", "competency_name": comp_name}
                ))

        return documents

    def _chunk_learning_style(self, query_results: Dict[str, List[Dict[str, Any]]]) -> List[TransformedDocument]:
        """Create learning style documents"""
        documents = []
        
        learning_style = self._safe_get(query_results.get("learningStyleQuery", []))
        learning_chart = query_results.get("learningStyleChartQuery", [])
        subject_ranks = query_results.get("subjectRanksQuery", [])

        if learning_style:
            # Main learning style document
            summary = f"학습 스타일: {learning_style.get('tnd1_name')} 기반"
            if learning_style.get('tnd1_study_tendency'):
                summary += f", 학습 성향: {learning_style['tnd1_study_tendency'][:50]}..."
            
            documents.append(TransformedDocument(
                doc_type="LEARNING_STYLE",
                content=learning_style,
                summary_text=summary,
                metadata={"data_sources": ["learningStyleQuery"], "created_at": datetime.now().isoformat(), "sub_type": "main"}
            ))

        # Subject recommendations
        if subject_ranks:
            top_subjects = subject_ranks[:5]
            subject_names = [s['subject_name'] for s in top_subjects]
            summary = f"추천 학습 과목: {', '.join(subject_names)}"
            
            documents.append(TransformedDocument(
                doc_type="LEARNING_STYLE",
                content={"subjects": top_subjects},
                summary_text=summary,
                metadata={"data_sources": ["subjectRanksQuery"], "created_at": datetime.now().isoformat(), "sub_type": "recommended_subjects"}
            ))

        # Learning method chart data
        if learning_chart:
            style_data = [item for item in learning_chart if item.get('item_type') == 'S']
            method_data = [item for item in learning_chart if item.get('item_type') == 'W']
            
            if style_data:
                documents.append(TransformedDocument(
                    doc_type="LEARNING_STYLE",
                    content={"style_data": style_data},
                    summary_text=f"학습 스타일 분석: {', '.join([s['item_name'] for s in style_data[:3]])}",
                    metadata={"data_sources": ["learningStyleChartQuery"], "created_at": datetime.now().isoformat(), "sub_type": "style_chart"}
                ))
            
            if method_data:
                documents.append(TransformedDocument(
                    doc_type="LEARNING_STYLE",
                    content={"method_data": method_data},
                    summary_text=f"학습 방법 분석: {', '.join([m['item_name'] for m in method_data[:3]])}",
                    metadata={"data_sources": ["learningStyleChartQuery"], "created_at": datetime.now().isoformat(), "sub_type": "method_chart"}
                ))

        # 학습 스타일 데이터가 전혀 없을 때 기본 문서 생성
        if not documents:
            logger.warning("학습 스타일 데이터가 없어 기본 문서를 생성합니다.")
            documents.append(TransformedDocument(
                doc_type="LEARNING_STYLE",
                content={"message": "학습 스타일 분석 데이터가 아직 준비되지 않았습니다."},
                summary_text="학습 스타일: 데이터 준비 중",
                metadata={"data_sources": [], "created_at": datetime.now().isoformat(), "sub_type": "unavailable"}
            ))

        return documents

    def _chunk_preference_analysis(self, query_results: Dict[str, List[Dict[str, Any]]]) -> List[TransformedDocument]:
        """Create enhanced preference analysis documents with intelligent fallback handling"""
        start_time = time.time()
        documents = []
        documents_created = 0
        documents_failed = 0
        
        # Get metrics collector for monitoring
        metrics_collector = get_preference_metrics_collector()
        
        # Extract all preference-related data
        preference_stats = self._safe_get(query_results.get("imagePreferenceStatsQuery", []))
        preference_data = query_results.get("preferenceDataQuery", [])
        preference_jobs = query_results.get("preferenceJobsQuery", [])
        
        # Track what data is available for intelligent fallback
        available_data = {
            "stats": bool(preference_stats and preference_stats.get('total_image_count')),
            "preferences": bool(preference_data),
            "jobs": bool(preference_jobs)
        }
        
        # Count available data components
        available_count = sum(available_data.values())
        
        # Calculate data completeness score
        data_completeness_score = available_count / 3.0
        
        # Create documents based on data availability
        try:
            if available_count == 0:
                # No preference data available - create comprehensive fallback document
                documents.append(self._create_preference_fallback_document(available_data))
                documents_created = 1
            elif available_count < 3:
                # Partial data available - create partial document + available data documents
                partial_content = {
                    "stats": preference_stats if available_data["stats"] else None,
                    "preferences": preference_data if available_data["preferences"] else None,
                    "jobs": preference_jobs if available_data["jobs"] else None
                }
                documents.append(self._create_partial_preference_document(available_data, partial_content))
                documents_created += 1
                
                # Create documents for available data
                if available_data["stats"]:
                    stats_docs = self._create_preference_stats_document(preference_stats, available_data)
                    documents.extend(stats_docs)
                    documents_created += len(stats_docs)
                if available_data["preferences"]:
                    pref_docs = self._create_preference_data_documents(preference_data, available_data)
                    documents.extend(pref_docs)
                    documents_created += len(pref_docs)
                if available_data["jobs"]:
                    job_docs = self._create_preference_jobs_documents(preference_jobs, available_data)
                    documents.extend(job_docs)
                    documents_created += len(job_docs)
            else:
                # All data available - create complete documents
                stats_docs = self._create_preference_stats_document(preference_stats, available_data)
                documents.extend(stats_docs)
                documents_created += len(stats_docs)
                
                pref_docs = self._create_preference_data_documents(preference_data, available_data)
                documents.extend(pref_docs)
                documents_created += len(pref_docs)
                
                job_docs = self._create_preference_jobs_documents(preference_jobs, available_data)
                documents.extend(job_docs)
                documents_created += len(job_docs)
                
                # Add completion summary document
                documents.append(self._create_preference_completion_summary(preference_stats, preference_data, preference_jobs))
                documents_created += 1
                
            success = True
            error_message = None
            
        except Exception as e:
            logger.error(f"Error creating preference documents: {e}")
            documents_failed = 1
            success = False
            error_message = str(e)
            
            # Create fallback error document
            documents.append(self._create_preference_error_document(str(e)))
            documents_created = 1
        
        # Record document creation metrics
        processing_time_ms = (time.time() - start_time) * 1000
        
        # Extract anp_seq from query results context if available
        anp_seq = getattr(self, '_current_anp_seq', 0)  # This would need to be set by the caller
        
        # Record metrics asynchronously
        import asyncio
        try:
            asyncio.create_task(metrics_collector.record_document_creation(
                anp_seq=anp_seq,
                documents_created=documents_created,
                documents_failed=documents_failed,
                total_processing_time_ms=processing_time_ms,
                data_completeness_score=data_completeness_score,
                success=success,
                error_message=error_message
            ))
        except Exception as e:
            logger.warning(f"Failed to record preference document metrics: {e}")
        
        return documents

    def _create_preference_error_document(self, error_message: str) -> TransformedDocument:
        """Create error document when preference processing fails"""
        content = {
            "error": True,
            "message": "선호도 분석 처리 중 오류가 발생했습니다.",
            "technical_details": error_message,
            "recommendations": [
                "잠시 후 다시 시도해 주세요.",
                "문제가 지속되면 관리자에게 문의하세요."
            ]
        }
        
        summary_text = "선호도 분석 처리 오류 - 기술적 문제로 인해 선호도 분석을 완료할 수 없습니다."
        
        return TransformedDocument(
            doc_type=DocumentType.PREFERENCE_ANALYSIS.value,
            content=content,
            summary_text=summary_text,
            metadata={
                "error": True,
                "timestamp": datetime.now().isoformat(),
                "processing_status": "failed"
            }
        )

    def _create_preference_completion_summary(self, stats: Dict[str, Any], preferences: List[Dict[str, Any]], jobs: List[Dict[str, Any]]) -> TransformedDocument:
        """Create summary document when all preference data is available"""
        
        # Extract key metrics
        response_rate = stats.get('response_rate', 0) if stats else 0
        pref_count = len(preferences) if preferences else 0
        job_count = len(jobs) if jobs else 0
        
        # Create comprehensive summary
        summary_text = f"선호도 분석 완료: {pref_count}개 선호 영역, {job_count}개 추천 직업"
        if response_rate:
            summary_text += f" (검사 응답률 {response_rate}%)"
        
        # Generate insights
        insights = []
        if response_rate >= 80:
            insights.append("검사가 충분히 완료되어 신뢰할 수 있는 분석 결과입니다.")
        if pref_count >= 5:
            insights.append("다양한 선호 영역이 식별되어 폭넓은 관심사를 보여줍니다.")
        if job_count >= 10:
            insights.append("많은 직업 옵션이 제시되어 선택의 폭이 넓습니다.")
        
        # Get top preferences
        top_preferences = []
        if preferences:
            sorted_prefs = sorted(preferences, key=lambda x: x.get('rank', 999))[:3]
            top_preferences = [p.get('preference_name', '') for p in sorted_prefs if p.get('preference_name')]
        
        content = {
            "completion_status": "완료",
            "response_rate": response_rate,
            "preference_count": pref_count,
            "job_count": job_count,
            "top_preferences": top_preferences,
            "insights": insights,
            "quality_score": self._calculate_preference_quality_score(response_rate, pref_count, job_count),
            "recommendation": "모든 선호도 분석 결과를 종합적으로 검토하여 진로 방향을 설정해보세요."
        }
        
        return TransformedDocument(
            doc_type="PREFERENCE_ANALYSIS",
            content=content,
            summary_text=summary_text,
            metadata={
                "data_sources": ["imagePreferenceStatsQuery", "preferenceDataQuery", "preferenceJobsQuery"], 
                "created_at": datetime.now().isoformat(), 
                "sub_type": "completion_summary",
                "completion_level": "complete",
                "quality_score": content["quality_score"]
            }
        )

    def _calculate_preference_quality_score(self, response_rate: float, pref_count: int, job_count: int) -> float:
        """Calculate quality score for preference analysis completeness"""
        score = 0.0
        
        # Response rate component (40% of score)
        if response_rate >= 90:
            score += 40
        elif response_rate >= 80:
            score += 35
        elif response_rate >= 70:
            score += 30
        elif response_rate >= 50:
            score += 20
        else:
            score += 10
        
        # Preference count component (30% of score)
        if pref_count >= 8:
            score += 30
        elif pref_count >= 5:
            score += 25
        elif pref_count >= 3:
            score += 20
        elif pref_count >= 1:
            score += 15
        
        # Job count component (30% of score)
        if job_count >= 15:
            score += 30
        elif job_count >= 10:
            score += 25
        elif job_count >= 5:
            score += 20
        elif job_count >= 1:
            score += 15
        
        return min(score, 100.0)

    def _create_preference_stats_document(self, preference_stats: Dict[str, Any], available_data: Dict[str, bool]) -> List[TransformedDocument]:
        """Create document for image preference test statistics with enhanced templates"""
        documents = []
        
        if available_data["stats"]:
            total_count = preference_stats.get('total_image_count', 0)
            response_count = preference_stats.get('response_count', 0)
            response_rate = preference_stats.get('response_rate', 0)
            
            summary = f"이미지 선호도 검사 통계: 총 {total_count}개 이미지 중 {response_count}개 응답 (응답률 {response_rate}%)"
            
            # Enhanced interpretation with actionable insights
            interpretation = self._generate_stats_interpretation(response_rate, total_count, response_count)
            
            # Add recommendations based on completion status
            recommendations = self._generate_stats_recommendations(response_rate)
            
            content = {
                **preference_stats,
                "interpretation": interpretation,
                "recommendations": recommendations,
                "completion_status": "완료" if response_rate >= 80 else "부분완료" if response_rate >= 50 else "미완료",
                "quality_indicator": self._get_quality_indicator(response_rate),
                "next_steps": self._get_stats_next_steps(response_rate)
            }
            
            documents.append(TransformedDocument(
                doc_type="PREFERENCE_ANALYSIS",
                content=content,
                summary_text=summary,
                metadata={
                    "data_sources": ["imagePreferenceStatsQuery"], 
                    "created_at": datetime.now().isoformat(), 
                    "sub_type": "test_stats",
                    "completion_level": "high" if response_rate >= 80 else "medium" if response_rate >= 50 else "low",
                    "response_rate": response_rate
                }
            ))
        
        return documents

    def _generate_stats_interpretation(self, response_rate: float, total_count: int, response_count: int) -> str:
        """Generate detailed interpretation of test statistics"""
        if response_rate >= 90:
            return (f"검사가 매우 충실히 완료되었습니다 ({response_count}/{total_count} 응답). "
                   "이는 매우 신뢰할 수 있는 선호도 분석 결과를 제공할 수 있으며, "
                   "개인의 선호 패턴을 정확하게 파악할 수 있습니다.")
        elif response_rate >= 80:
            return (f"검사가 충분히 완료되었습니다 ({response_count}/{total_count} 응답). "
                   "신뢰할 수 있는 선호도 분석 결과를 제공할 수 있으며, "
                   "주요 선호 경향을 명확하게 식별할 수 있습니다.")
        elif response_rate >= 60:
            return (f"검사가 어느 정도 완료되었습니다 ({response_count}/{total_count} 응답). "
                   "기본적인 선호도 경향을 파악할 수 있지만, "
                   "더 정확한 분석을 위해서는 추가 응답이 도움이 될 수 있습니다.")
        elif response_rate >= 40:
            return (f"검사가 부분적으로 완료되었습니다 ({response_count}/{total_count} 응답). "
                   "일반적인 선호 방향성은 파악할 수 있지만, "
                   "세부적인 선호도 분석의 정확도는 제한적일 수 있습니다.")
        else:
            return (f"검사 완료도가 낮습니다 ({response_count}/{total_count} 응답). "
                   "현재 결과로는 선호도 패턴을 정확히 파악하기 어려우며, "
                   "추가 검사 완료를 권장합니다.")

    def _generate_stats_recommendations(self, response_rate: float) -> List[str]:
        """Generate recommendations based on response rate"""
        if response_rate >= 80:
            return [
                "선호도 분석 결과를 자세히 검토해보세요",
                "추천된 직업들과 본인의 관심사를 비교해보세요",
                "다른 검사 결과와 종합하여 진로 방향을 설정해보세요"
            ]
        elif response_rate >= 60:
            return [
                "현재 결과를 참고하되, 추가 검사 완료를 고려해보세요",
                "다른 검사 결과와 함께 종합적으로 판단해보세요",
                "관심 있는 분야와 현재 결과를 비교해보세요"
            ]
        else:
            return [
                "검사를 더 완료하여 정확한 선호도 분석을 받아보세요",
                "현재는 다른 검사 결과를 우선적으로 참고하세요",
                "성향 분석이나 역량 분석 결과를 먼저 확인해보세요"
            ]

    def _get_quality_indicator(self, response_rate: float) -> str:
        """Get quality indicator based on response rate"""
        if response_rate >= 90:
            return "🟢 매우 높음"
        elif response_rate >= 80:
            return "🟢 높음"
        elif response_rate >= 60:
            return "🟡 보통"
        elif response_rate >= 40:
            return "🟠 낮음"
        else:
            return "🔴 매우 낮음"

    def _get_stats_next_steps(self, response_rate: float) -> List[str]:
        """Get next steps based on response rate"""
        if response_rate >= 80:
            return [
                "선호도 분석 상세 결과 확인",
                "추천 직업 목록 검토",
                "다른 검사 결과와 비교 분석"
            ]
        elif response_rate >= 60:
            return [
                "현재 선호도 결과 검토",
                "추가 검사 완료 고려",
                "성향 분석 결과와 비교"
            ]
        else:
            return [
                "검사 추가 완료",
                "다른 검사 결과 우선 확인",
                "성향 기반 직업 추천 검토"
            ]

    def _create_preference_data_documents(self, preference_data: List[Dict[str, Any]], available_data: Dict[str, bool]) -> List[TransformedDocument]:
        """Create enhanced documents for individual preference analysis results"""
        documents = []
        
        if available_data["preferences"]:
            # Create comprehensive overview document
            pref_names = [pref.get('preference_name', '') for pref in preference_data[:3] 
                         if pref and pref.get('preference_name')]
            
            if pref_names:
                overview_summary = f"선호도 분석 결과: {', '.join(pref_names)} 등 {len(preference_data)}개 선호 영역"
            else:
                overview_summary = f"선호도 분석 결과: {len(preference_data)}개 선호 영역"
            
            # Generate insights about preference patterns
            insights = self._generate_preference_insights(preference_data)
            
            documents.append(TransformedDocument(
                doc_type="PREFERENCE_ANALYSIS",
                content={
                    "preferences_overview": preference_data,
                    "total_preferences": len(preference_data),
                    "top_preferences": pref_names,
                    "insights": insights,
                    "preference_distribution": self._analyze_preference_distribution(preference_data),
                    "recommendations": self._generate_preference_overview_recommendations(preference_data)
                },
                summary_text=overview_summary,
                metadata={
                    "data_sources": ["preferenceDataQuery"], 
                    "created_at": datetime.now().isoformat(), 
                    "sub_type": "preferences_overview",
                    "completion_level": "high",
                    "preference_count": len(preference_data)
                }
            ))
            
            # Create enhanced individual preference documents
            for i, pref in enumerate(preference_data):
                if not pref:  # Skip None objects
                    continue
                pref_name = pref.get('preference_name')
                if pref_name and pref_name.strip():  # Check for non-empty name
                    rank = pref.get('rank', i + 1)
                    response_rate = pref.get('response_rate', 0)
                    description = pref.get('description', '')
                    
                    summary = f"{pref_name} 선호도: {rank}순위"
                    if response_rate:
                        summary += f", 응답률 {response_rate}%"
                    
                    # Enhanced analysis with career implications
                    analysis = self._generate_detailed_preference_analysis(pref_name, rank, description)
                    
                    # Career and development suggestions
                    career_implications = self._generate_career_implications(pref_name, rank)
                    
                    content = {
                        **pref,
                        "rank": rank,
                        "analysis": analysis,
                        "career_implications": career_implications,
                        "preference_strength": "강함" if rank == 1 else "보통" if rank <= 3 else "약함",
                        "development_suggestions": self._generate_development_suggestions(pref_name, rank),
                        "related_activities": self._suggest_related_activities(pref_name)
                    }
                    
                    documents.append(TransformedDocument(
                        doc_type="PREFERENCE_ANALYSIS",
                        content=content,
                        summary_text=summary,
                        metadata={
                            "data_sources": ["preferenceDataQuery"], 
                            "created_at": datetime.now().isoformat(), 
                            "sub_type": f"preference_{rank}",
                            "preference_name": pref_name,
                            "completion_level": "high",
                            "rank": rank
                        }
                    ))
        
        return documents

    def _generate_preference_insights(self, preference_data: List[Dict[str, Any]]) -> List[str]:
        """Generate insights about overall preference patterns"""
        insights = []
        
        # Filter out None objects first
        valid_preferences = [p for p in preference_data if p is not None]
        
        if len(valid_preferences) >= 8:
            insights.append("다양한 선호 영역이 식별되어 폭넓은 관심사와 적응력을 보여줍니다.")
        elif len(valid_preferences) >= 5:
            insights.append("적절한 수의 선호 영역이 있어 균형잡힌 관심사를 나타냅니다.")
        else:
            insights.append("명확한 선호 영역이 있어 집중적인 관심사를 보여줍니다.")
        
        # Analyze top preferences - handle None ranks
        top_prefs = sorted(valid_preferences, key=lambda x: x.get('rank') if x.get('rank') is not None else 999)[:3]
        if top_prefs:
            top_names = [p.get('preference_name', '') for p in top_prefs if p.get('preference_name')]
            if len(top_names) >= 2:
                insights.append(f"상위 선호도인 '{top_names[0]}'와 '{top_names[1]}'이 주요 관심 영역입니다.")
        
        return insights

    def _analyze_preference_distribution(self, preference_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze the distribution of preference strengths"""
        # Filter out None objects first
        valid_preferences = [p for p in preference_data if p is not None]
        
        strong_prefs = len([p for p in valid_preferences if (p.get('rank') or 999) <= 2])
        medium_prefs = len([p for p in valid_preferences if 3 <= (p.get('rank') or 999) <= 5])
        weak_prefs = len([p for p in valid_preferences if (p.get('rank') or 999) > 5])
        
        return {
            "strong_preferences": strong_prefs,
            "medium_preferences": medium_prefs,
            "weak_preferences": weak_prefs,
            "total_preferences": len(valid_preferences),
            "concentration_level": "집중형" if strong_prefs >= 3 else "균형형" if medium_prefs >= 3 else "분산형"
        }

    def _generate_preference_overview_recommendations(self, preference_data: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on overall preference pattern"""
        recommendations = []
        
        # Filter out None objects first
        valid_preferences = [p for p in preference_data if p is not None]
        
        top_prefs = sorted(valid_preferences, key=lambda x: x.get('rank') if x.get('rank') is not None else 999)[:3]
        if top_prefs:
            recommendations.append("상위 선호도 영역을 중심으로 진로 방향을 설정해보세요.")
            recommendations.append("선호도 기반 직업 추천을 확인하여 구체적인 직업을 탐색해보세요.")
        
        if len(valid_preferences) >= 5:
            recommendations.append("다양한 선호 영역을 활용할 수 있는 융합적 직업도 고려해보세요.")
        
        recommendations.append("성향 분석 결과와 비교하여 일치하는 부분을 확인해보세요.")
        
        return recommendations

    def _generate_detailed_preference_analysis(self, pref_name: str, rank: int, description: str) -> str:
        """Generate detailed analysis for individual preferences"""
        base_analysis = ""
        
        if rank == 1:
            base_analysis = f"'{pref_name}'은 가장 강한 선호를 보이는 영역입니다. "
            base_analysis += "이는 개인의 핵심적인 관심사이자 동기 요소로 작용할 가능성이 높습니다. "
        elif rank <= 3:
            base_analysis = f"'{pref_name}'은 상위 선호 영역 중 하나입니다. "
            base_analysis += "이 영역에 대한 관심과 적성이 있어 관련 활동에서 만족감을 느낄 수 있습니다. "
        elif rank <= 5:
            base_analysis = f"'{pref_name}'은 중간 정도의 선호를 보이는 영역입니다. "
            base_analysis += "상황에 따라 관심을 가질 수 있는 영역으로, 다른 요소와 결합하여 고려해볼 수 있습니다. "
        else:
            base_analysis = f"'{pref_name}'은 상대적으로 낮은 선호를 보이는 영역입니다. "
            base_analysis += "현재로서는 주요 관심사가 아니지만, 향후 경험을 통해 변화할 수 있습니다. "
        
        if description:
            base_analysis += f"구체적으로는 {description}"
        
        return base_analysis

    def _generate_career_implications(self, pref_name: str, rank: int) -> List[str]:
        """Generate career implications based on preference"""
        implications = []
        
        if rank <= 2:
            implications.append(f"{pref_name} 관련 직업을 우선적으로 고려해보세요.")
            implications.append("이 영역에서 전문성을 개발하면 높은 만족도를 얻을 수 있습니다.")
        elif rank <= 5:
            implications.append(f"{pref_name} 요소가 포함된 직업을 탐색해보세요.")
            implications.append("주 업무가 아니더라도 부분적으로 관련된 역할을 찾아보세요.")
        
        return implications

    def _generate_development_suggestions(self, pref_name: str, rank: int) -> List[str]:
        """Generate development suggestions based on preference"""
        suggestions = []
        
        if rank <= 3:
            suggestions.append(f"{pref_name} 관련 역량을 더욱 발전시켜보세요.")
            suggestions.append("관련 교육이나 경험 기회를 적극적으로 찾아보세요.")
            suggestions.append("이 영역의 전문가나 멘토를 찾아 조언을 구해보세요.")
        else:
            suggestions.append("다른 강점 영역에 더 집중하는 것을 권장합니다.")
            suggestions.append("필요시 기본적인 이해 수준으로 학습해보세요.")
        
        return suggestions

    def _suggest_related_activities(self, pref_name: str) -> List[str]:
        """Suggest activities related to the preference"""
        # This could be enhanced with a more sophisticated mapping
        activities = []
        
        if "실내" in pref_name or "조용" in pref_name:
            activities.extend(["독서", "연구", "분석 작업", "계획 수립"])
        elif "창의" in pref_name or "예술" in pref_name:
            activities.extend(["디자인", "글쓰기", "아이디어 발상", "예술 활동"])
        elif "사람" in pref_name or "소통" in pref_name:
            activities.extend(["팀 프로젝트", "발표", "상담", "교육"])
        elif "야외" in pref_name or "활동" in pref_name:
            activities.extend(["현장 업무", "체험 활동", "여행", "운동"])
        else:
            activities.extend(["관련 체험", "학습", "탐색"])
        
        return activities

    def _create_preference_jobs_documents(self, preference_jobs: List[Dict[str, Any]], available_data: Dict[str, bool]) -> List[TransformedDocument]:
        """Create enhanced documents for preference-based job recommendations"""
        documents = []
        
        if available_data["jobs"]:
            # Group jobs by preference type
            jobs_by_preference = {}
            for job in preference_jobs:
                if not job:  # Skip None objects
                    continue
                pref_type = job.get('preference_type', 'unknown')
                pref_name = job.get('preference_name')
                if not pref_name or not pref_name.strip():
                    pref_name = f'선호도 {pref_type}'
                
                if pref_name not in jobs_by_preference:
                    jobs_by_preference[pref_name] = []
                jobs_by_preference[pref_name].append(job)
            
            # Create overview document for all job recommendations
            if jobs_by_preference:
                total_jobs = sum(len(jobs) for jobs in jobs_by_preference.values())
                pref_types = list(jobs_by_preference.keys())
                
                overview_summary = f"선호도 기반 직업 추천: {len(pref_types)}개 선호 영역에서 총 {total_jobs}개 직업"
                
                documents.append(TransformedDocument(
                    doc_type="PREFERENCE_ANALYSIS",
                    content={
                        "total_jobs": total_jobs,
                        "preference_types": pref_types,
                        "jobs_by_preference": jobs_by_preference,
                        "overview_insights": self._generate_job_overview_insights(jobs_by_preference),
                        "career_diversity": self._assess_career_diversity(jobs_by_preference),
                        "recommendations": self._generate_job_overview_recommendations(jobs_by_preference)
                    },
                    summary_text=overview_summary,
                    metadata={
                        "data_sources": ["preferenceJobsQuery"], 
                        "created_at": datetime.now().isoformat(), 
                        "sub_type": "jobs_overview",
                        "completion_level": "high",
                        "job_count": total_jobs,
                        "preference_count": len(pref_types)
                    }
                ))
            
            # Create detailed documents for each preference type
            for pref_name, jobs in jobs_by_preference.items():
                job_names = [job.get('jo_name', '') for job in jobs[:3] if job.get('jo_name')]
                summary = f"{pref_name} 기반 추천 직업: {', '.join(job_names)}"
                if len(jobs) > 3:
                    summary += f" 등 {len(jobs)}개"
                
                # Enhanced analysis of job recommendations
                analysis = self._generate_comprehensive_job_analysis(pref_name, jobs)
                
                # Career path suggestions
                career_paths = self._suggest_career_paths(jobs)
                
                # Industry analysis
                industry_analysis = self._analyze_job_industries(jobs)
                
                content = {
                    "preference_name": pref_name,
                    "jobs": jobs,
                    "job_count": len(jobs),
                    "analysis": analysis,
                    "top_jobs": job_names,
                    "career_paths": career_paths,
                    "industry_analysis": industry_analysis,
                    "skill_requirements": self._extract_skill_requirements(jobs),
                    "education_recommendations": self._extract_education_recommendations(jobs),
                    "next_steps": self._suggest_job_exploration_steps(pref_name, jobs)
                }
                
                documents.append(TransformedDocument(
                    doc_type="PREFERENCE_ANALYSIS",
                    content=content,
                    summary_text=summary,
                    metadata={
                        "data_sources": ["preferenceJobsQuery"], 
                        "created_at": datetime.now().isoformat(), 
                        "sub_type": f"jobs_{pref_name.replace(' ', '_')}",
                        "preference_name": pref_name,
                        "completion_level": "high",
                        "job_count": len(jobs)
                    }
                ))
        
        return documents

    def _generate_job_overview_insights(self, jobs_by_preference: Dict[str, List[Dict[str, Any]]]) -> List[str]:
        """Generate insights about overall job recommendation patterns"""
        insights = []
        
        total_jobs = sum(len(jobs) for jobs in jobs_by_preference.values())
        pref_count = len(jobs_by_preference)
        
        if total_jobs >= 20:
            insights.append("매우 다양한 직업 옵션이 제시되어 선택의 폭이 넓습니다.")
        elif total_jobs >= 10:
            insights.append("적절한 수의 직업 옵션이 있어 구체적인 탐색이 가능합니다.")
        else:
            insights.append("명확한 직업 방향성이 제시되어 집중적인 탐색이 가능합니다.")
        
        if pref_count >= 4:
            insights.append("여러 선호 영역에서 직업이 추천되어 다양한 관심사를 반영합니다.")
        
        return insights

    def _assess_career_diversity(self, jobs_by_preference: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Assess the diversity of career recommendations"""
        all_jobs = []
        for jobs in jobs_by_preference.values():
            all_jobs.extend(jobs)
        
        # Extract industries (simplified)
        industries = set()
        for job in all_jobs:
            outline = job.get('jo_outline', '')
            if outline:
                industries.add(outline)
        
        return {
            "total_jobs": len(all_jobs),
            "unique_industries": len(industries),
            "diversity_score": min(len(industries) / max(len(all_jobs), 1) * 100, 100),
            "diversity_level": "높음" if len(industries) >= 8 else "보통" if len(industries) >= 4 else "낮음"
        }

    def _generate_job_overview_recommendations(self, jobs_by_preference: Dict[str, List[Dict[str, Any]]]) -> List[str]:
        """Generate recommendations for job exploration"""
        recommendations = []
        
        # Find preference with most jobs
        max_jobs_pref = max(jobs_by_preference.items(), key=lambda x: len(x[1]))
        recommendations.append(f"'{max_jobs_pref[0]}' 영역에서 가장 많은 직업이 추천되므로 우선적으로 탐색해보세요.")
        
        recommendations.extend([
            "각 선호 영역별 추천 직업을 자세히 검토해보세요.",
            "관심 있는 직업의 구체적인 업무 내용을 조사해보세요.",
            "추천 전공과 현재 전공/관심 분야를 비교해보세요.",
            "성향 기반 직업 추천과 비교하여 일치하는 직업을 찾아보세요."
        ])
        
        return recommendations

    def _generate_comprehensive_job_analysis(self, pref_name: str, jobs: List[Dict[str, Any]]) -> str:
        """Generate comprehensive analysis of job recommendations for a preference"""
        analysis = f"'{pref_name}' 선호도를 바탕으로 {len(jobs)}개의 직업이 추천되었습니다. "
        
        if len(jobs) >= 8:
            analysis += "매우 다양한 직업 옵션이 있어 선택의 폭이 넓고, 이 선호도가 여러 분야에서 활용될 수 있음을 보여줍니다. "
        elif len(jobs) >= 4:
            analysis += "적절한 수의 직업 옵션이 제공되어 구체적인 진로 탐색이 가능합니다. "
        else:
            analysis += "명확한 직업 방향성이 제시되어 집중적인 탐색이 가능합니다. "
        
        # Analyze job types
        job_outlines = [job.get('jo_outline', '') for job in jobs if job.get('jo_outline')]
        if job_outlines:
            unique_outlines = set(job_outlines)
            if len(unique_outlines) >= 5:
                analysis += "다양한 업무 영역에 걸쳐 추천되어 폭넓은 적용 가능성을 보여줍니다."
            else:
                analysis += "특정 업무 영역에 집중되어 명확한 전문성 방향을 제시합니다."
        
        return analysis

    def _suggest_career_paths(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Suggest career paths based on job recommendations"""
        paths = []
        
        # Group jobs by similar characteristics
        job_groups = {}
        for job in jobs:
            outline = job.get('jo_outline', '기타')
            if outline not in job_groups:
                job_groups[outline] = []
            job_groups[outline].append(job)
        
        for outline, group_jobs in job_groups.items():
            if len(group_jobs) >= 2:  # Only suggest paths with multiple jobs
                paths.append({
                    "path_name": f"{outline} 분야",
                    "jobs": [job.get('jo_name', '') for job in group_jobs],
                    "description": f"{outline} 영역에서의 다양한 직업 기회"
                })
        
        return paths

    def _analyze_job_industries(self, jobs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze industries represented in job recommendations"""
        industries = {}
        for job in jobs:
            outline = job.get('jo_outline', '기타')
            if outline not in industries:
                industries[outline] = []
            industries[outline].append(job.get('jo_name', ''))
        
        return {
            "industry_count": len(industries),
            "industries": industries,
            "dominant_industry": max(industries.items(), key=lambda x: len(x[1]))[0] if industries else None
        }

    def _extract_skill_requirements(self, jobs: List[Dict[str, Any]]) -> List[str]:
        """Extract common skill requirements from job recommendations"""
        skills = set()
        
        for job in jobs:
            # Extract from job main business
            main_business = job.get('jo_mainbusiness', '')
            if main_business:
                # Simple keyword extraction (could be enhanced)
                if '분석' in main_business:
                    skills.add('분석 능력')
                if '설계' in main_business:
                    skills.add('설계 능력')
                if '개발' in main_business:
                    skills.add('개발 능력')
                if '관리' in main_business:
                    skills.add('관리 능력')
                if '소통' in main_business or '상담' in main_business:
                    skills.add('소통 능력')
        
        return list(skills)

    def _extract_education_recommendations(self, jobs: List[Dict[str, Any]]) -> List[str]:
        """Extract education recommendations from job data"""
        majors = set()
        
        for job in jobs:
            major_info = job.get('majors', '')
            if major_info:
                # Split by common delimiters
                for delimiter in [',', '/', '·', '및']:
                    if delimiter in major_info:
                        major_parts = major_info.split(delimiter)
                        for part in major_parts:
                            clean_major = part.strip()
                            if clean_major:
                                majors.add(clean_major)
                        break
                else:
                    majors.add(major_info.strip())
        
        return list(majors)

    def _suggest_job_exploration_steps(self, pref_name: str, jobs: List[Dict[str, Any]]) -> List[str]:
        """Suggest specific steps for exploring these job recommendations"""
        steps = []
        
        if len(jobs) >= 5:
            steps.append("관심 있는 상위 3-5개 직업을 선별해보세요.")
        else:
            steps.append("모든 추천 직업을 자세히 검토해보세요.")
        
        steps.extend([
            "각 직업의 구체적인 업무 내용과 요구 역량을 조사해보세요.",
            "해당 분야 종사자와의 인터뷰나 멘토링을 고려해보세요.",
            "관련 교육 과정이나 자격증 정보를 확인해보세요.",
            "인턴십이나 체험 프로그램 기회를 찾아보세요."
        ])
        
        return steps

    def _create_preference_fallback_document(self, available_data: Dict[str, bool]) -> TransformedDocument:
        """Create informative fallback document when preference data is missing"""
        
        # Determine what specific data is missing and why
        missing_components = []
        if not available_data["stats"]:
            missing_components.append("이미지 선호도 검사 통계")
        if not available_data["preferences"]:
            missing_components.append("선호도 분석 결과")
        if not available_data["jobs"]:
            missing_components.append("선호도 기반 직업 추천")
        
        # Create helpful explanation based on what's missing
        explanation = self._generate_missing_data_explanation(missing_components)
        
        # Suggest alternatives based on available test results
        alternatives = self._generate_alternative_suggestions()
        
        # Provide specific recommendations
        recommendation = self._generate_specific_recommendations(missing_components)
        
        content = {
            "status": "데이터 준비 중",
            "missing_components": missing_components,
            "explanation": explanation,
            "alternatives": alternatives,
            "recommendation": recommendation,
            "data_availability": self._assess_data_availability(available_data),
            "next_steps": self._suggest_next_steps(missing_components)
        }
        
        return TransformedDocument(
            doc_type="PREFERENCE_ANALYSIS",
            content=content,
            summary_text="선호도 분석: 데이터 준비 중 - 다른 분석 결과 이용 가능",
            metadata={
                "data_sources": [], 
                "created_at": datetime.now().isoformat(), 
                "sub_type": "unavailable",
                "completion_level": "none",
                "has_alternatives": True,
                "missing_count": len(missing_components)
            }
        )

    def _generate_missing_data_explanation(self, missing_components: List[str]) -> str:
        """Generate detailed explanation for why preference data might be missing"""
        if len(missing_components) == 3:
            # All preference data is missing
            explanation = "현재 이미지 선호도 분석과 관련된 모든 데이터를 이용할 수 없습니다.\n\n"
            explanation += "이는 다음과 같은 이유일 수 있습니다:\n"
            explanation += "• 이미지 선호도 검사를 아직 시작하지 않았거나 완료하지 않았습니다\n"
            explanation += "• 검사는 완료했지만 결과 처리가 아직 진행 중입니다\n"
            explanation += "• 검사 응답률이 낮아 신뢰할 수 있는 분석이 어렵습니다\n"
            explanation += "• 일시적인 시스템 처리 지연이 발생했습니다\n"
            explanation += "• 검사 데이터에 오류가 있어 재처리가 필요합니다"
        elif len(missing_components) == 2:
            # Partial data missing
            explanation = f"현재 다음 선호도 분석 데이터를 이용할 수 없습니다:\n"
            explanation += "\n".join([f"• {component}" for component in missing_components])
            explanation += "\n\n이는 검사가 부분적으로만 완료되었거나, 일부 데이터 처리가 지연되고 있을 수 있습니다."
        else:
            # Single component missing
            component = missing_components[0]
            explanation = f"현재 {component} 데이터를 이용할 수 없습니다.\n\n"
            if "통계" in component:
                explanation += "검사 통계 정보는 처리 중이지만, 다른 선호도 분석 결과는 확인하실 수 있습니다."
            elif "분석 결과" in component:
                explanation += "선호도 분석은 처리 중이지만, 검사 통계와 직업 추천은 확인하실 수 있습니다."
            else:
                explanation += "직업 추천은 처리 중이지만, 다른 선호도 분석 결과는 확인하실 수 있습니다."
        
        return explanation

    def _generate_alternative_suggestions(self) -> str:
        """Generate suggestions for alternative test results to explore"""
        alternatives = "\n대신 다음 분석 결과를 확인하실 수 있습니다:\n\n"
        alternatives += "🔍 **성향 분석**\n"
        alternatives += "   • 개인의 성격 유형과 행동 패턴 분석\n"
        alternatives += "   • 주요 성향과 특성에 대한 상세한 설명\n"
        alternatives += "   • 성향 기반 강점과 개선 영역 파악\n\n"
        
        alternatives += "🧠 **사고력 분석**\n"
        alternatives += "   • 다양한 인지 능력과 사고 스타일 평가\n"
        alternatives += "   • 논리적, 창의적, 분석적 사고력 측정\n"
        alternatives += "   • 개인별 사고 강점 영역 식별\n\n"
        
        alternatives += "💪 **역량 분석**\n"
        alternatives += "   • 핵심 역량과 능력 평가\n"
        alternatives += "   • 직무별 적합성과 잠재력 분석\n"
        alternatives += "   • 개발 가능한 역량 영역 제시\n\n"
        
        alternatives += "💼 **직업 추천**\n"
        alternatives += "   • 성향과 역량 기반 직업 추천\n"
        alternatives += "   • 적합한 직무와 업무 환경 제안\n"
        alternatives += "   • 관련 전공과 학습 방향 안내\n\n"
        
        alternatives += "📚 **학습 스타일**\n"
        alternatives += "   • 개인에게 맞는 학습 방법 제안\n"
        alternatives += "   • 효과적인 공부 전략과 환경 추천\n"
        alternatives += "   • 추천 학습 과목과 분야 안내"
        
        return alternatives

    def _generate_specific_recommendations(self, missing_components: List[str]) -> str:
        """Generate specific recommendations based on what's missing"""
        if len(missing_components) == 3:
            return ("이미지 선호도 검사를 완료하지 않으셨다면 먼저 검사를 진행해보세요. "
                   "검사를 완료하셨다면 잠시 후 다시 확인해보시거나, "
                   "다른 분석 결과를 먼저 살펴보시는 것을 추천합니다.")
        elif len(missing_components) == 2:
            return ("일부 선호도 데이터는 처리 중입니다. "
                   "이용 가능한 다른 분석 결과를 먼저 확인해보시고, "
                   "선호도 분석은 잠시 후 다시 시도해보세요.")
        else:
            return ("대부분의 선호도 분석 결과는 이용 가능합니다. "
                   "현재 이용 가능한 결과를 먼저 확인해보시고, "
                   "누락된 부분은 잠시 후 다시 확인해보세요.")

    def _assess_data_availability(self, available_data: Dict[str, bool]) -> Dict[str, str]:
        """Assess and describe the availability of each data component"""
        availability = {}
        
        if available_data["stats"]:
            availability["검사_통계"] = "이용 가능"
        else:
            availability["검사_통계"] = "처리 중"
            
        if available_data["preferences"]:
            availability["선호도_분석"] = "이용 가능"
        else:
            availability["선호도_분석"] = "처리 중"
            
        if available_data["jobs"]:
            availability["직업_추천"] = "이용 가능"
        else:
            availability["직업_추천"] = "처리 중"
            
        return availability

    def _suggest_next_steps(self, missing_components: List[str]) -> List[str]:
        """Suggest specific next steps based on missing data"""
        steps = []
        
        if len(missing_components) == 3:
            steps.extend([
                "이미지 선호도 검사 완료 여부를 확인해보세요",
                "성향 분석 결과부터 확인해보세요",
                "사고력 분석으로 인지 능력을 파악해보세요",
                "역량 분석으로 강점 영역을 확인해보세요",
                "30분 후 선호도 분석을 다시 시도해보세요"
            ])
        elif "이미지 선호도 검사 통계" in missing_components:
            steps.extend([
                "이용 가능한 선호도 분석 결과를 먼저 확인해보세요",
                "검사 통계는 잠시 후 다시 확인해보세요"
            ])
        elif "선호도 분석 결과" in missing_components:
            steps.extend([
                "검사 통계를 통해 검사 완료 상태를 확인해보세요",
                "선호도 기반 직업 추천을 먼저 살펴보세요"
            ])
        else:
            steps.extend([
                "현재 이용 가능한 선호도 분석을 확인해보세요",
                "성향 기반 직업 추천과 비교해보세요"
            ])
            
        return steps

    def _create_partial_preference_document(self, available_data: Dict[str, bool], partial_content: Dict[str, Any]) -> TransformedDocument:
        """Create document for scenarios with partial preference data"""
        
        available_components = []
        missing_components = []
        
        if available_data["stats"]:
            available_components.append("이미지 선호도 검사 통계")
        else:
            missing_components.append("이미지 선호도 검사 통계")
            
        if available_data["preferences"]:
            available_components.append("선호도 분석 결과")
        else:
            missing_components.append("선호도 분석 결과")
            
        if available_data["jobs"]:
            available_components.append("선호도 기반 직업 추천")
        else:
            missing_components.append("선호도 기반 직업 추천")
        
        # Create informative content about partial availability
        explanation = f"선호도 분석이 부분적으로 완료되었습니다.\n\n"
        explanation += f"**이용 가능한 데이터:**\n"
        explanation += "\n".join([f"✅ {comp}" for comp in available_components])
        explanation += f"\n\n**처리 중인 데이터:**\n"
        explanation += "\n".join([f"⏳ {comp}" for comp in missing_components])
        
        explanation += "\n\n현재 이용 가능한 데이터로도 의미 있는 선호도 분석을 제공할 수 있습니다. "
        explanation += "누락된 데이터는 처리가 완료되는 대로 추가될 예정입니다."
        
        content = {
            "status": "부분 완료",
            "available_components": available_components,
            "missing_components": missing_components,
            "explanation": explanation,
            "partial_data": partial_content,
            "completion_percentage": (len(available_components) / 3) * 100,
            "recommendation": "현재 이용 가능한 선호도 분석을 먼저 확인해보시고, 추가 데이터는 잠시 후 다시 확인해보세요."
        }
        
        summary = f"선호도 분석: 부분 완료 ({len(available_components)}/3 항목 이용 가능)"
        
        return TransformedDocument(
            doc_type="PREFERENCE_ANALYSIS",
            content=content,
            summary_text=summary,
            metadata={
                "data_sources": [], 
                "created_at": datetime.now().isoformat(), 
                "sub_type": "partial_available",
                "completion_level": "partial",
                "available_count": len(available_components),
                "missing_count": len(missing_components)
            }
        )
    
    # ==================== MAIN TRANSFORMATION METHOD ====================
    async def transform_all_documents(
        self, 
        query_results: Dict[str, List[Dict[str, Any]]]
    ) -> List[TransformedDocument]:
        """
        Transform query results into semantically chunked documents optimized for RAG
        
        This method creates multiple focused documents instead of a few large ones,
        making it easier for the RAG system to find relevant information.
        """
        all_documents = []
        
        # Define chunking functions and their names for logging
        chunking_functions = [
            ("User Profile", self._chunk_user_profile),
            ("Personality Analysis", self._chunk_personality_analysis),
            ("Thinking Skills", self._chunk_thinking_skills),
            ("Career Recommendations", self._chunk_career_recommendations),
            ("Competency Analysis", self._chunk_competency_analysis),
            ("Learning Style", self._chunk_learning_style),
            ("Preference Analysis", self._chunk_preference_analysis),
        ]
        
        # Execute each chunking function
        for chunk_name, chunk_function in chunking_functions:
            try:
                logger.info(f"Processing {chunk_name} documents...")
                documents = chunk_function(query_results)
                
                # ▼▼▼ [핵심 추가] 생성된 모든 문서에 대해 가상 질문을 생성하고 메타데이터에 추가 ▼▼▼
                for doc in documents:
                    hypothetical_questions = self._generate_hypothetical_questions(
                        doc.summary_text, doc.doc_type, doc.content
                    )
                    doc.metadata['hypothetical_questions'] = hypothetical_questions
                    
                    # 검색에 사용될 텍스트는 이제 "요약문 + 가상질문들" 이 됩니다.
                    searchable_text = doc.summary_text + "\n" + "\n".join(hypothetical_questions)
                    doc.metadata['searchable_text'] = searchable_text
                # ▲▲▲ [핵심 추가 끝] ▲▲▲
                
                all_documents.extend(documents)
                logger.info(f"Created {len(documents)} {chunk_name} documents with hypothetical questions")
            except Exception as e:
                logger.error(f"Error processing {chunk_name}: {e}", exc_info=True)
                continue
        
        logger.info(f"Document transformation and chunking completed. Created {len(all_documents)} total documents.")
        
        # Log document type distribution for debugging
        doc_type_counts = defaultdict(int)
        for doc in all_documents:
            doc_type_counts[doc.doc_type] += 1
        
        logger.info(f"Document distribution: {dict(doc_type_counts)}")
        
        return all_documents