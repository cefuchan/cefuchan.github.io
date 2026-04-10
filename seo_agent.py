"""
🤖 SEO Agent — %100 Ücretsiz Versiyon
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Kullandığı araçlar:
  • Google Search Console API  (ücretsiz)
  • Kendi SEO kural motoru     (ücretsiz)
  • GitHub Actions             (ücretsiz)
  • GitHub Issues              (ücretsiz)
"""

import os
import json
import glob
import re
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
from bs4 import BeautifulSoup

# Google API
from google.oauth2 import service_account
from googleapiclient.discovery import build

# ──────────────────────────────────────────
# AYARLAR
# ──────────────────────────────────────────
GITHUB_TOKEN      = os.environ.get("GITHUB_TOKEN", "")
REPO_NAME         = os.environ.get("REPO_NAME", "")
SITE_URL          = os.environ.get("SITE_URL", "").rstrip("/")
GSC_JSON_STR      = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")

SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]

# ──────────────────────────────────────────
# 1. HTML DOSYALARINI BUL
# ──────────────────────────────────────────
def find_html_files():
    files = glob.glob("**/*.html", recursive=True)
    ignore = {"node_modules", "vendor", ".git"}
    return sorted(
        f for f in files
        if not any(part in ignore for part in Path(f).parts)
    )

# ──────────────────────────────────────────
# 2. HTML PARSE
# ──────────────────────────────────────────
def parse_page(filepath: str) -> dict:
    with open(filepath, encoding="utf-8", errors="ignore") as fh:
        soup = BeautifulSoup(fh, "lxml")

    title       = soup.title.string.strip() if soup.title and soup.title.string else ""
    description = ""
    keywords    = ""
    canonical   = ""
    robots      = ""

    for tag in soup.find_all("meta"):
        name = (tag.get("name") or "").lower()
        prop = (tag.get("property") or "").lower()
        if name == "description":
            description = tag.get("content", "")
        if name == "keywords":
            keywords = tag.get("content", "")
        if name == "robots":
            robots = tag.get("content", "")
        if prop == "og:description" and not description:
            description = tag.get("content", "")

    canon_tag = soup.find("link", rel="canonical")
    if canon_tag:
        canonical = canon_tag.get("href", "")

    h1s  = [h.get_text(strip=True) for h in soup.find_all("h1")]
    h2s  = [h.get_text(strip=True) for h in soup.find_all("h2")]
    h3s  = [h.get_text(strip=True) for h in soup.find_all("h3")]

    all_imgs   = soup.find_all("img")
    imgs_no_alt = [img.get("src", "?") for img in all_imgs if not img.get("alt")]

    # Dahili linkler
    links = [a.get("href", "") for a in soup.find_all("a", href=True)]

    body_text  = soup.get_text(separator=" ", strip=True)
    word_count = len(body_text.split())

    return {
        "file":        filepath,
        "title":       title,
        "description": description,
        "keywords":    keywords,
        "canonical":   canonical,
        "robots":      robots,
        "h1s":         h1s,
        "h2s":         h2s,
        "h3s":         h3s,
        "imgs_no_alt": imgs_no_alt,
        "total_imgs":  len(all_imgs),
        "links":       links,
        "word_count":  word_count,
        "body_text":   body_text[:500],
    }

