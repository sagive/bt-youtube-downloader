"""
YouTube Downloader - Modern CustomTkinter Edition
Support for Multi-language (English, Hebrew, Hindi, Thai), Video Metadata Preview,
Custom Tabbed Options, Download Queue, and FFmpeg integration.
"""

import os
import sys
import re
import json
import shutil
import urllib.request
import zipfile
import tempfile
import threading
import webbrowser
from PIL import Image, ImageTk
import customtkinter as ctk
from tkinter import filedialog, messagebox
import yt_dlp
from yt_dlp.postprocessor.ffmpeg import FFmpegPostProcessor


class TwitterCompatibilityPP(FFmpegPostProcessor):
    """
    Ensures downloaded videos meet strict Twitter/X & Social Media specifications:
    - Video Codec: H.264 (AVC)
    - Pixel Format: YUV420p (8-bit)
    - Audio Codec: AAC
    - Faststart enabled (moov atom at start of file)
    If video stream is already H.264 YUV420p, no re-encoding is performed.
    """
    def __init__(self, downloader=None):
        super().__init__(downloader)

    def run(self, info):
        filepath = info.get("filepath")
        if not filepath or not os.path.exists(filepath):
            return [], info

        ext = info.get("ext", "").lower()
        if ext not in ["mp4", "mkv", "webm", "mov"]:
            return [], info

        needs_reencode = False
        try:
            meta = self.get_metadata_object(filepath)
            streams = meta.get("streams", [])
            for stream in streams:
                codec_type = stream.get("codec_type")
                codec_name = (stream.get("codec_name") or "").lower()
                pix_fmt = (stream.get("pix_fmt") or "").lower()

                if codec_type == "video":
                    # Twitter/X requires H.264 and yuv420p
                    if codec_name != "h264" or pix_fmt != "yuv420p":
                        needs_reencode = True
                        break
                elif codec_type == "audio":
                    # Twitter/X requires AAC / MP3
                    if codec_name not in ["aac", "mp3"]:
                        needs_reencode = True
                        break
        except Exception:
            pass

        if needs_reencode:
            self.to_screen(f"[Social Media Compatibility] Re-encoding to standard H.264/AAC MP4 for Twitter...")
            temp_out = filepath + ".compat.mp4"
            opts = [
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "18",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "192k",
                "-movflags", "+faststart",
            ]
            self.run_ffmpeg(filepath, temp_out, opts)
            if os.path.exists(temp_out):
                try:
                    os.replace(temp_out, filepath)
                    info["ext"] = "mp4"
                except Exception:
                    pass

        return [], info


# Application Version
APP_VERSION = "v1.0.0"

