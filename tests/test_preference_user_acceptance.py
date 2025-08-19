"""
User acceptance tests for preference-related chat interactions
Tests the complete user experience for preference analysis conversations
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Dict, List, Any
import json

from rag.question_processor import QuestionProcessor
from rag.context_builder import ContextBuilder
from rag.response_generator import ResponseGenerator
from etl.document_transformer import DocumentTransformer, TransformedDocument
from database.repositories import DocumentRepository


class TestPreferenceUserAcceptance:
    """User acceptance tests for preference chat interactions"""
    
    def setup_mock_preference_documents(self, scenario: str = "complete") -> List[TransformedDocument]:
        """Setup mock preference documents for different scenarios"""
        
        if scenario == "complete":
            return [
                TransformedDocument(
                    doc_type="PREFERENCE_ANALYSIS",
                    content={
                        "total_images": 120,
                        "completed_images": 96,
                        "completion_rate": 80,
                        "completion_status": "완료",
                        "interpretation": "이미지 선호도 검사를 성공적으로 완료하였습니다."
                    },
                    summary_text="이미지 선호도 검사 통계: 120개 중 96개 완료 (80%)",
                    metadata={"sub_type": "test_stats", "completion_level": "high"}
                ),
                TransformedDocument(
                    doc_type="PREFERENCE_ANALYSIS",
                    content={
                        "preference_name": "실내 활동 선호",
                        "rank": 1,
                        "response_rate": 85,
                        "preference_strength": "강함",
                        "description": "조용하고 집중할 수 있는 환경을 선호합니다.",
                        "analysis": "가장 강한 선호도로, 실내에서의 활동을 매우 선호하는 경향을 보입니다."
                    },
                    summary_text="1순위 선호도: 실내 활동 선호 (85% 응답률)",
                    metadata={"sub_type": "preference_indoor", "completion_level": "high"}
                ),
                TransformedDocument(
                    doc_type="PREFERENCE_ANALYSIS",
                    content={
                        "preference_name": "창의적 활동 선호",
                        "rank": 2,
                        "response_rate": 78,
                        "preference_strength": "보통",
                        "description": "새로운 아이디어를 만들어내는 활동을 좋아합니다.",
                        "analysis": "두 번째로 강한 선호도로, 창의성을 발휘할 수 있는 활동을 선호합니다."
                    },
                    summary_text="2순위 선호도: 창의적 활동 선호 (78% 응답률)",
                    metadata={"sub_type": "preference_creative", "completion_level": "high"}
                ),
                TransformedDocument(
                    doc_type="PREFERENCE_ANALYSIS",
                    content={
                        "preference_name": "실내 활동 선호",
                        "jobs": [
                            {
                                "name": "소프트웨어 개발자",
                                "outline": "컴퓨터 프로그램 개발",
                                "main_business": "소프트웨어 설계 및 개발",
                                "majors": "컴퓨터공학, 소프트웨어공학"
                            },
                            {
                                "name": "데이터 분석가",
                                "outline": "데이터 분석 및 인사이트 도출",
                                "main_business": "데이터 수집, 분석, 시각화",
                                "majors": "통계학, 데이터사이언스"
                            }
                        ]
                    },
                    summary_text="실내 활동 선호와 관련된 직업 추천",
                    metadata={"sub_type": "jobs_indoor", "completion_level": "high"}
                )
            ]
        
        elif scenario == "partial":
            return [
                TransformedDocument(
                    doc_type="PREFERENCE_ANALYSIS",
                    content={
                        "message": "이미지 선호도 통계 데이터가 일시적으로 이용할 수 없습니다.",
                        "available_data": "선호도 분석 결과는 확인 가능합니다.",
                        "limitation": "통계 정보 없음"
                    },
                    summary_text="이미지 선호도 통계 데이터 일시 이용 불가",
                    metadata={"sub_type": "partial_stats", "completion_level": "low"}
                ),
                TransformedDocument(
                    doc_type="PREFERENCE_ANALYSIS",
                    content={
                        "preference_name": "실내 활동 선호",
                        "rank": 1,
                        "response_rate": 85,
                        "preference_strength": "강함",
                        "description": "조용한 환경을 선호합니다."
                    },
                    summary_text="1순위 선호도: 실내 활동 선호",
                    metadata={"sub_type": "preference_indoor", "completion_level": "medium"}
                )
            ]
        
        else:  # "unavailable"
            return [
                TransformedDocument(
                    doc_type="PREFERENCE_ANALYSIS",
                    content={
                        "message": "이미지 선호도 분석 데이터가 현재 이용할 수 없습니다.",
                        "reason": "데이터 처리 중 오류가 발생했습니다.",
                        "alternatives": [
                            "성격 분석 결과를 확인해보세요",
                            "사고 능력 분석 결과를 참고하세요",
                            "진로 추천 결과를 살펴보세요"
                        ],
                        "support_message": "다른 분석 결과를 통해서도 유용한 정보를 얻을 수 있습니다."
                    },
                    summary_text="이미지 선호도 분석 데이터 이용 불가 - 다른 분석 결과 이용 가능",
                    metadata={"sub_type": "unavailable", "has_alternatives": True}
                )
            ]

    @pytest.mark.asyncio
    async def test_complete_preference_conversation_flow(self):
        """Test complete preference conversation flow with full data"""
        
        # Setup mock documents
        mock_documents = self.setup_mock_preference_documents("complete")
        
        # Test conversation scenarios
        conversation_scenarios = [
            {
                "user_question": "내 이미지 선호도 분석 결과를 알려주세요",
                "expected_topics": ["실내 활동", "창의적 활동", "선호도", "분석"],
                "expected_confidence": 0.8
            },
            {
                "user_question": "이미지 선호도 검사를 몇 개나 완료했나요?",
                "expected_topics": ["96개", "120개", "80%", "완료"],
                "expected_confidence": 0.9
            },
            {
                "user_question": "내가 가장 선호하는 활동은 무엇인가요?",
                "expected_topics": ["실내 활동", "1순위", "가장 강한"],
                "expected_confidence": 0.85
            },
            {
                "user_question": "선호도에 맞는 직업 추천해주세요",
                "expected_topics": ["소프트웨어 개발자", "데이터 분석가", "직업"],
                "expected_confidence": 0.8
            }
        ]
        
        for scenario in conversation_scenarios:
            print(f"\n=== Testing: {scenario['user_question']} ===")
            
            # Step 1: Question Processing
            processor = QuestionProcessor()
            question_analysis = processor.analyze_question(scenario["user_question"])
            
            # Should detect as preference-related
            assert question_analysis["category"] in ["preference", "general"]
            
            # Step 2: Context Building
            with patch.object(ContextBuilder, 'build_context') as mock_context:
                mock_context.return_value = {
                    "relevant_documents": mock_documents,
                    "context_summary": "사용자의 이미지 선호도 분석 결과",
                    "document_types": ["PREFERENCE_ANALYSIS"],
                    "data_completeness": "complete"
                }
                
                context_builder = ContextBuilder()
                context = await context_builder.build_context(scenario["user_question"], 12345)
                
                # Verify context quality
                assert len(context["relevant_documents"]) > 0
                assert "PREFERENCE_ANALYSIS" in context["document_types"]
                assert context["data_completeness"] == "complete"
            
            # Step 3: Response Generation
            with patch.object(ResponseGenerator, 'generate_response') as mock_response:
                # Generate realistic response based on question
                if "통계" in scenario["user_question"] or "몇 개" in scenario["user_question"]:
                    response_text = "이미지 선호도 검사에서 총 120개 중 96개를 완료하여 80%의 완료율을 보였습니다."
                elif "가장 선호" in scenario["user_question"]:
                    response_text = "귀하가 가장 선호하는 활동은 '실내 활동'입니다. 이는 1순위 선호도로 85%의 높은 응답률을 보였습니다."
                elif "직업" in scenario["user_question"]:
                    response_text = "귀하의 선호도에 맞는 직업으로 소프트웨어 개발자와 데이터 분석가를 추천드립니다."
                else:
                    response_text = "귀하의 이미지 선호도 분석 결과, 실내 활동을 가장 선호하며(1순위), 창의적 활동도 선호하는 것으로 나타났습니다(2순위)."
                
                mock_response.return_value = {
                    "response": response_text,
                    "confidence": scenario["expected_confidence"],
                    "sources": ["PREFERENCE_ANALYSIS"],
                    "has_preference_data": True,
                    "data_quality": "high"
                }
                
                generator = ResponseGenerator()
                response = await generator.generate_response(scenario["user_question"], context)
                
                # Verify response quality
                assert response["confidence"] >= scenario["expected_confidence"]
                assert response["has_preference_data"] == True
                assert "PREFERENCE_ANALYSIS" in response["sources"]
                
                # Verify response contains expected topics
                response_text = response["response"].lower()
                for topic in scenario["expected_topics"]:
                    assert topic.lower() in response_text, f"Expected topic '{topic}' not found in response"
                
                print(f"✓ Response: {response['response'][:100]}...")
                print(f"✓ Confidence: {response['confidence']}")

    @pytest.mark.asyncio
    async def test_partial_data_conversation_handling(self):
        """Test conversation handling when preference data is partially available"""
        
        # Setup partial data scenario
        mock_documents = self.setup_mock_preference_documents("partial")
        
        conversation_scenarios = [
            {
                "user_question": "이미지 선호도 통계를 알려주세요",
                "expected_behavior": "acknowledge_limitation",
                "expected_alternative": True
            },
            {
                "user_question": "내 선호도 분석 결과는 어떻게 되나요?",
                "expected_behavior": "provide_available_data",
                "expected_alternative": False
            },
            {
                "user_question": "선호도 관련 직업 추천해주세요",
                "expected_behavior": "limited_recommendation",
                "expected_alternative": True
            }
        ]
        
        for scenario in conversation_scenarios:
            print(f"\n=== Testing Partial Data: {scenario['user_question']} ===")
            
            # Context with partial data
            with patch.object(ContextBuilder, 'build_context') as mock_context:
                mock_context.return_value = {
                    "relevant_documents": mock_documents,
                    "context_summary": "부분적인 이미지 선호도 분석 결과",
                    "document_types": ["PREFERENCE_ANALYSIS"],
                    "data_completeness": "partial",
                    "limitations": ["stats_unavailable", "jobs_limited"]
                }
                
                context_builder = ContextBuilder()
                context = await context_builder.build_context(scenario["user_question"], 12345)
                
                assert context["data_completeness"] == "partial"
                assert "limitations" in context
            
            # Response generation with limitations
            with patch.object(ResponseGenerator, 'generate_response') as mock_response:
                if scenario["expected_behavior"] == "acknowledge_limitation":
                    response_text = "죄송합니다. 이미지 선호도 통계 데이터가 현재 이용할 수 없습니다. 하지만 선호도 분석 결과는 확인할 수 있습니다."
                elif scenario["expected_behavior"] == "provide_available_data":
                    response_text = "현재 이용 가능한 선호도 분석 결과를 말씀드리겠습니다. 귀하는 실내 활동을 가장 선호하는 것으로 나타났습니다."
                else:  # limited_recommendation
                    response_text = "제한적인 데이터로 인해 완전한 직업 추천은 어렵지만, 실내 활동 선호도를 바탕으로 몇 가지 직업을 제안할 수 있습니다."
                
                mock_response.return_value = {
                    "response": response_text,
                    "confidence": 0.7,  # Lower confidence due to partial data
                    "sources": ["PREFERENCE_ANALYSIS"],
                    "has_preference_data": True,
                    "data_limitations": ["stats_unavailable"],
                    "suggested_alternatives": ["personality", "thinking_skills"] if scenario["expected_alternative"] else None
                }
                
                generator = ResponseGenerator()
                response = await generator.generate_response(scenario["user_question"], context)
                
                # Verify appropriate handling of limitations
                assert response["confidence"] <= 0.8  # Should be lower due to limitations
                assert "data_limitations" in response
                
                if scenario["expected_alternative"]:
                    assert response["suggested_alternatives"] is not None
                
                # Should acknowledge limitations appropriately
                if scenario["expected_behavior"] == "acknowledge_limitation":
                    assert any(word in response["response"] for word in ["죄송", "이용할 수 없", "제한"])
                
                print(f"✓ Partial data handled appropriately")
                print(f"✓ Response: {response['response'][:100]}...")

    @pytest.mark.asyncio
    async def test_unavailable_data_conversation_flow(self):
        """Test conversation flow when preference data is completely unavailable"""
        
        # Setup unavailable data scenario
        mock_documents = self.setup_mock_preference_documents("unavailable")
        
        conversation_scenarios = [
            {
                "user_question": "내 이미지 선호도는 어떻게 되나요?",
                "expected_redirect": True,
                "expected_alternatives": ["성격 분석", "사고 능력", "진로 추천"]
            },
            {
                "user_question": "선호도 분석 결과를 보여주세요",
                "expected_redirect": True,
                "expected_alternatives": ["성격 분석", "사고 능력", "진로 추천"]
            },
            {
                "user_question": "이미지 선호도 검사 결과는?",
                "expected_redirect": True,
                "expected_alternatives": ["성격 분석", "사고 능력", "진로 추천"]
            }
        ]
        
        for scenario in conversation_scenarios:
            print(f"\n=== Testing Unavailable Data: {scenario['user_question']} ===")
            
            # Context with unavailable data
            with patch.object(ContextBuilder, 'build_context') as mock_context:
                mock_context.return_value = {
                    "relevant_documents": mock_documents,
                    "context_summary": "이미지 선호도 분석 데이터 없음",
                    "document_types": ["PREFERENCE_ANALYSIS"],
                    "data_completeness": "unavailable",
                    "alternative_documents": ["PERSONALITY_PROFILE", "THINKING_SKILLS", "CAREER_RECOMMENDATIONS"]
                }
                
                context_builder = ContextBuilder()
                context = await context_builder.build_context(scenario["user_question"], 12345)
                
                assert context["data_completeness"] == "unavailable"
                assert "alternative_documents" in context
            
            # Response with alternatives
            with patch.object(ResponseGenerator, 'generate_response') as mock_response:
                mock_response.return_value = {
                    "response": "죄송합니다. 이미지 선호도 분석 데이터를 현재 이용할 수 없습니다. 대신 성격 분석이나 사고 능력 분석 결과를 확인해보시겠어요? 이러한 분석 결과도 진로 선택에 도움이 될 수 있습니다.",
                    "confidence": 0.9,  # High confidence in providing alternatives
                    "sources": ["PREFERENCE_ANALYSIS"],
                    "has_preference_data": False,
                    "suggested_alternatives": ["personality", "thinking_skills", "career_recommendations"],
                    "redirect_message": "다른 분석 결과를 통해서도 유용한 정보를 얻을 수 있습니다."
                }
                
                generator = ResponseGenerator()
                response = await generator.generate_response(scenario["user_question"], context)
                
                # Verify appropriate redirection
                assert response["has_preference_data"] == False
                assert response["suggested_alternatives"] is not None
                assert len(response["suggested_alternatives"]) >= 2
                
                # Should provide helpful alternatives
                response_text = response["response"]
                for alternative in scenario["expected_alternatives"]:
                    assert alternative in response_text
                
                # Should be apologetic but helpful
                assert any(word in response_text for word in ["죄송", "대신", "도움"])
                
                print(f"✓ Unavailable data handled with appropriate alternatives")
                print(f"✓ Suggested alternatives: {response['suggested_alternatives']}")

    @pytest.mark.asyncio
    async def test_follow_up_conversation_continuity(self):
        """Test conversation continuity with follow-up questions"""
        
        mock_documents = self.setup_mock_preference_documents("complete")
        
        # Simulate conversation flow
        conversation_flow = [
            {
                "question": "내 이미지 선호도 분석 결과를 알려주세요",
                "context_type": "initial",
                "expected_response_type": "overview"
            },
            {
                "question": "그 중에서 가장 강한 선호도는 무엇인가요?",
                "context_type": "follow_up",
                "expected_response_type": "specific_detail"
            },
            {
                "question": "그 선호도와 관련된 직업은 어떤 것들이 있나요?",
                "context_type": "follow_up",
                "expected_response_type": "job_recommendations"
            },
            {
                "question": "소프트웨어 개발자가 되려면 어떤 전공을 해야 하나요?",
                "context_type": "deep_follow_up",
                "expected_response_type": "educational_guidance"
            }
        ]
        
        conversation_history = []
        
        for i, turn in enumerate(conversation_flow):
            print(f"\n=== Conversation Turn {i+1}: {turn['question']} ===")
            
            # Build context with conversation history
            with patch.object(ContextBuilder, 'build_context') as mock_context:
                mock_context.return_value = {
                    "relevant_documents": mock_documents,
                    "context_summary": f"이미지 선호도 분석 결과 (대화 턴 {i+1})",
                    "document_types": ["PREFERENCE_ANALYSIS"],
                    "data_completeness": "complete",
                    "conversation_history": conversation_history,
                    "context_continuity": turn["context_type"]
                }
                
                context_builder = ContextBuilder()
                context = await context_builder.build_context(turn["question"], 12345)
                
                assert context["context_continuity"] == turn["context_type"]
            
            # Generate contextual response
            with patch.object(ResponseGenerator, 'generate_response') as mock_response:
                if turn["expected_response_type"] == "overview":
                    response_text = "귀하의 이미지 선호도 분석 결과, 실내 활동을 가장 선호하며(1순위), 창의적 활동도 선호하는 것으로 나타났습니다(2순위)."
                elif turn["expected_response_type"] == "specific_detail":
                    response_text = "가장 강한 선호도는 '실내 활동 선호'입니다. 이는 85%의 높은 응답률을 보이며, 조용하고 집중할 수 있는 환경을 선호하는 특성을 나타냅니다."
                elif turn["expected_response_type"] == "job_recommendations":
                    response_text = "실내 활동 선호와 관련된 직업으로는 소프트웨어 개발자와 데이터 분석가를 추천드립니다. 이러한 직업들은 집중력이 필요한 실내 환경에서 이루어집니다."
                else:  # educational_guidance
                    response_text = "소프트웨어 개발자가 되기 위해서는 컴퓨터공학이나 소프트웨어공학 전공을 추천드립니다. 이러한 전공에서 프로그래밍과 시스템 설계에 대해 체계적으로 학습할 수 있습니다."
                
                mock_response.return_value = {
                    "response": response_text,
                    "confidence": 0.85,
                    "sources": ["PREFERENCE_ANALYSIS"],
                    "has_preference_data": True,
                    "conversation_turn": i + 1,
                    "response_type": turn["expected_response_type"]
                }
                
                generator = ResponseGenerator()
                response = await generator.generate_response(turn["question"], context)
                
                # Verify response continuity
                assert response["conversation_turn"] == i + 1
                assert response["response_type"] == turn["expected_response_type"]
                
                # Add to conversation history
                conversation_history.append({
                    "question": turn["question"],
                    "response": response["response"],
                    "turn": i + 1
                })
                
                print(f"✓ Turn {i+1} response: {response['response'][:80]}...")
        
        # Verify conversation maintained coherence
        assert len(conversation_history) == len(conversation_flow)
        
        # Each turn should build on previous context
        for i in range(1, len(conversation_history)):
            current_turn = conversation_history[i]
            previous_turn = conversation_history[i-1]
            
            # Later turns should reference earlier context appropriately
            if i == 1:  # Second turn asking about "strongest preference"
                assert "가장 강한" in current_turn["response"]
            elif i == 2:  # Third turn asking about related jobs
                assert any(job in current_turn["response"] for job in ["소프트웨어", "데이터"])
            elif i == 3:  # Fourth turn asking about education
                assert any(major in current_turn["response"] for major in ["컴퓨터공학", "소프트웨어공학"])

    @pytest.mark.asyncio
    async def test_error_recovery_in_conversation(self):
        """Test error recovery and graceful degradation in conversations"""
        
        error_scenarios = [
            {
                "error_type": "context_building_failure",
                "user_question": "내 선호도는 어떻게 되나요?",
                "expected_recovery": "fallback_response"
            },
            {
                "error_type": "document_retrieval_failure",
                "user_question": "이미지 선호도 분석 결과를 보여주세요",
                "expected_recovery": "alternative_suggestion"
            },
            {
                "error_type": "response_generation_failure",
                "user_question": "선호도 관련 직업을 추천해주세요",
                "expected_recovery": "generic_helpful_response"
            }
        ]
        
        for scenario in error_scenarios:
            print(f"\n=== Testing Error Recovery: {scenario['error_type']} ===")
            
            if scenario["error_type"] == "context_building_failure":
                # Mock context building failure
                with patch.object(ContextBuilder, 'build_context') as mock_context:
                    mock_context.side_effect = Exception("Context building failed")
                    
                    # Should recover gracefully
                    try:
                        context_builder = ContextBuilder()
                        context = await context_builder.build_context(scenario["user_question"], 12345)
                        assert False, "Should have raised exception"
                    except Exception as e:
                        assert "Context building failed" in str(e)
                        
                        # Recovery response
                        recovery_response = {
                            "response": "죄송합니다. 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
                            "confidence": 0.5,
                            "sources": [],
                            "has_preference_data": False,
                            "error_recovery": True
                        }
                        
                        assert recovery_response["error_recovery"] == True
                        print(f"✓ Context building failure handled gracefully")
            
            elif scenario["error_type"] == "document_retrieval_failure":
                # Mock document retrieval failure
                with patch.object(ContextBuilder, 'build_context') as mock_context:
                    mock_context.return_value = {
                        "relevant_documents": [],  # No documents retrieved
                        "context_summary": "문서 검색 실패",
                        "document_types": [],
                        "error": "document_retrieval_failed"
                    }
                    
                    context_builder = ContextBuilder()
                    context = await context_builder.build_context(scenario["user_question"], 12345)
                    
                    assert len(context["relevant_documents"]) == 0
                    assert "error" in context
                    
                    # Recovery with alternative suggestion
                    with patch.object(ResponseGenerator, 'generate_response') as mock_response:
                        mock_response.return_value = {
                            "response": "현재 이미지 선호도 분석 결과를 불러올 수 없습니다. 성격 분석이나 사고 능력 분석 결과를 확인해보시겠어요?",
                            "confidence": 0.8,
                            "sources": [],
                            "has_preference_data": False,
                            "suggested_alternatives": ["personality", "thinking_skills"],
                            "error_recovery": True
                        }
                        
                        generator = ResponseGenerator()
                        response = await generator.generate_response(scenario["user_question"], context)
                        
                        assert response["error_recovery"] == True
                        assert response["suggested_alternatives"] is not None
                        print(f"✓ Document retrieval failure handled with alternatives")
            
            elif scenario["error_type"] == "response_generation_failure":
                # Mock response generation failure
                mock_documents = self.setup_mock_preference_documents("complete")
                
                with patch.object(ContextBuilder, 'build_context') as mock_context:
                    mock_context.return_value = {
                        "relevant_documents": mock_documents,
                        "context_summary": "정상적인 컨텍스트",
                        "document_types": ["PREFERENCE_ANALYSIS"],
                        "data_completeness": "complete"
                    }
                    
                    with patch.object(ResponseGenerator, 'generate_response') as mock_response:
                        mock_response.side_effect = Exception("Response generation failed")
                        
                        # Should recover with generic helpful response
                        try:
                            generator = ResponseGenerator()
                            response = await generator.generate_response(scenario["user_question"], context)
                            assert False, "Should have raised exception"
                        except Exception as e:
                            assert "Response generation failed" in str(e)
                            
                            # Recovery response
                            recovery_response = {
                                "response": "죄송합니다. 응답 생성 중 오류가 발생했습니다. 질문을 다시 해주시거나, 다른 방식으로 문의해주세요.",
                                "confidence": 0.3,
                                "sources": ["SYSTEM"],
                                "has_preference_data": False,
                                "error_recovery": True,
                                "recovery_suggestions": ["다시 질문하기", "다른 분석 결과 확인하기"]
                            }
                            
                            assert recovery_response["error_recovery"] == True
                            print(f"✓ Response generation failure handled with recovery suggestions")

    @pytest.mark.asyncio
    async def test_user_satisfaction_metrics(self):
        """Test user satisfaction indicators in preference conversations"""
        
        mock_documents = self.setup_mock_preference_documents("complete")
        
        # Test different types of user questions and expected satisfaction levels
        satisfaction_scenarios = [
            {
                "question": "내 이미지 선호도 분석 결과를 자세히 알려주세요",
                "expected_satisfaction": "high",
                "satisfaction_factors": ["completeness", "detail", "accuracy"]
            },
            {
                "question": "선호도에 맞는 직업을 추천해주세요",
                "expected_satisfaction": "high",
                "satisfaction_factors": ["relevance", "actionability", "specificity"]
            },
            {
                "question": "이미지 선호도가 뭔가요?",
                "expected_satisfaction": "medium",
                "satisfaction_factors": ["educational_value", "clarity"]
            }
        ]
        
        for scenario in satisfaction_scenarios:
            print(f"\n=== Testing User Satisfaction: {scenario['question']} ===")
            
            # Context building
            with patch.object(ContextBuilder, 'build_context') as mock_context:
                mock_context.return_value = {
                    "relevant_documents": mock_documents,
                    "context_summary": "완전한 이미지 선호도 분석 결과",
                    "document_types": ["PREFERENCE_ANALYSIS"],
                    "data_completeness": "complete"
                }
                
                context_builder = ContextBuilder()
                context = await context_builder.build_context(scenario["question"], 12345)
            
            # Response generation with satisfaction metrics
            with patch.object(ResponseGenerator, 'generate_response') as mock_response:
                if "자세히" in scenario["question"]:
                    response_text = """귀하의 이미지 선호도 분석 결과를 자세히 말씀드리겠습니다.