# ──────────────────────────────────────────
# 3. SEO KURAL MOTORU (API'siz, ücretsiz)
# ──────────────────────────────────────────
def analyze_seo(page: dict) -> dict:
    """
    Kurallara dayalı SEO analizi.
    Her kural: (severity, issue_mesajı, öneri)
    """
    issues  = []
    score   = 100
    tips    = []

    title       = page["title"]
    description = page["description"]
    h1s         = page["h1s"]
    word_count  = page["word_count"]

    # ── Title kontrolleri ──
    if not title:
        issues.append(("high", "Title etiketi eksik",
                        "<title>Sayfa Başlığı | Site Adı</title> ekle"))
        score -= 20
    elif len(title) < 30:
        issues.append(("medium", f"Title çok kısa ({len(title)} karakter)",
                        "30-60 karakter arası bir title yaz"))
        score -= 8
    elif len(title) > 65:
        issues.append(("medium", f"Title çok uzun ({len(title)} karakter, Google 60'ta keser)",
                        "60 karakterin altında tut"))
        score -= 5

    # ── Meta Description ──
    if not description:
        issues.append(("high", "Meta description eksik",
                        '<meta name="description" content="150-160 karakter açıklama"> ekle'))
        score -= 15
    elif len(description) < 80:
        issues.append(("medium", f"Meta description çok kısa ({len(description)} karakter)",
                        "120-160 karakter arası yaz, anahtar kelimelerini kullan"))
        score -= 7
    elif len(description) > 165:
        issues.append(("low", f"Meta description çok uzun ({len(description)} karakter)",
                        "160 karakterin altında tut, Google kısaltır"))
        score -= 3

    # ── H1 kontrolleri ──
    if not h1s:
        issues.append(("high", "H1 etiketi eksik",
                        "Sayfana tek bir <h1> etiketi ekle, ana konuyu belirt"))
        score -= 15
    elif len(h1s) > 1:
        issues.append(("medium", f"Birden fazla H1 var ({len(h1s)} adet)",
                        "Sayfada yalnızca 1 tane H1 kullan"))
        score -= 8

    # ── Görsel alt text ──
    if page["imgs_no_alt"]:
        n = len(page["imgs_no_alt"])
        issues.append(("medium", f"{n} görselde alt text eksik",
                        f'Şu görsellere alt=\"açıklama\" ekle: {", ".join(page["imgs_no_alt"][:3])}'))
        score -= min(n * 3, 12)

    # ── İçerik uzunluğu ──
    if word_count < 100:
        issues.append(("high", f"İçerik çok kısa ({word_count} kelime)",
                        "Sayfa içeriğini en az 300 kelimeye çıkar, Google ince içeriği sever değil"))
        score -= 15
    elif word_count < 300:
        issues.append(("medium", f"İçerik kısa ({word_count} kelime)",
                        "300+ kelime hedefle, bilgi değeri yüksek içerik ekle"))
        score -= 7

    # ── Canonical ──
    if not page["canonical"] and page["file"] != "index.html":
        issues.append(("low", "Canonical etiketi eksik",
                        f'<link rel="canonical" href="{SITE_URL}/{page["file"]}"> ekle'))
        score -= 4

    # ── Başlık hiyerarşisi ──
    if h1s and not page["h2s"]:
        issues.append(("low", "H2 etiketi yok",
                        "İçeriği bölümlere ayır, her bölüme H2 ekle"))
        score -= 4

    # ── Robots meta ──
    if "noindex" in page["robots"].lower():
        issues.append(("high", "Sayfa noindex ile işaretlenmiş — Google görmüyor!",
                        'robots meta etiketini kontrol et, noindex kaldır'))
        score -= 25

    # ── İçerik önerileri ──
    if word_count > 100 and not page["h3s"]:
        tips.append("İçerik uzunsa H3 alt başlıklar ekle, okunabilirliği artırır")
    if not page["keywords"]:
        tips.append("Meta keywords eskimiş olsa da bazı CMS'ler hâlâ kullanır, ekleyebilirsin")
    if page["total_imgs"] == 0 and word_count > 200:
        tips.append("Sayfa görsel içermiyor, en az 1 ilgili görsel ekle")
    if word_count > 500 and len(page["links"]) < 2:
        tips.append("Dahili link sayısı az, ilgili sayfalarına link ver")

    score = max(0, score)

    return {
        "score":   score,
        "issues":  issues,
        "tips":    tips,
    }

