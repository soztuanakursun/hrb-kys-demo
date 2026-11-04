# HRB KYS — Orijinal Tasarım Entegrasyonu V2 (Kurgusal Pilot)

Bu sürüm, kullanıcının gönderdiği **Kalite_Yonetim_Sistemi_Nihai (2) (1).html** dosyasının CSS tasarımını ve üst yatay menü düzenini temel alır; çalışan FastAPI oturum ve sunucu tarafı departman yetki kontrollerini korur. Orijinal 101 MB HTML'deki gerçek personel/doküman listeleri ve gömülü PDF'ler **pakete alınmamıştır**.

## Çalışan bölümler
- Kullanıcı adı / şifre ile giriş, yönetici hesabı (`demet.admin`), personel oluşturma ve sayfa/departman yetkileri.
- Departman kartları, doküman arama, yetkili PDF önizlemesi.
- Revizyon talebi, eski/yeni metin farkı, yönetici ret / yeni PDF yükleyerek onay, sınırlı otomatik tek satır PDF güncelleme.
- Departman bazlı doküman/revizyon raporu.
- Takvimde aylar arasında oklarla geçiş; 9 Kasım 2026 örnek başlangıcı.

## Henüz yapılmayanlar
- Orijinal uygulamanın bütün ayrıntıları birebir aktarılmış değildir. Takvimdeki iş atamaları ve gerçek ilerleme takibi, okundu onayı ve personel/rapor entegrasyonları henüz sunucu tarafında yoktur.
- PDF otomatik değişimi kısa ve tek satırlık metinlerle sınırlıdır; yayından sonra görsel kontrol gerektirir.
- Render Free üzerindeki SQLite ve yüklenen dosyalar kalıcı disk olmadan kaybolabilir. Bu **üretim sistemi değildir**.

## Render
- Mevcut serviste Root Directory `HRB_KYS_GITHUB_RENDER_HAZIR_DEMO` ise bu paketin `app.py`, `bridge.js`, `static/index.html`, `requirements.txt`, `render.yaml` dosyalarını **o klasörün içine** yerleştirin. ZIP'in üst klasörünü ayrıca iç içe eklemeyin.
- `KYS_ADMIN_PASSWORD` ortam değişkeni korunmalı. Şifreyi GitHub'a yüklemeyin.
- Eski `app.py` ve SQLite veritabanını korumak, var olan hesapların kaybolmaması için önemlidir. Render'ın geçici diski yine de veri kaybı riski taşır.
