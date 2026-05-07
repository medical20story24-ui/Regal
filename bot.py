
import logging
import pytz
from datetime import datetime, time
from telegram import Update, ChatPermissions
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, Defaults

# 1. الإعدادات
MY_TZ = pytz.timezone('Africa/Cairo')
GROUP_IDS = [-1003738377239]
# حطينا التوكن الجديد هنا يدوي عشان يقرأه فوراً
TOKEN = "8685861366:AAGmGYGu92tHgKb13QEsaScpMw8_WNJXqjA"

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# وظيفة التنفيذ
async def set_status(bot, chat_id, action):
    is_open = (action == "open")
    perms = ChatPermissions(can_send_messages=True) if is_open else ChatPermissions(can_send_messages=False)
    msg = "🫡 تم فتح الجروب حالاً" if is_open else "🫡 تم إغلاق الجروب تماماً"
    try:
        await bot.set_chat_permissions(chat_id=chat_id, permissions=perms)
        await bot.send_message(chat_id=chat_id, text=msg)
        return True
    except Exception as e:
        logger.error(f"Error: {e}")
        return False

# أوامر فورية
async def open_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await set_status(context.bot, update.effective_chat.id, "open")

async def close_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await set_status(context.bot, update.effective_chat.id, "close")

# شغل المواعيد (التايمر)
async def job_trigger(context: ContextTypes.DEFAULT_TYPE):
    chat_id, action = context.job.data
    await set_status(context.bot, chat_id, action)

def main():
    app = ApplicationBuilder().token(TOKEN).defaults(Defaults(tzinfo=MY_TZ)).build()
    
    # إضافة الأوامر للكود
    app.add_handler(CommandHandler("open_now", open_now))
    app.add_handler(CommandHandler("close_now", close_now))

    # المواعيد
    schedule = [((4,30),"open"), ((5,0),"close"), ((7,30),"open"), ((8,0),"close"), 
                ((14,30),"open"), ((15,0),"close"), ((20,0),"open"), ((21,0),"close")]

    for gid in GROUP_IDS:
        for (hr, mn), act in schedule:
            app.job_queue.run_daily(job_trigger, time=time(hour=hr, minute=mn, tzinfo=MY_TZ), data=(gid, act))

    logger.info("🚀 System Online with NEW TOKEN")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
