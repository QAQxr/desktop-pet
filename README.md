# Desktop Pet（桌宠）

一个运行在 Linux 桌面上的桌面宠物项目。第一阶段目标是建立**完整、稳定、可扩展**的桌宠框架，而不是接入 AI。

当前角色：**小白**（白发蓝眼、有小兔发夹）。

---

## 环境要求

- Linux（已在 Ubuntu 22.04.5 / GNOME 上验证）
- [Miniconda / Anaconda](https://docs.conda.io/)（`conda` 可用）
- 图形会话：X11 或 Wayland（GNOME）皆可
- 无需 `sudo`，不修改系统 Python

本机验证环境：

| 组件 | 版本 |
|---|---|
| OS | Ubuntu 22.04.5 LTS |
| Conda | 26.1.1 |
| Python | 3.11.16 |
| PySide6 | 6.11.2 |
| numpy | 2.4.6 |
| Pillow | 12.3.0 |
| PyYAML | 6.0.3 |

---

## Conda 环境创建方式

```bash
conda create -n desktop-pet python=3.11 -y
```

## 依赖安装方式

```bash
conda run -n desktop-pet python -m pip install -r requirements.txt
```

依赖精确版本见 `requirements.txt` 与 `logs/pip-freeze.txt`。

---

## 启动方式

```bash
./run.sh
```

或手动：

```bash
conda run --no-capture-output -n desktop-pet python src/main.py
```

可选参数：

```bash
# 渲染一帧保存为图片后退出（用于无干扰自检）
conda run --no-capture-output -n desktop-pet python src/main.py \
    --screenshot logs/check.png --screenshot-delay 1.0

# 指定配置
conda run --no-capture-output -n desktop-pet python src/main.py --config config/config.yaml
```

运行测试：

```bash
conda run -n desktop-pet python -m unittest discover -s tests -v
```

---

## 项目结构

```text
desktop-pet/
├── picture/
│   ├── original/          # 原始素材（只读，禁止修改/删除/重命名）
│   │   ├── file           # WebP 964×964（与 file.png 相同）
│   │   ├── file.png       # PNG 964×964 角色立绘（白底）
│   │   └── 素材.png        # PNG 1254×1254 角色设计参考图
│   └── generated/         # 程序生成的派生资源（占位）
│       ├── MANIFEST.json
│       └── character/idle/idle_00.png
├── src/
│   ├── main.py            # 程序入口
│   ├── config/            # 配置加载
│   │   └── settings.py
│   ├── animation/         # 动画层（独立于窗口）
│   │   ├── asset_loader.py   # 素材发现
│   │   ├── background.py     # 抠图
│   │   ├── transform.py      # AnimationTransform（视觉偏移）
│   │   ├── clock.py          # 可暂停时钟（纯 Python，可测试）
│   │   ├── idle.py           # IdleAnimation + 纯函数 idle_transform
│   │   └── controller.py     # AnimationController（Qt 定时驱动）
│   ├── behavior/          # 状态机 / 自主行为（后续）
│   ├── world/             # 桌面物件（后续）
│   ├── pet/               # 桌宠核心（后续）
│   └── ui/                # 透明窗口（只负责显示）
│       └── desktop_window.py
├── config/
│   └── config.yaml
├── tools/
│   └── generate_assets.py # 生成派生占位素材（只读原始素材）
├── tests/
├── logs/
├── requirements.txt
├── run.sh
└── README.md
```

设计原则：**窗口系统 ≠ 动画系统 ≠ 行为系统 ≠ 世界/物件系统**，各模块尽量解耦。

---

## 素材说明

### original（原始资源，只读）

位于 `picture/original/`，权限设为 `r--r--r--`。脚本与程序**只读取，绝不写入**。

| 文件 | 格式 | 尺寸 | 说明 |
|---|---|---|---|
| `file` | WebP | 964×964 | 与 `file.png` 逐像素相同 |
| `file.png` | PNG (RGB) | 964×964 | 角色立绘，白底不透明 |
| `素材.png` | PNG (RGBA) | 1254×1254 | 角色设计参考图（整张设计板，非精灵帧） |

> 原始设计板中包含动作标注（待机/走路/坐下/睡觉等）与物件（椅子/床/桌子等），但它们**不是可直接使用的独立动画帧**。

### generated / placeholder（程序生成的占位资源）

位于 `picture/generated/`，由 `tools/generate_assets.py` 生成：

- 用**边界洪水填充**抠掉白底，输出透明 RGBA。
- 输出 `character/idle/idle_00.png`，并在 `MANIFEST.json` 中标记为
  `"classification": "generated / placeholder"`。

> 这些是**占位素材，不是正式动作帧**。未来获得真实帧（idle/walk/sit…）时，只要按命名约定放入
> `picture/generated/character/<action>/`，即可被动画系统直接替换，**无需改动动画系统代码**。

### 素材命名约定

```text
<action>[_<left|right|front|back>]_<NN>.png   # 例如 idle_00.png、walk_right_01.png
```

`src/animation/asset_loader.py` 会按此约定扫描 `generated/`（优先）与 `original/` 目录。

---

## 当前已实现功能

### Step 4

- [x] 无边框、背景透明的桌面窗口（`Qt.FramelessWindowHint` + `WA_TranslucentBackground`）
- [x] 从 `picture/` 自动发现并加载角色素材
- [x] 白底自动抠图生成透明立绘（程序化占位）
- [x] 角色在透明窗口中正确显示
- [x] 配置文件化（`walk_speed` / `idle_time` / `window_scale` / `behavior_enabled` …）
- [x] 自动化测试与自检截图

### Step 5（程序化 Idle 动画）

- [x] 独立动画层：`transform → clock → idle → controller`，与窗口/UI 解耦
- [x] 用 `sin()` 驱动轻微上下浮动 + 轻微缩放（呼吸感），alpha 不变
- [x] 基于 `QTimer`（默认 30 FPS）驱动，不阻塞 GUI 主线程；不使用 `sleep` 循环
- [x] 支持 `start() / pause() / resume() / stop()`，暂停时画面冻结在当前位置
- [x] 动画参数全部配置化（周期、浮动幅度、缩放幅度、旋转、FPS、开关）
- [x] **世界位置与动画偏移分离**：动画只改变绘制偏移，不移动窗口
- [x] 动画在内存中完成，不生成任何新 PNG
- [x] 自动化测试覆盖动画数学、时钟暂停/恢复、控制器状态、配置加载

尚未实现（后续 Step）：移动、点击/拖动、状态机、桌面物件、自主行为。

---

## 动画系统（Step 5）

### 架构分层

```text
World Position   （窗口真实位置，ui/desktop_window.py）
      +
Animation Offset （animation/transform.py，动画产生的视觉偏移）
      =
Render Position  （最终绘制位置，paintEvent 中合成）
```

`DesktopWindow` 拥有窗口真实坐标，只通过 `set_animation_transform()` 接收偏移并在
`paintEvent` 中合成，**绝不通过 `window.move()` 实现呼吸动画**，为 Step 6 的移动留出空间。

### Idle 动画

- 纯函数 `idle_transform(t, ...)` 把「时间 → 偏移」抽象出来，便于单元测试。
- `IdleAnimation.sample(t)` 返回 `AnimationTransform(dy, scale, rotation, alpha)`。
- 默认参数：`duration=3.0s`、`float_amplitude=2.0px`、`scale_amplitude=0.01`、`rotation=0.0°`。
- 窗口四周预留 padding（由 `render_padding()` 计算），避免浮动/缩放被裁剪。

### 控制接口

```text
controller.start()    # 开始（t=0 立即渲染一帧）
controller.pause()    # 暂停，画面停止在当前状态
controller.resume()   # 从暂停处继续，不跳变
controller.stop()     # 停止并回到基础位置
```

### 配置

```yaml
animation:
  enabled: true
  fps: 30
  idle:
    enabled: true
    duration: 3.0
    float_amplitude: 2.0
    scale_amplitude: 0.01
    rotation_amplitude: 0.0
```

命令行开关（便于测试，未来可被右键菜单/行为系统复用）：

```bash
./run.sh --no-animation                 # 禁用动画
./run.sh --pause-at 1.0 --resume-at 2.5 # 1s 暂停、2.5s 恢复
./run.sh --run-seconds 8                # 运行 8 秒后自动退出
./run.sh --screenshot-seq logs/step5-animation-check --frame-count 6 --frame-interval 0.5
```

---

## 已知限制

- 当前只有**单帧静态立绘**，尚无正式动画帧；动作表现为占位。
- Idle 动画是**对单帧做程序化变换**（浮动/缩放），不是真实逐帧动画，幅度刻意很轻微。
- `rotation_amplitude` 默认为 0（不倾斜），因为单帧旋转在边缘容易显得不自然。
- 实测参考：30 FPS 下平均 CPU 约 10%、RSS 约 89 MB（软件渲染，随硬件与合成器而异）。
- 设计稿中的动作/物件为参考图，未切分，暂不能直接作为素材。
- `file` / `file.png` 白底抠图对浅色毛发边缘可能出现轻微残留，属占位级质量。
- 首次运行前需先生成派生素材：`conda run -n desktop-pet python tools/generate_assets.py`。

---

## Wayland / XWayland 说明

项目采用**自动兼容**策略，不强制绑定某一后端：

- 未设置 `QT_QPA_PLATFORM` 时，Qt 按当前会话自动选择后端（Wayland 会话 → `wayland`，X11 会话 → `xcb`）。
- **原生 Wayland 的限制**：合成器不允许应用任意摆放窗口位置，`move()` 可能被忽略，且无法保证“置底/桌面层级”。因此后续的**自由移动定位**功能在原生 Wayland 下可能受限。
- **XWayland 兼容模式**：当需要精确控制桌宠坐标时，可强制 `xcb`：

  ```bash
  QT_QPA_PLATFORM=xcb ./run.sh
  ```

  也可在 `config/config.yaml` 中设置 `platform.override: xcb`，或使用环境变量 `DESKTOP_PET_QT_PLATFORM=xcb`。
- 本项目**不修改系统环境**来强制切换后端。

透明度与无边框在 Wayland / X11 下均可用；差异主要在窗口定位与层级控制。

---

## 日志说明

| 位置 | 内容 |
|---|---|
| `~/opencode/log/desktop-pet/` | 开发审计日志（环境变更、文件增删、命令与结果） |
| `logs/` | 项目运行日志（`desktop-pet-YYYY-MM-DD.log`）、`pip-freeze.txt`、自检截图 |

日志中明确区分：**original resource / generated resource / project code / environment change**。
运行时日志（`*.log`）已在 `.gitignore` 中忽略。

---

## 后续计划

```text
Step 5  程序化 idle 动画（呼吸 / 轻微浮动）   ✅ 已完成
Step 6  基础移动（速度、目标点、左右方向）
Step 7  鼠标点击 / 拖动
Step 8  状态机（IDLE / WALK / SIT …）
Step 9  桌面物件（Chair 等）
Step 10 简单自主行为（规则系统，无 LLM）
```

远期：更多动作、更多物件、多角色、情绪/记忆、小游戏、环境感知。第一阶段不接入 LLM / 云 API / 数据库。
