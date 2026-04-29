# OpenAnima

<p align="center">
  <img src="icon.png" width="120" alt="OpenAnima Icon" />
</p>

## 🧠 What is OpenAnima?

**OpenAnima** is an open-source desktop animation overlay engine for Windows.

It allows you to place animated GIFs directly on your desktop, interact with them, and control their behavior in real time — similar to desktop pets or overlay tools, but fully customizable and extensible.

Instead of being just a wallpaper, OpenAnima lets you:

* Spawn multiple animated elements
* Drag them anywhere
* Lock them in place
* Make them click-through
* Control their speed, size, and opacity

All in a lightweight Python-based application.

---

## ✨ Core Features

### 🖱️ Desktop Animation Overlays

* Place animated GIFs anywhere on your screen
* Each animation is an independent window
* Smooth dragging and positioning

### 🎛️ Live Editing System

Modify animations in real time via the Control Panel:

* Scale (resize animations)
* Opacity (transparency)
* Speed (slow motion / fast playback)
* Always-on-top toggle
* Click-through mode

### 📌 Interaction Modes

* **Lock mode** → prevent accidental movement
* **Click-through mode** → interact with apps behind the animation

### 🧠 Persistent State

All animations automatically save:

* Position
* Scale
* Opacity
* Speed
* Interaction settings

Everything is restored on next launch.

---

## 🧰 Control Panel

OpenAnima includes a built-in Control Panel UI:

### 📚 Library Tab

* Browse available GIFs
* Import new animations
* Add them to desktop

### ⚡ Active Tab

* View all running animations
* Select, lock/unlock, or close them

### 🛠️ Editor Tab

* Fine-tune selected animation
* Adjust scale, opacity, and speed
* Toggle behavior settings

---

## 📦 Asset System

Animations are managed via a simple folder structure:

```
assets/
  pack1/
  pack2/
```

* Organize GIFs into packs
* Switch packs from the Control Panel
* Import new GIFs easily

---

## 🖥️ System Integration

* Runs in system tray
* Can stay always on top
* Lightweight runtime (low CPU/RAM usage)
* Works as a portable executable

---

## 🚀 Download

Get the latest Windows build from:

👉 [https://github.com/Ertugrulmutlu/OpenAnima/releases/tag/v0.1.0](https://github.com/Ertugrulmutlu/OpenAnima/releases/tag/v0.1.0)

---

## ▶️ Usage

### Start the app

```
OpenAnima.exe
```

### First launch

The app automatically creates:

```
assets/
config.json
```

### Add your first animation

1. Open Control Panel
2. Go to **Library**
3. Click **Import GIF**
4. Click **Add to Desktop**

---

## ⚙️ Build from Source

```bash
pip install -r requirements.txt
python main.py
```

---

## 📦 Build EXE

```bash
pyinstaller --noconfirm --onefile --windowed --name OpenAnima --icon=icon.ico --add-data "icon.ico;." main.py
```

Output:

```
dist/OpenAnima.exe
```

---

## 🧠 Tech Stack

* Python
* PySide6 (Qt)
* PyInstaller

---

## 💡 Why OpenAnima?

Most desktop customization tools are:

* Closed-source
* Heavy
* Hard to extend

OpenAnima is:

* Open-source
* Lightweight
* Hackable
* Developer-friendly

---

## 🔮 Future Ideas

* Plugin system
* Advanced animation behaviors
* More UI polish
* Cross-platform support

---

## 🤝 Contributing

Contributions are welcome.

If you have ideas or improvements:

* Open an issue
* Submit a pull request

---

## ⭐ Support

If you like the project, give it a star ⭐

---

## 📜 License

MIT License

---

Built with ❤️ by Ertuğrul Mutlu
