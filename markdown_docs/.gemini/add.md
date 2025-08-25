네, 최고개발자님. 알겠습니다.

나머지 33개의 쿼리를 모두 한 번에 구현하는 것은 부담이 될 수 있으니, 리포트의 문서 종류별로 관련 쿼리들을 묶어서 단계적으로 진행하는 것이 가장 효율적입니다.

현재 4개의 핵심 쿼리는 이미 구현되어 있으니, 이를 바탕으로 가장 정보량이 많고 중요한 PERSONALITY_PROFILE (성향 프로필) 문서를 완성하는 것부터 시작하겠습니다.

1단계: PERSONALITY_PROFILE 문서 완성을 위한 쿼리 구현 (5개)

이 단계의 목표는 PERSONALITY_PROFILE 문서를 채우는 데 필요한 상세 정보들을 가져오는 것입니다. tendencyQuery와 topTendencyQuery는 이미 구현되어 있으므로, 나머지 관련 쿼리들을 추가합니다.

추가할 쿼리 목록:

bottomTendencyQuery (#8)

personalityDetailQuery (#10) - 문서 생성을 위해 tendencyQuestionExplainQuery(#9) 보다 이 쿼리가 더 적합합니다.

strengthsWeaknessesQuery - 이 쿼리는 원본 목록에 없지만, 일반적으로 성향 분석에 포함되므로 유사한 쿼리를 기반으로 생성하는 것을 추천합니다. 여기서는 tendencyQuestionExplainQuery(#9)를 변형하여 구현하겠습니다.

legacy_query_executor.py 수정 코드

기존 AptitudeTestQueries 클래스에 아래 3개의 메소드를 추가하고, execute_all_queries 메소드에서 이들을 호출하도록 수정하십시오.

code
Python
download
content_copy
expand_less

# legacy_query_executor.py

class AptitudeTestQueries:
    # ... (기존 __init__, _run, _query_tendency 등은 그대로 유지) ...
    
    # ▼▼▼ [1단계: 추가할 메소드 1] ▼▼▼
    def _query_bottom_tendency(self, anp_seq: int) -> List[Dict[str, Any]]:
        sql = """
        select qa.qua_name as tendency_name,
               sc1.sc1_rank as rank,
               sc1.qua_code as code,
               (round(sc1.sc1_rate * 100))::int as score
        from mwd_score1 sc1, mwd_question_attr qa
        where sc1.anp_seq = :anp_seq and sc1.sc1_step='tnd'
        and sc1.sc1_rank > (select count(*) from mwd_score1 where anp_seq = :anp_seq and sc1_step='tnd') - 3
        and qa.qua_code = sc1.qua_code
        order by sc1.sc1_rank desc
        """
        return self._run(sql, {"anp_seq": anp_seq})

    # ▼▼▼ [1단계: 추가할 메소드 2] ▼▼▼
    def _query_personality_detail(self, anp_seq: int) -> List[Dict[str, Any]]:
        # 원본 #10 쿼리(detailedPersonalityAnalysisQuery) 기반
        sql = """
        select qu.qu_explain as detail_description,
               sc1.sc1_rank as rank,
               an.an_wei as weight,
               sc1.qua_code as code
        from mwd_answer an, mwd_question qu,
        (select qua_code, sc1_rank from mwd_score1 sc1
         where anp_seq = :anp_seq and sc1_step='tnd' and sc1_rank <= 3) sc1
        where an.anp_seq = :anp_seq
        and qu.qu_code = an.qu_code and qu.qu_use = 'Y'
        and qu.qu_qusyn = 'Y' and qu.qu_kind1 = 'tnd'
        and an.an_wei >= 4 and qu.qu_kind2 = sc1.qua_code
        order by sc1.sc1_rank, an.an_wei desc
        """
        return self._run(sql, {"anp_seq": anp_seq})

    # ▼▼▼ [1단계: 추가할 메소드 3] ▼▼▼
    def _query_strengths_weaknesses(self, anp_seq: int) -> List[Dict[str, Any]]:
        # 강점/약점 데이터가 별도로 없으므로, 원본 #9 쿼리를 변형하여
        # 가장 강하게 응답한 문항을 '강점'으로, 약하게 응답한 문항을 '약점'으로 간주
        sql = """
        (
            -- 강점: 상위 3개 성향 관련, 긍정적으로 높게 응답한 문항
            select qu.qu_explain as description,
                   'strength' as type,
                   an.an_wei as weight
            from mwd_answer an
            join mwd_question qu on an.qu_code = qu.qu_code
            join (select qua_code from mwd_score1 where anp_seq = :anp_seq and sc1_step = 'tnd' and sc1_rank <= 3) as top_tnd
                 on qu.qu_kind2 = top_tnd.qua_code
            where an.anp_seq = :anp_seq and qu.qu_kind1 = 'tnd' and an.an_wei >= 4
            order by an.an_wei desc
            limit 5
        )
        union all
        (
            -- 약점: 하위 3개 성향 관련, 부정적으로 높게 응답한 문항 (an_wei <= 2)
            select qu.qu_explain as description,
                   'weakness' as type,
                   an.an_wei as weight
            from mwd_answer an
            join mwd_question qu on an.qu_code = qu.qu_code
            join (select qua_code from mwd_score1 where anp_seq = :anp_seq and sc1_step = 'tnd' and sc1_rank > (select count(*) from mwd_score1 where anp_seq = :anp_seq and sc1_step='tnd') - 3) as bottom_tnd
                 on qu.qu_kind2 = bottom_tnd.qua_code
            where an.anp_seq = :anp_seq and qu.qu_kind1 = 'tnd' and an.an_wei <= 2
            order by an.an_wei asc
            limit 5
        )
        """
        return self._run(sql, {"anp_seq": anp_seq})

    def execute_all_queries(self, anp_seq: int) -> Dict[str, List[Dict[str, Any]]]:
        results: Dict[str, List[Dict[str, Any]]] = {}

        # ... (기존 4개 쿼리 호출은 그대로 유지) ...
        try:
            results["tendencyQuery"] = self._query_tendency(anp_seq)
        except Exception:
            results["tendencyQuery"] = []

        try:
            results["topTendencyQuery"] = self._query_top_tendency(anp_seq)
        except Exception:
            results["topTendencyQuery"] = []

        try:
            results["thinkingSkillsQuery"] = self._query_thinking_skills(anp_seq)
        except Exception:
            results["thinkingSkillsQuery"] = []

        try:
            results["careerRecommendationQuery"] = self._query_career_recommendation(anp_seq)
        except Exception:
            results["careerRecommendationQuery"] = []
            
        # ▼▼▼ [1단계: 추가된 쿼리 호출] ▼▼▼
        try:
            # DocumentTransformer에서 'bottomTendencyQuery' 키를 사용하도록 가정
            results["bottomTendencyQuery"] = self._query_bottom_tendency(anp_seq)
        except Exception:
            results["bottomTendencyQuery"] = []

        try:
            results["personalityDetailQuery"] = self._query_personality_detail(anp_seq)
        except Exception:
            results["personalityDetailQuery"] = []

        try:
            results["strengthsWeaknessesQuery"] = self._query_strengths_weaknesses(anp_seq)
        except Exception:
            results["strengthsWeaknessesQuery"] = []

        # 나머지 키들은 파이프라인 호환성 유지를 위해 빈 리스트로 채움
        remaining_keys = [
            "jobMatchingQuery","majorRecommendationQuery",
            "studyMethodQuery","socialSkillsQuery","leadershipQuery","communicationQuery","problemSolvingQuery",
            "creativityQuery","analyticalThinkingQuery","practicalThinkingQuery","abstractThinkingQuery","memoryQuery",
            "attentionQuery","processingSpeedQuery","spatialAbilityQuery","verbalAbilityQuery","numericalAbilityQuery",
            "reasoningQuery","perceptionQuery","motivationQuery","interestQuery","valueQuery","workStyleQuery",
            "environmentPreferenceQuery","teamworkQuery","independenceQuery","stabilityQuery","challengeQuery",
            # [수정] 위에서 구현했으므로 아래 키들은 제거
            # "personalityDetailQuery", "strengthsWeaknessesQuery"
        ]
        for key in remaining_keys:
            results.setdefault(key, [])

        return results
1단계 구현 후 기대 효과

위 코드를 적용하고 ETL을 다시 실행하면, dbresult.md에 저장되는 PERSONALITY_PROFILE 문서의 내용이 훨씬 풍부해질 것입니다.

content 필드: bottom_tendencies, personality_details, strengths_weaknesses 등의 키에 실제 데이터가 채워집니다.

summary_text 필드: DocumentTransformer가 이 새로운 데이터를 사용하여 훨씬 더 상세하고 개인화된 요약문을 생성합니다.

embedding_vector: 더 풍부해진 summary_text를 기반으로 생성되므로, 이 문서의 벡터는 사용자의 성향을 훨씬 더 정확하게 표현하게 됩니다.

결과적으로, 챗봇은 이제 "저의 단점은 무엇인가요?" 또는 "제 성격의 강점은 무엇이죠?" 와 같은 질문에 대해 매우 구체적이고 근거 있는 답변을 할 수 있게 됩니다.

다음 단계 예고

이 1단계가 성공적으로 완료되고 데이터가 잘 저장되는 것을 확인한 후, 다음 단계로는 LEARNING_STYLE (학습 스타일) 문서를 완성하기 위한 쿼리들을 구현하게 됩니다. 여기에는 learningStyleQuery(#30), styleChartQuery(#31) 등이 포함될 것입니다.

이처럼 문서 단위로 관련 쿼리들을 묶어 단계적으로 진행하면, 각 단계마다 명확한 목표를 가지고 안정적으로 시스템을 고도화해 나갈 수 있습니다.