# ──────────────────────────────────────────
# 4. GOOGLE SEARCH CONSOLE VERİSİ
# ──────────────────────────────────────────
def get_gsc_data() -> dict:
    """
    Son 28 günün GSC verisini çek.
    Dönüş: { url: { clicks, impressions, ctr, position, top_queries: [...] } }
    """
    if not GSC_JSON_STR or not SITE_URL:
        print("⚠️  GSC yapılandırması eksik, atlanıyor.")
        return {}

    try:
        creds_dict = json.loads(GSC_JSON_STR)
        creds = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=SCOPES
        )
        service = build("searchconsole", "v1", credentials=creds)

        end_date   = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        start_date = (datetime.now(timezone.utc) - timedelta(days=28)).strftime("%Y-%m-%d")

        # Sayfa bazlı performans
        page_resp = service.searchanalytics().query(
            siteUrl=SITE_URL,
            body={
                "startDate":  start_date,
                "endDate":    end_date,
                "dimensions": ["page"],
                "rowLimit":   50,
            }
        ).execute()

        # Keyword bazlı performans (tüm site)
        query_resp = service.searchanalytics().query(
            siteUrl=SITE_URL,
            body={
                "startDate":  start_date,
                "endDate":    end_date,
                "dimensions": ["query"],
                "rowLimit":   20,
            }
        ).execute()

        page_data = {}
        for row in page_resp.get("rows", []):
            url = row["keys"][0]
            page_data[url] = {
                "clicks":      row.get("clicks", 0),
                "impressions": row.get("impressions", 0),
                "ctr":         round(row.get("ctr", 0) * 100, 1),
                "position":    round(row.get("position", 0), 1),
            }

        top_queries = [
            {
                "query":       r["keys"][0],
                "clicks":      r.get("clicks", 0),
                "impressions": r.get("impressions", 0),
                "position":    round(r.get("position", 0), 1),
            }
            for r in query_resp.get("rows", [])
        ]

        print(f"✅ GSC: {len(page_data)} sayfa, {len(top_queries)} keyword verisi alındı.")
        return {"pages": page_data, "top_queries": top_queries}

    except Exception as e:
        print(f"❌ GSC hatası: {e}")
        return {}

# ──────────────────────────────────────────
# 5. SİTEMAP OLUŞTUR
# ──────────────────────────────────────────
def build_sitemap(html_files: list) -> str:
    urlset = Element("urlset")
    urlset.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    for filepath in html_files:
        if filepath == "index.html":
            loc = SITE_URL + "/"
        else:
            clean = filepath.replace("\\", "/").removesuffix(".html")
            loc   = SITE_URL + "/" + clean

        url = SubElement(urlset, "url")
        SubElement(url, "loc").text        = loc
        SubElement(url, "lastmod").text    = today
        SubElement(url, "changefreq").text = "weekly"
        SubElement(url, "priority").text   = "1.0" if filepath == "index.html" else "0.8"

    raw  = tostring(urlset, encoding="unicode")
    return minidom.parseString(raw).toprettyxml(indent="  ")

# ──────────────────────────────────────────
# 6. RAPOR OLUŞTUR
# ──────────────────────────────────────────
def build_report(results: list, gsc: dict) -> str:
    now   = datetime.now(timezone.utc).strftime("%d %B %Y %H:%M UTC")
    total = len(results)
    avg   = sum(r["analysis"]["score"] for r in results) // total if total else 0
    high  = sum(
        1 for r in results
        for iss in r["analysis"]["issues"]
        if iss[0] == "high"
    )

    lines = [
        f"# 🤖 SEO Agent Raporu — {now}",
        "",
        f"| Metrik | Değer |",
        f"|---|---|",
        f"| Taranan sayfa | {total} |",
        f"| Ortalama SEO puanı | **{avg}/100** |",
        f"| 🔴 Kritik sorun | {high} |",
        "",
        "---",
        "",
    ]

    # ── GSC Özeti ──
    if gsc:
        top_q = gsc.get("top_queries", [])[:10]
        if top_q:
            lines += [
                "## 📊 Google Search Console — Son 28 Gün",
                "",
                "### 🔑 En İyi 10 Keyword",
                "| Keyword | Tıklama | Gösterim | Ort. Pozisyon |",
                "|---|---|---|---|",
            ]
            for q in top_q:
                lines.append(
                    f"| {q['query']} | {q['clicks']} | {q['impressions']} | #{q['position']} |"
                )
            lines += ["", "---", ""]

        # Düşük CTR sayfalar
        pages = gsc.get("pages", {})
        low_ctr = [
            (url, d) for url, d in pages.items()
            if d["impressions"] > 50 and d["ctr"] < 2.0
        ]
        if low_ctr:
            lines += [
                "### ⚠️ Düşük CTR Sayfalar (gösterim var ama tıklanmıyor)",
                "| Sayfa | Gösterim | CTR | Pozisyon |",
                "|---|---|---|---|",
            ]
            for url, d in sorted(low_ctr, key=lambda x: -x[1]["impressions"])[:5]:
                lines.append(
                    f"| {url} | {d['impressions']} | %{d['ctr']} | #{d['position']} |"
                )
            lines += ["", "> 💡 Bu sayfaların meta description'ını daha çekici yap.", "", "---", ""]

        # Yüksek pozisyon, az tıklama (pozisyon 4-10 arası fırsatlar)
        opportunity = [
            (url, d) for url, d in pages.items()
            if 4 <= d["position"] <= 10 and d["impressions"] > 30
        ]
        if opportunity:
            lines += [
                "### 🚀 Fırsat Sayfaları (ilk sayfada, biraz itmek yeter!)",
                "| Sayfa | Pozisyon | Gösterim | Tıklama |",
                "|---|---|---|---|",
            ]
            for url, d in sorted(opportunity, key=lambda x: x[1]["position"])[:5]:
                lines.append(
                    f"| {url} | #{d['position']} | {d['impressions']} | {d['clicks']} |"
                )
            lines += ["", "> 💡 Bu sayfaların içeriğini zenginleştir, internal link ekle.", "", "---", ""]

    # ── Sayfa Analizleri ──
    lines += ["## 📄 Sayfa Analizleri", ""]

    for r in results:
        page     = r["page"]
        analysis = r["analysis"]
        score    = analysis["score"]
        issues   = analysis["issues"]
        tips     = analysis["tips"]
        file     = page["file"]

        # Puan rengi
        if score >= 80:
            badge = "🟢"
        elif score >= 55:
            badge = "🟡"
        else:
            badge = "🔴"

        lines += [
            f"### {badge} `{file}` — {score}/100",
            f"> 📝 Title: `{page['title'] or '(yok)'}` | "
            f"Kelime: {page['word_count']} | "
            f"H1: {len(page['h1s'])} | "
            f"Görsel: {page['total_imgs']}",
            "",
        ]

        if issues:
            lines.append("**⚠️ Sorunlar:**")
            for sev, msg, fix in sorted(issues, key=lambda x: {"high":0,"medium":1,"low":2}[x[0]]):
                emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}[sev]
                lines.append(f"- {emoji} {msg}")
                lines.append(f"  - 🔧 {fix}")
            lines.append("")

        if tips:
            lines.append("**💡 Öneriler:**")
            for tip in tips:
                lines.append(f"- {tip}")
            lines.append("")

        lines.append("---")
        lines.append("")

    lines += [
        "_Bu rapor SEO Agent tarafından otomatik oluşturulmuştur._",
        "_Ücretsiz araçlar: GitHub Actions + Google Search Console API_",
    ]

    return "\n".join(lines)

