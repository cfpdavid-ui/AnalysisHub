#!/usr/bin/env python3
"""
Analysis Hub - Complete UI with Auto-Detect Database Dropdown
Run with: streamlit run analysis_hub.py
"""

import streamlit as st
import sqlite3
import os
import glob
from anthropic import Anthropic
from datetime import datetime

# Page config
st.set_page_config(
    page_title="Analysis Hub",
    page_icon="🔍",
    layout="wide"
)

# Initialize session state
if 'api_key' not in st.session_state:
    st.session_state.api_key = ""

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # API Key
    api_key = st.text_input(
        "Anthropic API Key",
        type="password",
        value=st.session_state.api_key,
        help="Get from console.anthropic.com"
    )
    
    if api_key:
        st.session_state.api_key = api_key
        st.success("✓ API key set")
    else:
        st.warning("⚠️ API key required")
    
    st.markdown("---")
    st.subheader("📁 Database Selection")
    
    # Auto-detect databases in current directory
    db_files = sorted(glob.glob("*.db"))
    
    active_db = None
    
    if db_files:
        st.markdown("**📂 Found in directory:**")
        selected_db = st.selectbox(
            "Select database",
            options=["-- Select Database --"] + db_files,
            key="db_dropdown"
        )
        
        if selected_db != "-- Select Database --":
            active_db = selected_db
            st.success(f"✓ Selected: {selected_db}")
    else:
        st.info("ℹ️ No .db files in current directory")
    
    st.markdown("---")
    st.markdown("**📤 Or upload/specify:**")
    
    # Upload option
    uploaded_db = st.file_uploader("Upload .db file", type=['db'], key="upload")
    
    if uploaded_db:
        temp_path = f"temp_{uploaded_db.name}"
        with open(temp_path, "wb") as f:
            f.write(uploaded_db.getbuffer())
        active_db = temp_path
        st.success(f"✓ Uploaded: {uploaded_db.name}")
    
    # Manual path option
    manual_path = st.text_input("Or enter full path", placeholder="/path/to/database.db", key="manual")
    
    if manual_path and os.path.exists(manual_path):
        active_db = manual_path
        st.success(f"✓ Using: {os.path.basename(manual_path)}")
    
    st.markdown("---")
    st.markdown("### 🔧 Tools")
    st.markdown("""
    **Quick (100 items):**
    - Discovery
    - Topic  
    - Theological
    
    **Deep (200+ items):**
    - Deep Dive
    - Full Corpus
    """)

