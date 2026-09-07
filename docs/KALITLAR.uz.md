# Payme kalitlarini qayerdan olish kerak

Bu kutubxona ishlashi uchun `.env` faylida 4 ta qiymat kerak:

| O'zgaruvchi | Bu nima | Qayerdan olinadi |
|---|---|---|
| `PAYME_TOKEN` | Kassa ID (Merchant ID) — 24 ta belgidan iborat hex, masalan `100fe486b33784292111b7dc` | Payme Business kabineti → «Кассы» |
| `PAYME_SECRET_KEY` | Kassaning kalit-paroli | Kabinet → kassa → «Настройки» → «Инструменты разработчика» |
| `PAYME_ACCOUNT_KEY_1` | `account` obyektidagi asosiy maydon nomi (masalan `order_id`) | Kassa sozlamalarida siz o'zingiz belgilaysiz |
| `PAYME_ACCOUNT_KEY_2` | Ixtiyoriy ikkinchi maydon (standart: `order_type`) | Kassa sozlamalari |

`PAYME_ENV` esa kalit emas: `true` — production (haqiqiy pul), boshqa har qanday qiymat yoki umuman ko'rsatilmasa — test muhiti.

---

## 1. Kabinetga kirish va kassa yaratish

1. [business.payme.uz](https://business.payme.uz) saytiga telefon raqamingiz bilan kiring.
2. Biznesingizni yarating (yoki mavjud biznesni tanlang).
3. Biznesga **veb-kassa** qo'shing.

Kassa yaratilgandan so'ng Payme Business sizga **2 ta kalit** beradi: kabinet uchun `key` va sinov uchun `TEST_KEY`.

> Kassa sozlamalarida **Endpoint URL** ham ko'rsatiladi — bu Payme sizning serveringizga (Merchant API) so'rov yuboradigan manzil. Uni to'g'ri to'ldirmasangiz `receipts.create` ishlamaydi (pastdagi `-31623` xatosiga qarang).

---

## 2. `PAYME_TOKEN` — kassa ID sini olish

Rasmiy yo'riqnoma: [Поиск id кассы](https://developer.help.paycom.uz/poisk-klyucha-i-id-kassy-v-lichnom-kabinete/poisk-id-kassy/)

1. Shaxsiy kabinetga kiring.
2. Ro'yxatdan kerakli **biznesni** tanlang.
3. **«Кассы»** bo'limiga o'ting — shu biznesga tegishli kassalar ro'yxati chiqadi.
4. Kerakli kassaning o'ng tomonidagi **kontekst menyusini** oching.
5. **«Скопировать ID»** ni bosing.

Nusxalangan qiymat — bu `PAYME_TOKEN`. U 24 ta belgidan iborat, faqat `0-9a-f` harflaridan tashkil topgan bo'lishi kerak.

```env
PAYME_TOKEN=100fe486b33784292111b7dc
```

---

## 3. `PAYME_SECRET_KEY` — kassa kalitini olish

Rasmiy yo'riqnoma: [Поиск ключа-пароля от кассы](https://developer.help.paycom.uz/poisk-klyucha-i-id-kassy-v-lichnom-kabinete/poisk-klyucha-parolya-ot-kassy/)

1. Kabinetga kiring va **biznesni** tanlang.
2. **«Кассы»** bo'limidan kerakli **kassani oching**.
3. **«Настройки»** yorlig'iga o'ting.
4. **«Инструменты разработчика»** bo'limini oching.

U yerda ikkita kalit turadi:

- **«Ключ»** — to'lovlarni qabul qilish uchun ishlatiladi. `.env` dagi `PAYME_SECRET_KEY` aynan shu.
- **«Тестовый ключ» (TEST_KEY)** — kassangizni tekshirish uchun. U **Merchant API sandbox** ([test.paycom.uz](https://test.paycom.uz)) da ishlatiladi, ya'ni Payme sizning serveringizni chaqirib ko'radigan joyda.

```env
PAYME_SECRET_KEY=kassangizning_kaliti
```

> ⚠️ Kalitni hech qachon git ga qo'shmang, chatga tashlamang va logga yozmang. `.env` fayli `.gitignore` da turishi shart.

---

## 4. `PAYME_ACCOUNT_KEY_1` va `PAYME_ACCOUNT_KEY_2`

Bu kalitlar emas — bular **`account` obyektidagi maydon nomlari**. Ularni kassa sozlamalarida o'zingiz belgilaysiz: to'lov qaysi buyurtmaga tegishli ekanini Payme shu maydon orqali biladi.

Masalan, kassangizda maydon `order_id` deb nomlangan bo'lsa:

```env
PAYME_ACCOUNT_KEY_1=order_id
PAYME_ACCOUNT_KEY_2=order_type
```

Kutubxona ularni shunday yuboradi:

```json
{"method": "receipts.create",
 "params": {"amount": 100000, "account": {"order_id": "12345"}}}
```

**Nomi bir harf bo'lsa ham noto'g'ri bo'lsa**, Payme `-31610` xatosini qaytaradi va `data` maydonida kutilayotgan nomni aytadi — ya'ni to'g'ri nomni xatoning o'zidan bilib olsa bo'ladi:

```json
{"error": {"code": -31610, "data": "order_id"}}
```

---

## 5. Test muhiti (sandbox) haqida muhim ogohlantirish

Payme da **ikkita boshqa-boshqa "test"** bor, ular tez-tez chalkashtiriladi:

| Nima | Manzil | Kim kimni chaqiradi | Qaysi kalit |
|---|---|---|---|
| **Merchant API sandbox** | `test.paycom.uz` | Payme → sizning serveringiz | Merchant ID + `TEST_KEY` |
| **Subscribe API test hosti** | `checkout.test.paycom.uz` | Siz → Payme | Test hostida ro'yxatdan o'tgan alohida kassa |

Bu kutubxona **Subscribe API** bilan ishlaydi, ya'ni ikkinchi qator.

`checkout.test.paycom.uz` da **alohida kassalar ro'yxati** bor. Production kassangizning ID si u yerda ishlamaydi — javob har doim quyidagicha bo'ladi:

```json
{"error": {"code": -32504, "message": "Access denied.", "data": "invalid_id"}}
```

Bu "kalit noto'g'ri" degani emas — bu "bu kassa bu hostda umuman mavjud emas" degani. (Tekshirib ko'rilgan: o'ylab topilgan soxta ID ham aynan shu javobni oladi.)

Hujjatlarda test kabineti sifatida `merchant.test.paycom.uz` ko'rsatilgan, lekin **bu domen endi ishlamaydi** (DNS topilmaydi). Shuning uchun Subscribe API uchun test kirimini faqat Payme dan so'rab olish mumkin.

---

## 6. Qo'llab-quvvatlashga qanday murojaat qilish

Rasmiy hujjatda shunday deyilgan: *«Ключ-пароль от кассы запросите у технического специалиста Payme Business»*.

Aloqa uchun (business.payme.uz saytidan):

- Telefon: **+998 78 150-22-24**
- Telegram: [@PaymeBusiness](https://t.me/PaymeBusiness)
- Sizga biriktirilgan menejer (agar shartnoma bo'lsa)

### Xabar namunasi (rus tilida yuborgan ma'qul)

> Здравствуйте! Мы интегрируем **Subscribe API** (методы `cards.create`, `receipts.create`).
>
> Наш Merchant ID (production): `100fe486b33784292111b7dc`
> Название бизнеса: `...`
>
> Просим предоставить доступ к **тестовой среде Subscribe API** (`https://checkout.test.paycom.uz/api`): тестовую кассу и ключ-пароль к ней. Наш production ID на тестовом хосте возвращает `-32504 / invalid_id`, а `merchant.test.paycom.uz` из документации больше не открывается.
>
> Также просим подтвердить имя поля объекта `account` для нашей кассы.

### So'raladigan narsalar ro'yxati

1. Subscribe API test hosti uchun **test kassa ID** va **kalit**.
2. Kassangizdagi `account` maydonining aniq nomi (`PAYME_ACCOUNT_KEY_1`).
3. Kassa uchun **Endpoint URL** to'g'ri saqlanganini tasdiqlash.
4. Agar `cards.*` metodlari kerak bo'lsa — kassangizda Subscribe API yoqilganini tasdiqlash.

---

## 7. Tez-tez uchraydigan xatolar

| Kod | Payme xabari | Aslida nima bo'lgan | Yechim |
|---|---|---|---|
| `-32504` + `data: "invalid_id"` | Access denied | Bu kassa shu hostda ro'yxatda yo'q | Production uchun `PAYME_ENV=true`; test uchun Payme dan test kassa so'rang |
| `-32602` | Invalid Params | Karta raqami yoki muddati noto'g'ri formatda | Kutubxona buni o'zi tuzatadi: `"8600 0691 9540 6311"` va `"10/27"` ham qabul qilinadi |
| `-31610` | (bo'sh) | `account` maydon nomi noto'g'ri | `data` da to'g'ri nom yozilgan — `PAYME_ACCOUNT_KEY_1` ni shunga moslang |
| `-31623` | Сервис поставщика услуг работает некорректно | **Payme sizning serveringizni chaqirdi va sizning serveringiz rad etdi** | `error.data` ichidagi xatoni o'qing (kutubxonada: `MerchantEndpointError.endpoint_error`) |
| `-31301` | — | Karta bloklangan / muddati o'tgan / SMS ulanmagan | Payme bu uchalasi uchun bitta kod ishlatadi, farqlab bo'lmaydi |

### `-31623` haqida alohida

Bu xato Payme ning o'zida emas. `receipts.create` chaqirilganda Payme sizning kassangizga yozilgan **Endpoint URL** ga `CheckPerformTransaction` so'rovini yuboradi. Sizning serveringiz qaytargan xato `error.data` ichida turadi:

```json
{"code": -31623,
 "data": {"code": -32504, "message": {"ru": "Недостаточно привилегий."}}}
```

Ichkaridagi `-32504` — bu **sizning serveringiz** Payme ni tanimagani. Serveringiz `Authorization: Basic base64("Paycom:<kassa kaliti>")` sarlavhasini tekshiradi: login har doim `Paycom` so'zi, parol esa kassa kaliti. Production da test kalitini qoldirib ketish — eng ko'p uchraydigan sabab.

---

## 8. Yakuniy `.env`

```env
# true — production (haqiqiy pul), boshqa qiymat — test hosti
PAYME_ENV=false

PAYME_TOKEN=kassa_id_si
PAYME_SECRET_KEY=kassa_kaliti
PAYME_ACCOUNT_KEY_1=order_id
PAYME_ACCOUNT_KEY_2=order_type

# Ixtiyoriy: loglar qayerga yozilsin (standart: ./logs)
PAYME_LOG_DIR=logs
```

Tekshirish:

```bash
python examples/example.py
```

---

## Foydali havolalar

- [Payme Business hujjatlari](https://developer.help.paycom.uz/)
- [Subscribe API protokoli](https://developer.help.paycom.uz/protokol-subscribe-api/)
- [Subscribe API metodlari](https://developer.help.paycom.uz/metody-subscribe-api/)
- [Kassa ID sini topish](https://developer.help.paycom.uz/poisk-klyucha-i-id-kassy-v-lichnom-kabinete/poisk-id-kassy/)
- [Kassa kalitini topish](https://developer.help.paycom.uz/poisk-klyucha-i-id-kassy-v-lichnom-kabinete/poisk-klyucha-parolya-ot-kassy/)
- [Песочница (Merchant API sandbox)](https://developer.help.paycom.uz/pesochnitsa/)