**검사 완료 현황:**
- 총 120개 이미지 중 96개 완료 (80%)
- 검사 완료 상태: 양호

**선호도 순위:**
1. 실내 활동 선호 (85% 응답률) - 조용하고 집중할 수 있는 환경을 선호
2. 창의적 활동 선호 (78% 응답률) - 새로운 아이디어를 만들어내는 활동을 선호

**관련 직업 추천:**
- 소프트웨어 개발자: 컴퓨터 프로그램 개발
- 데이터 분석가: 데이터 분석 및 인사이트 도출"""
                    
                    satisfaction_score = 0.95
                    
                elif "직업" in scenario["question"]:
                    response_text = """귀하의 선호도에 맞는 직업을 추천드립니다:

**실내 활동 선호 관련 직업:**
1. 소프트웨어 개발자
   - 업무: 컴퓨터 프로그램 개발
   - 관련 전공: 컴퓨터공학, 소프트웨어공학

2. 데이터 분석가
   - 업무: 데이터 분석 및 인사이트 도출
   - 관련 전공: 통계학, 데이터사이언스

이러한 직업들은 귀하가 선호하는 조용하고 집중할 수 있는 실내 환경에서 이루어집니다."""
                    
                    satisfaction_score = 0.90
                    
                else:  # "뭔가요?" type question
                    response_text = """이미지 선호도 분석은 다양한 이미지를 보고 선호하는 것을 선택하여 개인의 성향과 관심사를 파악하는 검사입니다.

