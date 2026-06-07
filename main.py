import pygame, shutil, os, ctypes, pystray, threading
import tkinter as tk
from tkinter import ttk, simpledialog, filedialog, messagebox
from PIL import Image, ImageTk
from shutil import copy
from pystray import MenuItem as item
from webbrowser import open as open_web

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except:
    pass

ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(u'com.example.musicplayer')

mutex = ctypes.windll.kernel32.CreateMutexW(None, False, u'MusicPlayerSingletonMutex')
last_error = ctypes.windll.kernel32.GetLastError()
if last_error == 183:
    messagebox.showinfo("提示", "音乐播放器已在后台运行")
    exit(0)

pygame.mixer.init()

player=tk.Tk()
player.title('MusicPlayer')
player.iconbitmap(f'{os.path.dirname(__file__)}/icon.ico')
style = ttk.Style()
style.theme_use('clam')

style.configure('Win11.TButton', 
                background='#3d3d5c',
                foreground='white',
                borderwidth=0,
                relief='flat',
                padding=8,
                font=('Segoe UI', 10))
style.map('Win11.TButton',
          background=[('active', '#4a4a6a'), ('pressed', '#2d2d44')])

style.configure('Win11.TFrame',
                background='#1e1e2e')

style.configure('Win11.TListbox',
                background='#2d2d3d',
                foreground='white',
                borderwidth=0)

style.configure('Win11.Horizontal.TScale',
                background='#2d2d3d',
                troughcolor='#3d3d5c',
                sliderlength=20)

player.configure(bg='#1e1e2e')

album_frame = tk.Frame(player, bg='#1e1e2e')
album_frame.pack(pady=10)

song_name_label = ttk.Label(player, text='未选择音乐', foreground='#a0a0b0', background='#1e1e2e', font=('Segoe UI', 12))
song_name_label.pack(pady=5)

button_frame = tk.Frame(player, bg='#1e1e2e')
button_frame.pack(pady=5, side=tk.BOTTOM)

progress_frame = tk.Frame(player, bg='#1e1e2e')
progress_frame.pack(pady=5, side=tk.BOTTOM)

list_music_frame = tk.Frame(player, bg='#1e1e2e')
list_music_frame.pack(pady=5, padx=10, side=tk.BOTTOM)

search_frame = tk.Frame(player, bg='#1e1e2e')
search_frame.pack(pady=5, padx=10, side=tk.BOTTOM)

search_var = tk.StringVar()
search_entry = ttk.Entry(search_frame, textvariable=search_var, width=40, font=('Segoe UI', 10))
search_entry.pack(side='left', padx=5)

def search_music():
    search_text = search_var.get().lower()
    list_music.delete(0, tk.END)
    for item in music_list:
        if search_text in item.lower():
            list_music.insert(tk.END, item)

def clear_search():
    search_var.set('')
    reflesh_list_music()

search_button = ttk.Button(search_frame, text='搜索', width=8, command=search_music, style='Win11.TButton')
search_button.pack(side='left', padx=2)

clear_button = ttk.Button(search_frame, text='清除', width=8, command=clear_search, style='Win11.TButton')
clear_button.pack(side='left', padx=2)

import time

playing_music = False
is_paused = False
has_played = False
is_dragging = False
progress_var = tk.DoubleVar()
progress_bar = None
playback_base_sec = 0.0
play_start_tick = 0.0
play_mode = 0  # 0: 列表循环, 1: 单曲循环
current_song_index = -1
music_list = []

def format_time(seconds):
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"

def update_progress():
    global progress_bar, playback_base_sec, play_start_tick
    if not is_dragging:
        max_val = 100
        if progress_bar:
            max_val = progress_bar.cget('to')
        
        if pygame.mixer.music.get_busy():
            now_tick = time.time()
            current_pos = playback_base_sec + (now_tick - play_start_tick)
            if current_pos > max_val:
                current_pos = max_val
            progress_var.set(current_pos)
        else:
            current_pos = progress_var.get()
            if current_pos > max_val:
                current_pos = max_val
                progress_var.set(current_pos)
        try:
            current_time_label.config(text=format_time(current_pos))
            duration_label.config(text=format_time(max_val))
        except:
            pass
    player.after(100, update_progress)

tray_image = Image.open(f'{os.path.dirname(__file__)}/musicplayer.png')
tray_image = tray_image.resize((64, 64))

