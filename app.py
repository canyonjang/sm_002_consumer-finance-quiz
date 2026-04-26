import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------
# 1. 과목 및 설정 (분반 002용으로 설정됨)
# ---------------------------------------------------------
SUBJECT_NAME = "소비자재무설계1_002 퀴즈"
CURRENT_WEEK = "9주차"
ADMIN_PASSWORD = "3383"

# 퀴즈 데이터
QUIZ_DATA = [
    {"q": "1. (___________)은 어떤 일을 성공적으로 해낼 수 있다는 자신에 대한 믿음이다.", "a": "자기 효능감"},
    {"q": "2. 자기 자신을 타인과 관계된 존재로 여기는 것은 (_______________) 자아해석이라 한다.", "a": "상호의존적"},
    {"q": "3. 자신이 재무적 위험에 빠지더라도 도와줄 주변 사람이 있다고 믿는 것을 가리켜 (____________)가설이라고 한다. (한글만 적으세요)", "a": "쿠션"},
    {"q": "4. (_________)(또는 과학적)인 연구는 실제 가계부 데이터 등 구체적이고 논리적이면서 체계적인 방법을 적용하여 경험적 증거를 얻어낸다.", "a": "실증적"},
    {"q": "5.(_______)이란, 안락의자에 앉아 생각만 하는 것이 아니라, 밖으로 나가 실제 세상을 관찰하고 측정하여 얻은 구체적인 증거이다.", "a": "경험"},
    {"q": "6. 남녀의 한 달 평균 만남 횟수가 양적 연구방법이라면, 남녀가 만나서 나누는 대화 내용은 (______) 연구방법이다.", "a": "질적"},
    {"q": "7. (______)는 질적인 성격을 가진 연구대상을 수치화하여 관찰 및 측정이 가능하도록 만드는 것이다. (한글만 적으세요)", "a": "양화"}
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
