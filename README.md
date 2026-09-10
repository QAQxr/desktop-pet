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

XWayland（`xcb`）后端还需要一个 conda 包（非 pip）：

```bash
conda install -n desktop-pet -c conda-forge xcb-util-cursor -y
```

它提供 `libxcb-cursor.so.0`，仅装入 conda 环境，不修改系统。

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
│   ├── movement/          # 移动层（世界坐标，独立于绘制）
│   │   ├── position.py       # WorldPosition
│   │   ├── bounds.py         # MovementBounds（屏幕边界 + clamp）
│   │   ├── movement.py       # Direction / MovementState / MovementModel
│   │   └── controller.py     # MovementController（Qt 定时驱动）
│   ├── positioning/       # 平台窗口定位抽象（Step 6.1）
│   │   ├── service.py        # PositioningService + 能力判定
│   │   └── qt.py             # QtPositioningService（Qt 适配）
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

### Step 6（基础桌面移动）

- [x] 独立移动层 `movement/`：`WorldPosition / MovementBounds / MovementModel / MovementController`
- [x] 基于 `delta_time` 的运动：`position += velocity * delta_time`，帧率无关
- [x] 四方向移动（left / right / up / down），速度单位 pixels/second
- [x] 屏幕边界：从 Qt 屏幕几何计算，越界 `clamp` 并停止（不反弹、不寻路）
- [x] 状态：`IDLE / WALKING / PAUSED`
- [x] 移动与 Idle 动画**同时工作且互不覆盖**（移动改窗口世界坐标，动画只改绘制偏移）
- [x] 暂停/恢复同时作用于移动与动画，无位置跳变
- [x] 移动逻辑不依赖 `QWidget` 绘制；窗口只接收 `window.move()` 指令
- [ ] **注意：当前 “WALK” 只是移动状态**，并没有真实的行走逐帧动画，移动时仍播放 Idle 占位动画

### Step 6.1（平台窗口定位解耦 + 生命周期）

- [x] 新增定位抽象 `positioning/`：`PositioningService` 协议 + `supports_physical_positioning()`
- [x] 移动计算与平台定位彻底解耦：`MovementController` 不再调用 `window.move()`，也不再判断平台
- [x] `main.py` 不再堆积 `if wayland/X11`：平台细节封装在 `QtPositioningService`
- [x] 原生 Wayland：`supports_physical_positioning()==False`，逻辑位置更新但 `applied=False`，**不虚报移动成功**，打印明确警告
- [x] X11/XWayland：`applied=True`，真实窗口移动（回归验证通过）
- [x] 退出生命周期：`run.sh` 直接 `exec` 环境 python（不再经 `conda run` 转发）；程序安装 `SIGHUP/SIGINT/SIGTERM` 处理器优雅退出，关闭终端不再留下孤儿窗口/进程

尚未实现（后续 Step）：点击/拖动、状态机、桌面物件、自主行为。

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

## 移动系统（Step 6）

### 架构分层

```text
World Position     （movement/position.py，桌宠窗口真实坐标）
      +
Animation Offset   （animation/transform.py，动画视觉偏移）
      =
Render Position    （ui/desktop_window.py 的 paintEvent 合成）
```

职责严格分离：

```text
Movement   -> 改变窗口世界坐标（window.move）
Animation  -> 只改变窗口内部角色的绘制偏移
```

`MovementModel` 是纯逻辑（不含 Qt / 不绘制）；`MovementController` 仅用 `QElapsedTimer` + `QTimer`
计算并发出新坐标，由 `main.py` 把它接到 `window.move()`。因此两个系统不会互相争抢窗口坐标。

### 运动模型

```text
position += velocity * delta_time
velocity = direction_unit * speed      # speed: pixels/second
```

- 帧率无关：30 / 60 / 144 FPS 下速度一致。
- 无加速度、摩擦、碰撞、寻路（Step 6 范围之外）。

### 边界行为

- 从 Qt 当前屏幕 `availableGeometry()` 与窗口尺寸计算 `MovementBounds`（不使用固定 1920×1080）。
- 到达边界：**clamp 到边界并停止移动**（不反弹、不自动转身）。

### 配置

```yaml
movement:
  enabled: true
  speed: 120.0     # pixels per second
  direction: right # left | right | up | down（--movement-test 使用）
  fps: 60
```

