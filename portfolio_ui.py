"""Streamlit 기반 Portfolio AI 채팅 인터페이스 (Enhanced Version with Multiple Optimization Modes)."""
import streamlit as st
import requests
import json
from datetime import datetime
from typing import Dict, List

# 페이지 설정
st.set_page_config(
    page_title="Portfolio AI 투자 상담 - Enhanced",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API 설정
API_BASE_URL = "http://localhost:8008"

# --- 사이드바 시작 ---
with st.sidebar:
    st.header("👤 투자자 프로필")
    
    user_profile = {
        "age": st.slider("나이", 20, 70, 35),
        "monthly_income": st.number_input("월 소득 (만원)", 100, 2000, 400),
        "investment_amount": st.number_input("투자 금액 (만원)", 100, 50000, 1000),
        "experience_level": st.selectbox("투자 경험", ["초보", "중급", "고급"]),
        "risk_tolerance": st.selectbox("위험 성향", [
            "안전형 (원금보전 우선)", 
            "안정추구형 (안정성+수익성)", 
            "위험중립형 (균형투자)", 
            "적극투자형 (성장투자)", 
            "공격투자형 (고위험고수익)"
        ]),
        "investment_goal": st.selectbox("투자 목표", ["단기수익", "장기투자", "은퇴준비", "자산증식"]),
        "investment_period": st.selectbox("투자 기간", ["1년", "3년", "5년", "10년", "10년 이상"])
    }
    
    # 위험성향 간단화 (API 호환성)
    risk_map = {
        "안전형 (원금보전 우선)": "안전형",
        "안정추구형 (안정성+수익성)": "안전형",
        "위험중립형 (균형투자)": "중립형",
        "적극투자형 (성장투자)": "공격형",
        "공격투자형 (고위험고수익)": "공격형"
    }
    user_profile["risk_appetite"] = risk_map[user_profile["risk_tolerance"]]
    
    st.markdown("---")
    st.header("⚙️ 분석 옵션")
    
    # 새로운 최적화 옵션들
    optimization_preference = st.selectbox(
        "선호하는 최적화 방식",
        [
            "자동 추천 (AI가 성향에 맞게 선택)",
            "수학적 최적화 (샤프 비율 최대화)",
            "실무적 균형 (리스크-수익 균형)",
            "보수적 분산투자 (안정성 우선)"
        ]
    )
    
    # 최적화 방식 매핑
    optimization_mode_map = {
        "자동 추천 (AI가 성향에 맞게 선택)": None,
        "수학적 최적화 (샤프 비율 최대화)": "mathematical",
        "실무적 균형 (리스크-수익 균형)": "practical", 
        "보수적 분산투자 (안정성 우선)": "conservative"
    }
    
    selected_mode = optimization_mode_map[optimization_preference]
    
    include_comparison = st.checkbox(
        "여러 방식 비교 분석 포함",
        help="다양한 최적화 방식을 비교하여 보여줍니다"
    )
    
    # 분석 옵션 설명
    with st.expander("💡 최적화 방식 설명"):
        st.markdown("""
        **수학적 최적화**: 
        - 샤프 비율을 최대화하는 순수 수학적 접근
        - 최고 효율성, 하지만 종목 집중 가능성
        - 고급 투자자에게 적합
        
        **실무적 균형**:
        - 수익성과 리스크 관리의 균형 추구
        - 적당한 분산투자로 실무적 안정성
        - 중급 투자자에게 적합
        
        **보수적 분산투자**:
        - 안정성을 최우선으로 하는 접근
        - 높은 분산으로 리스크 최소화
        - 초보 투자자에게 적합
        """)
# --- 사이드바 끝 ---

# 메인 화면
st.title("🤖 Portfolio AI 투자 상담 - Enhanced")
st.subheader("AI와 함께하는 맞춤형 투자 컨설팅 (다중 최적화 지원)")

# 탭 구성
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "💬 AI 채팅 및 추천", 
    "📊 포트폴리오 비교 분석", 
    "⚡ 빠른 추천",
    "🧪 시스템 테스트",
    "🎯 5단계 위험성향 테스트"
])

# 세션 상태 초기화
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "last_analysis" not in st.session_state:
    st.session_state.last_analysis = None

