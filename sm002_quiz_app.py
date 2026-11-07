import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------
# 1. 과목 및 설정
# ---------------------------------------------------------
SUBJECT_NAME = "소비자재무설계2_002 퀴즈"
CURRENT_WEEK = "10주차"
ADMIN_PASSWORD = st.secrets["ADMIN_PASSWORD"]

TABLE_NAME = "sm002_quiz_results"

QUIZ_DATA = [
    {"q": "1. (_______) 가격은 B(시장의 현재 평가와 수급)에 의해 A(미래 현금흐름에 대한 기대)에서 크게 벗어날 수 있다.", "a": "단기"},
    {"q": "2. 주식의 본질은 기업이 미래에 만들어낼 (_____)과 현금흐름에 대한 청구권이다.", "a": "이익"},
    {"q": "3. (_______)은 주가를 이익으로 나눈 값이므로 “가격이 이익의 몇 배로 평가되는가”를 보여준다.", "a": "PER"},
    {"q": "4. (_______)은 특정 주식을 사려는 주문과 팔려는 주문의 상대적 힘을 뜻한다.", "a": "수급"},
    {"q": "5. liquidity pressure는 (________) 부족에 따른 가격 압력을 의미한다.", "a": "유동성"},
    {"q": "6. (_____________)는 그 기업이 돈을 벌고 있는가를 판단하기 위한 재무제표이다.", "a": "손익계산서"},
    {"q": "7. (________)활동 현금흐름은 본업에서 창출한 현금에 대한 것이다.", "a": "영업"},
]


NUM_QUESTIONS = len(QUIZ_DATA)

st.set_page_config(page_title=SUBJECT_NAME, layout="wide")


@st.cache_resource
def init_connection() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]   # publishable key
    return create_client(url, key)


try:
    supabase = init_connection()
except Exception:
    st.error(
        "Supabase 연결 설정이 필요합니다. "
        "Streamlit Secrets에 SUPABASE_URL, SUPABASE_KEY, ADMIN_PASSWORD를 등록해 주세요."
    )
    st.stop()


def normalize_answer(text: str) -> set[str]:
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


if "submitted_on_this_device" not in st.session_state:
    st.session_state.submitted_on_this_device = False

if "last_submission_message" not in st.session_state:
    st.session_state.last_submission_message = ""


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

                            supabase.table(TABLE_NAME).insert(row_dict).execute()

                            st.session_state.submitted_on_this_device = True
                            st.session_state.last_submission_message = (
                                f"{name} 학생, 제출 성공! ({total_correct}/{NUM_QUESTIONS})"
                            )
                            st.rerun()

                    except Exception as e:
                        if "duplicate key" in str(e).lower() or "23505" in str(e):
                            st.error(f"❌ {name} 학생은 이미 제출했습니다.")
                        else:
                            st.error(f"데이터 처리 중 오류가 발생했습니다: {e}")


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

        except Exception as e:
            st.error(f"데이터 로드 실패: {e}")


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

        except Exception as e:
            st.error(f"데이터 로드 실패: {e}")

    elif admin_pw != "":
        st.error("비밀번호 불일치")
