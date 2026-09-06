import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------
# 1. 과목 및 설정
#    다음 주차로 바꿀 때는 CURRENT_WEEK와 QUIZ_DATA를 수정하세요.
# ---------------------------------------------------------
SUBJECT_NAME = "소비자재무설계2_002 퀴즈"
CURRENT_WEEK = "1주차"

# 관리자 비밀번호는 GitHub 코드에 쓰지 않고 Streamlit Secrets에서 읽습니다.
ADMIN_PASSWORD = st.secrets["ADMIN_PASSWORD"]

# Supabase 테이블명
TABLE_NAME = "sm002_quiz_results"

# 퀴즈 데이터
QUIZ_DATA = [
    {
        "q": "1. MIT Media Lab의 연구 결과, 생성형 AI 그룹은 가장 낮은 (____) 연결성을 보였다.",
        "a": "뇌",
    },
    {
        "q": "2. 선종 발견율(ADR) 연구는 능력이 사라진 것이 아니라, 능력을 쓰는 (_______)이 사라진 것임을 알려준다.",
        "a": "습관",
    },
    {
        "q": "3. 연구 A와 연구 B는 '(_______)은 나쁘다'는 단순 명제를 기각한다.",
        "a": "위임",
    },
    {
        "q": "4. 'AI가 생성한 내용의 정확성을 비판적으로 평가한다'는 인지적 (_______)를 측정하는 문항이다.",
        "a": "경계",
    },
    {
        "q": "5. AI를 쓰면서 특정 주제를 이해하는 방식이 근본적으로 바뀌었다면, (__________) 학습 경험이 이뤄진 것이다.",
        "a": "전환적",
    },
    {
        "q": "6. 재무목표는 측정 가능하고 달성 (_________)을 가진 문장이어야 함",
        "a": "시점",
    },
    {
        "q": "7. (________________)에 따르면 구체적이고, 다소 어렵지만 달성 가능하며, 피드백이 있을 때 성과가 높아짐",
        "a": "목표설정이론",
    },
]

NUM_QUESTIONS = len(QUIZ_DATA)

# ---------------------------------------------------------
# 2. 페이지 설정
# ---------------------------------------------------------
st.set_page_config(page_title=SUBJECT_NAME, layout="wide")


# ---------------------------------------------------------
# 3. Supabase 연결
# ---------------------------------------------------------
@st.cache_resource
def init_connection() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
    return create_client(url, key)


try:
    supabase = init_connection()
except Exception:
    st.error(
        "Supabase 연결 설정이 필요합니다. "
        "Streamlit의 Secrets에 SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, "
        "ADMIN_PASSWORD를 등록해 주세요."
    )
    st.stop()


# ---------------------------------------------------------
# 4. 보조 함수
# ---------------------------------------------------------
def normalize_answer(text: str) -> set[str]:
    """
    정답 비교용 정규화:
    - 앞뒤 공백 제거
    - 문장 안 공백 제거
    - 영어 대소문자 무시
    - 쉼표(,)로 여러 답을 적은 경우 집합으로 비교
    """
    if text is None:
        return set()

    return {
        part.replace(" ", "").strip().lower()
        for part in str(text).split(",")
        if part.strip()
    }


def get_week_submissions():
    response = (
        supabase.table(TABLE_NAME)
        .select("*")
        .eq("주차", CURRENT_WEEK)
        .order("제출시간")
        .execute()
    )
    return pd.DataFrame(response.data)


# ---------------------------------------------------------
# 5. 세션 상태
# ---------------------------------------------------------
if "submitted_on_this_device" not in st.session_state:
    st.session_state.submitted_on_this_device = False

if "last_submission_message" not in st.session_state:
    st.session_state.last_submission_message = ""


# ---------------------------------------------------------
# 6. 화면
# ---------------------------------------------------------
st.title(f"📊 {SUBJECT_NAME}")

tab1, tab2, tab3 = st.tabs(
    ["✍️ 퀴즈 제출", "🖥️ 제출자 명단 확인", "🔐 성적 분석(교수용)"]
)