# --- API 호출 함수들 ---
def call_api(endpoint: str, payload: dict) -> Dict:
    """API 호출을 위한 범용 함수."""
    try:
        response = requests.post(f"{API_BASE_URL}{endpoint}", json=payload, timeout=180)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        st.error("🚨 요청 시간 초과 (Timeout). 백엔드 서버가 오래 걸리는 작업을 수행 중일 수 있습니다.")
    except requests.exceptions.HTTPError as e:
        st.error(f"🚨 API 오류 발생: {e.response.status_code}")
        try:
            st.json(e.response.json())
        except json.JSONDecodeError:
            st.text(e.response.text)
    except requests.exceptions.ConnectionError:
        st.error("🚨 API 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인해주세요.")
    except Exception as e:
        st.error(f"오류 발생: {e}")
    return {}

def display_portfolio_result(result_data: dict, title: str = "포트폴리오 분석 결과"):
    """포트폴리오 분석 결과를 표시하는 공통 함수"""
    
    st.subheader(title)
    
    portfolio_details = result_data.get("portfolio_details", {})
    
    if not portfolio_details:
        st.warning("포트폴리오 데이터가 없습니다.")
        return
    
    # 성과 지표 표시
    performance = portfolio_details.get("performance", {})
    if performance:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                "예상 연수익률", 
                f"{performance.get('expected_annual_return', 0):.1%}",
                help="포트폴리오의 예상 연간 수익률"
            )
        with col2:
            st.metric(
                "연변동성", 
                f"{performance.get('annual_volatility', 0):.1%}",
                help="포트폴리오의 예상 연간 변동성 (위험도)"
            )
        with col3:
            st.metric(
                "샤프 비율", 
                f"{performance.get('sharpe_ratio', 0):.3f}",
                help="위험 대비 수익률 지표 (높을수록 좋음)"
            )
    
    # 포트폴리오 구성 표시
    weights = portfolio_details.get("weights", {})
    if weights:
        st.subheader("📈 포트폴리오 구성")
        
        # 표 형태로 표시
        portfolio_data = []
        for ticker, data in weights.items():
            portfolio_data.append({
                "종목명": data.get("name", ticker),
                "종목코드": ticker,
                "비중": f"{data.get('weight', 0):.1%}",
                "섹터": data.get("sector", "기타")
            })
        
        st.dataframe(portfolio_data, use_container_width=True)
    
    # 포트폴리오 통계
    stats = portfolio_details.get("portfolio_stats", {})
    if stats:
        st.subheader("📊 포트폴리오 통계")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("종목 수", stats.get("num_positions", "N/A"))
        with col2:
            st.metric("최대 비중", f"{stats.get('max_single_weight', 0):.1%}")
        with col3:
            st.metric("집중도 위험", stats.get("concentration_risk", "N/A"))
        with col4:
            st.metric("분산 수준", stats.get("diversification_level", "N/A"))

def display_comparison_results(comparison_data: dict):
    """비교 분석 결과를 표시하는 함수"""
    
    st.subheader("📊 최적화 방식별 비교 분석")
    
    comparison_results = comparison_data.get("comparison_results", {})
    
    if not comparison_results:
        st.warning("비교 분석 데이터가 없습니다.")
        return
    
    # 비교 표 생성
    comparison_table = []
    
    for mode_name, result in comparison_results.items():
        if "error" not in result:
            perf = result.get("performance", {})
            stats = result.get("portfolio_stats", {})
            
            comparison_table.append({
                "최적화 방식": {
                    "mathematical": "수학적 최적화",
                    "practical": "실무적 균형", 
                    "conservative": "보수적 분산투자"
                }.get(mode_name, mode_name),
                "예상 수익률": f"{perf.get('expected_annual_return', 0):.1%}",
                "변동성": f"{perf.get('annual_volatility', 0):.1%}",
                "샤프 비율": f"{perf.get('sharpe_ratio', 0):.3f}",
                "종목 수": stats.get('num_positions', 'N/A'),
                "최대 비중": f"{stats.get('max_single_weight', 0):.1%}",
                "분산 수준": stats.get('diversification_level', 'N/A')
            })
    
    if comparison_table:
        st.dataframe(comparison_table, use_container_width=True)
        
        # 추천 의견 표시
        recommendation = comparison_data.get("recommendation", "")
        if recommendation:
            st.info(f"💡 **AI 추천**: {recommendation}")
        
        # 각 방식별 상세 결과 표시
        st.subheader("📋 방식별 상세 분석")
        
        for mode_name, result in comparison_results.items():
            if "error" not in result:
                mode_display_name = {
                    "mathematical": "🔬 수학적 최적화",
                    "practical": "⚖️ 실무적 균형",
                    "conservative": "🛡️ 보수적 분산투자"
                }.get(mode_name, mode_name)
                
                with st.expander(f"{mode_display_name} 상세보기"):
                    display_portfolio_result({"portfolio_details": result}, "")

