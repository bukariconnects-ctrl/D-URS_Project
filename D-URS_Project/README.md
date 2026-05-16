# D-URS — نظام مشاركة الموارد الجامعية اللامركزي

**Decentralized University Resource Sharing & Collaboration System**

نظام موزع هجين (Hybrid P2P) لمشاركة الملفات الدراسية بين الطلاب، يجمع بين البنية المركزية للتنسيق والبنية اللامركزية لنقل الملفات.

---

## المتطلبات الأساسية

### 1. Python

- **الإصدار المطلوب:** Python 3.8 أو أحدث
- يُفضل Python 3.10+ لضمان توفر جميع المكتبات القياسية المستخدمة

للتحقق من الإصدار المُثبّت:

```bash
python --version
```

### 2. pip (مدير حزم Python)

يأتي مُضمّناً مع Python 3.4+. للتحقق:

```bash
pip --version
```

---

## المكتبات المطلوبة

### مكتبات خارجية (يُلزم تثبيتها)

| المكتبة | الإصدار المُوصى به | الغرض في النظام |
|---------|-------------------|-----------------|
| **Flask** | 3.x | إطار عمل الويب — يخدم لوحات المدير والطالب وواجهة REST API |
| **cryptography** | 41.x+ | توليد شهادات SSL ذاتية التوقيع لاتصالات P2P المشفرة |

### مكتبات قياسية (مُضمّنة مع Python — لا تحتاج تثبيت)

| المكتبة | الغرض |
|---------|-------|
| `socket` | اتصالات TCP و P2P |
| `ssl` | تغليف المقابس بـ SSL/TLS |
| `threading` | التشغيل المتوازي (خيوط خفية لخدمة الويب و P2P والإشعارات) |
| `xmlrpc.server` / `xmlrpc.client` | استدعاء الإجراءات عن بعد (RPC) |
| `sqlite3` | قواعد البيانات المحلية والمركزية |
| `hashlib` | تجزئة SHA-256 (بصمة الملفات وكلمات المرور) |
| `secrets` | توليد رموز الجلسة الآمنة |
| `os`, `sys`, `pathlib` | عمليات النظام والمسارات |
| `mimetypes` | كشف أنواع الملفات (MIME) |
| `shutil` | نسخ الملفات (النسخ الاحتياطية) |
| `tempfile` | الملفات المؤقتة |
| `functools` | أدوات الوظائف (wrappers) |
| `urllib` | طلبات HTTP (رفع النسخ الاحتياطية) |
| `re` | التعابير النمطية |
| `datetime` | الطوابع الزمنية |

---

## التثبيت والإعداد

### الخطوة 1: استنساخ المشروع

```bash
git clone https://github.com/bukariconnects-ctrl/D-URS_Project.git
cd D-URS_Project
```

### الخطوة 2: إنشاء بيئة افتراضية (اختياري لكن مُوصى به)

```bash
# إنشاء البيئة
python -m venv venv

# تفعيل البيئة — Windows
venv\Scripts\activate

# تفعيل البيئة — Linux / macOS
source venv/bin/activate
```

### الخطوة 3: تثبيت المكتبات

```bash
pip install -r requirements.txt
```

محتوى `requirements.txt`:

```
Flask
cryptography
```

> **ملاحظة:** إذا لم تتوفر مكتبة `cryptography`، يعتمد النظام تلقائياً على أداة OpenSSL السطرية لتوليد الشهادات (انظر أدناه).

---

## أدوات اختيارية

### OpenSSL (بديل لتوليد الشهادات)

إذا لم تُثبّت مكتبة `cryptography`، يستخدم النظام أداة OpenSSL السطرية لتوليد شهادات SSL ذاتية التوقيع.

