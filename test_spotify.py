import sys
import os

print("🎵 בודקים חיבור ישיר לספוטיפיי...")

try:
    from sk_plugins_media import SpotifyPlugin
    
    print("\nמתחבר לחשבון שלך...")
    plugin = SpotifyPlugin()
    
    if plugin.sp is None:
        print("❌ החיבור נכשל. נוצרה שגיאה אול ספרית `spotipy` לא מותקנת.")
        sys.exit(1)
        
    print("✅ החיבור הוגדר בהצלחה בקוד.")
    
    print("\nמנסה למשוך מידע מהשיר הקרוב (השלב הזה יפתח את הדפדפן בפעם הראשונה!)...")
    print("אם נפתח לך דפדפן - פשוט לחץ על 'Agree' (אשר/הסכם).\n")
    
    # This will trigger the authentication flow (browser opens) if not yet cached
    # and then get the playing song
    result = plugin.now_playing()
    
    print(f"\n🎧 תוצאת ספוטיפיי: {result}")
    
    print("\n🎉 אם ראית סטטוס נגינה או שגיאה עדינה שאין שיר שמתנגן כעת - זה עובד מושלם!")

except ImportError as e:
    print(f"❌ שגיאת ייבוא: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ שגיאה כללית: {e}")
    sys.exit(1)
