# 失物解锁 - 校园寻物平台

基于人脸识别的失物招领系统。发布失物/招领信息，通过摄像头人脸识别确认认领人身份，数据持久化到本地 SQLite。

一个大一萌新小项目，还请多多指教。
目前还是demo版，如果有任何问题请联系：creep3rq@outlook.com

在windows和linux上实现略有区别（主要是我们的linux环境机只有cpu）

需要手动安装flask依赖（如果没有的话）buffalo_l模型会自动检测安装

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Flask, SQLite3 |
| 人脸识别 | InsightFace + ONNX Runtime |
| 图像处理 | OpenCV |
| 前端 | HTML + Tailwind CSS + vanilla JS |
| 摄像头 | getUserMedia + Canvas |

## 目录结构

```
├── face_demo2.py          # Flask 后端（API + 人脸识别）
├── index.html             # 前端页面（由 Flask serve）
├── data.db                # SQLite 数据库（自动生成，已 gitignore）
├── uploads/               # 用户上传的失物图片（自动生成，已 gitignore）
├── .gitignore
├── face_dataset/          # 人脸库（图片已 gitignore）
│   ├── README.md
│   └── .gitkeep
└── README.md
```

## 环境依赖

- Python 3.10+
- 摄像头（用于认领时人脸识别）

```bash
pip install flask insightface opencv-python numpy
```

> InsightFace 首次启动会自动下载模型（~330MB）到 `~/.insightface/models/`。

## 使用流程

### 1. 准备人脸数据

把人脸照片放到 `face_dataset/` 下，**文件名即人名**：

```
face_dataset/
├── somebody.png          # 识别为 "somebody"
└── 张三.jpg              # 识别为 "张三"
```

### 2. 启动服务

```powershell
cd E:\task
python face_demo2.py
```

看到 `[Server] http://localhost:5000` 即启动成功。

### 3. 打开页面

浏览器访问 **`http://localhost:5000/`**

### 4. 发布物品

点击「+ 发布新物品」→ 选择类型（招领/失物）→ 填写标签、描述、地点 → 上传图片 → 立即发布。

数据写入 `data.db`（items 表），图片存到 `uploads/` 目录。

### 5. 人脸认领

点击物品卡片上的「认领」→ 摄像头拍照 → 后端人脸比对：

- **匹配成功** → 显示姓名 + 相似度 →「确认认领」→ 物品状态变为「XXX 已认领」
- **未匹配** → 提示陌生人，无法认领 → 可重新拍照

认领记录写入 `data.db`（claim_log 表），包含：物品ID、认领人、相似度、时间戳。

### 6. 添加更多用户

把新用户的照片放入 `face_dataset/`，**重启服务**即可生效。

## API 列表

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/` | 前端页面 |
| GET | `/api/items` | 获取所有物品 |
| POST | `/api/items` | 发布新物品 |
| POST | `/api/items/<id>/claim` | 认领物品 |
| POST | `/api/upload` | 上传图片（FormData） |
| GET | `/api/logs` | 认领日志 |
| POST | `/recognize` | 人脸识别（Base64 图片） |

## 数据库

### items 表

| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER | 主键 |
| post_type | TEXT | 招领/失物 |
| tag | TEXT | 物品标签 |
| desc | TEXT | 描述 |
| loc | TEXT | 地点 |
| time | TEXT | 发布时间 |
| status | TEXT | 进行中/已认领 |
| claimed_by | TEXT | 认领人（NULL=未认领） |
| img_path | TEXT | 图片路径或 URL |

### claim_log 表

| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER | 主键 |
| item_id | INTEGER | 关联物品ID |
| name | TEXT | 认领人 |
| sim | REAL | 相似度 |
| time | TEXT | 认领时间 |