# --- Tab 1: AI 채팅 및 추천 ---
with tab1:
    st.markdown("### 💬 AI와 자유롭게 투자 상담하고 포트폴리오를 추천받으세요")
    
    # 채팅 히스토리 표시
    chat_container = st.container(height=500)
    with chat_container:
        for chat in st.session_state.chat_history:
            with st.chat_message(chat["role"]):
                st.markdown(chat["content"])
                
                # 포트폴리오 분석 결과가 있는 경우 표시
                if "portfolio_analysis" in chat and chat["portfolio_analysis"]:
                    with st.expander("📊 포트폴리오 분석 결과 상세보기"):
                        display_portfolio_result({"portfolio_details": chat["portfolio_analysis"]})
                
                # 비교 분석 결과가 있는 경우 표시
                if "comparison_data" in chat and chat["comparison_data"]:
                    with st.expander("📈 비교 분석 결과 상세보기"):
                        display_comparison_results(chat["comparison_data"])

    # 사용자 입력
    if prompt := st.chat_input("질문을 입력하세요..."):
        # 사용자 메시지 표시 및 저장
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # AI 응답 요청
        with st.spinner("AI가 답변을 생성하고 있습니다..."):
            
            # Enhanced Chat API 사용
            payload = {
                "message": prompt,
                "user_profile": user_profile,
                "include_portfolio": True,
                "optimization_preference": selected_mode if selected_mode else None,
                "comparison_analysis": include_comparison
            }
            
            response_data = call_api("/api/v2/chat/enhanced", payload)
            
            if response_data:
                # AI 메시지
                ai_message = response_data.get("message", "응답을 받지 못했습니다.")
                
                # 채팅 히스토리에 저장
                chat_entry = {
                    "role": "assistant",
                    "content": ai_message
                }
                
                # 포트폴리오 분석 결과 추가
                if response_data.get("portfolio_analysis"):
                    chat_entry["portfolio_analysis"] = response_data["portfolio_analysis"]
                
                # 비교 분석 결과 추가
                if response_data.get("comparison_summary"):
                    chat_entry["comparison_data"] = {
                        "comparison_results": response_data.get("optimization_options", {}),
                        "recommendation": response_data.get("comparison_summary", "")
                    }
                
                st.session_state.chat_history.append(chat_entry)
                st.rerun()  # 채팅 히스토리 업데이트를 위해 rerun
                
            else:
                st.error("AI로부터 응답을 받지 못했습니다.")

# --- Tab 2: 포트폴리오 비교 분석 ---
with tab2:
    st.markdown("### 📊 여러 최적화 방식을 비교하여 최적의 포트폴리오를 찾아보세요")
    
    st.info("💡 이 기능은 수학적 최적화, 실무적 균형, 보수적 분산투자 세 가지 방식을 모두 비교합니다.")
    
    if st.button("🔄 포트폴리오 비교 분석 실행", type="primary"):
        with st.spinner("여러 최적화 방식으로 분석 중..."):
            
            payload = {
                "initial_capital": user_profile["investment_amount"] * 10000,
                "risk_appetite": user_profile["risk_tolerance"],
                "experience_level": user_profile["experience_level"],
                "age": user_profile["age"],
                "investment_goal": user_profile["investment_goal"],
                "investment_period": user_profile["investment_period"]
            }
            
            response_data = call_api("/api/v2/portfolio/comparison", payload)
            
            if response_data:
                st.session_state.last_analysis = response_data
                
                # AI 설명 표시
                explanation = response_data.get("explanation", "")
                if explanation:
                    st.markdown("### 🤖 AI 분석 리포트")
                    st.markdown(explanation)
                
                # 비교 결과 표시
                if response_data.get("portfolio_details"):
                    display_comparison_results(response_data["portfolio_details"])
                else:
                    st.warning("비교 분석 결과를 표시할 수 없습니다.")
    
    # 이전 분석 결과가 있으면 표시
    if st.session_state.last_analysis:
        st.markdown("---")
        st.markdown("### 📋 최근 분석 결과")
        
        if st.button("🔄 최근 분석 결과 다시 보기"):
            if st.session_state.last_analysis.get("portfolio_details"):
                display_comparison_results(st.session_state.last_analysis["portfolio_details"])

