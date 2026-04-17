"""Generate Arabic user manual v2 with proper Arabic font rendering."""

import os
import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

DOCS_DIR = os.path.dirname(__file__)

# Register Arabic fonts
pdfmetrics.registerFont(TTFont("NotoArabic", os.path.join(DOCS_DIR, "NotoSansArabic-Regular.ttf")))
pdfmetrics.registerFont(TTFont("NotoArabicBold", os.path.join(DOCS_DIR, "NotoSansArabic-Bold.ttf")))

PRIMARY = HexColor("#25D366")
DARK = HexColor("#1A1A2E")
GRAY = HexColor("#6B7280")
LIGHT = HexColor("#F1F5F9")


def ar(text):
    """Reshape and reorder Arabic text for correct PDF rendering."""
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)


def build():
    output = os.path.join(DOCS_DIR, "KW_Growth_Engine_Manual_AR.pdf")
    doc = SimpleDocTemplate(output, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm, leftMargin=2.5*cm, rightMargin=2.5*cm)

    # Styles
    title_style = ParagraphStyle("ARTitle", fontName="NotoArabicBold", fontSize=28, leading=42, textColor=DARK, alignment=TA_CENTER, spaceAfter=12)
    subtitle_style = ParagraphStyle("ARSub", fontName="NotoArabic", fontSize=14, leading=22, textColor=GRAY, alignment=TA_CENTER, spaceAfter=30)
    h1 = ParagraphStyle("ARH1", fontName="NotoArabicBold", fontSize=22, leading=34, textColor=DARK, spaceBefore=28, spaceAfter=14, alignment=TA_RIGHT)
    h2 = ParagraphStyle("ARH2", fontName="NotoArabicBold", fontSize=16, leading=26, textColor=PRIMARY, spaceBefore=18, spaceAfter=10, alignment=TA_RIGHT)
    h3 = ParagraphStyle("ARH3", fontName="NotoArabicBold", fontSize=13, leading=22, textColor=DARK, spaceBefore=12, spaceAfter=8, alignment=TA_RIGHT)
    body = ParagraphStyle("ARBody", fontName="NotoArabic", fontSize=11, leading=20, textColor=black, spaceAfter=8, alignment=TA_RIGHT)
    bullet = ParagraphStyle("ARBul", fontName="NotoArabic", fontSize=11, leading=20, textColor=black, spaceAfter=5, alignment=TA_RIGHT)
    note = ParagraphStyle("ARNote", fontName="NotoArabic", fontSize=10, leading=16, textColor=GRAY, spaceAfter=10, alignment=TA_RIGHT)
    footer = ParagraphStyle("ARFoot", fontName="NotoArabic", fontSize=8, leading=12, textColor=GRAY, alignment=TA_CENTER)

    def tbl_style(has_header=True):
        s = [
            ("FONTNAME", (0, 0), (-1, -1), "NotoArabic"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#E5E7EB")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ]
        if has_header:
            s += [
                ("BACKGROUND", (0, 0), (-1, 0), DARK),
                ("TEXTCOLOR", (0, 0), (-1, 0), white),
                ("FONTNAME", (0, 0), (-1, 0), "NotoArabicBold"),
            ]
        return TableStyle(s)

    story = []

    # ═══ COVER ════════════════════════════════════════════════════════
    story.append(Spacer(1, 60))
    story.append(Paragraph(ar("محرك نمو واتساب الكويت"), title_style))
    story.append(Spacer(1, 8))
    story.append(Paragraph(ar("دليل المستخدم الشامل للمؤسسات"), subtitle_style))
    story.append(Spacer(1, 25))

    cover = [
        [ar("القيمة"), ar("البند")],
        ["1.0", ar("الإصدار")],
        [ar("أبريل 2026"), ar("التاريخ")],
        [ar("نظام إدارة علاقات العملاء عبر واتساب"), ar("المنصة")],
        [ar("الكويت / دول الخليج العربي"), ar("السوق المستهدف")],
        [ar("26 وحدة برمجية"), ar("الوحدات")],
        [ar("135 نقطة وصول"), ar("واجهات برمجة التطبيقات")],
        [ar("40 جدول بيانات"), ar("قاعدة البيانات")],
        [ar("23 صفحة"), ar("واجهة المستخدم")],
    ]
    t = Table(cover, colWidths=[250, 130])
    t.setStyle(tbl_style())
    story.append(t)
    story.append(PageBreak())

    # ═══ TABLE OF CONTENTS ════════════════════════════════════════════
    story.append(Paragraph(ar("فهرس المحتويات"), h1))
    story.append(Spacer(1, 10))
    toc = [
        "1. البدء والتسجيل",
        "2. لوحة التحكم الرئيسية",
        "3. إدارة جهات الاتصال والعملاء",
        "4. صندوق الوارد الموحد (واتساب)",
        "5. الحملات التسويقية والبث الجماعي",
        "6. منشئ بوت المحادثة التفاعلي",
        "7. محرك الأتمتة والقواعد الذكية",
        "8. خط المبيعات ولوحة كانبان",
        "9. منشئ صفحات الهبوط",
        "10. قوالب رسائل واتساب",
        "11. لوحة التحليلات والتقارير",
        "12. إدارة الشحن والتتبع",
        "13. المدفوعات والفواتير والاشتراكات",
        "14. الإعدادات وإدارة الفريق",
        "15. الامتثال وأمن البيانات",
        "16. مرجع واجهة برمجة التطبيقات API",
    ]
    for item in toc:
        story.append(Paragraph(ar(item), body))
    story.append(PageBreak())

    # ═══ CH 1: GETTING STARTED ════════════════════════════════════════
    story.append(Paragraph(ar("1. البدء والتسجيل"), h1))

    story.append(Paragraph(ar("1.1 إنشاء حساب جديد"), h2))
    story.append(Paragraph(ar("قم بزيارة الموقع app.kwgrowth.com/register وأدخل المعلومات التالية:"), body))
    for item in ["اسم الشركة", "البريد الإلكتروني", "اسم المستخدم", "كلمة المرور (8 أحرف على الأقل)"]:
        story.append(Paragraph(ar(item) + "  \u25cf", bullet))
    story.append(Paragraph(ar("سيتم تعيينك تلقائياً بدور المالك مع صلاحيات كاملة لجميع ميزات المنصة."), body))

    story.append(Paragraph(ar("1.2 تسجيل الدخول الأول"), h2))
    story.append(Paragraph(ar("بعد إتمام التسجيل، يتم توجيهك مباشرة إلى لوحة التحكم. رمز الوصول JWT صالح لمدة 15 دقيقة ويتم تجديده تلقائياً في الخلفية دون الحاجة لإعادة تسجيل الدخول."), body))

    story.append(Paragraph(ar("1.3 متطلبات النظام"), h2))
    req = [
        [ar("المتطلب"), ar("العنصر")],
        [ar("كروم 90+ أو فايرفوكس 88+ أو سفاري 14+"), ar("المتصفح")],
        [ar("حساب Meta Business مع Cloud API"), ar("واتساب")],
        [ar("حساب Tap Payments للدفع الإلكتروني"), ar("المدفوعات")],
        [ar("متجاوب - يعمل على جميع أحجام الشاشات"), ar("الجوال")],
    ]
    t = Table(req, colWidths=[280, 100])
    t.setStyle(tbl_style())
    story.append(t)
    story.append(PageBreak())

    # ═══ CH 2: DASHBOARD ══════════════════════════════════════════════
    story.append(Paragraph(ar("2. لوحة التحكم الرئيسية"), h1))
    story.append(Paragraph(ar("تعرض لوحة التحكم المؤشرات الرئيسية للأداء في نظرة واحدة:"), body))
    for item in [
        "إجمالي جهات الاتصال - عدد جهات الاتصال المسجلة في النظام",
        "المحادثات المفتوحة - المحادثات النشطة عبر واتساب",
        "الرسائل - عدد الرسائل الواردة والصادرة خلال الفترة",
        "الإيرادات - إجمالي قيمة الصفقات المكسوبة بالدينار الكويتي",
    ]:
        story.append(Paragraph(ar(item) + "  \u25cf", bullet))
    story.append(Paragraph(ar("يمكن الوصول إلى جميع الوحدات من خلال القائمة الجانبية. على الأجهزة المحمولة، اضغط على أيقونة القائمة لفتح القائمة الجانبية."), body))
    story.append(PageBreak())

    # ═══ CH 3: CONTACTS ═══════════════════════════════════════════════
    story.append(Paragraph(ar("3. إدارة جهات الاتصال والعملاء"), h1))

    story.append(Paragraph(ar("3.1 عرض وإدارة جهات الاتصال"), h2))
    story.append(Paragraph(ar("تعرض صفحة جهات الاتصال جميع العملاء في جدول بيانات متقدم يدعم:"), body))
    for item in [
        "البحث بالاسم أو رقم الهاتف أو البريد الإلكتروني",
        "التصفية حسب الحالة (نشط/غير نشط/محظور) والمصدر والوسوم",
        "الفرز التصاعدي والتنازلي بالنقر على أي عمود",
        "تحديد عدة جهات اتصال لتنفيذ إجراءات جماعية (حذف، إضافة وسم، تغيير الحالة)",
        "النقر على أي صف لفتح صفحة التفاصيل الكاملة",
    ]:
        story.append(Paragraph(ar(item) + "  \u25cf", bullet))

    story.append(Paragraph(ar("3.2 إنشاء جهة اتصال جديدة"), h2))
    story.append(Paragraph(ar("انقر على زر 'إضافة جهة اتصال' وأدخل البيانات المطلوبة. رقم الهاتف إلزامي بصيغة الكويت: 965XXXXXXXX+. يمكنك تعيين الوسوم والحقول المخصصة أثناء الإنشاء."), body))

    story.append(Paragraph(ar("3.3 الوسوم (التصنيفات)"), h2))
    story.append(Paragraph(ar("الوسوم هي تصنيفات ملونة لتنظيم جهات الاتصال. أنشئ وسوماً مثل: عميل مهم، عميل محتمل، عميل جديد. لكل وسم اسم ولون ووصف اختياري. تُدار الوسوم من: الإعدادات > الوسوم."), body))

    story.append(Paragraph(ar("3.4 الحقول المخصصة"), h2))
    story.append(Paragraph(ar("أنشئ حقولاً إضافية لتخزين بيانات خاصة بعملائك. الأنواع المدعومة: نص، رقم، تاريخ، قائمة اختيارات، نعم/لا."), body))

    story.append(Paragraph(ar("3.5 استيراد جهات الاتصال من ملف CSV"), h2))
    story.append(Paragraph(ar("انقر على 'استيراد CSV' لرفع ملف يحتوي على بيانات جهات الاتصال. يجب أن يحتوي الملف على عمود phone كحد أدنى. الأعمدة الاختيارية: first_name، last_name، email، notes. الأرقام المكررة يتم تحديث بياناتها تلقائياً."), body))
    story.append(PageBreak())

    # ═══ CH 4: INBOX ══════════════════════════════════════════════════
    story.append(Paragraph(ar("4. صندوق الوارد الموحد (واتساب)"), h1))

    story.append(Paragraph(ar("4.1 قائمة المحادثات"), h2))
    story.append(Paragraph(ar("تعرض اللوحة اليسرى جميع المحادثات مرتبة حسب آخر رسالة. كل محادثة تظهر: اسم جهة الاتصال، معاينة آخر رسالة، عدد الرسائل غير المقروءة (شارة خضراء)، ومؤشر الحالة:"), body))
    for item, color in [
        ("أخضر - مفتوحة", "#22C55E"), ("أصفر - قيد الانتظار", "#EAB308"),
        ("أزرق - مؤجلة", "#3B82F6"), ("رمادي - مغلقة", "#9CA3AF"),
    ]:
        story.append(Paragraph(ar(item) + "  \u25cf", bullet))

    story.append(Paragraph(ar("4.2 إرسال الرسائل"), h2))
    story.append(Paragraph(ar("اختر محادثة من القائمة، اكتب رسالتك في حقل الإدخال، ثم اضغط Enter أو زر 'إرسال'. يتم تسليم الرسائل عبر WhatsApp Cloud API. حالات التسليم:"), body))
    for item in [
        "ساعة رملية - قيد الإرسال",
        "علامة واحدة - تم الإرسال لخوادم واتساب",
        "علامتان - تم استلام الرسالة على الجهاز",
        "علامتان زرقاء - تمت قراءة الرسالة",
    ]:
        story.append(Paragraph(ar(item) + "  \u25cf", bullet))

    story.append(Paragraph(ar("4.3 إدارة المحادثات"), h2))
    story.append(Paragraph(ar("استخدم القائمة المنسدلة في أعلى المحادثة لتغيير حالتها: مفتوحة، قيد الانتظار، مؤجلة، مغلقة. يتم تحديث المحادثات تلقائياً كل 3 ثوان."), body))
    story.append(PageBreak())

    # ═══ CH 5: CAMPAIGNS ══════════════════════════════════════════════
    story.append(Paragraph(ar("5. الحملات التسويقية والبث الجماعي"), h1))
    story.append(Paragraph(ar("أرسل رسائل واتساب جماعية لعملائك. تدعم الحملات الميزات التالية:"), body))
    for item in [
        "رسائل القوالب - قوالب واتساب المعتمدة مسبقاً من Meta",
        "استهداف الجمهور - جميع جهات الاتصال، حسب الوسم، أو حسب شريحة مخصصة",
        "الجدولة الزمنية - إرسال فوري أو مجدول لتاريخ ووقت محدد",
        "تتبع التسليم - إحصائيات مفصلة: مرسلة، مستلمة، مقروءة، فاشلة",
        "إيقاف مؤقت واستئناف - إمكانية إيقاف حملة قيد الإرسال واستئنافها لاحقاً",
    ]:
        story.append(Paragraph(ar(item) + "  \u25cf", bullet))
    story.append(Paragraph(ar("ملاحظة: يتطلب واتساب قوالب رسائل معتمدة مسبقاً للبث الجماعي. أنشئ القوالب في قسم 'القوالب' أولاً ثم انتظر اعتماد Meta."), note))
    story.append(PageBreak())

    # ═══ CH 6: CHATBOTS ═══════════════════════════════════════════════
    story.append(Paragraph(ar("6. منشئ بوت المحادثة التفاعلي"), h1))
    story.append(Paragraph(ar("أنشئ تدفقات محادثة آلية باستخدام محرر مرئي بسيط. كل تدفق يتكون من عقد (خطوات) وروابط بينها."), body))

    story.append(Paragraph(ar("6.1 أنواع المحفزات"), h2))
    for item in [
        "مطابقة الكلمات المفتاحية - يتفعل عندما تحتوي الرسالة على كلمات محددة",
        "أي رسالة واردة - يتفعل مع كل رسالة جديدة",
        "محادثة جديدة - يتفعل عند بدء محادثة لأول مرة",
        "Webhook خارجي - يتفعل عبر استدعاء من نظام خارجي",
    ]:
        story.append(Paragraph(ar(item) + "  \u25cf", bullet))

    story.append(Paragraph(ar("6.2 أنواع العقد (الخطوات)"), h2))
    nodes = [
        [ar("الوصف"), ar("نوع العقدة")],
        [ar("إرسال رسالة نصية للعميل"), ar("إرسال رسالة")],
        [ar("طرح سؤال وانتظار الإجابة"), ar("طرح سؤال")],
        [ar("تفريع حسب محتوى الرسالة أو بيانات العميل"), ar("شرط")],
        [ar("انتظار عدد محدد من الثواني"), ar("تأخير")],
        [ar("تحويل المحادثة لموظف بشري"), ar("تعيين موظف")],
        [ar("إضافة وسم أو تحديث بيانات العميل"), ar("إجراء")],
        [ar("استدعاء واجهة برمجة خارجية"), ar("استدعاء API")],
    ]
    t = Table(nodes, colWidths=[280, 120])
    t.setStyle(tbl_style())
    story.append(t)
    story.append(PageBreak())

    # ═══ CH 7: AUTOMATIONS ════════════════════════════════════════════
    story.append(Paragraph(ar("7. محرك الأتمتة والقواعد الذكية"), h1))
    story.append(Paragraph(ar("تُشغل الأتمتة إجراءات تلقائية عند حدوث أحداث محددة في النظام. كل قاعدة أتمتة تتكون من: محفز + شروط (اختيارية) + إجراءات."), body))

    story.append(Paragraph(ar("7.1 المحفزات المتاحة"), h2))
    for item in ["رسالة واردة جديدة", "إنشاء جهة اتصال جديدة", "تحديث بيانات جهة اتصال", "بدء محادثة جديدة", "تغيير مرحلة صفقة في خط المبيعات"]:
        story.append(Paragraph(ar(item) + "  \u25cf", bullet))

    story.append(Paragraph(ar("7.2 عوامل التشغيل (الشروط)"), h2))
    story.append(Paragraph(ar("أضف شروطاً لتصفية الأحداث التي تُشغل الأتمتة. العوامل المتاحة: يساوي، لا يساوي، يحتوي، يبدأ بـ، أكبر من، أصغر من، ضمن القائمة."), body))

    story.append(Paragraph(ar("7.3 الإجراءات المتاحة"), h2))
    for item in [
        "رد تلقائي - إرسال رسالة نصية فورية",
        "إرسال قالب واتساب - رسالة قالب معتمدة",
        "إضافة أو إزالة وسم - تصنيف تلقائي للعميل",
        "تغيير حالة جهة الاتصال - نشط أو غير نشط",
        "تحديث نتيجة العميل المحتمل - زيادة أو إنقاص النقاط",
        "تعيين موظف بالتوجيه الذكي - يختار أفضل موظف متاح",
    ]:
        story.append(Paragraph(ar(item) + "  \u25cf", bullet))
    story.append(PageBreak())

    # ═══ CH 8: PIPELINE ═══════════════════════════════════════════════
    story.append(Paragraph(ar("8. خط المبيعات ولوحة كانبان"), h1))
    story.append(Paragraph(ar("توفر وحدة خط المبيعات لوحة كانبان مرئية لتتبع الصفقات عبر مراحل البيع المختلفة."), body))

    story.append(Paragraph(ar("8.1 المراحل"), h2))
    story.append(Paragraph(ar("كل خط مبيعات يحتوي على مراحل ملونة تمر بها الصفقات. المراحل الافتراضية: عميل محتمل جديد، تم التواصل، مؤهل، عرض سعر، تفاوض، مكسوبة، خاسرة. يمكنك تخصيص المراحل حسب عملك."), body))

    story.append(Paragraph(ar("8.2 إدارة الصفقات"), h2))
    story.append(Paragraph(ar("أنشئ صفقات بعنوان وقيمة بالدينار الكويتي (ثلاث خانات عشرية) مع إمكانية ربطها بجهة اتصال. اسحب بطاقات الصفقات بين الأعمدة لنقلها بين المراحل. يتم تسجيل جميع التغييرات تلقائياً في سجل النشاط:"), body))
    for item in ["تغيير المرحلة", "تعديل القيمة", "تغيير الحالة (مكسوبة/خاسرة)", "إضافة ملاحظات"]:
        story.append(Paragraph(ar(item) + "  \u25cf", bullet))
    story.append(PageBreak())

    # ═══ CH 9: LANDING PAGES ══════════════════════════════════════════
    story.append(Paragraph(ar("9. منشئ صفحات الهبوط"), h1))
    story.append(Paragraph(ar("أنشئ صفحات هبوط احترافية باستخدام محرر كتل بسيط مع زر دعوة للعمل عبر واتساب."), body))

    story.append(Paragraph(ar("9.1 أنواع الكتل المتاحة"), h2))
    for item in ["قسم البطل الرئيسي", "كتلة نص", "صورة", "شبكة المميزات", "زر دعوة للعمل", "شهادة عميل", "أسئلة شائعة", "فاصل"]:
        story.append(Paragraph(ar(item) + "  \u25cf", bullet))

    story.append(Paragraph(ar("9.2 زر واتساب للتواصل"), h2))
    story.append(Paragraph(ar("حدد رقم واتساب ورسالة مسبقة التعبئة. عندما ينقر الزائر على الزر، يُفتح واتساب مباشرة مع رقمك والرسالة جاهزة للإرسال."), body))

    story.append(Paragraph(ar("9.3 التحليلات"), h2))
    story.append(Paragraph(ar("تتبع كل صفحة عدد الزيارات والتحويلات (نقرات زر واتساب). اعرض نسبة التحويل في قائمة الصفحات وصفحة التفاصيل."), body))
    story.append(PageBreak())

    # ═══ CH 10-11 ═════════════════════════════════════════════════════
    story.append(Paragraph(ar("10. قوالب رسائل واتساب"), h1))
    story.append(Paragraph(ar("يتطلب واتساب قوالب رسائل معتمدة مسبقاً للمحادثات الصادرة. أنشئ قوالب مع متغيرات {{1}} و {{2}} وقدمها لاعتماد Meta. الفئات المدعومة: تسويقي، خدمي، مصادقة. بعد الاعتماد، يمكنك استخدام القالب في الحملات والأتمتة."), body))
    story.append(PageBreak())

    story.append(Paragraph(ar("11. لوحة التحليلات والتقارير"), h1))
    story.append(Paragraph(ar("توفر لوحة التحليلات رؤى شاملة ومحدثة لحظياً عبر جميع وحدات النظام:"), body))
    for item in [
        "لوحة التحكم - بطاقات المؤشرات الرئيسية (جهات اتصال، محادثات، رسائل، إيرادات)",
        "تحليل الرسائل - مخطط الحجم اليومي، توزيع حالات التسليم",
        "تحليل خط المبيعات - توزيع المراحل، نسبة الفوز، متوسط قيمة الصفقة",
        "أداء الفريق - لكل موظف: رسائل مرسلة، محادثات، صفقات مكسوبة، إيرادات",
        "صفحات الهبوط - زيارات وتحويلات لكل صفحة",
        "الأتمتة - عدد مرات التنفيذ ونسبة النجاح",
    ]:
        story.append(Paragraph(ar(item) + "  \u25cf", bullet))
    story.append(PageBreak())

    # ═══ CH 12: SHIPPING ══════════════════════════════════════════════
    story.append(Paragraph(ar("12. إدارة الشحن والتتبع"), h1))
    story.append(Paragraph(ar("أدر شحناتك مع تتبع متكامل من شركات الشحن. الشركات المدعومة: أرامكس الكويت، DHL، Fetchr، Shipa. الميزات:"), body))
    for item in [
        "إنشاء شحنات مع عناوين المنشأ والوجهة",
        "إنشاء أرقام تتبع تلقائياً",
        "7 حالات للشحنة: تم الإنشاء، تم الاستلام، في الطريق، خارج للتوصيل، تم التوصيل، فشل، مرتجع",
        "دعم الدفع عند الاستلام (COD) بالدينار الكويتي",
        "إشعارات تتبع تلقائية عبر واتساب للعملاء عند كل تغيير في حالة الشحنة",
    ]:
        story.append(Paragraph(ar(item) + "  \u25cf", bullet))
    story.append(PageBreak())

    # ═══ CH 13: PAYMENTS ══════════════════════════════════════════════
    story.append(Paragraph(ar("13. المدفوعات والفواتير والاشتراكات"), h1))

    story.append(Paragraph(ar("13.1 خطط الاشتراك"), h2))
    plans = [
        [ar("المؤسسات (79.900 د.ك/شهر)"), ar("النمو (29.900 د.ك/شهر)"), ar("المبتدئ (9.900 د.ك/شهر)"), ar("الميزة")],
        ["50,000", "5,000", "500", ar("جهات الاتصال")],
        ["100,000", "10,000", "1,000", ar("المحادثات شهرياً")],
        ["50", "10", "3", ar("أعضاء الفريق")],
        ["100", "25", "5", ar("قواعد الأتمتة")],
        [ar("نعم"), ar("نعم"), ar("لا"), ar("ميزات الذكاء الاصطناعي")],
        [ar("نعم"), ar("لا"), ar("لا"), ar("وصول واجهة API")],
    ]
    t = Table(plans, colWidths=[110, 110, 110, 110])
    t.setStyle(tbl_style())
    t.setStyle(TableStyle([("ALIGN", (0, 1), (2, -1), "CENTER")]))
    story.append(t)

    story.append(Paragraph(ar("13.2 طرق الدفع"), h2))
    story.append(Paragraph(ar("تتم معالجة المدفوعات عبر Tap Payments وتدعم: كي-نت (بطاقات الخصم الكويتية)، فيزا، ماستركارد، و Apple Pay. جميع المبالغ بالدينار الكويتي بثلاث خانات عشرية (مثال: 29.900 د.ك)."), body))

    story.append(Paragraph(ar("13.3 الفواتير"), h2))
    story.append(Paragraph(ar("يتم إنشاء فاتورة تلقائياً عند كل اشتراك أو تجديد. أرقام الفواتير بصيغة: INV-YYYYMM-NNNN. اعرض وادفع فواتيرك من: الإعدادات > الفواتير والاشتراك."), body))
    story.append(PageBreak())

    # ═══ CH 14: SETTINGS ══════════════════════════════════════════════
    story.append(Paragraph(ar("14. الإعدادات وإدارة الفريق"), h1))

    story.append(Paragraph(ar("14.1 إدارة أعضاء الفريق"), h2))
    story.append(Paragraph(ar("ادعُ أعضاء فريقك بالبريد الإلكتروني وعيّن لهم أدواراً:"), body))
    for item in [
        "مدير (Admin) - صلاحيات كاملة ما عدا الفواتير",
        "مشرف (Manager) - إدارة جهات الاتصال والمحادثات والصفقات",
        "موظف (Agent) - المحادثات وجهات الاتصال فقط",
    ]:
        story.append(Paragraph(ar(item) + "  \u25cf", bullet))

    story.append(Paragraph(ar("14.2 القنوات"), h2))
    story.append(Paragraph(ar("اربط قنوات التواصل: واتساب (أساسي)، إنستغرام، فيسبوك ماسنجر، دردشة الموقع، رسائل قصيرة، بريد إلكتروني. كل قناة تتطلب بيانات اعتماد خاصة بها."), body))

    story.append(Paragraph(ar("14.3 تصدير البيانات"), h2))
    story.append(Paragraph(ar("صدّر بياناتك كملفات CSV: جهات الاتصال، المحادثات، والصفقات. انتقل إلى: الإعدادات > تصدير البيانات وانقر زر التحميل."), body))
    story.append(PageBreak())

    # ═══ CH 15: COMPLIANCE ════════════════════════════════════════════
    story.append(Paragraph(ar("15. الامتثال وأمن البيانات"), h1))
    story.append(Paragraph(ar("تعرض لوحة الامتثال 8 فحوصات أمنية شاملة:"), body))
    for item in [
        "إقامة البيانات - خوادم AWS في البحرين (me-south-1) ضمن منطقة الخليج",
        "التشفير أثناء التخزين - تشفير قرص PostgreSQL بمعيار AES-256",
        "التشفير أثناء النقل - بروتوكول TLS 1.3 لجميع الاتصالات",
        "تتبع الموافقة - حالة اشتراك واتساب لكل جهة اتصال",
        "سياسة الاحتفاظ بالبيانات - قابلة للتكوين (الافتراضي: 365 يوم)",
        "سجل التدقيق - تسجيل جميع الإجراءات مع التفاصيل والتاريخ",
        "حق الحذف - إمكانية حذف بيانات العملاء بالكامل",
        "تصدير البيانات - تصدير CSV متاح لجميع البيانات",
    ]:
        story.append(Paragraph(ar(item) + "  \u2713", bullet))

    story.append(Spacer(1, 10))
    story.append(Paragraph(ar("إجراءات الأمان المطبقة:"), h3))
    for item in [
        "مصادقة JWT بصلاحية 15 دقيقة للرمز",
        "تشفير كلمات المرور بخوارزمية bcrypt (12 جولة)",
        "أمان على مستوى الصفوف PostgreSQL RLS لعزل المستأجرين",
        "نظام أدوار وصلاحيات RBAC مع 34 صلاحية",
        "تحديد معدل الطلبات للحماية من الاستخدام المفرط",
    ]:
        story.append(Paragraph(ar(item) + "  \u25cf", bullet))
    story.append(PageBreak())

    # ═══ CH 16: API ═══════════════════════════════════════════════════
    story.append(Paragraph(ar("16. مرجع واجهة برمجة التطبيقات API"), h1))
    story.append(Paragraph(ar("توفر المنصة واجهة RESTful API على المسار /v1/ مع 135 نقطة وصول عبر 26 وحدة. الوثائق التفاعلية متاحة على /docs و /redoc."), body))

    story.append(Paragraph(ar("16.1 المصادقة"), h2))
    story.append(Paragraph(ar("تتطلب جميع طلبات API رمز Bearer في رأس Authorization. احصل على الرموز عبر POST /v1/auth/login. تنتهي صلاحية رمز الوصول في 15 دقيقة. جدّده عبر POST /v1/auth/refresh باستخدام رمز التجديد."), body))

    story.append(Paragraph(ar("16.2 الوحدات الرئيسية"), h2))
    api_data = [
        [ar("النقاط"), ar("المسار"), ar("الوحدة")],
        ["4", "/v1/auth", ar("المصادقة")],
        ["7", "/v1/contacts", ar("جهات الاتصال")],
        ["5", "/v1/tags", ar("الوسوم")],
        ["6", "/v1/conversations", ar("المحادثات")],
        ["8", "/v1/campaigns", ar("الحملات")],
        ["6", "/v1/chatbots", ar("بوت المحادثة")],
        ["7", "/v1/automations", ar("الأتمتة")],
        ["16", "/v1/pipelines", ar("خط المبيعات")],
        ["10", "/v1/payments", ar("المدفوعات")],
        ["9", "/v1/shipping", ar("الشحن")],
        ["10", "/v1/landing-pages", ar("صفحات الهبوط")],
        ["6", "/v1/analytics", ar("التحليلات")],
        ["3", "/v1/ai", ar("الذكاء الاصطناعي")],
        ["3", "/v1/catalog", ar("كتالوج المنتجات")],
        ["3", "/v1/surveys", ar("الاستبيانات")],
        ["3", "/v1/export", ar("التصدير")],
        ["2", "/v1/qr", ar("رموز QR")],
    ]
    t = Table(api_data, colWidths=[50, 150, 180])
    t.setStyle(tbl_style())
    t.setStyle(TableStyle([("ALIGN", (0, 1), (0, -1), "CENTER")]))
    story.append(t)

    # Footer
    story.append(Spacer(1, 30))
    story.append(Paragraph(ar("محرك نمو واتساب الكويت - الإصدار 1.0") + " | app.kwgrowth.com | 2026", footer))

    doc.build(story)
    print(f"Arabic manual v2: {output}")
    return output


if __name__ == "__main__":
    build()
