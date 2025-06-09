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
        self.html_file_path = None
        self.html_content = ""
        self.text_elements = []
        self.flask_app = None
        self.flask_thread = None
        self.temp_html_file = None
        
        # Tạo giao diện
        self.create_widgets()
        
        # Kiểm tra đường dẫn file từ command line
        self.check_command_line_args()
    
    def bind_mousewheel(self, widget):
        """Bind sự kiện cuộn chuột/touchpad cho widget một cách ổn định"""
        def _on_mousewheel(event):
            try:
                # Lấy canvas từ scrollable frame
                canvas = self.scrollable_frame._parent_canvas
                
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
        
        # Frame cho nội dung chỉnh sửa với thanh cuộn
        content_frame = ctk.CTkFrame(main_frame)
        content_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Tạo scrollable frame
        self.scrollable_frame = ctk.CTkScrollableFrame(content_frame)
        self.scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Bind sự kiện cuộn chuột/touchpad cho scrollable frame
        self.bind_mousewheel(self.scrollable_frame)
        
        # Thêm focus tracking để cải thiện touchpad
        self.scrollable_frame.bind("<Button-1>", lambda e: self.scrollable_frame.focus_set())
        
        # Label hướng dẫn
        instruction_label = ctk.CTkLabel(
            self.scrollable_frame,
            text="Chọn file HTML để bắt đầu chỉnh sửa",
            font=ctk.CTkFont(size=16)
        )
        instruction_label.pack(pady=20)
    
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
        """Phân tích HTML và tạo các editor cho text"""
        # Xóa các widget cũ trong scrollable frame
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        # Parse HTML với BeautifulSoup
        soup = BeautifulSoup(self.html_content, 'html.parser')
        self.text_elements = []
        
        # Tìm tất cả các element có text
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
        
        # Tạo giao diện chỉnh sửa
        if not self.text_elements:
            no_text_label = ctk.CTkLabel(
                self.scrollable_frame,
                text="Không tìm thấy text nào để chỉnh sửa trong file HTML",
                font=ctk.CTkFont(size=14)
            )
            no_text_label.pack(pady=20)
            return
        
        # Tạo editor cho mỗi text element
        for i, text_data in enumerate(self.text_elements):
            self.create_text_editor(i, text_data)
        
        # Bind lại mousewheel cho các widget mới được tạo và refresh focus
        self.root.after(200, lambda: self.bind_mousewheel(self.scrollable_frame))
        self.root.after(300, lambda: self.scrollable_frame.focus_set())
    
    def create_text_editor(self, index, text_data):
        """Tạo editor cho một text element"""
        # Frame container cho mỗi editor
        editor_frame = ctk.CTkFrame(self.scrollable_frame)
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
        """Lấy HTML đã được cập nhật với text mới"""
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
            messagebox.showinfo("Preview", "Đang khởi động preview server...\nTrình duyệt sẽ tự động mở trong giây lát.")
            
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