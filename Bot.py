#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import logging
import os
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pytgcalls import PyTgCalls, StreamType
from pytgcalls.types.input_stream import AudioPiped, AudioVideoPiped
from pytgcalls.exceptions import NoActiveGroupCall
import yt_dlp
import json

# 鬲賳馗蹖賲丕鬲 API
API_ID = "27003875"  # 丕夭 my.telegram.org 亘诏蹖乇
API_HASH = "8c8575dfd6a7f5ecaa7804c6214ccac5"  # 丕夭 my.telegram.org 亘诏蹖乇  
BOT_TOKEN = "8102242216:AAE7Vu-Batpl80NLX65HQY-rLHTMED23wyE"
SESSION_NAME = "music_bot"

# 鬲賳馗蹖賲 賱丕诏
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 爻丕禺鬲 讴賱丕蹖賳鬲
app = Client(SESSION_NAME, api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
pytgcalls = PyTgCalls(app)

# 賲鬲睾蹖乇賴丕蹖 爻乇丕爻乇蹖
current_song = {}
queue = {}
user_settings = {}

class MusicBot:
    def __init__(self):
        self.ytdl_opts = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'extractaudio': True,
            'audioformat': 'mp3',
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
        }
        
        # 爻丕禺鬲 倬賵卮賴 丿丕賳賱賵丿
        os.makedirs('downloads', exist_ok=True)

    async def search_youtube(self, query: str):
        """噩爻鬲噩賵 丿乇 蹖賵鬲蹖賵亘"""
        try:
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                search_results = ydl.extract_info(
                    f"ytsearch3:{query}", 
                    download=False
                )
                return search_results.get('entries', [])
        except Exception as e:
            logger.error(f"禺胤丕 丿乇 噩爻鬲噩賵: {e}")
            return []

    async def download_audio(self, url: str):
        """丿丕賳賱賵丿 賮丕蹖賱 氐賵鬲蹖"""
        try:
            with yt_dlp.YoutubeDL(self.ytdl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                title = info.get('title', 'Unknown')
                
                # 鬲睾蹖蹖乇 倬爻賵賳丿 亘賴 mp3
                if not filename.endswith('.mp3'):
                    base_name = os.path.splitext(filename)[0]
                    mp3_filename = f"{base_name}.mp3"
                    if os.path.exists(filename):
                        os.rename(filename, mp3_filename)
                        filename = mp3_filename
                
                return filename, title
        except Exception as e:
            logger.error(f"禺胤丕 丿乇 丿丕賳賱賵丿: {e}")
            return None, str(e)

music_bot = MusicBot()

# 丿爻鬲賵乇丕鬲 乇亘丕鬲
@app.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    """丿爻鬲賵乇 卮乇賵毓"""
    welcome_text = """
馃幍 爻賱丕賲! 亘賴 乇亘丕鬲 賲賵夭蹖讴 賵蹖爻鈥屭┴з� 禺賵卮 丕賵賲丿蹖!

馃搵 丿爻鬲賵乇丕鬲:
/start - 卮乇賵毓 乇亘丕鬲
/play [丌賴賳诏] - 倬禺卮 賲賵夭蹖讴
/pause - 鬲賵賯賮 賲賵夭蹖讴  
/resume - 丕丿丕賲賴 倬禺卮
/stop - 鬲賵賯賮 讴丕賲賱
/skip - 乇丿 讴乇丿賳 丌賴賳诏
/queue - 氐賮 倬禺卮
/current - 丌賴賳诏 賮毓賱蹖

馃帶 亘乇丕蹖 卮乇賵毓貙 乇亘丕鬲 乇賵 亘賴 诏乇賵賴 丕囟丕賮賴 讴賳 賵 丕丿賲蹖賳 讴賳!
    """
    await message.reply_text(welcome_text)

@app.on_message(filters.command("play"))
async def play_command(client: Client, message: Message):
    """丿爻鬲賵乇 倬禺卮 賲賵夭蹖讴"""
    chat_id = message.chat.id
    
    if len(message.command) < 2:
        await message.reply_text("鉂� 賳丕賲 丌賴賳诏 蹖丕 賱蹖賳讴 乇賵 賵丕乇丿 讴賳!\n\n賲孬丕賱: `/play 賲丨爻賳 蹖诏丕賳賴 毓丕卮賯丕賳賴`")
        return
    
    query = " ".join(message.command[1:])
    processing_msg = await message.reply_text("馃攳 丿乇 丨丕賱 噩爻鬲噩賵...")
    
    try:
        # 噩爻鬲噩賵
        if 'youtube.com' in query or 'youtu.be' in query:
            url = query
            results = [{'webpage_url': url, 'title': '賱蹖賳讴 賲爻鬲賯蹖賲'}]
        else:
            results = await music_bot.search_youtube(query)
            
        if not results:
            await processing_msg.edit_text("鉂� 賴蹖趩 賳鬲蹖噩賴鈥屫й� 倬蹖丿丕 賳卮丿!")
            return
        
        # 賳賲丕蹖卮 賳鬲丕蹖噩
        if len(results) == 1 or 'youtube.com' in query:
            # 倬禺卮 賲爻鬲賯蹖賲
            url = results[0]['webpage_url']
            await play_song(chat_id, url, processing_msg)
        else:
            # 賳賲丕蹖卮 诏夭蹖賳賴鈥屬囏�
            keyboard = []
            for i, result in enumerate(results):
                title = result.get('title', '賳丕賲毓賱賵賲')[:40]
                duration = result.get('duration', 0)
                duration_str = f"{duration//60}:{duration%60:02d}" if duration else "賳丕賲毓賱賵賲"
                
                keyboard.append([InlineKeyboardButton(
                    f"馃幍 {title} ({duration_str})",
                    callback_data=f"play:{result['webpage_url']}"
                )])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await processing_msg.edit_text(
                f"馃幍 賳鬲丕蹖噩 噩爻鬲噩賵 亘乇丕蹖: **{query}**\n\n蹖讴蹖 乇賵 丕賳鬲禺丕亘 讴賳:",
                reply_markup=reply_markup
            )
            
    except Exception as e:
        logger.error(f"禺胤丕 丿乇 倬禺卮: {e}")
        await processing_msg.edit_text(f"鉂� 禺胤丕: {str(e)}")

async def play_song(chat_id: int, url: str, message: Message):
    """倬禺卮 丌賴賳诏 丿乇 賵蹖爻鈥屭┴з�"""
    try:
        await message.edit_text("馃摜 丿乇 丨丕賱 丿丕賳賱賵丿...")
        
        # 丿丕賳賱賵丿 丌賴賳诏
        file_path, title = await music_bot.download_audio(url)
        if not file_path:
            await message.edit_text(f"鉂� 禺胤丕 丿乇 丿丕賳賱賵丿: {title}")
            return
        
        await message.edit_text("馃幍 丿乇 丨丕賱 倬禺卮...")
        
        # 倬禺卮 丿乇 賵蹖爻鈥屭┴з�
        try:
            await pytgcalls.join_group_call(
                chat_id,
                AudioPiped(file_path),
                stream_type=StreamType().local_stream,
            )
            
            # 匕禺蹖乇賴 丕胤賱丕毓丕鬲 丌賴賳诏 賮毓賱蹖
            current_song[chat_id] = {
                'title': title,
                'file_path': file_path,
                'url': url
            }
            
            await message.edit_text(f"馃幍 **丿乇 丨丕賱 倬禺卮:**\n{title}")
            
        except NoActiveGroupCall:
            await message.edit_text("鉂� 賱胤賮丕賸 丕亘鬲丿丕 賵蹖爻鈥屭┴з� 诏乇賵賴 乇賵 卮乇賵毓 讴賳!")
        except Exception as e:
            await message.edit_text(f"鉂� 禺胤丕 丿乇 倬禺卮: {str(e)}")
            
    except Exception as e:
        logger.error(f"禺胤丕 丿乇 倬禺卮 丌賴賳诏: {e}")
        await message.edit_text(f"鉂� 禺胤丕: {str(e)}")

@app.on_message(filters.command("pause"))
async def pause_command(client: Client, message: Message):
    """鬲賵賯賮 賲賵夭蹖讴"""
    chat_id = message.chat.id
    try:
        await pytgcalls.pause_stream(chat_id)
        await message.reply_text("鈴� 賲賵夭蹖讴 賲鬲賵賯賮 卮丿!")
    except Exception as e:
        await message.reply_text(f"鉂� 禺胤丕: {str(e)}")

@app.on_message(filters.command("resume"))
async def resume_command(client: Client, message: Message):
    """丕丿丕賲賴 倬禺卮"""
    chat_id = message.chat.id
    try:
        await pytgcalls.resume_stream(chat_id)
        await message.reply_text("鈻讹笍 倬禺卮 丕丿丕賲賴 蹖丕賮鬲!")
    except Exception as e:
        await message.reply_text(f"鉂� 禺胤丕: {str(e)}")

@app.on_message(filters.command("stop"))
async def stop_command(client: Client, message: Message):
    """鬲賵賯賮 讴丕賲賱"""
    chat_id = message.chat.id
    try:
        await pytgcalls.leave_group_call(chat_id)
        
        # 倬丕讴 讴乇丿賳 賮丕蹖賱
        if chat_id in current_song:
            file_path = current_song[chat_id].get('file_path')
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
            del current_song[chat_id]
        
        await message.reply_text("鈴� 賲賵夭蹖讴 賲鬲賵賯賮 卮丿 賵 丕夭 賵蹖爻鈥屭┴з� 禺丕乇噩 卮丿賲!")
    except Exception as e:
        await message.reply_text(f"鉂� 禺胤丕: {str(e)}")

@app.on_message(filters.command("current"))
async def current_command(client: Client, message: Message):
    """賳賲丕蹖卮 丌賴賳诏 賮毓賱蹖"""
    chat_id = message.chat.id
    
    if chat_id not in current_song:
        await message.reply_text("鉂� 賴蹖趩 丌賴賳诏蹖 丿乇 丨丕賱 倬禺卮 賳蹖爻鬲!")
        return
    
    song_info = current_song[chat_id]
    await message.reply_text(f"馃幍 **丌賴賳诏 賮毓賱蹖:**\n{song_info['title']}")

@app.on_callback_query(filters.regex("^play:"))
async def callback_play(client: Client, callback_query: CallbackQuery):
    """倬乇丿丕夭卮 讴丕賱鈥屫ㄚ� 倬禺卮"""
    url = callback_query.data.replace("play:", "")
    chat_id = callback_query.message.chat.id
    
    await callback_query.answer("丿乇 丨丕賱 倬禺卮...")
    await play_song(chat_id, url, callback_query.message)

# 賲丿蹖乇蹖鬲 丕鬲賲丕賲 丌賴賳诏
@pytgcalls.on_stream_end()
async def on_stream_end(client: PyTgCalls, update):
    """賵賯鬲蹖 丌賴賳诏 鬲賲賵賲 卮丿"""
    chat_id = update.chat_id
    
    # 倬丕讴 讴乇丿賳 賮丕蹖賱
    if chat_id in current_song:
        file_path = current_song[chat_id].get('file_path')
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        del current_song[chat_id]
    
    # 丕诏乇 氐賮 倬禺卮 丿丕乇賴貙 丌賴賳诏 亘毓丿蹖 乇賵 倬禺卮 讴賳
    # (丕蹖賳 賯爻賲鬲 乇賵 賲蹖鈥屫堎嗃� 鬲賵爻毓賴 亘丿蹖)

async def main():
    """鬲丕亘毓 丕氐賱蹖"""
    print("馃 乇亘丕鬲 賲賵夭蹖讴 賵蹖爻鈥屭┴з� 卮乇賵毓 卮丿...")
    
    # 卮乇賵毓 pytgcalls
    await pytgcalls.start()
    
    # 卮乇賵毓 乇亘丕鬲
    await app.start()
    
    print("鉁� 乇亘丕鬲 丌賲丕丿賴 丕爻鬲!")
    
    # 賳诏賴鈥屫ж簇� 乇亘丕鬲
    await asyncio.sleep(float("inf"))

if __name__ == "__main__":
    asyncio.run(main())