def show_window(icon, item):
    global tray_thread
    icon.stop()
    player.deiconify()
    tray_thread = threading.Thread(target=run_tray, daemon=True)
    tray_thread.start()
    player.bind('<space>', switch_play)

def quit_tray(icon, item):
    icon.stop()
    pygame.mixer.music.stop()
    player.destroy()

def on_closing():
    player.withdraw()

def switch_play(event=None):
    global playing_music, is_paused, has_played
    if pygame.mixer.music.get_busy():
        pygame.mixer.music.pause()
        is_paused = True
        playing_music = True
    elif playing_music and is_paused:
        pygame.mixer.music.unpause()
        is_paused = False
        playing_music = True
    elif playing_music:
        pygame.mixer.music.play()
        is_paused = False
        has_played = True
        playing_music = True
def run_tray():
    menu = (item('显示窗口', show_window),
            item('隐藏窗口', on_closing),
            item('播放/暂停', switch_play),
            item('退出', quit_tray))
    tray_icon = pystray.Icon("MusicPlayer", tray_image, "MusicPlayer", menu)
    tray_icon.run()

player.protocol("WM_DELETE_WINDOW", on_closing)

tray_thread = threading.Thread(target=run_tray, daemon=True)
tray_thread.start()

update_progress()

def on_progress_change(value):
    current_time_label.config(text=format_time(float(value)))

def on_progress_drag_start(event):
    global is_dragging, is_paused
    is_dragging = True
    is_paused = True
    pygame.mixer.music.pause()

def on_progress_drag_end(event):
    global is_dragging, is_paused, playback_base_sec, play_start_tick
    is_dragging = False
    target_sec = progress_var.get()
    if progress_bar:
        max_val = progress_bar.cget('to')
        if target_sec > max_val:
            target_sec = max_val
            progress_var.set(target_sec)
    try:
        pygame.mixer.music.set_pos(target_sec)
        playback_base_sec = target_sec
        play_start_tick = time.time()
        pygame.mixer.music.unpause()
        is_paused = False
    except:
        pass

def reset_playback_timer():
    global playback_base_sec, play_start_tick
    playback_base_sec = 0.0
    play_start_tick = time.time()

def get_music_list():
    global music_list
    music_list = []
    data_dir = f"{os.path.dirname(__file__)}\\data"
    for dir_name in os.listdir(data_dir):
        dir_path = os.path.join(data_dir, dir_name)
        if os.path.isdir(dir_path):
            music_list.append(dir_name)

def check_music_end():
    global current_song_index, play_mode, playing_music, is_paused, has_played
    if playing_music and not pygame.mixer.music.get_busy() and not is_paused and has_played:
        if play_mode == 1:
            load_and_play_song(current_song_index)
        else:
            current_song_index = (current_song_index + 1) % len(music_list)
            load_and_play_song(current_song_index-1)
    player.after(100, check_music_end)

def load_and_play_song(index):
    global playing_music, is_paused, has_played, progress_bar, current_song_index
    if index < 0 or index >= len(music_list):
        return
    current_song_index = index
    selected = music_list[index]
    song_name_label.config(text=selected)
    dirfiles = os.listdir(f"{os.path.dirname(__file__)}\\data\\{selected}")
    
    for file in dirfiles:
        if file.lower().endswith(SUPPORTED_MUSIC_EXTENSIONS):
            pygame.mixer.music.load(os.path.join(f"{os.path.dirname(__file__)}\\data\\{selected}", file))
            pygame.mixer.music.play()
            playing_music = True
            is_paused = False
            has_played = True
            progress_var.set(0)
            reset_playback_timer()
            if progress_bar:
                try:
                    duration = pygame.mixer.Sound(os.path.join(f"{os.path.dirname(__file__)}\\data\\{selected}", file)).get_length()
                    progress_bar.config(to=duration)
                except:
                    progress_bar.config(to=100)
            break
    
    for file in dirfiles:
        if file.lower().endswith(SUPPORTED_IMAGE_EXTENSIONS):
            album_image = Image.open(os.path.join(f"{os.path.dirname(__file__)}\\data\\{selected}", file))
            album_image = album_image.resize((300, 300))
            album_image = ImageTk.PhotoImage(album_image)
            album.config(image=album_image)
            album.image = album_image
            break

def play_next():
    global current_song_index
    if len(music_list) == 0:
        return
    current_song_index = (current_song_index + 1) % len(music_list)
    load_and_play_song(current_song_index)

