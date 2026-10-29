import hmac
import io
from datetime import date

import pandas as pd
import streamlit as st
from supabase import create_client


st.set_page_config(
    page_title="灵感作词局 · 中文歌词知识库",
    page_icon="🎼",
    layout="wide",
)


# ---------- 1. 连接 Supabase ----------

@st.cache_resource
def get_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


try:
    if not st.secrets.get("SUPABASE_URL") or not st.secrets.get("SUPABASE_KEY"):
        st.error("缺少 Supabase 配置，请检查 Streamlit 的 Secrets。")
        st.stop()

    supabase = get_supabase()

except Exception as e:
    st.error("Supabase 初始化失败。请检查 Secrets 中的 URL 和 API Key。")
    st.caption(f"错误信息：{str(e)[:500]}")
    st.stop()


# ---------- 2. 简单的网页登录密码 ----------

app_password = st.secrets.get("APP_PASSWORD", "")

if app_password:
    if not st.session_state.get("authenticated", False):
        st.title("🎼 灵感作词局")
        st.caption("请输入网页登录密码")

        with st.form("login_form"):
            entered_password = st.text_input(
                "网页登录密码",
                type="password",
            )
            login_clicked = st.form_submit_button("登录")

        if login_clicked:
            if hmac.compare_digest(entered_password, app_password):
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("密码不正确，请重新输入。")

        st.stop()


# ---------- 3. 数据库通用操作 ----------

def fetch_rows(table, order_by="created_at", descending=True):
    query = supabase.table(table).select("*")

    if order_by:
        query = query.order(order_by, desc=descending)

    response = query.execute()
    return response.data or []


def fetch_df(table, order_by="created_at", descending=True):
    return pd.DataFrame(
        fetch_rows(table, order_by=order_by, descending=descending)
    )


def insert_row(table, data):
    supabase.table(table).insert(data).execute()


def clean_text(value):
    if value is None or pd.isna(value):
        return None
    value = str(value).strip()
    return value if value else None


def clean_rank(value):
    try:
        if value is None or pd.isna(value) or str(value).strip() == "":
            return None
        return int(float(value))
    except (ValueError, TypeError):
        return None


def check_connection():
    for table in ("songs", "analyses", "writing_samples"):
        supabase.table(table).select("*").limit(1).execute()


# 验证三个表都可以通过 Supabase API 访问
try:
    check_connection()
except Exception as e:
    st.error("已初始化 Supabase 客户端，但读取数据表失败。")
    st.warning(
        "请检查三个表是否存在、Data API 是否启用，以及 API Key "
        "是否有权限访问这些表。"
    )
    st.caption(f"错误信息：{str(e)[:700]}")
    st.stop()


# ---------- 4. 页面导航 ----------

st.title("🎼 灵感作词局")
st.caption("中文歌词知识库 · 专业分析 · 原创训练样本")
st.info(
    "独立新项目：管理歌曲元数据、授权状态、结构化分析和原创样本。"
    "未经许可的商业歌词不要粘贴或用于训练。"
)

with st.sidebar:
    st.header("工作台")
    page = st.radio(
        "选择模块",
        [
            "总览",
            "歌曲资料库",
            "新增歌曲",
            "歌词结构分析",
            "原创训练样本",
            "数据导入导出",
        ],
    )

    st.divider()
    st.caption("数据存储在 Supabase 云端数据库。请定期导出 CSV 备份。")

    if app_password and st.button("退出登录"):
        st.session_state["authenticated"] = False
        st.rerun()


# ---------- 5. 总览 ----------

