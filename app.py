import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------
# 1. 과목 및 설정 (분반 002용으로 설정됨)
# ---------------------------------------------------------
SUBJECT_NAME = "소비자재무설계1_002 퀴즈"
CURRENT_WEEK = "7주차"
ADMIN_PASSWORD = "3383"

# 퀴즈 데이터
QUIZ_DATA = [
    {"q": "1. 이슈5의 입장B의 위험 요소 중 하나로, 집값 급등 시 느끼는 상대적 박탈감을 의미하는 표현은 무엇인가?", "a": "벼락거지"},
    {"q": "2. MBTI와 투자 행태 연구에서 상반된 결과가 나오는 이유는, 연구 샘플의 (____________) 차이 때문으로 해석된다.", "a": "문화적"},
    {"q": "3. Gakhar and Prakash (2017)에 따르면, 감정(F) 유형일수록 본인의 판단을 지나치게 믿는 과잉 확신 편향이 (__________) 나타난다. (많게/적게 중에서 하나를 적으세요)", "a": "적게"},
    {"q": "4. MBTI가 투자성향을 ‘결정’하는 검사라는 주장은 (_____________). (적절하다/적절하지 않다 중에서 하나를 적으세요)", "a": "적절하지 않다"},
    {"q": "5. BIT(Behavioral Investor Types) 모델에서 “트렌드는 놓칠 수 없지! 친절한 유행 선도자”에 해당하는 유형은? (한글만 적으세요)", "a": "추종자"},
    {"q": "6. 보존가는 현재의 포트폴리오를 바꾸는 것에 큰 거부감을 느끼는 (_____________)편향과 관련이 깊다.", "a": "현상유지"},
    {"q": "7. 추종자는 기억에 잘 남는 뉴스나 정보(광고 등)에 의존해 종목을 고르는 (___________) 편향과 관련이 깊다.", "a": "가용성"}
]



NUM_QUESTIONS = len(QUIZ_DATA)

# 페이지 설정
st.set_page_config(page_title=f"{SUBJECT_NAME}", layout="wide")

# 구글 시트 연결
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except:
    st.error("구글 시트 연결 설정(Secrets)이 필요합니다.")

if "submitted_on_this_device" not in st.session_state:
    st.session_state.submitted_on_this_device = False

st.title(f"📊 {SUBJECT_NAME}")

tab1, tab2, tab3 = st.tabs(["✍️ 퀴즈 제출", "🖥️ 제출자 명단 확인", "🔐 성적 분석(교수용)"])

# --- [TAB 1] 학생 제출 화면 ---
with tab1:
    st.header("답안지")
    
    if st.session_state.submitted_on_this_device:
        st.warning("⚠️ 이 기기에서 제출이 완료되었습니다.")
    else:
        with st.form("quiz_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("이름", placeholder="이름")
            with col2:
                student_id = st.text_input("학번", placeholder="학번")
            
            st.divider()
            
            user_responses = []
            for i, item in enumerate(QUIZ_DATA):
                st.markdown(f"**{item['q']}**")
                ans = st.text_input(f"{i+1}번 답안", key=f"q{i}")
                user_responses.append(ans)

            submitted = st.form_submit_button("답안 제출하기")

            if submitted:
                if not name or not student_id:
                    st.error("이름과 학번을 입력해 주세요.")
                else:
                    try:
                        # 제출 시 중복 확인을 위해 실시간 데이터 읽기
                        master_df = conn.read(worksheet="전체데이터", ttl=0)
                        already_exists = master_df[(master_df['주차'] == CURRENT_WEEK) & (master_df['학번'] == student_id)]

                        if not already_exists.empty:
                            st.error(f"❌ {name} 학생은 이미 제출했습니다.")
                        else:
                            kst = timezone(timedelta(hours=9))
                            now_time = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")
                            row_dict = {"주차": CURRENT_WEEK, "제출시간": now_time, "이름": name, "학번": student_id}
                            
                            total_correct = 0
                            for i, item in enumerate(QUIZ_DATA, 1):
                                # [수정] 영어 대소문자 무시 비교 (.lower() 적용)
                                s_ans_set = set(item['a'].replace(" ", "").lower().split(","))
                                u_ans_set = set(user_responses[i-1].replace(" ", "").lower().split(","))
                                
                                is_correct = (s_ans_set == u_ans_set)
                                if is_correct: total_correct += 1
                                row_dict[f"q{i}_답"] = user_responses[i-1]
                                row_dict[f"q{i}_결과"] = "O" if is_correct else "X"
                            
                            row_dict["총점"] = total_correct
                            updated_master = pd.concat([master_df, pd.DataFrame([row_dict])], ignore_index=True)
                            conn.update(worksheet="전체데이터", data=updated_master)
                            
                            st.session_state.submitted_on_this_device = True
                            st.success(f"{name} 학생, 제출 성공! ({total_correct}/{NUM_QUESTIONS})")
                            # st.balloons() # 트래픽 최적화를 위해 제외
                            st.rerun() 
                    except Exception as e:
                        st.error("데이터 처리 중 오류가 발생했습니다.")

# --- [TAB 2] 제출 명단 확인 (트래픽 최적화 적용) ---
with tab2:
    st.subheader(f"📍 {CURRENT_WEEK} 제출 완료 명단")
    if st.button("🔄 명단 확인/새로고침"):
        try:
            # 트래픽 부하 감소를 위해 5분 캐시(ttl=300) 적용
            data = conn.read(worksheet="전체데이터", ttl=300)
            today_list = data[data['주차'] == CURRENT_WEEK]
            if not today_list.empty:
                st.write(f"현재 총 {len(today_list)}명 제출 완료")
                cols = st.columns(6)
                for i, row in enumerate(today_list.itertuples()):
                    cols[i % 6].success(f"✅ {row.이름}")
            else:
                st.write("아직 제출자가 없습니다.")
        except:
            st.error("데이터 로드 실패")

# --- [TAB 3] 성적 분석 ---
with tab3:
    st.header("🔐 관리자 인증")
    admin_pw = st.text_input("비밀번호를 입력하세요", type="password")
    if admin_pw == ADMIN_PASSWORD:
        try:
            data = conn.read(worksheet="전체데이터", ttl=0)
            if not data.empty:
                st.subheader("학생별 평균 정답률")
                stats = data.groupby(['학번', '이름'])['총점'].mean().reset_index()
                stats['정답률(%)'] = (stats['총점'] / NUM_QUESTIONS * 100).round(1)
                st.dataframe(stats, use_container_width=True)
                st.download_button("엑셀 다운로드", data=data.to_csv(index=False).encode('utf-8-sig'), file_name=f"{SUBJECT_NAME}_결과.csv", mime="text/csv")
        except:
            st.error("데이터 로드 실패")
    elif admin_pw != "":
        st.error("비밀번호 불일치")
