import random, threading, time, requests, base64, os
from kivy.clock import Clock
from kivy.storage.jsonstore import JsonStore
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.core.window import Window
from kivy.uix.image import Image as KivyImage
from kivy.uix.behaviors import ButtonBehavior

# Настройки окна для ПК/Телефона
Window.size = (360, 640)
Window.softinput_mode = "resize"

from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRaisedButton, MDFlatButton, MDIconButton
from kivymd.uix.label import MDLabel
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.textfield import MDTextField
from kivymd.uix.card import MDCard
from kivymd.uix.filemanager import MDFileManager

URL = "https://firebaseio.com"

# Делаем кликабельный виджет картинки, чтобы она реагировала на нажатия мышкой/пальцем
class ClickableImage(ButtonBehavior, KivyImage):
    def __init__(self, file_path, callback, **kwargs):
        super().__init__(**kwargs)
        self.source = file_path
        self.size_hint = (1, None)
        self.height = 200
        self.keep_ratio = True
        self.allow_stretch = True
        self.callback = callback

    def on_press(self):
        self.callback(self.source)

# Полностью исправленный класс пузырьков сообщений со скруглениями radius=[12]
class GlassBubble(MDBoxLayout):
    def __init__(self, text, is_my_msg=False, current_theme="Dark", is_media=False, media_type="image", click_callback=None, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.size_hint_y = None
        self.padding = 12
        self.spacing = 5
        
        if current_theme == "Dark":
            self.pos_hint = {"right": 0.95} if is_my_msg else {"left": 0.05}
            bubble_color = (0.2, 0.2, 0.22, 0.9) if is_my_msg else (0.14, 0.14, 0.16, 0.9)
            border_color = (0.12, 0.12, 0.14, 1) if is_my_msg else (0.25, 0.25, 0.28, 1)
            text_color = (1, 1, 1, 1) if is_my_msg else (0.85, 0.85, 0.9, 1)
        else:
            self.pos_hint = {"right": 0.95} if is_my_msg else {"left": 0.05}
            bubble_color = (0.9, 0.9, 0.92, 1) if is_my_msg else (0.95, 0.95, 0.97, 1)
            border_color = (0.75, 0.75, 0.78, 1) if is_my_msg else (0.8, 0.8, 0.83, 1)
            text_color = (0, 0, 0, 1) if is_my_msg else (0.3, 0.3, 0.35, 1)

        with self.canvas.before:
            Color(*bubble_color)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[12])
            Color(*border_color)
            self.border = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, 12), width=1.2)
            
        self.bind(pos=self.update_rect, size=self.update_rect)

        if is_media:
            if media_type == "image":
                try:
                    img_data = base64.b64decode(text.encode('utf-8'))
                    temp_path = f"temp_recv_{random.randint(100,999)}.png"
                    with open(temp_path, "wb") as f:
                        f.write(img_data)
                    
                    img_widget = ClickableImage(file_path=temp_path, callback=click_callback)
                    self.add_widget(img_widget)
                    self.height = 220
                except:
                    self.add_text_lbl("[Ошибка отображения фото]", text_color)
            else:
                self.add_text_lbl("🎥 Отправлено видео (Открыть на ПК/Телефоне)", text_color)
                self.height = 50
        else:
            self.add_text_lbl(text, text_color)

        self.size_hint_x = 0.7

    def add_text_lbl(self, text, text_color):
        lbl = MDLabel(text=text, size_hint_y=None, theme_text_color="Custom", text_color=text_color, font_style="Body1")
        lbl.bind(width=lambda instance, value: setattr(instance, 'text_size', (value, None)))
        lbl.bind(texture_size=lambda instance, size: setattr(instance, 'height', size))
        lbl.bind(texture_size=lambda instance, size: setattr(self, 'height', size + 25))
        self.add_widget(lbl)

    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size
        self.border.rounded_rectangle = (self.x, self.y, self.width, self.height, 12)


