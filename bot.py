import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
AUDD_API_TOKEN = os.getenv("AUDD_API_TOKEN")

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    file_obj = None

    if message.audio:
        file_obj = await message.audio.get_file()
    elif message.voice:
        file_obj = await message.voice.get_file()
    elif message.video:
        file_obj = await message.video.get_file()
    elif message.video_note:
        file_obj = await message.video_note.get_file()
    elif message.document:
        file_obj = await message.document.get_file()
    else:
        await message.reply_text("أرسل لي أي مقطع صوتي أو فيديو وسأبحث لك عنه فوراً.")
        return

    await message.reply_text("🔍 جاري تحليل البصمة الموسيقية واللحن والعزف والكلمات بدقة عالية...")

    file_path = "temp_media_file"
    await file_obj.download_to_drive(file_path)

    try:
        with open(file_path, "rb") as f:
            data = {
                'api_token': AUDD_API_TOKEN,
                'return': 'spotify,apple_music,lyrics',
            }
            files = {
                'file': f,
            }
            response = requests.post('https://api.audd.io/', data=data, files=files)
            result = response.json()

        if result.get('status') == 'success' and result.get('result'):
            song = result['result']
            title = song.get('title', 'غير معروف')
            artist = song.get('artist', 'غير معروف')
            album = song.get('album', 'غير متوفر')
            release_date = song.get('release_date', 'غير متوفر')
            song_link = song.get('song_link', '')
            
            lyrics_data = song.get('lyrics', {})
            lyrics_text = lyrics_data.get('lyrics', '')

            reply_text = (
                f"🎵 **تم العثور على الأغنية بنجاح!**\n\n"
                f"• **اسم الأغنية:** {title}\n"
                f"• **المطرب / الفنان:** {artist}\n"
                f"• **الألبوم:** {album}\n"
                f"• **تاريخ الإصدار:** {release_date}\n"
            )

            if song_link:
                reply_text += f"• **رابط الاستماع:** {song_link}\n"

            if lyrics_text:
                lines = lyrics_text.strip().split('\n')[:6]
                reply_text += f"\n📝 **كلمات الأغنية:**\n" + '\n'.join(lines)

            await message.reply_text(reply_text)
        else:
            await message.reply_text("❌ لم يتم التعرف على المقطع. قد يكون الصوت غير واضح تماماً أو غير مسجل بقاعدة بيانات البحث.")

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
