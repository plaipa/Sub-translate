"""Bot interface strings. English is the default and the fallback."""

UI_LANGUAGES = {  # code -> name shown on the picker button
    "en": "English", "fa": "فارسی", "zh": "中文", "ru": "Русский",
    "hi": "हिन्दी", "es": "Español", "tr": "Türkçe", "ar": "العربية",
}
DEFAULT_UI = "en"
PICK_UI = "🌐 Choose your language / زبان خود را انتخاب کنید / 请选择语言 / Выберите язык"

# Translation-target names shown on buttons (native names).
NATIVE = {
    "fa": "فارسی", "en": "English", "ar": "العربية", "tr": "Türkçe", "ru": "Русский",
    "de": "Deutsch", "fr": "Français", "es": "Español", "it": "Italiano", "pt": "Português",
    "zh-CN": "中文", "ja": "日本語", "ko": "한국어", "hi": "हिन्दी", "ur": "اردو", "az": "Azərbaycanca",
}

COMMANDS = ("start", "language", "help", "id")

SUPPORT = "@plaipa"
# Bot profile texts (Telegram limits: description 512 chars, short description 120).
DESCRIPTION = (
    "Translate subtitle files in seconds. Send a .srt or .vtt file, pick a language - "
    "English, Persian, Chinese, Russian, Hindi, Spanish, Turkish, Arabic and more - and get it "
    "back translated with the original timing and formatting intact. AI-powered, "
    "dialogue-aware translation that reads like natural speech.\n\n"
    "Send /start to begin.\n"
    f"Questions, problems or ideas? Contact support: {SUPPORT}"
)
SHORT_DESCRIPTION = f"AI subtitle translator for .srt/.vtt files. Support: {SUPPORT}"

