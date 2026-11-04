# HRB KYS — Orijinal 24 departman yapısına dayanan entegrasyon adayı

Bu paket önceki 90 kategori / 2 departman hatasını düzeltir. Orijinal HTML içindeki **24 departman başlığını** ve her departmanın **satır sayısını** temel alır. Her satır için kurgusal başlıklı, kurgusal içerikli PDF oluşturur. Gerçek HRB doküman adı, bağlantısı, metni, personel listesi veya gömülü PDF **bulunmaz**. Orijinal HTML'nin kurumsal CSS stili kullanılmıştır.

Giriş, kullanıcı ve sayfa/departman yetkileri, PDF erişimi, revizyon onaylama, okudum/kabul, takvim ve raporlar V5 FastAPI uygulamasından gelir. Orijinal HTML'deki tüm JS davranışları aktarılmış değildir; **nihai üretim sürümü değildir**.

## Yerel test

`pip install -r requirements.txt`
`KYS_ADMIN_PASSWORD` ortam değişkenine en az 12 karakterlik şifre atayın.
`uvicorn app:app --host 127.0.0.1 --port 8000`

Giriş kullanıcı adı: `demet.admin`. Veritabanı yalnızca ilk açılışta tohumlanır. **Mevcut Render servisinin üzerine kurmayın**; farklı demo veri tabanıyla test edin. Render Free üzerinde SQLite kalıcı değildir.