# ──────────────────────────────────────────
# 7. GITHUB ISSUE
# ──────────────────────────────────────────
def create_github_issue(title: str, body: str):
    if not GITHUB_TOKEN or not REPO_NAME:
        print("⚠️  GitHub token/repo eksik.")
        return

    url = f"https://api.github.com/repos/{REPO_NAME}/issues"
    resp = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept":        "application/vnd.github+json",
        },
        json={"title": title, "body": body, "labels": ["seo", "automated"]},
        timeout=15,
    )
    if resp.status_code == 201:
        print(f"✅ Issue açıldı: {resp.json()['html_url']}")
    else:
        print(f"❌ Issue açılamadı: {resp.status_code} — {resp.text[:200]}")

# ──────────────────────────────────────────
# 8. ANA AKIŞ
# ──────────────────────────────────────────
def main():
    print("🚀 SEO Agent başlatılıyor (ücretsiz mod)...")

    html_files = find_html_files()
    if not html_files:
        print("⚠️  HTML dosyası bulunamadı.")
        return
    print(f"📄 {len(html_files)} HTML dosyası bulundu.")

    # Sitemap
    if SITE_URL:
        sitemap = build_sitemap(html_files)
        with open("sitemap.xml", "w", encoding="utf-8") as f:
            f.write(sitemap)
        print("🗺️  sitemap.xml oluşturuldu.")

    # Sayfa analizleri
    results = []
    for i, filepath in enumerate(html_files, 1):
        print(f"🔍 [{i}/{len(html_files)}] {filepath}")
        page     = parse_page(filepath)
        analysis = analyze_seo(page)
        results.append({"page": page, "analysis": analysis})

    # GSC verisi
    print("📊 Google Search Console verisi çekiliyor...")
    gsc = get_gsc_data()

    # Rapor
    report = build_report(results, gsc)
    with open("seo_report.md", "w", encoding="utf-8") as f:
        f.write(report)
    print("📝 seo_report.md kaydedildi.")

    # Issue
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    create_github_issue(f"🤖 SEO Agent Raporu — {date_str}", report)

    print("✅ Tamamlandı!")

if __name__ == "__main__":
    main()