# --- Tab 3: 빠른 추천 ---
with tab3:
    st.markdown("### ⚡ 간단한 정보로 빠른 포트폴리오 추천받기")
    
    col1, col2 = st.columns(2)
    
    with col1:
        quick_investment = st.number_input("투자 가능 금액 (만원)", 10, 10000, 100, step=10)
        quick_risk = st.selectbox("위험 성향", ["안전형", "중립형", "공격형"], key="quick_risk")
        quick_experience = st.selectbox("투자 경험", ["초보", "중급", "고급"], key="quick_exp")
    
    with col2:
        quick_style = st.selectbox(
            "선호 스타일",
            [
                "AI 자동 선택",
                "수학적 최적화", 
                "실무적 균형",
                "보수적 분산투자"
            ],
            key="quick_style"
        )
        
        quick_comparison = st.checkbox("비교 분석 포함", key="quick_comp")
        
        st.markdown("**예상 소요 시간**")
        if quick_comparison:
            st.info("⏱️ 약 30-60초 (비교 분석 포함)")
        else:
            st.info("⏱️ 약 15-30초 (단일 분석)")
    
    if st.button("⚡ 빠른 추천 받기", type="primary", key="quick_recommend"):
        with st.spinner("빠른 분석 중..."):
            
            # 스타일 매핑
            style_map = {
                "AI 자동 선택": None,
                "수학적 최적화": "mathematical",
                "실무적 균형": "practical",
                "보수적 분산투자": "conservative"
            }
            
            payload = {
                "investment_amount": quick_investment,
                "risk_level": quick_risk,
                "experience": quick_experience,
                "preferred_style": style_map[quick_style],
                "include_comparison": quick_comparison
            }
            
            response_data = call_api("/api/v2/quick-recommendation", payload)
            
            if response_data:
                # 빠른 요약 표시
                st.success("✅ 빠른 추천이 완료되었습니다!")
                
                portfolio_summary = response_data.get("portfolio_summary", {})
                if portfolio_summary:
                    st.markdown("### 📋 포트폴리오 요약")
                    
                    # 핵심 지표
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("종목 수", portfolio_summary.get("total_positions", "N/A"))
                    with col2:
                        st.metric("예상 수익률", f"{portfolio_summary.get('expected_return', 0):.1%}")
                    with col3:
                        st.metric("변동성", f"{portfolio_summary.get('volatility', 0):.1%}")
                    with col4:
                        st.metric("샤프 비율", f"{portfolio_summary.get('sharpe_ratio', 0):.3f}")
                    
                    # 주요 보유 종목
                    top_holdings = portfolio_summary.get("top_holdings", [])
                    if top_holdings:
                        st.markdown("### 🏆 주요 보유 종목 (상위 3개)")
                        for i, holding in enumerate(top_holdings, 1):
                            st.markdown(
                                f"**{i}. {holding['name']}** - "
                                f"{holding['weight']:.1%} ({holding['sector']})"
                            )
                
                # 핵심 추천사항
                key_recommendations = response_data.get("key_recommendations", [])
                if key_recommendations:
                    st.markdown("### 💡 핵심 추천사항")
                    for rec in key_recommendations:
                        st.markdown(f"• {rec}")
                
                # 다음 단계
                next_steps = response_data.get("next_steps", [])
                if next_steps:
                    st.markdown("### 📝 다음 단계")
                    for step in next_steps:
                        st.markdown(f"1. {step}")
                
                # 상세 분석 결과 (확장 가능)
                full_analysis = response_data.get("full_analysis", {})
                if full_analysis:
                    with st.expander("🔍 상세 분석 결과 보기"):
                        if quick_comparison and full_analysis.get("portfolio_details", {}).get("comparison_results"):
                            display_comparison_results(full_analysis["portfolio_details"])
                        else:
                            display_portfolio_result(full_analysis)

