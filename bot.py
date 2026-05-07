import logging
import pytz
from datetime import datetime, time
from telegram import Update, ChatPermissions
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, Defaults

# 1. الإعدادات
MY_TZ = pytz.timezone('Africa/Cairo')
GROUP_IDS = [-1003738377239]
TOKEN = "8685861366:AAGmGYGu92tHgKb13QEsaScpMw8_WNJXqjA"

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- وظيفة حماية الأدمن ---
async def is_admin(update: Update):
    try:
        user = await update.effective_chat.get_member(update.effective_user.id)
        return user.status in ['administrator', 'creator']
    except: return False

# --- وظيفة التنفيذ (بالصلاحيات التفصيلية) ---
async def set_status(bot, chat_id, action):
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
        return True
    except Exception as e:
        logger.error(f"Error: {e}")
        return False

# --- أوامر فورية (أدمن فقط) ---
async def open_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await is_admin(update):
        await set_status(context.bot, update.effective_chat.id, "open")

async def close_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await is_admin(update):
        await set_status(context.bot, update.effective_chat.id, "close")

# --- شغل المواعيد (منطق الإجازات المخصص) ---
async def job_trigger(context: ContextTypes.DEFAULT_TYPE):
    chat_id, action, hr, mn = context.job.data
    now_eg = datetime.now(MY_TZ)
    weekday = now_eg.weekday() # 1=الثلاثاء، 4=الجمعة
    
    # 1. لو اليوم "جمعة" -> إجازة كاملة (Skip لكل المواعيد)
    if weekday == 4:
        logger.info(f"⏸️ Friday Full Skip: {hr}:{mn}")
        return

    # 2. لو اليوم "ثلاثاء" -> يفتح أول فترتين فقط ويقفل الباقي
    if weekday == 1:
        # المواعيد المسموح بها يوم الثلاثاء (الفجر والصبح)
        allowed_times = [(4,30), (5,0), (7,30), (8,0)]
        if (hr, mn) not in allowed_times:
            logger.info(f"⏸️ Tuesday Partial Skip: {hr}:{mn}")
            return

    # تنفيذ الأمر لو مش إجازة
    await set_status(context.bot, chat_id, action)

def main():
    app = ApplicationBuilder().token(TOKEN).defaults(Defaults(tzinfo=MY_TZ)).build()
    
    app.add_handler(CommandHandler("open_now", open_now))
    app.add_handler(CommandHandler("close_now", close_now))

    # المواعيد المجدولة الثابتة
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

    logger.info("🚀 System Online | Friday: OFF | Tuesday: Morning Only")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