# ---------------------------------------------------------
# TAB 1. 학생 제출
# ---------------------------------------------------------
with tab1:
    st.header("답안지")

    if st.session_state.submitted_on_this_device:
        if st.session_state.last_submission_message:
            st.success(st.session_state.last_submission_message)
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
                ans = st.text_input(f"{i + 1}번 답안", key=f"q{i}")
                user_responses.append(ans)

            submitted = st.form_submit_button("답안 제출하기")

            if submitted:
                name = name.strip()
                student_id = student_id.strip()

                if not name or not student_id:
                    st.error("이름과 학번을 입력해 주세요.")

                else:
                    try:
                        # 1) 동일 주차 + 동일 학번 중복 제출 확인
                        existing_data = (
                            supabase.table(TABLE_NAME)
                            .select("id")
                            .eq("주차", CURRENT_WEEK)
                            .eq("학번", student_id)
                            .limit(1)
                            .execute()
                        )

                        if existing_data.data:
                            st.error(f"❌ {name} 학생은 이미 제출했습니다.")

                        else:
                            # 2) 채점
                            kst = timezone(timedelta(hours=9))
                            now_time = datetime.now(kst).isoformat()

                            row_dict = {
                                "주차": CURRENT_WEEK,
                                "제출시간": now_time,
                                "이름": name,
                                "학번": student_id,
                            }

                            total_correct = 0

                            for i, item in enumerate(QUIZ_DATA, start=1):
                                correct_set = normalize_answer(item["a"])
                                user_set = normalize_answer(user_responses[i - 1])

                                is_correct = correct_set == user_set

                                if is_correct:
                                    total_correct += 1

                                row_dict[f"q{i}_답"] = user_responses[i - 1]
                                row_dict[f"q{i}_결과"] = "O" if is_correct else "X"

                            row_dict["총점"] = total_correct

                            # 3) Supabase 저장
                            supabase.table(TABLE_NAME).insert(row_dict).execute()

                            st.session_state.submitted_on_this_device = True
                            st.session_state.last_submission_message = (
                                f"{name} 학생, 제출 성공! "
                                f"({total_correct}/{NUM_QUESTIONS})"
                            )
                            st.rerun()

                    except Exception as e:
                        # DB의 UNIQUE 제약조건도 중복 제출을 한 번 더 막아 줍니다.
                        if "duplicate key" in str(e).lower() or "23505" in str(e):
                            st.error(f"❌ {name} 학생은 이미 제출했습니다.")
                        else:
                            st.error("데이터 처리 중 오류가 발생했습니다.")


# ---------------------------------------------------------
# TAB 2. 제출자 명단
# ---------------------------------------------------------
with tab2:
    st.subheader(f"📍 {CURRENT_WEEK} 제출 완료 명단")

    if st.button("🔄 명단 확인/새로고침"):
        try:
            today_list = get_week_submissions()

            if not today_list.empty:
                st.write(f"현재 총 {len(today_list)}명 제출 완료")

                cols = st.columns(6)

                for i, row in enumerate(today_list.itertuples(index=False)):
                    cols[i % 6].success(f"✅ {row.이름}")

            else:
                st.write("아직 제출자가 없습니다.")

        except Exception:
            st.error("데이터 로드 실패")


# ---------------------------------------------------------
# TAB 3. 교수용 성적 분석
# ---------------------------------------------------------
with tab3:
    st.header("🔐 관리자 인증")

    admin_pw = st.text_input("비밀번호를 입력하세요", type="password")

    if admin_pw == ADMIN_PASSWORD:
        try:
            response = (
                supabase.table(TABLE_NAME)
                .select("*")
                .order("주차")
                .order("학번")
                .execute()
            )

            data = pd.DataFrame(response.data)

            if not data.empty:
                st.subheader("학생별 평균 정답률")

                stats = (
                    data.groupby(["학번", "이름"])["총점"]
                    .mean()
                    .reset_index()
                )

                stats["정답률(%)"] = (
                    stats["총점"] / NUM_QUESTIONS * 100
                ).round(1)

                st.dataframe(stats, use_container_width=True)

                csv_data = data.to_csv(index=False).encode("utf-8-sig")

                st.download_button(
                    "CSV 다운로드",
                    data=csv_data,
                    file_name=f"{SUBJECT_NAME}_결과.csv",
                    mime="text/csv",
                )

            else:
                st.info("아직 제출된 데이터가 없습니다.")

        except Exception:
            st.error("데이터 로드 실패")

    elif admin_pw != "":
        st.error("비밀번호 불일치")
