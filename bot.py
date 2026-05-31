import logging
import pytz
import asyncio
from datetime import datetime, time
from telegram import Update, ChatPermissions
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, Defaults

# 1. الإعدادات الأساسية
MY_TZ = pytz.timezone('Africa/Cairo')
GROUP_IDS = [-1003738377239, -1003121062302, -1003952529188, -1003893444912, -1003953376550, -1003320530825]
TOKEN = "8820852443:AAFjo-cKYBkFde057jP_d3af_FjurZChji8"

# مانع التكرار العالمي - بيضمن إن مفيش أمرين يتنفذوا في نفس اللحظة
EXECUTION_LOCK = asyncio.Lock()

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- فحص الأدمن ---
async def is_admin(update: Update):
    try:
        user = await update.effective_chat.get_member(update.effective_user.id)
        return user.status in ['administrator', 'creator']
    except: return False

# --- وظيفة التنفيذ القهرية (تطبيق الصلاحيات) ---
async def set_status(bot, chat_id, action):
    async with EXECUTION_LOCK: # تفعيل مانع التكرار (قفل برمجي)
        is_open = (action == "open")
        if is_open:
            perms = ChatPermissions(
                can_send_messages=True, can_send_photos=True, can_send_videos=True,
                can_send_video_notes=True, can_send_documents=True,
                can_send_other_messages=False, can_add_web_page_previews=False,
                can_send_polls=False, can_send_voice_notes=False, can_send_audios=False
            )
            msg = "🫡 تم فتح الجروب حالاً"
        else:
            perms = ChatPermissions(can_send_messages=False)
            msg = "🫡 تم إغلاق الجروب تماماً"
            
        try:
            await bot.set_chat_permissions(chat_id=chat_id, permissions=perms)
            await bot.send_message(chat_id=chat_id, text=msg)
            await asyncio.sleep(1) # تهدئة السيرفر لمنع الـ Flood
            return True
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            return False

# --- الأوامر اليدوية ---
async def open_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await is_admin(update):
        await set_status(context.bot, update.effective_chat.id, "open")

async def close_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await is_admin(update):
        await set_status(context.bot, update.effective_chat.id, "close")

# --- محرك المواعيد الذكي ---
async def job_trigger(context: ContextTypes.DEFAULT_TYPE):
    chat_id, action, hr, mn = context.job.data
    # تم إزالة قيود الأيام والإجازات ليعمل البوت يومياً بشكل كامل
    await set_status(context.bot, chat_id, action)

def main():
    # drop_pending_updates=True بتنظف أي رسايل قديمة وقت ما البوت كان فاصل
    app = ApplicationBuilder().token(TOKEN).defaults(Defaults(tzinfo=MY_TZ)).build()
    
    app.add_handler(CommandHandler("open_now", open_now))
    app.add_handler(CommandHandler("close_now", close_now))

    # الجدول الزمني الصارم الجديد (يومياً)
    schedule = [
        ((4, 0), "open"), ((4, 30), "close"),      # 4:00 AM - 4:30 AM
        ((5, 0), "open"), ((5, 30), "close"),      # 5:00 AM - 5:30 AM
        ((8, 45), "open"), ((9, 0), "close"),      # 8:45 AM - 9:00 AM
        ((9, 45), "open"), ((10, 0), "close"),     # 9:45 AM - 10:00 AM
        ((12, 45), "open"), ((13, 0), "close"),    # 12:45 PM - 1:00 PM (الظهر)
        ((19, 45), "open"), ((20, 0), "close"),    # 7:45 PM - 8:00 PM (المغرب)
        ((20, 45), "open"), ((21, 0), "close")     # 8:45 PM - 9:00 PM
    ]

    for gid in GROUP_IDS:
        for (hr, mn), act in schedule:
            app.job_queue.run_daily(
                job_trigger, 
                time=time(hour=hr, minute=mn, tzinfo=MY_TZ), 
                data=(gid, act, hr, mn)
            )

    logger.info("🚀 System Secure | Anti-Spam Active | Cairo Time")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
