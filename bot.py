import os
import logging
import pytz
from datetime import datetime, time
from telegram import Update, ChatPermissions
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, Defaults

# 1. الإعدادات الأساسية
MY_TZ = pytz.timezone('Africa/Cairo')
GROUP_IDS = [-1003738377239]
TOKEN = os.getenv("MY_BOT_TOKEN")

# إعداد اللوجر
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def apply_status(bot, chat_id, action):
    is_open = (action == "open")
    perms = ChatPermissions(can_send_messages=True) if is_open else ChatPermissions(can_send_messages=False)
    alert_msg = "🫡 تم فتح الجروب حالاً" if is_open else "🫡 تم إغلاق الجروب تماماً"
    
    try:
        await bot.set_chat_permissions(chat_id=int(chat_id), permissions=perms)
        await bot.send_message(chat_id=int(chat_id), text=alert_msg)
        logger.info(f"✅ {action} SUCCESS for {chat_id}")
    except Exception as e:
        logger.error(f"❌ {action} FAILED: {e}")

async def job_trigger(context: ContextTypes.DEFAULT_TYPE):
    chat_id, action = context.job.data
    # استثناء أيام الإجازات (الثلاثاء والجمعة)
    now = datetime.now(MY_TZ)
    if now.weekday() in [1, 4] and now.hour > 9:
        logger.info("⏸️ Holiday Skip Active")
        return
    await apply_status(context.bot, chat_id, action)

def main():
    if not TOKEN:
        logger.error("❌ NO TOKEN FOUND IN VARIABLES!")
        return

    # بناء التطبيق بطريقة الـ Defaults الصارمة
    app = ApplicationBuilder().token(TOKEN).defaults(Defaults(tzinfo=MY_TZ)).build()
    
    # جدولة المواعيد
    schedule = [
        ((4, 30), "open"),  ((5, 0), "close"),
        ((7, 30), "open"),  ((8, 0), "close"),
        ((14, 30), "open"), ((15, 0), "close"),
        ((20, 0), "open"),  ((21, 0), "close")
    ]

    for gid in GROUP_IDS:
        for (hr, mn), act in schedule:
            app.job_queue.run_daily(
                job_trigger, 
                time=time(hour=hr, minute=mn, tzinfo=MY_TZ), 
                data=(gid, act)
            )

    print("🚀 System Online - Egypt Military Time")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