if page == "总览":
    songs = fetch_df("songs")
    analyses = fetch_df("analyses")
    samples = fetch_df("writing_samples")

    c1, c2, c3 = st.columns(3)
    c1.metric("歌曲记录", len(songs))
    c2.metric("分析记录", len(analyses))
    c3.metric("创作样本", len(samples))

    st.subheader("建议的工作流程")
    st.markdown(
        """
        1. **发现歌曲**：录入歌名、歌手、榜单信息和来源链接。
        2. **核验授权**：记录歌词是否允许保存、分析和训练。
        3. **结构化分析**：整理主题、叙事、韵脚、句式、Hook 和可唱性。
        4. **积累原创样本**：保存创作要求、初稿、精修稿和人工评分。
        5. **定期备份**：在“数据导入导出”下载 CSV 文件。
        """
    )

    st.subheader("最近录入的歌曲")
    if songs.empty:
        st.write("目前还没有歌曲记录。请从左侧进入“新增歌曲”。")
    else:
        columns = [
            "song_id", "title", "artist", "genre",
            "chart_rank", "permission_status", "created_at",
        ]
        available = [c for c in columns if c in songs.columns]
        st.dataframe(
            songs[available].head(10),
            use_container_width=True,
            hide_index=True,
        )


# ---------- 6. 歌曲资料库 ----------

