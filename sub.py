import os, pathlib, re, requests, msal
from dotenv import load_dotenv

BASE = pathlib.Path(__file__).resolve().parent
load_dotenv(BASE / ".env")

CLIENT_ID  = os.getenv("CLIENT_ID")
TENANT_ID  = os.getenv("TENANT_ID", "consumers")
GRAPH_EP   = os.getenv("GRAPH_ENDPOINT", "https://graph.microsoft.com/v1.0")
SCOPES     = ["Files.Read"]

# 比較対象フォルダ
FOLDERS = ["/kiwi/2023_kiwi", "/AutoShareMedia"]
PHOTO_EXT = (".heic", ".jpg", ".jpeg")

# MSAL 認証
app = msal.PublicClientApplication(
    client_id=CLIENT_ID,
    authority=f"https://login.microsoftonline.com/{TENANT_ID}",
)
flow = app.initiate_device_flow(scopes=SCOPES)
print(flow["message"])
result = app.acquire_token_by_device_flow(flow)
headers = {"Authorization": f"Bearer {result['access_token']}"}

# ページング対応で全件取得
def list_all(folder_path):
    url = f"{GRAPH_EP}/me/drive/root:{folder_path}:/children?$select=id,name,@microsoft.graph.downloadUrl&$top=999"
    items = []
    while url:
        res = requests.get(url, headers=headers).json()
        items += res.get("value", [])
        url = res.get("@odata.nextLink")
    return items

# 検証実行
for folder in FOLDERS:
    print(f"\n📁 {folder}")
    items = list_all(folder)
    photos = [i for i in items if i["name"].lower().endswith(PHOTO_EXT)]

    with_url = [i["name"] for i in photos if "@microsoft.graph.downloadUrl" in i]
    without  = [i["name"] for i in photos if "@microsoft.graph.downloadUrl" not in i]

    print(f"  画像ファイル数: {len(photos)}")
    print(f"  downloadUrl あり: {len(with_url)}")
    print(f"  downloadUrl なし: {len(without)}")

    print("  ✅ あり→", with_url[:5])
    print("  ⚠️ なし→", without[:5])
