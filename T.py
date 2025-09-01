import asyncio
import logging
import os
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
try:
    from pytgcalls import PyTgCalls
    from pytgcalls.types.input_stream import AudioPiped
    from pytgcalls.exceptions import NoActiveGroupCall
    PYTGCALLS_AVAILABLE = True
except ImportError:
    print("⚠️ py-tgcalls نصب نیست. ربات در حالت ساده اجرا می‌شود.")
    PYTGCALLS_AVAILABLE = False
    PyTgCalls = None
    AudioPiped = None
    NoActiveGroupCall = Exception
import yt_dlp
import json

# تنظیمات API
API_ID = 27003875  # عدد باید باشه (بدون گیومه)
API_HASH = "8c8575dfd6a7f5ecaa7804c6214ccac5"
BOT_TOKEN = "8102242216:AAE7Vu-Batpl80NLX65HQY-rLHTMED23wyE"
SESSION_NAME = "music_bot"

# تنظیم لاگ
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ساخت کلاینت
app = Client(SESSION_NAME, api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# py-tgcalls فقط اگر موجود باشه
if PYTGCALLS_AVAILABLE:
    pytgcalls = PyTgCalls(app)
else:
    pytgcalls = None

# متغیرهای سراسری
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
        
        # ساخت پوشه دانلود
        os.makedirs('downloads', exist_ok=True)

    async def search_youtube(self, query: str):
        """جستجو در یوتیوب"""
        try:
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                search_results = ydl.extract_info(
                    f"ytsearch3:{query}", 
                    download=False
                )
                return search_results.get('entries', [])
        except Exception as e:
            logger.error(f"خطا در جستجو: {e}")
            return []

    async def download_audio(self, url: str):
        """دانلود فایل صوتی"""
        try:
            with yt_dlp.YoutubeDL(self.ytdl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                title = info.get('title', 'Unknown')
                
                # تغییر پسوند به mp3
                if not filename.endswith('.mp3'):
                    base_name = os.path.splitext(filename)[0]
                    mp3_filename = f"{base_name}.mp3"
                    if os.path.exists(filename):
                        os.rename(filename, mp3_filename)
                        filename = mp3_filename
                
                return filename, title
        except Exception as e:
            logger.error(f"خطا در دانلود: {e}")
            return None, str(e)

music_bot = MusicBot()

# دستورات ربات
@app.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    """دستور شروع"""
    welcome_text = """
🎵 سلام! به ربات موزیک ویس‌کال خوش اومدی!

📋 دستورات:
/start - شروع ربات
/play [آهنگ] - پخش موزیک
/pause - توقف موزیک  
/resume - ادامه پخش
/stop - توقف کامل
/skip - رد کردن آهنگ
/queue - صف پخش
/current - آهنگ فعلی

🎧 برای شروع، ربات رو به گروه اضافه کن و ادمین کن!
    """
    await message.reply_text(welcome_text)

@app.on_message(filters.command("play"))
async def play_command(client: Client, message: Message):
    """دستور پخش موزیک"""
    chat_id = message.chat.id
    
    if len(message.command) < 2:
        await message.reply_text("❌ نام آهنگ یا لینک رو وارد کن!\n\nمثال: `/play محسن یگانه عاشقانه`")
        return
    
    query = " ".join(message.command[1:])
    processing_msg = await message.reply_text("🔍 در حال جستجو...")
    
    try:
        # جستجو
        if 'youtube.com' in query or 'youtu.be' in query:
            url = query
            results = [{'webpage_url': url, 'title': 'لینک مستقیم'}]
        else:
            results = await music_bot.search_youtube(query)
            
        if not results:
            await processing_msg.edit_text("❌ هیچ نتیجه‌ای پیدا نشد!")
            return
        
        # نمایش نتایج
        if len(results) == 1 or 'youtube.com' in query:
            # پخش مستقیم
            url = results[0]['webpage_url']
            await play_song(chat_id, url, processing_msg)
        else:
            # نمایش گزینه‌ها
            keyboard = []
            for i, result in enumerate(results):
                title = result.get('title', 'نامعلوم')[:40]
                duration = result.get('duration', 0)
                duration_str = f"{duration//60}:{duration%60:02d}" if duration else "نامعلوم"
                
                keyboard.append([InlineKeyboardButton(
                    f"🎵 {title} ({duration_str})",
                    callback_data=f"play:{result['webpage_url']}"
                )])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await processing_msg.edit_text(
                f"🎵 نتایج جستجو برای: **{query}**\n\nیکی رو انتخاب کن:",
                reply_markup=reply_markup
            )
            
    except Exception as e:
        logger.error(f"خطا در پخش: {e}")
        await processing_msg.edit_text(f"❌ خطا: {str(e)}")

async def play_song(chat_id: int, url: str, message: Message):
    """پخش آهنگ در ویس‌کال"""
    try:
        await message.edit_text("📥 در حال دانلود...")
        
        # دانلود آهنگ
        file_path, title = await music_bot.download_audio(url)
        if not file_path:
            await message.edit_text(f"❌ خطا در دانلود: {title}")
            return
        
        if not PYTGCALLS_AVAILABLE:
            # ارسال فایل صوتی
            await message.edit_text("🎵 ارسال فایل صوتی...")
            with open(file_path, 'rb') as audio_file:
                await app.send_audio(
                    chat_id=chat_id,
                    audio=audio_file,
                    caption=f"🎵 {title}"
                )
            os.remove(file_path)
            await message.edit_text(f"✅ **ارسال شد:**\n{title}")
            return
        
        await message.edit_text("🎵 در حال پخش...")
        
        # پخش در ویس‌کال
        try:
            await pytgcalls.join_group_call(
                chat_id,
                AudioPiped(file_path),
            )
            
            # ذخیره اطلاعات آهنگ فعلی
            current_song[chat_id] = {
                'title': title,
                'file_path': file_path,
                'url': url
            }
            
            await message.edit_text(f"🎵 **در حال پخش:**\n{title}")
            
        except NoActiveGroupCall:
            await message.edit_text("❌ لطفاً ابتدا ویس‌کال گروه رو شروع کن!")
        except Exception as e:
            await message.edit_text(f"❌ خطا در پخش: {str(e)}")
            
    except Exception as e:
        logger.error(f"خطا در پخش آهنگ: {e}")
        await message.edit_text(f"❌ خطا: {str(e)}")

@app.on_message(filters.command("pause"))
async def pause_command(client: Client, message: Message):
    """توقف موزیک"""
    chat_id = message.chat.id
    try:
        await pytgcalls.pause_stream(chat_id)
        await message.reply_text("⏸ موزیک متوقف شد!")
    except Exception as e:
        await message.reply_text(f"❌ خطا: {str(e)}")

@app.on_message(filters.command("resume"))
async def resume_command(client: Client, message: Message):
    """ادامه پخش"""
    chat_id = message.chat.id
    try:
        await pytgcalls.resume_stream(chat_id)
        await message.reply_text("▶️ پخش ادامه یافت!")
    except Exception as e:
        await message.reply_text(f"❌ خطا: {str(e)}")

@app.on_message(filters.command("stop"))
async def stop_command(client: Client, message: Message):
    """توقف کامل"""
    chat_id = message.chat.id
    try:
        await pytgcalls.leave_group_call(chat_id)
        
        # پاک کردن فایل
        if chat_id in current_song:
            file_path = current_song[chat_id].get('file_path')
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
            del current_song[chat_id]
        
        await message.reply_text("⏹ موزیک متوقف شد و از ویس‌کال خارج شدم!")
    except Exception as e:
        await message.reply_text(f"❌ خطا: {str(e)}")

@app.on_message(filters.command("current"))
async def current_command(client: Client, message: Message):
    """نمایش آهنگ فعلی"""
    chat_id = message.chat.id
    
    if chat_id not in current_song:
        await message.reply_text("❌ هیچ آهنگی در حال پخش نیست!")
        return
    
    song_info = current_song[chat_id]
    await message.reply_text(f"🎵 **آهنگ فعلی:**\n{song_info['title']}")

@app.on_callback_query(filters.regex("^play:"))
async def callback_play(client: Client, callback_query: CallbackQuery):
    """پردازش کال‌بک پخش"""
    url = callback_query.data.replace("play:", "")
    chat_id = callback_query.message.chat.id
    
    await callback_query.answer("در حال پخش...")
    await play_song(chat_id, url, callback_query.message)

# مدیریت اتمام آهنگ
@pytgcalls.on_stream_end()
async def on_stream_end(client: PyTgCalls, update):
    """وقتی آهنگ تموم شد"""
    chat_id = update.chat_id
    
    # پاک کردن فایل
    if chat_id in current_song:
        file_path = current_song[chat_id].get('file_path')
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        del current_song[chat_id]
    
    # اگر صف پخش داره، آهنگ بعدی رو پخش کن
    # (این قسمت رو می‌تونی توسعه بدی)

async def main():
    """تابع اصلی"""
    print("🤖 ربات موزیک ویس‌کال شروع شد...")
    
    # شروع pytgcalls
    await pytgcalls.start()
    
    # شروع ربات
    await app.start()
    
    print("✅ ربات آماده است!")
    
    # نگه‌داشتن ربات
    await asyncio.sleep(float("inf"))

if __name__ == "__main__":
    asyncio.run(main())
