import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------
# 1. 과목 및 설정 (분반 002용으로 설정됨)
# ---------------------------------------------------------
SUBJECT_NAME = "소비자재무설계1_002 퀴즈"
CURRENT_WEEK = "3주차"
ADMIN_PASSWORD = "3383"

# 퀴즈 데이터
QUIZ_DATA = [
    {"q": "1. 이슈1의 2x2 모형에서 미래를 위한 절약이 약하고, 현재의 나에게 투자도 약한 유형의 이름은 무엇인가?", "a": "현재 안주형"},
    {"q": "2. 계획된 행동이론에서 행위의도는 행동에 대한 태도, 주관적 규범, 지각된 (___________) 등에 영향을 받는다.", "a": "통제감"},
    {"q": "3. 계획된 행동이론에 대한 가장 대표적인 비판은 의도-행동 간극이며, 이를 해결하기 위해 (___________)를 추가하였다.", "a": "실행 의도"},
    {"q": "4. 3단계 재무설계 교육에서 1단계는 자신의 (_____________) 성향을 파악하는 것이다.", "a": "재무적"},
    {"q": "5. “저 사람(판매자)이 왜 저런 제안을 할까? 나에게 도움이 될까?”라는 의문을 풀기 위한 소비자들이 축적한 경험과 노하우는 무엇인가?", "a": "설득지식"},
    {"q": "6. (_______________) 유형은 제안자의 조언이 자신의 설득지식에 비춰볼 때 유용하지 않다는 판단으로 그 조언을 무시한다.", "a": "설득감시자"},
    {"q": "7. 시간해석이론에 따르면 사람들은 시간적으로 멀리 있는 대상은 (___________), 본질적, 특징적인 점에 집중해 해석하고, 시간적으로 가까운 대상은 (____________), 표면적, 사소한 점에 주목해 해석한다.", "a": "추상적, 구체적"}
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
