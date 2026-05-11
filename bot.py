import logging
import pytz
import asyncio
from datetime import datetime, time
from telegram import Update, ChatPermissions
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, Defaults

# 1. الإعدادات الأساسية
MY_TZ = pytz.timezone('Africa/Cairo')
GROUP_IDS = [-1003738377239, -1003121062302, -1003952529188, -1003893444912, -1003953376550]
TOKEN = "8685861366:AAGmGYGu92tHgKb13QEsaScpMw8_WNJXqjA"

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
    now_eg = datetime.now(MY_TZ)
    weekday = now_eg.weekday() # 1=الثلاثاء، 4=الجمعة

    # منطق الإجازات (أمن وطني)
    if weekday == 4: # الجمعة: إجازة كاملة
        return
    
    if weekday == 1: # الثلاثاء: أول فترتين فقط
        allowed_times = [(4,30), (5,0), (7,30), (8,0)]
        if (hr, mn) not in allowed_times:
            return

    await set_status(context.bot, chat_id, action)

def main():
    # drop_pending_updates=True بتنظف أي رسايل قديمة وقت ما البوت كان فاصل
    app = ApplicationBuilder().token(TOKEN).defaults(Defaults(tzinfo=MY_TZ)).build()
    
    app.add_handler(CommandHandler("open_now", open_now))
    app.add_handler(CommandHandler("close_now", close_now))

    # الجدول الزمني الصارم
    schedule = [
        ((4,30),"open"), ((5,0),"close"), 
        ((7,30),"open"), ((8,0),"close"), 
        ((14,30),"open"), ((15,0),"close"), 
        ((20,0),"open"), ((21,0),"close")
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

