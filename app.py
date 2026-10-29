import streamlit as st
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import date
import io

APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "lyrics_knowledge.db"

st.set_page_config(page_title="灵感作词局 · 中文歌词知识库", page_icon="🎼", layout="wide")

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS songs (
            song_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            artist TEXT,
            release_date TEXT,
            genre TEXT,
            platform TEXT,
            chart_name TEXT,
            chart_rank INTEGER,
            source_url TEXT,
            permission_status TEXT DEFAULT '待核验',
            lyric_text TEXT,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS analyses (
            analysis_id INTEGER PRIMARY KEY AUTOINCREMENT,
            song_id INTEGER,
            theme TEXT,
            narrative TEXT,
            imagery TEXT,
            emotion_arc TEXT,
            rhyme_notes TEXT,
            line_structure TEXT,
            hook_type TEXT,
            hook_score INTEGER,
            singability_score INTEGER,
            originality_notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(song_id) REFERENCES songs(song_id)
        );
        CREATE TABLE IF NOT EXISTS writing_samples (
            sample_id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_type TEXT,
            prompt TEXT,
            original_text TEXT,
            revised_text TEXT,
            rating INTEGER,
            rating_notes TEXT,
            rights_status TEXT DEFAULT '原创/已获授权',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """)

def query_df(sql, params=()):
    with get_conn() as conn:
        return pd.read_sql_query(sql, conn, params=params)

def execute(sql, params=()):
    with get_conn() as conn:
        conn.execute(sql, params)
        conn.commit()

init_db()

st.title("🎼 灵感作词局")
st.caption("中文歌词知识库 · 专业分析 · 原创训练样本")
st.info("独立新项目第一版：先管理歌曲元数据、授权状态、结构化分析和原创样本。未经许可的商业歌词不要粘贴或用于训练。")

with st.sidebar:
    st.header("工作台")
    page = st.radio("选择模块", [
        "总览", "歌曲资料库", "新增歌曲", "歌词结构分析", "原创训练样本", "数据导入导出"
    ])
    st.divider()
    st.caption("第一版无需 API Key。数据库保存在应用运行目录；免费云托管可能重启或重部署后丢失本地文件，重要数据请定期导出备份。")

if page == "总览":
    songs = query_df("SELECT * FROM songs")
    analyses = query_df("SELECT * FROM analyses")
    samples = query_df("SELECT * FROM writing_samples")
    c1, c2, c3 = st.columns(3)
    c1.metric("歌曲记录", len(songs))
    c2.metric("分析记录", len(analyses))
    c3.metric("创作样本", len(samples))
    st.subheader("建议的工作流程")
    st.markdown("""
    1. **发现歌曲**：先录入歌名、歌手、榜单信息和来源链接。
    2. **核验授权**：记录歌词是否允许保存、分析和训练。
    3. **结构化分析**：把主题、叙事、韵脚、句式、Hook、可唱性等变成可检索字段。
    4. **积累原创样本**：保存自己的创作要求、初稿、精修稿和人工评分。
    5. **定期导出备份**：通过“数据导入导出”保存 CSV 文件。
    """)
    st.subheader("最近录入的歌曲")
    if songs.empty:
        st.write("目前还没有歌曲记录。请从左侧进入“新增歌曲”。")
    else:
        st.dataframe(songs[["song_id","title","artist","genre","chart_rank","permission_status","created_at"]].tail(10), use_container_width=True, hide_index=True)

elif page == "歌曲资料库":
    st.subheader("歌曲资料库")
    q = st.text_input("搜索歌名、歌手、曲风或主题备注")
    df = query_df("""SELECT song_id,title,artist,release_date,genre,platform,chart_name,chart_rank,
                     source_url,permission_status,notes,created_at FROM songs
                     WHERE title LIKE ? OR artist LIKE ? OR genre LIKE ? OR notes LIKE ?
                     ORDER BY created_at DESC""", tuple([f"%{q}%"]*4))
    st.dataframe(df, use_container_width=True, hide_index=True)
    if not df.empty:
        st.caption("如需修改或删除记录，第一版建议先导出备份；后续版本可以增加逐条编辑、删除和批量审核。")

elif page == "新增歌曲":
    st.subheader("新增歌曲记录")
    st.caption("只记录元数据即可开始建库；歌词正文为可选项，仅在你拥有版权或已获得明确许可时填写。")
    with st.form("new_song", clear_on_submit=True):
        title = st.text_input("歌曲名称 *")
        artist = st.text_input("歌手")
        release_date = st.text_input("发行日期", placeholder="例如 2025-08-01")
        genre = st.text_input("曲风/类型")
        platform = st.text_input("平台")
        chart_name = st.text_input("榜单名称")
        chart_rank = st.number_input("榜单排名（没有可填 0）", min_value=0, step=1)
        source_url = st.text_input("来源链接")
        permission_status = st.selectbox("歌词授权状态", [
            "待核验", "仅元数据", "自有原创", "已获明确授权", "公有领域（已核实）", "禁止使用", "已撤回"
        ])
        lyric_text = st.text_area("歌词正文（仅限自有或明确获授权文本）", height=180)
        notes = st.text_area("备注/采集说明")
        submitted = st.form_submit_button("保存歌曲")
        if submitted:
            if not title.strip():
                st.error("请先填写歌曲名称。")
            elif permission_status in ["待核验", "仅元数据", "禁止使用", "已撤回"] and lyric_text.strip():
                st.error("当前授权状态不允许录入歌词正文。请清空歌词正文，或在确认权利后选择合适状态。")
            else:
                execute("""INSERT INTO songs(title,artist,release_date,genre,platform,chart_name,chart_rank,
                            source_url,permission_status,lyric_text,notes)
                            VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                        (title.strip(), artist, release_date, genre, platform, chart_name, int(chart_rank),
                         source_url, permission_status, lyric_text, notes))
                st.success("歌曲记录已保存。")

elif page == "歌词结构分析":
    st.subheader("歌词结构分析")
    songs = query_df("SELECT song_id,title,artist,permission_status,lyric_text FROM songs ORDER BY title")
    if songs.empty:
        st.warning("请先新增歌曲。")
    else:
        labels = {f"{r['song_id']} · {r['title']} — {r['artist'] or '歌手未填'}": int(r["song_id"]) for _, r in songs.iterrows()}
        chosen = st.selectbox("选择歌曲", list(labels.keys()))
        song_id = labels[chosen]
        selected = songs[songs["song_id"] == song_id].iloc[0]
        if selected["permission_status"] in ["待核验", "仅元数据", "禁止使用", "已撤回"]:
            st.warning("该歌曲当前未确认歌词使用权限。你可以记录基于公开元数据或独立创作经验形成的分析笔记，但不要粘贴未获授权的歌词正文。")
        with st.form("analysis_form", clear_on_submit=True):
            theme = st.text_input("主题/核心矛盾")
            narrative = st.text_input("叙事视角与推进方式")
            imagery = st.text_area("画面感/意象")
            emotion_arc = st.text_input("情绪曲线（开端→转折→结尾）")
            rhyme_notes = st.text_input("韵脚与押韵规律")
            line_structure = st.text_input("句式/字数/断句特点")
            hook_type = st.text_input("Hook 类型与记忆点")
            c1, c2 = st.columns(2)
            hook_score = c1.slider("Hook 记忆度", 1, 5, 3)
            singability_score = c2.slider("可唱性", 1, 5, 3)
            originality_notes = st.text_area("原创创作启发（不要复制歌词原句）")
            save = st.form_submit_button("保存分析")
            if save:
                execute("""INSERT INTO analyses(song_id,theme,narrative,imagery,emotion_arc,rhyme_notes,
                            line_structure,hook_type,hook_score,singability_score,originality_notes)
                            VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                        (song_id,theme,narrative,imagery,emotion_arc,rhyme_notes,line_structure,
                         hook_type,hook_score,singability_score,originality_notes))
                st.success("分析已保存。")
    st.subheader("已有分析")
    adf = query_df("""SELECT a.analysis_id,s.title,s.artist,a.theme,a.narrative,a.rhyme_notes,
                      a.hook_type,a.hook_score,a.singability_score,a.created_at
                      FROM analyses a LEFT JOIN songs s ON a.song_id=s.song_id
                      ORDER BY a.created_at DESC""")
    st.dataframe(adf, use_container_width=True, hide_index=True)

elif page == "原创训练样本":
    st.subheader("原创训练样本")
    st.caption("这里优先积累你自己写的歌词、修改前后对比、创作指令和人工偏好判断。")
    with st.form("sample_form", clear_on_submit=True):
        task_type = st.selectbox("任务类型", ["原创歌词", "歌词精修", "副歌Hook优化", "押韵检查", "句式/可唱性优化", "偏好比较"])
        prompt = st.text_area("创作要求/输入")
        original_text = st.text_area("初稿/原始文本（请确保有权使用）")
        revised_text = st.text_area("目标稿/修改稿（请确保有权使用）")
        rating = st.slider("整体质量评分", 1, 5, 3)
        rating_notes = st.text_area("评分理由（商业性、文学性、画面感、可唱性、押韵、Hook、原创性）")
        rights_status = st.selectbox("样本权利状态", ["原创/已获授权", "待核验"])
        save_sample = st.form_submit_button("保存样本")
        if save_sample:
            if rights_status != "原创/已获授权" and (original_text.strip() or revised_text.strip()):
                st.error("请不要把权利状态待核验的歌词正文存入训练样本。")
            else:
                execute("""INSERT INTO writing_samples(task_type,prompt,original_text,revised_text,rating,rating_notes,rights_status)
                            VALUES(?,?,?,?,?,?,?)""",
                        (task_type,prompt,original_text,revised_text,rating,rating_notes,rights_status))
                st.success("训练样本已保存。")
    samples = query_df("SELECT sample_id,task_type,prompt,rating,rating_notes,rights_status,created_at FROM writing_samples ORDER BY created_at DESC")
    st.dataframe(samples, use_container_width=True, hide_index=True)

elif page == "数据导入导出":
    st.subheader("数据导入导出")
    st.warning("建议每次批量导入前先下载备份。导入歌曲 CSV 时，必须包含 title 列；其他字段可留空。")
    all_tables = {
        "songs": "SELECT * FROM songs",
        "rights": None,
        "lyric_analysis": None,
        "analyses": "SELECT * FROM analyses",
        "training_examples": None,
        "writing_samples": "SELECT * FROM writing_samples",
        "text_assets": None
    }
    for name, sql in all_tables.items():
        if sql:
            df = query_df(sql)
            st.download_button(f"下载 {name}.csv", df.to_csv(index=False).encode("utf-8-sig"),
                               file_name=f"{name}.csv", mime="text/csv", key=f"dl_{name}")
    st.divider()
    uploaded = st.file_uploader("导入歌曲 CSV", type=["csv"])
    if uploaded is not None:
        try:
            imported = pd.read_csv(uploaded)
            if "title" not in imported.columns:
                st.error("CSV 必须有 title 列。请先下载 songs.csv 查看字段。")
            else:
                st.write("导入预览")
                st.dataframe(imported.head(20), use_container_width=True)
                if st.button("确认导入歌曲"):
                    allowed = ["title","artist","release_date","genre","platform","chart_name","chart_rank",
                               "source_url","permission_status","lyric_text","notes"]
                    for col in allowed:
                        if col not in imported.columns:
                            imported[col] = None
                    for _, r in imported.iterrows():
                        status = r.get("permission_status") or "待核验"
                        lyric = r.get("lyric_text")
                        if status in ["待核验", "仅元数据", "禁止使用", "已撤回"]:
                            lyric = None
                        execute("""INSERT INTO songs(title,artist,release_date,genre,platform,chart_name,chart_rank,
                                    source_url,permission_status,lyric_text,notes) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                                (str(r.get("title") or "").strip(), r.get("artist"), r.get("release_date"),
                                 r.get("genre"), r.get("platform"), r.get("chart_name"),
                                 int(r.get("chart_rank") or 0), r.get("source_url"), status, lyric, r.get("notes")))
                    st.success(f"已导入 {len(imported)} 条歌曲记录。")
        except Exception as e:
            st.error(f"读取失败：{e}")

st.divider()
st.caption("灵感作词局 · 第一版 MVP。后续可增加榜单自动发现、批量去重、授权审核队列、AI 分析接口、向量检索和评测面板。")
