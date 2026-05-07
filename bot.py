import logging
import pytz
import asyncio
from datetime import datetime, time
from telegram import Update, ChatPermissions
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, Defaults

# 1. التوقيت المصري الصارم
MY_TZ = pytz.timezone('Africa/Cairo')

# 2. الهوية الرقمية
GROUP_IDS = [-1003738377239]
TOKEN = "8685861366:AAFMqnVQDV4UFlXX3z6HVgsHX53H-YsT_ec"

# كاش لمنع التكرار المزعج
last_action_cache = {}

# إعداد اللوجر بشكل أوضح
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def apply_status(bot, chat_id, action):
    now = datetime.now(MY_TZ)
    cache_key = f"{chat_id}_{action}"
    
    # حماية من الـ Spam (30 ثانية)
    if cache_key in last_action_cache:
        if (now - last_action_cache[cache_key]).total_seconds() < 30:
            return False
    
    is_open = (action == "open")
    if is_open:
        perms = ChatPermissions(
            can_send_messages=True, can_send_photos=True, can_send_videos=True,
            can_send_video_notes=True, can_send_documents=True,
            can_send_other_messages=False, can_add_web_page_previews=False,
            can_send_polls=False, can_send_voice_notes=False, can_send_audios=False
        )
        alert_msg = "🫡 تم فتح الجروب حالاً"
    else:
        perms = ChatPermissions(can_send_messages=False)
        alert_msg = "🫡 تم إغلاق الجروب تماماً"
    
    try:
        await bot.set_chat_permissions(chat_id=int(chat_id), permissions=perms)
        await bot.send_message(chat_id=int(chat_id), text=alert_msg)
        last_action_cache[cache_key] = now
        logger.info(f"✅ SUCCESS: Group {chat_id} is now {action}")
        return True
    except Exception as e:
        logger.error(f"❌ FAILED to set permissions: {e}")
        return False

async def job_trigger(context: ContextTypes.DEFAULT_TYPE):
    # تفكيك البيانات المرسلة للمهمة
    chat_id, action, is_fixed = context.job.data
    
    if is_fixed:
        now_egypt = datetime.now(MY_TZ)
        day_of_week = now_egypt.weekday() # 0=Monday, 1=Tuesday...
        
        # استثناء فجر الثلاثاء (لو لسه قبل الساعة 9 الصبح)
        if day_of_week == 1 and now_egypt.hour < 9:
            logger.info("🔓 Tuesday Morning Exception: Processing normally")
        # استثناء أيام الإجازات (الثلاثاء والجمعة) باقي اليوم
        elif day_of_week in [1, 4]: 
            logger.info(f"⏸️ Holiday Skip (Day {day_of_week})")
            return
    
    await apply_status(context.bot, chat_id, action)

async def is_admin(update: Update):
    try:
        user = await update.effective_chat.get_member(update.effective_user.id)
        return user.status in ['administrator', 'creator']
    except Exception:
        return False

async def open_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await is_admin(update):
        await apply_status(context.bot, update.effective_chat.id, "open")

async def close_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await is_admin(update):
        await apply_status(context.bot, update.effective_chat.id, "close")

def main():
    # بناء التطبيق مع تحديد الـ Defaults بشكل صارم
    defaults = Defaults(tzinfo=MY_TZ)
    app = ApplicationBuilder().token(TOKEN).defaults(defaults).build()
    
    jq = app.job_queue
    
    if not jq:
        logger.error("❌ JobQueue is not available! Install python-telegram-bot[job-queue]")
        return

    # جدولة المواعيد
    schedule = [
        ((4, 30), "open"),  ((5, 0), "close"),
        ((7, 30), "open"),  ((8, 0), "close"),
        ((14, 30), "open"), ((15, 0), "close"),
        ((20, 0), "open"),  ((21, 0), "close")
    ]

    for gid in GROUP_IDS:
        for (hr, mn), act in schedule:
            # استخدام pytz.timezone مباشرة داخل time لضمان الدقة
            scheduled_time = time(hour=hr, minute=mn, tzinfo=MY_TZ)
            jq.run_daily(
                job_trigger, 
                time=scheduled_time, 
                data=(gid, act, True),
                name=f"{gid}_{hr}_{mn}_{act}"
            )
            logger.info(f"📅 Scheduled: {act} at {hr}:{mn} for {gid}")

    # الـ Handlers
    app.add_handler(CommandHandler("open_now", open_now))
    app.add_handler(CommandHandler("close_now", close_now))
    
    print("🚀 System Online - Egypt Military Time Active")
    
    # تشغيل البوت مع تنظيف التحديثات القديمة
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