S = {
"en": dict(
    welcome="Hi! Send me a subtitle file (.srt or .vtt), pick a target language, and I'll send it back translated.\n\nMenu: /language – change bot language · /help – how it works",
    help="How it works:\n1. Send a .srt or .vtt file (up to 5 MB).\n2. Pick the language to translate into.\n3. Get the translated file back.\n\n/language – change the bot's language\n/id – show your Telegram ID",
    ui_set="Language set to English.", bad_type="Only .srt and .vtt files are supported.",
    too_big="The file is larger than 5 MB.", pick_target="Which language should I translate to?",
    translating="Translating to {lang} …", progress="Translating to {lang} … {done}/{total}",
    failed="Translation failed. Please try again later.", done="✅ Done.",
    expired="That file has expired, please send it again.", private="This bot is private.",
    your_id="Your Telegram ID: {id}",
    cmd_start="Start", cmd_language="Change bot language", cmd_help="How it works", cmd_id="Show my Telegram ID"),
"fa": dict(
    welcome="سلام! یه فایل زیرنویس (.srt یا .vtt) برام بفرست، زبان مقصد رو انتخاب کن و ترجمه‌شده تحویل بگیر.\n\nمنو: /language – تغییر زبان بات · /help – راهنما",
    help="روش کار:\n۱. یه فایل .srt یا .vtt بفرست (حداکثر ۵ مگابایت).\n۲. زبانی که می‌خوای بهش ترجمه بشه رو انتخاب کن.\n۳. فایل ترجمه‌شده رو تحویل بگیر.\n\n/language – تغییر زبان بات\n/id – نمایش آیدی تلگرام شما",
    ui_set="زبان بات روی فارسی تنظیم شد.", bad_type="فقط فایل‌های .srt و .vtt پشتیبانی می‌شن.",
    too_big="فایل بزرگ‌تر از ۵ مگابایته.", pick_target="به چه زبانی ترجمه کنم؟",
    translating="در حال ترجمه به {lang} …", progress="در حال ترجمه به {lang} … {done}/{total}",
    failed="ترجمه با خطا مواجه شد. بعداً دوباره امتحان کن.", done="✅ آماده شد.",
    expired="فایل منقضی شده، دوباره بفرست.", private="این بات خصوصیه.",
    your_id="آیدی تلگرام شما: {id}",
    cmd_start="شروع", cmd_language="تغییر زبان بات", cmd_help="راهنما", cmd_id="نمایش آیدی تلگرام من"),
"zh": dict(
    welcome="你好！发送字幕文件（.srt 或 .vtt），选择目标语言，我会把翻译后的文件发回给你。\n\n菜单：/language – 更改机器人语言 · /help – 使用说明",
    help="使用方法：\n1. 发送 .srt 或 .vtt 文件（最大 5 MB）。\n2. 选择要翻译成的语言。\n3. 收到翻译后的文件。\n\n/language – 更改机器人语言\n/id – 显示你的 Telegram ID",
    ui_set="语言已设置为中文。", bad_type="仅支持 .srt 和 .vtt 文件。",
    too_big="文件超过 5 MB。", pick_target="要翻译成哪种语言？",
    translating="正在翻译成{lang} …", progress="正在翻译成{lang} … {done}/{total}",
    failed="翻译失败，请稍后再试。", done="✅ 完成。",
    expired="文件已过期，请重新发送。", private="这是私人机器人。",
    your_id="你的 Telegram ID：{id}",
    cmd_start="开始", cmd_language="更改机器人语言", cmd_help="使用说明", cmd_id="显示我的 Telegram ID"),
"ru": dict(
    welcome="Привет! Отправьте файл субтитров (.srt или .vtt), выберите язык перевода, и я верну переведённый файл.\n\nМеню: /language – сменить язык бота · /help – как это работает",
    help="Как это работает:\n1. Отправьте файл .srt или .vtt (до 5 МБ).\n2. Выберите язык перевода.\n3. Получите переведённый файл.\n\n/language – сменить язык бота\n/id – показать ваш Telegram ID",
    ui_set="Язык бота: русский.", bad_type="Поддерживаются только файлы .srt и .vtt.",
    too_big="Файл больше 5 МБ.", pick_target="На какой язык перевести?",
    translating="Перевожу на {lang} …", progress="Перевожу на {lang} … {done}/{total}",
    failed="Не удалось выполнить перевод. Попробуйте позже.", done="✅ Готово.",
    expired="Файл устарел, отправьте его снова.", private="Этот бот частный.",
    your_id="Ваш Telegram ID: {id}",
    cmd_start="Начать", cmd_language="Сменить язык бота", cmd_help="Как это работает", cmd_id="Показать мой Telegram ID"),
"hi": dict(
    welcome="नमस्ते! मुझे सबटाइटल फ़ाइल (.srt या .vtt) भेजें, लक्ष्य भाषा चुनें, और मैं अनुवाद करके वापस भेज दूँगा।\n\nमेनू: /language – बॉट की भाषा बदलें · /help – उपयोग कैसे करें",
    help="कैसे काम करता है:\n1. .srt या .vtt फ़ाइल भेजें (अधिकतम 5 MB)।\n2. जिस भाषा में अनुवाद चाहिए उसे चुनें।\n3. अनुवादित फ़ाइल पाएँ।\n\n/language – बॉट की भाषा बदलें\n/id – अपना Telegram ID देखें",
    ui_set="भाषा हिन्दी पर सेट की गई।", bad_type="केवल .srt और .vtt फ़ाइलें समर्थित हैं।",
    too_big="फ़ाइल 5 MB से बड़ी है।", pick_target="किस भाषा में अनुवाद करूँ?",
    translating="{lang} में अनुवाद हो रहा है …", progress="{lang} में अनुवाद हो रहा है … {done}/{total}",
    failed="अनुवाद विफल रहा। कृपया बाद में पुनः प्रयास करें।", done="✅ हो गया।",
    expired="फ़ाइल की अवधि समाप्त हो गई, कृपया दोबारा भेजें।", private="यह बॉट निजी है।",
    your_id="आपका Telegram ID: {id}",
    cmd_start="शुरू करें", cmd_language="बॉट की भाषा बदलें", cmd_help="उपयोग कैसे करें", cmd_id="मेरा Telegram ID दिखाएँ"),
"es": dict(
    welcome="¡Hola! Envíame un archivo de subtítulos (.srt o .vtt), elige el idioma de destino y te lo devolveré traducido.\n\nMenú: /language – cambiar el idioma del bot · /help – cómo funciona",
    help="Cómo funciona:\n1. Envía un archivo .srt o .vtt (máx. 5 MB).\n2. Elige el idioma al que traducir.\n3. Recibe el archivo traducido.\n\n/language – cambiar el idioma del bot\n/id – mostrar tu ID de Telegram",
    ui_set="Idioma establecido: español.", bad_type="Solo se admiten archivos .srt y .vtt.",
    too_big="El archivo supera los 5 MB.", pick_target="¿A qué idioma lo traduzco?",
    translating="Traduciendo a {lang} …", progress="Traduciendo a {lang} … {done}/{total}",
    failed="La traducción falló. Inténtalo de nuevo más tarde.", done="✅ Listo.",
    expired="El archivo ha caducado, envíalo de nuevo.", private="Este bot es privado.",
    your_id="Tu ID de Telegram: {id}",
    cmd_start="Iniciar", cmd_language="Cambiar idioma del bot", cmd_help="Cómo funciona", cmd_id="Mostrar mi ID de Telegram"),
"tr": dict(
    welcome="Merhaba! Bana bir altyazı dosyası (.srt veya .vtt) gönder, hedef dili seç; çevrilmiş halini geri göndereyim.\n\nMenü: /language – bot dilini değiştir · /help – nasıl çalışır",
    help="Nasıl çalışır:\n1. Bir .srt veya .vtt dosyası gönder (en fazla 5 MB).\n2. Çevrilecek dili seç.\n3. Çevrilmiş dosyayı al.\n\n/language – bot dilini değiştir\n/id – Telegram kimliğini göster",
    ui_set="Dil Türkçe olarak ayarlandı.", bad_type="Yalnızca .srt ve .vtt dosyaları desteklenir.",
    too_big="Dosya 5 MB'tan büyük.", pick_target="Hangi dile çevireyim?",
    translating="{lang} diline çevriliyor …", progress="{lang} diline çevriliyor … {done}/{total}",
    failed="Çeviri başarısız oldu. Lütfen daha sonra tekrar dene.", done="✅ Tamam.",
    expired="Dosyanın süresi doldu, lütfen tekrar gönder.", private="Bu bot özeldir.",
    your_id="Telegram kimliğin: {id}",
    cmd_start="Başlat", cmd_language="Bot dilini değiştir", cmd_help="Nasıl çalışır", cmd_id="Telegram kimliğimi göster"),
"ar": dict(
    welcome="مرحباً! أرسل لي ملف ترجمة (.srt أو .vtt)، واختر اللغة المطلوبة، وسأعيده إليك مترجماً.\n\nالقائمة: /language – تغيير لغة البوت · /help – طريقة الاستخدام",
    help="طريقة العمل:\n١. أرسل ملف .srt أو .vtt (حتى 5 ميغابايت).\n٢. اختر اللغة التي تريد الترجمة إليها.\n٣. استلم الملف المترجم.\n\n/language – تغيير لغة البوت\n/id – عرض معرّف تيليجرام الخاص بك",
    ui_set="تم ضبط اللغة على العربية.", bad_type="الملفات المدعومة فقط: .srt و .vtt.",
    too_big="حجم الملف أكبر من 5 ميغابايت.", pick_target="إلى أي لغة أترجم؟",
    translating="جارٍ الترجمة إلى {lang} …", progress="جارٍ الترجمة إلى {lang} … {done}/{total}",
    failed="فشلت الترجمة. حاول مرة أخرى لاحقاً.", done="✅ تم.",
    expired="انتهت صلاحية الملف، أرسله مرة أخرى.", private="هذا البوت خاص.",
    your_id="معرّف تيليجرام الخاص بك: {id}",
    cmd_start="ابدأ", cmd_language="تغيير لغة البوت", cmd_help="طريقة الاستخدام", cmd_id="عرض معرّفي"),
}


def text(ui: str, key: str, **kw) -> str:
    return S.get(ui, S[DEFAULT_UI])[key].format(**kw)