# Set appearance mode and color theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# -------------------------------------------------------------------
#  i18n Translations Dictionary
# -------------------------------------------------------------------
TRANSLATIONS = {
    "en": {
        "app_title": "YouTube Downloader",
        "subtitle": "Download videos & audio in high quality",
        "url_placeholder": "Paste YouTube video or playlist URL here...",
        "paste": "📋 Paste",
        "load": "🔍 Load",
        "settings": "⚙️",
        "tab_download": "Options",
        "tab_advanced": "Advanced",
        "format_label": "Format Type:",
        "quality_label": "Quality / Resolution:",
        "est_size": "Estimated Size:",
        "save_to": "Save Directory:",
        "browse": "📁 Browse",
        "subtitles": "Download Video Subtitles",
        "sub_lang": "Subtitle Language:",
        "playlist": "Download Full Playlist (if URL is playlist)",
        "filename_tpl": "Filename Format:",
        "ffmpeg_status": "FFmpeg Engine:",
        "ffmpeg_installed": "✅ Installed (High Quality Muxing Available)",
        "ffmpeg_missing": "⚠️ Missing - Limited to 720p without muxing",
        "ffmpeg_install_btn": "💿 Auto-Install FFmpeg",
        "download_btn": "⬇️ Download Now!",
        "downloading_btn": "⏳ Downloading...",
        "cancel_btn": "🛑 Cancel",
        "queue_title": "Recent Downloads & Queue",
        "no_info": "Paste a URL and click 'Load' to preview video details",
        "no_recent": "No recent downloads yet.",
        "channel": "Channel:",
        "duration": "Duration:",
        "views": "Views:",
        "status_ready": "Ready",
        "status_fetching": "Fetching metadata...",
        "status_downloading": "Downloading video...",
        "status_completed": "Completed!",
        "status_error": "Error",
        "status_cancelled": "Cancelled",
        "settings_title": "Settings",
        "language_label": "Application Language:",
        "theme_label": "Appearance Mode:",
        "open_folder": "📂 Open Folder",
        "open_youtube": "▶ Watch",
        "clear_queue": "🗑️ Clear History",
        "err_no_url": "Please enter a valid YouTube URL first.",
        "success_download": "Download completed successfully!",
        "video": "Video",
        "audio": "Audio (MP3)",
        "best": "Best Available",
        "theme_dark": "Dark",
        "theme_light": "Light",
        "theme_system": "System",
    },
    "he": {
        "app_title": "YouTube Downloader",
        "subtitle": "הורד סרטוני יוטיוב ואודיו באיכות גבוהה",
        "url_placeholder": "הדבק קישור לסרטון או פלייליסט מ-YouTube...",
        "paste": "📋 הדבק",
        "load": "🔍 טען",
        "settings": "⚙️",
        "tab_download": "אפשרויות",
        "tab_advanced": "מתקדם",
        "format_label": "סוג פורמט:",
        "quality_label": "איכות / רזולוציה:",
        "est_size": "גודל משוער:",
        "save_to": "תיקיית יעד:",
        "browse": "📁 בחר",
        "subtitles": "הורד כתוביות לסרטון",
        "sub_lang": "שפת כתוביות:",
        "playlist": "הורד פלייליסט מלא (אם הקישור הוא פלייליסט)",
        "filename_tpl": "תבנית שם קובץ:",
        "ffmpeg_status": "מנוע FFmpeg:",
        "ffmpeg_installed": "✅ מותקן (איכות מקסימלית זמינה)",
        "ffmpeg_missing": "⚠️ חסר - מוגבל ל-720p ללא מיזוג",
        "ffmpeg_install_btn": "💿 התקן FFmpeg אוטומטית",
        "download_btn": "⬇️ הורד עכשיו!",
        "downloading_btn": "⏳ מוריד...",
        "cancel_btn": "🛑 ביטול",
        "queue_title": "תור והיסטוריית הורדות",
        "no_info": "הכנס קישור ולחץ על 'טען' כדי לצפות בפרטי הסרטון",
        "no_recent": "אין הורדות אחרונות עדיין.",
        "channel": "ערוץ:",
        "duration": "אורך:",
        "views": "צפיות:",
        "status_ready": "מוכן",
        "status_fetching": "מאחזר פרטי סרטון...",
        "status_downloading": "מוריד...",
        "status_completed": "הושלם!",
        "status_error": "שגיאה",
        "status_cancelled": "בוטל",
        "settings_title": "הגדרות תוכנה",
        "language_label": "שפת ממשק:",
        "theme_label": "מצב תצוגה:",
        "open_folder": "📂 פתח תיקייה",
        "open_youtube": "▶ צפה",
        "clear_queue": "🗑️ נקה היסטוריה",
        "err_no_url": "אנא הכנס קישור תקין מ-YouTube.",
        "success_download": "ההורדה הסתיימה בהצלחה!",
        "video": "וידאו",
        "audio": "אודיו (MP3)",
        "best": "האיכות הטובה ביותר",
        "theme_dark": "כהה",
        "theme_light": "בהיר",
        "theme_system": "מערכת",
    },
    "hi": {
        "app_title": "YouTube Downloader",
        "subtitle": "उच्च गुणवत्ता में वीडियो और ऑडियो डाउनलोड करें",
        "url_placeholder": "यहाँ यूट्यूब वीडियो या प्लेलिस्ट यूआरएल पेस्ट करें...",
        "paste": "📋 पेस्ट करें",
        "load": "🔍 लोड करें",
        "settings": "⚙️",
        "tab_download": "विकल्प",
        "tab_advanced": "उन्नत",
        "format_label": "प्रारूप का प्रकार:",
        "quality_label": "गुणवत्ता / रिज़ॉल्यूशन:",
        "est_size": "अनुमानित आकार:",
        "save_to": "सहेजने का स्थान:",
        "browse": "📁 चुनें",
        "subtitles": "वीडियो उपशीर्षक डाउनलोड करें",
        "sub_lang": "उपशीर्षक भाषा:",
        "playlist": "पूरी प्लेलिस्ट डाउनलोड करें (यदि यूआरएल प्लेलिस्ट है)",
        "filename_tpl": "फ़ाइल नाम प्रारूप:",
        "ffmpeg_status": "FFmpeg इंजन:",
        "ffmpeg_installed": "✅ स्थापित (उच्च गुणवत्ता उपलब्ध)",
        "ffmpeg_missing": "⚠️ अनुपस्थित - 720p तक सीमित",
        "ffmpeg_install_btn": "💿 FFmpeg ऑटो-इंस्टॉल करें",
        "download_btn": "⬇️ अभी डाउनलोड करें!",
        "downloading_btn": "⏳ डाउनलोड हो रहा है...",
        "cancel_btn": "🛑 रद्द करें",
        "queue_title": "हाल के डाउनलोड और कतार",
        "no_info": "विवरण देखने के लिए यूआरएल पेस्ट करें और 'लोड करें' पर क्लिक करें",
        "no_recent": "अभी तक कोई डाउनलोड नहीं है।",
        "channel": "चैनल:",
        "duration": "अवधि:",
        "views": "दृश्य:",
        "status_ready": "तैयार",
        "status_fetching": "जानकारी प्राप्त की जा रही है...",
        "status_downloading": "डाउनलोड हो रहा है...",
        "status_completed": "पूरा हुआ!",
        "status_error": "त्रुटि",
        "status_cancelled": "रद्द किया गया",
        "settings_title": "सेटिंग्स",
        "language_label": "ऐप भाषा:",
        "theme_label": "थीम मोड:",
        "open_folder": "📂 फ़ोल्डर खोलें",
        "open_youtube": "▶ देखें",
        "clear_queue": "🗑️ इतिहास हटाएं",
        "err_no_url": "कृपया पहले एक वैध यूट्यूब यूआरएल दर्ज करें।",
        "success_download": "डाउनलोड सफलतापूर्वक पूरा हुआ!",
        "video": "वीडियो",
        "audio": "ऑडियो (MP3)",
        "best": "सर्वश्रेष्ठ गुणवत्ता",
        "theme_dark": "डार्क",
        "theme_light": "लाइट",
        "theme_system": "सिस्टम",
    },
    "th": {
        "app_title": "YouTube Downloader",
        "subtitle": "ดาวน์โหลดวิดีโอและไฟล์เสียงคุณภาพสูง",
        "url_placeholder": "วางลิงก์วิดีโอหรือเพลย์ลิสต์ YouTube ที่นี่...",
        "paste": "📋 วาง",
        "load": "🔍 โหลด",
        "settings": "⚙️",
        "tab_download": "ตัวเลือก",
        "tab_advanced": "ขั้นสูง",
        "format_label": "ประเภทรูปแบบ:",
        "quality_label": "คุณภาพ / ความละเอียด:",
        "est_size": "ขนาดโดยประมาณ:",
        "save_to": "บันทึกไปที่:",
        "browse": "📁 เรียกดู",
        "subtitles": "ดาวน์โหลดคำบรรยายวิดีโอ",
        "sub_lang": "ภาษาคำบรรยาย:",
        "playlist": "ดาวน์โหลดทั้งเพลย์ลิสต์ (หากลิงก์เป็นเพลย์ลิสต์)",
        "filename_tpl": "รูปแบบชื่อไฟล์:",
        "ffmpeg_status": "เอนจิน FFmpeg:",
        "ffmpeg_installed": "✅ ติดตั้งแล้ว (รองรับคุณภาพสูงสุด)",
        "ffmpeg_missing": "⚠️ ไม่พบ - จำกัดที่ 720p",
        "ffmpeg_install_btn": "💿 ติดตั้ง FFmpeg อัตโนมัติ",
        "download_btn": "⬇️ ดาวน์โหลดเดี๋ยวนี้!",
        "downloading_btn": "⏳ กำลังดาวน์โหลด...",
        "cancel_btn": "🛑 ยกเลิก",
        "queue_title": "รายการดาวน์โหลดล่าสุดและคิว",
        "no_info": "วางลิงก์และคลิก 'โหลด' เพื่อดูรายละเอียดวิดีโอ",
        "no_recent": "ยังไม่มีรายการดาวน์โหลด",
        "channel": "ช่อง:",
        "duration": "ความยาว:",
        "views": "ยอดเข้าชม:",
        "status_ready": "พร้อม",
        "status_fetching": "กำลังดึงข้อมูล...",
        "status_downloading": "กำลังดาวน์โหลด...",
        "status_completed": "เสร็จสมบูรณ์!",
        "status_error": "ข้อผิดพลาด",
        "status_cancelled": "ยกเลิกแล้ว",
        "settings_title": "การตั้งค่า",
        "language_label": "ภาษาของแอป:",
        "theme_label": "โหมดแสดงผล:",
        "open_folder": "📂 เปิดโฟลเดอร์",
        "open_youtube": "▶ รับชม",
        "clear_queue": "🗑️ ล้างประวัติ",
        "err_no_url": "กรุณาใส่ลิงก์ YouTube ที่ถูกต้องก่อน",
        "success_download": "ดาวน์โหลดเสร็จสมบูรณ์!",
        "video": "วิดีโอ",
        "audio": "เสียง (MP3)",
        "best": "ดีที่สุด",
        "theme_dark": "มืด",
        "theme_light": "สว่าง",
        "theme_system": "ระบบ",
    },
}


class YouTubeDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window Setup
        self.title(f"YouTube Downloader {APP_VERSION}")
        self.geometry("960x680")
        self.minsize(900, 600)
        self.configure(fg_color=("#F5F5F7", "#1A1A1A"))

        # Window Icon
        try:
            icon_path = os.path.join(self._get_app_dir(), "assets", "icon.png")
            if not os.path.exists(icon_path):
                icon_path = os.path.join(self._get_app_dir(), "bt-youtube-downloader-icon-512.png")
            if os.path.exists(icon_path):
                self._app_icon_img = ImageTk.PhotoImage(Image.open(icon_path))
                self.iconphoto(True, self._app_icon_img)
        except Exception:
            pass

        # Application State (Default: English)
        self.current_lang = "en"
        self.download_path = ctk.StringVar(value=os.path.expanduser("~/Downloads"))
        self.url_var = ctk.StringVar()
        self.format_mode = ctk.StringVar(value="Video")
        self.quality_var = ctk.StringVar(value="Best")
        self.subtitle_enabled = ctk.BooleanVar(value=False)
        self.sub_lang_var = ctk.StringVar(value="English")
        self.playlist_enabled = ctk.BooleanVar(value=False)
        self.filename_tpl_var = ctk.StringVar(value="%(title)s.%(ext)s")

        self.is_downloading = False
        self.cancel_requested = False
        self.active_ydl = None
        self.video_info = None

        self.ffmpeg_available = self._check_ffmpeg()
        self.recent_downloads = self._load_recent_downloads()

        # Build Main UI
        self._build_ui()
        self._refresh_ffmpeg_status()

    # -------------------------------------------------------------------
    #  Helper Methods
    # -------------------------------------------------------------------
    def t(self, key):
        """Translate key to current language with fallback to English."""
        lang_dict = TRANSLATIONS.get(self.current_lang, TRANSLATIONS["en"])
        return lang_dict.get(key, TRANSLATIONS["en"].get(key, key))

    @staticmethod
    def _check_ffmpeg():
        return shutil.which("ffmpeg") is not None

    def _get_app_dir(self):
        if getattr(sys, "frozen", False):
            return os.path.dirname(os.path.abspath(sys.executable))
        return os.path.dirname(os.path.abspath(__file__))

    def _load_recent_downloads(self):
        recent_file = os.path.join(self._get_app_dir(), "recent_downloads.json")
        try:
            if os.path.exists(recent_file):
                with open(recent_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return []

    def _save_recent_downloads(self):
        recent_file = os.path.join(self._get_app_dir(), "recent_downloads.json")
        try:
            with open(recent_file, "w", encoding="utf-8") as f:
                json.dump(self.recent_downloads[:15], f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    @staticmethod
    def _format_size(bytes_val):
        for unit in ["B", "KB", "MB", "GB"]:
            if bytes_val < 1024:
                return f"{bytes_val:.1f} {unit}"
            bytes_val /= 1024
        return f"{bytes_val:.1f} TB"

    @staticmethod
    def _format_speed(bytes_per_sec):
        for unit in ["B/s", "KB/s", "MB/s", "GB/s"]:
            if bytes_per_sec < 1024:
                return f"{bytes_per_sec:.1f} {unit}"
            bytes_per_sec /= 1024
        return f"{bytes_per_sec:.1f} TB/s"

    # -------------------------------------------------------------------
    #  UI Construction
    # -------------------------------------------------------------------
    def _build_ui(self):
        # 1. Top Header Bar
        self.header_frame = ctk.CTkFrame(self, height=65, corner_radius=0, fg_color=("#FFFFFF", "#242424"))
        self.header_frame.pack(fill="x", side="top")
        self.header_frame.pack_propagate(False)

        # Header Left: Logo & Titles
        logo_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        logo_frame.pack(side="left", padx=15, pady=8)

        logo_icon = ctk.CTkLabel(logo_frame, text="🎬", font=("Arial", 28))
        logo_icon.pack(side="left", padx=(0, 8))

        titles_sub_frame = ctk.CTkFrame(logo_frame, fg_color="transparent")
        titles_sub_frame.pack(side="left")

        self.app_title_lbl = ctk.CTkLabel(
            titles_sub_frame,
            text=f"{self.t('app_title')} {APP_VERSION}",
            font=("Arial", 16, "bold"),
            text_color=("#E50914", "#FF4444")
        )
        self.app_title_lbl.pack(anchor="w")

        self.subtitle_lbl = ctk.CTkLabel(
            titles_sub_frame,
            text=self.t("subtitle"),
            font=("Arial", 10),
            text_color=("#666666", "#AAAAAA")
        )
        self.subtitle_lbl.pack(anchor="w")

        # Header Right: Action Buttons
        header_actions = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        header_actions.pack(side="right", padx=15)

        self.settings_btn = ctk.CTkButton(
            header_actions,
            text=self.t("settings"),
            width=42,
            height=38,
            corner_radius=19,
            fg_color=("#EAEAEA", "#333333"),
            hover_color=("#D5D5D5", "#444444"),
            text_color=("#1A1A1A", "#FFFFFF"),
            command=self._open_settings_dialog
        )
        self.settings_btn.pack(side="right", padx=(5, 0))

        self.load_btn = ctk.CTkButton(
            header_actions,
            text=self.t("load"),
            width=90,
            height=38,
            corner_radius=19,
            fg_color="#FF4444",
            hover_color="#CC0000",
            font=("Arial", 13, "bold"),
            command=self._fetch_video_info
        )
        self.load_btn.pack(side="right", padx=(5, 0))

        self.paste_btn = ctk.CTkButton(
            header_actions,
            text=self.t("paste"),
            width=85,
            height=38,
            corner_radius=19,
            fg_color=("#EAEAEA", "#333333"),
            hover_color=("#D5D5D5", "#444444"),
            text_color=("#1A1A1A", "#FFFFFF"),
            font=("Arial", 12),
            command=self._paste_url
        )
        self.paste_btn.pack(side="right", padx=(5, 0))

        # Header Center: URL Entry
        self.url_entry = ctk.CTkEntry(
            self.header_frame,
            textvariable=self.url_var,
            placeholder_text=self.t("url_placeholder"),
            height=38,
            corner_radius=19,
            font=("Arial", 13)
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=15, pady=13)
        self.url_entry.bind("<Return>", lambda e: self._fetch_video_info())

        # Main Body Container
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=15, pady=10)

        # Top Split Area (Video Info Card + Options Panel)
        self.upper_split_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.upper_split_frame.pack(fill="x", side="top", pady=(0, 10))

        # 2. Video Info Card (Left side)
        self.info_card = ctk.CTkFrame(self.upper_split_frame, height=210, corner_radius=12, fg_color=("#FFFFFF", "#242424"))
        self.info_card.pack(side="left", fill="both", expand=True, padx=(0, 8))

        # Thumbnail Label (compact size to leave room for Options Panel)
        self.thumb_label = ctk.CTkLabel(
            self.info_card,
            text="🎬",
            font=("Arial", 36),
            width=200,
            height=130,
            corner_radius=8,
            fg_color=("#EFEFEF", "#1E1E1E")
        )
        self.thumb_label.pack(side="left", padx=10, pady=10)

        # Video Details Sub-frame
        self.details_frame = ctk.CTkFrame(self.info_card, fg_color="transparent")
        self.details_frame.pack(side="left", fill="both", expand=True, padx=8, pady=10)

        self.video_title_lbl = ctk.CTkLabel(
            self.details_frame,
            text=self.t("no_info"),
            font=("Arial", 13, "bold"),
            wraplength=240,
            justify="left",
            anchor="w"
        )
        self.video_title_lbl.pack(anchor="w", fill="x", pady=(2, 6))

        self.channel_lbl = ctk.CTkLabel(self.details_frame, text="", font=("Arial", 11), text_color=("#555555", "#AAAAAA"), anchor="w")
        self.channel_lbl.pack(anchor="w", pady=1)

        self.duration_lbl = ctk.CTkLabel(self.details_frame, text="", font=("Arial", 11), text_color=("#555555", "#AAAAAA"), anchor="w")
        self.duration_lbl.pack(anchor="w", pady=1)

        self.views_lbl = ctk.CTkLabel(self.details_frame, text="", font=("Arial", 11), text_color=("#555555", "#AAAAAA"), anchor="w")
        self.views_lbl.pack(anchor="w", pady=1)

        self.status_badge = ctk.CTkLabel(
            self.details_frame,
            text=self.t("status_ready"),
            font=("Arial", 10, "bold"),
            fg_color=("#E5F6FD", "#103247"),
            text_color=("#0288D1", "#29B6F6"),
            corner_radius=10,
            padx=8,
            pady=3
        )
        self.status_badge.pack(anchor="w", pady=(6, 0))

        # 3. Options Panel (Tabview on Right side with fixed 460px width)
        self.options_tabview = ctk.CTkTabview(self.upper_split_frame, width=460, height=210, corner_radius=12)
        self.options_tabview.pack(side="right", fill="both")

        # Fixed internal names for tabs: "tab1", "tab2"
        self.tab_dl = self.options_tabview.add("tab1")
        self.tab_adv = self.options_tabview.add("tab2")

        # Configure tab button texts dynamically
        self._update_tab_button_texts()

        # --- Tab 1: Download Options ---
        self.fmt_lbl = ctk.CTkLabel(self.tab_dl, text=self.t("format_label"), font=("Arial", 12, "bold"))
        self.fmt_lbl.grid(row=0, column=0, sticky="w", pady=(5, 5))

        self.fmt_seg_btn = ctk.CTkSegmentedButton(
            self.tab_dl,
            values=[self.t("video"), self.t("audio"), self.t("best")],
            command=self._on_format_segment_change
        )
        self.fmt_seg_btn.set(self.t("video"))
        self.fmt_seg_btn.grid(row=0, column=1, sticky="ew", pady=(5, 5), padx=(10, 0))

        self.qual_lbl = ctk.CTkLabel(self.tab_dl, text=self.t("quality_label"), font=("Arial", 12, "bold"))
        self.qual_lbl.grid(row=1, column=0, sticky="w", pady=5)

        self.quality_option_menu = ctk.CTkOptionMenu(
            self.tab_dl,
            variable=self.quality_var,
            values=["Best", "2160p (4K)", "1440p (2K)", "1080p", "720p", "480p", "360p"],
            command=self._update_estimated_size
        )
        self.quality_option_menu.grid(row=1, column=1, sticky="ew", pady=5, padx=(10, 0))

        self.est_size_lbl = ctk.CTkLabel(
            self.tab_dl,
            text=f"{self.t('est_size')} --",
            font=("Arial", 11, "italic"),
            text_color=("#666666", "#888888")
        )
        self.est_size_lbl.grid(row=2, column=0, columnspan=2, sticky="w", pady=2)

        self.path_lbl = ctk.CTkLabel(self.tab_dl, text=self.t("save_to"), font=("Arial", 12, "bold"))
        self.path_lbl.grid(row=3, column=0, sticky="w", pady=(8, 5))

        path_row = ctk.CTkFrame(self.tab_dl, fg_color="transparent")
        path_row.grid(row=3, column=1, sticky="ew", pady=(8, 5), padx=(10, 0))

        self.path_entry = ctk.CTkEntry(path_row, textvariable=self.download_path, font=("Arial", 11), height=30)
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.browse_btn = ctk.CTkButton(
            path_row,
            text=self.t("browse"),
            width=70,
            height=30,
            command=self._browse_folder
        )
        self.browse_btn.pack(side="right")

        self.tab_dl.columnconfigure(1, weight=1)

        # --- Tab 2: Advanced Settings ---
        self.sub_chk = ctk.CTkCheckBox(
            self.tab_adv,
            text=self.t("subtitles"),
            variable=self.subtitle_enabled,
            command=self._on_subtitle_toggle
        )
        self.sub_chk.grid(row=0, column=0, sticky="w", pady=5)

        self.sub_lang_menu = ctk.CTkOptionMenu(
            self.tab_adv,
            variable=self.sub_lang_var,
            values=["English", "Hebrew", "Hindi", "Thai", "Auto-generated"],
            width=130,
            state="disabled"  # Disabled by default until checkbox is ticked!
        )
        self.sub_lang_menu.grid(row=0, column=1, sticky="e", pady=5, padx=(10, 0))

        self.playlist_chk = ctk.CTkCheckBox(self.tab_adv, text=self.t("playlist"), variable=self.playlist_enabled)
        self.playlist_chk.grid(row=1, column=0, columnspan=2, sticky="w", pady=5)

        self.fn_lbl = ctk.CTkLabel(self.tab_adv, text=self.t("filename_tpl"), font=("Arial", 11, "bold"))
        self.fn_lbl.grid(row=2, column=0, sticky="w", pady=5)

        self.fn_entry = ctk.CTkEntry(self.tab_adv, textvariable=self.filename_tpl_var, height=28, font=("Arial", 11))
        self.fn_entry.grid(row=2, column=1, sticky="ew", pady=5, padx=(10, 0))

        self.ffmpeg_lbl = ctk.CTkLabel(self.tab_adv, text="", font=("Arial", 10), wraplength=340, justify="left")
        self.ffmpeg_lbl.grid(row=3, column=0, columnspan=2, sticky="w", pady=(8, 2))

        self.ffmpeg_install_btn = ctk.CTkButton(
            self.tab_adv,
            text=self.t("ffmpeg_install_btn"),
            height=26,
            fg_color=("#3B82F6", "#2563EB"),
            command=self._install_ffmpeg
        )

        self.tab_adv.columnconfigure(1, weight=1)

        # 4. Bottom Control Area
        self.bottom_control_frame = ctk.CTkFrame(self.main_container, corner_radius=12, fg_color=("#FFFFFF", "#242424"))
        self.bottom_control_frame.pack(fill="x", side="top", pady=(0, 10), padx=0)

        btn_row = ctk.CTkFrame(self.bottom_control_frame, fg_color="transparent")
        btn_row.pack(fill="x", padx=15, pady=(12, 5))

        self.download_btn = ctk.CTkButton(
            btn_row,
            text=self.t("download_btn"),
            font=("Arial", 16, "bold"),
            height=46,
            corner_radius=23,
            fg_color="#FF4444",
            hover_color="#CC0000",
            command=self._start_download
        )
        self.download_btn.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.cancel_btn = ctk.CTkButton(
            btn_row,
            text=self.t("cancel_btn"),
            font=("Arial", 14, "bold"),
            height=46,
            width=110,
            corner_radius=23,
            fg_color="transparent",
            border_width=2,
            border_color=("#FF4444", "#FF4444"),
            text_color=("#FF4444", "#FF4444"),
            hover_color=("#FFEEEE", "#3A1A1A"),
            state="disabled",
            command=self._cancel_download
        )
        self.cancel_btn.pack(side="right")

        progress_row = ctk.CTkFrame(self.bottom_control_frame, fg_color="transparent")
        progress_row.pack(fill="x", padx=15, pady=(5, 12))

        self.progress_bar = ctk.CTkProgressBar(progress_row, height=12, corner_radius=6, progress_color="#FF4444")
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", pady=(0, 6))

        progress_info = ctk.CTkFrame(progress_row, fg_color="transparent")
        progress_info.pack(fill="x")

        self.progress_lbl = ctk.CTkLabel(
            progress_info,
            text=f"📌 {self.t('status_ready')}",
            font=("Arial", 12),
            text_color=("#444444", "#CCCCCC")
        )
        self.progress_lbl.pack(side="left")

        self.speed_eta_lbl = ctk.CTkLabel(
            progress_info,
            text="",
            font=("Arial", 12),
            text_color=("#666666", "#999999")
        )
        self.speed_eta_lbl.pack(side="right")

        # 5. Download Queue / Recent History List
        queue_header_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        queue_header_frame.pack(fill="x", side="top", pady=(5, 5))

        self.queue_header_lbl = ctk.CTkLabel(
            queue_header_frame,
            text=f"📋 {self.t('queue_title')}",
            font=("Arial", 14, "bold")
        )
        self.queue_header_lbl.pack(side="left")

        self.clear_queue_btn = ctk.CTkButton(
            queue_header_frame,
            text=self.t("clear_queue"),
            width=110,
            height=28,
            fg_color=("#E0E0E0", "#333333"),
            hover_color=("#D0D0D0", "#444444"),
            text_color=("#333333", "#E0E0E0"),
            font=("Arial", 11),
            command=self._clear_queue
        )
        self.clear_queue_btn.pack(side="right")

        self.queue_scroll = ctk.CTkScrollableFrame(
            self.main_container,
            height=150,
            corner_radius=12,
            fg_color=("#FFFFFF", "#242424")
        )
        self.queue_scroll.pack(fill="both", expand=True, side="top")

        self._refresh_queue_list()

    def _on_subtitle_toggle(self):
        if self.subtitle_enabled.get():
            self.sub_lang_menu.configure(state="normal")
        else:
            self.sub_lang_menu.configure(state="disabled")

    def _update_tab_button_texts(self):
        try:
            btns = self.options_tabview._segmented_button._buttons_dict
            if "tab1" in btns:
                btns["tab1"].configure(text=self.t("tab_download"))
            if "tab2" in btns:
                btns["tab2"].configure(text=self.t("tab_advanced"))
        except Exception:
            pass

    # -------------------------------------------------------------------
    #  Format & Quality Handling & Accurate Size Estimation
    # -------------------------------------------------------------------
    def _on_format_segment_change(self, val):
        if val == self.t("audio"):
            self.quality_option_menu.configure(values=["320kbps", "192kbps", "128kbps", "96kbps"])
            self.quality_var.set("320kbps")
        else:
            self.quality_option_menu.configure(values=["Best", "2160p (4K)", "1440p (2K)", "1080p", "720p", "480p", "360p"])
            self.quality_var.set("Best")
        self._update_estimated_size()

    def _update_estimated_size(self, choice=None):
        if not self.video_info:
            self.est_size_lbl.configure(text=f"{self.t('est_size')} --")
            return

        duration = self.video_info.get("duration", 0)
        is_audio = self.fmt_seg_btn.get() == self.t("audio")
        quality_str = self.quality_var.get()

        # 1. Try to find exact format match in video_info formats if available
        formats = self.video_info.get("formats", [])
        matched_size = None

        if formats:
            if is_audio:
                # Audio format matching
                audio_formats = [f for f in formats if f.get("vcodec") == "none" and f.get("acodec") != "none"]
                if audio_formats:
                    # Take best audio format size or calculate from abr
                    best_audio = max(audio_formats, key=lambda f: f.get("abr") or 0)
                    matched_size = best_audio.get("filesize") or best_audio.get("filesize_approx")
            else:
                # Video format matching by height
                match = re.search(r"(\d+)", quality_str)
                target_h = int(match.group(1)) if match else 1080
                matching_video_formats = [f for f in formats if f.get("height") == target_h]
                if matching_video_formats:
                    best_vf = max(matching_video_formats, key=lambda f: f.get("tbr") or f.get("filesize") or 0)
                    vf_size = best_vf.get("filesize") or best_vf.get("filesize_approx")
                    if vf_size:
                        # Add ~15% for audio stream muxing
                        matched_size = int(vf_size * 1.15)

        if matched_size and matched_size > 0:
            size_str = self._format_size(matched_size)
            self.est_size_lbl.configure(text=f"{self.t('est_size')} ~{size_str}")
            return

        # 2. Dynamic Estimation Fallback based on Duration & Quality Bitrate
        if duration > 0:
            if is_audio:
                # Audio Bitrate Estimates (MB per minute)
                bitrate_map = {
                    "320kbps": 2.4,
                    "192kbps": 1.4,
                    "128kbps": 0.95,
                    "96kbps": 0.7,
                }
                mb_per_min = bitrate_map.get(quality_str, 2.0)
            else:
                # Video Resolution Estimates (MB per minute, including audio)
                res_map = {
                    "2160p (4K)": 45.0,
                    "1440p (2K)": 24.0,
                    "1080p": 12.0,
                    "720p": 6.0,
                    "480p": 3.2,
                    "360p": 1.8,
                    "Best": 15.0,
                }
                mb_per_min = res_map.get(quality_str, 12.0)

            est_mb = (duration / 60.0) * mb_per_min
            if est_mb >= 1000:
                self.est_size_lbl.configure(text=f"{self.t('est_size')} ~{est_mb / 1024.0:.2f} GB")
            else:
                self.est_size_lbl.configure(text=f"{self.t('est_size')} ~{est_mb:.1f} MB")
        else:
            self.est_size_lbl.configure(text=f"{self.t('est_size')} --")

    # -------------------------------------------------------------------
    #  Fetch Video Metadata & Info Card Update
    # -------------------------------------------------------------------
    def _paste_url(self):
        try:
            clipboard = self.clipboard_get()
            if clipboard:
                self.url_var.set(clipboard)
                self._fetch_video_info()
        except Exception:
            pass

    def _browse_folder(self):
        folder = filedialog.askdirectory(title=self.t("save_to"))
        if folder:
            self.download_path.set(folder)

    def _fetch_video_info(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning(self.t("app_title"), self.t("err_no_url"))
            return

        self._set_status_badge(self.t("status_fetching"), fg="#0288D1", bg=("#E5F6FD", "#103247"))
        self.video_title_lbl.configure(text=self.t("status_fetching"))
        self.load_btn.configure(state="disabled")

        def _fetch_task():
            try:
                ydl_opts = {
                    "quiet": True,
                    "no_warnings": True,
                    "extractor_args": {"youtube": {"player_client": ["android", "web"]}},
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    if "entries" in info:
                        info = info["entries"][0]
                    self.video_info = info

                self.after(0, lambda data=info: self._update_info_card_ui(data))

            except Exception as e:
                err_msg = str(e)
                self.after(0, lambda msg=err_msg: self._on_fetch_error(msg))

        threading.Thread(target=_fetch_task, daemon=True).start()

    def _update_info_card_ui(self, info):
        self.load_btn.configure(state="normal")
        title = info.get("title", "Unknown Title")
        uploader = info.get("uploader") or info.get("channel", "Unknown Channel")
        duration_sec = info.get("duration", 0)
        view_count = info.get("view_count", 0)
        thumbnail_url = info.get("thumbnail")

        mins, secs = divmod(duration_sec, 60)
        hrs, mins = divmod(mins, 60)
        dur_str = f"{hrs}:{mins:02d}:{secs:02d}" if hrs else f"{mins}:{secs:02d}"
        views_str = f"{view_count:,}" if view_count else "N/A"

        self.video_title_lbl.configure(text=title)
        self.channel_lbl.configure(text=f"👤 {self.t('channel')} {uploader}")
        self.duration_lbl.configure(text=f"⏱️ {self.t('duration')} {dur_str}")
        self.views_lbl.configure(text=f"👁️ {self.t('views')} {views_str}")

        self._set_status_badge(self.t("status_ready"), fg="#2E7D32", bg=("#E8F5E9", "#1B3E20"))
        self._update_estimated_size()

        if thumbnail_url:
            threading.Thread(target=self._load_thumbnail_image, args=(thumbnail_url,), daemon=True).start()

    def _load_thumbnail_image(self, url):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req) as resp:
                raw_data = resp.read()
            img = Image.open(urllib.request.io.BytesIO(raw_data))
            img = img.resize((200, 115), Image.Resampling.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(200, 115))
            self.after(0, lambda: self.thumb_label.configure(image=ctk_img, text=""))
        except Exception:
            pass

    def _on_fetch_error(self, err_msg):
        self.load_btn.configure(state="normal")
        self.video_title_lbl.configure(text=f"{self.t('status_error')}: URL unavailable")
        self._set_status_badge(self.t("status_error"), fg="#C62828", bg=("#FFEBEE", "#4A1212"))

    def _set_status_badge(self, text, fg, bg):
        self.status_badge.configure(text=text, text_color=fg, fg_color=bg)

    # -------------------------------------------------------------------
    #  FFmpeg Auto-Installation
    # -------------------------------------------------------------------
    def _refresh_ffmpeg_status(self):
        self.ffmpeg_available = self._check_ffmpeg()
        if self.ffmpeg_available:
            self.ffmpeg_lbl.configure(text=self.t("ffmpeg_installed"), text_color="#4CAF50")
            self.ffmpeg_install_btn.grid_remove()
        else:
            self.ffmpeg_lbl.configure(text=self.t("ffmpeg_missing"), text_color="#FF9800")
            self.ffmpeg_install_btn.grid(row=4, column=0, columnspan=2, sticky="ew", pady=5)

    def _install_ffmpeg(self):
        self.ffmpeg_install_btn.configure(state="disabled", text="⏳ Installing...")
        def _task():
            try:
                app_dir = self._get_app_dir()
                ffmpeg_dir = os.path.join(app_dir, "ffmpeg")
                os.makedirs(ffmpeg_dir, exist_ok=True)
                url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
                zip_path = os.path.join(tempfile.gettempdir(), "ffmpeg.zip")

                urllib.request.urlretrieve(url, zip_path)
                with zipfile.ZipFile(zip_path, "r") as zf:
                    for member in zf.namelist():
                        if member.endswith("ffmpeg.exe"):
                            zf.extract(member, ffmpeg_dir)
                            exe_path = os.path.join(ffmpeg_dir, member)
                            final_path = os.path.join(ffmpeg_dir, "ffmpeg.exe")
                            if os.path.exists(exe_path) and exe_path != final_path:
                                shutil.move(exe_path, final_path)
                            break
                os.remove(zip_path)
                os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
                self.after(0, self._on_ffmpeg_installed_success)
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("FFmpeg Error", str(e)))
            finally:
                self.after(0, lambda: self.ffmpeg_install_btn.configure(state="normal", text=self.t("ffmpeg_install_btn")))
        threading.Thread(target=_task, daemon=True).start()

    def _on_ffmpeg_installed_success(self):
        self._refresh_ffmpeg_status()
        messagebox.showinfo(self.t("app_title"), "FFmpeg installed successfully!")

    # -------------------------------------------------------------------
    #  Download Execution & Hooks
    # -------------------------------------------------------------------
    def _start_download(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning(self.t("app_title"), self.t("err_no_url"))
            return

        if self.is_downloading:
            return

        self.is_downloading = True
        self.cancel_requested = False
        self.download_btn.configure(state="disabled", text=self.t("downloading_btn"))
        self.cancel_btn.configure(state="normal")
        self.progress_bar.set(0)
        self._set_status_badge(self.t("status_downloading"), fg="#FF9800", bg=("#FFF3E0", "#3E2723"))

        threading.Thread(target=self._download_worker, daemon=True).start()

    def _cancel_download(self):
        if self.is_downloading:
            self.cancel_requested = True
            self.progress_lbl.configure(text=f"🛑 {self.t('status_cancelled')}...")

    def _progress_hook(self, data):
        if self.cancel_requested:
            raise RuntimeError("CANCELLED_BY_USER")

        if data["status"] == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate", 0)
            downloaded = data.get("downloaded_bytes", 0)
            speed = data.get("speed", 0)
            eta = data.get("eta", 0)

            if total > 0:
                percent = downloaded / total
                dl_str = self._format_size(downloaded)
                tot_str = self._format_size(total)
                spd_str = self._format_speed(speed) if speed else "-- KB/s"
                eta_str = f"{eta}s" if eta else "--"

                self.after(0, lambda: self._update_progress_ui(percent, f"⬇️ {dl_str} / {tot_str}", f"⚡ {spd_str} | ⏱️ ETA: {eta_str}"))

        elif data["status"] == "finished":
            self.after(0, lambda: self._update_progress_ui(1.0, f"✅ {self.t('status_completed')}", ""))

    def _update_progress_ui(self, val, msg, speed_eta):
        self.progress_bar.set(val)
        self.progress_lbl.configure(text=msg)
        self.speed_eta_lbl.configure(text=speed_eta)

    def _download_worker(self):
        url = self.url_var.get().strip()
        out_dir = self.download_path.get()
        fmt_selection = self.fmt_seg_btn.get()
        quality = self.quality_var.get()

        ydl_opts = {
            "outtmpl": os.path.join(out_dir, self.filename_tpl_var.get()),
            "progress_hooks": [self._progress_hook],
            "quiet": True,
            "no_warnings": True,
            "noplaylist": not self.playlist_enabled.get(),
            "extractor_args": {"youtube": {"player_client": ["android", "web"]}},
        }

        if fmt_selection == self.t("audio"):
            if self.ffmpeg_available:
                ydl_opts.update({
                    "format": "bestaudio/best",
                    "postprocessors": [{
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": quality.replace("kbps", ""),
                    }]
                })
            else:
                ydl_opts["format"] = "bestaudio/best"
        else:
            match = re.search(r"(\d+)", quality)
            h = match.group(1) if match else None
            if self.ffmpeg_available:
                if h:
                    ydl_opts["format"] = (
                        f"bestvideo[height<={h}][vcodec^=avc1]+bestaudio[acodec^=mp4a]/"
                        f"bestvideo[height<={h}][vcodec^=avc1]+bestaudio[ext=m4a]/"
                        f"bestvideo[height<={h}][vcodec^=avc1]+bestaudio/"
                        f"bestvideo[height<={h}][ext=mp4]+bestaudio[ext=m4a]/"
                        f"bestvideo[height<={h}]+bestaudio/"
                        f"best[height<={h}]/best"
                    )
                else:
                    ydl_opts["format"] = (
                        "bestvideo[vcodec^=avc1]+bestaudio[acodec^=mp4a]/"
                        "bestvideo[vcodec^=avc1]+bestaudio[ext=m4a]/"
                        "bestvideo[vcodec^=avc1]+bestaudio/"
                        "bestvideo[ext=mp4]+bestaudio[ext=m4a]/"
                        "bestvideo+bestaudio/"
                        "best"
                    )
                ydl_opts["merge_output_format"] = "mp4"
                ydl_opts["postprocessor_args"] = {
                    "merger": [
                        "-movflags", "+faststart",
                        "-c:a", "aac",
                    ]
                }
            else:
                ydl_opts["format"] = f"best[height<={h}][vcodec^=avc1]/best[height<={h}][ext=mp4]/best[height<={h}]/best" if h else "best[vcodec^=avc1]/best[ext=mp4]/best"

        if self.subtitle_enabled.get():
            ydl_opts.update({
                "writesubtitles": True,
                "subtitleslangs": [self.sub_lang_var.get().lower()[:2]],
            })

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                if fmt_selection != self.t("audio") and self.ffmpeg_available:
                    ydl.add_post_processor(TwitterCompatibilityPP(ydl))
                self.active_ydl = ydl
                info = ydl.extract_info(url, download=True)

            title = info.get("title", "Video") if info else "Video"
            thumb = info.get("thumbnail") if info else ""
            vid_id = info.get("id") if info else ""

            item = {"url": url, "title": title, "path": out_dir, "video_id": vid_id, "thumb": thumb}
            self.recent_downloads.insert(0, item)
            self._save_recent_downloads()

            self.after(0, lambda t=title: self._on_download_complete(t))

        except RuntimeError as e:
            if "CANCELLED_BY_USER" in str(e):
                self.after(0, self._on_download_cancelled)
            else:
                err_msg = str(e)
                self.after(0, lambda msg=err_msg: self._on_download_failed(msg))
        except Exception as e:
            err_msg = str(e)
            self.after(0, lambda msg=err_msg: self._on_download_failed(msg))

    def _on_download_complete(self, title):
        self._reset_download_state()
        self._set_status_badge(self.t("status_completed"), fg="#2E7D32", bg=("#E8F5E9", "#1B3E20"))
        self.progress_lbl.configure(text=f"✅ {self.t('success_download')}")
        self._refresh_queue_list()
        messagebox.showinfo(self.t("app_title"), f"{self.t('success_download')}\n\n{title}")

    def _on_download_cancelled(self):
        self._reset_download_state()
        self._set_status_badge(self.t("status_cancelled"), fg="#C62828", bg=("#FFEBEE", "#4A1212"))
        self.progress_lbl.configure(text=f"🛑 {self.t('status_cancelled')}")

    def _on_download_failed(self, err):
        self._reset_download_state()
        self._set_status_badge(self.t("status_error"), fg="#C62828", bg=("#FFEBEE", "#4A1212"))
        self.progress_lbl.configure(text=f"❌ {self.t('status_error')}")
        messagebox.showerror(self.t("app_title"), f"Error downloading:\n{err}")

    def _reset_download_state(self):
        self.is_downloading = False
        self.cancel_requested = False
        self.download_btn.configure(state="normal", text=self.t("download_btn"))
        self.cancel_btn.configure(state="disabled")

    # -------------------------------------------------------------------
    #  Queue & History Frame
    # -------------------------------------------------------------------
    def _refresh_queue_list(self):
        for child in self.queue_scroll.winfo_children():
            child.destroy()

        if not self.recent_downloads:
            no_downloads_lbl = ctk.CTkLabel(
                self.queue_scroll,
                text=self.t("no_recent"),
                font=("Arial", 12),
                text_color=("#888888", "#777777")
            )
            no_downloads_lbl.pack(pady=20)
            return

        for item in self.recent_downloads[:10]:
            card = ctk.CTkFrame(self.queue_scroll, height=45, corner_radius=8, fg_color=("#F5F5F5", "#1E1E1E"))
            card.pack(fill="x", pady=3, padx=2)

            play_btn = ctk.CTkButton(
                card,
                text=self.t("open_youtube"),
                width=65,
                height=28,
                corner_radius=14,
                fg_color="#FF4444",
                hover_color="#CC0000",
                font=("Arial", 10, "bold"),
                command=lambda u=item["url"]: webbrowser.open(u)
            )
            play_btn.pack(side="left", padx=8, pady=8)

            title_lbl = ctk.CTkLabel(
                card,
                text=item.get("title", "Download"),
                font=("Arial", 11, "bold"),
                anchor="w"
            )
            title_lbl.pack(side="left", fill="x", expand=True, padx=5)

            open_dir_btn = ctk.CTkButton(
                card,
                text=self.t("open_folder"),
                width=90,
                height=28,
                corner_radius=14,
                fg_color=("#E0E0E0", "#333333"),
                hover_color=("#D0D0D0", "#444444"),
                text_color=("#333333", "#E0E0E0"),
                font=("Arial", 10),
                command=lambda p=item.get("path", self.download_path.get()): os.startfile(p) if os.path.exists(p) else None
            )
            open_dir_btn.pack(side="right", padx=8, pady=8)

    def _clear_queue(self):
        self.recent_downloads.clear()
        self._save_recent_downloads()
        self._refresh_queue_list()

    # -------------------------------------------------------------------
    #  Settings Dialog Window (Multi-language selector)
    # -------------------------------------------------------------------
    def _open_settings_dialog(self):
        dlg = ctk.CTkToplevel(self)
        dlg.title(f"{self.t('settings_title')} - {APP_VERSION}")
        dlg.geometry("380x360")
        dlg.resizable(False, False)
        dlg.transient(self)
        dlg.grab_set()

        title_lbl = ctk.CTkLabel(dlg, text=self.t("settings_title"), font=("Arial", 16, "bold"))
        title_lbl.pack(pady=(15, 5))

        ver_lbl = ctk.CTkLabel(dlg, text=f"BT YouTube Downloader {APP_VERSION}", font=("Arial", 11), text_color=("#888888", "#777777"))
        ver_lbl.pack(pady=(0, 10))

        lang_lbl = ctk.CTkLabel(dlg, text=self.t("language_label"), font=("Arial", 12, "bold"))
        lang_lbl.pack(anchor="w", padx=25, pady=(5, 2))

        lang_map = {
            "English": "en",
            "עברית (Hebrew)": "he",
            "हिंदी (Hindi)": "hi",
            "ไทย (Thai)": "th",
        }

        curr_display = "English"
        for k, v in lang_map.items():
            if v == self.current_lang:
                curr_display = k

        lang_menu = ctk.CTkOptionMenu(
            dlg,
            values=list(lang_map.keys()),
            width=260,
            command=lambda choice: self._change_language(lang_map[choice])
        )
        lang_menu.set(curr_display)
        lang_menu.pack(padx=25, pady=(0, 15))

        theme_lbl = ctk.CTkLabel(dlg, text=self.t("theme_label"), font=("Arial", 12, "bold"))
        theme_lbl.pack(anchor="w", padx=25, pady=(5, 2))

        theme_menu = ctk.CTkOptionMenu(
            dlg,
            values=[self.t("theme_dark"), self.t("theme_light"), self.t("theme_system")],
            width=260,
            command=self._change_theme
        )
        theme_menu.set(self.t("theme_dark"))
        theme_menu.pack(padx=25, pady=(0, 20))

        close_btn = ctk.CTkButton(
            dlg,
            text="Close / סגור",
            width=140,
            height=34,
            corner_radius=17,
            command=dlg.destroy
        )
        close_btn.pack(pady=10)

    def _change_language(self, lang_code):
        self.current_lang = lang_code
        self.title(f"{self.t('app_title')} {APP_VERSION}")

        # 1. Update Header
        self.app_title_lbl.configure(text=f"{self.t('app_title')} {APP_VERSION}")
        self.subtitle_lbl.configure(text=self.t("subtitle"))
        self.url_entry.configure(placeholder_text=self.t("url_placeholder"))
        self.paste_btn.configure(text=self.t("paste"))
        self.load_btn.configure(text=self.t("load"))
        self.settings_btn.configure(text=self.t("settings"))

        # 2. Update Tab Buttons
        self._update_tab_button_texts()

        # 3. Update Options Tab 1 Labels
        self.fmt_lbl.configure(text=self.t("format_label"))
        self.fmt_seg_btn.configure(values=[self.t("video"), self.t("audio"), self.t("best")])
        self.qual_lbl.configure(text=self.t("quality_label"))
        self.path_lbl.configure(text=self.t("save_to"))
        self.browse_btn.configure(text=self.t("browse"))
        self._update_estimated_size()

        # 4. Update Options Tab 2 Labels
        self.sub_chk.configure(text=self.t("subtitles"))
        self.playlist_chk.configure(text=self.t("playlist"))
        self.fn_lbl.configure(text=self.t("filename_tpl"))
        self.ffmpeg_install_btn.configure(text=self.t("ffmpeg_install_btn"))

        # 5. Update Bottom Controls
        self.download_btn.configure(text=self.t("download_btn"))
        self.cancel_btn.configure(text=self.t("cancel_btn"))
        if not self.is_downloading:
            self.progress_lbl.configure(text=f"📌 {self.t('status_ready')}")

        # 6. Update Queue & Info Card
        self.queue_header_lbl.configure(text=f"📋 {self.t('queue_title')}")
        self.clear_queue_btn.configure(text=self.t("clear_queue"))
        if not self.video_info:
            self.video_title_lbl.configure(text=self.t("no_info"))
            self.status_badge.configure(text=self.t("status_ready"))

        self._refresh_ffmpeg_status()
        self._refresh_queue_list()

    def _change_theme(self, choice):
        if choice in ["Dark", "כהה", "डार्क", "มืด"]:
            ctk.set_appearance_mode("Dark")
        elif choice in ["Light", "בהיר", "लाइट", "สว่าง"]:
            ctk.set_appearance_mode("Light")
        else:
            ctk.set_appearance_mode("System")


# -------------------------------------------------------------------
#  Application Entry Point
# -------------------------------------------------------------------
def main():
    app = YouTubeDownloaderApp()
    app.mainloop()


if __name__ == "__main__":
    main()