class ChatApp(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "BlueGray"
        self.store = JsonStore("user_config.json")
        self.my_id, self.my_nickname, self.current_chat_target, self.chat_type = "", "", "global", "chats"
        self.my_active_chats, self.loaded_messages = [], set()
        self.sm = MDScreenManager()
        
        self.file_manager = MDFileManager(exit_manager=self.exit_file_manager, select_path=self.select_media_path)

        # --- ЭКРАН ВХОДА ---
        scr1 = MDScreen(name="login")
        lay1 = MDBoxLayout(orientation="vertical", padding=80, spacing=30, size_hint=(1, 1))
        lay1.add_widget(MDLabel(text="PSK MESSENGER", halign="center", font_style="H4"))
        self.nick_in = MDTextField(hint_text="Введите ваш никнейм...", size_hint_x=0.9, pos_hint={"center_x": 0.5}, mode="rectangle")
        lay1.add_widget(self.nick_in)
        lay1.add_widget(MDRaisedButton(text="Войти в чат", pos_hint={"center_x": 0.5}, size_hint_x=0.9, height=50, md_bg_color=(0.25, 0.25, 0.28, 1), on_release=self.register_user))
        scr1.add_widget(lay1)
        self.sm.add_widget(scr1)

        # --- ЭКРАН МЕНЮ ---
        scr2 = MDScreen(name="menu")
        lay2 = MDBoxLayout(orientation="vertical", padding=15, spacing=12)
        menu_top_bar = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=45, spacing=10)
        self.info_lbl = MDLabel(text="Мой ID:", font_style="H6", theme_text_color="Secondary")
        self.theme_btn = MDFlatButton(text="☀️ Светлая тема", on_release=self.toggle_theme)
        menu_top_bar.add_widget(self.info_lbl)
        menu_top_bar.add_widget(self.theme_btn)
        lay2.add_widget(menu_top_bar)
        
        f_lay = MDBoxLayout(orientation="horizontal", spacing=10, size_hint_y=None, height=50)
        self.f_in = MDTextField(hint_text="ID друга", size_hint_x=0.6, mode="rectangle")
        f_lay.add_widget(self.f_in)
        f_lay.add_widget(MDRaisedButton(text="Добавить", size_hint_x=0.4, md_bg_color=(0.25, 0.25, 0.28, 1), on_release=self.add_friend_chat))
        lay2.add_widget(f_lay)

        g_lay = MDBoxLayout(orientation="horizontal", spacing=10, size_hint_y=None, height=50)
        self.g_in = MDTextField(hint_text="Имя или ID группы", size_hint_x=0.6, mode="rectangle")
        g_lay.add_widget(self.g_in)
        g_lay.add_widget(MDRaisedButton(text="Группа+", size_hint_x=0.4, md_bg_color=(0.2, 0.2, 0.22, 1), on_release=self.handle_group))
        lay2.add_widget(g_lay)

        scroll1 = MDScrollView()
        self.chats_box = MDBoxLayout(orientation="vertical", spacing=12, size_hint_y=None)
        self.chats_box.bind(minimum_height=self.chats_box.setter("height"))
        scroll1.add_widget(self.chats_box)
        lay2.add_widget(scroll1)
        scr2.add_widget(lay2)
        self.sm.add_widget(scr2)

        # --- ЭКРАН ЧАТА ---
        scr3 = MDScreen(name="chat")
        lay3 = MDBoxLayout(orientation="vertical", padding=15, spacing=10)
        top = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=50, spacing=10)
        top.add_widget(MDFlatButton(text="<- Назад", theme_text_color="Custom", text_color=(0.5, 0.5, 0.5, 1), on_release=self.go_to_menu))
        self.c_title = MDLabel(text="Чат", font_style="H6")
        top.add_widget(self.c_title)
        lay3.add_widget(top)

        scroll2 = MDScrollView()
        self.msg_box = MDBoxLayout(orientation="vertical", spacing=15, size_hint_y=None, padding=10)
        self.msg_box.bind(minimum_height=self.msg_box.setter("height"))
        scroll2.add_widget(self.msg_box)
        lay3.add_widget(scroll2)

        # Создаем плотную черную нижнюю панель с радиусом скругления radius=[0]
        self.inp_lay = MDCard(
            orientation="horizontal", 
            spacing=5, 
            size_hint_y=None, 
            height=55, 
            padding=5, 
            md_bg_color=(0, 0, 0, 1),
            radius=[0]
        )
        
        clip_btn = MDIconButton(icon="paperclip", theme_text_color="Custom", text_color=(0.7, 0.7, 0.75, 1), on_release=self.open_file_manager)
        self.msg_in = MDTextField(hint_text="Ваше сообщение...", size_hint_x=0.6, mode="rectangle")
        self.msg_in.bind(focus=lambda instance, value: self.lift_input_panel(value))
        
        send_btn = MDRaisedButton(text="Отправить", size_hint_x=0.3, md_bg_color=(0.25, 0.25, 0.28, 1), on_release=self.send_message)
        
        self.inp_lay.add_widget(clip_btn)
        self.inp_lay.add_widget(self.msg_in)
        self.inp_lay.add_widget(send_btn)
        lay3.add_widget(self.inp_lay)
        scr3.add_widget(lay3)
        self.sm.add_widget(scr3)

        # --- ЭКРАН ГАЛЕРЕИ ---
        self.scr_viewer = MDScreen(name="viewer")
        viewer_lay = MDBoxLayout(orientation="vertical", padding=10, spacing=10)
        
        viewer_top = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=50)
        viewer_top.add_widget(MDFlatButton(text="<- Назад в чат", theme_text_color="Custom", text_color=(1, 1, 1, 1), on_release=self.close_image_viewer))
        viewer_lay.add_widget(viewer_top)
        
        self.big_img = KivyImage(size_hint=(1, 1), keep_ratio=True, allow_stretch=True)
        viewer_lay.add_widget(self.big_img)
        self.scr_viewer.add_widget(viewer_lay)
        self.sm.add_widget(self.scr_viewer)

        Clock.schedule_once(self.load_saved_user, 1)
        return self.sm
            def open_image_viewer(self, file_path):
        self.big_img.source = file_path
        self.sm.current = "viewer"

    def close_image_viewer(self, instance):
        self.sm.current = "chat"

    def open_file_manager(self, instance):
        path = "/" if os.name != 'nt' else "C:\\"
        self.file_manager.show(path)

    def exit_file_manager(self, *args):
        self.file_manager.close()

    def select_media_path(self, path):
        self.exit_file_manager()
        ext = path.split(".")[-1].lower()
        m_type = "image" if ext in ["png", "jpg", "jpeg", "webp"] else "video"
        threading.Thread(target=self.upload_media_worker, args=(path, m_type), daemon=True).start()

    def upload_media_worker(self, path, m_type):
        try:
            with open(path, "rb") as f:
                encoded_string = base64.b64encode(f.read()).decode('utf-8')
            requests.post(
                f"{URL}/{self.chat_type}/{self.current_chat_target}/messages.json", 
                json={"user": self.my_nickname, "text": encoded_string, "is_media": True, "media_type": m_type}
            )
        except: pass

    def lift_input_panel(self, has_focus):
        if has_focus:
            self.inp_lay.y = 250
        else:
            self.inp_lay.y = 0

    def toggle_theme(self, instance):
        if self.theme_cls.theme_style == "Dark":
            self.theme_cls.theme_style = "Light"
            self.theme_btn.text = "🌙 Темная тема"
        else:
            self.theme_cls.theme_style = "Dark"
            self.theme_btn.text = "☀️ Светлая тема"
        if self.sm.current == "chat":
            self.msg_box.clear_widgets()
            self.loaded_messages.clear()

    def load_saved_user(self, dt):
        if self.store.exists("user"):
            self.my_id = self.store.get("user")["id"]
            self.my_nickname = self.store.get("user")["name"]
            if self.store.exists("active_chats"):
                self.my_active_chats = self.store.get("active_chats")["list"]
            self.info_lbl.text = f"Вы: {self.my_nickname} (ID: {self.my_id})"
            self.sm.current = "menu"
            self.refresh_chats_list()
            threading.Thread(target=self.check_messages, daemon=True).start()

    def register_user(self, instance):
        name = self.nick_in.text.strip()
        if name:
            g_id = f"id_{random.randint(1000, 9999)}"
            self.my_id, self.my_nickname = g_id, name
            self.store.put("user", name=name, id=g_id)
            self.store.put("active_chats", list=[])
            try: requests.put(f"{URL}/users/{g_id}.json", json={"name": name})
            except: pass
            self.info_lbl.text = f"Вы: {name} (ID: {g_id})"
            self.sm.current = "menu"
            self.refresh_chats_list()
            threading.Thread(target=self.check_messages, daemon=True).start()

    def refresh_chats_list(self):
        self.chats_box.clear_widgets()
        self.chats_box.add_widget(MDRaisedButton(text="🌍 ОБЩИЙ ГЛОБАЛЬНЫЙ ЧАТ", size_hint_x=1, md_bg_color=(0.25, 0.25, 0.28, 0.5), on_release=lambda x: self.open_chat("global", "Общий чат", "chats")))
        for c in self.my_active_chats:
            btn = MDRaisedButton(text=f"{'💬' if c['type'] == 'chats' else '👥'} {c['title']}", size_hint_x=1, md_bg_color=(0.2, 0.2, 0.22, 0.8) if c['type'] == 'chats' else (0.15, 0.15, 0.17, 0.8), on_release=lambda x, t=c['target_id'], n=c['title'], y=c['type']: self.open_chat(t, n, y))
            self.chats_box.add_widget(btn)

    def add_friend_chat(self, instance):
        f_id = self.f_in.text.strip()
        if f_id and f_id != self.my_id:
            try:
                res = requests.get(f"{URL}/users/{f_id}.json")
                if res.status_code == 200 and res.json():
                    f_name = res.json().get("name", "Друг")
                    room = "_".join(sorted([self.my_id, f_id]))
                    if not any(c["target_id"] == room for c in self.my_active_chats):
                        self.my_active_chats.append({"target_id": room, "title": f"{f_name} ({f_id})", "type": "chats"})
                        self.store.put("active_chats", list=self.my_active_chats)
                        self.refresh_chats_list()
                    self.f_in.text = ""
            except: pass

    def handle_group(self, instance):
        entry = self.g_in.text.strip()
        if entry:
            if entry.startswith("group_"):
                try:
                    res = requests.get(f"{URL}/groups/{entry}.json")
                    if res.status_code == 200 and res.json():
                        g_name = res.json().get("group_name", "Группа")
                        if not any(c["target_id"] == entry for c in self.my_active_chats):
                            self.my_active_chats.append({"target_id": entry, "title": g_name, "type": "groups"})
                            self.store.put("active_chats", list=self.my_active_chats)
                            self.refresh_chats_list()
                except: pass
            else:
                g_id = f"group_{random.randint(1000, 9999)}"
                try: requests.put(f"{URL}/groups/{g_id}.json", json={"group_name": entry})
                except: pass
                self.my_active_chats.append({"target_id": g_id, "title": f"{entry} ({g_id})", "type": "groups"})
                self.store.put("active_chats", list=self.my_active_chats)
                self.refresh_chats_list()
            self.g_in.text = ""

    def open_chat(self, target, title, ctype):
        self.current_chat_target, self.chat_type = target, ctype
        self.c_title.text = f"Чат: {title}"
        self.msg_box.clear_widgets()
        self.loaded_messages.clear()
        self.sm.current = "chat"

    def go_to_menu(self, instance):
        self.sm.current = "menu"

    def send_message(self, instance):
        txt = self.msg_in.text.strip()
        if txt:
            try: requests.post(f"{URL}/{self.chat_type}/{self.current_chat_target}/messages.json", json={"user": self.my_nickname, "text": txt})
            except: pass
            self.msg_in.text = ""

    def check_messages(self):
        while True:
            if self.sm.current == "chat":
                try:
                    res = requests.get(f"{URL}/{self.chat_type}/{self.current_chat_target}/messages.json")
                    if res.status_code == 200 and res.json():
                        for m_id, m_data in res.json().items():
                            if m_id not in self.loaded_messages:
                                self.loaded_messages.add(m_id)
                                user = m_data.get('user')
                                text = m_data.get('text')
                                is_mine = (user == self.my_nickname)
                                is_m = m_data.get('is_media', False)
                                m_type = m_data.get('media_type', 'image')
                                
                                display_text = text if is_m else (f"{text}" if is_mine else f"{user}:\n{text}")
                                Clock.schedule_once(lambda dt, t=display_text, m=is_mine, is_med=is_m, mt=m_type: self.msg_box.add_widget(GlassBubble(text=t, is_my_msg=m, current_theme=self.theme_cls.theme_style, is_media=is_med, media_type=mt, click_callback=self.open_image_viewer)))
                except: pass
            time.sleep(1)

if __name__ == "__main__":
    from kivy.core.window import Window
    Window.size = (360, 640)
    ChatApp().run()