def play_prev():
    global current_song_index
    if len(music_list) == 0:
        return
    current_song_index = (current_song_index - 1) % len(music_list)
    load_and_play_song(current_song_index)

def switch_play_mode():
    global play_mode
    play_mode = (play_mode + 1) % 2
    mode_names = ['列表循环', '单曲循环']
    mode_button.config(text=mode_names[play_mode])

get_music_list()
check_music_end()

prev_button = ttk.Button(button_frame, text='上一首', width=10, command=play_prev, style='Win11.TButton')
prev_button.pack(side='left', padx=2)

start_play_button = ttk.Button(button_frame, text='播放/暂停', width=10, command=switch_play, style='Win11.TButton')
start_play_button.pack(side='left', padx=2)

next_button = ttk.Button(button_frame, text='下一首', width=10, command=play_next, style='Win11.TButton')
next_button.pack(side='left', padx=2)

mode_button = ttk.Button(button_frame, text='列表循环', width=10, command=switch_play_mode, style='Win11.TButton')
mode_button.pack(side='left', padx=2)

def upload_music():
    file_name = simpledialog.askstring("添加音乐", "请输入音乐文件名")
    if not file_name:
        return
    mfile_path = filedialog.askopenfilename(
        title="选择音乐文件",
        filetypes=[("音乐文件", "*.mp3;*.wav;*.aac;*.flac;*.ogg;*.m4a")]
    )
    if mfile_path:
        new_dir = os.path.join(f"{os.path.dirname(__file__)}\\data", file_name)
        if not os.path.exists(new_dir):
            os.makedirs(new_dir)
        music_ext = os.path.splitext(mfile_path)[1]
        copy(mfile_path, os.path.join(new_dir, file_name + music_ext))
    else:
        return
    pfile_path = filedialog.askopenfilename(
        title="选择图片文件",
        filetypes=[("图片文件", "*.jpg;*.png;*.jpeg;*.bmp;*.webp")]
    )
    if pfile_path:
        new_dir = os.path.join(f"{os.path.dirname(__file__)}\\data", file_name)
        if not os.path.exists(new_dir):
            os.makedirs(new_dir)
        copy(pfile_path, os.path.join(new_dir, file_name + ".jpg"))
        reflesh_list_music()
    else:
        copy(f'{os.path.dirname(__file__)}/musicplayer.png', os.path.join(new_dir, file_name + ".jpg"))
        reflesh_list_music()
upload_button = ttk.Button(button_frame, text='添加音乐', width=10, command=upload_music, style='Win11.TButton')
upload_button.pack(side='left', padx=2)

def delete_music():
    global playing_music
    if not list_music.curselection():
        messagebox.showinfo("提示", "请先选择要删除的音乐目录")
        return
    selected = list_music.get(list_music.curselection()[0])
    if messagebox.askyesno("确认删除", f"确定要删除 '{selected}' 目录及其所有内容吗？"):
        pygame.mixer.music.stop()
        pygame.mixer.music.unload()
        playing_music = False
        import shutil
        dir_path = os.path.join(f"{os.path.dirname(__file__)}\\data", selected)
        if os.path.exists(dir_path):
            for item in os.listdir(dir_path):
                item_path = os.path.join(dir_path, item)
                if os.path.isfile(item_path):
                    os.remove(item_path)
            os.rmdir(dir_path)
            reflesh_list_music()

delete_button = ttk.Button(button_frame, text='删除音乐', width=10, command=delete_music, style='Win11.TButton')
delete_button.pack(side='left', padx=2)

def restore_list():
    if messagebox.askyesno("确认恢复", "确定要恢复列表吗？这将清除当前data文件夹中的所有内容。"):
        pygame.mixer.music.stop()
        pygame.mixer.music.unload()
        data_dir = os.path.join(f"{os.path.dirname(__file__)}", "data")
        rdata_dir = os.path.join(f"{os.path.dirname(__file__)}", "rdata")
        
        if os.path.exists(data_dir):
            for item in os.listdir(data_dir):
                item_path = os.path.join(data_dir, item)
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)
        
        if os.path.exists(rdata_dir):
            for item in os.listdir(rdata_dir):
                src_path = os.path.join(rdata_dir, item)
                dst_path = os.path.join(data_dir, item)
                if os.path.isdir(src_path):
                    shutil.copytree(src_path, dst_path)
                else:
                    shutil.copy2(src_path, dst_path)
        
        reflesh_list_music()
        messagebox.showinfo("提示", "列表恢复完成！")