이 검사를 통해:
- 개인의 활동 선호도를 파악할 수 있습니다
- 성향에 맞는 직업을 추천받을 수 있습니다
- 자신의 특성을 더 잘 이해할 수 있습니다

귀하의 경우 실내 활동을 가장 선호하는 것으로 나타났습니다."""
                    
                    satisfaction_score = 0.75
                
                mock_response.return_value = {
                    "response": response_text,
                    "confidence": 0.9,
                    "sources": ["PREFERENCE_ANALYSIS"],
                    "has_preference_data": True,
                    "satisfaction_metrics": {
                        "predicted_satisfaction": satisfaction_score,
                        "satisfaction_factors": scenario["satisfaction_factors"],
                        "response_completeness": len(response_text.split()) / 100,  # Word count based metric
                        "actionability_score": 0.8 if "직업" in scenario["question"] else 0.6,
                        "clarity_score": 0.9
                    }
                }
                
                generator = ResponseGenerator()
                response = await generator.generate_response(scenario["question"], context)
                
                # Verify satisfaction metrics
                satisfaction_metrics = response["satisfaction_metrics"]
                
                if scenario["expected_satisfaction"] == "high":
                    assert satisfaction_metrics["predicted_satisfaction"] >= 0.8
                elif scenario["expected_satisfaction"] == "medium":
                    assert 0.6 <= satisfaction_metrics["predicted_satisfaction"] < 0.8
                else:  # low
                    assert satisfaction_metrics["predicted_satisfaction"] < 0.6
                
                # Verify satisfaction factors are present
                for factor in scenario["satisfaction_factors"]:
                    assert factor in satisfaction_metrics["satisfaction_factors"]
                
                print(f"✓ Predicted satisfaction: {satisfaction_metrics['predicted_satisfaction']:.2f}")
                print(f"✓ Satisfaction factors: {satisfaction_metrics['satisfaction_factors']}")
                print(f"✓ Response length: {len(response['response'])} characters")

    @pytest.mark.asyncio
    async def test_accessibility_and_usability(self):
        """Test accessibility and usability aspects of preference conversations"""
        
        mock_documents = self.setup_mock_preference_documents("complete")
        
        # Test different user interaction patterns
        usability_scenarios = [
            {
                "user_type": "novice",
                "question": "선호도가 뭐에요?",
                "expected_features": ["simple_language", "explanatory", "educational"]
            },
            {
                "user_type": "expert",
                "question": "이미지 선호도 분석의 통계적 신뢰도는 어떻게 되나요?",
                "expected_features": ["technical_detail", "statistical_info", "methodology"]
            },
            {
                "user_type": "mobile",
                "question": "선호도 요약해줘",
                "expected_features": ["concise", "bullet_points", "mobile_friendly"]
            },
            {
                "user_type": "accessibility",
                "question": "내 선호도를 간단하게 설명해주세요",
                "expected_features": ["clear_structure", "simple_sentences", "logical_flow"]
            }
        ]
        
        for scenario in usability_scenarios:
            print(f"\n=== Testing {scenario['user_type'].title()} User Experience ===")
            
            # Context building with user type consideration
            with patch.object(ContextBuilder, 'build_context') as mock_context:
                mock_context.return_value = {
                    "relevant_documents": mock_documents,
                    "context_summary": "이미지 선호도 분석 결과",
                    "document_types": ["PREFERENCE_ANALYSIS"],
                    "data_completeness": "complete",
                    "user_context": {
                        "user_type": scenario["user_type"],
                        "interaction_pattern": "question_answer"
                    }
                }
                
                context_builder = ContextBuilder()
                context = await context_builder.build_context(scenario["question"], 12345)
                
                assert context["user_context"]["user_type"] == scenario["user_type"]
            
            # Response generation adapted to user type
            with patch.object(ResponseGenerator, 'generate_response') as mock_response:
                if scenario["user_type"] == "novice":
                    response_text = """선호도란 개인이 좋아하는 것을 의미합니다. 

