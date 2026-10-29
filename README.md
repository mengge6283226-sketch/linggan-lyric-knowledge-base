# 灵感作词局 · 中文歌词知识库（独立在线网页）

## 本项目是什么
一个全新的 Streamlit 网页应用，第一版提供：
- 歌曲元数据管理
- 歌词正文授权状态提示
- 结构化歌词分析记录
- 原创训练样本管理
- CSV 导入导出

第一版不需要 API Key，也不接入旧项目。

## 重要：免费云端数据持久性
Streamlit Community Cloud 的本地文件并不适合当作永久数据库。第一版使用 SQLite 便于快速试用，请定期通过网页导出 CSV 备份。正式长期使用时建议改为外部托管数据库。

## 本地运行（Windows）
1. 安装 Python 3.11 或 3.12。
2. 解压项目文件。
3. 在项目文件夹地址栏输入 `cmd` 并回车。
4. 执行：
   ```bash
   py -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   streamlit run app.py
   ```

## 在线部署（Streamlit Community Cloud）
1. 在 GitHub 新建一个独立仓库，例如 `linggan-lyric-knowledge-base`。
2. 上传 `app.py`、`requirements.txt`、`README.md`。
3. 登录 Streamlit Community Cloud，连接 GitHub。
4. 创建新 app，选择新仓库、分支 `main`、主文件 `app.py`。
5. 部署完成后获得独立网页地址。

## 数据与版权注意
- 歌曲发行或歌词公开可见，不等于允许批量保存或模型训练。
- 未明确获准时，仅保存必要元数据、来源链接和原创分析笔记，不存完整歌词正文。
- 训练样本优先使用自有原创、明确授权的文本和人工创作的偏好数据。
- 需要定期导出数据备份；第一版不是生产级数据库。
