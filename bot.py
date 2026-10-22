import os
import urllib.parse
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
AUDD_API_TOKEN = os.getenv("AUDD_API_TOKEN")

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    file_obj = None
    original_name = ""

    if message.audio:
        file_obj = await message.audio.get_file()
        original_name = message.audio.file_name or ""
    elif message.voice:
        file_obj = await message.voice.get_file()
    elif message.video:
        file_obj = await message.video.get_file()
        original_name = message.video.file_name or ""
    elif message.video_note:
        file_obj = await message.video_note.get_file()
    elif message.document:
        file_obj = await message.document.get_file()
        original_name = message.document.file_name or ""
    else:
        await message.reply_text("أرسل لي أي مقطع صوتي أو فيديو وسأبحث لك عنه فوراً.")
        return

    await message.reply_text("🔍 جاري تحليل البصمة وتحديد الأغنية بدقة...")

    file_path = "temp_media_file"
    await file_obj.download_to_drive(file_path)

    try:
        song_title = ""
        song_artist = ""
        song_link = ""
        matched = False

        # 1. محاولة التعرف عبر البصمة (AudD)
        with open(file_path, "rb") as f:
            data = {'api_token': AUDD_API_TOKEN, 'return': 'spotify,apple_music,lyrics'}
            files = {'file': f}
            response = requests.post('https://api.audd.io/', data=data, files=files)
            result = response.json()

        if result.get('status') == 'success' and result.get('result'):
            song = result['result']
            song_title = song.get('title', '')
            song_artist = song.get('artist', '')
            song_link = song.get('song_link', '')
            if song_title:
                matched = True

        # 2. إذا لم يتعرف عليها AudD، نستخرج اسم نظيف من الملف المرفوع
        if not matched:
            clean_name = original_name
            for ext in ['.m4a', '.mp3', '.mp4', '.wav', '.mov', '.ogg']:
                clean_name = clean_name.replace(ext, '')
            clean_name = clean_name.replace('_', ' ').replace('-', ' ').strip()
            
            if clean_name and len(clean_name) > 1:
                song_title = clean_name
                song_artist = "مقطع محلي / يوتيوب"
            else:
                song_title = "مقطع صوتي مرسل"
                song_artist = "غير معروف"

        # تجهيز رابط يوتيوب مباشر ودقيق للبحث عن الأغنية بالاسم الصحيح
        search_query = urllib.parse.quote(f"{song_title} {song_artist if song_artist != 'غير معروف' else ''}")
        direct_yt_link = f"https://www.youtube.com/results?search_query={search_query}"

        reply_text = (
            f"🎵 **نتيجة التعرف على الأغنية:**\n\n"
            f"• **اسم الأغنية:** {song_title}\n"
            f"• **الفنان / المذيع:** {song_artist}\n"
        )

        if song_link:
            reply_text += f"• **رابط الاستماع الرسمي:** {song_link}\n"
        else:
            reply_text += f"• **رابط البحث المباشر في يوتيوب:** {direct_yt_link}\n"

        await message.reply_text(reply_text)

    except Exception as e:
        await message.reply_text(f"حدث خطأ أثناء المعالجة: {str(e)}")

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.AUDIO | filters.VOICE | filters.VIDEO | filters.VIDEO_NOTE | filters.Document.ALL, handle_media))
    app.run_polling()

if __name__ == '__main__':
    main()
