import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageDraw, ImageFont

def generate_tape():
    try:
        # 获取界面上的参数
        w = int(entry_w.get())
        h = int(entry_h.get())
        stripe_w = int(entry_stripe_w.get())
        stripe_gap = int(entry_stripe_gap.get())
        text = entry_text.get()
        font_size = int(entry_font_size.get())
        
        # 颜色设定：经典的警示黄和深灰黑
        color_bg = "#FFCC00" 
        color_stripe = "#1A1A1A"

        # 1. 创建基础图像 (黄色背景)
        img = Image.new('RGB', (w, h), color=color_bg)
        draw = ImageDraw.Draw(img)

        # 2. 画斜条纹 (黑色平行四边形)
        # 考虑到倾斜角度，循环范围需要向左扩展高度的距离
        step = stripe_w + stripe_gap
        for x in range(-h, w + h, step):
            points = [
                (x, 0),                           # 左上点
                (x + stripe_w, 0),                # 右上点
                (x + stripe_w - h, h),            # 右下点 (向左倾斜)
                (x - h, h)                        # 左下点
            ]
            draw.polygon(points, fill=color_stripe)

        # 3. 画文字 (带描边以防被条纹吞没)
        if text.strip():
            # 尝试加载支持中文的字体（优先微软雅黑，其次黑体）
            try:
                font = ImageFont.truetype("msyh.ttc", font_size)
            except IOError:
                try:
                    font = ImageFont.truetype("simhei.ttf", font_size)
                except IOError:
                    font = ImageFont.load_default()
                    messagebox.showwarning("字体警告", "未找到默认中文字体，可能无法显示中文。")

            # 计算文字居中的位置
            bbox = draw.textbbox((0, 0), text, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            
            text_x = (w - text_w) / 2
            # 修正Y轴偏移，使其在视觉上更居中
            text_y = (h - text_h) / 2 - bbox[1] 

            # 画文字：设置背景同色的粗描边，让文字在条纹中更清晰
            stroke_width = max(2, font_size // 12)
            draw.text((text_x, text_y), text, font=font, fill=color_stripe, 
                      stroke_width=stroke_width, stroke_fill=color_bg)

        # 4. 保存图片
        save_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG 图片", "*.png")],
            initialfile="CAUTION_TAPE.png",
            title="保存警示条"
        )
        if save_path:
            img.save(save_path)
            messagebox.showinfo("搞定！", f"无水印警示条已生成！\n保存在: {save_path}")

    except ValueError:
        messagebox.showerror("参数错误", "请输入有效的数字！尺寸、间距、字体大小必须是整数。")
    except Exception as e:
        messagebox.showerror("运行错误", f"出Bug了:\n{e}")

# ================= UI 界面设置 =================
root = tk.Tk()
root.title("硬核工业警示条生成器")
root.geometry("380x320")
root.configure(padx=20, pady=20)

# 创建输入框和标签的简易函数
def create_input(parent, label_text, default_val, row):
    tk.Label(parent, text=label_text, font=("微软雅黑", 10)).grid(row=row, column=0, sticky="e", pady=5)
    entry = tk.Entry(parent, font=("微软雅黑", 10), width=20)
    entry.insert(0, str(default_val))
    entry.grid(row=row, column=1, pady=5, padx=5)
    return entry

# 默认参数（你可以根据需要修改默认值）
entry_w = create_input(root, "总宽度 (像素):", 2000, 0)
entry_h = create_input(root, "总高度 (像素):", 150, 1)
entry_stripe_w = create_input(root, "黑条宽度:", 60, 2)
entry_stripe_gap = create_input(root, "黄条间距:", 80, 3)
entry_text = create_input(root, "警示文字:", "DANGER // 中国地质大学(北京) 教三101", 4)
entry_font_size = create_input(root, "字体大小:", 70, 5)

# 生成按钮
generate_btn = tk.Button(root, text="🔥 一键生成PNG", font=("微软雅黑", 12, "bold"), 
                         bg="#FFCC00", fg="#1A1A1A", command=generate_tape)
generate_btn.grid(row=6, column=0, columnspan=2, pady=20, ipadx=20)

root.mainloop()