> 顶层 `walk_speed` 为旧字段；当 `movement.speed` 未设置时作为回退值。

### 运行 / 验证移动

```bash
# 向右移动（真实 XWayland 窗口移动；GNOME Wayland 需 xcb）
QT_QPA_PLATFORM=xcb ./run.sh --move right --start-x 100 --start-y 200 --run-seconds 3

# 便捷测试：按 config 的方向移动
QT_QPA_PLATFORM=xcb ./run.sh --movement-test --run-seconds 4

# 禁用移动
./run.sh --no-movement

# 与动画一起截帧，日志会同时打印 world=(x,y) 与 anim_dy
./run.sh --move right --screenshot-seq logs/step6-movement-check --frame-count 6 --frame-interval 0.5
```

运行日志会输出：`initial / final / elapsed / distance / state`，用于核验速度与边界。

### 暂停 / 恢复

`--pause-at` / `--resume-at` 现在同时暂停/恢复移动与动画；暂停期间世界坐标冻结，
恢复后从暂停点继续，不会跳变。

---

## 平台定位与生命周期（Step 6.1）

### 定位抽象

移动计算与“能不能真的移动窗口”彻底分离：

```text
MovementModel        （只算“应该去哪”）
      ↓
MovementController   （QTimer/delta_time，只发 WorldPosition，不碰 window、不判断平台）
      ↓
WorldPosition
      ↓
PositioningService   （“能不能真的移动到那”）
      ├── QtPositioningService  -> xcb：window.move；wayland：拒绝并返回 False
      └── LogicalOnlyPositioning -> 仅供测试/无法物理定位的平台
```

`PositioningService` 提供：

```text
platform_name()
supports_physical_positioning()
set_position(x, y) -> bool   # False 表示平台未真正移动，调用方不得当作成功
```

- 判定规则：**原生 `wayland` 不支持物理定位**，`xcb`/`offscreen` 等支持。
- 原生 Wayland 下 `main.py` 会打印：逻辑位置在更新，但窗口不会真正移动，如需真实移动请用 XWayland/X11。
- 包名用 `positioning/` 而非 `platform/`，避免遮蔽 Python 标准库 `platform`（`src` 在 `sys.path` 首位）。

### 退出生命周期

- `run.sh` 解析出 conda 环境后**直接 `exec` 环境里的 python**，不再用 `conda run` 包裹，
  使桌宠进程处于前台进程组，关闭终端（SIGHUP）即可被送达。
- `main.py` 安装 `SIGHUP / SIGINT / SIGTERM` 处理器：收到信号后 `app.quit()`，Qt 事件循环退出、窗口销毁。
- 验证：正常退出、`--run-seconds` 自动退出、SIGHUP/SIGTERM/SIGINT 均**不残留 `main.py` 进程**。

---

## 桌宠显示层 / 平台后端（可行性调查）

目标：未来让桌宠显示在独立的“桌宠层”上、层内自由移动、且**透明区域点击穿透**。调查脚本见
[`experiments/README.md`](experiments/README.md)（可删除，不参与运行时）。

**在本机实测结论（Ubuntu 22.04 + GNOME + Wayland / Mutter）：**

| 能力 | 结果 |
|---|---|
| `zwlr_layer_shell_v1` | **不可用**（GNOME/Mutter 未实现） |
| `setMask` → Wayland `set_input_region` | **可用**（协议日志确认） |
| `setMask` → X11 窗口 shape | **可用**（`xwininfo -shape` 确认） |
| 真实点击穿透（区域外→下层应用，区域内→桌宠） | **PASS**（XWayland + XTEST 实测） |

**方案对照：**

| 方案 | 本机可用 | 定位 | 输入穿透 | 成本 |
|---|---|---|---|---|
| A. Qt 顶层窗口 + `move()`（现用） | 是 | xcb 可以；原生 Wayland 不行 | `setMask` 可行 | 低（已实现） |
| B. Layer Shell | GNOME **否**，wlroots/KDE 预期可以 | 自由/锚定 | 区域制 | 需新后端 + 多 compositor 测试 |
| C. GNOME Shell Extension | 技术上可行，未实现 | 完全可控 | 完全可控 | 高（JS、随 GNOME 版本失效、难复用 PySide6 渲染） |
| D. 其他桌面（KDE/wlroots） | 未安装，未验证 | Layer Shell 预期可以 | 区域制 | 架构应保持多后端 |

