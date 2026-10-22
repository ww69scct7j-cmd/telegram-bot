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
    file_name = ""

    if message.audio:
        file_obj = await message.audio.get_file()
        file_name = message.audio.file_name or ""
    elif message.voice:
        file_obj = await message.voice.get_file()
    elif message.video:
        file_obj = await message.video.get_file()
        file_name = message.video.file_name or ""
    elif message.video_note:
        file_obj = await message.video_note.get_file()
    elif message.document:
        file_obj = await message.document.get_file()
        file_name = message.document.file_name or ""
    else:
        await message.reply_text("أرسل لي أي مقطع صوتي أو فيديو وسأبحث لك عنه فوراً.")
        return

    await message.reply_text("🔍 جاري فحص البصمة والبحث الشامل لضمان جلب النتيجة...")

    file_path = "temp_media_file"
    await file_obj.download_to_drive(file_path)

    try:
        matched = False
        with open(file_path, "rb") as f:
            data = {'api_token': AUDD_API_TOKEN, 'return': 'spotify,apple_music,lyrics'}
            files = {'file': f}
            response = requests.post('https://api.audd.io/', data=data, files=files)
            result = response.json()

        if result.get('status') == 'success' and result.get('result'):
            song = result['result']
            title = song.get('title', '')
            artist = song.get('artist', '')
            song_link = song.get('song_link', '')

            if title or artist:
                reply_text = (
                    f"🎵 **تم العثور على الأغنية بنجاح:**\n\n"
                    f"• **اسم الأغنية:** {title}\n"
                    f"• **الفنان:** {artist}\n"
                )
                if song_link:
                    reply_text += f"• **الرابط:** {song_link}\n"
                await message.reply_text(reply_text)
                matched = True

        # إذا لم تجدها خدمة AudD (لأن الأغنية نادرة أو مشاهداتها قليلة)، يبحث مباشرة باسم الملف في يوتيوب
        if not matched:
            clean_name = file_name.replace('.m4a', '').replace('.mp3', '').replace('_', ' ').strip()
            
            if not clean_name or len(clean_name) < 2:
                clean_name = "مقطع صوتي بحث يوتيوب"

            search_query = urllib.parse.quote(clean_name)
            yt_url = f"https://www.youtube.com/results?search_query={search_query}"

            reply_text = (
                f"🔎 **الأغنية غير مسجلة في منصات البصمة (مثل سبوتيفاي)، ولكن هذا رابط البحث المباشر عنها:**\n\n"
                f"• **اسم الملف:** {clean_name}\n"
                f"• **رابط يوتيوب المباشر:** {yt_url}"
            )
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