# Helper functions
def detect_schema(db_path):
    """Auto-detect database schema"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    table_name = None
    for table in ['transcripts', 'articles', 'videos', 'sermons', 'content', 'posts', 'documents']:
        if table in tables:
            table_name = table
            break
    if not table_name and tables:
        table_name = tables[0]
    
    if not table_name:
        conn.close()
        return None, None, None, 0
    
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    
    title_col = None
    for col in ['title', 'name', 'video_title', 'subject', 'headline']:
        if col in columns:
            title_col = col
            break
    if not title_col:
        title_col = columns[0]
    
    content_col = None
    for col in ['transcript_text', 'content', 'text', 'body', 'transcript']:
        if col in columns:
            content_col = col
            break
    
    cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
    total = cursor.fetchone()[0]
    
    conn.close()
    return table_name, title_col, content_col, total

def get_sample_content(db_path, table_name, title_col, content_col, sample_size=100):
    """Get sample from database"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
    total = cursor.fetchone()[0]
    
    step = max(1, total // sample_size)
    
    try:
        cursor.execute(f'''
            SELECT {title_col}, {content_col}
            FROM {table_name} 
            WHERE {content_col} IS NOT NULL
            AND LENGTH({content_col}) > 100
            AND rowid % {step} = 0
            LIMIT {sample_size}
        ''')
    except:
        cursor.execute(f'''
            SELECT {title_col}, {content_col}
            FROM {table_name} 
            WHERE {content_col} IS NOT NULL
            LIMIT {sample_size}
        ''')
    
    results = cursor.fetchall()
    conn.close()
    return results

def get_all_content(db_path, table_name, title_col, content_col):
    """Get ALL content"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute(f'''
        SELECT {title_col}, {content_col}
        FROM {table_name} 
        WHERE {content_col} IS NOT NULL
        AND LENGTH({content_col}) > 100
    ''')
    
    results = cursor.fetchall()
    conn.close()
    return results

def chunk_content(sample, chunk_size=80000, items_per_chunk=30):
    """Split content into chunks"""
    chunks = []
    current_chunk = []
    current_length = 0
    current_items = 0
    
    for title, text in sample:
        text_str = str(text) if text else ""
        title_str = str(title) if title else "Untitled"
        excerpt = text_str[:2000]
        entry = f"Title: {title_str}\n{excerpt}\n\n"
        
        if current_items >= items_per_chunk or current_length + len(entry) > chunk_size:
            chunks.append("".join(current_chunk))
            current_chunk = [entry]
            current_length = len(entry)
            current_items = 1
        else:
            current_chunk.append(entry)
            current_length += len(entry)
            current_items += 1
    
    if current_chunk:
        chunks.append("".join(current_chunk))
    
    return chunks

# Main content
st.title("🔍 Analysis Hub")
st.markdown("*Complete content analysis toolkit*")

if not active_db:
    st.info("👈 Select a database from dropdown, upload, or enter path")
    st.markdown("""
    ### Analysis Types Available
    
    **Quick (100 items, 5-10 min, $5-10):**
    - 🔍 **Discovery** - What is this content about?
    - 🎯 **Topic** - Analyze specific topic
    - ⛪ **Theological** - Doctrine & orthodoxy check
    
    **Deep (200+ items, 10-60 min, $10-60+):**
    - 🔬 **Deep Dive** - Investigate specific concerns  
    - 📊 **Full Corpus** - Process EVERY item
    """)
    st.stop()

if not st.session_state.api_key:
    st.warning("⚠️ Enter API key in sidebar")
    st.stop()

# Show database info
schema_info = detect_schema(active_db)
if schema_info[0]:
    table_name, title_col, content_col, total_items = schema_info
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Database", os.path.basename(active_db))
    with col2:
        st.metric("Table", table_name)
    with col3:
        st.metric("Total Items", total_items)
else:
    st.error("Could not detect database schema")
    st.stop()

# Tabs
st.markdown("---")
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🔍 Discovery", 
    "🎯 Topic", 
    "⛪ Theological",
    "🔬 Deep Dive",
    "📊 Full Corpus"
])

# TAB 1: DISCOVERY
with tab1:
    st.header("🔍 Discovery Profile")
    st.markdown("Discovers what content is about - **no topic needed**")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        if st.button("🚀 Run Discovery Analysis", type="primary", key="discovery_btn", use_container_width=True):
            with st.spinner("Sampling content..."):
                sample = get_sample_content(active_db, table_name, title_col, content_col)
                chunks = chunk_content(sample)
            
            st.success(f"✓ Processing {len(sample)} items in {len(chunks)} chunks")
            
            client = Anthropic(api_key=st.session_state.api_key)
            analyses = []
            
            progress_bar = st.progress(0)
            status = st.empty()
            
            for i, chunk in enumerate(chunks):
                status.text(f"Analyzing chunk {i+1}/{len(chunks)}...")
                
                prompt = f"""Analyze this content and discover what it's about:

1. **Main Topics** (3-5): What subjects dominate?
2. **Core Message**: Central narrative
3. **Worldview**: Underlying beliefs
4. **Red Flags**: Concerning patterns (if any)
5. **Examples**: Specific quotes

CONTENT:
{chunk}"""
                
                try:
                    msg = client.messages.create(
                        model="claude-sonnet-4-20250514",
                        max_tokens=1500,
                        temperature=0.3,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    analyses.append(msg.content[0].text)
                except Exception as e:
                    analyses.append(f"Error: {e}")
                
                progress_bar.progress((i+1)/len(chunks))
            
            status.text("Synthesizing findings...")
            
            # Synthesize
            combined = "\n\n---CHUNK---\n\n".join(analyses)
            synthesis = f"""Synthesize into ONE profile:

1. **Executive Summary** (3-4 sentences)
2. **Primary Topics** (top 3-5)
3. **Core Message**
4. **Worldview**
5. **Red Flags** (if any)
6. **Bottom Line** (2-3 sentences)

ANALYSES:
{combined}"""
            
            msg = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2500,
                temperature=0.3,
                messages=[{"role": "user", "content": synthesis}]
            )
            
            result = msg.content[0].text
            
            progress_bar.progress(1.0)
            status.text("✓ Complete!")
            
            st.markdown("---")
            st.markdown("### 📊 Discovery Results")
            st.markdown(result)
            
            st.download_button(
                "📥 Download Report",
                data=result,
                file_name=f"discovery_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain"
            )
    
    with col2:
        st.markdown("**About**")
        st.markdown("Sample: 100 items")
        st.markdown("Time: 5-10 min")
        st.markdown("Cost: ~$5-10")

# TAB 2: TOPIC
with tab2:
    st.header("🎯 Topic Analysis")
    st.markdown("Analyze content about a **specific topic**")
    
    topic = st.text_input("Enter topic to analyze", placeholder="e.g., healing, prophecy, UFOs", key="topic_input")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        if st.button("🚀 Analyze Topic", type="primary", disabled=not topic, key="topic_btn", use_container_width=True):
            with st.spinner("Sampling content..."):
                sample = get_sample_content(active_db, table_name, title_col, content_col)
                chunks = chunk_content(sample)
            
            st.success(f"✓ Analyzing '{topic}' across {len(sample)} items")
            
            client = Anthropic(api_key=st.session_state.api_key)
            analyses = []
            
            progress_bar = st.progress(0)
            status = st.empty()
            
            for i, chunk in enumerate(chunks):
                status.text(f"Analyzing chunk {i+1}/{len(chunks)}...")
                
                prompt = f"""Analyze this content about "{topic}":

1. **Main Position**: What's the stance on {topic}?
2. **Key Claims**: Specific assertions about {topic}
3. **Evidence**: What's cited?
4. **Concerns**: Problems or red flags
5. **Examples**: Specific quotes

CONTENT:
{chunk}"""
                
                try:
                    msg = client.messages.create(
                        model="claude-sonnet-4-20250514",
                        max_tokens=1500,
                        temperature=0.3,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    analyses.append(msg.content[0].text)
                except Exception as e:
                    analyses.append(f"Error: {e}")
                
                progress_bar.progress((i+1)/len(chunks))
            
            status.text("Synthesizing analysis...")
            
            combined = "\n\n---CHUNK---\n\n".join(analyses)
            synthesis = f"""Synthesize analysis of "{topic}":

1. **Executive Summary**
2. **Main Position** on {topic}
3. **Core Claims**
4. **Evidence Quality**
5. **Concerns** (if any)
6. **Bottom Line**

ANALYSES:
{combined}"""
            
            msg = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                temperature=0.3,
                messages=[{"role": "user", "content": synthesis}]
            )
            
            result = msg.content[0].text
            
            progress_bar.progress(1.0)
            status.text("✓ Complete!")
            
            st.markdown("---")
            st.markdown(f"### 📊 Topic Analysis: {topic}")
            st.markdown(result)
            
            topic_slug = topic.lower().replace(' ', '_')
            st.download_button(
                "📥 Download Report",
                data=result,
                file_name=f"topic_{topic_slug}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
                key="topic_download"
            )
    
    with col2:
        st.markdown("**About**")
        st.markdown("Sample: 100 items")
        st.markdown("Time: 5-10 min")
        st.markdown("Cost: ~$5-10")

# TAB 3: THEOLOGICAL
with tab3:
    st.header("⛪ Theological Analysis")
    st.markdown("Analyze Christian content for **doctrine & orthodoxy**")
    
    st.info("✨ Improved: Checks for what IS present before claiming missing")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        if st.button("🚀 Run Theological Analysis", type="primary", key="theo_btn", use_container_width=True):
            with st.spinner("Sampling sermons..."):
                sample = get_sample_content(active_db, table_name, title_col, content_col)
                chunks = chunk_content(sample)
            
            st.success(f"✓ Processing {len(sample)} items")
            
            client = Anthropic(api_key=st.session_state.api_key)
            analyses = []
            
            progress_bar = st.progress(0)
            status = st.empty()
            
            for i, chunk in enumerate(chunks):
                status.text(f"Analyzing chunk {i+1}/{len(chunks)}...")
                
                prompt = f"""Analyze theologically - be ACCURATE:

**CRITICAL: Look for what IS present, don't assume missing**

1. **Theological Stream**: Reformed, Charismatic, NAR, etc.
2. **Gospel Present?**: Look for sin, repentance, faith, Jesus' death/resurrection
   - Quote examples if found
   - Only say absent if truly missing
3. **Top Themes**: What's emphasized
4. **Doctrinal Concerns**: Red flags (if any)
5. **Strengths**: What's done well

Be fair and accurate.

TRANSCRIPTS:
{chunk}"""
                
                try:
                    msg = client.messages.create(
                        model="claude-sonnet-4-20250514",
                        max_tokens=1800,
                        temperature=0.3,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    analyses.append(msg.content[0].text)
                except Exception as e:
                    analyses.append(f"Error: {e}")
                
                progress_bar.progress((i+1)/len(chunks))
            
            status.text("Synthesizing profile...")
            
            combined = "\n\n---CHUNK---\n\n".join(analyses)
            synthesis = f"""Synthesize ACCURATE theological profile:

**If gospel IS in chunks, say so clearly**

1. **Theological Stream**
2. **Gospel Presentation**: Present? Clear? Quote examples
3. **Top Themes**
4. **Concerns** (if validated)
5. **Strengths**
6. **Overall Verdict**: Orthodox / Mostly Orthodox / Concerning / Heterodox

ANALYSES:
{combined}"""
            
            msg = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                temperature=0.3,
                messages=[{"role": "user", "content": synthesis}]
            )
            
            result = msg.content[0].text
            
            progress_bar.progress(1.0)
            status.text("✓ Complete!")
            
            st.markdown("---")
            st.markdown("### 📊 Theological Profile")
            st.markdown(result)
            
            st.download_button(
                "📥 Download Report",
                data=result,
                file_name=f"theological_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
                key="theo_download"
            )
    
    with col2:
        st.markdown("**About**")
        st.markdown("Sample: 100 items")
        st.markdown("Time: 5-10 min")
        st.markdown("Cost: ~$5-10")
        st.markdown("**Improved accuracy!**")

# TAB 4: DEEP DIVE
with tab4:
    st.header("🔬 Deep Dive Investigation")
    st.markdown("Investigate a **specific concern** in detail")
    
    concern = st.text_input("What concern to investigate?", placeholder="e.g., mysticism, prosperity gospel", key="concern_input")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        if st.button("🔍 Investigate Concern", type="primary", disabled=not concern, key="dive_btn", use_container_width=True):
            with st.spinner("Sampling content (larger sample)..."):
                sample = get_sample_content(active_db, table_name, title_col, content_col, sample_size=200)
                chunks = chunk_content(sample, items_per_chunk=35)
            
            st.success(f"✓ Investigating '{concern}' across {len(sample)} items")
            
            client = Anthropic(api_key=st.session_state.api_key)
            investigations = []
            
            progress_bar = st.progress(0)
            status = st.empty()
            
            for i, chunk in enumerate(chunks):
                status.text(f"Investigating chunk {i+1}/{len(chunks)}...")
                
                prompt = f"""INVESTIGATE: {concern}

1. **Frequency**: How often appears?
2. **Examples**: Quote 5-10 specific examples
3. **Severity**: Minor / Moderate / Major / Severe
4. **Patterns**: What patterns?
5. **Impact**: Potential harm?
6. **Verdict**: Validated?

CONTENT:
{chunk}"""
                
                try:
                    msg = client.messages.create(
                        model="claude-sonnet-4-20250514",
                        max_tokens=2000,
                        temperature=0.2,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    investigations.append(msg.content[0].text)
                except Exception as e:
                    investigations.append(f"Error: {e}")
                
                progress_bar.progress((i+1)/len(chunks))
            
            status.text("Compiling investigation report...")
            
            combined = "\n\n---INVESTIGATION---\n\n".join(investigations)
            synthesis = f"""INVESTIGATION REPORT: {concern}

1. **EXECUTIVE SUMMARY**
2. **EVIDENCE** (10-15 examples with quotes)
3. **FREQUENCY & PREVALENCE**
4. **SEVERITY RATING** (1-10)
5. **PATTERN ANALYSIS**
6. **RECOMMENDATIONS**
7. **FINAL VERDICT**

DATA:
{combined}"""
            
            msg = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=3500,
                temperature=0.2,
                messages=[{"role": "user", "content": synthesis}]
            )
            
            result = msg.content[0].text
            
            progress_bar.progress(1.0)
            status.text("✓ Investigation complete!")
            
            st.markdown("---")
            st.markdown(f"### 🔬 Investigation: {concern}")
            st.markdown(result)
            
            concern_slug = concern.lower().replace(' ', '_')
            st.download_button(
                "📥 Download Investigation",
                data=result,
                file_name=f"deep_dive_{concern_slug}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
                key="dive_download"
            )
    
    with col2:
        st.markdown("**About**")
        st.markdown("Sample: 200 items")
        st.markdown("Time: 10-15 min")
        st.markdown("Cost: ~$10-15")
        st.markdown("**Detailed evidence**")

# TAB 5: FULL CORPUS
with tab5:
    st.header("📊 Full Corpus Analysis")
    st.markdown("Analyze **EVERY SINGLE ITEM** (not a sample)")
    
    st.warning("⚠️ EXPENSIVE - Processes ALL items")
    
    # Cost estimate
    if total_items:
        chunks_est = (total_items // 30) + 1
        cost_min = chunks_est * 0.5
        cost_max = chunks_est * 1.0
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Items to Process", total_items)
        with col2:
            st.metric("Time Est.", f"{chunks_est*0.5:.0f}-{chunks_est:.0f} min")
        with col3:
            st.metric("Cost Est.", f"${cost_min:.0f}-${cost_max:.0f}")
    
    analysis_type = st.radio(
        "Analysis Type",
        ["Discovery", "Theological"],
        key="corpus_type"
    )
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        confirm = st.checkbox(f"I understand: ALL {total_items} items, ${cost_min:.0f}-${cost_max:.0f}", key="corpus_confirm")
        
        if st.button("📊 Run Full Corpus", type="primary", disabled=not confirm, key="corpus_btn", use_container_width=True):
            with st.spinner("Loading entire database..."):
                all_items = get_all_content(active_db, table_name, title_col, content_col)
                chunks = chunk_content(all_items, items_per_chunk=30)
            
            st.success(f"✓ Processing ALL {len(all_items)} items in {len(chunks)} chunks")
            
            client = Anthropic(api_key=st.session_state.api_key)
            analyses = []
            
            progress_bar = st.progress(0)
            status = st.empty()
            
            # Choose prompt
            if analysis_type == "Discovery":
                base_prompt = """Analyze for patterns:
1. Main topics
2. Core message
3. Worldview
4. Red flags
5. Examples

CONTENT: {chunk}"""
            else:
                base_prompt = """Analyze theologically:
1. Theological stream
2. Gospel clarity
3. Top themes
4. Concerns
5. Strengths

TRANSCRIPTS: {chunk}"""
            
            for i, chunk in enumerate(chunks):
                progress = (i+1)/len(chunks)*100
                status.text(f"[{progress:.1f}%] Processing chunk {i+1}/{len(chunks)}...")
                
                try:
                    msg = client.messages.create(
                        model="claude-sonnet-4-20250514",
                        max_tokens=1500,
                        temperature=0.3,
                        messages=[{"role": "user", "content": base_prompt.format(chunk=chunk)}]
                    )
                    analyses.append(msg.content[0].text)
                except Exception as e:
                    analyses.append(f"[Error]")
                
                progress_bar.progress((i+1)/len(chunks))
            
            status.text("Synthesizing complete corpus...")
            
            combined = "\n\n---\n\n".join(analyses)
            synthesis = f"""FULL CORPUS SYNTHESIS - {len(all_items)} items:

1. **EXECUTIVE SUMMARY**
2. **DOMINANT THEMES**
3. **CORE MESSAGE**
4. **PATTERNS**
5. **STRENGTHS**
6. **CONCERNS**
7. **VERDICT**
8. **STATISTICS**: {len(all_items)} items, {len(chunks)} chunks

DATA:
{combined}"""
            
            msg = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                temperature=0.3,
                messages=[{"role": "user", "content": synthesis}]
            )
            
            result = msg.content[0].text
            
            progress_bar.progress(1.0)
            status.text("✓ Full corpus complete!")
            
            st.markdown("---")
            st.markdown("### 📊 Full Corpus Report")
            st.markdown(result)
            
            st.download_button(
                "📥 Download Full Report",
                data=result,
                file_name=f"full_corpus_{analysis_type.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
                key="corpus_download"
            )
    
    with col2:
        st.markdown("**About**")
        st.markdown(f"Sample: ALL {total_items}")
        st.markdown("Time: Varies")
        st.markdown("Cost: See estimate")
        st.markdown("**Definitive!**")

# Footer
st.markdown("---")
st.markdown("*Analysis Hub - Auto-Detect Databases*")
