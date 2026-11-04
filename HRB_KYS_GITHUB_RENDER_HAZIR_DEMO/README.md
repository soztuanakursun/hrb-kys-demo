# HRB KYS – GitHub / Render için kurgusal demo

**Bu, orijinal HRB arayüzünün birebir kopyası değildir.** Gerçek kurum dokümanları bulunmaz. Demo yalnızca kurgusal PDF ve departmanlarla kullanıcı/yetki akışını göstermek içindir. Üretim kullanımı için uygun değildir.

## GitHub'a yükleme
1. GitHub'da **Private** `hrb-kys-demo` deposu açın.
2. Depoda **Add file > Upload files** seçin. Bu ZIP'i açıp `app.py`, `bridge.js`, `requirements.txt`, `render.yaml`, `.gitignore`, `README.md` ve `static` klasörünü (içindeki `index.html` ile) yükleyin. ZIP'i tek dosya olarak yüklemeyin.
3. GitHub'a şifre, `.env`, `data` klasörü veya gerçek HRB dokümanı yüklemeyin.

## Render
1. Render'da GitHub bağlantısı kurun, **New > Blueprint** üzerinden özel depoyu seçin (render.yaml). Alternatif olarak Web Service oluşturup build/start komutlarını `render.yaml` içinden alın.
2. `KYS_ADMIN_PASSWORD` ortam değişkenine **en az 12 karakterli, benzersiz** bir demo şifresi girin. Şifreyi GitHub'a yazmayın.
3. İlk açılışta `demet.admin` kullanıcı adıyla giriş yapın.
4. Test kullanıcılarını oluşturup departman ve sayfa yetkilerini kaydedin; çıkış yapıp bu kullanıcılarla giriş yaparak kontrol edin.

**UYARI:** Render Free üzerinde yerel SQLite dosyaları ve kullanıcı kayıtları yeniden başlatmada kaybolabilir. Bu demo kalıcı değildir. Demo veritabanında kişisel/kurumsal bilgi kullanmayın. İnternete açık olduğundan gerçek şirket şifresi kullanmayın.
