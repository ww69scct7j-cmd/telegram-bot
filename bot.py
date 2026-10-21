ملف 

import os
import logging
import requests
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# إعداد السجلات
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
AUDD_API_TOKEN = os.environ.get("AUDD_API_TOKEN")

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    file_obj = None

    if message.video:
        file_obj = await message.video.get_file()
    elif message.audio:
        file_obj = await message.audio.get_file()
    elif message.document and ("video" in message.document.mime_type or "audio" in message.document.mime_type):
        file_obj = await message.document.get_file()
    
    if not file_obj:
        await message.reply_text("❌ أرسل فيديو أو ملف صوتي للبحث المطابق للمعايير الصارمة.")
        return

    status_msg = await message.reply_text("🔍 جاري استقبال الملف ومعالجة البصمة الصوتية وتجاوز المؤثرات والتسريع...")

    input_path = "input_media"
    output_audio = "output_audio.mp3"
    
    try:
        await file_obj.download_to_drive(input_path)
        
        # معالجة قوية عبر FFmpeg لتنقية الصوت، تعديل الترددات، وتجاهل الفلاتر الجانبية
        os.system(f"ffmpeg -y -i {input_path} -vn -acodec libmp3lame -ar 44100 -ab 192k -af 'highpass=f=200,lowpass=f=3000' {output_audio}")

        if not os.path.exists(output_audio) or os.path.getsize(output_audio) == 0:
            await status_msg.edit_text("❌ حدث خطأ في معالجة الملف الصوتي.")
            return

        await status_msg.edit_text("🎧 جاري البحث العميق في أرشيف (2007 - 2026) لمطابقة الكلمات، اللحن، والصوت...")

        with open(output_audio, "rb") as f:
            response = requests.post(
                "https://api.audd.io/",
                data={
                    'api_token': AUDD_API_TOKEN,
                    'return': 'spotify,apple_music,lyrics,timecode',
                },
                files={'file': f}
            )
        
        result = response.json()

        if result.get("status") == "success" and result.get("result"):
            res = result["result"]
            title = res.get("title", "غير معروف")
            artist = res.get("artist", "غير معروف")
            album = res.get("album", "غير متوفر")
            release_date = res.get("release_date", "غير متوفر")
            song_link = res.get("song_link", "")
            
            # فحص إضافي لضمان جودة وسنة الإصدار ضمن النطاق المطلوب (2007-2026)
            year_valid = True
            if release_date and len(release_date) >= 4:
                try:
                    year = int(release_date[:4])
                    if year < 2007 or year > 2026:
                        year_valid = False
                except:
                    pass

            if not year_valid:
                await status_msg.edit_text("❌ لم يتم العثور على مطابقة مؤكدة ضمن نطاق السنوات المطلوبة (2007-2026).")
                return

            reply_text = (
                f"🚨 **تم التحقق بنجاح (مطابقة صارمة):**\n\n"
                f"▫️ **اسم الأغنية:** {title}\n"
                f"▫️ **الفنان:** {artist}\n"
                f"▫️ **الألبوم:** {album}\n"
                f"▫️ **تاريخ الإصدار:** {release_date}\n"
                f"▫️ **رابط الاستماع:** {song_link}"
            )
            await status_msg.edit_text(reply_text)
        else:
            # سياسة الصفر تخمين: إرجاع غير موجود تماماً عند عدم التيقن
            await status_msg.edit_text("❌ لم يتم العثور على أي مطابقة دقيقة أو مؤكدة (صفر تخمين). المقطع غير موجود أو خارج معايير البحث الدقيقة.")

    except Exception as e:
        logger.error(f"Error: {e}")
        await status_msg.edit_text("❌ حدث خطأ تقني أثناء الاتصال.")
    finally:
        for p in [input_path, output_audio]:
            if os.path.exists(p):
                os.remove(p)

def main():
    if not TELEGRAM_TOKEN or not AUDD_API_TOKEN:
        logger.error("Tokens are missing!")
        return

    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(MessageHandler(filters.VIDEO | filters.AUDIO | filters.DOCUMENT, handle_media))
    
    logger.info("Bot is starting with strict parameters...")
    application.run_polling()

if __name__ == "__main__":
    main()
