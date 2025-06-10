import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import sys
import os
import re
import threading
import webbrowser
from flask import Flask, render_template_string
from bs4 import BeautifulSoup, NavigableString
import tempfile
import base64
from PIL import Image, ImageTk
import mimetypes

class HTMLTemplateEditor:
    def __init__(self):
        # Cấu hình customtkinter
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Khởi tạo cửa sổ chính
        self.root = ctk.CTk()
        self.root.title("HTML Template Editor")
        self.root.geometry("1200x800")
        
        # Biến lưu trữ
        self.link_elements = []  # Thêm dòng này sau self.image_elements = []
        self.html_file_path = None
        self.html_content = ""
        self.text_elements = []
        self.image_elements = []
        self.flask_app = None
        self.flask_thread = None
        self.temp_html_file = None
        
        # Tạo giao diện
        self.create_widgets()
        
        # Kiểm tra đường dẫn file từ command line
        self.check_command_line_args()
    
    def create_text_tab(self):
        """Tạo tab chỉnh sửa văn bản"""
        # Tạo scrollable frame cho text
        self.text_scrollable_frame = ctk.CTkScrollableFrame(self.text_tab)
        self.text_scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Bind sự kiện cuộn chuột/touchpad
        self.bind_mousewheel(self.text_scrollable_frame)
        self.text_scrollable_frame.bind("<Button-1>", lambda e: self.text_scrollable_frame.focus_set())
        
        # Label hướng dẫn
        instruction_label = ctk.CTkLabel(
            self.text_scrollable_frame,
            text="Chọn file HTML để bắt đầu chỉnh sửa văn bản",
            font=ctk.CTkFont(size=16)
        )
        instruction_label.pack(pady=20)
    
    def create_image_tab(self):
        """Tạo tab chỉnh sửa hình ảnh"""
        # Tạo scrollable frame cho image
        self.image_scrollable_frame = ctk.CTkScrollableFrame(self.image_tab)
        self.image_scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Bind sự kiện cuộn chuột/touchpad
        self.bind_mousewheel(self.image_scrollable_frame)
        self.image_scrollable_frame.bind("<Button-1>", lambda e: self.image_scrollable_frame.focus_set())
        
        # Label hướng dẫn
        instruction_label = ctk.CTkLabel(
            self.image_scrollable_frame,
            text="Chọn file HTML để bắt đầu chỉnh sửa hình ảnh",
            font=ctk.CTkFont(size=16)
        )
        instruction_label.pack(pady=20)

    def create_link_tab(self):
        """Tạo tab chỉnh sửa liên kết"""
        # Tạo scrollable frame cho link
        self.link_scrollable_frame = ctk.CTkScrollableFrame(self.link_tab)
        self.link_scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Bind sự kiện cuộn chuột/touchpad
        self.bind_mousewheel(self.link_scrollable_frame)
        self.link_scrollable_frame.bind("<Button-1>", lambda e: self.link_scrollable_frame.focus_set())

        # Label hướng dẫn
        instruction_label = ctk.CTkLabel(
            self.link_scrollable_frame,
            text="Chọn file HTML để bắt đầu chỉnh sửa liên kết",
            font=ctk.CTkFont(size=16)
        )
        instruction_label.pack(pady=20)

    
    def bind_mousewheel(self, widget):
        """Bind sự kiện cuộn chuột/touchpad cho widget một cách ổn định"""
        def _on_mousewheel(event):
            try:
                # Lấy canvas từ scrollable frame
                canvas = widget._parent_canvas
                
                # Tính toán delta phù hợp với hệ điều hành
                if event.delta:
                    delta = event.delta
                elif event.num == 4:
                    delta = 120
                elif event.num == 5:
                    delta = -120
                else:
                    return
                
                # Cuộn với tốc độ phù hợp
                scroll_amount = int(-1 * (delta / 120))
                canvas.yview_scroll(scroll_amount, "units")
                
            except Exception:
                pass
        
        # Bind trực tiếp cho toàn bộ ứng dụng khi focus vào scrollable area
        def _on_enter(event):
            # Bind cho Windows và macOS
            self.root.bind_all("<MouseWheel>", _on_mousewheel)
            # Bind cho Linux
            self.root.bind_all("<Button-4>", _on_mousewheel)
            self.root.bind_all("<Button-5>", _on_mousewheel)
            # Bind thêm cho touchpad
            self.root.bind_all("<Shift-MouseWheel>", _on_mousewheel)
            
        def _on_leave(event):
            try:
                self.root.unbind_all("<MouseWheel>")
                self.root.unbind_all("<Button-4>")
                self.root.unbind_all("<Button-5>")
                self.root.unbind_all("<Shift-MouseWheel>")
            except:
                pass
        
        # Bind events
        widget.bind('<Enter>', _on_enter)
        widget.bind('<Leave>', _on_leave)
        
        # Bind recursive cho tất cả children
        def bind_recursive(w):
            w.bind('<Enter>', _on_enter)
            try:
                for child in w.winfo_children():
                    bind_recursive(child)
            except:
                pass
        
        # Đợi một chút rồi bind cho children
        self.root.after(100, lambda: bind_recursive(widget))
    
    def check_command_line_args(self):
        """Kiểm tra nếu có đường dẫn file HTML từ command line"""
        if len(sys.argv) > 1:
            file_path = sys.argv[1]
            if os.path.exists(file_path) and file_path.endswith('.html'):
                self.html_file_path = file_path
                self.load_html_file()
            else:
                messagebox.showerror("Lỗi", f"File không tồn tại hoặc không phải file HTML: {file_path}")
    
    def create_widgets(self):
        """Tạo các widget cho giao diện"""
        # Frame chính
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Frame cho các nút điều khiển
        control_frame = ctk.CTkFrame(main_frame)
        control_frame.pack(fill="x", padx=10, pady=5)
        
        # Nút chọn file
        self.select_file_btn = ctk.CTkButton(
            control_frame, 
            text="Chọn File HTML", 
            command=self.select_html_file,
            width=120
        )
        self.select_file_btn.pack(side="left", padx=5)
        
        # Label hiển thị đường dẫn file
        self.file_path_label = ctk.CTkLabel(
            control_frame, 
            text="Chưa chọn file", 
            anchor="w"
        )
        self.file_path_label.pack(side="left", padx=10, fill="x", expand=True)
        
        # Nút Preview
        self.preview_btn = ctk.CTkButton(
            control_frame, 
            text="Preview", 
            command=self.preview_html,
            width=80,
            state="disabled"
        )
        self.preview_btn.pack(side="right", padx=5)
        
        # Nút Save As
        self.save_as_btn = ctk.CTkButton(
            control_frame, 
            text="Lưu Thành", 
            command=self.save_as_html,
            width=80,
            state="disabled"
        )
        self.save_as_btn.pack(side="right", padx=5)
        
        # Nút Save
        self.save_btn = ctk.CTkButton(
            control_frame, 
            text="Lưu", 
            command=self.save_html,
            width=60,
            state="disabled"
        )
        self.save_btn.pack(side="right", padx=5)
        
        # Frame cho nội dung chỉnh sửa với tab
        content_frame = ctk.CTkFrame(main_frame)
        content_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Tạo tabview
        self.tabview = ctk.CTkTabview(content_frame)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Tab chỉnh sửa text
        self.text_tab = self.tabview.add("Chỉnh sửa văn bản")
        self.create_text_tab()
        
        # Tab chỉnh sửa hình ảnh
        self.image_tab = self.tabview.add("Chỉnh sửa hình ảnh")
        self.create_image_tab()

        # Tab chỉnh sửa link
        self.link_tab = self.tabview.add("Chỉnh sửa liên kết")
        self.create_link_tab()
    
    def select_html_file(self):
        """Chọn file HTML"""
        file_path = filedialog.askopenfilename(
            title="Chọn file HTML",
            filetypes=[("HTML files", "*.html"), ("All files", "*.*")]
        )
        if file_path:
            self.html_file_path = file_path
            self.load_html_file()
    
    def load_html_file(self):
        """Tải và phân tích file HTML"""
        try:
            with open(self.html_file_path, 'r', encoding='utf-8') as file:
                self.html_content = file.read()
            
            # Cập nhật label đường dẫn
            self.file_path_label.configure(text=f"File: {os.path.basename(self.html_file_path)}")
            
            # Phân tích HTML và tạo giao diện chỉnh sửa
            self.parse_html_and_create_editors()
            
            # Kích hoạt các nút
            self.save_btn.configure(state="normal")
            self.save_as_btn.configure(state="normal")
            self.preview_btn.configure(state="normal")
            
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể đọc file HTML: {str(e)}")
    
    def parse_html_and_create_editors(self):
        """Phân tích HTML và tạo các editor cho text và hình ảnh"""
        # Xóa các widget cũ trong scrollable frames
        for widget in self.text_scrollable_frame.winfo_children():
            widget.destroy()
        for widget in self.image_scrollable_frame.winfo_children():
            widget.destroy()
        for widget in self.link_scrollable_frame.winfo_children():  # Thêm dòng này
            widget.destroy()
        
        # Parse HTML với BeautifulSoup
        soup = BeautifulSoup(self.html_content, 'html.parser')
        self.text_elements = []
        self.image_elements = []
        
        # Tìm tất cả các text elements
        text_tags = ['title', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'span', 'div', 'a', 'button', 'label', 'li', 'td', 'th']
        
        for tag_name in text_tags:
            elements = soup.find_all(tag_name)
            for element in elements:
                if element.string and element.string.strip():
                    self.text_elements.append({
                        'element': element,
                        'tag': tag_name,
                        'original_text': element.string.strip(),
                        'widget': None
                    })
        
        # Tìm tất cả các img elements
        img_elements = soup.find_all('img')
        for i, img in enumerate(img_elements):
            src = img.get('src', '')
            alt = img.get('alt', '')
            title = img.get('title', '')
            
            self.image_elements.append({
                'element': img,
                'index': i,
                'original_src': src,
                'alt': alt,
                'title': title,
                'widgets': {}
            })
        
        # Tìm tất cả các link elements
        link_elements = soup.find_all('a')
        for i, link in enumerate(link_elements):
            href = link.get('href', '')
            text = link.get_text(strip=True) if link.get_text(strip=True) else ''
            title = link.get('title', '')
            target = link.get('target', '')

            self.link_elements.append({
                'element': link,
                'index': i,
                'original_href': href,
                'text': text,
                'title': title,
                'target': target,
                'widgets': {}
            })
        
        # Tạo giao diện chỉnh sửa text
        self.create_text_editors()
        
        # Tạo giao diện chỉnh sửa image
        self.create_image_editors()

        # Tạo giao diện chỉnh sửa link
        self.create_link_editors()
    
    def create_text_editors(self):
        """Tạo các editor cho text elements"""
        if not self.text_elements:
            no_text_label = ctk.CTkLabel(
                self.text_scrollable_frame,
                text="Không tìm thấy text nào để chỉnh sửa trong file HTML",
                font=ctk.CTkFont(size=14)
            )
            no_text_label.pack(pady=20)
            return
        
        # Tạo editor cho mỗi text element
        for i, text_data in enumerate(self.text_elements):
            self.create_text_editor(i, text_data)
        
        # Bind lại mousewheel cho các widget mới được tạo và refresh focus
        self.root.after(200, lambda: self.bind_mousewheel(self.text_scrollable_frame))
        self.root.after(300, lambda: self.text_scrollable_frame.focus_set())
    
    def create_image_editors(self):
        """Tạo các editor cho image elements"""
        if not self.image_elements:
            no_image_label = ctk.CTkLabel(
                self.image_scrollable_frame,
                text="Không tìm thấy hình ảnh nào để chỉnh sửa trong file HTML",
                font=ctk.CTkFont(size=14)
            )
            no_image_label.pack(pady=20)
            return
        
        # Tạo editor cho mỗi image element
        for i, image_data in enumerate(self.image_elements):
            self.create_image_editor(i, image_data)
        
        # Bind lại mousewheel cho các widget mới được tạo và refresh focus
        self.root.after(200, lambda: self.bind_mousewheel(self.image_scrollable_frame))
        self.root.after(300, lambda: self.image_scrollable_frame.focus_set())
    
    def create_link_editors(self):
        """Tạo các editor cho link elements"""
        if not self.link_elements:
            no_link_label = ctk.CTkLabel(
                self.link_scrollable_frame,
                text="Không tìm thấy liên kết nào để chỉnh sửa trong file HTML",
                font=ctk.CTkFont(size=14)
            )
            no_link_label.pack(pady=20)
            return
    
        # Tạo editor cho mỗi link element
        for i, link_data in enumerate(self.link_elements):
            self.create_link_editor(i, link_data)

        # Bind lại mousewheel cho các widget mới được tạo và refresh focus
        self.root.after(200, lambda: self.bind_mousewheel(self.link_scrollable_frame))
        self.root.after(300, lambda: self.link_scrollable_frame.focus_set())

    def create_link_editor(self, index, link_data):
        """Tạo editor cho một link element"""
        # Frame container cho mỗi link editor
        editor_frame = ctk.CTkFrame(self.link_scrollable_frame)
        editor_frame.pack(fill="x", padx=5, pady=5)
        
        # Label mô tả
        title_label = ctk.CTkLabel(
            editor_frame,
            text=f"Liên kết #{index + 1}",
            font=ctk.CTkFont(weight="bold", size=14)
        )
        title_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        # Text liên kết
        text_label = ctk.CTkLabel(editor_frame, text="Văn bản hiển thị:")
        text_label.pack(anchor="w", padx=10, pady=(5, 2))
        
        text_entry = ctk.CTkEntry(editor_frame, height=35)
        text_entry.insert(0, link_data['text'])
        text_entry.pack(fill="x", padx=10, pady=(0, 5))
        
        # URL/Href
        href_label = ctk.CTkLabel(editor_frame, text="Đường dẫn (URL):")
        href_label.pack(anchor="w", padx=10, pady=(5, 2))
        
        href_entry = ctk.CTkEntry(editor_frame, height=35)
        href_entry.insert(0, link_data['original_href'])
        href_entry.pack(fill="x", padx=10, pady=(0, 5))
        
        # Title
        title_text_label = ctk.CTkLabel(editor_frame, text="Tiêu đề liên kết (Title):")
        title_text_label.pack(anchor="w", padx=10, pady=(5, 2))
        
        title_entry = ctk.CTkEntry(editor_frame, height=35)
        title_entry.insert(0, link_data['title'])
        title_entry.pack(fill="x", padx=10, pady=(0, 5))
        
        # Target
        target_label = ctk.CTkLabel(editor_frame, text="Cách mở liên kết:")
        target_label.pack(anchor="w", padx=10, pady=(5, 2))
        
        target_combobox = ctk.CTkComboBox(
            editor_frame,
            values=["", "_blank", "_self", "_parent", "_top"],
            height=35
        )
        target_combobox.set(link_data['target'])
        target_combobox.pack(fill="x", padx=10, pady=(0, 10))
        
        # Lưu widgets vào link_data
        link_data['widgets'] = {
            'text_entry': text_entry,
            'href_entry': href_entry,
            'title_entry': title_entry,
            'target_combobox': target_combobox
        }


    def create_text_editor(self, index, text_data):
        """Tạo editor cho một text element"""
        # Frame container cho mỗi editor
        editor_frame = ctk.CTkFrame(self.text_scrollable_frame)
        editor_frame.pack(fill="x", padx=5, pady=5)
        
        # Label mô tả tag
        tag_description = self.get_tag_description(text_data['tag'])
        tag_label = ctk.CTkLabel(
            editor_frame,
            text=f"{tag_description} ({text_data['tag'].upper()})",
            font=ctk.CTkFont(weight="bold")
        )
        tag_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        # Text editor
        if len(text_data['original_text']) > 100:  # Text dài dùng textbox
            text_widget = ctk.CTkTextbox(editor_frame, height=80)
            text_widget.insert("1.0", text_data['original_text'])
        else:  # Text ngắn dùng entry
            text_widget = ctk.CTkEntry(editor_frame, height=35)
            text_widget.insert(0, text_data['original_text'])
        
        text_widget.pack(fill="x", padx=10, pady=(0, 10))
        
        # Lưu widget vào text_data
        text_data['widget'] = text_widget
    
    def create_image_editor(self, index, image_data):
        """Tạo editor cho một image element"""
        # Frame container cho mỗi image editor
        editor_frame = ctk.CTkFrame(self.image_scrollable_frame)
        editor_frame.pack(fill="x", padx=5, pady=5)
        
        # Label mô tả
        title_label = ctk.CTkLabel(
            editor_frame,
            text=f"Hình ảnh #{index + 1}",
            font=ctk.CTkFont(weight="bold", size=14)
        )
        title_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        # Frame cho preview image
        preview_frame = ctk.CTkFrame(editor_frame)
        preview_frame.pack(fill="x", padx=10, pady=5)
        
        # Preview image
        preview_label = ctk.CTkLabel(preview_frame, text="Preview:")
        preview_label.pack(anchor="w", padx=5, pady=2)
        
        # Image preview widget
        image_preview = ctk.CTkLabel(preview_frame, text="Không thể tải hình ảnh")
        image_preview.pack(padx=5, pady=5)
        
        # Load và hiển thị preview
        self.load_image_preview(image_data['original_src'], image_preview)
        
        # Source URL/Path
        src_label = ctk.CTkLabel(editor_frame, text="Đường dẫn hình ảnh:")
        src_label.pack(anchor="w", padx=10, pady=(5, 2))
        
        src_entry = ctk.CTkEntry(editor_frame, height=35)
        src_entry.insert(0, image_data['original_src'])
        src_entry.pack(fill="x", padx=10, pady=(0, 5))
        
        # Alt text
        alt_label = ctk.CTkLabel(editor_frame, text="Văn bản thay thế (Alt):")
        alt_label.pack(anchor="w", padx=10, pady=(5, 2))
        
        alt_entry = ctk.CTkEntry(editor_frame, height=35)
        alt_entry.insert(0, image_data['alt'])
        alt_entry.pack(fill="x", padx=10, pady=(0, 5))
        
        # Title
        title_text_label = ctk.CTkLabel(editor_frame, text="Tiêu đề hình ảnh (Title):")
        title_text_label.pack(anchor="w", padx=10, pady=(5, 2))
        
        title_entry = ctk.CTkEntry(editor_frame, height=35)
        title_entry.insert(0, image_data['title'])
        title_entry.pack(fill="x", padx=10, pady=(0, 5))
        
        # Buttons frame
        buttons_frame = ctk.CTkFrame(editor_frame)
        buttons_frame.pack(fill="x", padx=10, pady=5)
        
        # Button chọn file từ máy
        upload_btn = ctk.CTkButton(
            buttons_frame,
            text="Chọn ảnh từ máy",
            command=lambda: self.upload_image(src_entry, image_preview),
            width=120
        )
        upload_btn.pack(side="left", padx=5, pady=5)
        
        # Button preview URL
        preview_btn = ctk.CTkButton(
            buttons_frame,
            text="Preview URL",
            command=lambda: self.preview_image_url(src_entry.get(), image_preview),
            width=100
        )
        preview_btn.pack(side="left", padx=5, pady=5)
        
        # Lưu widgets vào image_data
        image_data['widgets'] = {
            'src_entry': src_entry,
            'alt_entry': alt_entry,
            'title_entry': title_entry,
            'preview': image_preview
        }
    
    def load_image_preview(self, src, preview_widget):
        """Tải và hiển thị preview hình ảnh"""
        try:
            if src.startswith('data:image'):
                # Base64 image
                header, data = src.split(',', 1)
                image_data = base64.b64decode(data)
                
                # Tạo file tạm để PIL có thể đọc
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
                temp_file.write(image_data)
                temp_file.close()
                
                # Load với PIL
                pil_image = Image.open(temp_file.name)
                os.unlink(temp_file.name)  # Xóa file tạm
                
            elif src.startswith('http'):
                # URL image - không preview được trong app
                preview_widget.configure(text=f"URL: {src[:50]}...")
                return
            else:
                # Local file path
                if os.path.exists(src):
                    pil_image = Image.open(src)
                else:
                    # Thử relative path
                    if self.html_file_path:
                        base_dir = os.path.dirname(self.html_file_path)
                        full_path = os.path.join(base_dir, src)
                        if os.path.exists(full_path):
                            pil_image = Image.open(full_path)
                        else:
                            preview_widget.configure(text=f"File không tồn tại: {src}")
                            return
                    else:
                        preview_widget.configure(text=f"File không tồn tại: {src}")
                        return
            
            # Resize image để preview
            pil_image.thumbnail((150, 150), Image.Resampling.LANCZOS)
            
            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(pil_image)
            
            # Update preview
            preview_widget.configure(image=photo, text="")
            preview_widget.image = photo  # Keep a reference
            
        except Exception as e:
            preview_widget.configure(text=f"Lỗi tải ảnh: {str(e)}")
    
    def upload_image(self, src_entry, preview_widget):
        """Upload hình ảnh từ máy và convert thành base64"""
        file_path = filedialog.askopenfilename(
            title="Chọn hình ảnh",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.gif *.bmp *.webp"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            try:
                # Đọc file và convert thành base64
                with open(file_path, 'rb') as f:
                    image_data = f.read()
                
                # Xác định mime type
                mime_type = mimetypes.guess_type(file_path)[0]
                if not mime_type:
                    mime_type = 'image/png'
                
                # Tạo data URL
                base64_data = base64.b64encode(image_data).decode('utf-8')
                data_url = f"data:{mime_type};base64,{base64_data}"
                
                # Update src entry
                src_entry.delete(0, 'end')
                src_entry.insert(0, data_url)
                
                # Update preview
                self.load_image_preview(data_url, preview_widget)
                
                messagebox.showinfo("Thành công", "Đã upload hình ảnh thành công!")
                
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể upload hình ảnh: {str(e)}")
    
    def preview_image_url(self, url, preview_widget):
        """Preview hình ảnh từ URL"""
        if url.strip():
            self.load_image_preview(url.strip(), preview_widget)
        else:
            preview_widget.configure(text="Vui lòng nhập URL hình ảnh")
    
    def get_tag_description(self, tag):
        """Trả về mô tả cho từng loại tag"""
        descriptions = {
            'title': 'Tiêu đề trang',
            'h1': 'Tiêu đề chính',
            'h2': 'Tiêu đề phụ 1',
            'h3': 'Tiêu đề phụ 2',
            'h4': 'Tiêu đề phụ 3',
            'h5': 'Tiêu đề phụ 4',
            'h6': 'Tiêu đề phụ 5',
            'p': 'Đoạn văn',
            'span': 'Văn bản nhỏ',
            'div': 'Nội dung khối',
            'a': 'Liên kết',
            'button': 'Nút bấm',
            'label': 'Nhãn',
            'li': 'Mục danh sách',
            'td': 'Ô bảng',
            'th': 'Tiêu đề bảng'
        }
        return descriptions.get(tag, 'Văn bản')
    
    def get_updated_html(self):
        """Lấy HTML đã được cập nhật với text và image mới"""
        # Parse HTML lại
        soup = BeautifulSoup(self.html_content, 'html.parser')
        
        # Cập nhật text cho từng element
        for text_data in self.text_elements:
            element = text_data['element']
            widget = text_data['widget']
            
            if widget:
                # Lấy text mới từ widget
                if isinstance(widget, ctk.CTkTextbox):
                    new_text = widget.get("1.0", "end-1c").strip()
                else:  # CTkEntry
                    new_text = widget.get().strip()
                
                # Tìm element tương ứng trong soup mới và cập nhật
                elements = soup.find_all(text_data['tag'])
                for elem in elements:
                    if elem.string and elem.string.strip() == text_data['original_text']:
                        elem.string.replace_with(new_text)
                        break
        
        # Cập nhật image cho từng element
        for image_data in self.image_elements:
            widgets = image_data['widgets']
            if widgets:
                # Lấy giá trị mới từ widgets
                new_src = widgets['src_entry'].get().strip()
                new_alt = widgets['alt_entry'].get().strip()
                new_title = widgets['title_entry'].get().strip()
                
                # Tìm img element tương ứng và cập nhật
                img_elements = soup.find_all('img')
                if image_data['index'] < len(img_elements):
                    img_elem = img_elements[image_data['index']]
                    
                    # Cập nhật attributes
                    if new_src:
                        img_elem['src'] = new_src
                    if new_alt:
                        img_elem['alt'] = new_alt
                    else:
                        # Xóa attribute nếu rỗng
                        if 'alt' in img_elem.attrs:
                            del img_elem['alt']
                    
                    if new_title:
                        img_elem['title'] = new_title
                    else:
                        # Xóa attribute nếu rỗng
                        if 'title' in img_elem.attrs:
                            del img_elem['title']
            
        # Cập nhật link cho từng element
        for link_data in self.link_elements:
            widgets = link_data['widgets']
            if widgets:
                # Lấy giá trị mới từ widgets
                new_text = widgets['text_entry'].get().strip()
                new_href = widgets['href_entry'].get().strip()
                new_title = widgets['title_entry'].get().strip()
                new_target = widgets['target_combobox'].get().strip()
                
                # Tìm link element tương ứng và cập nhật
                link_elements = soup.find_all('a')
                if link_data['index'] < len(link_elements):
                    link_elem = link_elements[link_data['index']]
                    
                    # Cập nhật text content
                    if new_text:
                        link_elem.string = new_text
                    
                    # Cập nhật attributes
                    if new_href:
                        link_elem['href'] = new_href
                    
                    if new_title:
                        link_elem['title'] = new_title
                    else:
                        if 'title' in link_elem.attrs:
                            del link_elem['title']
                    
                    if new_target:
                        link_elem['target'] = new_target
                    else:
                        if 'target' in link_elem.attrs:
                            del link_elem['target']

        
        return str(soup)
    
    def save_html(self):
        """Lưu HTML đã chỉnh sửa vào file gốc"""
        try:
            updated_html = self.get_updated_html()
            with open(self.html_file_path, 'w', encoding='utf-8') as file:
                file.write(updated_html)
            messagebox.showinfo("Thành công", "Đã lưu file HTML thành công!")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể lưu file: {str(e)}")
    
    def save_as_html(self):
        """Lưu HTML đã chỉnh sửa vào file mới"""
        file_path = filedialog.asksaveasfilename(
            title="Lưu file HTML",
            defaultextension=".html",
            filetypes=[("HTML files", "*.html"), ("All files", "*.*")]
        )
        if file_path:
            try:
                updated_html = self.get_updated_html()
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write(updated_html)
                messagebox.showinfo("Thành công", f"Đã lưu file HTML thành công tại: {file_path}")
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể lưu file: {str(e)}")
    
    def preview_html(self):
        """Preview HTML bằng Flask với file tạm thời chứa các chỉnh sửa"""
        try:
            # Dừng Flask server cũ nếu có
            if self.flask_thread and self.flask_thread.is_alive():
                # Tạo request để shutdown server
                import requests
                try:
                    requests.get('http://127.0.0.1:5000/shutdown', timeout=1)
                except:
                    pass
            
            # Lấy HTML đã cập nhật với các chỉnh sửa
            updated_html = self.get_updated_html()
            
            # Tạo file HTML tạm thời
            temp_dir = tempfile.gettempdir()
            self.temp_html_file = os.path.join(temp_dir, 'html_editor_preview.html')
            
            with open(self.temp_html_file, 'w', encoding='utf-8') as f:
                f.write(updated_html)
            
            # Tạo Flask app mới
            self.flask_app = Flask(__name__)
            
            @self.flask_app.route('/')
            def preview():
                # Đọc file tạm thời để đảm bảo luôn có nội dung mới nhất
                with open(self.temp_html_file, 'r', encoding='utf-8') as f:
                    return f.read()
            
            @self.flask_app.route('/shutdown')
            def shutdown():
                # Xóa file tạm thời khi shutdown
                try:
                    if os.path.exists(self.temp_html_file):
                        os.remove(self.temp_html_file)
                except:
                    pass
                
                func = request.environ.get('werkzeug.server.shutdown')
                if func is None:
                    raise RuntimeError('Not running with the Werkzeug Server')
                func()
                return 'Server shutting down...'
            
            # Chạy Flask trong thread riêng
            def run_flask():
                self.flask_app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)
            
            self.flask_thread = threading.Thread(target=run_flask)
            self.flask_thread.daemon = True
            self.flask_thread.start()
            
            # Đợi một chút để server khởi động rồi mở trình duyệt
            threading.Timer(1.5, lambda: webbrowser.open('http://127.0.0.1:5000')).start()
            
            # Hiển thị thông báo
            def show_preview_message():
            	try:
            		if self.root.winfo_exists():  # Kiểm tra ứng dụng còn tồn tại
            			messagebox.showinfo("Preview", "Đang khởi động preview server...\nTrình duyệt sẽ tự động mở trong giây lát.")
            	except:
            		pass
            show_preview_message()
            
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể khởi động preview: {str(e)}")
    
    def run(self):
        """Chạy ứng dụng"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()
    
    def on_closing(self):
        """Xử lý khi đóng ứng dụng"""
        # Dừng Flask server nếu đang chạy
        if self.flask_thread and self.flask_thread.is_alive():
            try:
                import requests
                requests.get('http://127.0.0.1:5000/shutdown', timeout=1)
            except:
                pass
        
        # Xóa file HTML tạm thời nếu có
        if self.temp_html_file and os.path.exists(self.temp_html_file):
            try:
                os.remove(self.temp_html_file)
            except:
                pass
        
        self.root.destroy()

if __name__ == "__main__":
    app = HTMLTemplateEditor()
    app.run()