- **Windows:** تأتي مُضمّنة مع تثبيت Git for Windows، أو حمّلها من [slproweb.com](https://slproweb.com/products/Win32OpenSSL.html)
- **Linux:** `sudo apt install openssl` (غالباً مُثبّت مسبقاً)
- **macOS:** `brew install openssl`

للتحقق من التثبيت:

```bash
openssl version
```

---

## تشغيل النظام

### وضع العرض الموحد (Demo Mode)

هذا الوضع يُشغل الخادم المركزي مع عقد افتراضية داخل نفس العملية — مناسب للاختبار على جهاز واحد:

```bash
python server/central_server.py
```

بعد التشغيل:
1. افتح المتصفح على `http://127.0.0.1:5000`
2. سجّل دخولك بحساب المدير الافتراضي:
   - اسم المستخدم: `admin`
   - كلمة المرور: `admin123`
3. أنشئ حساب طالب من صفحة التسجيل
4. سجّل دخولك كطالب لمشاركة الملفات وتنزيلها والاشتراك في المواضيع

### وضع الإنتاج (Production Mode)

في بيئة الإنتاج، يُشغل كل طالب عقدته المستقلة على جهازه:

**على جهاز الخادم المركزي:**

```bash
python server/central_server.py
```

**على كل جهاز طالب:**

1. عدّل `shared/config.py` ليُشير إلى عنوان IP الفعلي للخادم المركزي:
   ```python
   SERVER_IP = '192.168.x.x'  # عنوان IP الفعلي للخادم
   SERVER_RPC_PORT = 8000
   SERVER_WEB_PORT = 5000
   ```

2. شغّل عقدة الطالب:
   ```bash
   python peer/peer_node.py
   ```

---

## هيكل المشروع

```
D-URS_Project/
├── server/                     # الخادم المركزي
│   ├── central_server.py       # نقطة الدخول الرئيسية (RPC + Flask + Broker)
│   ├── web_service.py          # تطبيق Flask الموحد (المدير + الطالب)
│   ├── db_manager.py           # إدارة قاعدة بيانات SQLite المركزية
│   ├── server_index.db         # قاعدة البيانات المركزية
│   ├── certs/                  # شهادات SSL للعقد الافتراضية
│   ├── storage/
│   │   └── backups/            # النسخ الاحتياطية للملفات
│   ├── templates/              # قوالب HTML (admin, student, login)
│   └── static/                 # ملفات CSS
│
├── peer/                       # عقدة الطالب
│   ├── peer_node.py            # نقطة الدخول الرئيسية (RPC Client + P2P)
│   ├── p2p_network.py          # خادم وعميل P2P عبر SSL/TCP
│   ├── local_db.py             # إدارة قاعدة بيانات SQLite المحلية
│   ├── web_app.py              # واجهة ويب الطالب المستقلة
│   ├── peer_local.db           # قاعدة البيانات المحلية
│   ├── certs/                  # شهادات SSL للعقدة
│   ├── downloads/              # الملفات المنزّلة
│   ├── shared_files/           # الملفات المُشاركة
│   ├── templates/              # قوالب HTML
│   └── static/                 # ملفات CSS
│
├── shared/                     # مكونات مشتركة
│   ├── config.py               # ثوابت الشبكة (IP, منافذ)
│   └── security.py             # تجزئة SHA-256 وتوليد الرموز
│
├── storage/
│   └── peers/                  # ملفات الطلاب الأصلية (في وضع Demo)
│
├── requirements.txt            # المكتبات المطلوبة
├── academic_documentation.md   # التوثيق الأكاديمي المفصل
├── academic_documentation.docx # نسخة Word من التوثيق
├── DOCUMENTATION.md            # التوثيق التقني
└── md_to_docx.py               # سكربت تحويل Markdown → Word
```

---

## المنافذ المستخدمة

| المنفذ | البروتوكول | الغرض |
|--------|-----------|-------|
| 8000 | XML-RPC | استدعاء الإجراءات عن بعد (تسجيل، بحث، اشتراك) |
| 5000 | HTTP/Flask | واجهة الويب (لوحات المدير والطالب) |
| 9000+ | SSL/TCP | اتصالات P2P بين الأقران (يُخصص ديناميكياً) |
| عشوائي | TCP | مستمع الإشعارات (يُخصص ديناميكياً) |

> **تنبيه:** تأكد من أن المنافذ 8000 و 5000 غير مُستخدمة من تطبيقات أخرى قبل التشغيل.

---

## استكشاف الأخطاء

| المشكلة | السبب المحتمل | الحل |
|---------|---------------|------|
| `ModuleNotFoundError: No module named 'flask'` | Flask غير مُثبّت | `pip install Flask` |
| `ModuleNotFoundError: No module named 'cryptography'` | cryptography غير مُثبّت | `pip install cryptography` أو ثبّت OpenSSL |
| `Address already in use` على المنفذ 8000 أو 5000 | منفذ مُستخدم من تطبيق آخر | أوقف التطبيق الآخر أو غيّر المنفذ في `shared/config.py` |
| فشل اتصال P2P | شهادة SSL غير موجودة | النظام يُولّدها تلقائياً — تأكد من صلاحيات الكتابة على مجلد `certs/` |
| المدير الافتراضي لا يعمل | قاعدة بيانات جديدة | احذف `server_index.db` وأعد تشغيل الخادم ليُعيد إنشاءها مع الحساب الافتراضي |

---

## إعادة توليد ملف Word من التوثيق

إذا عدّلت `academic_documentation.md` وأردت تحديث نسخة Word:

```bash
pip install python-docx
python md_to_docx.py
```

---

## ملخص سريع — من جهاز جديد إلى نظام يعمل

```bash
# 1. استنساخ
git clone https://github.com/bukariconnects-ctrl/D-URS_Project.git
cd D-URS_Project

# 2. بيئة افتراضية (اختياري)
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/macOS

# 3. تثبيت المكتبات
pip install -r requirements.txt

# 4. تشغيل
python server/central_server.py

# 5. فتح المتصفح
# http://127.0.0.1:5000
# admin / admin123
```
