import logging
import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
import yt_dlp
import requests
from io import BytesIO

# Bot Token - جایگزین کنید با توکن جدید
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

# تنظیمات لاگینگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class MusicBot:
    def __init__(self):
        self.ytdl_opts = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'extractaudio': True,
            'audioformat': 'mp3',
            'quiet': True,
            'no_warnings': True,
        }

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور شروع"""
        welcome_text = """
🎵 سلام! به ربات موزیک خوش اومدی!

دستورات قابل استفاده:
/start - شروع ربات
/help - راهنما
/search - جستجو موزیک

برای پخش موزیک، اسم آهنگ یا لینک یوتیوب بفرست!
        """
        await update.message.reply_text(welcome_text)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور راهنما"""
        help_text = """
📋 راهنمای استفاده:

🔍 برای جستجو:
- اسم آهنگ بفرست
- لینک یوتیوب بفرست
- /search [اسم آهنگ]

⚠️ نکات مهم:
- فقط از لینک‌های قانونی استفاده کن
- حجم فایل باید کمتر از ۵۰ مگابایت باشه
- صبر کن تا آهنگ دانلود بشه

🎵 ربات از یوتیوب موزیک و منابع آزاد استفاده می‌کنه
        """
        await update.message.reply_text(help_text)

    async def search_music(self, query):
        """جستجو موزیک در یوتیوب"""
        try:
            with yt_dlp.YoutubeDL(self.ytdl_opts) as ydl:
                search_query = f"ytsearch5:{query}"
                search_results = ydl.extract_info(search_query, download=False)
                
                if search_results and 'entries' in search_results:
                    return search_results['entries']
                return None
        except Exception as e:
            logger.error(f"خطا در جستجو: {e}")
            return None

    async def download_audio(self, url):
        """دانلود فایل صوتی"""
        try:
            with yt_dlp.YoutubeDL(self.ytdl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # بررسی حجم فایل
                if info.get('filesize') and info['filesize'] > 50 * 1024 * 1024:
                    return None, "فایل خیلی بزرگه! (بیشتر از ۵۰ مگابایت)"
                
                # دانلود فایل
                download_opts = self.ytdl_opts.copy()
                download_opts['outtmpl'] = 'downloads/%(title)s.%(ext)s'
                
                with yt_dlp.YoutubeDL(download_opts) as dl:
                    dl.download([url])
                
                # پیدا کردن فایل دانلود شده
                for file in os.listdir('downloads'):
                    if file.endswith(('.mp3', '.m4a', '.webm')):
                        return f"downloads/{file}", info.get('title', 'Unknown')
                        
                return None, "فایل پیدا نشد"
        except Exception as e:
            logger.error(f"خطا در دانلود: {e}")
            return None, str(e)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش پیام‌های کاربر"""
        message = update.message.text
        chat_id = update.message.chat_id
        
        # نمایش پیام در حال پردازش
        processing_msg = await update.message.reply_text("🔍 در حال جستجو...")
        
        try:
            # بررسی اینکه آیا لینک یوتیوب هست یا نه
            if 'youtube.com' in message or 'youtu.be' in message:
                url = message
            else:
                # جستجو در یوتیوب
                results = await self.search_music(message)
                if not results:
                    await processing_msg.edit_text("❌ هیچ نتیجه‌ای پیدا نشد!")
                    return
                
                # نمایش نتایج جستجو
                keyboard = []
                for i, result in enumerate(results[:3]):  # فقط ۳ نتیجه اول
                    title = result.get('title', 'Unknown')[:50]
                    duration = result.get('duration', 0)
                    duration_str = f"{duration//60}:{duration%60:02d}" if duration else "نامعلوم"
                    
                    keyboard.append([InlineKeyboardButton(
                        f"🎵 {title} ({duration_str})",
                        callback_data=f"download:{result['webpage_url']}"
                    )])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                await processing_msg.edit_text(
                    f"🎵 نتایج جستجو برای: {message}",
                    reply_markup=reply_markup
                )
                return
            
            # دانلود مستقیم
            await processing_msg.edit_text("📥 در حال دانلود...")
            file_path, title = await self.download_audio(url)
            
            if file_path:
                await processing_msg.edit_text("📤 در حال ارسال...")
                with open(file_path, 'rb') as audio_file:
                    await context.bot.send_audio(
                        chat_id=chat_id,
                        audio=audio_file,
                        title=title,
                        caption=f"🎵 {title}"
                    )
                
                # حذف فایل بعد از ارسال
                os.remove(file_path)
                await processing_msg.delete()
            else:
                await processing_msg.edit_text(f"❌ خطا در دانلود: {title}")
                
        except Exception as e:
            logger.error(f"خطا در پردازش پیام: {e}")
            await processing_msg.edit_text("❌ خطا در پردازش درخواست!")

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش کال‌بک‌های دکمه‌ها"""
        query = update.callback_query
        await query.answer()
        
        if query.data.startswith('download:'):
            url = query.data.replace('download:', '')
            
            await query.edit_message_text("📥 در حال دانلود...")
            
            file_path, title = await self.download_audio(url)
            
            if file_path:
                await query.edit_message_text("📤 در حال ارسال...")
                with open(file_path, 'rb') as audio_file:
                    await context.bot.send_audio(
                        chat_id=query.message.chat_id,
                        audio=audio_file,
                        title=title,
                        caption=f"🎵 {title}"
                    )
                
                os.remove(file_path)
                await query.delete_message()
            else:
                await query.edit_message_text(f"❌ خطا در دانلود: {title}")

def main():
    """تابع اصلی"""
    # ساخت پوشه دانلود
    os.makedirs('downloads', exist_ok=True)
    
    # ساخت ربات
    bot = MusicBot()
    application = Application.builder().token(BOT_TOKEN).build()
    
    # اضافه کردن هندلرها
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("help", bot.help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))
    application.add_handler(CallbackQueryHandler(bot.handle_callback))
    
    # شروع ربات
    print("🤖 ربات موزیک شروع شد...")
    application.run_polling()

if __name__ == '__main__':
    main()            'noplaylist': True,
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
