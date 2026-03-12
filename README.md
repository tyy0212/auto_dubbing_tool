# auto_dubbing_tool
专为出海短视频与直播团队打造的智能配音工具，集成Qwen大模型翻译与 ElevenLabs 语音合成，支持人工润色与批量处理，有效提升产出效率并降低 API 试错成本。

## 🎯 开发背景与痛点

在出海短视频和直播运营场景下，团队通常面临以下痛点：
- **机翻生硬**：常规机器翻译的脚本不符合目标市场的口语习惯，语音合成后缺乏自然感。
- **试错成本高**：若直接将中文生成长段外语音频，一旦发现个别词汇翻译有误，重新生成将消耗大量昂贵的 TTS（如 ElevenLabs）API 额度。
- **批量处理繁琐**：多条短视频文案如果依赖手工操作，需要反复切换软件复制粘贴，效率低下。

基于此，本项目将工作流重构为“两步走”的最佳实践：**中文输入 ➡️ AI 口语化翻译 ➡️ 人工核对润色 ➡️ 批量生成语音 ➡️ 下载发布**。

## ✨ 核心功能特性
- **可复制可下载**：翻译后的英文文本支持一键复制，提供英文音频的播放和下载按钮。
- **智能语感翻译**：接入大语言模型（兼容 OpenAI、DeepSeek、Qwen 等接口），内置“口播风”与“专业风”等系统级 Prompt，确保翻译结果更贴合需要的口语风格。
- **两步走工作流**：将文本翻译与语音合成解耦。系统允许运营人员先对英文翻译结果进行手动修改和润色，确认无误后再提交生成语音，有效避免资源浪费。
- **高效批量处理**：支持在输入框内通过“空行”分隔多条独立文案，系统可一键执行批量翻译，并按队列生成对应的音频文件。
- **ElevenLabs 深度集成**：前端动态拉取 ElevenLabs 官方音色库，实时展示当前账号的剩余字符额度，方便监控 API 资源消耗。
- **历史记录存储**：内置轻量级 SQLite 数据库，自动归档所有生成的双语文案与音频文件，支持一键复制英文文本、在线试听及本地下载。
- **良好 UI 体验**：基于 Vue 3 + Tailwind CSS 构建，提供流畅的响应式界面、清晰的异步加载状态与全局错误提示。

## 🛠️ 技术栈
- **前端 (Frontend)**：HTML5, Vue 3 (CDN), Tailwind CSS (CDN), Phosphor Icons
- **后端 (Backend)**：Python 3.8+, FastAPI, Uvicorn, SQLAlchemy, SQLite
- **核心 AI 服务**：OpenAI API (或兼容格式的大模型接口), ElevenLabs SDK

## 🚀 快速上手指南
### 1. 环境准备
确保你的电脑上已安装 Python 3.8 或更高版本。克隆本项目到本地后，在项目根目录创建并激活虚拟环境：
```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境 (macOS/Linux)
source venv/bin/activate
# 激活虚拟环境 (Windows)
# venv\Scripts\activate

# 安装核心依赖
pip install fastapi uvicorn sqlalchemy pydantic openai elevenlabs python-dotenv
```
### 2. 配置环境变量
在项目根目录下创建一个名为 .env 的文件，填入你的 API 密钥：
```bash
# 大语言模型配置 (以 OpenAI 为例，也可替换为 DeepSeek 等兼容接口)
LLM_API_KEY="sk-你的大模型API-Key"
LLM_BASE_URL="[https://api.openai.com/v1](https://api.openai.com/v1)" 

# ElevenLabs 语音合成配置
# ⚠️ 注意：请确保你的 ElevenLabs Key 具备 voices_read 和 user_read 权限！
ELEVENLABS_API_KEY="sk_你的ElevenLabs-Key"
```

### 3. 启动服务
在终端中运行以下命令启动 FastAPI 后端服务：
```bash
python main.py
```
终端显示 Uvicorn running on http://0.0.0.0:8000 后，直接在浏览器中打开 http://127.0.0.1:8000 即可使用完整网页工具。
(你也可以访问 http://127.0.0.1:8000/docs 查看由 FastAPI 自动生成的交互式 API 文档。)

# 💡 使用小贴士
## 1. 如何批量生成多条视频配音？
在左侧“中文原稿”输入框中，在不同的视频脚本之间敲击 两次回车（留出一个空行）。系统会自动将它们识别为独立的任务并批量处理。
## 2. 下载的音频存在哪里？
除了通过网页右侧直接点击“下载 MP3”外，所有生成的音频文件也会静默保存在项目根目录下的 static/audios/ 文件夹中。
## 3. 快速查看自己的额度
页面右上角会展示 ElevenLabs 剩余额度，方便查询。

# 页面展示
<img width="1186" height="842" alt="截屏2026-03-12 下午8 20 32" src="https://github.com/user-attachments/assets/a5565efa-e38f-4fa8-8966-6ec1ba28b949" />
