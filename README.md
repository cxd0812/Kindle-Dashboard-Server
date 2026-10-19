# Kindle Oasis Dashboard Server (Todo Edition)

[English](README-en.md)

这是一个专为 **Kindle Oasis** 及其他墨水屏设备设计的 E-ink 仪表盘服务端程序。

它旨在配合 Kindle 上的 KUAL 扩展（或其他浏览器/截图工具）使用，提供一个高对比度、低刷新率、信息丰富且美观的 "Always-on" 桌面副屏与待办看板。

## 🌟 特色功能

*   **全球化与智能定位**: 
    *   **IP 自动定位**: 启动时自动通过公网 IP 获取当前地理位置（经纬度、城市名称与时区），自动拉取当地天气与空气质量 (AQI)，免去手动配置经纬度的繁琐；同时保留手动配置兜底。
    *   **多语言界面**: 原生支持中文 (CN) 和英文 (EN) 切换。
    *   **多国法定节假日**: 集成 `holidays` 库，支持配置不同国家/地区的法定节假日与休息日倒计时。
*   **丰富的数据展示**:
    *   **天气预报**: 包含气温、湿度、UV 指数、AQI、降雨概率及未来趋势预测。
    *   **日历信息**: 包含公历日期、星期、农历日期以及自定义节假日提醒。
    *   **待办事项清单 (Todo List)**: 下半屏全面升级为墨水屏高对比度双列待办清单，直观展示今日任务与完成状态。
*   **多端待办事项管理系统**:
    *   **移动端与网页端管理界面 (`/todos`)**: 支持在手机、平板或电脑浏览器打开 `/todos`，随时新增任务、勾选完成、删除事项、一键清理已完成等，看板端实时同步更新。
    *   **本地数据持久化**: 待办数据保存在 `data/todos.json`，支持 Docker Volume 挂载持久化。
*   **服务端自动化渲染**:
    *   **高度可配置**: 通过 `.env` 文件配置分辨率、语言、位置、缓存时间等。
    *   **高质量抖动算法**: 渲染 16 级灰度图像并应用 Floyd-Steinberg 抖动，为 E-ink 屏提供最佳观感。
    *   **适配多设备**: `/render` 接口会自动缩放到配置的屏幕分辨率。

## 🛠 技术栈

*   **后端**: Python 3.12, Flask, uv
*   **前端**: HTML5, Tailwind CSS
*   **渲染**: Playwright (Chromium)
*   **图像处理**: Pillow (Dithering)
*   **数据源**:
    *   `Open-Meteo`: 实时天气与空气质量
    *   `ip-api.com / ipinfo.io`: IP 逆地理定位
    *   `lunardate`: 农历转换
    *   `holidays`: 法定节假日数据

## 🚀 快速开始

### 1. 配置文件

复制配置模版：

```bash
cp .env_example .env
```

`.env` 默认已开启 `AUTO_LOCATION=True`，会自动通过 IP 获取位置。若需固定位置，可将 `AUTO_LOCATION=False` 并填写指定的经纬度。

### 2. 使用 Docker 部署

```bash
# 构建镜像 (在项目根目录下)
docker build -t kindle-dashboard .

# 运行容器 (挂载 data 目录持久化保存待办事项)
docker run -d \
  --name kindle-dashboard \
  --restart unless-stopped \
  -p 5000:5000 \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  kindle-dashboard
```

### 3. 本地开发运行

```bash
uv sync
uv run playwright install chromium --with-deps
uv run app.py
```

## 🔌 访问接口

*   **`GET /todos`** (或 `/tasks`): **待办事项管理网页**，用手机或电脑浏览器打开即可随时添加、勾选、删除待办任务。
*   **`GET /dashboard`**: 返回响应式网页版的仪表盘（可直接在浏览器中预览）。
*   **`GET /render`**: 返回 **Kindle 优化版 (按配置分辨率、16级灰度)** 的 PNG 图片，供 Kindle 定时拉取显示。
*   **`GET /health`**: 健康检查接口，返回 `OK`。

## 📱 配套客户端

如果你的 Kindle 已越狱，可以配合 [Kindle-Dashboard](https://github.com/t0saki/Kindle-Dashboard) KUAL 插件脚本使用，实现自动联网下载图片并使用 FBInk 高质量渲染。

## 📄 许可证

MIT License
