import sys
import time

try:
    from sk_plugins_media import SpotifyPlugin
    
    print("🎵 יוצר קשר עם ספוטיפיי...")
    plugin = SpotifyPlugin()
    
    if plugin.sp is None:
        print("❌ קריסה - ספוטיפיי לא מוגדר.")
        sys.exit(1)

    print("\n🔍 מוצא מכשיר פעיל...")
    devices = plugin.sp.devices()
    active_device = None
    for d in devices.get('devices', []):
        if d['is_active']:
            active_device = d['id']
            print(f"✅ נמצא מכשיר פעיל: {d['name']}")
            break
            
    if not active_device and devices.get('devices'):
        # Just pick the first one if none is "active"
        active_device = devices['devices'][0]['id']
        print(f"⚠️ לא נמצא מכשיר שמנגן כרגע, מנסה להעיר את: {devices['devices'][0]['name']}")
    elif not active_device:
        print("❌ שגיאה: לא נמצאה אפליקציית ספוטיפיי פתוחה באף מכשיר!")
        print("הפעולה נכשלה. עליך לפתוח את תוכנת ספוטיפיי במחשב או בטלפון קודם.")
        sys.exit(1)

    print("\n▶️ מנסה לנגן שיר אקראי של עומר אדם...")
    results = plugin.sp.search(q='עומר אדם', type='track', limit=1)
    if results['tracks']['items']:
        track_uri = results['tracks']['items'][0]['uri']
        plugin.sp.start_playback(device_id=active_device, uris=[track_uri])
        print(f"🎶 מנגן עכשיו: {results['tracks']['items'][0]['name']}")
    
    time.sleep(5)
    
    print("\n⏸️ עוצר את השיר...")
    plugin.sp.pause_playback(device_id=active_device)
    print("✅ נעצר!")
    
    time.sleep(3)
    
    print("\n▶️ ממשיך מאותו מקום...")
    plugin.sp.start_playback(device_id=active_device)
    print("✅ ממשיך!")
    
    time.sleep(3)
    
    print("\n⏭️ מעביר לשיר הבא...")
    plugin.sp.next_track(device_id=active_device)
    print("✅ הועבר!")
    
    print("\n🎉 כל הפקודות דרך ה-API עובדות בהצלחה!")

except ImportError:
    print("❌ שגיאה בייבוא spotipy")
except Exception as e:
    print(f"❌ שגיאה בזמן הריצה: {e}")
    if "Restriction violated" in str(e) or "Premium required" in str(e):
        print("שים לב: שליטה בשירים דרך ה-API דורשת חשבון Spotify Premium.")