restore_button = ttk.Button(button_frame, text='恢复列表', width=10, command=restore_list, style='Win11.TButton')
restore_button.pack(side='left', padx=2)

reflesh_list_button = ttk.Button(button_frame, text='刷新列表', width=10, style='Win11.TButton')
reflesh_list_button.pack(side='left', padx=2)
list_music = tk.Listbox(list_music_frame, bg='#2d2d3d', fg='white', bd=0, selectbackground='#4a4a6a', font=('Segoe UI', 10), width=50, height=4)
list_music.pack()
list_music.bind('<<ListboxSelect>>',lambda event:play_music(event))
def reflesh_list_music():
    global music_list
    list_music.delete(0,tk.END)
    music_list = []
    data_dir = f"{os.path.dirname(__file__)}\\data"
    for dir_name in os.listdir(data_dir):
        dir_path = os.path.join(data_dir, dir_name)
        if os.path.isdir(dir_path):
            list_music.insert(tk.END, dir_name)
            music_list.append(dir_name)
reflesh_list_music()
reflesh_list_button.config(command=reflesh_list_music)

SUPPORTED_MUSIC_EXTENSIONS = ('.mp3', '.wav', '.aac', '.flac', '.ogg', '.m4a')
SUPPORTED_IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.bmp', '.webp')

def play_music(event):
    global playing_music, is_paused, has_played, progress_bar, current_song_index
    selected = list_music.get(event.widget.curselection()[0])
    current_song_index = music_list.index(selected)
    song_name_label.config(text=selected)
    dirfiles = os.listdir(f"{os.path.dirname(__file__)}\\data\\{selected}")
    for file in dirfiles:
        if file.lower().endswith(SUPPORTED_MUSIC_EXTENSIONS):
            pygame.mixer.music.load(os.path.join(f"{os.path.dirname(__file__)}\\data\\{selected}",file))
            progress_var.set(0)
            reset_playback_timer()
            if progress_bar:
                try:
                    duration = pygame.mixer.Sound(os.path.join(f"{os.path.dirname(__file__)}\\data\\{selected}",file)).get_length()
                    progress_bar.config(to=duration)
                    duration_label.config(text=format_time(duration))
                except:
                    progress_bar.config(to=100)
                    duration_label.config(text='01:40')
            break
    for file in dirfiles:
        if file.lower().endswith(SUPPORTED_IMAGE_EXTENSIONS):
            album_image=Image.open(os.path.join(f"{os.path.dirname(__file__)}\\data\\{selected}",file))
            if album_image.size[0]==2048 and album_image.size[1]==1080:
                album_image=album_image.resize((1024,540))
            else:
                album_image=album_image.resize((300,300))
            album_image=ImageTk.PhotoImage(album_image)
            album.config(image=album_image)
            album.image = album_image
            break
    playing_music = True
    is_paused = False
    has_played = False
image_album=Image.open(f'{os.path.dirname(__file__)}/musicplayer.png')
image_album=image_album.resize((300,300))
image_album=ImageTk.PhotoImage(image_album)
album = ttk.Label(album_frame, image=image_album)
album.image = image_album
album.pack()

current_time_label = ttk.Label(progress_frame, text='00:00', foreground='#a0a0b0', background='#1e1e2e', font=('Segoe UI', 9))
current_time_label.pack(side='left', padx=5)

progress_bar = ttk.Scale(progress_frame, variable=progress_var, from_=0, to=100, orient='horizontal', length=300, command=on_progress_change)
progress_bar.pack(side='left', padx=5)

duration_label = ttk.Label(progress_frame, text='00:00', foreground='#a0a0b0', background='#1e1e2e', font=('Segoe UI', 9))
duration_label.pack(side='left', padx=5)

phigros_chart_downloader_website_open = ttk.Button(button_frame, text='Phi下载器', width=10, command=lambda:open_web('https://swordalt.github.io/phigros-chart-downloader/'), style='Win11.TButton')
phigros_chart_downloader_website_open.pack(side=tk.LEFT, padx=2)

progress_bar.bind('<ButtonPress-1>', on_progress_drag_start)
progress_bar.bind('<ButtonRelease-1>', on_progress_drag_end)


player.mainloop()