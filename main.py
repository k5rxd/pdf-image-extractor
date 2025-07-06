from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image as KivyImage
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.checkbox import CheckBox
from kivy.uix.gridlayout import GridLayout
from kivy.core.window import Window
from kivy.uix.textinput import TextInput

import fitz  # PyMuPDF
from PIL import Image
import io
import os

class ImageItem(BoxLayout):
    def __init__(self, img_data, name, **kwargs):
        super().__init__(orientation='vertical', size_hint_y=None, height=200, **kwargs)
        self.img_data = img_data
        self.name = name
        self.checkbox = CheckBox(size_hint_y=None, height=30)
        self.add_widget(KivyImage(texture=self._get_texture(img_data), size_hint_y=None, height=150))
        self.add_widget(Label(text=name, size_hint_y=None, height=30))
        self.add_widget(self.checkbox)

    def _get_texture(self, data):
        pil_image = Image.open(io.BytesIO(data))
        pil_image.thumbnail((300, 300))
        buf = io.BytesIO()
        pil_image.save(buf, format='PNG')
        buf.seek(0)
        from kivy.core.image import Image as CoreImage
        return CoreImage(buf, ext='png').texture

class PDFExtractor(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        self.add_widget(Button(text='Select PDF', size_hint_y=None, height=50, on_press=self.select_pdf))
        self.scroll = ScrollView()
        self.container = GridLayout(cols=2, spacing=10, size_hint_y=None)
        self.container.bind(minimum_height=self.container.setter('height'))
        self.scroll.add_widget(self.container)
        self.add_widget(self.scroll)
        self.add_widget(Button(text='Save Selected Images', size_hint_y=None, height=50, on_press=self.save_images))
        self.extracted = []

    def select_pdf(self, instance):
        chooser = FileChooserIconView()
        popup = Popup(title='Choose PDF', content=chooser, size_hint=(0.9, 0.9))

        def on_selection(*args):
            if chooser.selection:
                popup.dismiss()
                self.extract_images(chooser.selection[0])

        chooser.bind(on_submit=lambda *x: on_selection())
        popup.open()

    def extract_images(self, pdf_path):
        self.container.clear_widgets()
        doc = fitz.open(pdf_path)
        self.extracted = []
        for page_num in range(len(doc)):
            images = doc.get_page_images(page_num)
            for idx, img in enumerate(images):
                xref = img[0]
                base = doc.extract_image(xref)
                data = base['image']
                name = f"p{page_num + 1}_i{idx + 1}.png"
                item = ImageItem(data, name)
                self.container.add_widget(item)
                self.extracted.append(item)

    def save_images(self, instance):
        layout = BoxLayout(orientation='vertical')
        path_input = TextInput(hint_text='Enter save directory path')
        layout.add_widget(path_input)
        layout.add_widget(Button(text='Save', on_press=lambda x: self._do_save(path_input.text)))
        popup = Popup(title='Save Location', content=layout, size_hint=(0.8, 0.4))
        popup.open()
        self._save_popup = popup

    def _do_save(self, folder):
        if not os.path.exists(folder):
            os.makedirs(folder)
        count = 0
        for item in self.extracted:
            if item.checkbox.active:
                with open(os.path.join(folder, item.name), 'wb') as f:
                    f.write(item.img_data)
                count += 1
        self._save_popup.dismiss()
        popup = Popup(title='Done', content=Label(text=f'Saved {count} image(s).'), size_hint=(0.6, 0.3))
        popup.open()

class ExtractorApp(App):
    def build(self):
        Window.clearcolor = (0.1, 0.1, 0.1, 1)
        return PDFExtractor()

if __name__ == '__main__':
    ExtractorApp().run()