# --- Tab 4: 시스템 테스트 ---
with tab4:
    st.markdown("### 🧪 백엔드 시스템 직접 테스트")
    st.warning("이 기능은 개발 및 디버깅 목적으로 사용됩니다.")

    # 1. 헬스 체크
    st.markdown("---")
    st.subheader("1. API 서버 상태 확인")
    if st.button("❤️ 서버 상태 확인 (Health Check)"):
        with st.spinner("서버 상태를 확인하는 중..."):
            try:
                res = requests.get(f"{API_BASE_URL}/health", timeout=10)
                res.raise_for_status()
                health_data = res.json()
                st.success("API 서버가 정상적으로 응답합니다.")
                
                # 상세 정보 표시
                col1, col2 = st.columns(2)
                with col1:
                    st.info(f"**버전**: {health_data.get('api_version', 'N/A')}")
                    st.info(f"**상태**: {health_data.get('status', 'N/A')}")
                with col2:
                    st.info(f"**DB 상태**: {health_data.get('database_status', 'N/A')}")
                    st.info(f"**시간**: {health_data.get('timestamp', 'N/A')}")
                
            except Exception as e:
                st.error(f"서버 상태 확인 실패: {e}")

    # 2. 최적화 엔진 테스트 (Enhanced)
    st.markdown("---")
    st.subheader("2. 다중 모드 최적화 엔진 테스트")
    
    test_tickers_input = st.text_input(
        "테스트할 종목 코드를 쉼표(,)로 구분하여 입력하세요.", 
        "005930, 035420, 051910, 000660",
        key="test_tickers"
    )
    
    if st.button("⚙️ 다중 모드 최적화 테스트 실행"):
        if test_tickers_input:
            tickers = [t.strip() for t in test_tickers_input.split(",")]
            with st.spinner("다중 모드 최적화 엔진을 테스트하는 중..."):
                try:
                    res = requests.post(f"{API_BASE_URL}/test/optimizer", json=tickers, timeout=120)
                    res.raise_for_status()
                    test_result = res.json()
                    
                    if test_result.get("status") == "completed":
                        st.success("✅ 다중 모드 최적화 엔진 테스트 성공!")
                        
                        # 결과별 표시
                        results_by_mode = test_result.get("results_by_mode", {})
                        
                        for mode, result in results_by_mode.items():
                            mode_name = {
                                "mathematical": "🔬 수학적 최적화",
                                "practical": "⚖️ 실무적 균형", 
                                "conservative": "🛡️ 보수적 분산투자"
                            }.get(mode, mode)
                            
                            if result.get("status") == "success":
                                with st.expander(f"{mode_name} 결과"):
                                    perf = result.get("performance", {})
                                    col1, col2, col3 = st.columns(3)
                                    with col1:
                                        st.metric("예상 수익률", f"{perf.get('expected_annual_return', 0):.1%}")
                                    with col2:
                                        st.metric("변동성", f"{perf.get('annual_volatility', 0):.1%}")
                                    with col3:
                                        st.metric("샤프 비율", f"{perf.get('sharpe_ratio', 0):.3f}")
                                    
                                    st.markdown("**포트폴리오 구성:**")
                                    weights = result.get("weights", {})
                                    for ticker, weight in weights.items():
                                        if weight > 0.01:
                                            st.markdown(f"• {ticker}: {weight:.1%}")
                            else:
                                st.error(f"{mode_name}: {result.get('detail', '알 수 없는 오류')}")
                        
                        # 비교 요약
                        comparison = test_result.get("comparison", {})
                        if comparison:
                            st.markdown("### 📊 모드별 비교 요약")
                            st.info(f"**종합 비교**: {comparison.get('summary', 'N/A')}")
                    
                    else:
                        st.error("최적화 엔진 테스트에 실패했습니다.")
                        st.json(test_result)
                        
                except Exception as e:
                    st.error(f"최적화 엔진 테스트 실패: {e}")
        else:
            st.warning("테스트할 종목 코드를 입력해주세요.")

    # 3. HyperCLOVA API 테스트
    st.markdown("---")
    st.subheader("3. AI 모델(HyperCLOVA X) 연결 테스트")
    if st.button("🧠 AI 모델 연결 테스트"):
        with st.spinner("AI 모델 연결 상태를 확인하는 중..."):
            try:
                res = requests.get(f"{API_BASE_URL}/test/hyperclova", timeout=60)
                res.raise_for_status()
                response_json = res.json()
                
                if response_json.get("status") == "success":
                    st.success("✅ AI 모델이 성공적으로 연결되었습니다.")
                elif response_json.get("status") == "warning":
                    st.warning("⚠️ AI 모델 연결에 실패했습니다. (모의 모드로 동작)")
                else:
                    st.error("❌ AI 모델 연결 테스트 실패")
                
                st.json(response_json)
                
            except Exception as e:
                st.error(f"AI 모델 테스트 실패: {e}")

    # 4. 최적화 방식 정보 조회
    st.markdown("---")
    st.subheader("4. 최적화 방식 정보")
    if st.button("📋 사용 가능한 최적화 방식 조회"):
        with st.spinner("최적화 방식 정보를 조회하는 중..."):
            try:
                res = requests.get(f"{API_BASE_URL}/api/optimization-modes", timeout=30)
                res.raise_for_status()
                modes_info = res.json()
                
                st.success("✅ 최적화 방식 정보 조회 성공")
                
                modes = modes_info.get("modes", [])
                for mode in modes:
                    with st.expander(f"{mode['display_name']} - {mode['name']}"):
                        st.markdown(f"**설명**: {mode['description']}")
                        st.markdown(f"**위험 수준**: {mode['risk_level']}")
                        st.markdown(f"**복잡도**: {mode['complexity']}")
                        
                        st.markdown("**특징:**")
                        for char in mode['characteristics']:
                            st.markdown(f"• {char}")
                
                # 선택 가이드
                selection_guide = modes_info.get("selection_guide", {})
                if selection_guide:
                    st.markdown("### 🎯 투자자 유형별 추천 방식")
                    guide_df = []
                    for profile, recommended_mode in selection_guide.items():
                        experience, risk = profile.split('_')
                        guide_df.append({
                            "투자 경험": experience,
                            "위험 성향": risk,
                            "추천 방식": recommended_mode
                        })
                    
                    st.dataframe(guide_df, use_container_width=True)
                
            except Exception as e:
                st.error(f"최적화 방식 정보 조회 실패: {e}")

