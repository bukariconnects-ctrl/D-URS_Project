# D-URS: نظام مشاركة الموارد الجامعية اللامركزي

## Decentralized University Resource Sharing & Collaboration System

### وثيقة تحليلية شاملة وفق مراحل مقرر الأنظمة الموزعة

---

## جدول المحتويات

1. [المقدمة والأهداف](#1-المقدمة-والأهداف)
2. [المرحلة الأولى: الكيانات والأدوار](#2-المرحلة-الأولى-الكيانات-والأدوار)
3. [المرحلة الثانية: النمط المعماري](#3-المرحلة-الثانية-النمط-المعماري)
4. [المرحلة الثالثة: النماذج الأساسية](#4-المرحلة-الثالثة-النماذج-الأساسية)
5. [المرحلة الرابعة: الاتصال منخفض المستوى](#5-المرحلة-الرابعة-الاتصال-منخفض-المستوى)
6. [المرحلة الخامسة: استدعاء الإجراءات عن بعد RPC](#6-المرحلة-الخامسة-استدعاء-الإجراءات-عن-بعد-rpc)
7. [المرحلة السادسة: الاتصال غير المباشر Pub/Sub](#7-المرحلة-السادسة-الاتصال-غير-المباشر-pubsub)
8. [المرحلة السابعة: خدمات الويب](#8-المرحلة-السابعة-خدمات-الويب)
9. [المرحلة الثامنة: هندسة البيانات](#9-المرحلة-الثامنة-هندسة-البيانات)
10. [المرحلة التاسعة: منطق الند للند والأمن](#10-المرحلة-التاسعة-منطق-الند-للند-والأمن)

---

## 1. المقدمة والأهداف

### 1.1 تعريف بالنظام

**D-URS** (Decentralized University Resource Sharing) هو نظام موزع لمشاركة الموارد الأكاديمية بين طلاب الجامعة. يتيح النظام للطلاب مشاركة الملفات الدراسية (محاضرات، ملخصات، أبحاث) عبر شبكة نظير لنظير (Peer-to-Peer) مع الحفاظ على فهرس مركزي للبحث والاكتشاف.

### 1.2 المشكلة التي يحلها النظام

في البيئة الجامعية، يعاني الطلاب من:
- **تشتت الموارد**: توزع المواد الدراسية عبر منصات متعددة دون نقطة وصول موحدة.
- **غياب التصنيف**: عدم وجود آلية موحدة لتصنيف الملفات حسب المواد أو التخصصات.
- **انعدام الإشعارات**: عدم إخطار الطلاب عند توفر موارد جديدة في مواد يهتمون بها.
- **مشاكل النزاهة**: عدم وجود آلية للتحقق من سلامة الملفات المنقولة.

### 1.3 أهداف النظام

| الهدف | الوصف | التقنية المستخدمة |
|-------|-------|-------------------|
| **الفهرسة المركزية** | توفير نقطة بحث واحدة لجميع الملفات المتاحة | Central Index Server + SQLite |
| **النقل اللامركزي** | نقل الملفات مباشرة بين الطلاب دون تحميل السيرفر | SSL TCP Sockets (P2P) |
| **الإشعارات الفورية** | تنبيه الطلاب عند نشر ملفات في مواضيع مشتركين بها | Pub/Sub Broker |
| **حوكمة المواضيع** | منع التصنيفات العشوائية عبر قائمة مواضيع معتمدة | Topics Table + Admin CRUD |
| **التحقق من النزاهة** | ضمان عدم تلف أو تعديل الملفات أثناء النقل | SHA-256 Integrity Check |
| **التحكم بالوصول** | فصل صلاحيات المدير عن الطالب | RBAC (Role-Based Access Control) |

### 1.4 هيكل المشروع

```
D-URS_Project/
├── server/                      # السيرفر المركزي
│   ├── central_server.py        # نقطة الدخول الرئيسية (RPC + Flask)
│   ├── db_manager.py            # إدارة قاعدة البيانات المركزية
│   ├── web_service.py           # تطبيق Flask الموحد (RBAC)
│   ├── certs/                   # شهادات SSL
│   ├── templates/               # قوالب HTML (admin, student, login, layout)
│   └── static/                  # ملفات CSS
├── peer/                        # عقدة الطالب المستقلة
│   ├── peer_node.py             # عميل RPC + منطق P2P
│   ├── p2p_network.py           # خادم/عميل TCP مع SSL
│   ├── local_db.py              # قاعدة بيانات الطالب المحلية
│   └── web_app.py               # واجهة ويب محلية للطالب
├── shared/                      # مكونات مشتركة
│   ├── config.py                # ثوابت الإعداد (IP, Ports)
│   └── security.py              # دوال SHA-256 وتوليد الرموز
├── storage/                     # تخزين ملفات الأقران الافتراضيين
└── requirements.txt             # المكتبات المطلوبة
```

### 1.5 التقنيات المستخدمة

| التقنية | الإصدار | الدور |
|---------|---------|-------|
| **Python** | 3.10+ | لغة البرمجة الأساسية |
| **Flask** | Latest | إطار عمل الويب |
| **SQLite3** | مدمج مع Python | قاعدة البيانات |
| **XML-RPC** | مدمج مع Python (`xmlrpc`) | استدعاء الإجراءات عن بعد |
| **SSL/TLS** | مدمج مع Python (`ssl`) | تشفير القنوات |
| **Bootstrap 5** | CDN | واجهة المستخدم |
| **cryptography** | Latest | توليد شهادات SSL |

---

## 2. المرحلة الأولى: الكيانات والأدوار

### 2.1 الكيانات الأساسية (Entities)

يتكون النظام من ثلاث كيانات رئيسية موزعة:

#### 2.1.1 السيرفر المركزي (Central Index Server)

هو العقدة المركزية التي تدير الفهرس العام وتنسق عمليات البحث والاشتراك. يعمل على ثلاث طبقات متزامنة:

```
Central Server
├── XML-RPC Server     (Port 8000)  ← واجهة الإجراءات عن بعد
├── Flask Web Service  (Port 5000)  ← واجهة الويب الموحدة
└── Pub/Sub Broker     (داخلي)      ← وسيط الإشعارات
```

**المسؤوليات:**
- تسجيل المستخدمين والمصادقة عليهم
- فهرسة الملفات المشاركة وربطها بمزوديها
- معالجة استعلامات البحث
- إدارة الاشتراكات وتوزيع الإشعارات
- حوكمة المواضيع (إضافة/حذف التصنيفات المعتمدة)
- عرض لوحة تحكم المدير ولوحة الطالب

**التنفيذ في الكود:**

يتم تشغيل السيرفر من `central_server.py` الذي يبدأ خادم XML-RPC وخدمة Flask في خيط منفصل:

```python
def start_server():
    db_manager.init_db()
    threading.Thread(
        target=web_service.start_web_service,
        args=(SERVER_IP, SERVER_WEB_PORT), daemon=True
    ).start()
    server = SimpleXMLRPCServer((SERVER_IP, SERVER_RPC_PORT), allow_none=True)
    server.register_instance(IndexServer())
    server.serve_forever()
```

#### 2.1.2 عقدة الطالب (Student Node / Peer Node)

كل طالب يمثل عقدة مستقلة في الشبكة. في الوضع الموحد (Unified Mode)، يُنشئ السيرفر عقدة افتراضية (Virtual Peer) لكل طالب يسجل دخوله:

```python
virtual_peers = {}  # Maps username -> { 'ip': ..., 'port': ..., 'thread': ... }

def start_virtual_peer(username):
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((SERVER_IP, 0))  # منفذ عشوائي حر
    port = server_socket.getsockname()[1]
    # ... تشغيل الخادم في خيط منفصل
    virtual_peers[username] = {'ip': SERVER_IP, 'port': port, 'thread': t}
```

**المسؤوليات:**
- مشاركة الملفات الدراسية مع تحديد التصنيف
- البحث عن الملفات وتحميلها من أقران آخرين
- الاشتراك بالمواضيع وإلغاء الاشتراك
- استلام الإشعارات عند نشر ملفات جديدة

#### 2.1.3 المدير (Admin)

دور إداري يتحكم في النظام عبر لوحة تحكم مخصصة:

**المسؤوليات:**
- مراقبة المستخدمين والملفات والاشتراكات
- إدارة المواضيع المعتمدة (إضافة/حذف)
- مراقبة العقد النشطة في الشبكة

### 2.2 التوزيع المكاني (Placement)

```
┌──────────────────────────────────────────────────┐
│                 Central Server                    │
│  ┌─────────────┐ ┌──────────┐ ┌───────────────┐  │
│  │  XML-RPC    │ │  Flask   │ │  Pub/Sub      │  │
│  │  Port 8000  │ │ Port 5000│ │  Broker       │  │
│  └──────┬──────┘ └────┬─────┘ └───────┬───────┘  │
│         │             │               │           │
│  ┌──────┴─────────────┴───────────────┴────────┐  │
│  │           SQLite Database                   │  │
│  │    (Users, Files, Subscriptions, Topics,    │  │
│  │     Notifications)                          │  │
│  └─────────────────────────────────────────────┘  │
└──────────────────────┬───────────────────────────┘
                       │ TCP/SSL
        ┌──────────────┼──────────────┐
        │              │              │
  ┌─────┴─────┐  ┌─────┴─────┐  ┌─────┴─────┐
  │ Virtual   │  │ Virtual   │  │ Virtual   │
  │ Peer A    │  │ Peer B    │  │ Peer C    │
  │ Port:Auto │  │ Port:Auto │  │ Port:Auto │
  │ SSL TCP   │  │ SSL TCP   │  │ SSL TCP   │
  └───────────┘  └───────────┘  └───────────┘
     Student A      Student B      Student C
```

في بيئة الإنتاج، يعمل كل طالب على جهاز مستقل باستخدام `peer_node.py`. أما في وضع العرض (Demo)، فيقوم السيرفر بإنشاء عقد افتراضية على منافذ عشوائية حرة باستخدام `socket.bind((SERVER_IP, 0))`.

### 2.3 الأدوار ونظام التحكم بالوصول (RBAC)

يعتمد النظام على نظام التحكم بالوصول المبني على الأدوار:

| الدور | الصلاحيات | مسار الواجهة |
|-------|----------|-------------|
| **admin** | إدارة المواضيع، مراقبة النظام، عرض الإحصائيات | `/admin` |
| **student** | مشاركة الملفات، البحث، التحميل، الاشتراك/إلغاء الاشتراك | `/dashboard` |

التنفيذ عبر مُزخرفات (Decorators) في Flask:

```python
def admin_required(f):
    @functools.wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if session.get('role') != 'admin':
            flash('Access denied. Admin privileges required.', 'danger')
            return redirect(url_for('student_dashboard'))
        return f(*args, **kwargs)
    return decorated
```

---

## 3. المرحلة الثانية: النمط المعماري

### 3.1 النمط الهجين (Hybrid P2P Architecture)

اعتمد نظام D-URS على **النمط الهجين للند للند** (Hybrid Peer-to-Peer) الذي يجمع بين مزايا النموذج المركزي واللامركزي، مستلهمًا من نموذج Napster المحسّن:

```
┌────────────────────────────────────────────────────┐
│                 Centralized Layer                    │
│    (Metadata, Search, Authentication, Pub/Sub)      │
│                                                     │
│  ┌───────────────────────────────────────────────┐  │
│  │         Central Index Server                  │  │
│  │  • فهرس الملفات (Filename, Hash, Provider)   │  │
│  │  • سجل المستخدمين (Authentication)           │  │
│  │  • جدول الاشتراكات (Topic Subscriptions)      │  │
│  │  • المواضيع المعتمدة (Governed Topics)        │  │
│  └───────────────────────────────────────────────┘  │
└────────────────────┬───────────────────────────────┘
                     │ RPC / HTTP
┌────────────────────┴───────────────────────────────┐
│                Decentralized Layer                   │
│           (Actual File Transfer via P2P)             │
│                                                     │
│    Peer A ◄──── SSL TCP ────► Peer B                │
│      │                          │                   │
│      └──── SSL TCP ────► Peer C ┘                   │
└─────────────────────────────────────────────────────┘
```

### 3.2 مبررات اختيار النمط الهجين

**لماذا لم نختر النمط المركزي الكامل (Client-Server)؟**
- سيصبح السيرفر عنق زجاجة (Bottleneck) عند نقل الملفات الكبيرة.
- ضغط كبير على عرض النطاق الترددي (Bandwidth) للسيرفر.
- نقطة فشل واحدة (Single Point of Failure) لعمليات النقل.

**لماذا لم نختر النمط اللامركزي الكامل (Pure P2P)؟**
- صعوبة البحث عن الملفات بدون فهرس مركزي (Flooding-based Search بطيء ومكلف).
- تعقيد إدارة المصادقة والتفويض بشكل لامركزي.
- عدم إمكانية حوكمة المواضيع بشكل مركزي.

**مزايا النمط الهجين المُعتمد:**

| الجانب | المركزي | اللامركزي |
|--------|---------|-----------|
| البحث عن الملفات | ✅ سريع ودقيق عبر الفهرس | |
| المصادقة والتفويض | ✅ موحد ومتسق | |
| حوكمة المواضيع | ✅ مُدار مركزيًا | |
| نقل الملفات | | ✅ مباشر بين الأقران |
| قابلية التوسع | | ✅ الحمل موزع |
| تحمل الأخطاء | | ✅ فشل ند لا يؤثر على الآخرين |

### 3.3 تدفق العمليات في النمط الهجين

**سيناريو: طالب يبحث عن ملف ويحمله**

```
Student A                Central Server              Student B
    │                          │                          │
    │──── (1) POST /search ───►│                          │
    │                          │──── SQL Query ───►       │
    │◄── (2) Results List ─────│                          │
    │   (filename, owner,      │                          │
    │    hash, provider_ip,    │                          │
    │    provider_port)        │                          │
    │                          │                          │
    │──── (3) POST /download ─►│                          │
    │                          │                          │
    │──── (4) SSL TCP Connect ────────────────────────────►│
    │──── (5) Send filename ──────────────────────────────►│
    │◄─── (6) OK:filesize ────────────────────────────────│
    │──── (7) READY ──────────────────────────────────────►│
    │◄─── (8) File chunks (4KB) ──────────────────────────│
    │                          │                          │
    │──── (9) SHA-256 Verify ──│                          │
    │◄── (10) send_file ──────│                          │
    │   (Browser Download)     │                          │
```

### 3.4 الشفافية (Transparency)

يحقق النظام عدة أنواع من الشفافية وفق تصنيف الأنظمة الموزعة:

- **شفافية الوصول (Access Transparency)**: الطالب يتعامل مع واجهة ويب موحدة بغض النظر عن مكان تخزين الملف الفعلي. استدعاءات RPC مخفية خلف واجهة Flask.
- **شفافية الموقع (Location Transparency)**: الطالب يبحث بالاسم فقط، والنظام يحدد عنوان IP والمنفذ الخاص بمزود الملف تلقائيًا.
- **شفافية الفشل (Failure Transparency)**: إذا كان مزود الملف غير متصل، يعرض النظام رسالة خطأ دون كشف التفاصيل التقنية.

---

## 4. المرحلة الثالثة: النماذج الأساسية

### 4.1 نموذج التفاعل (Interaction Model)

يستخدم النظام نمطين من التفاعل:

#### 4.1.1 التفاعل المتزامن (Synchronous) — RPC

عندما يقوم الطالب بالبحث عن ملف أو تسجيل ملف جديد، يتم استخدام **استدعاء إجراء عن بعد متزامن** (Synchronous RPC):

```
Student ──► lookup_file(token, "algorithms") ──► Central Server
Student ◄── {status: "success", results: [...]} ◄── Central Server
```

الطالب ينتظر (Blocking) حتى يحصل على الاستجابة من السيرفر. هذا مناسب لأن:
- عمليات البحث سريعة (استعلام SQL بسيط).
- الطالب يحتاج النتائج فورًا لاتخاذ قرار (أي ملف يحمّل).

**التنفيذ:**

```python
# في peer_node.py - استدعاء متزامن
def search_for_file(self, filename):
    response = self.server.lookup_file(self.token, filename)  # Blocking
    return response
```

#### 4.1.2 التفاعل غير المتزامن (Asynchronous) — Pub/Sub

عند نشر ملف جديد، يتم إرسال الإشعارات للمشتركين بشكل **غير متزامن** في خيط منفصل:

```python
# في web_service.py - إشعار غير متزامن
threading.Thread(
    target=publish_notification_to_subscribers,
    args=(topic, msg, username),
    daemon=True
).start()
```

هذا مناسب لأن:
- الناشر لا يحتاج انتظار تأكيد وصول الإشعار.
- بعض المشتركين قد يكونون غير متصلين.
- لا يجب أن يتأخر رد مشاركة الملف بسبب الإشعارات.

### 4.2 نموذج الفشل (Failure Model)

#### 4.2.1 أنواع الفشل المحتملة وطرق التعامل معها

| نوع الفشل | الوصف | آلية المعالجة |
|-----------|-------|---------------|
| **Crash Failure** | توقف عقدة طالب بشكل مفاجئ | خيوط `daemon=True` تنتهي تلقائيًا |
| **Omission Failure** | عدم استجابة مزود الملف | `socket.settimeout(3)` مع استثناء |
| **Network Partition** | انقطاع الاتصال أثناء النقل | التحقق من `received < file_size` |
| **Byzantine Failure** | تلاعب بمحتوى الملف | SHA-256 Integrity Verification |

#### 4.2.2 التعامل مع انقطاع العقد (Timeout/Retry)

عند محاولة إرسال إشعار لعقدة غير متصلة:

```python
# في central_server.py
def publish_notification(topic, message):
    subscribers = db_manager.get_subscribers(topic)
    for peer_ip, peer_port in subscribers:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)  # مهلة 3 ثوانٍ
            sock.connect((peer_ip, int(peer_port)))
            sock.sendall(message.encode('utf-8'))
            sock.close()
        except Exception:
            pass  # تجاهل العقد غير المتصلة
```

في الوضع الموحد (Unified Mode)، يتم تخزين الإشعارات في قاعدة البيانات بدلًا من الإرسال المباشر عبر TCP، مما يضمن عدم فقدان أي إشعار:

```python
# في web_service.py
def publish_notification_to_subscribers(topic, message, exclude_user=None):
    subs = db_manager.get_all_subscriptions()
    for s in subs:
        subscriber = s['peer_ip']
        if subscriber != exclude_user and s['topic'] == topic:
            db_manager.add_notification(subscriber, message)  # تخزين دائم
```

#### 4.2.3 التعامل مع فشل التحميل

عند فشل نقل الملف عبر P2P:

```python
def _p2p_download(provider_ip, provider_port, filename, expected_hash, save_dir):
    try:
        conn.connect((provider_ip, int(provider_port)))
        # ... نقل الملف ...
        actual_hash = hash_file(save_path)
        if actual_hash == expected_hash:
            return True
        else:
            os.remove(save_path)  # حذف الملف التالف
            return False
    except Exception as e:
        return False  # إبلاغ المستخدم بالفشل
```

### 4.3 نموذج الحماية (Security Model)

#### 4.3.1 التهديدات المحتملة

| التهديد | الوصف | مستوى الخطورة |
|---------|-------|---------------|
| **Man-in-the-Middle (MITM)** | اعتراض البيانات أثناء النقل | عالي |
| **Data Tampering** | تعديل محتوى الملفات أثناء النقل | عالي |
| **Unauthorized Access** | وصول غير مصرح به للموارد | متوسط |
| **Replay Attack** | إعادة استخدام رموز الجلسة | متوسط |
| **Topic Spoofing** | إنشاء تصنيفات مزيفة | منخفض |

#### 4.3.2 آليات الحماية المنفذة

| التهديد | الحل المنفذ | الموقع في الكود |
|---------|------------|----------------|
| MITM | تشفير SSL/TLS لجميع قنوات P2P | `p2p_network.py`, `web_service.py` |
| Data Tampering | تحقق SHA-256 بعد كل عملية نقل | `_p2p_download()`, `download_file()` |
| Unauthorized Access | مصادقة بالرمز + RBAC | `db_manager.verify_token()`, Decorators |
| Replay Attack | رموز جلسة عشوائية فريدة | `secrets.token_hex(16)` |
| Topic Spoofing | حوكمة المواضيع (قائمة معتمدة فقط) | `validate_topic()`, Admin-only CRUD |

---

## 5. المرحلة الرابعة: الاتصال منخفض المستوى

### 5.1 استخدام TCP Sockets

اختار النظام بروتوكول **TCP** (Transmission Control Protocol) لنقل الملفات بين الأقران للأسباب التالية:

| المعيار | TCP | UDP |
|---------|-----|-----|
| **الموثوقية** | ✅ مضمون (Reliable) | ❌ غير مضمون |
| **الترتيب** | ✅ مرتب (Ordered) | ❌ غير مرتب |
| **التحكم بالتدفق** | ✅ مدمج | ❌ يدوي |
| **مناسب لنقل الملفات** | ✅ نعم | ❌ لا |

**لماذا TCP وليس UDP؟**

نقل الملفات الأكاديمية يتطلب **موثوقية تامة** — فقدان حزمة واحدة من ملف PDF يعني تلف الملف بالكامل. لذلك، TCP هو الخيار الطبيعي لأنه يضمن وصول جميع الحزم بالترتيب الصحيح مع إعادة الإرسال التلقائية عند الفقدان.

### 5.2 بروتوكول النقل المخصص

صمم النظام بروتوكول تطبيقي بسيط فوق TCP:

```
المرحلة 1: الطلب
    Client ──► "algorithms.pdf"  (اسم الملف)

المرحلة 2: الاستجابة الأولية
    Server ──► "OK:1048576"      (حالة:حجم بالبايت)
    أو
    Server ──► "ERROR: File not found"

المرحلة 3: التأكيد
    Client ──► "READY"

المرحلة 4: نقل البيانات
    Server ──► [chunk 4KB] [chunk 4KB] ... [last chunk]
```

**التنفيذ على جانب الخادم:**

```python
def _handle_p2p_client(conn, addr, username):
    filename = conn.recv(1024).decode('utf-8').strip()
    file_path = os.path.join(user_dir, filename)
    if not os.path.exists(file_path):
        conn.sendall(b'ERROR: File not found')
        conn.close()
        return
    file_size = os.path.getsize(file_path)
    conn.sendall(f'OK:{file_size}'.encode('utf-8'))
    ack = conn.recv(16)  # انتظار READY
    with open(file_path, 'rb') as f:
        while True:
            chunk = f.read(4096)  # CHUNK_SIZE = 4096
            if not chunk:
                break
            conn.sendall(chunk)
```

**التنفيذ على جانب العميل:**

```python
def _p2p_download(provider_ip, provider_port, filename, expected_hash, save_dir):
    conn.connect((provider_ip, int(provider_port)))
    conn.sendall(filename.encode('utf-8'))
    header = conn.recv(1024).decode('utf-8')
    file_size = int(header.split(':')[1])
    conn.sendall(b'READY')
    received = 0
    with open(save_path, 'wb') as f:
        while received < file_size:
            chunk = conn.recv(CHUNK_SIZE)
            if not chunk:
                break
            f.write(chunk)
            received += len(chunk)
```

### 5.3 تغليف القنوات بـ SSL/TLS

جميع اتصالات TCP مغلفة بطبقة **SSL/TLS** لتشفير البيانات أثناء النقل:

**على جانب الخادم (Server-side SSL):**

```python
ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ssl_context.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((SERVER_IP, 0))
server_socket.listen(5)
ssl_socket = ssl_context.wrap_socket(server_socket, server_side=True)
```

**على جانب العميل (Client-side SSL):**

```python
ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE  # شهادة ذاتية التوقيع
raw_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
conn = ssl_context.wrap_socket(raw_socket)
conn.connect((provider_ip, int(provider_port)))
```

**لماذا شهادات ذاتية التوقيع (Self-Signed)?**

في بيئة جامعية محلية، لا حاجة لسلطة شهادات خارجية (CA). الهدف هو **تشفير القناة** وليس التحقق من هوية الخادم عبر طرف ثالث. يتم توليد الشهادة تلقائيًا باستخدام مكتبة `cryptography`:

```python
key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
cert = (
    x509.CertificateBuilder()
    .subject_name(x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, u"D-URS Server"),
    ]))
    .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365))
    .sign(key, hashes.SHA256())
)
```

---

## 6. المرحلة الخامسة: استدعاء الإجراءات عن بعد (RPC)

### 6.1 نظرة عامة على XML-RPC

يستخدم النظام **XML-RPC** (XML Remote Procedure Call) كآلية للاتصال بين عقد الطلاب والسيرفر المركزي. XML-RPC هو بروتوكول بسيط يستخدم HTTP كطبقة نقل و XML لتشفير البيانات.

**لماذا XML-RPC؟**
- **مدمج مع Python**: مكتبة `xmlrpc` جزء من المكتبة القياسية — لا حاجة لتثبيت مكتبات إضافية.
- **بسيط وشفاف**: الاستدعاء يبدو كاستدعاء دالة محلية (Access Transparency).
- **متعدد اللغات**: يمكن لعملاء بلغات أخرى الاتصال بالسيرفر.
- **مبني على HTTP**: يمر عبر جدران الحماية بسهولة.

### 6.2 الإجراءات المسجلة (Exposed Methods)

```python
class IndexServer:
    def register_user(self, username, password_hash)
    def login(self, username, password_hash)
    def register_file(self, token, filename, file_hash,
                      provider_ip, provider_port, topic)
    def subscribe(self, token, topic, peer_ip, notify_port)
    def lookup_file(self, token, filename)
```

### 6.3 تفصيل كل إجراء

#### 6.3.1 `register_user(username, password_hash)`

يسجل مستخدمًا جديدًا في قاعدة البيانات المركزية.

| المعامل | النوع | الوصف |
|---------|------|-------|
| `username` | string | اسم المستخدم (فريد) |
| `password_hash` | string | بصمة SHA-256 لكلمة المرور |

**الاستجابة:**
```python
{"status": "success", "message": "User 'ahmed' registered."}
# أو
{"status": "error", "message": "Username 'ahmed' already exists."}
```

#### 6.3.2 `login(username, password_hash)`

يتحقق من بيانات الاعتماد ويولّد رمز جلسة (Session Token).

**الاستجابة:**
```python
{"status": "success", "token": "a3f8c9d2e1b0..."}  # رمز عشوائي 32 حرف
# أو
{"status": "error", "message": "Invalid username or password."}
```

#### 6.3.3 `register_file(token, filename, file_hash, provider_ip, provider_port, topic)`

يسجل ملفًا مشاركًا في الفهرس المركزي. يتطلب رمز جلسة صالح.

**السلوك الإضافي:** بعد التسجيل الناجح، يتم إطلاق إشعار غير متزامن لجميع المشتركين في الموضوع:

```python
def register_file(self, token, filename, file_hash, provider_ip, provider_port, topic):
    db_manager.add_file(token, filename, file_hash, provider_ip, provider_port, topic)
    if topic:
        msg = f"New file '{filename}' available in topic '{topic}'!"
        threading.Thread(
            target=publish_notification, args=(topic, msg), daemon=True
        ).start()
    return {"status": "success", "message": f"File '{filename}' registered."}
```

#### 6.3.4 `lookup_file(token, filename)`

يبحث في الفهرس عن الملفات المطابقة باستخدام بحث جزئي (`LIKE %query%`):

```python
cursor.execute(
    'SELECT filename, file_hash, owner, provider_ip, provider_port, topic '
    'FROM Files WHERE filename LIKE ?',
    (f'%{filename}%',)
)
```

### 6.4 شفافية الوصول (Access Transparency)

من جانب العميل، يبدو استدعاء RPC كاستدعاء دالة محلية عادية:

```python
# في peer_node.py
class PeerNode:
    def __init__(self):
        self.server = ServerProxy(f'http://{SERVER_IP}:{SERVER_RPC_PORT}')

    def search_for_file(self, filename):
        # يبدو كاستدعاء محلي، لكنه في الحقيقة يرسل طلب HTTP إلى السيرفر
        response = self.server.lookup_file(self.token, filename)
        return response
```

الطالب لا يعرف أن الدالة `lookup_file` تُنفَّذ على جهاز آخر — هذه هي **شفافية الوصول**.

### 6.5 تسلسل التفاعل في RPC

```
PeerNode                     Network                   IndexServer
    │                            │                          │
    │── lookup_file(token, "x") ─│                          │
    │                            │── HTTP POST /RPC2 ──────►│
    │                            │   <?xml ...>             │
    │                            │   <methodCall>           │
    │                            │     <methodName>         │
    │                            │      lookup_file         │
    │                            │     </methodName>        │
    │                            │     <params>...</params> │
    │                            │   </methodCall>          │
    │                            │                          │
    │                            │   db_manager.search_file()
    │                            │                          │
    │                            │◄── HTTP 200 ────────────│
    │                            │   <?xml ...>             │
    │                            │   <methodResponse>       │
    │                            │     <params>...</params> │
    │                            │   </methodResponse>      │
    │                            │                          │
    │◄── {results: [...]} ───────│                          │
```

---

## 7. المرحلة السادسة: الاتصال غير المباشر (Pub/Sub)

### 7.1 نمط النشر/الاشتراك (Publish-Subscribe)

يستخدم النظام نمط **Pub/Sub** لإخطار الطلاب عند توفر ملفات جديدة في المواضيع التي اشتركوا بها. السيرفر المركزي يعمل كـ **وسيط (Broker)** بين الناشرين والمشتركين.

### 7.2 لماذا Pub/Sub وليس الاستعلام الدوري (Polling)؟

| المعيار | Pub/Sub | Polling |
|---------|---------|---------|
| **الكفاءة** | ✅ إشعار فقط عند وجود جديد | ❌ استعلامات متكررة بلا فائدة |
| **الفورية** | ✅ فوري | ❌ تأخير حسب فترة الاستعلام |
| **حمل الشبكة** | ✅ منخفض | ❌ عالي (طلبات مستمرة) |
| **الفصل بين المكونات** | ✅ الناشر لا يعرف المشتركين | ❌ مقترن (Coupled) |

### 7.3 التصفية بالموضوع (Topic-Based Filtering)

يعتمد النظام على **التصفية بالموضوع** حيث يشترك الطالب في تصنيف معين (مثل "Algorithms" أو "Databases") ويتلقى إشعارات فقط عن الملفات المنشورة في هذا التصنيف:

```
                    ┌──────────────────┐
                    │   Pub/Sub Broker │
                    │  (Central Server)│
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
      Topic: Algorithms  Topic: DB    Topic: Networks
              │              │              │
        ┌─────┴──┐      ┌───┴───┐      ┌───┴───┐
        │Student A│     │Student B│     │Student C│
        │Student C│     │Student A│     │        │
        └────────┘      └────────┘      └────────┘
```

### 7.4 دورة حياة الاشتراك

#### 7.4.1 الاشتراك (Subscribe)

```python
@app.route('/subscribe', methods=['POST'])
@student_required
def subscribe():
    username = session['username']
    topic = request.form.get('topic', '').strip()
    # التحقق من صلاحية الموضوع (حوكمة)
    if not db_manager.validate_topic(topic):
        flash(f"Invalid topic '{topic}'. Please select an approved topic.", 'danger')
        return redirect(url_for('student_dashboard'))
    db_manager.add_subscription_by_user(username, topic)
    flash(f"Subscribed to '{topic}'!", 'success')
    return redirect(url_for('student_dashboard'))
```

#### 7.4.2 إلغاء الاشتراك (Unsubscribe)

```python
@app.route('/unsubscribe', methods=['POST'])
@student_required
def unsubscribe():
    username = session['username']
    topic = request.form.get('topic', '').strip()
    db_manager.remove_subscription_by_user(username, topic)
    flash(f"Unsubscribed from '{topic}'.", 'success')
    return redirect(url_for('student_dashboard'))
```

#### 7.4.3 النشر والإشعار (Publish & Notify)

عند مشاركة ملف جديد، يتم إنشاء إشعار لكل مشترك في الموضوع:

```python
# عند مشاركة ملف في web_service.py
msg = f"New file '{uploaded.filename}' shared by {username} in topic '{topic}'!"
threading.Thread(
    target=publish_notification_to_subscribers,
    args=(topic, msg, username),
    daemon=True
).start()
```

```python
def publish_notification_to_subscribers(topic, message, exclude_user=None):
    subs = db_manager.get_all_subscriptions()
    notified = set()
    for s in subs:
        subscriber = s['peer_ip']
        if subscriber != exclude_user and subscriber not in notified:
            if s['topic'] == topic:
                db_manager.add_notification(subscriber, message)
                notified.add(subscriber)
```

**ملاحظة:** يتم استبعاد الناشر نفسه (`exclude_user`) من قائمة الإشعارات لتجنب تلقيه إشعارًا عن ملفه الخاص.

### 7.5 حوكمة المواضيع (Topic Governance)

لمنع التصنيفات العشوائية وضمان اتساق النظام، تم تطبيق نظام حوكمة حيث:

1. **المدير فقط** يستطيع إنشاء أو حذف المواضيع.
2. واجهة الطالب تعرض **قوائم منسدلة** بدلًا من حقول نصية حرة.
3. **التحقق على مستوى الخادم** يرفض أي موضوع غير معتمد:

```python
def validate_topic(topic_name):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM Topics WHERE name = ?', (topic_name,))
    row = cursor.fetchone()
    conn.close()
    return row is not None
```

### 7.6 استلام الإشعارات (Notification Polling)

في واجهة الويب، يتم جلب الإشعارات دوريًا عبر AJAX:

```javascript
function pollNotifications() {
    fetch('/api/notifications')
        .then(r => r.json())
        .then(data => {
            const container = document.getElementById('notifications');
            countBadge.textContent = data.length;
            if (data.length > 0) {
                let html = '';
                data.forEach(n => {
                    html += '<div class="notification-item">'
                          + n.message + '</div>';
                });
                container.innerHTML = html;
            }
        });
}
setInterval(pollNotifications, 3000);  // كل 3 ثوانٍ
```

---

## 8. المرحلة السابعة: خدمات الويب

### 8.1 واجهة REST API

يوفر النظام واجهة **REST API** مبنية بإطار Flask تعمل على المنفذ 5000:

#### 8.1.1 نقاط النهاية العامة (API Endpoints)

| الطريقة | المسار | الوصف | المصادقة |
|---------|--------|-------|---------|
| `GET` | `/api/users` | جلب قائمة المستخدمين | لا |
| `GET` | `/api/files` | جلب قائمة الملفات المفهرسة | لا |
| `GET` | `/api/notifications` | جلب إشعارات المستخدم الحالي | نعم (جلسة) |

```python
@app.route('/api/users', methods=['GET'])
def api_users():
    return jsonify(db_manager.get_all_users())

@app.route('/api/files', methods=['GET'])
def api_files():
    return jsonify(db_manager.get_all_files())

@app.route('/api/notifications')
@login_required
def api_notifications():
    username = session['username']
    notifs = db_manager.get_notifications(username)
    return jsonify(notifs)
```

#### 8.1.2 نقاط النهاية الوظيفية (Functional Routes)

| الطريقة | المسار | الوصف | الدور المطلوب |
|---------|--------|-------|-------------|
| `GET/POST` | `/login` | تسجيل الدخول / إنشاء حساب | عام |
| `GET` | `/logout` | تسجيل الخروج | مسجل دخوله |
| `GET` | `/admin` | لوحة تحكم المدير | admin |
| `POST` | `/admin/add_topic` | إضافة موضوع معتمد | admin |
| `POST` | `/admin/delete_topic` | حذف موضوع | admin |
| `GET` | `/dashboard` | لوحة الطالب | student |
| `POST` | `/share` | مشاركة ملف | student |
| `POST` | `/subscribe` | الاشتراك بموضوع | student |
| `POST` | `/unsubscribe` | إلغاء الاشتراك | student |
| `POST` | `/search` | البحث عن ملفات | student |
| `POST` | `/download` | تحميل ملف (P2P + Browser) | student |

### 8.2 لوحة تحكم المدير (Admin Dashboard)

تعرض لوحة التحكم الإدارية:

- **إحصائيات عامة**: عدد المستخدمين، الملفات، الاشتراكات، العقد النشطة.
- **جدول المستخدمين**: ID، اسم المستخدم، الدور.
- **جدول الملفات**: اسم الملف، البصمة، المالك، عنوان المزود، الموضوع.
- **إدارة المواضيع**: نموذج إضافة موضوع جديد، جدول المواضيع مع زر حذف.
- **العقد النشطة**: العقد الافتراضية المتصلة حاليًا.

### 8.3 لوحة الطالب (Student Dashboard)

تعرض لوحة الطالب:

- **مشاركة ملف**: رفع ملف مع اختيار موضوع من القائمة المعتمدة.
- **إدارة الاشتراكات**: الاشتراك بمواضيع جديدة، إلغاء الاشتراك (زر × على الشارة).
- **ملفاتي المشاركة**: قائمة الملفات التي شاركها الطالب.
- **الإشعارات**: إشعارات حية تُحدَّث كل 3 ثوانٍ.
- **البحث**: البحث عن ملفات في الشبكة.
- **اشتراكاتي**: عرض الملفات المنشورة ضمن المواضيع المشترك بها.
- **الملفات المتاحة**: جميع الملفات على الشبكة مع إمكانية التحميل.

### 8.4 عملية التحميل (Browser-Native Download)

يتم التحميل عبر تدفق ثنائي المراحل:

1. **المرحلة الأولى**: نقل P2P مؤقت — يحمّل الملف من مزوده عبر SSL TCP إلى مجلد مؤقت على السيرفر.
2. **المرحلة الثانية**: إرسال للمتصفح — يُرسل الملف للمتصفح كمرفق تنزيل حقيقي باستخدام `send_file`.

```python
@app.route('/download', methods=['POST'])
@student_required
def download():
    provider = virtual_peers[owner]
    temp_dir = tempfile.mkdtemp()
    success = _p2p_download(
        provider['ip'], provider['port'],
        filename, file_hash, temp_dir
    )
    if success:
        file_path = os.path.join(temp_dir, filename)
        return send_file(file_path, as_attachment=True, download_name=filename)
```

بهذا، يرى الطالب حوار التحميل المعتاد في المتصفح، تمامًا كتحميل أي ملف من الإنترنت.

---

## 9. المرحلة الثامنة: هندسة البيانات

### 9.1 استراتيجية التخزين

يعتمد النظام على **SQLite** كقاعدة بيانات لسببين:
- **خفيفة الوزن**: لا تحتاج خادم قاعدة بيانات منفصل.
- **ذاتية الاحتواء**: ملف واحد `.db` يسهل نقله ونسخه احتياطيًا.

### 9.2 قاعدة البيانات المركزية (Central Index)

**الموقع:** `server/server_index.db`

تحتوي على خمسة جداول:

#### 9.2.1 جدول المستخدمين (Users)

```sql
CREATE TABLE Users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'student',
    session_token TEXT
);
```

| العمود | النوع | الوصف |
|--------|------|-------|
| `id` | INTEGER | معرف فريد تلقائي |
| `username` | TEXT (UNIQUE) | اسم المستخدم |
| `password_hash` | TEXT | بصمة SHA-256 لكلمة المرور |
| `role` | TEXT | الدور (`admin` / `student`) |
| `session_token` | TEXT | رمز الجلسة الحالي (nullable) |

**ملاحظة أمنية:** لا تُخزَّن كلمات المرور بشكل نصي (Plain Text) أبدًا — تُخزَّن فقط بصمات SHA-256.

#### 9.2.2 جدول الملفات (Files)

```sql
CREATE TABLE Files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    owner TEXT NOT NULL DEFAULT '',
    provider_ip TEXT NOT NULL,
    provider_port INTEGER NOT NULL,
    topic TEXT
);
```

| العمود | النوع | الوصف |
|--------|------|-------|
| `filename` | TEXT | اسم الملف |
| `file_hash` | TEXT | بصمة SHA-256 للمحتوى |
| `owner` | TEXT | اسم المستخدم المالك |
| `provider_ip` | TEXT | عنوان IP لعقدة المزود |
| `provider_port` | INTEGER | منفذ TCP لعقدة المزود |
| `topic` | TEXT | تصنيف الملف |

**قرار معماري:** يُخزَّن عنوان IP والمنفذ مع كل ملف لأن العقد الافتراضية تحصل على منافذ عشوائية عند كل تشغيل. هذا يتيح للنظام توجيه طلبات التحميل مباشرة.

#### 9.2.3 جدول الاشتراكات (Subscriptions)

```sql
CREATE TABLE Subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    peer_ip TEXT NOT NULL,
    peer_port INTEGER NOT NULL,
    topic TEXT NOT NULL
);
```

في الوضع الموحد، يُستخدم حقل `peer_ip` لتخزين **اسم المستخدم** بدلًا من عنوان IP:

```python
def add_subscription_by_user(username, topic):
    # Avoid duplicates
    cursor.execute(
        'SELECT id FROM Subscriptions WHERE peer_ip = ? AND topic = ?',
        (username, topic)
    )
    if cursor.fetchone() is None:
        cursor.execute(
            'INSERT INTO Subscriptions (peer_ip, peer_port, topic) VALUES (?, ?, ?)',
            (username, 0, topic)  # port = 0 في الوضع الموحد
        )
```

#### 9.2.4 جدول الإشعارات (Notifications)

```sql
CREATE TABLE Notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

يُخزّن الإشعارات بشكل دائم مع طابع زمني تلقائي. تُعرض مرتبة من الأحدث إلى الأقدم:

```python
cursor.execute(
    'SELECT id, message, created_at FROM Notifications '
    'WHERE username = ? ORDER BY id DESC',
    (username,)
)
```

#### 9.2.5 جدول المواضيع (Topics)

```sql
CREATE TABLE Topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT ''
);
```

| العمود | النوع | الوصف |
|--------|------|-------|
| `name` | TEXT (UNIQUE) | اسم الموضوع (فريد) |
| `description` | TEXT | وصف اختياري |

هذا الجدول يمثل **حجر الأساس لحوكمة المواضيع** — أي موضوع لم يُضف بواسطة المدير لن يُقبل في النظام.

### 9.3 قاعدة البيانات المحلية (Peer Local DB)

**الموقع:** `peer/peer_local.db`

في وضع العقد المستقلة، كل طالب يملك قاعدة بيانات محلية تتتبع ملفاته المشاركة:

```sql
CREATE TABLE MyFiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    file_path TEXT NOT NULL
);
```

| العمود | الوصف |
|--------|-------|
| `filename` | اسم الملف كما يظهر على الشبكة |
| `file_hash` | بصمة SHA-256 |
| `file_path` | المسار المطلق على جهاز الطالب |

هذا الفصل بين القاعدة المركزية والمحلية يحقق مبدأ **استقلالية البيانات** في الأنظمة الموزعة — كل عقدة تعرف فقط ما تحتاج معرفته.

### 9.4 مخطط العلاقات (ER Diagram)

```
┌──────────────┐       ┌──────────────────┐       ┌──────────────┐
│    Users     │       │      Files       │       │    Topics    │
├──────────────┤       ├──────────────────┤       ├──────────────┤
│ id (PK)      │       │ id (PK)          │       │ id (PK)      │
│ username (UQ)│──┐    │ filename         │    ┌──│ name (UQ)    │
│ password_hash│  │    │ file_hash        │    │  │ description  │
│ role         │  ├───►│ owner (FK→Users) │    │  └──────────────┘
│ session_token│  │    │ provider_ip      │    │
└──────────────┘  │    │ provider_port    │    │
                  │    │ topic (FK→Topics)│────┘
                  │    └──────────────────┘
                  │
                  │    ┌──────────────────┐
                  │    │  Subscriptions   │
                  │    ├──────────────────┤
                  │    │ id (PK)          │
                  └───►│ peer_ip (→User)  │
                       │ peer_port        │
                       │ topic (→Topics)  │
                       └──────────────────┘

                       ┌──────────────────┐
                       │  Notifications   │
                       ├──────────────────┤
                       │ id (PK)          │
                  ┌───►│ username (→User) │
                  │    │ message          │
                  │    │ created_at       │
                  │    └──────────────────┘
```

---

## 10. المرحلة التاسعة: منطق الند للند والأمن

### 10.1 عملية نقل الملفات P2P

#### 10.1.1 التدفق الكامل

```
[1] الطالب يضغط "Download"
         │
         ▼
[2] Flask يستقبل POST /download
    (filename, owner, file_hash)
         │
         ▼
[3] البحث عن العقدة الافتراضية للمالك
    provider = virtual_peers[owner]
         │
         ▼
[4] إنشاء مجلد مؤقت
    temp_dir = tempfile.mkdtemp()
         │
         ▼
[5] اتصال SSL TCP بعقدة المزود
    conn.connect((provider_ip, provider_port))
         │
         ▼
[6] إرسال اسم الملف المطلوب
    conn.sendall(filename.encode())
         │
         ▼
[7] استقبال الحجم → إرسال READY → استقبال البيانات
    (chunks of 4096 bytes)
         │
         ▼
[8] التحقق من النزاهة بـ SHA-256
    actual_hash == expected_hash ?
         │
    ┌────┴────┐
    ▼         ▼
  [نجاح]   [فشل]
    │         │
    ▼         ▼
 send_file  حذف الملف
 (تحميل     + رسالة
  للمتصفح)   خطأ
```

#### 10.1.2 الجانب الخادم (Virtual Peer Server)

كل عقدة افتراضية تشغل خادم SSL TCP يستمع على منفذ عشوائي:

```python
def _handle_p2p_client(conn, addr, username):
    filename = conn.recv(1024).decode('utf-8').strip()
    user_dir = os.path.join(STORAGE_DIR, username)
    file_path = os.path.join(user_dir, filename)

    if not os.path.exists(file_path):
        conn.sendall(b'ERROR: File not found')
        conn.close()
        return

    file_size = os.path.getsize(file_path)
    conn.sendall(f'OK:{file_size}'.encode('utf-8'))
    ack = conn.recv(16)  # READY

    with open(file_path, 'rb') as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            conn.sendall(chunk)
```

#### 10.1.3 الجانب العميل (P2P Download)

```python
def _p2p_download(provider_ip, provider_port, filename, expected_hash, save_dir):
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    raw_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    conn = ssl_context.wrap_socket(raw_socket)

    conn.connect((provider_ip, int(provider_port)))
    conn.sendall(filename.encode('utf-8'))

    header = conn.recv(1024).decode('utf-8')
    if header.startswith('ERROR'):
        return False

    file_size = int(header.split(':')[1])
    conn.sendall(b'READY')

    received = 0
    with open(save_path, 'wb') as f:
        while received < file_size:
            chunk = conn.recv(CHUNK_SIZE)
            if not chunk:
                break
            f.write(chunk)
            received += len(chunk)

    # التحقق من النزاهة
    actual_hash = hash_file(save_path)
    if actual_hash == expected_hash:
        return True
    else:
        os.remove(save_path)  # حذف الملف التالف
        return False
```

### 10.2 التحقق من النزاهة (Integrity Verification)

#### 10.2.1 خوارزمية SHA-256

يستخدم النظام خوارزمية **SHA-256** (Secure Hash Algorithm 256-bit) لإنشاء بصمة رقمية فريدة لكل ملف:

```python
def hash_file(file_path: str) -> str:
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()
```

**الخصائص الأمنية لـ SHA-256:**
- **مقاومة الاصطدام**: احتمال أن ينتج ملفان مختلفان نفس البصمة ≈ 0.
- **أحادية الاتجاه**: لا يمكن استعادة المحتوى الأصلي من البصمة.
- **حساسية عالية**: تغيير بت واحد في الملف يغير البصمة بالكامل.

#### 10.2.2 تدفق التحقق

```
عند المشاركة (Share):
    hash_original = SHA-256(file)  ──► يُخزن في Files table

عند التحميل (Download):
    file_data ← P2P Transfer
    hash_received = SHA-256(file_data)

    if hash_received == hash_original:
        ✅ الملف سليم → تسليم للمتصفح
    else:
        ❌ الملف تالف/معدّل → حذف + رسالة خطأ
```

### 10.3 نظام المصادقة والرموز (Token-Based Authentication)

#### 10.3.1 تدفق المصادقة

```
[1] الطالب يدخل اسم المستخدم + كلمة المرور
         │
         ▼
[2] تحويل كلمة المرور إلى بصمة SHA-256
    password_hash = hashlib.sha256(password).hexdigest()
         │
         ▼
[3] مقارنة البصمة مع المخزنة في قاعدة البيانات
    SELECT id FROM Users
    WHERE username = ? AND password_hash = ?
         │
         ▼
[4] توليد رمز جلسة عشوائي
    token = secrets.token_hex(16)  # 32 حرف hex
         │
         ▼
[5] تخزين الرمز في الجلسة + قاعدة البيانات
    session['token'] = token
    UPDATE Users SET session_token = ? WHERE id = ?
```

#### 10.3.2 التحقق من الرمز

كل عملية حساسة عبر RPC تتطلب رمز جلسة صالح:

```python
def verify_token(token):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT id FROM Users WHERE session_token = ?',
        (token,)
    )
    user = cursor.fetchone()
    conn.close()
    return user is not None
```

#### 10.3.3 توليد الرموز الآمنة

```python
import secrets

def generate_token() -> str:
    return secrets.token_hex(16)
    # مثال: "a3f8c9d2e1b04f7a8c3d9e2f1a0b5c6d"
```

تستخدم مكتبة `secrets` مولّد أرقام عشوائية **آمن تشفيريًا** (CSPRNG) بدلًا من `random` الذي يمكن التنبؤ بسلسلته.

### 10.4 ملخص آليات الأمن

```
┌─────────────────────────────────────────────────────────┐
│                    Security Layers                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Layer 1: Authentication                                │
│  ├── SHA-256 Password Hashing                           │
│  ├── Secure Random Session Tokens (secrets.token_hex)   │
│  └── Role-Based Access Control (admin / student)        │
│                                                         │
│  Layer 2: Transport Security                            │
│  ├── SSL/TLS Encryption for P2P Sockets                 │
│  └── Self-Signed X.509 Certificates (RSA 2048-bit)      │
│                                                         │
│  Layer 3: Data Integrity                                │
│  ├── SHA-256 File Hashing at Share time                  │
│  └── SHA-256 Verification at Download time               │
│                                                         │
│  Layer 4: Governance                                    │
│  ├── Admin-controlled Topic Management                   │
│  ├── Server-side Topic Validation                        │
│  └── UI-enforced Dropdown Selection (no free text)       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## الخلاصة

نظام **D-URS** يمثل تطبيقًا عمليًا شاملًا لمفاهيم الأنظمة الموزعة، حيث تم دمج:

| المفهوم | التطبيق في D-URS |
|---------|-----------------|
| **الكيانات والأدوار** | Central Server + Virtual Peers + RBAC |
| **النمط المعماري** | Hybrid P2P (مركزي للبحث + لامركزي للنقل) |
| **نماذج التفاعل** | RPC متزامن + Pub/Sub غير متزامن |
| **نموذج الفشل** | Timeout + Graceful Degradation + Stored Notifications |
| **نموذج الحماية** | SSL + SHA-256 + Tokens + RBAC + Topic Governance |
| **الاتصال منخفض المستوى** | TCP Sockets مغلفة بـ SSL/TLS |
| **RPC** | XML-RPC مع شفافية الوصول |
| **Pub/Sub** | Topic-Based Filtering مع حوكمة مركزية |
| **خدمات الويب** | Flask REST API + Admin/Student Dashboards |
| **هندسة البيانات** | SQLite مركزي (5 جداول) + SQLite محلي (1 جدول) |
| **P2P والأمن** | SSL TCP Transfer + SHA-256 Integrity + Token Auth |

النظام جاهز للعمل في بيئة جامعية حقيقية مع إمكانية التوسع لدعم مزيد من العقد والمواضيع والملفات.

---

> **D-URS** — Decentralized University Resource Sharing & Collaboration System
> تم التطوير كمشروع تطبيقي لمقرر الأنظمة الموزعة

