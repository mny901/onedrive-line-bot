import os, pathlib, random, re, datetime as dt, requests, msal
from dotenv import load_dotenv

# === 基本設定 ===
BASE = pathlib.Path(__file__).resolve().parent
load_dotenv(BASE / ".env")

CLIENT_ID  = os.getenv("CLIENT_ID")
TENANT_ID  = os.getenv("TENANT_ID", "consumers")
SCOPES     = os.getenv("SCOPES", "Files.Read").split()
GRAPH_EP   = os.getenv("GRAPH_ENDPOINT", "https://graph.microsoft.com/v1.0")
LINE_TOKEN = os.getenv("LINE_CHANNEL_TOKEN")
LINE_TO    = os.getenv("LINE_GROUP_ID")

PHOTO_FOLDERS = [
    "/kiwi/2022_kiwi",
    "/kiwi/2023_kiwi",
    "/kiwi/2024_kiwi",
]
PHOTO_EXT = (".jpg", ".jpeg", ".heic")
photo_re  = re.compile(r"(\d{8})[_\-]", re.I)

# === MSAL 認証処理 ===
CACHE = BASE / "token_cache.bin"
cache = msal.SerializableTokenCache()
if CACHE.exists():
    cache.deserialize(CACHE.read_text())

app = msal.PublicClientApplication(
    client_id=CLIENT_ID,
    authority=f"https://login.microsoftonline.com/{TENANT_ID}",
    token_cache=cache,
)
acct = (app.get_accounts() or [None])[0]
result = app.acquire_token_silent(SCOPES, account=acct)
if not result:
    flow = app.initiate_device_flow(scopes=SCOPES)
    print(flow["message"])
    result = app.acquire_token_by_device_flow(flow)
if cache.has_state_changed:
    CACHE.write_text(cache.serialize())

headers = {"Authorization": f"Bearer {result['access_token']}"}

# === 日付フィルタ（月±1） ===
JST = dt.timezone(dt.timedelta(hours=9))
today = dt.datetime.now(JST).date()
target_months = {(today.month - 1) or 12, today.month, (today.month % 12) + 1}

# === OneDrive API ===
def list_all_items(folder_path):
    url = f"{GRAPH_EP}/me/drive/root:{folder_path}:/children?$expand=thumbnails&$top=999"
    items = []
    while url:
        res = requests.get(url, headers=headers).json()
        items += res.get("value", [])
        url = res.get("@odata.nextLink")
    return items

def filter_photos_by_month(items, months):
    matched = []
    for i in items:
        if "file" not in i or not i["name"].lower().endswith(PHOTO_EXT):
            continue
        m = photo_re.match(i["name"])
        if not m:
            continue
        try:
            shot_date = dt.datetime.strptime(m.group(1), "%Y%m%d").date()
            if shot_date.month in months and "@microsoft.graph.downloadUrl" in i:
                i["shot_date"] = shot_date
                matched.append(i)
        except:
            continue
    return matched

# === LINE送信 ===
def push_line(messages):
    res = requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers={
            "Authorization": f"Bearer {LINE_TOKEN}",
            "Content-Type": "application/json"
        },
        json={"to": LINE_TO, "messages": messages},
        timeout=20,
    )
    print("LINE status:", res.status_code, res.text)
    res.raise_for_status()

# === メイン処理 ===
random.shuffle(PHOTO_FOLDERS)
selected = None

for folder in PHOTO_FOLDERS:
    items = list_all_items(folder)
    seasonal_photos = filter_photos_by_month(items, target_months)
    if seasonal_photos:
        selected = random.choice(seasonal_photos)
        break

if not selected:
    raise RuntimeError("❌ 該当する季節の画像が見つかりませんでした。")

img_url = selected["@microsoft.graph.downloadUrl"]
shot_dt = selected["shot_date"]
msg_txt = f"📸 {shot_dt.strftime('%Y/%m/%d')} 頃の思い出"

messages = [
    {"type": "text", "text": msg_txt},
    {"type": "image", "originalContentUrl": img_url, "previewImageUrl": img_url}
]

push_line(messages)
print(f"✅ 送信完了: {selected['name']} from {folder}")