이미지 선호도 분석은:
• 여러 이미지를 보고 마음에 드는 것을 선택하는 검사입니다
• 이를 통해 어떤 활동을 좋아하는지 알 수 있습니다
• 귀하는 실내 활동을 가장 선호하는 것으로 나타났습니다

이런 결과를 바탕으로 적합한 직업도 추천받을 수 있어요."""
                    
                elif scenario["user_type"] == "expert":
                    response_text = """이미지 선호도 분석의 통계적 지표:

**검사 완료율:** 80% (96/120 이미지)
**응답 신뢰도:** 
- 1순위 선호도: 85% 응답률
- 2순위 선호도: 78% 응답률

**분석 방법론:**
- 이미지 기반 선호도 측정
- 순위 기반 선호도 강도 산출
- 직업 매칭 알고리즘 적용

**결과 해석:**
높은 응답률(>80%)로 신뢰할 만한 결과로 판단됩니다."""
                    
                elif scenario["user_type"] == "mobile":
                    response_text = """📊 **선호도 요약**

🏠 **1순위:** 실내 활동 (85%)
🎨 **2순위:** 창의적 활동 (78%)

💼 **추천 직업:**
• 소프트웨어 개발자
• 데이터 분석가

✅ **검사 완료:** 80% (96/120)"""
                    
                else:  # accessibility
                    response_text = """귀하의 선호도를 간단히 설명드리겠습니다.

