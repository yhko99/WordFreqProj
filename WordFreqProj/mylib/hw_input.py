import streamlit as st

st.title("Streamlit 기본 API 살펴보기")
st.subheader("사용자 입력 폼 만들기")

with st.form(key="user_input_form"):
    user_name = st.text_input("이름", value="고윤혁")
    user_age = st.number_input("나이", value=28, step=1)
    is_agreed = st.checkbox("약관에 동의합니다", value=True)
    
    submit_btn = st.form_submit_button(label="제출")

if submit_btn:
    st.write(f"이름: {user_name}, 나이: {user_age}")
    
    if is_agreed:
        st.success("약관에 동의했습니다.")