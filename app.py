import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------
# 1. 과목 및 설정 (새 과목을 만드실 때 이 부분만 수정하세요)
# ---------------------------------------------------------
SUBJECT_NAME = "소비자재무설계1_002 퀴즈"  # 과목 제목
CURRENT_WEEK = "2주차"           # 해당 주차
ADMIN_PASSWORD = "3383"          # 선생님용 비밀번호

# 퀴즈 데이터
QUIZ_DATA = [
    {"q": "1. 돈의 심리학 저자는 “모든 성공이 (_______)의 결실도 아니고, 모든 가난이 (___________)의 결과도 아님을 깨닫기를 바란다”고 조언한다.", "a": "노력, 게으름"},
    {"q": "2. 돈의 심리학 저자는 “네가 모은 한 푼, 한 푼은 모두 남들 손에 맡겨질 수 있었던 네 (_______) 한 조각을 소유하는 것과 같단다”라고 조언한다.", "a": "미래"},
    {"q": "3. 돈의 심리학 저자는 “실제 돈을 다루는 데는 감정, 인내, (____________), 태도 같은 요소(소프트 스킬)가 더 중요하다”고 주장한다.", "a": "자기 절제"},
    {"q": "4. 돈의 심리학 저자는 “사람들이 금융 의사결정을 내릴 때는, 냉철하게 (_________)이기 보다는 꽤 적당히 합리적”이라고 설명한다.", "a": "이성적"},
    {"q": "5. 우리나라에서는 (______________________)가 재무설계나 개인재무설계와 자주 혼용되어 왔다. (영어로 답하세요)", "a": "personal finance"},
    {"q": "6. 개인재무관리의 영역은 재무설계, 재무상당, 재무교육 등인데, 이들의 공동목표는 소비자의 (______________________) 증진이다.", "a": "재무적 복지"},
    {"q": "7. 경제적 복지의 4가지 유형 중에서, 객관적 조건은 좋은데, 주관적 평가가 불만족인 유형은?", "a": "주관적 불만형"}
]

# 문항 수를 자동으로 계산합니다.
NUM_QUESTIONS = len(QUIZ_DATA) 
# ---------------------------------------------------------

# 페이지 설정
st.set_page_config(page_title=f"{SUBJECT_NAME}", layout="wide")

# 구글 시트 연결
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except:
    st.error("구글 시트 연결 설정(Secrets)이 필요합니다.")

# [세션 상태] 기기별 제출 여부 메모리
if "submitted_on_this_device" not in st.session_state:
    st.session_state.submitted_on_this_device = False

# 메인 화면 UI
st.title(f"📊 {SUBJECT_NAME}")

tab1, tab2, tab3 = st.tabs(["✍️ 퀴즈 제출", "🖥️ 제출자 명단 확인", "🔐 성적 분석(교수용)"])

# --- [TAB 1] 학생 제출 화면 ---
with tab1:
    st.header("답안지")
    
    if st.session_state.submitted_on_this_device:
        st.warning("⚠️ 이 기기에서 제출이 완료되었습니다. 응시는 더 이상 불가능합니다.")
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

            # 1. 제출 버튼 문구 수정
            submitted = st.form_submit_button("답안 제출하고 확인받기 (기기당 답안 제출은 1회만 가능하니, 신중하게 검토하고 버튼 누르세요)")

            if submitted:
                if not name or not student_id:
                    st.error("이름과 학번을 입력해 주세요.")
                else:
                    try:
                        # [최적화] 데이터를 한 번만 읽어서 모든 검사와 저장을 처리
                        master_df = conn.read(worksheet="전체데이터", ttl=0)
                        
                        already_exists = master_df[
                            (master_df['주차'] == CURRENT_WEEK) & 
                            (master_df['학번'] == student_id)
                        ]

                        if not already_exists.empty:
                            st.error(f"❌ {name} 학생은 이미 이번 주 답안을 제출했습니다.")
                        else:
                            # 2. 제출 시간 포맷 수정 (한국 표준시 KST 적용)
                            kst = timezone(timedelta(hours=9))
                            now_time = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")
                            
                            row_dict = {
                                "주차": CURRENT_WEEK,
                                "제출시간": now_time,
                                "이름": name,
                                "학번": student_id
                            }
                            
                            # 채점 (순서 무관 채점 방식)
                            total_correct = 0
                            for i, item in enumerate(QUIZ_DATA, 1):
                                s_ans_set = set(item['a'].replace(" ", "").split(","))
                                u_ans_set = set(user_responses[i-1].replace(" ", "").split(","))
                                
                                is_correct = (s_ans_set == u_ans_set)
                                if is_correct: total_correct += 1
                                
                                row_dict[f"q{i}_답"] = user_responses[i-1]
                                row_dict[f"q{i}_결과"] = "O" if is_correct else "X"
                            
                            row_dict["총점"] = total_correct
                            
                            # [최적화] '전체데이터'에만 업데이트하여 API 부하 감소
                            updated_master = pd.concat([master_df, pd.DataFrame([row_dict])], ignore_index=True)
                            conn.update(worksheet="전체데이터", data=updated_master)
                            
                            st.session_state.submitted_on_this_device = True
                            st.success(f"{name} 학생, 제출 성공! ({total_correct}/{NUM_QUESTIONS})")
                            st.balloons()
                            st.rerun() 
                            
                    except Exception as e:
                        # 3. 과부하 안내 문구 삭제 (pass로 처리)
                        pass

# --- [TAB 2] 수동 새로고침 명단 (API 할당량 관리용) ---
with tab2:
    st.subheader(f"📍 {CURRENT_WEEK} 제출 완료 명단")
    st.info("명단을 확인하려면 아래 버튼을 누르세요.")
    
    if st.button("🔄 명단 새로고침 (클릭)"):
        try:
            data = conn.read(worksheet="전체데이터", ttl=0)
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
        st.success("인증 성공")
        try:
            data = conn.read(worksheet="전체데이터", ttl=0)
            if not data.empty:
                st.subheader("학생별 평균 정답률")
                stats = data.groupby(['학번', '이름'])['총점'].mean().reset_index()
                stats['정답률(%)'] = (stats['총점'] / NUM_QUESTIONS * 100).round(1)
                st.dataframe(stats, use_container_width=True)
                st.divider()
                st.download_button("엑셀 데이터 다운로드", data=data.to_csv(index=False).encode('utf-8-sig'), file_name=f"{SUBJECT_NAME}_결과.csv", mime="text/csv")
            else:
                st.info("데이터가 없습니다.")
        except:
            st.error("데이터 로드 실패")
    elif admin_pw != "":
        st.error("비밀번호 불일치")