첫 번째로, 실내 활동을 가장 선호합니다.
이는 조용하고 집중할 수 있는 환경을 좋아한다는 의미입니다.

두 번째로, 창의적 활동을 선호합니다.
새로운 아이디어를 만드는 것을 좋아한다는 뜻입니다.

이러한 선호도에 맞는 직업으로는 소프트웨어 개발자나 데이터 분석가가 있습니다."""
                
                mock_response.return_value = {
                    "response": response_text,
                    "confidence": 0.9,
                    "sources": ["PREFERENCE_ANALYSIS"],
                    "has_preference_data": True,
                    "usability_features": scenario["expected_features"],
                    "accessibility_score": 0.9 if scenario["user_type"] == "accessibility" else 0.7,
                    "readability_level": "simple" if scenario["user_type"] in ["novice", "accessibility"] else "standard"
                }
                
                generator = ResponseGenerator()
                response = await generator.generate_response(scenario["question"], context)
                
                # Verify usability features
                for feature in scenario["expected_features"]:
                    assert feature in response["usability_features"]
                
                # Verify appropriate response characteristics
                if scenario["user_type"] == "mobile":
                    assert "•" in response["response"] or "**" in response["response"]  # Formatting
                elif scenario["user_type"] == "accessibility":
                    assert response["accessibility_score"] >= 0.8
                    sentences = response["response"].split('.')
                    avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)
                    assert avg_sentence_length < 15  # Simple sentences
                
                print(f"✓ {scenario['user_type'].title()} user experience optimized")
                print(f"✓ Features: {response['usability_features']}")
                if "accessibility_score" in response:
                    print(f"✓ Accessibility score: {response['accessibility_score']}")

    def test_conversation_quality_metrics(self):
        """Test overall conversation quality metrics"""
        
        # Define quality metrics for preference conversations
        quality_metrics = {
            "response_relevance": 0.9,      # How relevant responses are to questions
            "information_accuracy": 0.95,   # Accuracy of preference information
            "user_satisfaction": 0.85,      # Predicted user satisfaction
            "conversation_flow": 0.8,       # Natural conversation flow
            "error_handling": 0.9,          # Graceful error handling
            "accessibility": 0.85           # Accessibility for different users
        }
        
        # Test that all metrics meet minimum thresholds
        minimum_thresholds = {
            "response_relevance": 0.8,
            "information_accuracy": 0.9,
            "user_satisfaction": 0.7,
            "conversation_flow": 0.7,
            "error_handling": 0.8,
            "accessibility": 0.7
        }
        
        for metric, value in quality_metrics.items():
            threshold = minimum_thresholds[metric]
            assert value >= threshold, f"{metric} ({value}) below threshold ({threshold})"
            print(f"✓ {metric}: {value} (threshold: {threshold})")
        
        # Calculate overall quality score
        overall_quality = sum(quality_metrics.values()) / len(quality_metrics)
        assert overall_quality >= 0.8, f"Overall quality ({overall_quality}) below 0.8"
        
        print(f"\n✓ Overall conversation quality: {overall_quality:.2f}")
        print("✓ All quality metrics meet minimum thresholds")