> B/C/D 对他家 compositor 的支持来自协议/文档，**本机未实测**，标注为预期而非结论。

**推荐：** 保持当前 Qt 顶层窗口后端；需要时在既有 `PositioningService` 抽象**背后**新增后端，
不重写 movement/animation：

```text
Desktop Pet core → DisplayBackend(abstract) → QtTopLevelBackend（现用）
                                            → LayerShellBackend（未来, wlroots/KDE）
                                            → GnomeExtensionBackend（未来, 较重, 可选）
```

当前 GNOME 环境：真实移动用 `xcb`；输入穿透用 `setMask`。**不**在本阶段实现 Layer Shell
后端（本机无法运行，且禁止安装/切换 compositor）。

---

## 已知限制

- 当前只有**单帧静态立绘**，尚无正式动画帧；动作表现为占位。
- **WALK 目前只是“移动状态”**：移动时仍播放 Idle 占位动画，没有真实行走逐帧动画，也没有左右翻转朝向。
- Idle 动画是**对单帧做程序化变换**（浮动/缩放），不是真实逐帧动画，幅度刻意很轻微。
- `rotation_amplitude` 默认为 0（不倾斜），因为单帧旋转在边缘容易显得不自然。
- 移动**不做碰撞、寻路、反弹、自动转身**；到达边界即 clamp 并停止。
- 多显示器：仅使用**当前窗口所在屏幕**的 `availableGeometry`，不实现跨屏移动（known limitation）。
- **原生 Wayland 下窗口移动不可见**，需 `QT_QPA_PLATFORM=xcb`（见上）。
- 实测参考：30 FPS 下平均 CPU 约 10%、RSS 约 89 MB（软件渲染，随硬件与合成器而异）。
- 设计稿中的动作/物件为参考图，未切分，暂不能直接作为素材。
- `file` / `file.png` 白底抠图对浅色毛发边缘可能出现轻微残留，属占位级质量。
- 首次运行前需先生成派生素材：`conda run -n desktop-pet python tools/generate_assets.py`。

---

## Wayland / XWayland 说明

项目采用**自动兼容**策略，不强制绑定某一后端：

- 未设置 `QT_QPA_PLATFORM` 时，Qt 按当前会话自动选择后端（Wayland 会话 → `wayland`，X11 会话 → `xcb`）。
- **原生 Wayland 的限制**：合成器**不允许应用任意摆放窗口位置**，`window.move()` 会被忽略。
  因此 Step 6 的**真实桌面移动在原生 Wayland 下不可见**（程序会检测到并打印警告，移动逻辑本身仍正确运行）。
- **XWayland（`xcb`）兼容模式**：需要精确控制桌宠坐标时使用。已验证真实窗口移动有效：

  ```bash
  QT_QPA_PLATFORM=xcb ./run.sh --move right --start-x 100 --start-y 200 --run-seconds 3
  ```

  也可在 `config/config.yaml` 设置 `platform.override: xcb`，或环境变量 `DESKTOP_PET_QT_PLATFORM=xcb`。
- **依赖说明**：Qt ≥ 6.5 的 `xcb` 插件需要 `libxcb-cursor.so.0`。本项目**不修改系统**，而是安装到 conda 环境：

  ```bash
  conda install -n desktop-pet -c conda-forge xcb-util-cursor -y
  ```

  `run.sh` 会自动把 `$CONDA_PREFIX/lib` 注入 `LD_LIBRARY_PATH`，因此无需改系统即可使用 `xcb`。
  （若直接运行 `python src/main.py` 而非 `./run.sh`，需自行 `export LD_LIBRARY_PATH=$CONDA_PREFIX/lib`。）

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
Step 6  基础移动（速度、目标点、左右方向）    ✅ 已完成
Step 7  鼠标点击 / 拖动
Step 8  状态机（IDLE / WALK / SIT …）
Step 9  桌面物件（Chair 等）
Step 10 简单自主行为（规则系统，无 LLM）
```

远期：更多动作、更多物件、多角色、情绪/记忆、小游戏、环境感知。第一阶段不接入 LLM / 云 API / 数据库。
