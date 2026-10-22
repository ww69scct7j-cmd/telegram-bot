import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
AUDD_API_TOKEN = os.getenv("AUDD_API_TOKEN")

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    file_obj = None

    # 1. استقبال أي نوع فيديو أو صوتي أو مستند مهما كانت المدة أو المفهوم
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
        await message.reply_text("الرجاء إرسال مقطع صوتي أو فيديو أو ملف وسائط لفحصه.")
        return

    await message.reply_text("🔍 جاري تحليل البصمة الصوتية، العزف، اللحن، والكلمات (للأغاني المصرية والمقاطع ذات المشاهدات القليلة أو القنوات الخاصة)...")

    file_path = "temp_media_file"
    await file_obj.download_to_drive(file_path)

    try:
        # 2. إرسال الملف كاملاً لتجاوز التسريع والحقوق والتعرف على النغمة والكلمات
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
            release_date = song.get('release_date', '')
            song_link = song.get('song_link', '')
            
            # 3. التحقق من سنة الإصدار (من 2007 إلى 2026)
            year = None
            if release_date:
                try:
                    year = int(release_date.split('-')[0])
                except ValueError:
                    year = None

            if year and not (2007 <= year <= 2026):
                await message.reply_text(f"⚠️ تم التعرف على الأغنية ({title} - {artist}) لكن سنة إصدارها ({year}) خارج نطاق السنوات المطلوبة (2007 - 2026).")
                return

            lyrics_data = song.get('lyrics', {})
            lyrics_text = lyrics_data.get('lyrics', '')

            reply_text = (
                f"🇪🇬 **تم التعرف على الأغنية بنجاح!**\n\n"
                f"• **اسم الأغنية:** {title}\n"
                f"• **المطرب / الفنان:** {artist}\n"
                f"• **الألبوم:** {album}\n"
                f"• **سنة الإصدار:** {release_date if release_date else 'ضمن النطاق المحدد (2007-2026)'}\n"
            )

            if song_link:
                reply_text += f"• **رابط الاستماع المباشر:** {song_link}\n"

            if lyrics_text:
                # عرض جزء أولي من الكلمات للتحقق
                lines = lyrics_text.strip().split('\n')[:4]
                short_lyrics = '\n'.join(lines)
                reply_text += f"\n📝 **جزء من كلمات الأغنية:**\n{short_lyrics}\n\n(يمكنك البحث عن الكلمات الكاملة عبر جوجل)"

            await message.reply_text(reply_text)
        else:
            await message.reply_text("❌ لم يتم العثور على مطابقة مؤكدة للبصمة الموسيقية واللحن بدون تخمين.")

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
