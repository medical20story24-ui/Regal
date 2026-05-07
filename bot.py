import logging
import pytz
import asyncio
from datetime import datetime, time
from telegram import Update, ChatPermissions
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, Defaults

# 1. التوقيت المصري الصارم (القاهرة)
MY_TZ = pytz.timezone('Africa/Cairo')

# 2. قائمة الـ IDs المعتمدة
GROUP_IDS = [
    -1003738377239
]

TOKEN = "8685861366:AAFKP3Nm1RG8wVx4k0aQf1KKEneCXf22ja8"

# مخزن لمنع التكرار (Global Dictionary)
last_action_cache = {}

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# ---------------- وظيفة التنفيذ القهرية (تطبيق الصلاحيات) ----------------

async def apply_status(bot, chat_id, action):
    now = datetime.now(MY_TZ)
    
    # --- نظام مانع التكرار الصارم ---
    cache_key = f"{chat_id}_{action}"
    if cache_key in last_action_cache:
        diff = (now - last_action_cache[cache_key]).total_seconds()
        if diff < 30:  # لو اتكرر في أقل من 30 ثانية ارفض التكرار
            logging.info(f"🛡️ Anti-Duplicate Blocked: {action} on {chat_id} (Diff: {diff}s)")
            return False
    
    is_open = (action == "open")
    if is_open:
        perms = ChatPermissions(
            can_send_messages=True, can_send_photos=True, can_send_videos=True,
            can_send_video_notes=True, can_send_documents=True,
            can_send_other_messages=False, can_add_web_page_previews=False,
            can_send_polls=False, can_send_voice_notes=False, can_send_audios=False
        )
        alert_msg = "\"🫡تم فتح الجروب حالاً\""
    else:
        perms = ChatPermissions(can_send_messages=False)
        alert_msg = "\"🫡تم اغلاق الجروب تماماً\""
    
    try:
        await bot.set_chat_permissions(chat_id=int(chat_id), permissions=perms)
        await bot.send_message(chat_id=int(chat_id), text=alert_msg)
        
        # تحديث وقت آخر عملية ناجحة
        last_action_cache[cache_key] = now
        
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
        day_of_week = now_egypt.weekday() # 1 = الثلاثاء، 4 = الجمعة
        
        # استثناء يوم الثلاثاء لأول فترتين فقط (قبل الساعة 9 صباحاً)
        is_early_morning = now_egypt.hour < 9
        
        if day_of_week == 1 and is_early_morning:
            # تنفيذ الأمر بشكل طبيعي يوم الثلاثاء في الصباح
            logging.info(f"🔓 Tuesday Morning Exception: Executing {action} on {chat_id}")
        elif day_of_week in [1, 4]: 
            # باقي حالات الثلاثاء والجمعة إجازة
            logging.info(f"⏸️ Holiday Skip: {chat_id}")
            return
    
    await apply_status(context.bot, chat_id, action)

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
    bot_defaults = Defaults(tzinfo=MY_TZ)
    app = ApplicationBuilder().token(TOKEN).defaults(bot_defaults).build()
    
    jq = app.job_queue
    for gid in GROUP_IDS:
        # المواعيد المطلوبة:
        # 1. 4:30 ص - 5:00 ص (تعمل الثلاثاء)
        # 2. 7:30 ص - 8:00 ص (تعمل الثلاثاء)
        # 3. 14:30 - 15:00 (إجازة الثلاثاء)
        # 4. 20:00 - 21:00 (إجازة الثلاثاء)
        daily_schedule = [
            ((4,30), "open"), ((5,0), "close"), 
            ((7,30), "open"), ((8,0), "close"),
            ((14,30), "open"), ((15,0), "close"),
            ((20,0), "open"), ((21,0), "close")
        ]
        for t, act in daily_schedule:
            jq.run_daily(job_trigger, time=time(t[0], t[1], tzinfo=MY_TZ), data=(gid, act, True))
            
    app.add_handler(CommandHandler("open_now", open_now))
    app.add_handler(CommandHandler("close_now", close_now))
    app.add_handler(CommandHandler("addtime", addtime))
    
    print(f"🚀 نظام التحكم ({len(GROUP_IDS)} IDs) يعمل بنبض القاهرة.. استثناء صباح الثلاثاء نشط.")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
