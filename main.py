import random, threading, time, requests
from kivy.clock import Clock
from kivy.storage.jsonstore import JsonStore
from kivy.graphics import Color, RoundedRectangle, Line
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.label import MDLabel
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.textfield import MDTextField

URL = "https://mess-6a769-default-rtdb.firebaseio.com"


# Исправленный класс серых пузырьков сообщений без сторонних функций
class GlassBubble(MDBoxLayout):
    def __init__(self, text, is_my_msg=False, current_theme="Dark", **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.size_hint_y = None
        self.padding = 10
        self.spacing = 3

        # Настройка цветов (Светлая или Темная темы)
        if current_theme == "Dark":
            if is_my_msg:
                self.pos_hint = {"right": 0.95}
                bubble_color = (0.2, 0.2, 0.22, 0.9)
                border_color = (0.12, 0.12, 0.14, 1)
                text_color = (1, 1, 1, 1)
            else:
                self.pos_hint = {"left": 0.05}
                bubble_color = (0.14, 0.14, 0.16, 0.9)
                border_color = (0.25, 0.25, 0.28, 1)
                text_color = (0.85, 0.85, 0.9, 1)
        else:
            if is_my_msg:
                self.pos_hint = {"right": 0.95}
                bubble_color = (0.9, 0.9, 0.92, 1)
                border_color = (0.75, 0.75, 0.78, 1)
                text_color = (0, 0, 0, 1)
            else:
                self.pos_hint = {"left": 0.05}
                bubble_color = (0.95, 0.95, 0.97, 1)
                border_color = (0.8, 0.8, 0.83, 1)
                text_color = (0.3, 0.3, 0.35, 1)

        # Рисуем пузырек и окантовку
        with self.canvas.before:
            Color(*bubble_color)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[12, 12, 12, 12])
            Color(*border_color)
            self.border = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, 12), width=1.2)

        self.bind(pos=self.update_rect, size=self.update_rect)

        # Текст с полностью безопасным расчетом авто-высоты
        lbl = MDLabel(text=text, size_hint_y=None, theme_text_color="Custom", text_color=text_color, font_style="Body1")

        # Лямбда-функция берет строго второй элемент, то есть высоту, решая ошибку ValueError
        lbl.bind(texture_size=lambda instance, size: setattr(instance, 'height', size[1]))
        lbl.bind(texture_size=lambda instance, size: setattr(self, 'height', size[1] + 20))
        lbl.bind(texture_size=lambda instance, size: setattr(self, 'width', min(size[0] + 30, 400)))

        self.add_widget(lbl)
        self.size_hint_x = None

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

        # --- ЭКРАН ВХОДА ---
        scr1 = MDScreen(name="login")
        lay1 = MDBoxLayout(orientation="vertical", padding=40, spacing=25, size_hint_y=None, adaptive_height=True,
                           pos_hint={"center_x": 0.5, "center_y": 0.5})
        lay1.add_widget(MDLabel(text="PSK MESSENGER", halign="center", font_style="H4"))
        self.nick_in = MDTextField(hint_text="Введите ваш никнейм...", size_hint_x=0.8, pos_hint={"center_x": 0.5},
                                   mode="rectangle")
        lay1.add_widget(self.nick_in)
        lay1.add_widget(
            MDRaisedButton(text="Войти в чат", pos_hint={"center_x": 0.5}, md_bg_color=(0.25, 0.25, 0.28, 1),
                           on_release=self.register_user))
        scr1.add_widget(lay1)
        self.sm.add_widget(scr1)

        # --- ЭКРАН МЕНЮ ---
        scr2 = MDScreen(name="menu")
        lay2 = MDBoxLayout(orientation="vertical", padding=15, spacing=12)

        # Верхняя панель меню с кнопкой Смены темы
        menu_top_bar = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=45, spacing=10)
        self.info_lbl = MDLabel(text="Мой ID:", font_style="H6", theme_text_color="Secondary")
        self.theme_btn = MDFlatButton(text="☀️ Светлая тема", on_release=self.toggle_theme)
        menu_top_bar.add_widget(self.info_lbl)
        menu_top_bar.add_widget(self.theme_btn)
        lay2.add_widget(menu_top_bar)

        f_lay = MDBoxLayout(orientation="horizontal", spacing=10, size_hint_y=None, height=50)
        self.f_in = MDTextField(hint_text="ID друга", size_hint_x=0.6, mode="rectangle")
        f_lay.add_widget(self.f_in)
        f_lay.add_widget(MDRaisedButton(text="Добавить", size_hint_x=0.4, md_bg_color=(0.25, 0.25, 0.28, 1),
                                        on_release=self.add_friend_chat))
        lay2.add_widget(f_lay)

        g_lay = MDBoxLayout(orientation="horizontal", spacing=10, size_hint_y=None, height=50)
        self.g_in = MDTextField(hint_text="Имя или ID группы", size_hint_x=0.6, mode="rectangle")
        g_lay.add_widget(self.g_in)
        g_lay.add_widget(MDRaisedButton(text="Группа+", size_hint_x=0.4, md_bg_color=(0.2, 0.2, 0.22, 1),
                                        on_release=self.handle_group))
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
        top.add_widget(MDFlatButton(text="<- Назад", theme_text_color="Custom", text_color=(0.5, 0.5, 0.5, 1),
                                    on_release=self.go_to_menu))
        self.c_title = MDLabel(text="Чат", font_style="H6")
        top.add_widget(self.c_title)
        lay3.add_widget(top)

        scroll2 = MDScrollView()
        self.msg_box = MDBoxLayout(orientation="vertical", spacing=15, size_hint_y=None)
        self.msg_box.bind(minimum_height=self.msg_box.setter("height"))
        scroll2.add_widget(self.msg_box)
        lay3.add_widget(scroll2)

        inp_lay = MDBoxLayout(orientation="horizontal", spacing=10, size_hint_y=None, height=55)
        self.msg_in = MDTextField(hint_text="Ваше сообщение...", size_hint_x=0.7, mode="rectangle")
        inp_lay.add_widget(self.msg_in)
        inp_lay.add_widget(MDRaisedButton(text="Отправить", size_hint_x=0.3, md_bg_color=(0.25, 0.25, 0.28, 1),
                                          on_release=self.send_message))
        lay3.add_widget(inp_lay)
        scr3.add_widget(lay3)
        self.sm.add_widget(scr3)

        Clock.schedule_once(self.load_saved_user, 1)
        return self.sm

    def toggle_theme(self, instance):
        # Функция-переключатель: меняет тему туда-обратно и обновляет текст кнопки
        if self.theme_cls.theme_style == "Dark":
            self.theme_cls.theme_style = "Light"
            self.theme_btn.text = "🌙 Темная тема"
        else:
            self.theme_cls.theme_style = "Dark"
            self.theme_btn.text = "☀️ Светлая тема"

        # Перерисовываем экран чата, чтобы старые сообщения тоже перекрасились в новые цвета
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
            try:
                requests.put(f"{URL}/users/{g_id}.json", json={"name": name})
            except:
                pass
            self.info_lbl.text = f"Вы: {name} (ID: {g_id})"
            self.sm.current = "menu"
            self.refresh_chats_list()
            threading.Thread(target=self.check_messages, daemon=True).start()

    def refresh_chats_list(self):
        self.chats_box.clear_widgets()
        self.chats_box.add_widget(
            MDRaisedButton(text="🌍 ОБЩИЙ ГЛОБАЛЬНЫЙ ЧАТ", size_hint_x=1, md_bg_color=(0.25, 0.25, 0.28, 0.5),
                           on_release=lambda x: self.open_chat("global", "Общий чат", "chats")))
        for c in self.my_active_chats:
            btn = MDRaisedButton(text=f"{'💬' if c['type'] == 'chats' else '👥'} {c['title']}", size_hint_x=1,
                                 md_bg_color=(0.2, 0.2, 0.22, 0.8) if c['type'] == 'chats' else (0.15, 0.15, 0.17, 0.8),
                                 on_release=lambda x, t=c['target_id'], n=c['title'], y=c['type']: self.open_chat(t, n,
                                                                                                                  y))
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
            except:
                pass

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
                except:
                    pass
            else:
                g_id = f"group_{random.randint(1000, 9999)}"
                try:
                    requests.put(f"{URL}/groups/{g_id}.json", json={"group_name": entry})
                except:
                    pass
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
            try:
                requests.post(f"{URL}/{self.chat_type}/{self.current_chat_target}/messages.json",
                              json={"user": self.my_nickname, "text": txt})
            except:
                pass
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
                                display_text = f"{text}" if is_mine else f"{user}:\n{text}"

                                # Передаем текущую тему (Dark или Light) внутрь пузырька
                                Clock.schedule_once(lambda dt, t=display_text, m=is_mine: self.msg_box.add_widget(
                                    GlassBubble(text=t, is_my_msg=m, current_theme=self.theme_cls.theme_style)))
                except:
                    pass
            time.sleep(1)


if __name__ == "__main__":
    ChatApp().run()
