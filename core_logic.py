import os
import uuid
from datetime import datetime
from typing import List, Optional
from dotenv import load_dotenv

from fastapi.responses import FileResponse
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from openai import OpenAI
from elevenlabs.client import ElevenLabs

# ==========================================
# 0. 初始化与环境配置
# ==========================================
load_dotenv()

# 创建音频存放目录
AUDIO_DIR = "static/audios"
os.makedirs(AUDIO_DIR, exist_ok=True)

# 初始化 API 客户端
llm_client = OpenAI(
    api_key=os.getenv("LLM_API_KEY"),
    base_url=os.getenv("LLM_BASE_URL")
)
tts_client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

# 初始化 FastAPI
app = FastAPI(title="Auto Dubbing API", description="短视频出海配音工具后端")

# 允许跨域请求（方便本地前端联调）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态目录，方便前端直接通过 URL 播放/下载音频
app.mount("/static", StaticFiles(directory="static"), name="static")

# ==========================================
# 1. 数据库配置 (功能 2：历史记录)
# ==========================================
SQLALCHEMY_DATABASE_URL = "sqlite:///./history.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 定义历史记录表模型
class HistoryRecord(Base):
    __tablename__ = "history_records"
    id = Column(Integer, primary_key=True, index=True)
    cn_text = Column(String, index=True)
    en_text = Column(String)
    voice_id = Column(String)
    audio_url = Column(String)
    char_count = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)

Base.metadata.create_all(bind=engine)

# 数据库会话依赖
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==========================================
# 2. Pydantic 数据模型 (用于 API 请求体验证)
# ==========================================
class TranslationRequest(BaseModel):
    texts: List[str]  # 支持批量输入 (功能 3)
    style: str = "tiktok"

class TTSRequest(BaseModel):
    cn_text: str
    en_text: str
    voice_id: str

class BatchTTSRequest(BaseModel):
    items: List[TTSRequest] # 批量生成请求

# ==========================================
# 3. 核心 API 路由实现
# ==========================================

# 【功能 4】：获取 API 剩余额度与字符预估
@app.get("/api/quota")
def get_api_quota():
    try:
        # 调用 ElevenLabs 用户接口获取订阅信息
        sub_info = tts_client.user.subscription.get()
        return {
            "status": "success",
            "character_count": sub_info.character_count, # 已用字符数
            "character_limit": sub_info.character_limit, # 总额度
            "remaining": sub_info.character_limit - sub_info.character_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/estimate")
def estimate_cost(request: TranslationRequest):
    # 粗略预估：中文字符数 * 1.5 大约等于英文字符数（仅供前端展示参考）
    total_cn_chars = sum(len(text) for text in request.texts)
    est_en_chars = int(total_cn_chars * 1.5)
    return {"cn_chars": total_cn_chars, "estimated_en_chars": est_en_chars}

# 【功能 1】：获取音色库
@app.get("/api/voices")
def get_voices():
    try:
        voices_response = tts_client.voices.get_all()
        voices_list = []
        for v in voices_response.voices:
            voices_list.append({
                "voice_id": v.voice_id,
                "name": v.name,
                "category": v.category,
                "preview_url": v.preview_url, # 前端可以用这个 URL 播放音色试听
                "labels": v.labels # 包含口音、性别、使用场景等标签
            })
        return {"status": "success", "voices": voices_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 【功能 3】：批量翻译接口
@app.post("/api/translate")
def translate_texts(request: TranslationRequest):
    system_prompt = "你是一个资深的英文短视频编导。请将中文翻译为流畅、自然、有感染力的英文口播文案。要求：句子简短，口语化，适合直接朗读。只需输出英文结果，不要包含任何解释。"
    if request.style == "professional":
        system_prompt = "你是一个专业的新闻播音员。请将中文翻译为专业、严谨的英文播报文案。只需输出英文结果。"

    results = []
    for text in request.texts:
        try:
            response = llm_client.chat.completions.create(
                model="qwen-plus",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                temperature=0.7
            )
            en_text = response.choices[0].message.content.strip()
            results.append({"cn_text": text, "en_text": en_text, "status": "success"})
        except Exception as e:
            results.append({"cn_text": text, "en_text": "", "status": "error", "detail": str(e)})
            
    return {"status": "success", "data": results}

# 【功能 3 & 功能 2】：批量生成语音并保存历史记录
@app.post("/api/generate_audio")
def generate_audio_batch(request: BatchTTSRequest):
    db = SessionLocal()
    results = []
    
    for item in request.items:
        try:
            # 1. 生成唯一文件名
            file_name = f"audio_{uuid.uuid4().hex[:8]}.mp3"
            file_path = os.path.join(AUDIO_DIR, file_name)
            
            # 2. 调用 ElevenLabs API
            audio_generator = tts_client.text_to_speech.convert(
                text=item.en_text,
                voice_id=item.voice_id,
                model_id="eleven_turbo_v2_5",
                output_format="mp3_44100_128"
            )
            
            # 3. 将流保存到本地文件
            with open(file_path, "wb") as f:
                for chunk in audio_generator:
                    if chunk:
                        f.write(chunk)
            
            audio_url = f"/static/audios/{file_name}"
            char_count = len(item.en_text)
            
            # 4. 写入数据库 (历史记录)
            db_record = HistoryRecord(
                cn_text=item.cn_text,
                en_text=item.en_text,
                voice_id=item.voice_id,
                audio_url=audio_url,
                char_count=char_count
            )
            db.add(db_record)
            db.commit()
            db.refresh(db_record)
            
            results.append({
                "id": db_record.id,
                "cn_text": item.cn_text,
                "audio_url": audio_url,
                "status": "success"
            })
            
        except Exception as e:
            results.append({"cn_text": item.cn_text, "status": "error", "detail": str(e)})
            
    db.close()
    return {"status": "success", "data": results}

# 【功能 2】：获取历史记录接口
@app.get("/api/history")
def get_history(limit: int = 50, offset: int = 0):
    db = SessionLocal()
    records = db.query(HistoryRecord).order_by(HistoryRecord.created_at.desc()).offset(offset).limit(limit).all()
    db.close()
    
    return {
        "status": "success",
        "data": [
            {
                "id": r.id,
                "cn_text": r.cn_text,
                "en_text": r.en_text,
                "voice_id": r.voice_id,
                "audio_url": r.audio_url, # 前端拼接域名即可访问，如 http://localhost:8000/static/audios/xxx.mp3
                "char_count": r.char_count,
                "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S")
            } for r in records
        ]
    }

# 【新功能】：强制下载音频接口
@app.get("/api/download")
def force_download(file_url: str):
    # 提取真正的文件名 (例如从 /static/audios/xxx.mp3 中提取 xxx.mp3)
    file_name = file_url.split("/")[-1]
    file_path = os.path.join(AUDIO_DIR, file_name)

    if os.path.exists(file_path):
        # FileResponse 会自动设置 headers，强制浏览器弹出下载框
        return FileResponse(
            path=file_path, 
            filename=f"英文配音_{file_name}", # 给用户下载的文件重新命个好听的名字
            media_type="audio/mpeg"
        )
    raise HTTPException(status_code=404, detail="文件未找到")

# 启动命令提示
if __name__ == "__main__":
    import uvicorn
    print("正在启动服务器...")
    print("请在浏览器访问 API 文档页面: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)