elif page == "歌曲资料库":
    st.subheader("歌曲资料库")
    q = st.text_input("搜索歌名、歌手、曲风或备注")

    df = fetch_df("songs")

    if not df.empty:
        if q.strip():
            search_columns = [
                c for c in ["title", "artist", "genre", "notes"]
                if c in df.columns
            ]
            mask = pd.Series(False, index=df.index)

            for column in search_columns:
                mask = mask | df[column].fillna("").astype(str).str.contains(
                    q.strip(), case=False, regex=False
                )

            df = df[mask]

        display_columns = [
            "song_id", "title", "artist", "release_date", "genre",
            "platform", "chart_name", "chart_rank", "source_url",
            "permission_status", "notes", "created_at",
        ]
        available = [c for c in display_columns if c in df.columns]
        st.dataframe(
            df[available],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("目前还没有歌曲记录。")


# ---------- 7. 新增歌曲 ----------

elif page == "新增歌曲":
    st.subheader("新增歌曲记录")
    st.caption(
        "只记录元数据即可开始建库。歌词正文仅限自有版权或已获得明确许可的文本。"
    )

    with st.form("new_song", clear_on_submit=True):
        title = st.text_input("歌曲名称 *")
        artist = st.text_input("歌手")
        release_date = st.text_input(
            "发行日期",
            placeholder="例如 2025-08-01",
        )
        genre = st.text_input("曲风/类型")
        platform = st.text_input("平台")
        chart_name = st.text_input("榜单名称")
        chart_rank = st.number_input(
            "榜单排名（没有可填 0）",
            min_value=0,
            step=1,
        )
        source_url = st.text_input("来源链接")

        permission_status = st.selectbox(
            "歌词授权状态",
            [
                "待核验",
                "仅元数据",
                "自有原创",
                "已获明确授权",
                "公有领域（已核实）",
                "禁止使用",
                "已撤回",
            ],
        )

        lyric_text = st.text_area(
            "歌词正文（仅限自有或明确获授权文本）",
            height=180,
        )
        notes = st.text_area("备注/采集说明")

        submitted = st.form_submit_button("保存歌曲")

        if submitted:
            restricted = [
                "待核验", "仅元数据", "禁止使用", "已撤回"
            ]

            if not title.strip():
                st.error("请先填写歌曲名称。")
            elif permission_status in restricted and lyric_text.strip():
                st.error(
                    "当前授权状态不允许录入歌词正文。"
                    "请清空歌词正文，或在确认权利后选择合适状态。"
                )
            else:
                try:
                    row = {
                        "title": title.strip(),
                        "artist": clean_text(artist),
                        "release_date": clean_text(release_date),
                        "genre": clean_text(genre),
                        "platform": clean_text(platform),
                        "chart_name": clean_text(chart_name),
                        "chart_rank": int(chart_rank) if chart_rank else None,
                        "source_url": clean_text(source_url),
                        "permission_status": permission_status,
                        "lyric_text": clean_text(lyric_text),
                        "notes": clean_text(notes),
                    }
                    insert_row("songs", row)
                    st.success("歌曲记录已保存到 Supabase。")
                except Exception as e:
                    st.error("保存失败，请检查数据库字段和权限。")
                    st.caption(f"错误信息：{str(e)[:500]}")


# ---------- 8. 歌词结构分析 ----------

elif page == "歌词结构分析":
    st.subheader("歌词结构分析")

    songs = fetch_df("songs")

    if songs.empty:
        st.warning("请先新增歌曲。")
    else:
        labels = {}

        for _, row in songs.iterrows():
            sid = row.get("song_id")
            title = row.get("title") or "未命名歌曲"
            artist = row.get("artist") or "歌手未填"
            labels[f"{sid} · {title} — {artist}"] = int(sid)

        chosen = st.selectbox("选择歌曲", list(labels.keys()))
        song_id = labels[chosen]
        selected = songs[songs["song_id"] == song_id].iloc[0]

        restricted = [
            "待核验", "仅元数据", "禁止使用", "已撤回"
        ]

        if selected.get("permission_status") in restricted:
            st.warning(
                "该歌曲当前未确认歌词使用权限。可以记录基于公开元数据"
                "或独立创作经验形成的分析笔记，但不要粘贴未获授权的歌词正文。"
            )

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

            originality_notes = st.text_area(
                "原创创作启发（不要复制歌词原句）"
            )
            save = st.form_submit_button("保存分析")

            if save:
                try:
                    row = {
                        "song_id": song_id,
                        "theme": clean_text(theme),
                        "narrative": clean_text(narrative),
                        "imagery": clean_text(imagery),
                        "emotion_arc": clean_text(emotion_arc),
                        "rhyme_notes": clean_text(rhyme_notes),
                        "line_structure": clean_text(line_structure),
                        "hook_type": clean_text(hook_type),
                        "hook_score": int(hook_score),
                        "singability_score": int(singability_score),
                        "originality_notes": clean_text(originality_notes),
                    }
                    insert_row("analyses", row)
                    st.success("分析已保存到 Supabase。")
                except Exception as e:
                    st.error("保存分析失败，请检查数据库字段和权限。")
                    st.caption(f"错误信息：{str(e)[:500]}")

    st.subheader("已有分析")
    adf = fetch_df("analyses")

    if not adf.empty:
        if not songs.empty:
            song_lookup = songs.set_index("song_id").to_dict("index")
            adf["歌曲名称"] = adf["song_id"].map(
                lambda sid: song_lookup.get(sid, {}).get("title", "歌曲已删除")
            )
            adf["歌手"] = adf["song_id"].map(
                lambda sid: song_lookup.get(sid, {}).get("artist", "")
            )

        columns = [
            "analysis_id", "歌曲名称", "歌手", "theme", "narrative",
            "rhyme_notes", "hook_type", "hook_score",
            "singability_score", "created_at",
        ]
        available = [c for c in columns if c in adf.columns]
        st.dataframe(
            adf[available],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("目前还没有分析记录。")


# ---------- 9. 原创训练样本 ----------

elif page == "原创训练样本":
    st.subheader("原创训练样本")
    st.caption(
        "优先积累自己创作的歌词、修改前后对比、创作指令和人工偏好判断。"
    )

    with st.form("sample_form", clear_on_submit=True):
        task_type = st.selectbox(
            "任务类型",
            [
                "原创歌词",
                "歌词精修",
                "副歌Hook优化",
                "押韵检查",
                "句式/可唱性优化",
                "偏好比较",
            ],
        )
        prompt = st.text_area("创作要求/输入")
        original_text = st.text_area("初稿/原始文本（请确保有权使用）")
        revised_text = st.text_area("目标稿/修改稿（请确保有权使用）")
        rating = st.slider("整体质量评分", 1, 5, 3)
        rating_notes = st.text_area(
            "评分理由（商业性、文学性、画面感、可唱性、押韵、Hook、原创性）"
        )
        rights_status = st.selectbox(
            "样本权利状态",
            ["原创/已获授权", "待核验"],
        )

        save_sample = st.form_submit_button("保存样本")

        if save_sample:
            if rights_status != "原创/已获授权" and (
                original_text.strip() or revised_text.strip()
            ):
                st.error(
                    "请不要把权利状态待核验的歌词正文存入训练样本。"
                )
            else:
                try:
                    row = {
                        "task_type": task_type,
                        "prompt": clean_text(prompt),
                        "original_text": clean_text(original_text),
                        "revised_text": clean_text(revised_text),
                        "rating": int(rating),
                        "rating_notes": clean_text(rating_notes),
                        "rights_status": rights_status,
                    }
                    insert_row("writing_samples", row)
                    st.success("训练样本已保存到 Supabase。")
                except Exception as e:
                    st.error("保存样本失败，请检查数据库字段和权限。")
                    st.caption(f"错误信息：{str(e)[:500]}")

    samples = fetch_df("writing_samples")

    if not samples.empty:
        columns = [
            "sample_id", "task_type", "prompt", "rating",
            "rating_notes", "rights_status", "created_at",
        ]
        available = [c for c in columns if c in samples.columns]
        st.dataframe(
            samples[available],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("目前还没有训练样本。")


# ---------- 10. 数据导入导出 ----------

elif page == "数据导入导出":
    st.subheader("数据导入导出")
    st.warning(
        "建议每次批量导入前先下载备份。导入歌曲 CSV 时，必须包含 title 列。"
    )

    tables = [
        ("songs", "歌曲资料"),
        ("analyses", "歌词分析"),
        ("writing_samples", "原创训练样本"),
    ]

    for table, label in tables:
        try:
            df = fetch_df(table)
            st.download_button(
                f"下载 {label} CSV",
                data=df.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"{table}.csv",
                mime="text/csv",
                key=f"download_{table}",
            )
        except Exception as e:
            st.error(f"读取 {label} 失败：{str(e)[:300]}")

    st.divider()
    st.subheader("导入歌曲 CSV")

    uploaded = st.file_uploader(
        "选择歌曲 CSV 文件",
        type=["csv"],
    )

    if uploaded is not None:
        try:
            imported = pd.read_csv(uploaded)

            if "title" not in imported.columns:
                st.error("CSV 必须有 title 列。")
            else:
                st.write("导入预览")
                st.dataframe(
                    imported.head(20),
                    use_container_width=True,
                    hide_index=True,
                )

                st.caption(
                    "导入时会跳过空歌名，并阻止未经授权状态的歌词正文入库。"
                )

                if st.button("确认导入歌曲"):
                    allowed = [
                        "title", "artist", "release_date", "genre",
                        "platform", "chart_name", "chart_rank",
                        "source_url", "permission_status",
                        "lyric_text", "notes",
                    ]

                    imported = imported.copy()

                    for col in allowed:
                        if col not in imported.columns:
                            imported[col] = None

                    success_count = 0
                    skipped_count = 0
                    errors = []

                    restricted = [
                        "待核验", "仅元数据", "禁止使用", "已撤回"
                    ]

                    for index, r in imported.iterrows():
                        title_value = clean_text(r.get("title"))

                        if not title_value:
                            skipped_count += 1
                            continue

                        status = clean_text(r.get("permission_status")) or "待核验"
                        lyric = clean_text(r.get("lyric_text"))

                        if status in restricted:
                            lyric = None

                        release_date = clean_text(r.get("release_date"))

                        row = {
                            "title": title_value,
                            "artist": clean_text(r.get("artist")),
                            "release_date": release_date,
                            "genre": clean_text(r.get("genre")),
                            "platform": clean_text(r.get("platform")),
                            "chart_name": clean_text(r.get("chart_name")),
                            "chart_rank": clean_rank(r.get("chart_rank")),
                            "source_url": clean_text(r.get("source_url")),
                            "permission_status": status,
                            "lyric_text": lyric,
                            "notes": clean_text(r.get("notes")),
                        }

                        try:
                            insert_row("songs", row)
                            success_count += 1
                        except Exception as e:
                            errors.append(
                                f"第 {index + 2} 行：{str(e)[:200]}"
                            )

                    st.success(
                        f"导入完成：成功 {success_count} 条，"
                        f"跳过空歌名 {skipped_count} 条，"
                        f"失败 {len(errors)} 条。"
                    )

                    if errors:
                        with st.expander("查看导入失败详情"):
                            for message in errors[:20]:
                                st.write(message)

        except Exception as e:
            st.error("CSV 读取失败，请确认文件格式正确。")
            st.caption(f"错误信息：{str(e)[:500]}")


st.divider()
st.caption(
    "灵感作词局 · Supabase 云端数据库版。请定期导出 CSV 备份，"
    "并只存储有权使用的歌词和创作样本。"
)