# --- Tab 5: 5단계 위험성향 테스트 ---
with tab5:
    st.markdown("### 🎯 신한증권 5단계 위험성향 시스템 테스트")
    st.info("신한증권 기준의 5단계 위험성향 분류 시스템을 실제 질문으로 테스트해보세요!")
    
    # 테스트 시나리오 선택
    test_scenarios = {
        "안전형 테스트": {
            "question": "1000만원으로 안전하게 투자하고 싶어요. 원금손실은 절대 피하고 싶습니다.",
            "expected": "안정추구형으로 분류, 대형 우량주 중심"
        },
        "균형형 테스트": {
            "question": "5000만원으로 코스피 대형주 중심으로 포트폴리오 만들어주세요. 적당한 수익을 원해요.",
            "expected": "위험중립형 분류, 코스피 키워드 감지"
        },
        "성장형 테스트": {
            "question": "반도체주와 바이오 중심으로 공격적인 포트폴리오 원합니다. 1억원 투자할게요.",
            "expected": "적극투자형 분류, 반도체/바이오 섹터 우선"
        },
        "코스닥 테스트": {
            "question": "코스닥 게임주 중심으로 구성해주세요. 높은 변동성도 괜찮아요. 3000만원 투자합니다.",
            "expected": "적극투자형 분류, 코스닥 키워드 감지"
        },
        "은퇴 준비 테스트": {
            "question": "은퇴 준비용으로 2억원 투자하려고 해요. 안정적이면서 조금의 성장도 원해요.",
            "expected": "안정추구형 분류, 배당주/우량주 중심"
        },
        "직접 입력": {
            "question": "",
            "expected": "사용자 직접 입력"
        }
    }
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        selected_scenario = st.selectbox(
            "테스트 시나리오 선택",
            list(test_scenarios.keys()),
            help="미리 준비된 시나리오를 선택하거나 직접 입력하세요"
        )
        
        if selected_scenario == "직접 입력":
            test_question = st.text_area(
                "테스트할 질문을 입력하세요",
                placeholder="예: 1000만원으로 IT주 중심으로 포트폴리오 만들어주세요",
                height=100
            )
        else:
            test_question = st.text_area(
                "테스트 질문",
                value=test_scenarios[selected_scenario]["question"],
                height=100
            )
    
    with col2:
        st.markdown("**기대 결과:**")
        if selected_scenario != "직접 입력":
            st.info(test_scenarios[selected_scenario]["expected"])
        else:
            st.info("직접 입력한 질문에 따라 결과가 달라집니다")
        
        # 위험성향 가이드
        with st.expander("📋 5단계 위험성향 가이드"):
            st.markdown("""
            **안정형**: 원금보전 최우선 (주식 5%)
            **안정추구형**: 안정성+수익성 (주식 20%)
            **위험중립형**: 균형투자 (주식 45%)
            **적극투자형**: 성장투자 (주식 70%)
            **공격투자형**: 고위험고수익 (주식 90%)
            """)
    
    # 테스트 실행
    if st.button("🚀 위험성향 시스템 테스트 실행", type="primary"):
        if not test_question.strip():
            st.warning("테스트할 질문을 입력해주세요.")
        else:
            with st.spinner("5단계 위험성향 시스템으로 분석 중..."):
                
                # 기본 투자자 프로필 생성
                test_profile = {
                    "initial_capital": user_profile["investment_amount"] * 10000,
                    "risk_appetite": user_profile["risk_appetite"],
                    "investment_amount": user_profile["investment_amount"] * 10000,
                    "investment_goal": user_profile["investment_goal"],
                    "investment_period": user_profile["investment_period"],
                    "age": user_profile["age"],
                    "experience_level": user_profile["experience_level"]
                }
                
                # Enhanced 포트폴리오 API 호출 (직접 구현)
                try:
                    import sys
                    import os
                    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
                    
                    from app.services.portfolio_enhanced import create_smart_portfolio
                    from app.services.portfolio_explanation import generate_enhanced_portfolio_explanation
                    from app.services.stock_database import StockDatabase
                    from app.schemas import PortfolioInput
                    import asyncio
                    
                    # PortfolioInput 생성
                    portfolio_input = PortfolioInput(**test_profile)
                    
                    # 데이터베이스 연결
                    db = StockDatabase()
                    
                    # 포트폴리오 분석
                    result = create_smart_portfolio(
                        user_input=portfolio_input,
                        db=db,
                        original_message=test_question
                    )
                    
                    if "error" in result:
                        st.error(f"❌ 분석 실패: {result['error']}")
                    else:
                        # 결과 표시
                        st.success("✅ 5단계 위험성향 분석 완료!")
                        
                        # 위험성향 분석 결과
                        risk_analysis = result.get('risk_profile_analysis', {})
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric(
                                "위험성향 분류", 
                                risk_analysis.get('risk_profile_type', 'N/A'),
                                help="신한증권 5단계 위험성향 분류 결과"
                            )
                        with col2:
                            st.metric(
                                "시장 필터", 
                                result.get('market_filter', 'N/A'),
                                help="사용자 메시지에서 감지된 시장 선호도"
                            )
                        with col3:
                            st.metric(
                                "선별 종목 수", 
                                f"{result.get('selected_tickers_count', 0)}개",
                                help="위험성향에 따라 선별된 종목 수"
                            )
                        
                        # 가이드라인 정보
                        guideline = risk_analysis.get('asset_allocation_guideline', {})
                        if guideline:
                            st.subheader("📋 자산배분 가이드라인")
                            
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.info(f"**권장 주식비중**\n{guideline.get('stocks_target', 'N/A')}%")
                            with col2:
                                st.info(f"**권장 채권비중**\n{guideline.get('bonds_target', 'N/A')}%")
                            with col3:
                                st.info(f"**단일종목 한도**\n{guideline.get('max_single_stock_limit', 'N/A')}%")
                            with col4:
                                st.info(f"**선호 시장**\n{guideline.get('preferred_market', 'N/A')}")
                            
                            st.markdown(f"**투자 철학**: {guideline.get('description', 'N/A')}")
                            st.markdown(f"**적합 섹터**: {', '.join(guideline.get('suitable_sectors', []))}")
                        
                        # 실제 포트폴리오 구성
                        weights = result.get('weights', {})
                        if weights:
                            st.subheader("💼 실제 포트폴리오 구성")
                            
                            portfolio_data = []
                            for ticker, info in weights.items():
                                portfolio_data.append({
                                    "종목명": info.get('name', ticker),
                                    "종목코드": ticker,
                                    "비중": f"{info.get('weight', 0):.1%}",
                                    "섹터": info.get('sector', 'N/A'),
                                    "시장": info.get('market', 'N/A')
                                })
                            
                            st.dataframe(portfolio_data, use_container_width=True)
                        
                        # 성과 지표
                        performance = result.get('performance', {})
                        if performance:
                            st.subheader("📊 예상 성과")
                            
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric(
                                    "예상 연수익률", 
                                    f"{performance.get('expected_annual_return', 0):.1%}"
                                )
                            with col2:
                                st.metric(
                                    "연변동성", 
                                    f"{performance.get('annual_volatility', 0):.1%}"
                                )
                            with col3:
                                st.metric(
                                    "샤프비율", 
                                    f"{performance.get('sharpe_ratio', 0):.3f}"
                                )
                        
                        # 준수성 검사
                        compliance = risk_analysis.get('compliance_check', {})
                        if compliance:
                            st.subheader("✅ 가이드라인 준수 여부")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                sector_compliant = compliance.get('within_sector_guidelines', False)
                                st.metric(
                                    "섹터 가이드라인 준수", 
                                    "✅ 준수" if sector_compliant else "❌ 미준수"
                                )
                            with col2:
                                limit_compliant = compliance.get('single_stock_limit_compliance', False)
                                st.metric(
                                    "단일종목 한도 준수", 
                                    "✅ 준수" if limit_compliant else "❌ 미준수"
                                )
                        
                        # AI 설명 생성
                        with st.expander("🤖 AI 상세 분석 보기"):
                            try:
                                # 비동기 함수 실행
                                async def get_explanation():
                                    return await generate_enhanced_portfolio_explanation(result)
                                
                                explanation = asyncio.run(get_explanation())
                                st.markdown(explanation)
                                
                            except Exception as e:
                                st.error(f"AI 설명 생성 실패: {e}")
                                st.markdown("**기본 분석 결과만 표시됩니다.**")
                        
                        # 키워드 감지 결과
                        st.subheader("🔍 키워드 감지 결과")
                        st.markdown(f"**원본 질문**: {test_question}")
                        st.markdown(f"**감지된 시장**: {result.get('market_filter', 'N/A')}")
                        st.markdown(f"**분류된 위험성향**: {risk_analysis.get('risk_profile_type', 'N/A')}")
                        
                except Exception as e:
                    st.error(f"❌ 테스트 실행 중 오류: {e}")
                    import traceback
                    with st.expander("오류 상세 정보"):
                        st.code(traceback.format_exc())
    
    # 사전 정의된 테스트 결과 예시
    st.markdown("---")
    st.subheader("📝 테스트 시나리오별 예상 결과")
    
    scenario_results = {
        "안전형 테스트": "안정추구형 → 주식 20%, 금융/전기전자 섹터 우선, KOSPI 선호",
        "균형형 테스트": "위험중립형 → 주식 45%, 코스피 키워드 감지, 균형 섹터 분산",
        "성장형 테스트": "적극투자형 → 주식 70%, 반도체/바이오 섹터 우선, 고성장 중심",
        "코스닥 테스트": "적극투자형 → 주식 70%, 코스닥 키워드 감지, 게임 섹터 우선",
        "은퇴 준비 테스트": "안정추구형 → 주식 20%, 배당주/우량주 중심, 안정성 우선"
    }
    
    for scenario, expected_result in scenario_results.items():
        with st.expander(f"💡 {scenario}"):
            st.info(expected_result)

# --- 푸터 ---
st.markdown("---")
st.markdown("🤖 **Portfolio AI Enhanced** | HyperCLOVA 기반 지능형 투자 상담 시스템 v2.0")
st.markdown("⚠️ 모든 투자 조언은 참고용이며, 투자 결정은 개인 책임입니다.")

# 사이드바 하단 정보
with st.sidebar:
    st.markdown("---")
    st.markdown("### 🔄 시스템 버전")
    st.info("**Enhanced Version 2.0**\n- 다중 최적화 방식 지원\n- 실시간 비교 분석\n- 향상된 AI 추천")
    
    if st.button("🗑️ 채팅 기록 초기화"):
        st.session_state.chat_history = []
        st.session_state.last_analysis = None
        st.success("채팅 기록이 초기화되었습니다.")
        st.rerun()