import logging
import pytz
import asyncio
from datetime import datetime, time
from telegram import Update, ChatPermissions
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, Defaults

# 1. التوقيت المصري الصارم (القاهرة)
MY_TZ = pytz.timezone('Africa/Cairo')

# 2. قائمة الـ 17 جروب المعتمدة (القديم + الـ 4 الجدد)
GROUP_IDS = [
    -1003870414631, -1003868568456, -1003843038200, -1003842260078,
    -1003773422592, -1003309198838, -1003544491812, -1003715228581,
    -1003304815564, -1003835237780, -1003851844806, -1003863374316,
    -1003843038200,
    -1003877292835, -1003747835947, -1003793666083, -1003705337445
]

TOKEN = "8685861366:AAFKP3Nm1RG8wVx4k0aQf1KKEneCXf22ja8"

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# ---------------- وظيفة التنفيذ القهرية (تطبيق الصلاحيات) ----------------

async def apply_status(bot, chat_id, action):
    is_open = (action == "open")
    if is_open:
        perms = ChatPermissions(
            can_send_messages=True, can_send_photos=True, can_send_videos=True,
            can_send_video_notes=True, can_send_documents=True,
            can_send_other_messages=False, can_add_web_page_previews=False,
            can_send_polls=False, can_send_voice_notes=False, can_send_audios=False
        )
        alert_msg = "أمر عسكري 🪖:\n\"🫡تم فتح الجروب حالاً\""
    else:
        perms = ChatPermissions(can_send_messages=False)
        alert_msg = "أمر عسكري 🪖:\n\"🫡تم اغلاق الجروب تماماً\""
    
    try:
        await bot.set_chat_permissions(chat_id=int(chat_id), permissions=perms)
        await bot.send_message(chat_id=int(chat_id), text=alert_msg)
        logging.info(f"✅ ACTION SUCCESS: {action} on {chat_id}")
        return True
    except Exception as e:
        logging.error(f"❌ ACTION FAILED: {chat_id} | {e}")
        return False

# ---------------- المحرك الذكي للمواعيد (Job Trigger) ----------------

async def job_trigger(context: ContextTypes.DEFAULT_TYPE):
    chat_id, action, is_fixed = context.job.data
    if is_fixed:
        now_egypt = datetime.now(MY_TZ)
        if now_egypt.weekday() in [1, 4]: 
            logging.info(f"⏸️ Holiday Skip: {chat_id}")
            return
    
    # تنفيذ الأمر وإرسال الرسالة
    success = await apply_status(context.bot, chat_id, action)
    
    # "مانع التكرار" - لو نجح الإرسال بنخلي البوت ياخد هدنة دقيقة عشان ميكررش لنفس الميعاد
    if success:
        await asyncio.sleep(60)

# ---------------- أوامر التحكم (أدمن فقط) ----------------

async def is_admin(update: Update):
    try:
        user = await update.effective_chat.get_member(update.effective_user.id)
        return user.status in ['administrator', 'creator']
    except: return False

async def addtime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    if len(context.args) < 2:
        await update.message.reply_text("⚠️ المثال: /addtime 05:30 06:00")
        return
    try:
        now_eg = datetime.now(MY_TZ)
        h1, m1 = map(int, context.args[0].split(':'))
        h2, m2 = map(int, context.args[1].split(':'))
        t_open_dt = now_eg.replace(hour=h1, minute=m1, second=0, microsecond=0)
        t_close_dt = now_eg.replace(hour=h2, minute=m2, second=0, microsecond=0)
        
        if t_open_dt <= now_eg:
            await apply_status(context.bot, update.effective_chat.id, "open")
            msg = "🔓 الميعاد حان فعلاً: تم كسر القفل والفتح فوراً."
        else:
            context.job_queue.run_once(job_trigger, when=t_open_dt, data=(update.effective_chat.id, "open", False))
            msg = f"✅ ميعاد الفتح القادم: {context.args[0]}"
            
        context.job_queue.run_once(job_trigger, when=t_close_dt, data=(update.effective_chat.id, "close", False))
        await update.message.reply_text(f"{msg}\n🔒 ميعاد القفل المجدول: {context.args[1]}")
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ فني: {e}")

async def open_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await is_admin(update): await apply_status(context.bot, update.effective_chat.id, "open")

async def close_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await is_admin(update): await apply_status(context.bot, update.effective_chat.id, "close")

# ---------------- تشغيل السيستم المركزي ----------------

def main():
    # ضبط التوقيت الافتراضي للسيستم بالكامل
    bot_defaults = Defaults(tzinfo=MY_TZ)
    app = ApplicationBuilder().token(TOKEN).defaults(bot_defaults).build()
    
    jq = app.job_queue
    for gid in GROUP_IDS:
        # تعديل المواعيد حسب طلبك الصارم (6 لـ 6:15 صباحاً) و (20 لـ 21 مساءً)
        daily_schedule = [
            ((6,0), "open"), ((6,15), "close"), 
            ((20,0), "open"), ((21,0), "close")
        ]
        for t, act in daily_schedule:
            jq.run_daily(job_trigger, time=time(t[0], t[1], tzinfo=MY_TZ), data=(gid, act, True))
            
    app.add_handler(CommandHandler("open_now", open_now))
    app.add_handler(CommandHandler("close_now", close_now))
    app.add_handler(CommandHandler("addtime", addtime))
    
    print(f"🚀 نظام التحكم ({len(GROUP_IDS)} IDs) يعمل بنبض القاهرة.. مانع التكرار نشط 200%.")
    # drop_pending_updates=True تمنع انفجار الرسايل عند إعادة التشغيل
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
