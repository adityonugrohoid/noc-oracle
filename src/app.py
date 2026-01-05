import streamlit as st
from engine import NOCEngine

# --- CSS Styling ---
st.markdown("""
<style>
    .block-container {
        padding-top: 1rem;
        padding-bottom: 0rem;
        padding-left: 2rem;
        padding-right: 2rem;
    }
    .reportview-container { background: #0e1117; }
    .main { background: #0e1117; color: #FAFAFA; }
    h1 { color: #00ADB5 !important; }
    .stButton>button {
        background-color: #00ADB5;
        color: white;
        border-radius: 5px;
        border: none;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- Page Config ---
st.set_page_config(
    page_title="NOC-Oracle",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- Cached Resources ---
@st.cache_resource
def init_engine():
    return NOCEngine()

# --- Main App ---
def main():
    st.title("📡 NOC-Oracle: Autonomous Runbook")
    
    # Initialize Engine
    with st.spinner("Initializing AI Core..."):
        try:
            engine = init_engine()
        except Exception as e:
            st.error(f"Failed to initialize engine: {e}")
            return

    # Input Area
    col_input, col_controls = st.columns([3, 1])
    with col_input:
        query = st.text_area(
            "Paste Alarm Log or Describe Issue", 
            height=100, 
            placeholder="e.g., How do I fix S-304 alarm on the Orbit-5G?"
        )
    with col_controls:
        st.write("") # Spacer
        st.write("") # Spacer
        generate_btn = st.button("Generate Fix 🔧", use_container_width=True)
        # THE COMPARISON TOGGLE
        show_comparison = st.checkbox("🔥 Show Hallucination Risk", value=True)

    st.markdown("---")

    if generate_btn and query:
        with st.spinner("Analyzing manual compliance & generating fix..."):
            try:
                # 1. Get the RAG Answer (The Truth)
                result = engine.get_solution(query)
                answer_rag = result.get("answer", "No answer generated.")
                docs = result.get("source_documents", [])
                
                # 2. Get the Baseline Answer (The Hallucination) - Only if requested
                answer_baseline = None
                if show_comparison:
                    answer_baseline = engine.get_baseline_response(query)

                # --- LAYOUT LOGIC ---
                if show_comparison:
                    # SPLIT VIEW: Comparison Mode
                    col_bad, col_good = st.columns(2)
                    
                    with col_bad:
                        st.subheader("🤖 Generic AI (No RAG)")
                        st.warning("⚠️ RISK: High Hallucination Probability")
                        # We display the raw hallucination
                        st.markdown(f"*{answer_baseline}*")
                        st.error("❌ ANALYSIS: This sounds plausible but is likely WRONG for the Orbit-5G.")

                    with col_good:
                        st.subheader("🧠 NOC-Oracle (With RAG)")
                        st.success("✅ VERIFIED: Sourced from Manual")
                        st.markdown(answer_rag)
                        
                        with st.expander("📖 View Source Proof"):
                             for i, doc in enumerate(docs, 1):
                                st.caption(f"Metadata: {doc.metadata}")
                                st.code(doc.page_content[:300] + "...", language="markdown")

                else:
                    # STANDARD VIEW: Fix + Proof
                    col_fix, col_proof = st.columns([1, 1])
                    with col_fix:
                        st.subheader("✅ Suggested Fix")
                        st.markdown(answer_rag)
                    with col_proof:
                        st.subheader("📖 Source Context")
                        with st.expander("View Retrieved Manual Chunks", expanded=True):
                            for i, doc in enumerate(docs, 1):
                                st.caption(f"Metadata: {doc.metadata}")
                                st.code(doc.page_content, language="markdown")

            except Exception as e:
                st.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()