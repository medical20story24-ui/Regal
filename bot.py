import logging
import pytz
import asyncio
from datetime import datetime, time
from telegram import Update, ChatPermissions
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, Defaults

# 1. التوقيت المصري الصارم
MY_TZ = pytz.timezone('Africa/Cairo')

# 2. الهوية الرقمية للجروب والتوكن
GROUP_IDS = [-1003738377239]
TOKEN = "8685861366:AAFMqnVQDV4UFlXX3z6HVgsHX53H-YsT_ec"

last_action_cache = {}
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

async def apply_status(bot, chat_id, action):
    now = datetime.now(MY_TZ)
    cache_key = f"{chat_id}_{action}"
    
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
        alert_msg = "🫡 تم اغلاق الجروب تماماً"
    
    try:
        await bot.set_chat_permissions(chat_id=int(chat_id), permissions=perms)
        await bot.send_message(chat_id=int(chat_id), text=alert_msg)
        last_action_cache[cache_key] = now
        logging.info(f"✅ SUCCESS: {action}")
        return True
    except Exception as e:
        logging.error(f"❌ FAILED: {e}")
        return False

async def job_trigger(context: ContextTypes.DEFAULT_TYPE):
    chat_id, action, is_fixed = context.job.data
    if is_fixed:
        now_egypt = datetime.now(MY_TZ)
        day_of_week = now_egypt.weekday() # 1 = Tuesday
        is_early_morning = now_egypt.hour < 9 
        
        if day_of_week == 1 and is_early_morning:
            logging.info("🔓 Tuesday Morning Exception Active")
        elif day_of_week in [1, 4]: 
            logging.info("⏸️ Holiday Skip")
            return
    
    await apply_status(context.bot, chat_id, action)

async def is_admin(update: Update):
    try:
        user = await update.effective_chat.get_member(update.effective_user.id)
        return user.status in ['administrator', 'creator']
    except: return False

async def open_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await is_admin(update): await apply_status(context.bot, update.effective_chat.id, "open")

async def close_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await is_admin(update): await apply_status(context.bot, update.effective_chat.id, "close")

def main():
    app = ApplicationBuilder().token(TOKEN).defaults(Defaults(tzinfo=MY_TZ)).build()
    jq = app.job_queue
    
    for gid in GROUP_IDS:
        schedule = [
            ((4,30),"open"), ((5,0),"close"),
            ((7,30),"open"), ((8,0),"close"),
            ((14,30),"open"), ((15,0),"close"),
            ((20,0),"open"), ((21,0),"close")
        ]
        for t, act in schedule:
            jq.run_daily(job_trigger, time=time(t[0], t[1], tzinfo=MY_TZ), data=(gid, act, True))
    
    app.add_handler(CommandHandler("open_now", open_now))
    app.add_handler(CommandHandler("close_now", close_now))
    
    # تصحيح المسافات هنا (أهم خطوة)
    print("🚀 System Online - Egypt Time")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
